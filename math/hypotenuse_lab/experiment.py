"""Experimento sintético: S é a entrada e a hipotenusa; Q é residual geométrico."""
import csv
import json
import math
from pathlib import Path


def triangle(s, p):
    """Aceita entradas normalizadas válidas; não corta P silenciosamente."""
    for value in (s, p):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("S e P devem ser números finitos")
    if not 0 <= p <= s <= 1:
        raise ValueError("Domínio exigido: 0 <= P <= S <= 1")
    q = math.sqrt(s-p) * math.sqrt(s+p)
    return dict(S=s, P=p, Q=q, theta=None if s == 0 else math.atan2(q, p),
                D=math.hypot(p-1, q))


def from_ratio(s, alpha):
    """P=alpha*S garante o domínio, mas alpha não é uma medição de eficiência."""
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError("alpha deve pertencer a [0,1]")
    return triangle(s, alpha*s)


def wave(point, t):
    """Um ciclo de codificação; a frequência escolhida não vem da aplicação."""
    return point["P"]*math.sin(2*math.pi*t) + point["Q"]*math.cos(2*math.pi*t)


def svg(name, title, series, xmax, ymin, ymax, xlabel, ylabel, out):
    width, height = 1000, 600
    left, right, top, bottom = 90, 250, 70, 80
    pw, ph = width-left-right, height-top-bottom
    def xy(x,y): return left+pw*x/xmax, top+ph*(ymax-y)/(ymax-ymin)
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
                '<rect width="100%" height="100%" fill="white"/>',
                f'<text x="40" y="32" font-family="sans-serif" font-size="22">{title}</text>']
    for i in range(5):
        x=xmax*i/4; y=ymin+(ymax-ymin)*i/4
        px,_=xy(x,0); _,py=xy(0,y)
        elements.extend([f'<path d="M{px} {top}V{top+ph} M{left} {py}H{left+pw}" stroke="#ddd"/>',
                         f'<text x="{px}" y="{top+ph+26}" text-anchor="middle" font-family="sans-serif">{x:.2f}</text>',
                         f'<text x="{left-12}" y="{py+5}" text-anchor="end" font-family="sans-serif">{y:.2f}</text>'])
    elements.append(f'<rect x="{left}" y="{top}" width="{pw}" height="{ph}" fill="none" stroke="#333"/>')
    for i,(label,color,points) in enumerate(series):
        coords=' '.join(f'{xy(x,y)[0]:.3f},{xy(x,y)[1]:.3f}' for x,y in points)
        elements.extend([f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3"/>',
                         f'<text x="{width-right+20}" y="{top+30*i+10}" fill="{color}" font-family="sans-serif" font-size="15">{label}</text>'])
    elements.extend([f'<text x="{left+pw/2}" y="{height-20}" text-anchor="middle" font-family="sans-serif">{xlabel}</text>',
                     f'<text x="20" y="{top+ph/2}" font-family="sans-serif">{ylabel}</text>', '</svg>'])
    (out/name).write_text('\n'.join(elements), encoding='utf-8')


def main():
    out=Path(__file__).parent/'output'; out.mkdir(exist_ok=True)
    rows=[]
    for s in (0,.25,.5,.75,1):
        for i in range(101):
            a=i/100; point=from_ratio(s,a)
            rows.append(dict(source_kind='SINTETICO', alpha=a, **point))
    with (out/'scenarios.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    error=max(abs(r['S']**2-r['P']**2-r['Q']**2) for r in rows)
    (out/'summary.json').write_text(json.dumps(dict(source_kind='synthetic',scenarios=len(rows),
        max_pythagorean_absolute_error=error,construction='S input; P=alpha*S; Q=sqrt(S-P)*sqrt(S+P)',
        domain='0<=P<=S<=1; 0<=alpha<=1',carrier_cycles=1),indent=2),encoding='utf-8')
    colors=['#2166ac','#e08214','#16865a','#9b4f96']
    svg('coefficients.svg','SINTÉTICO — S=0,8 fixo: distribuição entre P e Q',[
        ('P = alpha × S',colors[0],[(i/200,from_ratio(.8,i/200)['P']) for i in range(201)]),
        ('Q residual',colors[1],[(i/200,from_ratio(.8,i/200)['Q']) for i in range(201)]),
        ('S = 0,8',colors[2],[(0,.8),(1,.8)])],1,0,1,'alpha = P/S','valor',out)
    selected=[from_ratio(.8,a) for a in (0,.5,1/math.sqrt(2),1)]
    svg('waves.svg','SINTÉTICO — mesma amplitude S=0,8; fases diferentes',[
        (f'alpha={a:.4f}',color,[(i/400,wave(point,i/400)) for i in range(401)])
        for a,color,point in zip((0,.5,1/math.sqrt(2),1),colors,selected)
    ],1,-1,1,'tempo do ciclo de codificação','y(t)',out)
    print(json.dumps(dict(scenarios=len(rows),max_pythagorean_absolute_error=error)))


if __name__=='__main__': main()
