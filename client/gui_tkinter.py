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
from tkinter import messagebox, scrolledtext, ttk
import peer_discovery
import peer_streamer

# Server 設定
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5678
BUFFER_SIZE = 1024
BUTTON_MIN_WIDTH = 140
BUTTON_STYLE = "Mood.TButton"


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
        self.root.title("MoodDJ Pro - Tkinter GUI Client")
        self.root.geometry("720x520")
        self.root.minsize(620, 420)
        self.root.configure(padx=18, pady=18)
        self.root.columnconfigure(0, weight=1)
        for row in range(5):
            self.root.rowconfigure(row, weight=1 if row == 3 else 0)

        style = ttk.Style()
        style.configure(BUTTON_STYLE, padding=(10, 8), font=("Arial", 11))
        normal_fg = style.lookup("TButton", "foreground", default="#111111")
        style.map(BUTTON_STYLE, foreground=[("disabled", normal_fg), ("!disabled", normal_fg)])
        
        # 🔥 一啟動 GUI 就自動啟動 player
        threading.Thread(target=self.start_player_background, daemon=True).start()

        # 標題
        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="MoodDJ Pro", font=("Arial", 18, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(header, text="Enter your mood and let the DJ pick a song 🎶").grid(
            row=1, column=0, sticky="w", pady=(2, 0)
        )

        # 輸入框
        input_frame = ttk.LabelFrame(root, text="Mood Prompt")
        input_frame.grid(row=1, column=0, sticky="ew", pady=(15, 10))
        input_frame.columnconfigure(0, weight=1)
        self.prompt_entry = ttk.Entry(input_frame, font=("Arial", 12))
        self.prompt_entry.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.prompt_entry.bind("<Return>", lambda event: self.send_prompt())
        self.prompt_entry.focus_set()

        # 控制按鈕
        button_frame = ttk.Frame(root)
        button_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        for col in range(3):
            button_frame.columnconfigure(col, weight=1, uniform="btn", minsize=BUTTON_MIN_WIDTH)

        self.send_button = ttk.Button(
            button_frame, text="Send to Server", command=self.send_prompt, style=BUTTON_STYLE
        )
        self.send_button.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.p2p_discovery_button = ttk.Button(
            button_frame, text="Enable P2P Discovery", command=self.start_p2p_discovery, style=BUTTON_STYLE
        )
        self.p2p_discovery_button.grid(row=0, column=1, sticky="nsew", padx=4)

        self.p2p_stream_button = ttk.Button(
            button_frame, text="Start P2P Stream", command=self.start_p2p_stream, style=BUTTON_STYLE
        )
        self.p2p_stream_button.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        # 顯示狀態區域
        response_frame = ttk.LabelFrame(root, text="Server Response")
        response_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        response_frame.columnconfigure(0, weight=1)
        response_frame.rowconfigure(0, weight=1)
        self.response_box = scrolledtext.ScrolledText(
            response_frame,
            width=60,
            height=12,
            font=("Consolas", 10),
            wrap=tk.WORD,
        )
        self.response_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.response_box.insert(tk.END, "Waiting for command...\n")
        self.response_box.configure(state=tk.DISABLED)

        # 底部提示
        footer = ttk.Label(
            root, text="Note: Open player.py to hear music! 🎵", foreground="gray"
        )
        footer.grid(row=4, column=0, sticky="ew", pady=(10, 0))

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
