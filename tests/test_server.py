import asyncio
import json
import pytest_asyncio
import pytest

from pty_server import AsyncPtyClient
from pty_server.server import stop_server, start_websocket_server


@pytest_asyncio.fixture
async def server():
    async_server = asyncio.create_task(start_websocket_server())
    await asyncio.sleep(1)
    yield
    await stop_server()
    async_server.cancel()
    try:
        await async_server
    except asyncio.CancelledError:
        pass  # expected


@pytest_asyncio.fixture
async def aclient():
    async with AsyncPtyClient() as aclient:
        yield aclient

@pytest.mark.asyncio
async def test_async_echo_command(server, aclient):
    payload = json.dumps({"command": "echo Hello", "command_id": "test"})
    await aclient.send_message(payload)

    data = ""
    async for chunk in aclient.stream_response(timeout=0.1):
        data += chunk

    assert "$ echo Hello\n" in data
    assert "Hello\n" in data
    assert "Completed test\n" in data


@pytest.mark.asyncio
async def test_async_echo_variable(server, aclient):
    payload = json.dumps({"command": "export MY=Hello", "command_id": "test1"})
    await aclient.send_message(payload)

    payload = json.dumps({"command": "echo $MY", "command_id": "test2"})
    await aclient.send_message(payload)

    data = ""
    async for chunk in aclient.stream_response(timeout=0.1):
        data += chunk

    # We collected all the output from the two commands
    assert "$ export MY=Hello\n" in data
    assert "Completed test1\n" in data
    assert "$ echo $MY\n" in data
    assert "Hello\n" in data
    assert "Completed test2\n" in data

@pytest.mark.asyncio
async def test_async_failed_command(server, aclient):
    payload = json.dumps({"command": "clear", "command_id": "test1"})
    await aclient.send_message(payload)

    data = ""
    async for chunk in aclient.stream_response(timeout=0.1):
        data += chunk

    # We collected all the output from the two commands
    assert "$ clear\n" in data
    assert "Completed test1\n" in data
