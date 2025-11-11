# -*- coding: utf-8 -*-
"""
client/peer_streamer.py
-----------------------------------
功能：
 - P2P 音樂中繼 / 接收
 - 主 peer 將 UDP 音訊送給其他 peers
 - 其他 peer 收到後直接播放（PyAudio 或 sounddevice）
"""
import socket
import threading
import numpy as np

try:
    import pyaudio
    BACKEND = "pyaudio"
except Exception:
    import sounddevice as sd
    BACKEND = "sounddevice"

BUFFER_SIZE = 1024

class PeerStreamer:
    def __init__(self, peers, local_port=5681):
        self.peers = peers
        self.local_port = local_port
        self.running = False

    # === 傳送音訊資料到其他 peers ===
    def relay_audio(self, chunk: bytes):
        for peer in self.peers:
            try:
                ip, port = peer["ip"], peer["port"]
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.sendto(chunk, (ip, port))
            except Exception as e:
                print(f"[peer_streamer] Send error: {e}")

    # === 收音訊並播放 ===
    def listen_audio(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", self.local_port))
        print(f"[peer_streamer] Listening UDP on {self.local_port} for P2P stream...")
        self.running = True

        if BACKEND == "pyaudio":
            audio = pyaudio.PyAudio()
            stream = audio.open(format=pyaudio.paInt16, channels=1, rate=44100, output=True)
            while self.running:
                data, _ = sock.recvfrom(BUFFER_SIZE)
                if data:
                    stream.write(data)
        else:
            import sounddevice as sd
            with sd.OutputStream(samplerate=44100, channels=1, dtype='int16') as stream:
                while self.running:
                    data, _ = sock.recvfrom(BUFFER_SIZE)
                    if data:
                        samples = np.frombuffer(data, dtype=np.int16)
                        stream.write(samples)

    def start_listener(self):
        threading.Thread(target=self.listen_audio, daemon=True).start()
        print("[peer_streamer] Receiver thread started.")

    def stop(self):
        self.running = False
        print("[peer_streamer] Stopped.")


def main(peers=None, local_port=5681):
    """
    Blocking entry point used by the GUI to start a standalone UDP listener.
    """
    streamer = PeerStreamer(peers or [], local_port=local_port)
    try:
        streamer.listen_audio()
    except KeyboardInterrupt:
        streamer.stop()


if __name__ == "__main__":
    main()
