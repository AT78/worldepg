# worldepg

Automated worldwide XMLTV EPG aggregation from publicly available free sources, targeting up to 7 days of programme data.

## Outputs

- `guide.epg` — worldwide XMLTV guide (XML content, `.epg` extension)
- `guide.xml` — worldwide XMLTV guide
- `guide.xml.gz` — compressed worldwide XMLTV
- `countries/<code>.xml` — country feeds (best-effort country attribution)
- `status.json` — build summary

## Updates
GitHub Actions runs daily and can also be triggered manually from Actions. Coverage is dependent on free upstream listings; seven days is a target, not a guarantee for every channel.

## Sources and attribution
This project uses the open-source [iptv-org/epg](https://github.com/iptv-org/epg) scraping catalogue and source infrastructure. Upstream sources have their own terms, availability, and attribution requirements. We only aggregate publicly accessible listings; source availability is not guaranteed.

## Feed URLs
- https://raw.githubusercontent.com/AT78/worldepg/main/guide.epg
- https://raw.githubusercontent.com/AT78/worldepg/main/guide.xml
- https://raw.githubusercontent.com/AT78/worldepg/main/guide.xml.gz
- Country feeds: https://raw.githubusercontent.com/AT78/worldepg/main/countries/uk.xml (replace `uk`)

## Development
The workflow clones the upstream scraper catalogue and builds feeds. Source discovery and country attribution are intentionally documented as best-effort and can be tuned as coverage improves.
