import grpc
import json

import sys
sys.path.append('../')
import config
import server
import auction_pb2
import auction_pb2_grpc

   
if __name__ == "__main__":

    ### 1) use terminal to start three servers

    ### create a stub
    channel = grpc.insecure_channel('127.0.0.1:20020')
    stub =  auction_pb2_grpc.PlatformServiceStub(channel)

    # login and create a seller
    request = auction_pb2.PlatformServiceRequest()
    request.json = json.dumps({"op":config.LOGIN, "username":"buyer0","address":"127.0.0.1:20011"})
    response = stub.rpc_platform_serve(request)
    print(response.is_leader)
    print(response.json)

    # create an auction
    request = auction_pb2.PlatformServiceRequest()
    js = {
                "seller_username":"buyer0",
                "auction_name":"selling fake item",
                "item_name": "fake item",
                "base_price": 0,
                "price_increment_period": 300,
                "increment":1,
                "item_description": "fake item description"
        }
    js["op"] = config.SELLER_CREATE_AUCTION
    request.json = json.dumps(js)
    response = stub.rpc_platform_serve(request)
    print(response.json)

    # fetch auction
    request = auction_pb2.PlatformServiceRequest()
    request.json = json.dumps({"op":config.LOGIN, "username":"buyer1","address":"127.0.0.1:20023"})
    response = stub.rpc_platform_serve(request)
    
    request.json = json.dumps({"op":config.BUYER_FETCH_AUCTIONS,"username":"buyer1"})
    response = stub.rpc_platform_serve(request)
    print(response.json)





