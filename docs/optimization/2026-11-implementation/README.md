# 整体优化实施进度

**2026-11-03 最终复验：本轮技术验收通过。原10项及 REG-01 全部关闭，无剩余已确认技术阻断。**
详见[最终技术验收](../2026-11-acceptance/final-2026-11-03/README.md)及逐项记录。
原会话收尾统一学习源决定/子任务事务，并补齐新增事件的恢复引用链，经独立故障、并发、
治理、交付和恢复复验通过。最终195项运行测试收集（默认跳过1项、另行真实冒烟通过），
20项开发测试及完整规范检查通过；wheel/技能 ZIP 隔离复测及源码包重建一致性通过。
维护者已于本轮技术验收后授权提交发布，按 [0.1.0a2 发布说明](../../releases/v0.1.0a2.md)和
[发布流程](../../guides/releasing.md)推进；实际发布状态以 GitHub Releases 为准。

下文保留执行方各批次申报及当时待复验状态；当前独立结论以顶部链接为准。
前次[七项关闭、三项未关及一项回归](../2026-11-acceptance/recheck-2026-11-03/README.md)、
[初验返工](../2026-11-acceptance/README.md)和原回交证据保持原样。

依据：[已完成独立技术检查的方案](../2026-11-plan/README.md)。
执行分工及接手入口：[另一会话实施任务书](handoff/README.md)；原会话保留最终独立验收与收尾。
本轮按维护者进入实施的意图推进可逆代码工作，未提交、推送或发布。历史设计检查和发布报告
仍保留原始基准；其中“源码未变”是当时事实，不描述本轮工作树。

## 执行方批次记录：2026-11-03 定向返工 A/B/C/REG-01

### A：交付权威绑定与流式校验

- 既有 bag 的 payload 实际集合必须等于账本 snapshot 的 `data/<path>` 集合，额外/缺失成员
  均拒绝；不再只相信 bag 自己重封的 manifest。
- 回执按当前任务投影重新生成并做完整规范化比较，覆盖 goal、outcome、reviews、criteria、
  结果和执行事实；只改几个身份字段或重封 receipt/manifests 不能通过。
- 成员文件与存储 BLOB 使用流式 SHA256 与 `Store.hash_ref()` 校验，不整文件物化；8/32 MiB
  既有 bag 的复验 tracemalloc 峰值约 2.16 MiB，与文件大小无关。

### B：真实下载接口与固定 revision

- `FastEmbedder.prepare()` 改为直接调用锁定依赖 `huggingface_hub.snapshot_download`，传入
  `repo_id`、固定 `revision`、允许文件模式和 `cache_dir`；路径已存在但校验失败时使用
  `force_download=True` 显式重取，不再依赖 FastEmbed 构造器丢弃 kwargs 的路径。
- 下载后仍以固定目录和三份声明文件 SHA256 为消费门；普通查询使用 `specific_model_path` +
  `local_files_only=True`，tokenizer 同源；空库不准备模型。

### C：学习决定、待办与治理候选

- `learn decision=maintain` 在源任务记录 `learning_decision` 并关联 child task；源 seq 前进，
  `next`/inspect 可追溯。
- defer 后 no_change 不再保留旧 todo；晚于 defer 的决定解决该待办。
- 新增 `Workshop.todos()` 和 CLI `todos`，无需先知 TASK 即可跨任务发现遗留待办。
- 新增 `Library.governance()` / `Workshop.governance()` 和 CLI `governance`，按 scope 从已采用
  constraint 资产呈现结构化适用性/依赖/失效字段；任务 spec 可用 `governance_scope` 自动把
  当前范围规则固定到约定，完成前仍须 `asset.read` 固定引用；未知适用性交给 host 判断。
- 检索 profile 的 chunking 字段清单加入 applicability/dependencies/invalidation，按影响重建投影。

### 复验实测

- 192 项运行测试 + 19 项开发测试通过；新增流式内存、额外/伪造交付、maintain/todos 和治理
  scope 合同测试。
- 重新真实 E5 留出：混合 Recall@10 1.000、nDCG@5 0.9671（全文 0.975/0.9658）；学习闭环
  复跑形成/复用/修订/退役/不变路径。
- 仍保留宿主、跨平台、原生插件、冷模型首次下载和长期真人/团队收益限界；本轮只关闭定向
  返工门，不代签独立接受。

## 前序批次：独立验收返工 RW1–RW8（已提交复验，部分项由上一轮复验继续）

### 根因修复

- **完整交付意图**：`prepare-delivery` 先持久化完整成员计划与角色，再逐成员记录进度；`next`
  在计划不完整时返回 `prepare_delivery` 和全计划，只传 remaining 仍恢复全计划；改变计划明确
  拒绝；`complete` 要求计划路径/角色/媒体类型都在当前快照。
- **权威导出**：实际写出 `BagIt-Version: 1.0` 并重生成 tagmanifest；既有同序号 bag 额外核对
  task/revision/seq、快照、回执、成员集合、逐成员摘要与账本字节。自洽重封/换放其他任务 bag
  被拒绝；BagIt 的进程 cwd 修改由进程级锁串行化。
- **失败重评**：复用仅限无待处置失败的 `content` 作用域；A→B→A 产生真实新检查，`replaces`
  保留旧失败历史并处置当前失败。
- **模型准备**：空/损坏缓存由显式 `assets search --refresh` 以固定 revision 下载并逐文件 SHA256
  校验；普通查询使用固定目录和 `local_files_only=True`，tokenizer 同源；空库不准备模型。
- **两路融合**：全文/向量各自按资产去重并保留原排名后再加权 RRF；受控 FTS[A,B] +
  vector[B,C,D,A] 的 2:1 结果 B>A。
- **学习与治理**：资产可选结构化 applicability/dependencies/invalidation 并进入投影；
  交付后提供 maintain/defer/no_change，defer 成为可见 todo；任务约定可固定 adopted governance
  refs，完成前必须 `asset.read` 固定；未知适用性仍由 host 判断。
- **可移植分发**：完整路径与每级目录前缀统一 casefold；技能内新增 `references/operation.md`，
  打包器校验全部包内相对链接；技能 ZIP 自包含恢复入口。

### 复验实测

- 189 项运行测试 + 19 项开发测试通过；新增 10 项返工合同测试。
- 真实 E5 留出复测：混合 Recall@10 1.000、nDCG@5 0.9671（纯全文 0.975/0.9658，纯向量
  1.000/0.8851，旧基线 0.200/0.200）；正文独有 nDCG 0.9262 对仅元数据 0.4861。
- 学习闭环复跑：形成 0.322 s；首次复用搜索 8.203 s（含模型加载）；修订 1.188 s；退役
  0.175 s；不变 0.151 s 完成且源历史不变。
- 恢复复跑：3 任务/3 快照/11 块/1 stable 资产恢复前后一致，三任务交付字节相同。
- 固定安装器、fresh wheel、fresh ZIP、wheel/ZIP 重建在最终源码上重跑；旧 return 保持只读。

真实宿主轨迹、Windows/macOS、原生插件宿主、冷模型首次下载与长期真人/团队收益仍为明确限界。
原验收的 10 项发现逐项根因修复，待原会话复验及维护者裁定。

## 前序批次：W07 分发、恢复与文档收口（实现完成，跨平台/原生宿主有限）

### 固定安装器与 fresh 安装

- 使用官方 `skills@1.7.4`（Node 22.23.2）在本机对 Codex、Claude Code、Cursor、GitHub Copilot、
  Gemini CLI 五个目标各做项目级复制安装；每例从复制目录用 `python -I` 运行 `doctor`、建任务、
  发布成员、机械检查、语义审查和完整交付。五例均通过，布局分别落在对应应用的技能目录。
- 新建独立 venv，按 runtime/delivery/search 三个锁定文件安装，再安装本轮 wheel；从 `/tmp`
  运行安装包的 `doctor`（搜索/交付/SQLite 均 ready），完成一个任务并生成 BagIt 回执。便携
  `fairy.zip` 解包到独立目录后用同一 fresh venv 的 `python -I` 运行 `doctor`，通过。
- 可选 `.claude-plugin/plugin.json` 结构、版本和 `skills/fairy` 路径已核对；原生插件市场托管
  安装/更新没有执行，保持 unknown。Windows/macOS 原生宿主未测。

### 制品、锁与恢复

- 构建 wheel `astrofairy-0.1.0a1-py3-none-any.whl`、sdist 和便携 `fairy.zip`；runtime/
  delivery/search 锁、vendored BagIt wheel、模型 profile/API 快照、插件清单的路径/字节/SHA256
  已登记到本地证据。wheel 内包同源，fresh 安装后导入路径为 venv 的 site-packages，不指向工作树。
- `dev/verify_recovery.py` 建立 3 个任务（含两版快照、嵌套目录、候选验证任务）和 1 个 stable
  资产；备份、恢复到全新 home 后 `audit_state` 的 tasks/events/blobs/assets 完全一致，三个任务
  重新交付的全部字节与恢复前相同，资产仍为 stable。未知写入/外部状态仍未声明为可恢复。

## 前序批次：W06 检索质量与学习净收益（实现完成，宿主行为证据缺口已记录）

### 封存语料与真实模型留出评测

- 新增封存夹具 `dev/retrieval_eval/af-retrieval-v1.json`（SHA256
  `82b95326…`）：12 个多语言方法/工作流资产、12 条调参查询、20 条正例留出查询（长中文/
  短词/同义/中英混合/正文独有/精确编号/适用性）和 4 条无合适方法查询；留出标签在最终运行前
  固定。评测脚本 `dev/evaluate_retrieval.py` 使用真实本地 FastEmbed E5-large ONNX 重建索引，
  不借人造向量。
- 评测模式覆盖加权 RRF 混合、纯全文、纯向量和旧式元数据词重叠基线；另用相同资产元数据但
  占位正文的独立库比较“加入正文”的收益。权重只在 12 条调参查询上选择（全文 2:1），留出集
  只作最终复核。
- 最终留出结果：混合 Recall@10 = 1.000、nDCG@5 = 0.9658；纯全文 0.975/0.9658；纯向量
  1.000/0.8851；旧基线 0.200/0.200。混合 nDCG 与成熟全文对照持平且 Recall 更高；正文独有
  5 条查询的混合 nDCG 从仅元数据的 0.4861 提升到 0.9262。作用域/类型过滤 3 个用例无违规。
- 调参集混合结果 1.000/0.9923。无合适方法的 4 条查询仍会返回最近候选；自动拒用属于宿主/
  模型判断，本地检索不冒充“无方法”的证明。
- 资源：24 个资产/两库构建 2.609 s；全量投影 44.918 s，仅元数据投影 26.223 s；首查询
  0.433 s；热混合查询均值 0.204 s（全文 0.017 s、向量 0.182 s、旧基线 0.001 s）；真实
  模型加载后进程峰值 RSS 4,165,528 KB。模型缓存已存在，首次下载/冷进程未重测。

### 学习闭环与宿主行为边界

- `dev/evaluate_learning.py` 实际执行形成→采用→搜索/读取→修订→退役→不变路径：形成 0.328 s
  （源任务 2 次计数调用）；首次复用搜索 7.335 s（含模型加载），复用任务 2 次计数 + 1 次
  免费读取；修订 1.541 s 后搜索返回新头；退役 0.267 s 后旧批准头重新可见；不变维护任务
  0.203 s 完成且源历史不变。语义通过由执行者夹具判断，不是真人审查；单轮形成/复用未证明
  长期或团队净收益。
- 匹配的直接/技能行为用例冻结在 `dev/retrieval_eval/af-behavior-v1.json`（普通问答不建任务、
  单文件/多文件、修订、未知写入恢复），但本机没有可执行的宿主模型/会话通道，未运行、未伪造
  轨迹。恢复条件：在同一宿主/模型/权限/材料下安装本技能并记录加载、动作、首反馈、总时间、
  人工干预和会话证据；在此之前 V01/V03 的宿主遵循率、真实 token/费用/延迟保持未验收。

## 前序批次：W05 资源处置与校准（实现完成）

### 单一有类型资源配置

- 43 项处置的数值集中到冻结的 `Limits` dataclass；每个字段带预算编号、单位与消费者，`schema`
  导出完整清单。命令 JSON 16 MiB、普通语义文本 1 MiB、单内容 256 MiB、任务捕获总量 2 GiB、
  流块 1 MiB、回包 24 KiB、content.read 24576 字符、工具定义 3 MiB、单 Schema 1 MiB、
  Schema 图 65536 状态、资产正文 16 MiB、摘要/描述 4 KiB、路径 4096 字节、错误 4 KiB、
  控制标量 128 字节及文档内部块/扇出/缓存参数均有实际消费者。
- 检索默认短名单 8、候选池每路 100；普通 CLI 搜索页默认 50、单页最多 200，`cursor` 绑定
  查询、作用域、类型、来源代次、profile、表名/版本/epoch；能力目录默认 12、最多 100，同样
  提供游标。变化后的索引或参数不能被静默拼页。
- `content.read` 与 `asset.read` 为免费上下文读取，仍记录调用但不扣工作额度；模型请求、
  `asset.search`、机械检查、写入和捕获继续计数。`free_calls` 与 `used_calls` 分开展示。
  大资产正文不再在 24 KiB 处只返回指引，统一由回包文档/免费读取续读。
- SQLite 主/文档/备份忙碌等待统一 30 秒；文档初始化锁 30 秒；每库备份截止 300 秒且 CLI
  `backup --deadline` 可显式收紧；备份 128 页/步、忙睡 0.05 秒，manifest 16 KiB、恢复复制
  1 MiB。安装验证子进程 600 秒；资产导入有界读取后显式超限拒绝。
- 移除项保持移除：问答无累计硬限、无 6500 字节/1500 行提交门；只保留规模统计与职责审查。

### 真实校准结果

测量脚本 `dev/measure_resources.py` 在 Linux aarch64、Python 3.12.13、SQLite 3.53.0、
12 CPU、约 15 GiB 内存主机执行，结果保存在
`.evaluation/optimization-implementation/w05-resource-calibration.json`（本地证据，随最终返回打包）：

| 工作负载 | 实测 |
|---|---|
| 单文件 32/128/256 MiB 捕获 | 0.255 / 0.900 / 1.473 s；峰值 RSS 35.4 / 35.5 / 35.7 MB |
| 三文件 32+128+256 MiB | 2.627 s，436,207,616 字节，峰值 RSS 36.3 MB |
| 8×256 MiB 任务聚合 | 恰好 2,147,483,648 字节通过（20.788 s）；再加 1 字节返回 `limit`；峰值 RSS 36.9 MB |
| 24 次计数写 + 40 次免费读取 | 1.209 s；used 24 / free 40；未触发 128 预警 |
| 近 1 MiB Schema | 接受 1,044,600 字节（0.086 s）；超限 0.007 s 拒绝 |
| 锁竞争 | 等待 0.241 s 成功；busy timeout 30 s |
| 3 任务备份 | 0.912–1.143 s；33.6 MB 库对应 33.6 MB 备份 |

真实宿主 token、货币费用与整场对话时间为宿主管理，本地无法取得，记录为 unknown；不以本地
调用数或峰值内存替代。数据库/备份数据来自去重内容，备份增长与唯一字节一致。

## 前序批次：W04 检索与学习投影（实现完成）

### 检索依赖与固定模型 profile

- 检索依赖单独锁定：`dev/search-requirements.in` 的 38 个精确版本、官方 PyPI 元数据快照和
  `skills/fairy/scripts/requirements-search.lock` 机器校验；不混入核心 runtime 锁。
- 固定默认模型 `intfloat/multilingual-e5-large`（Qdrant ONNX 转换原件），记录源仓库、修订
  `ac6781cd…`、`model.onnx`/`model.onnx_data`/`tokenizer.json` 的 SHA256、维度 1024、
  512 token 上限、`query: `/`passage: ` 前缀和归一化。`dev/model_profiles/` 保存 API 原件
  快照并由 `dev/check_model_profile.py` 与运行时代码对账。
- 模型缓存只由显式 `assets search --refresh` 准备；普通搜索不下载或启动模型。空库不启动模型；
  缺模型/索引/分词器返回 `search_not_ready` 和接续方法。实际缓存文件已核验与记录哈希一致。

### 投影代次与混合查询

- 存储格式升 10，新增只读派生表 `search_projection`（epoch、source_generation、profile、
  LanceDB 表名/版本、更新时间）；索引写完成后再在主库事务提交指针。
- 资产事件全局序号作为 source generation；只为每个 scope/name 的最新 trial/stable 头建投影，
  候选和退役版本不进入普通发现。
- 内容按名称、摘要、标签、输入、参数、工作流步骤、正文和证据做结构切分；使用固定模型实际
  tokenizer 和 480 token 预算，长单元分窗保留覆盖与 locator，不静默截断。
- LanceDB 0.41.0 建立 ICU BM25 全文索引，使用固定 E5 向量和按资产排名的加权 RRF（全文 2:1，
  初始精确向量查询）；嵌入按 profile+文本摘要缓存，重复投影只补新块。W06 仅在调参查询上选择
  权重，再以封存留出集复核。
- 查询先在 SQLite 短读快照取得 G/指针/活跃头，要求指针 G 恰等于 G、epoch/profile 一致，
  释放事务后用独立 handle checkout 记录的表版本；过滤使用完整资产 ref，返回来源代次/
  profile/表版本/命中 locator。索引落后、版本丢失、profile 变化或恢复旧库均显式
  `search_not_ready`，刷新可重建；旧表版本保留。
- `Library`、`asset.search`、`assets search`（默认 8、最多 200、`--scope`/`--kind`/
  `--refresh`）和 `doctor` 搜索状态接入；学习/提案/采用/退役事件通过 asset generation
  自动驱动下一次显式投影。

## 前序批次：W03 可执行主文与阶段工作包（实现完成）

### 唯一 fairy 入口与包同源

- 技能目录迁移为唯一 `skills/fairy/`，frontmatter `name: fairy`；项目、Python 包、CLI 和品牌仍为
  AstroFairy/astrofairy。宿主默认提示改为 `$fairy`，插件清单指向 `./skills/fairy`；不建立旧名
  转发技能、别名或第二入口。
- pyproject、governance、开发工具、CI、便携 ZIP、元数据生成器、文档和测试路径统一到 fairy；
  便携 ZIP 根目录改为 `fairy/`，交付 wheel 随技能目录分发。
- 冻结的设计/复核/准备记录不改写；当前文档链接检查对这些历史基准显式豁免，保留其原始身份。

### 完整主文与阶段工作包

- `SKILL.md` 直接包含运行/恢复、约定与 provisional 细化、必要问题、成员制作与发布、
  `prepare-delivery`、机械/语义检查、失败处置、BagIt 交付、短任务示例和条件参考入口；
  不以字节上限裁剪必要步骤。
- `next` 输出 stage packet v1：`task`/`revision`/`seq`、当前动作、精确 `payload` 模板、
  完成条件 `completion`、恢复身份 `recovery`，以及现有 agreement/输出/快照/角色/失败状态。
  模板由当前约定和已记录输出生成，占位文本/角色/靶标/verdict 不是证据，也不授权副作用。
- 阶段包覆盖 refine/produce/publish/review/repair/check/close/resolve_pending 等动作；
  机械问题给出 `check` 载荷，模型审查才给出 `review` 载荷；历史细节通过免费 read 续读。

### prepare-delivery 组合与恢复

- CLI `prepare-delivery TASK --members plan.json` 按显式成员清单流式捕获工作区文件、发布完整
  快照并运行适用机械检查；逐动作保留既有事件和调用，不新建业务解释器。
- 已存在且内容摘要匹配的输出会复用；工作区文件缺失但已有对应输出时按已捕获内容接续；
  中断错误返回 task/seq、已完成和剩余成员，重试只做未完成工作。
- 组合不原子、不自动语义通过、不关闭任务；必需角色/语义准则仍由 `next` 的完成条件约束。

## 前序批次：W02 内容与交付闭环（实现完成）

### BagIt 原件与交付

- 采用官方 bagit 1.9.0 sdist，使用固定构建链（Python 3.12.13、pip 25.0.1、setuptools 84.2.1、
  wheel 0.48.0、setuptools-scm 10.3.4 等）在隔离环境生成标准 wheel；原件/构建/输出 SHA256、
  构建命令和版本登记在 `dev/vendor/bagit-1.9.0/manifest.json`，分发副本和交付锁绑定同一摘要。
- 交付在私有暂存目录生成标准 BagIt 1.0 目录：`data/` 放全部正式成员，根目录放 bagit.txt、
  SHA256 载荷清单、标签清单、bag-info.txt、receipt.json 和简明 README；由 bagit-python 实际
  生成并执行完整字节校验，不使用 fast 校验。
- 校验通过后同文件系统原子重命名到 `deliveries/<task>/<seq>/`；同序号目录已存在时重新完整
  校验并幂等返回，不覆盖；迟到事实生成新序号目录，旧交付保留。任务目录使用原生 file lock
  串行交付，不依赖 SQLite 写事务。
- 无快照的 cancelled/failed 关闭仍生成带空载荷清单和回执的有效 BagIt 目录；单文件交付额外
  提供直接文件链接，多成员交付提供每个成员的直接链接、bag 根、回执和说明。
- 损坏载荷、缺文件、多载荷文件、额外标签文件、标签内容变化和符号链接均在重新校验时拒绝；
  生成失败不发布混合目录，保留原状态并可重试。

### 流式捕获与聚合边界

- 文件捕获、哈希、存储和导出使用 1 MiB 流块与 SQLite `blobopen`/`zeroblob`，私有临时文件，
  不再把大文件整体物化；单内容 256 MiB、单任务唯一内容总量 2 GiB，超限在调用结果中明确拒绝。
- 初始附件在任务事务内流式捕获并校验聚合上限；模型报告/文本写入也进入同一任务聚合检查。
- 输出观察和成员发布使用存储长度校验，不通过整文件读取取得字节数。
- 审计/备份/恢复继续覆盖全部历史快照与成员引用；多快照、多成员恢复后可重新生成 BagIt 交付。

## 前序批次：W01 目标合同与单源（实现完成）

### 资源策略基础

- `ResourcePolicy` 使用标准库冻结 dataclass，默认预警/最终调用限额为 128/1024；CLI 支持
  `--resources FILE`，Python 接受验证后的策略对象，删除旧 `budget` 参数而不保留别名。
- 任务初始事件记录有效策略及确定 JSON 的 SHA256 指纹；修改源配置文件或任务约定不能更改
  既有任务策略。重开、重放、状态包、检查和关闭使用同一份记录。
- `next`/`inspect` 显示预警和剩余额度，大回包的控制信息保留预警；耗尽后仍可补交已有结果，
  权限、未知写入和必要检查不因资源放宽而豁免。
- 移除累计三次提问限制，保留一次一个待答对象；主动用户指示继续保留并推进约定修订。
- 移除主文 6500 字节及核心 1500 物理行硬门，保留真实测试收集、类型、风格和文档检查，
  将规模作为审查统计输出；没有把核心逻辑迁出原职责文件规避计数。

### 内容、成员与快照

- 内容仍以 SHA256 标识原始字节；成员为 `{ref, path, bytes, media_type, role}`，以规范
  相对路径区分。同一摘要可以对应多个成员，字节去重与成员身份分别成立。
- 快照为版本化格式 1 的成员清单，按规范路径排序并以确定 JSON 摘要标识；角色等验收字段
  参与身份，顺序调整不产生虚假内容修订。
- 发布接收完整成员清单，在事务内校验每个成员均为已观察输出或已有快照成员，并核对字节数
  和存储内容；单文件只是单成员快照。旧 `publish ref` 命令已删除，不保留别名。
- 交付导出全部正式成员到各自规范相对路径，回执包含快照身份、成员、职责覆盖、检查、
  未决失败和执行完整性。BagIt 全量生成/校验与中断恢复仍由 W02 接入。

### 准则作用域与检查身份

- 准则新增 `scope`（`content`/`member`/`collection`）与可选 `target`：
  内容靶标绑定摘要，成员靶标绑定路径和完整成员描述，集合靶标绑定完整快照或显式路径子集。
- 约定新增必要交付角色 `required_roles`；缺角色、靶标不存在或检查集合为空均不能完成。
- 审查记录绑定任务 revision、准则定义指纹、checker 固定定义、作用域和确切靶标；
  纯内容机械检查在准则/工具合同/参数/内容/revision 一致时可复用，`check` 返回 `reused`。
- 语义审查绑定当前快照；新快照不继承语义或集合级通过。未替代失败跨重发、改名、角色/媒体
  变化保持可见并阻塞必要完成；当前靶标的新实际机械检查或显式语义 `replaces` 才能替代。
- 候选验证任务以 `candidate` 角色种子成员启动；采用要求当前快照包含确切候选成员，且
  `package-json` 内容检查和 `asset-fitness` 成员审查均绑定该确切内容/成员。候选仅出现在
  集合中不能采用。

### 路径与约定细化

- 新增 pathvalidate 3.3.1 固定依赖及官方原件快照；相对路径要求 NFC、正斜线、可移植平台规则、
  大小写折叠唯一、无文件/目录冲突、无绝对/父级/控制字符/保留名；非 NFC 输入返回更正建议。
- 默认准则标记为 provisional；未细化的默认约定不能完成。`revise` 接受 `required_roles` 并
  清除 provisional；仅 provisional 标记变化的重复修订不推进 revision。
- 协议/存储格式为 9，旧格式在 DDL 前拒绝，不迁移或覆盖旧数据。

## 完成范围与剩余工作

W01–W07 的实现与自查覆盖 V07/V08/V10/V11/V12/V06/V13/V14/V15/V23/V04/V05/V22/V16/V17/
V18/V19/V20/V21/V24 及 W03 入口/阶段包/组合、W04 投影代次、W05 43 项资源处置与真实测量、
W06 真实 E5 留出检索与本地学习闭环、W07 五目标安装/fresh wheel/ZIP/全快照恢复，但未由原
会话独立验收。W08 仅做证据准备。宿主行为遵循率、V01/V03、真实 token/费用/整场时间、
Windows/macOS 与原生插件宿主仍未验收，不能据当前自查声称整轮完成。

## 验证

完整执行 `.venv/bin/python -B dev/check.py`，exit 0：179 项运行测试、19 项开发测试通过；
依赖锁/官方原件、vendored BagIt 身份、检索依赖与模型 profile、资源 Limits 清单、元数据、
Agent Skills 校验、Ruff、mypy 及文档链接均通过。W06 另有真实 E5 留出评测与学习闭环脚本
结果，见上文和本地证据文件。规模统计只报告数值，不以规模代替架构质量。
W01 正反例覆盖：同字节多路径/媒体、路径规范化与冲突、必要角色、三种作用域、空成员集合、
失败跨重发/改名/角色变化保留与当前检查替代、纯内容复用、语义快照绑定、候选精确采用、
provisional 细化及快照顺序无关身份。
W02 正反例覆盖：多成员 BagIt 生成/完整校验/回执/直接链接、载荷/标签损坏/缺文件/多文件/
额外标签拒绝、工作区变化不影响交付字节、生成失败无混合发布并可重试、并发交付单 bag、无快照
关闭的空载荷 bag、8 MiB 流式捕获与 256 MiB/2 GiB 边界拒绝、两快照多成员备份恢复和重交付。
W03 正反例覆盖：唯一 fairy 身份/无旧目录、stage packet 模板与完成/恢复字段、机械问题给 check
而非模型 pass、prepare-delivery 捕获/发布/检查、CLI 组合、中断后已完成成员复用与剩余接续、
非法计划/关闭任务拒绝、组合不自动语义通过。
W04 正反例覆盖：独立检索锁与官方快照校验、模型 profile 与运行时常量对账、空库/缺模型/
缺分词器/索引落后/版本丢失/profile 变化/恢复旧库的 `search_not_ready`、只投影最新试用/稳定
头、候选/退役不进入普通发现、RRF 全文加向量结果合并、作用域/类型过滤、结果上限与 locator、
显式刷新重建与旧表版本保留；真实 E5 冒烟测试以显式环境变量运行并通过（默认跳过）。
W05 正反例覆盖：Limits 清单与 schema 导出一致、1 MiB 文本与 1 MiB Schema 边界、256 MiB/
2 GiB 聚合通过及超一字节拒绝、24 次计数加 40 次免费读取、content.read 24576 字符上限、
免费计数不扣额度、搜索/目录游标分页与参数变化拒绝、默认 8/50/12/200/100、备份截止与锁参数；
真实测量见上节并记录宿主 token/费用/整场时间为 unknown。
W06 证据：真实 E5 留出混合 Recall@10 1.000、nDCG@5 0.9658（全文对照 0.975/0.9658，
向量 1.000/0.8851，旧基线 0.200/0.200）；正文独有 5 条 nDCG 0.9262 对仅元数据 0.4861；
过滤 3 例 0 违规；无匹配查询仍需宿主判断。学习形成/复用/修订/退役/不变路径实际执行并记录
调用与时间；直接/技能行为用例已冻结但因无宿主通道未执行，明确保留 V01/V03 证据缺口。
W07 证据：skills@1.7.4 五目标复制安装并完成脚本交付；fresh venv 安装 wheel 后 doctor ready
并完成 BagIt 交付；fairy.zip 在独立目录 doctor ready；全快照恢复前后 3 任务/30 事件/11 块/
1 资产一致，三个任务交付字节相同，资产仍 stable；wheel/sdist/ZIP/三个锁/BagIt/模型 profile
的字节与 SHA256 已登记。原生插件宿主与 Windows/macOS 未执行。

未进行真实宿主模型行为/费用/延迟评测，未声称这些未来验收已通过；原生宿主发现与
`skills` 安装器路径保留为 W07/V24 的待实测项。
原先存在的项目讲解文档 overlay 已逐字比对保留，本批更新其协议/快照/BagIt/入口/阶段包/检索说明。
审查记录见[W01 代码交付](../../audit/changes/2026-11-02_member-snapshot-contracts.md)、
[W02 代码交付](../../audit/changes/2026-11-02_bagit-delivery.md)、
[W03 代码交付](../../audit/changes/2026-11-02_fairy-stage-packets.md)和
[W04 代码交付](../../audit/changes/2026-11-02_search-projection.md)和
[W05 代码交付](../../audit/changes/2026-11-02_resource-calibration.md)和
[W06 代码与评测交付](../../audit/changes/2026-11-02_retrieval-learning-evaluation.md)和
[W07 分发与恢复交付](../../audit/changes/2026-11-02_distribution-recovery.md)。

下一条路径：W08 最终源码/证据封存与回交目录；完成后停止改动，等待原会话独立验收。
