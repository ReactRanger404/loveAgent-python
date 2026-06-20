"""工具调用智能体 - 对应 Java 的 ToolAgent"""
import json
import logging
import re
from typing import AsyncGenerator, Optional

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import BaseTool

from agents.agent_state import AgentState
from agents.react_agent import ReactAgent
from config.constants import FILE_SAVE_DIR

logger = logging.getLogger(__name__)


def _extract_file_path(text: str):
    """从工具返回文本中提取 PDF 文件路径（用于前端下载）"""
    # 匹配 PDF 生成成功的输出路径
    m = re.search(r'PDF generated successfully to:\s*(\S+\.pdf)', text)
    if m:
        return m.group(1).strip()
    return None


class ToolAgent(ReactAgent):
    """
    处理工具调用的智能体，具体实现了 think 和 act 方法。
    对应 Java: ToolAgent.java

    run_stream() 产出结构化事件：
      - {"type": "tool",   "content": "使用工具 [xxx]"}  → 工具调用进度
      - {"type": "text",   "content": "..."}              → LLM 回答文本
      - {"type": "file",   "content": "/api/file/xxx.pdf"} → 可下载的文件
      - {"type": "error",  "content": "..."}              → 错误信息
    """

    def __init__(
        self,
        available_tools: list[BaseTool],
        name: str = "ToolAgent",
        system_prompt: str = "",
        next_step_prompt: str = "",
        max_steps: int = 20,
        llm=None,
    ):
        super().__init__(name, system_prompt, next_step_prompt, max_steps)
        self.available_tools = available_tools
        self._tool_map = {tool.name: tool for tool in available_tools}
        self._llm = llm
        self._last_ai_message: AIMessage | None = None
        self._prompt_added = False
        self.summary: str = ""  # 历史对话摘要（由 SessionManager 注入）

    def _build_lc_messages(self) -> list:
        lc_messages = []
        if self.system_prompt:
            lc_messages.append(SystemMessage(content=self.system_prompt))
        if self.summary:
            lc_messages.append(SystemMessage(content=f"【历史对话摘要】\n{self.summary}"))
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
        return lc_messages

    def think(self) -> bool:
        if self.next_step_prompt and not self._prompt_added:
            self.messages.append({"role": "user", "content": self.next_step_prompt})
            self._prompt_added = True

        lc_messages = self._build_lc_messages()
        try:
            llm_with_tools = self._llm.bind_tools(self.available_tools)
            response = llm_with_tools.invoke(lc_messages)
            self._last_ai_message = response

            if not response.tool_calls:
                self.messages.append({"role": "assistant", "content": response.content or ""})
                logger.info("%s 最终回答：%s", self.name, response.content)
                return False

            logger.info("%s 选择了 %d 个工具", self.name, len(response.tool_calls))
            for tc in response.tool_calls:
                logger.info("  工具: %s, 参数: %s", tc["name"], json.dumps(tc["args"]))
            return True
        except Exception as e:
            logger.error("%s 思考出错: %s", self.name, e)
            self.messages.append({"role": "assistant", "content": f"处理时遇到了错误：{e!s}"})
            return False

    def act(self) -> tuple[list[dict], str]:
        """
        执行工具调用，返回 (events, result_text_for_history)
        events: 要发送给前端的结构化事件列表
        """
        events = []
        if not self._last_ai_message or not self._last_ai_message.tool_calls:
            return events, ""

        first = True
        for tool_call in self._last_ai_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call.get("id", "")

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

            # 检查终止
            if tool_name == "do_terminate":
                self.state = AgentState.FINISHED

            # 生成前端事件
            events.append({"type": "tool", "content": f"🔧 使用工具 [{tool_name}]"})

            # 检查是否有文件生成
            if tool_name in ("generate_pdf",):
                file_path = _extract_file_path(result_text)
                if file_path:
                    # 将本地路径转换为 URL
                    rel_path = file_path.replace("\\", "/")
                    if FILE_SAVE_DIR.replace("\\", "/") in rel_path:
                        url_path = rel_path.split(FILE_SAVE_DIR.replace("\\", "/"))[1].lstrip("/")
                        events.append({"type": "file", "content": f"/api/file/{url_path}"})

            logger.info("工具 %s 返回：%s", tool_name, result_text[:120])

        return events, "\n".join(
            f"工具 {tc['name']} 返回的结果：{self.messages[-1 - i]['content']}"
            for i, tc in enumerate(reversed(self._last_ai_message.tool_calls))
        )

    async def _build_tool_calls_from_chunks(self, msg) -> list[dict]:
        """从流式 chunk 的 tool_call_chunks 重建完整的 tool_calls"""
        if not msg or not msg.tool_call_chunks:
            return []
        # 按 index 分组合并 tool_call_chunks
        groups = {}
        for tcc in msg.tool_call_chunks:
            idx = tcc.get("index", 0)
            if idx not in groups:
                groups[idx] = {"id": "", "name": "", "args": ""}
            for key in ("id", "name", "args"):
                val = tcc.get(key, "")
                if val:
                    if key == "args":
                        groups[idx][key] += val
                    else:
                        groups[idx][key] = val
        # 解析 args JSON
        result = []
        for idx in sorted(groups.keys()):
            g = groups[idx]
            try:
                args = json.loads(g["args"]) if g["args"] else {}
            except json.JSONDecodeError:
                args = {}
            result.append({
                "name": g["name"],
                "args": args,
                "id": g["id"] or f"call_{idx}",
            })
        return result

    async def run_stream(self, user_prompt: str) -> AsyncGenerator[dict, None]:
        """
        流式运行，产出结构化事件 — 支持流式思考过程（逐 token 输出到 think 区）

        事件类型：
          - type: "think"        → 思考文本 token（流式，实时追加到 think 区）
          - type: "think_clear"  → 清空 think 区（最终回答已流式输出完毕，移出 think 区）
          - type: "tool"         → 工具调用步骤
          - type: "text"         → LLM 最终回答文本（流式，逐块追加到对话气泡）
          - type: "file"         → 生成的文件下载链接
          - type: "error"        → 错误信息
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

                # 构建消息列表
                lc_messages = self._build_lc_messages()
                if self.next_step_prompt and not self._prompt_added:
                    lc_messages.append(HumanMessage(content=self.next_step_prompt))
                    self.messages.append({"role": "user", "content": self.next_step_prompt})
                    self._prompt_added = True

                llm_with_tools = self._llm.bind_tools(self.available_tools)

                # ====== 流式思考：逐 token 输出 ======
                full_content = ""
                accumulated_msg = None

                async for chunk in llm_with_tools.astream(lc_messages):
                    if accumulated_msg is None:
                        accumulated_msg = chunk
                    else:
                        accumulated_msg = accumulated_msg + chunk
                    text_chunk = chunk.content or ""
                    if text_chunk:
                        full_content += text_chunk
                        yield {"type": "think", "content": text_chunk}

                # ====== 流式结束，判断下一步 ======
                # 重建完整的 tool_calls
                tool_calls = []
                if accumulated_msg:
                    if accumulated_msg.tool_calls:
                        tool_calls = accumulated_msg.tool_calls
                    elif accumulated_msg.tool_call_chunks:
                        tool_calls = await self._build_tool_calls_from_chunks(accumulated_msg)

                # 构造完整的 AI message 供 act() 使用
                self._last_ai_message = AIMessage(
                    content=full_content,
                    tool_calls=tool_calls,
                )

                if tool_calls:
                    # 有工具调用 → 流式输出的文本是"思考过程"
                    self.messages.append({"role": "assistant", "content": full_content})
                    # 执行工具
                    events, _ = self.act()
                    for ev in events:
                        yield ev
                else:
                    # 无工具调用 → 流式输出的文本是"思考过程"
                    self.messages.append({"role": "assistant", "content": full_content})
                    # ① 清空 think 区
                    yield {"type": "think_clear", "content": "clear"}

                    # ② 根据思考过程重新生成精炼的最终回答
                    try:
                        refine_prompt = (
                            "你是一个面向用户的AI助手。请根据以下你的思考过程，\n"
                            "生成一个简洁、结构清晰、用户友好的最终回答。\n"
                            "去掉推理过程中的中间步骤和规划，直接给出答案。\n"
                            "用与用户相同的语言回复。\n\n"
                            "思考过程：\n"
                            f"{full_content}"
                        )
                        final_text = ""
                        async for chunk in self._llm.astream([HumanMessage(content=refine_prompt)]):
                            text_chunk = chunk.content or ""
                            if text_chunk:
                                final_text += text_chunk
                                yield {"type": "text", "content": text_chunk}
                    except Exception as e:
                        logger.warning("最终回答生成失败，回退到思考过程: %s", e)
                        final_text = full_content
                        yield {"type": "text", "content": final_text}

                    # ③ 最终回答存入消息历史
                    self.messages.append({"role": "assistant", "content": final_text})
                    break

            if self.current_step >= self.max_steps:
                self.state = AgentState.FINISHED
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error("Error executing agent", exc_info=e)
            yield {"type": "error", "content": f"执行错误: {e!s}"}
        finally:
            self.cleanup()

    def step(self) -> str:
        """同步模式下保持原有行为"""
        should_act = self.think()
        if not should_act:
            if self._last_ai_message and self._last_ai_message.content:
                return self._last_ai_message.content
            return "思考完成"
        events, history_text = self.act()
        return history_text or "\n".join(e["content"] for e in events)
