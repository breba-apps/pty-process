import asyncio
import pytest_asyncio
import pytest

from pty_server import AsyncPtyClient
from pty_server.async_client import STATUS_COMPLETED, STATUS_TIMEOUT
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
    async with AsyncPtyClient() as aclient:
        yield aclient


@pytest.mark.asyncio
async def test_async_echo_command(server, aclient):
    response = await aclient.send_command("echo Hello")
    await asyncio.sleep(0.1)

    data = ""
    async for chunk in response.stream(timeout=1):
        data += chunk

    assert response.status == STATUS_COMPLETED
    assert "$ echo Hello\r\n" in data
    assert "Hello\r\n" in data


@pytest.mark.asyncio
async def test_async_echo_variable(server, aclient):
    response1 = await aclient.send_command("export MY=Hello")
    response2 = await aclient.send_command("echo $MY")

    data = ""
    async for chunk in response1.stream(timeout=0.1):
        data += chunk
    assert response1.status == STATUS_COMPLETED
    assert "$ export MY=Hello\r\n" in data

    data = ""
    async for chunk in response2.stream(timeout=0.1):
        data += chunk

    assert response2.status == STATUS_COMPLETED
    assert "$ echo $MY\r\n" in data
    assert "Hello\r\n" in data

@pytest.mark.asyncio
async def test_async_failed_command(server, aclient):
    response = await aclient.send_command("clear")

    data = ""
    async for chunk in response.stream(timeout=0.1):
        data += chunk

    assert response.status == STATUS_COMPLETED
    assert "$ clear\r\n" in data


@pytest.mark.asyncio
async def test_command_timeout(server, aclient):
    response = await aclient.send_command("sleep 1")

    data = ""
    async for chunk in response.stream(timeout=0.5):
        data += chunk

    assert response.status == STATUS_TIMEOUT
    assert "$ sleep 1" in data