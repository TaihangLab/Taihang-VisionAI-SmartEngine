import grpc
import hello_pb2
import hello_pb2_grpc
# hello_pb2.py 处理消息类型的定义和序列化/反序列化。
# hello_pb2_grpc.py 处理 gRPC 服务的定义以及客户端与服务器代码的生成。


# 创建一个gRPC通道
def run():
    # 连接RPC服务器
    channel = grpc.insecure_channel('localhost:50051')

    # 创建一个stub
    # stub 是客户端调用远程服务时的代理对象。它充当了一个**“占位符”**，客户端通过它来发送请求，服务器通过它来接收请求并返回响应。它的作用是封装通信的细节。
    stub = hello_pb2_grpc.HelloStub(channel)

    # 创建请求
    request = hello_pb2.HelloRequest(name="World")

    # 调用RPC SayHello方法
    response = stub.SayHello(request)
    print("Greeter client received: " + response.message)

if __name__ == '__main__':
    run()