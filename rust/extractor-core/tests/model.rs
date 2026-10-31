use serde_json::{json, Value};
use wave_extractor_core::{evaluate, extract_capture, ActivityState, Config, Observation, Status};

fn input() -> Value {
    json!({"service":"api-a","window":0,"duration_seconds":5,"completed":40,"failed":0,
        "mean_latency_seconds":0.04,"received":40,"active_start":0,"active_end":0,
        "queued_start":0,"queued_end":0,"queue_provenance":"no_application_job_queue_by_architecture",
        "available_start":true,"available_end":true,"scrape_valid":true})
}

fn eval(v: Value) -> wave_extractor_core::ResultRow {
    evaluate(
        &serde_json::from_value::<Observation>(v).unwrap(),
        &Config::default(),
    )
    .unwrap()
}

#[test]
fn activity_uses_arrivals_not_successes() {
    let mut v = input();
    v["failed"] = json!(40);
    let r = eval(v);
    assert_eq!(r.p, Some(0.0));
    assert!((r.v.unwrap() - 8.0 / 13.0).abs() < 1e-14);
    assert!(r.qv.unwrap() > 0.0);
}

#[test]
fn idle_pending_and_missing_are_distinct() {
    let mut v = input();
    for key in ["completed", "failed", "received"] {
        v[key] = json!(0);
    }
    v["mean_latency_seconds"] = Value::Null;
    let r = eval(v.clone());
    assert_eq!(r.operational_state, ActivityState::Idle);
    assert_eq!(
        (r.p, r.q0, r.v, r.qv, r.sv, r.theta),
        (Some(0.0), Some(1.0), Some(0.0), Some(0.0), Some(0.0), None)
    );
    v["active_start"] = json!(1);
    v["active_end"] = json!(1);
    let r = eval(v.clone());
    assert_eq!(r.operational_state, ActivityState::Pending);
    assert!(r.v.unwrap() > 0.0);
    v["received"] = Value::Null;
    let r = eval(v);
    assert_eq!(r.status, Status::Partial);
    assert!(r.v.is_none() && r.qv.is_none());
}

#[test]
fn invalid_and_contradictory_signals_do_not_create_idle() {
    let mut v = input();
    v["received"] = json!(0);
    let r = eval(v);
    assert_eq!(r.operational_state, ActivityState::Unknown);
    assert!(r.qv.is_none());
    let mut v = input();
    v["available_end"] = json!(false);
    assert!(eval(v).v.is_none());
    let mut v = input();
    v["counter_reset"] = json!(true);
    assert_eq!(eval(v).status, Status::Invalid);
    let mut v = input();
    v["completed"] = json!(9_007_199_254_740_992.0);
    assert_eq!(eval(v).status, Status::Invalid);
}

#[test]
fn geometry_grid_and_explicit_clipping() {
    for n in [0, 1, 20, 100, 200, 300] {
        let mut v = input();
        v["completed"] = json!(n);
        v["received"] = json!(n);
        let r = eval(v);
        let (p, q0, qv, sv, activity) = (
            r.p.unwrap(),
            r.q0.unwrap(),
            r.qv.unwrap(),
            r.sv.unwrap(),
            r.v.unwrap(),
        );
        assert!((p * p + q0 * q0 - 1.0).abs() < 1e-14);
        assert!((sv * sv - (p * p + activity * activity * q0 * q0)).abs() < 1e-14);
        assert!(sv <= 1.0 + 1e-14);
        assert!((qv - activity * q0).abs() < 1e-14);
        if n > 200 {
            assert_eq!(r.clipping_applied, Some(true));
            assert!(r.p_raw.unwrap() > p);
        }
    }
}

#[test]
fn capture_preserves_provenance_and_rejects_duplicate_identity() {
    let envelope = json!({"source_kind":"synthetic","run_id":"test","rows":[input()]});
    let report = extract_capture(envelope, &Config::default()).unwrap();
    assert_eq!(report.matrices[0].values.len(), 1);
    assert_eq!(report.input_metadata["run_id"], "test");
    assert_eq!(report.records[0].raw, input());
    let envelope = json!({"source_kind":"synthetic","rows":[input(),input()]});
    assert!(extract_capture(envelope, &Config::default()).is_err());
    let mut row = input();
    row["source_kind"] = json!("real");
    assert!(extract_capture(
        json!({"source_kind":"synthetic","rows":[row]}),
        &Config::default()
    )
    .is_err());
}

#[test]
fn changed_references_require_a_new_model_id() {
    let mut c = Config {
        k_per_second: 10.0,
        ..Config::default()
    };
    assert!(c.validate().is_err());
    c.model_id = "experimental-k10".into();
    assert!(c.validate().is_ok());
    c.k_per_second = 0.0;
    assert!(c.validate().is_err());
}

#[test]
fn matrices_align_missing_windows_without_inventing_zero() {
    let mut b = input();
    b["service"] = json!("api-b");
    b["window"] = json!(1);
    let report = extract_capture(
        json!({"source_kind":"synthetic","rows":[input(),b]}),
        &Config::default(),
    )
    .unwrap();
    assert_eq!(report.matrices[0].window_indices, vec![0, 1]);
    assert_eq!(report.matrices[1].window_indices, vec![0, 1]);
    assert_eq!(report.matrices[0].valid_mask, vec![true, false]);
    assert_eq!(report.matrices[1].valid_mask, vec![false, true]);
    assert_eq!(report.matrices[0].values[1], [None, None]);
}

#[test]
fn harmonic_cycle_has_effective_amplitude_and_energy() {
    let r = eval(input());
    let mean = (0..64)
        .map(|i| {
            wave_extractor_core::wave_at_phase(&r, std::f64::consts::TAU * f64::from(i) / 64.0)
                .unwrap()
                .powi(2)
        })
        .sum::<f64>()
        / 64.0;
    assert!((mean - r.sv.unwrap().powi(2) / 2.0).abs() < 1e-14);
    assert!(wave_extractor_core::wave_at_phase(&r, f64::NAN).is_none());
}
