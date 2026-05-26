# AgentScope DashScope TUI 演示

基于 [AgentScope](https://github.com/modelscope/agentscope) + [DashScope](https://dashscope.aliyuncs.com/) 的交互式对话演示程序。

**特性：**
- 通过 `config.yaml` 配置文件灵活设定模型参数，无需修改代码（首次运行自动从模板生成）
- `rich` 驱动的 TUI 终端界面，带彩色消息气泡和 Markdown 渲染
- 流式逐 token 输出（`stream=True`）
- 多轮对话，历史由 `InMemoryMemory` 维护
- 工具调用可选（Shell 命令执行、Python 代码执行、文件查看）
- API Key 支持环境变量，避免硬编码

---

## 快速开始

### 1. 安装依赖

本示例使用 [uv](https://docs.astral.sh/uv/) 进行包管理。

```bash
# 进入示例目录
cd examples/functionality/dashscope_demo

# 安装依赖（默认以本地可编辑模式引用仓库根目录的 agentscope）
uv sync
```

> 默认配置通过 `[tool.uv.sources]` 将 `agentscope` 指向仓库本地源码（可编辑模式），无需额外配置。
> 如需从 PyPI 安装，删除 `pyproject.toml` 中 `[tool.uv.sources]` 的 `agentscope` 行即可。

### 2. 配置 API Key

推荐使用环境变量（避免 Key 写入文件）：

```bash
export DASHSCOPE_API_KEY="your-api-key-here"
```

或者编辑自动生成的 `config.yaml`，在 `model.api_key` 字段填写（该文件已被 `.gitignore` 忽略，不会提交到版本控制）。

### 3. 运行演示

```bash
# 使用默认 config.yaml（首次运行自动从 config.yaml.template 生成）
uv run python main.py

# 指定自定义配置文件
uv run python main.py --config path/to/custom.yaml
```

> **注意**：`config.yaml` 不会进入版本控制（已添加到 `.gitignore`）。如需修改默认配置，请编辑 `config.yaml.template`。

---

## 配置文件说明

配置文件默认为 `config.yaml`，分三个段落：

### `model` — 模型配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model_name` | string | `"qwen-max"` | 模型名称，见[模型列表](https://help.aliyun.com/zh/model-studio/getting-started/models) |
| `api_key` | string | `""` | DashScope API Key，留空则读取环境变量 `DASHSCOPE_API_KEY` |
| `stream` | bool | `true` | 是否启用流式输出（推荐开启） |
| `enable_thinking` | bool | `false` | 是否启用深度思考（仅 Qwen3/QwQ/DeepSeek-R1 支持） |
| `multimodality` | bool/null | `null` | 多模态模式；null = 根据模型名称自动判断 |
| `generate_kwargs` | dict | — | 透传给 API 的生成参数（temperature、top_p、max_tokens 等） |
| `base_http_api_url` | string/null | `null` | 自定义 API Base URL |

**常用模型名称：**

| 模型 | 说明 |
|------|------|
| `qwen-max` | 旗舰版（均衡） |
| `qwen-plus` | 增强版 |
| `qwen-turbo` | 快速版（低成本） |
| `qwen-long` | 长文档版 |
| `qwq-32b` | 深度思考版（配合 `enable_thinking: true`） |
| `qwen-vl-max` | 多模态视觉版 |

### `agent` — Agent 配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | `"Friday"` | Agent 名称，显示在对话界面 |
| `sys_prompt` | string | — | 系统提示词，定义 Agent 角色和行为 |
| `max_iters` | int | `10` | ReAct 循环最大迭代次数 |
| `tools.enabled` | bool | `true` | 是否启用内置工具 |
| `tools.functions` | list | 全部 | 要注册的工具函数列表 |

**可用工具：**

| 工具名 | 说明 |
|--------|------|
| `execute_shell_command` | 执行 Shell 命令 |
| `execute_python_code` | 执行 Python 代码片段 |
| `view_text_file` | 查看文本文件内容 |

### `tui` — 界面配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `welcome_message` | string | 启动时欢迎语 |
| `goodbye_message` | string | 退出时告别语 |
| `user_color` | string | 用户消息颜色（rich 颜色名或十六进制） |
| `agent_color` | string | Agent 回复颜色 |
| `thinking_color` | string | 思考过程颜色 |
| `tool_color` | string | 工具调用颜色 |
| `exit_commands` | list | 触发退出的关键词列表（不区分大小写） |

---

## 使用技巧

- 输入 `exit`、`quit`、`q` 或 `退出` 可退出程序，也可按 `Ctrl+C`
- 修改 `config.yaml` 中的 `sys_prompt` 来定制 Agent 的角色和专业领域
- 将 `tools.enabled` 设为 `false` 可禁用工具，Agent 进入纯对话模式
- 开启 `enable_thinking` 后 Agent 会先输出思考过程（折叠面板展示）

---

## 目录结构

```
dashscope_demo/
├── pyproject.toml          # uv 依赖声明
├── config.yaml.template    # 配置模板（入版本控制）
├── config.yaml             # 实际配置（自动生成，不入版本控制）
├── main.py                 # 主程序
└── README.md               # 本文件
```

---

## 依赖说明

| 包 | 说明 |
|----|------|
| `agentscope` | 多智能体框架核心 |
| `dashscope` | 阿里云 DashScope Python SDK |
| `rich` | 终端美化（颜色、Markdown 渲染等） |
| `pyyaml` | YAML 配置文件解析 |
