"""Minimal local HTTP server that catches a single OAuth redirect and captures ?code=&state=."""
import http.server
import threading
import urllib.parse
from dataclasses import dataclass
from typing import Optional


@dataclass
class OAuthResult:
    code: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None


def _make_handler(result: OAuthResult, done: threading.Event, success_html: str):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            result.code = params.get("code", [None])[0]
            result.state = params.get("state", [None])[0]
            result.error = params.get("error_description", params.get("error", [None]))[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(success_html.encode())
            done.set()

        def log_message(self, *args):  # silence default request logging
            pass

    return Handler


def wait_for_callback(port: int, label: str, timeout: int = 180) -> OAuthResult:
    """Blocks until the OAuth provider redirects back to http://localhost:<port>/, or times out."""
    result = OAuthResult()
    done = threading.Event()
    success_html = f"<html><body><h3>{label} authenticated. You can close this tab.</h3></body></html>"
    handler = _make_handler(result, done, success_html)
    server = http.server.HTTPServer(("localhost", port), handler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    finished = done.wait(timeout)
    server.server_close()
    if not finished:
        result.error = "Timed out waiting for browser redirect."
    return result
