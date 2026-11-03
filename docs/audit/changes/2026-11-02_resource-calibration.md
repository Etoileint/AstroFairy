# 资源配置单源、免费读取与 W05 校准交付记录

日期：2026-11-02。工作树基准：`aaa9d3d930b94b7a46d9e47e0a226557c6340b43`，未提交。
对象：[W05 实施进度](../../optimization/2026-11-implementation/README.md)。
本记录覆盖 W05 的实现与自查；原会话独立验收与最终接受仍未发生。

## 实现与影响

43 项预算处置收敛到冻结的 `_limits.py` `Limits` dataclass；每个字段带预算编号、单位和消费者，
`schema` 导出清单。原散落在 `_contracts`、`_capabilities`、`_store`、`_documents`、
`_maintenance`、`_presentation`、`_runtime`、`_library`、`_search`、`_delivery` 的数值改为引用
单源，包括：命令 JSON 16 MiB、语义文本 1 MiB、内容 256 MiB、任务捕获 2 GiB、流块 1 MiB、
回包 24 KiB、content.read 24576 字符、工具定义 3 MiB、Schema 1 MiB/65536 状态、资产正文
16 MiB、摘要和描述 4 KiB、路径 4096 字节、错误 4 KiB、控制标量 128 字节、文档节点 16 KiB/
2048 字符/扇出 16/缓存 128/键前缀 16/审计块 8192 字符、SQLite 锁 30 秒、文档锁 30 秒、
备份锁 30 秒、备份截止 300 秒、备份 128 页/0.05 秒、manifest 16 KiB、恢复块 1 MiB、
安装 600 秒、交接 16 MiB/1 MiB。安装与交接常量留在开发工具中并以同一数值接入。

`content.read` 与 `asset.read` 标记为免费上下文读取：调用仍写入事件，但 `counted=false`，不计入
`remaining_calls`；`resource_status` 新增 `free_calls`。模型请求、`asset.search`、机械检查、
写入和捕获继续计数。大资产正文不再在 24 KiB 阈值只返回 `read_with`，统一返回完整包，由 24 KiB
回包文档和免费读取续读。`content.read` 请求上限从 6144 提到 24576 字符。

`asset.search` 新增 `cursor`/`next_cursor`：绑定查询、作用域、类型、source generation、profile、
表名、LanceDB 版本和 epoch；参数或索引变化返回 conflict/search_not_ready，不静默拼页。普通
CLI 搜索默认 50、能力目录默认 12 且两者最多 200/100；代理短名单仍默认 8。能力目录游标绑定
查询和目录摘要。`assets import` 读取 16 MiB+1 后显式拒绝，不再把有界读取当作大小校验。

备份 `backup --deadline` 可显式收紧每库截止；源/目标连接、文档初始化、主库连接统一 30 秒
busy 策略；文档节点/扇出/缓存参数经 `Limits` 暴露。移除项保持移除：无问答累计硬限、无
6500 字节/1500 行提交门。

## 实测与限界

新增 `dev/measure_resources.py`，以子进程隔离逐项测量峰值 RSS 和耗时。真实结果（Linux
aarch64、Python 3.12.13、SQLite 3.53.0、12 CPU、约 15 GiB 内存）：
单文件 32/128/256 MiB 为 0.255/0.900/1.473 s，峰值 RSS 35.4/35.5/35.7 MB；三文件
436,207,616 字节为 2.627 s、36.3 MB；8×256 MiB 恰好 2,147,483,648 字节通过（20.788 s、
36.9 MB），再加 1 字节返回 `limit`；24 次计数写加 40 次免费读取 1.209 s，used 24/free 40，
无预警；1,044,600 字节 Schema 接受、超限拒绝；锁竞争等待 0.241 s 成功；3 任务备份约
0.9–1.1 s，33.6 MB 库对应 33.6 MB 备份。证据文件为
`.evaluation/optimization-implementation/w05-resource-calibration.json`，随最终返回打包。

完整 `.venv/bin/python -B dev/check.py` 结果见实施进度记录。新增资源测试覆盖 Limits 清单与
schema 导出一致、1 MiB 文本/Schema 边界、24/12/50 默认值、目录游标、内容读取上限和免费计数；
检索测试覆盖分页游标及参数变化拒绝。真实宿主 token/费用/整场对话时间仍无法取得，明确记为
unknown；没有把本地调用数、缓存或文件时间冒充账单或首反馈。长正文资产接近 16 MiB 的完整
采用验证、跨平台锁行为和真实宿主模型行为不在本批证据内。W06–W08 义务未注销。

## 接续

W06 在固定语料/模型上测量 Recall@10、nDCG@5、正文收益、拒用与学习净收益；W05 只冻结资源
默认与实测资源路径。
