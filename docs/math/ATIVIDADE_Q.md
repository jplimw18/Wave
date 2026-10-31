# Ponderação de Q pela atividade — matriz de duas colunas

Modelo experimental `activity-pending-attenuation-v4`, separado da variante
de hipotenusa fixa. Nesta construção a amplitude EFETIVA deixa de ser S0.
Q0 e Qv são resíduos geométricos; nenhum deles mede diretamente desperdício.

## Definição

Mantemos S0=1, Tref=40 chamadas/s e Lref=0,1 s da rodada anterior.
Com N conclusões, F falhas e duração Δ, goodput=(N−F)/Δ. Quando N>0 e
a latência média L está disponível:

    alpha_raw = goodput/Tref * Lref/max(L,Lref)
    alpha = min(1,max(0,alpha_raw))
    P = S0*alpha
    Q0 = sqrt(S0−P)*sqrt(S0+P).

Preservamos alpha_raw, P bruto, P restrito e a intervenção do corte. Para N=0
observado e válido, P=0 por regra explícita de entrega zero; latência e fator de
qualidade ficam ausentes, não são preenchidos com zero. Dados ausentes ou
contadores inválidos não constituem uma janela ociosa válida.

Chamadas recebidas não equivalem a conclusões nem sucessos. Para considerar
trabalho iniciado anteriormente, usamos uma intensidade de atividade:

    lambda_eff = (received_delta + active_start + queued_start)/Δ
    V = lambda_eff/(lambda_eff+k), k=5 chamadas/s
    Qv = V*Q0
    Sv = hypot(P,Qv).

Entradas, tarefas ativas e fila devem ter escopos conhecidos. active_start e
queued_start devem ser conjuntos disjuntos. A fórmula inclui trabalho carregado
da janela anterior: lambda_eff não é estritamente uma taxa de chegadas. O parâmetro
k é experimental, fixado antes da coleta; não foi ajustado aos resultados.
Calcular V como 1/(1+k/lambda_eff), com V=0 em lambda_eff=0, evita overflow
desnecessário na soma do denominador. Se faltar uma entrada necessária, V é
ausente. Sem disponibilidade/coleta confirmada, não se assume V=0.

## Geometria e prova

Para 0≤P≤S0 e 0≤V≤1:

    Sv² = P² + V²*Q0² = P² + V²*(S0²−P²)
    P² ≤ Sv² ≤ S0²
    P ≤ Sv ≤ S0.

Em V=1 recuperamos Sv=S0; em V=0 temos Qv=0 e Sv=P. Se P=0 também,
Sv=0 e a fase é indefinida. Não atribuímos eficiência perfeita a esse estado.
Quando S0=0, P=Q0=Qv=Sv=0 para qualquer V válido.

Por janela real t, a portadora de codificação usa um tempo sintético τ:

    yv(τ;t)=P(t)*sin(2π*τ)+Qv(t)*cos(2π*τ)
    theta_v=atan2(Qv,P), para Sv>0
    yv=Sv*sin(2π*τ+theta_v).

A portadora de 1 Hz é escolhida para codificação, não descoberta nos dados.
Em 64 fases uniformes de um ciclo, a média de yv² é Sv²/2. Isso é energia
quadrática matemática, não consumo de energia da infraestrutura.

## Matriz e tensor

Cada serviço fornece M[t,:]=[P(t),Qv(t)], uma matriz n×2. O tensor de análise
é X[serviço,coordenada,janela], com coordenadas P e Qv. As decomposições SVD
e HOSVD completas verificam reconstrução, norma e ortogonalidade dos fatores.
Janelas ausentes são preservadas como null e explicitamente excluídas da
decomposição comum; não são preenchidas com zeros. A versão truncada mede
seu erro, sem promessa de reter anomalias ou obter o melhor diagnóstico.

Guardar também S0,Q0,V, raw e flags. Se S0 é conhecido e Q0>0, V pode ser
recuperado de Qv/Q0. Em Q0=0, todos os V produzem Qv=0; se S0 não é conhecido,
diferentes pares Q0,V podem gerar a mesma matriz. Mesmo com S0 conhecido, P
não recupera separadamente contagens, erros e latência que foram agregados.

## Ociosidade e trabalho pendente

O estado `ocioso_no_handler` exige disponibilidade e scrapes válidos, entradas,
ativas e fila iguais a zero nos escopos declarados, além de zero conclusões e
falhas. Se contagens contradizem atividade zero, V/Qv ficam ausentes. A atividade
final ausente impede declarar ociosidade; V ainda pode ser calculado quando
todos os componentes iniciais da intensidade são conhecidos, com estado indeterminado.

Uma chamada pendente sem chegadas não é ociosidade: em Δ=5s, active_start=1
produz lambda_eff=0,2 e V≈0,03846. O valor pequeno mostra que esta ponderação
NÃO garante, sozinha, destaque para bloqueios. O estado e os sinais de trabalho
pendente devem permanecer disponíveis. As classificações de eficiência ficam
`nao_avaliada`: a fronteira radial anterior não é automaticamente transferida
para esta geometria de amplitude variável.

## Rodada real e limites

31/10/2026, 00:33:02–00:33:52 em São Paulo: 20 janelas de duas APIs,
quatro ociosas no handler, 1.310 entradas/conclusões e 102 respostas 404
provocadas. Sem falhas de transporte, resets ou reinícios durante a captura.
As entradas são medidas por contador próprio; não inferidas de sucessos.
Fila de negócio igual a zero é uma característica explícita do código desta
aplicação, sem observação do backlog TCP. Trabalho pendente sem novas chegadas
é caso sintético dos testes, não uma falha induzida no Kubernetes nesta rodada.

As referências originais em evidence/activity-run/reference.json foram gravadas
antes da coleta sob nome provisório activity-q-v1. O identificador v4 nomeia
esta implementação final das mesmas fórmulas e parâmetros; o arquivo original
não foi alterado retroativamente. Captura, proveniência e auditoria ficam separadas
das transformações calculadas. Ver math/activity_lab/README.md para reprodução.
