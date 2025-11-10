# -*- coding: utf-8 -*-
"""
server/server.py
-----------------------------------
支援 Timeout / Encryption / Auto Thread 的安全版 Server
功能：
- TCP 控制 + 多執行緒
- AES/Fernet 加密通訊
- Timeout: 60 秒未活動自動斷線
- 非阻塞主迴圈（節流列印）
"""
import os
import sys
import socket
import threading
import time

# ------------------------------------------------------------
# 讓 Python 可以正確匯入上層 utils 模組
# ------------------------------------------------------------
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ------------------------------------------------------------
# 模組匯入
# ------------------------------------------------------------
from mood_analyzer import analyze_text
from music_manager import search_youtube_music
from streamer import broadcast_youtube_audio
from utils.encryptor import encrypt_message, decrypt_message, send_large, recv_large

# ------------------------------------------------------------
# 伺服器設定
# ------------------------------------------------------------
HOST = "0.0.0.0"
PORT = 5678
BUFFER_SIZE = 4096
BACKLOG = 5

# 串流目的地 UDP Port（⚠️ 由 client/player.py 綁定接收；server 不可綁這個 port）
UDP_PORT = 5680

# ------------------------------------------------------------
# 個別 client thread 處理函式
# ------------------------------------------------------------
def handle_client(conn, addr):
    print(f"[server] Connected by {addr}")
    conn.settimeout(60)      # 若 60 秒沒活動自動斷線
    conn.setblocking(False)  # 非阻塞 socket；我們用 try/except + sleep 來友善輪詢

    try:
        while True:
            try:
                # 非阻塞接收封包（分段）
                try:
                    encrypted_data = recv_large(conn, BUFFER_SIZE)
                except BlockingIOError:
                    time.sleep(0.05)
                    continue

                if not encrypted_data:
                    print(f"[server] {addr} disconnected.")
                    break

                # 解密
                try:
                    data = decrypt_message(encrypted_data)
                except Exception:
                    print(f"[server] ⚠️  Decryption failed from {addr}")
                    continue

                print(f"[server] Received (decrypted): {data}")

                # 回覆封包（加密 + 分段）
                response = f"[server] Mood processed: {data}"
                while True:
                    try:
                        send_large(conn, encrypt_message(response))
                        break
                    except BlockingIOError:
                        time.sleep(0.05)

                # 指令處理
                if data.startswith("/prompt "):
                    msg = data.replace("/prompt ", "", 1)
                    mood = analyze_text(msg)
                    stream_url = search_youtube_music(mood)

                    # 回覆分析結果
                    encrypted_response = encrypt_message(f"[server] Mood: {mood}")
                    sent = 0
                    while sent < len(encrypted_response):
                        try:
                            sent += conn.send(encrypted_response[sent:])
                        except BlockingIOError:
                            time.sleep(0.05)

                    # 提示串流目的地（方便你對照 player）
                    print(f"[server] ▶️  Start streaming to UDP port {UDP_PORT}")

                    # 開新 thread 廣播音樂（由 streamer 決定送往 127.0.0.1:UDP_PORT 或廣播位址）
                    threading.Thread(
                        target=broadcast_youtube_audio,
                        args=(stream_url,),   # 若你的 streamer 支援帶入目標，改成 args=(stream_url, '127.0.0.1', UDP_PORT)
                        daemon=True
                    ).start()

                else:
                    invalid_msg = encrypt_message("[server] Invalid command.")
                    sent = 0
                    while sent < len(invalid_msg):
                        try:
                            sent += conn.send(invalid_msg[sent:])
                        except BlockingIOError:
                            time.sleep(0.05)

            except socket.timeout:
                print(f"[server] {addr} connection timeout.")
                break

    except Exception as e:
        print(f"[server] Error: {e}")
    finally:
        conn.close()
        print(f"[server] Connection closed: {addr}")

# ------------------------------------------------------------
# 心跳監控伺服器（每條心跳連線用 blocking recv，不影響主迴圈）
# ------------------------------------------------------------
def heartbeat_server():
    hb_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    hb_port = 5690
    hb_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    hb_sock.bind((HOST, hb_port))
    hb_sock.listen(5)
    hb_sock.setblocking(False)
    print(f"[server] Listening [TCP] heartbeat on {HOST}:{hb_port}")

    while True:
        try:
            conn, addr = hb_sock.accept()
            print(f"[heartbeat] Connected by {addr}")
            threading.Thread(target=handle_heartbeat, args=(conn, addr), daemon=True).start()
        except BlockingIOError:
            time.sleep(0.3)
            continue

def handle_heartbeat(conn, addr):
    """保持心跳連線直到 client 主動中斷（阻塞式，簡單穩定）"""
    conn.setblocking(True)
    try:
        while True:
            data = conn.recv(32)
            if not data:
                break
            msg = data.decode(errors="replace").strip()
            # 可視需求加上驗證
            if msg == "ping":
                conn.sendall(b"pong")
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        conn.close()

# ------------------------------------------------------------
# 主伺服器啟動邏輯（Nonblocking + 列印節流）
# ------------------------------------------------------------
def start_server():
    # TCP 控制端
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(BACKLOG)
    srv.setblocking(False)

    print(f"[server] Listening [TCP] control  on {HOST}:{PORT}")
    print(f"[server] Target UDP stream port (client listens here): {UDP_PORT}")

    # 啟動心跳監控執行緒
    threading.Thread(target=heartbeat_server, daemon=True).start()

    last_log = 0.0
    try:
        while True:
            try:
                conn, addr = srv.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except BlockingIOError:
                # 節流列印，避免洗版
                now = time.time()
                if now - last_log >= 1.0:
                    print("[server] Nonblocking loop active")
                    last_log = now
                time.sleep(0.05)
                continue
    except KeyboardInterrupt:
        print("\n[server] Shutting down...")
    finally:
        srv.close()

# ------------------------------------------------------------
# 主程式入口
# ------------------------------------------------------------
if __name__ == "__main__":
    start_server()