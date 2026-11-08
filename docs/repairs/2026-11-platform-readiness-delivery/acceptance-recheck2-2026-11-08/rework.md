# 剩余机制边界定向返工

依据：[本轮独立复验](README.md)、[上轮返工要求](../acceptance-recheck-2026-11-08/rework.md)、
[ADR-0012](../../../adr/0012-platform-readiness-and-delivery-observation.md)与[T29等验收项](../validation.md)。
这是可交执行者的具体要求，不授予提交、推送、发布、Issue外部动作或兄弟仓写入权限。
已经闭合的机制保留；不增加兼容层、后台事务平台或全局exactly-once承诺。

## Standards

### STD01：记录实际选中的工具执行体

从同一个隔离环境解析并绑定实际uv执行体，使身份探测、摘要取得和compile的来源一致。
不能从Python邻接位置猜测另一文件；来源或摘要无法确认必须明确拒绝，不能写null后让check通过。
采用上游uv实际定位规则/接口，避免另造安装布局白名单。保留现有版本钉、白名单环境、配置隔离和官方索引策略。

回归至少含当前普通venv和uv支持的target布局；两者均用真实工具验证版本/实际文件/摘要一致。
明确拒绝缺摘要，保留PYTHONPATH/CWD注入拒绝及真实污染环境锁字节稳定。
主证据：本轮`standards/expanded-probe.py`、`expanded-results.json`、`target-tool-raw.json`。

## Spec

### F1 / SPEC04：一个覆盖返回与清理的交付进度边界

把进度作为动作阶段的单一事实源，从staging已验开始，覆盖安全检查、两次rename、发布复核、结果生成及锁释放。
已发生动作后的原生OSError与已有FairyError都必须保留task、completed、published、quarantined（若已有）和安全恢复动作。
锁释放失败不能覆盖原错误或把已发布结果退化成无身份通用失败；保留原异常cause，不泄露原始敏感文本。
不要靠给每个新故障点单独补except维持进度。不可恢复的进程终止不要求返回JSON。

回归以原生异常分别命中第一次rename、第二次rename、发布后安全检查、最终复核及返回前释放。
核对每个已发生动作与实际目录对应；没有发生隔离的错误不能伪造quarantined，已完成隔离不能丢失。
保持普通修复、有效包复用、不可读/redirect拒绝和安全外部sentinel反例。

### F2 / T29：在权威事务边界统一异常与确定性

事务体内原生sqlite3.Error与BEGIN/COMMIT异常使用一致的确定性传播契约。
实际已知回滚为false，无法确认明确unknown；回滚再失败保留原始错误及回滚结果，不能在上层因异常类型不同而默认false。
由事务层提供数据库事实，运行时补操作身份；不要恢复整方法`_precommit`推断。
数据库提交、invoked、外部效果、observed与交付投影仍分别表达，不改变committed含义或伪称未提交观察已持久化。

回归包括真实SQLite authorizer拒绝事务体INSERT并成功ROLLBACK、事务体异常加受控ROLLBACK失败、
COMMIT-busy与确认丢失、observed阶段同类失败。用独立连接核对持久事实，清楚标注同连接未提交数据。
保持原COMMIT异常cause不被回滚错误遮蔽，已提交invoked与禁重放效果控制不丢。

### F3 / T29：提交不确定时保留已经知道的调用身份

invoked提交失败/无法确认的回包保留task、call、operation、明确标注的已知/待确认序号、阶段和可执行调查动作。
已生成的call不因COMMIT确认失败丢失；未知不伪装为已提交，未知也不等于可以重放外部效果。
先inspect/history、必要时使用原有核对能力，不重新发明调用协议。

回归真实invoked COMMIT后受控确认丢失：独立连接有pending call，handler未执行，回包call与库中一致，
调查动作可用；已知回滚反例也不能误报committed=true。保持原REG02观察失败的身份和安全动作。

## 回交与复验

1. 新一轮源码、逐项处置、原始命令/退出码/环境、分发制品与证据另建目录；不覆盖三次回交和本轮/旧轮验收。
2. 复用本轮`spec/boundary-probe.py`、`sqlite-probe.py`及规范探针时保留原件；接口适配不能删除失败分支。
3. 保持STD02–06、SPEC01–03、GAP01/T35与原REG02通过；普通完整检查及对应分发按影响域重跑。
4. 原生平台、冷模型与宿主义务继续如实登记。执行者fixed与自检不代替原会话独立复验或维护者裁决。

本轮原始探针在维护者忽略的`.evaluation/issue-repair-acceptance/recheck2-20261108/`，
接手者需要对应目录及`evidence-inventory.json`；仅有公开汇总并不意味着已经取得原件。
