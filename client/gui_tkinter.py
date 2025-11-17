# -*- coding: utf-8 -*-
"""
MoodDJ Pro - Tkinter GUI Client
--------------------------------
功能：
- 使用 Tkinter 建立簡單 GUI，讓使用者輸入心情文字
- 將輸入透過 TCP 傳送到 Server（127.0.0.1:5678）
- 即時顯示伺服器回應（情緒分析結果與歌曲名稱）
- 可與 player.py 同時運作（UDP 播放音樂）
"""
import os, sys
# ✅ 讓 Python 找到上層的 utils 模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.encryptor import encrypt_message, decrypt_message, send_large, recv_large
import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
import peer_discovery
import peer_streamer

# Server 設定
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5678
BUFFER_SIZE = 1024


# 傳送 prompt 到伺服器
def send_prompt_to_server(prompt: str) -> str:
    # 建立 TCP 連線 
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((SERVER_IP, SERVER_PORT))
            # 傳送加密封包（分段）
            encrypted_data = encrypt_message(f"/prompt {prompt}")
            send_large(sock, encrypted_data)
            # 接收封包（分段）
            response_encrypted = recv_large(sock, BUFFER_SIZE)
            decrypted_response = decrypt_message(response_encrypted)
            return decrypted_response.strip()
    except Exception as e:
        return f"[Error] {e}"


# GUI 控制
class MoodDJ_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title(" MoodDJ Pro - Tkinter GUI Client")
        self.root.geometry("640x480")
        self.root.resizable(False, False)
        
        # 🔥 一啟動 GUI 就自動啟動 player
        threading.Thread(target=self.start_player_background, daemon=True).start()

        # 標題
        tk.Label(root, text="MoodDJ Pro", font=("Arial", 18, "bold")).pack(pady=5)
        tk.Label(root, text="Enter your mood and let the DJ pick a song 🎶").pack()

        # 輸入框
        self.prompt_entry = tk.Entry(root, width=50, font=("Arial", 12))
        self.prompt_entry.pack(pady=10)
        self.prompt_entry.bind("<Return>", lambda event: self.send_prompt())

        # 送出按鈕
        self.send_button = tk.Button(
            root, text="Send to Server", command=self.send_prompt, bg="#4CAF50", fg="white", width=20
        )
        self.send_button.pack(pady=5)

        # P2P 按鈕區域
        p2p_frame = tk.Frame(root)
        p2p_frame.pack(pady=5)
        self.p2p_discovery_button = tk.Button(
            p2p_frame, text="Enable P2P Discovery", command=self.start_p2p_discovery, bg="#2196F3", fg="white", width=20
        )
        self.p2p_discovery_button.pack(side=tk.LEFT, padx=5)
        self.p2p_stream_button = tk.Button(
            p2p_frame, text="Start P2P Stream", command=self.start_p2p_stream, bg="#f44336", fg="white", width=20
        )
        self.p2p_stream_button.pack(side=tk.LEFT, padx=5)

        # 顯示狀態區域
        tk.Label(root, text="Server Response:").pack(pady=(15, 0))
        self.response_box = scrolledtext.ScrolledText(root, width=60, height=10, font=("Consolas", 10))
        self.response_box.pack(pady=5)
        self.response_box.insert(tk.END, "Waiting for command...\n")
        self.response_box.configure(state=tk.DISABLED)

        # 底部提示
        tk.Label(root, text="Note: Open player.py to hear music! 🎵", fg="gray").pack(side=tk.BOTTOM, pady=5)

    # --------------------------------------------------------
    # 傳送按鈕行為
    # --------------------------------------------------------
    def send_prompt(self):
        user_input = self.prompt_entry.get().strip()
        if not user_input:
            messagebox.showwarning("Warning", "Please enter your mood text!")
            return

        # 禁用按鈕 避免重複
        self.send_button.config(state=tk.DISABLED)
        self.prompt_entry.delete(0, tk.END)

        # 使用 Thread 
        threading.Thread(target=self._send_thread, args=(user_input,), daemon=True).start()

    def _send_thread(self, text):
        self._log_async(f"[Client] Sending: {text}")
        response = send_prompt_to_server(text)
        self._log_async(response)
        self._log_async("[P2P] Discovery and Streaming status active.")
        self.root.after(0, lambda: self.send_button.config(state=tk.NORMAL))

    def _log(self, msg):
        self.response_box.configure(state=tk.NORMAL)
        self.response_box.insert(tk.END, msg + "\n")
        self.response_box.see(tk.END)
        self.response_box.configure(state=tk.DISABLED)

    def _log_async(self, msg):
        """Schedule UI log updates from worker threads."""
        self.root.after(0, lambda: self._log(msg))

    def start_p2p_discovery(self):
        self._log("[P2P] Starting peer discovery...")
        threading.Thread(target=peer_discovery.main, daemon=True).start()

    def start_p2p_stream(self):
        self._log("[P2P] Starting peer streaming...")
        threading.Thread(target=peer_streamer.main, daemon=True).start()
        
    def start_player_background(self):
        """自動啟動 client/player.py（保持可獨立啟動）"""
        import subprocess, sys, os
        try:
            player_path = os.path.join(os.path.dirname(__file__), "player.py")
            subprocess.Popen([sys.executable, player_path])
            self._log_async("[player] Background player 啟動成功")
        except Exception as e:
            self._log_async(f"[player] 啟動失敗: {e}")

# 主程式

if __name__ == "__main__":
    
    root = tk.Tk()
    app = MoodDJ_GUI(root)
    root.mainloop()