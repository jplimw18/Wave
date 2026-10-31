use opentelemetry_proto::tonic::collector::metrics::v1::ExportMetricsServiceRequest;
use prost::Message;
use std::io::{self, Read};
use wave_otlp_ingest::MAX_BATCH_BYTES;

pub struct DecodedFrame {
    pub request: ExportMetricsServiceRequest,
    pub protobuf: Vec<u8>,
}

pub fn read_frame(input: &mut impl Read) -> io::Result<Option<DecodedFrame>> {
    let mut header = [0; 4];
    // Um EOF antes do primeiro byte é fim normal. Após ele, o frame é obrigatório.
    loop {
        match input.read(&mut header[..1]) {
            Ok(0) => return Ok(None),
            Ok(_) => break,
            Err(e) if e.kind() == io::ErrorKind::Interrupted => continue,
            Err(e) => return Err(e),
        }
    }
    input.read_exact(&mut header[1..])?;
    let len = u32::from_le_bytes(header) as usize;
    if len > MAX_BATCH_BYTES {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "frame excede 8 MiB",
        ));
    }
    let mut payload = vec![0; len];
    input.read_exact(&mut payload)?;
    ExportMetricsServiceRequest::decode(payload.as_slice())
        .map(|request| {
            Some(DecodedFrame {
                request,
                protobuf: payload,
            })
        })
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
}
