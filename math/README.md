# Nucleo experimental C++

**Nova iteração P,Q,D:** [formalismo e decomposição](../docs/math/FORMALISMO_PQ.md), [plano de correlação](../docs/math/PLANO_CORRELACAO.md) e [fixtures de observações](../docs/math/CONTRATO_FIXTURES.md). P e Q são definidos independentemente de S; S=hypot(P,Q) e D=hypot(P−1,Q), com referência fixa (1,0). Matrizes temporais [P,Q,D], tensores serviço×métrica×tempo e plots sintéticos estão em [harmonic_lab](harmonic_lab/README.md). A candidata observacional está em `pq_contract/`. As seções abaixo preservam o histórico anterior, em que S era imposto e P>S podia invalidar o triângulo; não descrevem a nova hipótese.

Terceira hipotese, experimental e separada: [CPU utilizada/request na hipotenusa](CPU_TRIANGLE_REVIEW.md), com nova coleta emparelhada e grade de 720 casos.

Experimento posterior, separado e sem substituir o baseline: [hipotenusa construida com referencias Tmax/Lmax](REFERENCE_TRIANGLE_REVIEW.md). Inclui comparacao real/sintetica, cortes explicitos, calibracao ilustrativa e limites de garantia.

## Hipotese atualizada do usuario: triangulo de dominio restrito

O usuario definiu posteriormente **S=C/100 como hipotenusa**, P como cateto adjacente, Q como cateto oposto derivado e `y(t)=P*sin(omega*t)+Q*cos(omega*t)`. O campo `Result.s` e as evidencias usam S; a notacao inicial A representa o mesmo valor numerico. Q nao e medicao independente de perdas.

`triangle(S,P)` retorna Q somente se P<=S; senao preserva S/P, retorna `compatible=false` e Q ausente. Nenhum clamp e aplicado. Para dominio valido, Q=sqrt(S^2-P^2) e amplitude resultante hypot(P,Q)=S. A implementacao usa a forma numericamente mais estavel sqrt(S-P)*sqrt(S+P). Isto testa a hipotese, sem estabelecer relacao fisica ou demonstrar que dados reais respeitam seu dominio.

`triangle_sample` recebe frequencia positiva explicitamente. `sample-triangle.py` conserva S/P/Q, compatibilidade, frequencia, taxa de amostragem, duracao, indice, tempo e valor por janela. O experimento sintetico foi executado com **f=1 Hz, 32 amostras em 1 s**, parametros escolhidos somente para teste; o usuario ainda nao definiu frequencia nem amostragem finais. Janelas incompatíveis conservam linhas com y/Q vazios. Nao ha substituicao por outra onda.

```powershell
wsl -d lab-ubuntu -- sh -lc 'cd /mnt/c/Users/joaoplima/Documents/Aim && python3 scripts/sample-triangle.py --frequency-hz 1 --samples 32 --duration-seconds 1 --output evidence/triangle-samples.csv'
```

O arquivo `triangle-samples.csv` e sintetico; a CLI aplica a verificacao do dominio tambem a janelas reais. Dentro do dominio, (P,Q) recupera S, mas nao Lreal/Treal/E separadamente. A frequencia escolhida nao mede periodicidade da aplicacao.

Autorizacao de escopo ampliada durante a configuracao: testar somente as formulas propostas e explorar uma codificacao senoidal. Nenhuma LSTM, teoria de energia eletrica ou conclusao estatistica foi implementada.

`aim_metrics.hpp` e uma biblioteca header-only C++17 independente. `experiment.cpp` executa testes sinteticos e uma varredura de latencia; opcionalmente recebe uma janela real na CLI. O Collector continua sendo componente Go independente; nenhuma extensao C++ foi embutida nele. Integracao inicial: exportar janelas brutas para arquivo, calcular indices offline com C++, conservar as entradas. As transformacoes numericas propostas nao foram colocadas no pipeline de coleta.

## Contrato de entrada

- C: CPU percentual com denominador explicito `cpu_reference_cores` e descricao; exemplo `100 * delta process_cpu_seconds / (delta wall_seconds * 1 core)`. Um core e referencia de consumo, nao capacidade maxima da aplicacao. C pode superar 100.
- Lreal: media em segundos das duracoes de TODAS as requisicoes de aplicacao completadas na janela, inclusive falhas. Manter tambem histograma bruto para investigacao futura; esta escolha de media e operacional e precisa ser validada pelo grupo.
- Treal: total de requisicoes completadas / segundos de janela, incluindo erros. Nao usar somente sucessos.
- E: 100 * falhas / total. Nesta API sintetica, status diferente de 200 e falha.
- Lmax > 0 e Tmax > 0 configuraveis; ambos sao referencias experimentais, nao limites descobertos automaticamente.

A biblioteca recebe contagens e duracao, derivando Treal e E para evitar desconto duplo de erros. As entradas originais e referencias ficam em `Result.raw`/`references`. Ausencia e representada por `std::optional`, nunca por zero implicito. Sem trafego: Treal=0, NL/E/P indefinidos (NA); A ainda pode ser observado. Com CPU ausente, P ainda pode ser calculado, mas A e a onda nao. Referencias invalidas, janela nao positiva, numeros nao finitos, valores negativos e falhas acima do total sao rejeitados.

## Formulas e variantes

```
A = C / 100
NL = Lmax / max(Lreal, Lmax)
P_gradual = NL * (Treal / Tmax) * (1 - E / 100)
P_cut = Lreal > Lmax ? 0 : P_gradual
```

NL e qualidade preservada, nao degradacao crescente. Latencia bruta nunca e cortada; a violacao e sinalizada. O corte tem descontinuidade no limite e perde a severidade acima dele: 0,2 s e 1 s viram o mesmo P_cut=0. A variante gradual os distingue. Tambem perde distincao abaixo de Lmax via NL=1; preservar Lreal e necessario. P nao e limitado a 1: Treal=200/s, Tmax=100/s, E=0 e Lreal<=Lmax produzem P=2. Nenhuma variante limitada foi adicionada. P>S e possivel. A raiz do triangulo e calculada somente no dominio P<=S; fora dele a hipotese e sinalizada como incompatível.

## Alternativa computacional inicial, separada da hipotese do usuario

A opcao abaixo foi explorada ANTES da definicao de S como hipotenusa. Permanece apenas como alternativa para discussao e teste de reversibilidade de coordenadas; **nao e a formulacao atual do usuario** e nao substitui janelas incompatíveis do triangulo.

Uma opcao computacional reversivel para **duas coordenadas derivadas** e:

```
y(t) = A*cos(2*pi*f*t) + P_gradual*sin(2*pi*f*t)
R = hypot(A, P_gradual)
phi = atan2(P_gradual, A)
y(t) = R*cos(2*pi*f*t - phi)
A = R*cos(phi); P_gradual = R*sin(phi)
```

f=1 Hz nos testes e uma escolha sintetica de codificacao, nao frequencia inferida das metricas e nao evidencia de periodicidade da aplicacao. R e norma do vetor (A,P), nao potencia aparente fisica. P>A nao cria impossibilidade. Quando ambos sao zero, fase=0 por convencao (fisicamente nao identificavel).

Guardar R e phi recupera A/P ate precisao numerica; guardar so R perde direcao, guardar uma amostra perde informacao, e amostragem com fase/frequencia desconhecidas pode causar ambiguidade. Nem mesmo (A,P) recupera as quatro metricas: latencia/throughput/erro se combinam em P, e varias entradas produzem o mesmo resultado. Portanto isto nao demonstra compactacao sem perda das metricas originais. Manter brutos/referencias/flags e necessario. Concatenar ondas entre janelas tambem pode criar saltos artificiais; nao se implementou sinal temporal continuo.

Alternativas para discutir: manter o vetor (A,P) sem onda; manter (R,phi) com f fixo e metadados; usar canais separados para preservar mais coordenadas. Nao escolher frequencia por throughput nem fase por erro sem justificativa adicional. Os testes sao de coerencia algebrica e comportamento de borda, nao validacao cientifica de correlacao ou de capacidade preditiva.

## Reproduzir

Compilacao no WSL e independente de Docker; arquivos continuam no projeto Windows:

```powershell
wsl -d lab-ubuntu -- sh -lc 'cd /mnt/c/Users/joaoplima/Documents/Aim && sh scripts/test-math.sh'
```

Compila com g++ C++17, `-Wall -Wextra -Werror -pedantic -O2`. Evidencias: `evidence/math-tests.txt`, `evidence/math-sweep.csv`. CLI (Linux):

```sh
./math/build/experiment 20 0.1 200 0 1 1 0.1 100
# C Lseconds total failed window_seconds cpu_reference_cores Lmax_seconds Tmax_per_second
```

Referencias de teste Lmax=0,1 s e Tmax=100/s sao valores artificiais para exercitar limites; nao representam SLOs validados.

