# -*- coding: utf-8 -*-
"""
server/server.py
-----------------------------------
支援 Timeout / Encryption / Auto Thread 的安全版 Server
功能：
- TCP 控制 + 多執行緒
- AES/Fernet 加密通訊
- Timeout: 60 秒未活動自動斷線
"""
import os
import sys
import socket
import threading

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
from utils.encryptor import encrypt_message, decrypt_message


# ------------------------------------------------------------
# 伺服器設定
# ------------------------------------------------------------
HOST = "0.0.0.0"
PORT = 5678
BUFFER_SIZE = 4096
BACKLOG = 5


# ------------------------------------------------------------
# 個別 client thread 處理函式
# ------------------------------------------------------------
def handle_client(conn, addr):
    print(f"[server] Connected by {addr}")
    conn.settimeout(60)  # 若 60 秒沒活動自動斷線

    try:
        while True:
            try:
                # 接收並嘗試解密
                encrypted_data = conn.recv(BUFFER_SIZE)
                if not encrypted_data:
                    print(f"[server] {addr} disconnected.")
                    break

                try:
                    data = decrypt_message(encrypted_data)
                except Exception:
                    print(f"[server] ⚠️  Decryption failed from {addr}")
                    continue

                print(f"[server] Received (decrypted): {data}")

                # 指令處理
                if data.startswith("/prompt "):
                    msg = data.replace("/prompt ", "")
                    mood = analyze_text(msg)
                    stream_url = search_youtube_music(mood)

                    # 回覆加密訊息
                    response = f"[server] Mood: {mood}"
                    conn.sendall(encrypt_message(response))

                    # 開新 thread 廣播音樂
                    threading.Thread(
                        target=broadcast_youtube_audio,
                        args=(stream_url,),
                        daemon=True
                    ).start()

                else:
                    conn.sendall(encrypt_message("[server] Invalid command."))

            except socket.timeout:
                print(f"[server] {addr} connection timeout.")
                break

    except Exception as e:
        print(f"[server] Error: {e}")
    finally:
        conn.close()
        print(f"[server] Connection closed: {addr}")


# ------------------------------------------------------------
# 主伺服器啟動邏輯
# ------------------------------------------------------------
def start_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(BACKLOG)
    print(f"[server] Listening on {HOST}:{PORT} (secure mode) ...")

    try:
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[server] Shutting down...")
    finally:
        srv.close()


# ------------------------------------------------------------
# 主程式入口
# ------------------------------------------------------------
if __name__ == "__main__":
    start_server()