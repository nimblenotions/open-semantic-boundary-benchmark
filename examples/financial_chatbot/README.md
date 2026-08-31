# Financial chatbot (conceptual)

A financial-advice transcript may contain client identifiers, account detail, and proposed actions. A supervision or analytics consumer may need risk stage or intent without receiving names, exact holdings, or other identifiers.

Candidate exports include leaving the transcript as written, replacing identifiers (tokens or surrogates), or releasing permitted semantic fields. A Semantic Boundary evaluation could compare those alternatives by utility for the registered review purpose, residual linkage on the released representation, and provenance completeness.

This is an illustrative application of the framework. The CIKM 2026 artifact does not include a financial-chatbot corpus or results. A tiny synthetic provenance sketch is [`../provenance/finra_advisor_export.json`](../provenance/finra_advisor_export.json); it does not establish FINRA compliance.

The published lattice includes analogous surface strategies (`redact_tokenize`, `redact_surrogate`) in the medication-adherence study: [`../medication_adherence/`](../medication_adherence/README.md).
