# 供料、事实与权威地板

日期：2026-11-08。方案供料，不是修复验收。

## 已执行的基准核验

Linux aarch64 上重新运行隔离源码探针，未改动运行实现：

| 对象 | 源码通道 | 实验通道及限界 |
|---|---|---|
| #1 | `dev/lock_search.py` 的 marker 求值继承宿主环境 | 同一锁在 Linux 生成器通过，Windows 条件下拒绝；缺 loguru 的 colorama/win32-setctime、tqdm 的 colorama；不是原生 Windows 安装 |
| #2 | `_search.refresh()` 无活跃资产时早于 prepare 返回 | 显式 refresh 报 ready、prepare 调用0次、无投影；`page(refresh=True)` 返回空结果 |
| #3 | `_delivery._verify()` 混用 POSIX 文件集与 BagIt 宿主路径，还在转换前分类 tags | 真实有效 BagIt 包通过上游验证；模拟 Windows 清单表示后本项目报同一集合不一致；非原生 Windows |
| #4 | closed 提交在导出前，State.next_action 仅以 outcome 推导 delivered | 注入真实运行入口的导出异常，重开 Workshop 后仍 delivered/无包；重复 close 被拒，显式 deliver 恢复；晚到反馈导出失败也复现 |
| 诊断 | doctor 调用 `_search.status()`，只看依赖版本元数据存在性 | 模型目录不存在时 status 仍 ready=true，而 model_dir 报 search_not_ready；Issue 对 doctor 语义的解释不作为事实采用 |
| P3-D1 | 当前registry注入State，issues进入receipt，影响同seq精确比较 | 不追加事件，替换实际使用的snapshot.check定义后，issues从0到1；上游包仍有效，重复deliver报receipt不符 |
| P4-D1 | 交付只检查bag子树，未保护deliveries祖先 | 隔离临时home的deliveries指向同一fixture内的外部目录，实际close在home外写出包；非Windows junction实测 |
| P4-D2 | 已声明三文件清单未覆盖FastEmbed实际配置消费者；model_dir缓存可被prepare复用 | 官方固定wheel源码与已安装源码一致，明确读取三种额外配置；受控小清单首次验证后改文件，第二次显式prepare仍成功，无下载 |

原始探针、结果和逐文件源码 SHA256 在维护者证据目录
`.evaluation/issue-repair-design/2026-11-08/`。`diagnose.py` 可在基准及准备好的开发环境下以
`PYTHONPATH=. .venv/bin/python -B .evaluation/issue-repair-design/2026-11-08/diagnose.py` 重跑。
它只用隔离临时 home、受控导出失败及 Windows 表示模拟，不下载模型，不接触真实任务。
该目录被忽略，普通 clone 不包含这些原件；转交须连同哈希清单提供，或重建实验并标明为新证据。

## 权威来源及采用边界

逐件 URL、采购时间、字节数与 SHA256 见 [sources.json](sources.json)。原件位于其中登记的
`.reference/2026-11-platform-readiness-delivery/`；下载身份、内容摘要与检验必须分别成立。

| 来源 ID | 地板与对本项目的约束 |
|---|---|
| packaging-markers | packaging 的默认环境是宿主环境；环境覆盖不等于依赖求解。使用官方库，不手写 marker 语法或无限环境枚举器 |
| uv-resolution / uv-cli / uv-pip-compile | uv 提供 universal resolution 与带 marker/hash 的 requirements 输出；universal 时 Python 参数为下界，不能把平台模拟检查冒充原生安装 |
| pip-secure-installs | pin/hash 必须覆盖所有实际安装依赖，wheel-only 禁止隐式源码构建；继续保留哈希安装要求 |
| pylock-spec | PEP751 的 pylock.toml 是标准锁格式。必须比较，但它的存在不要求为本专项增加第二套安装链 |
| packaging-pylock | 官方成熟 pylock 解析/选择 API，可用于标准方案对照；不需自行发明锁格式解释器 |
| python-stat / python-pathlib | Windows junction/reparse与symlink不能混同；安全边界包括批准home下的祖先目录，不仅最终bag根 |
| fastembed-wheel | 从官方已锁wheel核查真实文件消费者，已安装preprocessor源码逐字吻合；不是只看本项目声明清单 |
| model-config / model-tokenizer_config / model-special_tokens_map | 三件JSON直接采购自固定模型revision，内容哈希已登记；未下载权重，未据此宣称真实推理通过 |
| bagit-rfc8493 | RFC8493 是 Informational 的 BagIt1.0格式依据；完整/有效包与本项目权威快照绑定分别核验，不把哈希一致冒充语义正确 |
| python-pathlib | 宿主路径与 as_posix 表示有明确差异；转换发生于适配边界，之后校验规范相对路径 |
| event-sourcing | 不可变事实与可重建投影分离；显式处理投影延迟、幂等及循环；并不要求引入云服务或消息总线 |
| github-matrix | 原生操作系统/解释器 job 执行实际安装与端到端测试，不由 Linux 的 marker 探针替代 |
| hf-download | 固定 revision、显式下载与本地缓存消费的官方接口；不以一次缓存存在冒充内容验证或推理成功 |
| uv-pypi | 官方 PyPI 采购时版本0.13.7及候选 wheel SHA256；开发工具 pin 在实现时进入本仓唯一工具版本来源 |

本项目已提交的 BagIt1.9.0原始 wheel/source 及 manifest 继续作为上游 API 实现依据，
不从第三方转载或模型记忆生成清单规范。

## 成熟工具可行性实验

采购官方 uv0.13.7 的 Linux aarch64 wheel，核对 PyPI 制品 SHA256 后提取执行体。
离线构造三个标准 wheel：根包、仅 Windows 依赖、仅 Python>=3.13 依赖。
实际执行 `uv pip compile --universal --python-version 3.12 --generate-hashes --only-binary :all:`
（加隔离 cache、离线 find-links 与禁止解释器下载），输出同时保留两个条件依赖和 SHA256。

原件：`.tools/uv-0.13.7/provenance.json`；实验命令、stdout/stderr、wheel 和结果在证据目录的
`resolver-fixture/`。该实验支持所需接口能力，不证明项目真实依赖已经锁定、所有平台 wheel 可用或原生安装已通过。
同一离线fixture另执行标准pylock输出，`pylock-command.json`记录退出0，原件为`pylock.probe.toml`；
它支持PEP751方案的可行性比较，不是额外产品锁或新安装链。

## 进入设计的条件

需求轴已在 [scope.md](scope.md)建立；P1独立技术复验通过。
权威原件已采购18件，HTTP403后的重试已成功；本地原件可复算。
P2的独立技术核验结果应进入交付记录；用户保留裁决，不把本页自述当作独立结论。
尚未执行修复或原生 Windows 测试；这些是实施阶段的硬义务。
