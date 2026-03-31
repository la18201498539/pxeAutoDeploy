import os
import threading
import http.server
from typing import Callable, Optional

from core.config import DeployConfig

_server: Optional[http.server.HTTPServer] = None
_server_thread: Optional[threading.Thread] = None
_install_done_callback: Optional[Callable] = None


def _make_handler(http_root: str):
    class PXEHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=http_root, **kwargs)

        def do_GET(self):
            if self.path == "/api/done":
                self._handle_done()
            else:
                super().do_GET()

        def _handle_done(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
            # Trigger callback in a separate thread to avoid blocking handler
            if _install_done_callback:
                threading.Thread(target=_install_done_callback, daemon=True).start()

        def log_message(self, fmt, *args):
            pass  # Suppress console noise; monitoring is done via syslog

    return PXEHandler


def start(config: DeployConfig, log: Callable, on_install_done: Callable = None):
    global _server, _server_thread, _install_done_callback

    _install_done_callback = on_install_done

    http_root = config.http_root
    os.makedirs(http_root, exist_ok=True)

    # Symlink centos8/ → ISO mount dir
    centos_link = os.path.join(http_root, "centos8")
    if os.path.islink(centos_link):
        os.unlink(centos_link)
    os.symlink(config.iso_mount_dir, centos_link)

    handler = _make_handler(http_root)
    _server = http.server.HTTPServer(("0.0.0.0", config.http_port), handler)
    _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _server_thread.start()

    log(f"HTTP 服务已启动: http://0.0.0.0:{config.http_port}/")
    log(f"  安装源:   {config.repo_url()}")
    log(f"  Kickstart: {config.ks_url()}")


def stop(log: Callable):
    global _server
    if _server:
        _server.shutdown()
        _server = None
        log("HTTP 服务已停止")
