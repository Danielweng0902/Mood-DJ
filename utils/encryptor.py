# -*- coding: utf-8 -*-
"""
utils/encryptor.py
-----------------------------------
封裝訊息加密與解密功能 (AES-based Fernet)
供 client / server 共用
"""
from cryptography.fernet import Fernet

# 你可以固定一組 key（或動態生成後寫入檔案）
# 產生新 key 可用：
# >>> from cryptography.fernet import Fernet
# >>> print(Fernet.generate_key())

SECRET_KEY = b'jZoOAKeJP1FpjZP_PbQo6b7T4-mzK2qOxi6_9IjECK4='
cipher = Fernet(SECRET_KEY)


def encrypt_message(message: str) -> bytes:
    """加密字串成 bytes"""
    return cipher.encrypt(message.encode())


def decrypt_message(encrypted_data: bytes) -> str:
    """解密 bytes 為字串"""
    return cipher.decrypt(encrypted_data).decode()

# ============================================================
#  Large Message Split / Join Utilities
# ============================================================

def send_large(sock, data: bytes):
    """傳送大封包：前置 10-byte 長度 header"""
    length = len(data)
    header = f"{length:<10}".encode()  # 固定 10 位，左對齊填空
    sock.sendall(header + data)

def recv_large(sock, buffer_size=1024):
    """接收大封包：先讀 header，再根據長度讀完整內容"""
    header = sock.recv(10)
    if not header:
        return b""
    total_len = int(header.decode().strip())
    data = b""
    while len(data) < total_len:
        chunk = sock.recv(buffer_size)
        if not chunk:
            break
        data += chunk
    return data