#!/usr/bin/env python3
"""Verify and extract 8 unchanged original V30 PostgreSQL source files."""
import base64, brotli, hashlib, io, json, pathlib, tarfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
EXPECTED={
  "tests/test_postgres_live.py": "841d3972d1874403ec6b0e31bf3916f4f426ba06a6d068ec519a604609d7ada0",
  "tests/test_postgres_audit_live.py": "fc5f6f9992dd283024d289ed364815f1aafb74aeafa92a0a50177745c47a12f5",
  "omega_postgres.py": "d1d4960b11a23ecf34fad017ec670c117c96fffb44a2adfb61550c3c24b38d8e",
  "omega_postgres_audit.py": "7b5d21f8f7c755567d45a1367f1588099bac3cef15bea41e8c7deda05958ed77",
  "omega_postgres_integrity.py": "2f1cc977f241cfbd7482c9f21602a318595872ebe7acdce6922b23b77e653b88",
  "omega_postgres_reader.py": "a3ee636ca70b492bdb09fa81d216e24bbd6c319d3f4ac81c4dd241c70a462d2b",
  "postgres_schema.sql": "4f2559128736cf0519701b6f7642206923dd923f8215dd3312b931c5a7a16caf",
  "postgres_audit_schema.sql": "662589a916a04ae3d5c42513a97e66e784a2ddb3074c0fa8b58e28d46f58c529"
}
COMPRESSED_SHA256="2a08450d7506f6b34ab2010d64dbd098a00d68a63bd694426edb8b8fd933b8e2"
def main():
    b64=(ROOT/"evidence"/"omega_v30_pg16_source.tar.br.b64").read_text(encoding="ascii").strip()
    blob=base64.b64decode(b64,validate=True)
    if hashlib.sha256(blob).hexdigest()!=COMPRESSED_SHA256:
        raise SystemExit("source archive checksum mismatch")
    tar_bytes=brotli.decompress(blob)
    out=ROOT/"v30_pg16_original"
    out.mkdir(exist_ok=True)
    seen=set()
    with tarfile.open(fileobj=io.BytesIO(tar_bytes),mode="r:") as archive:
        for member in archive:
            if not member.isfile() or member.name not in EXPECTED or member.name in seen:
                raise SystemExit("unexpected source archive entry")
            data=archive.extractfile(member).read()
            if hashlib.sha256(data).hexdigest()!=EXPECTED[member.name]:
                raise SystemExit("V30 source byte checksum mismatch")
            target=out/member.name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
            seen.add(member.name)
    if seen!=set(EXPECTED):
        raise SystemExit("missing original V30 source files")
    print("ORIGINAL_V30_SOURCE_8_SHA256_VERIFIED=TRUE")
if __name__=="__main__":
    main()
