"""Disposable CI-only *experiment* for loopback -> internal Docker TCP relay.

No OMEGA network changes, no external listener, no persistence, no passwords,
no raw traffic or exception logs, and no production or owner acceptance claim.
Requires --ci-disposable AND GITHUB_ACTIONS=true. Temporary listener closes
before the independent, unchanged Docker publication acceptance gate is run.
"""
import argparse
import os
import select
import socket
import socketserver
import threading
import time
from urllib.request import ProxyHandler, build_opener

from omega_probe_runner_loopback import RUNNER_ONLY, probe
from omega_runner_host_direct_route import target_ip
from omega_runner_host_port_audit import audit

_MAX_BYTES_EACH_DIRECTION = 131072
_CONNECTION_SECONDS = 6.0


class _RelayHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            with socket.create_connection((self.server.target, self.server.target_port),
                                          timeout=3) as upstream:
                self.request.settimeout(4)
                upstream.settimeout(4)
                peers = (self.request, upstream)
                live = set(peers)
                byte_count = {peers[0]: 0, peers[1]: 0}
                end = time.monotonic() + _CONNECTION_SECONDS
                while live and time.monotonic() < end:
                    ready, _, _ = select.select(list(live), [], [],
                                                min(0.5, max(0.0, end - time.monotonic())))
                    for source in ready:
                        payload = source.recv(8192)
                        peer = peers[1] if source is peers[0] else peers[0]
                        if not payload:
                            live.remove(source)
                            try:
                                peer.shutdown(socket.SHUT_WR)
                            except OSError:
                                pass
                            continue
                        byte_count[source] += len(payload)
                        if byte_count[source] > _MAX_BYTES_EACH_DIRECTION:
                            return
                        peer.sendall(payload)
        except (OSError, ValueError):
            pass  # Never publish Docker IP, path, HTTP body or host exception.


class _Relay(socketserver.ThreadingTCPServer):
    # Closing the listening socket is insufficient: daemon handler threads
    # could still relay traffic after a PASS is printed. Join ALL accepted
    # handler threads before the CI experiment can report success.
    daemon_threads = False
    block_on_close = True
    allow_reuse_address = False
    request_queue_size = 4
    max_concurrent_connections = 4

    def __init__(self, address, handler, *, target, target_port=8000):
        # Reject unsafe listeners before binding. This experiment must never
        # open a wildcard, LAN, IPv6 or non-loopback listener.
        if (not isinstance(address, tuple) or len(address) != 2
                or address[0] != "127.0.0.1"
                or not isinstance(address[1], int)
                or isinstance(address[1], bool)
                or not 0 <= address[1] <= 65535):
            raise ValueError("CI relay may bind IPv4 loopback only")
        self.target = target
        self.target_port = target_port
        self._slots = threading.BoundedSemaphore(self.max_concurrent_connections)
        super().__init__(address, handler, bind_and_activate=True)

    def process_request(self, request, client_address):
        # ThreadingMixIn otherwise creates one unbounded thread per incoming
        # connection. Cap concurrent clients, including slow or idle clients.
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


def experiment():
    """Returns fixed, sanitized results and cleans up even on failure."""
    found = audit()
    if (found["requested"] != "LOOPBACK_ONLY" or
            found["effective"] != "MISSING" or found["network"] != "INTERNAL"):
        return "PRECONDITIONS_NOT_MET"
    target, scope = target_ip()
    if not target or scope != "SINGLE_INTERNAL_BRIDGE_RFC1918":
        return "INTERNAL_TARGET_NOT_VERIFIED"
    try:
        with _Relay(("127.0.0.1", 18080), _RelayHandler, target=target) as server:
            if server.server_address != ("127.0.0.1", 18080):
                return "NONLOOPBACK_BIND"
            worker = threading.Thread(target=server.serve_forever,
                                      kwargs={"poll_interval": 0.05}, daemon=True)
            worker.start()
            try:
                opener = build_opener(ProxyHandler({})).open
                if probe(opener=opener) != RUNNER_ONLY:
                    return "HTTP_NOT_VERIFIED"
            except (OSError, ValueError, TypeError, AssertionError, KeyError):
                return "HTTP_NOT_VERIFIED"
            finally:
                server.shutdown()
                worker.join(timeout=3)
                if worker.is_alive():
                    return "RELAY_NOT_STOPPED"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as check:
            check.settimeout(0.5)
            if check.connect_ex(("127.0.0.1", 18080)) == 0:
                return "LISTENER_PERSISTED"
        return "PASS_EPHEMERAL_CI_ONLY_NOT_DOCKER_OR_OWNER_ACCEPTANCE"
    except (OSError, ValueError):
        return "RELAY_BLOCKED"


def main(argv=None):
    opts = argparse.ArgumentParser()
    opts.add_argument("--ci-disposable", action="store_true")
    args = opts.parse_args(argv)
    if not args.ci_disposable or os.environ.get("GITHUB_ACTIONS") != "true":
        print("OMEGA_CI_RELAY=DISABLED_OUTSIDE_EXPLICIT_CI")
        return 2
    result = experiment()
    print("OMEGA_CI_RELAY=" + result)
    return 0 if result == "PASS_EPHEMERAL_CI_ONLY_NOT_DOCKER_OR_OWNER_ACCEPTANCE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
