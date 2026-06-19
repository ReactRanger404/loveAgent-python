"""日志记录 Advisor - 对应 Java 的 MyLoggerAdvisor"""
import logging

logger = logging.getLogger(__name__)


class LoggerAdvisor:
    """
    自定义日志 Advisor
    打印请求和响应的文本内容
    对应 Java: MyLoggerAdvisor.java
    """

    @staticmethod
    def before_request(prompt: str):
        """记录请求"""
        logger.info("AI Request: %s", prompt)

    @staticmethod
    def after_response(response: str):
        """记录响应"""
        logger.info("AI Response: %s", response)
