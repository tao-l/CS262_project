from utils import *

class Test_1:
    def __init__(self):
        self.all_auctions = {}

        buyer_1 = UserData("buyer_1")
        buyer_2 = UserData("buyer_2")
        buyer_3 = UserData("buyer_3")

        for i in range(7):
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
            
            self.all_auctions[auction_id] = auction


    def get_all_auctions(self):
        return self.all_auctions
    
    
    def create_auction(self, request):
        new_auction_id = f"auction_id_{len(self.all_auctions)}"
        new_auction = AuctionData(name = request["auction_name"],
                                  id = new_auction_id, 
                                  seller = UserData(request["seller_username"]),
                                  item = ItemData(request["item_name"]), 
                                  base_price = request["base_price"],
                                  price_increment_period = request["price_increment_period"],
                                  increment = request["increment"])
        self.all_auctions[new_auction_id] = new_auction
        return True, "success"
    

    def find_address_from_server(self, username):
        if username == "seller_2":
            return True, RPC_Address(ip="127.0.0.1", port="60000")
        elif username == "buyer_1":
            return True, RPC_Address(ip="127.0.0.1", port="60001")
        elif username == "buyer_3":
            return True, RPC_Address(ip="127.0.0.1", port="60003")
        return False, None


test_1 = Test_1()
