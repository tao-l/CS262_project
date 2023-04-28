from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget
from PyQt6.QtWidgets import QMainWindow, QListWidget, QLabel, QPushButton, QMessageBox
from PyQt6.QtGui import QFont
from PyQt6.QtCore import pyqtSignal, QObject

from concurrent import futures
import grpc
import auction_pb2_grpc
import auction_pb2 as pb2

import time
import threading
from queue import Queue

import utils
from utils import UserData, AuctionData, ItemData, price_to_string

import test_toolkit
import logging
logging.basicConfig(level=logging.DEBUG)


""" Define the data a seller has """
class Data():
    def __init__(self):
        self.username = None
        # A mapping from aution's id to AuctionData,
        # records all the auctions the seller has. 
        self.my_auctions = {}
        # A lock used to prevent these data from being modified simultaneously by multiple threads. 
        self.lock = threading.Lock()
        # A dictionary that maps each seller's username to their RPC service stub
        self.rpc_stubs = {}


class Seller(QObject):
    ui_update_signal = pyqtSignal()

    def __init__(self, username, rpc_address):
        super().__init__()

        self.data = Data()
        self.data.username = username
        self.data.my_auctions = self.get_all_auctions_from_server()

        self.ui = SellerUI(self)
        self.ui_update_signal.connect(lambda : self.ui.update(self.data))

        # Start seller's RPC service 
        self.rpc = Seller_RPC_Servicer(self)
        rpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=64))
        auction_pb2_grpc.add_SellerServiceServicer_to_server(self.rpc, rpc_server)
        rpc_server.add_insecure_port(rpc_address.ip + ":" + rpc_address.port)
        rpc_server.start()
        threading.Thread(target=rpc_server.wait_for_termination, daemon=True).start()
        print("Seller RPC server started.")

        # Finally, update UI (by emitting signal to notify the UI component)
        self.ui_update_signal.emit()

    def get_all_auctions_from_server(self):
        return test_toolkit.Test_1.get_all_auctions_from_server()
    
    def create_auction(self):
        # new_auction = AuctionData(name="test auction", id="test_id_1", )
        # auction_id = "test_auction"
        pass
    

    """ Perform the operation that a buyer withdraws from an auction: 
        - Input:
            - auction_id (str)  :  the id of the auction the buyer is withdrawing from
            - username   (str)  :  the username of the buyer
        - Output:
            - success    (bool) :  whether the withdrawing operation is successful
            - message    (str)  :  error message if not successful
        * Note:
            This function may be called by multiple threads simultaneously
            (e.g., called by the multi-threaded RPC servicer).
            Lock is needed to prevent race condition. 
    """
    def withdraw(self, auction_id, username):
        with self.data.lock:
            if auction_id not in self.data.my_auctions:
                return False, f"This seller does not have auction {auction_id}"
            auction = self.data.my_auctions[auction_id]
            if username not in auction.buyers:
                return False, f"Buyer {username} did not join this auction ({auction_id})"
            
            # If the buyer already withdrew previously, simply return success message
            if auction.is_active(username) == False:
                return True, "Success"
            
            # Now we know that the buyer is active and can try to withdraw it.
            # If the buyer is the only buyer in the auction,
            # then this buyer should be the winner and cannot withdraw.  
            if auction.n_active_buyers() == 1:
                return False, f"Cannot withdraw!\n Because you are the only active buyer (winner) in the auction."

            # Otherwise, we can withdraw the buyer from the auction
            auction.withdraw(username)
            success, message = True, "Success"

            # After the buyer withdraws from the auction, 
            # we count the number of active buyers to determine whether the auction should be finished
            if auction.n_active_buyers() == 1:
                self.finish_auction(auction_id)
        
        # Notify all buyers that a buyer has withdrawn
        print(f"Seller: buyer [{username}] withdraws from auction [{auction_id}]. Notifying all buyers...")
        self.announce_price_to_all(auction_id)

        # At this point, the withdrawing operation is completed.
        # The seller's UI needs to be updated. 
        # So, we emit a signal to notify the UI to update.
        # We use a signal because the UI update is done in another thread. 
        self.ui_update_signal.emit()
        return success, message
    

    def announce_price_to_all(self, auction_id):
        if auction_id not in self.data.my_auctions:
            return
        auction = self.data.my_auctions[auction_id]

        # create a announce_price RPC request
        request = pb2.AnnouncePriceRequest()
        with self.data.lock:
            request.auction_id = auction_id
            request.round_id = auction.round_id
            request.price = auction.current_price
            # request.buyer_status = [????]  XXX
            for b in auction.buyers:
                request.buyer_status.append(
                        pb2.BuyerStatus(username=b, active=auction.is_active(b))
                    )
        
        # broadcast the request to all buyers in the auction
        for b in auction.buyers:
            threading.Thread(target = self.send_rpc_request_to_buyer,
                             args = ("announce_price", b, request), 
                             daemon = True).start()
    

    """ Finish an auction and notify buyers: 
        - Input:
            - auction_id (str)  :  the id of the auction to finish
        * Note:
            This function may be called by multiple threads simultaneously
            (e.g., called by the multi-threaded RPC servicer).
            Lock is needed to prevent race condition. 
    """
    def finish_auction(self, auction_id):
        if auction_id not in self.data.my_auctions:
            return
        
        print(f"Seller [{self.data.username}]: [{auction_id}] is finished")
        # with self.data.lock:
        for i in range(1):
            print("XXXXXXXXXXXXXXX Got lock XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            # Update the data
            auction = self.data.my_auctions[auction_id]
            auction.finished = True
            auction.winner_username = auction.get_winner()
            auction.transaction_price = auction.current_price
            rpc_request = pb2.FinishAuctionRequest(
                            auction_id = auction_id,
                            winner_username = auction.winner_username, 
                            price = auction.transaction_price
                 )
            
            for b in auction.buyers:
                rpc_request.buyer_status.append(
                        pb2.BuyerStatus(username=b, active=auction.is_active(b))
                    )
        
        # Notify all buyers that this auction is finished
        print(f"Seller: auction [{auction_id}] is finished. Starts to notify buyers.")
        for b in auction.buyers:
            threading.Thread(target = self.send_rpc_request_to_buyer,
                             args = ("finish_auction", b, rpc_request), 
                             daemon = True).start()
        
        # At this point, the finish auction operation is completed.
        # The seller's UI needs to be updated. 
        # So, we emit a signal to notify the UI to update.
        # (We do not update the UI directly here
        #  becasue the UI update is time consuming and must be single-threaded.)
        self.ui_update_signal.emit()
    

    def send_rpc_request_to_buyer(self, rpc_name, buyer, request):
        logging.debug(f"Seller sending RPC request {rpc_name} to {buyer}")
        if buyer not in self.data.rpc_stubs:
            (got_address, result) = self.find_address_from_server(buyer)
            if got_address:
                channel = grpc.insecure_channel(result.ip + ":" + result.port)
                stub = auction_pb2_grpc.BuyerServiceStub(channel)
                with self.data.lock:
                    self.data.rpc_stubs[buyer] = stub
            else:
                err_message = f"Cannot find buyer's network address."
                return False, err_message
        
        stub = self.data.rpc_stubs[buyer]
        try:
            if rpc_name == "finish_auction":
                print(f"Seller sending RPC to {buyer}: finish_auction")
                response = stub.finish_auction(request)
                print("Seller got response")
                success = True
            elif rpc_name == "announce_price":
                response = stub.announce_price(request)
                success = True
        except grpc.RpcError as e:
            print(e)
            return False, f"Cannot contact with buyer. Network error!"
        return success, response
    


    def find_address_from_server(self, username):
        return test_toolkit.Test_1.find_address_from_server(username)


""" The RPC servicer on a seller client: provides RPC services to a buyer.
    * Note:
        The RPC services are multi-threaded.
"""
class Seller_RPC_Servicer(auction_pb2_grpc.SellerServiceServicer):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
    
    def withdraw(self, request, context):
        # obtain data from the RPC request
        auction_id = request.auction_id
        buyer_username = request.username
        logging.debug(f"Seller received: withdraw ( {auction_id}, {buyer_username} )")
        # call the parent object's withdraw() function to perform the operation
        success, message = self.parent.withdraw(auction_id, buyer_username)
        if success:
            logging.debug(f"     Success: Buyer {buyer_username} withdrew from auction {auction_id}")
        return pb2.SuccessMessage(success=success, message=message)


BOLD = QFont()
BOLD.setBold(True)

class SellerUI(QWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.root_widget = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(QLabel(self.model.data.username))
    
    def update(self, data):
        print("Seller UI update called.")