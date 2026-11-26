# worldepg

Automated worldwide XMLTV aggregation from the numbered, curated EPG feeds published by [ferteque/Curated-M3U-Repository](https://github.com/ferteque/Curated-M3U-Repository), with a seven-day target window.

## Outputs

- `guide.epg` — worldwide XMLTV guide (XML content, `.epg` extension)
- `guide.xml` — worldwide XMLTV guide
- `guide.xml.gz` — compressed worldwide XMLTV
- `countries/<ISO-3166-1-alpha-2>.xml` — country feeds when reliable channel country metadata is available
- `status.json` — build summary, per-feed status, counts and failures

## Upstream source

The build discovers every file matching `epg<number>.xml.gz` in [ferteque/Curated-M3U-Repository](https://github.com/ferteque/Curated-M3U-Repository) and downloads them from the repository's raw GitHub URLs. For example:

- [epg6.xml.gz](https://raw.githubusercontent.com/ferteque/Curated-M3U-Repository/main/epg6.xml.gz)

The number in `epgN` is an EPGenius list identifier. It is not a country code; for example, `epg6` corresponds to list 6 (Ganjarelease) in [EPGenius](https://epgenius.org/). The builder preserves the numeric list identifier in `status.json` and never uses it as country attribution.

Each feed is downloaded and checked independently. A broken or unavailable feed does not prevent other valid feeds from being merged. Channels and programmes are deduplicated across feeds. Programme entries are filtered to the current seven-day target window; actual coverage depends on upstream listings and may be shorter for some channels.

## Feed URLs

- Worldwide XMLTV: https://raw.githubusercontent.com/AT78/worldepg/main/guide.xml
- Worldwide compressed XMLTV: https://raw.githubusercontent.com/AT78/worldepg/main/guide.xml.gz
- Worldwide EPG alias: https://raw.githubusercontent.com/AT78/worldepg/main/guide.epg
- Country feeds: https://raw.githubusercontent.com/AT78/worldepg/main/countries/gb.xml (replace `gb` with an available country code)

## Updates

GitHub Actions runs daily at 03:17 UTC and can also be started manually from the Actions tab. Generated feeds are validated before publication.

## Attribution and limitations

This project aggregates XMLTV programme metadata from the upstream repository. Availability, accuracy, schedule depth, and permitted reuse are determined by the upstream feed maintainers and source providers. A seven-day window is a target, not a guarantee that every channel has seven days of listings.
