#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import hashlib
import os
import pathlib
import subprocess
import tarfile
import urllib.request

from websockets.asyncio.server import serve

WORK = pathlib.Path('/tmp/llama-rpc-worker')
LLAMA_TAG = 'b11146'
LLAMA_FILE = 'llama-b11146-bin-ubuntu-x64.tar.gz'
LLAMA_URL = f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
LLAMA_SHA256 = 'c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'
TOKEN = os.environ['RPC_TUNNEL_TOKEN']
PUBLIC_PORT = int(os.environ.get('PORT', '10000'))
RPC_PORT = 50052


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, path: pathlib.Path) -> None:
    req = urllib.request.Request(url, headers={'User-Agent': 'phase1-rpc-worker/1'})
    with urllib.request.urlopen(req, timeout=120) as src, path.open('wb') as out:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def acquire_rpc_server() -> pathlib.Path:
    WORK.mkdir(parents=True, exist_ok=True)
    archive = WORK / LLAMA_FILE
    download(LLAMA_URL, archive)
    actual = sha256(archive)
    if actual != LLAMA_SHA256:
        raise RuntimeError(f'LLAMA_SHA_MISMATCH:{actual}')
    target = WORK / 'llama'
    with tarfile.open(archive, 'r:gz') as tf:
        tf.extractall(target, filter='data')
    matches = list(target.rglob('ggml-rpc-server'))
    if not matches:
        raise RuntimeError('RPC_SERVER_NOT_FOUND')
    matches[0].chmod(0o755)
    return matches[0]


async def tunnel(ws):
    if ws.request.path != '/' + TOKEN:
        await ws.close(code=1008, reason='unauthorized')
        return
    reader, writer = await asyncio.open_connection('127.0.0.1', RPC_PORT)
    print('RPC_TUNNEL_CONNECTED', flush=True)

    async def ws_to_tcp():
        async for message in ws:
            if isinstance(message, str):
                raise RuntimeError('TEXT_FRAME_NOT_ALLOWED')
            writer.write(message)
            await writer.drain()

    async def tcp_to_ws():
        while True:
            data = await reader.read(65536)
            if not data:
                break
            await ws.send(data)

    tasks = [asyncio.create_task(ws_to_tcp()), asyncio.create_task(tcp_to_ws())]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    writer.close()
    await writer.wait_closed()
    for task in done:
        exc = task.exception()
        if exc:
            raise exc


async def main_async():
    rpc = acquire_rpc_server()
    env = dict(os.environ)
    env['GGML_RPC_NO_RDMA'] = '1'
    proc = subprocess.Popen(
        [str(rpc), '-p', str(RPC_PORT)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    async def relay_logs():
        assert proc.stdout is not None
        while True:
            line = await asyncio.to_thread(proc.stdout.readline)
            if not line:
                break
            print('RPC_SERVER ' + line.rstrip(), flush=True)

    asyncio.create_task(relay_logs())
    await asyncio.sleep(2)
    if proc.poll() is not None:
        raise RuntimeError(f'RPC_SERVER_EXIT:{proc.returncode}')

    print(f'RPC_WSS_READY port={PUBLIC_PORT} local_rpc={RPC_PORT}', flush=True)
    async with serve(
        tunnel,
        '0.0.0.0',
        PUBLIC_PORT,
        max_size=None,
        compression=None,
        ping_interval=20,
        ping_timeout=20,
    ):
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main_async())
