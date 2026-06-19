# Changelog

All notable changes for the packages in the airo-tulip repo are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Unreleased

### Breaking changes
- Replaced the 0MQ REQ/REP transport with **Zenoh**, and redesigned the communication model along
  ROS 2 lines:
    - Velocity commands are now **streamed** (pub/sub) to the server and kept alive by a server-side
      **watchdog** (stops the platform if no command arrives within `watchdog_timeout`, default 0.3 s).
      The client streams the current setpoint at a fixed rate; `set_platform_velocity_target(...)`'s
      `timeout` reverts the setpoint to zero client-side. `set_platform_velocity_target`/`align_drives`
      no longer return a response (they're fire-and-forget); out-of-limit values raise locally and are
      additionally **clamped** by the server (reported via the status stream's `last_command_rejected`).
    - Odometry and a new, richer **platform status** (driver state, current mode, `drives_aligned`,
      per-drive health: error flag, status registers, temperature, current, bus voltage, watchdog state)
      are **streamed** from the server. `get_odometry`/`get_velocity`/`are_drives_aligned`/`get_status`
      now return the latest streamed value (no per-call round-trip); odometry is timestamped.
    - Discrete operations (handshake, `set_driver_type`, `reset_odometry`, `stop_server`) are Zenoh
      **queryable** (request/reply) calls.
    - The wire format is now **msgpack**, not pickle — removing the arbitrary-code-execution risk and
      making the protocol language-agnostic.
    - Connectivity is via a **Zenoh router** (`zenohd`) by default; `KELORobile(host)` and the server
      connect to it (default `tcp/<host>:7447`). A router must be running (typically on the KELO CPU brick).
    - `TulipServer`'s constructor changed: it no longer takes an IP/port to bind; it takes Zenoh session
      options (router endpoint, robot id, watchdog timeout). `KELORobile`'s default port is now 7447.
- Split the project into two packages. `airo-tulip` now contains only the client (`KELORobile`) and the
  shared API contract (`airo_tulip.api.messages`, `airo_tulip.api.types`); the hardware abstraction layer
  and server moved to the new `airo-tulip-hal` package. As a result:
    - Client imports are unchanged (`from airo_tulip.api.client import KELORobile`).
    - Server-side imports change: `airo_tulip.api.server` → `airo_tulip_hal.server`, and
      `airo_tulip.hardware.*` → `airo_tulip_hal.hardware.*`. Importing `airo_tulip.api.server` now raises a
      helpful `ImportError` pointing to `airo-tulip-hal`.
    - `PlatformDriverType` is now imported from `airo_tulip.api.types` (re-exported location), not
      `airo_tulip.hardware.platform_driver`.
    - Installing `airo-tulip` no longer pulls in `pysoem`; install `airo-tulip-hal` on the KELO CPU brick.

### Added
- Added a check to the handshake to ensure that client and server are running the same version of `airo-tulip`.
- New `airo-tulip-hal` package containing the hardware abstraction layer and `TulipServer`.
- New shared modules `airo_tulip.api.codec` (msgpack (de)serialization) and `airo_tulip.api.transport`
  (Zenoh session + key-expression helpers).
- New client methods: `get_status()` (full platform health), `is_alive()` (telemetry-freshness liveness),
  and `drive_aligned()` (align the drives, wait until aligned, then drive — no polling).

### Changed
- Corrected the velocity controller's wheel distance from `0.055 m` to `0.080 m` to match the KELO C++
  ground truth (`WheelModel.h`, `KELOdrive105`). The original value was a transcription error from the
  initial untested C++→Python port.
- Single-sourced drive geometry and safety-limit magic numbers into `constants.py`.
- The driver now propagates initialisation/step failures: `RobilePlatform.step()` returns a status and
  `TulipServer` aborts startup if EtherCAT initialisation fails and stops the loop on a step failure.
- Guarded shared driver state with a lock against the request/EtherCAT thread race; the request loop now
  always replies (so a failing handler can no longer wedge the server) and unknown messages return an error.
- The client handshake now raises an informative `KELORobileError` on version/UUID mismatch instead of
  using `assert` (which is stripped under `python -O`).

### Fixed
- `reset_odometry()` now actually resets the reported pose (it previously wrote an unused attribute).
- `WheelParamVelocity` no longer uses mutable numpy-array defaults, which made the package fail to import
  on Python 3.11+; added the previously-undeclared `max_pivot_error` field.
- Guarded against division by zero in velocity/odometry estimation when no time has elapsed.
- `clip_angle` now normalizes angles that are multiple revolutions out of range.

### Removed
- Removed the unused `pykalman` and `pyserial` dependencies, and dead code (`util.sign`, `WheelData`,
  unused constants and fields).
- Removed the `pyzmq` dependency (replaced by `eclipse-zenoh` + `msgpack`).

## 0.4.0

### Breaking changes

- The odometry functionality of `airo-tulip` is now reduced back to the original drive encoder based odometry. The compass and flow sensor based odometry have been removed, and are from now on supposed to be implemented in "user" code. This was done to reduce the complexity of the `airo-tulip` package and to make it more generic and robust (i.e., make it easier to add additional sensors in the future).
- Removed the ability to log to `rerun.io`. This was not actively used and logging can be performed by the user in their own code if needed.

### Changed

- Added `airo-typing` as a PyPI dependency, removing the requirement to manually install it.

## 0.3.2

### Fixed

- Fixed a sign bug with the orientation.

## 0.3.1

### Fixed

- Fixed a faulty import statement.

## 0.3.0

### Breaking changes

- We now use a compass for orientation computations.

## 0.2.4

### Fixed

- Fixed some import issues in the `RobilePlatform` class.
- Fixed crashes when the peripherals are not connected due to the peripheral client being `None` after the timeout introduced in version `0.2.3`.

## 0.2.3

### Fixed

- Added a timeout for the peripheral client of 2 seconds: if it fails to connect, the robile platform will not hang indefinitely.

## 0.2.2

### Added

- Status LEDs on the back of AIRO's mobile platform can now be set by the client.

### Changed

- Relaxed NumPy version requirement to any version in `pyproject.toml` of airo-tulip.

## 0.2.1

### Changed

- Relaxed NumPy version requirement to `<0.2` in `pyproject.toml` of airo-tulip.

## 0.2.0

### Added

- Dashboard server for easier remote interaction with the KELO CPU brick.
- Installation script `install.sh` for airo-tulip and the dashboard server, which also updates the KELO CPU brick crontab file for `root`.

## 0.1.0

### Added

- Changelog added, to keep track of changes since version `0.1.0`.
