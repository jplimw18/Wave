use base64::{engine::general_purpose::STANDARD, Engine};
use std::{
    error::Error,
    fs::File,
    io::{BufReader, BufWriter, Write},
    path::Path,
};
use tempfile::NamedTempFile;
use wave_extractor_core::{extract_capture, Config};

fn run() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() < 3 || !matches!(args[0].as_str(), "replay" | "decode-otlp") {
        return Err("uso: wave-extractor replay entrada.json saída.json [config.json] | decode-otlp journal.frames saída.ndjson".into());
    }
    match args[0].as_str() {
        "replay" if args.len() == 3 || args.len() == 4 => {
            let config: Config = if let Some(path) = args.get(3) {
                serde_json::from_reader(BufReader::new(File::open(path)?))?
            } else {
                Config::default()
            };
            let input = serde_json::from_reader(BufReader::new(File::open(&args[1])?))?;
            let report = extract_capture(input, &config)?;
            let mut temporary = temporary_output(Path::new(&args[2]))?;
            let mut output = BufWriter::new(temporary.as_file_mut());
            serde_json::to_writer_pretty(&mut output, &report)?;
            output.write_all(b"\n")?;
            output.flush()?;
            output.get_ref().sync_all()?;
            drop(output);
            temporary.persist_noclobber(&args[2]).map_err(|e| e.error)?;
            eprintln!(
                "{} janelas extraídas; origem={}",
                report.records.len(),
                report.source_kind
            );
        }
        "decode-otlp" if args.len() == 3 => {
            let mut input = BufReader::new(File::open(&args[1])?);
            let mut temporary = temporary_output(Path::new(&args[2]))?;
            let mut output = BufWriter::new(temporary.as_file_mut());
            let mut frames = 0_u64;
            while let Some(frame) = wave_extractor::read_frame(&mut input)? {
                serde_json::to_writer(
                    &mut output,
                    &serde_json::json!({
                        "schema_version": "wave.otlp-frame.v1", "frame_index": frames,
                        "protobuf_base64": STANDARD.encode(&frame.protobuf),
                        "diagnostic_request_is_authoritative": false,
                        "diagnostic_request": frame.request
                    }),
                )?;
                output.write_all(b"\n")?;
                frames += 1;
            }
            output.flush()?;
            output.get_ref().sync_all()?;
            drop(output);
            temporary.persist_noclobber(&args[2]).map_err(|e| e.error)?;
            eprintln!("{frames} frames OTLP decodificados");
        }
        _ => return Err("quantidade de argumentos inválida".into()),
    }
    Ok(())
}

fn temporary_output(path: &Path) -> std::io::Result<NamedTempFile> {
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    NamedTempFile::new_in(parent)
}

fn main() {
    if let Err(error) = run() {
        eprintln!("extração falhou: {error}");
        std::process::exit(1);
    }
}
