# fairy 入口、阶段工作包与 prepare-delivery 交付记录

日期：2026-11-02。工作树基准：`aaa9d3d930b94b7a46d9e47e0a226557c6340b43`，未提交。
对象：[W03 实施进度](../../optimization/2026-11-implementation/README.md)。
本记录覆盖 W03 的实现与自查；原会话独立验收与最终接受仍未发生。

## 实现与影响

技能目录迁移为唯一 `skills/fairy/`，frontmatter `name: fairy`；项目、Python 包、CLI 和品牌仍为
AstroFairy/astrofairy。宿主默认提示改为 `$fairy`，插件清单指向 `./skills/fairy`；没有旧名
转发技能、别名或第二入口。pyproject、governance、CI、便携 ZIP、元数据、开发工具、文档和测试
路径统一；便携 ZIP 根目录改为 `fairy/`。冻结设计/复核/准备记录的原始身份保留，当前链接检查
对这些历史基准显式豁免。

`SKILL.md` 直接包含运行/恢复、约定细化、必要问题、成员发布、`prepare-delivery`、检查/失败处置、
BagIt 交付、短任务示例和条件参考；不以 6500 字节上限裁剪必要步骤。`next` 输出 stage packet v1：
task/revision/seq、动作、精确 `payload` 模板、`completion` 和 `recovery`；模板由当前约定和已记录
输出生成，占位内容不是证据或副作用授权。机械问题给出 `check` 载荷，语义问题给出 `review` 载荷。

CLI `prepare-delivery` 按显式成员计划流式捕获工作区文件、发布完整快照并运行机械检查。它复用
摘要匹配的既有输出，工作区文件缺失但已有对应输出时按已捕获内容接续；中断错误返回 task/seq、
已完成和剩余成员。组合不原子、不自动语义通过、不关闭任务。

同时更新安装检查脚本到协议 9 的 revise/report/publish/check/review 流程；CI 增加 vendored BagIt
交付 wheel 安装步骤。

## 检查与限界

执行者 root 完成变更及影响域自查；未安排独立复验，不代签 W08 或最终接受。
新增 7 项运行测试覆盖唯一 fairy 身份、stage packet 模板/完成/恢复、机械问题载荷、prepare-delivery
捕获/发布/检查、CLI、中断复用与剩余接续、非法计划/关闭任务拒绝、组合不自动语义通过。

完整 `.venv/bin/python -B dev/check.py` exit 0：168 项运行测试、19 项开发测试通过；
依赖锁/官方原件、vendored BagIt 身份、元数据、技能格式、Ruff、mypy 和文档链接通过。
规模 10155 字节/2519 行。未做真实原生宿主发现、`skills` 安装器路径、真实模型遵循率、
费用/延迟或跨平台验收；W04–W08 义务未注销。

## 接续

W04 接入 LanceDB/FastEmbed 本地混合检索、固定模型 profile、结构切分、代次/epoch 同步和学习投影。
