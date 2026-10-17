#!/usr/bin/env node
// Audits original frozen 18 AC vs later auxiliary 11AC. Does NOT promote any scientific AC.
import fs from "node:fs";
import crypto from "node:crypto";
export const audit=function audit(ac,n,a,q){
const need=(cond,code)=>{if(!cond)throw Error("REJECT:"+code)};
const frozen=["AC-01","AC-02","AC-03","AC-04","AC-05","AC-06","AC-07","AC-08","AC-09","AC-11","AC-12","AC-13","AC-14","AC-15","AC-16","AC-17","AC-19","AC-20"];
need(n?.protocol==="PHASE1_MVP_TCC_V1"&&JSON.stringify(n.mvp?.required_ac)===JSON.stringify(frozen),"ORIGINAL_AC_SET");
need(ac.includes("fixed fixtures plus a lightweight model, EC, and Oracle are sufficient")&&ac.includes("AC-17.")&&ac.includes("AC-12."),"ORIGINAL_TEXT");
need(n.frozen_thresholds?.oracle_substitution_gain_material_abs===0.20&&n.frozen_thresholds?.dominant_tie_max_difference===0.10,"FROZEN_THRESHOLD");
need(n.canonical_inputs?.phase1_v2_dataset_sha256==="8bfce027bdc82a34b78e9b1a87f7812d907db34c164f50a9a996bd41b3b824d6","ORIGINAL_FIXTURE_DIGEST");
need(q?.fixture_count===10&&q.dataset_digest===n.canonical_inputs.phase1_v2_dataset_sha256&&q.oracle_replay?.status==="PASS"&&q.oracle_replay?.fixtures_passed===10&&q.oracle_replay?.fixtures_total===10&&q.leakage_gate?.status==="PASS","FROZEN_FIXTURE_QUALIFICATION");
need(a?.schema==="issue1-independent-proof.ac.v1"&&a.proof_package_mvp?.AC_count===11&&a.normative_contract?.original_required_AC===18&&a.proof_package_mvp.distinction.includes("not original 18-AC"),"AUXILIARY_NOT_NORMATIVE");
need(a.acceptance_criteria?.some(x=>x.id==="P02"&&x.pass.includes(">=120"))&&a.acceptance_criteria?.some(x=>x.id==="B02"&&x.pass.includes("Krippendorff"))&&a.acceptance_criteria?.some(x=>x.id==="C04"&&x.pass.includes(">=300")),"AUXILIARY_EXTENSIONS");
need(n.issue_dependencies&&!Object.keys(n.issue_dependencies).some(k=>k==="ISSUE-59"||k==="ISSUE-60"),"NEW_DEPENDENCY_MASQUERADING_AS_ORIGINAL");
return {schema:"ISSUE1_INDEPENDENCE_CRITERIA_AUDIT_V37",original_science_mvp:{total:18,proven:2,promoted:0,materiality:0.20,prequalified_fixture_count:q.fixture_count,oracle_replay:q.oracle_replay.status},root_dependencies:Object.keys(n.issue_dependencies),extension_11ac_non_normative:true,incorrect_blockers:["THIRD_PARTY_CRYPTO_SIGNATURE_MANDATORY","HUMAN_TWO_RATER_ALPHA_MANDATORY","120_UNSEEN_ITEMS_MANDATORY","300_NEGATIVE_100_POSITIVE_S4_MANDATORY","14778_PAIRWISE_POLICY_REVIEWS_MANDATORY","EVERY_POSSIBLE_UNKNOWN_OBLIGATION_MUST_BE_PROVEN_ABSENT"],required_phase1:["SOURCE_FROZEN_GOLD_SEPARATE_FROM_PREDICTOR","NO_ORACLE_LABEL_LEAKAGE","SAME_UPSTREAM_PER_COMPARISON","ACTUAL_EC_AND_LLM_ENGINES","S3_CANDIDATEWISE_SCORING","BOUNDED_S4_RESIDUAL_AND_FALSE_CLOSE_SCORING","REAL_TARGET_ONLY_A_B_C_D_E_ORACLE_INTERVENTIONS","UNCHANGED_THRESHOLD_0_20"],three_claims:{fixed_fixture_diagnostic:"ALLOWED_ON_FROZEN_SOURCE_AND_ACTUAL_ENGINES",external_generalization:"REQUIRES_SEPARATE_UNSEEN_DATA",third_party_blind_human_study:"OPTIONAL_ADDITIONAL_STUDY"},readiness:{original_10_fixtures:"SOURCE_AND_ORACLE_REPLAY_VERIFIED",actual_EC_native_qualifications:"NOT_ESTABLISHED_BY_THIS_AUDIT",four_layer_real_AE:"NOT_ESTABLISHED_BY_THIS_AUDIT",D04_D05_robust_external_authority:"UNPROVEN"},finding:"A later 11-AC external blind-research standard was promoted to an additional strict prerequisite although frozen 18-AC original MVP explicitly permits 10 fixed fixtures; scoping error rather than evidence the user must recruit a signed reviewer."};
};
const expected=["40e4d41914fb17ee5c7deb0cfd32276a41c9a1fc","08407bec73278aeda8ddd2d4d6efc810dadf46f9","c3a27b518ba42cc8bf41c91bacaf78baf5efcaef","7eca5217c608efb4982a15bd2969004a9d3f9537"];
function blob(b){return crypto.createHash("sha1").update(Buffer.concat([Buffer.from("blob "+b.length+String.fromCharCode(0)),b])).digest("hex")}
if(process.argv[1]?.endsWith("issue1_independence_criteria_audit_v37.mjs")){
 try{if(process.argv.length!==6)throw Error("USAGE: node this.mjs AC.md normative.json auxiliary.json qualification.json");
 const inp=process.argv.slice(2).map((path,i)=>{const b=fs.readFileSync(path);if(blob(b)!==expected[i])throw Error("SOURCE_BLOB_DRIFT:"+i);return b.toString("utf8")});
 console.log(JSON.stringify(audit(inp[0],JSON.parse(inp[1]),JSON.parse(inp[2]),JSON.parse(inp[3])),null,2));
 }catch(e){console.error(String(e));process.exitCode=3}
}
