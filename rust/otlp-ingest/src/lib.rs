//! OTLP ingress only: preserves protobuf batches without interpreting experimental P/Q.
use opentelemetry_proto::tonic::collector::metrics::v1::{
    metrics_service_server::MetricsService, ExportMetricsServiceRequest,
    ExportMetricsServiceResponse,
};
use prost::Message;
use std::{io, path::Path, sync::Arc};
use tokio::{
    fs::File,
    io::AsyncWriteExt,
    sync::{Mutex, Semaphore},
};
use tonic::{Request, Response, Status};

pub const MAX_BATCH_BYTES: usize = 8 * 1024 * 1024;

struct Journal {
    file: File,
    failed: bool,
}

pub struct Ingest {
    journal: Arc<Mutex<Journal>>,
    pending: Arc<Semaphore>,
}

impl Ingest {
    /// Refuses an existing path: each run gets a fresh journal. Interrupted journals
    /// must be inspected offline; appending could conceal a truncated frame.
    pub async fn create(path: impl AsRef<Path>) -> io::Result<Self> {
        let file = File::options()
            .write(true)
            .create_new(true)
            .open(path)
            .await?;
        Ok(Self {
            journal: Arc::new(Mutex::new(Journal {
                file,
                failed: false,
            })),
            pending: Arc::new(Semaphore::new(32)),
        })
    }
}

#[tonic::async_trait]
impl MetricsService for Ingest {
    async fn export(
        &self,
        request: Request<ExportMetricsServiceRequest>,
    ) -> Result<Response<ExportMetricsServiceResponse>, Status> {
        let batch = request.into_inner();
        if batch.encoded_len() > MAX_BATCH_BYTES {
            return Err(Status::resource_exhausted("batch exceeds 8 MiB"));
        }
        let permit = self
            .pending
            .clone()
            .try_acquire_owned()
            .map_err(|_| Status::unavailable("journal busy; retry later"))?;
        let payload = batch.encode_to_vec();
        // One complete length-delimited protobuf frame per accepted Export call.
        let mut frame = Vec::with_capacity(payload.len() + 4);
        frame.extend_from_slice(&(payload.len() as u32).to_le_bytes());
        frame.extend_from_slice(&payload);
        let journal = self.journal.clone();
        // Detached persistence survives cancellation of the RPC future. Otherwise
        // cancellation during write_all could leave a partial frame before the next.
        tokio::spawn(async move {
            let _permit = permit;
            let mut journal = journal.lock().await;
            if journal.failed {
                return Err(Status::unavailable(
                    "journal failed; restart with a new path",
                ));
            }
            let write = async {
                journal.file.write_all(&frame).await?;
                journal.file.sync_data().await
            }
            .await;
            if let Err(error) = write {
                journal.failed = true;
                eprintln!("journal write failed: {error}");
                return Err(Status::unavailable("journal write failed"));
            }
            Ok(Response::new(ExportMetricsServiceResponse {
                partial_success: None,
            }))
        })
        .await
        .map_err(|_| Status::internal("journal task failed"))?
    }
}
