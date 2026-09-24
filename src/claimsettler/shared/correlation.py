"""Trace/correlation id propagation across controller -> agent -> MCP calls."""

import contextvars
import uuid

_trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)


def new_trace_id() -> str:
    return uuid.uuid4().hex


def set_trace_id(trace_id: str) -> None:
    _trace_id_var.set(trace_id)


def get_trace_id() -> str:
    trace_id = _trace_id_var.get()
    if trace_id is None:
        trace_id = new_trace_id()
        _trace_id_var.set(trace_id)
    return trace_id
