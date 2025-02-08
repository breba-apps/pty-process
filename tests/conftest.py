import asyncio
import threading

import pytest_asyncio

from pty_server.server import stop_server, start_websocket_server


def run_server(server_ready: threading.Event):
    asyncio.run(start_websocket_server(server_ready))


@pytest_asyncio.fixture
async def server():
    server_ready = threading.Event()  # Thread-safe event
    server_thread = threading.Thread(target=run_server, args=(server_ready,), daemon=True)
    server_thread.start()

    server_ready.wait()  # Ensure the server is fully started before yielding

    yield  # Tests now execute with the server running

    stop_server()
    server_thread.join()
