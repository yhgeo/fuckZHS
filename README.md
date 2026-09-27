# fuckZHS 食用指北

> 本仓库是 [VermiIIi0n/fuckZHS](https://github.com/VermiIIi0n/fuckZHS) 的复刻分支。
> 上游自 2025-10 起停更，社区修复 PR 长期无人合并，本分支**合入了 6 个社区修复 PR**，
> 并补充了完整的服务器部署 / 多账号 / 每日自动化方案。

---

## ⚠️ 用之前先读这段

这个脚本会**绕过智慧树的正常学习过程**，违反其服务条款。风险由使用者自行承担：

- 账号可能被判定异常、限制功能，甚至受到处罚（上游 issue 区有实际案例）
- 从**云服务器**运行风险更高——数据中心 IP 段是被重点监控的
- **多个账号共用同一个出口 IP** 时，平台有能力按 IP 关联账号
- 建议始终设置每日时限（`-l`），不要一天刷满 24 小时
- 不要开 `-d` 调试模式，它会把账号密码明文写进日志

---

## 这是什么

一个 _Python3_ 脚本，**直连智慧树后端 API** 自动刷课，不需要浏览器、不需要图形界面。

### 与上游的差异

| 项目 | 说明 |
|---|---|
| 合入的 PR | `#167` 日志追加写入 / `#147` 填空题返回值修复 / `#156` 速度抖动反检测 / `#164` 每日时限改为全课程共享 / `#166` 撞验证码自动重试 + 长休息降风控 / `#168` 适配 2026 改版后的 AI 智课 |
| 跳过的 PR | `#161`（与 `#147` 在填空题逻辑上撞 10 个冲突块）、`#154`（会引入 Selenium + Chrome，破坏「无浏览器」这一核心优势） |
| 新增 | 服务器部署脚本、多账号框架、每日定时任务（见 [`deploy/`](./deploy)） |

完整的合并记录、冲突解决细节见 [`MERGE-NOTES.md`](./MERGE-NOTES.md)。

### 特性

- 支持校内学分课（hike）与知到共享学分课（zhidao）
- 自动回答弹题
- 可设每日时限
- 射后不管，无需交互
- **无浏览器依赖**：纯 `requests` + `Pillow` + `pycryptodome` + `tiktoken`，实测峰值内存 **96 MB**，CPU 基本空转

---

## 快速开始

### 方式一：下载预编译可执行程序（推荐）

到 [Releases](https://github.com/yhgeo/fuckZHS/releases) 下载对应平台的**单文件程序，不需要安装 Python**：

| 文件 | 平台 | 体积 |
|---|---|---|
| `fuckzhs-linux-x86_64` | Linux x86-64（glibc ≥ 2.14，基本任何发行版都能跑） | 约 41 MB |
| `fuckzhs-windows-x86_64.exe` | Windows x64 | 约 26 MB |

```bash
mkdir -p /opt/fuckzhs && cd /opt/fuckzhs
curl -L -o fuckzhs https://github.com/yhgeo/fuckZHS/releases/latest/download/fuckzhs-linux-x86_64
chmod +x fuckzhs

# 扫码登录（二维码存到 ./data/qr/，拉到本地扫）
./fuckzhs --fetch --show_in_terminal --image_path ./data/qr
```

> ⚠️ **必须把可执行文件放在可写目录**（如 `/opt/fuckzhs/`），不要放 `/usr/bin`。
> 它会在**自己旁边**生成 `config.json`、`cookies.json`、`logs/`、`execution.json` ——
> 这是有意设计：打包后代码位于临时解包目录，进程退出即删，所以状态文件必须落在可执行文件旁边。
>
> 词表已经内置在可执行文件里，**运行时不需要联网下载**（源码方式首次要下 40 秒）。

### 方式二：从源码运行

#### 环境要求

- Linux / macOS / Windows 均可（本分支在 Ubuntu 24.04 + Python 3.12.3 上验证）
- Python 3.10 及以上
- 服务器部署**不需要**图形界面

#### 1. 拉代码、建虚拟环境、装依赖

```bash
git clone https://github.com/yhgeo/fuckZHS.git
cd fuckZHS

# Ubuntu 24.04 默认不带 ensurepip，必须先装这个，否则建不了 venv
sudo apt install -y python3-venv

python3 -m venv .venv
# 国内服务器建议走镜像
.venv/bin/python -m pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
```

#### 2. 预热 tiktoken 词表（**别跳过**）

`tiktoken` 默认把词表缓存在 `/tmp`。而 systemd 的 `PrivateTmp=true` 会给每次运行一个独立的 `/tmp`——
结果是**每次跑 AI 课程都要重新从 Azure 下载词表**。实测首次 **39.8 秒**，缓存后 **0.388 秒**。

```bash
mkdir -p ./data/tiktoken-cache
TIKTOKEN_CACHE_DIR=./data/tiktoken-cache \
  .venv/bin/python -c "import tiktoken; tiktoken.encoding_for_model('gpt-4')"
```

之后每次运行都要带上 `TIKTOKEN_CACHE_DIR` 指向这个目录（`deploy/` 里的脚本已经带上了）。

#### 3. 扫码登录

```bash
.venv/bin/python main.py --fetch --show_in_terminal --image_path ./data/qr
```

- `--image_path` 会把二维码存成 PNG。**无头服务器上把它拉到本地扫**，比在 SSH 终端里扫字符画可靠得多
- `--fetch` 会在登录后**只拉课程列表就退出**，不会碰任何课程
- 登录成功后生成 `cookies.json`，之后运行会自动走 `Successfully recovered from saved cookies`，无需再扫码

#### 4. 确认可用

```bash
.venv/bin/python main.py --fetch
```

看到 `Successfully recovered from saved cookies` 就说明登录态有效，并且能正常访问课程接口。

### 自己构建可执行程序

仓库已配好 PyInstaller 配置和 GitHub Actions 工作流：

```bash
pip install -r requirements.txt pyinstaller
pyinstaller --clean --noconfirm packaging/fuckzhs.spec
# 产物：dist/fuckzhs（Linux/macOS）或 dist/fuckzhs.exe（Windows）
```

推送 `v*` 格式的 tag 会自动触发 [release.yml](.github/workflows/release.yml)，
在 ubuntu / windows 上矩阵构建并把产物发布到 Releases。

---

## 配置

`config.json` 会在首次运行时自动创建。部署时建议这样设置：

```json
{
    "username": "",
    "password": "",
    "qrlogin": true,
    "save_cookies": true,
    "proxies": {},
    "logLevel": "INFO",
    "tree_view": true,
    "progressbar_view": true,
    "qr_extra": {
        "show_in_terminal": true,
        "ensure_unicode": true
    },
    "image_path": "/opt/fuckzhs/data/qr",
    "pushplus": { "enable": false, "token": "" },
    "bark": { "enable": false, "token": "https://example.com/xxxxxxxxx" },
    "config_version": "1.4.0",
    "ai": {
        "enabled": true,
        "use_zhidao_ai": true,
        "openai": {
            "api_base": "https://api.openai.com",
            "api_key": "sk-",
            "model_name": "claude-3-5-sonnet-20240620"
        },
        "ppt_processing": {
            "provide_to_ai": false,
            "moonShot": {
                "base_url": "https://api.moonshot.cn/v1",
                "api_key": "sk-",
                "delete_after_convert": true
            }
        },
        "use_stream": true
    }
}
```

| 字段 | 说明 |
|---|---|
| `qrlogin` | **目前强制启用**扫码登录，优先级高于账号密码 |
| `save_cookies` | 保存登录态，后续免扫码 |
| `logLevel` | `NOTSET` / `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `tree_view` | 是否打印课程目录树 |
| `progressbar_view` | 是否打印进度条 |
| `image_path` | 登录二维码的保存目录，留空则不保存 |
| `qr_extra.show_in_terminal` | 把二维码打印到终端。**无头服务器上必须为 `true`**，原因见下方「关键坑」 |
| `qr_extra.ensure_unicode` | 用 Unicode 方块字符渲染终端二维码，比 ANSI 色块更容易扫 |
| `pushplus` / `bark` | 刷完或需要验证码时的推送通知，可留空 |
| `ai.openai.api_key` | 处理 **AI 课程**需要，普通课程不受影响 |

> `config.json` 里可能有账号密码，记得 `chmod 600`。

---

## 使用

### 命令行参数

| 参数 | 说明 |
|---|---|
| `-c`, `--course` | 课程 ID。`courseId`（校内学分课）/ `recruitAndCourseId`（共享课）/ `polymas:courseId`（AI 智课），可传多个 |
| `-v`, `--videos` | 只刷指定视频。`fileId` / `videoId` / `resourceId`（AI 智课），可传多个 |
| `-u`, `--username` | 账号（**当前无效**，扫码被强制启用） |
| `-p`, `--password` | 密码（**当前无效**，且会明文留在 shell 历史里） |
| `-q`, `--qrlogin` | 二维码登录，目前**强制开启** |
| `-s`, `--speed` | 播放速度。不设则用默认值（知到为 1.5）。设很高可以「秒过」，但行为特征明显，不建议 |
| `-t`, `--threshold` | 完成阈值，默认 `0.91`。**设成大于 `1.0` 会重刷已看完的视频**（见下方「重看」） |
| `-l`, `--limit` | 每日刷课时限（分钟）。**所有课程共享**，当天重复运行会累计（记录在 `daily_limit.json`） |
| `-d`, `--debug` | 调试日志，**会记录账号密码到 `logs/debug.log`**，别乱分享 |
| `-f`, `--fetch` | 拉取课程清单写入 `execution.json`，然后退出 |
| `--show_in_terminal` | 把二维码打印到终端 |
| `--proxy` | 代理，如 `http://127.0.0.1:8080` |
| `--tree_view` | 是否打印课程目录树 |
| `--progressbar_view` | 是否打印进度条 |
| `--image_path` | 二维码保存目录 |
| `-ai`, `--aicourse` | 刷 AI 课程，需传 `COURSE_ID CLASS_ID` 两个参数 |
| `--noexam` | 刷 AI 课程时跳过考试 |
| `-h`, `--help` | 帮助 |

### 常用示例

```bash
# 刷 execution.json 里列出的所有课程
.venv/bin/python main.py

# 只刷指定课程，并限制每门课 30 分钟
.venv/bin/python main.py -c 4e5f5a5940584859454a585958435b465a -l 32

# 刷新课程清单
.venv/bin/python main.py --fetch

# 刷 AI 课程（课程号 114514，班级号 4444）
.venv/bin/python main.py -ai 114514 4444
```

> 不知道课程 ID？进课程页面看网址里的 `courseId` / `recruitAndCourseId`，或者直接用 `-f` 拉清单。

---

## 关键坑（必读）

这些都是实际踩过的，踩中任何一条都会让你以为「脚本坏了」。

### 1. `-l` 是**所有课程共享**的每日上限，不是每门课各自算

`fucker.py` 里的定义写得很明白：

```python
self.limit = abs(limit)   # daily time limit for fucking, in minutes, shared across courses
```

所以 `-l 30` 跑全部课程时，**第一门课就会把 30 分钟预算吃光**，后面几门一分钟都刷不到。

**想要「每门课各自 30 分钟」**，得改成每门课单独调用一次，并在每次调用前重置 `daily_limit.json`
（删掉它，下次启动 `_loadDailyTime()` 就返回 0）。`deploy/fuckzhs-daily` 就是这么做的。

### 2. `-l` 的分钟数 ≠ 课程进度分钟数

主循环里有两个反检测机制会吃掉倍速收益：

```python
pause = pause or int(random() < 0.008)*60   # 每真实秒 0.8% 概率触发 60 秒暂停
if pause:
    played_time = last_submit               # 暂停期间进度会「回退」到上次上报点
```

暂停占掉约 **32%** 的时间，且回退的是未上报的进度——1.5 倍速的收益几乎被完全抵消。
逐行复刻主循环做数值模拟（30 次取中位数）得到：

| `-l` 设置 | 实际推进的课程进度 |
|---|---|
| 20 | 19.4 分钟 |
| 25 | 24.0 分钟 |
| 30 | 28.5 分钟 |
| **32** | **30.6 分钟** |
| 35 | 33.3 分钟 |

换算关系约为 **课程进度 ≈ 0.95 × `-l`**。要 30 分钟课程进度就取 `-l 32`。

> 另外，时限检查发生在**每个视频开头**，所以到点后会**播完当前视频**才停，实际进度通常比上表略多一点。

### 3. 无头服务器上 `show_in_terminal` 必须显式开启

```python
if show_in_terminal is None:
    show_in_terminal = platform.system() == "Windows"
```

Linux 上默认 `False`，于是走 `img.show()` → 调 `xdg-open` 找图片查看器 → 服务器上必然失败。
在 `config.json` 里设成 `true`，或命令行加 `--show_in_terminal`。

### 4. 扫码是强制的，账号密码登录走不到

```python
qrlogin = args.qrlogin or config.qrlogin or True   # 注释：Force enabled for v2.3.*
```

`or True` 让这个值恒为真，所以 `fucker.login(username, password)` 那条分支是**死代码**。
只能扫码，或者预先准备好 `cookies.json`。

### 5. 日志**不写进 journalctl**

`logger.py` 里设了 `to_console=False`，日志只落文件：

```
logs/debug.log  logs/info.log  logs/warning.log  logs/error.log  logs/critical.log
```

用 systemd 跑的时候，`journalctl` 只能看到 `print()` 的内容（目录树、进度条、提示语），
看不到 logger 的输出。排查问题要直接看日志文件。

### 6. 进度条在管道里会「消失」

Python 的 stdout 输出到管道时是**块缓冲**。`print(..., end='\r')` 的进度条会攒在缓冲区里，
表现为「日志半天不增长，看起来像卡死了」。实际进程在正常工作。
判断进程是否在干活，看 `/proc/<pid>/io` 的 `wchar` 是否增长、`wchan` 是否为 `hrtimer_nanosleep`。

---

## 多账号

`fuckZHS` 把**所有状态文件都写在「代码目录」里**，而不是当前工作目录：

```python
def getDir():
    return os.path.dirname(os.path.realpath(__file__))
```

涉及 `cookies.json`、`daily_limit.json`、`execution.json`、`logs/`、`aiexamAnswer/`、`AiDownloadCache/`。
**代码里没有任何环境变量能重定向这些路径。** 所以两个账号跑同一个目录会互相覆盖 cookies、互相消耗预算。

**做法：每个账号一份独立的代码副本，共享同一个 venv。**

```
/opt/fuckzhs/                        ← 主账号（代码 + .venv + tiktoken 缓存）
/opt/fuckzhs-accounts/<账号名>/       ← 其他账号（代码副本 + 独立状态）
```

**不能用软链接**——`getDir()` 用的是 `realpath()`，软链接会被解析回真实路径，隔离就失效了。必须真实副本。
好在成本极低：只需 9 个文件（`main.py` `fucker.py` `utils.py` `logger.py` `ObjDict.py` `sign.py` `zd_utils.py` `push.py` `meta.json`），
单实例约 **200 KB**；`images/` 和 `decrypt/` 没有被任何代码引用，不用复制。

`deploy/fuckzhs-account` 封装了增删和登录：

```bash
sudo fuckzhs-account list                      # 列出账号、登录态、课程数
sudo fuckzhs-account add <账号名>               # 创建实例
sudo fuckzhs-account login <账号名>             # 扫码登录 + 自动生成 courses.conf
sudo fuckzhs-account fetch <账号名>             # 刷新课程列表
sudo fuckzhs-account sync                      # 主目录 git pull 后同步代码到所有账号
sudo fuckzhs-account rm <账号名> --force        # 删除实例
```

---

## 每日自动刷课

`deploy/fuckzhs-daily` + `deploy/fuckzhs-daily.service` / `.timer` 实现「每天定时，每门课各自刷满 N 分钟」。

**它的核心逻辑**（对应上面的坑 1）：

```
for 每个账号:
    for 每门课:
        rm -f daily_limit.json      # 重置预算，让本门课拿到独立的每日额度
        python main.py -c <课程ID> -l 32
```

**课程列表**存在各实例目录的 `courses.conf` 里：

```
# <课程ID>|<显示名>|<重看阈值，可留空>
4e5f5a5940584859454a585958435b465a|职业生涯规划——体验式学习|1.1
4e5b5d5b475d4859454a585859435f445c|走近人工智能|
```

**并发**：账号之间并发、账号内部课程串行。两个环境变量控制：

| 变量 | 默认 | 说明 |
|---|---|---|
| `ZHS_MAXJOBS` | 4 | 同时最多几个账号（每进程约 96 MB 内存） |
| `ZHS_STAGGER` | 120 | 账号间错开启动的秒数，避免「同一 IP 同时多账号」的整齐特征 |
| `ZHS_MINUTES` | 32 | 每门课的预算（32 ≈ 30 分钟课程进度） |

**安装**（脚本默认按 `/opt/fuckzhs` 布局，如需改路径直接编辑脚本顶部的变量）：

```bash
sudo install -m755 deploy/fuckzhs-daily   /usr/local/bin/fuckzhs-daily
sudo install -m755 deploy/fuckzhs-account /usr/local/bin/fuckzhs-account
sudo install -m644 deploy/fuckzhs-daily.service /etc/systemd/system/
sudo install -m644 deploy/fuckzhs-daily.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fuckzhs-daily.timer

systemctl list-timers fuckzhs-daily.timer    # 看下次触发时间
journalctl -u fuckzhs-daily -f               # 看运行日志
sudo fuckzhs-daily --dry-run                 # 只打印计划，不执行
```

定时器默认每天 **09:00** 触发，带 **0–30 分钟随机延迟**（避免每天同一秒），`Persistent=true`（关机错过会补跑）。

### 关于「重看」

`courses.conf` 第三段是重看阈值。默认 `0.91`，**已看完的视频会被跳过**：

```python
if watch_state == 1 and self.end_thre <= 1.0:   # check end_thre in case someone wants to rewatch
    logger.info(f"Video {video.name} already watched")
    return
```

设成大于 `1.0` 就会跳过这个 return，`end_time` 变成 `videoSec × 阈值`，已看完的视频会继续往后播：

- `-t 1.1` → 每个已看完的视频再多刷 10% 的时长
- `-t 2.0` → 等于完整重看一遍（进度会报到 200%，特征明显，不建议）

> ⚠️ **智慧树是否把「重看」计入学习时长，尚未验证。** 而且上报进度会超过 100%，平台可能钳制或视为异常。
> 这是权宜手段，不是官方支持的用法。

---

## 已知限制

- **只处理视频**。章节测试、作业、讨论这类任务它做不了。有课程可能视频 100% 完成但总进度卡在 80% 左右，差的就是这部分
- **AI 课程需要额外配置** OpenAI / Moonshot 的 API key，否则只能跳过
- **上游已停更**，智慧树每次改版都可能让签名或接口失效，届时需要重跑反混淆 + 找 salt 的逆向流程（见 [`DEVELOPMENT.md`](./DEVELOPMENT.md)）
- **没有自动化测试**，改动后只能拿真账号实测

---

## 常见问题

**Q：cookie 失效了怎么办？**
重新扫码。删掉 `cookies.json`，然后跑一次带 `--fetch --show_in_terminal --image_path <目录>` 的命令。
判断是否失效：跑 `--fetch`，看不到 `Successfully recovered from saved cookies` 就是失效了。

**Q：为什么进度不涨？**
先看 `logs/info.log` 里是不是满屏 `already watched`——说明这门课的视频已经看完了。用上面的「重看」办法。

**Q：`-l` 设了 30，为什么第一门课刷完后面就不动了？**
因为 `-l` 是所有课程共享的，见「关键坑 1」。

**Q：怎么更新代码？**
```bash
cd /opt/fuckzhs && sudo git pull
sudo fuckzhs-account sync      # 如果用了多账号，同步代码副本
```

**Q：会不会被封号？**
看最上面那段。直连 API 的流量特征比模拟浏览器明显，云服务器 IP 风险更高，多账号共用 IP 风险更高。
上游 issue 区有「脚本检测异常并被实际处罚」的记录。风险自己掂量。

---

## 文件结构

```
.
├── main.py                 # 入口：参数解析、登录、调度
├── fucker.py               # 核心：全部 API 调用与刷课逻辑
├── utils.py                # 路径解析、二维码显示、cookie 转换
├── logger.py               # 日志（注意 to_console=False，只落文件）
├── ObjDict.py              # 支持属性访问的 dict
├── sign.py / zd_utils.py   # 签名与加解密
├── push.py                 # pushplus / bark 推送
├── meta.json               # 版本信息
├── decrypt/                # 上游的 JS 反混淆工具（运行时不使用）
├── images/                 # README 用图（运行时不使用）
├── deploy/                 # 服务器部署脚本（本分支新增）
│   ├── fuckzhs-daily           # 每日刷课：多账号 + 每门课独立预算
│   ├── fuckzhs-account         # 多账号管理
│   ├── fuckzhs-daily.service   # systemd 服务单元
│   └── fuckzhs-daily.timer     # systemd 定时器
├── MERGE-NOTES.md          # 本分支合入了哪些 PR、冲突怎么解的
└── DEVELOPMENT.md          # 上游作者的 API 文档与逆向笔记
```

运行时会在代码目录生成：`config.json`、`cookies.json`、`execution.json`、`daily_limit.json`、`logs/`、`data/`。

---

## 来源与致谢

- 上游项目：[VermiIIi0n/fuckZHS](https://github.com/VermiIIi0n/fuckZHS)（MIT License，`LICENSE` 已保留）
- 合入的 6 个 PR 来自上游社区的贡献者，详见 [`MERGE-NOTES.md`](./MERGE-NOTES.md)
- 作者的技术笔记（反混淆、解密、API 逆向过程）见 [`DEVELOPMENT.md`](./DEVELOPMENT.md)
- 上游讨论区：[常见问题](https://github.com/VermiIIi0n/fuckZHS/discussions/25) · [版本更新注意事项](https://github.com/VermiIIi0n/fuckZHS/discussions/24)
