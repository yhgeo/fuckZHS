"""PyInstaller 运行时钩子：把 tiktoken 的词表缓存指向可执行文件内的副本。

构建时词表已被打进包内（见 fuckzhs.spec 的 datas），解包到 sys._MEIPASS。
这样运行时不需要联网下载，也不会受 systemd PrivateTmp 影响。

如果用户自己设了 TIKTOKEN_CACHE_DIR（例如想用持久化目录），尊重用户的设置。
"""
import os
import sys

_base = getattr(sys, '_MEIPASS', None)
if _base:
    _bundled = os.path.join(_base, 'data-gym-cache')
    if os.path.isdir(_bundled):
        os.environ.setdefault('TIKTOKEN_CACHE_DIR', _bundled)
