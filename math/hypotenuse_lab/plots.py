"""Gera SVGs dos resultados da hipótese S como hipotenusa, sem dependências gráficas."""
from __future__ import annotations

import html
import math
from pathlib import Path


def _number(value):
    """Converte números finitos; valores ausentes/inválidos viram None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _svg_start(width, height, title, label):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="white"/>',
            f'<text x="{width/2}" y="25" text-anchor="middle" font-family="sans-serif" font-size="17">{html.escape(title)}</text>',
            f'<text x="{width/2}" y="47" text-anchor="middle" font-family="sans-serif" font-size="11">{html.escape(label)}</text>']


def _polyline_segments(points, color, stroke=2):
    """Desenha trechos separados; None quebra a linha e não conecta lacunas."""
    out, segment = [], []
    for point in points:
        if point is None:
            if len(segment) > 1:
                out.append(f'<polyline points="{" ".join(segment)}" fill="none" stroke="{color}" stroke-width="{stroke}"/>')
            segment = []
        else:
            segment.append(f"{point[0]:.2f},{point[1]:.2f}")
    if len(segment) > 1:
        out.append(f'<polyline points="{" ".join(segment)}" fill="none" stroke="{color}" stroke-width="{stroke}"/>')
    return out


def _axes(out, left, top, width, height, xmin, xmax, ymin, ymax, xlabel, ylabel, xticks=5, yticks=5):
    out.append(f'<path d="M{left} {top} V{top+height} H{left+width}" fill="none" stroke="#444"/>')
    for i in range(xticks):
        f = i/(xticks-1) if xticks > 1 else 0
        x, value = left+width*f, xmin+(xmax-xmin)*f
        out.extend([f'<path d="M{x:.1f} {top} V{top+height}" stroke="#eee"/>',
                    f'<text x="{x:.1f}" y="{top+height+16}" text-anchor="middle" font-family="sans-serif" font-size="10">{value:.3g}</text>'])
    for i in range(yticks):
        f = i/(yticks-1) if yticks > 1 else 0
        y, value = top+height-height*f, ymin+(ymax-ymin)*f
        out.extend([f'<path d="M{left} {y:.1f} H{left+width}" stroke="#eee"/>',
                    f'<text x="{left-7}" y="{y+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="10">{value:.3g}</text>'])
    out.append(f'<text x="{left+width/2}" y="{top+height+39}" text-anchor="middle" font-family="sans-serif" font-size="11">{html.escape(xlabel)}</text>')
    out.append(f'<text x="12" y="{top+height/2}" font-family="sans-serif" font-size="11">{html.escape(ylabel)}</text>')


def _scale_x(value, xmin, xmax, left, width):
    return left+width*(value-xmin)/(xmax-xmin or 1)


def _scale_y(value, ymin, ymax, top, height):
    return top+height-height*(value-ymin)/(ymax-ymin or 1)


def _save(out_dir, filename, parts):
    parts.append('</svg>')
    (out_dir/filename).write_text("\n".join(parts), encoding="utf-8")


def _temporal(records, out_dir, label):
    """Painéis por serviço para P, Q, S e D, indexados pela janela."""
    services = sorted({str(r.get("service", "desconhecido")) for r in records})
    if not services:
        services = ["sem dados"]
    width, row_h, height = 900, 250, 100+250*len(services)
    parts = _svg_start(width, height, "S, P, Q e D por janela", label)
    colors = {"P": "#1769aa", "Q": "#e67e22", "S": "#2e8b57", "D": "#9b59b6"}
    metrics = ("P", "Q", "S", "D")
    for si, service in enumerate(services):
        subset = sorted((r for r in records if str(r.get("service", "desconhecido")) == service),
                        key=lambda r: _number(r.get("window_index")) if _number(r.get("window_index")) is not None else -1)
        indexes = [_number(r.get("window_index")) for r in subset]
        valid_indexes = [x for x in indexes if x is not None]
        xmin, xmax = (min(valid_indexes), max(valid_indexes)) if valid_indexes else (0., 1.)
        if xmin == xmax: xmin, xmax = xmin-.5, xmax+.5
        known = [_number(r.get(m)) for r in subset for m in metrics]
        known = [x for x in known if x is not None]
        limit = max(1.0, max(known, default=1.0))*1.08
        top, plot_h, left, plot_w = 70+si*row_h, 160, 75, 785
        parts.append(f'<text x="{left}" y="{top-10}" font-family="sans-serif" font-size="13">Serviço: {html.escape(service)}</text>')
        _axes(parts, left, top, plot_w, plot_h, xmin, xmax, 0, limit, "índice da janela", "valor")
        for metric in metrics:
            points = []
            for idx, row in zip(indexes, subset):
                value = _number(row.get(metric))
                if idx is None or value is None:
                    points.append(None)
                else:
                    points.append((_scale_x(idx,xmin,xmax,left,plot_w), _scale_y(value,0,limit,top,plot_h)))
            parts.extend(_polyline_segments(points, colors[metric]))
        # Legenda de cada serviço, incluindo S como referência constante se assim vier no contrato.
        for j, metric in enumerate(metrics):
            x = left+j*85
            parts.append(f'<path d="M{x} {top+plot_h+56} h18" stroke="{colors[metric]}" stroke-width="3"/><text x="{x+22}" y="{top+plot_h+60}" font-family="sans-serif" font-size="11">{metric}</text>')
    _save(out_dir, "temporal.svg", parts)


def _trajectory(records, out_dir, label):
    """Plano P-Q com círculo unitário e a referência A=(1,0), em escala igual."""
    W, H = 860, 700
    left, top, side = 115, 95, 480
    parts = _svg_start(W, H, "Trajetória no plano P-Q", label)
    # Domínio normalizado [0,1]². O círculo completo é recortado pela área dos eixos.
    lo, hi = 0.0, 1.0
    sx = lambda x: left+side*(x-lo)/(hi-lo)
    sy = lambda y: top+side-side*(y-lo)/(hi-lo)
    parts.extend(['<defs>', f'<clipPath id="pq-plot-area"><rect x="{left}" y="{top}" width="{side}" height="{side}"/></clipPath>', '</defs>'])
    parts.append(f'<rect x="{left}" y="{top}" width="{side}" height="{side}" fill="none" stroke="#555"/>')
    for i in range(5):
        value = i/4
        x,y=sx(value),sy(value)
        parts.extend([f'<path d="M{x:.1f} {top} V{top+side}" stroke="#e8e8e8"/>',
                      f'<text x="{x:.1f}" y="{top+side+18}" text-anchor="middle" font-family="sans-serif" font-size="10">{value:.2f}</text>',
                      f'<path d="M{left} {y:.1f} H{left+side}" stroke="#e8e8e8"/>',
                      f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="10">{value:.2f}</text>'])
    parts.append(f'<text x="{left+side/2}" y="{top+side+42}" text-anchor="middle" font-family="sans-serif" font-size="12">P normalizado</text>')
    parts.append(f'<text x="28" y="{top+side/2}" text-anchor="middle" transform="rotate(-90,28,{top+side/2})" font-family="sans-serif" font-size="12">Q normalizado</text>')
    parts.append(f'<g clip-path="url(#pq-plot-area)"><circle cx="{sx(0):.2f}" cy="{sy(0):.2f}" r="{side/(hi-lo):.2f}" fill="none" stroke="#999" stroke-dasharray="5 5"/>')
    ax, ay = sx(1), sy(0)
    parts.append(f'<path d="M{ax-7:.1f} {ay-7:.1f} L{ax+7:.1f} {ay+7:.1f} M{ax-7:.1f} {ay+7:.1f} L{ax+7:.1f} {ay-7:.1f}" stroke="#111" stroke-width="3"/><text x="{ax-55:.1f}" y="{ay-10:.1f}" font-family="sans-serif" font-size="11">A=(1,0)</text>')
    bx, by = sx(1/math.sqrt(2)), sy(1/math.sqrt(2))
    parts.append(f'<circle cx="{bx:.2f}" cy="{by:.2f}" r="5" fill="#d33"/><text x="{bx+8:.1f}" y="{by-7:.1f}" font-family="sans-serif" font-size="11">B45</text>')
    services = sorted({str(r.get("service", "desconhecido")) for r in records})
    palette = ["#1769aa", "#e67e22", "#2e8b57", "#9b59b6", "#d33"]
    legend = []
    for si, service in enumerate(services):
        subset = sorted((r for r in records if str(r.get("service", "desconhecido")) == service),
                        key=lambda r: _number(r.get("window_index")) if _number(r.get("window_index")) is not None else -1)
        pts = []
        for row in subset:
            p, q = _number(row.get("P")), _number(row.get("Q"))
            pts.append(None if p is None or q is None else (sx(p), sy(q)))
        # Traço espesso e traço fino interrompido permitem ver séries quase coincidentes.
        dash = ' stroke-dasharray="7 5"' if si % 2 else ''
        parts.append(f'<g{dash}>')
        parts.extend(_polyline_segments(pts, palette[si%len(palette)], 2 if si % 2 else 4))
        parts.append('</g>')
        for row, point in zip(subset, pts):
            if point is not None:
                parts.append(f'<circle cx="{point[0]:.2f}" cy="{point[1]:.2f}" r="{2 if si % 2 else 4}" fill="{palette[si%len(palette)]}"><title>{html.escape(service)}, janela {html.escape(str(row.get("window_index")))}</title></circle>')
        ly = 125+si*24
        legend.append(f'<path d="M635 {ly} h18" stroke="{palette[si%len(palette)]}" stroke-width="3"{dash}/><text x="660" y="{ly+4}" font-family="sans-serif" font-size="11">{html.escape(service)}</text>')
    parts.append('</g>')
    parts.extend(legend)
    parts.append(f'<text x="430" y="680" text-anchor="middle" font-family="sans-serif" font-size="11">Eixos P e Q em escala igual; círculo unitário tracejado, recortado à área dos eixos.</text>')
    _save(out_dir, "trajectory.svg", parts)


def _waves(records, out_dir, label):
    """Exibe até três ondas-modelo em portadora sintética de 1 Hz, durante 1 s."""
    valid = [r for r in records if all(_number(r.get(k)) is not None for k in ("P", "Q", "S"))]
    selected = []
    if valid:
        service = min(str(row.get("service", "")) for row in valid)
        ordered = sorted((row for row in valid if str(row.get("service", "")) == service), key=lambda row: row["P"])
        selected = [ordered[index] for index in sorted({0, len(ordered)//2, len(ordered)-1})]
    W, panel_h, H = 850, 210, 95+210*max(1,len(selected))
    parts = _svg_start(W, H, "Ondas harmônicas para janelas selecionadas", label)
    if not selected:
        parts.append('<text x="60" y="100" font-family="sans-serif">Sem janelas válidas para reconstruir a onda.</text>')
    for i, row in enumerate(selected):
        top, left, plot_w, plot_h = 65+i*panel_h, 80, 740, 125
        p,q,s = (_number(row[k]) for k in ("P","Q","S"))
        times = [j/200 for j in range(201)]
        ys = [p*math.sin(2*math.pi*t)+q*math.cos(2*math.pi*t) for t in times]
        ymax=max(1.0,s)*1.1
        title=f"{row.get('service','serviço')} — janela {row.get('window_index')} — P={p:.4g}, S={s:.4g}; portadora sintética 1 Hz"
        parts.append(f'<text x="{left}" y="{top-8}" font-family="sans-serif" font-size="12">{html.escape(title)}</text>')
        _axes(parts,left,top,plot_w,plot_h,0,1,-ymax,ymax,"tempo sintético (s)","y(t)")
        points=[(_scale_x(t,0,1,left,plot_w),_scale_y(y,-ymax,ymax,top,plot_h)) for t,y in zip(times,ys)]
        parts.extend(_polyline_segments(points,"#1769aa",2))
    _save(out_dir,"waves.svg",parts)


def generate_plots(records, out_dir, label):
    """Gera temporal.svg, trajectory.svg e waves.svg para uma fonte selecionada.

    Parâmetros:
        records: lista de registros do pipeline; P/Q/S/D ausentes devem ser None.
        out_dir: diretório exclusivo para a origem correspondente.
        label: rótulo de proveniência, por exemplo SINTÉTICO ou MEDIÇÕES DO LAB + TRANSFORMAÇÃO EXPERIMENTAL.
    """
    rows = list(records)
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)
    _temporal(rows, destination, label)
    _trajectory(rows, destination, label)
    _waves(rows, destination, label)
    return [destination/name for name in ("temporal.svg", "trajectory.svg", "waves.svg")]
