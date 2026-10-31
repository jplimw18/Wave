"""Demonstração SINTÉTICA da candidata radial normalizada e de sua fronteira."""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import numpy as np

CONTRACT_DIR = Path(__file__).resolve().parents[1] / "pq_contract"
sys.path.insert(0, str(CONTRACT_DIR))
from bounded_candidate import BOUNDARY_RADIUS, classify_point  # noqa: E402
from harmonic_lab import hosvd

RADIUS = BOUNDARY_RADIUS


def make_trajectories():
    """Retorna trajetórias P,Q normalizadas e sintéticas para quatro serviços e 12 janelas."""
    t = np.arange(12, dtype=float)
    paths = []
    for service in range(4):
        phase = 2*math.pi*t/12 + service*0.31
        p = np.clip(0.57 + 0.31*np.cos(phase), 0, 1)
        q = np.clip(0.43 + 0.29*np.sin(phase + service*0.12), 0, 1)
        paths.append(np.column_stack((p, q)))
    # Inclui referências e contraexemplos geométricos no conjunto sintético registrado.
    paths[0][0] = (1.0, 0.0)  # Referência ideal A.
    paths[1][0] = (1/math.sqrt(2), 1/math.sqrt(2))  # Ponto B45 na fronteira.
    paths[2][0] = (0.0, 0.0)  # O repouso geométrico está fora da região.
    paths[3][0] = (0.1, 0.1)  # A direção de 45 graus também pode estar fora da região.
    return t, paths


def write_csv(out_dir: Path, times, paths):
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "boundary_windows.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_kind", "service", "window", "P", "Q", "D", "deltaD", "boundary_status"])
        for service, points in enumerate(paths, 1):
            prev_d = None
            for window, (p, q) in enumerate(points):
                result = classify_point(float(p), float(q))
                d = result["D"]
                delta = None if prev_d is None else d-prev_d
                w.writerow(["SINTETICO", service, int(times[window]), p, q, d, delta, result["boundary_status"]])
                prev_d = d
    return path


def write_svgs(out_dir: Path, times, paths):
    # Área quadrada: uma unidade normalizada ocupa o mesmo número de pixels em P e Q.
    colors = ["#1769aa", "#e67e22", "#2e8b57", "#9b59b6"]
    size, left, top, bottom = 620, 95, 70, 90
    plot = size-top-bottom
    def xy(p, q):
        return left+plot*p, size-bottom-plot*q
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">',
             f'<defs><clipPath id="square"><rect x="{left}" y="{top}" width="{plot}" height="{plot}"/></clipPath>',
             '<marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#444"/></marker></defs>',
             '<rect width="100%" height="100%" fill="white"/>',
             '<text x="310" y="30" text-anchor="middle" font-family="sans-serif" font-size="17">SINTÉTICO — trajetórias no plano P,Q</text>',
             f'<rect x="{left}" y="{top}" width="{plot}" height="{plot}" fill="none" stroke="#333"/>',
             f'<text x="315" y="{size-25}" text-anchor="middle" font-family="sans-serif">P normalizado [0,1]</text>',
             '<text x="28" y="300" text-anchor="middle" transform="rotate(-90,28,300)" font-family="sans-serif">Q normalizado [0,1]</text>',
             '<g clip-path="url(#square)">',
             f'<circle cx="{xy(1,0)[0]}" cy="{xy(1,0)[1]}" r="{plot*RADIUS:.2f}" fill="#e6f3e9" stroke="#d33" stroke-width="2" stroke-dasharray="7 5"/>']
    for service, points in enumerate(paths):
        pts = [xy(*point) for point in points]
        for i in range(len(pts)-1):
            parts.append(f'<path d="M{pts[i][0]:.1f},{pts[i][1]:.1f} L{pts[i+1][0]:.1f},{pts[i+1][1]:.1f}" fill="none" stroke="{colors[service]}" stroke-width="2" marker-end="url(#arrow)"/>')
        for i, (px, py) in enumerate(pts):
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="{colors[service]}"/><title>serviço {service+1}, janela {i}</title>')
    ax, ay = xy(1, 0)
    bx, by = xy(1/math.sqrt(2), 1/math.sqrt(2))
    parts.extend(['</g>', f'<path d="M{ax-6} {ay-6} L{ax+6} {ay+6} M{ax-6} {ay+6} L{ax+6} {ay-6}" stroke="#111" stroke-width="3"/>',
                  f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="6" fill="#d33"/>',
                  '<text x="380" y="62" font-family="sans-serif" font-size="12">fronteira r = √(2−√2)</text>',
                  f'<text x="{ax-5}" y="{ay-12}" text-anchor="end" font-family="sans-serif" font-size="12">A=(1,0)</text>',
                  f'<text x="{bx+9}" y="{by-9}" font-family="sans-serif" font-size="11">B45</text>',
                  '<text x="310" y="48" text-anchor="middle" font-family="sans-serif" font-size="11">B45=(1/√2,1/√2); região sombreada: D≤r</text>',
                  '<text x="310" y="565" text-anchor="middle" font-family="sans-serif" font-size="11">Setas indicam ordem temporal (janela 0 → 11); círculo cortado pelo domínio quadrado.</text>',
                  ])
    for value in (0, .25, .5, .75, 1):
        px, py = xy(value, value)
        parts.append(f'<text x="{px:.1f}" y="{size-bottom+18}" text-anchor="middle" font-family="sans-serif" font-size="10">{value:g}</text>')
        parts.append(f'<text x="{left-8}" y="{py+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="10">{value:g}</text>')
    parts.append('</svg>')
    (out_dir / "boundary_pq_trajectories.svg").write_text("\n".join(parts), encoding="utf-8")

    W,H,L,R,T,B = 760,440,75,25,55,60
    all_d = [classify_point(float(p),float(q))["D"] for path in paths for p,q in path]
    ymax = max(max(all_d), RADIUS)*1.08
    def dx(t): return L+(W-L-R)*t/(len(times)-1)
    def dy(v): return H-B-(H-T-B)*v/ymax
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           '<rect width="100%" height="100%" fill="white"/>',
           '<text x="380" y="28" text-anchor="middle" font-family="sans-serif" font-size="17">SINTÉTICO — D por janela e raio de fronteira</text>',
           f'<path d="M{L} {T} V{H-B} H{W-R}" fill="none" stroke="#555"/>',
           f'<path d="M{L} {dy(RADIUS):.1f} H{W-R}" stroke="#d33" stroke-width="2" stroke-dasharray="7 5"/>',
           f'<text x="{W-R-175}" y="{dy(RADIUS)-7:.1f}" fill="#d33" font-family="sans-serif">r={RADIUS:.4f}</text>',
           f'<text x="380" y="{H-15}" text-anchor="middle" font-family="sans-serif">janela</text>',
           '<text x="12" y="230" font-family="sans-serif">D</text>']
    for i in range(5):
        xv=(len(times)-1)*i/4; px=dx(xv); val=ymax*i/4; py=dy(val)
        out += [f'<path d="M{px:.1f} {T} V{H-B}" stroke="#eee"/>',
                f'<text x="{px:.1f}" y="{H-B+16}" text-anchor="middle" font-family="sans-serif" font-size="10">{xv:.0f}</text>',
                f'<path d="M{L} {py:.1f} H{W-R}" stroke="#eee"/>',
                f'<text x="{L-7}" y="{py+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="10">{val:.2f}</text>']
    for service, points in enumerate(paths):
        values=[classify_point(float(p),float(q))["D"] for p,q in points]
        coords=" ".join(f"{dx(x):.1f},{dy(v):.1f}" for x,v in zip(times,values))
        out.append(f'<polyline points="{coords}" fill="none" stroke="{colors[service]}" stroke-width="2"/><text x="{W-R-95}" y="{T+16*service}" fill="{colors[service]}" font-family="sans-serif" font-size="12">serviço {service+1}</text>')
    out.append('</svg>')
    (out_dir / "boundary_distance_by_window.svg").write_text("\n".join(out), encoding="utf-8")


def run_demo(out_dir: Path):
    times, paths = make_trajectories()
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = write_csv(out_dir, times, paths)
    write_svgs(out_dir, times, paths)
    # Aplica as decomposições existentes ao tensor normalizado serviço x [P,Q,D] x janela.
    matrices = [np.column_stack((points, [classify_point(float(p),float(q))["D"] for p,q in points]))
                for points in paths]
    tensor = np.stack([matrix.T for matrix in matrices])
    complete, _, _ = hosvd(tensor)
    reduced, _, _ = hosvd(tensor, (2, 2, 3))
    tensor_norm = np.linalg.norm(tensor)
    with (out_dir / "boundary_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_kind", "metric", "value"])
        writer.writerows([
            ["SINTETICO", "tensor_shape", ";".join(map(str, tensor.shape))],
            ["SINTETICO", "service1_pqd_matrix_rank", np.linalg.matrix_rank(matrices[0])],
            ["SINTETICO", "service1_singular_values", ";".join(map(str, np.linalg.svd(matrices[0], compute_uv=False)))],
            ["SINTETICO", "hosvd_full_relative_error", np.linalg.norm(complete-tensor)/tensor_norm],
            ["SINTETICO", "hosvd_truncated_relative_error", np.linalg.norm(reduced-tensor)/tensor_norm],
        ])
    print(f"CSV SINTÉTICO: {csv_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "output")
    run_demo(parser.parse_args().out)
