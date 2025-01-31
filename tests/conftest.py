import asyncio

import pytest_asyncio

from pty_server.server import stop_server, start_websocket_server


@pytest_asyncio.fixture
async def server():
    async_server = asyncio.create_task(start_websocket_server())
    await asyncio.sleep(1)
    yield
    stop_server()
    await async_server