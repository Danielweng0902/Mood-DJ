import sounddevice as sd
from scipy.io.wavfile import write

def record_audio(duration=5, output="temp.wav"):
    """Record environment sound for a few seconds."""
    fs = 44100
    print(f"[recorder] Recording {duration}s ...")
    data = sd.rec(int(duration*fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    write(output, fs, data)
    print(f"[recorder] Saved: {output}")
    return output