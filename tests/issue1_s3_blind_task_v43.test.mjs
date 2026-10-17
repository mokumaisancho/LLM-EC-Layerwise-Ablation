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
import {cleanTask,canonicalHash} from "../tools/issue1_s3_gold_contamination_preflight_v42.mjs";

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
 assert.equal(gitBlob(fs.readFileSync(canon)),"e354884f20a534a3be429ffdcff5f72135472436");
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
s2.content_hash=canonicalHash(s2);
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

test("P01 rejects candidate semantic tampering with old content_hash",()=>{
 const altered=JSON.parse(JSON.stringify(s2));
 altered.candidates[0].semantic_transition.operation="BYPASS_CONTROL";
 assert.throws(()=>cleanTask(base,altered,aliases,[1,0]),/REJECT:S2_CONTENT_HASH_MISMATCH/);
});
test("P01 rejects an identical fixture id with modified s2 hash",()=>{
 const altered=JSON.parse(JSON.stringify(s2));
 altered.content_hash="0".repeat(64);
 assert.throws(()=>cleanTask(base,altered,aliases,[1,0]),/REJECT:S2_CONTENT_HASH_MISMATCH/);
});
test("P01 CLI refuses even recomputed S2 mutation if sealed manifest unchanged",()=>{
 const generated=path.join(temp,"generated");
 const fid="M001";
 const source=path.join(generated,fid);
 const mutateDir=path.join(temp,"mutation-original");
 fs.mkdirSync(path.join(mutateDir,"input"),{recursive:true});
 fs.mkdirSync(path.join(mutateDir,"oracle"));
 for(const f of ["input/task.json","oracle/s1_domain_semantic_ir.json","oracle/s2_candidate_set.json","fixture_manifest.json"]){fs.copyFileSync(path.join(source,f),path.join(mutateDir,f));}
 const mutated=path.join(mutateDir,"oracle/s2_candidate_set.json");
 const content=JSON.parse(fs.readFileSync(mutated));
 content.candidates[0].semantic_transition.operation="BYPASS_CONTROL";
 content.content_hash=canonicalHash(content);
 fs.writeFileSync(mutated,JSON.stringify(content));
 const work=path.join(temp,"mutation-work");fs.mkdirSync(work);
 const r=spawnSync("node",[tool,py,canon,path.join(mutateDir,"input/task.json"),mutated],{cwd:work,encoding:"utf8",timeout:60000});
 assert.equal(r.status,3,r.stdout+" / "+r.stderr);
 assert.match(r.stderr,/REJECT:S2_MANIFEST_HASH_MISMATCH/);
 assert.ok(!fs.existsSync(path.join(work,"s3_predictor_visible_v42.json")));
});
