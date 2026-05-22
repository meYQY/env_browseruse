# Browser-Use Task Generation Framework

确定性的 browser-use benchmark 题目生成管道。从 WebArena 环境实体库出发，自动生成带有 ground truth 断言和 verifier 模板的结构化任务——**全程不依赖 LLM 做任何逻辑决策**。

## 快速开始

```bash
pip install -r requirements.txt                    # 仅需 PyYAML + requests

PYTHONPATH=src python3 -m pytest tests/ -v         # 76 个测试, ~0.7s, 无需 API key

PYTHONPATH=src python3 -m taskgen.cli generate \
  --count 100 --mock-llm \
  --entities data/normalized/entities.json \
  --output data/outputs/generated_tasks_100.json   # 离线生成 100 道题
```

## 框架做了什么

1. **加载**归一化环境实体库（213 个实体，覆盖 GitLab / Shopping / Forum / CMS 四个环境）
2. **生成** browser-use 任务：通过 13 阶段确定性管道，控制能力维度、难度（L1-L5）、环境、任务模板
3. **产出** ground truth（预期后端状态）和 verifier 模板（DB/API 查询规格），全部基于确定性映射规则
4. **LLM** 仅在 Stage 9 用于自然语言改写，不参与实体选择、GT 生成、验证逻辑等任何决策
5. **执行** 17 项质量检查，任何一项不通过则废弃重试
6. **导出** JSON / CSV / Markdown，并诚实标注验证状态

## 框架不做什么

- 任务**未经后端验证**。所有 verifier 标注为 `execution_status: "not_executed"`，`backend_grounded: false`
- 仅覆盖**状态变更类操作**。查询类和条件分支类任务暂不支持
- LLM **不参与验证**。Ground truth 和 verifier 逻辑完全确定性

## 核心设计原则

| 原则 | 实现方式 |
|------|---------|
| 规则控制事实 | 实体库 + 参数值池（requirement banks） |
| 模板控制结构 | 任务模板注册表（24 个模板） |
| 映射规则控制预期状态 | 确定性 assertion 生成（15 种 action → DB 状态映射） |
| 模板控制验证逻辑 | DB/API checker 模板（assertion 1:1 翻译为查询） |
| LLM 只管语言 | Kimi K2.6 仅做 NL 渲染 |

## 考察维度

- **Memory（信息追踪）**— Agent 需要根据定位条件找到正确的目标实体并执行操作。难度通过定位条件数控制（L1: 0-1 个 → L5: 3+ 个）
- **Long-horizon（多步操作）**— Agent 需要完成跨页面/跨状态的多步操作链。难度通过实体数和操作步数控制（L1: 1 实体 1 步 → L5: 3 实体 9 步）

## 难度模型（L1-L5）

难度在生成**之前**通过结构规则控制，不是生成之后标注。

| 等级 | Memory（定位复杂度） | Long-horizon（操作链长度） |
|------|---------------------|--------------------------|
| L1 | 0-1 个定位条件 | 1 步操作, 1 个实体 |
| L2 | 1 个条件 | 1-2 步操作, 1 个实体 |
| L3 | 2-3 个条件 | 2-3 步操作, 2 个实体 |
| L4 | 2-4 个条件 + 排除筛选 | 2-3 步操作, 2 个实体 |
| L5 | 3+ 个条件 + 排名/排除 | 2-4 步操作, 3 个实体 |

## 覆盖环境与操作

| 环境 | 实体类型 | 支持操作 |
|------|---------|---------|
| GitLab | issue, project, merge_request | comment, add_label, assign, close, reopen |
| Shopping | product, product_variant | add_to_cart, update_quantity, remove_from_cart, write_review |
| Forum | community, post | create_post, comment_post, edit_post |
| CMS Admin | cms_page | create_page, edit_page, publish_page |

共 **15 个原子操作**，组合为 **24 个任务模板**（单操作 + 多操作链）。

## 管道流程（13 阶段）

```
Stage 0   加载配置资产          loaders.py              YAML 配置 + 实体库
Stage 1   规划生成单元格        planning.py             {ability, difficulty, env} 单元格
Stage 2   选结构骨架            structure_rules.py      难度约束（条件数、操作数）
Stage 3   选任务模板            template_registry.py    决定做什么操作
Stage 4   选目标实体            entity_selector.py      选哪个实体 + 定位字段
Stage 5   填充参数              requirement_selector.py 从受控参数池选值
Stage 6   拼装结构化任务        pipeline.py             合并所有组件
Stage 7   生成 ground truth     ground_truth.py         action → 预期 DB 状态
Stage 8   生成 verifier         verifier.py             assertion → 可执行查询
Stage 9   生成自然语言描述      instruction_generator.py + llm/   ← 唯一使用 LLM
Stage 10  质量检查（17 项）     quality.py              不通过 → 废弃重试
Stage 11  多样性筛选            diversity.py            平衡分布
Stage 12  导出                  exporter.py             JSON / CSV / Markdown
```

Stage 1-8 和 10 完全确定性（相同 seed 可复现）。仅 Stage 9 调用 LLM，且只做表面文本改写。

## 快速查看已生成的题目

项目已附带预生成的输出文件，无需运行任何命令即可直接查看生成结果：

| 文件 | 说明 |
|------|------|
| [`data/outputs/generated_10_examples.json`](data/outputs/generated_10_examples.json) | **10 道精选示例**，每道包含完整的 task_description、actions、ground_truth、verifier、quality_checks |
| [`data/outputs/generated_10_examples.md`](data/outputs/generated_10_examples.md) | 同上的 Markdown 可读版本 |
| [`data/outputs/generated_tasks_100.json`](data/outputs/generated_tasks_100.json) | 100 道完整任务集 |
| [`data/outputs/generation_report.json`](data/outputs/generation_report.json) | 生成报告（多样性统计 + 废弃原因） |

也可以用命令行快速浏览：

```bash
# 列出 10 道精选题的难度、维度、环境、描述
PYTHONPATH=src python3 -c "
import json
for i, t in enumerate(json.load(open('data/outputs/generated_10_examples.json')), 1):
    print(f\"{i}. [{t['ability_dimension']} {t['difficulty']} | {t['target_environment']}]\")
    print(f\"   {t['task_description'][:100]}...\")
    print(f\"   actions={len(t['actions'])}  assertions={len(t['ground_truth']['assertions'])}  quality={t['quality_checks']['passed']}\")
    print()
"

# 查看第 1 道题的完整结构（ground truth + verifier + quality checks）
PYTHONPATH=src python3 -c "
import json; print(json.dumps(json.load(open('data/outputs/generated_10_examples.json'))[0], indent=2, ensure_ascii=False))
"

# 查看 100 题的多样性分布
PYTHONPATH=src python3 -m taskgen.cli report --input data/outputs/generated_tasks_100.json
```

---

## 如何验收本项目

### 第一步：运行测试（仅需 `pip install` 即可）

```bash
PYTHONPATH=src python3 -m pytest tests/ -v
```

76 个测试，覆盖全部管道阶段、GT 生成、质量检查、多样性约束、验收守卫。无需 API key、无需网络。

### 第二步：端到端生成任务

```bash
PYTHONPATH=src python3 -m taskgen.cli generate \
  --count 100 --mock-llm \
  --entities data/normalized/entities.json \
  --output data/outputs/generated_tasks_100.json
```

产出 5 个文件到 `data/outputs/`：

| 文件 | 说明 |
|------|------|
| `generated_tasks_100.json` | 完整任务集（含 GT + verifier） |
| `generated_tasks_100.csv` | 摘要 CSV，便于表格分析 |
| `generated_10_examples.json` | 10 道精选示例（L1-L5 × 两个维度） |
| `generated_10_examples.md` | 可读 Markdown 格式 |
| `generation_report.json` | 多样性统计 + 废弃原因统计 |

### 第三步：查看单道题的完整结构

```bash
PYTHONPATH=src python3 -c "
import json
from taskgen.loaders import RuntimeContext
from taskgen.pipeline import Pipeline
from taskgen.llm.fake import FakeProvider

ctx = RuntimeContext('config', 'data/normalized/entities.json')
pipe = Pipeline(
    entities=ctx.entities, task_templates=ctx.task_templates,
    structure_rules=ctx.structure_rules, requirement_banks=ctx.requirement_banks,
    generation_plan=ctx.generation_plan, llm_provider=FakeProvider(), seed=42)
tasks = pipe.run(target_count=5)
print(json.dumps(tasks[0], indent=2, ensure_ascii=False))
"
```

### 第四步：验证可复现性

```bash
PYTHONPATH=src python3 -m taskgen.cli generate --count 50 --mock-llm --seed 42 \
  --entities data/normalized/entities.json --output /tmp/run1.json
PYTHONPATH=src python3 -m taskgen.cli generate --count 50 --mock-llm --seed 42 \
  --entities data/normalized/entities.json --output /tmp/run2.json
diff /tmp/run1.json /tmp/run2.json   # 无输出 = 完全一致
```

### 第五步：生产模式（可选，需 Kimi API key）

```bash
export KIMI_API_KEY="your-key"
PYTHONPATH=src python3 -m taskgen.cli generate --count 10 \
  --entities data/normalized/entities.json --output data/outputs/kimi_tasks.json
```

与 mock 模式唯一区别：Stage 9 调用 Kimi API 做自然语言改写，其余阶段不变。

## 任务输出示例

```json
{
  "task_id": "task_0001",
  "task_description": "In GitLab, find the issue whose title is file upload 413. Add a comment containing \"added reproduction steps\".",
  "target_environment": "gitlab",
  "ability_dimension": "Memory",
  "difficulty": "L1",
  "target_entity": {
    "entity_id": "gitlab_issue_018",
    "site": "gitlab",
    "entity_type": "issue",
    "selected_locator_fields": {"title_contains": "file upload 413"}
  },
  "actions": [
    {"type": "comment", "target": "A", "body_must_include": ["added reproduction steps"]}
  ],
  "ground_truth": {
    "type": "expected_backend_state",
    "assertions": [{
      "check_object": "issue_comments",
      "conditions": {"issue_ref": "gitlab_issue_018", "author_ref": "current_user"},
      "must_satisfy": {"exists": true, "body_must_include": ["added reproduction steps"]}
    }]
  },
  "verifier": {
    "type": "db_api_checker_template",
    "checks": [{
      "query": {
        "resource": "issue_comments",
        "filters": {"issue_ref": "gitlab_issue_018", "author_ref": "current_user"}
      },
      "condition": {"exists": true, "body_must_include": ["added reproduction steps"]}
    }],
    "execution_status": "not_executed"
  },
  "validation_status": {
    "symbolic_grounded": true,
    "backend_grounded": false,
    "verifier_executed": false,
    "needs_backend_validation": true
  },
  "quality_checks": {"passed": true, "checks": {"entity_exists": true, "...17 checks total...": true}}
}
```

**Ground truth** = 任务完成后预期的环境状态（如"issue 下有一条包含 X 的评论"）
**Verifier** = 可对后端执行的 DB/API 查询模板，用于验证 ground truth 是否成立

两者均由确定性代码生成，不涉及 LLM 判断。

## 已知限制

- **实体为符号化标注**：从 WebArena 公开的 812 道人工标注题中反向提取，未连接真实数据库验证。`backend_grounded` 诚实标注为 `false`
- **Verifier 未实际执行**：模板结构完整，但需接入 WebArena 后端才能运行
- **无条件分支任务**：所有任务为线性操作序列。WebArena 约 15% 的题含 if/else 逻辑
- **无跨站任务**：每道题仅涉及一个环境
- **无纯信息检索任务**：仅覆盖状态变更操作。WebArena 约 30% 为查询型任务
- **商品类目随机分配**：原始数据无类目信息，`normalizer.py` 通过固定种子随机分配

## 项目结构

```
src/taskgen/
├── pipeline.py             主流程编排器（Stage 0-12）
├── loaders.py              配置/数据加载 + RuntimeContext
├── planning.py             Stage 1: 生成单元格规划
├── structure_rules.py      Stage 2: 难度骨架选择
├── template_registry.py    Stage 3: 任务模板选择
├── entity_selector.py      Stage 4: 实体 + 定位字段选择
├── requirement_selector.py Stage 5: 参数填充
├── ground_truth.py         Stage 7: 确定性 GT 生成（15 种 action 映射）
├── verifier.py             Stage 8: Verifier 模板生成
├── instruction_generator.py Stage 9: 自然语言指令生成
├── quality.py              Stage 10: 17 项质量检查
├── diversity.py            Stage 11: 多样性筛选
├── exporter.py             Stage 12: 导出
├── quality_evaluator.py    与 WebArena 官方题目的对比评估
├── normalizer.py           原始数据归一化
├── schemas.py              数据类定义
├── cli.py                  CLI 入口（6 个子命令）
└── llm/
    ├── base.py             LLMProvider 抽象基类
    ├── fake.py             Mock provider（无网络，用于测试）
    └── kimi.py             Kimi API provider（OpenAI 兼容接口）

config/
├── generation_plan.yaml              分布目标（维度/难度/环境占比）
├── difficulty_structure_rules.yaml   结构骨架（2 维度 × 5 难度）
├── task_templates/                   24 个任务模板（4 个环境）
└── requirement_banks/                参数值池（评论内容、标签、评分等）

data/
├── entities/          WebArena 原始实体数据
├── normalized/        归一化实体库（213 个实体, 4 环境, 8 类型）
└── outputs/           生成的任务输出

tests/                 76 个测试, 11 个测试文件（~0.7s, 无需 API key）
```

## 环境变量

| 变量 | 是否必须 | 默认值 | 说明 |
|------|---------|--------|------|
| `KIMI_API_KEY` | 生产模式需要 | — | Kimi/Moonshot API key |
| `KIMI_BASE_URL` | 否 | `https://api.moonshot.cn/v1` | API 端点 |
| `KIMI_MODEL` | 否 | `kimi-k2.6` | 模型标识 |

## CLI 命令参考

```bash
# 查看原始数据
PYTHONPATH=src python3 -m taskgen.cli inspect-data --data-dir data/

# 归一化实体
PYTHONPATH=src python3 -m taskgen.cli normalize --input data/entities --output data/normalized/entities.json

# 生成任务（mock LLM）
PYTHONPATH=src python3 -m taskgen.cli generate --count 100 --mock-llm --entities data/normalized/entities.json --output data/outputs/tasks.json

# 生成精选示例
PYTHONPATH=src python3 -m taskgen.cli generate-examples --count 10 --mock-llm --entities data/normalized/entities.json --output data/outputs/examples.json

# 多样性报告
PYTHONPATH=src python3 -m taskgen.cli report --input data/outputs/tasks.json

# 与 WebArena 对比评估
PYTHONPATH=src python3 -m taskgen.cli evaluate-quality --generated data/outputs/tasks.json --webarena path/to/webarena_tasks.json
```
