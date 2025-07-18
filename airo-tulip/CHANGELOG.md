# Changelog

All notable changes for the packages in the airo-tulip repo are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Unreleased

### Breaking changes

### Added
- Added a check to the handshake to ensure that client and server are running the same version of `airo-tulip`.

### Changed

### Fixed

### Removed

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
