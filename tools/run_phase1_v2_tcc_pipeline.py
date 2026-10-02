#!/usr/bin/env python3
"""Compatibility entrypoint.

The old Phase1-v2 partial pipeline is retired because it could run only the
S3/S4 harness and bypass the full AC/dependency gates. All execution now routes
to PHASE1_MVP_TCC_V1.
"""
from __future__ import annotations

import runpy
from pathlib import Path

TARGET = Path(__file__).with_name("run_phase1_mvp_tcc.py")

if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
