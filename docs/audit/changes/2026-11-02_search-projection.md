# 本地混合检索、固定模型与投影代次交付记录

日期：2026-11-02。工作树基准：`aaa9d3d930b94b7a46d9e47e0a226557c6340b43`，未提交。
对象：[W04 实施进度](../../optimization/2026-11-implementation/README.md)。
本记录覆盖 W04 的实现与自查；原会话独立验收与最终接受仍未发生。

## 实现与影响

检索依赖独立成组：`dev/search-requirements.in` 固定 38 个精确版本，`dev/search_snapshots/`
保存官方 PyPI 元数据原件并校验 SHA256，`dev/lock_search.py` 生成
`skills/fairy/scripts/requirements-search.lock`。检索依赖不混入核心 runtime 锁；CI 与
`dev/check.py` 校验锁和快照身份。

默认模型固定为 `intfloat/multilingual-e5-large`（Qdrant ONNX 转换原件），记录源仓库、修订
`ac6781cd…`、`model.onnx`/`model.onnx_data`/`tokenizer.json` 的 SHA256、1024 维、512 token
上限、`query: `/`passage: ` 前缀和归一化。`dev/model_profiles/` 保存 API 原件快照，
`dev/check_model_profile.py` 与 `_search.py` 的运行时常量双向对账。模型缓存只在显式
`assets search --refresh` 时准备；普通查询不下载或启动模型，空库不加载模型，缺模型、缺分词器、
缺索引、索引落后、表版本丢失、profile 变化或恢复旧库均返回 `search_not_ready` 和接续方法。

存储格式升 10，新增只读派生表 `search_projection`（epoch、source generation、profile、
LanceDB 表名/版本、更新时间）。资产事件全局序号作为 source generation；只为每个 scope/name
的最新试用/稳定头建投影，候选与退役版本不进入普通发现。内容按名称、摘要、标签、输入、参数、
工作流步骤、正文和证据结构切分，使用固定模型实际 tokenizer 和 480 token 预算，长单元分窗并
保留 locator，不静默截断。LanceDB 0.41.0 建 ICU BM25 全文索引，搭配固定 E5 向量和按资产排名的
加权 RRF（全文 2:1，初始精确向量查询）；嵌入按 profile+文本摘要缓存，重复投影只补新块。

查询先在 SQLite 短读快照取得 G/指针/活跃头，要求指针 G 恰等于当前 G、epoch/profile 一致，
释放事务后用独立 handle checkout 记录的表版本；过滤使用完整资产 ref，返回来源代次/profile/
表版本/命中 locator。索引写完成后才提交指针；刷新可重建，旧表版本保留。`Library`、
`asset.search`、`assets search`（默认 8、最多 200、`--scope`/`--kind`/`--refresh`）和
`doctor` 搜索状态接入；学习/提案/采用/退役事件通过 asset generation 自动驱动下一次显式投影。

主文、宿主/学习/review/runtime 参考、架构、操作、理解文档、双语 README 同步更新为协议/存储
格式 10，并说明检索入口、模型准备、投影代次和故障接续。

## 检查与限界

执行者 root 完成变更及影响域自查；未安排独立复验，不代签 W08 或最终接受。
新增 12 项检索测试（默认 11 项运行、1 项真实 E5 冒烟显式跳过）：空库/缺模型/缺分词器/
索引落后/表版本丢失/profile 变化/恢复旧库的 `search_not_ready`、只投影最新头、候选/退役排除、
RRF 合并、作用域/类型过滤、结果上限与 locator、显式刷新与旧表保留。真实 E5 冒烟以
`ASTROFAIRY_TEST_E5=1 ASTROFAIRY_MODEL_CACHE="$PWD/.cache/fastembed"` 单独运行通过
（8 项、9.587 s），缓存文件 SHA256 与 profile 一致。

完整 `.venv/bin/python -B dev/check.py` exit 0：173 项运行测试、19 项开发测试通过；
依赖锁/官方原件、vendored BagIt 身份、检索依赖与模型 profile、元数据、技能格式、Ruff、mypy
和文档链接通过。未测量检索质量（Recall@10/nDCG@5）、256 MiB 峰值、真实宿主行为、费用/延迟
或跨平台安装；游标分页（B16 剩余项）未实现。W05–W08 义务未注销。

## 接续

W05 对 43 项资源处置接入真实消费者并测量文件 32/128/256 MiB、聚合、schema、锁和备份路径，
冻结默认值；检索质量与行为验收留在 W06。
