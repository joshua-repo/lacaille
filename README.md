# lacaille

Options research in four packages, one repository:

| package | what it does |
|---|---|
| [`antlia`](src/antlia/README.md) | market data: vendor extraction, a cache-first store, one canonical schema |
| [`vela`](src/vela/README.md) | backtesting: engine, strategies, pricing, risk, metrics |
| [`pictor`](src/pictor/README.md) | rendering: the dashboard and research posts |
| [`puppis`](src/puppis/README.md) | forward testing: vela's strategies against a paper account |

vela and pictor read market data only through antlia; pictor renders vela's
results from the files vela writes, never by importing it. These boundaries
are import-linter contracts in `pyproject.toml`.

```bash
uv sync                      # add --extra ibkr / thetadata / trading212 / yfinance / publish as needed
uv run pytest
uv run lint-imports
```

Only puppis may place orders, and only on a paper account.
