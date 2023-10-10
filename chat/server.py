import asyncio
import logging
import websockets

logging.basicConfig(level=logging.INFO)
connected_clients = set()
NO_USER_TIMEOUT = 60  # 60 seconds


async def handler(websocket, path):
    connected_clients.add(websocket)
    user_count_msg = f"USERS_COUNT|{len(connected_clients)}"
    await asyncio.gather(*[client.send(user_count_msg) for client in connected_clients])
    try:
        async for message in websocket:
            if message == "disconnecting":
                logging.info(f"Client {websocket.remote_address} is disconnecting.")
                break
            await asyncio.gather(*[client.send(message) for client in connected_clients if client != websocket])
    except websockets.ConnectionClosed:
        logging.warning(f"Connection with {websocket.remote_address} was closed unexpectedly.")
    except Exception as e:
        logging.error(f"An error occurred with {websocket.remote_address}: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
            logging.info(f"Client {websocket.remote_address} has been removed.")
            disconnect_msg = f"{websocket.remote_address} has disconnected."
            user_count_msg = f"USERS_COUNT|{len(connected_clients)}"
            await asyncio.gather(*[client.send(user_count_msg) for client in connected_clients],
                                 *[client.send(disconnect_msg) for client in connected_clients])


async def check_connections(server_running):
    while server_running:
        await asyncio.sleep(10)
        if not connected_clients:
            logging.warning("No users connected. Setting timeout for server shutdown.")
            await asyncio.sleep(NO_USER_TIMEOUT)
            if not connected_clients:
                logging.info("No users reconnected. Closing server.")
                for task in asyncio.all_tasks():
                    task.cancel()
                break


def start_server():
    server_running = True
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(check_connections(server_running))
    try:
        loop.run_until_complete(websockets.serve(handler, 'localhost', 8765))
        loop.run_forever()
    except OSError as e:
        if e.errno == 10048:  # The error code for address already in use
            logging.info("Server is already running. Not starting a new one.")
        else:
            logging.error(f"An unexpected error occurred: {e}")
    except asyncio.CancelledError:
        logging.info("All tasks are cancelled, and server is shutting down.")


if __name__ == "__main__":
    start_server()
