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
    
    for i in range(4):
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
            auction.buyers["test_buyer"] = True
            auction.started = False
        
        if i == 3:
            auction.buyers["buyer_1"] = True
            auction.buyers["test_buyer"] = True
            auction.started = True
            auction.round_id = 3

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


def announce_price_for_non_started_auction():
    print("\n========= TEST : announce_price_for_non_started_auction ==== Begins =========")
    request = pb2.AnnouncePriceRequest(auction_id = "auction_id_0",
                                       round_id = 0, 
                                       price = 100)
    assert b.data.auctions["auction_id_0"].round_id == -1
    assert b.data.auctions["auction_id_0"].started == False
    stub.announce_price(request)
    assert b.data.auctions["auction_id_0"].round_id == 0
    assert b.data.auctions["auction_id_0"].started == True
    assert b.data.auctions["auction_id_0"].current_price == 100
    print("On Buyer's UI, should see [test_buyer] did not join [auction_0] because the buyer status does not include this buyer.")
    print("========= TEST : announce_price_for_non_started_auction ==== Good =========")
    
announce_price_for_non_started_auction()


def announce_price_and_withdraw_the_test_buyer():
    print("\n========= TEST : announce_price_and_withdraw_the_test_buyer ==== Begins =========")
    auctions_copy = get_some_auctions()
    auctions_copy["auction_id_1"].buyers["test_buyer"] = False
    request = pb2.AnnouncePriceRequest(
                auction_id = "auction_id_1",
                round_id = 1, 
                price = 200, 
                buyer_status = auctions_copy["auction_id_1"].get_buyer_status_list())
    assert b.data.auctions["auction_id_1"].buyers["test_buyer"] == True
    stub.announce_price(request)
    assert b.data.auctions["auction_id_1"].round_id == 1
    assert b.data.auctions["auction_id_1"].current_price == 200
    assert b.data.auctions["auction_id_1"].buyers["test_buyer"] == False
    print("Should see [test_buyer] has withdrawn from [auction_1] on the UI.")
    print("========= TEST : announce_price_and_withdraw_the_test_buyer ==== Good =========")
    
announce_price_and_withdraw_the_test_buyer()


def announce_price_and_withdraw_other_buyers():
    print("\n========= TEST : announce_price_and_withdraw_other_buyers ==== Begins =========")
    auctions_copy = get_some_auctions()
    auctions_copy["auction_id_2"].buyers["buyer_2"] = False
    request = pb2.AnnouncePriceRequest(
                auction_id = "auction_id_2",
                round_id = 1, 
                price = 200, 
                buyer_status = auctions_copy["auction_id_2"].get_buyer_status_list())
    assert b.data.auctions["auction_id_2"].buyers["buyer_2"] == True
    stub.announce_price(request)
    assert b.data.auctions["auction_id_2"].buyers["buyer_2"] == False
    print("Should see [buyer_2] has withdrawn from [auction_2] on the UI.")
    print("========= TEST : announce_price_and_withdraw_other_buyers ==== Good =========")
    
announce_price_and_withdraw_other_buyers()


def announce_price_for_an_auction_that_the_buyer_did_not_join():
    print("\n======== TEST : announce_price_for_an_auction_that_the_buyer_did_not_join === Begins ========")
    request = pb2.AnnouncePriceRequest(
                auction_id = "no_such_auction",
                round_id = 1, 
                price = 200)
    assert "no_auch_aucion" not in b.data.auctions
    stub.announce_price(request)
    assert "no_auch_aucion" not in b.data.auctions
    print("Nothing should happen.")
    print("======== TEST : announce_price_and_withdraw_other_buyers === Good ========")
    
announce_price_for_an_auction_that_the_buyer_did_not_join()


def announce_price_with_a_smaller_round_id():
    print("\n======== TEST : announce price with a smaller (out-dated) round id === Begins ========")
    auctions_copy = get_some_auctions()
    request = pb2.AnnouncePriceRequest(
                auction_id = "auction_id_3",
                round_id = 2, 
                price = 200)
    assert b.data.auctions["auction_id_3"].round_id == 3
    stub.announce_price(request)
    assert b.data.auctions["auction_id_3"].round_id == 3
    print("Nothing should happen.")
    print("======== TEST : announce price with a smaller (out-dated) round id === Good ========")
    
announce_price_with_a_smaller_round_id()

print("\nAll good!!! ")

app.exec()  # PtQt routine: execute the application

