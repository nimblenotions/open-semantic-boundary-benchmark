# Security policy

Open Semantic Boundary Benchmark (Open SBB) is a **research benchmark** for evaluating semantic export strategies on **synthetic pilot data**. It is not a production privacy gateway, HIPAA certification, or hosted service.

## Supported versions

| Version | Supported |
|---------|-----------|
| `opensbb-v0.1.2` (Zenodo) | Yes |
| `main` | Yes |
| Older tags | Best-effort; prefer upgrading |

Security fixes land on `main` and are noted in [`CHANGELOG.md`](CHANGELOG.md).

## Reporting a vulnerability

**Please do not open a public GitHub issue** for security-sensitive reports.

Report privately by either:

1. **Email:** [gb@nimblenotions.ca](mailto:gb@nimblenotions.ca) (PGP optional; ask if you need a key)
2. **GitHub:** [Private security advisory](https://github.com/nimblenotions/open-semantic-boundary-benchmark/security/advisories/new) on this repository (if enabled for your account/org)

Include:

- Affected version or commit
- Steps to reproduce
- Impact (e.g. arbitrary code execution, credential leak, path traversal)
- Any proof-of-concept you can share safely

We aim to acknowledge reports within **5 business days** and to provide a fix or mitigation timeline when confirmed.

There is **no bug bounty** program for this repository.

## In scope

Issues in this repo that could affect someone running the benchmark locally, for example:

- Unsafe deserialization or shell invocation in harness scripts
- Path traversal or arbitrary file write when processing benchmark inputs
- Credential handling bugs in tooling that talks to local services (e.g. Ollama)

## Out of scope

- **Synthetic corpus content** — pilot personas and events are generated fixtures, not real PHI
- **Third-party runtimes** — Ollama, Python, OS packages, and model weights you install separately
- **Dependency version bumps** — report via normal [issues](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues) or Dependabot PRs unless exploitability in *this* harness is demonstrated
- **Misuse on production traces** — running the harness on live sensitive data without your own governance
- **Compliance claims** — Open SBB does not certify HIPAA, GDPR, OTel, or production safety (see [`open-sbb/README.md`](open-sbb/README.md#not-claimed))

## Safe use

- Treat the committed pilot as **research artifacts** with checksums in [`README.md`](README.md)
- Use `make repro-smoke` for audit without calling external LLMs
- Full regeneration (`make pipeline`) requires a **local** Ollama instance you control; do not expose Ollama to untrusted networks

## General bugs

Reproduction problems, metric mismatches, and documentation fixes belong in public issues — see [`CONTRIBUTING.md`](CONTRIBUTING.md).
