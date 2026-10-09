# pictor

The rendering layer: one self-contained dashboard page.

The dashboard (`pictor calendar`) has two workspaces, each a row of tabs:

- **Analysis** -- the market as it is now.
  - *Portfolio*: a watchlist kept by hand in a TOML file. No broker behind it.
  - *Metrics* and *Pipeline*: laid out, not wired. Empty panes say what they
    wait on; nothing is mocked.
- **Research** -- work over a fixed dataset.
  - *Data*, *Parameters*, *Results*: laid out, not wired. They will show what
    a backtest engine writes to disk.

The page reads no broker: no positions, balances, margin or currency
conversion. Market data, when it arrives, comes through
[antlia](https://github.com/joshua-repo/antlia).

## Usage

```bash
uv sync

uv run pictor calendar --open                         # write the page and open it
uv run pictor calendar --watchlist my-list.toml       # Portfolio from this file
```

**The watchlist** is read from `~/.pictor/watchlist.toml`, or `$PICTOR_WATCHLIST`,
or `--watchlist`. See [watchlist.example.toml](watchlist.example.toml) for the
shape. With no file the Portfolio tab says where it looked; a file that does not
parse is an error.

## Working on the front end

The dashboard's UI lives in `web/` as ES modules and CSS. Vite bundles it and
inlines everything into **one self-contained HTML file** committed at
`src/pictor/_web/index.html`, which is what `pictor calendar` fills in with a
JSON payload. Installing pictor needs no Node and no build step -- the built
file ships in the wheel.

```bash
./web/build.sh     # rebuild after editing web/src
```

That script runs Node in a throwaway `node:22-alpine` container and installs
nothing on your machine. If you edit `web/src` and forget to rebuild, rendering
warns you rather than quietly serving the previous build.

Or as a library:

```python
from pictor.charts import build_calendar_html
from pictor.watchlist import load_watchlist

open("calendar.html", "w").write(build_calendar_html(watchlist=load_watchlist()))
```
