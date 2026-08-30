# Security policy

Open Semantic Boundary Benchmark (Open-SBB) is a research benchmark for evaluating semantic disclosure and export strategies. The CIKM 2026 artifact uses synthetic pilot data and is intended for research and reproducibility work.

Open-SBB is not a production privacy or security gateway, a hosted service, or a compliance certification mechanism. Its evaluation results should not be interpreted as establishing HIPAA, GDPR, or other regulatory compliance.

## Supported versions

Security fixes are maintained on the active development branch. 
Security issues affecting the frozen CIKM 2026 artifact should identify the `cikm-2026` release or exact affected commit. Older experimental tags and snapshots are retained primarily for provenance and may receive fixes on a best-effort basis.


## Reporting a vulnerability

Please do not open a public GitHub issue for security-sensitive reports.

Report them privately using either:

1. **Email:** [gb@nimblenotions.ca](mailto:gb@nimblenotions.ca)
2. **GitHub:** [Private security advisory](https://github.com/nimblenotions/open-semantic-boundary-benchmark/security/advisories/new), when available

Please include:

* the affected version or commit;
* steps needed to reproduce the issue;
* the expected security impact, such as arbitrary code execution, credential exposure, path traversal, or unintended file modification; and
* any proof of concept that can be shared safely.

Security-sensitive reports are appreciated and will be reviewed as maintainer capacity permits. Confirmed issues will be addressed or documented when practical.

There is currently no bug-bounty program for this repository.

## In scope

Security issues in repository code or tooling that could affect someone running the benchmark locally are in scope. Examples include:

* unsafe deserialization or command execution;
* path traversal or unintended arbitrary file writes when processing benchmark inputs;
* credential or secret-handling vulnerabilities in benchmark tooling; and
* vulnerabilities in repository code that could cause execution of untrusted input outside the intended benchmark workflow.

## Out of scope

The following are generally outside the scope of this repository's security policy:

* **Synthetic corpus content:** the CIKM pilot personas and events are generated research fixtures rather than real patient or user records.
* **Third-party runtimes and dependencies:** vulnerabilities in Python, operating-system packages, Ollama, model runtimes, or externally obtained model weights should normally be reported to their respective maintainers unless the vulnerability arises from how Open-SBB uses them.
* **Routine dependency updates:** non-security version bumps should be handled through normal issues or dependency-management pull requests.
* **Use with production-sensitive data:** Open-SBB does not provide the governance, access controls, or operational safeguards required for handling live sensitive traces.
* **Compliance determinations:** benchmark results do not certify HIPAA, GDPR, or other regulatory or production-safety requirements.

## Safe use

For the frozen CIKM 2026 artifact, use the supported verification workflow:

```bash
make repro-cikm-2026
```

This verification path uses committed evaluation artifacts and does not regenerate the LLM-based transformation outputs.

Broader regeneration and development workflows may require local model runtimes and may exercise historical pipeline components retained for provenance. Review the relevant commands before running them, keep local services restricted to trusted interfaces, and do not expose development model endpoints to untrusted networks.

The frozen CIKM protocol and verification artifacts are documented under [`releases/cikm-2026/`](releases/cikm-2026/).

## General bugs

Reproduction problems, metric mismatches, and documentation issues that are not security-sensitive should be reported through public GitHub issues. See [`CONTRIBUTING.md`](CONTRIBUTING.md).
