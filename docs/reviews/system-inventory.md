# 全量架构、机制及组合台账

生成视图。定义单源为 system-inventory.json。
更新后运行 `python dev/check_review_preparation.py --render`。
所有对象均须完成行业调查与对标。本表登记范围和进度。状态不代表达标。

A 为整体/子架构。M 为机制。C 为组合路径。U 为从愿景导出的待证责任。
文件与符号登记用于发现漏登记。语义覆盖仍需正式复核。

基线 `22b7ece5d8388379f7b4bcaf47de4c047173cd9b`。
候选权威源详情见[来源目录](authority-sources.md)。

## 已有轮次证据

| 对象 | 状态 | 证据 |
|---|---|---|
| A01 | R03三段实际模型/自然改稿/关键问答及独立复验完成；D01预算边界调度建议未修，原生/真人/长期效果待证 | [轮次记录](R01-vision-and-claims.md)、[轮次记录](R03-user-experience-and-guidance.md) |
| A02 | R14声明边界及局部权限/数据取证与独立复验完成；条件性D01扩展效果分类未修，模型抗注入/真实宿主/完整生命周期待后续 | [轮次记录](R02-core-architecture.md)、[轮次记录](R06-deterministic-and-model-boundaries.md)、[轮次记录](R14-authorization-data-and-security.md) |
| A03 | R06 局部机制及单个真实前向样本已取证/独立复验；扩展工具契约缺口未修，整体效果与既有事项待证 | [轮次记录](R02-core-architecture.md)、[轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R06-deterministic-and-model-boundaries.md) |
| A04 | R05真实多文件样本/陌生模型审核及机制独立复验完成；D01同内容冲突门和条件性D02对象错绑未修，整体效果待证 | [轮次记录](R02-core-architecture.md)、[轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R05-deliverables-and-evidence.md) |
| A05 | R14声明边界及局部权限/数据取证与独立复验完成；条件性D01扩展效果分类未修，模型抗注入/真实宿主/完整生命周期待后续 | [轮次记录](R02-core-architecture.md)、[轮次记录](R05-deliverables-and-evidence.md)、[轮次记录](R14-authorization-data-and-security.md) |
| A06 | R02 局部结构与探针证据已记录；完整行业对标及相关边界待证；R08 七对象八问及合成维护/新上下文迁移取证完成；真实学习收益、自然触发和人的进步待证；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限 | [轮次记录](R02-core-architecture.md)、[轮次记录](R08-learning-and-feedback.md)、[轮次记录](R09-workflows-reuse-and-sharing.md) |
| A07 | R12主审与独立取证完成；五布局同源/同版生命周期及Codex本机发现有限证据，D01及旧项开放，原生调用/跨平台/升级待证 | [轮次记录](R02-core-architecture.md)、[轮次记录](R11-agent-skills-contracts.md)、[轮次记录](R12-distribution-and-host-use.md) |
| A08 | R07双臂短任务/多维规模与独立复验取证完成；D01 Unicode字面匹配未修，R02-D02增长补证，普遍净收益/语义/长期效果待证；R10 主审及补做独立复验取证完成；R10-D01版本准入时序MAJOR/P2未修、FDP子类型保留，长期效果/政策待证 | [轮次记录](R02-core-architecture.md)、[轮次记录](R07-speed-and-economy.md)、[轮次记录](R10-long-term-evolution-and-growth.md) |
| A09 | R15综合主审与独立证据核对完成；13确认问题及2边界候选开放，整体/原生/真实人类/长期效果未验收 | [轮次记录](R01-vision-and-claims.md)、[轮次记录](R02-core-architecture.md)、[轮次记录](R15-evidence-and-integration.md) |
| M01 | R03三段实际模型/自然改稿/关键问答及独立复验完成；D01预算边界调度建议未修，原生/真人/长期效果待证 | [轮次记录](R11-agent-skills-contracts.md)、[轮次记录](R03-user-experience-and-guidance.md) |
| M02 | R07双臂短任务/多维规模与独立复验取证完成；D01 Unicode字面匹配未修，R02-D02增长补证，普遍净收益/语义/长期效果待证 | [轮次记录](R11-agent-skills-contracts.md)、[轮次记录](R06-deterministic-and-model-boundaries.md)、[轮次记录](R07-speed-and-economy.md) |
| M03 | R12主审与独立取证完成；五布局同源/同版生命周期及Codex本机发现有限证据，D01及旧项开放，原生调用/跨平台/升级待证 | [轮次记录](R03-user-experience-and-guidance.md)、[轮次记录](R12-distribution-and-host-use.md) |
| M04 | R12主审与独立取证完成；五布局同源/同版生命周期及Codex本机发现有限证据，D01及旧项开放，原生调用/跨平台/升级待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R14-authorization-data-and-security.md)、[轮次记录](R12-distribution-and-host-use.md) |
| M05 | R03三段实际模型/自然改稿/关键问答及独立复验完成；D01预算边界调度建议未修，原生/真人/长期效果待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R05-deliverables-and-evidence.md)、[轮次记录](R03-user-experience-and-guidance.md) |
| M06 | R06 局部机制及单个真实前向样本已取证/独立复验；扩展工具契约缺口未修，整体效果与既有事项待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R06-deterministic-and-model-boundaries.md) |
| M07 | R05真实多文件样本/陌生模型审核及机制独立复验完成；D01同内容冲突门和条件性D02对象错绑未修，整体效果待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R05-deliverables-and-evidence.md) |
| M08 | R03三段实际模型/自然改稿/关键问答及独立复验完成；D01预算边界调度建议未修，原生/真人/长期效果待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R03-user-experience-and-guidance.md) |
| M09 | R05真实多文件样本/陌生模型审核及机制独立复验完成；D01同内容冲突门和条件性D02对象错绑未修，整体效果待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R06-deterministic-and-model-boundaries.md)、[轮次记录](R05-deliverables-and-evidence.md) |
| M10 | R06 局部机制及单个真实前向样本已取证/独立复验；扩展工具契约缺口未修，整体效果与既有事项待证 | [轮次记录](R02-core-architecture.md)、[轮次记录](R06-deterministic-and-model-boundaries.md) |
| M11 | R14声明边界及局部权限/数据取证与独立复验完成；条件性D01扩展效果分类未修，模型抗注入/真实宿主/完整生命周期待后续 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R06-deterministic-and-model-boundaries.md)、[轮次记录](R14-authorization-data-and-security.md) |
| M12 | R14声明边界及局部权限/数据取证与独立复验完成；条件性D01扩展效果分类未修，模型抗注入/真实宿主/完整生命周期待后续 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R05-deliverables-and-evidence.md)、[轮次记录](R14-authorization-data-and-security.md) |
| M13 | R05真实多文件样本/陌生模型审核及机制独立复验完成；D01同内容冲突门和条件性D02对象错绑未修，整体效果待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R05-deliverables-and-evidence.md) |
| M14 | R05真实多文件样本/陌生模型审核及机制独立复验完成；D01同内容冲突门和条件性D02对象错绑未修，整体效果待证 | [轮次记录](R06-deterministic-and-model-boundaries.md)、[轮次记录](R05-deliverables-and-evidence.md) |
| M15 | R07双臂短任务/多维规模与独立复验取证完成；D01 Unicode字面匹配未修，R02-D02增长补证，普遍净收益/语义/长期效果待证 | [轮次记录](R06-deterministic-and-model-boundaries.md)、[轮次记录](R14-authorization-data-and-security.md)、[轮次记录](R07-speed-and-economy.md) |
| M16 | R05真实多文件样本/陌生模型审核及机制独立复验完成；D01同内容冲突门和条件性D02对象错绑未修，整体效果待证 | [轮次记录](R06-deterministic-and-model-boundaries.md)、[轮次记录](R05-deliverables-and-evidence.md) |
| M17 | R05真实多文件样本/陌生模型审核及机制独立复验完成；D01同内容冲突门和条件性D02对象错绑未修，整体效果待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R05-deliverables-and-evidence.md) |
| M18 | R05真实多文件样本/陌生模型审核及机制独立复验完成；D01同内容冲突门和条件性D02对象错绑未修，整体效果待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R05-deliverables-and-evidence.md) |
| M19 | R07双臂短任务/多维规模与独立复验取证完成；D01 Unicode字面匹配未修，R02-D02增长补证，普遍净收益/语义/长期效果待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R03-user-experience-and-guidance.md)、[轮次记录](R07-speed-and-economy.md) |
| M20 | R07双臂短任务/多维规模与独立复验取证完成；D01 Unicode字面匹配未修，R02-D02增长补证，普遍净收益/语义/长期效果待证 | [轮次记录](R05-deliverables-and-evidence.md)、[轮次记录](R07-speed-and-economy.md) |
| M21 | R14声明边界及局部权限/数据取证与独立复验完成；条件性D01扩展效果分类未修，模型抗注入/真实宿主/完整生命周期待后续；R10 主审及补做独立复验取证完成；R10-D01版本准入时序MAJOR/P2未修、FDP子类型保留，长期效果/政策待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R14-authorization-data-and-security.md)、[轮次记录](R10-long-term-evolution-and-growth.md) |
| M22 | R14声明边界及局部权限/数据取证与独立复验完成；条件性D01扩展效果分类未修，模型抗注入/真实宿主/完整生命周期待后续 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R05-deliverables-and-evidence.md)、[轮次记录](R14-authorization-data-and-security.md) |
| M23 | R14声明边界及局部权限/数据取证与独立复验完成；条件性D01扩展效果分类未修，模型抗注入/真实宿主/完整生命周期待后续 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R14-authorization-data-and-security.md) |
| M24 | R14声明边界及局部权限/数据取证与独立复验完成；条件性D01扩展效果分类未修，模型抗注入/真实宿主/完整生命周期待后续 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R14-authorization-data-and-security.md) |
| M25 | R03三段实际模型/自然改稿/关键问答及独立复验完成；D01预算边界调度建议未修，原生/真人/长期效果待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R03-user-experience-and-guidance.md) |
| M26 | pending formal review；R08 七对象八问及合成维护/新上下文迁移取证完成；真实学习收益、自然触发和人的进步待证；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限 | [轮次记录](R08-learning-and-feedback.md)、[轮次记录](R09-workflows-reuse-and-sharing.md) |
| M27 | pending formal review；R08 七对象八问及合成维护/新上下文迁移取证完成；真实学习收益、自然触发和人的进步待证；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限 | [轮次记录](R08-learning-and-feedback.md)、[轮次记录](R09-workflows-reuse-and-sharing.md) |
| M28 | R14声明边界及局部权限/数据取证与独立复验完成；条件性D01扩展效果分类未修，模型抗注入/真实宿主/完整生命周期待后续；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限 | [轮次记录](R14-authorization-data-and-security.md)、[轮次记录](R09-workflows-reuse-and-sharing.md) |
| M29 | pending formal review；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限；R10 主审及补做独立复验取证完成；R10-D01版本准入时序MAJOR/P2未修、FDP子类型保留，长期效果/政策待证 | [轮次记录](R09-workflows-reuse-and-sharing.md)、[轮次记录](R10-long-term-evolution-and-growth.md) |
| M30 | R07双臂短任务/多维规模与独立复验取证完成；D01 Unicode字面匹配未修，R02-D02增长补证，普遍净收益/语义/长期效果待证；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限 | [轮次记录](R07-speed-and-economy.md)、[轮次记录](R09-workflows-reuse-and-sharing.md) |
| M31 | R04 协议/恢复局部取证及独立复验完成；三组接口发现未修复，完整对象与 FDP 分型仍待后续处置；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R09-workflows-reuse-and-sharing.md) |
| M32 | pending formal review；R08 七对象八问及合成维护/新上下文迁移取证完成；真实学习收益、自然触发和人的进步待证；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限 | [轮次记录](R08-learning-and-feedback.md)、[轮次记录](R09-workflows-reuse-and-sharing.md) |
| M33 | R14声明边界及局部权限/数据取证与独立复验完成；条件性D01扩展效果分类未修，模型抗注入/真实宿主/完整生命周期待后续；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限 | [轮次记录](R14-authorization-data-and-security.md)、[轮次记录](R09-workflows-reuse-and-sharing.md) |
| M34 | R14声明边界及局部权限/数据取证与独立复验完成；条件性D01扩展效果分类未修，模型抗注入/真实宿主/完整生命周期待后续；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限 | [轮次记录](R06-deterministic-and-model-boundaries.md)、[轮次记录](R14-authorization-data-and-security.md)、[轮次记录](R09-workflows-reuse-and-sharing.md) |
| M35 | R07双臂短任务/多维规模与独立复验取证完成；D01 Unicode字面匹配未修，R02-D02增长补证，普遍净收益/语义/长期效果待证；R10 主审及补做独立复验取证完成；R10-D01版本准入时序MAJOR/P2未修、FDP子类型保留，长期效果/政策待证 | [轮次记录](R06-deterministic-and-model-boundaries.md)、[轮次记录](R07-speed-and-economy.md)、[轮次记录](R10-long-term-evolution-and-growth.md) |
| M36 | R12主审与独立取证完成；五布局同源/同版生命周期及Codex本机发现有限证据，D01及旧项开放，原生调用/跨平台/升级待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R03-user-experience-and-guidance.md)、[轮次记录](R12-distribution-and-host-use.md) |
| M37 | R12主审与独立取证完成；五布局同源/同版生命周期及Codex本机发现有限证据，D01及旧项开放，原生调用/跨平台/升级待证 | [轮次记录](R11-agent-skills-contracts.md)、[轮次记录](R12-distribution-and-host-use.md) |
| M38 | R12主审与独立取证完成；五布局同源/同版生命周期及Codex本机发现有限证据，D01及旧项开放，原生调用/跨平台/升级待证 | [轮次记录](R11-agent-skills-contracts.md)、[轮次记录](R12-distribution-and-host-use.md) |
| M39 | R16主审与独立取证完成；D02 MINOR/P2转换前导零未修；用户未裁定 | [轮次记录](R12-distribution-and-host-use.md)、[轮次记录](R16-documents-development-and-public-claims.md) |
| M40 | R12主审与独立取证完成；五布局同源/同版生命周期及Codex本机发现有限证据，D01及旧项开放，原生调用/跨平台/升级待证 | [轮次记录](R11-agent-skills-contracts.md)、[轮次记录](R12-distribution-and-host-use.md) |
| M41 | R03三段实际模型/自然改稿/关键问答及独立复验完成；D01预算边界调度建议未修，原生/真人/长期效果待证 | [轮次记录](R11-agent-skills-contracts.md)、[轮次记录](R03-user-experience-and-guidance.md) |
| M42 | R15综合主审与独立证据核对完成；13确认问题及2边界候选开放，整体/原生/真实人类/长期效果未验收 | [轮次记录](R16-documents-development-and-public-claims.md)、[轮次记录](R15-evidence-and-integration.md) |
| M43 | R15综合主审与独立证据核对完成；13确认问题及2边界候选开放，整体/原生/真实人类/长期效果未验收 | [轮次记录](R12-distribution-and-host-use.md)、[轮次记录](R16-documents-development-and-public-claims.md)、[轮次记录](R15-evidence-and-integration.md) |
| M44 | R16主审与独立取证完成；N01导航漂移已修；长期治理成本待证；用户未裁定 | [轮次记录](R10-long-term-evolution-and-growth.md)、[轮次记录](R16-documents-development-and-public-claims.md) |
| M45 | R15综合主审与独立证据核对完成；13确认问题及2边界候选开放，整体/原生/真实人类/长期效果未验收 | [轮次记录](R13-mattpocock-alignment.md)、[轮次记录](R16-documents-development-and-public-claims.md)、[轮次记录](R15-evidence-and-integration.md) |
| C01 | R03三段实际模型/自然改稿/关键问答及独立复验完成；D01预算边界调度建议未修，原生/真人/长期效果待证 | [轮次记录](R01-vision-and-claims.md)、[轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R05-deliverables-and-evidence.md)、[轮次记录](R03-user-experience-and-guidance.md) |
| C02 | R03三段实际模型/自然改稿/关键问答及独立复验完成；D01预算边界调度建议未修，原生/真人/长期效果待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R05-deliverables-and-evidence.md)、[轮次记录](R03-user-experience-and-guidance.md) |
| C03 | R03三段实际模型/自然改稿/关键问答及独立复验完成；D01预算边界调度建议未修，原生/真人/长期效果待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R14-authorization-data-and-security.md)、[轮次记录](R03-user-experience-and-guidance.md) |
| C04 | pending formal review；R08 七对象八问及合成维护/新上下文迁移取证完成；真实学习收益、自然触发和人的进步待证；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限；R10 主审及补做独立复验取证完成；R10-D01版本准入时序MAJOR/P2未修、FDP子类型保留，长期效果/政策待证 | [轮次记录](R08-learning-and-feedback.md)、[轮次记录](R09-workflows-reuse-and-sharing.md)、[轮次记录](R10-long-term-evolution-and-growth.md) |
| C05 | R12主审与独立取证完成；五布局同源/同版生命周期及Codex本机发现有限证据，D01及旧项开放，原生调用/跨平台/升级待证 | [轮次记录](R14-authorization-data-and-security.md)、[轮次记录](R09-workflows-reuse-and-sharing.md)、[轮次记录](R12-distribution-and-host-use.md) |
| C06 | R16主审与独立取证完成；公开CI有据；原生业务/跨版本升级待证；用户未裁定 | [轮次记录](R11-agent-skills-contracts.md)、[轮次记录](R12-distribution-and-host-use.md)、[轮次记录](R16-documents-development-and-public-claims.md) |
| C07 | R07双臂短任务/多维规模与独立复验取证完成；D01 Unicode字面匹配未修，R02-D02增长补证，普遍净收益/语义/长期效果待证；R10 主审及补做独立复验取证完成；R10-D01版本准入时序MAJOR/P2未修、FDP子类型保留，长期效果/政策待证 | [轮次记录](R02-core-architecture.md)、[轮次记录](R07-speed-and-economy.md)、[轮次记录](R10-long-term-evolution-and-growth.md) |
| C08 | R14声明边界及局部权限/数据取证与独立复验完成；条件性D01扩展效果分类未修，模型抗注入/真实宿主/完整生命周期待后续 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R06-deterministic-and-model-boundaries.md)、[轮次记录](R14-authorization-data-and-security.md) |
| U01 | R03三段实际模型/自然改稿/关键问答及独立复验完成；D01预算边界调度建议未修，原生/真人/长期效果待证；R08 七对象八问及合成维护/新上下文迁移取证完成；真实学习收益、自然触发和人的进步待证 | [轮次记录](R03-user-experience-and-guidance.md)、[轮次记录](R08-learning-and-feedback.md) |
| U02 | pending formal review；R08 七对象八问及合成维护/新上下文迁移取证完成；真实学习收益、自然触发和人的进步待证；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限 | [轮次记录](R08-learning-and-feedback.md)、[轮次记录](R09-workflows-reuse-and-sharing.md) |
| U03 | R07双臂短任务/多维规模与独立复验取证完成；D01 Unicode字面匹配未修，R02-D02增长补证，普遍净收益/语义/长期效果待证；R09 14对象八问、变化修订与全新接收试验取证完成；R07-D01未修，长期成熟/语义覆盖/完整分享证据仍有限 | [轮次记录](R07-speed-and-economy.md)、[轮次记录](R09-workflows-reuse-and-sharing.md) |
| U04 | R04 协议/恢复局部取证及独立复验完成；三组接口发现未修复，完整对象与 FDP 分型仍待后续处置；R10 主审及补做独立复验取证完成；R10-D01版本准入时序MAJOR/P2未修、FDP子类型保留，长期效果/政策待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R10-long-term-evolution-and-growth.md) |
| U05 | R15综合主审与独立证据核对完成；13确认问题及2边界候选开放，整体/原生/真实人类/长期效果未验收 | [轮次记录](R11-agent-skills-contracts.md)、[轮次记录](R12-distribution-and-host-use.md)、[轮次记录](R15-evidence-and-integration.md) |
| U06 | R15综合主审与独立证据核对完成；13确认问题及2边界候选开放，整体/原生/真实人类/长期效果未验收 | [轮次记录](R05-deliverables-and-evidence.md)、[轮次记录](R15-evidence-and-integration.md) |
| U07 | R03三段实际模型/自然改稿/关键问答及独立复验完成；D01预算边界调度建议未修，原生/真人/长期效果待证 | [轮次记录](R04-protocol-and-recovery.md)、[轮次记录](R14-authorization-data-and-security.md)、[轮次记录](R03-user-experience-and-guidance.md) |

## architecture

| 编号与对象 | 当前行为/边界 | 对标问题 | 复核面 / 权威源 | 定位 |
|---|---|---|---|---|
| A01 产品范围与低负担委托 | 用户提出任务，宿主负责组织和执行。 | 这种委托方式与初始化、人工介入需求是否一致？ | R01 R03 / S10 S11 S40 S42 S03 S48 S57 | [README.zh-CN.md](../../README.zh-CN.md#L1)、[SKILL.md](../../skills/astrofairy/SKILL.md#L1) |
| A02 协作宿主与本地运行器边界 | 模型与大部分任务工具由宿主提供，运行器控制自己的协议和操作。 | 成熟宿主原生能力、编排框架或当前分工的保证与成本如何比较？ | R02 R06 R14 / S01 S23 S24 S35 S43 S48 S42 S49 S56 | [architecture.md](../../docs/guides/architecture.md#L1)、[Workshop](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L35)、[Context](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L29) |
| A03 协议、判定、调用和存储分离 | 命令表、状态规则、调度组合与存储分属不同职责。 | 每一职责是否必要且可替换，是否有更成熟的组合或更小实现？ | R02 R04 R06 / S12 S19 S20 S37 S48 S42 S49 | [_contracts.py](../../skills/astrofairy/scripts/astrofairy/_contracts.py#L1)、[_kernel.py](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L1)、[_runtime.py](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L1)、[_store.py](../../skills/astrofairy/scripts/astrofairy/_store.py#L1) |
| A04 受控任务循环及完成语义 | 任务循环通过显式命令和状态决定下一步。 | 与成熟状态建模、持久工作流及宿主直接执行相比如何？ | R02 R04 R05 / S12 S21 S23 S37 S43 S44 S48 S42 | [State](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L11)、[Workshop.next](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L402)、[SKILL.md](../../skills/astrofairy/SKILL.md#L1) |
| A05 原始证据、事件与派生视图 | 保存内容字节与事件，重放后生成任务状态和回执。 | 事件化与内容寻址带来的保证、限制和成本是否值得？ | R02 R05 R14 / S13 S25 S26 S31 S42 S51 S52 S35 | [_store.py](../../skills/astrofairy/scripts/astrofairy/_store.py#L1)、[replay](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L63)、[Workshop.inspect](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L457) |
| A06 外置资产与任务化维护 | 经验通过维护任务和候选验证进入外部资产库。 | 与成熟记忆系统、工作流注册和版本库相比覆盖及学习效果如何？ | R02 R08 R09 / S03 S23 S39 S43 S42 S61 S62 S63 | [_library.py](../../skills/astrofairy/scripts/astrofairy/_library.py#L1)、[Workshop.learning_task](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L512)、[learning.md](../../skills/astrofairy/references/learning.md#L1) |
| A07 共享 skill 加可选分发适配 | 一份 skill 源目录带运行器，可经安装器、ZIP、可选 wheel 或插件清单分发。 | 共享契约及各宿主差异是否正确处理，维护成本如何？ | R02 R11 R12 / S01 S02 S03 S04 S32 S42 S65 S66 S67 | [0002-portable-standard-skill.md](../../docs/adr/0002-portable-standard-skill.md#L1)、[pyproject.toml](../../pyproject.toml#L1)、[package_skill.py](../../dev/package_skill.py#L1) |
| A08 稳定核心与外围增长 | 任务策略与经验外置，入口和部分核心文件有体积预算。 | 新增职责、替换能力和规模增长时，复杂度是否真正留在外围？ | R02 R07 R10 / S03 S11 S23 S39 S43 S42 S58 S59 | [governance.toml](../../governance.toml#L1)、[AGENTS.md](../../AGENTS.md#L1)、[0001-small-workshop.md](../../docs/adr/0001-small-workshop.md#L1) |
| A09 整体组合及端到端保证 | 以上分工组合为委托、产出、检查、交付和学习路径。 | 成熟组件的保证在连接处是否丢失，整体是否仍简洁、快速和可分析？ | R01 R02 R15 / S10 S11 S21 S23 S26 S43 S44 S48 S42 S70 S71 | [README.zh-CN.md](../../README.zh-CN.md#L1)、[architecture.md](../../docs/guides/architecture.md#L1) |

## mechanism

| 编号与对象 | 当前行为/边界 | 对标问题 | 复核面 / 权威源 | 定位 |
|---|---|---|---|---|
| M01 技能发现与调用入口 | 描述支持自动选择，用户也可显式提及。 | 触发精度、误触发及宿主支持如何验证？ | R03 R11 / S01 S03 S05 S06 S07 S08 S09 S57 | [SKILL.md](../../skills/astrofairy/SKILL.md#L1) |
| M02 条件资料与按需披露 | 首次读宿主协议，恢复与学习资料按条件打开。 | 指针是否既准确又节约上下文？ | R06 R07 R11 / S01 S03 S49 S59 | [SKILL.md](../../skills/astrofairy/SKILL.md#L1)、[host.md](../../skills/astrofairy/references/host.md#L1) |
| M03 环境就绪诊断 | doctor 检查解释器和目录条件，不建立数据存储。 | 检测是否覆盖真实前提，错误解释能否支持低负担恢复？ | R03 R12 / S04 S16 S17 S45 S66 | [_run](../../skills/astrofairy/scripts/astrofairy/_cli.py#L79) |
| M04 数据目录与任务工作区 | 数据目录持久保存，任务创建时准备专用工作区。 | 权限、平台、目录寿命和升级隔离是否成立？ | R04 R12 R14 / S16 S17 S66 | [Store.__init__](../../skills/astrofairy/scripts/astrofairy/_store.py#L17)、[Workshop._start](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L50) |
| M05 建任务、默认标准和附件快照 | 保存原始请求、目标、准则、预算和原始附件字节。 | 默认标准足够吗，材料保真与上下文供给是否一致？ | R03 R04 R05 / S18 S19 S26 S51 S52 S57 | [Workshop.start](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L70) |
| M06 严格 JSON 与命令字段契约 | 拒绝重复键及未知字段，schema 从命令表生成。 | 与成熟模式校验相比接受域、错误和维护成本如何？ | R04 R06 / S18 S19 S20 S47 S49 | [_contracts.py](../../skills/astrofairy/scripts/astrofairy/_contracts.py#L1) |
| M07 要求来源与修订 | 区分 user/policy/derived，修改明确要求需关联后续用户输入。 | 来源归属、修订授权与真实意图是否一致？ | R04 R05 / S19 S23 S26 S43 | [Workshop.submit](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L271)、[criteria_value](../../skills/astrofairy/scripts/astrofairy/_contracts.py#L96) |
| M08 关键提问与输入转发 | 提问需推荐答案，最多三次，回答进入事件并增加修订。 | 提问是否必要、回答是否正确进入后续目标与验收？ | R03 R04 / S03 S40 S57 | [admit_question](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L140)、[Workshop.submit](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L271) |
| M09 模型工作请求与报告 | 模型请求保留目的及引用，报告需对应待处理调用。 | 是否准确绑定输入、输出和执行者，协议负担是否值得？ | R04 R05 R06 / S23 S26 S43 S48 S49 S51 S52 | [Workshop._request](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L110)、[Workshop._known_outputs](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L107)、[Workshop.submit](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L271) |
| M10 工具注册、字段发现与能力目录 | 工具声明 effect 和参数；目录按能力名子串检索。 | 成熟工具接口与当前注册方式的覆盖、发现成本如何？ | R02 R06 / S01 S19 S23 S43 S48 S49 | [Capability](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L51)、[builtins](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L166)、[Workshop.catalog](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L440) |
| M11 动作准入、预算与重复防护 | 先检查 scope/budget，同类未决操作阻止盲目重试。 | 与幂等键、重试和执行租约等成熟机制的责任边界如何？ | R04 R06 R14 / S12 S21 S22 S44 S49 | [admit_call](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L99)、[require_open](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L112)、[State.budget_left](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L59) |
| M12 调用前留痕与执行后观测 | 调用先落事件，异常按作用类型记 failed 或 unknown。 | 副作用与日志之间的窗口如何处理；不确定性能否恢复？ | R04 R05 R14 / S21 S22 S24 S26 S44 S48 S53 | [Workshop.invoke](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L133) |
| M13 成果登记与版本绑定 | 成果需来自本任务已观测输出，每次登记形成新目标。 | 是否能定位真实最终交付物且使旧检查失效？ | R04 R05 / S26 S31 S53 | [Workshop.submit](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L271)、[State.artifact](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L27) |
| M14 文件捕获与类型标记 | 按字节捕获工作区文件，推断或接受类型。 | 类型、实际格式、读取预算和来源语义是否分开？ | R05 R06 / S17 S26 S50 S51 S52 | [_capture](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L80) |
| M15 内容访问与分段读取 | 按当前任务可访问引用读取，文本有分段和长度限制。 | 权限、编码、二进制处理及大材料读取如何比较？ | R06 R07 R14 / S17 S18 S58 | [Context.content](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L40)、[_read](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L101) |
| M16 机械检查器 | 内置 semantic 之外的 nonempty/json/contains 检查。 | 能检什么、不能检什么，成熟格式工具如何接入？ | R05 R06 / S18 S19 S20 S49 S53 | [check_content](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L137)、[_check](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L156)、[Workshop.check](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L221) |
| M17 语义审查、替代链和冲突 | 审查绑定当前修订与成果；新通过不自动覆盖旧失败。 | 证据与判断能否验证，冲突和替代是否真实？ | R04 R05 / S23 S26 S43 S48 S53 | [Workshop._review](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L197)、[admit_review](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L117)、[State.active_reviews](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L30)、[State.issues](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L42) |
| M18 关闭门与结果分类 | 完整交付需必要检查通过、无待答和未决调用；部分交付需成果。 | 结果分类是否准确，是否有错误完成或无法退出？ | R04 R05 / S12 S21 S23 S43 S44 S53 | [State.complete](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L51)、[admit_close](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L146) |
| M19 下一步工作包与调度 | 由状态返回 produce/review/repair/resolve 等行动与上下文。 | 调度优先级、包大小与宿主实际推进是否协调？ | R03 R04 R07 / S12 S23 S37 S43 S57 S58 S39 | [Workshop.next](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L402) |
| M20 回执与交付导出 | 完整视图写入 receipt，回包仅返回路径和简要状态。 | 审核者能否还原内容组织；成果组合与后续更新如何？ | R05 R07 / S25 S26 S27 S51 S52 S58 | [Workshop.inspect](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L457)、[Workshop.deliver](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L477) |
| M21 SQLite 存储与事务 | 标准库 SQLite，显式写事务，存储版本不支持时拒绝。 | 实际事务与并发、崩溃、备份、迁移前提是否足够？ | R04 R10 R14 / S13 S14 S16 S64 | [Store.__init__](../../skills/astrofairy/scripts/astrofairy/_store.py#L17)、[Store.close](../../skills/astrofairy/scripts/astrofairy/_store.py#L49)、[Store.transaction](../../skills/astrofairy/scripts/astrofairy/_store.py#L53)、[Store.tasks](../../skills/astrofairy/scripts/astrofairy/_store.py#L125) |
| M22 事件链、序号与重放 | 事件按序追加并校验哈希链，当前状态由事件重建。 | 与成熟事件溯源相比一致性、篡改检测和成本如何？ | R04 R05 R14 / S12 S25 S26 S51 S52 | [Store.events](../../skills/astrofairy/scripts/astrofairy/_store.py#L78)、[Store.append](../../skills/astrofairy/scripts/astrofairy/_store.py#L97)、[replay](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L63)、[Workshop.state](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L47)、[Workshop._append](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L104) |
| M23 内容寻址与字节完整性 | 字节内容以 SHA256 引用保存，读取时重算。 | 规范化、重复、完整性、真实性与保留策略如何界定？ | R04 R14 / S18 S31 S47 | [Store.put](../../skills/astrofairy/scripts/astrofairy/_store.py#L62)、[Store.get](../../skills/astrofairy/scripts/astrofairy/_store.py#L69)、[canonical](../../skills/astrofairy/scripts/astrofairy/_contracts.py#L34)、[digest](../../skills/astrofairy/scripts/astrofairy/_contracts.py#L43) |
| M24 路径约束、原子写与文件权限 | 约束普通路径越界，用临时文件同步后替换，POSIX 私有权限。 | 成熟文件操作实践、并发、竞态及持久性保证如何？ | R04 R14 / S17 S35 S54 S55 | [Context.path](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L33)、[atomic_write](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L58)、[_write](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L71) |
| M25 重开、未决动作与迟到结果 | 重开同一数据目录可继续；未决工具动作无通用自动对账。 | 成熟恢复方案相比缺口、人工负担和可接受边界是什么？ | R03 R04 / S21 S22 S24 S44 S57 | [replay](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L63)、[Workshop.submit](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L271)、[review.md](../../skills/astrofairy/references/review.md#L1) |
| M26 资产提案与工作流结构 | 资产有种类、范围、摘要、标签和证据；工作流步骤需完成条件。 | 契约是否足以执行复用，是否存在过拟合或内容混杂？ | R08 R09 / S03 S19 S39 S61 S62 | [Library.propose](../../skills/astrofairy/scripts/astrofairy/_library.py#L76) |
| M27 候选验证任务与固定策略 | 精确候选作为验证成果，固定 package-json 与 asset-fitness 标准。 | 机械和语义验证的充分性、独立性和成本如何？ | R08 R09 / S03 S19 S23 S43 S61 S62 | [validation_criteria](../../skills/astrofairy/scripts/astrofairy/_library.py#L24)、[Workshop.validation_task](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L500) |
| M28 采用与基准竞争 | 采用需精确包的完整验证，头版本变化时拒绝陈旧基准。 | 并发采用、身份、信任及成熟度判断是否可靠？ | R09 R14 / S13 S23 S31 S43 | [Library.adopt](../../skills/astrofairy/scripts/astrofairy/_library.py#L137) |
| M29 资产状态、版本、退役与回退 | candidate/trial/stable/retired，历史不覆盖，退役后可显露旧活跃版本。 | 状态含义是否由证据支撑，版本选择和淘汰如何比较？ | R09 R10 / S23 S31 S33 S39 S43 S46 S64 | [Library.status](../../skills/astrofairy/scripts/astrofairy/_library.py#L52)、[Library.head](../../skills/astrofairy/scripts/astrofairy/_library.py#L60)、[Library.get](../../skills/astrofairy/scripts/astrofairy/_library.py#L70)、[Library._event](../../skills/astrofairy/scripts/astrofairy/_library.py#L130)、[Library.retire](../../skills/astrofairy/scripts/astrofairy/_library.py#L158) |
| M30 资产检索与排序 | 对名称、摘要、标签做词项子串评分，限定范围、数量和活跃头版本。 | 与全文、语义、混合及重排方案如何比相关性、漏检、延迟与成本？ | R07 R09 / S15 S28 S29 S30 S38 S58 S60 | [Library.search](../../skills/astrofairy/scripts/astrofairy/_library.py#L163)、[_search](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L112) |
| M31 资产读取与精确版本钉选 | 读取已采用资产记录使用引用，长内容可分段读取。 | 检索结果到实际执行是否一致，旧版本与退役如何处理？ | R04 R09 / S23 S26 S31 S43 S63 | [_asset](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L120)、[Workshop.invoke](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L133) |
| M32 反馈与独立维护任务 | 交付后记录反馈，按需以表现快照创建维护任务，允许不变。 | 回流触发、证据支持和实际后续收益如何评价？ | R08 R09 / S03 S23 S39 S43 S61 | [Workshop.learning_task](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L512)、[Workshop.submit](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L271) |
| M33 资产分享与导入验证 | 导出 JSON 包；核验摘要后转本地候选，保留发送者声明的证据说明。 | 可迁移依赖、来源可信度、隐私和本地复验是否完整？ | R09 R14 / S18 S26 S31 S36 S35 S63 | [Library.export](../../skills/astrofairy/scripts/astrofairy/_library.py#L183)、[Library.import_bundle](../../skills/astrofairy/scripts/astrofairy/_library.py#L186) |
| M34 被动工具说明与内容信任 | tool-spec 是资料，导入不安装代码；约束与事实需要不同用途。 | 资料、执行能力和授权的分界能否保持？ | R06 R09 R14 / S01 S03 S35 S49 | [learning.md](../../skills/astrofairy/references/learning.md#L1)、[Library.propose](../../skills/astrofairy/scripts/astrofairy/_library.py#L76) |
| M35 资源限额与增长预算 | 限制 blob、问题、调用和查询；限定入口及四个文件的体积。 | 预算是否作用于真实成本，是否有移出预算文件的规避？ | R06 R07 R10 / S11 S23 S27 S43 S58 S59 | [_contracts.py](../../skills/astrofairy/scripts/astrofairy/_contracts.py#L1)、[governance.toml](../../governance.toml#L1)、[structural_checks](../../dev/check.py#L38) |
| M36 CLI 错误、状态与诊断接口 | 统一 JSON 输出，失败和未知返回非零；schema/doctor 不开存储。 | 错误语义是否有遗漏，调用者能否可靠判断和恢复？ | R03 R04 R12 / S18 S19 S20 S45 S66 | [_cli.py](../../skills/astrofairy/scripts/astrofairy/_cli.py#L1)、[_errors.py](../../skills/astrofairy/scripts/astrofairy/_errors.py#L1)、[__main__.py](../../skills/astrofairy/scripts/astrofairy/__main__.py#L1) |
| M37 自包含启动与可选 Python 包 | launcher 仅定位自己的 scripts；wheel 从同源代码构建。 | 脱离仓库、site-packages 和平台默认路径后是否可运行？ | R11 R12 / S01 S04 S32 S45 | [fairy.py](../../skills/astrofairy/scripts/fairy.py#L1)、[pyproject.toml](../../pyproject.toml#L1)、[_version.py](../../skills/astrofairy/scripts/astrofairy/_version.py#L1)、[__init__.py](../../skills/astrofairy/scripts/astrofairy/__init__.py#L1) |
| M38 便携 ZIP 内容过滤 | 标准目录打包，排除测试、缓存与构建元数据，无私有安装清单。 | 源、复制安装、ZIP 内容及许可是否一致？ | R11 R12 / S01 S04 S36 | [package_skill.py](../../dev/package_skill.py#L1) |
| M39 派生版本、许可与包元数据同步 | 由包元数据及版本生成插件文件并同步许可。 | 版本转换、错误输入和消费者漂移如何验证？ | R12 R16 / S32 S33 S36 S46 | [sync_metadata.py](../../dev/sync_metadata.py#L1)、[MANIFEST.in](../../MANIFEST.in#L1)、[LICENSE](../../LICENSE#L1)、[LICENSE](../../skills/astrofairy/LICENSE#L1) |
| M40 原生插件与市场清单 | 提供可选 plugin/marketplace 清单，未宣称已在市场上架。 | 各消费者实际解析、缓存和升级如何工作？ | R11 R12 / S03 S05 S06 S08 | [plugin.json](../../.claude-plugin/plugin.json#L1)、[marketplace.json](../../.claude-plugin/marketplace.json#L1) |
| M41 可选 UI 元数据 | 提供展示名、简述及默认提示，未禁止隐式调用。 | 字段和发现行为是否符合对应宿主实际版本？ | R03 R11 / S01 S06 | [openai.yaml](../../skills/astrofairy/agents/openai.yaml#L1) |
| M42 测试面、类型与规范检查 | 统一入口执行归属测试、Ruff、mypy、文档引用和预算检查。 | 检查是否覆盖真实义务，是否有镜像测试或未执行表面？ | R15 R16 / S02 S04 S41 S68 S70 S71 | [check.py](../../dev/check.py#L1)、[check_installation.py](../../dev/check_installation.py#L1)、[test_metadata.py](../../dev/tests/test_metadata.py#L1)、[test_package_skill.py](../../dev/tests/test_package_skill.py#L1)、[tests](../../skills/astrofairy/scripts/astrofairy/tests#L1)、[requirements-dev.lock](../../requirements-dev.lock#L1) |
| M43 提交门与 CI 构建 | 本地 pre-commit 运行检查，CI 检查并构建 wheel/sdist/ZIP。 | 本地与远程执行体、覆盖通道、权限及版本锚是否一致？ | R12 R15 R16 / S34 S41 S69 | [pre-commit](../../.githooks/pre-commit#L1)、[check.yml](../../.github/workflows/check.yml#L1) |
| M44 文档、单源组织与公开边界 | 双语 README、设计决策、运行指南和忽略目录；公开用语专业。 | 声明与行为能否双向追踪，治理和资料增长是否适度？ | R10 R16 / S03 S32 S36 S41 | [AGENTS.md](../../AGENTS.md#L1)、[README.md](../../README.md#L1)、[README.zh-CN.md](../../README.zh-CN.md#L1)、[.gitignore](../../.gitignore#L1)、[.gitattributes](../../.gitattributes#L1)、[docs](../../docs#L1) |
| M45 研究来源与验证声明 | 首版研究记录固定 Matt 来源及本地试用，并区分未测项。 | 原始证据与研究结论是否可重建，权威与效果是否被混淆？ | R13 R15 R16 / S01 S03 S26 S70 S71 | [initial-validation.md](../../docs/reports/initial-validation.md#L1)、[mattpocock-alignment.md](../../docs/reports/mattpocock-alignment.md#L1) |

## composition

| 编号与对象 | 当前行为/边界 | 对标问题 | 复核面 / 权威源 | 定位 |
|---|---|---|---|---|
| C01 首次任务到交付 | 从提出任务到实际成果及回执的组合路径。 | 初始化、准则、动作、检查与交付间是否存在缺口？ | R01 R03 R04 R05 / S01 S23 S26 S40 S43 S48 S51 S52 S57 | [SKILL.md](../../skills/astrofairy/SKILL.md#L1)、[_runtime.py](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L1) |
| C02 要求变化到重新验收 | 转发用户变化并修订任务，旧审查按版本失效。 | 改变要求与改变成果的两种版本是否协同？ | R03 R04 R05 / S12 S23 S26 S43 S48 S53 S57 | [Workshop.submit](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L271)、[_kernel.py](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L1) |
| C03 中断到恢复与迟到结果 | 重放、未决识别、结果核对及回执更新的组合路径。 | 全链是否保持真实，用户需要多少排错能力？ | R03 R04 R14 / S21 S22 S24 S44 S57 | [_store.py](../../skills/astrofairy/scripts/astrofairy/_store.py#L1)、[_kernel.py](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L1)、[_runtime.py](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L1) |
| C04 经验到下一次任务收益 | 反馈、维护、候选、验证、采用、检索和实际复用。 | 各连接处是否可达、有效并避免旧事实污染？ | R08 R09 R10 / S03 S23 S39 S43 S61 S62 | [_library.py](../../skills/astrofairy/scripts/astrofairy/_library.py#L1)、[Workshop.learning_task](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L512) |
| C05 发送到接收端独立使用 | 导出、传输、导入、当地验证与后续使用。 | 缺发送端数据库、私有文件或工具时能否成立？ | R09 R12 R14 / S18 S26 S36 S35 S63 | [Library.export](../../skills/astrofairy/scripts/astrofairy/_library.py#L183)、[Library.import_bundle](../../skills/astrofairy/scripts/astrofairy/_library.py#L186) |
| C06 公开源到多宿主安装与升级 | 仓库、安装器、目录、脚本、宿主及独立数据目录。 | 安装、加载、行为及更新保留能否逐层对应？ | R11 R12 R16 / S01 S03 S04 S32 S65 S66 S67 | [README.md](../../README.md#L1)、[check_installation.py](../../dev/check_installation.py#L1)、[package_skill.py](../../dev/package_skill.py#L1) |
| C07 规模增长及外部能力替换 | 任务、版本、资产和工具增长下的整体变化。 | 成本曲线、检索质量与核心变更量如何？ | R02 R07 R10 / S11 S23 S27 S39 S43 S58 S15 S64 | [governance.toml](../../governance.toml#L1)、[_runtime.py](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L1)、[_library.py](../../skills/astrofairy/scripts/astrofairy/_library.py#L1)、[_store.py](../../skills/astrofairy/scripts/astrofairy/_store.py#L1) |
| C08 权限与副作用贯穿路径 | 任务 effect、运行器动作与宿主权限共同约束工作。 | 只读、内部登记、实际写入和对外发布是否被正确区分？ | R04 R06 R14 / S17 S22 S35 S44 S49 S56 | [host.md](../../skills/astrofairy/references/host.md#L1)、[_kernel.py](../../skills/astrofairy/scripts/astrofairy/_kernel.py#L1)、[_capabilities.py](../../skills/astrofairy/scripts/astrofairy/_capabilities.py#L1) |

## requirement probe

| 编号与对象 | 当前行为/边界 | 对标问题 | 复核面 / 权威源 | 定位 |
|---|---|---|---|---|
| U01 使用者思路进步的证据路径 | 愿景要求；当前没有已验证的长期行为证据。 | 由哪些交互和记录证明用户逐渐更会表达与判断？ | R03 R08 / S03 S39 S40 S57 S61 | [SKILL.md](../../skills/astrofairy/SKILL.md#L1) |
| U02 重复任务成熟与回流触发 | 宿主可决定维护与采用；自动收敛程度待证。 | 是否需要用户主动组织维护，何种证据可认定成熟？ | R08 R09 / S03 S23 S39 S43 S61 S62 | [Workshop.learning_task](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L512)、[_library.py](../../skills/astrofairy/scripts/astrofairy/_library.py#L1) |
| U03 检索需求的语义覆盖 | 当前是词项匹配；语义及跨措辞适用性待证。 | 现有实现满足哪些实际任务，需要哪些成熟检索能力？ | R07 R09 / S15 S28 S29 S30 S38 S60 | [Library.search](../../skills/astrofairy/scripts/astrofairy/_library.py#L163) |
| U04 长期数据保留与版本演化 | 初版拒绝未知存储版本；长期清理、迁移及备份策略待复核。 | 在声明生命周期下如何保留、清理、升级并恢复？ | R04 R10 / S13 S23 S25 S31 S33 S43 S46 S64 | [_store.py](../../skills/astrofairy/scripts/astrofairy/_store.py#L1)、[_library.py](../../skills/astrofairy/scripts/astrofairy/_library.py#L1) |
| U05 原生宿主及平台支持证据 | 已有安装与隔离运行，原生宿主的行为矩阵未完成。 | 每类宿主、系统、调用方式和权限环境需要什么证据？ | R11 R12 R15 / S05 S06 S07 S08 S09 S65 S66 S67 S70 | [README.md](../../README.md#L1)、[check_installation.py](../../dev/check_installation.py#L1) |
| U06 审核者理解组织依据的能力 | 已有目标、假设、调用及审查依据，实际重建成本待证。 | 能否从成果和回执看懂组织取舍及逐项事实来源？ | R05 R15 / S10 S26 S40 S51 S52 S70 | [Workshop.inspect](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L457)、[Workshop.deliver](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L477) |
| U07 未知效果恢复的操作闭环 | 当前阻断不确定结果的完整关闭；任意外部动作无自动核对。 | 恢复责任、工具支持和人工负担是否符合可用目标？ | R03 R04 R14 / S21 S22 S24 S44 S57 | [Workshop.next](../../skills/astrofairy/scripts/astrofairy/_runtime.py#L402)、[review.md](../../skills/astrofairy/references/review.md#L1) |

## 文件覆盖索引

| 初版文件 | 负责机制 | 符号数 |
|---|---|---|
| .claude-plugin/marketplace.json | M40 | 0 |
| .claude-plugin/plugin.json | M40 | 0 |
| .gitattributes | M44 | 0 |
| .githooks/pre-commit | M43 | 0 |
| .github/workflows/check.yml | M43 | 0 |
| .gitignore | M44 | 0 |
| AGENTS.md | M44 | 0 |
| LICENSE | M39 | 0 |
| MANIFEST.in | M39 | 0 |
| README.md | M44 | 0 |
| README.zh-CN.md | M44 | 0 |
| dev/__init__.py | M42 | 0 |
| dev/check.py | M35 M42 | 3 |
| dev/check_installation.py | M42 | 4 |
| dev/package_skill.py | M38 | 2 |
| dev/sync_metadata.py | M39 | 3 |
| dev/tests/__init__.py | M42 | 0 |
| dev/tests/test_metadata.py | M42 | 2 |
| dev/tests/test_package_skill.py | M42 | 3 |
| docs/adr/0001-small-workshop.md | M44 | 0 |
| docs/adr/0002-portable-standard-skill.md | M44 | 0 |
| docs/guides/architecture.md | M44 | 0 |
| docs/guides/operation.md | M44 | 0 |
| docs/reports/initial-validation.md | M44 M45 | 0 |
| docs/reports/mattpocock-alignment.md | M44 M45 | 0 |
| governance.toml | M35 | 0 |
| pyproject.toml | M37 | 0 |
| requirements-dev.lock | M42 | 0 |
| skills/astrofairy/LICENSE | M39 | 0 |
| skills/astrofairy/SKILL.md | M01 M02 | 0 |
| skills/astrofairy/agents/openai.yaml | M41 | 0 |
| skills/astrofairy/references/host.md | M02 | 0 |
| skills/astrofairy/references/learning.md | M34 | 0 |
| skills/astrofairy/references/review.md | M25 | 0 |
| skills/astrofairy/scripts/astrofairy/__init__.py | M37 | 0 |
| skills/astrofairy/scripts/astrofairy/__main__.py | M36 | 0 |
| skills/astrofairy/scripts/astrofairy/_capabilities.py | M10 M14 M15 M16 M24 M30 M31 | 13 |
| skills/astrofairy/scripts/astrofairy/_cli.py | M03 M36 | 4 |
| skills/astrofairy/scripts/astrofairy/_contracts.py | M06 M07 M23 M35 | 12 |
| skills/astrofairy/scripts/astrofairy/_errors.py | M36 | 3 |
| skills/astrofairy/scripts/astrofairy/_kernel.py | M08 M11 M13 M17 M18 M22 M25 | 12 |
| skills/astrofairy/scripts/astrofairy/_library.py | M26 M27 M28 M29 M30 M33 M34 | 13 |
| skills/astrofairy/scripts/astrofairy/_runtime.py | M04 M05 M07 M08 M09 M10 M12 M13 M16 M17 M19 M20 M22 M25 M27 M31 M32 | 20 |
| skills/astrofairy/scripts/astrofairy/_store.py | M04 M21 M22 M23 | 9 |
| skills/astrofairy/scripts/astrofairy/_version.py | M37 | 0 |
| skills/astrofairy/scripts/astrofairy/tests/__init__.py | M42 | 0 |
| skills/astrofairy/scripts/astrofairy/tests/_support.py | M42 | 6 |
| skills/astrofairy/scripts/astrofairy/tests/test_cli.py | M42 | 8 |
| skills/astrofairy/scripts/astrofairy/tests/test_library.py | M42 | 14 |
| skills/astrofairy/scripts/astrofairy/tests/test_workshop.py | M42 | 29 |
| skills/astrofairy/scripts/fairy.py | M37 | 0 |

以上是登记范围。不代表已完成审查。实际读取、判断、反例和证据见[轮次索引](INDEX.md)。
各对象状态与证据引用以 JSON 为准。未裁定对象仍承担完整对标义务。
