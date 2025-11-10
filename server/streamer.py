# -*- coding: utf-8 -*-
import socket
import subprocess
import time

UDP_PORT = 5680
BUFFER_SIZE = 1024

def broadcast_youtube_audio(audio_url: str, target_ip: str = "127.0.0.1", target_port: int = UDP_PORT):
    """Fetch audio stream from YouTube and broadcast chunks via UDP broadcast."""
    print(f"[streamer] Broadcasting YouTube audio: {audio_url} to all clients on network ({target_ip}:{target_port})")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("0.0.0.0", 0))

    # 使用 ffmpeg 從 YouTube 串流轉成 PCM (16-bit, mono, 44.1kHz)
    cmd = [
        "ffmpeg",
        "-i", audio_url,
        "-f", "s16le",        # 原始 PCM
        "-acodec", "pcm_s16le",
        "-ac", "1",
        "-ar", "44100",
        "-"
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    while True:
        chunk = process.stdout.read(BUFFER_SIZE)
        if not chunk:
            print("[streamer] No more data, stream end.")
            break
        while True:
            try:
                sock.sendto(chunk, (target_ip, target_port))
                print(f"[streamer] Broadcasted chunk {len(chunk)} bytes")
                break
            except OSError as e:
                print(f"[streamer] OSError during sendto: {e}, retrying in 0.05s")
                time.sleep(0.05)
        time.sleep(0.005)

    time.sleep(0.1)
    process.terminate()
    sock.close()
    print("[streamer] Done broadcasting.")