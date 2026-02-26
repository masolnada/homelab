FROM rust:bookworm AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y libsqlite3-dev && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/eudoxia0/hashcards.git .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y libsqlite3-0 ca-certificates git openssh-client python3 && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /root/.ssh && ssh-keyscan github.com >> /root/.ssh/known_hosts 2>/dev/null
COPY --from=builder /build/target/release/hashcards /usr/local/bin/hashcards
COPY entrypoint.sh /entrypoint.sh
COPY proxy.py /proxy.py
RUN chmod +x /entrypoint.sh
WORKDIR /data
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
