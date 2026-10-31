# Atenuação por atividade: P e Qv

Esta variante mantém metadados S0/Q0/V e produz matriz temporal [P,Qv], tensor
serviço×2×tempo e ondas com amplitude efetiva Sv. Fórmulas, prova e limites:
[ATIVIDADE_Q.md](../../docs/math/ATIVIDADE_Q.md).

## Executar da raiz

Usar Python 3.11+ e ambiente isolado com NumPy fixado:

```sh
python -m pip install -r math/activity_lab/requirements.txt
python -m unittest discover -s math/activity_lab -p 'test_*.py' -v
python math/activity_lab/pipeline.py
python math/activity_lab/pipeline.py --input evidence/activity-run/capture.json --out math/activity_lab/output/real
```

Dependências locais reutilizadas, sem executar as demonstrações antigas:
math/hypotenuse_lab/experiment.py e math/harmonic_lab/harmonic_lab.py.
O primeiro contém a geometria da hipotenusa; o segundo contém HOSVD.
Executar os testes desta pasta em processo Python separado das outras variantes,
que usam nomes de módulos de demonstração semelhantes.

## Artefatos

- output/synthetic: 20 janelas modeladas, incluindo ociosidade, corte de P e
  trabalho pendente sem novas chegadas.
- output/real: 20 janelas medidas no Kubernetes, incluindo quatro ociosas.
- results.json preserva metadados, raw, V, Q0, Qv, S0 e Sv.
- windows.csv traz resultados por serviço e janela.
- matrices_tensors.json contém matrizes n×2, tensor 2×2×10, fatores avaliados
  por erros de ortogonalidade/reconstrução e tensor de ondas 2×10×64.
- activity.svg, trajectory.svg e waves.svg mostram valores e proveniência.
  Os PNGs são renderizações dos mesmos SVGs para visualização no chat.

O caso de ociosidade válida resulta em P=0, Q0=1, V=0, Qv=0 e Sv=0.
Isso remove o residual da representação efetiva, mas não declara eficiência.
Não aplicar automaticamente o raio da variante de hipotenusa fixa.

## Verificação executada

12 testes aprovados: geometria (176 combinações S0/alpha/V), extremos e fase
nula, dados inválidos/ausentes, ociosidade, trabalho pendente sem chegadas,
contadores contraditórios, cortes, identificabilidade, decomposição e gráficos.
O caso de contagens contraditórias garante que atividade zero não atenue Q
artificialmente quando há conclusões incompatíveis com esses sinais.

| Resultado | Sintéticos | Medições novas do Kubernetes |
|---|---:|---:|
| Registros | 20 | 20 |
| Ociosos no handler | 2 | 4 |
| Pendentes sem novas chegadas | 2 | 0 |
| Matriz por serviço | 10×2 | 10×2 |
| Tensor | 2×2×10 | 2×2×10 |
| Erro relativo HOSVD completa | 4,11×10⁻¹⁶ | 5,44×10⁻¹⁶ |
| Erro relativo HOSVD truncada | 42,11% | 28,97% |

Os erros de truncagem pertencem à aproximação experimental de ranks (2,1,3).
Ela não é usada para substituir o tensor completo nem para afirmar retenção
de toda a informação. As ondas têm 64 fases por janela; a diferença máxima
entre sua média quadrática e Sv²/2 foi 1,11×10⁻¹⁶ na rodada real.

A coleta real ocorreu em 31/10/2026, 00:33:02–00:33:52 em São Paulo. Entradas e
conclusões totalizaram 1.310, incluindo 102 respostas 404 provocadas, sem falhas
de transporte, resets ou reinícios durante captura. Ver evidências e escopo em
[README da coleta](../../evidence/activity-run/README.md).
