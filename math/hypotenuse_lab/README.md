# Padrão principal: S como hipotenusa

O pipeline completo está em `pipeline.py` e no [contrato v3](../../docs/math/HIPOTENUSA_PIPELINE.md). Ele fixa Sref=1, Tref=40 req/s e Lref=0,1s antes da coleta; calcula alpha a partir da entrega útil penalizada pela média de latência, limita alpha explicitamente a [0,1] e preserva valores brutos/cortes. CPU/RSS são covariáveis, sem entrar em S. S não representa provisionamento ou capacidade medida. Q é resíduo geométrico, não perda medida. As candidatas anteriores ficam preservadas.

S é entrada normalizada em [0,1]. Escolhe-se alpha em [0,1], P=alpha*S e
Q=sqrt(S²−P²), calculado por sqrt(S−P)*sqrt(S+P). Entradas diretas P>S
são rejeitadas, não corrigidas silenciosamente. Esta variante não substitui as
candidatas em que P e Q eram definidos independentemente.

O núcleo `experiment.py`, isoladamente, não escolhe qual métrica real deve originar S ou alpha. Essa escolha experimental está explícita no pipeline v3 acima.
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

O núcleo usa somente a biblioteca padrão. `output/` contém 505 pares sintéticos, resumo do erro de Pitágoras e gráficos SVG da distribuição e das ondas resultantes.

## Pipeline completo

Use Python 3.11 ou superior em um ambiente virtual e instale a versão testada do NumPy:

```powershell
python -m pip install -r math/hypotenuse_lab/requirements.txt
python math/hypotenuse_lab/pipeline.py
```

O modo padrão gera 20 janelas sintéticas (duas APIs × dez janelas), incluindo duas acima da referência para exercitar o corte. Produz matriz temporal [P,Q,D], tensor serviço×métrica×janela, SVD/HOSVD, tensor de ondas com 64 fases e três SVGs em `output/pipeline-synthetic/`. Todos esses dados são modelados, não coletados.

Para analisar uma captura real existente, separadamente:

```powershell
python math/hypotenuse_lab/pipeline.py --input evidence/hypotenuse-run/capture.json --out math/hypotenuse_lab/output/pipeline-observed
```

A entrada preserva `source_kind`, timestamps, contadores, histogramas e demais brutos. Não substitua uma captura ausente por dados históricos sem identificar sua origem. Ausências no tensor são `null`; a decomposição usa apenas as janelas completas comuns, com exclusões explícitas. Ondas são codificações de 1 Hz, não periodicidade observada. A geometria S=1 torna sua amplitude constante e a média quadrática igual a 0,5 por construção.

## Rodada executada em 30/10/2026, horário de São Paulo

Executados 15 testes: quatro do núcleo geométrico (incluindo a grade de 505 cenários), nove do pipeline e dois dos gráficos. Todos passaram. O pipeline foi executado tanto com os cenários sintéticos quanto com a captura nova do Kubernetes, mantendo os diretórios separados.

A captura `evidence/hypotenuse-run/capture.json` contém 20 registros, duas APIs × dez janelas, com timestamps UTC de 31/10/2026 aproximadamente 02:54:48–02:55:39; correspondem a 30/10/2026 23:54:48–23:55:39 em São Paulo. O SHA256 da entrada é `0e5ecda40f0f2203771c52c94c8a5c2d456f456d686e601083ca03c866214f19`. As referências foram registradas separadamente antes da coleta em `reference.json`.

| Verificação | Cenários sintéticos | Medições novas do laboratório |
|---|---:|---:|
| Registros / janelas comuns | 20 / 10 | 20 / 10 |
| Cortes explícitos de P | 2 | 0 |
| Tensor geométrico | 2×3×10 | 2×3×10 |
| Tensor de ondas | 2×10×64 | 2×10×64 |
| Posto da matriz de ondas | 2 | 2 |
| Erro relativo HOSVD completa | 1,0243×10⁻¹⁵ | 5,8252×10⁻¹⁶ |
| Erro relativo HOSVD truncada | 0,028891 | 0,014679 |
| Erro máximo da média quadrática do ciclo | 1,11×10⁻¹⁶ | 1,11×10⁻¹⁶ |

Na coleta real, todas as médias de latência ficaram abaixo de 0,1s: o fator de qualidade foi 1 em todas as janelas. Houve duas classificações geométricas dentro e 18 fora; isso é a aplicação do limiar imposto, não uma avaliação validada de eficiência. As 110 respostas 404 foram provocadas pelo plano de carga; não representam falhas internas espontâneas. A auditoria operacional separada registrou 1.720 concluídas, zero falhas de transporte, zero reinícios de contador/pod e concordância das contagens cliente-servidor. Q elevado nas janelas de baixa demanda é consequência da construção S=1, não evidência de desperdício.
