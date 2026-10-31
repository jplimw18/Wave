use serde::{Deserialize, Serialize};

const MODEL: &str = "activity-pending-attenuation-v4";
const MAX_EXACT_COUNT: f64 = 9_007_199_254_740_991.0;

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Config {
    pub model_id: String,
    pub s0: f64,
    pub throughput_per_second: f64,
    pub latency_seconds: f64,
    pub k_per_second: f64,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            model_id: MODEL.into(),
            s0: 1.0,
            throughput_per_second: 40.0,
            latency_seconds: 0.1,
            k_per_second: 5.0,
        }
    }
}

impl Config {
    pub fn validate(&self) -> std::result::Result<(), String> {
        if self.model_id.trim().is_empty()
            || !self.s0.is_finite()
            || !(0.0..=1.0).contains(&self.s0)
            || [
                self.throughput_per_second,
                self.latency_seconds,
                self.k_per_second,
            ]
            .iter()
            .any(|v| !v.is_finite() || *v <= 0.0)
        {
            return Err("referências inválidas".into());
        }
        if self.model_id == MODEL && *self != Self::default() {
            return Err("alterar referências exige um model_id diferente".into());
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Deserialize)]
pub struct Observation {
    pub service: String,
    #[serde(alias = "window")]
    pub window_index: u64,
    pub duration_seconds: Option<f64>,
    pub completed: Option<f64>,
    pub failed: Option<f64>,
    #[serde(alias = "latency_seconds")]
    pub mean_latency_seconds: Option<f64>,
    pub received: Option<f64>,
    pub active_start: Option<f64>,
    pub active_end: Option<f64>,
    pub queued_start: Option<f64>,
    pub queued_end: Option<f64>,
    pub queue_provenance: Option<String>,
    pub available_start: Option<bool>,
    pub available_end: Option<bool>,
    pub scrape_valid: Option<bool>,
    #[serde(default)]
    pub counter_reset: bool,
}

#[derive(Clone, Copy, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Status {
    Ok,
    Partial,
    Missing,
    Invalid,
}

#[derive(Clone, Copy, Debug, Serialize, PartialEq, Eq)]
pub enum ActivityState {
    #[serde(rename = "indeterminado")]
    Unknown,
    #[serde(rename = "ocioso_no_handler")]
    Idle,
    #[serde(rename = "ativo_no_handler")]
    Active,
    #[serde(rename = "pendente_no_handler")]
    Pending,
}

#[derive(Clone, Debug, Serialize)]
pub struct ResultRow {
    pub status: Status,
    pub reason: Option<&'static str>,
    pub operational_state: ActivityState,
    pub activity_reason: Option<&'static str>,
    pub pending_observed: Option<bool>,
    pub lambda_effective: Option<f64>,
    #[serde(rename = "V")]
    pub v: Option<f64>,
    #[serde(rename = "S0")]
    pub s0: f64,
    #[serde(rename = "P_raw")]
    pub p_raw: Option<f64>,
    #[serde(rename = "P_restricted")]
    pub p_restricted: Option<f64>,
    #[serde(rename = "P")]
    pub p: Option<f64>,
    #[serde(rename = "Q0")]
    pub q0: Option<f64>,
    #[serde(rename = "Qv")]
    pub qv: Option<f64>,
    #[serde(rename = "Sv")]
    pub sv: Option<f64>,
    #[serde(rename = "D0")]
    pub d0: Option<f64>,
    #[serde(rename = "D")]
    pub d: Option<f64>,
    pub theta0: Option<f64>,
    pub theta: Option<f64>,
    pub alpha_raw: Option<f64>,
    pub alpha: Option<f64>,
    pub quality_factor: Option<f64>,
    pub goodput_per_second: Option<f64>,
    pub clipping_applied: Option<bool>,
    pub restriction_delta: Option<f64>,
    pub delivery_rule: Option<&'static str>,
    pub efficiency_assessment: &'static str,
}

impl ResultRow {
    fn new(s0: f64) -> Self {
        Self {
            status: Status::Invalid,
            reason: None,
            operational_state: ActivityState::Unknown,
            activity_reason: None,
            pending_observed: None,
            lambda_effective: None,
            v: None,
            s0,
            p_raw: None,
            p_restricted: None,
            p: None,
            q0: None,
            qv: None,
            sv: None,
            d0: None,
            d: None,
            theta0: None,
            theta: None,
            alpha_raw: None,
            alpha: None,
            quality_factor: None,
            goodput_per_second: None,
            clipping_applied: None,
            restriction_delta: None,
            delivery_rule: None,
            efficiency_assessment: "nao_avaliada",
        }
    }
}

fn count(v: f64) -> bool {
    v.is_finite() && (0.0..=MAX_EXACT_COUNT).contains(&v) && v.fract() == 0.0
}

fn activity(o: &Observation, k: f64, r: &mut ResultRow) {
    let Some(dt) = o.duration_seconds.filter(|dt| dt.is_finite() && *dt > 0.0) else {
        r.activity_reason = Some("invalid_window_or_reset");
        return;
    };
    if o.counter_reset {
        r.activity_reason = Some("invalid_window_or_reset");
        return;
    }
    if o.available_start != Some(true)
        || o.available_end != Some(true)
        || o.scrape_valid != Some(true)
    {
        r.activity_reason = Some("availability_or_scrape_not_confirmed");
        return;
    }
    let scope = o.queue_provenance.as_deref();
    if !matches!(
        scope,
        Some("no_application_job_queue_by_architecture" | "measured_application_queue")
    ) {
        r.activity_reason = Some("queue_scope_not_declared");
        return;
    }
    let values = [
        o.received,
        o.active_start,
        o.queued_start,
        o.active_end,
        o.queued_end,
    ];
    if values.iter().flatten().any(|v| !count(*v)) {
        r.activity_reason = Some("invalid_activity_counts");
        return;
    }
    if scope == Some("no_application_job_queue_by_architecture")
        && [o.queued_start, o.queued_end]
            .iter()
            .flatten()
            .any(|v| *v != 0.0)
    {
        r.activity_reason = Some("architecture_queue_contradiction");
        return;
    }
    let [Some(received), Some(active), Some(queued), _, _] = values else {
        r.activity_reason = Some("missing_arrivals_or_initial_pending");
        return;
    };
    let lambda = (received + active + queued) / dt;
    if !lambda.is_finite() {
        r.activity_reason = Some("nonfinite_activity");
        return;
    }
    r.lambda_effective = Some(lambda);
    r.v = Some(if lambda == 0.0 {
        0.0
    } else {
        1.0 / (1.0 + k / lambda)
    });
    if values.iter().any(Option::is_none) {
        r.activity_reason = Some("missing_final_activity_signals");
        return;
    }
    let pending = [o.active_start, o.active_end, o.queued_start, o.queued_end]
        .iter()
        .flatten()
        .any(|v| *v > 0.0);
    r.pending_observed = Some(pending);
    if values.iter().all(|v| *v == Some(0.0)) {
        if o.completed != Some(0.0) || o.failed != Some(0.0) {
            r.v = None;
            r.activity_reason = Some("zero_activity_with_unconfirmed_zero_completions");
        } else {
            r.operational_state = ActivityState::Idle;
        }
    } else {
        r.operational_state = if received == 0.0 && pending {
            ActivityState::Pending
        } else {
            ActivityState::Active
        };
    }
}

pub fn evaluate(o: &Observation, c: &Config) -> std::result::Result<ResultRow, String> {
    c.validate()?;
    let mut r = ResultRow::new(c.s0);
    activity(o, c.k_per_second, &mut r);
    let Some(dt) = o.duration_seconds.filter(|dt| dt.is_finite() && *dt > 0.0) else {
        r.reason = Some("invalid_window_or_reset");
        return Ok(r);
    };
    if o.counter_reset {
        r.reason = Some("invalid_window_or_reset");
        return Ok(r);
    }
    let (Some(n), Some(f)) = (o.completed, o.failed) else {
        r.status = Status::Missing;
        r.reason = Some("missing_completed_or_failed");
        return Ok(r);
    };
    if !count(n) || !count(f) || f > n {
        r.reason = Some("invalid_completed_or_failed");
        return Ok(r);
    }
    if o.mean_latency_seconds
        .is_some_and(|l| !l.is_finite() || l < 0.0)
    {
        r.reason = Some("invalid_latency");
        return Ok(r);
    }
    let goodput = (n - f) / dt;
    if !goodput.is_finite() {
        r.reason = Some("nonfinite_goodput");
        return Ok(r);
    }
    let (raw_alpha, quality, rule) = if n == 0.0 {
        (
            0.0,
            None,
            "zero_completed_means_zero_delivery_without_latency_estimate",
        )
    } else if let Some(l) = o.mean_latency_seconds {
        let quality = c.latency_seconds / l.max(c.latency_seconds);
        (
            goodput / c.throughput_per_second * quality,
            Some(quality),
            "quality_adjusted_goodput",
        )
    } else {
        r.status = Status::Partial;
        r.reason = Some("missing_latency");
        r.goodput_per_second = Some(goodput);
        return Ok(r);
    };
    if !raw_alpha.is_finite() {
        r.reason = Some("nonfinite_delivery");
        return Ok(r);
    }
    let alpha = raw_alpha.clamp(0.0, 1.0);
    let p = c.s0 * alpha;
    let q0 = (c.s0 - p).sqrt() * (c.s0 + p).sqrt();
    r.status = if r.v.is_some() {
        Status::Ok
    } else {
        Status::Partial
    };
    r.reason = if r.v.is_some() {
        None
    } else {
        r.activity_reason
    };
    r.p_raw = Some(c.s0 * raw_alpha);
    r.p_restricted = Some(p);
    r.p = Some(p);
    r.q0 = Some(q0);
    r.d0 = Some((p - 1.0).hypot(q0));
    r.theta0 = (c.s0 > 0.0).then(|| q0.atan2(p));
    r.alpha_raw = Some(raw_alpha);
    r.alpha = Some(alpha);
    r.quality_factor = quality;
    r.goodput_per_second = Some(goodput);
    r.clipping_applied = Some(alpha != raw_alpha);
    r.restriction_delta = Some(p - c.s0 * raw_alpha);
    r.delivery_rule = Some(rule);
    if let Some(v) = r.v {
        let qv = v * q0;
        let sv = p.hypot(qv);
        r.qv = Some(qv);
        r.sv = Some(sv);
        r.d = Some((p - 1.0).hypot(qv));
        r.theta = (sv > 0.0).then(|| qv.atan2(p));
    }
    Ok(r)
}
