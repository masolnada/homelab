FROM rust:bookworm AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y libsqlite3-dev && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/eudoxia0/hashcards.git .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y libsqlite3-0 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/target/release/hashcards /usr/local/bin/hashcards
WORKDIR /data
EXPOSE 8000
CMD ["hashcards", "drill", "."]
