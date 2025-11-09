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

from utils.encryptor import encrypt_message, decrypt_message
import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

# ------------------------------------------------------------
# Server 設定
# ------------------------------------------------------------
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5678
BUFFER_SIZE = 1024


# ------------------------------------------------------------
# 傳送 prompt 到伺服器的函式
# ------------------------------------------------------------
def send_prompt_to_server(prompt: str) -> str:
    """建立 TCP 連線 → 傳送 /prompt 指令（加密）→ 接收伺服器回覆（解密）"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((SERVER_IP, SERVER_PORT))
            # 傳送加密指令
            encrypted_data = encrypt_message(f"/prompt {prompt}")
            sock.sendall(encrypted_data)
            # 接收加密回覆並解密
            response = sock.recv(BUFFER_SIZE)
            decrypted_response = decrypt_message(response)
            return decrypted_response.strip()
    except Exception as e:
        return f"[Error] {e}"


# ------------------------------------------------------------
# GUI 控制邏輯
# ------------------------------------------------------------
class MoodDJ_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎧 MoodDJ Pro - Tkinter GUI Client")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

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

        # 禁用按鈕避免重複按
        self.send_button.config(state=tk.DISABLED)
        self.prompt_entry.delete(0, tk.END)

        # 使用 Thread 避免 UI 卡住
        threading.Thread(target=self._send_thread, args=(user_input,), daemon=True).start()

    def _send_thread(self, text):
        self._log(f"[Client] Sending: {text}")
        response = send_prompt_to_server(text)
        self._log(response)
        self.send_button.config(state=tk.NORMAL)

    def _log(self, msg):
        self.response_box.configure(state=tk.NORMAL)
        self.response_box.insert(tk.END, msg + "\n")
        self.response_box.see(tk.END)
        self.response_box.configure(state=tk.DISABLED)


# ------------------------------------------------------------
# 主程式入口
# ------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = MoodDJ_GUI(root)
    root.mainloop()