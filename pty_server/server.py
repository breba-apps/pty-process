import asyncio
import json
import logging
import shlex

from websockets.asyncio.server import serve, ServerConnection
from websockets.exceptions import ConnectionClosed

from interactive_process import InteractiveProcess, TerminatedProcessError, ReadWriteError

PORT = 44440

logger = logging.getLogger(__name__)
# We'll keep a reference to the running server so we can stop it via commands
ws_server = None


async def stream_output(process: InteractiveProcess, connection: ServerConnection, end_marker: str):
    """
    Continuously reads from the InteractiveProcess and sends its output
    to the WebSocket until `end_marker` is encountered or the process ends.
    """
    while True:
        try:
            # This timeout controls how fast we are plucking data from command output
            output = process.read_nonblocking(timeout=0.05)
            if output:
                logger.info(f"Process output: {output.strip()}")
                await connection.send(output)

                if end_marker in output:
                    logger.info("Breaking on end marker")
                    break
        except TimeoutError:
            # Give the event loop a chance to run
            # Should not use this timeout for anything else because it complicates things unnecessarily
            # Just use the timeout on read to control how fast we pluck data
            await asyncio.sleep(0.0)
        except (TerminatedProcessError, ReadWriteError) as exc:
            logger.info(f"End of process output: {exc}")
            break
        except Exception as exc:
            logger.exception(exc)
            break


async def command_scheduler_loop(commands_queue: asyncio.Queue,
                                 process: InteractiveProcess,
                                 connection: ServerConnection):
    """
    A loop that pulls commands off an asyncio.Queue and dispatches them
    to `handle_command`.
    """
    while True:
        command = await commands_queue.get()
        await handle_command(command, process, connection)


def command_end_marker(command_id):
    return f"Completed {command_id}"


async def handle_command(command: dict, process: InteractiveProcess, connection: ServerConnection):
    """
    Process a command dictionary, send it to the InteractiveProcess, and stream back output.
    """
    logger.info(f"command: {command}")
    if not command:
        return

    command_text = command.get("command")
    command_id = command.get("command_id", "unknown")

    # Echo the command first (shell-escaped)
    escaped_command = shlex.quote(command_text)
    echo_text = f"echo $ {escaped_command}\n"
    process.send_command(echo_text)
    logger.info(f"Sending to process echo: {echo_text}")

    # Actual command with an end marker so that we know when to stop streaming
    end_marker = command_end_marker(command_id)
    # For now we will produce the same end marker in both cases
    # TODO: in the future should send an exit code with the done signal to let client know if command failed or not
    shell_command = f"{command_text} && echo {end_marker} || echo {end_marker}"
    process.send_command(shell_command)
    logger.info(f"Sending to process command: {shell_command}")

    # Stream the output back to the client until we see the end marker
    await stream_output(process, connection, end_marker)


async def stop_server():
    """
    Closes the global WebSocket server, if running.
    """
    global ws_server
    if ws_server is not None:
        logger.info("Closing server...")
        ws_server.close()
        # Wait for it to shut down gracefully
        await ws_server.wait_closed()
        ws_server = None
        logger.info("Server closed.")


async def handle_websocket(connection: ServerConnection):
    """
    Main handler for each WebSocket connection. It sets up an
    InteractiveProcess and manages incoming messages and scheduling commands.

    If you need the HTTP path, headers, etc., you can use:
    - connection.request.path
    - connection.request.headers
    """
    client_address = connection.remote_address
    logger.info(f"WebSocket connection from {client_address}")

    process = InteractiveProcess()
    # Example: activate a virtual environment
    process.send_command('. .venv/bin/activate')

    # Create a queue for incoming commands
    commands_queue = asyncio.Queue()

    # Start a task to schedule commands from the queue
    command_scheduler_task = asyncio.create_task(
        command_scheduler_loop(commands_queue, process, connection)
    )

    try:
        while True:
            # Receive a JSON message from the client
            message = await connection.recv()
            if not message:
                break

            try:
                data = json.loads(message.strip())
            except json.JSONDecodeError:
                await connection.send("Error: Invalid JSON data received.")
                continue

            cmd = data.get("command")
            if cmd == "quit":
                logger.info("Quit command received; shutting down...")
                await connection.send("Server will shut down now.")
                await stop_server()
                break
            elif cmd:
                # Schedule the command for execution
                await commands_queue.put(data)

            # If there's interactive input (e.g. responding to a prompt)
            input_text = data.get("input")
            if input_text:
                logger.info(f"Sending user input to process: {input_text}")
                # Echo the input back for terminal-like behavior
                await connection.send(input_text)
                # Send input to the process
                process.send_command(input_text)

    except ConnectionClosed as exc:
        logger.info(f"Client {client_address} disconnected: {exc}")
    finally:
        # Cancel the scheduling task
        command_scheduler_task.cancel()

        # Close the underlying process if needed
        process.send_command("exit\n")
        logger.info("Closed process.")

        # Attempt to close the connection gracefully
        await connection.close()
        logger.info("WebSocket connection closed.")


async def start_websocket_server():
    """
    Starts the WebSocket server on the specified port with the new asyncio implementation.
    Runs until stopped by `stop_server()` or external shutdown.
    """
    global ws_server
    logger.info(f"Starting WebSocket server on 0.0.0.0:{PORT}")

    # Use the modern "async with" syntax. This is the recommended approach ≥ websockets 14.
    async with serve(handle_websocket, "0.0.0.0", PORT) as server:
        ws_server = server  # Keep a reference so we can close it later
        logger.info("Server started, serving until stopped...")
        # Keep the server running indefinitely
        await asyncio.Future()  # block forever unless canceled externally

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("server.log"),  # Log to file
            logging.StreamHandler()  # Log to console
        ]
    )

    try:
        asyncio.run(start_websocket_server())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received; shutting down.")

if __name__ == "__main__":
    main()