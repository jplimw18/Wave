FROM rust:1.90-bookworm AS build
WORKDIR /source
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release --locked

FROM debian:bookworm-slim
COPY --from=build /source/target/release/wave-otlp-ingest /usr/local/bin/
ENV OTLP_LISTEN=0.0.0.0:4317 OTLP_JOURNAL=/data/metrics.otlp.frames
WORKDIR /data
EXPOSE 4317
ENTRYPOINT ["wave-otlp-ingest"]
