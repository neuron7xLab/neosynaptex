# Regime Controller Formal Mathematical Specification

Let entropy be clipped:
\[
e_t = \mathrm{clip}(\hat e_t, 0, 1)
\]

Velocity:
\[
V_t = \begin{cases}
(\gamma_t-\gamma^*)(1-e_t), & e_t<e_{th}\\
0, & e_t\ge e_{th}
\end{cases}
\]

Gate:
\[
g_t = \sigma(V_t - V_{t-1}),\quad \sigma(x)=\frac{1}{1+e^{-x}}
\]

Action update:
\[
w'_{t+1} = w_t + \eta g_t \nabla w_t
\]

Rest-phase decay:
\[
w_{t+1}=\begin{cases}
(1-\alpha)w'_{t+1}, & g_t<r_{th}\\
w'_{t+1}, & \text{otherwise}
\end{cases}
\]
