"""Candidata para análise local; não decodifica OTLP, coleta dados ou comprova eficiência/correlação."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

MODEL_ID = "pq-goodput-latency-error-v1"


def evaluate(observation, reference):
    """Retorna valores derivados compatíveis com JSON e estados explícitos de invalidez/ausência."""
    result = dict(model_id=MODEL_ID, status="invalid", reason=None,
                  P=None, Q=None, S=None, D=None, theta=None,
                  z_latency=None, z_error=None)
    def finite(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    for key in ("throughput_per_second", "latency_seconds", "error_fraction"):
        if not finite(reference.get(key)) or reference[key] <= 0:
            result["reason"] = "invalid_reference:" + key
            return result
    if observation.get("counter_reset", False):
        result["reason"] = "counter_reset"
        return result
    dt = observation.get("duration_seconds")
    if not finite(dt) or dt <= 0:
        result["reason"] = "invalid_duration"
        return result
    n, f = observation.get("completed"), observation.get("failed")
    if n is None or f is None:
        result.update(status="missing", reason="missing_counts")
        return result
    if (not isinstance(n, int) or isinstance(n, bool) or not isinstance(f, int)
            or isinstance(f, bool) or not 0 <= f <= n):
        result["reason"] = "invalid_counts"
        return result
    latency = observation.get("mean_latency_seconds")
    if latency is not None and (not finite(latency) or latency < 0):
        result["reason"] = "invalid_latency"
        return result
    result["P"] = (n-f)/dt/reference["throughput_per_second"]
    if not math.isfinite(result["P"]):
        result.update(P=None, reason="nonfinite_derived")
        return result
    if n == 0:
        result.update(status="partial", reason="no_traffic")
        return result
    if latency is None:
        result.update(status="partial", reason="missing_latency")
        return result
    zl = max(0.0, latency/reference["latency_seconds"]-1)
    ze = (f/n)/reference["error_fraction"]
    q = math.hypot(zl, ze)/math.sqrt(2)
    s = math.hypot(result["P"], q)
    d = math.hypot(result["P"]-1, q)
    if not all(map(math.isfinite, (zl, ze, q, s, d))):
        result.update(P=None, reason="nonfinite_derived")
        return result
    result.update(status="ok", Q=q, S=s, D=d,
                  theta=math.atan2(q, result["P"]) if s else None,
                  z_latency=zl, z_error=ze)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "output")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    fixture_path = Path(__file__).parent / "fixtures.json"
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
    records = [dict(id=case["id"], source_kind="synthetic",
                    observation=case["observation"], reference=fixtures["reference"],
                    derived=evaluate(case["observation"], fixtures["reference"]))
               for case in fixtures["cases"]]
    historical_path = Path(__file__).parent / "fixtures" / "historical-windows.json"
    historical_bytes = historical_path.read_bytes()
    for item in json.loads(historical_bytes):
        observation = dict(duration_seconds=item["duration_seconds"],
                           completed=item["total_requests"], failed=item["failed_requests"],
                           mean_latency_seconds=item["latency_seconds"], counter_reset=False)
        records.append(dict(id=item["service"], source_kind="historical_real_lab_measurement",
                            workload_kind="synthetic_application", observation=observation,
                            reference=fixtures["reference"], derived=evaluate(observation, fixtures["reference"])))
    output = dict(model_id=MODEL_ID, fixture_contract="observation-fixture-v1",
                  historical_source=str(historical_path.relative_to(root)),
                  historical_original_source="evidence/real-windows.json",
                  historical_sha256=hashlib.sha256(historical_bytes).hexdigest(),
                  historical_date_documented="2026-10-12",
                  date_provenance="STATUS.md; o JSON de origem contém relógios monotônicos, sem timestamps UTC",
                  reset_provenance="Reinícios históricos dos contadores não auditados independentemente aqui; deltas não negativos considerados válidos",
                  new_cluster_collection=False, records=records)
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "candidate_results.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
