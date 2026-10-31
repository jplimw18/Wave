# Pipeline v3: S como hipotenusa e referência fixa

O padrão geométrico desta rodada é **S como entrada/hipotenusa**, P restrito a 0≤P≤S e Q calculado como resíduo geométrico. As candidatas v1/v2 em que P e Q eram definidos independentemente permanecem preservadas para comparação, mas não são o modelo principal desta rodada.

O usuário definiu o padrão geométrico, sem definir qual métrica operacional origina S. Para executar uma candidata transparente e isolar essa hipótese, foram fixadas **antes da coleta** as referências experimentais Sref=1, Tref=40 requisições/s e Lref=0,1 s por API. Sref não mede CPU, recursos provisionados, energia ou capacidade máxima. Nenhuma referência é ajustada aos extremos observados. CPU e RSS permanecem como covariáveis brutas.

## 1. Das observações ao triângulo

Para cada serviço e janela: Δ>0 é a duração observada, N é o total de requisições concluídas, F é o subconjunto de falhas, e L é a média da duração das requisições concluídas na mesma população. As falhas já entram uma vez em N−F; não aplicar novamente a fração de sucessos.

    goodput = (N−F)/Δ
    quality = Lref/max(L,Lref)
    alpha_raw = (goodput/Tref)*quality
    S = Sref = 1
    P_raw = S*alpha_raw
    alpha = min(1,max(0,alpha_raw))
    P = P_restricted = S*alpha
    Q = sqrt(S−P)*sqrt(S+P)
    D = hypot(P−1,Q)
    theta = atan2(Q,P), quando S>0.

Identificador: `s-fixed-reference-quality-v3`. A escolha vem da candidata histórica de referência normalizada em `math/REFERENCE_TRIANGLE_REVIEW.md`, mas agora o corte é **intervenção declarada** para manter o domínio. O comparativo com CPU em `math/CPU_TRIANGLE_REVIEW.md` demonstrou que alterar S por uma razão de recursos não garantia coerência ou interpretação operacional. Não se adota uma fórmula de CPU nesta versão.

`P_raw`, `P_restricted`, `alpha_raw`, `alpha`, `restriction_delta=P−P_raw`, `clipping_applied`, `clipping_below_zero` e `clipping_above_one` ficam registrados, assim como as observações e referências. Por exemplo, 60 sucessos/s, latência abaixo de Lref, produzem P_raw=1,5 e P=1: o excesso 0,5 está preservado. Uma entrada direta P>S na função geométrica `triangle` é rejeitada; só o pipeline observacional aplica a restrição declarada.

Com N=0, a média L é indefinida. A versão v3 marca a janela como ociosa, mantém Sref disponível e deixa alpha/P/Q/D/onda ausentes; não inventa qualidade de serviço sem tráfego. Ausência de série não é zero tráfego. Falhas totais com N>0 e L válido produzem P=0,Q=S: isso é resultado da definição, não medição de perda física. Contagens inválidas, reinício de contador, duração não positiva e valores não finitos impedem o cálculo. CPU ausente não impede a geometria desta candidata, pois não integra suas fórmulas.

Q alto pode resultar de pouca demanda, de falhas, de penalidade de latência ou de suas combinações. Q não é uma medição independente de atrito. A média de latência não identifica caudas; os histogramas brutos da coleta devem permanecer disponíveis. Requisições `/health` e `/metrics` não integram a população de aplicação instrumentada; respostas 404 controladas entram no total e nas falhas, conforme o plano de coleta.

## 2. Propriedades e limites

Para alpha∈[0,1], P=S alpha garante 0≤P≤S. A identidade Q²=(S−P)(S+P)=S²−P² demonstra P²+Q²=S². A forma fatorada evita subtração direta de quadrados próximos; o teste numérico verifica o erro de arredondamento. S fixo força P e Q a percorrerem um arco. A redução de Q quando P aumenta é construída matematicamente, não uma anticorrelação operacional descoberta.

Com S=1, a amplitude é constante e a direção carrega toda a variação de cada par: P=cos(theta), Q=sin(theta), D²=2−2P. Assim, a superfície antes parametrizada por P,Q reduz-se a um arco unidimensional. A matriz [P,Q,D] ainda pode ter posto linear 3, pois Q e D são funções não lineares de P. Posto linear não é número de variáveis independentes da construção.

A referência geométrica desejada continua A=(1,0). No padrão geral S variável, o ponto de equilíbrio angular é (S/√2,S/√2). Para o S=1 desta candidata, ele coincide com B45=(1/√2,1/√2). Se usada a fronteira radial v2 com r=√(2−√2), **somente sobre este arco unitário** a condição D≤r equivale a P≥1/√2 e theta≤45°. O contraexemplo v2 (0,1;0,1) continua correto no quadrado geral, mas não pertence ao arco S=1. O pipeline v3 conserva D sem afirmar eficiência validada nem recalibrar automaticamente a fronteira.

O pipeline registra também `boundary_status` dentro/fronteira/fora/ausente como diagnóstico geométrico, com a tolerância absoluta anterior de 10⁻¹² em D. Quando L≤Lref, a fronteira equivale a goodput≥40/√2≈28,284271 req/s. Com 35 req/s e 20% de respostas não bem-sucedidas, goodput=28 req/s fica ligeiramente fora. Esse limiar é uma reexpressão da própria fórmula; não acrescenta um critério independente. Aumentar Q quando a demanda é baixa é imposto pela identidade, não evidência de desperdício.

S=0 é coberto no núcleo geométrico: P=Q=0 e fase ausente. Não é a referência operacional principal desta rodada, que fixa S=1. Para v3, D está em [0,√2]; P,Q estão em [0,1]. Nenhum desses limites estabelece capacidade real da aplicação.

## 3. Onda, matrizes e tensor

O tempo operacional de cada janela é mantido em seus timestamps. Dentro de cada janela, τ é um eixo separado de **codificação**:

    y(τ) = P sin(2πfτ) + Q cos(2πfτ)
         = S sin(2πfτ+theta).

Usa-se f=1 Hz apenas como portadora sintética, com 64 amostras uniformes em [0,1), sem duplicar o ponto final. A onda não é uma observação oscilatória do serviço. Para essa grade, B=[sin,cos] satisfaz BᵀB=32I e a média de y² é S²/2=0,5. O tensor de ondas tem eixos serviço × janela × fase, com 64 fases; sua matrização por fase tem posto no máximo 2. Gerar 64 pontos não cria 64 observações operacionais independentes.

Cada serviço tem uma matriz temporal com linhas [P,Q,D]. O tensor geométrico possui eixos serviço × (P,Q,D) × janela. Não se aplicam centralização ou reescala antes desta demonstração de SVD/HOSVD; trata-se de decomposição das coordenadas definidas, não de uma alegação de componentes causais ou de uma análise de correlação calibrada. As matrizes de observações brutas permanecem no CSV/JSON com unidades e população explícitas.

A SVD registra valores singulares, posto e erro de reconstrução. A HOSVD registra bases ortogonais, conservação de norma e erros completo/truncado. A truncagem usa postos no máximo (2,2,3), limitados pelas dimensões disponíveis; é uma demonstração de perda, não uma seleção validada de postos. A reconstrução completa verifica consistência numérica; sua precisão não valida a hipótese operacional.

Ausências são `null` no tensor exportado. As decomposições usam somente a interseção de janelas completas entre serviços, com índices incluídos/omitidos explícitos; não há preenchimento por zero. O pareamento é pelo índice do plano de carga, não pela suposição de timestamps exatamente iguais. Os timestamps preservados permitem auditar o desalinhamento temporal entre serviços. Duplicatas de serviço/janela são rejeitadas.

## 4. Entradas e proveniência

`pipeline.py` aceita o envelope `source_kind` e `rows` (ou `windows`). O adaptador reconhece os campos da coleta:

| Coleta | Campo canônico |
|---|---|
| service | service |
| window | window_index |
| completed / failed | completed / failed |
| mean_latency_seconds | latency_seconds |
| duration_seconds | duration_seconds |
| cpu_cores / rss_bytes | covariáveis sem alteração |
| start_utc / end_utc | timestamps originais |
| counter_reset | invalidação explícita |

Campos adicionais, inclusive `before`, `after`, histogramas e texto Prometheus, são preservados em `raw`. O arquivo de entrada é identificado por SHA256. `source_kind="synthetic"` identifica cenários modelados; `real_kubernetes_synthetic_workload` identifica medições reais de aplicações sintéticas no Kubernetes. Uma fonte histórica deve receber identificação histórica explícita e nunca ser apresentada como uma coleta atual. O modelo de origem não muda o fato de P,Q,D e ondas serem transformações experimentais.

O cenário sintético padrão contém duas APIs e dez janelas, taxas modeladas de 2 a 60 req/s, latências/erros controlados e CPU/RSS igualmente sintéticos. A janela de 60 req/s exercita o corte acima de Tref; ela não afirma que o cluster medido recebeu essa carga. A coleta real planejada usa suas próprias taxas e valores registrados. Não combinar os dois conjuntos como uma única amostra empírica.

## 5. Reprodução e validação

O núcleo `experiment.py` usa a biblioteca padrão e cobre 505 pares S/alpha. O pipeline usa NumPy 2.3.5, conforme `requirements.txt`, e gera SVGs sem dependência gráfica adicional.

```powershell
python -m pip install -r math/hypotenuse_lab/requirements.txt
python -m unittest discover -s math/hypotenuse_lab -p 'test_*.py' -v
python math/hypotenuse_lab/experiment.py
python math/hypotenuse_lab/pipeline.py
python math/hypotenuse_lab/pipeline.py --input evidence/hypotenuse-run/capture.json --out math/hypotenuse_lab/output/pipeline-observed
```

O último comando só pode ser executado quando o arquivo real existir e sua origem for verificada. Ele não inicia o cluster nem gera carga. Os resultados sintéticos ficam separados em `output/pipeline-synthetic`; os observados ficam no diretório explicitamente informado.

Artefatos: `results.json` (brutos, referências, cortes e estados), `windows.csv` (matriz tabular por janela), `matrices_tensors.json` (tensor com ausências, seleção de janelas, SVD/HOSVD e ondas), `temporal.svg`, `trajectory.svg`, `waves.svg`. Os testes cobrem extremos, ausência, inválidos, corte explícito, erros sem desconto duplicado, irrelevância da CPU para S nesta candidata, identidades, posto das ondas, energia do ciclo e reconstruções.

Uma rodada com poucas janelas e carga planejada não estima capacidade máxima nem eficiência populacional. Avaliações de correlação, efeitos externos e utilidade preditiva continuam no [plano de validação](PLANO_CORRELACAO.md), preservando a separação entre propriedades impostas pela fórmula e resultados observados.
