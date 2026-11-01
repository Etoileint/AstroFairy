# 权威来源目录

生成视图。元数据单源为 authority-sources.json。
已取得材料用于准备取证。适用性、条款、成熟度与对标结论尚待正式复核。
ISO 目录/摘要不代表取得标准全文。官方实现自述不替代实际效果验证。

| 编号 | 一手来源及类别 | 固定版本 / 取得原件数 | 用途及限制 |
|---|---|---|---|
| S01 | [Agent Skills specification](https://agentskills.io/specification)。Agent Skills maintainers。specification | URL 版本。其余依取得时间与 SHA256 定位 / 5 | 目录、元数据、依赖与按需披露。共享格式不保证宿主执行或模型质量 |
| S02 | [Agent Skills reference implementation](https://github.com/agentskills/agentskills)。agentskills/agentskills maintainers。implementation | 69ef37e9424c / 2 | 参考校验与元数据解析。工具检查范围不等于规范全部语义 |
| S03 | [Matt Pocock skills](https://github.com/mattpocock/skills)。Matt Pocock。reference implementation | 59db609eb1e1 / 8 | 全部参考实践和当前分发实现。参考选择不自动成为行业强制标准 |
| S04 | [skills installer](https://github.com/vercel-labs/skills)。vercel-labs/skills maintainers。implementation | d8eca76d5dbe / 5 | 安装发现、复制、目标应用和更新。安装器目标列表不证明应用实际兼容 |
| S05 | [Claude Code skills](https://code.claude.com/docs/en/skills)。Anthropic。host contract | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 技能加载和厂商扩展。只约束该宿主及所核验版本 |
| S06 | [Codex skills](https://developers.openai.com/codex/skills/)。OpenAI。host contract | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 技能发现、脚本和可选元数据。只约束该宿主及所核验版本 |
| S07 | [Cursor skills](https://cursor.com/docs/skills)。Cursor。host contract | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 技能发现与调用。实际支持仍需应用内试验 |
| S08 | [VS Code agent skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills)。Microsoft。host contract | URL 版本。其余依取得时间与 SHA256 定位 / 1 | Copilot 技能发现及集成。VS Code 与独立 CLI 的行为分别核验 |
| S09 | [Gemini CLI skills](https://geminicli.com/docs/cli/skills/)。Google Gemini CLI maintainers。host contract | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 技能发现、激活及信任约定。实际支持仍需应用内试验 |
| S10 | [ISO/IEC/IEEE 42010:2022](https://www.iso.org/standard/74393.html)。ISO/IEC/IEEE。standard catalog | URL 版本。其余依取得时间与 SHA256 定位 / 1 | 架构描述对象、关注点与关系。目录和摘要不支持全文条款合规判断；不是架构实现质量认证 |
| S11 | [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html)。ISO/IEC。standard catalog | URL 版本。其余依取得时间与 SHA256 定位 / 1 | 质量视角覆盖入口。目录和摘要不支持全文条款合规判断 |
| S12 | [SCXML Recommendation](https://www.w3.org/TR/2015/REC-scxml-20150901/)。W3C。specification | URL 版本。其余依取得时间与 SHA256 定位 / 1 | 状态、事件、转移与终止设计。比较语义，不要求星灵使用 XML 或声明 SCXML 合规 |
| S13 | [SQLite transactions](https://www.sqlite.org/lang_transaction.html)。SQLite project。official documentation | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 事务、隔离与并发写入。底层事务保证不自动延伸到外部副作用 |
| S14 | [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html)。SQLite project。official documentation | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 崩溃一致性、磁盘与文件系统假设。需核验当前连接模式及实际故障行为 |
| S15 | [SQLite FTS5](https://www.sqlite.org/fts5.html)。SQLite project。implementation | URL 版本。其余依取得时间与 SHA256 定位 / 3 | 成熟全文检索候选。全文检索与语义检索分别评价，需核对扩展可用性 |
| S16 | [Python 3.12 sqlite3](https://docs.python.org/3.12/library/sqlite3.html)。Python Software Foundation。official documentation | URL 版本。其余依取得时间与 SHA256 定位 / 3 | 连接、事务和异常契约。文档接口契约仍需结合实际 SQLite 版本 |
| S17 | [Python 3.12 os](https://docs.python.org/3.12/library/os.html)。Python Software Foundation。official documentation | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 文件权限、替换及同步接口。原子替换、持久性与竞态隔离分别核验 |
| S18 | [RFC 8259 JSON](https://www.rfc-editor.org/rfc/rfc8259.txt)。IETF / RFC Editor。specification | URL 版本。其余依取得时间与 SHA256 定位 / 1 | JSON、编码、互操作性与重复键。本地规范化算法不自动等于跨实现规范化标准 |
| S19 | [JSON Schema 2020-12 core](https://json-schema.org/draft/2020-12/json-schema-core.html)。JSON Schema project。specification | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 成熟数据契约和校验方案。自有命令字段表不应被误称为完整 JSON Schema |
| S20 | [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/)。Pydantic maintainers。implementation | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 成熟类型与数据校验候选。需比较保证、依赖与维护成本，尚未选用 |
| S21 | [Temporal workflows](https://docs.temporal.io/workflows)。Temporal。implementation | URL 版本。其余依取得时间与 SHA256 定位 / 1 | 持久执行、工作流和重放候选。服务型运行环境与本地 skill 不同，按职责可比维度评价 |
| S22 | [Temporal activity execution](https://docs.temporal.io/activity-execution)。Temporal。official documentation | URL 版本。其余依取得时间与 SHA256 定位 / 3 | 副作用、执行结果和重试。不能据此宣称外部动作普遍恰好执行一次 |
| S23 | [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)。LangChain maintainers。implementation | URL 版本。其余依取得时间与 SHA256 定位 / 4 | 检查点、任务状态与跨任务记忆。比较当前版本语义和部署依赖，尚未选用 |
| S24 | [LangGraph durable execution entry (redirects to persistence)](https://docs.langchain.com/oss/python/langgraph/durable-execution)。LangChain maintainers。implementation | URL 版本。其余依取得时间与 SHA256 定位 / 1 | 恢复、重放和副作用分离。原生模型编排和会话宿主需明确适配差异；原入口当前重定向到 persistence，正式复核按实际目标页取证 |
| S25 | [Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)。Microsoft Azure Architecture Center。reference architecture | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 事件、投影、历史重建及模式成本。参考架构不等于强制标准或采用建议 |
| S26 | [PROV-DM](https://www.w3.org/TR/prov-dm/)。W3C。specification | URL 版本。其余依取得时间与 SHA256 定位 / 4 | 实体、活动、主体及来源关系。不要求完整实现 PROV，作为来源语义对照 |
| S27 | [OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/)。OpenTelemetry / CNCF maintainers。specification documentation | URL 版本。其余依取得时间与 SHA256 定位 / 1 | 执行链与耗时观测候选。遥测不等于审计认证，不要求新增常驻服务 |
| S28 | [Retrieval-Augmented Generation paper](https://arxiv.org/abs/2005.11401)。Lewis et al. original authors。primary research | URL 版本。其余依取得时间与 SHA256 定位 / 1 | 检索增强生成原始研究入口。论文不规定本项目必须用向量数据库 |
| S29 | [pgvector](https://github.com/pgvector/pgvector)。pgvector maintainers。implementation | 3fc275dab278 / 2 | 向量、近邻与混合检索候选。PostgreSQL 依赖及适用规模需比较，尚未选用 |
| S30 | [Qdrant hybrid queries](https://qdrant.tech/documentation/concepts/hybrid-queries/)。Qdrant maintainers。implementation | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 混合检索、融合和重排候选。实现能力与效果评价分开；尚未选用 |
| S31 | [Git objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)。Git / Pro Git original authors。official documentation | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 成熟内容寻址及对象身份对照。内容哈希不提供外部见证或执行真实性保证 |
| S32 | [pyproject.toml specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/)。PyPA。specification | URL 版本。其余依取得时间与 SHA256 定位 / 2 | Python 分发元数据与构建。Python 包是可选渠道，不能代替 skill 目录验证 |
| S33 | [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)。Semantic Versioning authors。specification | URL 版本。其余依取得时间与 SHA256 定位 / 3 | 插件版本与发布语义。还需核对 Python 版本规范及实际宿主消费者 |
| S34 | [GitHub Actions secure use](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)。GitHub。official documentation | URL 版本。其余依取得时间与 SHA256 定位 / 3 | CI 引用、权限和发布边界。CI 通过不代表语义质量或所有宿主通过 |
| S35 | [LLM prompt injection prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)。OWASP Cheat Sheet Series maintainers。primary guidance | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 外部材料与资产的信任边界。指导不是绝对安全证明，需实际攻击与授权边界检查 |
| S36 | [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt)。Apache Software Foundation。license | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 许可证和分发义务。参考项目采用不同许可时分别核验 |
| S37 | [XState implementation](https://github.com/statelyai/xstate)。Stately / XState maintainers。implementation | 060cd63378b4 / 2 | 成熟状态建模及解释器候选。JavaScript 环境、规模与适配成本需单独评价 |
| S38 | [BEIR retrieval evaluation](https://arxiv.org/abs/2104.08663)。Thakur et al. original authors。primary research | URL 版本。其余依取得时间与 SHA256 定位 / 1 | 跨任务检索评价设计。研究基准不能直接代替星灵任务样本 |
| S39 | [LangGraph / LangChain memory](https://docs.langchain.com/oss/python/langgraph/memory)。LangChain maintainers。implementation | URL 版本。其余依取得时间与 SHA256 定位 / 3 | 记忆分类、检索与维护候选。记忆存储不直接证明学习有效或用户能力提升 |
| S40 | [Ten usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)。Jakob Nielsen / Nielsen Norman Group。primary guidance | URL 版本。其余依取得时间与 SHA256 定位 / 2 | 反馈、用户控制、错误恢复与可见性。启发式需要实际用户行为验证，不是本项目认证 |
| S41 | [NIST SP 800-218 SSDF](https://csrc.nist.gov/pubs/sp/800/218/final)。NIST。standard publication | URL 版本。其余依取得时间与 SHA256 定位 / 5 | 成熟开发与供应链实践入口。按适用责任审查，不整套引入重型治理 |
| S42 | [ATAM: Method for Architecture Evaluation](https://www.sei.cmu.edu/library/atam-method-for-architecture-evaluation/)。Kazman, Klein, Clements / CMU SEI。primary architecture research | CMU/SEI-2000-TR-004 / 2 | 场景、质量属性、架构风险与取舍的成熟评估方法。原始报告不规定星灵必须采用其完整组织形式；适用性待正式复核 |
| S43 | [LangGraph source implementation](https://github.com/langchain-ai/langgraph)。LangChain maintainers。implementation | eb8ec111b3e9 / 2 | 成熟编排与状态执行候选源码。未选用，需比较职责、保证、部署和维护成本 |
| S44 | [Temporal Python SDK source](https://github.com/temporalio/sdk-python)。Temporal maintainers。implementation | 64b700540a14 / 2 | 成熟编排与状态执行候选源码。未选用，需比较职责、保证、部署和维护成本 |
| S45 | [Python 3.12 argparse](https://docs.python.org/3.12/library/argparse.html)。Python Software Foundation。official documentation | Python 3.12 / 2 | CLI 参数、子命令与错误语义。库接口契约不代表业务协议正确 |
| S46 | [Python version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/)。PyPA。specification | URL 版本。其余依取得时间与 SHA256 定位 / 2 | Python 版本与插件语义版本映射。需明确预发布和消费者差异 |
| S47 | [RFC 8785 JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.txt)。IETF / RFC Editor。specification | URL 版本。其余依取得时间与 SHA256 定位 / 1 | 跨实现规范化与内容身份对照。RFC 为 Informational；当前 Python JSON 排序不自动等于 JCS 合规 |
| S48 | [OpenAI Agents SDK source](https://github.com/openai/openai-agents-python)。OpenAI。implementation | cd26bbbc5284 / 2 | 成熟编排与状态执行候选源码。未选用，需比较职责、保证、部署和维护成本 |
| S49 | [MCP tool contracts and execution errors](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)。Model Context Protocol official specification and maintainers。specification and official type definitions | 2026-07-28 current clauses; 2025-11-25 comparison and type definitions / 4 | 扩展工具发现、输入契约、安全可修复错误及提示/权限区分。本地runner不是MCP端点；只按相同职责比较，不强制采用传输/所有字段 |
| S50 | [Python 3.12 mimetypes](https://docs.python.org/3.12/library/mimetypes.html)。Python Software Foundation。official documentation | Python 3.12 documentation; actual tested interpreter 3.12.13 / 1 | 文件扩展名到MIME提示的成熟标准库机制。不检查真实文件格式、渲染、事实或语义质量 |
| S51 | [RO-Crate structure and provenance](https://www.researchobject.org/ro-crate/specification)。RO-Crate community official specification。specification | 1.3 current long-term release on official index; scoped structure/provenance reading / 3 | 多文件/来源/软件版本及有界元数据组合候选。基础crate不是穷尽清单，不证明语义/来源事实；本轮未宣称RO-Crate合规或执行validator |
| S52 | [RFC 8493 BagIt](https://www.rfc-editor.org/rfc/rfc8493.txt)。RFC Editor; BagIt authors。Informational RFC | BagIt 1.0, RFC8493, October 2018 / 1 | 文件清单完整性、逐文件checksum及complete/valid区分。只核opaque payload bytes/fixity，不证明语义、业务正确或抵抗主动篡改 |
| S53 | [SLSA artifact verification](https://slsa.dev/spec/v1.2/verifying-artifacts)。SLSA official specification maintainers。approved specification guidance | v1.2 fixed Approved comparison baseline, not asserted latest / 1 | 核对证据subject与实际artifact摘要，区分来源信任与对象一致性。借同职责比较，不要求通用技能采用构建签名/等级，不声明SLSA认证 |
| S54 | [Python 3.12 pathlib](https://docs.python.org/3.12/library/pathlib.html)。Python Software Foundation。official documentation | Python3.12 / 1 | 路径解析、符号链接与归属判断。resolve加归属比较不是敌对竞争隔离或多租户权限 |
| S55 | [Python 3.12 tempfile](https://docs.python.org/3.12/library/tempfile.html)。Python Software Foundation。official documentation | Python3.12 / 1 | 复用mkstemp独占创建、私有模式和清理责任。原子临时文件创建不证明最终目录持久化或Windows账户ACL |
| S56 | [Claude Code permissions](https://code.claude.com/docs/en/permissions)。Anthropic official Claude Code documentation。official documentation | Retrieved current official page 2026-10-29; content SHA anchored / 1 | 宿主原生allow/ask/deny及执行层授权职责比较。仅官方文档选段，未本机执行该应用或证明所有宿主一致 |
| S57 | [Guidelines for Human-AI Interaction (CHI2019 original and HAX)](https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/)。Amershi et al.; ACM CHI2019; Microsoft Research original author repository。original research and official author guidance | CHI2019 DOI10.1145/3290605.3300233; official current HAX index retrieved2026-10-29 / 3 | 初始能力/限制、时机/相关信息、调用/退出/纠正/疑问/解释/近期记忆与谨慎适应的原作者交互评估依据。原研究验证指南，不验证本项目；非ISO或产品认证；PDF只读表及讨论等选段，真实成员负担和长期效果待证 |
| S58 | [Python 3.12 clocks and microbenchmarking](https://docs.python.org/3.12/library/time.html)。Python Software Foundation。official documentation or original engineering guidance | Python3.12 documentation as retrieved / 2 | 区分monotonic经过时间/CPU、重复测量原向量和基线。微基准和进程墙钟不提供模型token/价格/真实UI时延或总体统计保证 |
| S59 | [Building effective agents: simplicity, economy and ACI](https://www.anthropic.com/research/building-effective-agents)。Anthropic engineering authors。official documentation or original engineering guidance | Original2024 engineering guidance with current tooling-change notice / 1 | 简单组合、成本与效果权衡、工具格式和接口防错。历史工程经验不是2026所有API标准或性能认证；当前页面明确工具生态已改变 |
| S60 | [Unicode literal matching: Python casefold and SQLite lower](https://www.sqlite.org/lang_corefunc.html)。Python Software Foundation and SQLite maintainers。official documentation or original engineering guidance | Python3.12 and current SQLite core-function docs / 4 | 核对查询与元数据两侧归一化的实际语义。casefold/lower并非等价；本轮不宣称完整Unicode等价规范、所有分词或语义质量通过 |
| S61 | [LangMem memory extraction and feedback optimization](https://github.com/langchain-ai/langmem)。LangChain / LangMem maintainers。official documentation and fixed source implementation | ae6f15fb76603fa2c86ad05f1ecb4a110fa8060b and current concepts page / 4 | 比较事实/经历/行为方法、成功与纠正信号、已有记忆合并、反馈轨迹和存储接线。选段和固定指南比较；未安装执行依赖，不以官方收益描述认定本项目长期有效 |
| S62 | [Common Workflow Language workflow reference](https://www.commonwl.org/v1.2/Workflow.html)。Common Workflow Language project。official specification | v1.2 reference page, retrieval timestamp and content digest / 1 | 对照输入类型、数据依赖、步骤run、requirements与hints；不要求方法资产冒充执行引擎。R09按原件选段比较；未运行规范一致性套件、执行器或制品注册表，不宣称Astro资产格式符合该标准 |
| S63 | [OCI content descriptors and artifact manifests](https://github.com/opencontainers/image-spec/tree/v1.1.1)。Open Container Initiative。official specification | image-spec v1.1.1 / 2 | 对照内容摘要、描述符、制品类型及多件依赖分发的职责。R09按原件选段比较；未运行规范一致性套件、执行器或制品注册表，不宣称Astro资产格式符合该标准 |
| S64 | [SQLite online backup and VACUUM lifecycle](https://www.sqlite.org/backup.html)。SQLite maintainers。official documentation | Official current docs, retrieval timestamp and SHA256 / 2 | 比较一致数据库备份、压紧、逻辑删除和保留政策的不同职责。R10选段与无并发写者的本机API恢复；不证明断电/任意工作区备份或完整保留政策 |
| S65 | [OpenAI Codex app-server protocol](https://developers.openai.com/codex/app-server/)。OpenAI。primary documentation | retrieval identity and explicitly stated runtime version / 1 | 原生skills/list发现及初始化。不替代模型调用或全部桌面应用认证 |
| S66 | [SQLite window-function version floor](https://sqlite.org/windowfunctions.html)。SQLite maintainers。primary documentation | retrieval identity and explicitly stated runtime version / 2 | 实际SQL窗口语法能力及引入版本。未运行旧SQLite整栈；不是SQL全特性兼容证明 |
| S67 | [GitHub Copilot native Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)。GitHub。primary documentation | retrieval identity and explicitly stated runtime version / 1 | CLI/IDE/云端原生技能位置与边界。各应用表面分别验证，不由VSCode文档替代全部GitHub产品 |
| S68 | [Python3.12 unittest discovery](https://docs.python.org/3.12/library/unittest.html)。Python Software Foundation。primary documentation | Explicit document version and retrieval identity / 2 | 测试导入、发现与包标记规则。不代替实际收集对账，不由所有unittest特性推项目覆盖 |
| S69 | [Git hook execution contract](https://github.com/git/git/blob/v2.51.0/Documentation/githooks.adoc)。Git project maintainers。primary documentation | Explicit document version and retrieval identity / 1 | 可执行位、core.hooksPath、pre-commit非零拒绝。固定v2.51文档；本机2.20.1仅验证脚本，不冒称新子命令或commit派发 |
| S70 | [Agent evaluation engineering: tasks, trials and graders](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)。Anthropic official engineering。industry engineering guidance | Actual retrieved page SHA and explicit specification versions; rolling framework docs not a pinned executed release / 1 | 任务/尝试/结果与代码/模型/人类评分、能力及回归的区分。实践指导非强制标准；不以文章陈述代替本项目效果测量 |
| S71 | [Inspect AI tasks and scorers](https://inspect.aisi.org.uk/tasks.html)。Inspect AI maintainers, official inspect.aisi.org.uk documentation。mature evaluation framework documentation | Actual retrieved page SHA and explicit specification versions; rolling framework docs not a pinned executed release / 2 | 数据集/求解/评分/epoch/日志职责，成熟工具备选。未在本轮安装或运行Inspect；文档API不证明本项目达到该框架全部能力 |

原始页、响应目标、SHA256、时间和固定提交见 JSON。原件缓存在本机忽略目录。未随公开分发复制。
可变 URL 的历史内容需要保留原件才能复验。摘要只能说明内容身份。
相同 URL 不保证今后提供相同内容。
正式引用必须补上具体条款/源码位置、支持的主张和适用条件。不能只附项目主页。
