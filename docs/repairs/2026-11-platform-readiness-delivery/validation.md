# 验收矩阵与设计攻击面

状态：实施验收规范，非已通过报告。需求来自[scope.md](scope.md)，机制来自[ADR-0012](../../adr/0012-platform-readiness-and-delivery-observation.md)。

| T | 触发/对象 | 必须观察的结果 | 需求 |
|---|---|---|---|
| T01 | 同输入在不同宿主/显式环境求解 | 保留Windows和Python版本分支；无宿主默认覆盖策略 | R01,R02 |
| T02 | 删除colorama/win32-setctime或某一条件分支 | 检查/原生安装应失败，不得同源自检全绿 | R01,R02,R13 |
| T03 | 修改源元数据、hash、root、工具pin或策略 | 离线一致性检查拒绝；未声明输入不得改变结果 | R01,R02,R09 |
| T04 | 全新Linux aarch64、Linux x86_64与Windows x64环境 | core/delivery/search哈希安装、pip check、导入与最小任务交付通过；分别记证据 | R01,R05,R11 |
| T05 | 空活跃库普通搜索；候选/退休资产库；元数据浏览 | 无下载、模型加载或向量调用；结果准确 | R03,R10 |
| T06 | 空库 assets prepare；空库 search --refresh | 同一准备服务确实调用；固定revision/hash核验；后者projection=empty且保留准备元信息 | R03,R04 |
| T07 | 非空库refresh、scope无匹配、空query浏览 | 准备和当前代次正确；显式refresh结果不丢；浏览无必要推理 | R03,R04,R10 |
| T08 | 缺依赖、版本不符、只有dist-info但导入失败 | 元数据、导入/ABI与推理验证层次不混淆；错误给出对应恢复 | R04,R12 |
| T09 | 无home/模型不存在/只有目录/缺文件/同长损坏 | doctor不创建home/数据库/锁、不下载、不做大文件hash；存在性不是verified | R04,R10 |
| T10 | 六个真实消费文件逐一缺失/同长改写，显式准备/验证、中断/重试，同进程首次验证后再损坏 | 清单覆盖真实消费者及可选配置存在性；每次显式验证重新观测而不复用_verified_dir；固定内容修复，不切换模型，验证后重试成功 | R03,R04,R08 |
| T11 | 并发准备、并发资产采用与refresh | 缓存锁有界；网络不持SQLite事务；刷新读取新代次或诚实拒绝过时投影 | R03,R04,R09 |
| T12 | 普通非空语义搜索；旧/缺/错误profile索引 | 允许必要本地推理，不下载；投影身份无误，错误不是空成功 | R04,R10 |
| T13 | POSIX与Windows本机BagIt完整任务 | upstream full validate与项目权威校验均通过；payload不被分类成tag | R05,R08 |
| T14 | 绝对/盘符/UNC、逃逸、转换后碰撞、祖先symlink、Windows祖先/目标/载荷子目录junction或其他重解析点 | 锁/staging创建前拒绝危险祖先，发布前复核；不写外部目标，不移动redirect；不粗暴禁止HF缓存内部规范链接 | R05,R08 |
| T15 | 重封装自洽但换payload/receipt、删/加文件、损坏权威blob | 继续拒绝；不放松既有38类权威绑定反例与流式检查 | R05,R08,R09 |
| T16 | 正常close及next | acceptance、closed、probe、validated导出各有准确语义；不存在outcome→delivered推断 | R06,R12 |
| T17 | close事实提交后导出失败并重开运行时 | committed身份仍在、错误非零、next给deliver、只重试导出；不重放close | R06,R07,R11 |
| T18 | closed后晚到model report/feedback导出失败 | 原始事实保留；当前seq恢复路径正确；旧包不覆盖 | R07,R08,R11 |
| T19 | closed后晚到工具观察，或观察后追加asset_used | 工具状态仍是实际观察，导出错误不伪装工具执行失败/unknown；call与提交seq可追溯 | R06,R07,R11 |
| T20 | learn maintain/defer/no_change提交后导出失败 | 决定及child身份保留；只deliver，不重复创建child/决定；收据含新事实 | R07,R08,R11,R12 |
| T21 | next/inspect/doctor cheap probe | 不创建导出锁/目录，不全量hash包；existing只表示unverified，不能把存在当有效 | R06,R08,R10 |
| T22 | same-seq并发deliver；导出中追加不同seq | 同seq锁串行复用；回包/receipt只绑定同一冻结状态；新next能看见新seq | R07,R08,R09 |
| T23 | expected-seq已落后或导出选中后又有新事件 | 前者拒绝并引导刷新；后者结果标明S，不声称阻止后来写入 | R07,R08 |
| T24 | 有效包删掉、损坏或被换成自洽替代包 | next不永久断言delivered；deliver完整校验失败时提供修复，不覆盖原包 | R06,R08 |
| T25 | 显式repair；源库损坏、unsafe祖先/root/后代（含junction）或权限不足 | 仅安全识别的派生坏目录可隔离；先建验新包，保留隔离物；源数据从不改写，外部链接目标不触碰 | R07,R08,R09 |
| T26 | 注入repair隔离前、两次rename之间、发布后失败 | 事实与旧对象保留，缺包可再生，错误保存已发生动作；不声称两次rename原子化 | R07,R08 |
| T27 | 备份恢复closed任务；学习/晚到事实推进seq | 缺包给deliver；正确重建当前快照；不迁移旧包或重放业务效果 | R07,R08,R11 |
| T28 | 旧seq导出与当前执行冲突 | inspect_conflict优先；导出状态不能消除冲突或改写历史结果 | R06,R08,R09 |
| T29 | 提交前失败、提交后失败、无法确认提交、回包归档失败 | 三种提交确定性准确；恢复controls保留task/call/child/seq/动作；无原始敏感异常泄漏 | R07,R11,R12 |
| T30 | 超大错误/多文件结果的24KiB封装 | 控制字段有界、可继续读取；正常交付与后提交失败身份不丢 | R07,R10,R12 |
| T31 | 单文件/多文件、partial/failed/cancelled、重复恢复 | 都能给出正确的关闭/导出状态与证据，单次validated回包使host完成交付步而不循环next | R06,R07,R12 |
| T32 | wheel/skill ZIP/sdist独立安装与再生 | roots/官方快照/工具声明/锁/诊断/必要资源齐全，无维护者私有路径依赖 | R01,R02,R11,R13 |
| T33 | 完整普通检查、旧安全回归、协议消费者 | owner测试、typing/style/链接/metadata通过；旧名无别名残留；历史证据保持基准 | R09,R11,R13 |
| T34 | 人类任务入口与agent完整恢复脚本 | 人无新增环境表单或技术问题；agent仅据准确下一步完成准备/交付/学习 | R10,R12,R13 |
| T35 | 同seq重启、替换当前checker定义、重复deliver/repair | 历史receipt字节稳定，当前assessment可变且标明身份；有效旧包不因当前registry变化被当坏包；换投影规则必须换格式 | R06,R08,R09,R11 |

## 原生矩阵与证明限界

- 最低必需：Linux aarch64（当前维护者机器）、Linux x86_64（现有CI参考）、Windows x64，CPython3.12。
- universal Python>=3.12解析与原生3.12验证是不同范围；其他解释器版本、macOS和其他架构逐格登记，未运行不能标通过。
- 每格分别记录wheel可选择、实际哈希安装、导入/ABI、BagIt、原生锁/路径和最小完整任务；一个成功布尔不能代替这些观测。
- 真实固定E5验证单列硬件/缓存/下载情况；纯替身用例证明调度，不证明真实模型完整或推理质量。
- 现有正确性与安全负例至少保持原拒绝结果；任何平台跳过必须有与功能承诺对应的明确理由，不能跳过报错路径来关闭Issue。

## 双向追溯与收敛

T表逐项指定R；实施回交反向汇总R→T→命令/结果/原件SHA256。没有证据的T项保持未执行。
设计攻击起点：权威/派生边界、显式/隐式动作、存在/验证、版本/平台分支、提交前后、当前/历史序号、
正常/缺失/损坏、重启/恢复、并发/中断、普通/大回包、单/多成员与四种outcome。
从需求输入与消费者调用链两路重查；新增反例回到相关设计和受影响测试，不以测试数量或文件数证明完备。
当前矩阵是有界验收要求，不是未来所有边界可被穷尽验证的声明。
