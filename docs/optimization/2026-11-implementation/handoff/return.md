# 回交合同与原会话验收

## 目录和身份

在项目忽略目录 `.evaluation/optimization-implementation/<run-id>/return/` 写本轮回交资料。
执行 agent 完成后只需给维护者这个目录；正式方案、运行器和技能不包含评测私有数据。

回交以 `submission.json` 为入口，形状见 [return.schema.json](return.schema.json)，
可以从 [submission.template.json](submission.template.json)起步。模板的待办状态不是执行证据。
必须引用本次 source-manifest.json 的 SHA256，并生成**最终源码**的新清单及源码 ZIP。
不能用输入基准清单冒充输出身份，也不能仅提交 Git diff 漏掉未跟踪新文件或删除信息。

输入清单是冻结的“开始时工作树”。启动前可这样核对（仓库根目录、锁定解释器）：

```python
from pathlib import Path
from dev.check_validation_handoff import check_files, read_json

root = Path.cwd()
baseline = read_json(root / "docs/optimization/2026-11-implementation/handoff/source-manifest.json")
check_files(root, baseline["files"])
```

这复用已有身份检查，不调用旧 P03–P07/F09 的专用任务入口；旧验收基线不改写。
执行后工作树发生合法变化，不能继续用启动比对命令当最终验证。

## 必需材料

- `report.md`：最终行为、工作包状态、原症状如何消失、验证与限界、剩余具体事项和接受建议。
- `coverage.json`：原 decisions.json 全部 78 对象和 43 预算逐个接续；按编号提供实现/保留/
  删除/未完成状态、实际源码位置和验证证据，不能凭运行总数或复制设计理由判通过。
- `runs.json` 与原始日志：命令数组、cwd、解释器/宿主/模型/依赖身份、输入和产出、开始/结束、
  exit code、实际模式及日志位置。计划、尝试、失败、通过和引用旧结论分别表达。
- `metrics.json`：行为、检索和资源实测；调参与留出集身份、算法/字段范围、原件/model profile、
  冷/热启动和费用可取得性、正反例。不可测字段明确 unknown，不编造新账单或真人证据。
- `findings.json`：发现、证据、根因处理和影响域复验，未解决项/方案偏离明确；没有发现也写明。
- 最终源码清单与 ZIP：含所有当前有效源码、配置、文档、新增/改名文件及相对输入的删除清单；
  不含 `.git`、虚拟环境、缓存、真实任务数据或评测私密资料。保留文件原始字节和相对路径。
- `evidence-inventory.json`：除本清单和 submission.json 自身外，所有回交文件的相对路径、bytes、
  SHA256；包含报告、运行/覆盖/指标/发现、最终源码清单及 ZIP、必要日志。它们的引用必须能解析。

大日志或必要原件可以放相邻封存包，通过回交目录里的摘要清单和确切包身份关联，不能只给
易失的绝对路径或可变 latest URL。源码 ZIP 是最终交付身份，不能替代真实运行的工具/模型证明。

`coverage.json` 顶层为 objects、budgets、cases 三个对象，键分别为原 78 编号、B01–B43、
V01–V24。每行含 basis、verification（passed/limited/not_run/failed）及 evidence 路径数组；
objects/budgets 另含 implementation（implemented/retained/removed/partial/not_started/blocked）
和 implementation_refs（实际源码/删除清单定位）数组。完成处置须有定位，passed 须有证据。
证据路径是回交目录内的文件路径，具体段落/运行编号写在 basis 或文件内容里。

## 自查与诚实完成条件

最终代码执行项目 `dev/check.py` 及新增依赖/模型锁、分发和受影响路径的必要验证。
按方案 V01–V24 覆盖正常/拒绝/恢复路径，声称通过须指向实际运行；有限验证完成后按门收敛。
保留完整测试收集、类型、风格、来源/锁和文档链接。新增测试属于代码所有者，执行通道真实存在。
不用另一个轮次的日志声称最终源码已测；实测前后若源码再变，重验受影响范围并更新身份。

`submission.json` 必须保持 `product_accepted=false`、`independent_acceptance=pending_original_session`。
W08 仅填写证据准备状态，独立验收由原会话执行。其他 W 包区分实现完成与验证通过；
部分实测缺口如实标 limited/blocked，不能为“交完全部任务”编造或隐藏。

本机交接目录的 `check_handoff.py` 可核对输入/回交结构及文件身份；它复用既有校验函数和
python-jsonschema，检查通过也不证明执行、质量、权威性或接受。没有该本机缓存时，直接使用
JSON Schema 验证器和既有 check_files；规则在正式文档和 schema 中，不依赖临时脚本授权。

## 原会话验收顺序

1. 认领回交目录，核对输入身份、最终源码/证据身份、实际工作树与输出一致；不覆盖或重建丢失身份。
2. 查 78/43 处置是否完整且有实际依据，检查 W01–W08/V01–V24 状态，无静默降标和未声明偏离。
3. 对最终源码独立检查关键合同，复跑代表性原症状、身份/失败/并发/恢复反例和必要测试。
4. 读真实模型/检索/资源/分发证据，核实对照与限界；缺口有范围判断，结构校验不代签语义效果。
5. 形成接受、返工或限界结论；对具体发现作根因修复和影响域复验，更新当前说明/记录。
6. 收尾并向维护者报告。提交、推送、发布及最终产品接受仍按维护者授权处理。
