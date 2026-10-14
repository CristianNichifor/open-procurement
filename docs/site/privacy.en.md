# Privacy

In short: this site does not track you. It sets no cookies, runs no analytics or
audience measurement, has no accounts and no forms.

## Who runs the site

Cristian Nichifor, the author of the project. For any question about this page or the
data, open an issue:
https://github.com/CristianNichifor/open-procurement/issues

## What runs in your browser

- **No cookies and no local storage.** The page writes nothing to your browser beyond
  the ordinary cache, which the browser manages itself.
- **No analytics.** There are no statistics scripts, pixels or traffic-measurement
  services.
- **Search runs locally.** Queries execute in your browser with DuckDB-Wasm, over public
  data files. What you search for is not sent anywhere.

## Who receives the technical requests

Every web page reaches you through a server, which receives the technical data any
request carries: IP address, browser type and the address requested.

- **Hosting:** Cloudflare Pages (projects.cristian-nichifor.com). The same files are
  also published through GitHub Pages while that deploy path exists.
- **CDN:** the DuckDB-Wasm query engine is downloaded from cdn.jsdelivr.net, and the
  two extensions it uses to read the data files (parquet, httpfs) from
  extensions.duckdb.org. These are the only third-party requests the page makes.

The site's own code records nothing about visitors.

## External links

Links to data.gov.ro, GitHub or other sites lead to services with their own privacy
rules, and are only fetched if you click them.

## The published data

The data comes from official public sources and names contracting authorities and
companies. If a record is wrong, or concerns you and you want to respond, see the
[right of reply](CORRECTIONS.md).
