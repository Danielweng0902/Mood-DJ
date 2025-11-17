# -*- coding: utf-8 -*-
"""
client/player.py
----------------
跨平台 UDP 音樂播放模組：
 - 優先使用 PyAudio（若可用）
 - 若 PyAudio 不可用，則自動改用 sounddevice（macOS / Linux 原生支援）
"""
from __future__ import annotations

import socket
import sys
from typing import Iterable, Optional, Protocol

UDP_PORT = 5680
BUFFER_SIZE = 1764  # 20ms of 44.1kHz mono PCM (matching server stream)
SAMPLE_RATE = 44100
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2


class PlaybackBackend(Protocol):
    """Minimal interface implemented by all playback backends."""

    def play(self, chunk: bytes) -> None: ...
    def close(self) -> None: ...


class PyAudioBackend:
    """PortAudio-based audio output."""

    def __init__(self) -> None:
        import pyaudio  # type: ignore

        self._pa = pyaudio.PyAudio()
        self._stream = self._pa.open(
            format=self._pa.get_format_from_width(SAMPLE_WIDTH_BYTES),
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            output=True,
        )
        print("[player] ✅ Using PyAudio backend")

    def play(self, chunk: bytes) -> None:
        self._stream.write(chunk)

    def close(self) -> None:
        self._stream.stop_stream()
        self._stream.close()
        self._pa.terminate()


class SoundDeviceBackend:
    """sounddevice (CoreAudio/ALSA) fallback backend."""

    def __init__(self) -> None:
        import numpy as np  # type: ignore
        import sounddevice as sd  # type: ignore

        self._np = np
        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
        )
        self._stream.start()
        print("[player] ✅ Using sounddevice backend")

    def play(self, chunk: bytes) -> None:
        samples = self._np.frombuffer(chunk, dtype=self._np.int16)
        self._stream.write(samples)

    def close(self) -> None:
        self._stream.stop()
        self._stream.close()


def create_backend() -> PlaybackBackend:
    """Return the best available playback backend."""
    try:
        return PyAudioBackend()
    except Exception as exc:
        print(f"[player] ⚠️ PyAudio unavailable, falling back to sounddevice: {exc}", file=sys.stderr)
        try:
            return SoundDeviceBackend()
        except Exception as fallback_exc:
            raise RuntimeError("No valid audio backend available") from fallback_exc


def iter_audio_packets(sock: socket.socket) -> Iterable[bytes]:
    """Yield raw PCM packets received over UDP."""
    while True:
        data, _ = sock.recvfrom(BUFFER_SIZE)
        if data:
            yield data


def listen_udp(host: str = "127.0.0.1", port: int = UDP_PORT) -> None:
    """Bind to the UDP stream and play audio using the preferred backend."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"[player] Listening UDP on {host}:{port} ...")

    backend: Optional[PlaybackBackend] = None
    try:
        backend = create_backend()
        for chunk in iter_audio_packets(sock):
            backend.play(chunk)
    except KeyboardInterrupt:
        print("[player] Stopped by user.")
    finally:
        if backend:
            backend.close()
        sock.close()


if __name__ == "__main__":
    listen_udp()
