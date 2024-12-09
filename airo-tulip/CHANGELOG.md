# Changelog

All notable changes for the packages in the airo-tulip repo are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses a [CalVer](https://calver.org/) versioning scheme with monthly releases, see [here](versioning.md)

## Unreleased

### Breaking changes

- Replaced 0MQ with CycloneDDS for communication between the server and the client with the publish/subscribe pattern.
  This should result in more flexible code and allows multiple client connections (e.g., to monitor the battery level).

### Added

- `get_voltage_bus()` method added to server and client to monitor battery status.

### Changed

### Fixed

### Removed

- `align_drives()` method removed from server and client, because it was not reliable. May be added back in the future.
- `timeout` parameter removed from velocity commands, because it made robot logic complex.

## 0.1.0

### Breaking changes

### Added

- `CHANGELOG.md` added, to keep track of changes since version `0.1.0`.

### Changed

### Fixed

### Removed
