# Validação desta etapa

Execução local em Docker Desktop Linux, imagem rust:1.90-bookworm
(digest sha256:3914072ca0c3b8aad871db9169a651ccfce30cf58303e5d6f2db16d1d8a7e58f).
Rust não foi instalado no host; rustfmt/clippy foram adicionados ao container
descartável. Cargo.lock conserva as dependências resolvidas.

Comando executado no container:

```sh
rustup component add rustfmt clippy
cargo fmt
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
```

Resultado: teste de integração gRPC aprovado (1 teste, 0 falhas); compilação do
binário e biblioteca aprovadas; Clippy finalizado com exit code 0 sem warnings.
Não há unit tests adicionais; não contar os alvos com zero testes como evidência.

O teste usa porta efêmera loopback, servidor tonic e cliente OTLP reais, métrica
sintética `test.cpu.cores=0.25`, resource `service.name=api-a`, timestamp conservado.
Compara protobuf decodificado do journal à mensagem original, recusa journal
existente e verifica que lote acima de 8 MiB não altera o arquivo.

Não foi executada homologação Collector → Rust dentro do Minikube. O perfil
aim-lab foi consultado e estava Stopped nesta sessão. Não há nova captura real,
teste de carga, validação de cancelamento/falha de disco, TLS, spans ou ABI final.
O teste numérico de P/Q/D é separado e não é comprovado pelo sucesso gRPC.
