use opentelemetry_proto::tonic::{
    collector::metrics::v1::{
        metrics_service_client::MetricsServiceClient, metrics_service_server::MetricsServiceServer,
        ExportMetricsServiceRequest,
    },
    common::v1::{any_value::Value, AnyValue, KeyValue},
    metrics::v1::{
        metric::Data, number_data_point, Gauge, Metric, NumberDataPoint, ResourceMetrics,
        ScopeMetrics,
    },
    resource::v1::Resource,
};
use prost::Message;
use tokio_stream::wrappers::TcpListenerStream;
use wave_otlp_ingest::{Ingest, MAX_BATCH_BYTES};

#[tokio::test]
async fn grpc_preserves_resource_metric_value_and_rejects_large_batch() {
    let path = std::env::temp_dir().join(format!("wave-grpc-{}.frames", std::process::id()));
    let ingest = Ingest::create(&path).await.unwrap();
    assert!(Ingest::create(&path).await.is_err());
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let address = listener.local_addr().unwrap();
    let (stop_tx, stop_rx) = tokio::sync::oneshot::channel();
    let server = tokio::spawn(async move {
        tonic::transport::Server::builder()
            .add_service(
                MetricsServiceServer::new(ingest).max_decoding_message_size(MAX_BATCH_BYTES),
            )
            .serve_with_incoming_shutdown(TcpListenerStream::new(listener), async {
                let _ = stop_rx.await;
            })
            .await
            .unwrap();
    });
    let mut client = MetricsServiceClient::connect(format!("http://{address}"))
        .await
        .unwrap();
    let batch = ExportMetricsServiceRequest {
        resource_metrics: vec![ResourceMetrics {
            resource: Some(Resource {
                attributes: vec![KeyValue {
                    key: "service.name".into(),
                    value: Some(AnyValue {
                        value: Some(Value::StringValue("api-a".into())),
                    }),
                    ..Default::default()
                }],
                ..Default::default()
            }),
            scope_metrics: vec![ScopeMetrics {
                metrics: vec![Metric {
                    name: "test.cpu.cores".into(),
                    unit: "{cpu}".into(),
                    data: Some(Data::Gauge(Gauge {
                        data_points: vec![NumberDataPoint {
                            time_unix_nano: 123456789,
                            value: Some(number_data_point::Value::AsDouble(0.25)),
                            ..Default::default()
                        }],
                    })),
                    ..Default::default()
                }],
                ..Default::default()
            }],
            ..Default::default()
        }],
    };
    assert!(client
        .export(batch.clone())
        .await
        .unwrap()
        .into_inner()
        .partial_success
        .is_none());
    let bytes = tokio::fs::read(&path).await.unwrap();
    let size = u32::from_le_bytes(bytes[..4].try_into().unwrap()) as usize;
    assert_eq!(size, bytes.len() - 4);
    assert_eq!(
        ExportMetricsServiceRequest::decode(&bytes[4..]).unwrap(),
        batch
    );
    let mut oversized = batch;
    oversized.resource_metrics[0].schema_url = "x".repeat(MAX_BATCH_BYTES + 1);
    assert!(client.export(oversized).await.is_err());
    assert_eq!(
        tokio::fs::metadata(&path).await.unwrap().len(),
        bytes.len() as u64
    );
    stop_tx.send(()).unwrap();
    server.await.unwrap();
    tokio::fs::remove_file(path).await.unwrap();
}
