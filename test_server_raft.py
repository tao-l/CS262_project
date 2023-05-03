import grpc
import json
import config
import server
import auction_pb2
import auction_pb2_grpc

   
if __name__ == "__main__":

    ### 1) use terminal to start three servers

    ### create a stub
    channel = grpc.insecure_channel('127.0.0.1:20010')
    stub =  auction_pb2_grpc.PlatformServiceStub(channel)

    # login and create a seller
    request = auction_pb2.PlatformServiceRequest()
    request.json = json.dumps({"op":config.LOGIN, "username":"buyer0","address":"127.0.0.1:20011"})
    
    response = stub.rpc_platform_serve(request)
