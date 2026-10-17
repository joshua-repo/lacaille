# ops/ib-gateway -- the IB Gateway that antlia and puppis connect to

IB Gateway is a Java desktop application with no headless mode and no login
API. It runs here in a Docker container with a virtual screen, you log in to
it by hand through that screen, and everything else talks to it over ports on
`127.0.0.1`. The whole deployment is one file, `compose.yml`.

```bash
docker compose -f ops/ib-gateway/compose.yml up -d     # from the repo root
```

| file | what it is |
|---|---|
| `compose.yml` | the gateway and a noVNC bridge to its screen. No secrets. |
| `.env` | **yours, gitignored**: `VNC_SERVER_PASSWORD=...`, and optionally `TRADING_MODE=live` (the default is `paper`). |

**No broker password is stored anywhere.** You type it into the gateway's own
login dialog. The image still contains IBC (the login robot it was built
around); given no credentials, IBC leaves the dialog to you.

## How the pieces fit

```
 lacaille/ops/ib-gateway/
 ├── compose.yml ─────────────┐      image, ports, mode, restart time (no secrets)
 └── .env  (gitignored) ──────┤      VNC_SERVER_PASSWORD; TRADING_MODE if not paper
                              │
           `docker compose up -d`  (reads .env beside the file)
                              │
 ┌─ container ib-gateway ─────┼──────────────────────────────────────────────┐
 │                            ▼                                              │
 │   Xvfb (virtual screen) ── IB Gateway (Java) ◄─── 2FA push ─── your phone │
 │        │                   login dialog: you type, through the screen     │
 │        │                   API 4001 live / 4002 paper (container-local)   │
 │        │                        │                                         │
 │     x11vnc :5900           socat :4003 / :4004                            │
 │                                                                           │
 │   /home/ibgateway/settings ◄─ volume ib-gateway_ib-gateway-settings       │
 │   (jts.ini, the token that spares a 2FA on the nightly soft restart)      │
 └────────┼───────────────────────────┼──────────────────────────────────────┘
          │ 5900                      │ 4003, 4004 (socat)
 ┌─ container novnc ┐                 │
 │ websockify :8080 │                 │
 └────────┼─────────┘                 │
 host ════╪═══════ 127.0.0.1 ═════════╪═════════════════════════════════════
          │ 6080                      │ 4002 paper, 4001 live
          ▼                           ▼
   browser: the gateway's      antlia.auth / antlia.live (client ids 900+);
   screen -- log in here       puppis, its own socket
                                      ▲
                                      │ host + port only, no secret
                              ~/.antlia/credentials.toml
                              [ibkr.paper] port = 4002, [ibkr.live] port = 4001
```

| secret | lives in | read by |
|---|---|---|
| IBKR username and password | your head | the gateway's login dialog, typed through noVNC |
| second factor | your phone (IB Key) | every full login: a cold start, and about once a week |
| VNC password | `ops/ib-gateway/.env` | the container's x11vnc; `antlia gateway` only if exported in your shell (it prefills the noVNC link and never prints it) |
| session state | the `ib-gateway-settings` volume | the gateway; it lets the nightly soft restart skip a 2FA |

Keep the VNC password out of the repo-root `.env`: VS Code injects that file
into every launch configuration and test run.

**Read-only is the gateway's setting, not the client's.** `readonly=True` on an
API client only tells the client library the API is read-only (it skips syncing
orders at connect); it does not stop that client from sending one. The block
that counts is `READ_ONLY_API`, and it is `"no"` here because puppis places
paper orders through this gateway.

## Logging in

1. `docker compose -f ops/ib-gateway/compose.yml up -d`
2. Open `http://127.0.0.1:6080/vnc.html?autoconnect=1&resize=scale` (the bare
   `:6080` is only a file listing) and enter the VNC password.
3. In the gateway's login dialog, log in to the **paper** account (or live,
   if `.env` says `TRADING_MODE=live`). Confirm the 2FA on your phone.
4. Check: `uv run antlia auth ibkr -p paper --verify` names a `DU...` account.

The gateway restarts itself every night at 10:00 PM London time without asking
for a login (`AUTO_RESTART_TIME`). It cannot skip the full login IBKR demands
about once a week, nor one after a cold start -- the container being recreated,
Docker restarting, or the machine (on WSL2, Windows) rebooting.

## Everyday commands

From the repo root (`-f ops/ib-gateway/compose.yml` on each), or from this
directory without it:

```bash
docker compose ps                    # both containers, their state and ports
docker compose logs -f ib-gateway    # follow the gateway's log
docker compose up -d                 # apply compose.yml / .env changes (recreates: a login)
docker compose restart ib-gateway    # a cold restart: a login
docker compose stop                  # stop both; `start` resumes without re-reading config
```

**`docker compose config` prints every interpolated value, secrets included.**
Grep it: `docker compose config | grep -E "TRADING_MODE|published"`.

## Live or paper

`TRADING_MODE=live` in `.env`, then `up -d`, then log in to the live account.
Paper is 4002 and live is 4001; the mode not running refuses connections.
`~/.antlia/credentials.toml` points antlia at each:

```toml
[ibkr.paper]
port = 4002

[ibkr.live]
port = 4001
```

The image's `TRADING_MODE=both` is not supported: it moves each instance's
settings to `settings_live` / `settings_paper`, outside the volume mounted
here.

## The settings volume

Docker creates a named volume owned by **root**; the image runs as
**1000:1000**. A freshly created volume therefore makes the container die with

    common.sh: /home/ibgateway/settings/jts.ini: Permission denied

and `restart: unless-stopped` turns that into a crash loop. The published ports
go with it, so what you actually see is `ConnectionRefused` -- nothing that
mentions permissions. The existing volume is already fixed. If it is ever
recreated (`docker compose down -v`, or deleted by hand -- so don't), chown it
once:

```bash
docker run --rm -v ib-gateway_ib-gateway-settings:/s alpine:3.20 chown -R 1000:1000 /s
```

## `.env` values are interpolated, and quoting does not save you

Measured on compose v5.5.0, because this ate hours:

| written in `.env` | what the container receives |
|---|---|
| `PW=ab$cd` | `ab` |
| `PW="ab$cd"` | `ab` -- **double quotes do not protect** |
| `PW=ab$$cd` | `ab$cd` |
| `PW='ab$cd'` | `ab$cd` |

`env_file:` interpolates too. Trailing whitespace is eaten as well. Pick a VNC
password without `$`, or write each `$` as `$$`.

**Shell environment beats the `.env` file.** In a terminal that has run
`set -a; . .env; set +a`, or `export TRADING_MODE=...`, a later `up -d` uses the
shell's values and the file is ignored.

## History

Until 2026-10-17 this was an override layered over a separate compose project
in `~/ib-gateway`, joined by `COMPOSE_FILE` in that project's `.env`, with IBC
typing a stored password and IBC's command server switched on through a
vendored template. One file replaced all of it. IBC itself was retired
upstream on 2026-09-01; a gateway image without it is a possible next step.
