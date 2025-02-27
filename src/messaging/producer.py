from typing import Dict, Any
from rocketmq.client import Producer, Message
import json
from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class RocketMQProducer:
    def __init__(self):
        self.config = Config()
        self._producer = None

    async def start(self):
        """启动生产者"""
        try:
            self._producer = Producer(self.config.rocketmq["group_id"])
            self._producer.set_name_server_address(self.config.rocketmq["name_server"])
            self._producer.start()
            logger.info("RocketMQ producer started successfully")
        except Exception as e:
            logger.error(f"Failed to start RocketMQ producer: {str(e)}")
            raise

    async def send_message(
        self, 
        data: Dict[str, Any], 
        tags: str = None, 
        keys: str = None
    ) -> bool:
        """发送消息到RocketMQ"""
        if not self._producer:
            raise RuntimeError("Producer not started")

        try:
            message = Message(self.config.rocketmq["topics"]["result"])
            message.set_body(json.dumps(data).encode('utf-8'))
            
            if tags:
                message.set_tags(tags)
            if keys:
                message.set_keys(keys)

            send_result = self._producer.send_sync(message)
            logger.info(f"Message sent successfully, msgId: {send_result.msg_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False

    async def stop(self):
        """停止生产者"""
        if self._producer:
            try:
                self._producer.shutdown()
                logger.info("RocketMQ producer stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping RocketMQ producer: {str(e)}") 