# 后续验证交接入口

日期：2026-11-01。用户已同意：由另一Agent执行后续验证，完成后回交本会话验收。
本目录是开发外围的验证任务包，不进入技能入口、运行器或成员使用流程。

## 接手步骤

1. 读仓库AGENTS、[正式任务书](assignment.md)与[回交/验收清单](return-checklist.md)。
2. 读[当前工作范围](../repairs/work-program.json)，再按需读[项目逻辑说明](../guides/understanding-astrofairy.md)、
   [架构](../guides/architecture.md)、[操作](../guides/operation.md)和[F09收口](../repairs/F09-record-lifetime-and-state-recovery.md)。
3. 使用已准备的Python运行版本核对；命令在仓库根目录执行：

```sh
.venv/bin/python dev/check_validation_handoff.py
```

4. 在`.evaluation/product-validation/<run-id>/`建立本轮独立环境、任务home和证据目录。按任务书先做P03，
   可独立准备P04/P05，再做P06与P07。不要在真实团队数据上试验恢复或覆盖已有home。
5. 回交前核对结果材料：

```sh
.venv/bin/python dev/check_validation_handoff.py --return .evaluation/product-validation/<run-id>/return
```

此命令只核对版本、结构、文件身份和回交完整性；**不证明实际执行、真人身份、成果质量或整体通过**。
即使材料结构合法，也可能全部待证，须如实交回。主工作状态和产品接受不由执行Agent修改。

## 给新Agent的一段启动指令

> 请在`~/Program/AstroFairy`按`docs/evaluation/README.md`和正式任务书接手P03–P07验证。
> 产品基线和主台账只读，使用指定独立评测目录；可按任务书委派全新上下文的产出与评分Agent。
> 完成后提交可核验回交包并写回交索引，交原会话验收；真人、长期和不可用环境保持真实边界，不代签整体接受。

## 当前基线

正式依据是[基线清单](baseline.json)登记的F09收口156份文件；包版本0.1.0a1、协议/存储7、文档块格式1。
Git HEAD `22b7ece5d8388379f7b4bcaf47de4c047173cd9b`是初版历史基线，**不是当前156文件修复版本**。
工作区有继承的修改及未跟踪文件；不得reset、clean、覆盖、提交或切换掉它们。
新交接资料没有改变上述产品基线，核对器允许新增验证资料，仍要求全部156个原文件逐字一致。

已完成的P00/P01/P02技术结论与原15项问题修复可引用。已有134运行测试、17开发测试和三面演练的F09证据；
本次新增交接校验测试另计，不回写历史测试数。旧综合复核是冻结历史，其“未修”字样不得当作当前未修列表。
原依据见[综合复核](../reviews/overall-assessment.json)，当前依据见[工作范围](../repairs/work-program.json)。

本机现成材料位于`.evaluation/repairs/F09/primary/`和`independent/`；它们被Git忽略，不保证其他机器具备。
便携交接副本在`.evaluation/product-validation/handoff-20261101/`：包含精确产品源码副本、最终制品和选定本机证据，
以及SHA清单。副本不含Git数据库、运行环境、真实任务home或整个评测历史；不能用它冒充完整历史Git审计。
完整验证任务包使用工作区或handoff-materials.zip；运行wheel/技能ZIP和产品sdist不代表包含全部评测资源。
缺少本机原始证据时，将其记为“引用既有结论、未重新读取原始日志”，或明确安排必要重验。

## 五项工作与回交

| 工作 | 执行责任 | 完成边界 |
|---|---|---|
| P03 | 实际模型任务、直接路线对照与质量/成本分析 | 有范围的可用性及经济性证据，不能由预写答案的协议夹具代替 |
| P04 | 安装、原生发现/调用、更新、平台、Office渲染分层实测 | 没有环境的通道继续待证；安装布局通过不代表原生宿主通过 |
| P05 | 准备试用包并整理真实成员记录 | Agent不代演真人；未取得真人数据时交回可直接试用的材料 |
| P06 | 重复任务复用、反例、检索相关性和成熟方案比较 | 区分受控收益、真实长期收益和人的改善 |
| P07 | 权威来源/当前描述/原要求覆盖与终验建议 | 给本会话提交建议，最终产品接受仍由用户决定 |

[范围映射](scope-map.json)由原检查/要求/场景/对象和现行路由生成，只作导航，不是新一轮已通过判断。
[固定材料](fixtures/pack.json)提供起步任务；[独立评分参考](fixtures/private/rubrics.json)不送入产出上下文。
[回交结构](submission.schema.json)限定资料形状，业务判断仍由验收完成。

## 推荐技能

- `handoff`：需要压缩会话时使用；临时会话摘要放系统临时目录，正式依据引用本目录。
- `first-principles-design`：P07的设计级复核、真实发现真实性复查，或后续获准的概念修复；按现行技能回源装载。
- `openai-docs`：实际核查Codex/OpenAI宿主、模型或接口时按该技能读取官方当前资料。

技能不可达时如实说明缺口，不以记忆代替原文。普通评测执行不必重新套一轮完整核心架构设计。
