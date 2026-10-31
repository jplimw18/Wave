mod capture;
mod model;

pub use capture::{extract_capture, CaptureReport, Matrix, Record};
pub use model::{evaluate, ActivityState, Config, Observation, ResultRow, Status};

pub fn wave_at_phase(row: &ResultRow, phase_radians: f64) -> Option<f64> {
    if !phase_radians.is_finite() {
        return None;
    }
    let (sin, cos) = phase_radians.sin_cos();
    Some(row.p? * sin + row.qv? * cos)
}
