import pytest
import grpc
from src.protos.generated import ai_engine_pb2, ai_engine_pb2_grpc

@pytest.mark.asyncio
class TestGRPCServer:
    async def test_load_model(self, grpc_channel):
        """测试加载模型API"""
        stub = ai_engine_pb2_grpc.AIEngineStub(grpc_channel)
        
        request = ai_engine_pb2.LoadModelRequest(
            model_name="test_model",
            model_path="/path/to/model",
            batch_size=1,
            min_workers=1,
            max_workers=1
        )
        
        response = await stub.LoadModel(request)
        assert response.success

    async def test_create_skill(self, grpc_channel):
        """测试创建技能API"""
        stub = ai_engine_pb2_grpc.AIEngineStub(grpc_channel)
        
        request = ai_engine_pb2.CreateSkillRequest(
            name="test_skill",
            type="detection",
            config={"model": "test_model"}
        )
        
        response = await stub.CreateSkill(request)
        assert response.success

    async def test_process_video_stream(self, grpc_channel):
        """测试视频流处理API"""
        stub = ai_engine_pb2_grpc.AIEngineStub(grpc_channel)
        
        async def request_iterator():
            # 模拟视频帧数据
            yield ai_engine_pb2.FrameData(
                task_id="test_task",
                frame=b"test_frame",
                skill_name="test_skill"
            )
        
        responses = []
        async for response in stub.ProcessVideoStream(request_iterator()):
            responses.append(response)
            
        assert len(responses) > 0
        assert all(isinstance(r, ai_engine_pb2.DetectionResult) for r in responses) 