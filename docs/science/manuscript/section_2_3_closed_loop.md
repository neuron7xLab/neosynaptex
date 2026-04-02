# 2.3 Stability of the Closed Loop

Let \(e_t := \gamma_t - 1\) be deviation from the critical regime. The closed loop
receives \(k\) witness estimates
\[
\tilde e_{i,t} = e_t + \nu_{i,t}, \quad i=1,\dots,k
\]
where at most \(f\) witnesses are faulty and honest witnesses satisfy
\[
|\nu_{i,t}| \le \sigma.
\]

After anomaly isolation, robust aggregated error is computed by median consensus:
\[
\bar e_t = \operatorname{median}\{\tilde e_{i,t}: i\notin \mathcal O_t\}.
\]
We require \(k \ge 2f+1\), yielding honest-majority robustness.

Bounded control update:
\[
u_t = -\operatorname{clip}(\eta \bar e_t, -\varepsilon, +\varepsilon),\qquad
\varepsilon \le 0.05,\ \eta>0
\]
and closed-loop dynamics
\[
e_{t+1}=e_t+u_t+r_t,\qquad |r_t|\le \rho.
\]

Quality dynamics:
\[
Q_{t+1}\le Q_t-a(|e_t|-\delta)_+ + b,\qquad a>0,\ b\ge 0
\]
where \((x)_+ := \max(x,0)\).

## Proposition A (Unique attracting critical interval in \(\gamma\)-coordinate)

Assume:
1. \(k\ge2f+1\)
2. honest witness noise is bounded: \(|\nu_{i,t}|\le\sigma\)
3. drift is bounded: \(|r_t|\le\rho\)
4. \(\varepsilon>\rho\)

Define \(\delta_* := \sigma + \rho/\eta\). For any state with \(|e_t|>\delta_*\), update is
sign-correct and contractive:
\[
|e_{t+1}|<|e_t|.
\]
Hence
\[
\mathcal A_\gamma:=\{e:|e|\le\delta_*\}
\]
is the unique attracting interval in the \(\gamma\)-coordinate; no stable equilibrium exists outside
\(\mathcal A_\gamma\).

### Proof sketch

Under honest-majority median, if \(|e_t|>\sigma\), then
\[
\operatorname{sign}(\bar e_t)=\operatorname{sign}(e_t),\quad |\bar e_t|\ge |e_t|-\sigma.
\]
In unclipped regime:
\[
|e_{t+1}|
\le |e_t|-\eta|\bar e_t|+\rho
\le |e_t|-\eta(|e_t|-\sigma)+\rho
\]
which is strictly contractive for \(|e_t|>\sigma+\rho/\eta=\delta_*\).
In clipped regime:
\[
|e_{t+1}|\le|e_t|-\varepsilon+\rho<|e_t|
\]
because \(\varepsilon>\rho\). Lyapunov candidate:
\[
V_\gamma(e):=(|e|-\delta_*)_+
\]
strictly decreases outside \(\mathcal A_\gamma\).

## Proposition B (Binary asymptotic structure with quality collapse)

Assume Proposition A and additionally:
\[
\exists\Delta>\delta_*:\ \ |e_t|\ge\Delta \Rightarrow a(|e_t|-\delta)-b\ge c>0.
\]
Then every long-run trajectory has two outcomes:
1. it enters and remains in \(\mathcal A_\gamma\), or
2. it is absorbed into quality collapse (\(Q_t\) crosses any \(Q_{\min}\in(0,1)\)).

No third stable long-run regime exists under these assumptions.

### Proof sketch

By Proposition A, only \(\mathcal A_\gamma\) attracts in \(\gamma\)-coordinate.
If a trajectory does not remain in \(\mathcal A_\gamma\), it visits \(|e_t|\ge\Delta\)
infinitely often; on those steps, \(Q_{t+1}\le Q_t-c\), forcing eventual collapse.
