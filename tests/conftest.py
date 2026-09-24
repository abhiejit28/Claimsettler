"""Spins up the three real MCP servers (KMA, FraudAgent, ComplianceAgent) as
subprocesses, using fake/in-memory providers and a shared temp SQLite
database — no external credentials needed. This is a real MCP contract
exercise: the API talks to these servers over actual Streamable HTTP, not
mocks."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_SERVER_SPECS = [
    ("claimsettler.mcp_servers.kma.server", 8100),
    ("claimsettler.mcp_servers.fraud_agent.server", 8101),
    ("claimsettler.mcp_servers.compliance_agent.server", 8102),
]


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.3)
    raise TimeoutError(f"port {port} did not open within {timeout}s")


@pytest.fixture(scope="session")
def integration_db_url(tmp_path_factory) -> str:
    db_path = tmp_path_factory.mktemp("db") / "integration.db"
    return f"sqlite+aiosqlite:///{db_path}"


@pytest.fixture(scope="session")
def mcp_servers(integration_db_url: str):
    base_env = {
        **os.environ,
        "DATABASE_URL": integration_db_url,
        "EMBEDDING_PROVIDER": "fake",
        "VECTOR_STORE": "fake",
        "RERANKER": "fake",
        "LLM_PROVIDER": "fake",
        "PII_DETECTOR": "regex_only",  # avoids a spaCy model load per test session
        "PYTHONPATH": str(ROOT / "src"),
    }

    procs = []
    for module, port in _SERVER_SPECS:
        env = {**base_env, "PORT": str(port), "HOST": "127.0.0.1"}
        proc = subprocess.Popen(
            [sys.executable, "-m", module],
            env=env,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        procs.append((proc, module))

    try:
        for _proc, _module in procs:
            pass
        for _module, port in _SERVER_SPECS:
            _wait_for_port("127.0.0.1", port)
    except TimeoutError:
        for proc, module in procs:
            proc.terminate()
            output = proc.stdout.read().decode() if proc.stdout else ""
            print(f"--- {module} output ---\n{output}")
        raise

    yield

    for proc, _module in procs:
        proc.terminate()
    for proc, _module in procs:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
