#!/bin/sh
set -e

SHA=$(git ls-remote https://github.com/masolnada/markcards.git HEAD | cut -c1-7)
DATE=$(date +'%Y%m%d')

APP_VERSION="${DATE}-${SHA}" docker compose up -d --build markcards
