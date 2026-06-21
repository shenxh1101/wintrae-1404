
import os
import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.processor import EpisodeProcessor, EpisodeProcessResult
from src.folder_watcher import FolderWatcher
from src.utils import ensure_directory, format_duration


class PodcastToolCLI:
    def __init__(self):
        self.config = Config()
        self.processor = EpisodeProcessor(self.config)
        self.watcher = None
        self.current_result = None

    def print_header(self):
        print("\n" + "=" * 60)
        print("        🎙️ 播客素材整理工具 v1.0")
        print("=" * 60)

    def print_section(self, title: str):
        print(f"\n{'─' * 60}")
        print(f"  {title}")
        print(f"{'─' * 60}")

    def print_validation_result(self, result: EpisodeProcessResult):
        self.print_section("📋 素材校验结果")

        print(f"\n  期号: {result.episode_number or '未检测到'}")
        print(f"  目录: {result.directory}")

        if result.validation:
            if result.validation.is_valid:
                print("\n  ✅ 所有文件齐全，命名规范")
            else:
                print("\n  ❌ 存在问题：")

            if result.validation.missing_files:
                print(f"\n  缺失文件:")
                for f in result.validation.missing_files:
                    print(f"    - {f}")

            if result.validation.naming_issues:
                print(f"\n  命名问题:")
                for issue in result.validation.naming_issues:
                    print(f"    - {issue}")

            if result.validation.sensitive_words_found:
                print(f"\n  ⚠️  敏感词检测:")
                for filename, word, context in result.validation.sensitive_words_found:
                    print(f"    - [{filename}] 发现 '{word}': {context}")

            if result.validation.files:
                print(f"\n  已识别文件:")
                for file_type, filepath in result.validation.files.items():
                    print(f"    {file_type:8s}: {os.path.basename(filepath)}")

            if result.validation.warnings:
                print(f"\n  警告:")
                for w in result.validation.warnings:
                    print(f"    - {w}")

    def print_audio_info(self, result: EpisodeProcessResult):
        if not result.audio_info:
            return

        self.print_section("🎵 音频信息")

        info = result.audio_info
        if info.is_valid:
            print(f"\n  ✅ 音频校验通过")
        else:
            print(f"\n  ❌ 音频存在问题")

        print(f"\n  文件: {info.filename}")
        print(f"  时长: {info.duration_formatted} ({info.duration_seconds:.0f}秒)")
        print(f"  格式: {info.format}")
        if info.bitrate:
            print(f"  比特率: {info.bitrate // 1000} kbps")
        if info.sample_rate:
            print(f"  采样率: {info.sample_rate} Hz")
        if info.channels:
            print(f"  声道数: {info.channels}")
        if info.title:
            print(f"  标题: {info.title}")
        if info.artist:
            print(f"  艺术家: {info.artist}")

        if info.issues:
            print(f"\n  问题:")
            for issue in info.issues:
                print(f"    - {issue}")

        if info.warnings:
            print(f"\n  警告:")
            for w in info.warnings:
                print(f"    - {w}")

    def print_cover_info(self, result: EpisodeProcessResult):
        if not result.cover_info:
            return

        self.print_section("🖼️  封面检查")

        info = result.cover_info
        if info.is_valid:
            print(f"\n  ✅ 封面校验通过")
        else:
            print(f"\n  ❌ 封面存在问题")

        print(f"\n  文件: {info.filename}")
        print(f"  尺寸: {info.width} x {info.height} px")
        print(f"  比例: {info.aspect_ratio:.3f}")
        print(f"  大小: {info.file_size_mb:.2f} MB")
        print(f"  格式: {info.format}")
        if info.mode:
            print(f"  颜色模式: {info.mode}")

        if info.issues:
            print(f"\n  问题:")
            for issue in info.issues:
                print(f"    - {issue}")

        if info.warnings:
            print(f"\n  警告:")
            for w in info.warnings:
                print(f"    - {w}")

    def print_generated_content(self, result: EpisodeProcessResult):
        if not result.generated_content:
            return

        content = result.generated_content

        self.print_section("📝 生成内容")

        if content.title_candidates:
            print(f"\n  🏷️  标题候选:")
            for i, title in enumerate(content.title_candidates, 1):
                print(f"    {i}. {title}")

        if content.timeline:
            print(f"\n  ⏱️  时间轴草稿:")
            for item in content.timeline:
                print(f"    [{item['time']}] {item['topic']}")

        if content.guest_intro:
            print(f"\n  👤 嘉宾介绍:")
            print(f"    {content.guest_intro[:100]}..." if len(content.guest_intro) > 100 else f"    {content.guest_intro}")

        if content.social_media:
            print(f"\n  📱 社媒文案:")
            for platform, text in content.social_media.items():
                print(f"    - {platform}: {text[:50]}...")

        if content.todo_list:
            print(f"\n  ✅ 待办清单:")
            for item in content.todo_list[:3]:
                print(f"    - {item}")
            if len(content.todo_list) > 3:
                print(f"    ... 共 {len(content.todo_list)} 项")

        if content.warnings:
            print(f"\n  警告:")
            for w in content.warnings:
                print(f"    - {w}")

    def print_release_package(self, result: EpisodeProcessResult):
        if not result.release_package:
            return

        pkg = result.release_package

        self.print_section("📦 发布包")

        print(f"\n  期号: {pkg.episode_number}")
        print(f"  标题: {pkg.title}")
        print(f"  输出目录: {pkg.output_dir}")
        print(f"  状态: {'✅ 准备就绪' if pkg.is_ready else '⚠️  存在问题'}")

        if pkg.checklist:
            print(f"\n  检查清单:")
            for item, checked in pkg.checklist:
                status = "✅" if checked else "⬜"
                print(f"    {status} {item}")

        if pkg.rename_plans:
            print(f"\n  重命名计划:")
            for plan in pkg.rename_plans:
                status = "✅" if plan.success else "⏳"
                print(f"    {status} {plan.file_type}:")
                print(f"       原: {os.path.basename(plan.source)}")
                print(f"       新: {os.path.basename(plan.target)}")

    def process_directory(self, directory: str):
        print(f"\n🔍 正在处理目录: {directory}")

        result = self.processor.process_episode(directory)
        self.current_result = result

        self.print_validation_result(result)
        self.print_audio_info(result)
        self.print_cover_info(result)
        self.print_generated_content(result)
        self.print_release_package(result)

        return result

    def interactive_release(self, result: EpisodeProcessResult):
        if not result.release_package:
            print("❌ 没有可发布的内容")
            return

        print("\n" + "=" * 60)
        print("  确认发布")
        print("=" * 60)

        title = result.release_package.title
        print(f"\n  当前标题: {title}")

        choice = input("\n  是否修改标题？(y/N): ").strip().lower()
        if choice == "y":
            new_title = input("  请输入新标题: ").strip()
            if new_title:
                result.release_package.title = new_title

        print(f"\n  将生成以下文件到: {result.release_package.output_dir}")
        for plan in result.release_package.rename_plans:
            print(f"    - {os.path.basename(plan.target)}")

        choice = input("\n  确认执行重命名和生成发布文件？(y/N): ").strip().lower()
        if choice != "y":
            print("  已取消")
            return

        print("\n  🚀 正在生成发布包...")

        try:
            pkg = self.processor.confirm_and_release(
                result, title=result.release_package.title
            )

            print("\n  ✅ 发布包生成完成！")
            print(f"\n  输出目录: {pkg.output_dir}")
            print(f"\n  生成的文件:")
            for f in pkg.generated_files:
                print(f"    - {os.path.basename(f)}")

            choice = input("\n  是否归档本期素材？(y/N): ").strip().lower()
            if choice == "y":
                success = self.processor.archive_episode(result)
                if success:
                    print(f"  ✅ 已归档到: {pkg.archive_dir}")
                else:
                    print("  ❌ 归档失败")

        except Exception as e:
            print(f"❌ 发布失败: {e}")

    def start_watcher(self):
        self.print_section("👀 文件夹监听模式")

        print(f"\n  监听目录: {self.config.input_dir}")
        print("  放入音频、封面、嘉宾资料和摘要后将自动检测")
        print("  按 Ctrl+C 停止监听\n")

        def on_new_episode(directory):
            print(f"\n  🎉 检测到新期数素材: {directory}")
            result = self.process_directory(directory)

            if result.is_valid:
                print("\n  ✅ 所有校验通过！")
            else:
                print("\n  ⚠️  存在需要处理的问题")

        def on_file_change(filepath, event_type):
            filename = os.path.basename(filepath)
            print(f"  [文件{event_type}] {filename}")

        self.watcher = FolderWatcher(
            self.config,
            on_change=on_file_change,
            on_new_episode=on_new_episode,
        )

        self.watcher.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n  停止监听...")
            self.watcher.stop()
            print("  已停止")

    def show_menu(self):
        self.print_header()
        print("\n  请选择操作:")
        print()
        print("  1. 扫描输入目录")
        print("  2. 扫描指定目录")
        print("  3. 启动文件夹监听")
        print("  4. 查看当前结果")
        print("  5. 确认并生成发布包")
        print("  6. 显示配置信息")
        print("  0. 退出")
        print()

    def show_config(self):
        self.print_section("⚙️  配置信息")

        print(f"\n  输入目录: {self.config.input_dir}")
        print(f"  输出目录: {self.config.output_dir}")
        print(f"  归档目录: {self.config.archive_dir}")

        print(f"\n  音频扩展名: {', '.join(self.config.get('naming.audio_extensions', []))}")
        print(f"  封面扩展名: {', '.join(self.config.get('naming.cover_extensions', []))}")

        audio_cfg = self.config.get("audio", {})
        if audio_cfg:
            print(f"\n  音频最小时长: {format_duration(audio_cfg.get('min_duration_seconds', 60))}")
            print(f"  音频最大时长: {format_duration(audio_cfg.get('max_duration_seconds', 7200))}")
            print(f"  推荐格式: {audio_cfg.get('preferred_format', 'mp3')}")

        cover_cfg = self.config.get("cover", {})
        if cover_cfg:
            print(f"\n  封面最小尺寸: {cover_cfg.get('min_width', 1400)}x{cover_cfg.get('min_height', 1400)}")
            print(f"  目标比例: {cover_cfg.get('target_ratio', 1.0)}")
            print(f"  最大文件大小: {cover_cfg.get('max_file_size_mb', 5)} MB")

        sensitive_words = self.config.get("sensitive_words", [])
        if sensitive_words:
            print(f"\n  敏感词列表: {', '.join(sensitive_words)}")

    def run(self):
        ensure_directory(self.config.input_dir)
        ensure_directory(self.config.output_dir)
        ensure_directory(self.config.archive_dir)

        parser = argparse.ArgumentParser(description="播客素材整理工具")
        parser.add_argument("directory", nargs="?", help="要处理的目录路径")
        parser.add_argument("--watch", "-w", action="store_true", help="启动文件夹监听")
        parser.add_argument("--scan", "-s", action="store_true", help="扫描输入目录")
        parser.add_argument("--release", "-r", action="store_true", help="自动生成发布包")
        parser.add_argument("--config", "-c", help="配置文件路径")

        args = parser.parse_args()

        if args.config:
            self.config = Config(args.config)
            self.processor = EpisodeProcessor(self.config)

        if args.directory:
            result = self.process_directory(args.directory)
            if args.release and result.is_valid:
                self.interactive_release(result)
            return

        if args.watch:
            self.start_watcher()
            return

        if args.scan:
            self.scan_input_directory()
            return

        self._interactive_loop()

    def _interactive_loop(self):
        while True:
            self.show_menu()
            choice = input("  请输入选项 [0-6]: ").strip()

            if choice == "0":
                print("\n👋 再见！")
                break

            elif choice == "1":
                self.scan_input_directory()

            elif choice == "2":
                directory = input("\n  请输入目录路径: ").strip()
                if directory and os.path.exists(directory):
                    self.process_directory(directory)
                else:
                    print("  ❌ 目录不存在")

            elif choice == "3":
                self.start_watcher()

            elif choice == "4":
                if self.current_result:
                    self.print_validation_result(self.current_result)
                    self.print_audio_info(self.current_result)
                    self.print_cover_info(self.current_result)
                    self.print_generated_content(self.current_result)
                    self.print_release_package(self.current_result)
                else:
                    print("\n  暂无结果，请先扫描目录")

            elif choice == "5":
                if self.current_result:
                    self.interactive_release(self.current_result)
                else:
                    print("\n  暂无结果，请先扫描目录")

            elif choice == "6":
                self.show_config()

            else:
                print("\n  ❌ 无效选项")

            input("\n  按回车键继续...")

    def scan_input_directory(self):
        input_dir = self.config.input_dir
        ensure_directory(input_dir)

        subdirs = []
        for item in os.listdir(input_dir):
            item_path = os.path.join(input_dir, item)
            if os.path.isdir(item_path):
                subdirs.append(item_path)

        if not subdirs:
            print(f"\n📂 扫描根目录: {input_dir}")
            self.process_directory(input_dir)
        else:
            print(f"\n📂 发现 {len(subdirs)} 个子目录")
            for i, subdir in enumerate(subdirs, 1):
                print(f"\n  [{i}] {os.path.basename(subdir)}")
                self.process_directory(subdir)


def main():
    cli = PodcastToolCLI()
    cli.run()


if __name__ == "__main__":
    main()
