"""智能体状态枚举"""
from enum import Enum


class AgentState(str, Enum):
    """代理执行状态，对应 Java 的 AgentState 枚举"""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"
