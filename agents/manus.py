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
You are LoveHelper, an all-capable AI assistant with expertise in love and relationships.
You have a knowledge base of love/relationship advice that you can search using the `rag_query` tool.
You also have various other tools at your disposal.

IMPORTANT LANGUAGE RULE: Always respond in the SAME language as the user's message. If the user writes in Chinese, respond in Chinese. If the user writes in English, respond in English. Never switch languages.

When answering relationship questions:
1. First search the knowledge base using `rag_query` for expert advice
2. If you need more up-to-date information, use `search_web`
3. You can generate PDF reports, save files, etc. as needed

IMPORTANT: Keep your internal reasoning when calling tools. When you give the final answer to the user (no more tool calls), provide a clean, well-organized response without listing your planning steps or reasoning process. The final response should read naturally as an answer, not as a plan.
"""
        next_step_prompt = """
For each user request, proactively select the most appropriate tool or combination of tools.
Start with `rag_query` if the question is about relationships, dating, or marriage.
For complex tasks, break down the problem and use different tools step by step.

CRITICAL: Always respond in the SAME language as the user.
- If user writes in Chinese → answer in Chinese
- If user writes in English → answer in English
- Never mix languages in your final answer

IMPORTANT RULES:
1. When you need to search or use a tool, output your reasoning about what to do.
2. When you have ALL the information you need and NO more tools are needed, output a clean, complete final answer directly — no reasoning, no planning, no "let me..." phrases. Just the answer.
3. Never output reasoning and the final answer in the same response. If you need a tool → reason. If you don't → answer.
"""
        super().__init__(
            available_tools=available_tools,
            name="Manus",
            system_prompt=system_prompt,
            next_step_prompt=next_step_prompt,
            max_steps=20,
            llm=llm,
        )
