# 平台、准备状态与交付恢复定向返工

日期：2026-11-08。基准：`c330e72b56bd3a3f5486054addc1b59e8990dae8` 加首轮实施与 W6
验收后未提交工作树。状态：STD01–STD06、SPEC01–SPEC04、GAP01 与 T29/T35 覆盖缺口已修复并自检；
未提交、未推送、未发布、未关闭 Issue；再次独立验收与维护者接受尚未发生。

依据：[W6 首轮结论](../../repairs/2026-11-platform-readiness-delivery/acceptance-2026-11-08/README.md)与
[定向返工清单](../../repairs/2026-11-platform-readiness-delivery/acceptance-2026-11-08/rework.md)。
首轮验收证据、实施回交与历史记录均保持原样；本记录只声明返工与执行者自检。

## 逐发现处置

| ID | 根因处理 | 回归 |
|---|---|---|
| STD01 | uv 子进程改用显式环境白名单；UV_/PIP_/CONDA_/PYTHON*/VIRTUAL_ENV 不再跨边界；保留 PATH、证书、代理等系统/网络必需项；额外传 `--no-sources` | `test_ambient_environment_cannot_reach_the_resolver`：污染环境下锁字节不变 |
| STD02 | 每个来源条目校验官方 `https://pypi.org/pypi/<name>/<version>/json` 身份；`check` 将当前快照清单字节与 provenance `snapshots_sha256` 接线；update 复用条目同样验 URL | `test_source_url_identity_and_manifest_binding_are_checked`（未批准域/摘要漂移/版本错位） |
| STD03 | 新增受身份约束的上游消费者原件目录 `dev/model_profiles/fastembed-0.9.1/`（官方 wheel 内两件源码 + 审计清单）；wheel 身份对照冻结 PyPI 元数据；源码哈希/消费名/六文件集合/锁版本形成重新审计门 | `dev/tests/test_model_profile.py`（零 wheel、源码变更、同步漏项、版本变化） |
| STD04 | 跨 profile 改为同一显式环境单元内比较共同包版本；相同合法 fork 通过，同环境冲突拒绝 | `test_identical_environment_forks_are_accepted_per_cell` |
| STD05 | 显式环境补齐 `platform_release`/`platform_version` 并要求覆盖 packaging 默认环境全部字段；无法表达的目标字段 marker 在锁与依赖元数据中 fail-closed | `test_marker_environment_is_complete_and_host_independent` |
| STD06 | 删除旧 flat manifest 解析/转换分支；update 与 check 只接受现行 format 2，旧格式明确拒绝 | `test_legacy_manifest_is_rejected_by_update_and_check` |
| SPEC01 | 路径安全拒绝改用 `unsafe_delivery`；repair 只处理可重建的 `integrity`/`version`，不吞 `unsafe_delivery`；移动旧树前再次检查整树 | `test_repair_refuses_unsafe_descendants`、边界/恢复测试 |
| SPEC02 | 提交后导出统一捕获 `sqlite3.Error`，保留 task/operation/committed/committed_seq/selected_seq/target/deliver 恢复；CLI 不再降级为无上下文 storage_failed | `test_post_commit_sqlite_export_error_preserves_recovery` |
| SPEC03 | 失败回包使用冻结导出实际选中的 S；选中前失败明确 `selection=unknown`、`selected_seq=null`，不再重读最新 seq 伪造目标 | `test_failure_selection_identity_is_the_frozen_snapshot` |
| SPEC04 | repair 全生命周期跟踪动作；隔离后发布失败与发布后最终复核失败均保留 `completed`/`published`/`quarantined` 与恢复命令；不删除隔离物 | `test_repair_postpublication_failure_reports_progress`、rename 间中断测试 |
| GAP01 | `State.live_checkers` 区分历史投影与当前评估；当前 registry 缺少必需机械 checker 时 live review 不成立、acceptance 报 `missing_checkers` 并 fail-closed；历史 receipt 仍稳定复用 | `test_missing_current_checkers_fail_closed_but_history_stays_valid` |
| T29 | 提交前错误显式 `details.committed=false`；不确定写观察显式 `committed="unknown"`；导出失败仍为 `delivery.committed=true` | `test_precommit_failure_reports_false_explicitly`、`test_unknown_write_reports_unknown_commit` |
| T35 | 新增冻结 event→receipt golden：固定事件、固定 canonical receipt 字节与 SHA；当前 checker 变化不改变历史 receipt | `test_receipt_golden.py` + `fixtures/receipt-projection-2.json` |

## 已执行检查

- 完整 `dev/check.py` 退出 0：235 项运行测试（默认跳过 1 项真实模型）、37 项开发测试；
  lock core 10/search 41、模型消费者审计、vendored BagIt、原生任务冒烟、ruff/mypy、skill 与文档链接通过。
- 定向返工回归 52 项通过（两类锁/消费者测试、交付 hardening、恢复、边界、receipt golden）。
- 分发：wheel、sdist、skill ZIP 由同一候选重新构建；全新 venv 分别安装/解包，`pip check` 通过，
  `doctor` 不创建 home，最小任务 start→…→close→deliver 通过。
- 真实缓存（非下载）：`assets prepare` 六文件 SHA-256、空库 `search --refresh` 返回
  `projection.state=empty` 与准备结果、`doctor --verify-search` 为 `verified` 且未创建 home。

## 限界

- 未执行原生 Windows x64、Linux x86_64 CI、macOS；CI 矩阵只是配置，不是运行证据。
- 未执行真实冷模型下载/中断恢复或真实 E5 推理；只验证既有缓存字节。
- 未执行完整 skills CLI 安装矩阵与真实 host 恢复交互；`dev/check_installation.py` 仍为未执行义务。
- 原验收探针针对已被替换的私有 API；对应场景已转写为本仓红绿测试，原探针与结果不改。
- 再次独立验收、维护者接受、提交发布均未发生；Issue 保持开放。

## 证据

新回交目录：`issue-repair-implementation/rework-2026-11-08/return/`（位于忽略的 `.evaluation/`，
普通 clone 不含；转交须附清单与 SHA256）。首轮回交与 W6 证据未改写。
