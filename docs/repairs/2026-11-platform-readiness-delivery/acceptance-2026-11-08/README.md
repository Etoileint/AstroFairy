# W6 首轮独立验收

日期：2026-11-08。结论：**当前回交不通过，需定向返工；未接受、未提交、未发布。**
规范与方案符合性分别审查，不以某一轴的通过抵销另一轴问题。实施者与本轮独立审查者分离，维护者保留最终裁决。

## 输入与身份

- Git HEAD仍为`c330e72b56bd3a3f5486054addc1b59e8990dae8`，实现为未提交工作树。
- 实施回交`source-manifest.json`摘要为`e6e7252963d4fe0c9a10a18572e28758241789b30aae996c91b7c90f7617a35e`。
- 独立核对353件现存文件、4件删除的HEAD身份、45件证据及回交文件清单：无字节/哈希不符。
  证据清单中的`dist/`相对仓根，其他条目相对实施目录；验收记录显式保留该解析规则。
- 改写验收导航前已将353件输入封存为验收证据目录的`submitted-source.zip`；后续文档状态更新不混入实施源基准。
- 已审设计以[ADR-0012](../../../adr/0012-platform-readiness-and-delivery-observation.md)和冻结候选为准；
  独立比对确认没有把实施偏离偷偷改成新设计要求。

## Standards：规范审查

独立验证者：`issue_repair_standards_acceptance`。六项均有隔离函数/副本实验证据。

| ID | 优先级 | 确认问题与限界 |
|---|---|---|
| STD01 | P1 | 锁更新进程继承UV_CONSTRAINT等宿主环境；真实uv读入未声明的约束，违背无ambient输入契约 |
| STD02 | P1 | 来源URL改为未批准域、来源清单摘要偏离已记provenance，离线check仍通过；来源身份链未闭合 |
| STD03 | P2 | 消费者门只比对可同步修改的清单；wheel摘要全0或同步遗漏仍被FastEmbed消费的config.json均通过；当前六文件运行清单本身正确 |
| STD04 | P2 | 跨profile核对把环境选择摊平成版本集合；两profile有相同且正确的Win/Linux版本fork也被拒绝 |
| STD05 | P1 | 显式环境漏platform_release/platform_version，合法marker从宿主回填后判定改变；当前冻结依赖未使用两字段，不冒称现有Windows分支已经误选 |
| STD06 | P2 | update保留旧flat manifest读取并转写format2的实际兼容迁移分支，违反开发期无兼容负担 |

源码重点为`dev/lock_dependencies.py`和`dev/check_model_profile.py`；规范锚、复现与修复完成条件见
[返工清单](rework.md)。uv universal确实已投入使用，但后处理与来源检查仍未满足整体契约。

## Spec：方案符合性审查

独立验证者：`issue_repair_spec_acceptance`。四项新增实现缺陷及一项本范围内既有遗漏分别记录。

| ID | 优先级 | 确认问题与限界 |
|---|---|---|
| SPEC01 | P1 | repair吞掉unsafe后代拒绝，将含symlink的旧树移入quarantine并返回validated；外部目标未改写，不夸大为外部内容破坏 |
| SPEC02 | P1 | 已提交close后的导出copy读抛SQLite错误，CLI只回generic storage_failed，丢task/committed/seq及deliver恢复；事实已持久 |
| SPEC03 | P2 | 导出实际选中S=10，之后追加到11再失败，错误回包却宣称selected_seq=11及target11 |
| SPEC04 | P2 | repair两次rename成功后最终复核失败，错误未保留已完成quarantine/publication及隔离对象身份 |
| GAP01 | P2 | 当前checker缺失时仍报告acceptance.complete=true、issues为空；历史包复用正确，但live适用性未fail-closed。这是既有条件的本轮符合性遗漏，不是新增回归 |

另外，T29的提交前false/不确定unknown尚无相应完整契约证明；T35没有固定event→receipt golden期望值。
这些验收覆盖缺口需随相关修复关闭，不以测试名称或动态同源比较代替。
70成员直接deliver的归档回包仍可完整读取，不把“需继续读取”误列为数据丢失。

## 已独立执行的正向检查

- `dev/check.py`退出0：226运行测试（默认跳过1真实模型）、26开发测试，typing/style/锁/模型清单/技能/文档检查通过。
- 方案审查者独立复跑交付恢复/路径/呈现/存储相关36项，退出0；新增反例仍揭示未覆盖交叉状态。
- 主验收者另启`ASTROFAIRY_TEST_E5=1`，对既有`.cache/fastembed`执行真实E5推理烟测：1项通过。
  运行中有CPU特性探测警告，未妨碍该功能烟测；不据此声称性能或质量评测通过。
- 该真实模型验证使用已有缓存，不是冷下载；未把实施者准备的CI矩阵当成实际远端运行。

## 未完成的环境与覆盖义务

执行者T表原有28项passed、7项partial；独立反例直接否定T25/T26/T29的完整通过，并揭示T01/T03/T35相关机制/覆盖缺口。
原表保留不改；本结论是新的独立记录，不能把旧passed直接累计成终验通过。

仍未执行：原生Windows x64/Windows11报告环境、Linux x86_64实际通道、Windows junction/reparse负例、
真实模型冷下载/中断恢复、跨进程准备锁争用、完整原生安装矩阵与实际host恢复交互。
真实缓存推理烟测仅补齐相应子项，不消除这些义务。其他平台/解释器没有新增支持承诺。

## 证据与回交

原始证据位于维护者忽略目录`.evaluation/issue-repair-acceptance/20261108/`：
`intake.json`、`submitted-source.zip`及摘要、`submitted-artifacts/`、`canonical-check.log`、`real-e5-smoke.log`，
以及`standards/`、`spec/`的独立报告、脚本、原始输出。普通clone不含，转交须携带清单与哈希。
旧实施回交及设计/发布证据未改；本轮未修改产品实现。

下一步按[定向返工清单](rework.md)回交新候选与证据，原会话复验；四Issue保持开放。
维护者已指示由原实施agent执行该返工清单，尚未收到新候选；本轮不通过结论保留。
规范轴6项，最高为宿主输入/来源放行；方案轴4项新增缺陷＋1项既有遗漏，最高为已提交事实丢恢复身份。
