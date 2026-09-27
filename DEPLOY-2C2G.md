# 2 核 2G 服务器部署指南

## 结论先说

**2 核 2G 完全够用，而且余量很大。**

实测数据（本项目代码，加载全部依赖 + 实例化 + tiktoken 编码器）：

| 指标 | 实测值 |
|---|---|
| 裸 Python 解释器基线 | 23.4 MB |
| 完整运行态峰值 RSS | **95.5 MB** |
| 浏览器依赖 | 无 |

它本质是一个 `requests` 直连 API 的脚本，运行期间绝大部分时间在等网络和 `sleep`，
CPU 基本空转。**单核 512MB 的机器都能跑**，2C2G 属于超配。

> 注意：本结论仅对 `fuckZHS` 这一路线成立。`Autovisor` 走 Playwright 路线，必须装浏览器，
> 资源占用是完全不同的量级，不在本文讨论范围。

---

## 一、环境准备

以 Ubuntu 22.04 / 24.04 为例：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
python3 --version   # 需要 3.10 或以上
```

> Ubuntu 22.04 自带 3.10，24.04 自带 3.12，都满足要求。

---

## 二、安装

```bash
cd ~
# 把 fuckZHS-merged 目录上传到服务器，例如：
#   scp -r fuckZHS-merged user@server:~/
cd ~/fuckZHS-merged

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

依赖只有 5 个，都很轻：`Pillow` / `pycryptodome` / `requests` / `tiktoken` / `OpenAI`。
国内服务器建议加镜像源：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

---

## 三、登录：无头服务器的关键坑

**不要直接在服务器上跑扫码登录。** 原因在 `utils.py`：

```python
def showImage(img, show_in_terminal=False, ensure_unicode=False):
    if show_in_terminal:
        ...
    else:
        img = Image.open(io.BytesIO(img))
        threading.Thread(target=img.show).run()   # 调系统图片查看器
```

而 `main.py` 里 `show_in_terminal` 的默认值是：

```python
show_in_terminal = platform.system() == "Windows"
```

也就是说**在 Linux 上默认是 False**，会走 `img.show()` 去调系统图片查看器。
服务器没有图形界面，这一步会失败或直接卡住。

### 推荐做法：本地登录一次，把 cookies 传上去

这是最稳的路径，服务器端全程无需交互。

1. **在有桌面的机器上**（Windows/macOS 都行）跑一次登录：
   - 确保 `config.json` 里 `"save_cookies": true`
   - 运行 `python main.py -q`，用手机扫码完成登录
   - 同目录会生成 `cookies.json`

2. **把 `cookies.json` 传到服务器**：

   ```bash
   scp cookies.json user@server:~/fuckZHS-merged/
   ```

3. 服务器上直接运行。程序会走这个分支，自动复用凭据：

   ```
   Successfully recovered from saved cookies
   ```

> `cookies.json` 里是你的登录凭据，**等同于账号密码**。传输和存放都要注意权限：
> `chmod 600 cookies.json`

### 备选做法：在终端里打印二维码

如果不想传 cookies，可以强制在终端渲染二维码：

```bash
python main.py --show_in_terminal
```

这会把二维码以 ANSI 块字符画到终端，用手机扫。**注意**：
- 服务器终端需要支持 UTF-8，否则二维码会乱码
- 服务器时间必须准确，否则二维码可能已过期
- 交互式扫码在 SSH 里可行，但放进 systemd 就不行了

### 关于账号密码登录

上游 README 明确写了：**账号密码自动登录目前失效**，只剩二维码可用。
所以不要指望用 `-u` / `-p` 做无人值守登录，用 cookies 方案。

---

## 四、配置 config.json

首次运行 `main.py` 会自动生成 `config.json`。关键字段：

```json
{
  "save_cookies": true,
  "logLevel": "INFO",
  "tree_view": true,
  "proxies": {},
  "pushplus": { "enable": false, "token": "" },
  "bark": { "enable": false, "token": "" }
}
```

- `save_cookies`：**保持 true**，否则每次都要重新登录
- `pushplus` / `bark`：想把刷课进度推送到微信/手机就填 token，不填就关掉
- `proxies`：需要走代理时填，格式如 `{"https": "http://127.0.0.1:7890"}`

---

## 五、运行

先手动跑一次，确认能正常登录并识别课程：

```bash
source .venv/bin/activate
python main.py --fetch          # 只拉课程清单，不刷，先验证登录是否成功
python main.py -c <课程ID>      # 刷指定课程
```

课程 ID 取自网址：校内学分课是 `courseId`，共享学分课是 `recruitAndCourseId`。

### 用 systemd 做守护进程

```ini
# /etc/systemd/system/fuckzhs.service
[Unit]
Description=fuckZHS
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/fuckZHS-merged
ExecStart=/home/youruser/fuckZHS-merged/.venv/bin/python main.py -c <课程ID>
Restart=on-failure
RestartSec=60
StandardOutput=append:/home/youruser/fuckZHS-merged/run.log
StandardError=append:/home/youruser/fuckZHS-merged/run.log

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fuckzhs
sudo systemctl status fuckzhs
tail -f ~/fuckZHS-merged/run.log
```

> `os.get_terminal_size()` 在 `fucker.py` 里已经用 try/except 包住了，取不到就回退 80 列。
> 所以没有 TTY 的 systemd 环境下也能正常运行。

### 或直接用 tmux（更简单）

```bash
tmux new -s fuckzhs
source .venv/bin/activate && python main.py -c <课程ID>
# Ctrl+B 然后 D 脱离
```

---

## 六、安全注意事项

1. **`-p` 参数是明文密码**，会留在 shell 历史和进程列表里。**不要用**，走 cookies 方案。
2. **`-d` 调试日志会记录账号密码**。生产环境不要开 `-d`，`logLevel` 保持 `INFO`。
3. `cookies.json` 权限设为 `600`，且**不要**提交到任何 git 仓库。
4. `run.log` 也可能包含敏感信息，注意目录权限。
5. 服务器上的 `config.json`、`cookies.json` 都已被 `.gitignore` 覆盖，但仍建议手动确认。

---

## 七、风控提示

- **云服务器是数据中心 IP，风控命中概率高于家庭宽带。** 这是本方案相比「本地跑」最大的劣势。
- 已合入的 **#166** 专门为此设计：撞到验证码时不再直接退出，而是等待重试，
  并且每观看 45 分钟主动休息 3-10 分钟，模拟真人节奏。
- **但长休息期间如果服务器被判定为异常，仍可能触发滑块验证。** 触发后程序会暂停等待人工验证，
  这时需要你手动介入（通过 pushplus/bark 通知，或看日志）。
- 上游 issue 区已有用户反馈「脚本检测异常并被实际处罚」，请自行评估风险。

---

## 八、常见问题

| 现象 | 原因与处理 |
|---|---|
| 卡住不动、日志停在扫码 | 没加 `--show_in_terminal`，走了 `img.show()`。改用 cookies 方案或加上该参数 |
| `Successfully recovered from saved cookies` 之后报错 | cookies 过期了。本地重新登录生成新的 `cookies.json` |
| 终端二维码乱码 | 终端不是 UTF-8。设 `export LANG=C.UTF-8`，或改用 cookies 方案 |
| 提示课程识别不到 | 该课程类型未适配。目前支持校内学分课、知到共享课、AI 智课（#168 新增）。其他类型需等适配 |
| `ModuleNotFoundError: No module named 'openai'` | 依赖没装全，`pip install -r requirements.txt` 重跑 |
| 内存占用异常高 | 正常情况下应在 100MB 左右。用 `ps -o rss= -p $(pgrep -f main.py)` 核对 |
