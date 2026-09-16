"""In-flight generation registry for cancel-able streaming answers.

The streaming generator registers its ``gen_id`` as soon as it starts, then
``attach``-es the live response once the streaming request is established, and
``release``-es when it finishes. A cancel request sets the cancelled event and
closes the live response, which unblocks the generator thread currently blocked
waiting for the next token (Ollama aborts generation when the client
disconnects).
"""

from __future__ import annotations

import threading

_active: dict[str, "_Handle"] = {}
_lock = threading.Lock()


class _Handle:
    __slots__ = ("cancelled", "resp")

    def __init__(self) -> None:
        self.cancelled = threading.Event()
        self.resp = None


def register(gen_id: str | None) -> bool:
    """Register an in-flight generation so it can be cancelled by id."""
    if not gen_id:
        return False
    with _lock:
        _active[gen_id] = _Handle()
        return True


def attach(gen_id: str | None, resp) -> None:
    """Attach the live response once the streaming request is established."""
    if not gen_id:
        return
    with _lock:
        handle = _active.get(gen_id)
        if handle is not None:
            handle.resp = resp


def release(gen_id: str | None) -> None:
    if not gen_id:
        return
    with _lock:
        _active.pop(gen_id, None)


def is_cancelled(gen_id: str | None) -> bool:
    if not gen_id:
        return False
    with _lock:
        handle = _active.get(gen_id)
        return bool(handle and handle.cancelled.is_set())


def request_cancel(gen_id: str | None) -> bool:
    """Signal cancellation and sever the live connection to Ollama.

    Returns True if a matching generation existed, False otherwise.
    """
    if not gen_id:
        return False
    with _lock:
        handle = _active.get(gen_id)
        if handle is None:
            return False
        handle.cancelled.set()
        resp = handle.resp
        handle.resp = None
    if resp is not None:
        try:
            resp.close()
        except Exception:
            pass
    return True
