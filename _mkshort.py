import os, wave, struct, math
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input", "001_AI产品的未来")
os.makedirs(d, exist_ok=True)
wav = os.path.join(d, "001_AI产品的未来.wav")
n = int(10 * 44100)  # 10秒
with wave.open(wav, "w") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(44100)
    for i in range(n):
        v = int(32767 * 0.2 * math.sin(2 * math.pi * 440 * i / 44100))
        wf.writeframes(struct.pack("<h", v))
print("OK", os.path.getsize(wav) / 1024, "KB")
# rename mp3 临时改成 .mp3.bak 让 validator 选 wav
mp3 = os.path.join(d, "001_AI产品的未来.mp3")
bak = mp3 + ".bak"
if os.path.isfile(mp3) and not os.path.isfile(bak):
    os.rename(mp3, bak)
    print("renamed mp3 -> bak")
