#!/usr/bin/env python3
"""Build worldepg from the numbered, curated XMLTV feeds published by ferteque."""
from __future__ import annotations

import concurrent.futures
import copy
import gzip
import json
import re
import shutil
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
REPOSITORY = CONFIG["upstream_repository"]
API_URL = CONFIG["upstream_api"]
RAW_BASE = CONFIG["raw_base"]
DAYS = int(CONFIG.get("target_days", 7))
MAX_WORKERS = int(CONFIG.get("download_workers", 4))
WORK = ROOT / "_source_cache"
COUNTRY_CODES = set(CONFIG.get("iso_country_codes", []))


def request(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "worldepg/1.0 (+https://github.com/AT78/worldepg)"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def discover_feeds() -> list[dict]:
    listing = json.loads(request(API_URL).decode("utf-8"))
    feeds = []
    for item in listing:
        match = re.fullmatch(r"epg(\d+)\.xml\.gz", item.get("name", ""))
        if match and item.get("type") == "file":
            feeds.append({
                "id": int(match.group(1)),
                "name": item["name"],
                "url": item.get("download_url") or f"{RAW_BASE}/{item['name']}",
                "size_bytes": item.get("size", 0),
            })
    return sorted(feeds, key=lambda item: item["id"])


def download_feed(feed: dict) -> tuple[dict, Path | None, str | None]:
    path = WORK / feed["name"]
    try:
        data = request(feed["url"], timeout=180)
        if len(data) < 100 or not data.startswith(b"\x1f\x8b"):
            raise ValueError("Response is not a valid gzip file or is unexpectedly small")
        path.write_bytes(data)
        # Verify gzip integrity before attempting XML parsing.
        with gzip.open(path, "rb") as stream:
            stream.read(1)
        return feed, path, None
    except Exception as exc:
        path.unlink(missing_ok=True)
        return feed, None, f"{type(exc).__name__}: {exc}"[:500]


def parse_xmltv_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    match = re.match(r"^(\d{14})(?:\s*([+-]\d{4}))?", value.strip())
    if not match:
        return None
    try:
        naive = datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
        offset = match.group(2)
        if offset:
            sign = 1 if offset[0] == "+" else -1
            minutes = int(offset[1:3]) * 60 + int(offset[3:5])
            from datetime import timedelta
            return naive.replace(tzinfo=timezone(sign * timedelta(minutes=minutes))).astimezone(timezone.utc)
        # XMLTV timestamps without an offset are treated as UTC and recorded as such.
        return naive.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def channel_country(channel: ET.Element) -> str | None:
    # Prefer explicit XMLTV country metadata; then use the standard two-letter
    # suffix convention used by many XMLTV channel IDs.
    for node in channel.findall("country"):
        value = (node.text or "").strip().upper()
        if value in COUNTRY_CODES:
            return value.lower()
    channel_id = (channel.get("id") or "").lower()
    match = re.search(r"\.([a-z]{2})$", channel_id)
    if match and match.group(1).upper() in COUNTRY_CODES:
        return match.group(1)
    return None


def programme_key(programme: ET.Element) -> tuple:
    return (
        programme.get("channel", ""),
        programme.get("start", ""),
        programme.get("stop", ""),
        (programme.findtext("title") or "").strip().casefold(),
    )


def xml_bytes(channels: dict, programmes: list[ET.Element]) -> bytes:
    root = ET.Element("tv", {
        "generator-info-name": "worldepg",
        "generator-info-url": "https://github.com/AT78/worldepg",
    })
    for channel_id in sorted(channels):
        root.append(channels[channel_id])
    for programme in sorted(programmes, key=lambda p: (p.get("start", ""), p.get("channel", ""))):
        root.append(programme)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main() -> None:
    WORK.mkdir(exist_ok=True)
    started = datetime.now(timezone.utc)
    feeds = discover_feeds()
    if not feeds:
        raise RuntimeError("No epg<number>.xml.gz feeds were found in the upstream repository")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(download_feed, feed) for feed in feeds]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda row: row[0]["id"])

    channel_nodes: dict[str, ET.Element] = {}
    programme_nodes: dict[tuple, ET.Element] = {}
    feed_status = []
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=DAYS)

    for feed, path, error in results:
        if error:
            feed_status.append({"feed": feed["name"], "epgenius_id": feed["id"], "download": "failed", "error": error})
            continue
        feed_channels = 0
        feed_programmes = 0
        try:
            with gzip.open(path, "rb") as stream:
                for event, element in ET.iterparse(stream, events=("end",)):
                    if element.tag == "channel":
                        channel_id = element.get("id")
                        if channel_id:
                            if channel_id not in channel_nodes:
                                channel_nodes[channel_id] = copy.deepcopy(element)
                            feed_channels += 1
                        element.clear()
                    elif element.tag == "programme":
                        start = parse_xmltv_timestamp(element.get("start"))
                        stop = parse_xmltv_timestamp(element.get("stop"))
                        if start and stop and stop > now and start < cutoff:
                            key = programme_key(element)
                            if key not in programme_nodes:
                                programme_nodes[key] = copy.deepcopy(element)
                            feed_programmes += 1
                        element.clear()
            feed_status.append({
                "feed": feed["name"], "epgenius_id": feed["id"], "download": "ok",
                "channels_seen": feed_channels, "programmes_in_window_seen": feed_programmes,
                "download_bytes": path.stat().st_size,
            })
        except Exception as exc:
            feed_status.append({"feed": feed["name"], "epgenius_id": feed["id"], "download": "invalid", "error": f"{type(exc).__name__}: {exc}"[:500]})

    if not channel_nodes or not programme_nodes:
        raise RuntimeError("No usable channel/programme data was collected; existing published feeds were preserved")

    # Keep only channels that have programmes in the selected coverage window.
    used_ids = {p.get("channel") for p in programme_nodes.values()}
    channel_nodes = {cid: node for cid, node in channel_nodes.items() if cid in used_ids}
    programme_nodes = {key: node for key, node in programme_nodes.items() if node.get("channel") in channel_nodes}
    if not channel_nodes or not programme_nodes:
        raise RuntimeError("Merged feed has no matched channel/programme pairs; preserving previous outputs")

    merged = xml_bytes(channel_nodes, list(programme_nodes.values()))
    (ROOT / "guide.xml").write_bytes(merged)
    (ROOT / "guide.epg").write_bytes(merged)
    with gzip.open(ROOT / "guide.xml.gz", "wb", compresslevel=9) as stream:
        stream.write(merged)

    country_channels: dict[str, dict] = defaultdict(dict)
    channel_to_country = {}
    for channel_id, channel in channel_nodes.items():
        country = channel_country(channel)
        if country:
            country_channels[country][channel_id] = channel
            channel_to_country[channel_id] = country
    country_programmes: dict[str, list] = defaultdict(list)
    for programme in programme_nodes.values():
        country = channel_to_country.get(programme.get("channel", ""))
        if country:
            country_programmes[country].append(programme)

    country_dir = ROOT / "countries"
    country_dir.mkdir(exist_ok=True)
    # Only replace country feeds after the worldwide feed has been successfully built.
    for old in country_dir.glob("*.xml"):
        old.unlink()
    for country, channels in sorted(country_channels.items()):
        (country_dir / f"{country}.xml").write_bytes(xml_bytes(channels, country_programmes[country]))

    succeeded = sum(1 for row in feed_status if row["download"] == "ok")
    report = {
        "generated_utc": started.isoformat(),
        "target_days": DAYS,
        "upstream_repository": REPOSITORY,
        "upstream_feed_count": len(feeds),
        "feeds_downloaded_and_parsed": succeeded,
        "feeds_failed_or_invalid": len(feeds) - succeeded,
        "feeds": feed_status,
        "channels": len(channel_nodes),
        "programmes": len(programme_nodes),
        "country_feeds": len(country_channels),
        "country_method": "XMLTV channel country element, then ISO-3166-1 alpha-2 channel-ID suffix",
        "coverage_note": "Seven-day target window. Actual schedule depth depends on each upstream feed. epgN is an EPGenius list identifier, not a country code.",
    }
    (ROOT / "status.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(WORK, ignore_errors=True)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
