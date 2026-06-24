# AIRO Tulip

This repository contains two Python packages, one intended to run on the mobile robot (`airo-tulip-hal`) and the other intended to run on the computer driving the mobile robot (`airo-tulip`).

In detail:

- `./kelo-tulip`: KELO Robotics' original C++ implementation of the KELO Robile platform driver (KELO Tulip). Kept as a reference.
- `./airo-tulip`: a lightweight Python **client** package and the shared API contract. Install this on any machine that controls the robot over the network (laptop, workstation, NUC). It does **not** depend on the robot hardware libraries (no `pysoem`).
- `./airo-tulip-hal`: the **hardware abstraction layer** and the server (`airo-tulip-server`). This runs on the KELO CPU brick and talks to the drives over EtherCAT.
- `./deploy`: systemd unit templates and an example robot configuration, used by the installer.
- `./install.sh`: system-wide installer for a KELO CPU brick (virtual environment, configuration, and a boot service).

The two Python packages are documented in their own READMEs: [`airo-tulip`](airo-tulip/README.md) (the client) and [`airo-tulip-hal`](airo-tulip-hal/README.md) (the server / hardware layer). Task-oriented how-to guides for using both packages live in [`docs/`](docs/README.md): [getting started](docs/getting_started.md), [client usage](docs/client_usage.md), and [server usage](docs/server_usage.md).

The client and server communicate over [Zenoh](https://zenoh.io/): by default they connect **peer**-to-peer (the brick runs the server, which listens for direct client connections — no router needed), and clients connect to drive the robot and read its state. A Zenoh router (`zenohd`) can be used instead for setups with many clients or that span subnets.

## Packages and PyPI

The two Python packages are distributed differently:

- **`airo-tulip`** (the client + shared API contract) **is published to PyPI** at
  <https://pypi.org/project/airo-tulip/>, so client machines can install it with `pip install airo-tulip`.
  Maintainers publish a new release with [`airo-tulip/publish_pypi.sh`](airo-tulip/publish_pypi.sh), which
  runs `uv build` and `uv publish`. Before publishing, bump the version in `airo-tulip/pyproject.toml` and
  set `UV_PUBLISH_TOKEN` to a PyPI API token.
- **`airo-tulip-hal`** (the hardware layer + server) **is not published to PyPI.** It only ever runs on the
  KELO CPU brick and is built from this repository's source by `install.sh` (into `/opt/airo-tulip`), so a
  `pip install` distribution would serve no purpose. Deploy and update it from source (see below).

The client and server must run the **same `airo-tulip` version** — the connection handshake enforces this —
so when you publish a new `airo-tulip` release, remember to update the deployed bricks to match.

## Installing on the KELO CPU brick

`install.sh` performs a **system-wide installation** that configures a KELO CPU brick (running Ubuntu) to run the robot server automatically on boot.

### What "installing" means here

The installer builds the packages and installs them into fixed **system locations** (`/opt`, `/etc`, `/usr/local/bin`, and systemd), independent of where you cloned the source. The packages are installed **non-editable**, so:

- the source clone is only needed *during* installation and **can be deleted afterwards**;
- editing the source has **no effect** on the installed/running robot (that's what development mode, below, is for) — you re-run the installer to deploy changes.

This is a deliberate split: production installs are stable and system-managed; development is separate and never touches the system (see [Development](#development)).

### Prerequisites

These are normally already present on the brick (`gcc`/`make` are needed to build the `pysoem` EtherCAT extension):

```bash
sudo apt-get update -y
sudo apt-get install -y git gcc curl make
```

And [`uv`](https://github.com/astral-sh/uv), the Python package/environment manager:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install

```bash
git clone https://github.com/airo-ugent/airo-tulip
cd airo-tulip
./install.sh
```

The installer runs as your user and uses `sudo` for the steps that need it (building into `/opt` and registering a systemd service). It is **idempotent** and thus safe to re-run. It needs network access.

### What it installs, and where everything goes

| Location | What it is |
|---|---|
| `/opt/airo-tulip/venv/` | Virtual environment with the `airo-tulip` and `airo-tulip-hal` packages (non-editable) and the `airo-tulip-server` console script |
| `/usr/local/bin/airo-tulip-server` | Symlink to the server console script, so it's on the system `PATH` |
| `/etc/airo-tulip/robot.yaml` | Your platform configuration (EtherCAT device + drive layout), seeded from `deploy/robot.example.yaml` on first install and **never overwritten afterwards** |
| `/etc/systemd/system/tulip.service` | Boot service running `airo-tulip-server --config /etc/airo-tulip/robot.yaml` |

The service runs **as root**, because the EtherCAT master needs raw-socket access to the network interface.

After installation (and a reboot), the brick automatically runs the server, which listens for direct (peer) client connections on port 7447. You then control the robot from any machine on the network with the `KELORobile` client — see [`airo-tulip/README.md`](airo-tulip/README.md).

### Configure your platform

The drive layout and EtherCAT device are specific to each robot, so **edit `/etc/airo-tulip/robot.yaml` before driving** (the values come from KELO with your platform). See the comments in [`deploy/robot.example.yaml`](deploy/robot.example.yaml). After editing, restart the server:

```bash
sudo systemctl restart tulip
```

### Useful service commands

```bash
sudo systemctl status tulip      # is the server running?
journalctl -u tulip -f           # follow the server logs
sudo systemctl restart tulip     # apply configuration changes
sudo systemctl stop tulip        # stop the server
```

## Updating and rolling back

Because the install is non-editable, you update by **reinstalling a new version of the source** and re-running the installer:

```bash
cd airo-tulip            # a fresh clone, or your existing one
git fetch --tags
git checkout <tag>       # we recommend pinning to a release tag rather than tracking main
./install.sh             # rebuilds and reinstalls into /opt; restarts the services
```

To **roll back**, check out the previous tag and run `./install.sh` again. Your `/etc/airo-tulip/robot.yaml` is never overwritten, so your platform configuration is preserved across updates and rollbacks.

## Development

Development is fully separate from installation: **do not run `install.sh`** — it makes no system changes, uses no systemd, and doesn't require root.

A development checkout uses an editable virtual environment local to the clone, so your code edits take effect immediately:

```bash
git clone https://github.com/airo-ugent/airo-tulip
cd airo-tulip
uv sync                  # creates ./.venv with the packages installed editable
```

- **Client / library work** (on a laptop): import the packages from your own code, or see the package READMEs for `pip install -e` instructions.
- **Running the server for testing** (on the robot hardware): provide a local config and run it in the foreground so you can watch the logs:

  ```bash
  cp deploy/robot.example.yaml robot.yaml   # then edit for your platform (git-ignored)
  uv run airo-tulip-server --config robot.yaml
  ```

  The server listens for direct (peer) client connections, so no router is needed. It does not touch `/opt`, `/etc`, or systemd.
- **Hardware-free testing**: the client and server can run against each other in peer mode without a router or the EtherCAT hardware (this is how the loopback tests work).

If a brick already has a production install, stop the boot service first (`sudo systemctl stop tulip`) so it doesn't contend for the EtherCAT bus while you run a development server.

## Uninstalling

```bash
sudo systemctl disable --now tulip
sudo rm /etc/systemd/system/tulip.service
sudo systemctl daemon-reload
sudo rm -f /usr/local/bin/airo-tulip-server
sudo rm -rf /opt/airo-tulip /etc/airo-tulip
```
