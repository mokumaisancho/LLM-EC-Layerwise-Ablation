// Issue #1 S4 fail-closed preflight; not a semantic judge, not a scientific AC promotion.
// Run: node tools/issue1_s4_scoring_integrity_gate_v24.mjs <V20.json> <V21.json>.
import {readFileSync} from "node:fs";
import {createHash} from "node:crypto";
export const audit = function audit(v20,v21,pins) {
  const fail=(why)=>{throw new Error("FAIL_CLOSED:"+why)};
  const check=(ok,why)=>{if(!ok)fail(why)};
  check(pins.v20=== "a78df93af631f07b284dc3c8c74594f6989fbb6b","V20_SOURCE_PIN");
  check(pins.v21=== "8235c07ef2cc2655ea6da43e266ff59bea5bf8f9","V21_SOURCE_PIN");
  check(v20.schema==="ISSUE1_S4_SOURCE_BOUND_OBLIGATION_POINTERS_V20","V20_SCHEMA");
  check(v21.schema==="ISSUE1_S4_POLICY_SOURCE_LINE_POINTERS_V21","V21_SCHEMA");
  check(Array.isArray(v20.cases)&&v20.cases.length===164,"CASE_COUNT");
  check(Array.isArray(v21.policy_case_source_links)&&v21.policy_case_source_links.length===164,"POLICY_LINK_COUNT");
  check(v21.source.v20_task_blob===pins.v20,"CROSS_SOURCE_REFERENCE");
  const byId=new Map();
  const uniqueAssertions=new Set();
  let assertions=0,nlTask=0,high=0;
  const priority=[];
  for(const c of v20.cases) {
    check(typeof c.case_id==="string"&&!byId.has(c.case_id),"DUPLICATE_OR_INVALID_CASE_ID");
    byId.set(c.case_id,c);
    check(["airline","retail"].includes(c.publisher_domain),"UNKNOWN_DOMAIN");
    check(c.policy_obligation_inventory_attested===false && c.blind_evaluator_attested===false && c.real_task_close_authorized===false,"SELF_ATTESTED_CLOSE");
    check(Number.isInteger(c.expected_action_count)&&c.expected_action_count>=0,"ACTION_COUNT");
    check(Number.isInteger(c.expected_communication_count)&&c.expected_communication_count>=0,"COMM_COUNT");
    check(Array.isArray(c.nl_assertions),"ASSERTION_FORMAT");
    if(c.nl_assertions.length) {
      nlTask++;
      for(const x of c.nl_assertions) {
        check(typeof x.assertion_id==="string"&&!uniqueAssertions.has(x.assertion_id)&&typeof x.text==="string"&&x.text.trim(),"ASSERTION_INTEGRITY");
        uniqueAssertions.add(x.assertion_id); assertions++;
      }
      const nlOnly=c.expected_action_count===0&&c.expected_communication_count===0;
      if(nlOnly) high++;
      priority.push({case_id:c.case_id,priority:nlOnly?"P0_NO_ALTERNATE_REWARD":"P1_NL_REWARD_OMITTED",explicit_assertion_count:c.nl_assertions.length,expected_actions:c.expected_action_count,expected_communications:c.expected_communication_count,source_git_blob:c.source_git_blob});
    }
  }
  const visited=new Set();
  for(const link of v21.policy_case_source_links) {
    check(byId.has(link.case_id)&&!visited.has(link.case_id),"ORPHAN_DUPLICATE_POLICY_LINK");
    visited.add(link.case_id);
    const c=byId.get(link.case_id);
    check(link.domain===c.publisher_domain&&link.task_source_git_blob===c.source_git_blob,"SOURCE_LINK_MISMATCH");
    check(link.policy_git_blob===v21.policy[link.domain].source_git_blob,"POLICY_SHA_MISMATCH");
    check(link.all_source_policy_clauses_semantically_bound===false && link.independently_exhaustive_policy_obligations===false,"UNPROVEN_EXHAUSTIVENESS_ATTESTED");
  }
  check(assertions===135&&nlTask===58&&high===7,"PUBLISHER_ASSERTION_INVENTORY_DRIFT");
  check(v20.summary.tasks===164&&v20.summary.explicit_nl===135&&v20.summary.nl_only===7,"PUBLISHED_SUMMARY_DRIFT");
  check(v20.scope_limits.default_reward_basis_skips_NL===true&&v20.scope_limits.independent_NL_judge_executed===false,"UNVERIFIED_SCORING_ASSUMPTION");
  check(v21.policy.airline.mechanical_candidate_policy_lines.length===45&&v21.policy.retail.mechanical_candidate_policy_lines.length===29,"POLICY_CANDIDATE_COUNT_DRIFT");
  priority.sort((x,y)=>x.priority.localeCompare(y.priority)||x.case_id.localeCompare(y.case_id,undefined,{numeric:true}));
  return {schema:"ISSUE1_S4_SCORING_INTEGRITY_GATE_V24",source:{research_repo:"mokumaisancho/LLM-EC-Layerwise-Ablation",v20_blob:pins.v20,v21_blob:pins.v21,publisher_repo:v20.source.repository,publisher_commit:v20.source.commit},control:"PASS",scientific_terminal:"BLOCKED_EXTERNAL",scientific_root_AC:{passed:2,required:18,promoted:0},independent_all_obligation_s4_qualified:false,reason:"Publisher-declared NL assertions are outside default scoring; no independent per-case all-policy inventory/judge or authenticated semantic completeness. Structural source checks cannot certify real-world closure.",observations:{total_tasks:164,nl_explicit_tasks:58,nl_assertions:135,nl_only_high_risk:7,tasks_without_explicit_nl:106,policy_candidate_lines:{airline:45,retail:29},cases_independently_complete:0},critical_cases:priority.filter(x=>x.priority.startsWith("P0")),remaining_nl_cases:priority.filter(x=>x.priority.startsWith("P1")).map(x=>x.case_id),next_science_dependency:["D04: blind independent S3 all-admissible gold","D05: independent task+policy exhaustive obligations, authenticated judge including NL_ASSERTION in scoring, positive proof for empty obligation set","D06: real source-pinned original LLM/EC/Oracle target-only receipts","D07: matched 8-arm replay","D08: scoring and counterfactuals","D09: frozen 18 AC decision"],never_auto_promote:true};
};
function gitBlob(bytes){return createHash("sha1").update(Buffer.concat([Buffer.from("blob "+bytes.length+String.fromCharCode(0)),bytes])).digest("hex");}
if(process.argv[1]?.endsWith("issue1_s4_scoring_integrity_gate_v24.mjs")){
  try{
    if(process.argv.length!==4)throw Error("require two pinned JSON paths");
    const raw20=readFileSync(process.argv[2]),raw21=readFileSync(process.argv[3]);
    const result=audit(JSON.parse(raw20),JSON.parse(raw21),{v20:gitBlob(raw20),v21:gitBlob(raw21)});
    console.log(JSON.stringify(result,null,2));
    process.exitCode=2; // structural validation PASS but science BLOCKED_EXTERNAL
  }catch(e){console.error(String(e));process.exitCode=3;}
}
