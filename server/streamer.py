# -*- coding: utf-8 -*-
import socket
import subprocess
import time

UDP_PORT = 5680
BUFFER_SIZE = 1024

def broadcast_youtube_audio(audio_url: str):
    """Fetch audio stream from YouTube and broadcast chunks via UDP."""
    print(f"[streamer] Broadcasting YouTube audio: {audio_url}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

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
        sock.sendto(chunk, ( "127.0.0.1" , UDP_PORT))
        print(f"[streamer] Sent chunk {len(chunk)} bytes")
        time.sleep(0.005)

    process.terminate()
    sock.close()
    print("[streamer] Done broadcasting.")