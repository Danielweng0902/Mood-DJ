# -*- coding: utf-8 -*-
"""
client/peer_discovery.py
-----------------------------------
功能：
 - 向伺服器註冊自己的 IP / UDP port
 - 向伺服器請求目前線上 peers 清單
 - 可被其他模組（如 peer_streamer）匯入使用
"""
import socket
import json
import threading
import time

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5700    # P2P 註冊用獨立 port

class PeerDiscovery:
    def __init__(self, local_ip="127.0.0.1", udp_port=5680):
        self.local_ip = local_ip
        self.udp_port = udp_port
        self.peers = []
        self.running = False

    def register_self(self):
        """註冊自己的 IP/Port 給 server"""
        msg = json.dumps({"ip": self.local_ip, "port": self.udp_port})
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(msg.encode(), (SERVER_IP, SERVER_PORT))

    def fetch_peers(self):
        """向 server 請求 peers"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(b"LIST", (SERVER_IP, SERVER_PORT))
            s.settimeout(2)
            try:
                data, _ = s.recvfrom(4096)
                self.peers = json.loads(data.decode())
            except socket.timeout:
                pass
        return self.peers

    def auto_refresh(self):
        """背景自動更新 peer list"""
        self.running = True
        while self.running:
            self.register_self()
            self.fetch_peers()
            time.sleep(10)

    def start(self):
        t = threading.Thread(target=self.auto_refresh, daemon=True)
        t.start()
        print("[peer_discovery] Auto peer sync started.")

    def stop(self):
        self.running = False
        print("[peer_discovery] Peer sync stopped.")


def main(local_ip="127.0.0.1", udp_port=5680):
    """
    Simple entry point so other modules (e.g. gui_tkinter) can launch the
    background peer discovery loop without importing the class manually.
    """
    discovery = PeerDiscovery(local_ip=local_ip, udp_port=udp_port)
    try:
        discovery.auto_refresh()
    except KeyboardInterrupt:
        discovery.stop()


if __name__ == "__main__":
    main()
