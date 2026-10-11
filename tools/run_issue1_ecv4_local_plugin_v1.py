#!/usr/bin/env python3
"""Run optional research-scoped EC S3/S4 plugin with actual public inputs."""
import argparse
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from tools.issue1_ecv4_local_plugin_v1 import evaluate

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ec-root",type=Path,required=True)
    p.add_argument("--s2",type=Path,required=True)
    p.add_argument("--task",type=Path,required=True)
    p.add_argument("--policy",type=Path,required=True)
    p.add_argument("--framing",type=Path,required=True)
    p.add_argument("--policy-sha",required=True)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    try:
        sources=[a.s2,a.task,a.policy,a.framing]
        if any(not x.is_file() or x.is_symlink() for x in sources):
            raise ValueError("PLUGIN_INPUT_MISSING_OR_SYMLINK")
        inputs=[json.loads(x.read_text()) for x in sources]
        result=evaluate(a.ec_root,*inputs[:2],inputs[2],a.policy_sha,inputs[3])
        output=json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
        if a.out:
            if a.out.is_symlink():raise ValueError("PLUGIN_OUTPUT_SYMLINK")
            a.out.write_text(output)
        print(json.dumps({
            "protocol":result["protocol"],
            "S3":result["s3_selected"],
            "S4":result["s4_diagnostic"],
            "real_world_closure":result["real_world_close_authorized"],
        }))
        return 0
    except Exception as ex:
        print(json.dumps({"terminal":"PLUGIN_FAIL_CLOSED",
                          "error":type(ex).__name__+":"+str(ex)[:200]}))
        return 3

if __name__=="__main__":raise SystemExit(main())
