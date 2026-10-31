use crate::{evaluate, Config, Observation, ResultRow, Status};
use serde::Serialize;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Serialize)]
pub struct Record {
    pub service: String,
    pub window_index: u64,
    pub raw: Value,
    #[serde(flatten)]
    pub result: ResultRow,
}

#[derive(Debug, Serialize)]
pub struct Matrix {
    pub service: String,
    pub columns: [&'static str; 2],
    pub window_indices: Vec<u64>,
    pub values: Vec<[Option<f64>; 2]>,
    pub valid_mask: Vec<bool>,
}

#[derive(Debug, Serialize)]
pub struct CaptureReport {
    pub schema_version: &'static str,
    pub implementation: &'static str,
    pub source_kind: String,
    pub references: Config,
    pub input_metadata: Value,
    pub records: Vec<Record>,
    pub matrices: Vec<Matrix>,
}

pub fn extract_capture(input: Value, config: &Config) -> Result<CaptureReport, String> {
    config.validate()?;
    let mut object = input
        .as_object()
        .cloned()
        .ok_or("entrada deve ser objeto JSON")?;
    let source = object
        .get("source_kind")
        .and_then(Value::as_str)
        .filter(|s| !s.trim().is_empty())
        .ok_or("source_kind ausente")?
        .to_owned();
    let rows = object
        .remove("rows")
        .and_then(|v| v.as_array().cloned())
        .filter(|v| !v.is_empty())
        .ok_or("rows deve ser uma lista não vazia")?;
    let mut seen = BTreeSet::new();
    let mut records = Vec::with_capacity(rows.len());
    let mut grouped: BTreeMap<String, BTreeMap<u64, [Option<f64>; 2]>> = BTreeMap::new();
    for raw in rows {
        if let Some(row_source) = raw.get("source_kind") {
            if row_source.as_str() != Some(&source) {
                return Err("source_kind divergente na janela".into());
            }
        }
        let o: Observation =
            serde_json::from_value(raw.clone()).map_err(|e| format!("janela inválida: {e}"))?;
        if o.service.trim().is_empty() {
            return Err("service vazio".into());
        }
        if !seen.insert((o.service.clone(), o.window_index)) {
            return Err("par serviço/janela duplicado".into());
        }
        let result = evaluate(&o, config)?;
        // P válido isoladamente não constitui uma linha completa de duas coordenadas.
        let pair = if result.status == Status::Ok {
            [result.p, result.qv]
        } else {
            [None, None]
        };
        grouped
            .entry(o.service.clone())
            .or_default()
            .insert(o.window_index, pair);
        records.push(Record {
            service: o.service,
            window_index: o.window_index,
            raw,
            result,
        });
    }
    let indices: Vec<_> = seen
        .iter()
        .map(|(_, window)| *window)
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    let matrices = grouped
        .into_iter()
        .map(|(service, windows)| {
            let values: Vec<_> = indices
                .iter()
                .map(|index| windows.get(index).copied().unwrap_or([None, None]))
                .collect();
            let valid_mask = values
                .iter()
                .map(|pair| pair.iter().all(Option::is_some))
                .collect();
            Matrix {
                service,
                columns: ["P", "Qv"],
                window_indices: indices.clone(),
                values,
                valid_mask,
            }
        })
        .collect();
    Ok(CaptureReport {
        schema_version: "wave.capture-extraction.v1",
        implementation: "wave-extractor-rust/0.1.0",
        source_kind: source,
        references: config.clone(),
        input_metadata: Value::Object(object),
        records,
        matrices,
    })
}
