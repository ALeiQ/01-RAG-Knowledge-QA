from __future__ import annotations

from src.qa import cancel


class _FakeResp:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


def test_register_attach_release() -> None:
    resp = _FakeResp()
    assert cancel.register("s1")
    assert cancel.is_cancelled("s1") is False
    cancel.attach("s1", resp)
    assert cancel.request_cancel("s1") is True
    assert cancel.is_cancelled("s1") is True
    assert resp.closed == 1
    cancel.release("s1")
    assert cancel.is_cancelled("s1") is False
    assert cancel.request_cancel("s1") is False


def test_request_cancel_closes_resp_once() -> None:
    resp = _FakeResp()
    cancel.register("s2")
    cancel.attach("s2", resp)
    assert cancel.request_cancel("s2") is True
    assert cancel.is_cancelled("s2") is True
    assert resp.closed == 1
    # Idempotent: second cancel no-ops, no double close.
    assert cancel.request_cancel("s2") is True
    assert resp.closed == 1
    cancel.release("s2")
    assert cancel.request_cancel("s2") is False


def test_cancel_before_attach_only_sets_flag() -> None:
    cancel.register("s3")
    assert cancel.is_cancelled("s3") is False
    assert cancel.request_cancel("s3") is True
    assert cancel.is_cancelled("s3") is True
    # Attaching after cancel must not resurrect; releasing keeps it cancelled-free.
    cancel.attach("s3", _FakeResp())
    assert cancel.is_cancelled("s3") is True
    cancel.release("s3")
    assert cancel.is_cancelled("s3") is False


def test_empty_gen_id_is_noop() -> None:
    assert cancel.register("") is False
    assert cancel.request_cancel("") is False
    assert cancel.register(None) is False
    assert cancel.request_cancel(None) is False
    cancel.attach("", _FakeResp())
    cancel.attach(None, _FakeResp())
