"""终端操作工具 - 对应 Java 的 TerminalOperationTool"""
import subprocess
import sys
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def execute_terminal_command(command: str) -> str:
    """
    Execute a command in the terminal.
    :param command: Command to execute in the terminal
    :return: Command output
    """
    try:
        # Windows 用 cmd.exe，Linux/Mac 用 sh
        if sys.platform == "win32":
            shell_cmd = ["cmd.exe", "/c", command]
        else:
            shell_cmd = ["sh", "-c", command]

        result = subprocess.run(
            shell_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.returncode != 0:
            output += f"\nCommand failed with exit code: {result.returncode}"
            if result.stderr:
                output += f"\nStderr: {result.stderr}"
        return output.strip() or "(无输出)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {e!s}"


terminal_command_tool = execute_terminal_command
