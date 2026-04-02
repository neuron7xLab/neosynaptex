# Dependence-Correctness Notes (α-mixing sketch)

We use dependence-aware inference where windows are not i.i.d. and serial dependence is explicit.

## Assumptions
- Weak stationarity of transformed series \((\log T_t, \log C_t)\).
- α-mixing with summable tail: \(\sum_k \alpha(k)^{\delta/(2+\delta)} < \infty\).
- Finite \(2+\delta\) moments.

## Consistency sketch
For robust slope estimator \(\hat\gamma\) (Theil-Sen over dependent samples),
\[
\hat\gamma \xrightarrow{p} \gamma
\]
under mixing + moment assumptions.

## Finite-sample envelope (heuristic)
\[
\mathrm{bias}(\hat\gamma) = O\!\left(\frac{\alpha_*}{\sqrt{N_{\mathrm{eff}}}}\right),\qquad
N_{\mathrm{eff}} = \left\lfloor\frac{N}{\tau_{\mathrm{int}}}\right\rfloor.
\]

Implementation references:
- `core/block_bootstrap.py`
- `scripts/compute_neff.py`
