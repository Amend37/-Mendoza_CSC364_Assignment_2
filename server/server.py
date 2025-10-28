import socket, struct, time, threading

# ---- Constants ----
HOST, PORT = "localhost", 5000
BUF_SIZE = 2048

LOGIN, LOGOUT, JOIN, LEAVE, SAY, LIST, WHO, KEEP_ALIVE = range(8)

# ---- State ----
channels = {"Common": set()}
users = {}  # addr → {"username": str, "channels": set, "last": float}

# ---- Helpers ----
def send_text(addr, text):
    server.sendto(text.encode(), addr)

def broadcast(channel, text):
    for addr in channels.get(channel, set()):
        send_text(addr, text)

def logout_user(addr):
    if addr not in users: return
    u = users.pop(addr)
    for ch in u["channels"]:
        channels[ch].discard(addr)
        if not channels[ch]:
            del channels[ch]
    print(f"[LOGOUT] {u['username']} disconnected")

# ---- Packet Handlers ----
def handle_login(data, addr):
    username = data[4:36].decode().strip("\x00")
    users[addr] = {"username": username, "channels": {"Common"}, "last": time.time()}
    channels.setdefault("Common", set()).add(addr)
    print(f"[LOGIN] {username} joined Common")

def handle_say(data, addr):
    ch = data[4:36].decode().strip("\x00")
    msg = data[36:100].decode().strip("\x00")
    u = users[addr]["username"]

    if msg.startswith("/"):
        send_text(addr, "Unknown command. Type /help for list of commands.")
        return

    text = f"[{ch}][{u}]: {msg}"
    broadcast(ch, text)
    print(text)


def handle_join(data, addr):
    ch = data[4:36].decode().strip("\x00")
    channels.setdefault(ch, set()).add(addr)
    users[addr]["channels"].add(ch)
    send_text(addr, f"Joined channel {ch}")
    print(f"[JOIN] {users[addr]['username']} -> {ch}")

def handle_leave(data, addr):
    ch = data[4:36].decode().strip("\x00")
    if ch in users[addr]["channels"]:
        users[addr]["channels"].remove(ch)
        channels[ch].discard(addr)
        if not channels[ch]: del channels[ch]
        send_text(addr, f"Left channel {ch}")
        print(f"[LEAVE] {users[addr]['username']} <- {ch}")

def handle_list(addr):
    chs = list(channels.keys())
    send_text(addr, "Existing channels:\n  " + "\n  ".join(chs))

def handle_who(data, addr):
    ch = data[4:36].decode().strip("\x00")
    if ch in channels:
        names = [users[a]["username"] for a in channels[ch]]
        send_text(addr, f"Users on {ch}:\n  " + "\n  ".join(names))
    else:
        send_text(addr, f"Channel {ch} does not exist.")

def cleanup():
    while True:
        time.sleep(120)
        now = time.time()
        for addr in list(users.keys()):
            if now - users[addr]["last"] > 120:
                logout_user(addr)

# ---- Main ----
def main():
    global server
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((HOST, PORT))
    print(f"Server started on {HOST}:{PORT}")

    threading.Thread(target=cleanup, daemon=True).start()

    while True:
        data, addr = server.recvfrom(BUF_SIZE)
        if addr not in users and struct.unpack("!I", data[:4])[0] != LOGIN:
            continue
        users.setdefault(addr, {}).update(last=time.time())

        mtype = struct.unpack("!I", data[:4])[0]
        if   mtype == LOGIN:      handle_login(data, addr)
        elif mtype == LOGOUT:     logout_user(addr)
        elif mtype == JOIN:       handle_join(data, addr)
        elif mtype == LEAVE:      handle_leave(data, addr)
        elif mtype == SAY:        handle_say(data, addr)
        elif mtype == LIST:       handle_list(addr)
        elif mtype == WHO:        handle_who(data, addr)

if __name__ == "__main__":
    main()
