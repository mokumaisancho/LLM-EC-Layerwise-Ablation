#!/bin/zsh
set -euo pipefail

# One-run, fail-closed recovery for the already-authorized InitiativeDispatcher Mac.
# Tests in an isolated checkout before any existing LaunchAgent or queue is changed.
REPO='mokumaisancho/initiative-dispatcher'
BRANCH='fix/history-capacity-rca-v44-20261016'
PIN='87d054651b77ea8bc42f62c7b2e011953670bc57'
PR='1'
OLD_ID='INIT-ISSUE1-S3S4-V41'
OLD_RID='d19ba6c294a0108df8afbf72'
DATA="$HOME/Library/Application Support/InitiativeDispatcher"
PLIST="$HOME/Library/LaunchAgents/com.local.initiative-dispatcher.plist"
STAGE="$DATA/releases/v44-$(printf '%s' "$PIN" | cut -c1-12)"
LOG="$HOME/Library/Logs/initiative-dispatcher-v44-repair.log"
RESULT_JSON="$DATA/v44-repair-last-result.json"
PHASE='INITIAL_CHECKS'
TEST_STATUS='NOT_RUN'
MERGE_STATUS='NOT_ATTEMPTED'
V41_STATUS='UNCHANGED'
MAC_STATUS='UNCHANGED'

# The PR comment is the durable remote result, including failures. Never upload
# raw terminal/Codex output, which can include credentials or sensitive data.
report_exit() {
  local rc=$?
  trap - EXIT
  set +e
  local verdict='BLOCKED'
  [[ $rc -eq 0 ]] && verdict='PASS'
  local test_counts='unavailable'
  if [[ -f "$LOG" ]]; then
    test_counts="$(grep -E '^Ran [0-9]+ tests? in [0-9.]+s$' "$LOG" | tail -n 2 | awk '{print $2}' | paste -sd '+' -)"
    [[ -n "$test_counts" ]] || test_counts='unavailable'
  fi
  local failed_test_ids='none'
  if [[ -f "$LOG" ]]; then
    failed_test_ids="$(grep -E '^(FAIL|ERROR): test_[A-Za-z0-9_]+ \(' "$LOG" | sed -E 's/^(FAIL|ERROR): (test_[A-Za-z0-9_]+).*/\2/' | sort -u | head -n 12 | paste -sd ',' -)"
    [[ -n "$failed_test_ids" ]] || failed_test_ids='none'
  fi
  local report="RCA v44 automated Mac run: **${verdict}** (exit ${rc}); phase: \`${PHASE}\`; tests: \`${TEST_STATUS}\`; test counts: \`${test_counts}\`; failed test IDs: \`${failed_test_ids}\`; merge: \`${MERGE_STATUS}\`; V41: \`${V41_STATUS}\`; Mac: \`${MAC_STATUS}\`; pinned source: \`${PIN}\`. No raw local log or secrets were uploaded."
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$RESULT_JSON" "$verdict" "$rc" "$PHASE" "$TEST_STATUS" "$MERGE_STATUS" "$V41_STATUS" "$MAC_STATUS" "$PIN" "$test_counts" <<'LOCAL_RESULT_JSON' >/dev/null 2>&1
import json, os, sys
path, verdict, rc, phase, tests, merge, supersede, mac, pin, counts = sys.argv[1:]
obj = {"schema": "INITIATIVE_DISPATCHER_V44_LOCAL_EXECUTION_REPORT",
       "result": verdict, "exit_code": int(rc), "phase": phase,
       "tests": tests, "test_count_summary": counts, "merge": merge,
       "old_v41": supersede, "mac_install": mac, "source_commit": pin,
       "raw_log_uploaded": False}
with open(path, 'w', encoding='utf-8') as f:
    json.dump(obj, f, sort_keys=True, indent=2)
    f.write('\n')
os.chmod(path, 0o600)
LOCAL_RESULT_JSON
  fi
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    if gh pr comment "$PR" -R "$REPO" --body "$report" >/dev/null 2>&1; then
      print "AUTO_GITHUB_REPORT_POSTED: https://github.com/$REPO/pull/$PR"
    else
      print 'AUTO_GITHUB_REPORT_FAILED: local structured result retained.'
    fi
  else
    print 'AUTO_GITHUB_REPORT_UNAVAILABLE: gh authentication or network unavailable.'
  fi
  print "RESULT=${verdict} PHASE=${PHASE} EXIT_CODE=${rc} LOCAL_RESULT=${RESULT_JSON}"
  exit "$rc"
}
trap report_exit EXIT

umask 077
mkdir -p "$HOME/Library/Logs" "$DATA/releases"
chmod 700 "$DATA/releases"
exec > >(tee -a "$LOG") 2>&1
print 'REPAIR_V44_START'

command -v gh >/dev/null || { print 'BLOCKED: gh CLI not installed'; exit 2; }
command -v python3 >/dev/null || { print 'BLOCKED: Python3 unavailable'; exit 2; }
command -v git >/dev/null || { print 'BLOCKED: git unavailable'; exit 2; }
test -f "$PLIST" || { print 'BLOCKED: no existing LaunchAgent plist'; exit 2; }
test -d "$DATA/tcc-compiler/.git" || { print 'BLOCKED: pinned TCC not installed'; exit 2; }
gh auth status >/dev/null 2>&1 || { print 'BLOCKED: gh not authenticated'; exit 2; }

PHASE='VERIFY_REMOTE_SOURCE_PIN'
# Prove the remote branch has not changed since it was inspected in this chat.
REMOTE_HEAD=$(gh api "repos/$REPO/git/ref/heads/$BRANCH" --jq '.object.sha')
[[ "$REMOTE_HEAD" == "$PIN" ]] || { print 'BLOCKED: source Git commit changed'; exit 3; }
PR_HEAD=$(gh api "repos/$REPO/pulls/$PR" --jq '.head.sha')
[[ "$PR_HEAD" == "$PIN" ]] || { print 'BLOCKED: PR source changed'; exit 3; }

PHASE='DOWNLOAD_PINNED_REPOSITORY'
if [[ ! -d "$STAGE/.git" ]]; then
  [[ ! -e "$STAGE" ]] || { print 'BLOCKED: staging path occupied'; exit 3; }
  gh repo clone "$REPO" "$STAGE" -- --quiet
fi
git -C "$STAGE" fetch -q origin "$BRANCH"
git -C "$STAGE" checkout -q --detach "$PIN"
[[ "$(git -C "$STAGE" rev-parse HEAD)" == "$PIN" ]] || exit 3
print 'SOURCE_GIT_PIN_PASS'

PHASE='RUN_REGRESSION_AND_FULL_SUITE'
# No real Codex jobs are launched during these tests. Pinned upstream source is read-only.
(
 cd "$STAGE"
 export PYTHONPATH="$STAGE" TCC_COMPILER_ROOT="$DATA/tcc-compiler"
 python3 -m compileall -q initiative_dispatcher
 python3 -m unittest discover -s tests -p 'test_*rca_v44.py' -v
 python3 -m unittest discover -s tests -p 'test_*.py' -v
)
TEST_STATUS='FULL_SUITE_PASS'
print 'FULL_TEST_SUITE_PASS'

PHASE='VERIFY_NO_RUNNING_HOST_JOBS'
# Verify all other host claims are inactive, and target queue has not been claimed.
# The previously queued V41 is now DONE with a signed PASS receipt.
# DO NOT supersede it: completed evidence must remain immutable. The old branch
# stays available for a genuinely unclaimed QUEUED case, without changing ACs.
V41_TARGET_STATE=$(python3 - "$REPO" "$OLD_ID" "$OLD_RID" <<'VERIFY_CLAIMS'
import base64,json,subprocess,sys
repo,old,rid=sys.argv[1:]
def api(path):
    p=subprocess.run(['gh','api',f'repos/{repo}/{path}'],capture_output=True,text=True,check=True)
    return json.loads(p.stdout)
entries=api('contents/state')
for entry in entries:
    if entry.get('type')!='file' or not entry.get('name','').endswith('.json'):continue
    d=api(f'contents/{entry["path"]}')
    v=json.loads(base64.b64decode(d['content']))
    if v.get('status') in ('RUNNING','VERIFYING'):
        raise SystemExit('BLOCKED: an initiative has a live RUNNING/VERIFYING ownership claim')
    if v.get('status')=='QUEUED' and v.get('id')!=old:
        raise SystemExit('BLOCKED: another initiative is QUEUED; review scheduling first')
v=api(f'contents/state/{old}.json')
s=json.loads(base64.b64decode(v['content']))
if s.get('status') == 'DONE':
    receipt=api(f'contents/receipts/{old}/{rid}.json')
    r=json.loads(base64.b64decode(receipt['content']))
    checks=r.get('checks') or []
    if not(s.get('active_run') is None and s.get('acs',{}).get('AC-01')=='COMPLETE'
      and r.get('outcome')=='COMPLETE' and r.get('exit_code')==0
      and r.get('run_id')==rid and r.get('signature')
      and any(x.get('path')=='proof.txt' and x.get('pass') is True for x in checks)):
        raise SystemExit('BLOCKED: prior DONE lacks complete signed/verifiable V41 receipt')
    print('DONE')
elif (s.get('status')=='QUEUED' and s.get('revision')==1
      and s.get('active_run')==rid and not s.get('claim_token')):
    print('QUEUED')
else:
    raise SystemExit('BLOCKED: V41 state changed or retains an active claim')
VERIFY_CLAIMS
)
[[ "$V41_TARGET_STATE" == 'DONE' || "$V41_TARGET_STATE" == 'QUEUED' ]] || { print 'BLOCKED: unexpected V41 preflight result'; exit 3; }
print "V41_VERIFIED_EXISTING_STATE=$V41_TARGET_STATE"

PHASE='MERGE_TESTED_REPAIR_PR'
# Switch repository code only after regression success; no GitHub Actions is enabled by this script.
# Do not delete the repair branch or rewrite completed-history evidence.
gh pr ready "$PR" -R "$REPO" >/dev/null
gh pr merge "$PR" -R "$REPO" --merge >/dev/null
MERGE_STATUS='MERGED'
print 'GITHUB_CODE_MERGE_PASS'

if [[ "$V41_TARGET_STATE" == 'DONE' ]]; then
  # Successful V41 is an historical native TCC control receipt; do not forge
  # SUPERSEDED and do not rerun its completed AC.
  V41_STATUS='ALREADY_DONE_SIGNED_RECEIPT_PRESERVED'
  print 'V41_DONE_SIGNED_RECEIPT_PRESERVED'
else
PHASE='SUPERSEDE_UNCLAIMED_V41_WITH_CAS'
# Authorized, CAS-guarded supersession: old v41 was a control-only dead graph.
# Never write DONE, alter original_fingerprint/acs, or delete queued/receipt files.
python3 - "$REPO" "$OLD_ID" "$OLD_RID" <<'CAS_SUPERSEDE'
import base64,json,subprocess,sys,time
repo,iid,rid=sys.argv[1:]
path=f'repos/{repo}/contents/state/{iid}.json'
def call(*args, input=None):
    r=subprocess.run(['gh','api',*args],capture_output=True,text=True,input=input)
    if r.returncode:raise SystemExit('BLOCKED: GitHub CAS API failed: '+r.stderr[:250])
    return json.loads(r.stdout)
item=call(path);v=json.loads(base64.b64decode(item['content']))
if not(v.get('status')=='QUEUED' and v.get('revision')==1 and v.get('active_run')==rid and not v.get('claim_token')):
    raise SystemExit('BLOCKED: V41 state changed after preflight; no CAS performed')
receipt_path=f'repos/{repo}/contents/receipts/{iid}/{rid}.json'
probe=subprocess.run(['gh','api',receipt_path],capture_output=True,text=True)
if probe.returncode==0 or not ('HTTP 404' in probe.stderr or '404 Not Found' in probe.stderr):
    raise SystemExit('BLOCKED: receipt unexpectedly exists or cannot be verified missing')
v.update(status='SUPERSEDED',active_run=None,
         superseded_by='docs/ISSUE1_NATIVE_TCC_SPEC_V42_INPUT.json',
         revision=v['revision']+1,timestamp=time.time())
v['history']=(v.get('history',[])+[{'event':'SUPERSEDED','run':rid,'at':time.time(),
                                  'reason':'V41_UNPRODUCED_ACTUAL_ENGINE_GATE'}])[-20:]
payload={'message':'Safely supersede unreachable V41 control-only queue; preserve all original and receipt evidence',
         'sha':item['sha'],'content':base64.b64encode((json.dumps(v,sort_keys=True,indent=2)+'\n').encode()).decode()}
call('-X','PUT',path,'--input','-',input=json.dumps(payload))
print('V41_SUPERSEDED_BY_CAS_PASS')
CAS_SUPERSEDE

V41_STATUS='SUPERSEDED_BY_CAS'
fi
PHASE='RECONFIGURE_PRIVATE_LAUNCHAGENT'
# Install new receiver source in an isolated pinned checkout, without editing old working-tree files.
BACKUP="$DATA/receiver-v44-prechange.plist"
[[ ! -e "$BACKUP" ]] || { print 'BLOCKED: prior backup present, not overwriting'; exit 4; }
cp -p "$PLIST" "$BACKUP"
python3 - "$PLIST" "$STAGE" <<'UPDATE_PLIST'
import os,plistlib,sys,tempfile
from pathlib import Path
p=Path(sys.argv[1]);stage=Path(sys.argv[2])
with p.open('rb') as f:plist=plistlib.load(f)
args=plist.get('ProgramArguments',[])
if plist.get('Label')!='com.local.initiative-dispatcher' or len(args)<3 or args[1]!='-m' or args[2]!='initiative_dispatcher.tcc_runner':
    raise SystemExit('BLOCKED: LaunchAgent program differs from pinned installer contract')
args[2]='initiative_dispatcher.host_diagnostics'
plist['ProgramArguments']=args
plist['WorkingDirectory']=str(stage)
fd,name=tempfile.mkstemp(prefix='v44-plist-',suffix='.plist',dir=str(p.parent))
try:
 with os.fdopen(fd,'wb') as f:plistlib.dump(plist,f)
 os.chmod(name,0o600)
 os.replace(name,p)
finally:
 if os.path.exists(name):os.unlink(name)
print('NEW_PLIST_VERIFIED_WRITTEN')
UPDATE_PLIST
plutil -lint "$PLIST"

PHASE='RESTART_PRIVATE_LAUNCHAGENT'
# This only restarts the existing user-owned receiver. Restores plist if launchctl fails.
if ! launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null; then
  print 'BLOCKED: could not bootout current agent; restoring original plist'
  cp -p "$BACKUP" "$PLIST"
  exit 4
fi
if ! launchctl bootstrap "gui/$(id -u)" "$PLIST"; then
  print 'BLOCKED: bootstrap failed; restoring old plist'
  cp -p "$BACKUP" "$PLIST"
  launchctl bootstrap "gui/$(id -u)" "$PLIST" || true
  exit 5
fi
launchctl print "gui/$(id -u)/com.local.initiative-dispatcher" >/dev/null
MAC_STATUS='LAUNCHAGENT_REGISTERED'
PHASE='COMPLETED'
print 'HOST_LAUNCHAGENT_V44_REGISTERED'

# The EXIT handler uploads the final structured success OR failure status to the PR.
print 'RCA_V44_APPLIED; original scientific MVP remains 2/18.'
