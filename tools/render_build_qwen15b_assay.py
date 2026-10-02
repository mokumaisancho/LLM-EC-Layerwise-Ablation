#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import render_qwen05b_reframe_assay as assay

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results' / 'phase1_qwen25_1p5b_reframe_build_runtime.json'
OUT.parent.mkdir(parents=True, exist_ok=True)

# Execute the exact frozen parameterized assay synchronously in Render's build phase.
assay.run_assay()
state = dict(assay.STATE)
OUT.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
print('BUILD_ASSAY_TERMINAL=' + json.dumps(state, ensure_ascii=False, separators=(',', ':')), flush=True)
# Always preserve/deploy the evidence artifact; scientific PASS/FAIL is in state.status.
