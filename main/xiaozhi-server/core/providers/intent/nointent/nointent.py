from ..base import IntentProviderBase
from typing import List, Dict
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

class IntentProvider(IntentProviderBase):
    async def detect_intent(self, dialogue_history: List[Dict]) -> str:
        """
        默认的意图识别实现，始终返回继续聊天
        Args:
            dialogue_history: 对话历史记录列表
        Returns:
            固定返回"继续聊天"
        """
        logger.bind(tag=TAG).debug("Using NoIntentProvider, always returning continue chat")
        return self.intent_options["continue_chat"]
