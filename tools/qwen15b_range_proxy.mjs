import http from 'node:http';

const PORT = Number(process.env.PORT || 10000);
const BODY = Buffer.from(JSON.stringify({
  ok: true,
  state: 'STOPPED',
  reason: 'temporary Qwen 1.5B range proxy neutralized after Phase1 build-phase assay completed',
  canonical_result: 'results/phase1_qwen25_1p5b_reframe_actual_2026-10-03.json'
}));

http.createServer((_req, res) => {
  res.writeHead(200, {
    'content-type': 'application/json',
    'content-length': String(BODY.length),
    'cache-control': 'no-store'
  });
  res.end(BODY);
}).listen(PORT, () => console.log(`qwen15b range proxy STOPPED on ${PORT}`));
