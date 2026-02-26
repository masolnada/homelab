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

# Run proxy — it manages the hashcards lifecycle
exec python3 /proxy.py
