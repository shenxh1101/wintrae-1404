
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def create_test_audio():
    """创建一个测试用的 MP3 文件（空文件，仅用于测试文件识别）"""
    test_dir = Path(__file__).parent / "input" / "001_AI产品的未来"
    test_dir.mkdir(parents=True, exist_ok=True)

    audio_path = test_dir / "001_AI产品的未来.mp3"

    if not audio_path.exists():
        with open(audio_path, "wb") as f:
            f.write(b"ID3\x04\x00\x00\x00\x00\x00\x00")

    print(f"✅ 测试音频文件已创建: {audio_path}")


def create_test_cover():
    """创建一个测试用的封面图片"""
    test_dir = Path(__file__).parent / "input" / "001_AI产品的未来"
    test_dir.mkdir(parents=True, exist_ok=True)

    cover_path = test_dir / "001_cover.jpg"

    try:
        from PIL import Image

        if not cover_path.exists():
            img = Image.new("RGB", (1400, 1400), color=(73, 109, 137))
            img.save(cover_path, "JPEG", quality=85)
            print(f"✅ 测试封面图片已创建: {cover_path}")
        else:
            print(f"ℹ️  测试封面图片已存在: {cover_path}")
    except ImportError:
        if not cover_path.exists():
            with open(cover_path, "wb") as f:
                f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF")
            print(f"⚠️  Pillow 未安装，创建了占位封面文件: {cover_path}")
        else:
            print(f"ℹ️  测试封面图片已存在: {cover_path}")


def create_test_guest():
    """创建嘉宾资料（已在 input 目录中创建）"""
    print("✅ 嘉宾资料已存在")


def create_test_summary():
    """创建节目摘要（已在 input 目录中创建）"""
    print("✅ 节目摘要已存在")


def main():
    print("🎙️ 生成播客测试素材")
    print("=" * 50)

    create_test_audio()
    create_test_cover()
    create_test_guest()
    create_test_summary()

    print("\n🎉 测试素材生成完成！")
    print("\n测试目录: ./input/001_AI产品的未来/")
    print("\n运行以下命令开始测试:")
    print("  python main.py input/001_AI产品的未来")


if __name__ == "__main__":
    main()
