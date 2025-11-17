# -*- coding: utf-8 -*-
"""
client/client.py
-----------------------------------
支援 Auto-Reconnect / Encryption 的安全版 Client
功能：
- 自動重新連線
- TCP 加密傳輸
- 接收加密回覆並解密顯示
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
from dataclasses import dataclass
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server"))

from utils.encryptor import SecureChannel


@dataclass(frozen=True)
class ClientConfig:
    server_ip: str = "127.0.0.1"
    server_port: int = 5678
    heartbeat_port: int = 5690
    buffer_size: int = 4096
    poll_interval: float = 0.05
    heartbeat_interval: float = 5.0


class MoodDJClient:
    """Command-line TCP client with automatic reconnect + heartbeat."""

    def __init__(self, config: Optional[ClientConfig] = None) -> None:
        self.config = config or ClientConfig()
        self._control_sock: Optional[socket.socket] = None
        self._channel: Optional[SecureChannel] = None
        self._running = True

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def run(self) -> None:
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        self._connect_control()

        try:
            while True:
                try:
                    cmd = input("> ").strip()
                except EOFError:
                    break

                if not cmd:
                    continue
                if not cmd.startswith("/text "):
                    print("Usage: /text <your mood>")
                    continue

                prompt = cmd.replace("/text ", "", 1)
                self._handle_prompt(prompt)
        except KeyboardInterrupt:
            print("\n[client] Exiting.")
        finally:
            self._running = False
            self._close_control()

    # ------------------------------------------------------------------
    # Networking helpers
    # ------------------------------------------------------------------
    def _connect_control(self) -> None:
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.config.server_ip, self.config.server_port))
                sock.setblocking(False)
                self._control_sock = sock
                self._channel = SecureChannel(sock, buffer_size=self.config.buffer_size)
                print("[client] ✅ Connected to server.")
                return
            except Exception as exc:
                print(f"[client] ⚠️ Connect failed ({exc}), retrying in 3s...")
                time.sleep(3)

    def _reconnect(self) -> None:
        self._close_control()
        self._connect_control()

    def _close_control(self) -> None:
        if self._control_sock:
            try:
                self._control_sock.close()
            except OSError:
                pass
        self._control_sock = None
        self._channel = None

    def _ensure_channel(self) -> SecureChannel:
        if not self._channel:
            raise ConnectionError("Client is not connected to the server")
        return self._channel

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _handle_prompt(self, prompt: str) -> None:
        while True:
            try:
                channel = self._ensure_channel()
                self._send_text(channel, f"/prompt {prompt}")
                ack = self._wait_for_message(channel)
                if ack:
                    print(ack)
                response = self._wait_for_message(channel)
                if response:
                    print(response)
                    self._maybe_hint_player(response)
                return
            except (ConnectionResetError, ConnectionError, BrokenPipeError, OSError) as exc:
                print(f"[client] ⚠️ Connection lost during request ({exc}), reconnecting...")
                self._reconnect()
            except Exception as exc:
                print(f"[client] Unexpected error: {exc}")
                time.sleep(self.config.poll_interval)

    def _send_text(self, channel: SecureChannel, message: str) -> None:
        while True:
            try:
                channel.send_text(message)
                return
            except BlockingIOError:
                time.sleep(self.config.poll_interval)

    def _wait_for_message(self, channel: SecureChannel) -> str:
        while True:
            try:
                message = channel.recv_text()
            except BlockingIOError:
                time.sleep(self.config.poll_interval)
                continue

            if message is None:
                raise ConnectionResetError("Server closed the connection")
            return message

    def _maybe_hint_player(self, response: str) -> None:
        if "http" in response or "udp://" in response:
            print("[client] 💡 Run client/player.py to start listening to the UDP stream.")

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------
    def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                with socket.create_connection(
                    (self.config.server_ip, self.config.heartbeat_port), timeout=10
                ) as hb:
                    hb.settimeout(10)
                    print("[heartbeat] ✅ Connected to server.")
                    while self._running:
                        hb.sendall(b"ping")
                        resp = hb.recv(32)
                        if not resp:
                            raise ConnectionResetError("Empty response, server closed connection")
                        print(f"[heartbeat] {resp.decode().strip()}")
                        time.sleep(self.config.heartbeat_interval)
            except Exception as exc:
                if not self._running:
                    break
                print(f"[heartbeat] Retrying in 3s... ({exc})")
                time.sleep(3)


def main() -> None:
    MoodDJClient().run()


if __name__ == "__main__":
    main()
