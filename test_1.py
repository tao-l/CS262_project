from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QMainWindow

from buyer import Buyer
from seller import Seller

import auction_pb2 as pb2

import time
import threading

import utils


def test_handle_announce_price(buyer):
    def announce_price_many_times(auction_id, times):
        price = 0
        for i in range(times):
            price += 1
            request = pb2.AnnouncePriceRequest(auction_id = auction_id,
                                               round_id   = i, 
                                               price      = price)
            threading.Thread(target = buyer.handle_announce_price,
                             args   = (request,),
                             daemon = True).start()
    
    print("Test: ------  buyer's handle_announce_price() ----- begins ---------- ")
    time.sleep(2)
    auction_id = "no such auction";  times = 100
    announce_price_many_times(auction_id, times)
    print(f"Test: (1) Nothing should happen, because [{auction_id}] is not in buyer's auction list.")    
    
    auction_id = "auction_id_1";     times = 100
    announce_price_many_times(auction_id, times)
    time.sleep(2)
    print(f"Test: (2) Should see Buyer's auction [{auction_id}]'s price updated to {1.00}.")
    assert buyer.data.auctions[auction_id].round_id == times-1
    print(f"          and Buyer's round_id == {times-1}, good!")

    print("Test: ------  buyer's handle_announce_price() ----- done -------- ")
    

if __name__ == "__main__":
    app = QApplication([])
    window = QMainWindow()

    buyer_1 = Buyer("buyer_1", utils.RPC_Address("127.0.0.1", "60001"))
    buyer_1.ui.show()

    # buyer_3 = Buyer("buyer_3", utils.RPC_Address("127.0.0.1", "60003"))
    # buyer_3.ui.show()

    seller = Seller("seller_2", utils.RPC_Address("127.0.0.1", "60000"))
    seller.ui.show()
    
    threading.Thread(target=test_handle_announce_price, args=(buyer_1,), daemon=True).start()

    app.exec()