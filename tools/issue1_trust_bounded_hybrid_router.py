"""Issue #1: verified-formal-only EC routing, otherwise preserve original LLM.

The policy's *source independence* is not inferred by this function. Trusted
references/target allowlist must be provisioned out of band from the LLM and
from user-supplied task data. No arbitrary user approval flag is accepted.

Uses the existing SymPy SAT formal equivalence evaluator and existing EC API
as injected callable. Does NOT implement a new semantic parser or EC planner.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

try:
    from issue1_independent_formal_policy_equivalence import compare, PolicyEquivalenceError, digest
except ModuleNotFoundError:
    # Normal in tests importing via path. The tests explicitly install the pinned
    # sibling module in sys.path before importing this one.
    raise

BOUNDED_TARGETS = frozenset({'governed_next_action', 'formal_policy_s3'})


@dataclass(frozen=True)
class TrustedReference:
    policy_sha256: str
    source_sha256: str
    target: str
    # Source and reviewer custody MUST be established outside this module;
    # only a pre-approved reference object may enter the host adapter.


def route(*, llm_output: Any, proposed_policy: Mapping[str, Any] | None,
          frozen_reference: Mapping[str, Any] | None,
          trusted: TrustedReference | None,
          observed_source_sha256: str | None,
          requested_target: str,
          native_ec: Callable[..., Any] | None,
          ec_input: Any = None) -> dict[str, Any]:
    """No full semantic-competence claims: EC only on attested matched formal scope.

    For unknown/untrusted policy, preserves object identity of the LLM result.
    `native_ec` must be a previously imported, SHA-verified EC engine adapter.
    Caller controls neither `trusted` nor the `native_ec` code when deployed.
    """
    def fallback(why: str, counterexamples: list | None = None):
        return {'route': 'LLM_UNCHANGED', 'reason': why, 'decision': llm_output,
                'counterexamples': counterexamples or [],
                'root_science_AC_promoted': 0}

    if requested_target not in BOUNDED_TARGETS:
        return fallback('UNSUPPORTED_SEMANTIC_TARGET')
    if trusted is None or frozen_reference is None:
        return fallback('NO_INDEPENDENTLY_PINNED_FORMAL_REFERENCE')
    if not isinstance(trusted, TrustedReference) or trusted.target != requested_target:
        return fallback('TRUST_TARGET_SCOPE_MISMATCH')
    if (not isinstance(observed_source_sha256, str) or
            observed_source_sha256 != trusted.source_sha256):
        return fallback('SOURCE_CUSTODY_HASH_MISMATCH')
    if proposed_policy is None:
        return fallback('NO_PROPOSED_FORMAL_POLICY')

    try:
        proof = compare(frozen_reference, proposed_policy, trusted.policy_sha256)
    except (PolicyEquivalenceError, ValueError, TypeError, KeyError):
        return fallback('FORMAL_REFERENCE_OR_PROPOSAL_INVALID')
    if not proof['formal_equivalent_to_pinned_reference']:
        return fallback('FORMAL_RULE_NOT_EQUIVALENT',
                        [r for r in proof['checks'] if not r['equivalent']])
    if native_ec is None:
        return fallback('PINNED_NATIVE_EC_NOT_AVAILABLE')

    # Execute the immutable, independently provisioned *reference*, not the
    # potentially model-authored proposal. No raw NL or oracle/gold is passed.
    try:
        decision = native_ec(ec_input=ec_input, policy=frozen_reference)
    except Exception:
        return fallback('NATIVE_EC_RUNTIME_FAIL_CLOSED')

    # S4 full real-world closure is *not* in BOUNDED_TARGETS. Do not
    # promote native formal-policy CLOSE to completed real-world task.
    return {'route': 'EC_FORMAL_SCOPE_ONLY', 'reason': 'MATCHED_TRUSTED_FORMAL_POLICY',
            'decision': decision, 'original_llm_output': llm_output,
            'formal_reference_sha256': trusted.policy_sha256,
            'formal_proposal_sha256': digest(proposed_policy),
            'source_sha256': trusted.source_sha256,
            'real_world_task_close_authorized': False,
            'semantic_generalization_non_degradation_proven': False,
            'root_science_AC_promoted': 0}
