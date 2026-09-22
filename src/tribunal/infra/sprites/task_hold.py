"""Sprites の Tasks API で pause を抑止する。

Sprites は 30 秒ほど inbound request が途切れると pause し、service 内で走っている
処理も一緒に凍結する。Tasks API に task を登録している間だけ pause しない。
expire を過ぎた task は自動で消えるので、プロセスが落ちても hold は残らない。
"""

import json
import logging
import re
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.client import HTTPConnection
from typing import Any

logger = logging.getLogger(__name__)

SOCKET_PATH = "/.sprite/api.sock"
_HOST = "sprite"

# expire より短い間隔で延長する。落ちたとき hold が残る時間は expire が上限。
EXPIRE_SECONDS = 300
REFRESH_SECONDS = 60

# 接続できない環境では即座に諦める。ここで待つと ack 後の応答がその分遅れる。
TIMEOUT_SECONDS = 2.0

_INVALID_NAME_CHARS = re.compile(r"[^a-z0-9-]+")


class _UnixHTTPConnection(HTTPConnection):
    """unix domain socket 上の HTTP。Tasks API は TCP を listen していない。"""

    def __init__(self, socket_path: str, timeout: float = TIMEOUT_SECONDS) -> None:
        super().__init__(_HOST, timeout=timeout)
        self._socket_path = socket_path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self._socket_path)
        self.sock = sock


# DELETE が登録中の POST を追い越すと、消したはずの task が残って課金が続く。
_api_lock = threading.Lock()


def _request(method: str, path: str, body: dict[str, Any] | None = None) -> int:
    with _api_lock:
        return _request_locked(method, path, body)


def _request_locked(method: str, path: str, body: dict[str, Any] | None = None) -> int:
    conn = _UnixHTTPConnection(SOCKET_PATH)
    try:
        payload = json.dumps(body) if body is not None else None
        headers = {"Host": _HOST}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        response.read()
        return response.status
    finally:
        conn.close()


def sanitize_name(name: str) -> str:
    """task 名は英小文字・数字・dash だけ。Slack の thread_ts はドットを含む。"""
    return _INVALID_NAME_CHARS.sub("-", name.lower()).strip("-")


def is_available() -> bool:
    """Tasks API が使えるか（Sprites 上で動いているか）。"""
    try:
        return _request("GET", "/v1/tasks") == 200
    except OSError:
        return False


_refresh_stops: dict[str, threading.Event] = {}
_lock = threading.Lock()


def acquire(raw_name: str) -> str | None:
    """task を登録して pause を止める。取れたら task 名、駄目なら None。

    ack を返し終えると inbound request が切れた扱いになるので、
    ack ハンドラの中（= まだ起きていることが確実な間）に呼ぶ。
    """
    name = sanitize_name(raw_name)
    try:
        status = _request("POST", "/v1/tasks", {"name": name, "expire": EXPIRE_SECONDS})
    except OSError:
        # Sprites 上でなければ socket が無い。hold なしで続行する。
        logger.debug("tasks api unavailable, running without hold: %s", name)
        return None

    # 409 は同じ thread への重複配信。既にある hold をそのまま使う。
    if status not in (200, 201, 409):
        logger.warning("failed to register task %s: HTTP %d", name, status)
        return None

    logger.info("task hold acquired: %s", name)
    done = threading.Event()
    with _lock:
        previous = _refresh_stops.get(name)
        if previous is not None:
            previous.set()
        _refresh_stops[name] = done

    def refresh() -> None:
        while not done.wait(REFRESH_SECONDS):
            try:
                status = _request("PUT", f"/v1/tasks/{name}", {"expire": EXPIRE_SECONDS})
                # cold boot と spritesd 再起動で task は消える。PUT では復活しない。
                if status == 404:
                    _request("POST", "/v1/tasks", {"name": name, "expire": EXPIRE_SECONDS})
                    logger.info("task hold re-registered after restart: %s", name)
            except OSError:
                logger.warning("failed to refresh task %s", name)

    threading.Thread(target=refresh, daemon=True).start()
    return name


def release(name: str | None) -> None:
    """acquire した task を解放する。取れていなければ何もしない。"""
    if name is None:
        return
    with _lock:
        done = _refresh_stops.pop(name, None)
    if done is not None:
        done.set()
    try:
        _request("DELETE", f"/v1/tasks/{name}")
        logger.info("task hold released: %s", name)
    except OSError:
        logger.warning("failed to release task %s; expires in %ds", name, EXPIRE_SECONDS)


@contextmanager
def hold(raw_name: str) -> Iterator[None]:
    """acquire / release を同じスコープで済ませられるとき用。"""
    name = acquire(raw_name)
    try:
        yield
    finally:
        release(name)
