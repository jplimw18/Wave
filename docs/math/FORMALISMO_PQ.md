# P e Q independentes de S: contrato e decomposição

**Nova candidata v2:** [normalização e fronteira radial](FRONTEIRA_RADIAL.md) fixa P,Q em [0,1], conserva valores anteriores ao corte e classifica D em relação ao raio sqrt(2−sqrt(2)), centrado em (1,0). As fórmulas observacionais sem limite superior descritas abaixo são a v1 preservada para comparação. As identidades geométricas e os limites de identificação continuam aplicáveis; a classificação de eficiência é uma convenção adicional, não uma consequência dessas identidades.

Esta proposta sucede os experimentos de `math/README.md`, sem apagar suas hipóteses ou resultados. A independência aqui é **de definição**: P e Q são calculados das métricas, sem usar S; depois S=hypot(P,Q). Não se afirma independência estatística entre P e Q. Compartilhar erros, latência, demanda ou infraestrutura geralmente os torna dependentes.

## 1. Contrato por serviço e janela

Para serviço s e janela j com duração Δ>0, conservar contagens brutas, timestamps, identificador do experimento e referências versionadas. Definir N como requisições concluídas na mesma rota/população, F como falhas, 0≤F≤N, T=N/Δ, e=F/N quando N>0. Escolher antes do teste Tref>0 e Lref>0 por serviço. São referências operacionais, não uma capacidade física automaticamente conhecida.

Uma candidata inicial simples de entrega útil normalizada é

    P = (N-F)/(Δ Tref).

P não é limitado a 1. Não multiplicar novamente por (1-e), pois os sucessos já descontam falhas. Uma candidata distinta, a comparar por ablação, conserva a penalidade de latência dos experimentos anteriores:

    P_quality = P * Lref/max(L,Lref),

onde L é uma estatística de latência declarada (primeiro a média, disponível no histórico). P_quality e P são modelos diferentes; não alternar conforme o resultado. Se a utilidade significa cumprir um prazo, uma medição direta de sucessos dentro do prazo é preferível, mas exige histograma conjunto de estado e latência ou registros por requisição. O histograma atual não tem rótulo de estado e não permite obter exatamente essa interseção.

Construir um vetor de atritos não negativos z e pesos a_k≥0, soma a_k=1, fixados no treino:

    z_latency = max(0, L/Lref - 1)
    z_error   = e/eref                         (eref>0)
    Q = sqrt(sum_k a_k * z_k²).

Primeira candidata reproduzível: somente esses dois componentes, a_latency=a_error=0,5. eref é uma escala positiva de erro, não precisa ser um SLO tolerado. Não usar zero como denominador mesmo que a meta de erro seja zero. O excesso positivo é uma transformação declarada: latências abaixo de Lref têm o mesmo componente zero; conservar a latência bruta. Como alternativa de sensibilidade, testar L/Lref sem corte em outro model_id.

CPU, memória, filas, espera, retries e throttling podem ser canais adicionais quando medidos e definidos. CPU alta sozinha não demonstra atrito; trabalho útil também consome CPU. Uma razão de custo CPU por sucesso requer sucessos>0, uma referência de custo independente e o mesmo escopo de processo/container. Nunca interpretar request de CPU como teto nem converter ociosidade automaticamente em desperdício. Até validar esses canais, mantê-los como covariáveis externas e não incluí-los em Q.

Por fim, para P,Q finitos:

    S = hypot(P,Q)
    D = hypot(P-1,Q)
    theta = atan2(Q,P), se S>0
    theta = ausente, se S=0.

Para estes índices P,Q≥0, theta pertence a [0,π/2]. A álgebra posterior vale também para coeficientes reais com sinais; esse domínio mais amplo é matemático, sem interpretação automática de entrega negativa.

**Ausências:** N=0 produz P=0 como contagem útil observada; e e latência são ausentes, portanto o Q de dois componentes e a curva ficam ausentes. Isso difere explicitamente do contrato histórico que deixava P ausente sem tráfego. Não confundir ausência de tráfego com ausência de scrape. Não substituir um componente ausente por zero nem renormalizar pesos silenciosamente. Reset de contador, mudança de pod, Δ inválido e valores não finitos invalidam a janela afetada; guardar motivo e dados brutos. Um Q com outro subconjunto exige outro model_id.

## 2. O triângulo e o que ele não demonstra

S²=P²+Q² e P≤S seguem da definição para P,Q≥0, inclusive se P>1. Não há aqui o problema de domínio Q=sqrt(S²-P²) quando S era imposto pela CPU ou por referências. Essa resolução é algébrica: não confirma nenhuma lei física nem a hipótese histórica.

S pode crescer porque houve mais entrega ou mais atrito. Logo não é uma escala de saúde ordenada. P/S (S>0) é somente uma razão geométrica; P=0,1,Q=0 e P=10,Q=0 têm a mesma razão. Para demonstrar eficiência seria necessário definir trabalho útil e recursos gastos, medir a relação sob carga comparável e confrontar um critério externo. Se P e Q compartilham erro/latência, sua correlação pode ser parcialmente construída pelas fórmulas.

### Terceira métrica: distância ao ponto de referência (1,0)

Por orientação explícita do usuário, a referência de eficiência máxima proposta é **(P0,Q0)=(1,0)**. Adota-se a distância euclidiana no plano dos índices normalizados:

    D(j) = sqrt((P(j)-1)² + Q(j)²).

Usar `hypot(P-1,Q)` evita quadrados intermediários desnecessários. D≥0; D=0 se e somente se P=1 e Q=0. Para o ponto geométrico de repouso (0,0), D=1. Isso não força Q=0 numa janela sem tráfego: no contrato observacional Q está ausente e D também. A referência é a especificada, sem substituí-la por uma referência estimada depois dos resultados.

P=1 significa atingir Tref de entrega útil na candidata simples. Logo o significado da referência depende de Tref e da fórmula de P. O termo "máxima" expressa a referência desejada; não demonstra um ótimo físico. Por exemplo, P=2,Q=0 dá D=1: uma entrega acima da referência se afasta geometricamente, embora possa ser operacionalmente desejável. Não ordenar eficiência apenas por D sem validar esse comportamento e declarar a interpretação.

Uma expansão direta prova **D²=S²−2P+1**. A desigualdade triangular e sua reversa entre origem, referência e (P,Q) dão **|S−1|≤D≤S+1**. D não é um terceiro grau de liberdade independente; é uma transformação não linear de P,Q e não recupera métricas já descartadas.

Para janelas ordenadas em tempo operacional T_j, registrar D_j, ΔD_j=D_j−D_(j−1) e vD_j=ΔD_j/(T_j−T_(j−1)), com denominador positivo. ΔD<0 indica aproximação à referência e ΔD>0 afastamento; zero só informa distância constante, permitindo movimento tangencial. Registrar também ΔP,ΔQ, tempo decorrido e lacunas. Não calcular diferenças entre serviços, resets ou execuções diferentes. Se qualquer ponto for ausente, a diferença correspondente é ausente.

Quando P e Q são diferenciáveis e D>0, Ddot=((P−1)Pdot+Q Qdot)/D. Em D=0 essa fórmula é indefinida e D pode não ser diferenciável; preferir diferenças discretas para janelas observadas. A fase interna τ da onda não é o tempo operacional T_j usado para medir movimento.

A matriz temporal proposta é **M_j,:=[P(T_j),Q(T_j),D(T_j)]**, uma linha por janela. As colunas originais não são ortogonais em geral. Sua SVD produz bases ortonormais. O tensor correspondente é **A_PQD[serviço, métrica∈{P,Q,D}, tempo]**. Conservar separadamente o tensor A de métricas brutas e suas máscaras. Uma matriz [P,Q,D] pode ter rank linear 3, embora a superfície parametrizada tenha dimensão intrínseca no máximo 2: por exemplo as linhas (0,0,1), (1,0,0), (1,1,1) são linearmente independentes. O limite rank≤2 da matriz de ondas abaixo não se aplica à matriz aumentada por D.

## 3. Curva como codificação de duas coordenadas

Usar τ como coordenada de fase **interna à janela**, para não confundi-la com o tempo operacional j. Com ω>0 fixo e conhecido:

    b(τ) = [sin(ωτ), cos(ωτ)]ᵀ
    c = [P,Q]ᵀ
    y(τ) = b(τ)ᵀc = S sin(ωτ+theta).

A identidade vem de sin(a+b)=sin(a)cos(b)+cos(a)sin(b), com P=S cos(theta), Q=S sin(theta). Para S=0, a curva é zero para qualquer fase; fase não é identificável. Frequência e origem da fase são metadados indispensáveis para recuperar P e Q. A frequência escolhida para codificar índices não mede periodicidade do serviço.

Se P(j) e Q(j) mudarem entre janelas, a expressão é uma família de curvas. Concatená-las pode criar saltos artificiais; não inferir espectro físico, energia ou causalidade dos saltos. Uma única senoide por janela é uma escolha de representação.

### Rotação e produtos internos

    R(theta) = [[cos(theta), -sin(theta)],
                [sin(theta),  cos(theta)]]
    c = R(theta)[S,0]ᵀ,
    RᵀR=I, det(R)=1.

A verificação decorre de cos²+sin²=1 e cancelamento dos termos cruzados. R preserva norma e produto interno; é uma matriz ortogonal. Os vetores unitários sin/cos são ortogonais sob o produto interno de ciclo completo

    <f,g> = (2/Tcycle) integral_0^Tcycle f(τ)g(τ)dτ,
    Tcycle = 2π/ω.

Neste produto, <sin,sin>=<cos,cos>=1 e <sin,cos>=0. Portanto <y,y>=P²+Q². Na média temporal usual, mean(y²)=S²/2 e RMS(y)=S/sqrt(2). Essa energia quadrática é matemática, não energia de hardware.

### Amostras e projeção

Com n amostras, B tem colunas sin(ωτ_i) e cos(ωτ_i), e y=Bc. Para τ_i=i*Tcycle/n, i=0,...,n-1, n≥3, BᵀB=(n/2)I. Então H=sqrt(2/n)B tem **colunas ortonormais**, mas não é matriz ortogonal quadrada quando n>2. Recupera-se c=(2/n)Bᵀy; Π=HHᵀ é o projetor ortogonal no subespaço das duas colunas.

Em amostragem geral, usar c_hat=argmin ||Bc-y||₂, resolvido por QR ou SVD, e registrar posto e condicionamento. A recuperação única exige rank(B)=2: duas fases cuja diferença não seja múltiplo de π bastam sem ruído. Amostras repetidas ou separadas por meio ciclo podem dar rank=1. Instantes quase degenerados ampliam ruído. Não usar a fórmula 2/n fora de uma grade que satisfaça a identidade. Um resíduo pequeno contra uma onda gerada dos próprios P,Q verifica implementação, não adequação a medições externas.

## 4. Matrizes de métricas e de ondas são objetos distintos

X∈R^(J×K) pode organizar janelas de um serviço nas linhas e K métricas normalizadas nas colunas. Centralização/escala são ajustadas apenas no treino, preservando parâmetros e máscara de ausências. Coluna constante não tem correlação definida; removê-la da análise de correlação com motivo explícito. Para comparar serviços, tratar o tipo de serviço como estrato ou incluir efeitos por serviço; misturar suas escalas pode inverter associações.

A SVD é X=UΣVᵀ. Na forma completa U e V são ortogonais quadradas; na forma reduzida têm colunas ortonormais. Valores singulares são não negativos. X_r=U_rΣ_rV_rᵀ tem erro de Frobenius ao quadrado igual à soma dos σ_i² descartados, para a SVD ordenada. Colunas de V são direções em métricas, não causas. A implementação usa a convenção `U, sigma, Vh` do [NumPy](https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html).

Já uma matriz de ondas Y, com uma linha por serviço/janela e n fases fixas, satisfaz Y=CBᵀ, C contendo apenas P e Q. Logo rank(Y)≤2. Decompor Y em muitos modos independentes não recupera informação descartada antes em P,Q. Comparar esse baseline de rank 2 com a SVD dos dados brutos normalizados evita atribuir riqueza artificial à senoide.

## 5. Tensores e HOSVD

Guardar o tensor de entrada A[s,m,j] com eixos **serviço × métrica × janela**, unidades originais, máscara de presença e referências separadas. Métricas que não existem para PostgreSQL não viram zeros. Primeiro usar um subconjunto comum válido ou tensores separados por família; modelos específicos de dados ausentes são uma etapa adicional. Uma célula é uma observação ou estimativa declarada, não um ponto arbitrário da senoide.

Na HOSVD completa, obter U_s,U_m,U_j como bases ortogonais das matrizações em cada modo. Definir

    G = A ×₁ U_sᵀ ×₂ U_mᵀ ×₃ U_jᵀ
    A = G ×₁ U_s  ×₂ U_m  ×₃ U_j.

O produto ×_k multiplica as fibras do eixo k pela matriz indicada. Com bases completas, as duas operações se cancelam em cada modo e preservam a norma de Frobenius. A reconstrução é exata em aritmética exata; a diferença computada deve ser compatível com precisão numérica. G não é, em geral, uma diagonal de tensor. A construção multilinear e suas propriedades são descritas por [De Lathauwer, De Moor e Vandewalle (2000)](https://epubs.siam.org/doi/10.1137/S0895479896305696).

Na HOSVD truncada conservar r_s,r_m,r_j colunas por modo e reconstruir A_hat. Medir ||A-A_hat||F/||A||F, erro por métrica/serviço/regime e qualidade fora do treino. Se ||A||F=0, registrar erro absoluto zero e razão relativa ausente. A truncagem não é garantia de melhor aproximação multilinear global nem de retenção de anomalias raras. Erro de reconstrução baixo também não garante previsão ou diagnóstico útil.

Uma versão de ondas W[s,j,i]=P[s,j]sin(ωτ_i)+Q[s,j]cos(ωτ_i) tem rank do modo fase no máximo 2. Esse tensor codifica somente dois coeficientes por par serviço/janela. O tensor A de métricas permanece necessário para investigar suas relações.

### Não unicidade e não identificabilidade

Mesmo com A conhecido, trocar simultaneamente sinais de fatores e núcleo preserva reconstrução; valores singulares repetidos permitem rotações dentro do subespaço degenerado. Um Tucker geral permite rotações ortogonais compensadas no núcleo. Não há interpretação causal única dos fatores apenas por impor ortogonalidade.

Com apenas c=W x, W∈R^(2×K), K>2, rank(W)≤2, existe direção não nula v com Wv=0. Logo x e x+v produzem P,Q e a curva iguais. Exemplo: W=[[1,0,0],[0,1/2,1/2]], x=[1,2,4], x'=[1,3,3]. Ambos produzem P=1,Q=3; diferem nas métricas 2 e 3. Para a Q de norma ponderada, também há muitas combinações com a mesma norma. Mais amostras da mesma curva não resolvem essa perda.

## 6. Escopo dos testes

`math/harmonic_lab/` contém uma demonstração separada, com dados sintéticos, de rotação, amostragem, SVD, HOSVD, trajetória PQ, distância D e perda de identificação. `math/pq_contract/` implementa a candidata de P,Q acima, deriva S,D,theta e reaplica offline as duas janelas históricas. Testes algébricos aprovados estabelecem coerência numérica. A validação empírica proposta está em `PLANO_CORRELACAO.md` e continua necessária para dar significado operacional aos índices.
