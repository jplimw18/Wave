use opentelemetry_proto::tonic::{
    collector::metrics::v1::{
        metrics_service_client::MetricsServiceClient, metrics_service_server::MetricsServiceServer,
        ExportMetricsServiceRequest,
    },
    common::v1::{any_value::Value, AnyValue, InstrumentationScope, KeyValue},
    metrics::v1::{
        metric::Data, number_data_point, Metric, NumberDataPoint, ResourceMetrics, ScopeMetrics,
        Sum,
    },
    resource::v1::Resource,
};
use std::{fs::File, io::BufReader, process::Command};
use tokio_stream::wrappers::TcpListenerStream;
use wave_otlp_ingest::{Ingest, MAX_BATCH_BYTES};

#[tokio::test]
async fn official_grpc_export_roundtrips_into_extractor_ndjson() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("metrics.frames");
    let receiver = Ingest::create(&path).await.unwrap();
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let address = listener.local_addr().unwrap();
    let (stop_tx, stop_rx) = tokio::sync::oneshot::channel();
    let server = tokio::spawn(async move {
        tonic::transport::Server::builder()
            .add_service(
                MetricsServiceServer::new(receiver).max_decoding_message_size(MAX_BATCH_BYTES),
            )
            .serve_with_incoming_shutdown(TcpListenerStream::new(listener), async {
                let _ = stop_rx.await;
            })
            .await
            .unwrap();
    });
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
                scope: Some(InstrumentationScope {
                    name: "wave-lab".into(),
                    ..Default::default()
                }),
                metrics: vec![Metric {
                    name: "aim_http_received_requests_total".into(),
                    unit: "{request}".into(),
                    data: Some(Data::Sum(Sum {
                        aggregation_temporality: 2,
                        is_monotonic: true,
                        data_points: vec![NumberDataPoint {
                            start_time_unix_nano: 10,
                            time_unix_nano: 20,
                            value: Some(number_data_point::Value::AsInt(40)),
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
    let mut client = MetricsServiceClient::connect(format!("http://{address}"))
        .await
        .unwrap();
    client.export(batch.clone()).await.unwrap();
    let mut journal = BufReader::new(File::open(&path).unwrap());
    assert_eq!(
        wave_extractor::read_frame(&mut journal)
            .unwrap()
            .unwrap()
            .request,
        batch
    );
    assert!(wave_extractor::read_frame(&mut journal).unwrap().is_none());
    let output = dir.path().join("decoded.ndjson");
    let result = Command::new(env!("CARGO_BIN_EXE_wave-extractor"))
        .arg("decode-otlp")
        .arg(&path)
        .arg(&output)
        .output()
        .unwrap();
    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    let decoded: serde_json::Value = serde_json::from_reader(File::open(output).unwrap()).unwrap();
    assert_eq!(
        decoded["diagnostic_request"],
        serde_json::to_value(&batch).unwrap()
    );
    stop_tx.send(()).unwrap();
    server.await.unwrap();
}
