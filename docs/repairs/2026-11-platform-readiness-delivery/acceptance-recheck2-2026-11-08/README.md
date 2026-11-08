# W6 第二次返工候选独立复验

日期：2026-11-08。结论：**仍需定向返工；未最终接受、未提交、未发布。**
本轮关闭了多项既有缺口，但完整错误边界尚未闭合。规范与方案轴分别判定，测试通过不替代契约符合性。

## 基准与独立验证

- HEAD为`c330e72b56bd3a3f5486054addc1b59e8990dae8`加未提交候选。
  回交源清单SHA256：`151ddc5b7b68bb949eda453836909f253811d5188d3d7e2fee48a309bf92b574`。
  **368条记录＝364件现存文件＋4件删除**，全部字节及HEAD删除身份核验一致；74件回交证据一致。
- 修改导航前封存364件源码和wheel、sdist、skill ZIP；前两轮独立验收的23件、47件封存证据未改。
  三种制品的源码条目均与冻结候选一致，运行包无遗漏。没有重建或覆盖执行者制品。
- 主验收者独立运行完整检查：241项运行测试（默认1项真实模型skip）、40项开发测试通过。
  另显式启用真实E5既有缓存推理烟测，1项通过；这不是冷下载或跨平台验证。
- 独立规范复核22项开发测试通过；独立方案复核72项相关运行测试通过，另执行原始反例及相邻分支探针。
  定向测试与完整测试重叠，不相加为唯一覆盖数。
- 主验收者独立安装封存wheel并完成最小任务交付。第一次夹具继承了基础解释器而非项目已准备依赖，
  doctor正确拒绝；显式加入已准备依赖目录后通过，模块位置确认为新环境内的wheel。
  这是分发源码独立运行检查，不冒称全新依赖安装。执行者另有fresh wheel/sdist/ZIP自检证据。

## Standards：规范轴

验证者：`rework2_standards_acceptance`。

| ID | 结论 | 证据与实际影响 |
|---|---|---|
| STD01 | 部分未闭合，P2 | PYTHONPATH/CWD注入已修复，真实uv污染环境下两锁稳定。但执行体摘要仍猜测Python邻接路径；uv支持的target布局中，真实工具执行成功而`tool.sha256=null`，update/check均放行。当前普通venv摘要正常，未观察到版本错选或新注入 |
| STD02 | 通过 | 既有来源字节、清单摘要、非法未选中来源、版本URL错位及缺失provenance在check/update均拒绝，负例无写；合法新增/刷新经批准来源的受控响应通过 |
| STD03 | 通过 | 六项完整消费义务不再由可同步删改声明决定；逐项同步漏删均拒绝，固定源码/版本变化须重新审定 |
| STD04 | 通过 | 合法同环境fork通过；A/B含冲突包而C仅有无关包仍拒绝，首尾环境单元均验证 |
| STD05/STD06 | 保持通过 | 不借用宿主marker字段，不能表示的字段拒绝；旧flat清单拒绝，无兼容分支 |

STD01定位：`dev/lock_dependencies.py:321–329`猜路径并允许None，update写入摘要时不拒绝缺值。
依据为[再次返工单](../acceptance-recheck-2026-11-08/rework.md)的完整工具生命周期边界及ADR-0012来源记录要求。
真实target布局试验使用原uv包/二进制、真实版本探测与两次真实离线compile；不是替身冒充求解。

## Spec：方案符合性轴

验证者：`rework2_spec_acceptance`。

| ID | 结论 | 实际结果 |
|---|---|---|
| SPEC01 | 本机范围通过 | 真实uid1000不可读子树拒绝，不移动、不隔离，外部sentinel不变；普通坏包仍可修复。原生Windows范围未据此通过 |
| SPEC02/SPEC03 | 保持通过 | 闭后各调用者导出失败保留已提交事实/身份；实际选中快照与未知目标的表示准确 |
| SPEC04 / F1 | 部分未闭合，P2 | 原post-publication路径检查已有完整进度，第二次rename失败也正确；但原生OSError直接重抛，最终lock.release又在进度边界外。实际隔离、发布均完成后受控释放失败，CLI仅回通用错误，丢published/quarantined/task/recovery |
| T29 / F2 | 部分未闭合，P2 | COMMIT-busy成功回滚为false，受控丢确认明确unknown，原COMMIT错误保留；但事务体里的原生SQLite异常未归一化。真实SQLITE_AUTH拒绝close INSERT并成功ROLLBACK后，回包仍缺false/task/op/seq |
| T29 / F3 | 部分未闭合，P2 | invoked真实COMMIT后受控确认丢失，回包有unknown和task，却丢已知call及可执行调查动作；库中保留pending invoked。handler没有运行，不声称发生了重复效果 |
| REG02 | 原错误断言修复，原生异常分支并入F2 | 已提交invoked、外部效果和观察分开，原observed失败保留call与禁重放调查；原生语句异常加ROLLBACK失败时，内部unknown分类仍丢失 |
| GAP01/T35 | 保持通过 | 当前checker缺失时live assessment不通过；历史receipt及固定golden字节/grounding验证稳定 |

F1定位：`_delivery.py:573`只增强FairyError，`:584`在finally释放锁。
F2定位：`_store.py:189`事务体仅对FairyError附确定性；`_runtime.py:79,92`对未归一化观察异常默认false。
F3定位：`_runtime.py:423`提交失败回包未保留已知调用身份与调查控制。
均沿用ADR-0012、T29与上轮要求，没有新增事务服务、事件种类或跨系统原子性要求。

补充观察失败负例中，独立连接仍见seq2，同连接见未提交seq3，清理回滚后仍为seq2；
它证明未知分类传播缺口，不证明持久观察已经提交，也不声称SQLite自然发生成功COMMIT后随机抛错。
本轮没有已提交事实丢失或重复外部效果的证据。四类均按P2记录，不沿用上一轮不同后果的P1评级。

## 证据、限界与后续

原始材料位于维护者忽略目录`.evaluation/issue-repair-acceptance/recheck2-20261108/`：
`intake.json`、`submitted-source.zip`、`submitted-source-manifest.json`、`submitted-artifacts/`、
`artifact-source-binding.json`、完整检查/真实模型/封存wheel日志及`standards/`、`spec/`独立报告与探针。
`acceptance.json`登记结论，`evidence-inventory.json`封存本轮证据。普通clone不含；转交须附对应原件与哈希。
本次回交的74件证据统一相对`issue-repair-implementation/rework2-2026-11-08/`，没有沿用旧混合路径基准。

原生Windows、Linux x86_64、macOS、junction/reparse原生负例、真实冷下载/中断、跨进程缓存锁、
完整skills CLI安装矩阵与真实host恢复交互仍未执行；配置矩阵、暖缓存、POSIX夹具均不能抵销这些义务。
四条Issue保持开放，不发布跨平台修复声明。

下一步见[定向返工要求](rework.md)。本轮只写新验收记录与导航；产品、旧证据及兄弟仓未改。
规范轴剩1类P2，最高风险为执行体来源记录缺失；方案轴剩3类P2，最高风险为失败恢复状态与身份丢失。
最终产品接受、提交与发布仍由维护者另行裁决。
