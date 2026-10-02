import http from 'node:http';
import { createHash } from 'node:crypto';

const PORT = Number(process.env.PORT || 10000);
const MODEL_URL = 'https://huggingface.co/bartowski/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf';
const EXPECTED_SHA256 = '1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370';
const ALLOWED = new Set([4,8,16,32,64].map(x=>x*1024*1024));
let totalSize = null;

async function discoverSize(){
  if(totalSize!==null) return totalSize;
  const r=await fetch(MODEL_URL,{redirect:'follow',headers:{Range:'bytes=0-0','User-Agent':'phase1-qwen15b-range-proxy/1'}});
  if(r.status!==206) throw new Error(`SIZE_PROBE_STATUS_${r.status}`);
  const cr=r.headers.get('content-range')||'';
  const m=/^bytes 0-0\/(\d+)$/.exec(cr);
  if(!m) throw new Error(`SIZE_PROBE_CONTENT_RANGE:${cr}`);
  await r.arrayBuffer();
  totalSize=Number(m[1]);
  return totalSize;
}

async function part(index, partBytes){
  const size=await discoverSize();
  const total=Math.ceil(size/partBytes);
  if(!Number.isSafeInteger(index)||index<0||index>=total) throw new Error(`INVALID_INDEX:${index};total=${total}`);
  const start=index*partBytes;
  const end=Math.min(size-1,start+partBytes-1);
  const expected=end-start+1;
  const r=await fetch(MODEL_URL,{redirect:'follow',headers:{Range:`bytes=${start}-${end}`,'User-Agent':'phase1-qwen15b-range-proxy/1','Accept':'application/octet-stream'}});
  if(r.status!==206) throw new Error(`UPSTREAM_STATUS_${r.status}`);
  const cr=r.headers.get('content-range')||'';
  if(cr!==`bytes ${start}-${end}/${size}`) throw new Error(`CONTENT_RANGE_MISMATCH:${cr}`);
  const data=Buffer.from(await r.arrayBuffer());
  if(data.length!==expected) throw new Error(`LENGTH_MISMATCH:${data.length};expected=${expected}`);
  return {data,index,total,start,end,size,partBytes,sha256:createHash('sha256').update(data).digest('hex')};
}

const server=http.createServer(async(req,res)=>{
  try{
    const u=new URL(req.url,`http://${req.headers.host||'localhost'}`);
    if(u.pathname==='/health'){
      res.writeHead(200,{'content-type':'application/json'}); return res.end(JSON.stringify({ok:true,state:'READY',model:'Qwen2.5-1.5B-Instruct-Q4_K_M.gguf',expected_sha256:EXPECTED_SHA256}));
    }
    if(u.pathname==='/manifest'){
      const size=await discoverSize();
      res.writeHead(200,{'content-type':'application/json'}); return res.end(JSON.stringify({ok:true,model_url:MODEL_URL,expected_size:size,expected_sha256:EXPECTED_SHA256,part_bytes:[4,8,16,32,64].map(x=>x*1024*1024),drive_required:false}));
    }
    if(u.pathname==='/part.bin'){
      const pb=Number(u.searchParams.get('part_bytes')||16*1024*1024);
      if(!ALLOWED.has(pb)) throw new Error(`INVALID_PART_BYTES:${pb}`);
      const p=await part(Number(u.searchParams.get('index')),pb);
      res.writeHead(200,{'content-type':'application/octet-stream','content-length':String(p.data.length),'cache-control':'public,max-age=3600','x-part-index':String(p.index),'x-total-parts':String(p.total),'x-byte-start':String(p.start),'x-byte-end':String(p.end),'x-part-sha256':p.sha256,'x-model-size':String(p.size),'x-model-sha256':EXPECTED_SHA256}); return res.end(p.data);
    }
    res.writeHead(404); res.end('not found\n');
  }catch(e){res.writeHead(500,{'content-type':'text/plain'});res.end(`ERROR:${e?.message||e}\n`);}
});
server.listen(PORT,()=>console.log(`qwen15b range proxy ready on ${PORT}`));
