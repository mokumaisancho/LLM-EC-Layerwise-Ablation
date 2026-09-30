# Fixture Authoring Rules

1. Define the task and protected intent before any LLM/EC output is inspected.
2. Build S1-S4 oracle artifacts from the task specification and domain rules, not by copying an implementation output.
3. Encode semantic equivalence with constraints; do not require exact wording.
4. Keep candidate generation and candidate selection labels separate.
5. Include negative cases explicitly: plausible-but-invalid candidate, unnecessary reframe, false closure.
6. Record all source references used to construct the oracle.
7. Do not change a frozen oracle to improve an implementation score. Create a new fixture generation instead.
8. Do not mix results across fixture generations.
9. Every downstream comparison must reference the exact upstream artifact hash used.
10. GitHub Actions are not part of validation; validation is run explicitly and results are persisted.
