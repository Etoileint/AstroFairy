# 当前开发状态

核对日期：2026-11-08。本文件是新接手者的导航；Issue 的实时状态以 GitHub 为准，
版本事实以标签、发布说明及其对应源码为准。它不代替协议或设计规范。

## 从这里接手

1. 阅读 [AGENTS.md](AGENTS.md) 和 [CONTRIBUTING.md](CONTRIBUTING.md)。
2. 按 README 的开发命令准备环境，启用提交钩子，执行 `dev/check.py`。
3. 从 [AstroFairy Issues](https://github.com/Etoileint/AstroFairy/issues) 选择已授权的任务，
   先核实报告与影响域，再设计、实现和验证。下面的历史批次不是自动重开的任务单。
4. 接手验收取证时，先读[证据获取与复验](docs/development/evidence.md)。
   使用维护者外部开发组织时，按[组织接入规则](CONTRIBUTING.md#external-development-organization)加载原件。

## 已发布基准

- [0.1.0a3 Alpha](https://github.com/Etoileint/AstroFairy/releases/tag/v0.1.0a3)，2026-11-08已公开预发布。
- 源提交：`b31b1cc5266178f43785dc157538d72757863100`；技能目录和调用名为`fairy`。
- 本版协议11、阶段包2、回执投影2、存储10、归档1；没有旧库迁移/兼容承诺，使用获准的新home。
- [双语发布说明](docs/releases/v0.1.0a3.md)、[项目逻辑讲解](docs/guides/understanding-astrofairy.md)、
  [发布执行与附件核验](docs/audit/changes/2026-11-08_v0.1.0a3-published.md)。
- 源提交的候选/main/tag两平台CI均通过；Git归档制品、三种独立安装、固定标签安装器复制、
  草稿及公开附件下载校验均通过。Alpha发布不代表全部长期效果验证已完成。
- 此前[0.1.0a2](docs/releases/v0.1.0a2.md)及更早发布保留原标签/附件/历史结论，不覆盖。

## 当前收到的问题

四条公开反馈保持开放；实现与三轮定向返工已完成独立技术复验。
**Windows第二轮指定复测已通过，无新增返工项**，见
[原件查收与独立验收](docs/audit/changes/2026-11-08_windows-round2-acceptance.md)。
维护者已接受本批修复并授权新Alpha发布；剩余集成与真实使用观察按发布后范围保留，不冒称全量验证完成。

| 入口 | 已确认根因 | 当前验证与剩余范围 |
|---|---|---|
| [#1](https://github.com/Etoileint/AstroFairy/issues/1) | 宿主marker求值导致Windows条件依赖遗漏 | Windows条件依赖、真实导入、完整任务及新环境CI已通过；不据此宣称所有平台认证 |
| [#2](https://github.com/Etoileint/AstroFairy/issues/2) | 空活跃库显式refresh跳过准备，doctor只看依赖元数据 | 机制回归、六文件消费审定及Linux既有缓存E5已通过；真实冷下载/中断、独立进程缓存争用和Windows E5仍待观察 |
| [#3](https://github.com/Etoileint/AstroFairy/issues/3) | BagIt上游路径表示与项目POSIX分类边界不一致 | Windows单/多文件及子目录BagIt、home外四处junction的ordinary/repair和三制品任务通过；不声称穷尽所有重解析点或Windows ACL |
| [#4](https://github.com/Etoileint/AstroFairy/issues/4) | close/晚到事实提交后导出失败仍被推断为delivered，不限于Windows | 原生关闭/导出/恢复owner回归通过；T34真实host按准确控制接续仍待观察 |

### 当前候选和已取得的验证

- 产品候选：`c9824b24b1627dd10de70fbcfe028a0dc9dfcfd5`；测试修正候选：
  `6ced5c9a1a59d0f615c0f324564f48955c58fed1`；GitHub交接HEAD：
  `3645fc6a601b5e162f801d6e62b96c7ee1c8b025`。产品runtime、锁、协议及版本未因测试修正改变。
- [交接任务](handoff/windows-validation/README.md)与[草稿PR #5](https://github.com/Etoileint/AstroFairy/pull/5)
  仍是GitHub取件/回交通道；维护者本机旧ZIP不再是Windows取件前提。
- Windows第二轮ZIP69,575字节，整体及62件清单原件全部核验，前后377项源码/制品身份一致。
  26条外层命令均exit0；255运行（248通过、7项允许skip）＋42开发通过。
  7项skip为3项POSIX专项、2项真实WinError1314文件symlink和2项真实模型；目录junction实际执行。
  源/wheel/sdist/ZIP各8条CLI均在checkout外完成任务及上游BagIt验证，制品来源核对通过。
- 同一交接HEAD的[PR CI](https://github.com/Etoileint/AstroFairy/actions/runs/42523300428)与
  [push CI](https://github.com/Etoileint/AstroFairy/actions/runs/42523294898)均通过：
  Linux x86_64/Windows x64完整门、smoke、wheel/sdist构建和skill打包均实际执行。
  Linux aarch64本机255运行（默认1skip）＋42开发与同一collector演练此前通过；平台结果各自保留。
- 第一轮87,226字节/148件原件已核验；当时完整门与CI失败的结论保留。
  后续已修正测试连接生命周期、工具发现及原生断言，不能再将旧失败表述为当前CI状态。

### 仍须推进的既有工作

T10真实冷下载/中断恢复、T11独立进程缓存争用、Windows真实E5推理、完整skills CLI安装矩阵，
以及T34真实宿主的准备/失败调查/交付恢复/学习。T32三制品独立运行部分通过，不替代完整安装矩阵。
这些是原计划剩余观察，不增加新的平台承诺，也不自动要求对已通过的修正重复返工。
macOS及其他解释器/架构未由本轮认证。

原范围、根因及权威依据见[专项供料](docs/repairs/2026-11-platform-readiness-delivery/supply.md)、
[方案](docs/repairs/2026-11-platform-readiness-delivery/README.md)、
[ADR-0012](docs/adr/0012-platform-readiness-and-delivery-observation.md)及
[实施计划](docs/repairs/2026-11-platform-readiness-delivery/plan.md)。
[第三次返工独立复验](docs/repairs/2026-11-platform-readiness-delivery/acceptance-recheck3-2026-11-08/README.md)
保留STD01、F1/F2/F3等技术闭合及两轴0open结论；其
[剩余表](docs/repairs/2026-11-platform-readiness-delivery/acceptance-recheck3-2026-11-08/remaining-validation.md)
保留当时基准，新取得的平台结果以上述最新查收为准。

历史入口：[首轮独立验收](docs/repairs/2026-11-platform-readiness-delivery/acceptance-2026-11-08/README.md)、
[首轮返工复验](docs/repairs/2026-11-platform-readiness-delivery/acceptance-recheck-2026-11-08/README.md)、
[第二次返工复验](docs/repairs/2026-11-platform-readiness-delivery/acceptance-recheck2-2026-11-08/README.md)、
[第一轮Windows原件复核](docs/audit/changes/2026-11-08_windows-validation-evidence-review.md)、
[跨平台测试修正](docs/audit/changes/2026-11-08_cross-platform-test-repair.md)和
[第二轮交接准备](docs/audit/changes/2026-11-08_windows-validation-round2.md)。旧记录、原件和旧失败不改写。
本轮原件位于本机忽略目录`.evaluation/windows-acceptance/round2-20261108/`，公开GitHub分片及摘要
登记在最新查收记录；普通clone不假定含有维护者的本机证据。

最新授权包括AstroFairy的正常提交/推送、合并收口、新Alpha标签和GitHub预发布。
四条用户Issue状态/评论及兄弟仓写入仍不在本次操作范围；后续发现按新证据处理。

## 已完成批次与仍待观察的效果

初版技术修复及后续整体优化已有各自的验收记录。
[2026-11-03 最终技术验收](docs/optimization/2026-11-acceptance/final-2026-11-03/README.md)
关闭了当时原10项发现、流式校验回归和收尾发现。发布检查收集195项运行测试
（194通过，默认跳过的真实模型测试另行通过），20项开发测试通过。
这是该版本和试验范围下的历史结论，不覆盖发布后的新报告。

真实成员易用性、宿主遵循率、广泛跨平台和原生插件生命周期、冷模型下载环境及长期团队收益，
继续按各项记录保留限界。它们不因发布而自动通过，也不要求无期限等待才能开展正常开发。

历史入口：[早期复核](docs/reviews/README.md)、[早期修复与工作范围](docs/repairs/README.md)、
[整体优化](docs/optimization/README.md)、[设计与变更记录](docs/audit/INDEX.md)。
旧交接中的未提交工作树、旧目录、旧格式号、旧任务状态和当时授权，只解释其冻结时点。
当前开发使用本入口、现行指南、真实源码与本次任务授权。

## 维护此入口

发布新版本、确定任务优先级或改变验证范围时，更新本文件的日期及链接；历史报告保留原基准。
新增可复用设计决定进入 ADR，任务执行和审查事实进入项目记录。产品经验仍进入外置资产库，
不持续追加到 AGENTS.md 或 CLAUDE.md。
