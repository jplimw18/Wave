use base64::{engine::general_purpose::STANDARD, Engine};
use opentelemetry_proto::tonic::{
    collector::metrics::v1::ExportMetricsServiceRequest,
    metrics::v1::{
        metric::Data, number_data_point::Value, Gauge, Metric, NumberDataPoint, ResourceMetrics,
        ScopeMetrics,
    },
};
use prost::Message;
use std::{fs, process::Command};

#[test]
fn json_projection_does_not_replace_authoritative_nan_payload() {
    let batch = ExportMetricsServiceRequest {
        resource_metrics: vec![ResourceMetrics {
            scope_metrics: vec![ScopeMetrics {
                metrics: vec![Metric {
                    name: "nonfinite".into(),
                    data: Some(Data::Gauge(Gauge {
                        data_points: vec![NumberDataPoint {
                            value: Some(Value::AsDouble(f64::NAN)),
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
    let mut protobuf = batch.encode_to_vec();
    protobuf.extend_from_slice(&[0xa0, 0x06, 0x01]);
    let mut bytes = (protobuf.len() as u32).to_le_bytes().to_vec();
    bytes.extend_from_slice(&protobuf);
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("nan.frames");
    let output = dir.path().join("nan.ndjson");
    fs::write(&input, bytes).unwrap();
    let result = Command::new(env!("CARGO_BIN_EXE_wave-extractor"))
        .arg("decode-otlp")
        .arg(input)
        .arg(&output)
        .output()
        .unwrap();
    assert!(result.status.success());
    let decoded: serde_json::Value = serde_json::from_slice(&fs::read(output).unwrap()).unwrap();
    assert_eq!(decoded["diagnostic_request_is_authoritative"], false);
    let wire = STANDARD
        .decode(decoded["protobuf_base64"].as_str().unwrap())
        .unwrap();
    assert_eq!(wire, protobuf);
    let restored = ExportMetricsServiceRequest::decode(wire.as_slice()).unwrap();
    let Some(Data::Gauge(gauge)) = &restored.resource_metrics[0].scope_metrics[0].metrics[0].data
    else {
        panic!("gauge ausente")
    };
    let Some(Value::AsDouble(value)) = gauge.data_points[0].value else {
        panic!("valor ausente")
    };
    assert!(value.is_nan());
}
