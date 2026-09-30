#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查某个 fuckZHS 实例的登录态是否还有效。

用途：无人值守运行前的预检。

为什么需要它：cookies 失效时，main.py 会回退到**扫码登录**。在无人值守环境里
没有人能扫码，脚本就会卡在那里空转（上游原实现甚至是无限重试）。定时任务因此
永远不返回，后续的定时触发全部被 systemd 丢弃 —— 每天的学习记录就此断掉。

有了预检，登录失效时会在几秒内以非零退出码失败，日志里给出明确提示。

用法：
    check_login.py <实例目录>

退出码：
    0  登录有效
    1  登录失效（需要重新扫码）
    2  参数错误
"""
import json
import os
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_login.py <instance_dir>", file=sys.stderr)
        return 2

    d = os.path.abspath(sys.argv[1])
    if not os.path.isdir(d):
        print("LOGIN_FAIL: 实例目录不存在: %s" % d)
        return 1

    sys.path.insert(0, d)
    os.chdir(d)

    cookies_file = os.path.join(d, "cookies.json")
    if not os.path.exists(cookies_file):
        print("LOGIN_FAIL: cookies.json 不存在，需要先登录")
        return 1

    try:
        from fucker import Fucker

        f = Fucker()
        with open(cookies_file, encoding="utf-8") as fp:
            f.cookies = json.load(fp)
        courses = f.getZhidaoList()
        if not courses:
            raise RuntimeError("课程列表为空")
        print("LOGIN_OK: %d 门课程" % len(courses))
        return 0
    except Exception as e:
        print("LOGIN_FAIL: %s: %s" % (type(e).__name__, str(e)[:200]))
        return 1


if __name__ == "__main__":
    sys.exit(main())
