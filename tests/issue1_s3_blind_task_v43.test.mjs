#!/usr/bin/env node
// Source-pinned regression for the *predictor-visible* S3 channel.
// Model/EC/Oracle execution is outside this test. Uses real Python-generated fixtures.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {spawnSync} from "node:child_process";
import crypto from "node:crypto";
import {fileURLToPath} from "node:url";
import {cleanTask} from "../tools/issue1_s3_gold_contamination_preflight_v42.mjs";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const py=path.join(root,"tools/generate_phase1_measurement_v2.py");
const canon=path.join(root,"tools/generate_phase1_measurement_v2_canonical.py");
const tool=path.join(root,"tools/issue1_s3_gold_contamination_preflight_v42.mjs");
const gitBlob=(b)=>crypto.createHash("sha1").update(Buffer.concat([Buffer.from("blob "+b.length+"\0"),b])).digest("hex");
const expected=[["M001",2],["M002",2],["M003",3],["M004",2],["M005",2],["M006",2],["M007",2],["M008",2],["M009",3],["M010",2]];
function run(exe,args,cwd){const r=spawnSync(exe,args,{cwd,encoding:"utf8",timeout:60000});assert.equal(r.status,0,`${exe} failed: ${r.stderr}`);return r.stdout}
const temp=fs.mkdtempSync(path.join(os.tmpdir(),"issue1-s3-clean-"));
test.after(()=>fs.rmSync(temp,{recursive:true,force:true}));
test("P00 source pins",()=>{
 assert.equal(gitBlob(fs.readFileSync(py)),"26bf4a57451769f0a1b617687abe216f773faa8f");
 assert.equal(gitBlob(fs.readFileSync(canon)),"e354884f20a534a3be429ffdcff5f72135472436c");
});
test("P01 ten real canonical fixtures: task rules visible, gold isolated",()=>{
 const generated=path.join(temp,"generated");
 run("python3",[canon,"--out",generated],temp);
 for(const [id,count] of expected){
   const fixture=path.join(generated,id);
   const taskFile=path.join(fixture,"input/task.json");
   const s2File=path.join(fixture,"oracle/s2_candidate_set.json");
   const task=JSON.parse(fs.readFileSync(taskFile));
   const s2=JSON.parse(fs.readFileSync(s2File));
   const work=path.join(temp,id);
   fs.mkdirSync(work);
   run("node",[tool,py,canon,taskFile,s2File],work);
   const visible=JSON.parse(fs.readFileSync(path.join(work,"s3_predictor_visible_v42.json")));
   const secret=JSON.parse(fs.readFileSync(path.join(work,"s3_PRIVATE_alias_map_v42.json")));
   assert.equal(visible.candidates.length,count,id);
   assert.equal(visible.task.prompt,task.prompt,id);
   assert.deepEqual(visible.task.facts,task.context.facts,id);
   assert.deepEqual(visible.task.domain_rules,task.context.domain_rules,id);
   assert.equal(new Set(visible.candidates.map(x=>x.candidate_id)).size,count,id);
   assert.equal(new Set(Object.values(secret.aliases)).size,count,id);
   assert.equal(secret.source_sha256,crypto.createHash("sha256").update(fs.readFileSync(s2File)).digest("hex"));
   const encoded=JSON.stringify(visible);
   assert.doesNotMatch(encoded,/oracle_constraints|acceptable_candidate_ids|fixture_id|relation_groups|Domain-rule-compatible transition|rule-incompatible transition/,id);
   for(const c of s2.candidates)assert.ok(!encoded.includes('"'+c.candidate_id+'"'),id);
   for(const c of visible.candidates)assert.match(c.candidate_id,/^c_[a-f0-9]{32}$/,id);
   assert.equal(fs.statSync(path.join(work,"s3_PRIVATE_alias_map_v42.json")).mode&0o777,0o600,id);
   assert.equal(visible.schema,"S3_SEMANTIC_PREDICTOR_INPUT_GOLD_BLIND_V43",id);
 }
});
const base={schema_version:"TASK_INPUT_V1",fixture_id:"M001",prompt:"Choose",context:{facts:["a"],domain_rules:["Require a"]}};
const s2={schema_version:"S2_CANDIDATE_SET_V1",fixture_id:"M001",candidates:[{candidate_id:"v1",semantic_transition:{operation:"SAFE"}},{candidate_id:"x1",semantic_transition:{operation:"UNSAFE"}}]};
const aliases={v1:"c_"+"1".repeat(32),x1:"c_"+"2".repeat(32)};
const reject=(id,t,s,a,o)=>test(id,()=>assert.throws(()=>cleanTask(t,s,a,o),/REJECT:/));
reject("P01 rejects unrelated task/S2", {...base,fixture_id:"M002"},s2,aliases,[1,0]);
reject("P01 rejects no domain rules",{...base,context:{facts:["a"],domain_rules:[]}},s2,aliases,[1,0]);
reject("P01 rejects repeated order index",base,s2,aliases,[1,1]);
reject("P01 rejects non-opaque alias",base,s2,{v1:"v1",x1:"x1"},[1,0]);
reject("P01 rejects oracle metadata in facts",{...base,context:{facts:["oracle_constraints=leak"],domain_rules:["r"]}},s2,aliases,[1,0]);
test("P01 permutation removes authored valid-first position hint",()=>{
 const visible=cleanTask(base,s2,aliases,[1,0]);
 assert.equal(visible.candidates[0].semantic_operation,"UNSAFE");
 assert.equal(visible.candidates[1].semantic_operation,"SAFE");
});
