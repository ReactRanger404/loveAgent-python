"""上下文查询增强器 - 对应 Java 的 LoveAppContextualQueryAugmenterFactory"""


class QueryAugmenter:
    """
    上下文查询增强器
    当检索结果为空时，返回预设的提示信息
    对应 Java: LoveAppContextualQueryAugmenterFactory
    """

    @staticmethod
    def create_prompt() -> str:
        """
        创建空上下文时的提示模板
        对应 Java 的 emptyContextPromptTemplate
        """
        return "抱歉，我只能回答恋爱相关的问题，别的没办法帮到您哦。"
