from utils import *
import copy
import logging

class Test_1:
    def __init__(self):
        self.all_auctions = {}
        self.addresses = {}

        self.addresses["seller_2"] = "127.0.0.1:60000"
        self.addresses["buyer_1"] =  "127.0.0.1:60001"
        self.addresses["buyer_3"] = "127.0.0.1:60003"
        

        buyer_1 = UserData("buyer_1")
        buyer_2 = UserData("buyer_2")
        buyer_3 = UserData("buyer_3")

        for i in range(9):
            seller = UserData(f"seller_{i}")
            item = ItemData(f"item_{i}")
            base_price = i
            auction_id = f"auction_id_{i}"
            auction_name = f"auction_{i}"
            auction = AuctionData(auction_name, auction_id, seller, item, base_price)
            auction.increment = 1

            if i == 1:
                auction.seller = UserData("seller_1")
                auction.buyers[buyer_1.username] = True
                auction.buyers[buyer_2.username] = True
                auction.started = False
            
            if i == 2: 
                auction.seller = UserData("seller_2")
                auction.buyers[buyer_1.username] = True
                auction.buyers[buyer_2.username] = True
                auction.started = False
            
            if i == 3:
                auction.seller = UserData("seller_2")
                auction.buyers[buyer_1.username] = True
                auction.buyers[buyer_2.username] = False
                auction.buyers[buyer_3.username] = True
                auction.started = True
            
            if i == 4:
                auction.seller = UserData("seller_2")
                auction.buyers[buyer_1.username] = False
                auction.buyers[buyer_2.username] = True
                auction.started = True
            
            if i == 5:
                auction.seller = UserData("seller_2")
                auction.buyers[buyer_1.username] = True
                auction.buyers[buyer_2.username] = True
                auction.buyers[buyer_3.username] = True
                auction.started = True

            if i == 6:
                auction.started = True
                auction.finished = True
                auction.winner_username = "buyer_3"
                auction.transaction_price = 99999
            
            
            if i == 7:
                auction.started = False
                auction.finished = True
                auction.buyers[buyer_1.username] = True
                auction.winner_username = ""
                auction.transaction_price = 99999

            self.all_auctions[auction_id] = auction
    

    def login(self, request):
        self.addresses[request["username"]] = request["address"]
        return {"success": True, "message": "Login successful"}
    

    def get_all_auctions(self, request):
        list_of_dicts = []
        for (id, a) in self.all_auctions.items():
            list_of_dicts.append( a.to_dict() )
        return {"success": True, "message":list_of_dicts}
    
    
    def create_auction(self, request):
        new_auction_id = f"auction_id_{len(self.all_auctions)}"
        new_auction = AuctionData(name = request["auction_name"],
                                  id = new_auction_id, 
                                  seller = UserData(request["seller_username"]),
                                  item = ItemData(name = request["item_name"], description = request["item_description"]), 
                                  base_price = request["base_price"],
                                  price_increment_period = request["price_increment_period"],
                                  increment = request["increment"])
        self.all_auctions[new_auction_id] = new_auction
        return {"success": True, "message":"success"}
    

    def start_auction(self, request):
        auction_id = request["auction_id"]
        auction = self.all_auctions[auction_id]
        assert request["username"] == auction.seller.username
        assert auction.finished == False
        if auction.started == True:
            return {"success": True, "message": "success"}
        else:
            auction.started = True
            return {"success": True, "message": auction.to_dict()}
    
    
    def finish_auction(self, request):
        auction_id = request["auction_id"]
        if self.all_auctions[auction_id].finished == True: 
            print(f" ====================== Platform: auction {auction_id} trying to finish ----- already finished ----------")
            return {"success": True, "message" : "Auction already finished"}
        else:
            print(f" ======================= Platform: auction {auction_id} trying to finish ----- good ----------")
            assert request["finished"] == True
            self.all_auctions[auction_id].update_from_dict(request)
            return {"success": True, "message" : "Auction finished successfully"}
    

    def buyer_join_auction(self, request):
        auction_id = request["auction_id"]
        buyer_id = request["username"]
        if auction_id not in self.all_auctions:
            return {"success": False, "message": "Auction does not exists"}
        auction = self.all_auctions[auction_id]
        if auction.started == True:
            return {"success": False, "message": "Auction has started"} 
        if auction.finished == True:
            return {"success": False, "message": "Auction has finished"} 
        
        auction.buyers[buyer_id] = True
        return {"success": True, "message": "Success"}
    
    def buyer_quit_auction(self, request):
        auction_id = request["auction_id"]
        buyer_id = request["username"]
        if auction_id not in self.all_auctions:
            return {"success": False, "message": "Auction does not exists"}
        auction = self.all_auctions[auction_id]
        if auction.started == True:
            return {"success": False, "message": "Auction has started. Cannot quit."} 
        if auction.finished == True:
            return {"success": False, "message": "Auction has finished"}
        if buyer_id in auction.buyers:
            auction.buyers.pop(buyer_id)
        return {"success": True, "message": "Success"}


    def find_address_from_server(self, username):
        if username in self.addresses:
            return True, self.addresses[username]
        return False, f"Cannot find the address of {username}"
    

    def rpc_to_server(self, request):
        """ rpc_to_server for testing.
        
        - Input: request : a dictionary
        - Output: (server_ok, response), where
            - server_ok : bool
            - response  : a dictionary
        """
        logging.debug("Test 1: rpc_to_server, request:", request)
        server_ok = True
        if request["op"] == "GET_USER_ADDRESS":
            success, addr = self.find_address_from_server(request["username"])
            return server_ok, {"success": success, "message":addr}
        elif request["op"] == "BUYER_JOIN_AUCTION":
            return server_ok, self.buyer_join_auction(request)
        elif request["op"] == "BUYER_QUIT_AUCTION":
            return server_ok, self.buyer_quit_auction(request)
        elif request["op"] == "BUYER_FETCH_AUCTIONS":
            return server_ok, self.get_all_auctions(request)
        elif request["op"] == "SELLER_CREATE_AUCTION":
            return server_ok, self.create_auction(request)
        elif request["op"] == "SELLER_START_AUCTION":
            return server_ok, self.start_auction(request)
        elif request["op"] == "SELLER_FETCH_AUCTIONS":
            return server_ok, self.get_all_auctions(request)
        elif request["op"] == "SELLER_FINISH_AUCTION":
            return server_ok, self.finish_auction(request)
        elif request["op"] == "LOGIN":
            return server_ok, self.login(request)
        else:
            raise Exception("operation " + request["op"] + " not supported!")


test_1 = Test_1()
