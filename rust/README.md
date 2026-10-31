# Fundação Rust do Wave

Workspace com três responsabilidades:

| Pacote | Responsabilidade |
|---|---|
| wave-otlp-ingest | Receber ExportMetricsServiceRequest por OTLP/gRPC e persistir journal |
| wave-extractor-core | Validar observações e calcular P, Q0, V, Qv, Sv e matrizes |
| wave-extractor | CLI de replay de capturas e decodificação do journal |

O cálculo é síncrono e separado do transporte Tokio. O receptor não conhece as
fórmulas. O núcleo não depende de gRPC, rede ou arquivos. A CLI combina os adaptadores.

## Compilar e testar

Da pasta rust, com Rust 1.90:

```sh
cargo test --workspace --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo fmt --all -- --check
```

Também é possível executar esses comandos na imagem Docker rust:1.90-bookworm,
montando o repositório inteiro em /work e usando /work/rust como diretório de
trabalho. Os testes de paridade leem os arquivos de referência em math/.
Este desenvolvimento foi executado no Docker Linux a partir do Windows.
Compilação nativa Windows ainda não foi validada. MSYS2 e g++ não são requisitos.

## Replay das observações reais

```sh
cargo run --locked -p wave-extractor -- replay ../evidence/activity-run/capture.json replay.json
```

A saída conserva source_kind, metadados de entrada e raw de cada observação,
além de resultados tipados. Cada serviço produz uma matriz de colunas P/Qv,
alinhada pela união dos índices de janela, com valid_mask. Linhas incompletas
ficam [null,null] na matriz; valores parciais conhecidos permanecem no registro.
Uma linha ociosa válida [0,0] não é tratada como ausência.

O arquivo de saída deve ser novo. Ele é preparado em arquivo temporário no
mesmo diretório e publicado somente ao finalizar, sem substituir um existente.
Falhas de leitura/decode não publicam uma saída parcial. As garantias finais
de persistência e publicação dependem do filesystem; não há promessa exactly-once.

## Ler o journal OTLP

Com o receptor encerrado e o journal disponível:

```sh
cargo run --locked -p wave-extractor -- decode-otlp metrics.otlp.frames metrics.ndjson
```

Formato do journal aprovado: comprimento u32 little-endian seguido do payload
ExportMetricsServiceRequest. Cada frame tem no máximo 8 MiB. EOF no início de
um frame termina normalmente; header ou payload incompleto é erro. O comando
é leitura finita, não acompanhamento contínuo nem API de assinatura.

Cada linha NDJSON contém protobuf_base64, que conserva exatamente o payload do
journal, e diagnostic_request, uma projeção dos campos conhecidos. A projeção
NÃO é autoritativa: JSON pode representar doubles NaN/Infinity como null e tipos
gerados podem ignorar campos desconhecidos. Use os bytes Protobuf para consumir
os valores. Esta projeção não é o contrato OTLP/HTTP JSON. A preservação é do
journal de entrada; o receptor atual já decodifica/reencoda os campos conhecidos
antes de gravá-lo, conforme suas limitações documentadas.

Não há conversão automática de batches OTLP arbitrários para janelas de cálculo.
A próxima etapa deve definir identidade, nomes/unidades das métricas, deltas de
contadores, resets, limites temporais e agregação por réplica antes desse cálculo.

## Referências e compatibilidade

O model_id padrão activity-pending-attenuation-v4 usa S0=1, Tref=40 chamadas/s,
Lref=0,1s e k=5 chamadas/s. Uma configuração JSON opcional pode ser passada como
quarto argumento do replay; modificar referências exige outro model_id.
Ver config.example.json. O núcleo limita S0 a [0,1] e exige referências positivas.

Capturas devem conter source_kind e rows não vazios; cada linha deve identificar
service e window/window_index inteiro não negativo. Contagens precisam ser
inteiros finitos representáveis exatamente até 2^53−1. Tipos incorretos no JSON
rejeitam a captura; valores numéricos inválidos ou ausentes recebem estados
explícitos por observação. A ausência de counter_reset mantém a convenção falsa
do modelo Python; fontes operacionais devem fornecer essa informação.

O adaptador trabalha com observações já agregadas em um escopo de serviço.
Pares service/window duplicados e source_kind divergente são rejeitados, sem
misturar namespaces ou réplicas silenciosamente. Timestamps e demais identidades
originais permanecem em raw; este código não agrega métricas de múltiplos pods.

Cargo.lock nesta pasta governa o workspace. otlp-ingest/Cargo.lock permanece
para o Dockerfile de contexto isolado do receptor, que não copia o workspace.
Os dois contextos preservam as dependências do receptor aprovadas na revisão.

Esta é uma API interna Rust e uma saída JSON versionada; não uma ABI final.
A matriz não recupera as métricas agregadas. V não substitui estado operacional,
Qv não mede desperdício físico e efficiency_assessment permanece nao_avaliada.
SVD/HOSVD e aprendizagem continuam no laboratório Python, não foram portadas
como parte desta fundação. Ver ../docs/extractor/FUNDACAO_RUST.md.

