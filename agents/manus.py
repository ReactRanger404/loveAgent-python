"""Manus 超级智能体 - 对应 Java 的 Manus.java"""
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from agents.tool_agent import ToolAgent

logger = logging.getLogger(__name__)


class Manus(ToolAgent):
    """
    全能 AI 超级智能体（拥有自主规划能力，可以直接使用）
    对应 Java: Manus.java

    继承自 ToolAgent，配置了专属的系统提示词和最大步骤数。
    """

    def __init__(
        self,
        available_tools: list[BaseTool],
        llm: BaseChatModel,
    ):
        system_prompt = """
You are YuManus, an all-capable AI assistant, aimed at solving any task presented by the user.
You have various tools at your disposal that you can call upon to efficiently complete complex requests.
"""
        next_step_prompt = """
Based on user needs, proactively select the most appropriate tool or combination of tools.
For complex tasks, you can break down the problem and use different tools step by step to solve it.
After using each tool, clearly explain the execution results and suggest the next steps.
If you want to stop the interaction at any point, use the `do_terminate` tool/function call.
"""
        super().__init__(
            available_tools=available_tools,
            name="Manus",
            system_prompt=system_prompt,
            next_step_prompt=next_step_prompt,
            max_steps=20,
            llm=llm,
        )
