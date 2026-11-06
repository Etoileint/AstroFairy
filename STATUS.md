# 当前开发状态

核对日期：2026-11-05。本文件是新接手者的导航；Issue 的实时状态以 GitHub 为准，
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
- 协议及存储格式10，文档归档格式1；开发期没有旧库迁移或接口兼容负担。
- [本版双语说明](docs/releases/v0.1.0a2.md)、[项目逻辑讲解](docs/guides/understanding-astrofairy.md)。
- 发布时主分支及标签 CI 通过；附件下载、校验和、固定版本安装及新依赖环境验证通过。
  [主分支 CI](https://github.com/Etoileint/AstroFairy/actions/runs/41628414958)与
  [标签 CI](https://github.com/Etoileint/AstroFairy/actions/runs/41628640927)是公开记录。

## 当前收到的问题

以下为核对日的公开反馈快照，**均未在本次仓库筹备中独立验证，也未修复或关闭**。
Issue 中的复现步骤和建议是待核实材料，不自动成为实现要求。

| 入口 | 报告范围 | 接续要求 |
|---|---|---|
| [#1](https://github.com/Etoileint/AstroFairy/issues/1) | Windows 检索依赖锁可能缺少平台条件依赖 | 核实锁生成的 marker 求值、目标平台与安装承诺 |
| [#2](https://github.com/Etoileint/AstroFairy/issues/2) | 空资产库 refresh 可能未按说明预热固定模型 | 核实显式准备入口、空库行为与文档契约 |
| [#3](https://github.com/Etoileint/AstroFairy/issues/3) | Windows BagIt 清单路径比较可能导致交付失败 | 核实上游路径表示与本项目规范路径之间的边界 |
| [#4](https://github.com/Etoileint/AstroFairy/issues/4) | 导出失败后 next 可能仍显示 delivered | 核实关闭事实、实际导出与恢复引导之间的关系 |

#3 与 #4 存在报告关联，后者声称影响不限于 Windows；复现时分别确定成立条件。
当前没有由本文件额外授予的问题修复、外部消息、提交或发布权限。

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
