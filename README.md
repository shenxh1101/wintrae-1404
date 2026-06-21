
# 🎙️ 播客素材整理工具

自动化工具，为播客团队整理每期节目发布素材。提供文件夹监听、素材校验、音频信息读取、文案模板填充、封面尺寸检查和发布清单生成等功能。

## ✨ 功能特性

### 📁 文件夹监听
- 实时监控指定目录的文件变化
- 自动检测新放入的素材文件
- 支持 watchdog 库监听和轮询两种模式
- 文件写入稳定后才触发处理（防抖机制）

### ✅ 素材校验
- 自动识别期号（支持三位数字编号，如 `001`、`023`）
- 检查必需文件是否齐全（音频、封面、嘉宾资料、摘要）
- 验证文件命名规范
- 检测敏感占位词（如 TODO、待补充、placeholder 等）

### 🎵 音频信息读取
- 支持 MP3、WAV、M4A、FLAC、AAC 等格式
- 读取音频时长、比特率、采样率、声道数
- 提取元数据（标题、艺术家、专辑）
- 校验时长范围、推荐格式、比特率

### 🖼️ 封面尺寸检查
- 支持 JPG、PNG、WEBP 等格式
- 检查尺寸、比例、文件大小
- 验证颜色模式
- 自定义最小尺寸、目标比例、容差

### 📝 文案模板填充
- 生成多个标题候选
- 自动生成时间轴草稿
- 提取嘉宾介绍
- 生成多平台社媒文案（微博、小红书、微信公众号、Twitter）
- 生成待办清单
- 支持 Jinja2 自定义模板

### 📦 发布清单与重命名
- 生成发布检查清单
- 预览重命名计划
- 手动确认后批量重命名
- 生成 shownotes、嘉宾介绍、社媒文案等文件
- 支持归档功能

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 生成测试素材

```bash
python create_test_data.py
```

### 运行程序

#### 交互式模式

```bash
python main.py
```

#### 扫描指定目录

```bash
python main.py input/001_AI产品的未来
```

#### 扫描输入目录

```bash
python main.py --scan
```

#### 启动文件夹监听

```bash
python main.py --watch
```

## 📂 目录结构

```
.
├── main.py                 # 主程序入口
├── config.yaml             # 配置文件
├── requirements.txt        # 依赖清单
├── input/                  # 输入目录（监听目录）
│   └── 001_AI产品的未来/   # 某期节目素材
│       ├── 001_AI产品的未来.mp3   # 音频文件
│       ├── 001_cover.jpg         # 封面图
│       ├── 001_嘉宾资料.md       # 嘉宾资料
│       └── 001_节目摘要.md       # 节目摘要
├── output/                 # 输出目录（生成的发布素材）
│   └── 001/                # 某期节目输出
├── archive/                # 归档目录
├── templates/              # 文案模板
│   ├── shownotes.md
│   ├── weibo.txt
│   ├── xiaohongshu.txt
│   ├── wechat.txt
│   └── twitter.txt
└── src/                    # 源代码
    ├── config.py           # 配置管理
    ├── validator.py        # 素材校验
    ├── audio_analyzer.py   # 音频分析
    ├── cover_checker.py    # 封面检查
    ├── content_generator.py # 内容生成
    ├── folder_watcher.py   # 文件夹监听
    ├── release_manager.py  # 发布管理
    ├── processor.py        # 编排处理
    └── utils.py            # 工具函数
```

## ⚙️ 配置说明

编辑 `config.yaml` 自定义工具行为：

### 监听目录

```yaml
watch:
  input_dir: "./input"      # 输入/监听目录
  output_dir: "./output"    # 输出目录
  archive_dir: "./archive"  # 归档目录
```

### 文件命名规范

```yaml
naming:
  episode_pattern: "^(\\d{3})"  # 期号正则
  audio_extensions: [".mp3", ".wav", ".m4a", ".flac", ".aac"]
  cover_extensions: [".jpg", ".jpeg", ".png", ".webp"]
  required_files: ["audio", "cover", "guest", "summary"]
```

### 音频校验

```yaml
audio:
  min_duration_seconds: 60      # 最小时长（秒）
  max_duration_seconds: 7200    # 最大时长（秒）
  preferred_format: "mp3"       # 推荐格式
  preferred_bitrate: 192000     # 推荐比特率
```

### 封面校验

```yaml
cover:
  min_width: 1400           # 最小宽度
  min_height: 1400          # 最小高度
  target_ratio: 1.0         # 目标比例
  ratio_tolerance: 0.01     # 比例容差
  max_file_size_mb: 5       # 最大文件大小
```

### 敏感词

```yaml
sensitive_words:
  - "TODO"
  - "待补充"
  - "placeholder"
  - "xxx"
```

## 📝 模板说明

所有文案模板位于 `templates/` 目录，使用 Jinja2 语法。

### 可用变量

| 变量名 | 说明 |
|--------|------|
| `episode_number` | 期号，如 `001` |
| `title` | 完整标题 |
| `short_title` | 短标题（30字内） |
| `subtitle` | 副标题 |
| `summary_short` | 短摘要（100字内） |
| `guest_name` | 嘉宾姓名 |
| `guest_title` | 嘉宾职位 |
| `guest_bio` | 嘉宾简介 |
| `key_points` | 要点列表（带 `- ` 前缀） |
| `bullet_points` | 要点列表（带 `• ` 前缀） |
| `highlights` | 亮点列表 |
| `timeline` | 时间轴列表（含 time 和 topic） |
| `links` | 相关链接 |
| `tags` | 标签（空格分隔） |
| `publish_date` | 发布日期 |
| `listen_link` | 收听链接 |
| `podcast_name` | 播客名称 |

### 示例

```markdown
# 第{{ episode_number }}期：{{ title }}

嘉宾：{{ guest_name }}
{{ guest_title }}

{{ guest_bio }}
```

## 🎯 使用流程

### 标准工作流

1. **准备素材**：将音频、封面、嘉宾资料、节目摘要放入 `input/期号_标题/` 目录
2. **扫描校验**：运行 `python main.py --scan` 检查素材完整性
3. **查看结果**：检查校验结果、音频信息、封面信息、生成的文案
4. **确认发布**：确认标题后，执行批量重命名和文件生成
5. **归档**：（可选）将发布素材归档到 `archive/` 目录

### 监听模式

1. 运行 `python main.py --watch` 启动监听
2. 将素材文件放入 `input/` 目录
3. 工具自动检测并处理新素材
4. 处理完成后查看结果

## 🛠️ 命令行参数

```
python main.py [directory] [options]

位置参数:
  directory           要处理的目录路径

可选参数:
  --watch, -w         启动文件夹监听
  --scan, -s          扫描输入目录
  --release, -r       自动生成发布包（需配合 directory 参数）
  --config CONFIG, -c CONFIG
                      指定配置文件路径
  --help              显示帮助信息
```

## 📋 嘉宾资料格式

支持 Markdown 或纯文本格式，自动解析以下信息：

```markdown
# 嘉宾姓名

嘉宾职位

嘉宾简介...（支持多行）

## 联系方式

- 链接1
- 链接2
```

也支持键值对格式：

```
姓名：张三
职位：产品经理
简介：...
```

## 📋 节目摘要格式

支持 Markdown 或纯文本格式，自动解析以下信息：

```markdown
# 节目标题

## 摘要

节目简介...

## 要点

- 要点1
- 要点2

## 标签

- 标签1
- 标签2
```

## 🧪 测试

运行工作流测试：

```bash
python test_workflow.py
```

生成测试数据：

```bash
python create_test_data.py
```

生成测试音频（WAV 格式）：

```bash
python generate_test_audio.py
```

## 📦 依赖说明

| 库 | 用途 | 可选 |
|----|------|------|
| watchdog | 文件夹监听 | 是（降级为轮询） |
| mutagen | 音频元数据读取 | 是（降级为基础检查） |
| Pillow | 图片尺寸检查 | 是（降级为基础检查） |
| PyYAML | 配置文件解析 | 否 |
| Jinja2 | 模板渲染 | 否 |

## 📄 许可证

MIT License
