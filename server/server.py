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
from __future__ import annotations

import os
import socket
import sys
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

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
from utils.encryptor import SecureChannel


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 5678
    udp_port: int = 5680  # client/player.py listens on this port
    heartbeat_port: int = 5690
    backlog: int = 5
    buffer_size: int = 4096
    connection_timeout: int = 60
    poll_interval: float = 0.05
    log_interval: float = 1.0


class MoodDJServer:
    """High level orchestration of the TCP control plane + UDP streamer."""

    def __init__(self, config: Optional[ServerConfig] = None) -> None:
        self.config = config or ServerConfig()
        self._last_log = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> None:
        control_socket = self._create_control_socket()
        print(f"[server] Listening [TCP] control on {self.config.host}:{self.config.port}")
        print(f"[server] Target UDP stream port (client listens here): {self.config.udp_port}")

        threading.Thread(target=self._heartbeat_server, daemon=True).start()

        try:
            while True:
                try:
                    conn, addr = control_socket.accept()
                except BlockingIOError:
                    self._log_nonblocking_loop()
                    time.sleep(self.config.poll_interval)
                    continue

                threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr),
                    daemon=True,
                ).start()
        except KeyboardInterrupt:
            print("\n[server] Shutting down...")
        finally:
            control_socket.close()

    # ------------------------------------------------------------------
    # Client handling
    # ------------------------------------------------------------------
    def _handle_client(self, conn: socket.socket, addr: Tuple[str, int]) -> None:
        print(f"[server] Connected by {addr}")
        conn.settimeout(self.config.connection_timeout)
        conn.setblocking(False)
        channel = SecureChannel(conn, buffer_size=self.config.buffer_size)

        try:
            while True:
                try:
                    message = channel.recv_text()
                except BlockingIOError:
                    time.sleep(self.config.poll_interval)
                    continue

                if message is None:
                    print(f"[server] {addr} disconnected.")
                    break

                print(f"[server] Received (decrypted): {message}")
                self._send_text(channel, f"[server] Mood processed: {message}")
                self._process_command(message, channel)
        except socket.timeout:
            print(f"[server] {addr} connection timeout.")
        except Exception as exc:
            print(f"[server] Error: {exc}")
        finally:
            conn.close()
            print(f"[server] Connection closed: {addr}")

    def _process_command(self, message: str, channel: SecureChannel) -> None:
        if message.startswith("/prompt "):
            prompt = message.replace("/prompt ", "", 1)
            self._handle_prompt(prompt, channel)
        else:
            self._send_text(channel, "[server] Invalid command.")

    def _handle_prompt(self, prompt: str, channel: SecureChannel) -> None:
        mood = analyze_text(prompt)
        stream_url = search_youtube_music(mood)

        self._send_text(channel, f"[server] Mood: {mood}")
        print(f"[server] ▶️  Start streaming to UDP port {self.config.udp_port}")

        threading.Thread(
            target=broadcast_youtube_audio,
            args=(stream_url,),
            daemon=True,
        ).start()

    def _send_text(self, channel: SecureChannel, message: str) -> None:
        while True:
            try:
                channel.send_text(message)
                return
            except BlockingIOError:
                time.sleep(self.config.poll_interval)

    # ------------------------------------------------------------------
    # Heartbeat handling
    # ------------------------------------------------------------------
    def _heartbeat_server(self) -> None:
        hb_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        hb_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        hb_sock.bind((self.config.host, self.config.heartbeat_port))
        hb_sock.listen(self.config.backlog)
        hb_sock.setblocking(False)
        print(f"[server] Listening [TCP] heartbeat on {self.config.host}:{self.config.heartbeat_port}")

        while True:
            try:
                conn, addr = hb_sock.accept()
            except BlockingIOError:
                time.sleep(self.config.poll_interval * 6)
                continue

            print(f"[heartbeat] Connected by {addr}")
            threading.Thread(target=self._handle_heartbeat, args=(conn,), daemon=True).start()

    def _handle_heartbeat(self, conn: socket.socket) -> None:
        """Keep the heartbeat connection alive until the client disconnects."""
        conn.setblocking(True)
        try:
            while True:
                data = conn.recv(32)
                if not data:
                    break
                msg = data.decode(errors="replace").strip()
                if msg == "ping":
                    conn.sendall(b"pong")
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _create_control_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.config.host, self.config.port))
        sock.listen(self.config.backlog)
        sock.setblocking(False)
        return sock

    def _log_nonblocking_loop(self) -> None:
        now = time.time()
        if now - self._last_log >= self.config.log_interval:
            print("[server] Nonblocking loop active")
            self._last_log = now


# ------------------------------------------------------------
# 主程式入口
# ------------------------------------------------------------
def start_server() -> None:
    MoodDJServer().start()


if __name__ == "__main__":
    start_server()
