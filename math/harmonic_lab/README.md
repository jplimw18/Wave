# Harmonic lab (synthetic)

This small Python exercise is a synthetic algebraic demonstrator, separate from the existing C++ experiments and from the project document's independent P/Q calculation. A rank-deficient fit returns the minimum-norm coefficients and the reported rank; these coefficients are not uniquely identified. It models one window as

`y(t) = P sin(ωt) + Q cos(ωt)`, with `S = hypot(P,Q)` and `θ = atan2(Q,P)`, so that `y(t) = S sin(ωt+θ)`. `P` and `Q` are fitted independently by least squares; they are not derived from `S`. The optional labels “delivery” and “friction” can be used for P and Q as dimensionless indices, but the fit does not establish that they measure efficiency. The `atan2` phase is left undefined (`None`) when `S=0`.

The operationally shaped synthetic demo has four services, three nonnegative time-varying metrics `[P,Q,D]`, and twelve windows. It defines `D(t)=hypot(P(t)-1,Q(t))`, the distance to the chosen reference `(1,0)`. D is derived from P and Q, so it adds no independent information. The choice `P_ref=1` depends on normalization and does not prove that the reference is a real-world maximum. `synthetic_windows.csv` exports a temporal matrix (windows by P/Q/D) per service with ΔD and ΔD/Δt; `synthetic_summary.csv` reports the SVD of service 1 and HOSVD of the full service × metric × window tensor. A 3-column `[P,Q,D]` matrix can have rank 3 because D is nonlinear in P,Q; the two-dimensional harmonic coefficient fit does not constrain this operational matrix to rank 2. Some algebraic unit tests deliberately cover signed coefficients outside the operational domain.

Use Python 3.11+ and create an isolated environment from this directory. NumPy is pinned to the tested version; Matplotlib is optional and may be installed separately when PNG plots are wanted. The core demo falls back to SVG using only the standard library.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Then run from this directory:

```powershell
python harmonic_lab.py
python -m unittest test_harmonic_lab.py
```

The demo creates `output/synthetic_summary.csv` and plots prefixed `synthetic_`, including the P-Q temporal path with reference marker and D over time. Both trajectory plot implementations use equal scale on P and Q so one unit has the same visual length on each axis. The plots are SVG and are generated with Python's standard library when Matplotlib is absent. Matplotlib, when installed, produces PNG plots. All service metrics and trajectories are deliberately synthetic. No real-data input schema is defined.

The tests cover rotation orthogonality, amplitude-phase reconstruction, least-squares recovery including rank-deficient and nonuniform samples, uniform full-cycle basis orthogonality and mean-square energy, zero-amplitude phase, SVD reconstruction and truncation, HOSVD full/truncated reconstruction and factor orthogonality, invalid/empty inputs, distance nonnegativity and zero condition, triangle bounds and squared identity, changing distance over windows, a rank-3 `[P,Q,D]` example, and a concrete projection null direction: for the 3×2 projection shown in the source, `(1,1,-1)` maps to zero, so observations in three metrics cannot identify arbitrary components along that direction.
