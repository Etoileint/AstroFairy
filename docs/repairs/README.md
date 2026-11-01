# 修复与优化

以根因为单位修复，保持小核心、低交互负担和标准技能分发。开发期直接采用正确的新契约，不承担旧数据或旧接口兼容。

整体进度见[完整工作范围](work-program.md)及其[状态数据](work-program.json)。下面15项是问题修复子台账，
不覆盖全部原计划的有限支持、待证、持续观察和整体终验义务。

[状态单源](status.json)登记每项发现的当前状态；[F01](F01-evidence-and-admission.md)记录首批改动、验证和边界。
[F02](F02-admission-and-available-actions.md)处理协议准入、初始约定、错误回包和下一步调度。
[F03](F03-declared-tool-contracts.md)处理扩展工具的参数契约、预验证与可纠正反馈。
[F04](F04-unicode-discovery-and-sqlite-admission.md)处理 Unicode 元数据匹配与底层 SQLite 能力准入，
设计见[ADR-0006](../adr/0006-unicode-discovery-and-sqlite-admission.md)。
[F05](F05-package-to-plugin-version-contract.md)处理包版本到插件版本的规范转换与拒绝范围，
设计见[ADR-0007](../adr/0007-package-to-plugin-version-contract.md)。
[F06](F06-authoritative-attempt-confirmation.md)为显式支持的工具补充原尝试的权威核对，
设计见[ADR-0008](../adr/0008-authoritative-attempt-confirmation.md)。
[F07](F07-bounded-agent-responses.md)处理完整回包字节预算、免费文档读取与学习快照目录，
设计见[ADR-0009](../adr/0009-bounded-agent-responses.md)。
设计理由分别见[ADR-0003](../adr/0003-review-identity-and-effect-contracts.md)与
[ADR-0004](../adr/0004-admission-and-available-actions.md)。
工具契约设计见[ADR-0005](../adr/0005-declared-tool-contracts.md)。

[初版复核](../reviews/README.md)继续指向冻结提交及当时结论。历史基线自检从 Git blob 核验，
不会要求修复后的工作区继续等于旧源码，也不替代新实现的测试和独立复验。

F01–F05 已完成原 13 项确认发现的技术修复与独立复验；F06 按显式支持工具的正向完整结果核对范围闭合 R02-D01。
F07 已完成 R02-D02 原总工作包消费范围的技术修复与独立复验；原台账 15 项现均为 verified，状态以台账为准。
这不是整体产品终验。[F08](F08-shared-authenticated-documents.md)已完成P01文档共享与按需验证的技术实现和独立复验，
设计见[ADR-0010](../adr/0010-shared-authenticated-documents.md)。[F09](F09-record-lifetime-and-state-recovery.md)已按严格重放、保留政策和状态备份恢复范围完成P02技术复验，
设计见[ADR-0011](../adr/0011-record-lifetime-and-state-recovery.md)。P03–P07继续开放，整体产品未终验。
下一阶段需依据实际任务取证这些相邻成本、宿主行为和长期学习效果，维护者保留包括存储代价在内的终局接受。
修复通过不等于真实成员、跨宿主和长期学习效果已验收。提交、推送和发布不在本轮授权动作中。
