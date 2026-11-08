# 平台、准备状态与交付恢复实施（W1–W5）

日期：2026-11-08。基准：`c330e72b56bd3a3f5486054addc1b59e8990dae8`。
状态：实施执行者完成 W1–W5 与自检；未提交、未推送、未发布、未关闭 Issue；
W6 独立验收、维护者接受和发布裁决尚未发生。本记录是执行者自检，不是原会话验收结论。

授权：维护者指示另一 agent 按[专项方案](../../repairs/2026-11-platform-readiness-delivery/README.md)
实施，原会话承担 W6。[ADR-0012](../../adr/0012-platform-readiness-and-delivery-observation.md)
为设计权威，[验收矩阵](../../repairs/2026-11-platform-readiness-delivery/validation.md)为验收规范。
该授权不包含提交、推送、发布、外部消息、关闭 Issue 或修改兄弟仓库。

## 实施内容

- W1 依赖锁：删除两套手写闭包生成器与旧诊断 JSON，新增单一开发入口 `dev/lock_dependencies.py`
  与数据配置 `dev/dependency-profiles.toml`。`update` 用官方 uv 0.13.7 universal 解析
  （`--universal --python-version 3.12 --generate-hashes --only-binary :all:`，显式官方索引、
  无解释器下载）；`check` 离线核对输入/策略摘要、provenance、发行版元数据快照、wheel-only 哈希和
  universal 条件闭包。解析器身份取 `requirements-dev.lock` 单源（`uv==0.13.7`）。
  生成锁保留 pip requirements + hash 格式；core 增加 `packaging==26.3`（诊断 marker 求值的上游 API），
  search 仅补 `colorama==0.4.6 ; sys_platform == 'win32'` 与
  `win32-setctime==1.2.1 ; sys_platform == 'win32'` 两个条件分支；已核对既有无条件版本零漂移。
  生成 `_dependency_manifest.json`（格式 2，保留 marker）替换旧扁平诊断清单。
- W2 检索准备：模型清单从三件扩展到 FastEmbed 0.9.1 实际消费的六件
  （`model.onnx`、`model.onnx_data`、`tokenizer.json`、`config.json`、
  `tokenizer_config.json`、`special_tokens_map.json`）；`assets prepare` 为共享显式准备服务，
  每次重新流式 SHA-256 校验并绕过 `_verified_dir` 历史成功，模型缓存级锁串行化并发准备；
  `assets search --refresh` 复用同一服务并在准备后读取新代次。空活跃库显式 refresh 返回
  `projection.state=empty` 与准备元信息，普通空库查询不加载模型。`doctor` 分层报告
  dependencies/model/projection/recovery；新增 `doctor --verify-search`（流式校验、不下载、不推理、
  不建库）。模型 profile 增加消费者审计（fastembed 版本、wheel SHA256、必需/可选但固定的文件分类），
  `dev/check_model_profile.py` 校验运行时清单、锁版本与 API 快照。
- W3 交付路径边界：BagIt 暴露的 manifest/tagmanifest key 先按宿主表示转换为规范 POSIX 相对身份，
  再做 payload/tag 分类和集合比较；拒绝绝对/盘符/UNC/逃逸/转换后碰撞。交付从批准 canonical home
  经 `deliveries/task/seq` 到 lock/staging 的每级路径检查符号链接、Windows junction 与 reparse point，
  发布前在原生交付锁内复核；不跟随、不移动 redirect。
- W4 交付与恢复：`State.next_action` 对历史关闭返回 `closed`，不再从 outcome 推导 delivered；
  runtime 组合廉价 `delivery` 观察（`not_closed`/`absent`/`unverified`/`unsafe`）与动作
  `deliver`/`verify_delivery`/`inspect_delivery`（`inspect_conflict` 优先）。协议 11、阶段包 2、
  回执投影 2；回执仅由冻结事件和记录中的 checker 身份生成，当前 checker registry 只进入独立 assessment。
  close、晚到 report/feedback、晚到工具观察/asset_used 与 learn 统一走提交后共享导出；
  导出失败返回 `committed=true`、操作/提交身份、目标与 `deliver` 恢复命令，不回滚事实、
  不伪装工具状态、不要求重放效果。显式 `deliver` 支持 `--expected-seq` 与 `--repair`：
  先构建并完整校验替代包，再隔离坏目录（不删除）后发布；重认 redirect、源库损坏和外部目标为拒绝。
- W5 分发与说明：`governance.toml` 使用单一锁检查并登记原生任务冒烟；CI 矩阵覆盖
  ubuntu-latest 与 windows-latest，安装四类锁后执行 `pip check`、完整检查、原生任务冒烟、构建与
  skill 打包；同步 SKILL、references、guides、README、CONTRIBUTING、AGENTS、STATUS 与专项状态。
  历史发布说明、评审和验收记录保持原基准。

## 已执行检查

- 基线（改动前）：`.venv/bin/python -B dev/check.py` 通过（195 项运行测试收集，默认跳过 1 项真实模型；
  20 项开发测试）。
- 实施后完整检查：`.venv/bin/python -B dev/check.py` 通过；224 项运行测试（默认跳过 1 项真实模型）、
  26 项开发测试；锁一致性（core 10 / search 41）、模型 profile 六件消费者审计、vendored BagIt、
  原生任务冒烟、ruff/mypy、skill 结构与文档链接均通过。
- 专项回归：新增依赖锁负例（条件分支删除/元数据/策略/工具 pin/跨档案版本），检索准备空库/候选/非空/
  六件逐文件缺失与同长损坏/同进程重复验证/并发串行/分层观察，Windows 路径表示注入与碰撞/逃逸拒绝，
  交付祖先/root/target/payload redirect、关闭后导出失败/晚到事实/学习/expected-seq/并发/损坏替换/
  repair 中断与隔离、checker 变更回执稳定、提交前失败、24 KiB 控制字段保留。
- 分发（Linux aarch64 本机）：wheel、sdist、skill ZIP 均重新构建；全新 venv 分别从四类哈希锁和 wheel
  安装、从 sdist 安装、从 ZIP 解包 skill 运行；`pip check` 通过；`doctor` 不创建 home 且分层观察正确；
  最小任务 start→report→publish→check→close→deliver 原生通过并再次以 upstream BagIt 校验。
  actionlint 通过更新后的工作流 YAML。

## 限界与未完成义务

- 未执行原生 Windows；CI 矩阵已准备但本次授权禁止推送，因此没有远端运行记录。W1 的 Windows 分支由
  universal 锁的离线闭包审计验证，不等同于原生安装通过；#1/#3 保持开放。
- 未下载真实冷模型、未运行真实 E5 推理或质量评测；六件校验与空库准备使用受控替身和本地既有缓存证据。
  真实模型集成仍按 validation 的显式义务执行。
- 未执行 Linux x86_64 CI；本机为 Linux aarch64。macOS 与其他解释器版本未验证。
- `dev/check_installation.py`（skills CLI 安装矩阵）与远端平台 job 未在本机执行。
- 单一 receipt 规则变更（投影语义）需要新的投影格式；当前格式 2 的 golden 行为由测试约束，
  但不声称穷尽未来规则。
- 原始证据、命令日志、分发构建与清单位于被忽略的
  `.evaluation/issue-repair-implementation/2026-11-08/`；普通 clone 不含。转交须附清单与 SHA256。

## 状态声明

技术检查、实施、自检、独立验收、提交发布是不同状态。本记录只声明 W1–W5 实施与执行者自检完成并回交；
不声明 W6 通过、产品已接受或 Issue 已修复关闭。
