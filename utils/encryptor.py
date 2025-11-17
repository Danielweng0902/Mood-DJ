# -*- coding: utf-8 -*-
"""
utils/encryptor.py
-----------------------------------
封裝訊息加密與解密功能 (AES-based Fernet)
供 client / server 共用
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from cryptography.fernet import Fernet

# 你可以固定一組 key（或動態生成後寫入檔案）
# 產生新 key 可用：
# >>> from cryptography.fernet import Fernet
# >>> print(Fernet.generate_key())

SECRET_KEY = b"jZoOAKeJP1FpjZP_PbQo6b7T4-mzK2qOxi6_9IjECK4="
cipher = Fernet(SECRET_KEY)

HEADER_SIZE = 10  # bytes reserved for the length prefix


def encrypt_message(message: str) -> bytes:
    """加密字串成 bytes"""
    return cipher.encrypt(message.encode())


def decrypt_message(encrypted_data: bytes) -> str:
    """解密 bytes 為字串"""
    return cipher.decrypt(encrypted_data).decode()


def _recv_exact(sock, size: int) -> bytes:
    """Read exactly size bytes unless the socket closes."""
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            break
        chunks.extend(chunk)
    return bytes(chunks)


# ============================================================
#  Large Message Split / Join Utilities
# ============================================================

def send_large(sock, data: bytes) -> None:
    """傳送大封包：前置固定長度 header，確保 framing 一致"""
    length = len(data)
    header = f"{length:<{HEADER_SIZE}}".encode("ascii")
    sock.sendall(header + data)


def recv_large(sock, buffer_size: int = 1024) -> bytes:
    """接收大封包：先讀 header，再根據長度讀完整內容"""
    header = _recv_exact(sock, HEADER_SIZE)
    if not header:
        return b""

    try:
        total_len = int(header.decode().strip())
    except ValueError as exc:
        raise ValueError(f"Invalid length header: {header!r}") from exc

    data = bytearray()
    while len(data) < total_len:
        chunk = sock.recv(min(buffer_size, total_len - len(data)))
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


@dataclass
class SecureChannel:
    """Helper that encapsulates encrypt/decrypt + framing for a socket."""

    sock: Any
    buffer_size: int = 4096

    def send_text(self, message: str) -> None:
        """Encrypt and send a UTF-8 string."""
        send_large(self.sock, encrypt_message(message))

    def recv_text(self) -> Optional[str]:
        """
        Receive and decrypt a single message.
        Returns None when the remote side closed the socket.
        """
        payload = recv_large(self.sock, self.buffer_size)
        if not payload:
            return None
        return decrypt_message(payload)
