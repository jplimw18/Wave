use opentelemetry_proto::tonic::collector::metrics::v1::ExportMetricsServiceRequest;
use prost::Message;
use std::io::{Cursor, ErrorKind};
use wave_extractor::read_frame;

#[test]
fn frame_boundary_eof_and_corruption_are_distinct() {
    assert!(read_frame(&mut Cursor::new([])).unwrap().is_none());
    assert_eq!(
        read_frame(&mut Cursor::new([0, 0])).err().unwrap().kind(),
        ErrorKind::UnexpectedEof
    );
    assert_eq!(
        read_frame(&mut Cursor::new([1, 0, 0, 0]))
            .err()
            .unwrap()
            .kind(),
        ErrorKind::UnexpectedEof
    );
    assert!(read_frame(&mut Cursor::new([255, 255, 255, 255])).is_err());
    assert!(read_frame(&mut Cursor::new([1, 0, 0, 0, 255])).is_err());
}

#[test]
fn preserves_multiple_official_requests() {
    let batch = ExportMetricsServiceRequest::default();
    let payload = batch.encode_to_vec();
    let mut bytes = Vec::new();
    for _ in 0..2 {
        bytes.extend_from_slice(&(payload.len() as u32).to_le_bytes());
        bytes.extend_from_slice(&payload);
    }
    let mut cursor = Cursor::new(bytes);
    for _ in 0..2 {
        assert_eq!(read_frame(&mut cursor).unwrap().unwrap().request, batch);
    }
    assert!(read_frame(&mut cursor).unwrap().is_none());
}

#[test]
fn retains_unknown_fields_without_reencoding() {
    // Campo 100, varint 1: não conhecido pelo tipo gerado atual.
    let protobuf = vec![0xa0, 0x06, 0x01];
    let mut bytes = (protobuf.len() as u32).to_le_bytes().to_vec();
    bytes.extend_from_slice(&protobuf);
    let frame = read_frame(&mut Cursor::new(bytes)).unwrap().unwrap();
    assert_eq!(frame.protobuf, protobuf);
    assert_ne!(frame.request.encode_to_vec(), frame.protobuf);
}
