# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 —— 生成单文件可执行程序

构建（在仓库根目录执行）：
    pip install -r requirements.txt pyinstaller
    pyinstaller --clean --noconfirm packaging/fuckzhs.spec

产物：
    dist/fuckzhs         （Linux / macOS）
    dist/fuckzhs.exe     （Windows）

两个必须处理的点：

1. **tiktoken 词表**。默认在运行时从 Azure 下载，国内实测要 40 秒，
   而且 systemd 的 PrivateTmp 会让缓存每次失效。这里在构建阶段就下载好
   并打进可执行文件，运行时由 rthook_tiktoken.py 指向包内缓存。

2. **状态文件位置**。fuckZHS 把 cookies.json / config.json / logs 等
   全部写在「代码目录」。打包后代码位于临时解包目录，进程退出即删。
   utils.getDir() 已做 frozen 判断，改用可执行文件所在目录 —— 所以
   **可执行文件必须放在可写目录里**（例如 /opt/fuckzhs/），不要放 /usr/bin。

注意：spec 里的相对路径是相对 **spec 文件所在目录** 解析的（不是 CWD），
所以下面所有路径都显式拼成绝对路径。
"""
import os
import subprocess
import sys

from PyInstaller.utils.hooks import collect_submodules

# SPECPATH 由 PyInstaller 注入，指向本 spec 所在目录（<repo>/packaging）
ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))
CACHE_DIR = os.path.join(ROOT, 'build_tiktoken_cache')

# ---- 1. 构建期预下载 tiktoken 词表 ----------------------------------------
# 注意：这里只能用 ASCII 输出。Windows 的 stdout 默认是 cp1252，
# 打印中文会抛 UnicodeEncodeError 导致构建失败。
os.makedirs(CACHE_DIR, exist_ok=True)
_env = dict(os.environ, TIKTOKEN_CACHE_DIR=CACHE_DIR)
print('[spec] ROOT =', ROOT)
print('[spec] downloading tiktoken vocab into', CACHE_DIR)
subprocess.check_call(
    [sys.executable, '-c', "import tiktoken; tiktoken.encoding_for_model('gpt-4')"],
    env=_env)
print('[spec] cached files:', sorted(os.listdir(CACHE_DIR)))

datas = [
    (CACHE_DIR, 'data-gym-cache'),                    # 词表缓存，运行时由 rthook 指向它
    (os.path.join(ROOT, 'meta.json'), '.'),           # 版本信息，供更新检查读取
]

# tiktoken 通过 tiktoken_ext.openai_public 动态注册编码器，必须显式收集
hiddenimports = collect_submodules('tiktoken_ext') + ['tiktoken_ext.openai_public']

a = Analysis(
    [os.path.join(ROOT, 'main.py')],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(ROOT, 'packaging', 'rthook_tiktoken.py')],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='fuckzhs',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
