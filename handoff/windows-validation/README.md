# Windows 原生验证：第二轮统一复测

> 本任务已完成并通过[独立验收](../../docs/audit/changes/2026-11-08_windows-round2-acceptance.md)。
> 这是冻结的历史验证任务，复验须取得`3645fc6a601b5e162f801d6e62b96c7ee1c8b025`及其任务材料。
> 当前发布源码已有版本和文档更新，不应直接对当前工作树运行旧候选身份校验；
> 旧任务正文、制品与摘要解释冻结对象，不承担新版本的发布身份。

仓库 `Etoileint/AstroFairy`，分支 `handoff/windows-validation-20261108`，
[草稿 PR #5](https://github.com/Etoileint/AstroFairy/pull/5)。双方仅通过 GitHub 交接。

第一轮原始 ZIP 已完整收到：87,226 字节、148 件清单文件全部核验；无需重传。
这轮统一复测测试连接生命周期、工具环境发现、原生路径断言及安全负例。
产品运行时代码与 `c9824b24b1627dd10de70fbcfe028a0dc9dfcfd5` 一致；
新的测试源码候选、清单和三制品身份以 [assignment.json](assignment.json) 为准。
旧交接及制品保留在 `3f402b42797694d752c6cde7452980f0febbf14c` 的 Git 历史中。
当前制品虽然仍叫 `0.1.0a2`，属于开发候选，不能用已发布旧附件替代。

## 权限

仅在本项目独立 checkout、venv、临时夹具和 `.evaluation` 证据目录写入。
不修改产品、锁、测试或 skip，不绕 hooks，不合并、不打 tag、不发布、不变更用户 Issue。
不使用业务数据、凭证、完整环境变量；不提权、不开 Developer Mode、不改变系统安全策略。
失败也回交原始记录，不要求先修成绿色；新发现由原会话分析处理。

## 取件

使用原生 Windows x64 / CPython 3.12；WSL 或容器不能替代。
先检查工作树，保留已有证据；旧 checkout 有未提交修改时，另建新 clone，不能覆盖。

```powershell
git -c core.autocrlf=false clone --branch handoff/windows-validation-20261108 https://github.com/Etoileint/AstroFairy.git AstroFairy-round2
Set-Location AstroFairy-round2
git config core.autocrlf false
git config core.hooksPath .githooks
py -3.12 handoff/windows-validation/verify_candidate.py
```

保留完整 Git 历史。若复用干净旧 checkout，可正常 fetch 后 fast-forward 到 PR 最新明确任务提交。
开始前将 `git rev-parse HEAD` 与 PR 最新任务核对；身份校验必须通过。
清单来自候选 Git blob，覆盖 `handoff/` 外源码；交接目录是独立载体，三件制品另有摘要。
仅当前状态/审计索引允许导航覆盖；校验通过只证明身份，不代表功能通过。

新 checkout 按下列命令准备。已有正确环境可复用，但仍执行 pip check，并保留准备失败记录；
PowerShell 每条命令后检查 `$LASTEXITCODE`，失败先停下排查，不将后续成功代替前项结果。
无需激活或更改 ExecutionPolicy。

```powershell
py -3.12 -m venv .venv
$fairyPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
& $fairyPython -m pip install --require-hashes --only-binary=:all: -r skills/fairy/scripts/requirements-runtime.lock
& $fairyPython -m pip install --no-index --find-links skills/fairy/scripts/wheels --require-hashes -r skills/fairy/scripts/requirements-delivery.lock
& $fairyPython -m pip install --require-hashes --only-binary=:all: -r skills/fairy/scripts/requirements-search.lock
& $fairyPython -m pip install -r requirements-dev.lock
& $fairyPython -m pip install --no-deps --no-build-isolation -e .
& $fairyPython -m pip check
```

开发工具为版本 pin，core/delivery/search 才是哈希锁，不混称。
不降版本、删 hash 或换旧制品。若环境准备失败，先向 PR 回交精确命令、退出码及原始日志。

## 统一执行

下面一个命令会执行完整门、原生任务、真实依赖导入和三制品独立安装任务。
目录必须是新的；失败仍产生 ZIP，完整执行通常需要数分钟，取决于新 venv 的下载速度。
不会下载模型权重，不要求管理员权限或 Node。

```powershell
& $fairyPython -B handoff/windows-validation/collect.py --out .evaluation/windows-round2
```

收集器记录源码前后身份、平台/Python/SQLite、每条命令 argv/cwd/起止时间/退出码及 stdout/stderr 原始字节。
逐 CLI 输入/输出以 JSON/Base64 保留，程序随包；`launch_error` 表示没有成功启动，`exit=-1` 为本地标记。
wheel/sdist/ZIP 各用新 venv，在 checkout 外以隔离解释器运行 doctor→完整任务→上游 BagIt 校验，
wheel/sdist 还核对实际导入来自对应 venv；ZIP 明确使用其自身 launcher。

完整门含 255 项运行和 42 项开发测试；计数不是唯一覆盖量。
Windows 上三个 POSIX 权限/DAC 用例应明确 skip；两个真实模型用例按缓存/显式开启条件 skip。
两个文件 symlink 用例仅在真实 WinError 1314 时允许能力 skip；其他错误继续失败。
目录安全测试在 Windows 使用真实 junction，无需普通 symlink 权限，不能因缺 Developer Mode 跳过。
正式 owner 用例覆盖 home 外 sentinel 的 ancestor/task/sequence/payload 四处，ordinary/repair 均拒绝，
任务事实及目标不变；这是已测 junction 范围，不代表穷尽所有重解析点或 Windows ACL 认证。

测试失败不要自行改代码。可加新的、独立的最小探针和原始日志解释根因；额外探针必须连脚本一起回交。
若收集器本身在产 ZIP 前异常，保留现有输出与 traceback，不能删除失败目录后只报重试成功。

## 回交

输出包括 `.evaluation/windows-round2/`、同名 `.zip` 和 `.zip.sha256`。
先检查包内没有真实敏感信息；本轮脚本只使用生成的测试数据，不读取完整环境或凭证。
已登录 GitHub CLI 后，用显式发送命令向授权 PR #5 回交 ZIP 分片：

```powershell
& $fairyPython -B handoff/windows-validation/send.py .evaluation/windows-round2.zip
```

发送前验证 sidecar；每片含整体 bytes/SHA256 和 part/parts，接收者按字节重组验证。
中途失败保留已发评论，报告成功片号；重新发送相同包时按整体身份去重，不能覆盖或删旧证据。
如无 CLI/写权限，可在同一 PR 附件上传原 ZIP 并提供校验和；明确通道缺口，不宣称已上传。
另外评论简述平台、完整门结果、实际 skip、原生 junction 和三制品结果，以及 ZIP 身份和发现。
只向本草稿 PR 发任务证据，不向用户 Issue 或其他服务发消息。

收集器的 `checks_passed` 只表示其已执行检查通过，不代维护者验收，也不代表原计划全部闭合。
冷下载/中断 T10、跨进程模型缓存 T11、真实 E5 推理、完整 skills CLI 安装矩阵和真实宿主 T34
仍分开登记；本轮不擅自执行约 2GB 模型下载或将脚本任务冒称真实 agent 遵循率。
此前单/多文件与子目录 BagIt 原件已收到，不要求重做旧包；本轮以规范化正式用例及新三制品日志消除补件缺口。
Linux x86_64 与 Windows 托管 CI 各自实际执行，不由本机或开发机结果互相推定。
