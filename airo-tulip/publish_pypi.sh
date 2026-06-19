#!/usr/bin/env bash

# Use this script to publish airo-tulip to PyPI.
# Make sure that you've updated the version number in pyproject.toml!
#
# Authentication: set UV_PUBLISH_TOKEN to a PyPI API token (or pass --token to `uv publish`).

set -euo pipefail

# Always build/publish this package, regardless of the current working directory.
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ -d dist ]; then
  echo "Removing dist/ directory..."
  rm -rf dist
fi

echo "Building..."
uv build

echo "Publishing..."
uv publish
