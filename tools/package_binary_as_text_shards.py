#!/usr/bin/env python3
import argparse, base64, hashlib, json
from pathlib import Path


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser(description='Package any binary as GitHub-safe UTF-8 Base64 shards.')
    ap.add_argument('input', type=Path)
    ap.add_argument('output_dir', type=Path)
    ap.add_argument('--shard-mib', type=int, default=4)
    args = ap.parse_args()

    src = args.input
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    shard_size = args.shard_mib * 1024 * 1024
    whole = hashlib.sha256()
    shards = []
    total = 0

    with src.open('rb') as f:
        i = 0
        while True:
            raw = f.read(shard_size)
            if not raw:
                break
            whole.update(raw)
            total += len(raw)
            encoded = base64.b64encode(raw).decode('ascii')
            name = f'part-{i:04d}.b64'
            (out / name).write_text(encoded + '\n', encoding='ascii')
            shards.append({
                'index': i,
                'file': name,
                'decoded_size': len(raw),
                'sha256': sha256_bytes(raw),
            })
            i += 1

    manifest = {
        'schema_version': 1,
        'source_filename': src.name,
        'total_size': total,
        'sha256': whole.hexdigest(),
        'encoding': 'base64',
        'shard_size_bytes': shard_size,
        'shard_count': len(shards),
        'shards': shards,
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
