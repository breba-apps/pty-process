import asyncio
import json
import pytest_asyncio
import pytest

from pty_server.async_client import AsyncWebSocketClient
from pty_server.server import stop_server, start_websocket_server


@pytest_asyncio.fixture
async def server():
    async_server = asyncio.create_task(start_websocket_server())
    await asyncio.sleep(1)
    yield
    await stop_server()
    async_server.cancel()


@pytest_asyncio.fixture
async def aclient():
    async with AsyncWebSocketClient() as aclient:
        yield aclient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_async_echo_command(server, aclient):
    payload = json.dumps({"command": "echo Hello", "command_id": "test"})
    await aclient.send_message(payload)

    data = ""
    async for chunk in aclient.stream_response(timeout=0.1):
        data += chunk

    assert "$ echo Hello\r\n" in data
    assert "Hello\r\n" in data
    assert "Completed test\r\n" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_async_echo_variable(server, aclient):
    payload = json.dumps({"command": "export MY=Hello", "command_id": "test1"})
    await aclient.send_message(payload)

    payload = json.dumps({"command": "echo $MY", "command_id": "test2"})
    await aclient.send_message(payload)

    data = ""
    async for chunk in aclient.stream_response(timeout=0.1):
        data += chunk

    # We collected all the output from the two commands
    assert "$ export MY=Hello\r\n" in data
    assert "Completed test1\r\n" in data
    assert "$ echo $MY\r\n" in data
    assert "Hello\r\n" in data
    assert "Completed test2\r\n" in data

