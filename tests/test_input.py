import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from pty_server import AsyncPtyClient


@pytest_asyncio.fixture
async def aclient() -> AsyncGenerator[AsyncPtyClient, None]:
    async with AsyncPtyClient() as aclient:
        yield aclient

@pytest.mark.asyncio
async def test_async_input(server, aclient):
    response = await aclient.send_command("""read -p "Please enter today's date(YYYY-MM-DD): " user_date""")

    data = await response.text(timeout=0.1)

    assert response.timedout()
    assert "$ read -p \"Please enter today's date(YYYY-MM-DD): \" user_date\n" in data

    await aclient.send_input("2022-01-01")
    await asyncio.sleep(1)
    data = await response.text(timeout=1)
    assert response.completed()
    assert "2022-01-01\n" in data

    response = await aclient.send_command("echo Hello there $user_date")
    data = await response.text(timeout=0.1)

    assert response.completed()
    assert data == "$ echo Hello there $user_date\nHello there 2022-01-01\n"
    assert "\n\n" not in data


