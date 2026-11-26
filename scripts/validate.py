#!/usr/bin/env python3
"""Validate generated XMLTV outputs without loading multi-million-row feeds into memory."""
import gzip
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent


def parse(path, compressed=False):
    """Stream-parse an XMLTV file and check programme channel references."""
    opener = gzip.open if compressed else open
    root = None
    root_tag = None
    channels = set()
    referenced_channels = set()
    channel_count = 0
    programme_count = 0

    with opener(path, "rb") as stream:
        for event, element in ET.iterparse(stream, events=("start", "end")):
            if event == "start":
                if root is None:
                    root = element
                    root_tag = element.tag
                    if root_tag != "tv":
                        raise ValueError(f"{path}: root element must be tv")
                continue

            if element.tag == "channel":
                channel_id = element.get("id")
                if channel_id:
                    channels.add(channel_id)
                    channel_count += 1
            elif element.tag == "programme":
                channel_id = element.get("channel")
                if channel_id:
                    referenced_channels.add(channel_id)
                programme_count += 1

            if element.tag in ("channel", "programme"):
                # Release the processed record and all previously completed
                # siblings from the root, keeping memory bounded while parsing.
                root.clear()

    if root_tag != "tv":
        raise ValueError(f"{path}: empty or invalid XMLTV document")

    missing = referenced_channels - channels
    if missing:
        sample = ", ".join(sorted(missing)[:5])
        raise ValueError(
            f"{path}: {len(missing)} programme channel reference(s) "
            f"have no matching channel (examples: {sample})"
        )
    if programme_count and not channels:
        raise ValueError(f"{path}: programmes without channels")

    return channel_count, programme_count


def main():
    for name in ("guide.xml", "guide.epg"):
        path = ROOT / name
        if not path.exists():
            raise FileNotFoundError(path)
        channel_count, programme_count = parse(path)
        print(f"{name}: {channel_count} channels, {programme_count} programmes")

    compressed_path = ROOT / "guide.xml.gz"
    if not compressed_path.exists():
        raise FileNotFoundError(compressed_path)
    channel_count, programme_count = parse(compressed_path, compressed=True)
    print(
        f"guide.xml.gz: {channel_count} channels, "
        f"{programme_count} programmes (stream-validated)"
    )

    report = json.loads((ROOT / "status.json").read_text())
    if report.get("target_days") != 7:
        raise ValueError("status target_days should be 7")

    countries = ROOT / "countries"
    country_files = list(countries.glob("*.xml"))
    for path in country_files:
        parse(path)
    print(f"Validated {len(country_files)} country files and compressed guide")


if __name__ == "__main__":
    main()
