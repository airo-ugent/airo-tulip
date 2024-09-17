#!/usr/bin/env bash

if [ -d dist ]; then
  echo "Removing dist/ directory..."
  rm -rf dist
fi

echo "Building..."
python -m build

echo "Publishing..."
python -m twine upload dist/*
