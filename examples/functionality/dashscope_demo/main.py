# -*- coding: utf-8 -*-
"""AgentScope DashScope TUI 演示程序。

通过 YAML 配置文件驱动模型参数，使用 rich 库提供美观的终端交互界面，
支持流式输出的多轮对话。

运行方式：
    uv run python main.py
    uv run python main.py --config path/to/custom.yaml
"""
import argparse
import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.tool import (
    Toolkit,
    execute_python_code,
    execute_shell_command,
    view_text_file,
)

# 所有可用的内置工具映射
_AVAILABLE_TOOLS = {
    "execute_shell_command": execute_shell_command,
    "execute_python_code": execute_python_code,
    "view_text_file": view_text_file,
}


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

def load_config(config_path: str) -> dict[str, Any]:
    """加载并基本校验 YAML 配置文件。"""
    path = Path(config_path)
    if not path.exists():
        print(f"[错误] 配置文件不存在: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        try:
            cfg = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"[错误] 配置文件解析失败:\n{e}", file=sys.stderr)
            sys.exit(1)

    for section in ("model", "agent", "tui"):
        if section not in cfg:
            print(f"[错误] 配置文件缺少必要段落: [{section}]", file=sys.stderr)
            sys.exit(1)

    return cfg


# ---------------------------------------------------------------------------
# 组件构建
# ---------------------------------------------------------------------------

def build_model(cfg: dict[str, Any]) -> DashScopeChatModel:
    """根据配置构建 DashScopeChatModel 实例。"""
    model_cfg = cfg["model"]

    api_key = model_cfg.get("api_key") or os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print(
            "[错误] DashScope API Key 未配置。\n"
            "请在 config.yaml 的 model.api_key 字段填写，\n"
            "或设置环境变量 DASHSCOPE_API_KEY。",
            file=sys.stderr,
        )
        sys.exit(1)

    return DashScopeChatModel(
        model_name=model_cfg["model_name"],
        api_key=api_key,
        stream=model_cfg.get("stream", True),
        enable_thinking=model_cfg.get("enable_thinking", False),
        multimodality=model_cfg.get("multimodality"),
        generate_kwargs=model_cfg.get("generate_kwargs") or {},
        base_http_api_url=model_cfg.get("base_http_api_url"),
    )


def build_agent(
    cfg: dict[str, Any],
    model: DashScopeChatModel,
) -> ReActAgent:
    """根据配置构建 ReActAgent 实例。"""
    agent_cfg = cfg["agent"]
    tools_cfg = agent_cfg.get("tools", {})

    toolkit = Toolkit()
    if tools_cfg.get("enabled", True):
        requested_fns = tools_cfg.get("functions", list(_AVAILABLE_TOOLS.keys()))
        for fn_name in requested_fns:
            fn = _AVAILABLE_TOOLS.get(fn_name)
            if fn is not None:
                toolkit.register_tool_function(fn)
            else:
                print(
                    f"[警告] 未知工具函数 '{fn_name}'，已跳过。",
                    file=sys.stderr,
                )

    return ReActAgent(
        name=agent_cfg["name"],
        sys_prompt=agent_cfg["sys_prompt"],
        model=model,
        formatter=DashScopeChatFormatter(),
        toolkit=toolkit,
        memory=InMemoryMemory(),
        max_iters=agent_cfg.get("max_iters", 10),
    )


# ---------------------------------------------------------------------------
# TUI 渲染
# ---------------------------------------------------------------------------

def _get_color(tui_cfg: dict[str, Any], key: str, default: str) -> str:
    """安全获取 TUI 颜色配置。"""
    return tui_cfg.get(key, default) or default


def print_welcome(console: Console, tui_cfg: dict[str, Any], agent_name: str) -> None:
    """渲染欢迎界面。"""
    console.print()
    console.print(Rule("[bold blue]AgentScope × DashScope TUI 演示[/bold blue]"))
    console.print()

    welcome_msg = tui_cfg.get(
        "welcome_message",
        "欢迎！输入 'exit' 退出。",
    )
    console.print(
        Panel(
            Text(welcome_msg, justify="center"),
            title=f"[bold]Agent: {agent_name}[/bold]",
            border_style="blue",
            padding=(1, 4),
        )
    )
    console.print()


def print_goodbye(console: Console, tui_cfg: dict[str, Any]) -> None:
    """渲染退出界面。"""
    console.print()
    goodbye_msg = tui_cfg.get("goodbye_message", "感谢使用，再见！")
    console.print(
        Panel(
            Text(goodbye_msg, justify="center"),
            border_style="dim blue",
            padding=(0, 4),
        )
    )
    console.print()


def get_user_input(console: Console, tui_cfg: dict[str, Any]) -> str:
    """获取用户输入（带彩色提示符）。"""
    user_color = _get_color(tui_cfg, "user_color", "cyan")
    try:
        console.print(f"[bold {user_color}]You ›[/bold {user_color}] ", end="")
        return input()
    except EOFError:
        return "exit"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

async def main(config_path: str = "config.yaml") -> None:
    """异步主函数：加载配置 → 构建组件 → TUI 主循环。

    Agent 自身处理流式输出（框架内置增量打印机制），
    TUI 层负责欢迎页、输入提示和退出逻辑。
    """
    console = Console()

    # 如果配置文件不存在，自动从模板复制
    config_file = Path(config_path)
    if not config_file.exists():
        template_file = config_file.with_suffix(config_file.suffix + ".template")
        if template_file.exists():
            shutil.copy2(template_file, config_file)
            console.print(
                f"[dim]已从模板 [{template_file.name}] 生成配置文件 [{config_file.name}][/dim]",
            )
        else:
            print(
                f"[错误] 配置文件不存在: {config_path}\n"
                f"且模板文件 {template_file} 也不存在。",
                file=sys.stderr,
            )
            sys.exit(1)

    # 加载配置
    cfg = load_config(config_path)
    tui_cfg = cfg.get("tui", {})
    exit_commands = {
        cmd.lower() for cmd in tui_cfg.get("exit_commands", ["exit", "quit", "q"])
    }

    # 构建模型和 Agent
    with console.status("[bold blue]正在初始化模型和 Agent...[/bold blue]"):
        model = build_model(cfg)
        agent = build_agent(cfg, model)

    # 打印欢迎界面
    print_welcome(console, tui_cfg, agent.name)

    # 主对话循环：与项目原生设计一致，让 agent 自身处理流式输出
    while True:
        try:
            user_input = get_user_input(console, tui_cfg)
        except KeyboardInterrupt:
            print()
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.lower() in exit_commands:
            break

        # 构造用户消息并调用 Agent
        user_msg = Msg(name="User", content=user_input, role="user")
        try:
            await agent(user_msg)
        except KeyboardInterrupt:
            console.print("\n[dim]（已中断当前回复）[/dim]")
        except Exception as e:  # noqa: BLE001
            console.print(f"[bold red][错误][/bold red] {e}")

    print_goodbye(console, tui_cfg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AgentScope DashScope TUI 演示程序",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径（默认: config.yaml，不存在时自动从 config.yaml.template 复制）",
    )
    args = parser.parse_args()

    asyncio.run(main(config_path=args.config))
