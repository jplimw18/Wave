# Fundação do extrator em Rust

## Base consolidada

Os PRs 10, 11, 12, 14 e 16 foram considerados aprovados pelo usuário e
integrados em dev. Conflitos de documentação mantiveram as variantes históricas;
o coletor conservou o suporte posterior a janelas de taxa zero. Nenhuma promoção
para homl ou main foi realizada. O PR 18 corrigiu o ACK de escrita do receptor:
write_all → flush → sync_data. O erro foi reproduzido antes e depois em tmpfs cheio.

A revisão independente executou 56 testes Python e os pipelines sobre as
capturas existentes. A skill the-judge produziu pareceres com evidência e gate;
o achado de perda de dados no receptor foi corrigido antes desta fundação.
A decisão de implementação em C++ foi cancelada pelo usuário; seguimos em Rust.

## Caminho dos dados nesta etapa

    Collector → OTLP/gRPC → receptor Rust → journal Protobuf
                                            ↓
                                  CLI decode-otlp → NDJSON com bytes e diagnóstico

    Captura de janelas JSON → adaptador tipado → núcleo matemático
                                                 ↓
                                      registros + matrizes P/Qv

São dois adaptadores explícitos. Não tratamos automaticamente um contador OTLP
como taxa nem inventamos a semântica de um Gauge. O receptor permanece ponto de
ingestão de métricas; spans e transmissão funcional contínua seguem como evolução.

## Contrato matemático preservado

Mantemos a candidata de atividade, com referências e brutos versionados:

    P = S0*clip(goodput/Tref * Lref/max(L,Lref),0,1)
    Q0 = sqrt(S0−P)*sqrt(S0+P)
    lambda_eff = (entradas + ativas_iniciais + fila_inicial)/Δ
    V = lambda_eff/(lambda_eff+k)
    Qv = V*Q0
    Sv = hypot(P,Qv).

Sem conclusões observadas, P=0 por regra explícita e latência/qualidade ficam
ausentes. Ausência de atividade não vira zero: V e Qv ficam ausentes quando não
há evidência suficiente. Pendências sem novas chegadas são preservadas no estado.
O núcleo também gera amostras por fase via wave_at_phase; não infere frequência
da aplicação. As classificações de eficiência continuam desabilitadas.

O replay conserva raw por registro; matrizes têm índices alinhados e máscara
de validade. Contagens fora da faixa exata de f64 são inválidas. Configurações
alteradas precisam de identificador de modelo próprio, impedindo mudar a
interpretação mantendo o mesmo rótulo de referência.

## Verificação e limites de implantação

Os testes de paridade comparam 40 observações de referência, 20 sintéticas e 20
medidas no Kubernetes, incluindo ociosidade, trabalho pendente e corte de P.
Status, ausências e estados são comparados exatamente; números usam tolerância
absoluta 1e−12 mais relativa 1e−10, conforme o contrato experimental anterior.
As referências medidas são históricas desta sessão de laboratório: estes testes
não produzem novas chamadas nem demonstram eficiência real.

Um teste integrado inicia gRPC em loopback, envia uma mensagem OTLP oficial,
verifica sua gravação e a lê na CLI. Outros casos cobrem frames incompletos,
payload inválido, tamanho máximo, saída existente e preservação de NaN/campos
desconhecidos nos bytes do journal. A saída não é publicada após erro de decode.

O ensaio local usa Rust 1.90 em Docker Linux. O workflow de CI executa fmt,
Clippy e testes com lockfile. Não foi validada implantação nativa Windows nem
conversão contínua das métricas OTLP do Minikube em janelas Rust. Essas são
etapas posteriores à fundação, com aceite e testes em homl.

## Próximas entregas delimitadas

1. Mapear métricas OTLP por identidade de recurso, scope e atributos, preservando
   unidades, temporalidade, timestamps e sinalização de resets.
2. Construir janelas por réplica e agregá-las por serviço com regras explícitas
   para trabalho que atravessa fronteiras, histogramas e sinais ausentes.
3. Implementar consumo contínuo do journal com cursor, detecção de truncagem e
   política de repetição; leitura de arquivo finito não substitui essa semântica.
4. Comparar janelas obtidas via OTLP com a captura do laboratório antes de
   habilitar cálculos em fluxo contínuo ou fixar uma ABI.

Referências técnicas consultadas:

- https://doc.rust-lang.org/cargo/reference/workspaces.html
- https://docs.rs/opentelemetry-proto/0.32.0/opentelemetry_proto/
- https://docs.rs/tempfile/latest/tempfile/struct.NamedTempFile.html#method.persist_noclobber
- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
