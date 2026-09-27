# 合并说明（MERGE-NOTES）

本仓库是 `VermiIIi0n/fuckZHS` 的 fork，已把上游 8 个待合并 PR 中可用的 **6 个**合并进 `master`，
用于解决上游作者停更、社区修复 PR 无人合并的问题。

- **上游**：https://github.com/VermiIIi0n/fuckZHS
- **本仓库（fork）**：https://github.com/yhgeo/fuckZHS
- **基线**：上游 `master` @ `04cbbb8`（上游最后提交 2025-10-28）
- **合并结果**：本仓库 `master` @ `4e0764d`
- **许可证**：MIT（上游仓库自带，保留原 `LICENSE`，本产物同样受 MIT 约束）

---

## 一、已合入的 6 个 PR

按合并顺序：

| PR | 作者 | 提交 | 内容 |
|---|---|---|---|
| #167 | mouse7878 | `75a177d` | 日志文件改为追加写入，不再清空历史日志 |
| #147 | flyShaoyu | `a5d0630` | 修复填空题返回值解包错误、错误将答案 ID 当答案 |
| #156 | KiriAky107 | `2cefa65` | 增强视频学习功能的反检测机制（速度抖动） |
| #164 | jerry-271828 | `a0d9ec4` | 单课程时限改为全课程共享的每日时限 |
| #166 | mouse7878 | `a3ac93a` | 撞验证码时自动等待重试 + 定期长休息降低风控 |
| #168 | yylsping | `7e4e68a` | 适配 2026 改版后的 AI 智课（hikeAiCourse / polymas 平台） |

改动总量：`fucker.py` +460 行左右，另有 `main.py` / `logger.py` / `README.md` / `.gitignore`。

---

## 二、未合入的 2 个 PR 及原因

| PR | 标题 | 跳过原因 |
|---|---|---|
| **#161** | 重构 OpenAI 调用为 SDK & 新增填空题支持 | 与 #147 撞车，`fucker.py` **10 个冲突块**。两者都在改填空题逻辑，且 #161 是 483 增 / 370 删的大重构。**与 #147 二选一**，本次选了改动更小、更聚焦的 #147。若需要 OpenAI SDK 化，可单独 cherry-pick 并手工重写填空题部分。 |
| **#154** | 不完美的pr：修复账号密码登录，新增 ai 课程适配 | 会引入 `faker.py`（**实为 Selenium 登录器**，命名误导）与 `polymas_course_fetcher.py`，把 `selenium` + `webdriver_manager` + Chrome 依赖引进来，**破坏本项目「无浏览器、轻量部署」的核心优势**。其 AI 课程适配功能已由 #168 覆盖。作者自己也标注为「不完美」。 |

---

## 三、手工解决的 2 处冲突（#166 vs 已合入的 #156）

合并 #166 时与 #156 在 `fucker.py` 有 2 处冲突，已手工解决：

**1. `CaptchaException` 异常处理**（约 477 行）
合并两者：保留 #156 的详细日志（含异常信息），同时加入 #166 的 `captcha_hit` 标志位。

```python
except CaptchaException as e:
    self.captcha_hit = True
    logger.info(f"Captcha required: {e}")
```

**2. 主事件循环的播放模拟**（约 564 行）
两者都是反检测手段，**互补而非互斥**，因此全部保留：

- 保留 #156 的**速度抖动** `uniform(-0.15, 0.15)`
- 保留 #166 的**长休息**机制（每 45 分钟休息 3-10 分钟）
- 随机暂停概率取 **#166 的 0.008**（#156 原为 0.0035；#166 更新且明确针对风控调优，云服务器 IP 风险更高，取更保守值）

代码中已用 `# [merge]` 注释标出这几处，便于日后回溯。

---

## 四、验证结果

| 项目 | 结果 |
|---|---|
| `compileall` 全量语法检查 | 通过 |
| `python main.py -h` | 正常运行，已含 #168 新增的 `--noexam` 参数 |
| 导入 + 实例化 + tiktoken 峰值内存 | **95.5 MB**（与合并前的 95.1 MB 基本持平） |
| 浏览器依赖 | 无（已确认未引入 playwright / selenium / webdriver） |

**未做的验证**：真账号登录与刷课流程未实测（需要真实凭据，且会产生实际请求）。
合并后的功能正确性建议先用一门不重要的课试跑确认。

---

## 五、如何继续合并

本仓库就是合并结果的载体，直接 clone 即可：

```bash
git clone https://github.com/yhgeo/fuckZHS.git
```

若上游又出现新的 PR 需要补合，先添加上游远端，再按 PR 号取分支（**不需要额外 fork**）：

```bash
git remote add upstream https://github.com/VermiIIi0n/fuckZHS.git
git fetch upstream pull/<PR号>/head:pr-<PR号>
git merge pr-<PR号>
```

### 关于未合入的 #161

`#161` 与已合入的 `#147` 都改填空题逻辑，直接合会撞 10 个冲突块。两种处理方式：

- **放弃 #147 改用 #161**：`git revert` 掉 #147 的合并提交后再合 #161
- **保留 #147，单独移植 #161**：`git cherry-pick 8cbddec`，然后手工处理冲突

`#161` 的提交为 `8cbddec`。

---

## 六、风险声明

1. 本项目本质是绕过学习过程的自动化脚本，**违反智慧树服务条款**，账号存在被判定异常的风险。
2. 上游 issue 区已有用户反馈「脚本检测异常并被实际处罚」，请自行评估。
3. 云服务器为数据中心 IP，风控命中概率高于家庭宽带。已合入的 #166 长休息机制即为此设计。
4. 上游作者已停更 11 个月。智慧树若再次改版（尤其是签名 salt 或接口变更），
   需要重跑作者 README 中记载的逆向流程（deobfuscate → 找 salt → 重写解密函数）。
5. 本仓库**没有测试**（上游即无 `tests/`），任何改动只能靠真账号实测验证。
