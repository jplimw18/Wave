use serde_json::{json, Value};
use wave_extractor_core::{extract_capture, Config};

const REAL: &str = include_str!("../../../math/activity_lab/output/real/results.json");
const SYNTHETIC: &str = include_str!("../../../math/activity_lab/output/synthetic/results.json");

fn compare(reference: &str) {
    let expected: Value = serde_json::from_str(reference).unwrap();
    let gold = expected["records"].as_array().unwrap();
    let input = json!({"source_kind":expected["source_kind"],"rows":gold.iter().map(|r|r["raw"].clone()).collect::<Vec<_>>()});
    let actual = extract_capture(input, &Config::default()).unwrap();
    assert_eq!(actual.records.len(), gold.len());
    let fields = [
        "status",
        "reason",
        "operational_state",
        "activity_reason",
        "pending_observed",
        "lambda_effective",
        "V",
        "S0",
        "P_raw",
        "P_restricted",
        "P",
        "Q0",
        "Qv",
        "Sv",
        "D0",
        "D",
        "theta0",
        "theta",
        "alpha_raw",
        "alpha",
        "quality_factor",
        "goodput_per_second",
        "clipping_applied",
        "restriction_delta",
        "delivery_rule",
        "efficiency_assessment",
    ];
    let mut max_error = 0.0_f64;
    for (record, expected) in actual.records.iter().zip(gold) {
        let observed = serde_json::to_value(record).unwrap();
        for key in fields {
            let (a, b) = (&observed[key], &expected[key]);
            if let (Some(a), Some(b)) = (a.as_f64(), b.as_f64()) {
                let error = (a - b).abs();
                max_error = max_error.max(error);
                assert!(
                    error <= 1e-12 + 1e-10 * b.abs(),
                    "{} janela {} campo {key}: {a} != {b}",
                    record.service,
                    record.window_index
                );
            } else {
                assert_eq!(
                    a, b,
                    "{} janela {} campo {key}",
                    record.service, record.window_index
                );
            }
        }
    }
    eprintln!(
        "paridade: {} janelas, {} campos, erro máximo={max_error:e}",
        gold.len(),
        fields.len()
    );
}

#[test]
fn matches_python_on_measured_kubernetes_windows() {
    compare(REAL);
}

#[test]
fn matches_python_on_synthetic_idle_pending_and_clipping() {
    compare(SYNTHETIC);
}
