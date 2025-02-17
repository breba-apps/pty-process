import pytest
import pytest_asyncio

from pty_server import AsyncPtyClient
from pty_server.async_client import STATUS_COMPLETED, STATUS_TIMEOUT


@pytest_asyncio.fixture
async def aclient():
    async with AsyncPtyClient() as aclient:
        yield aclient


@pytest.mark.asyncio
async def test_async_echo_command(server, aclient):
    response = await aclient.send_command("echo Hello")

    data = await response.text(0.01)

    assert response.status == STATUS_COMPLETED
    assert "$ echo Hello\n" in data
    assert "Hello\n" in data


@pytest.mark.asyncio
async def test_async_echo_variable(server, aclient):
    response1 = await aclient.send_command("export MY=Hello")
    response2 = await aclient.send_command("echo $MY")

    data = await response1.text(timeout=0.1)
    assert response1.status == STATUS_COMPLETED
    assert "$ export MY=Hello\n" in data

    data = await response2.text(timeout=0.1)

    assert response2.status == STATUS_COMPLETED
    assert "$ echo $MY\n" in data
    assert "Hello\n" in data


@pytest.mark.asyncio
async def test_async_failed_command(server, aclient):
    response = await aclient.send_command("clear")

    data = await response.text(timeout=0.1)

    assert response.status == STATUS_COMPLETED
    assert "$ clear\n" in data


@pytest.mark.asyncio
async def test_command_timeout(server, aclient):
    response = await aclient.send_command("sleep 5")

    data = await response.text(timeout=0.5)

    assert response.status == STATUS_TIMEOUT
    assert "$ sleep 5" in data


@pytest.mark.asyncio
async def test_no_venv(server, aclient):
    await aclient.send_command('python3 -m venv .venv')
    response = await aclient.send_command('VIRTUAL_ENV_DISABLE_PROMPT=1 . .venv/bin/activate')
    data = await response.text(6)

    assert response.completed()
    assert "$ VIRTUAL_ENV_DISABLE_PROMPT=1 . .venv/bin/activate" in data

    response = await aclient.send_command('echo Hello')
    data = await response.text(6)

    assert response.completed()
    assert "echo Hello" in data
    assert "venv" not in data
