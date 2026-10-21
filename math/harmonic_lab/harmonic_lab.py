"""Small synthetic lab for two-coefficient harmonic models and tensor compression."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def coefficients(signal, omega: float, times=None):
    """Fit y=P sin(omega*t)+Q cos(omega*t); return P,Q,S,theta,rank."""
    y = np.asarray(signal, dtype=float)
    if y.ndim != 1 or y.size == 0 or not np.all(np.isfinite(y)):
        raise ValueError("signal must be a finite 1-D array")
    if not np.isfinite(omega) or omega <= 0:
        raise ValueError("omega must be finite and positive")
    t = np.arange(y.size, dtype=float) if times is None else np.asarray(times, dtype=float)
    if t.shape != y.shape or not np.all(np.isfinite(t)):
        raise ValueError("times must be finite and match signal")
    design = np.column_stack((np.sin(omega*t), np.cos(omega*t)))
    pq, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    p, q = map(float, pq)
    s = float(np.hypot(p, q))
    theta = None if s == 0 else float(np.arctan2(q, p))
    return p, q, s, theta, int(rank)


def rotation(theta):
    if not np.isfinite(theta):
        raise ValueError("theta must be finite")
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


def reconstruct(times, omega, p, q):
    vals = np.asarray([omega, p, q], dtype=float)
    t = np.asarray(times, dtype=float)
    if not np.all(np.isfinite(vals)) or omega <= 0 or not np.all(np.isfinite(t)):
        raise ValueError("finite inputs and omega > 0 required")
    return p*np.sin(omega*t) + q*np.cos(omega*t)


def distance(p, q):
    """Distance to normalized reference (1, 0); missing or invalid pair is undefined."""
    if p is None or q is None:
        return None
    try:
        p, q = float(p), float(q)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(p) or not np.isfinite(q):
        return None
    with np.errstate(over="ignore"):
        d = float(np.hypot(p - 1.0, q))
    return d if np.isfinite(d) else None


def hosvd(tensor, ranks=None):
    """HOSVD; ranks are optional truncation dimensions for each tensor mode."""
    x = np.asarray(tensor, dtype=float)
    if x.ndim < 2 or any(size == 0 for size in x.shape) or not np.all(np.isfinite(x)):
        raise ValueError("tensor must be finite, nonempty, and have at least two modes")
    factors = []
    for mode in range(x.ndim):
        unfolding = np.moveaxis(x, mode, 0).reshape(x.shape[mode], -1)
        u, _, _ = np.linalg.svd(unfolding, full_matrices=True)
        factors.append(u)
    if ranks is None:
        used = factors
    else:
        if (len(ranks) != x.ndim or any(not isinstance(r, (int, np.integer)) or isinstance(r, (bool, np.bool_))
                                      or r < 1 or r > x.shape[i] for i, r in enumerate(ranks))):
            raise ValueError("each truncation rank must be within its mode size")
        used = [u[:, :r] for u, r in zip(factors, ranks)]
    core = x
    for mode, u in enumerate(used):
        core = np.tensordot(u.T, core, axes=(1, mode))
        core = np.moveaxis(core, 0, mode)
    approx = core
    for mode, u in enumerate(used):
        approx = np.tensordot(u, approx, axes=(1, mode))
        approx = np.moveaxis(approx, 0, mode)
    return approx, core, used


def run_demo(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    omega = 2*np.pi
    t = np.linspace(0, 1, 501)
    p, q = 2.0, 0.75
    y = reconstruct(t, omega, p, q)
    fitted = coefficients(y, omega, t)

    # Synthetic operational tensor: service x [P,Q,D] x time window.
    windows = np.arange(12, dtype=float)
    tensor = np.empty((4, 3, len(windows)))
    for i in range(4):
        phase = 2*np.pi*windows/len(windows) + i*.37
        ps = 1.1 + .55*np.sin(phase) + .08*i
        qs = .55 + .42*np.cos(phase*.8) - .03*i
        ds = np.hypot(ps-1.0, qs)
        tensor[i, 0, :] = ps
        tensor[i, 1, :] = qs
        tensor[i, 2, :] = ds
    assert np.all(tensor >= 0), "operational synthetic indices must be nonnegative"
    with (out_dir / "synthetic_windows.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_kind", "service", "window_time", "P", "Q", "D", "delta_D", "delta_D_per_time"])
        for service in range(tensor.shape[0]):
            for j, instant in enumerate(windows):
                delta = "" if j == 0 else tensor[service,2,j]-tensor[service,2,j-1]
                velocity = "" if j == 0 else delta/(instant-windows[j-1])
                writer.writerow(["SINTETICO", service+1, instant, *tensor[service,:,j], delta, velocity])
    matrix = tensor[0, :, :].T  # rows: windows; columns: P,Q,D for service 0
    u, singular, vh = np.linalg.svd(matrix, full_matrices=False)
    matrix_rank = int(np.linalg.matrix_rank(matrix))
    matrix_rank2_error = float(np.linalg.norm(matrix - u[:, :2] @ np.diag(singular[:2]) @ vh[:2, :]))
    full, _, _ = hosvd(tensor)
    truncated, _, _ = hosvd(tensor, (2, 2, 3))
    full_error = float(np.linalg.norm(full-tensor))
    trunc_error = float(np.linalg.norm(truncated-tensor))
    tensor_norm = float(np.linalg.norm(tensor))
    # Projection from three metrics to two coefficients has a null direction.
    projection = np.array([[1.,0.], [0.,1.], [1.,1.]])
    null_direction = np.array([1.,1.,-1.])
    assert np.allclose(null_direction @ projection, 0)
    with (out_dir / "synthetic_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["SINTETICO", "metric", "value"])
        w.writerows([("SINTETICO", "P", fitted[0]), ("SINTETICO", "Q", fitted[1]),
                     ("SINTETICO", "S", fitted[2]), ("SINTETICO", "theta_rad", fitted[3]),
                     ("SINTETICO", "signal_rank", fitted[4]),
                     ("SINTETICO", "cycle_mean_y2", float(np.mean(y[:-1]**2))),
                     ("SINTETICO", "expected_S2_over_2", fitted[2]**2/2),
                     ("SINTETICO", "service_count", tensor.shape[0]),
                     ("SINTETICO", "metric_order", "P;Q;D"),
                     ("SINTETICO", "window_count", tensor.shape[2]),
                     ("SINTETICO", "D_reference", "P_ref=1;Q_ref=0"),
                     ("SINTETICO", "service0_matrix_rank_PQD_by_window", matrix_rank),
                     ("SINTETICO", "service0_matrix_singular_values", ";".join(map(str,singular))),
                     ("SINTETICO", "service0_matrix_svd_rank2_error", matrix_rank2_error),
                     ("SINTETICO", "hosvd_full_error", full_error),
                     ("SINTETICO", "hosvd_full_relative_error", full_error/tensor_norm),
                     ("SINTETICO", "hosvd_truncated_error", trunc_error),
                     ("SINTETICO", "hosvd_truncated_relative_error", trunc_error/tensor_norm),
                     ("SINTETICO", "service0_D_max_abs_delta_per_window", float(np.max(np.abs(np.diff(tensor[0,2,:]))))),
                     ("SINTETICO", "projection_null_direction", ";".join(map(str,null_direction)))])
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        # Keep the demo useful with only Python's standard library.
        import html
        def svg_plot(filename, title, series, x_label, y_label):
            width, height, left, right, top, bottom = 760, 420, 72, 24, 52, 55
            flat = [v for _, vals, _ in series for v in vals]
            lo, hi = min(flat), max(flat)
            if hi == lo: hi = lo + 1
            all_x = [v for _, _, xs in series for v in xs]
            xlo, xhi = min(all_x), max(all_x)
            if xhi == xlo: xhi = xlo + 1
            colors = ["#1769aa", "#e67e22", "#2e8b57", "#9c27b0"]
            parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                     '<rect width="100%" height="100%" fill="white"/>',
                     f'<text x="{width/2}" y="26" text-anchor="middle" font-family="sans-serif" font-size="17">{html.escape(title)}</text>',
                     f'<text x="{width/2}" y="{height-10}" text-anchor="middle" font-family="sans-serif" font-size="12">{html.escape(x_label)}</text>',
                     f'<text x="15" y="{height/2}" font-family="sans-serif" font-size="12">{html.escape(y_label)}</text>',
                     f'<path d="M{left} {top} V{height-bottom} H{width-right}" fill="none" stroke="#555"/>']
            for i in range(5):
                xv = xlo + (xhi-xlo)*i/4
                px = left + (width-left-right)*i/4
                yv = lo + (hi-lo)*i/4
                py = height-bottom - (height-top-bottom)*i/4
                parts.extend([f'<path d="M{px:.1f} {top} V{height-bottom}" stroke="#ddd"/>',
                              f'<text x="{px:.1f}" y="{height-bottom+17}" text-anchor="middle" font-family="sans-serif" font-size="10">{xv:.3g}</text>',
                              f'<path d="M{left} {py:.1f} H{width-right}" stroke="#eee"/>',
                              f'<text x="{left-7}" y="{py+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="10">{yv:.3g}</text>'])
            parts.append('<text x="740" y="45" text-anchor="end" font-family="sans-serif" font-size="11">SINTÉTICO</text>')
            for idx, (label, vals, xs) in enumerate(series):
                pts = []
                for x, v in zip(xs, vals):
                    px = left + (width-left-right)*(x-xlo)/(xhi-xlo)
                    py = height-bottom - (height-top-bottom)*(v-lo)/(hi-lo)
                    pts.append(f"{px:.1f},{py:.1f}")
                parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{colors[idx%len(colors)]}" stroke-width="2"/>')
                if len(pts) == 1:
                    px, py = pts[0].split(",")
                    parts.append(f'<circle cx="{px}" cy="{py}" r="5" fill="{colors[idx%len(colors)]}"/>')
                parts.append(f'<text x="{width-right-110}" y="{top+18*idx}" font-family="sans-serif" font-size="12" fill="{colors[idx%len(colors)]}">{html.escape(label)}</text>')
            parts.append('</svg>')
            (out_dir / filename).write_text("\n".join(parts), encoding="utf-8")
        # Parametric P-Q path with directional arrows, time ordering, and the reference.
        pq = tensor[0, :2, :].T
        xmin, xmax = min(0.8, float(pq[:,0].min())), max(1.8, float(pq[:,0].max()))
        ymin, ymax = min(-0.1, float(pq[:,1].min())), max(1.0, float(pq[:,1].max()))
        # A square plotting box and equal numeric spans preserve equal px/unit.
        span = max(xmax-xmin, ymax-ymin)
        xmid, ymid = (xmin+xmax)/2, (ymin+ymax)/2
        xmin, xmax = xmid-span/2, xmid+span/2
        ymin, ymax = ymid-span/2, ymid+span/2
        W,H,L,R,T,B = 680,500,135,165,55,65
        def xy(px, qy):
            return L+(W-L-R)*(px-xmin)/(xmax-xmin), H-B-(H-T-B)*(qy-ymin)/(ymax-ymin)
        pts = [xy(px,qy) for px,qy in pq]
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
                 '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#1769aa"/></marker></defs>',
                 '<rect width="100%" height="100%" fill="white"/>',
                 '<text x="340" y="25" text-anchor="middle" font-family="sans-serif" font-size="17">SINTÉTICO — trajetória temporal no plano P,Q</text>',
                 f'<path d="M{L} {T} V{H-B} H{W-R}" fill="none" stroke="#555"/>',
                 f'<text x="350" y="{H-15}" text-anchor="middle" font-family="sans-serif">P (índice sintético)</text>',
                 f'<text x="16" y="250" font-family="sans-serif">Q (índice sintético)</text>']
        for tick in range(5):
            xv, yv = xmin + span*tick/4, ymin + span*tick/4
            px, py = xy(xv, yv)
            parts.append(f'<text x="{px:.1f}" y="{H-B+18}" text-anchor="middle" font-family="sans-serif" font-size="10">{xv:.2f}</text>')
            parts.append(f'<text x="{L-8}" y="{py+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="10">{yv:.2f}</text>')
        for j in range(len(pts)-1):
            parts.append(f'<path d="M{pts[j][0]:.1f},{pts[j][1]:.1f} L{pts[j+1][0]:.1f},{pts[j+1][1]:.1f}" fill="none" stroke="#1769aa" stroke-width="2" marker-end="url(#arr)"/>')
        for j,(px,py) in enumerate(pts):
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="#1769aa"/><text x="{px+5:.1f}" y="{py-5:.1f}" font-family="sans-serif" font-size="10">{j}</text>')
        rx,ry = xy(1.,0.)
        parts.append(f'<path d="M{rx-7:.1f} {ry-7:.1f} L{rx+7:.1f} {ry+7:.1f} M{rx-7:.1f} {ry+7:.1f} L{rx+7:.1f} {ry-7:.1f}" stroke="#d33" stroke-width="3"/><text x="{rx+9:.1f}" y="{ry+14:.1f}" fill="#d33" font-family="sans-serif">referência (1,0)</text></svg>')
        (out_dir / "synthetic_pq_trajectory.svg").write_text("\n".join(parts), encoding="utf-8")
        svg_plot("synthetic_harmonic.svg", "SINTÉTICO — reconstrução harmônica", [("y(t)", y, t)], "tempo t", "amplitude y")
        svg_plot("synthetic_distance.svg", "SINTÉTICO — distância D ao ponto (1,0)", [(f"serviço {i+1}", tensor[i,2,:], windows) for i in range(4)], "janela temporal", "D = hypot(P−1,Q)")
        svg_plot("synthetic_svd.svg", "SINTÉTICO — serviço 1: janela × [P,Q,D]", [("singulares", singular, np.arange(1,len(singular)+1))], "índice singular", "valor singular")
        svg_plot("synthetic_hosvd.svg", "SINTÉTICO — erros HOSVD", [("full", [full_error], [1]), ("truncado", [trunc_error], [2])], "aproximação (1=full, 2=truncado)", "erro Frobenius")
        print("matplotlib indisponível; plots SVG sintéticos gerados via biblioteca padrão")
    else:
        fig, ax = plt.subplots()
        ax.plot(tensor[0,0,:], tensor[0,1,:], "o-", label="serviço sintético 1 (ordem temporal)")
        for k, (px, qy) in enumerate(tensor[0,:2,:].T): ax.annotate(str(k), (px,qy), xytext=(4,4), textcoords="offset points", fontsize=8)
        ax.scatter([1], [0], marker="x", s=90, color="red", label="referência (1,0)")
        ax.set(xlabel="P (índice sintético)", ylabel="Q (índice sintético)", title="SINTÉTICO — trajetória temporal P,Q")
        ax.set_aspect("equal", "box")
        ax.legend(); fig.tight_layout(); fig.savefig(out_dir / "synthetic_pq_trajectory.png"); plt.close(fig)
        fig, ax = plt.subplots()
        for i in range(tensor.shape[0]): ax.plot(windows, tensor[i,2,:], "o-", label=f"serviço {i+1}")
        ax.set(xlabel="janela temporal", ylabel="D = hypot(P−1,Q)", title="SINTÉTICO — distância ao ponto de referência")
        ax.legend(); fig.tight_layout(); fig.savefig(out_dir / "synthetic_distance.png"); plt.close(fig)
        fig, ax = plt.subplots()
        ax.plot(t, y, label="SINTÉTICO y(t)")
        ax.set(xlabel="t", ylabel="y", title="SINTÉTICO — reconstrução harmônica")
        ax.legend(); fig.tight_layout(); fig.savefig(out_dir / "synthetic_harmonic.png"); plt.close(fig)
        fig, ax = plt.subplots()
        ax.semilogy(np.arange(1, len(singular)+1), singular, "o-")
        ax.set(xlabel="índice singular", ylabel="valor singular", title="SINTÉTICO — serviço 1: janelas × [P,Q,D]")
        fig.tight_layout(); fig.savefig(out_dir / "synthetic_svd.png"); plt.close(fig)
        fig, ax = plt.subplots()
        ax.bar(["full", "truncado"], [full_error, trunc_error])
        ax.set(ylabel="erro Frobenius", title="SINTÉTICO — HOSVD")
        fig.tight_layout(); fig.savefig(out_dir / "synthetic_hosvd.png"); plt.close(fig)
        print("plots sintéticos gerados")
    print(f"CSV sintético: {out_dir / 'synthetic_summary.csv'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "output")
    run_demo(parser.parse_args().out)
