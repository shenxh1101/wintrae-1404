
import os
import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.processor import EpisodeProcessor, EpisodeProcessResult
from src.folder_watcher import FolderWatcher
from src.state_manager import StateManager
from src.dashboard import (
    EpisodeDashboard,
    FILTER_ALL,
    FILTER_READY,
    FILTER_PENDING,
    FILTER_HAS_ISSUES,
    FILTER_RELEASED,
    FILTER_NOT_RELEASED,
    VALID_FILTERS,
)
from src.utils import ensure_directory, format_duration


def safe_input(prompt: str = "") -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


class PodcastToolCLI:
    def __init__(self):
        try:
            self.config = Config()
        except Exception:
            from src.config import Config
            self.config = Config()
        try:
            self.state_manager = StateManager(self.config)
        except Exception:
            self.state_manager = StateManager()
        try:
            self.processor = EpisodeProcessor(self.config, self.state_manager)
        except Exception:
            self.processor = None
        try:
            self.dashboard = EpisodeDashboard(self.config, self.state_manager)
        except Exception:
            self.dashboard = None
        self.watcher = None
        self.current_result = None

    def print_header(self):
        try:
            print("\n" + "=" * 60)
            print("         播客素材整理工具 v1.0")
            print("=" * 60)
        except Exception:
            pass

    def print_section(self, title: str):
        try:
            print(f"\n{'─' * 60}")
            print(f"  {str(title) if title else ''}")
            print(f"{'─' * 60}")
        except Exception:
            pass

    def print_validation_result(self, result: EpisodeProcessResult):
        try:
            self.print_section(" 素材校验结果")
        except Exception:
            pass

        try:
            ep = str(result.episode_number) if getattr(result, "episode_number", None) else "未检测到"
            print(f"\n  期号: {ep}")
        except Exception:
            pass

        try:
            directory = getattr(result, "directory", "")
            print(f"  目录: {str(directory) if directory else ''}")
        except Exception:
            pass

        try:
            if result.validation is None:
                return
        except Exception:
            return

        try:
            is_valid = bool(getattr(result.validation, "is_valid", False))
            if is_valid:
                print("\n   所有文件齐全，命名规范")
            else:
                print("\n   存在问题：")
        except Exception:
            pass

        try:
            missing_files = getattr(result.validation, "missing_files", [])
            if isinstance(missing_files, list) and missing_files:
                print(f"\n  缺失文件:")
                for f in missing_files:
                    try:
                        print(f"    - {str(f)}")
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            naming_issues = getattr(result.validation, "naming_issues", [])
            if isinstance(naming_issues, list) and naming_issues:
                print(f"\n  命名问题:")
                for issue in naming_issues:
                    try:
                        print(f"    - {str(issue)}")
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            swf = getattr(result.validation, "sensitive_words_found", [])
            if isinstance(swf, list) and swf:
                print(f"\n   敏感词检测:")
                for item in swf:
                    try:
                        if isinstance(item, (list, tuple)) and len(item) >= 3:
                            filename, word, context = item[0], item[1], item[2]
                            print(f"    - [{str(filename)}] 发现 '{str(word)}': {str(context)}")
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            files = getattr(result.validation, "files", {})
            if isinstance(files, dict) and files:
                print(f"\n  已识别文件:")
                for file_type, filepath in files.items():
                    try:
                        if isinstance(filepath, str):
                            basename = os.path.basename(filepath)
                            print(f"    {str(file_type):8s}: {basename}")
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            warnings = getattr(result.validation, "warnings", [])
            if isinstance(warnings, list) and warnings:
                print(f"\n  警告:")
                for w in warnings:
                    try:
                        print(f"    - {str(w)}")
                    except Exception:
                        continue
        except Exception:
            pass

    def print_audio_info(self, result: EpisodeProcessResult):
        try:
            if result.audio_info is None:
                return
        except Exception:
            return

        try:
            self.print_section(" 音频信息")
        except Exception:
            pass

        info = result.audio_info

        try:
            is_valid = bool(getattr(info, "is_valid", False))
            if is_valid:
                print(f"\n   音频校验通过")
            else:
                print(f"\n   音频存在问题")
        except Exception:
            pass

        try:
            filename = getattr(info, "filename", "")
            print(f"\n  文件: {str(filename) if filename else ''}")
        except Exception:
            pass

        try:
            dur_fmt = getattr(info, "duration_formatted", "")
            dur_sec = getattr(info, "duration_seconds", None)
            if dur_sec is not None and isinstance(dur_sec, (int, float)) and dur_sec >= 0:
                print(f"  时长: {str(dur_fmt) if dur_fmt else ''} ({dur_sec:.0f}秒)")
            elif dur_fmt:
                print(f"  时长: {str(dur_fmt)}")
            else:
                print(f"  时长: 未知")
        except Exception:
            try:
                print(f"  时长: 未知")
            except Exception:
                pass

        try:
            fmt = getattr(info, "format", "")
            print(f"  格式: {str(fmt) if fmt else ''}")
        except Exception:
            pass

        try:
            bitrate = getattr(info, "bitrate", None)
            if bitrate is not None and isinstance(bitrate, (int, float)) and bitrate > 0:
                print(f"  比特率: {int(bitrate) // 1000} kbps")
        except Exception:
            pass

        try:
            sr = getattr(info, "sample_rate", None)
            if sr is not None and isinstance(sr, (int, float)) and sr > 0:
                print(f"  采样率: {sr} Hz")
        except Exception:
            pass

        try:
            ch = getattr(info, "channels", None)
            if ch is not None and isinstance(ch, (int, float)) and ch > 0:
                print(f"  声道数: {int(ch)}")
        except Exception:
            pass

        try:
            title = getattr(info, "title", "")
            if title and isinstance(title, str) and title.strip():
                print(f"  标题: {title}")
        except Exception:
            pass

        try:
            artist = getattr(info, "artist", "")
            if artist and isinstance(artist, str) and artist.strip():
                print(f"  艺术家: {artist}")
        except Exception:
            pass

        try:
            issues = getattr(info, "issues", [])
            if isinstance(issues, list) and issues:
                print(f"\n  问题:")
                for issue in issues:
                    try:
                        print(f"    - {str(issue)}")
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            warnings = getattr(info, "warnings", [])
            if isinstance(warnings, list) and warnings:
                print(f"\n  警告:")
                for w in warnings:
                    try:
                        print(f"    - {str(w)}")
                    except Exception:
                        continue
        except Exception:
            pass

    def print_cover_info(self, result: EpisodeProcessResult):
        try:
            if result.cover_info is None:
                return
        except Exception:
            return

        try:
            self.print_section(" 封面检查")
        except Exception:
            pass

        info = result.cover_info

        try:
            is_valid = bool(getattr(info, "is_valid", False))
            if is_valid:
                print(f"\n   封面校验通过")
            else:
                print(f"\n   封面存在问题")
        except Exception:
            pass

        try:
            filename = getattr(info, "filename", "")
            print(f"\n  文件: {str(filename) if filename else ''}")
        except Exception:
            pass

        try:
            width = getattr(info, "width", None)
            height = getattr(info, "height", None)
            if (width is not None and isinstance(width, (int, float)) and width >= 0
                    and height is not None and isinstance(height, (int, float)) and height >= 0):
                print(f"  尺寸: {int(width)} x {int(height)} px")
            else:
                print(f"  尺寸: 未知")
        except Exception:
            try:
                print(f"  尺寸: 未知")
            except Exception:
                pass

        try:
            ar = getattr(info, "aspect_ratio", None)
            if ar is not None and isinstance(ar, (int, float)) and ar >= 0:
                print(f"  比例: {float(ar):.3f}")
            else:
                print(f"  比例: 未知")
        except Exception:
            try:
                print(f"  比例: 未知")
            except Exception:
                pass

        try:
            fsm = getattr(info, "file_size_mb", None)
            if fsm is not None and isinstance(fsm, (int, float)) and fsm >= 0:
                print(f"  大小: {float(fsm):.2f} MB")
            else:
                print(f"  大小: 未知")
        except Exception:
            try:
                print(f"  大小: 未知")
            except Exception:
                pass

        try:
            fmt = getattr(info, "format", "")
            print(f"  格式: {str(fmt) if fmt else ''}")
        except Exception:
            pass

        try:
            mode = getattr(info, "mode", "")
            if mode and isinstance(mode, str) and mode.strip():
                print(f"  颜色模式: {mode}")
        except Exception:
            pass

        try:
            issues = getattr(info, "issues", [])
            if isinstance(issues, list) and issues:
                print(f"\n  问题:")
                for issue in issues:
                    try:
                        print(f"    - {str(issue)}")
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            warnings = getattr(info, "warnings", [])
            if isinstance(warnings, list) and warnings:
                print(f"\n  警告:")
                for w in warnings:
                    try:
                        print(f"    - {str(w)}")
                    except Exception:
                        continue
        except Exception:
            pass

    def print_generated_content(self, result: EpisodeProcessResult):
        try:
            if result.generated_content is None:
                return
        except Exception:
            return

        content = result.generated_content

        try:
            self.print_section(" 生成内容")
        except Exception:
            pass

        try:
            tcs = getattr(content, "title_candidates", None)
            if isinstance(tcs, list) and tcs:
                print(f"\n   标题候选:")
                for i, title in enumerate(tcs, 1):
                    try:
                        if isinstance(title, str):
                            print(f"    {i}. {title}")
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            tl = getattr(content, "timeline", None)
            if isinstance(tl, list) and tl:
                print(f"\n   时间轴草稿:")
                for item in tl:
                    try:
                        if isinstance(item, dict):
                            t = item.get("time", "")
                            tp = item.get("topic", "")
                            print(f"    [{str(t)}] {str(tp)}")
                        elif isinstance(item, (list, tuple)) and len(item) >= 2:
                            print(f"    [{str(item[0])}] {str(item[1])}")
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            gi = getattr(content, "guest_intro", "")
            if gi and isinstance(gi, str) and gi.strip():
                print(f"\n   嘉宾介绍:")
                if len(gi) > 100:
                    print(f"    {gi[:100]}...")
                else:
                    print(f"    {gi}")
        except Exception:
            pass

        try:
            sm = getattr(content, "social_media", None)
            if isinstance(sm, dict) and sm:
                print(f"\n   社媒文案:")
                for platform, text in sm.items():
                    try:
                        safe_text = str(text) if isinstance(text, str) else ""
                        if len(safe_text) > 50:
                            print(f"    - {str(platform)}: {safe_text[:50]}...")
                        else:
                            print(f"    - {str(platform)}: {safe_text}")
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            tdl = getattr(content, "todo_list", None)
            if isinstance(tdl, list) and tdl:
                print(f"\n   待办清单:")
                shown = 0
                for item in tdl:
                    try:
                        if isinstance(item, str):
                            print(f"    - {item}")
                            shown += 1
                            if shown >= 3:
                                break
                    except Exception:
                        continue
                if len(tdl) > 3:
                    print(f"    ... 共 {len(tdl)} 项")
        except Exception:
            pass

        try:
            warnings = getattr(content, "warnings", [])
            if isinstance(warnings, list) and warnings:
                print(f"\n  警告:")
                for w in warnings:
                    try:
                        print(f"    - {str(w)}")
                    except Exception:
                        continue
        except Exception:
            pass

    def print_release_package(self, result: EpisodeProcessResult):
        try:
            if result.release_package is None:
                return
        except Exception:
            return

        pkg = result.release_package

        try:
            self.print_section(" 发布包")
        except Exception:
            pass

        try:
            ep = getattr(pkg, "episode_number", "")
            print(f"\n  期号: {str(ep) if ep else ''}")
        except Exception:
            pass

        try:
            title = getattr(pkg, "title", "")
            print(f"  标题: {str(title) if title else ''}")
        except Exception:
            pass

        try:
            od = getattr(pkg, "output_dir", "")
            print(f"  输出目录: {str(od) if od else ''}")
        except Exception:
            pass

        try:
            is_ready = bool(getattr(pkg, "is_ready", False))
            print(f"  状态: {' 准备就绪' if is_ready else '  存在问题'}")
        except Exception:
            pass

        try:
            checklist = getattr(pkg, "checklist", [])
            if isinstance(checklist, list) and checklist:
                print(f"\n  检查清单:")
                for item in checklist:
                    try:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            name, checked = item[0], bool(item[1])
                            status = "" if checked else ""
                            print(f"    {status} {str(name)}")
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            plans = getattr(pkg, "rename_plans", [])
            if isinstance(plans, list) and plans:
                print(f"\n  重命名计划:")
                for plan in plans:
                    try:
                        success = bool(getattr(plan, "success", False))
                        ft = getattr(plan, "file_type", "")
                        src = getattr(plan, "source", "")
                        tgt = getattr(plan, "target", "")
                        status = "" if success else ""
                        print(f"    {status} {str(ft)}:")
                        if src and isinstance(src, str):
                            print(f"       原: {os.path.basename(src)}")
                        if tgt and isinstance(tgt, str):
                            print(f"       新: {os.path.basename(tgt)}")
                    except Exception:
                        continue
        except Exception:
            pass

    def process_directory(self, directory: str):
        try:
            print(f"\n 正在处理目录: {str(directory) if directory else ''}")
        except Exception:
            pass

        result = None
        try:
            if self.processor is None:
                try:
                    print("   处理器未初始化")
                except Exception:
                    pass
                from src.processor import EpisodeProcessResult
                result = EpisodeProcessResult(episode_number="未知", directory=str(directory) if directory else "")
                result.errors.append("处理器未初始化")
                self.current_result = result
                return result
            result = self.processor.process_episode(directory)
        except Exception as e:
            try:
                from src.processor import EpisodeProcessResult
                result = EpisodeProcessResult(episode_number="未知", directory=str(directory) if directory else "")
                result.errors.append(f"处理异常: {e}")
            except Exception:
                pass

        self.current_result = result

        try:
            self.print_validation_result(result)
        except Exception:
            pass
        try:
            self.print_audio_info(result)
        except Exception:
            pass
        try:
            self.print_cover_info(result)
        except Exception:
            pass
        try:
            self.print_generated_content(result)
        except Exception:
            pass
        try:
            self.print_release_package(result)
        except Exception:
            pass

        try:
            if result is not None and getattr(result, "errors", None):
                print(f"\n 处理过程中的错误:")
                for err in result.errors:
                    try:
                        print(f"    ! {str(err)}")
                    except Exception:
                        continue
        except Exception:
            pass

        return result

    def interactive_release(self, result: EpisodeProcessResult):
        try:
            if result is None or result.release_package is None:
                print(" 没有可发布的内容")
                return
        except Exception:
            try:
                print(" 没有可发布的内容")
            except Exception:
                pass
            return

        try:
            print("\n" + "=" * 60)
            print("  确认发布")
            print("=" * 60)
        except Exception:
            pass

        try:
            title = getattr(result.release_package, "title", "")
            print(f"\n  当前标题: {str(title) if title else ''}")
        except Exception:
            pass

        choice = safe_input("\n  是否修改标题？(y/N): ").strip().lower()
        if choice == "y":
            new_title = safe_input("  请输入新标题: ").strip()
            if new_title:
                try:
                    result.release_package.title = new_title
                except Exception:
                    pass

        try:
            od = getattr(result.release_package, "output_dir", "")
            print(f"\n  将生成以下文件到: {str(od) if od else ''}")
        except Exception:
            pass

        try:
            plans = getattr(result.release_package, "rename_plans", [])
            if isinstance(plans, list):
                for plan in plans:
                    try:
                        tgt = getattr(plan, "target", "")
                        if tgt and isinstance(tgt, str):
                            print(f"    - {os.path.basename(tgt)}")
                    except Exception:
                        continue
        except Exception:
            pass

        choice = safe_input("\n  确认执行重命名和生成发布文件？(y/N): ").strip().lower()
        if choice != "y":
            print("  已取消")
            return

        try:
            print("\n   正在生成发布包...")
        except Exception:
            pass

        try:
            if self.processor is None:
                try:
                    print("  处理器未初始化")
                except Exception:
                    pass
                return

            use_title = None
            try:
                if result.release_package is not None:
                    t = getattr(result.release_package, "title", None)
                    if t and isinstance(t, str) and t.strip():
                        use_title = t
            except Exception:
                use_title = None

            pkg, errors = self.processor.confirm_and_release(result, title=use_title)

            if isinstance(errors, list) and errors:
                try:
                    print(f"\n  发布过程中出现问题:")
                    for e in errors:
                        print(f"    ! {str(e)}")
                except Exception:
                    pass

            if pkg is None:
                try:
                    print("   发布失败")
                except Exception:
                    pass
                return

            try:
                print("\n   发布包生成完成！")
            except Exception:
                pass

            try:
                od = getattr(pkg, "output_dir", "")
                print(f"\n  输出目录: {str(od) if od else ''}")
            except Exception:
                pass

            try:
                gf = getattr(pkg, "generated_files", [])
                if isinstance(gf, list) and gf:
                    print(f"\n  生成的文件:")
                    for f in gf:
                        try:
                            if isinstance(f, str):
                                print(f"    - {os.path.basename(f)}")
                        except Exception:
                            continue
            except Exception:
                pass

            choice = safe_input("\n  是否归档本期素材？(y/N): ").strip().lower()
            if choice == "y":
                try:
                    success = self.processor.archive_episode(result)
                    if success:
                        try:
                            ad = getattr(pkg, "archive_dir", "")
                            print(f"   已归档到: {str(ad) if ad else ''}")
                        except Exception:
                            print("   已归档")
                    else:
                        print("   归档失败")
                except Exception:
                    try:
                        print("   归档失败")
                    except Exception:
                        pass

        except Exception as e:
            try:
                print(f" 发布失败: {e}")
            except Exception:
                pass

    def start_watcher(self):
        try:
            self.print_section(" 文件夹监听模式")
        except Exception:
            pass

        try:
            in_dir = getattr(self.config, "input_dir", "")
            print(f"\n  监听目录: {str(in_dir) if in_dir else ''}")
        except Exception:
            pass

        try:
            print("  放入音频、封面、嘉宾资料和摘要后将自动检测")
            print("  按 Ctrl+C 停止监听\n")
        except Exception:
            pass

        def on_new_episode(directory):
            try:
                d = str(directory) if directory else ""
                print(f"\n   检测到新期数素材: {d}")
                result = self.process_directory(directory)

                try:
                    is_valid = bool(getattr(result, "is_valid", False))
                    if is_valid:
                        print("\n   所有校验通过！")
                    else:
                        print("\n    存在需要处理的问题")
                except Exception:
                    pass
            except Exception:
                pass

        def on_file_change(filepath, event_type):
            try:
                if isinstance(filepath, str):
                    filename = os.path.basename(filepath)
                    et = str(event_type) if event_type else ""
                    print(f"  [文件{et}] {filename}")
            except Exception:
                pass

        try:
            self.watcher = FolderWatcher(
                self.config,
                on_change=on_file_change,
                on_new_episode=on_new_episode,
            )
        except Exception as e:
            try:
                print(f"   监听器初始化失败: {e}")
            except Exception:
                pass
            return

        try:
            self.watcher.start()
        except Exception as e:
            try:
                print(f"   监听启动失败: {e}")
            except Exception:
                pass
            return

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            try:
                print("\n\n  停止监听...")
            except Exception:
                pass
            try:
                if self.watcher is not None:
                    self.watcher.stop()
            except Exception:
                pass
            try:
                print("  已停止")
            except Exception:
                pass

    def show_menu(self):
        self.print_header()
        try:
            print("\n  请选择操作:")
            print()
            print("  1. 扫描输入目录")
            print("  2. 扫描指定目录")
            print("  3. 启动文件夹监听")
            print("  4. 查看当前结果")
            print("  5. 确认并生成发布包")
            print("  6. 显示配置信息")
            print("  7. 期数看板（全部）")
            print("  8. 期数看板（仅就绪）")
            print("  9. 期数看板（仅待处理/有问题）")
            print("  0. 退出")
            print()
        except Exception:
            pass

    def show_dashboard(self, filter_name: str = FILTER_ALL):
        try:
            if self.dashboard is None:
                try:
                    self.dashboard = EpisodeDashboard(self.config, self.state_manager)
                except Exception:
                    try:
                        print("   看板未初始化")
                    except Exception:
                        pass
                    return
            try:
                rows = self.dashboard.scan(filter_name=filter_name, save_state=True)
                print(self.dashboard.render_table(rows))
            except Exception as e:
                try:
                    print(f"   看板扫描失败: {e}")
                except Exception:
                    pass
        except Exception:
            try:
                print("   看板渲染失败")
            except Exception:
                pass

    def show_config(self):
        try:
            self.print_section(" 配置信息")
        except Exception:
            pass

        try:
            in_dir = getattr(self.config, "input_dir", "")
            print(f"\n  输入目录: {str(in_dir) if in_dir else ''}")
        except Exception:
            pass

        try:
            out_dir = getattr(self.config, "output_dir", "")
            print(f"  输出目录: {str(out_dir) if out_dir else ''}")
        except Exception:
            pass

        try:
            arc_dir = getattr(self.config, "archive_dir", "")
            print(f"  归档目录: {str(arc_dir) if arc_dir else ''}")
        except Exception:
            pass

        try:
            audio_exts = self.config.get("naming.audio_extensions", [])
            if isinstance(audio_exts, list):
                str_exts = [str(e) for e in audio_exts if isinstance(e, str)]
                print(f"\n  音频扩展名: {', '.join(str_exts)}")
        except Exception:
            pass

        try:
            cover_exts = self.config.get("naming.cover_extensions", [])
            if isinstance(cover_exts, list):
                str_exts = [str(e) for e in cover_exts if isinstance(e, str)]
                print(f"  封面扩展名: {', '.join(str_exts)}")
        except Exception:
            pass

        try:
            audio_cfg = self.config.get("audio", {})
            if isinstance(audio_cfg, dict) and audio_cfg:
                min_dur = audio_cfg.get("min_duration_seconds", 60)
                max_dur = audio_cfg.get("max_duration_seconds", 7200)
                pref_fmt = audio_cfg.get("preferred_format", "mp3")
                print(f"\n  音频最小时长: {format_duration(min_dur)}")
                print(f"  音频最大时长: {format_duration(max_dur)}")
                print(f"  推荐格式: {str(pref_fmt)}")
        except Exception:
            pass

        try:
            cover_cfg = self.config.get("cover", {})
            if isinstance(cover_cfg, dict) and cover_cfg:
                mw = cover_cfg.get("min_width", 1400)
                mh = cover_cfg.get("min_height", 1400)
                tr = cover_cfg.get("target_ratio", 1.0)
                mfsm = cover_cfg.get("max_file_size_mb", 5)
                print(f"\n  封面最小尺寸: {mw}x{mh}")
                print(f"  目标比例: {tr}")
                print(f"  最大文件大小: {mfsm} MB")
        except Exception:
            pass

        try:
            sensitive_words = self.config.get("sensitive_words", [])
            if isinstance(sensitive_words, list) and sensitive_words:
                safe_words = [str(w) for w in sensitive_words if isinstance(w, str)]
                print(f"\n  敏感词列表: {', '.join(safe_words)}")
        except Exception:
            pass

    def run(self):
        try:
            in_dir = getattr(self.config, "input_dir", None)
            if in_dir:
                ensure_directory(str(in_dir))
        except Exception:
            pass
        try:
            out_dir = getattr(self.config, "output_dir", None)
            if out_dir:
                ensure_directory(str(out_dir))
        except Exception:
            pass
        try:
            arc_dir = getattr(self.config, "archive_dir", None)
            if arc_dir:
                ensure_directory(str(arc_dir))
        except Exception:
            pass

        parser = argparse.ArgumentParser(description="播客素材整理工具")
        parser.add_argument("directory", nargs="?", help="要处理的目录路径")
        parser.add_argument("--watch", "-w", action="store_true", help="启动文件夹监听")
        parser.add_argument("--scan", "-s", action="store_true", help="扫描输入目录")
        parser.add_argument("--release", "-r", action="store_true", help="自动生成发布包")
        parser.add_argument("--dashboard", "-d", action="store_true", help="显示期数看板")
        parser.add_argument(
            "--filter",
            "-f",
            default=FILTER_ALL,
            choices=sorted(VALID_FILTERS),
            help=f"看板筛选条件 (默认: {FILTER_ALL})",
        )
        parser.add_argument("--config", "-c", help="配置文件路径")

        try:
            args = parser.parse_args()
        except SystemExit:
            return
        except Exception:
            return

        try:
            if args.config:
                self.config = Config(args.config)
                try:
                    self.state_manager = StateManager(self.config)
                except Exception:
                    self.state_manager = StateManager()
                try:
                    self.processor = EpisodeProcessor(self.config, self.state_manager)
                except Exception:
                    pass
                try:
                    self.dashboard = EpisodeDashboard(self.config, self.state_manager)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            if args.dashboard:
                flt = FILTER_ALL
                try:
                    if args.filter and isinstance(args.filter, str) and args.filter in VALID_FILTERS:
                        flt = args.filter
                except Exception:
                    flt = FILTER_ALL
                self.show_dashboard(flt)
                return
        except Exception:
            pass

        try:
            if args.directory:
                result = self.process_directory(args.directory)
                try:
                    if args.release and result is not None and getattr(result, "is_valid", False):
                        self.interactive_release(result)
                except Exception:
                    pass
                return
        except Exception:
            pass

        try:
            if args.watch:
                self.start_watcher()
                return
        except Exception:
            pass

        try:
            if args.scan:
                self.scan_input_directory()
                return
        except Exception:
            pass

        try:
            self._interactive_loop()
        except Exception:
            pass

    def _interactive_loop(self):
        while True:
            try:
                self.show_menu()
                choice = safe_input("  请输入选项 [0-9]: ").strip()

                if choice == "0":
                    try:
                        print("\n 再见！")
                    except Exception:
                        pass
                    break

                elif choice == "1":
                    self.scan_input_directory()

                elif choice == "2":
                    directory = safe_input("\n  请输入目录路径: ").strip()
                    try:
                        if directory and isinstance(directory, str) and os.path.exists(directory):
                            self.process_directory(directory)
                        else:
                            print("   目录不存在")
                    except Exception:
                        try:
                            print("   目录检查失败")
                        except Exception:
                            pass

                elif choice == "3":
                    self.start_watcher()

                elif choice == "4":
                    if self.current_result is not None:
                        try:
                            self.print_validation_result(self.current_result)
                        except Exception:
                            pass
                        try:
                            self.print_audio_info(self.current_result)
                        except Exception:
                            pass
                        try:
                            self.print_cover_info(self.current_result)
                        except Exception:
                            pass
                        try:
                            self.print_generated_content(self.current_result)
                        except Exception:
                            pass
                        try:
                            self.print_release_package(self.current_result)
                        except Exception:
                            pass
                    else:
                        try:
                            print("\n  暂无结果，请先扫描目录")
                        except Exception:
                            pass

                elif choice == "5":
                    if self.current_result is not None:
                        self.interactive_release(self.current_result)
                    else:
                        try:
                            print("\n  暂无结果，请先扫描目录")
                        except Exception:
                            pass

                elif choice == "6":
                    self.show_config()

                elif choice == "7":
                    self.show_dashboard(FILTER_ALL)

                elif choice == "8":
                    self.show_dashboard(FILTER_READY)

                elif choice == "9":
                    self.show_dashboard(FILTER_HAS_ISSUES)

                else:
                    try:
                        print("\n   无效选项")
                    except Exception:
                        pass

                safe_input("\n  按回车键继续...")

            except KeyboardInterrupt:
                try:
                    print("\n\n 再见！")
                except Exception:
                    pass
                break
            except Exception:
                try:
                    safe_input("\n  按回车键继续...")
                except Exception:
                    pass

    def scan_input_directory(self):
        try:
            input_dir = getattr(self.config, "input_dir", None)
            if not input_dir:
                try:
                    print("   输入目录未配置")
                except Exception:
                    pass
                return
            input_dir = str(input_dir)
        except Exception:
            try:
                print("   输入目录获取失败")
            except Exception:
                pass
            return

        try:
            ensure_directory(input_dir)
        except Exception:
            pass

        subdirs = []
        try:
            if not os.path.exists(input_dir):
                try:
                    print(f"   输入目录不存在: {input_dir}")
                except Exception:
                    pass
                return
            for item in os.listdir(input_dir):
                try:
                    item_path = os.path.join(input_dir, item)
                    if os.path.isdir(item_path):
                        subdirs.append(item_path)
                except Exception:
                    continue
        except (OSError, PermissionError) as e:
            try:
                print(f"   扫描输入目录失败: {e}")
            except Exception:
                pass
            return
        except Exception:
            try:
                print("   扫描输入目录异常")
            except Exception:
                pass
            return

        if not subdirs:
            try:
                print(f"\n 扫描根目录: {input_dir}")
            except Exception:
                pass
            self.process_directory(input_dir)
        else:
            try:
                print(f"\n 发现 {len(subdirs)} 个子目录")
            except Exception:
                pass
            for i, subdir in enumerate(subdirs, 1):
                try:
                    print(f"\n  [{i}] {os.path.basename(subdir)}")
                except Exception:
                    pass
                self.process_directory(subdir)


def main():
    try:
        cli = PodcastToolCLI()
        cli.run()
    except KeyboardInterrupt:
        try:
            print("\n 已退出")
        except Exception:
            pass
    except Exception:
        pass


if __name__ == "__main__":
    main()
