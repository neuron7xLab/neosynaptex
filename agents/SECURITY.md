# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting vulnerabilities

Report security vulnerabilities via GitHub Issues with the `security` label,
or email neuron7xlab@gmail.com.

**Do not** open a public issue for vulnerabilities that could be exploited
before a fix is available.

## Security design

This library implements epistemic security primitives:

- **Fail-closed gates**: missing evidence blocks scoring, not inflates it
- **Anti-gaming detection**: artifact reuse, self-review loops, provenance washing
- **Confidence calibration**: 0.95+ claims require formal proof gate
- **Input adversarial robustness**: NCE treats all input as potentially
  incomplete, contradictory, manipulative, or based on false premises
- **Prompt injection resistance**: Kriterion treats artifact content as data,
  not authority — the protocol holds authority

## Dependencies

Core dependencies are minimal: `numpy`, `pydantic`. Optional dependencies
are isolated behind extras (`[science]`, `[api]`, `[ml]`).
