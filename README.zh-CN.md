# AstroFairy · 星灵

**有序推进 AI 任务，保留检查依据，积累可复用工作流。**

[English](README.md) · 简体中文

AstroFairy 是遵循 [Agent Skills 开放规范](https://agentskills.io/specification) 的技能包，
帮助现有智能体将任务请求和原始材料转化为可用成果。智能体负责需求澄清、组织、执行和审查，
小型 Python 运行器维护任务记录。

提出任务、提供相关文件，偶尔回答影响结果的关键问题，即可获得成果、简短的假设与限制说明，
以及需要复核时可查看的详细回执。

> 当前为早期 Alpha：本地运行器和便携 skill 已实现；尚未逐一验证所有安装目标的原生应用发现、
> 插件管理及更新行为。

## 安装

需要：

- 支持 Agent Skills、本地命令执行和文件访问的智能体应用。
- Python 3.12+，用于运行随包附带的脚本；无需第三方 Python 包或额外模型 API key。
- Node.js/npm，用于运行 [skills CLI](https://github.com/vercel-labs/skills) 安装器。
- 一个可写、可持久保存的数据目录，用于任务历史和可复用资产。

从 GitHub 安装到当前项目：

```sh
npx skills@latest add Etoileint/AstroFairy --skill astrofairy --copy
```

安装器会让你选择目标应用。需要无人值守、用户级安装时，指定应用并添加 `-g --yes`：

```sh
npx skills@latest add Etoileint/AstroFairy --skill astrofairy --agent codex --copy -g --yes
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
`skills/astrofairy/` 文件夹复制到应用支持的技能目录。该目录自带运行器，无需另行 `pip install`。
若应用未立即显示新技能，可以重新加载技能或新建会话。

## 使用

首次会话可以对智能体说：

> 使用 astrofairy，检查运行环境，并初始化用于保存任务和可复用资产的持久目录。

之后提供材料，直接委托任务：

> 用 astrofairy，根据这份报告做一份用于内部复盘的演示文稿。

> 用 astrofairy，对比这些方案并推荐可执行的下一步。

> 根据新的受众修改成果，保持原始数据不变。

智能体负责选择方法、管理任务编号和检查实际成果。当你的决定实质影响结果时，它会向你提问。
普通问答可以直接回答，无需建立任务。明确提及 `astrofairy` 可以表达选用该技能的意图；
自动选择行为由宿主应用决定。

## 工作方式

1. **明确任务：** 保存请求和材料，推导目标、检查标准与重要假设。
2. **执行产出：** 按需检索资产，选择合适工作流并执行，直到形成实际成果。
3. **检查成果：** 执行适用的机械检查，依据语义准则审查成果。
4. **交付结果：** 返回成果和回执，如实区分完整、部分、失败或取消的结果。

原始材料和成果字节会被保留。检查绑定任务修订和成果版本，成果改变后需要重新检查。
工具观测与模型判断分别记录。回执保存目标、假设、输入、执行动作和审查依据，供后续复核。

模型和任务所需工具由宿主提供。文档制作、渲染、浏览等专门能力取决于宿主可用的工具；
AstroFairy 没有内置所有文件格式的制作引擎。

## 学习与分享

成功方法、纠正、反馈和重复任务结构，都可以支持外置资产库的改进。
方法和工作流按需检索，避免不断增加常驻指令。

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

## 开发

```sh
python -m venv .venv
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

标准 skill 目录是主要分发单元。`dist/astrofairy.zip` 打包同一目录并排除开发文件，
可选 wheel 从同一份运行器源码构建。`.claude-plugin/` 提供可选原生插件清单；
本项目尚未验证原生托管安装与更新，这些文件不代表已在插件市场上架。

查看协议，以及建立一个最小开发任务：

```sh
python -m astrofairy schema
python -m astrofairy --home .fairy doctor
python -m astrofairy --home .fairy start --request 'Prepare a source-based project brief'
```

解析器是命令字段单源，`requirements-dev.lock` 是开发工具版本单源，`governance.toml` 声明测试面和增长预算。
修改包元数据或根 LICENSE 后，运行 `python dev/sync_metadata.py`；检查模式和 CI 会拒绝过期的派生文件。
验证结果见[首版记录](docs/reports/initial-validation.md)与[分发对照研究](docs/reports/mattpocock-alignment.md)，
具体操作见[运行指南](docs/guides/operation.md)。

## 致谢与许可证

技能包装和指令设计参考了 [Matt Pocock 的 skills](https://github.com/mattpocock/skills)，
包括按需披露、需求澄清与工作环境改进的方法。AstroFairy 是独立实现。

采用 [Apache License 2.0](LICENSE)。
