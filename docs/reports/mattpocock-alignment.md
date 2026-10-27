# Matt Pocock 对照研究与 AstroFairy 改进

日期：2026-10-27。研究基准固定为
[`mattpocock/skills@59db609`](https://github.com/mattpocock/skills/tree/59db609eb1e18aaf59b63284d0e52255aff0c63c)。
结论：沿用开放的 Agent Skills 目录协议和已有安装生态；借鉴信息组织、依赖判断和回顾方法，
将星灵自己的状态、核验和学习约束落实在脚本中。保留低交互、轻任务的产品目标。

## 研究范围与依据

从官方 GitHub 接口取得目录树，选取分发、写作、澄清、执行、回顾、教学与交接相关源文件。
原文快照、路径、获取 URL、SHA256 保存在忽略目录 `.reference/mattpocock/<commit>/`。
不把外部技能的命令或工程组织要求当成本项目的授权。

| 核对对象 | 固定版本一手资料 | 关注点 |
|---|---|---|
| 全包分发 | [README](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/README.md)、[插件决策及后续更新](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/.agents/adr/0002-ship-as-a-claude-code-plugin.md) | 通用安装与托管插件共存，不能把历史限制误当现状 |
| 分发实现 | [插件清单](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/.claude-plugin/plugin.json)、[版本同步](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/scripts/sync-plugin-version.mjs) | 一份技能源、显式选择、版本联动 |
| 指令写作 | [writing-for-agents](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/productivity/writing-for-agents/SKILL.md)、[SKILL-MECHANICS](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/productivity/writing-for-agents/SKILL-MECHANICS.md) | 条件指针、按需披露、结束条件、删除重复和廉价查询缓存 |
| 澄清 | [grilling](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/productivity/grilling/SKILL.md)、[grill-me](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/productivity/grill-me/SKILL.md) | 区分可调查事实与用户决策；给出推荐答案 |
| 依赖 | [硬依赖与软依赖决策](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/.agents/adr/0001-explicit-setup-pointer-only-for-hard-dependencies.md)、[工程配置入口](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/engineering/setup-matt-pocock-skills/SKILL.md) | 有硬依赖才要求初始化，非必要资料允许缺省 |
| 回顾 | [retro](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/engineering/retro/SKILL.md) | 改善工作环境，机械错误交给门禁，节约工具输出 |
| 学习 | [teach](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/productivity/teach/SKILL.md)、[学习记录](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/productivity/teach/LEARNING-RECORD-FORMAT.md) | 用证据判断学习，记录影响而非活动流水，允许替代旧理解 |
| 相邻流程 | [prototype](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/engineering/prototype/SKILL.md)、[handoff](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/productivity/handoff/SKILL.md)、[tdd](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/engineering/tdd/SKILL.md) | 用可运行证据消除不确定性，保留交接事实，不照搬领域流程 |

规范依据另行区分：
[Agent Skills specification](https://agentskills.io/specification) 是共享格式规范；
[参考校验器](https://github.com/agentskills/agentskills/tree/main/skills-ref) 是开发校验工具；
[Vercel skills CLI](https://github.com/vercel-labs/skills) 是已有安装实现，并非标准本身。
不同宿主的发现、工具权限和插件管理仍由宿主规定。

## 具体发现与落地

| 发现或借鉴 | AstroFairy 的处理 | 核验方式 |
|---|---|---|
| 仅有合法 SKILL.md 不足以证明可安装；旧目录复制后缺运行器 | 运行器和归属测试移到 `skills/astrofairy/scripts/astrofairy/`，launcher 仅查自身目录；wheel 读取同源代码 | 源目录复制、ZIP、真实安装器之后以 `-I -S` 执行 |
| 用自制打包补齐安装内容，会掩盖源目录缺陷 | 删除 ZIP 的依赖注入和私有 manifest，普通目录本身就是交付单元 | ZIP 文件逐项与标准目录原文件字节比较，检查重名 |
| Matt 同时支持通用安装和托管插件 | 保留 skills CLI 路线；提供 `.claude-plugin/` 清单与可选 OpenAI UI 元数据 | 五种项目级安装夹具；原生托管安装另列未测 |
| 多份版本或许可证会漂移 | 从 Python 版本、包 metadata 和根 LICENSE 生成分发文件 | `dev/sync_metadata.py --check`；故意更改版本的漂移测试 |
| 校验器也存在版本差异 | 开放规范允许 `compatibility`，本机 Codex 简易校验器尚不接受；将依赖声明放正文，保持共享 frontmatter 的最小字段集 | 同时运行开放规范参考校验器与本机 skill-creator 校验器 |
| 指令中的廉价查询缓存会过期 | 用 `schema` 和 `capabilities` 作为字段权威，移除重复工具参数列表 | 单源命令表、拒绝未知字段的运行器测试 |
| 主入口应体现动作和完成条件 | 入口压缩为 Define → Produce → Check → Deliver，恢复与学习按条件打开 | 入口字节预算和真实前向使用观察 |
| 初始化只适用于硬依赖 | 首次用只读 `doctor` 检查 Python 与数据目录；不要求先建 issue tracker、术语表或团队规范 | 就绪检查不创建状态；来源文件不依赖 AstroProject |
| 工具经济性不能只靠提示词 | 交付调用返回路径、结果和序列号；完整核验记录留在 receipt，按需 inspect | 断言简短回包不含 calls/reviews，receipt 保留来源 |
| 回顾应改善环境而非增厚 AGENTS | 沿用独立资产库、按需查询、版本绑定、候选验证、试用与退役；机械问题增加检查 | 原有学习/分享测试与本轮安装回归检查 |
| 学习不等于纠错日志 | 保留成功、反馈、重复结构与有效工具选择；可以修订、退休或不变 | 正反馈进入维护任务，分享导入保留来源并在本地再验证 |

## 有意保留的差异

1. 当前 upstream `grilling` 会一轮提出所有已可回答的问题，并穷尽决策树后等待确认。
   星灵借鉴依赖关系和推荐答案，但遵从用户明确要求：可查事实由智能体调查，普通可逆选择自行采用
   合理默认值，只有影响结果的关键决策才一次问一个简单问题，不引入整轮架构问卷。
2. Matt 的很多技能面向开发人员，要求用户记住入口、选流程或管理 issue。
   星灵只有一个日常入口，选择方法和保存任务编号是智能体的责任。资产数量不等于技能描述数量。
3. `retro` 的结论偏向提出改进建议。星灵在已授权范围内可进一步执行维护，但先交付，维护走普通任务机制，
   候选未经验证不能被采用；一次满意不自动代表普遍适用或团队共识。
4. `teach` 提供学习证据与取代关系的参考，不据此把用户交互变成教学作业。
   让使用者渐渐理解好成果的判断依据，可以通过简短交付说明实现，不强制额外培训步骤。
5. 不复制工程技能的大量外围结构、不迁移 Matt 的全包到星灵、不增加宿主专用工具依赖。
   本次没有增加核心生命周期状态或新的流程分支；新增的是可移植分发、诊断及检查工具。

## 安装验证及边界

实际工具：Node.js 24.22.1（官方归档 SHA256 核对），Vercel `skills` 1.7.4，Python 3.12.13。
安装工具、下载缓存、夹具及结果均保存在本项目忽略目录，未安装到用户全局目录或修改全局配置。

| 安装器目标 | 实测结果 | 后续隔离运行 |
|---|---|---|
| `codex` | 项目级复制成功 | doctor → start → request/report → publish → check/review → close，成果与来源一致 |
| `claude-code` | 项目级复制成功 | 同上 |
| `cursor` | 项目级复制成功 | 同上 |
| `github-copilot` | 项目级复制成功 | 同上 |
| `gemini-cli` | 项目级复制成功 | 同上 |

复现入口：`dev/check_installation.py`，传入 Node 和已安装 skills CLI 的路径。
原始回包、安装位置和交付句柄在 `.evaluation/installation/results.json`。
Python 使用 `-I -S`，因此不会靠本机 editable 包掩盖遗漏。该测试的语义判断是显式标记的
脚本夹具，不冒充真实模型评估。目录与 ZIP 的隔离回归检查不需要 Node，已进入普通检查入口。

Matt 分发 ADR 的首段描述过旧版 Codex 的单路径限制，但同一文件 2026-10-07 更新已记录支持
skills 数组及 `.claude-plugin` 回退。这里借鉴其当前清单组织方式；没有依据旧段落制造双份技能目录。
托管插件自动更新和五种原生应用的发现/触发效果尚未逐一实测。没有远程仓库、市场上架或团队远程同步服务。
“格式校验通过”“安装运行通过”“任务质量优秀”是三个不同结论。

首版的真实模型前向测试见[原始验证记录](initial-validation.md)。本轮最终检查结果追加在下方，
新增检查不把既有小样本升级为对任意任务质量或长期不膨胀的保证。

## 本轮最终结果

- `python dev/check.py`：44 项运行器/CLI/学习库测试、3 项开发与分发测试通过；
  Ruff ALL、格式、mypy、相对引用、测试归属及增长预算检查通过。
- 开放规范参考校验器 `skills-ref` 0.1.1 与本机 skill-creator 简易校验均通过。
  本机简易校验器未作为跨宿主项目依赖引入。
- 五种真实安装器目标的项目级复制与 `-I -S` 协议交付均通过。wheel、sdist 构建成功；
  wheel 的 Python 源文件逐项与 canonical skill 比较一致，隔离目录安装后实际建立任务成功。
- skill 主入口不足 3 KB，四个受预算约束的核心文件合计不足 1,000 行；
  数据来自本轮检查，预算仍由 `governance.toml` 管理，不据此声称架构已被证明永久完备。

另由全新上下文执行者，使用本轮便携 skill 快照与一份合成活动材料，完成用户形式的请求
“给我做个 PPT”。未提供预期分析或缺陷提示，实际提出人类问题 0 个；
从开始到交付约 2 分 53 秒，含试用记录约 3 分 42 秒。

产物为 8 页、约 42 KB 的可编辑 PPTX 与 receipt。执行者自行选择内部复盘场景和组织方式，
记录假设与验收准则；对比报名、到场、收入、直接成本与直接结余，展示公式，注明样本和数据限制，
将建议与已批准事项区分。复核者读取了逐页提取文字、核验结果和回执，原始数据及上述关键解释一致。
ZIP、XML、页数和形状边界经过实际检查；没有 PowerPoint/LibreOffice 渲染器，真实视觉渲染和字体替代未验证。
PPT 由宿主已有 Pandoc 与标准库生成，这不是星灵运行器自带 PPT 引擎；其他宿主的格式工具需要另行发现。

一次复合 capability 查询无结果，改用名称片段后恢复；没有现成 PPT 资产，执行者自行生成。
这些是样本观察，不因一次摩擦增加核心规则或专用 PPT 分支。完整材料、成果、回执与
`evaluation.md` 保存在 `.evaluation/portable-forward/`。语义审查仍明确归属于模型，
PPT 结构检查由宿主执行，不冒充本地运行器的独立工具证明。

本轮项目改动限于 AstroFairy；没有提交、推送、发布或用户级安装。
