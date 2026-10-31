# Experimento separado: S como hipotenusa

S é entrada normalizada em [0,1]. Escolhe-se alpha em [0,1], P=alpha*S e
Q=sqrt(S²−P²), calculado por sqrt(S−P)*sqrt(S+P). Entradas diretas P>S
são rejeitadas, não corrigidas silenciosamente. Esta variante não substitui as
candidatas em que P e Q eram definidos independentemente.

O teste sintético não escolhe qual métrica real deve originar S ou alpha.
Q é um residual geométrico, não uma medição independente de atrito ou erros.
Restringir P por alpha muda a definição anterior de entrega útil; não usar esse
parâmetro como eficiência validada sem um contrato de métricas adicional.

Para S>0, cos(theta)=P/S=alpha e sin(theta)=Q/S=sqrt(1−alpha²).
Quando S=0, P=Q=0 e a fase fica ausente. O equilíbrio de 45 graus ocorre em
P=Q=S/sqrt(2); portanto o ponto (1/sqrt(2),1/sqrt(2)) só ocorre para S=1.
Se mantida a fronteira radial anterior, ela continua baseada na referência
unitária fixa; não recalibrar o raio por S sem definir uma nova hipótese.

A onda y(t)=P*sin(2*pi*t)+Q*cos(2*pi*t) tem amplitude S e fase theta.
O ciclo é uma escolha de codificação sintética, não periodicidade medida.
O S fixo impõe um arco no plano P,Q: aumentar P reduz Q por construção.
Isso não é evidência de anticorrelação operacional. A distância permanece
D=hypot(P−1,Q), com D²=S²−2P+1.

## Executar da raiz

```sh
python -m unittest discover -s math/hypotenuse_lab -p 'test_*.py' -v
python math/hypotenuse_lab/experiment.py
```

Somente biblioteca padrão Python. output/ contém 505 pares sintéticos, resumo
do erro de Pitágoras e gráficos SVG da distribuição e das ondas resultantes.
