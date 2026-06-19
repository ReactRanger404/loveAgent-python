"""Re2（Re-reading）Advisor - 对应 Java 的 ReReadingAdvisor"""


class ReReadingAdvisor:
    """
    自定义 Re2 Advisor
    通过重读用户提示词来提高 LLM 的推理能力
    对应 Java: ReReadingAdvisor.java
    """

    @staticmethod
    def augment_prompt(user_text: str) -> str:
        """
        改写 Prompt：在用户提示词后追加 'Read the question again'
        """
        return f"{user_text}\nRead the question again: {user_text}"
