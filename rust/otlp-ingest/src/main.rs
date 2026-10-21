use opentelemetry_proto::tonic::collector::metrics::v1::metrics_service_server::MetricsServiceServer;
use wave_otlp_ingest::{Ingest, MAX_BATCH_BYTES};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let address = std::env::var("OTLP_LISTEN")
        .unwrap_or_else(|_| "127.0.0.1:4317".into())
        .parse()?;
    let path = std::env::var("OTLP_JOURNAL").unwrap_or_else(|_| "metrics.otlp.frames".into());
    let service = MetricsServiceServer::new(Ingest::create(&path).await?)
        .max_decoding_message_size(MAX_BATCH_BYTES);
    eprintln!("OTLP metrics receiver on {address}; journal={path}");
    tonic::transport::Server::builder()
        .concurrency_limit_per_connection(8)
        .add_service(service)
        .serve_with_shutdown(address, async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
