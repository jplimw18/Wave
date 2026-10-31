# Rodada com controle de atividade V

Coleta nova em **31/10/2026, 00:33:02–00:33:52, America/Sao_Paulo**.
Os arquivos registram UTC: 03:33:02–03:33:52. São métricas medidas em aplicações
sintéticas reais no Kubernetes, não valores gerados para formar uma curva.

## Instrumentação e mudança no laboratório

O Docker e o perfil Minikube aim-lab já estavam disponíveis. Acrescentamos ao
handler HTTP das duas APIs:

- `aim_http_received_requests_total`: entradas no handler.
- `aim_http_active_requests`: chamadas em andamento no handler, incluindo espera
  pela conexão/operação no banco e escrita da resposta.

`/metrics` e `/health` não entram nessas métricas. A chamada ativa é decrementada
em bloco `finally`. Construímos `aim-api:activity-v1` e atualizamos somente api-a
e api-b, aguardando os novos pods ficarem prontos. PostgreSQL, PVC e Collector
foram preservados. Os reinícios do rollout ocorreram antes da captura; não houve
reinícios durante as janelas auditadas.

O manifesto base ainda menciona `aim-api:lab-v1`; esta execução usou override de
imagem. Para reproduzir a instrumentação, construir explicitamente a nova tag e
usar `kubectl --context aim-lab -n aim-lab set image deployment/api-a api=aim-api:activity-v1`
e o equivalente para api-b. O arquivo images-before.txt registra as tags anteriores.
Restaurar essas tags é uma operação reversível; nenhum rollback foi executado
automaticamente após o teste.

## Coleta

`scripts/capture-activity.py` usa o helper `scripts/capture-hypotenuse.py`.
Copiar os dois para o mesmo diretório temporário de api-a e executar o primeiro.
Ele gera dez janelas nominais de 5 segundos para cada API, simultaneamente.
Taxas alvo: 0, 2, 8, 16, 25, 35, 35, 8, 2, 0 chamadas/s. Algumas janelas usam
rota inexistente para provocar 404. `/work` grava eventos sintéticos no banco.
Não houve reset nem remoção de eventos antigos.

Resultados auditados: **20 janelas, 4 ociosas, 1.310 entradas e conclusões,
102 respostas 404 deliberadas, zero falhas de transporte e zero reinícios**.
Em todas as janelas, deltas de entradas e conclusões coincidem com as respostas
observadas pelo cliente. Novas métricas também aparecem no snapshot Collector.

`capture.json` conserva todos os snapshots, contadores, histogramas, CPU/RSS de
processo, disponibilidade nos limites, plano de carga e respostas do cliente.
`audit.json` resume a auditoria; pods-before/after identificam instâncias e reinícios.

## Referências fixadas antes da coleta

`reference.json` declara S0=1, Tref=40 req/s, Lref=0,1 s e k=5 req/s.
O modelo calcula atividade efetiva como
`(received_delta + active_start + queued_start)/duration_seconds` e usa
`V=lambda_eff/(lambda_eff+k)`. A atividade efetiva não é apenas taxa de chegada:
inclui uma contagem de trabalho já pendente no início da janela.

O pipeline Python, em diretório separado, calcula P, Q0, V, Qv e Sv. Os dados
originais são preservados; ociosidade não é ausência de telemetria. Não avaliar
eficiência de atendimento nas janelas ociosas.

## Limites observacionais

- A aplicação não tem uma fila assíncrona de negócio. `queued_start/end=0` é uma
  declaração arquitetural explícita, não uma métrica inferida de série ausente.
- Backlog TCP, rede e demanda anterior à entrada no handler não são observados.
  A classificação é de ociosidade no escopo do handler, não prova de ausência de
  demanda externa global.
- Probes e chamadas ativas são amostradas nos limites; não há disponibilidade
  contínua nem contagem de rejeições antes do handler.
- Todas as chamadas do cliente encerraram antes do snapshot final. Um bloqueio
  sem chegadas novas é cenário dos testes sintéticos, não injetado nesta rodada.
- CPU/RSS são do processo; não coletamos banda nem kubeletstats nesta etapa.
- A primeira tentativa de copiar scripts selecionou um pod antigo terminando,
  foi abortada antes da carga. A execução definitiva selecionou um pod novo pronto.
- A matriz [P,Qv] não recupera V e Q0 isoladamente. Preservar esses metadados.
- A nova hipotenusa é Sv=hypot(P,Qv); S0 deixa de ser a amplitude efetiva após a
  ponderação. Nenhuma classificação geométrica prova eficiência operacional.
