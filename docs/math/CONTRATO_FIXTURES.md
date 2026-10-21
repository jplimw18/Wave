# Contrato de observações para futura paridade Python/Rust

Este é um formato de fixtures de teste versionado, não uma ABI, wire protocol ou mudança no OTLP. O receptor Rust permanece responsável por preservar mensagens oficiais; este avaliador Python opera depois da extração de uma janela. A futura extração Rust deve produzir a mesma observação sem misturar transporte, agregação e cálculo de índices.

A cópia mínima histórica está em `math/pq_contract/fixtures/historical-windows.json`, tornando a demonstração reproduzível sem a pasta completa `evidence/`. É uma cópia byte a byte de `evidence/real-windows.json`, SHA256 `1312f0dee386181c8f597daf3fccba4abecdb407e50055b40fdc6edc4667f0ce`, documentada no STATUS original como coletada em 12/10/2026. A origem JSON contém relógio monotônico, sem timestamps UTC. O programa registra esse hash e não reclassifica essas janelas como coleta nova.

`math/pq_contract/fixtures.json` define dez cenários sintéticos. `pq_candidate.py` aplica a candidata de `FORMALISMO_PQ.md` e reanalisa separadamente as duas janelas históricas de `evidence/real-windows.json`. `output/candidate_results.json` contém entradas, referências e resultados, hash da origem histórica, data documental e indicação de que nenhuma coleta nova ocorreu. Valores históricos são medidas reais de aplicações sintéticas no laboratório.

## Campos e semântica

| Campo da observação | Unidade e regra |
|---|---|
| duration_seconds | segundos, finito e >0 |
| completed | inteiro ≥0, delta de concluídas da população definida |
| failed | inteiro entre 0 e completed, subconjunto de falhas |
| mean_latency_seconds | segundos, finito ≥0 ou null; mesma população |
| counter_reset | bool; true invalida a janela antes do cálculo |

Referências estritamente positivas: throughput_per_second, latency_seconds e error_fraction (fração, não porcentagem). Nesta candidata, pesos são fixos em 0,5/0,5; mudar pesos exige outro model_id. Identidade do serviço, janela, métricas OTLP, atributos, temporality e start/end timestamps pertencem ao registro de extração descrito em `PLANO_CORRELACAO.md`; o fixture numérico mínimo não substitui esses metadados.

Contadores cumulativos precisam de diferenças por identidade de série, com tratamento explícito de reset. Deltas OTLP não devem ser diferenciados novamente. Gauges não devem ser tratados como contadores. Histogramas devem preservar buckets e contagens antes de obter médias/quantis. O receptor ainda não implementa essa agregação por janela; o protocolo de equivalência começará pela fixture de observação e, em uma etapa posterior, por mensagens OTLP conhecidas que a gerem.

## Resultados e equivalência

Saída contém model_id, status, reason, P/Q/S/D/theta e componentes z_latency/z_error. D=hypot(P−1,Q) usa a referência fixa (1,0) e fica ausente se P ou Q estiver ausente. Estados são `ok`, `partial`, `missing` e `invalid`. Ausentes são JSON null; NaN/Infinity não são admitidos em JSON. Inputs não finitos em memória são rejeitados. Comparar status/reason/null exatamente; floats finitos por `abs(a-b) <= 1e-12 + 1e-10*abs(b)` no domínio dessas fixtures. A tolerância deverá ser revisada para outras escalas, nunca ampliada apenas para esconder divergência.

Casos cobertos: entrega sem erro; erro e latência juntos (P=0,8, Q=1, S=sqrt(1,64)); throughput acima da referência sem clamp; falhas totais; zero tráfego; contagens ausentes; latência ausente; reset; contagens inválidas. Testes adicionais verificam referências inválidas, overflow derivado e as janelas históricas. A extração e o cálculo futuro em Rust devem reproduzir essas semânticas; esta entrega não afirma paridade entre implementações ainda inexistentes.

Zero tráfego conserva P=0, mas Q/S/theta ficam ausentes. Sem contagens, P também é ausente. Latência ausente conserva P quando as contagens são válidas. Reset ou contagens inválidas não geram um zero válido. Para esta candidata de dois atritos, uma janela válida com tráfego sempre tem P>0 ou Q>0; a fase nula de S=0 é testada no laboratório algébrico separado.

## Executar

Com Python 3, da raiz do projeto:

```powershell
python -m unittest discover -s math/pq_contract -p 'test_*.py' -v
python math/pq_contract/pq_candidate.py
```

Este avaliador usa somente a biblioteca padrão. O experimento de decomposição em `math/harmonic_lab/` usa NumPy. Correlação estatística, extração OTLP e coleta longitudinal permanecem no plano; não são substituídas pelas fixtures.
