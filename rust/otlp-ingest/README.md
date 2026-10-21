# Wave: receptor OTLP/gRPC mínimo

Esta etapa prepara o ponto de entrada do futuro transmissor. O Collector é cliente
gRPC e chama `opentelemetry.proto.collector.metrics.v1.MetricsService/Export`;
este programa Rust é servidor. Não é uma assinatura nem consulta ao Collector.
Spans e transmissão contínua funcional serão evoluções separadas após validação.

Usa Tokio, tonic e prost, com tipos Protobuf oficiais pré-gerados por
`opentelemetry-proto=0.32.0`; não precisa instalar protoc nem inventar contrato.
As mensagens completas preservam Resource, scopes, timestamps, atributos,
histogramas e temporalidade. Nenhum cálculo de P/Q/S ocorre na ingestão.
Preservação é semântica dos campos conhecidos nessa versão: prost pode descartar
campos Protobuf desconhecidos ao decodificar. O journal não é captura byte a byte
do tráfego; evolução do contrato exige revisar a versão dos tipos gerados.

## Executar

```powershell
cd C:\Users\joaoplima\Documents\Aim\rust\otlp-ingest
cargo test --locked
$env:OTLP_JOURNAL = 'capture-001.otlp.frames'
cargo run --locked
```

Sem Rust no host, usar container (o comando grava target/ e Cargo.lock localmente):

```powershell
docker run --rm --mount "type=bind,source=$($PWD.Path),target=/work" -w /work rust:1.90-bookworm cargo test --locked
docker build -t wave-otlp-ingest:dev .
New-Item -ItemType Directory -Force data
docker run --rm -p 127.0.0.1:4317:4317 --mount "type=bind,source=$($PWD.Path)\data,target=/data" wave-otlp-ingest:dev
```

O processo recusa journal existente. Para outra execução forneça novo caminho
por `OTLP_JOURNAL`; não apague capturas para reiniciar. Dentro do container,
`OTLP_LISTEN=0.0.0.0:4317`; no host o padrão é loopback.

## Encaminhamento pelo laboratório

O lab existente coleta Prometheus/PostgreSQL e exporta snapshot Prometheus;
não possui saída OTLP automaticamente. O fragmento collector-export.example.yaml
mostra o exporter a adicionar em infra/collector.yaml, preservando os existentes.
Para Collector dentro do Minikube, o endereço precisa ser alcançável a partir do
pod: prefira Service do receptor dentro do cluster; para receptor no host, valide
a rota host.minikube.internal e firewall. localhost no pod não é o host Windows.
Não aplicar este fragmento isoladamente: ele não contém os receivers e credenciais
do laboratório. A implantação em homl deverá demonstrar Collector → Rust com
dados reais antes de aceitar a integração.

## Journal e semântica de aceitação

Cada frame é `[comprimento u32 little-endian][ExportMetricsServiceRequest protobuf]`.
Não é protobuf length-delimited varint, arquivo OTLP padrão nem ABI final.
O cabeçalho tem 4 bytes; limites de frame: 8 MiB. Lotes são serializados sob mutex;
ACK ocorre após write_all + sync_data. Uma falha desabilita novas escritas até
reinício com outro caminho, evitando continuar após frame potencialmente parcial.
Leitores devem detectar header/payload incompletos e preservar evidência.
Até 32 persistências pendentes são aceitas; excesso recebe UNAVAILABLE para retry.
A tarefa de persistência continua se a chamada gRPC for cancelada, evitando que
cancelamento interrompa uma gravação no meio e permita outra sobre frame parcial.

Não há deduplicação, replay, retenção ou garantia exactly-once. Queda entre gravação
e ACK pode gerar duplicatas por retry. sync_data não é garantia contra toda falha de
filesystem/host, nem sincronização da entrada de diretório. Não há autenticação/TLS;
esta configuração destina-se ao laboratório local e não deve ser exposta externamente.

Teste grpc.rs abre servidor/cliente gRPC reais em loopback, envia uma métrica
sintética com service.name e valor, decodifica o journal e compara a mensagem
completa. Verifica recusa de arquivo existente e de lote acima do limite.
Não confundir esse teste com coleta real do Minikube.

## Evolução condicionada à matemática

1. Preservar batches brutos e metadados de captura; construir janelas sem misturar
   cumulativos/deltas nem médias de percentis.
2. Gerar contrato de observações aceito pela análise matemática, com unidades,
   referências versionadas, valores ausentes e cobertura explícitos.
3. Comparar resultados Python/Rust em fixtures idênticas antes de definir ABI.
4. Adicionar recepção/geração/transmissão de spans e seu controle de fluxo em PR próprio.

A orientação matemática atual usa também D(t)=hypot(P(t)-1,Q(t)), com referência
(1,0). Esse índice pertence à análise derivada; não muda o contrato OTLP e não
deve ser confundido com uma métrica independente coletada dos containers.

Fontes: https://docs.rs/opentelemetry-proto/0.32.0/ e https://docs.rs/tonic/0.14.6/.
