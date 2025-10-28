import socket
import threading
import json
import sys
import time

if len(sys.argv) != 4:
    print("Usage: python client.py <server_host> <port> <username>")
    sys.exit(1)

SERVER_HOST = sys.argv[1]
SERVER_PORT = int(sys.argv[2])
USERNAME = sys.argv[3]
KEEP_ALIVE_INTERVAL = 60
last_sent = time.time()
active_channel = "Common"
joined_channels = {"Common"}

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_addr = (SERVER_HOST, SERVER_PORT)

def send_json(msg_type, **kwargs):
    global last_sent
    message = {"type": msg_type, "username": USERNAME}
    message.update(kwargs)
    data = json.dumps(message).encode("utf-8")
    client_socket.sendto(data, server_addr)
    last_sent = time.time()

def send_keepalive():
    send_json("keepalive")

def listen_for_messages():
    while True:
        try:
            data, _ = client_socket.recvfrom(2048)
            text = data.decode("utf-8")
            print("\r" + text + "\n> ", end="")
        except Exception:
            break

def keepalive_loop():
    while True:
        time.sleep(KEEP_ALIVE_INTERVAL)
        if time.time() - last_sent >= KEEP_ALIVE_INTERVAL:
            send_keepalive()

def main():
    global active_channel
    send_json("login")
    threading.Thread(target=listen_for_messages, daemon=True).start()
    threading.Thread(target=keepalive_loop, daemon=True).start()
    print("Connected to MustangChat. Joined Common by default.")
    print("Type /help for a list of commands.\n")

    while True:
        try:
            user_input = input("> ").strip()
            if not user_input:
                continue
            if user_input == "/help":
                print("""
Available commands:
/help                 Show this help menu
/join <channel>       Join or create a channel
/leave <channel>      Leave a channel
/switch <channel>     Switch your active channel
/list                 List all channels
/who <channel>        Show users in a channel
/exit                 Logout and quit
""")
                continue
            if user_input == "/exit":
                send_json("logout")
                print("Goodbye!")
                break
            if user_input.startswith("/join "):
                ch = user_input.split(maxsplit=1)[1]
                send_json("join", channel=ch)
                joined_channels.add(ch)
                active_channel = ch
                continue
            if user_input.startswith("/leave "):
                ch = user_input.split(maxsplit=1)[1]
                if ch in joined_channels:
                    send_json("leave", channel=ch)
                    joined_channels.remove(ch)
                    if active_channel == ch:
                        active_channel = "Common"
                else:
                    print("You are not in that channel.")
                continue
            if user_input.startswith("/switch "):
                ch = user_input.split(maxsplit=1)[1]
                if ch in joined_channels:
                    active_channel = ch
                    print(f"Switched to {ch}")
                else:
                    print("You must join the channel first.")
                continue
            if user_input == "/list":
                send_json("list")
                continue
            if user_input.startswith("/who "):
                ch = user_input.split(maxsplit=1)[1]
                send_json("who", channel=ch)
                continue
            send_json("say", channel=active_channel, text=user_input)
        except KeyboardInterrupt:
            send_json("logout")
            print("\nLogged out.")
            break

if __name__ == "__main__":
    main()
