"""抽象基础智能体 - 对应 Java 的 BaseAgent"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from agents.agent_state import AgentState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    抽象基础代理类，用于管理代理状态和执行流程。
    提供状态转换、记忆管理和基于步骤的执行循环的基础功能。
    对应 Java: BaseAgent.java
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
        # 消息历史（替代 Java 的 messageList）
        self.messages: list[dict] = []

    def run(self, user_prompt: str) -> str:
        """
        运行智能体（同步方式）
        对应 Java: run(String userPrompt)
        """
        # 1. 基础校验
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")
        if not user_prompt or not user_prompt.strip():
            raise RuntimeError("Cannot run agent with empty user prompt")

        # 2. 执行
        self.state = AgentState.RUNNING
        self.messages.append({"role": "user", "content": user_prompt})
        results = []

        try:
            for i in range(self.max_steps):
                if self.state == AgentState.FINISHED:
                    break
                step_number = i + 1
                self.current_step = step_number
                logger.info("Executing step %d/%d", step_number, self.max_steps)
                step_result = self.step()
                result = f"Step {step_number}: {step_result}"
                results.append(result)

            if self.current_step >= self.max_steps:
                self.state = AgentState.FINISHED
                results.append(f"Terminated: Reached max steps ({self.max_steps})")

            return "\n".join(results)
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error("Error executing agent step %d/%d", self.current_step, self.max_steps, exc_info=e)
            return f"执行错误: {e!s}"
        finally:
            self.cleanup()

    async def run_stream(self, user_prompt: str):
        """
        运行智能体（流式输出）—— 异步生成器
        对应 Java: runStream(String userPrompt) -> SseEmitter
        """
        # 1. 基础校验
        if self.state != AgentState.IDLE:
            yield f"错误：无法从状态运行代理：{self.state}"
            return
        if not user_prompt or not user_prompt.strip():
            yield "错误：不能使用空提示词运行代理"
            return

        # 2. 执行
        self.state = AgentState.RUNNING
        self.messages.append({"role": "user", "content": user_prompt})

        try:
            for i in range(self.max_steps):
                if self.state == AgentState.FINISHED:
                    break
                step_number = i + 1
                self.current_step = step_number
                logger.info("Executing step %d/%d", step_number, self.max_steps)
                step_result = self.step()
                result = f"Step {step_number}: {step_result}"
                yield result

            if self.current_step >= self.max_steps:
                self.state = AgentState.FINISHED
                yield f"执行结束：达到最大步骤（{self.max_steps}）"
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error("Error executing agent", exc_info=e)
            yield f"执行错误: {e!s}"
        finally:
            self.cleanup()

    @abstractmethod
    def step(self) -> str:
        """定义单个步骤，子类必须实现"""
        ...

    def cleanup(self):
        """清理资源，子类可重写"""
        pass
