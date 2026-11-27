# worldepg

Automated worldwide XMLTV aggregation from the numbered, curated EPG feeds published by [ferteque/Curated-M3U-Repository](https://github.com/ferteque/Curated-M3U-Repository), with a seven-day target window.

## Outputs

The daily workflow builds these outputs and publishes them as downloadable assets on the repository's rolling **Latest EPG feeds** release. Country files are generated in `countries/` during the build, then uploaded to the release using their short filename (for example, `gb.xml`):

- `guide.epg` — worldwide XMLTV guide (XML content, `.epg` extension)
- `guide.xml` — worldwide XMLTV guide
- `guide.xml.gz` — compressed worldwide XMLTV guide
- `countries/<ISO-3166-1-alpha-2>.xml` — country feeds when reliable channel country metadata is available
- `status.json` — build summary, per-feed status, counts and failures

Large feeds are deliberately not committed to Git: GitHub rejects ordinary repository files over 100 MB. Release assets support files up to 2 GB each, which accommodates the current generated feeds. The workflow validates every output before publishing. New assets are uploaded before obsolete country assets are pruned, so a failed upload does not deliberately wipe the existing feed set. The uncompressed worldwide guide is very large; most clients should use `guide.xml.gz` when supported.

## Feed downloads

Stable public download links (the files are replaced by the daily workflow):

- Worldwide XMLTV: https://github.com/AT78/worldepg/releases/download/latest/guide.xml
- Worldwide compressed XMLTV: https://github.com/AT78/worldepg/releases/download/latest/guide.xml.gz
- Worldwide EPG alias: https://github.com/AT78/worldepg/releases/download/latest/guide.epg
- Build status: https://github.com/AT78/worldepg/releases/download/latest/status.json
- Country feeds: https://github.com/AT78/worldepg/releases/download/latest/gb.xml (replace `gb` with the desired two-letter country code).

Country assets are at the release root, not under a `countries/` URL path. For example, the UK feed is `https://github.com/AT78/worldepg/releases/download/latest/gb.xml`.

## Upstream source

The build discovers every file matching `epg<number>.xml.gz` in [ferteque/Curated-M3U-Repository](https://github.com/ferteque/Curated-M3U-Repository) and downloads them from the repository's raw GitHub URLs. For example:

- [epg6.xml.gz](https://raw.githubusercontent.com/ferteque/Curated-M3U-Repository/main/epg6.xml.gz)

The number in `epgN` is an EPGenius list identifier. It is not a country code; for example, `epg6` corresponds to list 6 (Ganjarelease) in [EPGenius](https://epgenius.org/). The builder preserves the numeric list identifier in `status.json` and never uses it as country attribution.

Each feed is downloaded and checked independently. A broken or unavailable feed does not prevent other valid feeds from being merged. Channels and programmes are deduplicated across feeds. Programme entries are filtered to the current seven-day target window; actual coverage depends on upstream listings and may be shorter for some channels.

## Updates

GitHub Actions runs daily at 03:17 UTC and can also be started manually from the Actions tab. Generated feeds are validated before publication. Only the compact `status.json` build report is committed to the repository; large feed files are published as release assets to stay within GitHub's repository file-size limits.

## Attribution and limitations

This project aggregates XMLTV programme metadata from the upstream repository. Availability, accuracy, schedule depth, and permitted reuse are determined by the upstream feed maintainers and source providers. A seven-day window is a target, not a guarantee that every channel has seven days of listings.
