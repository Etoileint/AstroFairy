# 全量机制与工作路径

本页由 mechanisms.json 生成。对象为调查覆盖，不复制历史 verdict，不声明本轮已逐行审计全部实现。
历史对象编号全部保留并重新定位；新增机制补足初版之后的变更。源码身份以 baseline.json 为准。

## 正常工作与信息交接

| 阶段 | 当前主要责任/信息入口 | 下一阶段重点核对 |
|---|---|---|
| 安装与发现 | 安装器/目录/插件、名称描述和宿主发现 | 真正入口、首用准备是否由 agent 承担 |
| 请求与材料 | 宿主提炼约定，start 捕获附件 | 原话、附件、必要目标与长资料能否完整进入 |
| 判断与澄清 | 模型决定可逆默认和关键问答 | 必要问题可问、无效重复不打扰 |
| 组织与执行 | 主文/host.md/schema/capabilities/next | 每阶段必要信息是否直接可得，是否过度依赖自主读取 |
| 登记与检查 | publish、机械 check、语义 review | 所有正式文件及其依赖关系是否受到覆盖 |
| 交付与审核 | close、导出、receipt 和聊天说明 | 用户实际拿到哪些文件，能否理解结构与依据 |
| 修改/恢复 | answer/revise、pending/confirmation、迟到事实 | 旧判断有效性、未知效果、预算与重建 |
| 反馈与学习 | feedback、learn、维护/验证/采用 | 成功/纠正/重复/不变均可表达，是否存在自行想起的断点 |
| 发现与复用 | search、read、固定版本、适用判断 | 正文和语义可发现性、误用/拒用、净收益 |
| 记录与维护 | 事件/blob/文档、审计、备份/恢复 | 实际资源增长、引用完整性与可恢复性 |

## 逐对象调查台账

| 对象 | 职责 | 调查任务 | 当前定位 |
|---|---|---|---|
| A01 | 产品范围与低负担委托 | T08 | [README.zh-CN.md:1](../../../README.zh-CN.md)；[SKILL.md:1](../../../skills/astrofairy/SKILL.md) |
| A02 | 协作宿主与本地运行器边界 | T08 | [architecture.md:1](../../../docs/guides/architecture.md)；[_runtime.py · Workshop:47](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_capabilities.py · Context:35](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py) |
| A03 | 协议、判定、调用和存储分离 | T08 | [_contracts.py:1](../../../skills/astrofairy/scripts/astrofairy/_contracts.py)；[_kernel.py:1](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_runtime.py:1](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_store.py:1](../../../skills/astrofairy/scripts/astrofairy/_store.py) |
| A04 | 受控任务循环及完成语义 | T08 | [_kernel.py · State:19](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_runtime.py · Workshop.next:486](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[SKILL.md:1](../../../skills/astrofairy/SKILL.md) |
| A05 | 原始证据、事件与派生视图 | T08 | [_store.py:1](../../../skills/astrofairy/scripts/astrofairy/_store.py)；[_kernel.py · replay:113](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_runtime.py · Workshop.inspect:536](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| A06 | 外置资产与任务化维护 | T08 | [_library.py:1](../../../skills/astrofairy/scripts/astrofairy/_library.py)；[_runtime.py · Workshop.learning_task:614](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[learning.md:1](../../../skills/astrofairy/references/learning.md) |
| A07 | 共享 skill 加可选分发适配 | T08 | [0002-portable-standard-skill.md:1](../../../docs/adr/0002-portable-standard-skill.md)；[pyproject.toml:1](../../../pyproject.toml)；[package_skill.py:1](../../../dev/package_skill.py) |
| A08 | 稳定核心与外围增长 | T08 | [governance.toml:1](../../../governance.toml)；[AGENTS.md:1](../../../AGENTS.md)；[0001-small-workshop.md:1](../../../docs/adr/0001-small-workshop.md) |
| A09 | 整体组合及端到端保证 | T08 | [README.zh-CN.md:1](../../../README.zh-CN.md)；[architecture.md:1](../../../docs/guides/architecture.md) |
| M01 | 技能发现与调用入口 | T01, T07 | [SKILL.md:1](../../../skills/astrofairy/SKILL.md) |
| M02 | 条件资料与按需披露 | T01 | [SKILL.md:1](../../../skills/astrofairy/SKILL.md)；[host.md:1](../../../skills/astrofairy/references/host.md) |
| M03 | 环境就绪诊断 | T07 | [_cli.py · _run:107](../../../skills/astrofairy/scripts/astrofairy/_cli.py) |
| M04 | 数据目录与任务工作区 | T07, T06 | [_store.py · Store.__init__:65](../../../skills/astrofairy/scripts/astrofairy/_store.py)；[_runtime.py · Workshop._start:92](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M05 | 建任务、默认标准和附件快照 | T01, T06 | [_runtime.py · Workshop.start:108](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M06 | 严格 JSON 与命令字段契约 | T01, T06 | [_contracts.py:1](../../../skills/astrofairy/scripts/astrofairy/_contracts.py) |
| M07 | 要求来源与修订 | T01, T06 | [_runtime.py · Workshop.submit:360](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_contracts.py · criteria_value:118](../../../skills/astrofairy/scripts/astrofairy/_contracts.py) |
| M08 | 关键提问与输入转发 | T01, T03 | [_kernel.py · admit_question:281](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_runtime.py · Workshop.submit:360](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M09 | 模型工作请求与报告 | T01, T06 | [_runtime.py · Workshop._request:129](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_runtime.py:1](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_runtime.py · Workshop.submit:360](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M10 | 工具注册、字段发现与能力目录 | T01, T08 | [_capabilities.py · Capability:65](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py)；[_capabilities.py · builtins:311](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py)；[_runtime.py · Workshop.catalog:520](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M11 | 动作准入、预算与重复防护 | T03, T06 | [_kernel.py · admit_call:203](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_kernel.py · require_open:218](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_kernel.py · State.budget_left:109](../../../skills/astrofairy/scripts/astrofairy/_kernel.py) |
| M12 | 调用前留痕与执行后观测 | T06 | [_runtime.py · Workshop.invoke:152](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M13 | 成果登记与版本绑定 | T02 | [_runtime.py · Workshop.submit:360](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_kernel.py · State.artifact:35](../../../skills/astrofairy/scripts/astrofairy/_kernel.py) |
| M14 | 文件捕获与类型标记 | T02 | [_capabilities.py · _capture:224](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py) |
| M15 | 内容访问与分段读取 | T01, T03, T04 | [_capabilities.py · Context.content:47](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py)；[_capabilities.py · _read:245](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py) |
| M16 | 机械检查器 | T02, T06 | [_capabilities.py · check_content:279](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py)；[_capabilities.py · _check:298](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py)；[_runtime.py · Workshop.check:303](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M17 | 语义审查、替代链和冲突 | T02, T06 | [_runtime.py · Workshop._review:276](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_kernel.py · admit_review:256](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_kernel.py · State.active_reviews:66](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_kernel.py · State.issues:79](../../../skills/astrofairy/scripts/astrofairy/_kernel.py) |
| M18 | 关闭门与结果分类 | T02, T06 | [_kernel.py · State.complete:88](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_kernel.py · admit_close:287](../../../skills/astrofairy/scripts/astrofairy/_kernel.py) |
| M19 | 下一步工作包与调度 | T01, T08 | [_runtime.py · Workshop.next:486](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M20 | 回执与交付导出 | T02, T06 | [_runtime.py · Workshop.inspect:536](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_runtime.py · Workshop.deliver:572](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M21 | SQLite 存储与事务 | T06 | [_store.py · Store.__init__:65](../../../skills/astrofairy/scripts/astrofairy/_store.py)；[_store.py · Store.close:132](../../../skills/astrofairy/scripts/astrofairy/_store.py)；[_store.py · Store.transaction:136](../../../skills/astrofairy/scripts/astrofairy/_store.py)；[_store.py · Store.tasks:208](../../../skills/astrofairy/scripts/astrofairy/_store.py) |
| M22 | 事件链、序号与重放 | T03, T06 | [_store.py · Store.events:161](../../../skills/astrofairy/scripts/astrofairy/_store.py)；[_store.py · Store.append:180](../../../skills/astrofairy/scripts/astrofairy/_store.py)；[_kernel.py · replay:113](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_runtime.py · Workshop.state:82](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_runtime.py · Workshop._append:126](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M23 | 内容寻址与字节完整性 | T02, T06 | [_store.py · Store.put:145](../../../skills/astrofairy/scripts/astrofairy/_store.py)；[_store.py · Store.get:152](../../../skills/astrofairy/scripts/astrofairy/_store.py)；[_contracts.py · canonical:46](../../../skills/astrofairy/scripts/astrofairy/_contracts.py)；[_contracts.py · digest:55](../../../skills/astrofairy/scripts/astrofairy/_contracts.py) |
| M24 | 路径约束、原子写与文件权限 | T02, T06 | [_capabilities.py · Context.path:40](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py)；[_capabilities.py · atomic_write:202](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py)；[_capabilities.py · _write:215](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py) |
| M25 | 重开、未决动作与迟到结果 | T06 | [_kernel.py · replay:113](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_runtime.py · Workshop.submit:360](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[review.md:1](../../../skills/astrofairy/references/review.md) |
| M26 | 资产提案与工作流结构 | T05 | [_library.py · Library.propose:79](../../../skills/astrofairy/scripts/astrofairy/_library.py) |
| M27 | 候选验证任务与固定策略 | T02, T05 | [_library.py · validation_criteria:27](../../../skills/astrofairy/scripts/astrofairy/_library.py)；[_runtime.py · Workshop.validation_task:601](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M28 | 采用与基准竞争 | T05 | [_library.py · Library.adopt:140](../../../skills/astrofairy/scripts/astrofairy/_library.py) |
| M29 | 资产状态、版本、退役与回退 | T04, T05 | [_library.py · Library.status:55](../../../skills/astrofairy/scripts/astrofairy/_library.py)；[_library.py · Library.head:63](../../../skills/astrofairy/scripts/astrofairy/_library.py)；[_library.py · Library.get:73](../../../skills/astrofairy/scripts/astrofairy/_library.py)；[_library.py · Library._event:133](../../../skills/astrofairy/scripts/astrofairy/_library.py)；[_library.py · Library.retire:161](../../../skills/astrofairy/scripts/astrofairy/_library.py) |
| M30 | 资产检索与排序 | T04 | [_library.py · Library.search:166](../../../skills/astrofairy/scripts/astrofairy/_library.py)；[_capabilities.py · _search:254](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py) |
| M31 | 资产读取与精确版本钉选 | T01, T04 | [_capabilities.py · _asset:262](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py)；[_runtime.py · Workshop.invoke:152](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M32 | 反馈与独立维护任务 | T05 | [_runtime.py · Workshop.learning_task:614](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_runtime.py · Workshop.submit:360](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| M33 | 资产分享与导入验证 | T05, T06 | [_library.py · Library.export:187](../../../skills/astrofairy/scripts/astrofairy/_library.py)；[_library.py · Library.import_bundle:190](../../../skills/astrofairy/scripts/astrofairy/_library.py) |
| M34 | 被动工具说明与内容信任 | T05, T06 | [learning.md:1](../../../skills/astrofairy/references/learning.md)；[_library.py · Library.propose:79](../../../skills/astrofairy/scripts/astrofairy/_library.py) |
| M35 | 资源限额与增长预算 | T03 | [_contracts.py:1](../../../skills/astrofairy/scripts/astrofairy/_contracts.py)；[governance.toml:1](../../../governance.toml)；[check.py:1](../../../dev/check.py) |
| M36 | CLI 错误、状态与诊断接口 | T01, T03 | [_cli.py:1](../../../skills/astrofairy/scripts/astrofairy/_cli.py)；[_errors.py:1](../../../skills/astrofairy/scripts/astrofairy/_errors.py)；[__main__.py:1](../../../skills/astrofairy/scripts/astrofairy/__main__.py) |
| M37 | 自包含启动与可选 Python 包 | T07 | [fairy.py:1](../../../skills/astrofairy/scripts/fairy.py)；[pyproject.toml:1](../../../pyproject.toml)；[_version.py:1](../../../skills/astrofairy/scripts/astrofairy/_version.py)；[__init__.py:1](../../../skills/astrofairy/scripts/astrofairy/__init__.py) |
| M38 | 便携 ZIP 内容过滤 | T07 | [package_skill.py:1](../../../dev/package_skill.py) |
| M39 | 派生版本、许可与包元数据同步 | T07 | [sync_metadata.py:1](../../../dev/sync_metadata.py)；[MANIFEST.in:1](../../../MANIFEST.in)；[LICENSE:1](../../../LICENSE)；[LICENSE:1](../../../skills/astrofairy/LICENSE) |
| M40 | 原生插件与市场清单 | T07 | [plugin.json:1](../../../.claude-plugin/plugin.json)；[marketplace.json:1](../../../.claude-plugin/marketplace.json) |
| M41 | 可选 UI 元数据 | T07 | [openai.yaml:1](../../../skills/astrofairy/agents/openai.yaml) |
| M42 | 测试面、类型与规范检查 | T09 | [check.py:1](../../../dev/check.py)；[check_installation.py:1](../../../dev/check_installation.py)；[test_metadata.py:1](../../../dev/tests/test_metadata.py)；[test_package_skill.py:1](../../../dev/tests/test_package_skill.py)；[requirements-dev.lock:1](../../../requirements-dev.lock) |
| M43 | 提交门与 CI 构建 | T09 | [pre-commit:1](../../../.githooks/pre-commit)；[check.yml:1](../../../.github/workflows/check.yml) |
| M44 | 文档、单源组织与公开边界 | T08, T09 | [AGENTS.md:1](../../../AGENTS.md)；[README.md:1](../../../README.md)；[README.zh-CN.md:1](../../../README.zh-CN.md)；[.gitignore:1](../../../.gitignore)；[.gitattributes:1](../../../.gitattributes) |
| M45 | 研究来源与验证声明 | T09 | [initial-validation.md:1](../../../docs/reports/initial-validation.md)；[mattpocock-alignment.md:1](../../../docs/reports/mattpocock-alignment.md) |
| C01 | 首次任务到交付 | T01, T02, T03, T07 | [SKILL.md:1](../../../skills/astrofairy/SKILL.md)；[_runtime.py:1](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| C02 | 要求变化到重新验收 | T01, T02, T06 | [_runtime.py · Workshop.submit:360](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_kernel.py:1](../../../skills/astrofairy/scripts/astrofairy/_kernel.py) |
| C03 | 中断到恢复与迟到结果 | T02, T03, T06 | [_store.py:1](../../../skills/astrofairy/scripts/astrofairy/_store.py)；[_kernel.py:1](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_runtime.py:1](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| C04 | 经验到下一次任务收益 | T01, T03, T04, T05 | [_library.py:1](../../../skills/astrofairy/scripts/astrofairy/_library.py)；[_runtime.py · Workshop.learning_task:614](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| C05 | 发送到接收端独立使用 | T04, T05, T06 | [_library.py · Library.export:187](../../../skills/astrofairy/scripts/astrofairy/_library.py)；[_library.py · Library.import_bundle:190](../../../skills/astrofairy/scripts/astrofairy/_library.py) |
| C06 | 公开源到多宿主安装与升级 | T01, T07 | [README.md:1](../../../README.md)；[check_installation.py:1](../../../dev/check_installation.py)；[package_skill.py:1](../../../dev/package_skill.py) |
| C07 | 规模增长及外部能力替换 | T03, T04, T05, T08 | [governance.toml:1](../../../governance.toml)；[_runtime.py:1](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_library.py:1](../../../skills/astrofairy/scripts/astrofairy/_library.py)；[_store.py:1](../../../skills/astrofairy/scripts/astrofairy/_store.py) |
| C08 | 权限与副作用贯穿路径 | T06 | [host.md:1](../../../skills/astrofairy/references/host.md)；[_kernel.py:1](../../../skills/astrofairy/scripts/astrofairy/_kernel.py)；[_capabilities.py:1](../../../skills/astrofairy/scripts/astrofairy/_capabilities.py) |
| U01 | 使用者思路进步的证据路径 | T05 | [SKILL.md:1](../../../skills/astrofairy/SKILL.md) |
| U02 | 重复任务成熟与回流触发 | T05 | [_runtime.py · Workshop.learning_task:614](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_library.py:1](../../../skills/astrofairy/scripts/astrofairy/_library.py) |
| U03 | 检索需求的语义覆盖 | T04 | [_library.py · Library.search:166](../../../skills/astrofairy/scripts/astrofairy/_library.py) |
| U04 | 长期数据保留与版本演化 | T03, T06 | [_store.py:1](../../../skills/astrofairy/scripts/astrofairy/_store.py)；[_library.py:1](../../../skills/astrofairy/scripts/astrofairy/_library.py) |
| U05 | 原生宿主及平台支持证据 | T07 | [README.md:1](../../../README.md)；[check_installation.py:1](../../../dev/check_installation.py) |
| U06 | 审核者理解组织依据的能力 | T02, T06 | [_runtime.py · Workshop.inspect:536](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[_runtime.py · Workshop.deliver:572](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| U07 | 未知效果恢复的操作闭环 | T03, T06 | [_runtime.py · Workshop.next:486](../../../skills/astrofairy/scripts/astrofairy/_runtime.py)；[review.md:1](../../../skills/astrofairy/references/review.md) |
| N01 | 声明式工具契约、运行环境与 Schema 准入 | T01, T03, T06, T07 | [_contracts.py · SchemaContract:260](../../../skills/astrofairy/scripts/astrofairy/_contracts.py) |
| N02 | 权威尝试核对与当前执行完整性 | T02, T03, T06 | [_kernel.py · reconciliation_for:171](../../../skills/astrofairy/scripts/astrofairy/_kernel.py) |
| N03 | 有界回包、免费文档选读与恢复标识 | T01, T03 | [_presentation.py · encode_response:39](../../../skills/astrofairy/scripts/astrofairy/_presentation.py) |
| N04 | 共享认证文档、局部读取与全量审计 | T01, T03, T06 | [_documents.py · freeze:557](../../../skills/astrofairy/scripts/astrofairy/_documents.py) |
| N05 | 记录寿命、完整审计、备份与新目录恢复 | T02, T03, T06 | [_maintenance.py · backup_state:286](../../../skills/astrofairy/scripts/astrofairy/_maintenance.py) |
| N06 | 初始约定严格归一化与附件原子捕获 | T01, T03, T06 | [_runtime.py · Workshop.start:108](../../../skills/astrofairy/scripts/astrofairy/_runtime.py) |
| N07 | 候选策略验证与精确采用绑定 | T02, T05, T06 | [_library.py · Library.adopt:140](../../../skills/astrofairy/scripts/astrofairy/_library.py) |
| N08 | 真实测试收集与执行通道 | T09 | [run_tests.py:1](../../../dev/run_tests.py)；[_testing.py:1](../../../dev/_testing.py) |
| N09 | 哈希锁定依赖、就绪检查与首次启动 | T01, T07 | [_cli.py · _run:107](../../../skills/astrofairy/scripts/astrofairy/_cli.py) |

## 全量覆盖的边界

每个运行模块有调查归属，所有历史架构/机制/组合/需求对象有接续问题。
名称和位置覆盖不证明语义完备；下一阶段仍须从实际用户路径反推遗漏职责。
依赖准备、分发脚本、测试/CI、文档和研究声明由 M37–M45/N08/N09 继续覆盖，
不因为不在核心行数统计内而退出调查。预算另见 limits.json，不在此重复维护。
