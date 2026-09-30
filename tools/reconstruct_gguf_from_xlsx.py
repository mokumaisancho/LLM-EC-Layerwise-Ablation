#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def shared_strings(z: ZipFile) -> list[str]:
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return [
        "".join(t.text or "" for t in si.iter(f"{{{NS_MAIN}}}t"))
        for si in root.findall(f"{{{NS_MAIN}}}si")
    ]


def sheet_paths(z: ZipFile) -> list[tuple[str, str]]:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rel = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rel}
    out = []
    for s in wb.find(f"{{{NS_MAIN}}}sheets"):
        name = s.attrib["name"]
        rid = s.attrib[f"{{{NS_REL}}}id"]
        target = relmap[rid]
        path = target.lstrip("/") if target.startswith("/") else "xl/" + target
        out.append((name, path))
    return out


def sheet_cells(z: ZipFile, path: str, strings: list[str]) -> dict[str, str]:
    root = ET.fromstring(z.read(path))
    out: dict[str, str] = {}
    for cell in root.iter(f"{{{NS_MAIN}}}c"):
        ref = cell.attrib.get("r")
        value = cell.find(f"{{{NS_MAIN}}}v")
        if not ref or value is None:
            continue
        raw = value.text or ""
        if cell.attrib.get("t") == "s":
            raw = strings[int(raw)]
        out[ref] = raw
    return out


def reconstruct(source: Path) -> bytes:
    with ZipFile(source) as z:
        strings = shared_strings(z)
        parts: dict[int, bytes] = {}
        total_parts: int | None = None

        for name, path in sheet_paths(z):
            if name != "__COGCOMP_XFER" and not name.startswith("__COGCOMP_M_"):
                continue
            cells = sheet_cells(z, path, strings)
            for col in ("B", "D"):
                if cells.get(f"{col}1") != "MODEL":
                    continue
                index = int(float(cells[f"{col}2"]))
                total = int(float(cells[f"{col}3"]))
                start = int(float(cells[f"{col}4"]))
                end = int(float(cells[f"{col}5"]))
                length = int(float(cells[f"{col}6"]))
                expected_sha = cells[f"{col}7"]
                chunks: list[str] = []
                row = 9
                while True:
                    value = cells.get(f"{col}{row}")
                    if not value or not re.fullmatch(r"[A-Za-z0-9+/=]+", value):
                        break
                    chunks.append(value)
                    row += 1
                blob = base64.b64decode("".join(chunks), validate=True)
                if len(blob) != length:
                    raise ValueError(f"part {index}: length mismatch")
                if end - start + 1 != length:
                    raise ValueError(f"part {index}: byte range mismatch")
                if sha256(blob) != expected_sha:
                    raise ValueError(f"part {index}: sha256 mismatch")
                if index in parts:
                    raise ValueError(f"part {index}: duplicate")
                parts[index] = blob
                total_parts = total if total_parts is None else total_parts
                if total_parts != total:
                    raise ValueError("inconsistent total_parts")

    if total_parts is None:
        raise ValueError("no MODEL parts found")
    missing = sorted(set(range(total_parts)) - set(parts))
    if missing:
        raise ValueError(f"missing parts: {missing}")
    return b"".join(parts[i] for i in range(total_parts))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--expected-size", type=int)
    ap.add_argument("--expected-sha256")
    args = ap.parse_args()

    blob = reconstruct(args.xlsx)
    if blob[:4] != b"GGUF":
        raise SystemExit("FAIL: output is not GGUF")
    if args.expected_size is not None and len(blob) != args.expected_size:
        raise SystemExit("FAIL: final size mismatch")
    digest = sha256(blob)
    if args.expected_sha256 and digest != args.expected_sha256:
        raise SystemExit("FAIL: final sha256 mismatch")
    args.output.write_bytes(blob)
    print(f"PASS size={len(blob)} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
