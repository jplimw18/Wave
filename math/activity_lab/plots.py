"""Plots SVG para a variante de atividade V e resíduo geométrico Q0."""
from __future__ import annotations

import html
import math
from pathlib import Path


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _start(width, height, title, label):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="white"/>',
            f'<text x="{width/2}" y="25" text-anchor="middle" font-family="sans-serif" font-size="17">{html.escape(title)}</text>',
            f'<text x="{width/2}" y="44" text-anchor="middle" font-family="sans-serif" font-size="10">{html.escape(label)}</text>']


def _save(path, parts):
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def _axes(parts, left, top, width, height, xmin, xmax, ymin, ymax, xlabel, ylabel):
    parts.append(f'<path d="M{left} {top} V{top+height} H{left+width}" fill="none" stroke="#444"/>')
    for i in range(5):
        f=i/4
        x=left+width*f; xv=xmin+(xmax-xmin)*f
        y=top+height-height*f; yv=ymin+(ymax-ymin)*f
        parts.extend([f'<path d="M{x:.1f} {top} V{top+height}" stroke="#eee"/>',
                      f'<text x="{x:.1f}" y="{top+height+16}" text-anchor="middle" font-family="sans-serif" font-size="10">{xv:.3g}</text>',
                      f'<path d="M{left} {y:.1f} H{left+width}" stroke="#eee"/>',
                      f'<text x="{left-7}" y="{y+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="10">{yv:.3g}</text>'])
    parts.extend([f'<text x="{left+width/2}" y="{top+height+37}" text-anchor="middle" font-family="sans-serif" font-size="11">{html.escape(xlabel)}</text>',
                  f'<text x="12" y="{top+height/2}" font-family="sans-serif" font-size="11">{html.escape(ylabel)}</text>'])


def _segments(points, color, width=2, dash=None):
    result=[]; run=[]
    dash_attr=f' stroke-dasharray="{dash}"' if dash else ""
    for point in points:
        if point is None:
            if len(run)>1:
                result.append(f'<polyline points="{" ".join(run)}" fill="none" stroke="{color}" stroke-width="{width}"{dash_attr}/>')
            run=[]
        else:
            run.append(f"{point[0]:.2f},{point[1]:.2f}")
    if len(run)>1:
        result.append(f'<polyline points="{" ".join(run)}" fill="none" stroke="{color}" stroke-width="{width}"{dash_attr}/>')
    return result


def _x(value, low, high, left, width):
    return left+width*(value-low)/(high-low or 1)


def _y(value, low, high, top, height):
    return top+height-height*(value-low)/(high-low or 1)


def _activity(records, outdir, label):
    services=sorted({str(row.get("service", "desconhecido")) for row in records}) or ["sem dados"]
    W,row_h=940,245
    H=75+row_h*len(services)
    parts=_start(W,H,"Índices de atividade por janela",label)
    palette={"V":"#1769aa","Q0":"#e67e22","Qv":"#2e8b57","Sv":"#9b59b6","S0":"#555555"}
    metrics=("V","Q0","Qv","Sv","S0")
    for si, service in enumerate(services):
        subset=sorted((r for r in records if str(r.get("service","desconhecido"))==service),
                      key=lambda r: _num(r.get("window_index")) if _num(r.get("window_index")) is not None else -1)
        indexes=[_num(r.get("window_index")) for r in subset]
        valid=[v for v in indexes if v is not None]
        xmin,xmax=(min(valid),max(valid)) if valid else (0.,1.)
        if xmin==xmax: xmin,xmax=xmin-.5,xmax+.5
        values=[_num(row.get(m)) for row in subset for m in metrics]
        ymax=max(1.,max((v for v in values if v is not None),default=1.))*1.08
        left,top,plotw,ploth=78,65+si*row_h,830,150
        parts.append(f'<text x="{left}" y="{top-9}" font-family="sans-serif" font-size="13">Serviço: {html.escape(service)}</text>')
        _axes(parts,left,top,plotw,ploth,xmin,xmax,0,ymax,"índice da janela","valor")
        for metric in metrics:
            points=[]
            for idx,row in zip(indexes,subset):
                val=_num(row.get(metric))
                points.append(None if idx is None or val is None else (_x(idx,xmin,xmax,left,plotw),_y(val,0,ymax,top,ploth)))
            parts.extend(_segments(points,palette[metric],2 if metric!="S0" else 1.5))
        for j,metric in enumerate(metrics):
            lx=left+j*93
            parts.append(f'<path d="M{lx} {top+ploth+54} h17" stroke="{palette[metric]}" stroke-width="3"/><text x="{lx+22}" y="{top+ploth+58}" font-family="sans-serif" font-size="11">{metric}</text>')
    _save(outdir/"activity.svg",parts)


def _trajectory(records,outdir,label):
    W,H=820,650
    left,top,side=105,85,470
    lo,hi=0.,1.
    sx=lambda v:left+side*(v-lo)/(hi-lo)
    sy=lambda v:top+side-side*(v-lo)/(hi-lo)
    parts=_start(W,H,"Trajetória no plano P-Qv",label)
    parts.extend(['<defs>',f'<clipPath id="activity-plane"><rect x="{left}" y="{top}" width="{side}" height="{side}"/></clipPath>','</defs>',
                  f'<rect x="{left}" y="{top}" width="{side}" height="{side}" fill="none" stroke="#444"/>'])
    for i in range(5):
        v=i/4;x=sx(v);y=sy(v)
        parts.extend([f'<path d="M{x:.1f} {top} V{top+side}" stroke="#eee"/>',
                      f'<text x="{x:.1f}" y="{top+side+17}" text-anchor="middle" font-family="sans-serif" font-size="10">{v:.2f}</text>',
                      f'<path d="M{left} {y:.1f} H{left+side}" stroke="#eee"/>',
                      f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="10">{v:.2f}</text>'])
    parts.extend([f'<text x="{left+side/2}" y="{top+side+40}" text-anchor="middle" font-family="sans-serif" font-size="12">P</text>',
                  f'<text x="25" y="{top+side/2}" text-anchor="middle" transform="rotate(-90 25 {top+side/2})" font-family="sans-serif" font-size="12">Qv</text>',
                  f'<g clip-path="url(#activity-plane)">'])
    colors=["#1769aa","#e67e22","#2e8b57","#9b59b6","#d33"]
    services=sorted({str(r.get("service","desconhecido")) for r in records})
    for si,service in enumerate(services):
        subset=sorted((r for r in records if str(r.get("service","desconhecido"))==service),key=lambda r:_num(r.get("window_index")) or 0)
        pts=[]
        for row in subset:
            p,q=_num(row.get("P")),_num(row.get("Qv"))
            pts.append(None if p is None or q is None else (sx(p),sy(q)))
        service_key=service.strip().lower()
        if service_key=="api-a":
            color,width,dash,marker_radius="#1769aa",4,None,5
        elif service_key=="api-b":
            color,width,dash,marker_radius="#e67e22",2,"7 4",3
        else:
            color,width,dash,marker_radius=colors[si%len(colors)],2,None,3
        parts.extend(_segments(pts,color,width,dash))
        for row,pt in zip(subset,pts):
            if pt is not None:
                parts.append(f'<circle cx="{pt[0]:.2f}" cy="{pt[1]:.2f}" r="{marker_radius}" fill="{color}"><title>{html.escape(service)}, janela {html.escape(str(row.get("window_index")))}</title></circle>')
    parts.append('</g>')
    # Legenda propositalmente fora do recorte do plano.
    for si,service in enumerate(services):
        y=112+si*23
        if service.strip().lower()=="api-a": color,width,dash="#1769aa",4,None
        elif service.strip().lower()=="api-b": color,width,dash="#e67e22",2,"7 4"
        else: color,width,dash=colors[si%len(colors)],2,None
        dash_attr=f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(f'<path d="M620 {y} h20" stroke="{color}" stroke-width="{width}"{dash_attr}/><text x="647" y="{y+4}" font-family="sans-serif" font-size="11">{html.escape(service)}</text>')
    parts.append(f'<text x="410" y="630" text-anchor="middle" font-family="sans-serif" font-size="11">Escala igual nos dois eixos; pontos conectados em ordem de janela.</text>')
    _save(outdir/"trajectory.svg",parts)


def _waves(records,outdir,label):
    services=sorted({str(r.get("service","desconhecido")) for r in records})
    selected=[]
    for service in services:
        valid=[r for r in records if str(r.get("service","desconhecido"))==service and all(_num(r.get(k)) is not None for k in ("V","P","Qv","S0","Sv"))]
        if len(valid)<3:
            continue
        valid.sort(key=lambda r:_num(r.get("V")))
        for idx in sorted({0,len(valid)//2,len(valid)-1}):
            row=valid[idx]
            # Mantém até os mesmos três regimes de um único serviço.
            selected=[(service,valid[0]),(service,valid[len(valid)//2]),(service,valid[-1])]
            break
        if selected: break
    W,ph,H=900,220,95+220*max(1,len(selected))
    parts=_start(W,H,"Ondas para regimes mínimo, mediano e máximo de V",label)
    if not selected:
        parts.append('<text x="60" y="110" font-family="sans-serif">Não há três janelas válidas do mesmo serviço para selecionar regimes.</text>')
    for i,(service,row) in enumerate(selected):
        p,q,s0,sv=(_num(row[k]) for k in ("P","Qv","S0","Sv"))
        top,left,plotw,ploth=65+i*ph,82,780,130
        times=[j/200 for j in range(201)]
        vals=[p*math.sin(2*math.pi*t)+q*math.cos(2*math.pi*t) for t in times]
        bound=max(1.,s0,sv)*1.1
        title=f"{service} — janela {row.get('window_index')} — regime V={_num(row['V']):.3g} — portadora sintética 1 Hz"
        parts.append(f'<text x="{left}" y="{top-8}" font-family="sans-serif" font-size="12">{html.escape(title)}</text>')
        _axes(parts,left,top,plotw,ploth,0,1,-bound,bound,"tempo sintético (s)","y(t)")
        pts=[(_x(t,0,1,left,plotw),_y(v,-bound,bound,top,ploth)) for t,v in zip(times,vals)]
        parts.extend(_segments(pts,"#1769aa",2))
        # Faixas horizontais: S0 é referência e Sv é amplitude efetiva.
        for amp,color,dash in ((s0,"#d33","6 4"),(sv,"#2e8b57","")):
            for sign in (-1,1):
                yy=_y(sign*amp,-bound,bound,top,ploth)
                parts.append(f'<path d="M{left} {yy:.2f} H{left+plotw}" stroke="{color}" stroke-width="1.5" stroke-dasharray="{dash}"/>')
        parts.append(f'<text x="{left+5}" y="{top+14}" fill="#d33" font-family="sans-serif" font-size="10">S0 ref={s0:.3g}</text><text x="{left+110}" y="{top+14}" fill="#2e8b57" font-family="sans-serif" font-size="10">Sv efetiva={sv:.3g}</text>')
    _save(outdir/"waves.svg",parts)


def generate_plots(records,outdir,label):
    """Gera activity.svg, trajectory.svg e waves.svg para uma fonte/proveniência.

    Parâmetros:
        records: registros do pipeline, com métricas ausentes representadas por None.
        outdir: diretório dos gráficos dessa fonte.
        label: rótulo de proveniência, por exemplo SINTÉTICO ou MEDIÇÕES DO LAB.
    """
    rows=list(records)
    destination=Path(outdir)
    destination.mkdir(parents=True,exist_ok=True)
    _activity(rows,destination,label)
    _trajectory(rows,destination,label)
    _waves(rows,destination,label)
    return [destination/name for name in ("activity.svg","trajectory.svg","waves.svg")]
