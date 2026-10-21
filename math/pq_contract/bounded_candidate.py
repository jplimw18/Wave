"""Candidata radial normalizada; a classificação é uma convenção geométrica."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from pq_candidate import evaluate as evaluate_unbounded

MODEL_ID = "pq-bounded-radial-unit45-v2"
BOUNDARY_RADIUS = math.sqrt(2-math.sqrt(2))
BOUNDARY_ATOL = 1e-12
BALANCED_POINT = (1/math.sqrt(2), 1/math.sqrt(2))


def normalize_unit(value):
    """Limita um índice finito a [0,1] e conserva o valor anterior e os cortes."""
    if value is None:
        return dict(raw=None, value=None, below_zero=None, above_one=None, clipped=None)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("o índice deve ser finito ou ausente")
    return dict(raw=value, value=min(1.0, max(0.0, value)), below_zero=value < 0,
                above_one=value > 1, clipped=value < 0 or value > 1)


def classify_point(p, q, atol=BOUNDARY_ATOL):
    """Classifica a distância à referência (1,0); ausências permanecem ausentes."""
    if isinstance(atol, bool) or not isinstance(atol, (int, float)) or not math.isfinite(atol) or atol < 0:
        raise ValueError("a tolerância deve ser finita e não negativa")
    result = dict(D=None, boundary_radius=BOUNDARY_RADIUS, boundary_delta=None,
                  boundary_status="ausente", geometrically_efficient=None)
    for value in (p, q):
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or not math.isfinite(value) or not 0 <= value <= 1):
            raise ValueError("P e Q devem pertencer a [0,1] ou estar ausentes")
    if p is None or q is None:
        return result
    d = math.hypot(p-1, q)
    delta = d-BOUNDARY_RADIUS
    status = "fronteira" if abs(delta) <= atol else ("dentro" if delta < 0 else "fora")
    result.update(D=d, boundary_delta=delta, boundary_status=status,
                  geometrically_efficient=status in ("dentro", "fronteira"))
    return result


def evaluate(observation, reference):
    """Normaliza entrega e componentes do atrito usando referências fixas da rodada."""
    raw = evaluate_unbounded(observation, reference)
    normalization = {"P": normalize_unit(raw["P"]),
                     "z_latency": normalize_unit(raw["z_latency"]),
                     "z_error": normalize_unit(raw["z_error"])}
    p = normalization["P"]["value"]
    zl, ze = (normalization[key]["value"] for key in ("z_latency", "z_error"))
    q = None if zl is None or ze is None else min(1.0, math.hypot(zl, ze)/math.sqrt(2))
    s = None if p is None or q is None else math.hypot(p, q)
    theta = None if s is None or s == 0 else math.atan2(q, p)
    operational_state = "ocioso" if raw["reason"] == "no_traffic" else (
        "observado" if raw["status"] == "ok" else "indeterminado")
    result = dict(model_id=MODEL_ID, status=raw["status"], reason=raw["reason"],
                  operational_state=operational_state, P=p, Q=q, S=s, theta=theta,
                  raw_indices=dict(P=raw["P"], Q=raw["Q"], S=raw["S"], D=raw["D"]),
                  normalization=normalization,
                  raw_q_above_one=None if raw["Q"] is None else raw["Q"] > 1,
                  clipping_applied=any(item["clipped"] is True for item in normalization.values()))
    result.update(classify_point(p, q))
    return result


def main():
    parser = argparse.ArgumentParser(description="Avalia a candidata radial; não mede eficiência real.")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "output")
    args = parser.parse_args()
    fixtures = json.loads((Path(__file__).parent / "bounded_fixtures.json").read_text(encoding="utf-8"))
    records = [dict(id=case["id"], source_kind="synthetic", observation=case["observation"],
                    reference=fixtures["reference"], derived=evaluate(case["observation"], fixtures["reference"]))
               for case in fixtures["observations"]]
    historical_path = Path(__file__).parent / "fixtures" / "historical-windows.json"
    historical_bytes = historical_path.read_bytes()
    for item in json.loads(historical_bytes):
        observation = dict(duration_seconds=item["duration_seconds"], completed=item["total_requests"],
                           failed=item["failed_requests"], mean_latency_seconds=item["latency_seconds"])
        records.append(dict(id=item["service"], source_kind="historical_real_lab_measurement",
                            workload_kind="synthetic_application", observation=observation,
                            reference=fixtures["reference"], derived=evaluate(observation, fixtures["reference"])))
    geometry = [dict(**case, derived=classify_point(case["P"], case["Q"])) for case in fixtures["geometry"]]
    output = dict(model_id=MODEL_ID, reference_point=[1, 0], balanced_point=BALANCED_POINT,
                  boundary_radius=BOUNDARY_RADIUS, boundary_atol=BOUNDARY_ATOL,
                  boundary_assumption="Equilíbrio de 45 graus na circunferência unitária; convenção geométrica, sem validação de eficiência real.",
                  normalization_policy="P e componentes z_latency/z_error limitados a [0,1]; Q é a norma ponderada dos componentes limitados, com pesos 0,5/0,5.",
                  historical_source="math/pq_contract/fixtures/historical-windows.json",
                  historical_sha256=hashlib.sha256(historical_bytes).hexdigest(),
                  historical_date_documented="2026-10-12", new_cluster_collection=False,
                  records=records, geometry=geometry)
    args.out.mkdir(parents=True, exist_ok=True)
    destination = args.out / "bounded_candidate_results.json"
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
