import socket, struct, sys, threading, time

SERVER_HOST, SERVER_PORT, USER = sys.argv[1], int(sys.argv[2]), sys.argv[3]

LOGIN, LOGOUT, JOIN, LEAVE, SAY, LIST, WHO, KEEP_ALIVE = range(8)
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
active = "Common"
joined = {"Common"}
last_send = time.time()

def send(pkt):
    global last_send
    client.sendto(pkt, (SERVER_HOST, SERVER_PORT))
    last_send = time.time()

def send_login():  send(struct.pack("!I32s", LOGIN, USER.encode()))
def send_logout(): send(struct.pack("!I", LOGOUT))
def send_join(ch): send(struct.pack("!I32s", JOIN, ch.encode()))
def send_leave(ch):send(struct.pack("!I32s", LEAVE, ch.encode()))
def send_say(ch, msg): send(struct.pack("!I32s64s", SAY, ch.encode(), msg.encode()))
def send_list():  send(struct.pack("!I", LIST))
def send_who(ch): send(struct.pack("!I32s", WHO, ch.encode()))
def send_keepalive(): send(struct.pack("!I", KEEP_ALIVE))

def listener():
    while True:
        data, _ = client.recvfrom(2048)
        print("\r" + data.decode() + "\n> ", end="")

def keepalive_loop():
    while True:
        if time.time() - last_send > 60:
            send_keepalive()
        time.sleep(10)

def main():
    global active
    send_login()
    threading.Thread(target=listener, daemon=True).start()
    threading.Thread(target=keepalive_loop, daemon=True).start()
    print("Joined Common. Type /help for commands.")

    help_text = """
Available commands:
/join <channel>    - Join or create a channel
/leave <channel>   - Leave a joined channel
/switch <channel>  - Switch active channel
/list              - List all existing channels
/who <channel>     - List users on that channel
/exit              - Logout and exit
/help              - Show this help text
"""

    while True:
        try:
            msg = input("> ").strip()
            if not msg:
                continue

            if msg == "/help":
                print(help_text)
                continue

            if msg.startswith("/exit"):
                send_logout()
                print("Goodbye!")
                break

            elif msg.startswith("/join "):
                ch = msg.split(maxsplit=1)[1]
                send_join(ch)
                joined.add(ch)
                active = ch
                print(f"Joined {ch} and switched to it.")

            elif msg.startswith("/leave "):
                ch = msg.split(maxsplit=1)[1]
                if ch in joined:
                    send_leave(ch)
                    joined.remove(ch)
                    if active == ch:
                        active = "Common"
                        print("Switched back to Common.")
                else:
                    print("You’re not in that channel.")

            elif msg.startswith("/switch "):
                ch = msg.split(maxsplit=1)[1]
                if ch in joined:
                    active = ch
                    print(f"Switched to {ch}.")
                else:
                    print("You must join the channel first.")

            elif msg.startswith("/list"):
                send_list()

            elif msg.startswith("/who "):
                ch = msg.split(maxsplit=1)[1]
                send_who(ch)

            else:
                if active:
                    send_say(active, msg)
                else:
                    print("No active channel. Use /switch <channel>.")

        except KeyboardInterrupt:
            send_logout()
            print("\nLogged out (Ctrl+C).")
            break


if __name__ == "__main__":
    main()
