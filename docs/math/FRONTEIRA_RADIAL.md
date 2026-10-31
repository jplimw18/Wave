# Candidata v2: normalização e fronteira radial

A candidata `pq-bounded-radial-unit45-v2` aplica a nova convenção solicitada: **0≤P,Q≤1**, referência central A=(1,0) e fronteira circular baseada no equilíbrio trigonométrico de 45 graus. É uma regra geométrica para comparar distribuições relativas de entrega e atrito. Não usa máximos ou mínimos observados da série para escolher sua referência. A candidata anterior `pq-goodput-latency-error-v1`, sem limite superior para P/Q, permanece disponível com seus resultados originais.

## Hipótese que determina o raio

A igualdade P=Q define uma reta e uma direção de 45 graus quando P=Q>0. Não determina amplitude. Para fixar um ponto dessa reta, esta candidata assume explicitamente a **circunferência unitária** somente para a referência de equilíbrio:

    B = (cos(π/4), sin(π/4)) = (1/√2, 1/√2)
    A = (1,0)
    r = ||B-A||₂ = sqrt((1/√2−1)² + (1/√2)²)
      = sqrt(2−sqrt(2)) ≈ 0,7653668647301795.

As observações P,Q continuam no quadrado [0,1]²; não se exige P²+Q²=1 para cada janela. Se a hipótese fosse uma distribuição aditiva P+Q=1, o ponto equilibrado seria (0,5;0,5) e o raio seria 1/√2≈0,707107. Essas escolhas são distintas. A versão v2 adota a primeira, conforme a interpretação trigonométrica solicitada.

## Normalização com referências fixas

Defina clip(x)=min(1,max(0,x)). As referências Tref>0, Lref>0 e eref>0 são registradas antes da rodada e não são recalibradas por janela. A partir das contagens/latência válidas do contrato v1:

    P_raw = (N−F)/(Δ Tref)
    zL_raw = max(0, L/Lref−1)
    zE_raw = (F/N)/eref
    Q_raw = hypot(zL_raw,zE_raw)/sqrt(2)

    P = clip(P_raw)
    zL = clip(zL_raw)
    zE = clip(zE_raw)
    Q = clip(hypot(zL,zE)/sqrt(2)).

O atrito tem pesos iguais, 0,5/0,5. O corte ocorre **nos componentes antes da composição**; por isso Q não é, em geral, igual a clip(Q_raw). Por exemplo, zL_raw=3,zE_raw=0 produz Q=1/√2, enquanto clip(Q_raw)=1. Essa diferença é deliberada e faz parte do `model_id` v2. O corte final de Q apenas protege o limite superior contra arredondamento; a norma ponderada já pertence a [0,1] em aritmética exata.

O código preserva observações, referências, P_raw/Q_raw/S_raw/D_raw e, para cada componente normalizado, `raw`, `value`, `below_zero`, `above_one` e `clipped`. Também registra `raw_q_above_one` e `clipping_applied`. O excesso acima da referência fica visível nesses campos. Duas entradas diferentes podem gerar o mesmo índice limitado; os brutos são indispensáveis para distinguir a severidade.

A função de corte suporta os dois sentidos. Entretanto, contagens ou latências fisicamente inválidas continuam sendo rejeitadas pelo contrato; não são corrigidas artificialmente para zero. O componente de excesso de latência já é não negativo por definição. Ausências propagam-se: não são valores zero e não provocam redistribuição dos pesos.

## Distância, amplitude e classificação

    S = hypot(P,Q)
    D = hypot(P−1,Q)
    D² = S²−2P+1.

Embora P,Q estejam em [0,1], **S e D podem chegar a √2**. A fase é theta=atan2(Q,P) para S>0 e fica ausente em S=0. Os valores geométricos não representam energia ou trabalho físico.

A classificação ideal é D≤r como região geometricamente eficiente segundo esta convenção e D>r como região externa. A implementação registra a fronteira separadamente usando uma tolerância **absoluta de 10⁻¹² nas unidades adimensionais de D**:

| Condição numérica | `boundary_status` | `geometrically_efficient` |
|---|---|---|
| D−r < −atol | `dentro` | true |
| abs(D−r) ≤ atol | `fronteira` | true |
| D−r > atol | `fora` | false |
| P ou Q ausente | `ausente` | null |

A faixa de tolerância absorve diferenças de arredondamento e inclui valores ligeiramente acima do raio. Não é intervalo de confiança nem tolerância para erro de medição. `boundary_delta=D−r` permite inspecionar a distância assinada à fronteira. A regra rejeita pares fornecidos fora de [0,1] antes da classificação; a etapa de normalização precisa ser explícita.

## Casos que distinguem geometria de comportamento operacional

| Ponto | D | Classificação | Interpretação limitada |
|---|---:|---|---|
| Ideal (1,0) | 0 | dentro | Referência escolhida |
| B=(1/√2,1/√2) | r | fronteira | Equilíbrio unitário de 45 graus |
| Repouso geométrico (0,0) | 1 | fora | Não é avaliação de uma janela sem tráfego |
| (1,1) | 1 | fora | Ambos os índices no limite superior |
| (0,1) | √2 | fora | Maior distância no quadrado |
| (0,1;0,1) | sqrt(0,82)≈0,905539 | fora | Também tem theta=45 graus |

Assim, pertencer à região circular **não equivale a theta≤45 graus**. O par P=Q=0,1 demonstra que o ângulo sozinho não determina a distância. O significado de "eficiente" permanece geométrico e condicionado às fórmulas e referências adotadas.

Outro efeito verificável: no eixo Q=0, a região aceita P≥1−r≈0,234633, considerando o domínio quadrado e sem a faixa numérica. Portanto, uma entrega normalizada relativamente baixa pode estar dentro. Isso decorre da fronteira solicitada e deve ser confrontado com objetivos operacionais externos; não deve ser ocultado por recalibração posterior.

Na coleta, N=0 é registrado como `operational_state="ocioso"`, P=0, Q ausente, classificação ausente. Já o ponto matemático completo (0,0) pode ser classificado como fora. Manter essa distinção evita inventar Q=0 para decidir sobre uma janela ociosa.

## Matrizes, tensores e movimento

Cada linha temporal continua sendo [P(T),Q(T),D(T)]. O tensor tem eixos serviço × (P,Q,D) × tempo; preserve também os tensores de valores brutos e as máscaras/indicadores de corte. O posto linear de [P,Q,D] pode ser 3, embora D seja uma função dos outros dois índices. Não se passa a ter três graus de liberdade independentes.

Registrar ΔD e ΔD/ΔT entre janelas válidas do mesmo serviço/execução. Valores negativos indicam aproximação de A; positivos indicam afastamento. A passagem de uma classe para outra pode decorrer de comportamento, mudança de referências ou corte; compare os brutos e mantenha referências fixas. A referência circular não altera os limites de identificabilidade da curva harmônica ou da HOSVD.

## Implementação e reprodução

`math/pq_contract/bounded_candidate.py` implementa a normalização, preservação dos brutos e classificação. `bounded_fixtures.json` contém nove cenários de observação e seis pontos geométricos. O programa reanalisa também as duas janelas históricas preservadas, sem coleta nova. Os resultados ficam em `output/bounded_candidate_results.json`, separados da v1.

`math/harmonic_lab/boundary_demo.py` gera somente trajetórias sintéticas, um gráfico do quadrado/círculo/B e outro de D ao longo das janelas com o raio marcado. O CSV `boundary_windows.csv` conserva P,Q,D, movimento e classe por janela. Os gráficos mantêm a mesma escala visual nos eixos P e Q.

```powershell
python -m unittest discover -s math/pq_contract -p 'test_*.py' -v
python -m unittest discover -s math/harmonic_lab -p 'test_*.py' -v
python math/pq_contract/bounded_candidate.py
python math/harmonic_lab/boundary_demo.py
```

Nenhum desses testes demonstra eficiência real. O plano de validação deve comparar classe, distância e cortes com entrega útil/latência/recursos medidos externamente, sob demanda e configuração controladas, incluindo os casos limítrofes e as janelas ociosas.
