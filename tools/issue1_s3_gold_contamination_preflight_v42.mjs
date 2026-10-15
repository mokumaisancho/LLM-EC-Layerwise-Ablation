#!/usr/bin/env node
// V42 fixes source-defined gold-leakage; cryptographic alias mapping MUST remain private to scorer.
import fs from "node:fs";
import crypto from "node:crypto";
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
const blob=(b)=>crypto.createHash("sha1").update(Buffer.concat([Buffer.from("blob "+b.length+"\0"),b])).digest("hex");
if(process.argv[1]?.endsWith("issue1_s3_gold_contamination_preflight_v42.mjs")){
try{
if(process.argv.length!==5)throw Error("USAGE: node this.mjs generator.py canonical.py s2_input.json");
const b=process.argv.slice(2).map(x=>fs.readFileSync(x));
if(blob(b[0])!=="26bf4a57451769f0a1b617687abe216f773faa8f"||blob(b[1])!=="e354884f20a534a3be429ffdcff5f72135472436")throw Error("SOURCE_BLOB_DRIFT");
const original=JSON.parse(b[2]),aliases=Object.fromEntries(original.candidates.map(x=>[x.candidate_id,"c_"+crypto.randomBytes(16).toString("hex")]));
const out=clean(original,aliases);
fs.writeFileSync("s3_predictor_visible_v42.json",JSON.stringify(out,null,2)+"\n",{flag:"wx",mode:0o600});
fs.writeFileSync("s3_PRIVATE_alias_map_v42.json",JSON.stringify({aliases,source_sha256:crypto.createHash("sha256").update(b[2]).digest("hex")},null,2)+"\n",{flag:"wx",mode:0o600});
console.log(JSON.stringify({audit:inspect(b[0].toString(),b[1].toString()),predictor_payload_sha256:crypto.createHash("sha256").update(fs.readFileSync("s3_predictor_visible_v42.json")).digest("hex"),actual_LLM_EC_run:false}));
}catch(e){console.error(String(e));process.exitCode=3}
}
