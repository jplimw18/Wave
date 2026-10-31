use std::{fs, process::Command};

#[test]
fn truncated_journal_never_publishes_partial_output() {
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("broken.frames");
    let output = dir.path().join("decoded.ndjson");
    fs::write(&input, [0, 0, 0, 0, 1]).unwrap();
    let result = Command::new(env!("CARGO_BIN_EXE_wave-extractor"))
        .arg("decode-otlp")
        .arg(&input)
        .arg(&output)
        .output()
        .unwrap();
    assert!(!result.status.success());
    assert!(!output.exists());
    assert_eq!(fs::read_dir(dir.path()).unwrap().count(), 1);
}

#[test]
fn existing_output_is_not_overwritten() {
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("valid.frames");
    let output = dir.path().join("existing.ndjson");
    fs::write(&input, [0, 0, 0, 0]).unwrap();
    fs::write(&output, "preservar").unwrap();
    let result = Command::new(env!("CARGO_BIN_EXE_wave-extractor"))
        .arg("decode-otlp")
        .arg(&input)
        .arg(&output)
        .output()
        .unwrap();
    assert!(!result.status.success());
    assert_eq!(fs::read_to_string(&output).unwrap(), "preservar");
    assert_eq!(fs::read_dir(dir.path()).unwrap().count(), 2);
}
