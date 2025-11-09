# -*- coding: utf-8 -*-
import socket

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5678

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((SERVER_IP, SERVER_PORT))
        print("[client] Connected. Type '/text I feel happy'")
        while True:
            cmd = input("> ")
            if not cmd:
                break
            if cmd.startswith("/text "):
                msg = cmd.replace("/text ", "")
                sock.sendall(f"/prompt {msg}".encode())
                print(sock.recv(1024).decode())
            else:
                print("Usage: /text <mood sentence>")

if __name__ == "__main__":
    main()