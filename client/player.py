# -*- coding: utf-8 -*-
"""
client/player.py
----------------
跨平台 UDP 音樂播放模組：
 - 優先使用 PyAudio（若可用）
 - 若 PyAudio 不可用，則自動改用 sounddevice（macOS / Linux 原生支援）
"""
import socket

UDP_PORT = 5680
BUFFER_SIZE = 1024

# ------------------------------------------------------------
# 嘗試載入 PyAudio；若失敗，自動使用 sounddevice
# ------------------------------------------------------------
try:
    import pyaudio
    AUDIO_BACKEND = "pyaudio"
    print("[player] ✅ Using PyAudio backend")
except Exception as e:
    print("[player] ⚠️ PyAudio unavailable, fallback to sounddevice:", e)
    import numpy as np
    import sounddevice as sd
    AUDIO_BACKEND = "sounddevice"

# ------------------------------------------------------------
# 主函式：監聽 UDP 音訊封包並播放
# ------------------------------------------------------------
def listen_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", UDP_PORT))
    print(f"[player] Listening UDP on port {UDP_PORT} ...")

    if AUDIO_BACKEND == "pyaudio":
        # PyAudio 模式：使用 PortAudio 實時輸出
        audio = pyaudio.PyAudio()
        stream = audio.open(format=audio.get_format_from_width(2),
                            channels=1,
                            rate=44100,
                            output=True)
        try:
            while True:
                data, _ = sock.recvfrom(BUFFER_SIZE)
                if data:
                    stream.write(data)
        except KeyboardInterrupt:
            print("[player] Stopped by user.")
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
            sock.close()

    else:
        # sounddevice 模式：以 NumPy + CoreAudio 播放
        try:
            stream = sd.OutputStream(samplerate=44100, channels=1, dtype='int16')
            stream.start()
            while True:
                data, _ = sock.recvfrom(BUFFER_SIZE)
                if data:
                    samples = np.frombuffer(data, dtype=np.int16)
                    stream.write(samples)
        except KeyboardInterrupt:
            print("[player] Stopped by user.")
        finally:
            stream.stop()
            stream.close()
            sock.close()

# ------------------------------------------------------------
# 主程式入口
# ------------------------------------------------------------
if __name__ == "__main__":
    listen_udp()