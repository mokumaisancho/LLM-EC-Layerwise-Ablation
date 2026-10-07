from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

from ec_v3_adapter import ECV3SuiteBridge
from suite_loader import load_suite, require_runtime_stage


EXPECTED_V4_REPO = "mokumaisancho/GPT-EC-Closure-Engine"
EXPECTED_V4_BRANCH = "GPT-EC-V4"
EXPECTED_V4_REF = "f0f2d4a8634a130b710a326072438a51428929a3"
CANDIDATE_CONFIG = "ECV4_SUITE_CANDIDATE.json"


class ECV4SuiteBridge(ECV3SuiteBridge):
    """V4 bridge preserving the qualified V3 inner Suite envelope."""

    @staticmethod
    def _candidate_config(root: Path) -> dict[str, Any]:
        path = root / CANDIDATE_CONFIG
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise RuntimeError("ECV4_CANDIDATE_CONFIG_INVALID") from exc
        if not isinstance(value, dict):
            raise RuntimeError("ECV4_CANDIDATE_CONFIG_INVALID")
        ec = value.get("ec") or {}
        expected = {
            "generation": "V4",
            "repo": EXPECTED_V4_REPO,
            "branch": EXPECTED_V4_BRANCH,
            "ref": EXPECTED_V4_REF,
        }
        for key, required in expected.items():
            if ec.get(key) != required:
                raise RuntimeError(f"ECV4_CANDIDATE_CONFIG_MISMATCH:{key}")
        invariants = value.get("suite_invariants") or {}
        if invariants.get("github_actions_enabled") is not False:
            raise RuntimeError("ECV4_GITHUB_ACTIONS_MUST_REMAIN_DISABLED")
        if invariants.get("exact_operation_binding") is not True:
            raise RuntimeError("ECV4_EXACT_OPERATION_BINDING_REQUIRED")
        return value

    @staticmethod
    def _checkout_state(root: Path) -> tuple[str, str]:
        try:
            head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
            tree = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD^{tree}"], check=True,
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
            dirty = subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"], check=True,
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError("ECV4_PIN_VERIFICATION_FAILED") from exc
        if head != EXPECTED_V4_REF:
            raise RuntimeError(f"ECV4_CHECKOUT_REF_MISMATCH:{head}:{EXPECTED_V4_REF}")
        if dirty:
            raise RuntimeError("ECV4_CHECKOUT_DIRTY")
        return head, tree

    @staticmethod
    def _is_under(path: Path, root: Path) -> bool:
        try:
            path.resolve().relative_to(root.resolve())
            return True
        except ValueError:
            return False

    @classmethod
    def _require_v4_module_provenance(cls, experiment: Path) -> None:
        module = sys.modules.get("v4_control")
        if module is None:
            return
        raw = getattr(module, "__file__", None)
        expected = experiment / "poc16_v4_control"
        if not raw or not cls._is_under(Path(raw), expected):
            raise RuntimeError("ECV4_MODULE_PROVENANCE_MISMATCH:v4_control")

    @classmethod
    def from_ec_v4_checkout(
        cls,
        *,
        ec_v4_root: str | Path,
        base_controller: Any,
        ledger: Any,
        suite_root: str | Path | None = None,
        manifest: Mapping[str, Any] | None = None,
        runtime_stage: str = "EXPERIMENTAL",
    ) -> "ECV4SuiteBridge":
        loaded = load_suite(suite_root)
        normalized_stage = require_runtime_stage(loaded, runtime_stage)
        if manifest is not None and dict(manifest) != dict(loaded.manifest):
            raise RuntimeError("SUPPLIED_MANIFEST_NOT_LOCKED_CONFIGURATION")
        suite_path = loaded.root
        cls._candidate_config(suite_path)
        root = Path(ec_v4_root).resolve()
        pre = cls._checkout_state(root)
        experiment = root / "02_experiments" / "metacognition_vnext"
        paths = [
            experiment / "poc01_state_vector", experiment / "poc02_competence_map",
            experiment / "poc03_pressure_interlock", experiment / "poc04_proof_memory",
            experiment / "poc05_sensor_certification", experiment / "poc06_expected_value_router",
            experiment / "poc07_epistemic_cache", experiment / "poc08_dynamic_focus_graph",
            experiment / "poc09_integrated_control", experiment / "poc11_consistency_exploration_guard",
            experiment / "poc12_cognitive_integrity_guard", experiment / "poc13_gpt_runtime_gateway",
            experiment / "poc15_human_utility_guard", experiment / "poc16_v4_control",
        ]
        missing = [str(path) for path in paths if not path.is_dir()]
        if missing:
            raise RuntimeError("ECV4_CHECKOUT_INCOMPLETE:" + ",".join(missing))
        cls._require_module_provenance(experiment)
        cls._require_v4_module_provenance(experiment)
        for path in reversed(paths):
            text = str(path)
            if text not in sys.path:
                sys.path.insert(0, text)
        from gpt_runtime_gateway import ActionObservation, GPTActionProposal
        from runtime_assembly import build_ec_v4_runtime
        cls._require_module_provenance(experiment)
        cls._require_v4_module_provenance(experiment)
        runtime = build_ec_v4_runtime(base_controller=base_controller, ledger=ledger)
        post = cls._checkout_state(root)
        if post != pre:
            raise RuntimeError("ECV4_CHECKOUT_CHANGED_DURING_ASSEMBLY")
        cls._require_module_provenance(experiment)
        cls._require_v4_module_provenance(experiment)
        return cls(
            loaded_configuration=loaded,
            runtime=runtime,
            proposal_type=GPTActionProposal,
            observation_type=ActionObservation,
            runtime_stage=normalized_stage,
        )

    def select_next_action(
        self,
        plan: Mapping[str, Any],
        *,
        completed_work_ids=(),
        blocked_work: Mapping[str, str] | None = None,
        dynamic_context: Mapping[str, Any] | None = None,
        dynamic_state_authority: Any | None = None,
    ) -> dict[str, Any]:
        return self.runtime.v4_control.select_next_action(
            plan,
            completed_work_ids=completed_work_ids,
            blocked_work=blocked_work,
            dynamic_context=dynamic_context,
            dynamic_state_authority=dynamic_state_authority,
        )

    def evaluate_prior_art(
        self,
        packet: Mapping[str, Any] | None,
        *,
        expected_binding: Mapping[str, Any] | None = None,
        relevance_authority: Any | None = None,
    ) -> dict[str, Any]:
        return self.runtime.v4_control.evaluate_prior_art(
            packet,
            expected_binding=expected_binding,
            relevance_authority=relevance_authority,
        )


__all__ = ["CANDIDATE_CONFIG", "ECV4SuiteBridge", "EXPECTED_V4_BRANCH", "EXPECTED_V4_REF", "EXPECTED_V4_REPO"]
