#!/usr/bin/env bash

# Use this script to publish airo-tulip to PyPI.
# Make sure that you've updated the version number in pyproject.toml!

if [ -d dist ]; then
  echo "Removing dist/ directory..."
  rm -rf dist
fi

echo "Building..."
python -m build

echo "Publishing..."
python -m twine upload dist/*
