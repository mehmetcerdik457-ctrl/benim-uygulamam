import hashlib
import http.server
import mimetypes
import os
import pathlib
import socketserver
import urllib.request
import zipfile

ARTIFACT_URL = "https://res.cloudinary.com/eeapbio5/raw/upload/v1789816129/mehmet_yaratilis/MEHMET_YARATILIS_PWA_v0.2.2.zip"
EXPECTED_SHA256 = "518d82cceb2843bc4db75d46876f1adc57558b601264bf2e888c9b09232fcbb0"
ZIP_PATH = "/tmp/MEHMET_YARATILIS_PWA_v0.2.2.zip"
EXTRACT_DIR = "/tmp/mehmet_v022"
ROOT = pathlib.Path(EXTRACT_DIR) / "MEHMET_YARATILIS_PWA_v0.2.2" / "MEHMET_YARATILIS_PWA"

print("RUNTIME_BOOT_START", flush=True)
urllib.request.urlretrieve(ARTIFACT_URL, ZIP_PATH)
payload = pathlib.Path(ZIP_PATH).read_bytes()
actual = hashlib.sha256(payload).hexdigest()
print(f"ARTIFACT_SIZE={len(payload)}", flush=True)
print(f"ARTIFACT_SHA256={actual}", flush=True)
if actual != EXPECTED_SHA256:
    raise SystemExit(f"SHA256_MISMATCH expected={EXPECTED_SHA256} actual={actual}")

with zipfile.ZipFile(ZIP_PATH) as zf:
    bad = zf.testzip()
    if bad is not None:
        raise SystemExit(f"ZIP_INTEGRITY_FAIL={bad}")
    zf.extractall(EXTRACT_DIR)

if not ROOT.is_dir():
    raise SystemExit(f"ROOT_NOT_FOUND={ROOT}")

os.chdir(ROOT)
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Permissions-Policy", "camera=(self), microphone=(self)")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, fmt, *args):
        print("HTTP", self.address_string(), fmt % args, flush=True)

port = int(os.environ.get("PORT", "8080"))
socketserver.TCPServer.allow_reuse_address = True
print(f"SERVING_ROOT={ROOT}", flush=True)
print(f"SERVING_PORT={port}", flush=True)
with socketserver.TCPServer(("0.0.0.0", port), Handler) as server:
    server.serve_forever()
