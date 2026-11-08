# 平台、准备状态与交付恢复第二次定向返工

日期：2026-11-08。基准：`c330e72b56bd3a3f5486054addc1b59e8990dae8` 加首轮实施与两轮验收后的
未提交工作树。状态：再次返工清单的 STD01–STD04、SPEC01、SPEC04、T29＋REG02 已按机制边界修复并自检；
未提交、未推送、未发布、未关闭 Issue；再次独立复验与维护者接受尚未发生。

依据：[再次独立复验](../../repairs/2026-11-platform-readiness-delivery/acceptance-recheck-2026-11-08/README.md)
与[再次返工要求](../../repairs/2026-11-platform-readiness-delivery/acceptance-recheck-2026-11-08/rework.md)。
首轮实施回交、首轮返工回交及两轮验收记录与证据均保持原样；本记录只声明本轮返工与执行者自检。

## 逐项处置

| ID | 根因处理 | 回归 |
|---|---|---|
| STD01 | 工具选择、版本/身份探测、执行体摘要与真正 compile 执行共享 `sys.executable -I -m uv` 白名单环境与 `cwd=root`；`PYTHONPATH`/CWD 伪 `uv.py` 不再进入身份探测 | `test_tool_identity_probe_ignores_ambient_modules`；原 `tool-selection-probe.py`：伪模块未执行、选中 `-I -m uv` |
| STD02 | `check` 校验全部保留来源；`update` 开始前比较现有清单字节与 provenance，漂移、非法未选中来源、版本/URL 错位均拒绝，不能由 update 重新盖章；合法新增仍走权威采购后记录 | `test_update_refuses_to_bless_existing_source_drift`（含未选中非法来源）；原 `probe.py` STD02 三负例与 update 复用漂移、未选中来源均拒绝 |
| STD03 | 固定消费者原件与代码内 `FIXED_CONSUMPTION` 六文件义务独立于可改 `consumes`；逐文件核对源码哈希、观察到的消费名与完整集合，同步删除声明不能缩减检验集合；版本/源码变化触发重新审计 | `test_synchronized_omission_is_not_proof`；原 `consumer-effect-probe.py` 证明 config 值真实影响 padding；原 `probe.py` 同步漏项拒绝 |
| STD04 | 按每个环境单元收集所有实际包含该包的 profile 版本再比较，不再取全部 profile 交集；合法 fork 通过，A/B 冲突不因 C 无关包而消失 | `test_partial_profile_overlap_still_compares_involved_profiles`、`test_identical_environment_forks_are_accepted_per_cell`；原 `probe.py` 三 profile 反例拒绝且与首轮冻结函数同判 |
| SPEC01 | `os.walk(onerror=...)` 收集不可遍历子树，无法证明整树安全时以 `unsafe_delivery` fail-closed；不移动、不跟随旧树，外部目标不触碰；普通坏包仍可重建 | `test_unreadable_old_tree_is_not_quarantined_or_followed`（uid 1000 非特权 chmod 0）；原 `unsafe-walk-probe.py` |
| SPEC04 | 进度错误边界从已验 staging 覆盖到返回：pre/post-publication 安全检查、rename、发布后复核、`_links` 失败均携回 `completed`/`published`/`quarantined`/`recovery`；清理自身失败不遮蔽原错误 | `test_postpublication_guard_failure_reports_full_progress`；原 `probe.py` 发布后 lstat 失败保留全部进度 |
| T29 | Store 事务显式区分 BEGIN/COMMIT 失败、已知回滚与无法确认；COMMIT-busy 且成功 ROLLBACK → `committed=false`；确认丢失 → `committed="unknown"`；保留原始 COMMIT 错误作为原因，ROLLBACK 再失败只作为附加元数据。回包区分 `committed`（权威数据库）、`committed_seq`（已提交 invoked）、`effect_state`（外部效果）、`observed`（观察入库），不再输出含义含混的 `commit` | `test_real_commit_busy_after_rollback_reports_not_committed`、`test_lost_commit_acknowledgment_is_explicit_unknown`、`test_commit_error_is_not_masked_by_rollback_failure`；原 `probe.py` 两场景 |
| REG02 | 删除整段 `_precommit` 默认 false 推断；invoked 已提交、外部效果已发生时观察入库失败回包保留 task/call/已提交序号/`effect_state`/`observed=false` 与只读调查动作，不引导重放效果 | `test_observed_append_failure_preserves_invoked_identity_and_effect`；原 `invoke-progress-probe.py` |
| 保留绿项 | SPEC02/SPEC03/GAP01/T35、STD05/STD06 及既有规范子场景未改动，回归继续通过 | 全量运行测试与规范探针 |

## 已执行检查

- 完整 `dev/check.py` 退出 0：241 项运行测试（默认跳过 1 项真实模型）、40 项开发测试；
  锁 core 10/search 41、模型消费者审计、vendored BagIt、原生任务冒烟、ruff/mypy、skill 与文档链接通过。
- 回归增量：本轮新增 6 项运行回归（真实 SQLite COMMIT-busy、确认丢失、ROLLBACK 遮蔽、观察入库失败、
  不可读旧树、发布后安全检查失败）；运行收集由 235 增至 241。
- 验收方规范/方案探针在本候选上重跑：`standards/probe.py`、`real-uv.py`、`tool-selection-probe.py`、
  `consumer-effect-probe.py`，`spec/probe.py`、`unsafe-walk-probe.py`、`invoke-progress-probe.py`
  均给出预期结果；真实 uv 使用离线暖缓存副本，污染环境锁字节不变。
- 分发：由本候选重建 wheel、sdist、skill ZIP 至新证据目录（不覆盖旧 `dist/`）；全新 venv 分别安装
  wheel/sdist，`pip check` 通过，`doctor` 不创建 home，最小任务 start→…→close→deliver 通过；
  提取 skill ZIP 后 doctor 与最小任务通过。
- 真实缓存（非下载）：`assets prepare` 六文件 SHA-256、空库 `assets search --refresh` 返回
  `projection.state=empty`、`doctor --verify-search` 为 `verified` 且未创建 home。

## 限界

- 未执行原生 Windows x64、Linux x86_64 CI、macOS；CI 矩阵只是配置，不是运行证据。
- 未执行真实冷模型下载/中断恢复或真实 E5 推理；只验证既有缓存字节。
- 未执行 junction/reparse 原生负例、跨进程缓存锁、完整 skills CLI 安装矩阵与真实 host 恢复交互。
- 本轮探针由执行者针对当前候选自检；最终独立复验、维护者接受、提交发布均未发生，Issue 保持开放。

## 证据

本轮证据根：`.evaluation/issue-repair-implementation/rework2-2026-11-08/`（位于本机忽略目录，
普通 clone 不含；转交须附清单与 SHA256）。制品在 `artifacts/`，命令日志在 `logs/`，探针与结果在
`selfcheck/`，分发安装与真实缓存工作目录在 `dist-check/` 与 `prepare-home/`、`refresh-home/`。
原三次回交与两轮验收目录未改写。
