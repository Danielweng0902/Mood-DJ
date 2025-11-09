# -*- coding: utf-8 -*-
import socket
import threading
from mood_analyzer import analyze_text
from music_manager import search_youtube_music
from streamer import broadcast_youtube_audio

HOST = "0.0.0.0"
PORT = 5678
BUFFER_SIZE = 1024
BACKLOG = 5

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind((HOST, PORT))
srv.listen(BACKLOG)
print(f"[server] Listening on {HOST}:{PORT} ...")

def handle_client(conn, addr):
    print(f"[server] Connected by {addr}")
    try:
        while True:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            text = data.decode(errors="replace").strip()
            print(f"[server] Received: {text}")

            if text.startswith("/prompt "):
                msg = text.replace("/prompt ", "")
                mood = analyze_text(msg)
                stream_url = search_youtube_music(mood)
                conn.sendall(f"[server] Mood: {mood}\n".encode())

                # 開新 thread 廣播 YouTube 串流
                threading.Thread(target=broadcast_youtube_audio, args=(stream_url,), daemon=True).start()
            else:
                conn.sendall(b"[server] Invalid command.\n")
    except Exception as e:
        print(f"[server] Error: {e}")
    finally:
        conn.close()

try:
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
except KeyboardInterrupt:
    print("\n[server] Shutting down...")
finally:
    srv.close()