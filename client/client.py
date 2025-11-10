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
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 加入專案根目錄
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server"))  # 加入 server/
import socket
import time
import threading
from utils.encryptor import encrypt_message, decrypt_message
from player import play_stream

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5678
BUFFER_SIZE = 4096
UDP_START_PORT = 5680

def find_available_udp_port(start_port):
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as test_sock:
            try:
                test_sock.bind(('', port))
                return port
            except OSError:
                port += 1

def heartbeat_thread():
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as hb:
                hb.connect((SERVER_IP, 5690))
                hb.settimeout(10)
                print("[Heartbeat] ✅ Connected to server.")
                while True:
                    try:
                        hb.sendall(b"ping")
                        resp = hb.recv(32)
                        if not resp:
                            raise ConnectionResetError("Empty response, server closed connection")
                        print(f"[Heartbeat] {resp.decode().strip()}")
                        time.sleep(5)
                    except (socket.timeout, ConnectionResetError, BrokenPipeError) as e_inner:
                        print(f"[Heartbeat] ⚠️ Lost heartbeat: {e_inner}")
                        break
        except Exception as e:
            print(f"[Heartbeat] Retrying in 3s... ({e})")
            time.sleep(3)
            

def connect_to_server():
    """自動重連機制"""
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_IP, SERVER_PORT))
            sock.setblocking(False)
            print("[client] ✅ Connected to server.")
            return sock
        except Exception as e:
            print(f"[client] ⚠️ Connect failed ({e}), retrying in 3s...")
            time.sleep(3)


def main():
    udp_port = find_available_udp_port(UDP_START_PORT)
    print(f"[client] Using UDP port {udp_port} (to avoid conflict with server)")

    heartbeat = threading.Thread(target=heartbeat_thread, daemon=True)
    heartbeat.start()

    sock = connect_to_server()

    # Setup UDP socket listener before sending commands
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp_sock.bind(('', udp_port))
        print(f"[client] UDP listener started on port {udp_port}")
    except Exception as e:
        print(f"[client] Error binding UDP socket on port {udp_port}: {e}")
        udp_sock.close()
        return

    while True:
        try:
            cmd = input("> ")
            if not cmd:
                break

            if cmd.startswith("/text "):
                msg = cmd.replace("/text ", "")

                # Tell server which UDP port client listens on
                try:
                    setudp_msg = encrypt_message(f"/setudp {udp_port}")
                    sock.sendall(setudp_msg)
                except Exception as e:
                    print(f"[client] Error sending /setudp command: {e}")

                encrypted = encrypt_message(f"/prompt {msg}")
                sock.sendall(encrypted)

                # Receive response and decrypt
                try:
                    data = sock.recv(BUFFER_SIZE)
                    if not data:
                        print("[client] No data received from server.")
                        continue
                    try:
                        response = decrypt_message(data)
                    except Exception as e_dec:
                        print(f"[client] Decryption failed: {e_dec}")
                        continue
                    print(response)

                    # If response includes stream URL, start UDP listener thread for playback
                    if "http" in response or "udp://" in response:
                        # Extract URL (simple heuristic)
                        url_start = response.find("http")
                        if url_start == -1:
                            url_start = response.find("udp://")
                        if url_start != -1:
                            url = response[url_start:].split()[0]
                            print(f"[client] Starting audio stream playback from URL: {url}")
                            # Start streamer playback thread
                            threading.Thread(target=streamer.play_stream, args=(udp_sock, url), daemon=True).start()
                except BlockingIOError:
                    # No data available yet
                    pass
                except Exception as e_recv:
                    print(f"[client] Error receiving or processing server response: {e_recv}")

            else:
                print("Usage: /text <your mood>")
            time.sleep(0.05)
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"[client] ⚠️ Connection lost, auto reconnecting... Detail: {e}")
            try:
                sock.close()
            except Exception as e_close:
                print(f"[client] Error closing socket: {e_close}")
            sock = connect_to_server()
        except KeyboardInterrupt:
            print("\n[client] Exiting.")
            break
        except Exception as e:
            print(f"[client] Unexpected error: {e}")
            time.sleep(0.05)

    try:
        sock.close()
    except Exception as e:
        print(f"[client] Error closing socket on exit: {e}")
    try:
        udp_sock.close()
    except Exception as e:
        print(f"[client] Error closing UDP socket on exit: {e}")


if __name__ == "__main__":
    main()