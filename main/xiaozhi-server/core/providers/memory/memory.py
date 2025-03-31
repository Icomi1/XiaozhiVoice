from .base import MemoryProviderBase
from config.logger import setup_logging
import json
import os

TAG = __name__
logger = setup_logging()

class MemoryProvider(MemoryProviderBase):
    def __init__(self, config):
        # 先初始化父类
        super().__init__(config)
        # 初始化自己的属性
        self.memories = []
        self.memory_file = "tmp/memory.json"
        # 确保 current_user_id 存在
        if not hasattr(self, 'current_user_id'):
            self.current_user_id = None
        # 加载记忆
        self.load_memory()

    def load_memory(self):
        """从文件加载记忆"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = data.get('memories', [])
                    if 'current_user_id' in data:
                        self.current_user_id = data['current_user_id']
                    if 'role_id' in data:
                        self.role_id = data['role_id']
                    logger.bind(tag=TAG).info(f"已加载记忆，当前用户: {self.current_user_id}")
            else:
                # 如果文件不存在，确保 current_user_id 为 None
                self.current_user_id = None
                self.role_id = None
                logger.bind(tag=TAG).info("记忆文件不存在，初始化新记忆")
        except Exception as e:
            logger.bind(tag=TAG).error(f"加载记忆失败: {e}")
            # 确保在加载失败时也设置 current_user_id
            self.current_user_id = None
            self.role_id = None
            self.memories = []

    def save_memory_to_file(self):
        """保存记忆到文件"""
        try:
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'memories': self.memories,
                    'current_user_id': self.current_user_id,
                    'role_id': self.role_id
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.bind(tag=TAG).error(f"保存记忆失败: {e}")

    async def save_memory(self, msgs):
        """保存新的记忆"""
        self.memories.append(msgs)
        self.save_memory_to_file()
        logger.bind(tag=TAG).debug(f"保存新记忆: {msgs}")
        return len(self.memories) - 1

    async def query_memory(self, query: str) -> str:
        """查询记忆"""
        # 简单实现：返回最近的记忆
        if not self.memories:
            return "没有找到相关记忆"
        return str(self.memories[-1])

    def init_memory(self, role_id: str, llm=None):
        """初始化记忆，但保留已存在的用户ID"""
        # 先调用父类的 init_memory
        super().init_memory(role_id, llm)
        # 如果没有当前用户ID，则设置
        if not self.current_user_id:
            self.current_user_id = role_id
            self.save_memory_to_file()
            logger.bind(tag=TAG).info(f"初始化记忆，设置默认用户ID: {role_id}")
        else:
            logger.bind(tag=TAG).info(f"保留现有用户ID: {self.current_user_id}")

    def set_current_user(self, user_id: str):
        """设置当前用户ID"""
        # 先调用父类的 set_current_user
        super().set_current_user(user_id)
        # 保存到文件
        self.save_memory_to_file()
        logger.bind(tag=TAG).info(f"设置当前用户为: {user_id}")

# 创建全局 memory_provider 实例
memory_provider = MemoryProvider(config={}) 