import socket
import threading
import time
import json
import pytest
import importlib
from unittest.mock import patch, AsyncMock
from contextlib import contextmanager

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from src.api.mcp import MCPAuthMiddleware
from src.models.schemas import DocumentSearchResult
import src.config
import src.api.mcp
import src.main


# Setup dynamic port allocation and background server management
class UvicornServer(threading.Thread):
    def __init__(self, app, host="127.0.0.1", port=8001):
        super().__init__(daemon=True)
        config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.exception = None

    def run(self):
        try:
            self.server.run()
        except Exception as e:
            self.exception = e

    def stop(self):
        self.server.should_exit = True


@contextmanager
def run_app_in_background(app, host="127.0.0.1"):
    # Find a free port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, 0))
    port = s.getsockname()[1]
    s.close()

    server = UvicornServer(app, host=host, port=port)
    server.start()

    # Wait for server to start accepting connections
    start_time = time.time()
    started = False
    while time.time() - start_time < 5:
        if server.exception:
            raise server.exception
        try:
            with socket.create_connection((host, port), timeout=0.1):
                started = True
                break
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.05)

    if not started:
        if getattr(server.server, "should_exit", False):
            raise RuntimeError("Uvicorn failed to start (lifespan or server initialization failed).")
        raise RuntimeError("Uvicorn does not start")

    try:
        yield port
    finally:
        server.stop()
        server.join(timeout=5.0)
        if server.is_alive():
            raise RuntimeError("The background server did not stop.")


# 1. Test MCPAuthMiddleware
def test_mcp_auth_middleware():
    async def dummy_app(scope, receive, send):
        response = JSONResponse({"status": "ok"})
        await response(scope, receive, send)

    # Allowed without key
    middleware_no_key = MCPAuthMiddleware(dummy_app, api_key="")
    client_no_key = TestClient(middleware_no_key)
    res = client_no_key.get("/")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

    # Enforcement with key
    middleware_with_key = MCPAuthMiddleware(dummy_app, api_key="secret-key")
    client_with_key = TestClient(middleware_with_key)

    # Missing header -> 401
    res = client_with_key.get("/")
    assert res.status_code == 401
    assert res.headers.get("www-authenticate") == "Bearer"
    assert res.json() == {"detail": "Unauthorized: Invalid or missing Bearer token"}

    # Invalid structure -> 401
    res = client_with_key.get("/", headers={"Authorization": "InvalidHeader"})
    assert res.status_code == 401
    assert res.headers.get("www-authenticate") == "Bearer"

    # Wrong token -> 401
    res = client_with_key.get("/", headers={"Authorization": "Bearer wrong-token"})
    assert res.status_code == 401
    assert res.headers.get("www-authenticate") == "Bearer"

    # Valid token -> 200
    res = client_with_key.get("/", headers={"Authorization": "Bearer secret-key"})
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# 2. Test MCP Enabled vs Disabled Routing
def test_mcp_disabled_routing(monkeypatch):
    monkeypatch.setattr(src.config.settings, "MCP_ENABLED", False)
    importlib.reload(src.api.mcp)
    importlib.reload(src.main)

    client = TestClient(src.main.app)
    response = client.get("/mcp/")
    assert response.status_code == 404

    # Restore default setting and reload to reset state
    monkeypatch.setattr(src.config.settings, "MCP_ENABLED", True)
    importlib.reload(src.api.mcp)
    importlib.reload(src.main)


# 3. Test background server lifespan error handling
def test_mcp_lifespan_failure():
    async def broken_lifespan(app):
        raise RuntimeError("Lifespan setup failed.")
        yield

    broken_app = Starlette(lifespan=broken_lifespan)
    
    with pytest.raises(RuntimeError, match="Uvicorn failed to start"):
        with run_app_in_background(broken_app):
            pass


# 4. Test background server stop failure check
def test_mcp_server_stop_failure(monkeypatch):
    async def dummy_lifespan(app):
        yield

    dummy_app = Starlette(lifespan=dummy_lifespan)

    # Mock stop to do nothing, simulating a hung server
    def mock_stop(self):
        pass

    monkeypatch.setattr(UvicornServer, "stop", mock_stop)

    with pytest.raises(RuntimeError, match="The background server did not stop"):
        with run_app_in_background(dummy_app):
            pass


# 5. Protocol-level integration flow using ClientSession
@pytest.mark.anyio
async def test_mcp_protocol_flow(monkeypatch):
    monkeypatch.setattr(src.config.settings, "MCP_ENABLED", True)
    monkeypatch.setattr(src.config.settings, "MCP_API_KEY", "test-secret-key")
    # Add a wildcard port host so dns rebinding doesn't block the dynamic port
    monkeypatch.setattr(src.config.settings, "MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*")
    
    importlib.reload(src.api.mcp)
    importlib.reload(src.main)

    mock_results = [
        DocumentSearchResult(
            document_id="doc-123",
            title="Test Doc",
            type="case",
            client_name="Client A",
            industry="Tech",
            geography="US",
            use_case="Test Case",
            tags=["tag1"],
            authors=["Author A"],
            source_bucket="bucket",
            source_object_key="key",
            chunk_id="chunk-123",
            chunk_index=0,
            content="This is matching test content.",
            score=0.95
        )
    ]

    with patch("src.api.mcp.perform_semantic_search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_results

        with run_app_in_background(src.main.app) as port:
            mcp_url = f"http://127.0.0.1:{port}/mcp/"
            headers = {"Authorization": "Bearer test-secret-key"}

            async with streamablehttp_client(mcp_url, headers=headers) as transport:
                read_stream, write_stream, _ = transport
                async with ClientSession(read_stream, write_stream) as session:
                    # Initialize session
                    init_result = await session.initialize()
                    assert init_result.protocolVersion is not None

                    # Discover tools
                    tools = await session.list_tools()
                    tool_names = [t.name for t in tools.tools]
                    assert "search_knowledge_base" in tool_names

                    # Verify limits validation in schema
                    search_tool = next(t for t in tools.tools if t.name == "search_knowledge_base")
                    properties = search_tool.inputSchema.get("properties", {})
                    assert "limit" in properties
                    
                    limit_prop = properties["limit"]
                    # Depending on how FastMCP/pydantic translates ge/le, check minimum/maximum
                    minimum = limit_prop.get("minimum", limit_prop.get("ge"))
                    maximum = limit_prop.get("maximum", limit_prop.get("le"))
                    assert minimum == 1
                    assert maximum == 20

                    # Successful search call
                    result = await session.call_tool(
                        "search_knowledge_base",
                        {"query": "test query", "limit": 5}
                    )
                    assert result.isError is False
                    
                    response_data = json.loads(result.content[0].text)
                    assert response_data["query"] == "test query"
                    assert response_data["result_count"] == 1
                    assert response_data["results"][0]["document_id"] == "doc-123"
                    assert response_data["results"][0]["score"] == 0.95

                    # Schema limit validation bounds checks (should error out)
                    # Note: FastMCP will validate this input schema. Let's call with invalid limit
                    result_invalid_limit = await session.call_tool(
                        "search_knowledge_base",
                        {"query": "test query", "limit": 25}
                    )
                    assert result_invalid_limit.isError is True
                    assert "limit" in result_invalid_limit.content[0].text.lower() or "validation" in result_invalid_limit.content[0].text.lower()

                    # Schema query validation bounds checks (empty query)
                    result_empty_query = await session.call_tool(
                        "search_knowledge_base",
                        {"query": "", "limit": 5}
                    )
                    assert result_empty_query.isError is True

                    # Empty search matches maps to successful JSON response with result count 0
                    mock_search.return_value = []
                    result_empty = await session.call_tool(
                        "search_knowledge_base",
                        {"query": "unmatched search term", "limit": 5}
                    )
                    assert result_empty.isError is False
                    response_empty = json.loads(result_empty.content[0].text)
                    assert response_empty["result_count"] == 0
                    assert len(response_empty["results"]) == 0
                    assert "message" in response_empty

                    # Infrastructure/technical failure maps to tool error
                    mock_search.side_effect = Exception("Postgres connection timeout")
                    result_fail = await session.call_tool(
                        "search_knowledge_base",
                        {"query": "trigger failure", "limit": 5}
                    )
                    assert result_fail.isError is True
                    assert "internal" in result_fail.content[0].text.lower() or "postgres" in result_fail.content[0].text.lower()

    # Re-import to clean up settings
    monkeypatch.setattr(src.config.settings, "MCP_ENABLED", True)
    monkeypatch.setattr(src.config.settings, "MCP_API_KEY", "")
    monkeypatch.setattr(src.config.settings, "MCP_ALLOWED_HOSTS", "localhost:8000,127.0.0.1:8000,leadgen-api:8000,leadgen-api-dev:8000,localhost:*,127.0.0.1:*")
    importlib.reload(src.api.mcp)
    importlib.reload(src.main)


def test_mcp_dns_rebinding_and_routing(monkeypatch):
    monkeypatch.setattr(src.config.settings, "MCP_ENABLED", True)
    monkeypatch.setattr(src.config.settings, "MCP_API_KEY", "mcp-test-key")
    monkeypatch.setattr(src.config.settings, "MCP_ALLOWED_HOSTS", "allowed-host.com")
    importlib.reload(src.api.mcp)
    importlib.reload(src.main)

    with TestClient(src.main.app) as client:
        # 1. Allowed Host succeeds (or returns 401 but NOT 421)
        res_allowed = client.post("/mcp/", headers={"Host": "allowed-host.com"})
        assert res_allowed.status_code == 401

        # 2. Unlisted Host is rejected with 421 (when authorized)
        res_unlisted = client.post("/mcp/", headers={
            "Host": "evil-host.com",
            "Authorization": "Bearer mcp-test-key",
            "Content-Type": "application/json",
        })
        assert res_unlisted.status_code == 421

        # 3. Authentication still runs correctly with allowed host
        res_auth_ok = client.post("/mcp/", headers={
            "Host": "allowed-host.com",
            "Authorization": "Bearer mcp-test-key",
            "Content-Type": "application/json"
        })
        # Since it is Streamable HTTP, a POST with empty body is rejected as invalid content or bad request, but got past DNS & Auth checks
        assert res_auth_ok.status_code in (400, 405, 406, 200)

        # 4. Other endpoints (/health, /ui) are unaffected by Host header
        res_health = client.get("/health", headers={"Host": "evil-host.com"})
        assert res_health.status_code == 200

        res_ui = client.get("/ui", headers={"Host": "evil-host.com"})
        assert res_ui.status_code != 421

    # Restore default settings
    monkeypatch.setattr(src.config.settings, "MCP_ENABLED", True)
    monkeypatch.setattr(src.config.settings, "MCP_API_KEY", "")
    monkeypatch.setattr(src.config.settings, "MCP_ALLOWED_HOSTS", "localhost:8000,127.0.0.1:8000,leadgen-api:8000,leadgen-api-dev:8000,localhost:*,127.0.0.1:*")
    importlib.reload(src.api.mcp)
    importlib.reload(src.main)

