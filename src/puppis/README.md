# puppis

The forward test. *Puppis*, the stern of the ship Lacaille split from Argo
Navis, where the helm is: vela (the sails) is tried in a backtest; puppis
steers the same strategies against a live market, on a **paper** account.

- Market data comes from `antlia`, never from puppis's own socket.
- Strategies, sizing, margin and pricing are `vela`'s, imported, never copied.
- puppis owns the broker socket for orders, the paper-only guard, and (from
  M2) a journal of everything it decided and everything that filled.

Nothing imports puppis. It refuses to run against any account that is not a
paper account (IBKR's start `DU`), because nothing else would stop it: a
client's `readonly=True` blocks nothing.

```bash
uv sync --extra ibkr
uv run puppis check            # connect, check the account is paper, show positions and fills
```

The gateway it connects to is `ops/ib-gateway/` at the repo root.

Status: M0 -- the connection, the guard and the read side of the broker. No
order is placed yet.
