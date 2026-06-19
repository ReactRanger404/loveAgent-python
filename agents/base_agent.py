"""抽象基础智能体 - 对应 Java 的 BaseAgent"""
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from agents.agent_state import AgentState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    抽象基础代理类，用于管理代理状态和执行流程。
    提供状态转换、记忆管理和基于步骤的执行循环的基础功能。
    对应 Java: BaseAgent.java

    run_stream() 产出结构化事件（dict），包含 type 字段：
      - type: "tool"    → 工具调用步骤（前端显示为小提示）
      - type: "text"    → LLM 回答文本（前端流式渲染到聊天框）
      - type: "error"   → 错误信息
      - type: "file"    → 生成的文件（前端显示下载按钮）
    """

    def __init__(
        self,
        name: str = "Agent",
        system_prompt: str = "",
        next_step_prompt: str = "",
        max_steps: int = 10,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.next_step_prompt = next_step_prompt
        self.state = AgentState.IDLE
        self.current_step = 0
        self.max_steps = max_steps
        self.messages: list[dict] = []

    def run(self, user_prompt: str) -> str:
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")
        if not user_prompt or not user_prompt.strip():
            raise RuntimeError("Cannot run agent with empty user prompt")

        self.state = AgentState.RUNNING
        self.messages.append({"role": "user", "content": user_prompt})
        results = []

        try:
            for i in range(self.max_steps):
                if self.state == AgentState.FINISHED:
                    break
                self.current_step = i + 1
                results.append(self.step())

            if self.current_step >= self.max_steps:
                self.state = AgentState.FINISHED
            return "\n".join(results)
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error("Error executing agent", exc_info=e)
            return f"执行错误: {e!s}"
        finally:
            self.cleanup()

    async def run_stream(self, user_prompt: str) -> AsyncGenerator[dict, None]:
        """
        流式运行，产出结构化事件。
        子类（ToolAgent 等）重写此方法以发送更细粒度的事件。
        """
        if self.state != AgentState.IDLE:
            yield {"type": "error", "content": f"无法从状态运行代理：{self.state}"}
            return
        if not user_prompt or not user_prompt.strip():
            yield {"type": "error", "content": "不能使用空提示词运行代理"}
            return

        self.state = AgentState.RUNNING
        self.messages.append({"role": "user", "content": user_prompt})

        try:
            for i in range(self.max_steps):
                if self.state == AgentState.FINISHED:
                    break
                self.current_step = i + 1
                logger.info("Step %d/%d", self.current_step, self.max_steps)
                result = self.step()
                yield {"type": "text", "content": result}

            if self.current_step >= self.max_steps:
                self.state = AgentState.FINISHED
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error("Error executing agent", exc_info=e)
            yield {"type": "error", "content": f"执行错误: {e!s}"}
        finally:
            self.cleanup()

    def reset(self):
        """重置状态以便接收新任务，保留对话历史"""
        self.state = AgentState.IDLE
        self.current_step = 0

    @abstractmethod
    def step(self) -> str:
        ...

    def cleanup(self):
        pass
