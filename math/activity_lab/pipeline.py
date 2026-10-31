"""Atenuação por atividade: janelas → P,Q0,V → Qv,Sv → matriz de duas colunas."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

MATH_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(MATH_ROOT / "hypotenuse_lab"))
sys.path.append(str(MATH_ROOT / "harmonic_lab"))
from experiment import triangle
from harmonic_lab import hosvd
from plots import generate_plots

MODEL_ID = "activity-pending-attenuation-v4"
REFERENCES = {"S0": 1.0, "throughput_per_second": 40.0, "latency_seconds": .1, "k_per_second": 5.0}
PHASE_SAMPLES = 64


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def count_valid(value):
    return finite(value) and value >= 0 and int(value) == value


def attenuate(s0, p, v):
    """Mantém S0/Q0 e calcula a hipotenusa efetiva Sv; V ausente não vira zero."""
    base = triangle(s0, p)
    if v is not None and (not finite(v) or not 0 <= v <= 1):
        raise ValueError("V deve pertencer a [0,1] ou estar ausente")
    result = dict(S0=s0, P=p, Q0=base["Q"], D0=base["D"], theta0=base["theta"], V=v,
                  Qv=None, Sv=None, D=None, theta=None)
    if v is not None:
        qv = v*base["Q"]
        sv = math.hypot(p, qv)
        result.update(Qv=qv, Sv=sv, D=math.hypot(p-1,qv), theta=math.atan2(qv,p) if sv else None)
    return result


def activity(raw, k):
    """Combina ingressos e trabalho pendente inicial no escopo observado do handler."""
    result = dict(V=None, lambda_effective=None, operational_state="indeterminado",
                  activity_reason=None, pending_observed=None, idle_scope="handler HTTP e fila de aplicação declarada")
    if not finite(k) or k <= 0:
        result["activity_reason"] = "invalid_k"
        return result
    dt = raw.get("duration_seconds")
    if not finite(dt) or dt <= 0 or raw.get("counter_reset", False):
        result["activity_reason"] = "invalid_window_or_reset"
        return result
    if not all(raw.get(key) is True for key in ("available_start", "available_end", "scrape_valid")):
        result["activity_reason"] = "availability_or_scrape_not_confirmed"
        return result
    provenance = raw.get("queue_provenance")
    if provenance not in ("no_application_job_queue_by_architecture", "measured_application_queue"):
        result["activity_reason"] = "queue_scope_not_declared"
        return result
    keys = ("received", "active_start", "queued_start", "active_end", "queued_end")
    values = [raw.get(key) for key in keys]
    if any(value is not None and not count_valid(value) for value in values):
        result["activity_reason"] = "invalid_activity_counts"
        return result
    if provenance == "no_application_job_queue_by_architecture" and any(raw.get(key) not in (None, 0) for key in ("queued_start", "queued_end")):
        result["activity_reason"] = "architecture_queue_contradiction"
        return result
    if any(raw.get(key) is None for key in keys[:3]):
        result["activity_reason"] = "missing_arrivals_or_initial_pending"
        return result
    lam = sum(raw[key] for key in keys[:3])/dt
    if not math.isfinite(lam):
        result["activity_reason"] = "nonfinite_activity"
        return result
    result.update(lambda_effective=lam, V=0.0 if lam == 0 else 1/(1+k/lam))
    if any(value is None for value in values):
        result["activity_reason"] = "missing_final_activity_signals"
        return result
    pending = any(raw[key] > 0 for key in ("active_start", "active_end", "queued_start", "queued_end"))
    result["pending_observed"] = pending
    if all(value == 0 for value in values):
        if not count_valid(raw.get("completed")) or raw.get("completed") != 0 or not count_valid(raw.get("failed")) or raw.get("failed") != 0:
            result.update(V=None, operational_state="indeterminado", activity_reason="zero_activity_with_unconfirmed_zero_completions")
        else:
            result["operational_state"] = "ocioso_no_handler"
    else:
        result["operational_state"] = "pendente_no_handler" if raw["received"] == 0 and pending else "ativo_no_handler"
    return result


def derive(raw, source_kind):
    """Preserva brutos e cortes; ausência de latência não impede P=0 sem conclusões."""
    result = dict(model_id=MODEL_ID, source_kind=source_kind, raw=raw, references=dict(REFERENCES),
                  service=raw["service"], window_index=raw.get("window", raw.get("window_index")),
                  start_utc=raw.get("start_utc"), end_utc=raw.get("end_utc"),
                  status="invalid", reason=None, S0=REFERENCES["S0"], P_raw=None, P=None, P_restricted=None,
                  Q0=None,Qv=None,Sv=None,D0=None,D=None,theta0=None,theta=None,
                  alpha_raw=None,alpha=None,quality_factor=None,goodput_per_second=None,
                  clipping_applied=None,restriction_delta=None,delivery_rule=None,
                  efficiency_assessment="nao_avaliada")
    signal = activity(raw, REFERENCES["k_per_second"])
    result.update(signal)
    dt, n, f = (raw.get(key) for key in ("duration_seconds", "completed", "failed"))
    latency = raw.get("mean_latency_seconds", raw.get("latency_seconds"))
    if not finite(dt) or dt <= 0 or raw.get("counter_reset", False):
        result["reason"] = "invalid_window_or_reset"
        return result
    if not count_valid(result["window_index"]):
        result["reason"] = "invalid_window_index"
        return result
    if n is None or f is None:
        result.update(status="missing",reason="missing_completed_or_failed")
        return result
    if not count_valid(n) or not count_valid(f) or f > n:
        result["reason"] = "invalid_completed_or_failed"
        return result
    if latency is not None and (not finite(latency) or latency < 0):
        result["reason"] = "invalid_latency"
        return result
    goodput = (n-f)/dt
    if not math.isfinite(goodput):
        result["reason"] = "nonfinite_goodput"
        return result
    quality = None
    if n == 0:
        alpha_raw = 0.0
        delivery_rule = "zero_completed_means_zero_delivery_without_latency_estimate"
    elif latency is None:
        result.update(status="partial",reason="missing_latency",goodput_per_second=goodput)
        return result
    else:
        quality = REFERENCES["latency_seconds"]/max(latency,REFERENCES["latency_seconds"])
        alpha_raw = goodput/REFERENCES["throughput_per_second"]*quality
        delivery_rule = "quality_adjusted_goodput"
    if not math.isfinite(alpha_raw):
        result["reason"] = "nonfinite_delivery"
        return result
    alpha = min(1.0,max(0.0,alpha_raw))
    p_raw = REFERENCES["S0"]*alpha_raw
    p = REFERENCES["S0"]*alpha
    result.update(attenuate(REFERENCES["S0"],p,signal["V"]))
    result.update(status="ok" if signal["V"] is not None else "partial",
                  reason=None if signal["V"] is not None else signal["activity_reason"],
                  P_raw=p_raw,P_restricted=p,alpha_raw=alpha_raw,alpha=alpha,
                  quality_factor=quality,goodput_per_second=goodput,
                  clipping_applied=alpha_raw!=alpha,restriction_delta=p-p_raw,delivery_rule=delivery_rule)
    return result


def synthetic_input():
    """Duas APIs modeladas, incluindo ociosidade e trabalho pendente sem chegadas."""
    rates = [0,2,8,16,25,35,60,8,2,0]
    rows = []
    for service in ("api-a","api-b"):
        for j,rate in enumerate(rates):
            count = int(rate*5)
            rows.append(dict(service=service,window=j,duration_seconds=5.,start_utc=None,end_utc=None,
                received=count,completed=count,failed=int(count*.2) if j==5 else 0,
                mean_latency_seconds=.04 if count else None,
                active_start=1 if j==9 else 0,active_end=1 if j==9 else 0,
                queued_start=0,queued_end=0,queue_provenance="no_application_job_queue_by_architecture",
                available_start=True,available_end=True,scrape_valid=True,counter_reset=False,
                note="Cenário modelado: última janela mantém uma chamada pendente sem novas chegadas."))
    return dict(source_kind="synthetic",rows=rows)


def analyze(records):
    """Matrizes n×2 e tensor serviço×2×tempo, com seleção explícita de janelas válidas."""
    services = sorted({r["service"] for r in records})
    windows = sorted({r["window_index"] for r in records if count_valid(r["window_index"])})
    lookup = {}
    for row in records:
        key = row["service"],row["window_index"]
        if key in lookup: raise ValueError("par serviço/janela duplicado")
        lookup[key] = row
    metrics = ("P","Qv")
    complete = [j for j in windows if all(lookup.get((s,j),{}).get("status")=="ok" for s in services)]
    result = dict(services=services,windows=windows,metrics=metrics,
        tensor=[[[lookup.get((s,j),{}).get(m) for j in windows] for m in metrics] for s in services],
        complete_window_indices=complete,omitted_window_indices=[j for j in windows if j not in complete],
        decomposition=None)
    if not complete: return result
    x = np.array([[[lookup[(s,j)][m] for j in complete] for m in metrics] for s in services])
    full,core,factors = hosvd(x)
    ranks = tuple(min(n,r) for n,r in zip(x.shape,(2,1,3)))
    reduced,_,_ = hosvd(x,ranks)
    norm = np.linalg.norm(x)
    phase = np.arange(PHASE_SAMPLES)/PHASE_SAMPLES
    basis = np.column_stack((np.sin(2*np.pi*phase),np.cos(2*np.pi*phase)))
    waves = x.transpose(0,2,1)@basis.T
    effective = np.array([[lookup[(s,j)]["Sv"] for j in complete] for s in services])
    matrices = []
    for s,block in zip(services,x):
        matrix = block.T
        u,sigma,vh = np.linalg.svd(matrix,full_matrices=False)
        matrices.append(dict(service=s,values=matrix.tolist(),singular_values=sigma.tolist(),
            rank=int(np.linalg.matrix_rank(matrix)),reconstruction_error=float(np.linalg.norm((u*sigma)@vh-matrix)),
            right_factor_orthogonality_error=float(np.linalg.norm(vh@vh.T-np.eye(vh.shape[0])))))
    result["decomposition"] = dict(shape=list(x.shape),matrices=matrices,
        hosvd_full_absolute_error=float(np.linalg.norm(full-x)),
        hosvd_full_relative_error=float(np.linalg.norm(full-x)/norm) if norm else None,
        hosvd_truncated_ranks=ranks,hosvd_truncated_relative_error=float(np.linalg.norm(reduced-x)/norm) if norm else None,
        core_norm_error=float(abs(np.linalg.norm(core)-norm)),
        max_factor_orthogonality_error=max(float(np.linalg.norm(u.T@u-np.eye(u.shape[1]))) for u in factors),
        carrier_hz=1,phase_times=phase.tolist(),wave_tensor=waves.tolist(),wave_tensor_shape=list(waves.shape),
        wave_matrix_rank=int(np.linalg.matrix_rank(waves.reshape(-1,PHASE_SAMPLES))),
        max_cycle_energy_error=float(np.max(np.abs(np.mean(waves**2,axis=-1)-effective**2/2))))
    return result


def run(envelope,out,input_sha256=None):
    if not isinstance(envelope.get("source_kind"),str) or not isinstance(envelope.get("rows"),list) or not envelope["rows"]:
        raise ValueError("entrada exige source_kind e rows não vazio")
    records = [derive(row,envelope["source_kind"]) for row in envelope["rows"]]
    analysis = analyze(records)
    out.mkdir(parents=True,exist_ok=True)
    result = dict(model_id=MODEL_ID,source_kind=envelope["source_kind"],references=REFERENCES,
        input_sha256=input_sha256,input_metadata={k:v for k,v in envelope.items() if k!="rows"},records=records)
    for name,data in (("results.json",result),("matrices_tensors.json",analysis)):
        (out/name).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    columns = ["source_kind","service","window_index","start_utc","end_utc","status","reason",
        "operational_state","activity_reason","lambda_effective","V","P_raw","P_restricted","P","Q0","Qv","S0","Sv","D0","D",
        "alpha_raw","alpha","quality_factor","goodput_per_second","clipping_applied","restriction_delta","delivery_rule","efficiency_assessment"]
    with (out/"windows.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore");writer.writeheader();writer.writerows(records)
    label="SINTÉTICO" if envelope["source_kind"]=="synthetic" else "MEDIÇÕES DO LAB + TRANSFORMAÇÃO EXPERIMENTAL"
    generate_plots(records,out,label)
    print(json.dumps(dict(output=str(out),records=len(records),complete_windows=len(analysis["complete_window_indices"])),ensure_ascii=False))
    return result,analysis


if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Atenuação explícita de Q0 por ingressos e trabalho pendente inicial.")
    parser.add_argument("--input",type=Path)
    parser.add_argument("--out",type=Path,default=Path(__file__).parent/"output"/"synthetic")
    args=parser.parse_args()
    data=args.input.read_bytes() if args.input else None
    run(json.loads(data) if data else synthetic_input(),args.out,hashlib.sha256(data).hexdigest() if data else None)
