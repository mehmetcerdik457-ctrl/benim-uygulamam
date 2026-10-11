"""Socket-level CI relay tests using localhost-only synthetic HTTP servers."""
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import omega_ci_ephemeral_loopback_relay as m


class MockAPI(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        data = b'{"mode":"mock","production_ready":false}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        self.send_response(403)
        self.send_header("Content-Length", "0")
        self.end_headers()


class RelayTests(unittest.TestCase):
    def test_real_local_tcp_relay_get_200_and_post_403_and_cleanup(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), MockAPI) as mock:
            mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
            mock_thread.start()
            try:
                with m._Relay(("127.0.0.1", 0), m._RelayHandler,
                              target="127.0.0.1", target_port=mock.server_port) as relay:
                    self.assertEqual(relay.server_address[0], "127.0.0.1")
                    relay_thread = threading.Thread(target=relay.serve_forever, daemon=True)
                    relay_thread.start()
                    try:
                        opener = build_opener(ProxyHandler({})).open
                        base = "http://127.0.0.1:" + str(relay.server_address[1])
                        with opener(base + "/api/health", timeout=4) as response:
                            self.assertEqual(response.status, 200)
                            self.assertIn(b'"production_ready":false', response.read())
                        with self.assertRaises(HTTPError) as denied:
                            opener(Request(base + "/api/execute", data=b"{}",
                                           method="POST"), timeout=4)
                        self.assertEqual(denied.exception.code, 403)
                        denied.exception.close()
                    finally:
                        relay.shutdown()
                        relay_thread.join(timeout=3)
                        self.assertFalse(relay_thread.is_alive())
            finally:
                mock.shutdown()
                mock_thread.join(timeout=3)

    def test_blocked_preconditions_cannot_start_relay(self):
        with patch.object(m, "audit", return_value={
            "requested": "LOOPBACK_ONLY",
            "effective": "LOOPBACK_ONLY",
            "network": "INTERNAL",
        }):
            self.assertEqual(m.experiment(), "PRECONDITIONS_NOT_MET")

    def test_script_not_enabled_outside_explicit_ci(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(m.main(["--ci-disposable"]), 2)
            self.assertIn("DISABLED_OUTSIDE_EXPLICIT_CI", output.getvalue())

    def test_script_requires_explicit_flag_even_on_ci(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(m.main([]), 2)


if __name__ == "__main__":
    unittest.main()
