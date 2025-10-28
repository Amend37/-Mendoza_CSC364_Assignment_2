"""
MustangChat Server
------------------
A simple UDP-based chat server that supports multiple users and channels.
"""

import socket
import threading
import time
import json
import sys

# Default host and port (can be overridden by command line args)
HOST = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
BUFFER_SIZE = 2048

# Timeouts
KEEP_ALIVE_INTERVAL = 60     # clients must send a keep-alive every 60s
USER_TIMEOUT = 120           # users inactive for 120s are logged out

# Server data structures
users = {}       # addr -> { "username": str, "channels": set(), "last_seen": time }
channels = {}    # channel_name -> set of user addresses

# Helper: send a plain text message back to a client
def send_message(server_socket, addr, text):
    server_socket.sendto(text.encode("utf-8"), addr)

# Helper: broadcast to everyone in a channel
def broadcast(server_socket, channel, text):
    if channel not in channels:
        return
    for addr in channels[channel]:
        send_message(server_socket, addr, text)

# Remove user cleanly
def logout_user(addr, server_socket):
    if addr not in users:
        return
    user = users[addr]
    username = user["username"]

    # Remove from all channels
    for ch in list(user["channels"]):
        if ch in channels:
            channels[ch].discard(addr)
            if not channels[ch]:
                del channels[ch]

    del users[addr]
    print(f"[LOGOUT] {username}")
    server_socket.sendto(f"You have been logged out, {username}.".encode(), addr)

# Periodically remove inactive users
def cleanup_loop(server_socket):
    while True:
        time.sleep(10)
        now = time.time()
        to_remove = [a for a, u in users.items() if now - u["last_seen"] > USER_TIMEOUT]
        for addr in to_remove:
            logout_user(addr, server_socket)

# Handle incoming messages from clients
def handle_message(data, addr, server_socket):
    try:
        message = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError:
        send_message(server_socket, addr, "Invalid message format.")
        return

    msg_type = message.get("type")
    username = message.get("username")

    # LOGIN
    if msg_type == "login":
        users[addr] = {
            "username": username,
            "channels": {"Common"},
            "last_seen": time.time()
        }
        channels.setdefault("Common", set()).add(addr)
        print(f"[LOGIN] {username} joined Common")
        send_message(server_socket, addr, f"Welcome {username}! Joined Common.")

    # LOGOUT
    elif msg_type == "logout":
        logout_user(addr, server_socket)

    # SAY
    elif msg_type == "say":
        channel = message.get("channel")
        text = message.get("text")
        if addr not in users or channel not in users[addr]["channels"]:
            send_message(server_socket, addr, "Error: You are not in that channel.")
            return
        sender = users[addr]["username"]
        formatted = f"[{channel}][{sender}]: {text}"
        print(formatted)
        broadcast(server_socket, channel, formatted)

    # JOIN
    elif msg_type == "join":
        channel = message.get("channel")
        users[addr]["channels"].add(channel)
        channels.setdefault(channel, set()).add(addr)
        send_message(server_socket, addr, f"Joined channel {channel}")
        print(f"[JOIN] {username} -> {channel}")

    # LEAVE
    elif msg_type == "leave":
        channel = message.get("channel")
        if channel in users[addr]["channels"]:
            users[addr]["channels"].remove(channel)
            channels[channel].discard(addr)
            if not channels[channel]:
                del channels[channel]
            send_message(server_socket, addr, f"Left channel {channel}")
            print(f"[LEAVE] {username} <- {channel}")

    # LIST
    elif msg_type == "list":
        ch_list = ", ".join(channels.keys()) or "No channels"
        send_message(server_socket, addr, "Channels: " + ch_list)

    # WHO
    elif msg_type == "who":
        channel = message.get("channel")
        if channel not in channels:
            send_message(server_socket, addr, f"Channel {channel} does not exist.")
            return
        members = [users[a]["username"] for a in channels[channel]]
        send_message(server_socket, addr, f"Users in {channel}: " + ", ".join(members))

    # KEEP ALIVE
    elif msg_type == "keepalive":
        if addr in users:
            users[addr]["last_seen"] = time.time()

    # Unknown
    else:
        send_message(server_socket, addr, "Unknown message type.")

# Main server loop
def main():
    print(f"Starting MustangChat Server on {HOST}:{PORT}")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((HOST, PORT))

    # Start cleanup thread
    threading.Thread(target=cleanup_loop, args=(server_socket,), daemon=True).start()

    while True:
        try:
            data, addr = server_socket.recvfrom(BUFFER_SIZE)
            handle_message(data, addr, server_socket)
        except KeyboardInterrupt:
            print("\nServer shutting down...")
            break
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
