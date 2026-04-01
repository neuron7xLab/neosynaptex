"""DNCA smoke test — run with: python -m neuron7x_agents.dnca.smoke_test"""
import torch
from neuron7x_agents.dnca import DNCA
from neuron7x_agents.dnca.diagnostics import RegimeDiagnostics


def main():
    torch.manual_seed(42)
    dnca = DNCA(state_dim=64, hidden_dim=128)
    diag = RegimeDiagnostics(dnca)
    for i in range(200):
        obs = torch.sin(torch.arange(64, dtype=torch.float32) * 0.3) * 0.5 + torch.randn(64) * 0.1
        out = dnca.step(obs, reward=0.01 if i % 20 == 0 else 0.0)
        diag.record(out)
    print(diag.summary())
    print(diag.plot_ascii())
    print("\nDNCA smoke test: PASS")


if __name__ == "__main__":
    main()
