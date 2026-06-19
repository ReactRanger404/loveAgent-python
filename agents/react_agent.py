"""ReAct (Reasoning and Acting) 模式的智能体抽象类"""
import logging
from abc import abstractmethod

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ReactAgent(BaseAgent):
    """
    ReAct (Reasoning and Acting) 模式的智能体抽象类
    实现了思考-行动的循环模式
    对应 Java: ReactAgent.java
    """

    @abstractmethod
    def think(self) -> bool:
        """
        处理当前状态并决定下一步行动
        :return: True 表示需要执行行动，False 表示不需要
        """
        ...

    @abstractmethod
    def act(self) -> str:
        """
        执行决定的行动
        :return: 行动执行结果
        """
        ...

    def step(self) -> str:
        """实现一步：先思考，再行动"""
        try:
            should_act = self.think()
            if not should_act:
                return "思考完成 - 无需行动"
            return self.act()
        except Exception as e:
            logger.exception("步骤执行失败")
            return f"步骤执行失败：{e!s}"
