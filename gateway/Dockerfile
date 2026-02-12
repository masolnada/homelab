FROM caddy:builder@sha256:40aa5af183f83631ca8566ca076a1c05d14c02311d7a3e8fad9374c45d3574f6 AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare

FROM caddy:latest@sha256:d8c17a862962def15cde69863a3a463f25a2664942eafd7bdbf050e9c3116b83

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
