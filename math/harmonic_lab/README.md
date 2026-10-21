# Laboratório harmônico com dados sintéticos

Este programa Python demonstra a álgebra com dados sintéticos, separadamente dos experimentos C++ existentes e do cálculo de P/Q a partir das observações. Quando a matriz de ajuste tem posto insuficiente, a função retorna os coeficientes de norma mínima e informa o posto; esses coeficientes não são identificados de forma única. Uma janela é representada por

`y(t) = P sin(ωt) + Q cos(ωt)`, com `S = hypot(P,Q)` e `θ = atan2(Q,P)`, de modo que `y(t) = S sin(ωt+θ)`. `P` e `Q` são ajustados por mínimos quadrados sem depender de `S`; isso não pressupõe independência estatística entre eles. Os termos “entrega” e “atrito” podem nomear os índices adimensionais, mas o ajuste não demonstra que medem eficiência. A fase calculada por `atan2` fica indefinida (`None`) quando `S=0`.

A demonstração sintética representa quatro serviços, três métricas não negativas `[P,Q,D]` que variam no tempo e doze janelas. Define `D(t)=hypot(P(t)-1,Q(t))`, a distância à referência escolhida `(1,0)`. D é derivada de P e Q e não acrescenta informação independente. A escolha `P_ref=1` depende da normalização e não comprova que a referência seja um máximo real. `synthetic_windows.csv` exporta uma matriz temporal por serviço, com janelas nas linhas, P/Q/D nas colunas e os valores de ΔD e ΔD/Δt. `synthetic_summary.csv` registra a SVD do serviço 1 e a HOSVD do tensor completo serviço × métrica × janela. A matriz `[P,Q,D]` pode ter posto 3 porque D é uma função não linear de P,Q; os dois coeficientes da curva harmônica não limitam essa matriz ampliada ao posto 2. Alguns testes algébricos cobrem deliberadamente coeficientes com sinal fora do domínio operacional.

Use Python 3.11 ou superior e crie um ambiente isolado a partir deste diretório. A versão do NumPy está fixada na versão testada. Matplotlib é opcional e pode ser instalado separadamente para gerar gráficos PNG. Quando ele não está disponível, os gráficos são produzidos em SVG pela biblioteca padrão do Python; o cálculo continua usando NumPy.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Em seguida, execute neste diretório:

```powershell
python harmonic_lab.py
python -m unittest test_harmonic_lab.py
```

A demonstração cria `output/synthetic_summary.csv` e gráficos com o prefixo `synthetic_`, incluindo a trajetória temporal P-Q com a referência marcada e a distância D ao longo do tempo. As duas versões do gráfico de trajetória usam a mesma escala nos eixos P e Q: uma unidade tem o mesmo comprimento visual em ambos. Todos os valores de serviços e trajetórias são sintéticos. Este laboratório algébrico não define um formato de entrada para dados reais; o contrato de observações está em [CONTRATO_FIXTURES.md](../../docs/math/CONTRATO_FIXTURES.md).

Os testes verificam ortogonalidade da rotação; reconstrução por amplitude e fase; recuperação por mínimos quadrados com amostras não uniformes e posto insuficiente; ortogonalidade e média quadrática num ciclo completo uniformemente amostrado; fase com amplitude zero; reconstrução e truncagem por SVD; reconstrução completa e truncada por HOSVD e ortogonalidade dos fatores; entradas inválidas ou vazias; propriedades da distância D; desigualdade triangular e identidade dos quadrados; variação de D entre janelas; e um exemplo de `[P,Q,D]` com posto 3. Também verificam uma direção nula da projeção: na matriz 3×2 do código, `(1,1,-1)` é levado a zero, impedindo identificar componentes arbitrários nessa direção a partir dos dois coeficientes.

Nomes de arquivos, funções, campos CSV/JSON e estados de máquina permanecem em sua forma original para preservar os contratos. A referência histórica copiada em `pq_contract/fixtures/` também permanece intacta para conservar sua origem e seu hash.
