"""Janelas observadas ou sintéticas → hipotenusa fixa → ondas → matrizes/tensores."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from experiment import from_ratio
from plots import generate_plots

MODEL_ID = "s-fixed-reference-quality-v3"
REFERENCES = {"S_reference": 1.0, "throughput_per_second": 40.0, "latency_seconds": 0.1}
CARRIER_HZ = 1.0
PHASE_SAMPLES = 64
BOUNDARY_RADIUS = math.sqrt(2-math.sqrt(2))
BOUNDARY_ATOL = 1e-12


def canonicalize(raw):
    """Adapta explicitamente o esquema da coleta Kubernetes ao esquema matemático."""
    return dict(service=raw["service"], window_index=raw.get("window_index", raw.get("window")),
                start_utc=raw.get("start_utc"), end_utc=raw.get("end_utc"),
                duration_seconds=raw.get("duration_seconds"),
                completed=raw.get("completed", raw.get("total_requests")),
                failed=raw.get("failed", raw.get("failed_requests")),
                latency_seconds=raw.get("mean_latency_seconds", raw.get("latency_seconds")),
                cpu_cores=raw.get("cpu_cores"), rss_bytes=raw.get("rss_bytes", raw.get("memory_rss_bytes")),
                counter_reset=raw.get("counter_reset", False))


def derive(raw, source_kind, references=None):
    """Calcula a candidata com referências fixas; mantém brutos e intervenção explícita."""
    ref = dict(REFERENCES if references is None else references)
    obs = canonicalize(raw)
    result = dict(model_id=MODEL_ID, source_kind=source_kind, **obs, reference=ref, raw=raw,
                  status="invalid", reason=None, operational_state="indeterminado",
                  S=None, P_raw=None, P=None, P_restricted=None, Q=None, D=None, theta=None,
                  alpha_raw=None, alpha=None, quality_factor=None, goodput_per_second=None,
                  clipping_applied=None, clipping_below_zero=None, clipping_above_one=None,
                  restriction_delta=None, boundary_radius=BOUNDARY_RADIUS,
                  boundary_delta=None, boundary_status="ausente")
    def finite(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if (ref.get("S_reference") != 1.0 or not finite(ref.get("S_reference")) or
            any(not finite(ref.get(key)) or ref[key] <= 0 for key in ("throughput_per_second", "latency_seconds"))):
        result["reason"] = "invalid_reference"
        return result
    result["S"] = ref["S_reference"]
    if not isinstance(obs["window_index"], int) or isinstance(obs["window_index"], bool) or obs["window_index"] < 0:
        result["reason"] = "invalid_window_index"
        return result
    if obs["counter_reset"]:
        result["reason"] = "counter_reset"
        return result
    dt, n, f, latency = (obs[key] for key in ("duration_seconds", "completed", "failed", "latency_seconds"))
    if not finite(dt) or dt <= 0:
        result["reason"] = "invalid_duration"
        return result
    if n is None or f is None:
        result.update(status="missing", reason="missing_counts")
        return result
    if (not isinstance(n, int) or isinstance(n, bool) or not isinstance(f, int)
            or isinstance(f, bool) or not 0 <= f <= n):
        result["reason"] = "invalid_counts"
        return result
    if latency is not None and (not finite(latency) or latency < 0):
        result["reason"] = "invalid_latency"
        return result
    goodput = (n-f)/dt
    if not math.isfinite(goodput):
        result["reason"] = "nonfinite_derived"
        return result
    result["goodput_per_second"] = goodput
    if n == 0:
        result.update(status="partial", reason="no_traffic", operational_state="ocioso")
        return result
    if latency is None:
        result.update(status="partial", reason="missing_latency")
        return result
    quality = ref["latency_seconds"]/max(latency, ref["latency_seconds"])
    raw_alpha = (goodput/ref["throughput_per_second"])*quality
    if not math.isfinite(raw_alpha):
        result["reason"] = "nonfinite_derived"
        return result
    alpha = min(1.0, max(0.0, raw_alpha))
    point = from_ratio(ref["S_reference"], alpha)
    raw_p = ref["S_reference"]*raw_alpha
    result.update(point)
    delta = point["D"]-BOUNDARY_RADIUS
    boundary_status = "fronteira" if abs(delta) <= BOUNDARY_ATOL else ("dentro" if delta < 0 else "fora")
    result.update(status="ok", reason=None, operational_state="observado", alpha_raw=raw_alpha,
                  alpha=alpha, P_raw=raw_p, P_restricted=point["P"], quality_factor=quality,
                  clipping_below_zero=raw_alpha < 0, clipping_above_one=raw_alpha > 1,
                  clipping_applied=raw_alpha != alpha, restriction_delta=point["P"]-raw_p,
                  boundary_delta=delta, boundary_status=boundary_status)
    return result


def synthetic_input():
    """Cenários modelados; não são medições de um cluster em execução."""
    rates = [2, 8, 16, 25, 35, 60, 25, 16, 8, 2]
    latencies = [.02, .03, .04, .08, .12, .06, .15, .07, .03, .02]
    error_fractions = [0, 0, 0, .1, .25, 0, .2, 0, 0, 0]
    rows = []
    for service_index, service in enumerate(("api-a", "api-b")):
        for window, rate in enumerate(rates):
            count = int(rate*5)
            rows.append(dict(service=service, window=window, start_utc=None, end_utc=None,
                             synthetic_elapsed_seconds=window*5, duration_seconds=5.0,
                             completed=count, failed=int(count*error_fractions[window]),
                             mean_latency_seconds=latencies[window]*(1+.15*service_index),
                             cpu_cores=.01+.003*rate*(1+.1*service_index),
                             rss_bytes=40_000_000+int(rate*100_000), counter_reset=False,
                             load=dict(target_rate=rate),
                             note="Cenário sintético; janela de 60 req/s exercita corte acima de Tref."))
    return dict(source_kind="synthetic", scenario="duas APIs e dez janelas modeladas", rows=rows)


def hosvd(x, ranks=None):
    """Bases ortogonais completas ou truncadas, com reconstrução por produtos de modo."""
    factors = []
    for mode in range(x.ndim):
        unfolded = np.moveaxis(x, mode, 0).reshape(x.shape[mode], -1)
        u, _, _ = np.linalg.svd(unfolded, full_matrices=True)
        factors.append(u if ranks is None else u[:, :ranks[mode]])
    core = x
    for mode, u in enumerate(factors):
        core = np.moveaxis(np.tensordot(u.T, core, axes=(1, mode)), 0, mode)
    reconstructed = core
    for mode, u in enumerate(factors):
        reconstructed = np.moveaxis(np.tensordot(u, reconstructed, axes=(1, mode)), 0, mode)
    return reconstructed, core, factors


def analyze(records):
    """Preserva ausências; decompõe somente janelas completas comuns aos serviços."""
    services = sorted({row["service"] for row in records})
    windows = sorted({row["window_index"] for row in records if isinstance(row["window_index"], int)})
    lookup = {}
    for row in records:
        key = row["service"], row["window_index"]
        if key in lookup:
            raise ValueError("par serviço/janela duplicado; não agregar silenciosamente")
        lookup[key] = row
    features = ("P", "Q", "D")
    full_tensor = [[[lookup.get((service, window), {}).get(metric) for window in windows]
                    for metric in features] for service in services]
    complete = [window for window in windows if all(lookup.get((service, window), {}).get("status") == "ok" for service in services)]
    output = dict(services=services, windows=windows, metrics=features, tensor=full_tensor,
                  complete_window_indices=complete, omitted_window_indices=[w for w in windows if w not in complete],
                  aggregation="Janelas pareadas pelo índice do plano; timestamps e eventual desalinhamento permanecem nos registros.",
                  centered=False, scaled=False, decomposition=None)
    if not complete:
        output["reason"] = "no_complete_common_windows"
        return output
    tensor = np.array([[[lookup[(service, window)][metric] for window in complete] for metric in features] for service in services])
    matrices = []
    for service, block in zip(services, tensor):
        matrix = block.T
        u, singular, vh = np.linalg.svd(matrix, full_matrices=False)
        matrices.append(dict(service=service, values=matrix.tolist(), singular_values=singular.tolist(),
                             rank=int(np.linalg.matrix_rank(matrix)),
                             reconstruction_error=float(np.linalg.norm((u*singular)@vh-matrix))))
    complete_tensor, core, factors = hosvd(tensor)
    ranks = tuple(min(size, target) for size, target in zip(tensor.shape, (2, 2, 3)))
    reduced, _, _ = hosvd(tensor, ranks)
    norm = np.linalg.norm(tensor)
    phases = np.arange(PHASE_SAMPLES)/PHASE_SAMPLES
    basis = np.column_stack((np.sin(2*np.pi*CARRIER_HZ*phases), np.cos(2*np.pi*CARRIER_HZ*phases)))
    coefficients = tensor[:, :2, :].transpose(0, 2, 1)
    waves = coefficients @ basis.T
    energy = np.mean(waves**2, axis=-1)
    output["decomposition"] = dict(shape=list(tensor.shape), matrices=matrices,
        hosvd_full_absolute_error=float(np.linalg.norm(complete_tensor-tensor)),
        hosvd_full_relative_error=float(np.linalg.norm(complete_tensor-tensor)/norm) if norm else None,
        hosvd_truncated_ranks=ranks, hosvd_truncated_relative_error=float(np.linalg.norm(reduced-tensor)/norm) if norm else None,
        core_norm_error=float(abs(np.linalg.norm(core)-norm)),
        max_factor_orthogonality_error=max(float(np.linalg.norm(u.T@u-np.eye(u.shape[1]))) for u in factors),
        carrier_hz=CARRIER_HZ, phase_samples=PHASE_SAMPLES,
        wave_tensor_shape=list(waves.shape), wave_tensor=waves.tolist(), phase_times=phases.tolist(),
        wave_matrix_rank=int(np.linalg.matrix_rank(waves.reshape(-1, PHASE_SAMPLES))),
        max_cycle_energy_error=float(np.max(np.abs(energy-.5))))
    return output


def run(envelope, output, input_sha256=None):
    source_kind = envelope.get("source_kind")
    rows = envelope.get("rows", envelope.get("windows"))
    if not isinstance(source_kind, str) or not source_kind or not isinstance(rows, list) or not rows:
        raise ValueError("entrada exige source_kind explícito e lista não vazia rows/windows")
    records = [derive(row, source_kind) for row in rows]
    analysis = analyze(records)
    output.mkdir(parents=True, exist_ok=True)
    metadata = {key: value for key, value in envelope.items() if key not in ("rows", "windows")}
    result = dict(model_id=MODEL_ID, source_kind=source_kind, input_sha256=input_sha256,
                  input_metadata=metadata, references=REFERENCES, references_fixed_before_measurement=True,
                  reference_provenance="Escolha experimental acordada antes da coleta: S=1,Tref=40req/s,Lref=0,1s; sem calibração de capacidade.",
                  observed_count=len(records), records=records)
    for filename, data in (("results.json", result), ("matrices_tensors.json", analysis)):
        (output/filename).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    columns = ["source_kind", "service", "window_index", "start_utc", "end_utc", "status", "reason", "operational_state",
               "duration_seconds", "completed", "failed", "goodput_per_second", "latency_seconds", "cpu_cores", "rss_bytes",
               "S", "P_raw", "P_restricted", "P", "Q", "D", "theta", "alpha_raw", "alpha", "quality_factor", "clipping_applied", "restriction_delta",
               "boundary_radius", "boundary_delta", "boundary_status"]
    with (output/"windows.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader(); writer.writerows(records)
    label = "SINTÉTICO" if source_kind == "synthetic" else "MEDIÇÕES DO LAB + TRANSFORMAÇÃO EXPERIMENTAL"
    generate_plots(records, output, label)
    print(json.dumps(dict(output=str(output), source_kind=source_kind, windows=len(records),
                          complete_windows=len(analysis["complete_window_indices"]),
                          clipped=sum(row["clipping_applied"] is True for row in records)), ensure_ascii=False))
    return result, analysis


def main():
    parser = argparse.ArgumentParser(description="Pipeline de hipotenusa fixa: síntese ou observações explicitamente identificadas.")
    parser.add_argument("--input", type=Path, help="Envelope JSON da coleta, com source_kind e rows/windows.")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent/"output"/"pipeline-synthetic")
    args = parser.parse_args()
    if args.input:
        data = args.input.read_bytes()
        run(json.loads(data), args.out, hashlib.sha256(data).hexdigest())
    else:
        run(synthetic_input(), args.out)


if __name__ == "__main__":
    main()
