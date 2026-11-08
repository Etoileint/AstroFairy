# Windows 原生验证交接

从 GitHub 本交接分支取得任务、候选、制品；结果回到该分支对应的草稿 PR。无需本机旧验证包或私有开发组织。

- 仓库：`Etoileint/AstroFairy`；分支：`handoff/windows-validation-20261108`。
- 固定候选提交：`c9824b24b1627dd10de70fbcfe028a0dc9dfcfd5`。本交接提交只增加任务/制品/校验和当前导航；产品字节与候选一致。
- [assignment.json](assignment.json)钉住源码、制品与权限；[candidate-manifest.json](candidate-manifest.json)来自候选Git blob。
- 上轮4类P2已闭合，当前工作是原计划剩余验证，不是重新开发。现状见[STATUS](../../STATUS.md)，
  规则见[AGENTS](../../AGENTS.md)和[CONTRIBUTING](../../CONTRIBUTING.md)。
- 包名仍含`0.1.0a2`，但[artifacts/](artifacts/)是本候选已验字节，不是已发布tag的旧附件；不得按版本号另取旧包。

## 权限和回交边界

只在新验证checkout、独立venv、夹具、模型缓存和证据目录内写入，不触碰其他项目和业务数据。
不修改产品/锁/协议，不改skip放宽门槛，不提交修复、合并、打tag、发布或变更Issue状态。
失败先区分产品根因、测试夹具和环境限制，保留最小复现与建议，交原会话处理。
不私自提权、全局装包或调整系统安全策略；只采集试验数据，不公开凭证、完整环境变量和个人/业务资料。

GitHub是双方通信通道。执行者可在**本分支对应的草稿PR**回复验证报告和原始证据，未执行不标通过。
原始ZIP可用PR附件回交；也可按文件在评论给出原始UTF-8文本、路径和摘要。原始失败日志不能只剩截屏或概述。
本机完整检查失败可能阻止正常Git提交，禁止绕过hooks；通过PR回交失败不要求先把失败候选伪装为绿色。
如无可用附件/评论写权限，明确回报通道缺口，不谎称原件已上传。

## 1. GitHub取件与环境准备

最低目标 Windows x64 / CPython3.12。记录真实Windows版本/架构、Python/SQLite/Git、文件系统和验证起始HEAD。
不能用WSL、Linux容器或Windows路径模拟代替Windows本机。

在有写权限的位置使用新目录（可调整末尾目录名）：

```powershell
git -c core.autocrlf=false clone --branch handoff/windows-validation-20261108 https://github.com/Etoileint/AstroFairy.git AstroFairy-validation
Set-Location AstroFairy-validation
git config core.autocrlf false
git config core.hooksPath .githooks
py -3.12 handoff/windows-validation/verify_candidate.py
```

保留完整Git历史，不使用浅克隆或单独GitHub源码ZIP；历史测试依赖旧blob。
校验器必须成功，记录当前HEAD及固定candidate提交，后续验证和回交前再运行，证明产品字节未变。
它只核对身份，不代表Windows功能通过。唯一允许的候选旧文件覆盖是交接导航（STATUS/审计索引）；
所有产品、锁、测试、原设计与已有报告仍逐字节核对。

PowerShell逐条执行并记录退出码；无需激活venv或修改ExecutionPolicy：

```powershell
py -3.12 -m venv .venv
$fairyPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
& $fairyPython -m pip install --require-hashes --only-binary=:all: -r skills/fairy/scripts/requirements-runtime.lock
& $fairyPython -m pip install --no-index --find-links skills/fairy/scripts/wheels --require-hashes -r skills/fairy/scripts/requirements-delivery.lock
& $fairyPython -m pip install --require-hashes --only-binary=:all: -r skills/fairy/scripts/requirements-search.lock
& $fairyPython -m pip install -r requirements-dev.lock
& $fairyPython -m pip install --no-deps --no-build-isolation -e .
& $fairyPython -m pip check
& $fairyPython -B dev/check.py
& $fairyPython -B dev/smoke_task.py
```

每条失败都保留stdout、stderr和退出码；不要把管道最后一个命令成功当作此前成功。
禁止降版本、去掉hash、换镜像、换其他模型或只保留无依赖安装来让验收变绿。
缺Git或CPython时使用维护者认可的官方安装方式；不要私自提权安装或覆盖已有环境。

## 2. 核心原生验证（优先完成）

| 对象 | 必须观察 |
|---|---|
| T04 / Issue #1 | 从全新venv完成core/delivery/search哈希安装和pip check；记录colorama、win32-setctime的实际安装版本。实际导入lancedb、fastembed、onnxruntime、tokenizers，元数据存在不能当ABI可用 |
| T13 / Issue #3 | 原生`dev/smoke_task.py`实际创建并full-validate BagIt；补多文件/含子目录交付，确认payload未误分类为tag；项目权威校验与上游校验均通过 |
| T14 | 用Windows真实junction/reparse分别覆盖home下deliveries祖先、task目录、目标seq目录和payload后代；ordinary deliver与repair都拒绝，不跟随、不移动链接，外部sentinel字节不变，权威任务事实不丢 |
| T25/T26 / Issue #4 | 普通坏包显式repair先验新包、隔离旧对象且保留；覆盖隔离前、两rename之间、发布后的失败。错误进度与实际目录相符。关闭/晚到事实保留，重开后只恢复deliver，不重放业务效果 |
| T29 | 对应owner回归保持；未知提交的call和调查动作可用，原始数据库错误不被rollback/释放错误遮蔽。受控代理与真实原生错误分别标明 |

安全负例的“外部”仅指测试home外、仍在本次夹具范围内的目录。保留sentinel前后hash与实际lstat属性。
移除junction只能移除链接本身；不递归删除外部目标。没有权限创建某种链接时登记未执行和环境原因，不能标通过。
普通symlink可能受Developer Mode/权限限制；不得自动改变系统策略。junction是独立原生负例，不用symlink模拟代替。
不必制造所有未知重解析点类型；明确已测类型及尚未覆盖范围。

已知待原生判定的测试夹具：`dev/tests/test_dependency_lock.py`的真实target布局用例含`.venv/bin/uv`与POSIX目录；
部分交付测试使用`chmod(0)`或普通symlink。Windows的chmod并不等于POSIX权限拒绝。
完整检查仍须实际执行；若因此失败，记录精确test/traceback及实际产品旁证，回交跨平台夹具修正建议，
不能改skip、只跑子集或预期异常后把原始完整检查记为通过。可继续独立执行其他原生项并逐项回交。

## 3. 分发与宿主验证

用本交接目录`handoff/windows-validation/artifacts/`三件原制品分别做wheel、sdist、skill ZIP独立安装/运行（T32）：
新venv、准备锁定依赖、pip check、doctor无副作用、最小完整任务、实际BagIt校验。
源checkout不可通过CWD/PYTHONPATH/旧editable安装暗中供包；记录实际`astrofairy.__file__`，确认来自目标安装。
skill ZIP使用其中的`fairy/scripts/fairy.py`及已准备解释器；源码不能依赖本机维护者路径。
不要用相同版本号从PyPI/GitHub另下的旧版替换此处制品。

有可用真实agent时，按fairy主skill执行一个小的多文件交付任务，再执行一次受控交付失败后的接续（T34）；
记录agent是否读到关键步骤、是否实际按调查/deliver接续、是否交付全部成员与可审核回执。
脚本调用CLI属于协议/安装证据，不能冒称真实模型遵循率或长期用户效果。
完整skills CLI安装矩阵如未执行，仍保留未执行，不因某一个宿主成功而全绿。

## 4. 后续集成项

冷下载/中断恢复（T10）和独立进程缓存锁（T11）可在Windows或后续Linux验证中执行，单独记录。
先完成无需大模型权重的原生安装、路径与交付项，再安排2GB级固定模型下载与真实推理；
完整冷下载会占带宽/磁盘，未准备好时准确回交未执行，不能把空库返回/已有缓存hash当下载或推理通过。
不得将Linux aarch64既有缓存和二进制环境复制到Windows当作全新安装。

## 5. 回交

输出到`.evaluation/windows-validation/return/`并生成回交ZIP。按上方授权在本分支草稿PR回交报告与原件，由原会话独立验收。

可用`gh pr list --repo Etoileint/AstroFairy --head handoff/windows-validation-20261108 --state open`找到交接PR，
再用`gh pr comment NUMBER --repo Etoileint/AstroFairy --body-file .evaluation/windows-validation/return/report.md`回交报告。
多行正文使用真实UTF-8文件；不要把日志塞进shell字符串。附件或分文件原始文本及哈希必须可供另一机器取得。
不需要推送修复或修改其他PR/Issue；评论不得包含真实数据或凭证。

- `report.md`：每个T和Issue的pass/fail/not_run、准确范围、发现与下一步；不代维护者最终接受。
- `environment.json`：OS/架构、Python/SQLite/Git、依赖及文件系统；不收集完整环境变量、凭证或业务文件。
- `runs.json`：每条命令参数数组、cwd、开始/结束时间、exit、stdout/stderr文件；保留失败尝试。
- `findings.json`：产品/夹具/环境分类、最小复现、预期与实际、源码位置、敏感信息已去除。
- `coverage.json`：T04/T10/T11/T13/T14/T25/T26/T29/T32/T34逐项证据索引及未覆盖范围。
- `source-before.json`、`source-after.json`：固定候选manifest的present文件SHA256及deleted状态；证明验证前后产品是否改变。
- `evidence-inventory.json`：所有回交原件的相对路径、字节数、SHA256（不包含自身）；同时给出整个回交ZIP的SHA256。
- 对失败或unknown保留调用/任务/序号及实际存储/目录观察。可分享纯测试数据库/包；不放venv、模型权重、用户真实数据和密码。

原会话根据GitHub原始证据独立验收；Linux x86_64 CI、其他平台及未执行集成项继续各自登记，不能由Windows结果推定。
