# server/peer_registry.py
# 用於管理 peer 清單（IP + Port）

import socket, json, threading

PEER_PORT = 5700
peers = []

def registry_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PEER_PORT))
    print(f"[peer_registry] Listening on UDP {PEER_PORT} ...")

    while True:
        data, addr = sock.recvfrom(4096)
        msg = data.decode()
        if msg == "LIST":
            sock.sendto(json.dumps(peers).encode(), addr)
        else:
            try:
                peer = json.loads(msg)
                if peer not in peers:
                    peers.append(peer)
                    print(f"[peer_registry] Registered {peer}")
            except Exception:
                pass

if __name__ == "__main__":
    threading.Thread(target=registry_server, daemon=False).start()