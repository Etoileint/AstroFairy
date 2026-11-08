# AstroFairy · 星灵

**有序推进 AI 任务，保留检查依据，积累可复用工作流。**

[English](README.md) · 简体中文

AstroFairy 是遵循 [Agent Skills 开放规范](https://agentskills.io/specification) 的技能包，
帮助现有智能体将任务请求和原始材料转化为可用成果。智能体负责需求澄清、组织、执行和审查，
小型 Python 运行器维护任务记录。

提出任务、提供相关文件，偶尔回答影响结果的关键问题，即可获得成果、简短的假设与限制说明，
以及需要复核时可查看的详细回执。

> 当前为早期 Alpha · `0.1.0a3`：本地运行器和便携 skill 已实现并测试；尚未逐一验证所有安装目标的
> 原生应用发现、插件管理及更新行为。详见[发布说明与验证范围](docs/releases/v0.1.0a3.md)。

希望从逻辑理解整个项目，可以读[项目逻辑说明](docs/guides/understanding-astrofairy.md)。
[复核工作区](docs/reviews/README.md)包含全量架构与机制台账及取证准备，不代表这些设计已经通过复核。

## 安装

需要：

- 支持 Agent Skills、本地命令执行和文件访问的智能体应用。
- Python 3.12+ 与随技能提供的哈希锁定运行依赖；无需额外模型 API key。
- 该解释器的 SQLite 须支持窗口函数、物化 CTE、确定性回调和外键；`doctor` 实测这些能力，不创建任务数据。
- Node.js 22.20.0+ 和 npm，用于运行本次验证的 [skills CLI](https://github.com/vercel-labs/skills)
  1.7.4 安装器（[发布的运行要求](https://www.npmjs.com/package/skills/v/1.7.4)）。
  后续安装器版本可能调整要求；手动复制安装无需 Node.js。
- 一个可写、可持久保存的数据目录，用于任务历史和可复用资产。

智能体按[运行环境准备说明](skills/fairy/references/runtime.md)一次性准备本地虚拟环境并复用，
无需使用者管理版本，也不全局安装或静默下载依赖。

从 GitHub 安装到当前项目：

```sh
npx skills@latest add Etoileint/AstroFairy --skill fairy --copy
```

需要固定本次发布及已验证安装器时，使用：

```sh
npx skills@1.7.4 add https://github.com/Etoileint/AstroFairy/tree/v0.1.0a3 --skill fairy --copy
```

安装器会让你选择目标应用。需要无人值守、用户级安装时，指定应用并添加 `-g --yes`：

```sh
npx skills@latest add Etoileint/AstroFairy --skill fairy --agent codex --copy -g --yes
```

| 应用 | `--agent` 参数值 |
|---|---|
| Codex | `codex` |
| Claude Code | `claude-code` |
| Cursor | `cursor` |
| GitHub Copilot | `github-copilot` |
| Gemini CLI | `gemini-cli` |

这五种安装目标已通过项目级复制安装与运行器隔离测试，尚不能据此证明每个原生应用都能正确加载和调用。
私有仓库需要有访问权限的 Git 凭据。

使用本地仓库时，把 `Etoileint/AstroFairy` 换成本机目录路径。手动安装时，将整个
`skills/fairy/` 文件夹复制到应用支持的技能目录。该目录自带运行器，无需另行 `pip install`。
若应用未立即显示新技能，可以重新加载技能或新建会话。

## 使用

首次会话可以对智能体说：

> 使用 fairy（星灵），检查运行环境，并初始化用于保存任务和可复用资产的持久目录。

之后提供材料，直接委托任务：

> 用 fairy（星灵），根据这份报告做一份用于内部复盘的演示文稿。

> 用 fairy（星灵），对比这些方案并推荐可执行的下一步。

> 根据新的受众修改成果，保持原始数据不变。

智能体负责选择方法、管理任务编号和检查实际成果。当你的决定实质影响结果时，它会向你提问。
普通问答可以直接回答，无需建立任务。明确提及 `fairy` 或「星灵」可以表达选用该技能的意图；
自动选择行为由宿主应用决定。

## 工作方式

1. **明确任务：** 保存请求和材料，推导目标、检查标准、交付职责与重要假设；默认约定为临时的，须按实际任务细化。
2. **执行产出：** 按需检索资产，选择合适工作流并执行，直到所有正式成员实际形成。
3. **检查成果：** 执行适用的机械检查，依据语义准则审查当前快照；准则可作用于内容、指定成员或整个集合。
4. **交付结果：** 如实以完整、部分、失败或取消结束任务。运行器保留这一已提交事实，并单独记录导出观测；导出成功时返回完整校验的 BagIt 目录、全部正式成员和回执。导出失败不撤回已提交事实，回包给出有界错误和 `deliver` 恢复命令，不要求重做工作。

原始材料与成员字节会被保留。成员具有规范相对路径、媒体类型和交付角色；快照是按路径排序的不可变成员清单。
检查绑定任务约定修订、准则定义、作用域和确切靶标；新快照不继承语义或集合级判断，纯内容机械检查只在身份一致时复用。
未替代的失败会持续显示并要求显式处置。工具观测与模型判断分别记录。
回执保存目标、假设、输入、快照成员、执行动作和审查依据，供后续复核。
回执投影 2 只由已记录事实和已记录检查器身份生成：同一任务序号在重启或当前检查器注册表变化后仍保持相同回执字节，当前评估另行报告。
本版使用协议 11、阶段包 2 和存储格式 10。旧数据库不迁移、不兼容，由智能体为新任务选用获准的新状态目录。
已有派生包损坏或格式不受支持时，只通过显式 repair 重建：先校验新包，再把旧目录移入隔离目录（不删除）。

面向智能体的命令回包有固定字节预算。较大的完整记录通过不可变文档和免费分段读取保留，
智能体按需查看相关部分，快照共用不变内容。局部读取核对所读部分，另有完整审计检查整份文档。
使用者无需管理这些步骤。这个机制不保证磁盘、重放耗时或宿主整体对话上下文恒定。

写工具可显式指定受信的只读核对工具，以权威结果确认原尝试，同时保留原来的未知观察；当前成果仍须独立检查。
相互矛盾的正向证据持续显示争议，历史关闭之后也不会消失。无法核对或仍不确定时如实采用部分、失败或取消结果，
详见[恢复协议](skills/fairy/references/review.md)。

模型和任务所需工具由宿主提供。文档制作、渲染、浏览等专门能力取决于宿主可用的工具；
AstroFairy 没有内置所有文件格式的制作引擎。

## 学习与分享

成功方法、纠正、反馈和重复任务结构，都可以支持外置资产库的改进。
方法和工作流按需检索，避免不断增加常驻指令。检索使用本地 BM25/向量混合索引，只为活跃采用头建投影；
候选和退役版本不进入普通发现；`assets prepare` 在模型缺失时显式下载固定 revision，并流式校验六个实际消费文件的 SHA256，不建索引、不推理；`assets search --refresh` 复用同一准备服务并重建投影。普通搜索不会静默下载；显式 refresh 遇到空库时返回空投影和准备结果。

交付后，智能体可以提出可复用资产，通过独立任务验证，再进入试用或稳定使用状态。
资产可以修订或退役，维护也可以得出无需改变的结论。导出资产是可传输的 JSON 包，
接收方导入后仍需本地验证。目前通过文件分享，尚未实现团队账户权限、远程同步或自动后台维护。

## 数据与信任边界

数据目录应与安装的 skill 分开，以便更新时保留历史和学习资产。运行器支持显式 `--home`；
未指定时依次使用 `ASTROFAIRY_HOME`、`~/.local/share/astrofairy`。宿主需要有权访问所选位置。

AstroFairy 依靠智能体配合与本地检查运行，不隔离宿主，也不独立认证语义质量。
模型审查仍属于模型判断，本地完整性哈希不代表外部认证。被中断且结果不确定的动作会阻止完整交付，
直到完成核对。本地约束调用次数和内容预算，实际模型 token 与耗时由宿主管理。
详见[架构与约束边界](docs/guides/architecture.md)。

结构化工作可能比直接回答消耗更多调用与时间，简单任务尤其如此。受控样例支持可行性，
不能据此承诺普遍的质量、速度或成本优势。真人使用体验、长期学习收益及资源取舍仍需持续观察。

## 开发

新接手的开发者或 agent 先读[贡献与开发指南](CONTRIBUTING.md)和[当前开发状态](STATUS.md)，
据此区分现行规则、GitHub待核实问题、历史记录、检查层次及证据获取方式。
`CLAUDE.md` 使用原生导入加载同一份 `AGENTS.md`。

```sh
python -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r skills/fairy/scripts/requirements-runtime.lock
.venv/bin/python -m pip install --no-index --find-links skills/fairy/scripts/wheels --require-hashes -r skills/fairy/scripts/requirements-delivery.lock
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r skills/fairy/scripts/requirements-search.lock
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python dev/check.py
```

上述命令使用 POSIX 虚拟环境路径，Windows 请使用对应的 `.venv\Scripts\python`。
执行 `git config core.hooksPath .githooks`，启用本地提交前检查。

构建可选 Python 包和便携 skill 压缩包：

```sh
.venv/bin/python -m build --no-isolation
.venv/bin/python dev/package_skill.py
```

标准 skill 目录是主要分发单元。`dist/fairy.zip` 打包同一目录并排除开发文件，
可选 wheel 从同一份运行器源码构建。`.claude-plugin/` 提供可选原生插件清单；
本项目尚未验证原生托管安装与更新，这些文件不代表已在插件市场上架。

查看协议，以及建立一个最小开发任务：

```sh
python -m astrofairy schema
python -m astrofairy --home .fairy doctor
python -m astrofairy --home .fairy start --request 'Prepare a source-based project brief'
```

解析器是命令字段单源，`requirements-dev.lock` 是开发工具版本单源，`governance.toml` 声明测试面、检查命令和架构度量。
修改包元数据或根 LICENSE 后，运行 `python dev/sync_metadata.py`；检查模式和 CI 会拒绝过期的派生文件。
包版本采用三段数字，可带 a/b/rc 预发布标记；开发生成器用 packaging.Version 规范化后派生插件 SemVer，
超出声明范围的 epoch/post/dev/local 等形式在生成前拒绝，详见[版本契约](docs/adr/0007-package-to-plugin-version-contract.md)。
验证结果见[首版记录](docs/reports/initial-validation.md)与[分发对照研究](docs/reports/mattpocock-alignment.md)，
具体操作见[运行指南](docs/guides/operation.md)。
[修复工作区](docs/repairs/README.md)单独登记初版复核后的改动与重验。
[发布流程](docs/guides/releasing.md)说明版本、检查和制品发布方法。
[优化验收](docs/optimization/2026-11-acceptance/final-2026-11-03/README.md)保留此前优化的技术复验；
[Windows原生验收](docs/audit/changes/2026-11-08_windows-round2-acceptance.md)记录本次平台与交付修正的新增证据。

## 版本历史

- `0.1.0a1`（2026-11-01）：首个公开 Alpha，提供可追溯任务交付和外置可复用资产。
- `0.1.0a2`（2026-11-03）：`fairy` 入口、完整主指令和阶段包、多文件 BagIt 交付、资源政策重整、本地混合检索，以及贯通的学习/治理与恢复验证。[发布说明](docs/releases/v0.1.0a2.md)。

- `0.1.0a3`（2026-11-08）：通用条件依赖锁、显式模型准备与诊断、Windows BagIt/junction 原生验证，以及保留已提交事实的交付恢复和稳定回执。[发布说明](docs/releases/v0.1.0a3.md)。

## 致谢与许可证

技能包装和指令设计参考了 [Matt Pocock 的 skills](https://github.com/mattpocock/skills)，
包括按需披露、需求澄清与工作环境改进的方法。AstroFairy 是独立实现。

采用 [Apache License 2.0](LICENSE)。
