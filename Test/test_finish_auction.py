""" This test tests the announce_price() RPC service provided by the buyer to the seller """
# Import some necessary packages
import logging
logging.basicConfig(level=logging.CRITICAL)
from PyQt6.QtWidgets import QApplication

# Import the Buyer object from buyer.py
import sys
sys.path.append('../')
import buyer
buyer.DEMON = False 

# Start a buyer that provides RPC service at the given address
app = QApplication([])
b = buyer.Buyer(username="test_buyer", rpc_address="127.0.0.1:35000", server_stubs=[])
b.ui.show()

# Create some auctions in the buyer's data structure:
from utils import AuctionData, UserData, ItemData
def get_some_auctions():
    some_auctions = {}
    
    for i in range(3):
        seller = UserData(f"seller_1")
        item = ItemData(f"item_{i}")
        base_price = i
        auction_id = f"auction_id_{i}"
        auction_name = f"auction_{i}"
        auction = AuctionData(auction_name, auction_id, seller, item, base_price)
        auction.increment = 1

        if i == 0:
            auction.buyers["test_buyer"] = True
            auction.buyers["buyer_2"] = True
            auction.buyers["buyer_3"] = True
            auction.started = False

        if i == 1:
            auction.buyers["test_buyer"] = True
            auction.buyers["buyer_2"] = True
            auction.buyers["buyer_3"] = True
            auction.buyers["buyer_4"] = True
            auction.started = True
            
        if i == 2:
            auction.buyers["buyer_1"] = True
            auction.buyers["buyer_2"] = True
            auction.started = True

        some_auctions[auction_id] = auction

    return some_auctions


with b.data.lock:
    b.data.auctions = get_some_auctions()

b.ui_update_all_signal.emit()


# Then, we test the seller's withdraw RPC service
import grpc
import auction_pb2 as pb2
import auction_pb2_grpc
channel = grpc.insecure_channel("127.0.0.1:35000")
stub = auction_pb2_grpc.BuyerServiceStub(channel)

def finish_a_non_started_auction():
    print("\n========= TEST : finish a non-started auction ==== Begins =========")
    data_copy = get_some_auctions()
    request = pb2.FinishAuctionRequest(
                    auction_id = "auction_id_0",
                    winner_username = "", 
                    price = -1,
                    buyer_status = data_copy["auction_id_0"].get_buyer_status_list())
    assert b.data.auctions["auction_id_0"].finished == False
    stub.finish_auction(request)
    assert b.data.auctions["auction_id_0"].finished == True
    assert b.data.auctions["auction_id_0"].winner_username == ""
    assert b.data.auctions["auction_id_0"].transaction_price == -1
    print("Should see [auction_0] is finished without a winner")
    print("========= TEST : finish a non-started auction ==== Good =========")

finish_a_non_started_auction()


def finish_a_started_auction():
    print("\n========= TEST : finish a started auction ==== Begins =========")
    data_copy = get_some_auctions()
    request = pb2.FinishAuctionRequest(
                    auction_id = "auction_id_1",
                    winner_username = "amazing winner", 
                    price = 9999,
                    buyer_status = data_copy["auction_id_1"].get_buyer_status_list())
    assert b.data.auctions["auction_id_1"].finished == False
    stub.finish_auction(request)
    assert b.data.auctions["auction_id_1"].finished == True
    assert b.data.auctions["auction_id_1"].winner_username == "amazing winner"
    assert b.data.auctions["auction_id_1"].transaction_price == 9999
    print("Should see [auction_1] is finished with winner 'amazing winner'")
    print("========= TEST : finish a started auction ==== Good =========")

finish_a_started_auction()


def finish_an_auction_that_is_in_test_buyers_list_but_does_not_have_test_buyer():
    print("\n========= TEST : finish an auction that is in [test_buyer]'s list but does not have the test buyer ==== Begins =========")
    data_copy = get_some_auctions()
    request = pb2.FinishAuctionRequest(
                    auction_id = "auction_id_2",
                    winner_username = "amazing winner", 
                    price = 9999,
                    buyer_status = data_copy["auction_id_2"].get_buyer_status_list())
    assert b.data.auctions["auction_id_2"].finished == False
    stub.finish_auction(request)
    assert b.data.auctions["auction_id_2"].finished == True
    print("Should see [auction_2] is finished. But cannot see the list of buyers because [test_buyer] does not join this auction.")
    print("========= TEST : finish an auction that is in [test_buyer]'s list but does not have the test buyer ==== Good =========")

finish_an_auction_that_is_in_test_buyers_list_but_does_not_have_test_buyer()


def finish_an_auction_that_is_not_in_test_buyers_list():
    print("\n========= TEST : finish an auction that is not in [test_buyer]'s list ==== Begins =========")
    request = pb2.FinishAuctionRequest(
                    auction_id = "no such auction")
    assert "no such auction" not in b.data.auctions
    stub.finish_auction(request)
    assert "no such auction" not in b.data.auctions
    print("Nothing should happen")
    print("========= TEST : finish an auction that is not in [test_buyer]'s list ==== Good =========")

finish_an_auction_that_is_not_in_test_buyers_list()

print("\nAll good!!! ")

app.exec()  # PtQt routine: execute the application

