# Windows第二轮原件查收与独立验收

日期：2026-11-08。维护者通知Windows机已完成，原会话按
[第二轮任务](../../../handoff/windows-validation/README.md)查收并核验原件。
结论：**本轮约定的Windows原生复测通过，无新增返工项**。这不是原专项整体验收或发布裁定。

## 对象与证据身份

- 交接HEAD：`3645fc6a601b5e162f801d6e62b96c7ee1c8b025`；测试源码候选：
  `6ced5c9a1a59d0f615c0f324564f48955c58fed1`；产品runtime仍等于`c9824b24b1627dd10de70fbcfe028a0dc9dfcfd5`。
- [执行者结论](https://github.com/Etoileint/AstroFairy/pull/5#issuecomment-6727636058)及三片原件
  [1](https://github.com/Etoileint/AstroFairy/pull/5#issuecomment-6727609463)、
  [2](https://github.com/Etoileint/AstroFairy/pull/5#issuecomment-6727609748)、
  [3](https://github.com/Etoileint/AstroFairy/pull/5#issuecomment-6727610061)均已实际取得。
- `windows-round2.zip`：69,575字节，SHA256
  `1a73b09cf6a81bec53b1b73a18919b6bf4bf67f0485cea9d2594a2ea87681b50`。
  严格解码重组后整体摘要匹配；ZIP共63件，除清单自身外62件逐件大小/摘要匹配，路径安全检查通过。
- 验证前后源码身份记录完全一致：377 checks、errors为空，清单摘要为
  `7671d958af0288c2a66be3c2005b637afa567644551762f656a46cf5932bad32`。
  collector、verifier、smoke三份随包程序逐字节等于交接HEAD对应Git blob，未执行收到的脚本。

原件与本机独立核验程序/JSON在忽略目录`.evaluation/windows-acceptance/round2-20261108/`；
普通clone不带本机副本，但可从上述公开PR原始分片按整体身份恢复。
首轮87,226字节旧包及旧失败报告保持原样，不重封、不将旧失败改写成通过。

## 独立核验结果

| 对象 | 原始观察与结论 |
|---|---|
| 环境 | 原生Windows AMD64；platform为`Windows-11-10.0.26100-SP0`；CPython3.12.16 conda-forge构建、项目venv，SQLite3.54.1。执行者友好系统名另称Windows10，保留差异，按原始platform/构建记录，不据此扩大版本认证 |
| 完整检查 | 逐行核出255运行＋42开发、297个不同测试结果；运行248通过/7skip，开发42通过；canonical整体exit0，类型/格式/锁/文档等门均通过 |
| skip | 3项POSIX权限/DAC；2项文件symlink因真实WinError1314；2项真实模型。精确测试名和理由与任务允许范围一致，没有扩大skip |
| 原生安全负例 | 四个home外位置ancestor/task/sequence/payload的ordinary/repair正式owner用例通过；另有ancestor/task/target负例及共同denied-walk用例通过。junction实际执行，不能将文件symlink能力skip解释为目录负例未运行 |
| 原生恢复 | delivery_recovery的18项及storage_errors等owner结果通过；未发现上一轮SQLite清理、工具路径和原生路径断言失败。受控失败仍是对应测试程序的覆盖，不冒称真实宿主交互 |
| 命令原件 | 26条外层命令全部exit0、launch_error为空，时序有效，stdout/stderr齐全；canonical为完整入口，无筛选参数 |
| 原生导入 | lancedb、fastembed、onnxruntime、tokenizers真实导入成功；native doctor的search依赖观察包括Windows条件依赖且issues为空。这不证明模型权重已下载或推理已执行 |
| 源及三制品任务 | native/wheel/sdist/ZIP各8条CLI，全部exit0、时刻位于相应外层命令内；cwd均在checkout外，解释器使用隔离模式；doctor ready且home原先不存在，机械check通过，close返回full validated、seq8，next为verify_delivery |
| 三制品来源 | 每件新venv有创建/哈希安装/pip check日志；wheel/sdist实际模块落在各自venv的site-packages，ZIP使用自身launcher。已绑定的smoke程序还执行上游BagIt校验，整体返回成功 |

本轮native源环境复用前轮准备的venv，不能表述为第二轮重做了全新search哈希安装。
第一轮原件及未变的锁保留其安装证据；以下托管CI另外覆盖新环境core/delivery/search哈希安装。
三制品任务准备core/delivery，sdist另外准备版本钉住的构建工具，不宣称这些最小venv具备search推理能力。
各层命令/测试计数存在嵌套，不累加为独立覆盖量。

## 托管CI与范围推进

再次查询确认同一交接HEAD的[PR run](https://github.com/Etoileint/AstroFairy/actions/runs/42523300428)和
[push run](https://github.com/Etoileint/AstroFairy/actions/runs/42523294898)均success；
各自Linux x86_64/Windows x64的完整检查、smoke、wheel/sdist构建及skill打包步骤均实际通过。
托管Windows与开发机环境独立记录：前者5项skip，后者7项skip，新增两项确为文件symlink权限差异。

本轮补齐Windows完整检查、BagIt及junction原生负例、三制品独立运行的指定缺口。
结合首轮多文件/子目录BagIt原件和既有Linux证据，T04/T13/T14及T32制品子项取得新增原生证据；
不将这些结论扩展为所有重解析点、Windows ACL、其他解释器/平台或整个T32安装矩阵认证。

仍保留原计划未执行项：T10真实冷下载/中断恢复，T11独立进程缓存争用，Windows真实E5推理，
完整skills CLI安装矩阵，以及T34真实宿主的准备/失败调查/交付恢复/学习。
它们是既有集成观察缺口，本轮未发现新产品缺陷；不重新打开已通过的修正或重复索取旧包。

本次只更新查收记录与当前导航，产品代码/测试/锁/版本未改；未合并main、打tag、发布或变更四条用户Issue。
历史验收和[原剩余验证表](../../repairs/2026-11-platform-readiness-delivery/acceptance-recheck3-2026-11-08/remaining-validation.md)
保留冻结时点，当前新增结论以本记录为准。
