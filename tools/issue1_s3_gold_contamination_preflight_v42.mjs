#!/usr/bin/env node
// V42 fixes source-defined gold-leakage; cryptographic alias mapping MUST remain private to scorer.
import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";
export const inspect=function inspect(g,c){
const must=(v,m)=>{if(!v)throw Error("REJECT:"+m)};
const ids=[...g.matchAll(/"id": "(M\d{3})", "category"/g)].map(z=>z[1]);
must(ids.join()==="M001,M002,M003,M004,M005,M006,M007,M008,M009,M010","TEN_FIXTURE_SCOPE");
const signs={"positive_id_name":'cid = "v" + str(i+1)',"negative_id_name":'"candidate_id": "x1"',"published_gold_in_s2":'"acceptable_candidate_ids": acceptable',"gold_in_s3":'"acceptable_selected_candidate_ids": acceptable',"correct_claim_tag":'"Domain-rule-compatible transition."',"wrong_claim_tag":'"Plausible but rule-incompatible transition."',"correct_only_dependencies":'"dependencies": ["goal"]',"wrong_only_dependencies":'"dependencies": [], "evidence_refs": []',"correct_evidence":'"evidence_refs": ["input/task.json"]'};
for(const [k,v] of Object.entries(signs))must(g.includes(v),"MISSING_SOURCE_MARKER_"+k);
must(c.includes('if fid == "M003"')&&c.includes('elif fid == "M009"')&&c.includes('"relation_groups"'),"ORACLE_RELATION_SOURCE");
return {source_cases:10,gold_leak_keys:Object.keys(signs),trivial_v_prefix_selector_10_10_by_generator_definition:true,ten_fixture_oracle_replay_is_not_semantic_performance:true};
};
export const clean=function clean(s,aliases){
const must=(v,m)=>{if(!v)throw Error("REJECT:"+m)};
must(s?.schema_version==="S2_CANDIDATE_SET_V1"&&Array.isArray(s.candidates)&&s.candidates.length>=2,"SOURCE_S2_INVALID");
const ids=s.candidates.map(c=>c.candidate_id);
must(ids.every(x=>typeof x==="string")&&new Set(ids).size===ids.length,"SOURCE_IDS_BAD");
must(aliases&&typeof aliases==="object"&&!Array.isArray(aliases)&&Object.keys(aliases).length===ids.length&&ids.every(x=>Object.hasOwn(aliases,x)),"ALIAS_COVERAGE");
const vals=ids.map(x=>aliases[x]);
must(vals.every(x=>typeof x==="string"&&/^c_[a-f0-9]{32}$/.test(x))&&new Set(vals).size===vals.length,"ALIAS_NOT_OPAQUE");
const out={schema:"S3_BLIND_PREDICTOR_INPUT_V42",candidates:s.candidates.map(c=>{must(typeof c.semantic_transition?.operation==="string"&&c.semantic_transition.operation.length>0,"MISSING_OPERATOR");return {candidate_id:aliases[c.candidate_id],semantic_operation:c.semantic_transition.operation}})};
const enc=JSON.stringify(out);
must(ids.every(id=>!enc.includes('"'+id+'"'))&&!/oracle_constraints|acceptable_candidate_ids|fixture_id|relation_groups|Domain-rule-compatible transition|rule-incompatible transition/.test(enc),"GOLD_LEAK_REMAINS");
return out;
};
// Successor input contract: the predictor must see task facts/rules as well as
// semantic operations. V42's option-only clean() cannot measure semantic S3.
// Python generator canonical_hash equivalence (recursive lexical key ordering).
export const canonicalHash=function canonicalHash(o){
 const sort=(v)=>Array.isArray(v)?v.map(sort):(v&&typeof v==="object")?
   Object.fromEntries(Object.keys(v).sort().map(k=>[k,sort(v[k])])):v;
 const source={...o};delete source.content_hash;
 return crypto.createHash("sha256").update(JSON.stringify(sort(source)),"utf8").digest("hex");
};
export const cleanTask=function cleanTask(task,s2,aliases,order=null){
const must=(v,m)=>{if(!v)throw Error("REJECT:"+m)};
must(task?.schema_version==="TASK_INPUT_V1" && typeof task.prompt==="string" && task.prompt.trim(),"SOURCE_TASK_INVALID");
must(task.context && Array.isArray(task.context.facts) && Array.isArray(task.context.domain_rules),"TASK_CONTEXT_REQUIRED");
must(task.context.facts.every(x=>typeof x==="string") && task.context.domain_rules.every(x=>typeof x==="string"),"UNSAFE_TASK_CONTEXT");
must(task.context.domain_rules.length>0,"RULES_REQUIRED");
must(task.fixture_id===s2.fixture_id,"CROSS_FIXTURE_UPSTREAM_MISMATCH");
must(typeof s2.content_hash==="string"&&s2.content_hash===canonicalHash(s2),"S2_CONTENT_HASH_MISMATCH");
const stripped=clean(s2,aliases);
const n=stripped.candidates.length;
if(order===null){
  order=[...Array(n).keys()];
  for(let i=n-1;i>0;i--){let j=crypto.randomInt(i+1);[order[i],order[j]]=[order[j],order[i]]}
}
must(Array.isArray(order) && order.length===n && new Set(order).size===n
  && order.every(x=>Number.isInteger(x)&&x>=0&&x<n),"ORDER_NOT_PERMUTATION");
const out={
schema:"S3_SEMANTIC_PREDICTOR_INPUT_GOLD_BLIND_V43",
task:{prompt:task.prompt,facts:[...task.context.facts],domain_rules:[...task.context.domain_rules]},
candidates:order.map(i=>stripped.candidates[i])
};
const visible=JSON.stringify(out);
const forbidden=/oracle_constraints|acceptable_candidate_ids|acceptable_selected_candidate_ids|fixture_id|relation_groups|Domain-rule-compatible transition|rule-incompatible transition|measurement-author-defined/;
must(!forbidden.test(visible),"REFERENCE_LABEL_VISIBLE");
must(s2.candidates.every(c=>!visible.includes('"'+c.candidate_id+'"')),"ORIGINAL_ID_VISIBLE");
must(out.candidates.length===n && out.candidates.every(c=>/^c_[a-f0-9]{32}$/.test(c.candidate_id)),"PREDICTOR_IDS_INVALID");
return out;
};

const blob=(b)=>crypto.createHash("sha1").update(Buffer.concat([Buffer.from("blob "+b.length+"\0"),b])).digest("hex");
if(process.argv[1]?.endsWith("issue1_s3_gold_contamination_preflight_v42.mjs")){
try{
if(process.argv.length!==6)throw Error("USAGE: node this.mjs generator.py canonical.py task.json s2_input.json");
const b=process.argv.slice(2).map(x=>fs.readFileSync(x));
if(blob(b[0])!=="26bf4a57451769f0a1b617687abe216f773faa8f"||blob(b[1])!=="e354884f20a534a3be429ffdcff5f72135472436")throw Error("SOURCE_BLOB_DRIFT");
const task=JSON.parse(b[2]),original=JSON.parse(b[3]);
const fixtureDir=path.dirname(path.dirname(process.argv[4]));
const manifest=JSON.parse(fs.readFileSync(path.join(fixtureDir,"fixture_manifest.json"),"utf8"));
const must=(v,reason)=>{if(!v)throw Error("REJECT:"+reason)};
must(manifest.fixture_id===task.fixture_id && manifest.fixture_id===original.fixture_id,"FIXTURE_MANIFEST_ID_MISMATCH");
must(manifest.hashes.task===canonicalHash(task),"TASK_MANIFEST_HASH_MISMATCH");
must(manifest.hashes.s2_oracle===original.content_hash,"S2_MANIFEST_HASH_MISMATCH");
must(original.content_hash===canonicalHash(original),"S2_CONTENT_HASH_MISMATCH");
const s1=JSON.parse(fs.readFileSync(path.join(fixtureDir,"oracle/s1_domain_semantic_ir.json"),"utf8"));
must(s1.fixture_id===task.fixture_id&&s1.content_hash===canonicalHash(s1),"S1_SOURCE_HASH_MISMATCH");
must(original.semantic_ir_hash===s1.content_hash,"S2_S1_HASH_CHAIN_MISMATCH");
const aliases=Object.fromEntries(original.candidates.map(x=>[x.candidate_id,"c_"+crypto.randomBytes(16).toString("hex")]));
const out=cleanTask(task,original,aliases);
const source_sha256=crypto.createHash("sha256").update(b[3]).digest("hex");
const task_sha256=crypto.createHash("sha256").update(b[2]).digest("hex");
fs.writeFileSync("s3_predictor_visible_v42.json",JSON.stringify(out,null,2)+"\n",{flag:"wx",mode:0o600});
fs.writeFileSync("s3_PRIVATE_alias_map_v42.json",JSON.stringify({aliases,task_sha256,source_sha256},null,2)+"\n",{flag:"wx",mode:0o600});
console.log(JSON.stringify({audit:inspect(b[0].toString(),b[1].toString()),predictor_payload_sha256:crypto.createHash("sha256").update(fs.readFileSync("s3_predictor_visible_v42.json")).digest("hex"),actual_LLM_EC_run:false,task_rules_present:true,source_candidate_position_randomized:true}));
}catch(e){console.error(String(e));process.exitCode=3}
}
