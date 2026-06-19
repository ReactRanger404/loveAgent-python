"""恋爱大师应用 - 对应 Java 的 LoveApp.java"""
import logging
import uuid
from typing import AsyncGenerator, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from advisors.logger_advisor import LoggerAdvisor
from rag.query_rewriter import QueryRewriter

logger = logging.getLogger(__name__)


class LoveApp:
    """
    恋爱大师 AI 应用
    支持：基础对话、流式输出、RAG 知识库问答
    对应 Java: LoveApp.java
    """

    SYSTEM_PROMPT = (
        "扮演深耕恋爱心理领域的专家。开场向用户表明身份，告知用户可倾诉恋爱难题。"
        "围绕单身、恋爱、已婚三种状态提问"
        "：单身状态询问社交圈拓展及追求心仪对象的困扰；"
        "恋爱状态询问沟通、习惯差异引发的矛盾；已婚状态询问家庭责任与亲属关系处理的问题。"
        "引导用户详述事情经过、对方反应及自身想法，以便给出专属解决方案。"
    )

    def __init__(
        self,
        llm: BaseChatModel,
        retriever: Optional[VectorStoreRetriever] = None,
        llm_for_rewrite: Optional[BaseChatModel] = None,
    ):
        self._llm = llm
        self._retriever = retriever
        # 会话历史存储 {chat_id: InMemoryChatMessageHistory}
        self._sessions: dict[str, InMemoryChatMessageHistory] = {}
        self._query_rewriter = QueryRewriter(llm_for_rewrite or llm)

    def _get_session_history(self, chat_id: str) -> BaseChatMessageHistory:
        """获取或创建会话历史"""
        if chat_id not in self._sessions:
            self._sessions[chat_id] = InMemoryChatMessageHistory()
        return self._sessions[chat_id]

    def _build_prompt(self, use_rag: bool = False) -> ChatPromptTemplate:
        """构建提示词模板"""
        if use_rag and self._retriever:
            return ChatPromptTemplate.from_messages([
                ("system", f"{self.SYSTEM_PROMPT}\n\n上下文信息：\n{{context}}"),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ])
        return ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])

    def _build_chain(self):
        """构建基础对话链"""
        prompt = self._build_prompt(use_rag=False)
        return RunnableWithMessageHistory(
            prompt | self._llm,
            self._get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    def chat(self, message: str, chat_id: Optional[str] = None) -> str:
        """
        基础对话（同步）
        对应 Java: doChat(String message, String chatId)
        """
        chat_id = chat_id or str(uuid.uuid4())
        LoggerAdvisor.before_request(message)

        chain = self._build_chain()
        response = chain.invoke(
            {"input": message},
            config={"configurable": {"session_id": chat_id}},
        )

        content = response.content if hasattr(response, "content") else str(response)
        LoggerAdvisor.after_response(content)
        return content

    async def chat_stream(self, message: str, chat_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        SSE 流式对话
        对应 Java: doChatByStream(String message, String chatId)
        """
        chat_id = chat_id or str(uuid.uuid4())
        LoggerAdvisor.before_request(message)

        chain = self._build_chain()

        async for chunk in chain.astream(
            {"input": message},
            config={"configurable": {"session_id": chat_id}},
        ):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content
            elif isinstance(chunk, str):
                yield chunk

    def chat_with_rag(self, message: str, chat_id: Optional[str] = None) -> str:
        """
        结合 RAG 知识库对话
        对应 Java: doChatWithRage(String message, String chatId)
        """
        if not self._retriever:
            return "RAG 知识库未配置"

        chat_id = chat_id or str(uuid.uuid4())

        # 查询重写
        rewritten = self._query_rewriter.rewrite(message)
        LoggerAdvisor.before_request(f"[重写后] {rewritten}")

        # 手动实现 RAG：检索 + 组装 prompt + LLM
        docs = self._retriever.invoke(rewritten)
        context = "\n\n".join(
            doc.page_content if hasattr(doc, "page_content") else str(doc)
            for doc in docs[:3]
        )

        if not context.strip():
            return "抱歉，我只能回答恋爱相关的问题，别的没办法帮到您哦。"

        history = self._get_session_history(chat_id)
        messages = [SystemMessage(content=self.SYSTEM_PROMPT)]
        # 添加历史消息
        for msg in history.messages[-6:]:  # 最近 6 轮
            messages.append(msg)
        # 添加带上下文的用户消息
        messages.append(HumanMessage(
            content=f"上下文信息：\n{context}\n\n用户问题：{rewritten}"
        ))

        response = self._llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)

        # 保存到历史
        history.add_user_message(rewritten)
        history.add_ai_message(content)

        LoggerAdvisor.after_response(content)
        return content
