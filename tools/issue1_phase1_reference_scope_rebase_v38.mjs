#!/usr/bin/env node
// v38: Evaluate original Phase1 reference readiness separately from optional extended generalization.
// NO downstream engine can be promoted from source qualification or self-asserted receipt flags.
import fs from "node:fs";
import crypto from "node:crypto";
export const decision=function decision(C,E,Q,claims){
 const require=(x,m)=>{if(!x)throw Error("REJECT:"+m)};
 require(C.protocol==="PHASE1_MVP_TCC_V1"&&C.mvp.required_ac.length===18&&C.frozen_thresholds.oracle_substitution_gain_material_abs===.2,"NORMATIVE_DRIFT");
 require(Q.fixture_count===10&&Q.dataset_digest===C.canonical_inputs.phase1_v2_dataset_sha256&&Q.oracle_replay.status==="PASS"&&Q.oracle_replay.fixtures_passed===10&&Q.leakage_gate.status==="PASS","BENCHMARK_REFERENCE_INVALID");
 require(E.proof_package_mvp.AC_count===11&&E.proof_package_mvp.distinction.includes("not original 18-AC"),"EXTENDED_AC_PRIORITY_DRIFT");
 require(!Object.keys(C.issue_dependencies).some(s=>["ISSUE-59","ISSUE-60"].includes(s)),"MISSING_ORIGINAL_AUTHORITY");
 const root={original_ac_passed:2,original_ac_total:18,promoted:0,original_data_source_fixed:true,third_party_signature_gate_for_fixed_fixture:false,original_threshold:.2};
 const evals={
 D04:{fixed_fixture_reference_oracle:"READY_FOR_ACTUAL_ARMS",external_blind_generalization:"SEPARATE_UNPROVEN_TIER",gold_separate_from_predictor:"REQUIRES_RUNTIME_VERIFICATION",competing_equivalent:"M003_M009_SOURCE_FIXTURES_NOT_INDEPENDENT_HELDOUT"},
 D05:{bounded_fixture_obligations:"FROZEN_ORACLE_REPLAY_AVAILABLE",real_S4_close_accuracy:"REQUIRES_S4_EXECUTION_AND_INDEPENDENT_SCORING",full_task_policy_exhaustiveness:"UNPROVEN_FOR_TAU2",scope:"10-original-fixtures",mandatory_14778_pair_reviews:false},
 next:{must_run:["ISSUE-23_QUALIFIED_EC_NATIVE_ADAPTER","ISSUE-20_ACTUAL_EC_BINDING","ISSUE-22_TRUE_LLM_S1_S2_AND_CACHED_OUTPUTS","ISSUE-9_ACTUAL_C_D_AND_E_TARGET_ONLY","ISSUE-61_TARGET_ONLY_ENGINE_PROVENANCE_FIX","ROOT_ISSUE1_REAL_SCORING"],optional_not_phase1:["ISSUE-59_EXTENDED_BLIND_S3","ISSUE-60_EXTENDED_FULL_POLICY_S4"],status:"ACTUAL_ENGINE_AND_CAUSAL_EVIDENCE_NOT_YET_QUALIFIED"}};
 if(claims!==undefined){
 require(typeof claims==="object"&&claims!==null&&!Array.isArray(claims),"CLAIMS_FORMAT");
 if(claims.promote_original_AC===true)throw Error("REJECT:NO_REAL_AE_PROOF");
 if(claims.independent_signature_required_for_fixed_fixture===true)throw Error("REJECT:EXTRA_SIGNATURE_NOT_NORMATIVE");
 if(claims.all_policy_lines_every_task_required_for_fixed_fixture===true)throw Error("REJECT:EXTENDED_SCOPE_NOT_NORMATIVE");
 if(claims.assert_full_science_qualified===true)throw Error("REJECT:ACTUAL_ENGINES_AND_TARGET_ONLY_RECEIPTS_NOT_PROVEN");
 }
 return {schema:"ISSUE1_D04_D05_PHASE1_VS_EXTENDED_REBASE_V38",root,scopes:evals,source_criteria_priority:["2026-10-03_FROZEN_18_AC","2026-10-15_VERSIONED_REBASE","AUXILIARY_11AC_EXTENDED_ONLY"],exit_policy:"READY_FOR_REFERENCE_DOES_NOT_EQUAL_REAL_EC_LLM_AE_PASS"};
};
function blob(b){return crypto.createHash("sha1").update(Buffer.concat([Buffer.from("blob "+b.length+String.fromCharCode(0)),b])).digest("hex");}
if(process.argv[1]?.endsWith("issue1_phase1_reference_scope_rebase_v38.mjs")){
try{
if(process.argv.length!==5)throw Error("USAGE: node script.mjs normative.json auxiliary.json qualification.json");
const pins=["08407bec73278aeda8ddd2d4d6efc810dadf46f9","c3a27b518ba42cc8bf41c91bacaf78baf5efcaef","7eca5217c608efb4982a15bd2969004a9d3f9537"];
const d=process.argv.slice(2).map((s,i)=>{const b=fs.readFileSync(s);if(blob(b)!==pins[i])throw Error("SOURCE_PIN_DRIFT:"+i);return JSON.parse(b.toString("utf8"))});
console.log(JSON.stringify(decision(...d),null,2));
}catch(e){console.error(String(e));process.exitCode=3}
}
