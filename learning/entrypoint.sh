#!/bin/sh
set -e

# Set up deploy key
mkdir -p /root/.ssh
cp /run/deploy_key /root/.ssh/id_ed25519
chmod 600 /root/.ssh/id_ed25519

# Initial clone if not present
if [ ! -d /data/decks/.git ]; then
    git clone git@github.com:masolnada/flashcards.git /data/decks
fi

# Start pull-on-request proxy in the background
python3 /proxy.py &

# Keep hashcards running on internal port; proxy handles git pull on each request
while true; do
    hashcards drill --host 0.0.0.0 --port 8001 --open-browser false /data/decks
    sleep 5
done
