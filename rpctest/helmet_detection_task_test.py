import asyncio
import grpc
from protos.ts_scripts import task_pb2, task_pb2_grpc
from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

async def test_helmet_detection():
    config = Config()
    server_addr = f"{config.server['host']}:{config.server['port']}"

    async with grpc.aio.insecure_channel(server_addr) as channel:
        stub = task_pb2_grpc.TaskServiceStub(channel)

        try:
            # 创建安全帽检测任务请求
            request = task_pb2.StartTaskRequest(
                video_stream="rtsp://admin:admin123@192.168.1.64:554/cam/realmonitor?channel=1&subtype=0",
                skill_name="helmet_detection",  # 使用安全帽检测技能
                alert_level=2,  # 提高告警级别
                frame_rate=10.0,  # 降低帧率以减少资源消耗
                roi=[0.0, 0.0, 1.0, 1.0],  # 全画面检测
                duration=300,  # 运行5分钟
                labels={
                    "camera": "construction_site",
                    "location": "working_area",
                    "type": "safety_monitor"
                },
                parameters={
                    "confidence_threshold": "0.6",  # 提高置信度阈值
                    "nms_threshold": "0.45",
                    "min_person_size": "50",  # 最小目标尺寸
                    "check_interval": "2",  # 检测间隔（秒）
                }
            )

            # 发送启动任务请求
            response = await stub.StartTask(request)
            logger.info(f"Helmet detection task started: {response}")
            task_id = response.task_id

            # 监控任务状态
            for _ in range(5):  # 每10秒查询一次状态，共5次
                await asyncio.sleep(10)
                status_request = task_pb2.TaskStatusRequest(task_id=task_id)
                status = await stub.GetTaskStatus(status_request)
                logger.info(f"Task status: {status}")

            # 运行60秒后停止
            await asyncio.sleep(60)

            # 停止任务
            stop_request = task_pb2.StopTaskRequest(task_id=task_id)
            stop_response = await stub.StopTask(stop_request)
            logger.info(f"Task stopped: {stop_response}")

        except grpc.RpcError as e:
            logger.error(f"RPC error: {e.details()}")
        except Exception as e:
            logger.error(f"Error: {str(e)}")

def main():
    try:
        asyncio.run(test_helmet_detection())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")

if __name__ == "__main__":
    main()