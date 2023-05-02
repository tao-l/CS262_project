import json
import auction_pb2 as pb2
import config

def test_login():
    # prepare input
    request = pb2.PlatformServiceRequest()
    js = {"op":config.LOGIN, "username": "name", "address":"127.0.0.1:4056"}
    request.json = json.dumps(js)
    # call platform service
    response = stub.rpc_platform_serve(request)
    
    # parsing output
    if response.is_leader:
        js = json.loads(response.json)
        if js["success"]: 
            # Do operation here
        else:
            # other operation here
        print(js["message"])
    

def test_get_user_address():
    # prepare input
    request = pb2.PlatformServiceRequest()
    js = {"op":config.GET_USER_ADDRESS, "username": "name"}
    request.json = json.dumps(js)
    # call platform service
    response = stub.rpc_platform_serve(request)
    
    if response.is_leader:
        js = json.loads(response.json)
        if js["success"]: 
            address = js["message"]
            ip = address.split(":")[0]
            port = address.split(":")[1]
            # Do operation here
        else:
            # other operation here
        print(js["message"])

def test_buyer_fetch_auctions():
    # prepare input
    request = pb2.PlatformServiceRequest()
    js = {"op":config.BUYER_FETCH_AUCTIONS, "username": "myname"}
    request.json = json.dumps(js)

    # call platform service
    response = stub.rpc_platform_serve(request)
    
    if response.is_leader:
        js = json.loads(response.json)
        if js["success"]: 
            for auction in js["message"]:
                auction_data = AuctionData()
                auction_data.update_from_dict(auction)
                # Do operation here, check if I have participated
                # info control realized by the platform
                if "myname" in auction_data.buyers:
                    pass
                else:
                    pass
        else:
            # other operation here
            print(js["message"])


def test_seller_fetch_auctions()
    # prepare input
    request = pb2.PlatformServiceRequest()
    js = {"op":config.BUYER_FETCH_AUCTIONS, "username": "myname"}
    request.json = json.dumps(js)

    # call platform service
    response = stub.rpc_platform_serve(request)
    
    if response.is_leader:
        js = json.loads(response.json)
        if js["success"]: 
            # only auctions 
            for auction in js["message"]:
                auction_data = AuctionData()
                auction_data.update_from_dict(auction)
                # Do operation here, checking whether this auction belong to seller herself
                # info control realized by the platform
                if auction_data.seller.username == "myname":
                    pass
                else:
                    pass
                
        else:
            # other operation here
            # myname does not exist
            print(js["message"])

def test_buyer_join_auction()
    # prepare input
    request = pb2.PlatformServiceRequest()
    js = {"op":config.BUYER_JOIN_AUCTION, "username": "myname", "auction_id":"1"}
    request.json = json.dumps(js)

    # call platform service
    response = stub.rpc_platform_serve(request)
    
    if response.is_leader:
        js = json.loads(response.json)
        if not js["success"]:
            # auction started or finished
            pass
        else:
            pass
        print(js["message"])

def test_buyer_quit_auction():
    # prepare input
    request = pb2.PlatformServiceRequest()
    js = {"op":config.BUYER_QUIT_AUCTION, "username": "myname", "auction_id":"1"}
    request.json = json.dumps(js)

    # call platform service
    response = stub.rpc_platform_serve(request)
    
    if response.is_leader:
        js = json.loads(response.json)
        if not js["success"]:
            # auction started or finished
            pass
        else:
            pass
        print(js["message"])

def test_seller_create_auction():
    # prepare input
    request = pb2.PlatformServiceRequest()
    js = auction_data.to_dict()
    js["op"] = config.SELLER_CREATE_AUCTION
    request.json = json.dumps=(js)

    # call platform service
    response = stub.rpc_platform_serve(request)
    
    if response.is_leader:
        js = json.loads(response.json)
        if not js["success"]:
            print(js["message"]) # an identical auction exists
        else:
            auction_id = js["message"].split(" ")[1]

# same for seller_finish_auction
def test_seller_start_auction():
    # prepare input
    request = pb2.PlatformServiceRequest()
    js = {"op":config.SELLER_START_AUCTION, "username": "myname", "auction_id":"1"}
    request.json = json.dumps(js)
    response = pb2.PlatformServiceResponse()
    if response.is_leader:
        js = json.loads(response.json)
        pass # based on js["success"]

def test_seller_update_auction():
    # prepare input
    request = pb2.PlatformServiceRequest()
    js = auction_data.to_dict()
    js["op"] = config.SELLER_UPDATE_AUCTION
    request.json = json.dumps(js)
    response = pb2.PlatformServiceResponse()
    if response.is_leader:
        js = json.loads(response.json)
        pass # based on js["success"] and print js["message"]


