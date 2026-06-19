"""工具调用智能体 - 对应 Java 的 ToolAgent"""
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import BaseTool

from agents.agent_state import AgentState
from agents.react_agent import ReactAgent

logger = logging.getLogger(__name__)


class ToolAgent(ReactAgent):
    """
    处理工具调用的智能体，具体实现了 think 和 act 方法。
    对应 Java: ToolAgent.java
    """

    def __init__(
        self,
        available_tools: list[BaseTool],
        name: str = "ToolAgent",
        system_prompt: str = "",
        next_step_prompt: str = "",
        max_steps: int = 10,
        llm=None,
    ):
        super().__init__(name, system_prompt, next_step_prompt, max_steps)
        self.available_tools = available_tools
        self._tool_map = {tool.name: tool for tool in available_tools}
        self._llm = llm
        # 记录最近一次 LLM 响应（含 tool_calls）
        self._last_ai_message: AIMessage | None = None

    def think(self) -> bool:
        """
        调用 LLM，解析是否需要调用工具
        对应 Java ToolAgent.think()
        """
        # 1. 添加 next_step_prompt 作为额外的 user message
        if self.next_step_prompt:
            self.messages.append({"role": "user", "content": self.next_step_prompt})

        # 2. 构建 LangChain 消息列表
        lc_messages = []
        if self.system_prompt:
            lc_messages.append(SystemMessage(content=self.system_prompt))
        for msg in self.messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg.get("content", "")))
            elif msg["role"] == "tool":
                lc_messages.append(ToolMessage(
                    content=msg.get("content", ""),
                    tool_call_id=msg.get("tool_call_id", ""),
                ))

        try:
            # 3. 调用 LLM（绑定工具）
            llm_with_tools = self._llm.bind_tools(self.available_tools)
            response = llm_with_tools.invoke(lc_messages)

            # 4. 记录响应
            self._last_ai_message = response

            # 5. 检查是否调用了工具
            if not response.tool_calls:
                # 没有工具调用：记录 AI 回复
                self.messages.append({"role": "assistant", "content": response.content or ""})
                logger.info("%s 的思考：%s", self.name, response.content)
                return False

            # 有工具调用
            logger.info("%s 的思考：%s", self.name, response.content)
            for tc in response.tool_calls:
                logger.info("工具名称：%s，参数：%s", tc["name"], json.dumps(tc["args"]))
            logger.info("%s 选择了 %d 个工具来使用", self.name, len(response.tool_calls))
            return True

        except Exception as e:
            logger.error("%s 的思考过程遇到了问题：%s", self.name, e)
            self.messages.append({"role": "assistant", "content": f"处理时遇到了错误：{e!s}"})
            return False

    def act(self) -> str:
        """
        执行工具调用并处理结果
        对应 Java ToolAgent.act()
        """
        if not self._last_ai_message or not self._last_ai_message.tool_calls:
            return "没有工具需要调用"

        results = []
        for tool_call in self._last_ai_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call.get("id", "")

            # 查找工具并执行
            tool = self._tool_map.get(tool_name)
            if tool is None:
                result_text = f"错误：未找到工具 '{tool_name}'"
            else:
                try:
                    result = tool.invoke(tool_args)
                    result_text = str(result)
                except Exception as e:
                    result_text = f"工具执行失败: {e!s}"

            # 记录到消息历史
            self.messages.append({
                "role": "tool",
                "content": result_text,
                "tool_call_id": tool_call_id,
                "name": tool_name,
            })

            # 检查终止工具
            if tool_name == "do_terminate":
                self.state = AgentState.FINISHED

            result_line = f"工具 {tool_name} 返回的结果：{result_text}"
            results.append(result_line)
            logger.info(result_line)

        return "\n".join(results)
