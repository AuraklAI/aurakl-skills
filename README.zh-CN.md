# Aurakl 插件：工业级 Agent 技能套件 (中文文档)

[![Version](https://img.shields.io/badge/版本-1.0.0-blue.svg)](./plugin.json)
[![Python](https://img.shields.io/badge/Python-3.9+-brightgreen.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/开源协议-Apache--2.0-orange.svg)](./LICENSE)
[![Dependencies](https://img.shields.io/badge/第三方依赖-0%20(纯标准库)-success.svg)](./requirements.txt)
[![Tests](https://img.shields.io/badge/单元测试-65%2F65%20全部通过-brightgreen.svg)](./tests/)

[English Documentation](./README.md)

**Aurakl Plugin** 是专为 AI 结对编程与自主 Agent（Google Antigravity、Claude Code、Cursor 及 Agent Skills 规范）打造的企业级生产力插件。它打包了经过工业级验证的**产品管理（PM）**与**软件架构师（Architect）**双核心技能，内置数学不变量校验、笛卡尔完备性审计与纯 Python 确定性裁判（Oracle）。

---

## 🌟 核心特性与设计哲学

- **双层 SOP 与确定性交付**：彻底告别 LLM 的模糊生成。所有阶段产物必须通过强类型 JSON Schema 契约校验与机器可执行的 Lineage Oracle 门禁。
- **全链路动态语言同构**：自动识别用户 Prompt 语言。中文交互全链路生成 100% 纯中文交付物（含所有中间态 JSON 与最终 Markdown），严禁中英混杂；规范技术标识（如 `REQ-*`, `INV-*`, `FEAT-*`）保持标准英文形式。
- **零占位符与拒绝幻觉**：严格禁止 `TODO`、`TBD`、`待定`、`占位符`、`后续补充` 等空壳文本。校验器层一票否决。
- **闭世界数据闭包 (Closed-World Data Closure)**：任何前置条件与入参必须追溯到明确的来源（用户输入、数据库字段、第三方下游），严禁数据凭空产生。
- **零外部依赖 (Zero Dependency)**：所有校验引擎、渲染器、审计工具均基于 Python 3.9+ 原生标准库（`json`, `argparse`, `pathlib`, `re`, `unittest`）开发，无需执行 `pip install` 即可开箱即用。

---

## 📦 插件包含的核心技能

```text
aurakl-plugin/
├── plugin.json                    # 插件清单文件
├── rules/
│   └── AGENTS.md                  # 插件级 Agent 铁律（全局质量守恒约束）
├── skills/
│   ├── aurakl-product-manager/    # 工业级产品管理专家技能
│   └── aurakl-software-architect/ # 工业级软件架构专家技能
```

### 1. `aurakl-product-manager` (工业级产品管理专家)
严格遵循 **ISO/IEC/IEEE 29148** 需求工程标准，驱动 7 阶段落地流水线：
- **Stage 01 需求澄清与证伪**：5W1H 槽位追问、痛点证伪（`painkiller` vs `vitamin`）、四类领域原型适配（移动端/桌面端/纯后端/IoT）。
- **Stage 02 市场与竞品情报**：多维矩阵量化分析，确立核心防御壁垒（"Why We Win"）。
- **Stage 03 全角色旅程与故事建模**：$\ge 3$ 个角色独立触点链路，推导 100% 覆盖的 INVEST 用户故事。
- **Stage 04 契约化 PRD 编写**：RFC 2119 规范性业务规则，状态转移规约与闭世界数据源闭包。
- **Stage 05 形式化产品不变量**：跨状态机、代数守恒、安全权限、UX 兜底四维形式化不变量。
- **Stage 06 验收用例矩阵**：不变量 100% 测试覆盖（10,000 bp），防御性负向用例占比 $\ge 30\%$。
- **Stage 07 端到端血缘审查与发布**：全链路闭合审计与多维 Markdown 渲染。

### 2. `aurakl-software-architect` (工业级软件架构专家)
严格践行 **Linus Torvalds 务实架构哲学**，驱动 9 阶段技术蓝图：
- **Stage 01 技术选型 ADR 决策**：加权打分对比矩阵，严禁选定方案标记放弃。
- **Stage 02 三层模块化单体拓扑**：清晰物理边界与反腐层，严禁过度微服务化。
- **Stage 03 100% PRD 领域建模**：实体、值对象、聚合根与生命周期不变量。
- **Stage 04 物理数据库与索引设计**：提供可直接执行的建表 DDL、高效复合索引及回滚 Migration。
- **Stage 05 强类型向后兼容 API 契约**：完整请求/响应 JSON 示例与业务错误码字典。
- **Stage 06 三路径业务时序图**：成功主路径、参数/业务校验失败分支、系统超时/服务降级分支。
- **Stage 07 九维架构不变量矩阵**：幂等、事务边界、并发防御、隔离策略物理落地。
- **Stage 08 有向无环技术依赖图 (DAG)**：拓扑排序检测，杜绝循环依赖。
- **Stage 09 笛卡尔完备性审计与就绪审查**：一票否决权治理门禁。

---

## 🚀 安装与分发指南

### 方式 1：标准 Agent Skills 一键安装（推荐，跨平台通用）
适用于 **Antigravity、Claude Code、Cursor、Codex、Cline、Amp** 等所有支持 Agent Skills 标准的宿主环境，通过 `npx skills` 一行命令搞定：

```bash
# 1. 项目级一键安装（推荐，为当前项目注入全部技能，写入 .agents/skills/）：
npx skills add aurakl/aurakl-plugin

# 2. 或仅安装单个技能：
npx skills add aurakl/aurakl-plugin -s aurakl-product-manager
npx skills add aurakl/aurakl-plugin -s aurakl-software-architect

# 3. 跨项目全局安装（所有项目通用）：
npx skills add aurakl/aurakl-plugin -g

# 4. 本地工作区极速体验（如果你已处于本仓库目录中）：
npx skills add . -y
```

### 方式 2：Antigravity 专有插件模式（Bundle 规则 + 技能）
如果你使用 Google Antigravity 并希望同时绑定 `rules/AGENTS.md` 自动化质量门禁与技能包：
```bash
# 项目工程级（团队共享，直接提交至项目 Git）：
mkdir -p .agents/plugins
git clone https://github.com/aurakl/aurakl-plugin.git .agents/plugins/aurakl-plugin

# 个人机器全局生效：
mkdir -p ~/.gemini/config/plugins
git clone https://github.com/aurakl/aurakl-plugin.git ~/.gemini/config/plugins/aurakl-plugin
```

### 方式 3：Python 命令行与 CI/CD 自动化集成 (`pip`)
若你需要在持续集成流水线、代码提交流程或终端中独立调用确定性不变量验证引擎：
```bash
cd aurakl-plugin
pip install -e .
aurakl status
```

---

## 🛠️ CLI 常用指令示例

### 产品管理工具集 (`aurakl pm`)
```bash
# 1. 5W1H 槽位评估与交互追问生成
aurakl pm elicit --input brief.json

# 2. 五维验收门禁自动核验 (Schema 校验)
aurakl pm validate --artifact output.json --schema prd.v2.json

# 3. 计算不变量覆盖率与防御用例占比
aurakl pm calc-metrics --criteria acceptance_criteria.json --invariants product_invariants.json

# 4. 全链路端到端血缘与闭合审计 (Oracle 判定)
aurakl pm audit --suite suite.json

# 5. 渲染工业级 Markdown 文档
aurakl pm render --source source/ --output requirement/
```

### 架构设计工具集 (`aurakl arch`)
```bash
# 1. 架构验收校验 (绑定上游 PRD)
aurakl arch validate <path_to_json> --suite --upstream-prd <path_to_prd>

# 2. 渲染 Markdown 架构蓝图 (支持 --lang zh / --lang en)
aurakl arch render <path_to_json> --lang zh -o architecture.zh.md

# 3. 笛卡尔完备性审计
aurakl arch cartesian <path_to_suite_json>

# 4. 架构 Lineage Oracle 门禁校验
aurakl arch oracle <path_to_suite_json> --upstream-prd <path_to_prd>
```

---

## 🧪 验证与自测

运行插件完整性与全部 65 项自动化单元测试：
```bash
# 使用统一 CLI
./bin/aurakl test

# 或直接运行 Python 测试脚本
python3 tests/test_plugin_integrity.py -v
```

---

## 📄 开源许可

本项目遵循 [Apache License 2.0](./LICENSE) 开源许可协议。
