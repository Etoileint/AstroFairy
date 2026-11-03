# 优化回交最终技术复验

**结论：本轮技术验收通过。原10项发现及 REG-01 已关闭，无剩余已确认的技术阻断。**
维护者保留最终产品接受与发布决定；本轮未提交、推送、打标签或发布。
这是一轮有范围的复验，不将外部宿主、平台或长期效果写成全部验证通过。

依据为[正式方案](../../2026-11-plan/design.md)、[实施验收范围](../../2026-11-plan/execution.md)
及[上一轮剩余门](../recheck-2026-11-03/remaining-work.md)。旧报告保留当时结论，
本报告接续其状态；逐项结果见 [findings.json](findings.json)。

## 接收身份与本会话收尾

回交位于 `.evaluation/optimization-implementation/recheck-fixes-2026-11-03/return/`：
320 份源码、96 份证据及 ZIP 已核对。源码清单 SHA256 为
`736b0fe3a14772bbe0c2c816b60d332e0ea728934ab96c721f468e78f8b0a612`，
源码 ZIP SHA256 为 `c04d5efe91ed873c246ef6daf219b099773dc9082786e2c37e9dcce352594684`。
前序输入为 `60efe30821a0294b285d9fe93c4ed8f1e90c4a2d1d272fdc3e159d63ee2a4192`。
基准是包含未跟踪文件的回交工作树，不是空的 HEAD 差异；旧回交包保持原样。

收到的版本先通过 192 项运行测试收集、19 项开发测试及完整规范检查，但独立检查仍发现
maintain 先提交子任务、后记录源决定的窗口。定向拒绝后者会留下未关联子任务，重试会再建一个。
原会话按既有收尾授权作根因修复，再交独立主体复验：

- 源快照、子任务、源决定及链接统一在同一主数据库事务；Python 原生入口与命令共用该路径。
  快照保留决定前序号，响应返回已提交决定的准确序号。失败回滚，旧序号重试拒绝。
- 相关恢复测试揭示新增事件未进入备份审计。移除恢复端重复事件白名单，以 replay 识别事件并
  拒绝未知类型；恢复验证维护子任务与源文档的任务/序号链接，以及已捕获交付进度的引用和长度。
  未捕获成员仍为待办，不伪装成已有文件。没有新增兼容分支、迁移或业务专用流程。
- 源码分发物缺少锁引用的本地 wheel、上游 sdist 与检索依赖输入文件。按标准 MANIFEST
  扩展通用资源类型，解压源码包后核验上游原件/锁，再重建逐成员字节一致的技能 ZIP；
  回归测试先独立重现缺件，再确认修复。

主数据库回滚可能在独立文档库留下未引用派生块；这不等于跨文件系统原子事务或自动清理。
源交付内容和旧 Bag 不变，新增学习事实推进源序号并生成新回执。

收尾后的源码、差异、分发物和证据单独登记在
`.evaluation/optimization-acceptance/20261103-final/` 的 `post-tail-source-manifest.json`、
`post-tail-source.zip`、`root-tail.diff` 和 `final-attestation.json`，不会覆盖执行方回交身份。

## Standards

规范轴原3项均关闭，本轮收尾无新增未关规范发现：实际 BagIt 1.0 及回执一致，可移植路径
覆盖大小写/目录前缀冲突，独立技能包的运行与恢复资料完整。原会话按 review 技能组织独立
检查；检查者不参与被检查部分的实现。本轮根因收尾另经只读复验。

更新后的 wheel 与便携 ZIP 重建并核对包内源码字节；在仓库外的全新目录使用 Python `-I`
运行学习决定、待办、审计、备份、校验与恢复。wheel 经标准 pip 安装到全新 target，沿用已
准备的运行依赖；本轮没有冒称重新建立了全部依赖环境或测过所有原生宿主。

## Spec

方案轴原3项均关闭，无新增未关方案发现。完整交付计划在中断与恢复后仍保留成员和角色；
失败检查可以合法重评，旧历史不被覆盖。正确既有 Bag 可幂等复用；38 组内部合法重封反例
被拒，包括额外/缺失/替换/改名成员、删除回执27种字段、篡改约定/结果/审查及换放其他任务。
权威存储字节损坏亦拒绝。校验以真实账本投影为依据，不只相信包自身的清单。

REG-01 关闭：8/32/128 MiB 既有 Bag 校验的 Python 分配峰值均约 2.06 MiB，不随文件大小
双份增长。该测量是 tracemalloc 分配量，不是操作系统 RSS 或所有资源上界。

检索/学习原4项也均关闭：

- RRF 保留每一路的资产贡献；已关闭项沿相关测试复验，未机械重复所有历史实验。
- 模型准备直接调用锁定依赖的公开 `huggingface_hub.snapshot_download`，明确请求固定 revision。
  独立受控传输覆盖空缓存、半下载、同长度损坏、有效缓存、失败重试与错误目录；生产 SHA 门
  核消费文件，普通查询缺缓存时不调用下载或模型构造器。真实已缓存 E5 另行冒烟通过。
- 治理候选从权威采用头按范围取得，10 个必需约束不受默认 top-8 截断；排除与未知适用性
  有明确表示。旧任务保留旧引用，新任务使用新版；字段 profile 改变会拒绝旧投影，重建可用。
- maintain/defer/no_change 与跨任务待办贯通；四种原生/命令及源/子写失败组合均回滚，
  两连接竞争同一 expected_seq 一成功一冲突、仅一个子任务。带学习记录和中断交付的状态
  audit→backup→verify→restore 后一致；仅补缺失 b 即交回捕获的 a 与新 b。悬空子任务链接拒绝。

独立复验还确认连续学习决定产生正确新回执，所有旧 Bag 的逐文件 SHA256 不变。

## 最终验证与证据

- `.venv/bin/python -B dev/check.py`：195 项运行测试收集，194 通过、1 项按默认配置跳过；
  20 项开发测试通过。类型、风格、技能格式、元数据、锁、权威快照和文档引用检查通过。
- 单独启用真实 E5 缓存冒烟：1 项通过；完整冷网络下载时长和失败环境不在本轮实测范围。
- 新增4项拥有者回归测试；独立失败注入、并发、恢复、治理与交付接续探针通过。

本机证据目录为 `.evaluation/optimization-acceptance/20261103-final/`。主要文件：
`receipt.json`、`canonical-check.log`、`post-tail-canonical.log`、`final-canonical.log`、
`delivery-independent.json`、
`model-prepare-independent.json`、`real-e5-independent.log`、`learning_atomic_recovery_probe.json`、
`governance_postfix_probe.json`、`tail-standards-delivery-review.json`、`distribution-post-tail.json`、`sdist-regression-red.log`、
`sdist-regression-green.log`、`sdist-independent/review.json`。
最初学习失败探针与引用旧测试方法名造成的 loader error 日志保留；改后独立证据及
`learning_postfix_regression_v2.log` 分开存放，未将旧失败覆盖成通过。

Standards 未关0项；Spec 未关0项；检索/学习及流式回归未关0项。真实宿主遵循率、
Windows/macOS、原生插件生命周期、全新依赖环境全矩阵、冷模型下载及长期真人/团队收益
继续保持原有限界。既有真实 E5 留出质量评测仍绑定其原始语料和证据，本轮没有重复评测或
借缓存冒烟扩大其结论。`0.1.0a1` 旧公开发布也不代表这次优化已发布。

面向维护者的[逻辑说明](../../../guides/understanding-astrofairy.md)已更新到当前工作树，
[当前实施入口](../../2026-11-implementation/README.md)接续本报告，历史报告不改写。
