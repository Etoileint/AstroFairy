# W6 返工候选独立复验

日期：2026-11-08。结论：**仍需定向返工，未接受、未提交、未发布。**
规范与方案符合性分别检查，实施者的fixed标签不代替独立观察。设计要求没有为迁就实现而放宽。

## 输入与实际执行

- HEAD仍为`c330e72b56bd3a3f5486054addc1b59e8990dae8`加未提交返工工作树。
- 回交source manifest SHA256：`b3c77f30024eb106da739b52b0370524b0b7b59d82a91ab63ee89143000fb368`。
  **364条记录＝360件现存文件＋4件删除**；全部字节/身份核验一致，28件证据亦一致。
- 修改验收导航前封存360件源文件及三件提交制品；首轮独立验收的23件封存证据均未改。
- 主验收者独立运行完整检查：235运行测试（默认1真实模型skip）、37开发测试通过；
  另启真实E5既有缓存推理烟测，1项通过。不是冷下载、跨平台或性能验证。
- 两名独立审查者分别复验规范与方案，相关开发19项及两组47/48项运行测试通过；后两组存在重叠，不冒称95项唯一覆盖。

## Standards：规范轴

验证者：`rework_standards_acceptance`。

| ID | 结论 | 实际结果与限界 |
|---|---|---|
| STD01 | 未闭合 | 真正求解的白名单已有效，真实uv离线暖缓存污染试验保持两锁字节相同；但工具身份探测仍继承PYTHONPATH，实际执行并接受隔离伪uv模块 |
| STD02 | 未闭合 | check能拒绝旧漂移反例；update复用仍可把已漂移清单写成新provenance，随后check转绿，未选中的非法来源也可保留 |
| STD03 | 未闭合 | wheel身份、源码哈希与六文件当前值有改进；仍以可改consumes清单决定遍历集合，保持固定源码不变，同步删掉config.json后门报告5文件通过 |
| STD04 | 原误拒修复，新增回归仍需修复 | 相同合法fork通过、两profile同环境冲突拒绝；新增第三profile不含共享包时，前两者的冲突反被全交集算法漏掉。当前只有两profile，不夸大成现存两锁冲突 |
| STD05 | 通过 | 环境字段完整，不能表达的marker明确拒绝，不借用宿主release/version |
| STD06 | 通过 | 现行check/update拒绝旧flat格式，迁移分支已删除 |

消费者反例使用真实固定FastEmbed tokenizer程序和合成tokenizer配置，证明config值影响padding；
不是声称当前六文件运行清单漏项，也不是权重质量试验。

## Spec：方案符合性轴

验证者：`rework_spec_acceptance`。

| ID | 结论 | 实际结果与限界 |
|---|---|---|
| SPEC01 | 未闭合 | 普通symlink已拒绝；真实uid1000不可读子树中的symlink被os.walk静默跳过，repair仍整体隔离并返回validated。外部sentinel未改 |
| SPEC02 | 原问题通过 | close、晚到反馈/报告/工具观察及learn的SQLite导出失败保留已提交身份、原观察状态和deliver恢复；不抵销T29的数据库提交缺口 |
| SPEC03 | 通过 | 失败回包绑定实际冻结S；未选中时明确unknown/null，不再伪造最新序号 |
| SPEC04 | 未闭合 | 最终_verify的错误有进度；但两次rename后、_verify之前的路径检查PermissionError仍越出进度边界，丢已完成动作/隔离身份 |
| GAP01 | 通过 | 当前checker缺失时live assessment不通过，历史receipt稳定可复用 |
| T29 | 未闭合 | 真实SQLite COMMIT-busy并成功ROLLBACK后缺显式false；受控真实COMMIT成功后确认丢失缺unknown/操作身份，ROLLBACK错误还遮蔽原错误。现有unknown-write测试是外部效果未知，不是数据库提交未知 |
| T35 | 通过 | 固定事件→receipt字节和SHA可复算，当前checker变化不改历史输出；篡改记录检查目标会使grounding失败 |
| REG02（独立报告S-R3） | 新增P1回归 | invoked已提交、外部write sentinel已生成，observed入库失败后，整段_precommit却报告committed=false且无call/task。旧候选没有这个错误断言；不冒称已观察到重复外部写入 |

STD04的漏检也由旧/新函数等价输入比较确认是返工回归。其余未闭合反例不因最小旧反例已变绿而消失。
后续需要修复的是完整工具/来源管线、独立消费发现、安全遍历及提交/修复阶段边界，见[再次返工要求](rework.md)。

## 限界、证据与计数更正

原生Windows、Linux x86_64、junction/reparse原生负例、冷模型下载/中断恢复、跨进程缓存锁、
完整skills CLI安装矩阵及真实host恢复交互仍未执行。无需为本次已确认代码缺陷修改这些原有义务。

原始证据位于维护者忽略目录`.evaluation/issue-repair-acceptance/recheck-20261108/`：
`intake.json`、`submitted-source.zip`、`submitted-artifacts/`、`canonical-check.log`、`real-e5-smoke.log`、
`standards/`与`spec/`中的独立报告、脚本、原始输出及哈希。普通clone不含。
三件dist条目仍相对仓根，其他证据相对返工目录；本轮以明确解析索引核验并封存，下次须统一/显式路径基准。

更正首轮计数口径：首轮source manifest的353条记录实际是349件现存＋4件删除，并非353件现存另加4件删除。
首轮汇总沿用了执行者错误计数；字节核验、349件源码ZIP和不通过结论不受影响。原始记录保留，本条作为更正。

本轮只修改验收记录与导航，没有代执行者修改产品。规范轴2项通过、4项未闭合（含STD04返工回归）；
方案轴SPEC02/SPEC03/GAP01/T35通过，SPEC01/SPEC04/T29未闭合，另有新增REG02。
最高风险分别是工具/来源身份放行与已发生动作被错误断言未提交。维护者保留最终裁决。
