# Using airo-tulip

This directory documents how to **use** the two Python packages in this repository to drive a KELO
Robile mobile platform:

- [`airo-tulip`](../airo-tulip/README.md) — the lightweight **client** (`KELORobile`) and the shared API
  contract. Runs on any machine that controls the robot over the network (laptop, workstation, NUC).
- [`airo-tulip-hal`](../airo-tulip-hal/README.md) — the **hardware abstraction layer** and the
  `TulipServer`. Runs on the KELO CPU brick and talks to the drives over EtherCAT.

The client and server talk to each other over [Zenoh](https://zenoh.io/). By default they connect
**peer**-to-peer: the brick runs the server, which listens for direct client connections on port `7447`,
and clients connect to it directly — no router needed.

```
laptop / workstation              KELO CPU brick
┌──────────────────┐  Zenoh / TCP  ┌────────────────────────┐
│ airo-tulip       │ ◀───────────▶ │ airo-tulip-hal         │
│  KELORobile      │   :7447       │  TulipServer           │
│  (your script)   │               │  hardware / EtherCAT   │
└──────────────────┘               └────────────────────────┘
```

## Where to start

| If you want to… | Read |
|---|---|
| Install everything and drive the robot for the first time | [Getting started](getting_started.md) |
| Write a program that controls the robot | [Client usage (`airo-tulip`)](client_usage.md) |
| Run / configure the server on the KELO brick | [Server usage (`airo-tulip-hal`)](server_usage.md) |
| Understand the architecture and design | [How it works](../airo-tulip/docs/how_it_works.md) |

## Related documentation

These conceptual / setup guides live alongside the `airo-tulip` package:

- [`kelo_setup.md`](../airo-tulip/docs/kelo_setup.md) — first-time hardware/network set-up of the platform.
- [`external_devices.md`](../airo-tulip/docs/external_devices.md) — mounting extra devices (sensors,
  compute) and reaching them through the brick.
- [`how_it_works.md`](../airo-tulip/docs/how_it_works.md) — how the code base is structured and why.

The repository [`README.md`](../README.md) covers installing, updating, and uninstalling the server on a
KELO CPU brick with `install.sh`.

> **Version match.** The client and server must run the **same `airo-tulip` version** — the connection
> handshake enforces this and will refuse to connect on a mismatch. When you upgrade one side, upgrade
> the other to match.
