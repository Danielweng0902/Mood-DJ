# -*- coding: utf-8 -*-
"""
client/client_secure.py
-----------------------------------
支援 Auto-Reconnect / Encryption 的安全版 Client
功能：
- 自動重新連線
- TCP 加密傳輸
- 接收加密回覆並解密顯示
"""
import socket
import time
from utils.encryptor import encrypt_message, decrypt_message

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5678
BUFFER_SIZE = 4096


def connect_to_server():
    """自動重連機制"""
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_IP, SERVER_PORT))
            print("[client] ✅ Connected to server.")
            return sock
        except Exception as e:
            print(f"[client] ⚠️ Connect failed ({e}), retrying in 3s...")
            time.sleep(3)


def main():
    sock = connect_to_server()

    while True:
        try:
            cmd = input("> ")
            if not cmd:
                break

            if cmd.startswith("/text "):
                msg = cmd.replace("/text ", "")
                encrypted = encrypt_message(f"/prompt {msg}")
                sock.sendall(encrypted)
                data = sock.recv(BUFFER_SIZE)
                response = decrypt_message(data)
                print(response)
            else:
                print("Usage: /text <your mood>")
        except (ConnectionResetError, BrokenPipeError, OSError):
            print("[client] ⚠️ Connection lost, auto reconnecting...")
            sock.close()
            sock = connect_to_server()
        except KeyboardInterrupt:
            print("\n[client] Exiting.")
            break

    sock.close()


if __name__ == "__main__":
    main()