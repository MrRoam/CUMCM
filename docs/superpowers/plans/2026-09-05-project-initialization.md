# CUMCM 项目初始化实施计划

> **供智能体执行：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项实施。所有步骤使用复选框跟踪。

**目标：** 建立一套面向全国大学生数学建模竞赛的最小可靠目录、中文协作契约和可直接使用的记录模板。

**架构：** 仓库按“输入、探索、正式代码、生成结果、论文、提交物”的生命周期分区。根文档分别承担导航、稳定规则、重大决策和 AI 使用记录职责，技术栈保持未绑定状态。

**技术栈：** Git、Markdown、通用文本与二进制文件规则；不引入编程语言、论文工具或第三方依赖。

**规格：** `docs/superpowers/specs/2026-09-01-project-initialization-design.md`

## 全局约束

- 所有文档使用中文和 UTF-8。
- 保留现有 `AGENTS.md` 的教练角色、学生团队背景和禁止直接向 `main` 推送的规则。
- 不决定 Python、MATLAB、LaTeX 或 Word。
- 不写入个人绝对路径、成员姓名、具体赛题、虚构命令或模型结论。
- 不覆盖、回退或提交与本次初始化无关的用户改动。
- 当前工作在 `codex/project-initialization` 分支完成，不直接推送或合并到 `main`。

---

### 任务 1：建立根级协作文档

**文件：**

- 修改：`README.md`
- 修改：`AGENTS.md`
- 创建：`DECISIONS.md`
- 创建：`AI_USAGE.md`

**接口：**

- 输入：已确认的初始化设计、现有 `AGENTS.md` 规则、当前工具链未决定的事实。
- 输出：团队入口、全仓库执行契约、重大决策模板和 AI 使用记录模板。

- [x] **步骤 1：扩充 README**

  写明项目目标、当前状态、目录职责、单向工作流、探索成果晋升规则、短分支协作方式、二进制文件单一整合者规则，以及工具链待决定状态。

- [x] **步骤 2：在既有 AGENTS 规则上追加协作契约**

  保留现有角色描述与规则 1，新增适用范围、优先级、目录不变量、可复现性、科研诚信、协作安全、验证交付和敏感信息规则。明确文档使用中文、路径必须为仓库相对路径。

- [x] **步骤 3：创建重大决策模板**

  `DECISIONS.md` 包含使用方法和首条“项目目录采用生命周期分区”的已接受决策；后续条目固定包含日期、状态、背景、决定、理由、备选方案和影响。

- [x] **步骤 4：创建 AI 使用记录模板**

  `AI_USAGE.md` 区分赛前准备与正式竞赛期间，记录日期、阶段、工具型号、用途、提示方式、采纳内容、人工修改、核验方法和相关文件，并给出竞赛期间逐次记录模板。

- [x] **步骤 5：检查文档职责和既有规则**

  运行：

  ```powershell
  rg -n "不要直接向main分支推送|写文档时，请用中文|inputs/official|DECISIONS.md|AI_USAGE.md" README.md AGENTS.md DECISIONS.md AI_USAGE.md
  rg -n "TODO|TBD|待补充|PLACEHOLDER" README.md AGENTS.md DECISIONS.md AI_USAGE.md
  ```

  预期：第一条命令找到所有关键约束；第二条命令无输出并以代码 1 结束。

### 任务 2：建立生命周期目录与 Git 规则

**文件：**

- 创建：`inputs/official/.gitkeep`
- 创建：`inputs/external/.gitkeep`
- 创建：`experiments/.gitkeep`
- 创建：`src/.gitkeep`
- 创建：`outputs/.gitkeep`
- 创建：`paper/.gitkeep`
- 创建：`submission/.gitkeep`
- 创建：`.gitignore`
- 创建：`.gitattributes`

**接口：**

- 输入：README 和 AGENTS 中定义的目录职责。
- 输出：可由 Git 跟踪的空目录骨架，以及跨平台一致的忽略和属性规则。

- [x] **步骤 1：创建最小目录骨架**

  为七个叶子目录创建空 `.gitkeep`，不建立 `notebooks/`、`references/`、`tests/`、`configs/`、`scripts/` 或工具专用目录。

- [x] **步骤 2：创建精确的忽略规则**

  `.gitignore` 覆盖操作系统垃圾、IDE 本地配置、密钥文件、Python/MATLAB/LaTeX 缓存、Office 临时文件、通用日志和临时目录；保留示例环境文件，并且不得整体忽略 `outputs/` 或 `submission/`。

- [x] **步骤 3：创建文件属性规则**

  `.gitattributes` 使用 `* text=auto`，Markdown 和常见源码使用 LF；Word、Excel、PDF、压缩包、图片和 MATLAB 二进制数据标记为 `binary`。

- [x] **步骤 4：验证忽略和属性行为**

  使用临时文件验证 `.env`、`__pycache__`、Office 锁文件和日志会被忽略，而 `outputs/figure.png` 不因目录规则被忽略。验证后删除本次检查创建的临时文件。

### 任务 3：整体审查与原子提交

**文件：**

- 检查：本计划中全部创建和修改的文件。

**接口：**

- 输入：任务 1 和任务 2 的所有产物。
- 输出：可供团队审阅并具备合并条件的初始化分支提交。

- [x] **步骤 1：检查规格覆盖**

  对照设计文档，逐项确认根文件职责、六个生命周期阶段、协作规则、提交边界、工具链非目标和验证要求均已实现。

- [x] **步骤 2：检查差异与空白错误**

  运行：

  ```powershell
  git diff --check
  git status --short
  git diff -- README.md AGENTS.md DECISIONS.md AI_USAGE.md .gitignore .gitattributes
  ```

  预期：`git diff --check` 退出码为 0；状态中只有本次初始化文件。

- [ ] **步骤 3：提交初始化变更**

  仅暂存本计划涉及的文件，检查暂存差异后提交：

  ```powershell
  git commit -m "chore: 初始化数学建模协作仓库"
  ```

- [ ] **步骤 4：提交后验证**

  运行目录结构检查、关键规则检索、Git 状态检查和最近提交检查。预期分支为 `codex/project-initialization`，工作区干净，且未执行推送、合并或创建拉取请求。
