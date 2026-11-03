# 返工复验剩余项 A/B/C/REG-01 修复记录

日期：2026-11-03。依据：[2026-11-03 返工复验](../../optimization/2026-11-acceptance/recheck-2026-11-03/README.md)
及 [剩余修复与复验门](../../optimization/2026-11-acceptance/recheck-2026-11-03/remaining-work.md)。

## 修复

- **SPEC-02**：既有 bag 的实际 payload 集合与账本 snapshot 成员集合严格相等；回执与从当前
  task/revision/seq/投影生成的完整回执做规范化比较，覆盖 goal/outcome/reviews 等全部字段；
  额外成员、伪造回执、换任务/seq、重封 manifests 均拒绝。
- **REG-01**：成员文件用 `hashlib.file_digest` 流式摘要，存储内容用新增 `Store.hash_ref()`
  的 `blobopen` 流式摘要；不再 `read_bytes()` + `store.get()` 双份物化。8/32 MiB 既有 bag
  复验 tracemalloc 峰值约 2.16 MiB，与文件大小无关。
- **ROOT-02**：准备改为锁定 `huggingface_hub.snapshot_download`，显式传 `repo_id`、固定
  `revision`、`cache_dir`、允许文件模式和 `force_download`；已有目录校验失败时强制重取。
  固定目录 SHA256 门和离线查询路径保留。
- **ROOT-04**：maintain 在源任务记录决定并关联 child；defer 后 no_change 清除当前 todo；
  新增无需 TASK 的 `todos` 发现入口；新增 `governance` 范围和候选发现，任务可用
  `governance_scope` 自动固定 adopted constraint refs；结构化字段进入 profile 字段清单。

## 验证与限界

新增/更新测试覆盖额外 payload、伪造 receipt、流式复验、maintain/child/todos、治理 scope、
快照下载 kwargs 和固定模型离线消费。完整检查结果见当前进度；真实宿主/跨平台/长期收益仍为
明确限界。本轮不修改已关闭项的历史结论，不代签独立接受。
