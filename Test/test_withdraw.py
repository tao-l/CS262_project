""" This test tests the withdraw() RPC service provided by the seller to the buyers """
# Import some necessary packages
import logging
logging.basicConfig(level=logging.CRITICAL)
from PyQt6.QtWidgets import QApplication

# Import the Seller object from seller.py
import sys
sys.path.append("../")
from seller import Seller

# Start a seller that provides RPC service at the given address
app = QApplication([])
s = Seller(username="test_seller", rpc_address="127.0.0.1:35000", server_stubs=[])
s.ui.show()

# Create some auctions in the seller's data structure:
from utils import AuctionData, UserData, ItemData
def get_some_auctions():
    some_auctions = {}
    
    for i in range(7):
        seller = UserData(f"test_seller")
        item = ItemData(f"item_{i}")
        base_price = i
        auction_id = f"auction_id_{i}"
        auction_name = f"auction_{i}"
        auction = AuctionData(auction_name, auction_id, seller, item, base_price)
        auction.increment = 1

        if i == 0:
            auction.buyers["buyer_1"] = True
            auction.buyers["buyer_2"] = True
            auction.buyers["buyer_3"] = True
            auction.started = True

        if i == 1:
            auction.buyers["buyer_1"] = True
            auction.buyers["buyer_2"] = True
            auction.started = False
            
        if i == 2:
            auction.buyers["buyer_1"] = True
            auction.buyers["buyer_2"] = True
            auction.started = False
        
        if i == 3:
            auction.buyers["buyer_1"] = True
            auction.buyers["buyer_2"] = True
            auction.started = True
            auction.finished = True
            auction.winner_username = "buyer_2"
            auction.transaction_price = 99999

        if i == 4:
            auction.buyers["buyer_1"] = True
            auction.buyers["buyer_2"] = True
            auction.started = False
            auction.finished = True
            auction.winner_username = ""
            auction.transaction_price = -1
        
        if i == 5:
            auction.buyers["buyer_1"] = True
            auction.buyers["buyer_2"] = True
            auction.buyers["buyer_3"] = False
            auction.started = True
            
        if i == 6:
            auction.buyers["buyer_1"] = False
            auction.buyers["buyer_2"] = True
            auction.started = True

        some_auctions[auction_id] = auction

    return some_auctions


with s.data.lock:
    s.data.my_auctions = get_some_auctions()
    s.ui_update_all_signal.emit()


# Then, we test the seller's withdraw RPC service
import grpc
import auction_pb2 as pb2
import auction_pb2_grpc
channel = grpc.insecure_channel("127.0.0.1:35000")
stub = auction_pb2_grpc.SellerServiceStub(channel)

def normal_withdraw():
    print("\n========= TEST : normal_withdraw ==== Begins =========")

    request = pb2.UserAuctionPair( username = "buyer_2", 
                                   auction_id = "auction_id_0" )
    assert s.data.my_auctions["auction_id_0"].buyers["buyer_2"] == True
    response = stub.withdraw(request)
    assert s.data.my_auctions["auction_id_0"].buyers["buyer_2"] == False
    print("Should see [buyer_2] withdraws from [auction_0] on screen")
    assert response.success == True
    assert s.data.my_auctions["auction_id_0"].finished == False

    request = pb2.UserAuctionPair( username = "buyer_1", 
                                   auction_id = "auction_id_0" )
    assert s.data.my_auctions["auction_id_0"].buyers["buyer_1"] == True
    response = stub.withdraw(request)
    assert s.data.my_auctions["auction_id_0"].buyers["buyer_1"] == False
    print("Should see [buyer_1] withdraws from [auction_0] on screen")
    print("And then the auction is finished.")
    assert response.success == True
    assert s.data.my_auctions["auction_id_0"].finished == True

    print("========= TEST : normal_withdraw ==== Good =========")
    
normal_withdraw()


def withdraw_non_existing_auction_and_user():
    print("\n========= TEST : withdraw_non_existing_auction_and_user ==== Begins =========")

    request = pb2.UserAuctionPair( username = "buyer_2", 
                                   auction_id = "no such auction" )
    response = stub.withdraw(request)
    print(response.message)
    assert response.success == False
    
    request = pb2.UserAuctionPair( username = "no such user", 
                                   auction_id = "auction_id_1" )
    response = stub.withdraw(request)
    print(response.message)
    assert response.success == False

    print("========= TEST : withdraw_non_existing_auction_and_user ==== Good =========")

withdraw_non_existing_auction_and_user()


def withdraw_non_started_auction_and_finished_auction():
    print("\n========= TEST : withdraw_non_started_auction_and_finished_auction ==== Begins =========")

    request = pb2.UserAuctionPair( username = "buyer_2", 
                                   auction_id = "auction_id_2" )  # non-started acution
    response = stub.withdraw(request)
    print(response.message)
    assert response.success == False
    assert s.data.my_auctions["auction_id_2"].buyers["buyer_2"] == True

    request = pb2.UserAuctionPair( username = "buyer_2", 
                                   auction_id = "auction_id_3" )  # finished (and started) auction
    response = stub.withdraw(request)
    print(response.message)
    assert response.success == False
    assert s.data.my_auctions["auction_id_3"].buyers["buyer_2"] == True

    request = pb2.UserAuctionPair( username = "buyer_2", 
                                   auction_id = "auction_id_4" )  # finished (and not started) auction
    response = stub.withdraw(request)
    print(response.message)
    assert response.success == False
    assert s.data.my_auctions["auction_id_4"].buyers["buyer_2"] == True

    print("========= TEST : withdraw_non_started_auction_and_finished_auction ==== Good =========")

withdraw_non_started_auction_and_finished_auction()


def withdraw_already_withdrawn_buyer():
    print("\n========= TEST : withdraw_already_withdrawn_buyer ==== Begins =========")

    request = pb2.UserAuctionPair( username = "buyer_3", 
                                   auction_id = "auction_id_5" )
    assert s.data.my_auctions["auction_id_5"].buyers["buyer_3"] == False
    response = stub.withdraw(request)
    print(response.message)
    assert response.success == True
    assert s.data.my_auctions["auction_id_5"].buyers["buyer_3"] == False
    print("========= TEST : withdraw_already_withdrawn_buyer ==== Good =========")

withdraw_already_withdrawn_buyer()


def withdraw_the_only_active_buyer():
    print("\n========= TEST : withdraw_the_only_active_buyer ==== Begins =========")
    print("Before withdraw, the auction is not finished") 
    assert s.data.my_auctions["auction_id_6"].finished == False

    request = pb2.UserAuctionPair( username = "buyer_2", 
                                   auction_id = "auction_id_6" )
    assert s.data.my_auctions["auction_id_6"].buyers["buyer_2"] == True
    response = stub.withdraw(request)
    print(response.message)
    assert response.success == False
    assert s.data.my_auctions["auction_id_6"].buyers["buyer_2"] == True
    print("After the (unsuccessful) withdraw, the auction should be finished")
    assert s.data.my_auctions["auction_id_6"].finished == True
    print("========= TEST : withdraw_the_only_active_buyer ==== Good =========")

withdraw_the_only_active_buyer()


print("All good!!! ")

app.exec()  # PtQt routine: execute the application

