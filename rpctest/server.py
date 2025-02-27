import grpc
from concurrent import futures # Python的concurrent.futures库提供了ThreadPoolExecutor和ProcessPoolExecutor两个执行器，可以用来在单独的线程或进程中执行任务
import time

import hello_pb2
import hello_pb2_grpc
# hello_pb2.py 处理消息类型的定义和序列化/反序列化。
# hello_pb2_grpc.py 处理 gRPC 服务的定义以及客户端与服务器代码的生成。


#实现HelloService服务
class HelloService(hello_pb2_grpc.HelloServicer):
    def SayHello(self, request, context):
        #收到请求
        print("Received request: %s" % request.name)
        return hello_pb2.HelloResponse(message='Hello, %s!' % request.name)



# 启动服务器
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    hello_pb2_grpc.add_HelloServicer_to_server(HelloService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server is running on port 50051...")
    try:
        while True:
            time.sleep(3600) #休眠的是主线程，而不是处理请求的线程。
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()