#!/bin/sh
set -e

while true; do
    hashcards drill --host 0.0.0.0 --open-browser false .
    sleep 60
done
