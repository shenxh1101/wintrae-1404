
import os
import wave
import struct
import math
from pathlib import Path


def generate_test_wav(output_path, duration_seconds=120, sample_rate=44100, frequency=440):
    """生成一个简单的正弦波 WAV 文件用于测试"""
    n_samples = int(duration_seconds * sample_rate)

    with wave.open(output_path, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for i in range(n_samples):
            value = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * i / sample_rate))
            wav_file.writeframes(struct.pack('<h', value))

    return output_path


def main():
    test_dir = Path(__file__).parent / "input" / "001_AI产品的未来"
    test_dir.mkdir(parents=True, exist_ok=True)

    wav_path = test_dir / "001_AI产品的未来.wav"

    print(f"🎵 正在生成测试音频文件: {wav_path}")
    print("   时长: 2分钟")
    print("   格式: WAV (16bit, 44.1kHz, 单声道)")
    print("   这可能需要几秒钟...")

    generate_test_wav(str(wav_path), duration_seconds=120)

    file_size = os.path.getsize(wav_path) / 1024 / 1024
    print(f"\n✅ 测试音频生成完成!")
    print(f"   文件大小: {file_size:.2f} MB")

    mp3_path = test_dir / "001_AI产品的未来.mp3"
    if mp3_path.exists():
        mp3_path.unlink()
        print(f"   已删除旧的占位 MP3 文件")


if __name__ == "__main__":
    main()
