import asyncio
import grpc
from protos.ts_scripts import task_pb2, task_pb2_grpc
from src.core.config import Config


async def test_task():
    config = Config()
    server_addr = f"{config.server['host']}:{config.server['port']}"

    # 创建异步通道
    async with grpc.aio.insecure_channel(server_addr) as channel:
        # 创建任务服务存根
        stub = task_pb2_grpc.TaskServiceStub(channel)

        try:
            # 创建任务请求
            request = task_pb2.StartTaskRequest(
                video_stream="rtsp://admin:admin123@192.168.1.64:554/cam/realmonitor?channel=1&subtype=0",
                skill_name="person_detection",
                alert_level=1,
                frame_rate=15.0,
                roi=[0.1, 0.1, 0.9, 0.9],  # [x1, y1, x2, y2]
                duration=60,  # 运行60秒
                labels={
                    "camera": "entrance",
                    "location": "main_gate"
                },
                parameters={
                    "confidence_threshold": "0.5",
                    "nms_threshold": "0.45"
                }
            )

            # 发送启动任务请求
            response = await stub.StartTask(request)
            print(f"Task started: {response}")

            # 等待一段时间
            await asyncio.sleep(10)

            # 发送停止任务请求
            stop_request = task_pb2.StopTaskRequest(
                task_id=response.task_id
            )
            stop_response = await stub.StopTask(stop_request)
            print(f"Task stopped: {stop_response}")

        except grpc.RpcError as e:
            print(f"RPC error: {e.details()}")
        except Exception as e:
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_task())