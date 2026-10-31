# Plano de correlação por serviço e validação iterativa

**Rodada adicional v2:** aplicar o contrato da [fronteira radial](FRONTEIRA_RADIAL.md), mantendo a v1 como comparação. Fixar Tref/Lref/eref antes da rodada; conservar valores brutos e indicadores de corte. Avaliar separadamente as classes dentro/fronteira/fora/ausente e o estado ocioso. Incluir o ponto unitário B45, casos P=Q de amplitudes diferentes, extremos do quadrado e passagens pela fronteira. A fronteira circular é uma hipótese de classificação; confrontá-la com os resultados externos definidos neste plano. Comparar desempenho dos modelos sobre valores brutos, índices limitados e indicadores de corte para quantificar a perda por saturação. Não usar os máximos/mínimos da série para ajustar a referência de equilíbrio.

Estado desta entrega: inspeção de arquivos e experimentos matemáticos locais. Nenhuma nova coleta de cluster foi feita por esta frente. `README.md` e `STATUS.md` registram o laboratório validado em 12/10/2026; o estado de execução atual precisa de verificação operacional separada. O código local mostra APIs api-a/api-b, PostgreSQL e Collector com receivers Prometheus/PostgreSQL. Não há kubeletstats no manifesto inspecionado.

## 1. Inventário e população

| Fonte verificada nos arquivos | Uso possível | Limite que deve acompanhar a análise |
|---|---|---|
| `aim_http_requests_total{service,route,status}` | Concluídas, falhas e vazão útil por janela | Definir `/work` ou outra população explícita; health/metrics não são carga útil |
| `aim_http_request_duration_seconds_{sum,count,bucket}` | Média e histograma de duração por serviço/rota | O timer termina antes da escrita da resposta; não é latência completa medida pelo cliente |
| `aim_db_operations_total{service}` | Operações bem-sucedidas do cliente de banco | Não somar com requisições HTTP como se fossem trabalhos independentes |
| `process_cpu_seconds_total` | CPU do processo instrumentado | Não representa todo o cgroup/pod, nem CPU do PostgreSQL |
| Receiver PostgreSQL no Collector | Métricas do banco observáveis no snapshot | Confirmar nomes/unidades efetivamente exportados e reset de estatísticas |
| Requests/limits no manifesto/pod | Configuração e estratificação | Não são uso, capacidade medida ou métricas dinâmicas |

Antes de cada rodada registrar endpoints/séries disponíveis, permissões de leitura, identidade de pod/container/imagem e versão do manifesto. Leitura de README não substitui `docker version`, estado do perfil minikube e pods Ready. Executar esses checks na frente operacional e anexar a evidência ao run_id.

A coleta histórica `scripts/collect-window.py` soma todas as rotas instrumentadas e usa duas capturas instantâneas. Ela não registra relógio civil por janela, indicadores de reinício dos contadores ou distinção entre ausência da série e zero na soma. É adequada como evidência histórica limitada; uma coleta longitudinal deve corrigir essas limitações. Os contadores são atualizados em momentos próximos, mas não numa transação única de coleta: avaliar inconsistências de contagem em fronteiras e tolerâncias justificadas, sem truncar diferenças silenciosamente.

## 2. Registro canônico

Salvar uma linha por serviço, réplica e janela antes de agregar. Campos mínimos: `run_id`, `source_kind` (real ou `synthetic`, para sintético), `service`, `service_type`, `route_scope`, `pod_uid`, `container_id`, `start_utc`, `end_utc`, `duration_seconds`, `restart_count_before/after`, contadores/histogramas antes/depois, unidade, escopo da CPU, recursos solicitados e limites (`requests/limits`), taxa oferecida (`offered_rate`), concorrência, tamanho do conteúdo da requisição, versão e indicadores de ausência/reinício dos contadores.

Salvar separadamente `model_id`, Tref/Lref/eref, pesos, política sem tráfego, política de resets, versão de extração, conjunto usado para calibração e hash da entrada. Registrar P, cada z_k, Q, S, D, theta, razões e flags, mantendo brutos. D é a distância euclidiana à referência fixa (1,0). Organizar linhas temporais [P,Q,D] e tensor serviço×(P,Q,D)×tempo; preservar também matrizes/tensores de métricas brutas. Candidatas diferentes são colunas/modelos diferentes. Escalas e pesos não podem ser modificados após observar o teste para melhorar correlações.

Para várias réplicas, primeiro obter deltas válidos por réplica, depois somar contagens e CPU; formar taxas com janelas alinhadas. A média de latência é soma dos deltas de duração dividida pela soma das contagens. Somar deltas dos buckets compatíveis antes de estimar quantis; não fazer média de percentis de réplicas. O cálculo de quantis por histograma e suas limitações estão na [documentação oficial do Prometheus](https://prometheus.io/docs/practices/histograms/).

## 3. Hipóteses testáveis

H1: P acompanha entrega útil medida por um cliente independente sob demanda e payload controlados. Como P contém sucessos do servidor, correlação com o mesmo contador de sucessos é tautológica e serve apenas para consistência, não validação.

H2: Q aumenta em intervenções que elevam atrito operacional e melhora a discriminação de violações externas de latência/erro além de demanda, CPU e P. Latência/erro usados para formar Q não são critérios independentes; usar observação externa ou resultado futuro em janela separada, declarando a ligação conceitual.

H3: modos reduzidos de X/A retêm informação suficiente para a tarefa externa com erro e estabilidade aceitáveis em dados não usados no ajuste. A métrica de sucesso deve ser escolhida antes: por exemplo, erro de previsão de latência do cliente ou discriminação de um episódio injetado. Reconstrução e diagnóstico são avaliações distintas.

H4: a codificação senoidal não melhora informação disponível sobre o baseline (P,Q), pois é determinística e reversível somente nesses dois coeficientes. Qualquer ganho de um algoritmo sobre ondas precisa ser comparado com o mesmo algoritmo ou capacidade equivalente sobre P,Q, e com métricas brutas.

H5: D e ΔD descrevem aproximação/afastamento da referência (1,0); testar se esse movimento coincide com o resultado externo desejado, inclusive no regime P>1. Plotar trajetória PQ com sequência temporal e ponto de referência marcado, e D ao longo das janelas com lacunas visíveis. A associação D-desfecho é hipótese empírica; a identidade D²=S²−2P+1 é somente uma propriedade construída.

## 4. Rodadas planejadas

1. **Qualidade de dados.** Sem tráfego, carga baixa e reinício controlado apenas quando autorizado operacionalmente. Confirmar contagens servidor/cliente, timestamps, sobreposição de janelas, lacunas e resets. Validar invariantes 0≤F≤N, Δ>0, histograma consistente e IDs estáveis. Não inferir ausência de erro de uma série faltante.
2. **Calibração separada.** Degraus de taxa oferecida e concorrência, payload fixo, aquecimento excluído com regra prévia. Escolher Tref de um regime explicitamente definido; o máximo de carga ritmada observado não prova capacidade. Fixar Lref/eref/pesos e escala das métricas antes de usar os dados de teste.
3. **Comparação sob controle.** Repetir cada configuração em ordem aleatorizada, com réplicas de execução. Variar um fator por vez inicialmente: demanda, payload, atraso do banco e custo CPU. Em seguida usar desenho fatorial para separar interações. Registrar carga do host e dependência compartilhada entre api-a/api-b/PostgreSQL; serviços no mesmo host não são réplicas experimentais independentes.
4. **Estabilidade e generalização.** Reservar execuções e períodos completos para teste. Repetir sob configurações de recursos explicitamente registradas. Não embaralhar janelas adjacentes entre treino e teste; ajustar centralização, normalização, seleção de features, ranks e pesos apenas no treino, com seleção no conjunto de validação.
5. **Critério de decisão.** Manter o modelo simples se Q ou decomposição não acrescentarem utilidade externa reproduzível. Publicar resultados negativos, sensibilidade a pesos/referências, incerteza e dados ausentes. Nenhum critério de aprovação é apenas obter triângulo válido ou reconstruir a própria onda.

Proposta inicial de janela: 30 s com coleta a cada 5 s, mais sensibilidades 15/60 s, sem sobreposição na análise principal. São escolhas de desenho a testar, não parâmetros já validados. Janela maior reduz resolução temporal e pode esconder episódios curtos. Guardar o histórico de scrapes permite recalcular. Não fixar n arbitrário como garantia de significância: após piloto, estimar variabilidade entre execuções e dimensionar repetições para a precisão/efeito mínimo definido.

## 5. Análise de associações

Calcular por serviço e regime Pearson para associação linear e Spearman para monotonia, exibindo dispersão e número de janelas válidas. Variáveis constantes e pares sem suporte suficiente recebem NA. Guardar matriz de número de observações por par; comparação de correlações calculadas em populações diferentes exige cautela. Explorar defasagens predefinidas com fronteiras de execução preservadas; escolher a melhor defasagem em todos os dados introduz seleção otimista.

Controlar taxa oferecida, concorrência, payload e configuração por estratificação ou regressão previamente definida; comparar estimativas ajustadas e brutas. Relações não lineares exigem inspeção dos resíduos e modelos com validação separada. Corrigir a multiplicidade de pares/defasagens explorados ou tratar a análise explicitamente como exploratória, confirmando depois em rodada nova.

Janelas próximas são autocorrelacionadas. Para intervalos de confiança, reamostrar execuções independentes quando houver quantidade suficiente; para séries longas dentro de execução, usar blocos contíguos com comprimento escolhido por diagnóstico de dependência e sensibilidade. Não tratar cada ponto da senoide sintetizada como nova observação experimental. Se houver apenas duas janelas históricas, não produzir p-valores ou conclusão de correlação útil.

Uma correlação alta entre S e P ou Q decorre parcialmente de S=hypot(P,Q). Uma correlação entre CPU e throughput pode refletir demanda. Correlação cruzada com atraso não estabelece que um serviço causou o outro. Para afirmar efeito causal das intervenções, são necessários desenho, controles, replicação e limites de generalização explícitos.

## 6. Comparações mínimas e artefatos por rodada

Comparar métricas brutas normalizadas; P isolado; (P,Q); (P,Q,D); D isolado e ΔD/Δt; (S,theta); S isolado; SVD e HOSVD truncadas. (S,theta) e (P,Q) contêm a mesma informação quando S>0 e a fase está definida. S e D isolados perdem direção. D não adiciona informação independente a P,Q, mas sua transformação não linear pode mudar a aproximação por modelos lineares. Incluir ablação de cada componente de Q e de P_quality para detectar dupla ponderação da mesma falha.

Artefatos esperados: inventário da infraestrutura; dados e referências imutáveis; tabela de qualidade/ausência; gráficos por serviço e regime; correlações com incerteza; curvas de erro por rank; erros por métrica e anomalia; resultados em teste; relatório de sensibilidades. Fixar semente para sintéticos, registrar versões e identificar cada gráfico como real, histórico ou sintético. Resultados desta entrega ficam em `math/harmonic_lab/`, sem sobrescrever `evidence/`.

## 7. O que as evidências históricas permitem agora

`evidence/real-windows.json` contém uma janela por API, documentada como coletada em 12/10/2026 no STATUS. O JSON contém instantes monotônicos, não registros de tempo UTC; a data vem da documentação histórica. As durações são aproximadamente 10 s. As aplicações executam cargas sintéticas, embora os contadores sejam medições reais do laboratório.

Com Tref=100/s e Lref=0,1 s (referências artificiais anteriores), ambas têm erro zero e média abaixo de Lref. Portanto, para a candidata de dois atritos deste documento, Q=0, P é aproximadamente 0,247921 para api-a e 0,245946 para api-b, S=P, theta=0, e D=1−P (aproximadamente 0,752079 e 0,754054). Isso mostra o comportamento da definição; não significa ausência de custo, fila, cauda de latência ou atritos não instrumentados. Nenhuma escolha de eref>0 altera esses dois Q porque e=0. Como há somente uma janela por serviço, não há ΔD temporal real disponível.

As duas janelas não identificam relação temporal, tensor representativo, peso ótimo ou correlação populacional. O exemplo histórico também não pode justificar uma previsão de comportamento fora da carga leve observada. Mais amostras artificiais da curva não aumentam o tamanho dessa amostra empírica.
