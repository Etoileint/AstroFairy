# 独立验收返工记录（RW1–RW8）

日期：2026-11-03。输入来源：[独立验收](../../optimization/2026-11-acceptance/README.md)与
[10 项发现](../../optimization/2026-11-acceptance/findings.json)；返工拆分见
[rework.md](../../optimization/2026-11-acceptance/rework.md)。未提交、推送或发布。

## 已修复

- **RW1/SPEC-01**：`prepare-delivery` 在任何捕获前记录完整成员计划与角色，逐成员记录进度；
  `next` 在计划不完整时返回 `prepare_delivery` 和完整计划；只传 remaining 的续接仍恢复全计划；
  计划变更明确拒绝；`complete` 要求计划成员、角色和媒体类型都在当前快照。
- **RW2/SPEC-02/STD-01**：交付显式写 `BagIt-Version: 1.0` 并重生成标签清单；同序号既有 bag
  除 BagIt 自校验外，还核对任务/revision/seq、快照、回执、成员集合、字节摘要和账本内容；
  自洽重封或换放其他任务 bag 被拒绝。BagIt 库调用由进程级锁串行化以覆盖其 cwd 修改。
- **RW3/SPEC-03**：复用只在无待处置失败且作用域为 `content` 时成立；A→B→A 产生真实新检查并
  通过 `replaces` 处置旧失败，不删除历史。
- **RW4/ROOT-02/03**：`FastEmbedder.prepare()` 用固定 revision 下载并 SHA256 校验声明文件，
  损坏/半下载时显式重试；普通 `_load` 使用固定目录和 `local_files_only=True`；tokenizer 从
  同一固定目录取得；空库不准备模型。
- **RW5/ROOT-01**：全文与向量各自按资产去重/保留排名后再融合；受控 FTS[A,B]、vector[B,C,D,A]
  的 2:1 结果 B 在 A 前。
- **RW6/ROOT-04**：资产可选结构化 applicability/dependencies/invalidation，进入包与检索投影；
  交付后 `next` 提供 maintain/defer/no_change，defer 成为可发现 todo；任务约定可固定 adopted
  governance refs，完成前必须 `asset.read` 固定，未知适用性仍由 host 判断。
- **RW7/STD-02/03**：大小写折叠统一用于完整路径及每级目录前缀冲突；新增技能内
  `references/operation.md`，`package_skill.py` 校验包内全部相对链接，分发件自包含恢复资料。
- **RW8**：操作/架构/技能/宿主参考文档按实际行为更新；重建 wheel/ZIP 与安装、恢复、真实模型
  证据；新回交目录不覆盖旧 return。

## 验证与限界

新增 10 项返工合同测试，覆盖全计划续接、计划变更拒绝、BagIt 1.0/权威绑定、大小写前缀冲突、
失败重评、两路融合、结构化字段/学习决定、固定模型准备/离线消费、治理固定和自包含分发。
真实 E5 留出复测：混合 Recall@10 1.000、nDCG@5 0.9671（纯全文 0.975/0.9658）；正文独有
nDCG 0.9262 对仅元数据 0.4861。具体运行/资源身份见新回交的 metrics/runs。

仍保持限界：真实宿主遵循率、Windows/macOS、原生插件宿主、冷模型首次下载和长期真人/团队收益
未取得；没有用测试或结构检查代替这些证据。上一轮 return 目录保持只读，未覆盖。
