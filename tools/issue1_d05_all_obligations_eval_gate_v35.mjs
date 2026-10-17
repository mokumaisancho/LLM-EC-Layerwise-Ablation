#!/usr/bin/env node
// v35: Source-complete task policy and publisher NL assertions gate.
// Actual independent signature verification must be handled by a separately pinned trusted verifier.
import fs from "node:fs";
import crypto from "node:crypto";
export const evaluate=function evaluate(p,c,proposal,authority){
const reject=why=>{throw Error("REJECT:"+why)};
if(p?.schema!=="ISSUE1_S4_SOURCE_BOUND_OBLIGATION_POINTERS_V20"||c?.schema!=="ISSUE1_EXTERNAL_FULL_POLICY_SCOPE_V30"||p.cases?.length!==164||c.overall?.task_count!==164)reject("SOURCE_SCOPE");
if(p.source?.commit!==c.commit||p.source?.pins?.airline?.git_blob!=="a18c17a1619ab1b78370ac0bc5f0e4df46cff5b9"||p.source?.pins?.retail?.git_blob!=="2c6373d7ab16cf1b9543043d31d87f0daf292d92")reject("SOURCE_PINS");
const byId=new Map(p.cases.map(x=>[x.case_id,x]));
if(byId.size!==164)reject("DUPLICATE_SOURCE_CASES");
if(proposal===null||proposal===undefined)return {verdict:"BLOCKED_AUTHORITY_REQUIRED",scientific_promotion:0,cases:164,nl_assertions:135,nl_only_cases:7,case_proof_count:0};
if(!proposal.case_id||!byId.has(proposal.case_id))reject("UNKNOWN_CASE");
const d=proposal.case_id.split("/")[0],orig=byId.get(proposal.case_id),pdom=c.domains?.[d];
if(!pdom||proposal.source_task_blob!==orig.source_git_blob||proposal.source_policy_blob!==pdom.policy.blob_sha)reject("CASE_SOURCE_DRIFT");
if(!Array.isArray(proposal.line_reviews))reject("INCOMPLETE_POLICY_ROWS");
const universe=pdom.policy.nonempty_lines.map(x=>x.line),set=new Set(universe),seen=new Set(),applicable=[];
if(proposal.line_reviews.length!==set.size)reject("POLICY_LINE_COVERAGE");
for(const x of proposal.line_reviews){
if(!set.has(x.line)||seen.has(x.line))reject("EXTRA_OR_DUPLICATE_LINE");
seen.add(x.line);
if(!["NOT_APPLICABLE","NON_NORMATIVE","MANDATORY","PROHIBITED","UNKNOWN"].includes(x.disposition)||typeof x.source_reason!=="string"||!x.source_reason.trim())reject("UNJUSTIFIED_OR_BAD_DISPOSITION");
if(x.disposition==="UNKNOWN")return {verdict:"BLOCKED_UNRESOLVED_POLICY",scientific_promotion:0,case_id:proposal.case_id};
if(["MANDATORY","PROHIBITED"].includes(x.disposition))applicable.push(x);
}
if(seen.size!==set.size)reject("OMITTED_POLICY_LINE");
const required=orig.nl_assertions.map(x=>x.assertion_id);
const ids=proposal.nl_judgments?.map(x=>x.assertion_id);
if(!Array.isArray(ids)||ids.length!==required.length||new Set(ids).size!==ids.length||ids.some(id=>!required.includes(id)))reject("NATURAL_LANGUAGE_JUDGMENT_MISSING");
if(proposal.nl_judgments.some(x=>typeof x.passed!=="boolean"||typeof x.evidence_ref!=="string"||!x.evidence_ref))reject("UNVERIFIED_NL_JUDGMENT");
if(proposal.nl_judgments.some(x=>x.passed===false))return {verdict:"FAIL_PUBLISHER_NL",scientific_promotion:0,case_id:proposal.case_id};
if(applicable.length===0 && (proposal.empty_set_proof?.verified!==true||!proposal.empty_set_proof?.source_ref))reject("NO_POSITIVE_ZERO_PROOF");
if(applicable.length>0){
 const verdicts=proposal.obligation_judgments;
 if(!Array.isArray(verdicts)||verdicts.length!==applicable.length||new Set(verdicts.map(x=>x.line)).size!==applicable.length||verdicts.some(x=>!applicable.some(y=>y.line===x.line)||typeof x.satisfied!=="boolean"||!x.trace_ref))reject("OBLIGATION_JUDGMENT_MISMATCH");
 if(verdicts.some(x=>!x.satisfied))return {verdict:"FAIL_REQUIRED_OBLIGATION",scientific_promotion:0,case_id:proposal.case_id};
}
if(!proposal.upstream_S1_SHA||!proposal.upstream_S2_SHA||!proposal.upstream_S3_SHA||!proposal.actual_agent_trajectory_sha)reject("MISSING_EXECUTION_BINDING");
if(!authority || authority.independent_issuer_attested!==true || authority.cryptographic_signature_verified!==true || authority.evaluator_separate_from_predictor!==true|| authority.source_policy_and_task_review_complete!==true)return {verdict:"BLOCKED_INDEPENDENT_AUTHORITY",case_id:proposal.case_id,source_scoped_structural_pass:true,scientific_promotion:0};
return {verdict:"FORMAL_PROOF_STRUCTURALLY_COMPLETE",case_id:proposal.case_id,source_scoped_structural_pass:true,scientific_promotion:0,warning:"This function cannot verify issuer or custody. Calling code must independently verify signature and trust anchor; this does not certify scientific S4."};
};
function blob(b){return crypto.createHash("sha1").update(Buffer.concat([Buffer.from("blob "+b.length+String.fromCharCode(0)),b])).digest("hex");}
if(process.argv[1]?.endsWith("issue1_d05_all_obligations_eval_gate_v35.mjs")){
 try{
  if(process.argv.length!==5)throw Error("Usage: node gate.mjs v20-inventory.json v30-policy-universe.json case_proposal.json");
  const a=fs.readFileSync(process.argv[2]),b=fs.readFileSync(process.argv[3]);
  if(blob(a)!=="a78df93af631f07b284dc3c8c74594f6989fbb6b"||blob(b)!=="c918e3fccbcd9a563b6f0af594dd2e0b138f8ca1")throw Error("SOURCE_BLOB_DRIFT");
  const c=JSON.parse(fs.readFileSync(process.argv[4],"utf8"));
  // No external trust key is enrolled. This CLI MUST NOT infer trusted authority from caller JSON.
  const result=evaluate(JSON.parse(a),JSON.parse(b),c,null);
  console.log(JSON.stringify(result,null,2));
  process.exitCode=2;
 }catch(e){console.error(String(e));process.exitCode=3;}
}
