from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QStackedLayout
from PyQt6.QtWidgets import QMainWindow, QListWidget, QLabel, QPushButton, QMessageBox, QTableWidget
from PyQt6.QtGui import QFont
from PyQt6.QtCore import pyqtSignal, QObject

from concurrent import futures
import grpc
import auction_pb2_grpc
import auction_pb2 as pb2

import time
import threading

import utils
from utils import UserData, AuctionData, ItemData, price_to_string, RPC_Address

import test_toolkit
import logging
logging.basicConfig(level=logging.DEBUG)


""" Define the data a buyer has """
class Data():
    def __init__(self):
        self.username = None
        # A mapping from aution's id to AuctionData
        self.auctions = {} 
        # Record the RPC service address of each seller: 
        # A dictionary that maps each seller's username to RPC_Address
        self.addresses = {}
        # A dictionary that maps each seller's username to their RPC service stub
        self.rpc_stubs = {}
        # A lock used to prevent these data from being modified simultaneously by multiple threads. 
        self.lock = threading.Lock()


class Buyer(QObject):
    ui_update_signal = pyqtSignal()

    def __init__(self, username, rpc_address):
        super().__init__()

        self.data = Data()
        self.data.username = username
        self.data.auctions = self.get_all_auctions_from_server()

        self.ui = BuyerUI(self)
        self.ui_update_signal.connect(lambda : self.ui.update(self.data))

        # Start buyer's RPC service 
        self.rpc = Buyer_RPC_Servicer(self)
        rpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=64))
        auction_pb2_grpc.add_BuyerServiceServicer_to_server(self.rpc, rpc_server)
        rpc_server.add_insecure_port(rpc_address.ip + ":" + rpc_address.port)
        rpc_server.start()
        threading.Thread(target=rpc_server.wait_for_termination, daemon=True).start()
        print(f"Buyer {self.data.username} RPC server started.")

        # Finally, update UI (by emitting signal to notify the UI component)
        self.ui_update_signal.emit()

    
    def handle_announce_price(self, request):
        auction_id = request.auction_id
        round_id = request.round_id
        price = request.price
        buyer_status = request.buyer_status

        # Acquire lock before modifying data
        with self.data.lock:
            if auction_id not in self.data.auctions:
                return
            auction = self.data.auctions[auction_id]

            # If seller's round_id  <  buyer's round_id on record: 
            #   This means that the seller's annouce_price request is out-of-date, 
            #   just ignore it
            if round_id < auction.round_id:
                return
            
            # From now on, we have seller's round_id  >=  buyer's round_id
            # We first sync the two round_ids: 
            auction.round_id = round_id

            if round_id > -1:
                # round_id > -1 means that the auction is started
                auction.started = True
            
            # Update price:
            auction.current_price = price
            # Update buyer information (some buyers may have withdrawn)
            auction.update_buyer_status(buyer_status)
        
        # After the operation, the UI needs to be updated. 
        # So, we emit a signal to notify the UI to update.
        # We must use a signal because the UI update is done in another thread. 
        self.ui_update_signal.emit()
    

    def handle_finish_auction(self, request):
        # Obtain information from the request
        auction_id = request.auction_id
        winner_username = request.winner_username
        transaction_price = request.price
        buyer_status = request.buyer_status
        logging.debug(f"Buyer {self.data.username} receives finish_auction RPC, auction = {auction_id}")
        
        # Acquire lock before modifying the data
        with self.data.lock:
            if auction_id not in self.data.auctions:
                return
            # Update the data
            auction = self.data.auctions[auction_id]
            auction.finished = True
            auction.winner_username = winner_username
            auction.transaction_price = transaction_price
            auction.update_buyer_status(buyer_status)
        
        # After the data is updated, the UI needs to be updated. 
        # We emit a signal to notify the UI to update.
        # We use a signal because the UI update is done in another thread. 
        self.ui_update_signal.emit()
    

    def get_all_auctions_from_server(self):
        return test_toolkit.Test_1.get_all_auctions_from_server()
    
    def join_auction(self, auction_id):
        (success, message) = True, "Cannot join this auction"
        if not success:
            self.ui.display_message(message)
        self.update_auction_data(auction_id)
    

    """ Perform the operation that the buyer (self) withdraw from an auction
        - Input:
            - auction_id (str)  : the id of the auction the buyer is withdrawing from
        - Return:
            - success    (bool) : whether this operation is successful
            - message    (str)  : error message if not successful
    """
    def withdraw(self, auction_id):
        if auction_id not in self.data.auctions:
            return False, f"Auction {auction_id} does not exists!"
        
        # get the seller's id of the auction
        with self.data.lock:
            seller_username = self.data.auctions[auction_id].seller.username
        
        # check whether this buyer has the seller's RPC service address
        if seller_username not in self.data.rpc_stubs:
            # if not, get the address from the server
            (got_address, result) = self.find_address_from_server(seller_username)
            if got_address:
                # if got the address, create a RPC stub with the address
                channel = grpc.insecure_channel(result.ip + ":" + result.port)
                stub = auction_pb2_grpc.SellerServiceStub(channel)
                with self.data.lock:
                    self.data.rpc_stubs[seller_username] = stub
            else:
                # if cannot get the address, return NOT SUCCESSFUL
                return False, f"Cannot find seller's network address."
        
        # at this point, we should have the seller's RPC stub
        stub = self.data.rpc_stubs[seller_username]
        request = pb2.UserAuctionPair()
        request.auction_id = auction_id
        request.username = self.data.username
        # try to send the withdrawing request to the seller using the stub
        # and return the response 
        try:
            response = stub.withdraw(request)
            success, message = response.success, response.message
        except grpc.RpcError as e:
            print(e)
            success, message = False, f"Cannot withdraw. Network error!"
        
        return success, message
    

    def find_address_from_server(self, username):
        return test_toolkit.Test_1.find_address_from_server(username)

    def update_auction_data(self, auction_id):
        with self.lock:
            self.data.auctions[auction_id].joined = True
        self.ui_update_signal.emit()


""" The RPC servicer on a buyer client: provides RPC services to a seller.
    Note:
        The RPC services are multi-threaded,
        but we want them to be processed sequentially.
        So, we put the requests to a request queue in the parent object.
        The parent object will handle those reqeusts sequentially. 
"""
class Buyer_RPC_Servicer(auction_pb2_grpc.BuyerServiceServicer):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
    
    def announce_price(self, request, context):
        self.parent.handle_announce_price(request)
        return pb2.SuccessMessage(success=True)

    def finish_auction(self, request, context):
        self.parent.handle_finish_auction(request)
        return pb2.SuccessMessage(success=True)


BOLD = QFont()
BOLD.setBold(True)

class Join_Auction_Page(QWidget):
    def __init__(self, root_widget):
        super().__init__()
        self.root_widget = root_widget
        self.auction_id = None

        layout = QVBoxLayout()

        row_1 = QHBoxLayout()
        row_1.addWidget(QLabel("Seller "))
        self.seller_label = QLabel()
        self.seller_label.setFont(BOLD)
        row_1.addWidget(self.seller_label)
        layout.addLayout(row_1)

        row_2 = QHBoxLayout()
        row_2.addWidget(QLabel("selling:"))
        self.item_label = QLabel()
        self.item_label.setFont(BOLD)
        row_2.addWidget(self.item_label)
        layout.addLayout(row_2)

        row_3 = QHBoxLayout()
        row_3.addWidget(QLabel("at base price: "))
        self.base_price_label = QLabel()
        self.base_price_label.setFont(BOLD)
        row_3.addWidget(self.base_price_label)
        layout.addLayout(row_3)

        layout.addWidget(QLabel("Auction has not started yet."))
        layout.addWidget(QLabel("Do you want to join this auction? "))
        
        self.join_button = QPushButton("Join")
        self.join_button.clicked.connect(self.join_button_clicked)
        layout.addWidget(self.join_button)

        self.setLayout(layout)

    def join_button_clicked(self):
        # dialog = QMessageBox()
        # dialog.setText("Cannot join this auction!")
        # dialog.exec()
        auction_id = self.root_widget.selected_auction
        self.root_widget.model.join_auction(auction_id)
    
    """ This function is called when we need to update the UI
        with new auction_data
    """
    def update(self, auction_data):
        self.auction_id = auction_data.id
        self.seller_label.setText(auction_data.seller.username)
        self.item_label.setText(auction_data.item.name)
        self.base_price_label.setText(price_to_string(auction_data.base_price))


class Auction_Started_Page(QWidget):
    def __init__(self, root_widget):
        super().__init__()
        self.root_widget = root_widget
        self.auction_id = None
        
        layout = QVBoxLayout()

        seller_row = QHBoxLayout()
        seller_row.addWidget(QLabel("Seller "))
        self.seller_label = QLabel()
        self.seller_label.setFont(BOLD)
        seller_row.addWidget(self.seller_label)
        layout.addLayout(seller_row)

        item_row = QHBoxLayout()
        item_row.addWidget(QLabel("selling:"))
        self.item_label = QLabel()
        self.item_label.setFont(BOLD)
        item_row.addWidget(self.item_label)
        layout.addLayout(item_row)

        layout.addWidget(QLabel("Auction has started."))

        price_row = QHBoxLayout()
        price_row.addWidget(QLabel("Current price: "))
        self.current_price_label = QLabel()
        self.current_price_label.setFont(BOLD)
        price_row.addWidget(self.current_price_label)
        layout.addLayout(price_row)

        buyers_view = QVBoxLayout()
        buyers_view.addWidget(QLabel("Current buyers:"))
        self.buyers_list = QListWidget()
        buyers_view.addWidget(self.buyers_list)
        layout.addLayout(buyers_view)


        self.active_widget = QWidget()
        active_layout = QVBoxLayout()
        active_layout.addWidget(QLabel("\nDo you want to withdraw from the auction?"))
        self.withdraw_button = QPushButton("Withdraw")
        self.withdraw_button.clicked.connect(self.withdraw_button_clicked)
        active_layout.addWidget(self.withdraw_button)
        self.active_widget.setLayout(active_layout)

        self.withdrew_info = QLabel("\nYou have withdrawn from the auction.\nCannot re-join.")

        self.active_withdrew_layout = QStackedLayout()
        self.active_withdrew_layout.addWidget(self.active_widget)
        self.active_withdrew_layout.addWidget(self.withdrew_info)
        self.active_withdrew_layout.setCurrentWidget(self.active_widget)

        layout.addLayout(self.active_withdrew_layout)

        self.setLayout(layout)

    def withdraw_button_clicked(self):
        auction_id = self.auction_id
        success, message = self.root_widget.model.withdraw(auction_id)
        if not success:
            self.root_widget.display_message(message)
        self.root_widget.update()
        

    """ This function is called when we need to update the UI
        with new auction_data
    """
    def update(self, auction_data):
        self.auction_id = auction_data.id
        self.seller_label.setText(auction_data.seller.username)
        self.item_label.setText(auction_data.item.name)
        self.current_price_label.setText(price_to_string(auction_data.current_price))
        
        self.buyers_list.clear()
        for b in auction_data.buyers:
            active_or_withdrew = "active" if auction_data.is_active(b) else "withdrew"
            self.buyers_list.addItem(b + "  :  " + active_or_withdrew)

        current_buyer = self.root_widget.data.username
        if current_buyer in auction_data.buyers:
            if auction_data.is_active(current_buyer) == True:
                self.active_withdrew_layout.setCurrentWidget(self.active_widget)
            else:
                self.active_withdrew_layout.setCurrentWidget(self.withdrew_info)


class Auction_Finished_Page(QWidget):
    def __init__(self, root_widget):
        super().__init__()
        self.root_widget = root_widget
        self.auction_id = None
        
        layout = QVBoxLayout()

        seller_row = QHBoxLayout()
        seller_row.addWidget(QLabel("Seller "))
        self.seller_label = QLabel()
        self.seller_label.setFont(BOLD)
        seller_row.addWidget(self.seller_label)
        layout.addLayout(seller_row)

        item_row = QHBoxLayout()
        item_row.addWidget(QLabel("sold:"))
        self.item_label = QLabel()
        self.item_label.setFont(BOLD)
        item_row.addWidget(self.item_label)
        layout.addLayout(item_row)

        layout.addWidget(QLabel("Auction has finished."))

        winner_row = QHBoxLayout()
        winner_row.addWidget(QLabel("Winner:"))
        self.winner_label = QLabel()
        self.winner_label.setFont(BOLD)
        winner_row.addWidget(self.winner_label)
        layout.addLayout(winner_row)

        price_row = QHBoxLayout()
        price_row.addWidget(QLabel("Transaction price: "))
        self.price_label = QLabel()
        self.price_label.setFont(BOLD)
        price_row.addWidget(self.price_label)
        layout.addLayout(price_row)

        self.setLayout(layout)

    """ This function is called when we need to update the UI
        with new auction_data
    """
    def update(self, auction_data):
        self.auction_id = auction_data.id
        self.seller_label.setText(auction_data.seller.username)
        self.item_label.setText(auction_data.item.name)
        self.winner_label.setText(auction_data.winner_username)
        self.price_label.setText(price_to_string(auction_data.transaction_price))


class BuyerUI(QWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.data = None

        # record the auction selected by the user, namely, the auction to display on screen
        self.selected_auction = None

        mainlayout = QHBoxLayout()
        self.setLayout(mainlayout)

        column_1 = QVBoxLayout()

        column_1.addWidget(QLabel("Current user:"))
        self.username_label = QLabel()
        self.username_label.setFont(BOLD)
        column_1.addWidget(self.username_label)

        column_1.addWidget(QLabel("Choose auction:"))
        self.auction_list = QListWidget()
        self.auction_list.itemClicked.connect(self.auction_list_clicked)
        column_1.addWidget(self.auction_list)
        mainlayout.addLayout(column_1)

        column_2 = QVBoxLayout()
        self.stacked_widget = QStackedWidget()
        self.empty_page = QWidget()
        self.join_auction_page = Join_Auction_Page(self)
        self.auction_started_page = Auction_Started_Page(self)
        self.auction_finished_page = Auction_Finished_Page(self)
        self.stacked_widget.addWidget(self.empty_page)
        self.stacked_widget.addWidget(self.join_auction_page)
        self.stacked_widget.addWidget(self.auction_started_page)
        self.stacked_widget.addWidget(self.auction_finished_page)
        self.stacked_widget.setCurrentWidget(self.empty_page)
        column_2.addWidget(self.stacked_widget)

        mainlayout.addLayout(column_2)

    def auction_list_clicked(self, item):
        self.selected_auction = item.text()
        self.update_displayed_auction()
    
    """ Update the UI of the auction displayed on screen """
    def update_displayed_auction(self):
        w = self.empty_page
        if (self.data != None) and (self.selected_auction in self.data.auctions):
            # get the data of the selected auction
            a = self.data.auctions[self.selected_auction]

            if a.finished == True:
                w = self.auction_finished_page
            elif a.started == True:
                w = self.auction_started_page
            # elif self.data.username not in a.buyers: 
                # if a.joined == False:
            else:
                w = self.join_auction_page
                
            # update the widget using auction data "a"
            w.update(a)
        self.stacked_widget.setCurrentWidget(w)

    def switch_to_auction_started(self):
        self.auction_started_page.update(self.auction_data)
        self.stacked_widget.setCurrentWidget(self.auction_started_page)
    
    """ When the buyer's data change, this function should be called to
        update the UI.
        Input: the new data. 
    """
    def update(self, data=None):
        if data == None:
            data = self.model.data
        
        self.username_label.setText(data.username)
        
        if (self.data == None) or (data.auctions != self.data.auctions):
            self.auction_list.clear()
            for id in data.auctions:
                self.auction_list.addItem(id)
        
        self.data = data
        self.update_displayed_auction()
    
    def display_message(self, message):
        QMessageBox.critical(self, "", message)