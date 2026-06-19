"""终止工具 - 对应 Java 的 TerminateTool"""
from langchain_core.tools import tool


@tool
def do_terminate() -> str:
    """
    Terminate the interaction when the request is met OR if the assistant cannot proceed further with the task.
    When you have finished all the tasks, call this tool to end the work.
    """
    return "任务结束"


terminate_tool = do_terminate
