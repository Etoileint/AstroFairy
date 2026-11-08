# Windows原件收件复核与接续范围

日期：2026-11-08。结论：**主证据包收件和字节核验完成，若干Windows原生功能结果已证；完整检查仍失败，尚未整体验收。**
这是对[初步查收](2026-11-08_windows-validation-intake.md)的后续记录，旧报告/原件不改写。

## 已取得的原件

- [PR #5](https://github.com/Etoileint/AstroFairy/pull/5)的4条`AF_WINDOWS_EVIDENCE_V1`数据评论重组出原ZIP：
  87,226字节，SHA256 `e0b7a89f1ae3ce46b6bfd3a9c244133b653a0511a0f147545cd47f6622de93df`，与首次回交一致。
- ZIP共149件成员，除inventory自身外的148件文件逐件字节数/SHA256均匹配，无缺失或摘要不符。
  ZIP成员采用反斜杠，inventory采用正斜杠；在读取边界唯一转换并检查路径/碰撞，未改变原ZIP或成员字节。
- 原件包括29条主命令记录、全部对应stdout/stderr、身份快照、环境/覆盖/发现表、6件探针及三制品运行记录。
  部分原生stderr不是UTF-8；保留字节，以ASCII测试标记核对结果，不以替换解码冒充原始文本。
- 前后身份快照一致：交接HEAD `3f402b42797694d752c6cde7452980f0febbf14c`，候选
  `c9824b24b1627dd10de70fbcfe028a0dc9dfcfd5`，373件检查、0错误，清单摘要与分派一致。
- [补充评论](https://github.com/Etoileint/AstroFairy/pull/5#issuecomment-6726087047)保留分类撤回和两项repair补测说明。
  此评论不在首次冻结ZIP内，单独收录，不混充原ZIP已有内容。

## 按原件核对的结果

验证范围为该Windows x64开发机、CPython3.12.16 conda-forge构建、SQLite3.54.1、NTFS。
报告的系统名称与build字符串按原件保留，不据此推定其他发行渠道、补丁版本或Windows机器全部通过。

| 面 | 本轮可以确认 | 保留范围 |
|---|---|---|
| 身份与安装 | 三个runtime/delivery/search哈希锁安装、editable安装、pip check成功；colorama/win32-setctime实装，四个检索相关模块真实导入成功 | 开发依赖仅版本钉住，并非第四条哈希锁；初始两条`-c`引号错误尝试保留，后续脚本方式通过 |
| T04 / Issue #1相关面 | Windows依赖闭包/导入及CLI最小交付有原始记录支持 | T04整体验证还涉及其他原生格；CI完整检查仍不通过 |
| T13 / Issue #3相关面 | 单/多文件及子目录BagIt交付validated，上游validate=True；两成员内容hash与manifest一致，Windows上游反斜杠键和POSIX交付成员正确分责 | 该路径/样例范围通过，不推定所有路径类型 |
| T14 | 原生junction创建成功；祖先/task关闭导出拒绝、权威关闭事实保留、next=inspect_delivery，sentinel未变；seq/payload普通与repair的拒绝日志已取得 | 后两例探针程序未入ZIP；新增祖先/task repair目前只有补充说明，未取得其新脚本/日志原件；见下方边界 |
| T32 | 三件原制品来源路径明确；wheel/sdist安装日志、三个doctor无home副作用、三个close=validated和上游验证汇总相互一致 | 原件未提供完整分发driver/逐条cwd元数据，部分隔离条件依赖汇总；完整skills CLI与其他平台矩阵仍未通过 |
| T25/T26/T29 | 原生owner模块及受控错误路径已有部分结果，原始失败trace可读 | owner测试面仍失败，不能仅凭部分用例成功闭合整项 |
| T10/T11/T34 | 准确登记未执行 | 冷下载/中断、跨进程模型缓存锁、真实宿主、真实E5推理及安装矩阵没有新增通过证据 |

主测试面原始结果为249项、11failure/20error/2skip；开发面42项、1failure/1error。
整体`dev/check.py`退出1。单独通过的后续命令不能改写整体失败；与托管CI的不同计数亦不合并为唯一失败数。

## 分类更正与证据限界

1. 执行者已撤回跨盘ValueError未捕获的判断。原件与CI一致：ValueError是cause，外层已经是FairyError；
   实际失败是Linux含义的文案断言。保留当前拒绝语义，不按原建议重复加catch，也不为文案把合法原生表示一律拒绝。
2. SQLite清理问题不能一概作为环境限制略过。上一轮已据官方文档、源码和最小试验确认测试连接所有权遗漏；
   后续应同时保留事务提交/回滚语义和确定关闭，不能只把`with connect`机械换成不提交的closing。
3. 原`probes/t14_junction.py`实际将目标放在`home/outside`，位于交付树外却仍在批准home内。
   它证明这些junction被拒绝，尚不满足原任务“目标在home外”的实测范围；不能把源代码的一般拒绝逻辑代替该实测要求。
4. `coverage.json`引用的`probes/t14_junction_deliver.py`缺失；`t32/logs/`实际对应已收录的`t32/`日志，
   后者可明确对账而非认定全部日志缺失。补充所称新探针与runs31/32没有随原包回交，不能据名称假装读过原件。
   这些差异保留为下一轮正式用例/证据覆盖要求；不再要求重复传原ZIP或不断为旧探针往返补件。

## 下一轮集中修正的四个机制

| 机制 | 修正方向与必须保留的保证 |
|---|---|
| 测试资源生命周期 | 为测试自建SQLite连接明确事务与close所有权，覆盖异常退出；不靠GC、清理重试或吞WinError32；产品正常close语义保持 |
| 工具与环境发现 | 由当前解释器、上游uv定位和实际venv布局生成真实工具夹具；去掉维护者`.venv`、POSIX目录及Python路径常量依赖，版本期望回到pin入口 |
| 表示与断言语义 | 规范成员路径继续POSIX，原生文件系统路径按Path语义比较；错误按稳定代码/拒绝性质检查，不把另一平台文案当通用承诺 |
| 原生能力与可重复验证入口 | 明确POSIX权限/symlink可用条件，提供有实际覆盖的Windows junction/权限测试；目标放到home外，四个位置ordinary/repair均验证。额外探针纳入正式owner测试/入口，命令、程序与结果可对账 |

以上是有限测试/CI机制修正范围，尚未实施，不是新产品架构或新增兼容层。
修正后统一复跑本机和两平台CI，并由Windows端复验正式原生用例；T10/T11/T34另按原计划执行。
当前没有据本轮原件确认新的核心产品缺陷，但完整检查失败不可忽略，不合并、不发布、不关闭四条Issue。

本机证据位于忽略目录`.evaluation/windows-acceptance/return2-20261108/`，包含原ZIP、路径映射/逐件校验、
原始成员、补充评论与独立评估；旧15件初步查收证据及更早97件验收证据保持原样。
本次只更新查收记录/导航与交接文档范围，不修改产品、锁、版本或兄弟仓。
