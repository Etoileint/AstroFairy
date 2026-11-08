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

- [0.1.0a2 Alpha](https://github.com/Etoileint/AstroFairy/releases/tag/v0.1.0a2)，2026-11-03 发布。
- 源提交：`1574ce89dd2e29e9a3b0be5997302b32b0bfe335`；技能目录和调用名为 `fairy`。
- 0.1.0a2 的发布事实为协议及存储格式10、文档归档格式1；当前开发工作树已推进到协议11、
  阶段包2、回执投影2、存储10、归档1。开发期没有旧库迁移或接口兼容负担。
- [本版双语说明](docs/releases/v0.1.0a2.md)、[项目逻辑讲解](docs/guides/understanding-astrofairy.md)。
- 发布时主分支及标签 CI 通过；附件下载、校验和、固定版本安装及新依赖环境验证通过。
  [主分支 CI](https://github.com/Etoileint/AstroFairy/actions/runs/41628414958)与
  [标签 CI](https://github.com/Etoileint/AstroFairy/actions/runs/41628640927)是公开记录。

## 当前收到的问题

四条公开反馈**保持开放**。W1–W5实现与三轮定向返工已回交；最新W6独立复验确认已登记整改发现闭合，
**本轮定向整改技术复验通过**。原生/集成验证仍有缺口，专项未整体验收；维护者最终接受与发布未发生。
验证候选已固化为`c9824b24b1627dd10de70fbcfe028a0dc9dfcfd5`，通过独立GitHub交接分支流转，不并入主分支。
Issue中的复现步骤和建议是待核实材料，不自动成为实现要求。

| 入口 | 已确认根因 | 仍须观察 |
|---|---|---|
| [#1](https://github.com/Etoileint/AstroFairy/issues/1) | 宿主marker求值导致Windows条件依赖遗漏 | 本候选原生Windows哈希安装与完整任务 |
| [#2](https://github.com/Etoileint/AstroFairy/issues/2) | 空活跃库显式refresh跳过准备，doctor只看依赖元数据 | 冷下载/中断恢复、跨进程缓存准备；不能用已有缓存推理替代 |
| [#3](https://github.com/Etoileint/AstroFairy/issues/3) | BagIt上游路径表示与项目POSIX分类边界不一致 | 原生Windows完整BagIt及junction/reparse负例 |
| [#4](https://github.com/Etoileint/AstroFairy/issues/4) | close/晚到事实提交后导出失败仍被推断为delivered，不限于Windows | 原生平台及真实host按准确控制接续；本机关闭/导出/恢复回归已通过 |

[专项供料](docs/repairs/2026-11-platform-readiness-delivery/supply.md)保留根因试验与权威依据，
[方案入口](docs/repairs/2026-11-platform-readiness-delivery/README.md)、
[ADR-0012](docs/adr/0012-platform-readiness-and-delivery-observation.md)与
[实施计划](docs/repairs/2026-11-platform-readiness-delivery/plan.md)分别承担设计、机制与分派。
实施同时覆盖历史receipt/当前checker分责、交付redirect拒绝、模型六文件完整消费义务及显式重复验证。

最新[第三次返工独立复验](docs/repairs/2026-11-platform-readiness-delivery/acceptance-recheck3-2026-11-08/README.md)：
STD01实际工具摘要、F1完整交付进度、F2事务体原生异常确定性、F3未知invoked调用身份均闭合；
STD02–06、SPEC01–03、GAP01/T35及原REG02保持通过。规范轴0项open，方案轴0项open。
主验收者独立完整检查249项运行（默认1skip）＋42项开发、真实E5既有缓存推理通过；
两轴定向测试、原始探针、分发源码核对与封存wheel交付通过。计数重叠，不合计唯一覆盖。

原T04/T10/T11/T13/T14/T32/T34仍partial，见
[剩余验证与收口](docs/repairs/2026-11-platform-readiness-delivery/acceptance-recheck3-2026-11-08/remaining-validation.md)。
最低必需矩阵中Linux x86_64、Windows x64尚未取得本候选执行证据；macOS等也未被本轮认证。
冷下载/中断、跨进程缓存锁、完整skills CLI矩阵、真实host交互尚未验证；配置矩阵、模拟和暖缓存均不能抵销。
本轮不新增代码返工单，转入原计划剩余验证；不发布跨平台修复声明或关闭Issue。
维护者提供Windows开发机后，已完成[Windows验证移交包准备](docs/audit/changes/2026-11-08_windows-validation-handoff.md)：
固定未提交源码、必要Git历史、三制品及原生任务单已封装，本机恢复演练通过；Windows端尚未执行，待回交原始证据。
维护者随后指定双方仅通过GitHub通信，现行取件入口改为[Windows交接任务](handoff/windows-validation/README.md)，
见[GitHub交接记录](docs/audit/changes/2026-11-08_github-windows-handoff.md)。分支为`handoff/windows-validation-20261108`，
通过对应草稿PR回交证据；上述本机ZIP保留为历史准备产物，不再要求Windows端取得它。

| 历史关口 | 冻结结论 |
|---|---|
| [W1–W5实施回交](docs/audit/changes/2026-11-08_platform-readiness-implementation.md) | 实现与执行者自检完成，交原会话W6验收 |
| [首轮独立验收](docs/repairs/2026-11-platform-readiness-delivery/acceptance-2026-11-08/README.md) | 确认规范、实现及范围内遗漏，需返工 |
| [首轮返工独立复验](docs/repairs/2026-11-platform-readiness-delivery/acceptance-recheck-2026-11-08/README.md) | 部分闭合，仍有缺口及返工回归 |
| [第二次返工独立复验](docs/repairs/2026-11-platform-readiness-delivery/acceptance-recheck2-2026-11-08/README.md) | 多项闭合，剩4类P2 |
| [第三次返工回交](docs/audit/changes/2026-11-08_platform-readiness-rework3.md) | 执行者完成4类机制修复与自检；独立结论以上述最新复验为准 |

最新回交证据在本机忽略的`.evaluation/issue-repair-implementation/rework3-2026-11-08/`，
独立复验在`.evaluation/issue-repair-acceptance/recheck3-20261108/`；普通clone不含，转交须附原件与哈希。
旧回交与旧验收不改写；各自的未执行范围不能因新测试通过而自动消失。
原实施分派的授权不等于发布授权。后续GitHub交接限独立分支与对应草稿PR的验证通信；不授权主分支合并、
打tag、发布、四条用户Issue状态/评论变更或兄弟仓写入。

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
