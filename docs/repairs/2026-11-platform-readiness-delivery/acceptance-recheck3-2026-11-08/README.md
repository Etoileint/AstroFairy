# W6 第三次返工候选独立复验

日期：2026-11-08。结论：**上轮4类P2均闭合，本轮定向整改技术复验通过，未发现新的阻断项。**
规范轴0项open，方案轴0项open。原生/集成验证仍有未执行项，因此专项尚未整体验收；
维护者最终接受、提交、推送、发布及Issue外部动作均未发生。

## 对象与独立执行

- HEAD为`c330e72b56bd3a3f5486054addc1b59e8990dae8`加未提交候选。
  回交源清单SHA256：`0a2038eb32494ad75164a00a43eb5dba9529f225d12778d5e4060afc812c2166`。
  **372条源记录＝368件现存文件＋4件删除**，逐件字节及HEAD删除身份核验一致，71件回交证据一致。
- 在修改验收导航前封存368件源码及三件提交制品；前3轮独立验收封存的23、47、60件证据未改。
  旧报告保留自己的候选和结论，本页不把历史不通过改写为当时通过。
- 未提交工作树不能用空的提交diff冒充无改动。本轮对比上一轮冻结ZIP及回交源清单，
  包括未跟踪文件；产品运行实现改动集中于交付、Store事务和运行时身份补充，开发锁工具同步修正。
- 主验收者独立完整检查退出0：249项运行测试（默认跳过1项真实模型）、42项开发测试通过。
  另显式启用真实E5既有缓存推理，1项通过；ONNX报告CPU特性检测警告，功能烟测通过，不据此作性能结论。
- 两位独立验证者分别执行规范与方案复验：24项开发定向测试、47项运行定向测试通过。
  定向测试与完整测试重叠，不将这些数量相加为唯一覆盖数。

## Standards：规范轴

验证者：`rework3_standards_acceptance`。结论：**STD01–STD06均在本轮范围闭合，0项open。**

| 项 | 独立观察 |
|---|---|
| STD01 | 通过同一隔离解释器调用上游`uv.find_uv_bin()`取得真实执行体，不再猜Python邻接路径。普通venv及真实target布局中版本、实际文件摘要、update provenance一致，真实离线compile后check通过。缺失/畸形摘要拒绝；私有工具在compile后受控消失，update失败且不重写provenance |
| STD02 | 既有来源字节、清单摘要、非法未选中来源、版本URL错位、缺失来源记录均在check/update拒绝，负例无写；批准来源的受控新增/刷新通过 |
| STD03 | 固定六项消费义务的同步漏删均拒绝；固定源码/版本审定通过，真实FastEmbed配置对padding的消费可观测 |
| STD04–STD06 | 合法fork通过，A/B冲突且C无关仍拒绝；marker不借宿主字段，不能表达者拒绝；旧flat格式拒绝，无迁移分支 |

原5个独立探针逐字保留，新增工具生命周期探针；6组探针均退出0。CWD/PYTHONPATH影子模块未执行，
污染环境两锁字节稳定。复制候选初次测试缺少`.venv`夹具，补只读工具链接后同命令通过；失败日志亦保留。
这不是当前普通venv曾经存在target布局错误的声称，也不以离线求解代替原生安装。

## Spec：方案符合性轴

验证者：`rework3_spec_acceptance`。结论：**F1/SPEC04、F2/T29、F3/T29均闭合，0项open。**

| 项 | 独立观察 |
|---|---|
| F1 / SPEC04 | 统一进度封装覆盖已验staging后的检查、rename、结果生成与锁释放。原生/类型化错误的completed、published、quarantined与实际目录相符；同时发生主错误和释放失败时保留主cause，不退化成无身份通用错误 |
| F2 / T29 | Store统一事务体原生SQLite异常与BEGIN/COMMIT确定性；真实authorizer拒绝和COMMIT-busy成功回滚为false；受控回滚失败及确认丢失明确unknown，原始cause保留。运行时补身份，不恢复整方法默认false |
| F3 / T29 | invoked真实COMMIT后受控丢确认仍保留call、known/attempted seq及调查动作；独立连接中的pending call与回包一致，handler未运行。真实CLI history可用，重复未确认写被拒绝；已知回滚准确为false |
| 保持项 | SPEC01–SPEC03、GAP01/T35、原REG02通过；真实uid1000不可读树拒绝且外部sentinel不变，晚到调用者/冻结选择/历史receipt字节及篡改grounding拒绝均保持 |

7个旧独立探针逐字保留、无接口适配后重跑退出0；新增16个断言场景覆盖10个交付与6个事务分支。
独立连接区分持久invoked seq2与同连接未提交observed seq3，清理后核对结果；不把未提交数据当持久事实。
确认丢失/回滚失败代理证明错误传播，不声称SQLite自然发生成功返回后随机抛错，也不声称观察到重复效果。
契约没有为迁就实现而放宽；没有增加兼容层、权威事件、后台事务服务或跨系统exactly-once保证。

## 分发、证据与最终状态

三件制品已封存；wheel的19件、sdist的357件、skill ZIP的33件源码条目均与候选一致，无运行模块遗漏。
主验收者将封存wheel独立安装到新环境，显式复用已准备依赖，确认导入模块位于新环境并完成最小任务交付。
这不是全新依赖安装；执行者另交fresh wheel/sdist/ZIP自检，已校验其原件身份。

原始证据在维护者忽略目录`.evaluation/issue-repair-acceptance/recheck3-20261108/`：
`intake.json`、`submitted-source.zip`、`submitted-source-manifest.json`、`submitted-artifacts/`、
`artifact-source-binding.json`、完整检查/真实模型/封存wheel日志、两轴报告/探针/原始结果/哈希清单，
以及`acceptance.json`、`final-integrity.json`、`evidence-inventory.json`。普通clone不含；转交须附相应原件与摘要。
本次71件回交证据统一相对`issue-repair-implementation/rework3-2026-11-08/`。

T04/T10/T11/T13/T14/T32/T34继续partial，详见[剩余验证与收口](remaining-validation.md)。
最低原生矩阵中的Linux x86_64与Windows x64尚无本候选执行证据；macOS等也没有被本轮认证。
冷下载/中断、跨进程缓存锁、完整skills CLI矩阵及真实宿主交互仍未验证。
本轮既有缓存推理不能抵销上述义务，四条Issue保持开放，不发布跨平台修复声明。

本轮不新增代码返工单，后续转入原计划剩余验证。没有代执行者修改产品，未改兄弟仓。
规范轴0项、方案轴0项未闭合发现；无本轮阻断风险项，整体验收与发布状态仍须依据剩余证据和维护者裁决。
