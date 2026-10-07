#!/usr/bin/env python3
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
tests=subprocess.run([sys.executable,"-m","unittest","-v","tests.test_semantic_runtime_execution_v2"],cwd=ROOT,text=True,capture_output=True)
v3=subprocess.run([sys.executable,"-m","unittest","-v","tests.test_semantic_runtime_operator_policy_v3"],cwd=ROOT,text=True,capture_output=True)
v1=subprocess.run([sys.executable,"-m","unittest","-v","tests.test_semantic_runtime_product"],cwd=ROOT,text=True,capture_output=True)
result={"protocol":"SEMANTIC_RUNTIME_V2_TRUST_GATE_V1","pass":tests.returncode==0 and v1.returncode==0 and v3.returncode==0,"v2_tests_pass":tests.returncode==0,"v1_regression_pass":v1.returncode==0,"v3_policy_tests_pass":v3.returncode==0,"v3_test_output":(v3.stdout+v3.stderr)[-8000:],"v2_test_output":(tests.stdout+tests.stderr)[-9000:],"v1_output":(v1.stdout+v1.stderr)[-5000:],"terminal":"V2_TRUST_GATE_PASS" if tests.returncode==0 and v1.returncode==0 else "V2_TRUST_GATE_FAIL_CLOSED"}
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(0 if result["pass"] else 3)
