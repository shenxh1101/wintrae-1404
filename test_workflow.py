
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.processor import EpisodeProcessor
from src.release_manager import ReleaseManager


def test_full_workflow():
    print("=" * 60)
    print("  🎙️ 播客素材整理工具 - 完整工作流测试")
    print("=" * 60)

    config = Config()
    processor = EpisodeProcessor(config)

    test_dir = Path(__file__).parent / "input" / "001_AI产品的未来"

    if not test_dir.exists():
        print(f"\n❌ 测试目录不存在: {test_dir}")
        return False

    print(f"\n📂 测试目录: {test_dir}")

    print("\n🔍 步骤1: 素材校验...")
    result = processor.process_episode(str(test_dir))

    print(f"\n   期号: {result.episode_number}")
    print(f"   校验状态: {'✅ 通过' if result.validation.is_valid else '❌ 有问题'}")

    if result.validation.missing_files:
        print(f"   缺失文件: {result.validation.missing_files}")

    if result.validation.naming_issues:
        print(f"   命名问题: {len(result.validation.naming_issues)} 项")

    if result.validation.sensitive_words_found:
        print(f"   敏感词: {len(result.validation.sensitive_words_found)} 处")

    print("\n🎵 步骤2: 音频分析...")
    if result.audio_info:
        print(f"   文件: {result.audio_info.filename}")
        print(f"   时长: {result.audio_info.duration_formatted}")
        print(f"   状态: {'✅ 通过' if result.audio_info.is_valid else '⚠️  有问题'}")
        if result.audio_info.issues:
            for issue in result.audio_info.issues:
                print(f"     - {issue}")
    else:
        print("   ⚠️  未找到音频文件")

    print("\n🖼️  步骤3: 封面检查...")
    if result.cover_info:
        print(f"   文件: {result.cover_info.filename}")
        print(f"   尺寸: {result.cover_info.width}x{result.cover_info.height}")
        print(f"   比例: {result.cover_info.aspect_ratio:.3f}")
        print(f"   状态: {'✅ 通过' if result.cover_info.is_valid else '❌ 不通过'}")
    else:
        print("   ⚠️  未找到封面文件")

    print("\n📝 步骤4: 内容生成...")
    if result.generated_content:
        print(f"   标题候选: {len(result.generated_content.title_candidates)} 个")
        for i, title in enumerate(result.generated_content.title_candidates[:3], 1):
            print(f"     {i}. {title}")

        print(f"   时间轴: {len(result.generated_content.timeline)} 个节点")
        print(f"   社媒平台: {len(result.generated_content.social_media)} 个")
        print(f"   待办事项: {len(result.generated_content.todo_list)} 项")
    else:
        print("   ⚠️  内容生成失败")

    print("\n📦 步骤5: 生成发布包和重命名...")
    if result.release_package:
        print(f"   输出目录: {result.release_package.output_dir}")
        print(f"   重命名计划: {len(result.release_package.rename_plans)} 个文件")

        print("\n   执行重命名...")
        processor.confirm_and_release(result)

        print(f"\n   生成的文件:")
        for f in result.release_package.generated_files:
            exists = "✅" if os.path.exists(f) else "❌"
            print(f"     {exists} {os.path.basename(f)}")

        print(f"\n   检查清单状态:")
        passed = sum(1 for _, checked in result.release_package.checklist if checked)
        total = len(result.release_package.checklist)
        print(f"     通过: {passed}/{total}")

    print("\n" + "=" * 60)
    print("  ✅ 测试完成！")
    print("=" * 60)

    print(f"\n📂 输出目录: {result.release_package.output_dir if result.release_package else 'N/A'}")
    print("\n生成的文件列表:")
    if result.release_package:
        output_dir = result.release_package.output_dir
        if os.path.exists(output_dir):
            for f in sorted(os.listdir(output_dir)):
                fpath = os.path.join(output_dir, f)
                size = os.path.getsize(fpath)
                print(f"  - {f} ({size} bytes)")

    return True


if __name__ == "__main__":
    test_full_workflow()
