# 证据获取与复验

开发者日常检查、历史原件审计和产品效果评测各有范围。先明确要复验哪份结论、哪个源码基准，
再取得对应材料；不要因为工作区里恰好有缓存，就推定新接手者也有。

## 可直接取得的材料

| 材料 | 取得方式与用途 |
|---|---|
| 源码、测试、依赖锁、供应商原件和元数据快照 | 正常克隆本仓；用于开发、构建及普通机械检查 |
| 当前状态、原设计、冻结复核及逐项结论 | [STATUS.md](../../STATUS.md)及其链接；每份结论保留自己的日期、对象和限界 |
| 公开发布的源码版本和四个附件 | [0.1.0a2 Release](https://github.com/Etoileint/AstroFairy/releases/tag/v0.1.0a2)；公开源码归档不包含完整Git历史 |
| 发布提交和标签的 CI | [main](https://github.com/Etoileint/AstroFairy/actions/runs/41628414958)、[tag](https://github.com/Etoileint/AstroFairy/actions/runs/41628640927)；在线日志保存期限由平台决定 |
| 当前可转交的本机原始证据 | 下述维护者持有的校验包；摘要和获取状态登记在 [evidence-index.json](evidence-index.json) |

模型权重、虚拟环境和工具缓存不进Git。普通 `dev/check.py` 不要求真实 E5 权重；启用真实模型
检查或评测前，按[贡献指南](../../CONTRIBUTING.md#validation-levels)准备依赖和固定模型缓存。
普通克隆也不要求存在维护者的外部开发组织。

## 维护者持有的转交包

核对日期为2026-11-05。包名为 `astrofairy-v0.1.0a2-evidence.zip`，确切字节数和SHA256以
[索引](evidence-index.json)为准。本机落点是索引中的 `bundle.local_path`；文件已封装、逐项读回
并校验。它未上传到公开 Release，普通Git克隆不会自动取得。维护者可通过获准的文件通道转交，
接收者先按索引校验；不要把一个尚未公开的本机路径写成公共下载地址。

包的范围：

- 最终技术验收原有50份证据的封存ZIP及其独立身份记录；原ZIP保持字节不变。
- 最后一轮定向返工回交的96份登记证据、源清单和源码ZIP。
- `0.1.0a2` 发布执行记录、固定安装验证、CI状态及下载后核验的四个公开附件。
- 三份来源目录登记的194条快照引用，对应191个不同原件；均按原登记SHA256和字节数核对，
  保留原相对路径。目录为[早期复核](../reviews/authority-sources.json)、
  [实际反馈准备](../optimization/2026-11-use-feedback/sources.json)与
  [整体方案](../optimization/2026-11-plan/sources.json)。

包内 `inventory.json` 登记每个文件的路径、字节数和SHA256；`SHA256SUMS` 同时登记清单及
文件摘要。原工作区相对路径位于 `workspace/` 下。摘要证明字节身份，不证明材料内容正确、
来源真实性或某项业务结论。来源真实性仍结合原目录的权威URL、版本和获取记录判断。

包不包含模型权重、环境、真实任务数据或外部私有开发组织；它也不补称已收录全部早期复核
每一轮的原始执行目录。需要超出本包范围的历史材料时，应按报告引用确认是否另有档案。
无法取得就记录对应结论的复验缺口，不能拿当前重新运行的结果冒充当时原始记录。

## 接收后校验

将取得的文件放到索引所列位置，或在下面的读取代码中显式指定收到的文件。以下操作只读包，
不恢复目录、不运行其中的脚本：

```sh
python - <<'PY'
import hashlib, json, zipfile
from pathlib import Path
index = json.loads(Path('docs/development/evidence-index.json').read_text(encoding='utf-8'))
path = Path(index['bundle']['local_path'])
assert path.stat().st_size == index['bundle']['bytes']
with path.open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == index['bundle']['sha256']
with zipfile.ZipFile(path) as bundle:
    rows = json.loads(bundle.read('inventory.json'))['files']
    assert set(bundle.namelist()) == {'inventory.json', 'SHA256SUMS'} | {row['path'] for row in rows}
    for row in rows:
        assert bundle.getinfo(row['path']).file_size == row['bytes']
        with bundle.open(row['path']) as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256']
print('Bundle and all inventoried files verified')
PY
```

如需恢复原相对路径，先在新的临时目录安全解包并校验，再在独立完整克隆中恢复所需的
`.reference/`、`.evaluation/` 材料。不要覆盖现有工作区、已有证据或业务状态。
历史准备自检可用 `.venv/bin/python dev/check_review_preparation.py --verify-snapshots`；
它核对冻结源码、登记结构和本机来源原件，不是产品符合性检查。

## 重新运行与今后的交接

复跑使用本次明确选定的提交、平台、依赖、输入及新输出目录。真实模型冒烟、检索质量、学习
闭环和恢复的命令入口见[贡献指南](../../CONTRIBUTING.md#validation-levels)。历史包中的脚本
绑定当时源码；运行前阅读其输入、依赖和作用范围，不默认适用于新版本。

新结果应同时留下命令、退出状态、输入/源码身份、实际产物与限界。新一轮证据另建目录及
清单，不重封旧档案来制造旧结果变化。若需新转交包，登记其确切范围、摘要和真实获取通道。
无需把环境、模型权重或所有原始日志塞进Git，也不能只留一个无人可取得的绝对路径。
