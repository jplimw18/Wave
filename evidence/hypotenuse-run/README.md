# Coleta do laboratório para a variante S como hipotenusa

Execução local: **30/10/2026, 23:54:48–23:55:39, America/Sao_Paulo**.
O JSON registra UTC: 31/10/2026, 02:54:48–02:55:39. Dados novos, distintos
das duas janelas históricas de 12/10. Workloads sintéticos reais no Kubernetes,
não números inventados para o gráfico.

Perfil aim-lab, Kubernetes 1.35.0, Minikube 1.39.0, Docker Engine 29.6.2;
api-a/api-b, PostgreSQL 17.4 e Collector contrib 0.147.0 existentes, sem upgrade.
Inicialização retomou containers e PVC existentes. Nenhum dado anterior apagado.

## Arquivos

- capture.json: 20 observações reais, snapshots Prometheus completos das APIs
  antes/depois, contadores, histogramas, CPU/RSS de processo, resultados HTTP do
  cliente e snapshot final do Collector; envelope identifica origem explicitamente.
- reference.json: referências experimentais fixadas antes da coleta, não calibradas
  para melhorar os resultados: S=1, Tref=40 req/s, Lref=0,1s.
- audit.json: verificações de contagens, integridade e continuidade dos pods.
- pods-before.json/pods-after.json e workloads.txt: evidências locais de identidade,
  reinícios, readiness, imagens e limites. Não contêm valores do Secret do banco.

## Procedimento e limites

scripts/capture-hypotenuse.py roda por kubectl exec em api-a e gera carga HTTP
nas duas APIs simultaneamente. Dez janelas por serviço, duração nominal 5 s, taxas
alvo 2, 8, 16, 25, 35, 35, 25, 16, 8, 2 req/s. Alguns períodos usam deliberadamente rota
inexistente para produzir 404; isso não reproduz falha interna de produção.
Inicializa séries 200/404 antes das janelas. Health e metrics não entram nos
contadores de requisições. A carga /work insere eventos sintéticos no PostgreSQL.

A auditoria encontrou 1.720 conclusões, 110 erros 404 deliberados, 0 falhas de transporte,
0 resets e 0 reinícios durante captura. Contagens do cliente coincidem com deltas
do servidor em todas as janelas. Snapshots individuais não são transações atômicas;
o cliente sequencial termina as operações antes de cada snapshot.

A latência registrada é a do timer instrumentado no servidor, não fim a fim.
CPU/RSS são do processo Python, não consumo total do pod. Não foi instalado
kubeletstats nem coletada banda. O cliente e os serviços compartilham o nó;
a taxa alvo não é benchmark de capacidade. O snapshot Collector verifica presença
das fontes, não equivalência temporal exata entre scrapes. Não coletamos spans.

O pipeline matemático transforma observações já coletadas. S=1 é referência
geométrica fixa, não medida de provisionamento ou energia. Q é residual:
baixo tráfego pode resultar em Q alto mesmo sem erros. Essas saídas não são
validação operacional de eficiência. PostgreSQL é dependência observada,
não uma terceira série de trabalho útil com contrato próprio nesta rodada.

## Recuperação necessária antes da coleta

Docker estava parado e falhou ao iniciar por sockets AF_UNIX inacessíveis.
O encerramento normal falhou; encerramos somente processos Docker da tentativa
travada e renomeamos reversivelmente pastas de sockets para backups:

- AppData/Local/Docker/run-wave-backup-20261030
- AppData/Local/Docker/run-wave-backup-20261030-retry
- AppData/Local/docker-secrets-engine-wave-backup-20261030

Nenhum reset de fábrica, alteração de configuração, remoção de volume ou imagem.
O comportamento corresponde ao relato no projeto Docker:
https://github.com/docker/desktop-feedback/issues/531.
Após recuperação, aguardamos pods e CoreDNS Ready antes da coleta definitiva.
A primeira tentativa de coleta falhou antes de gerar janelas por DNS ainda em
inicialização; nenhum arquivo parcial foi publicado como captura válida.

