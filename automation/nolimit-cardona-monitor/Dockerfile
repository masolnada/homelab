FROM node:22-alpine

WORKDIR /app

# No runtime dependencies; copy manifest for metadata and source.
COPY package.json ./
COPY src ./src

# Persist monitor state across restarts.
VOLUME ["/data"]

ENV NODE_ENV=production \
    STATE_FILE=/data/state.json

CMD ["node", "src/index.js"]
