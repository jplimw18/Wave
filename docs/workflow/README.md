# Fluxo de trabalho Wave

Project: https://github.com/users/jplimw18/projects/2
Repositório: https://github.com/jplimw18/Wave

## Estados e evidências

Cada entrega tem uma issue, adicionada ao Project em Triagem. A progressão é Triagem → Backlog → Análise → Implementação → Testes → Validação → Concluído. O estado Concluído exige critérios de aceite atendidos e evidências vinculadas. Issues ainda em descoberta permanecem em Análise; execução numérica não constitui prova matemática.

## Branches e PRs

1. Criar branch própria a partir de dev, com referência à issue.
2. Abrir PR para dev contendo problema, escopo, validação e limitações. Vincular a issue com `Refs #N`; não encerrar a validação teórica apenas porque uma implementação foi integrada.
3. Promover conjuntos revisados por PR dev → homl. Registrar execução no Minikube, versões, entradas, saídas e documentação.
4. Após aceite explícito, abrir PR homl → main. main representa o estado íntegro aceito. Não promover nem mesclar automaticamente.

O repositório estava vazio. O bootstrap criou somente README mínimo na main e originou homl/dev no mesmo commit; toda implementação subsequente deve seguir o fluxo acima. main, homl e dev exigem PR, inclusive para administradores. Force push e exclusão estão bloqueados. Não há checks obrigatórios nem número mínimo de aprovações: os gates de testes, aceite e direção das promoções continuam sendo exigências deste processo, ainda sem automação.

## Validação iterativa

O modelo matemático deve definir domínio, unidades, referências, dados ausentes, degenerações e distinção entre hipótese e identidade. Python verifica reconstrução, ortogonalidade, tolerâncias e casos adversariais. Dados sintéticos e observados devem ser identificados. A ingestão Rust preserva os envelopes OTLP e não fixa antecipadamente a ABI matemática.

Cada iteração deve registrar versão do modelo, dataset, comandos, tolerâncias, resultados e contraexemplos. A integração com o laboratório é uma etapa separada: o diretório AIM existente não foi importado integralmente para Wave e pode conter materiais e configurações que exigem revisão. A migração deve ser seletiva e sem segredos.

## Operação do Project

As issues iniciais foram adicionadas em Triagem. A movimentação subsequente exige evidência correspondente; não foi configurada automação de transição. Toda issue nova deve ser adicionada ao Project e triada. Dependências e aceite devem constar do corpo da issue ou PR.
