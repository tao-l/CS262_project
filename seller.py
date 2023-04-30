from PyQt6.QtWidgets import QWidget, QStackedWidget, QListWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QStackedLayout
from PyQt6.QtWidgets import QLabel, QPushButton, QMessageBox, QLineEdit, QDialog, QDialogButtonBox, QGroupBox
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


DEBUG = False

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
    ui_update_auctions_signal = pyqtSignal()
    ui_update_all_signal = pyqtSignal()

    def __init__(self, username, rpc_address):
        super().__init__()

        self.data = Data()
        self.data.username = username

        self.ui = SellerUI(self)
        self.ui_update_all_signal.connect(lambda : self.ui.update_all(self.data))
        self.ui_update_auctions_signal.connect(lambda : self.ui.update_auctions(self.data.my_auctions))

        # Start seller's RPC service 
        self.rpc = Seller_RPC_Servicer(self)
        rpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=64))
        auction_pb2_grpc.add_SellerServiceServicer_to_server(self.rpc, rpc_server)
        rpc_server.add_insecure_port(rpc_address.ip + ":" + rpc_address.port)
        rpc_server.start()
        threading.Thread(target=rpc_server.wait_for_termination, daemon=True).start()
        print("Seller RPC server started.")

        def data_fetch_loop():
            while True:
                self.fetch_auctions_from_server()
                time.sleep(1)
        threading.Thread(target=data_fetch_loop, daemon=True).start()

        # Finally, update UI (by emitting signal to notify the UI component)
        self.ui_update_all_signal.emit()
    

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
            (e.g., called by the multi-threaded RPC servicer and when announce_price cannot reach this buyer).
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
                return True, "Buyer withdrew previously."
            
            # Now we know that the buyer is active and can try to withdraw it.
            # If the buyer is the only buyer in the auction,
            # then this buyer should be the winner and cannot withdraw.  
            if auction.n_active_buyers() == 1:
                # print(f"Buyer {username} cannot withdraw because it is the only buyer left. ")
                success, message = False, f"Cannot withdraw!\n Because you are the only active buyer (winner) in the auction."
            else: 
            # Otherwise, we can withdraw the buyer from the auction
                auction.withdraw(username)
                success, message = True, "Success"

            # After the buyer withdraws from the auction, 
            # we count the number of active buyers to determine whether the auction should be finished
            if auction.n_active_buyers() == 1:
                auction.finished = True
        
        if auction.finished:
            threading.Thread(target = self.finish_auction,
                             args   = (auction_id, True),  # the "True" means that this auction has a winner
                             daemon = True).start()
        
        # Notify all buyers that a buyer has withdrawn, using the announce_price function
        print(f"Seller: tried to withdraw [{username}] from auction [{auction_id}], succees = {success}. \n  Notifying all buyers...")
        self.announce_price_to_all(auction_id, requires_ack=False)

        # At this point, the withdrawing operation is completed.
        # The seller's UI needs to be updated. 
        # So, we emit a signal to notify the UI to update.
        # We use a signal because the UI update is done in another thread. 
        self.ui_update_auctions_signal.emit()
        return success, message
    

    """ Announce price to all buyers in auction [auction_id].
        Bool parameter [requires_ack] specifies whether the seller requires acknowledgement from buyers. 
        If requires_ack = True, then a buyer who does not acknowledge the price announcement will be withdrawn. 
        (Note : this function may be called frequently if the price increment period increment is small.) 
    """
    def announce_price_to_all(self, auction_id, requires_ack=True):
        # create an announce_price RPC request
        request = pb2.AnnouncePriceRequest()
        with self.data.lock:
            if auction_id not in self.data.my_auctions:
                return
            auction = self.data.my_auctions[auction_id]

            request.auction_id = auction_id
            request.round_id = auction.round_id
            request.price = auction.current_price
            for b in auction.buyers:
                request.buyer_status.append(
                        pb2.BuyerStatus(username=b, active=auction.is_active(b))
                    )
        
        # # broadcast the request to all buyers in the auction
        # for b in auction.buyers:
        #     threading.Thread(target = self.send_rpc_request_to_buyer,
        #                      args = ("announce_price", b, request), 
        #                      daemon = True).start()

        # Broadcast the request to all buyers in the auction. 
        for b in auction.buyers:
            print(f"Announce_price sent to {b}")
            success, response = self.RPC_to_buyer("announce_price", request, b)
            print(f"Announce_price for {b} success = {success}")
            if requires_ack:
                # if requires acknowlegement, 
                # then a buyer who does not acknowledge the request is withdrawn 
                if not success:
                    self.withdraw(auction_id, b)
    

    def RPC_to_buyer(self, rpc_name, request, buyer):
        # First, get the buyer's RPC stub
        with self.data.lock:
            if buyer not in self.data.rpc_stubs:
                return False, f"Does not have buyer's RPC stub."
            stub = self.data.rpc_stubs[buyer]
        # Then, try to make the RPC call
        try:
            if rpc_name == "announce_price":
                response = stub.announce_price(request)
            elif rpc_name == "finish_auction":
                response = stub.finish_auction(request)
            else:
                raise Exception(f"RPC {rpc_name} not supported")
        except grpc.RpcError as e:
            return False, "RPC error"
        return True, response
    

    """ Finish an auction and notify buyers: 
        - Input:
            - auction_id (str)  :  the id of the auction to finish
        * Note:
            This function may be called by multiple threads simultaneously
            (e.g., called by the multi-threaded RPC servicer).
            Lock is needed to prevent race condition. 
    """
    def finish_auction(self, auction_id, has_winner=True):
        print(f"Seller [{self.data.username}]: finishing [{auction_id}]")
        with self.data.lock:
            if auction_id not in self.data.my_auctions:
                return
            # Update the auction data
            auction = self.data.my_auctions[auction_id]
            auction.finished = True
            if has_winner:
                # the case that the auction has a winner
                auction.winner_username = auction.get_winner()
                auction.transaction_price = auction.current_price
            else:
                # the case that the auction does not have a winner when finishing
                auction.winner_username = ""
                auction.transaction_price = auction.base_price
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
        self.ui_update_auctions_signal.emit()
    

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
    

    """ A loop that continuously increases the price of acution [auction_id], 
        used when the auction is started. 
    """
    def price_increment_loop(self, auction_id):
        while True:
            # Announce price to all buyers and update the seller's UI
            self.announce_price_to_all(auction_id)
            self.ui_update_auctions_signal.emit()

            # get the price increment period and sleep for that period
            with self.data.lock:
                period = self.data.my_auctions[auction_id].price_increment_period
            time.sleep(period / 1000)
            
            # go to the next round if the auction is not finished yet 
            with self.data.lock:
                auction = self.data.my_auctions[auction_id]
                if not auction.finished:
                    auction.round_id += 1
                    auction.current_price += auction.increment
                else:
                    break
    

    """ Seller starts auction [auction_id],
        Parameter [resume] indicates whether this auction is resumed from a previously started but paused auction
    """
    def start_auction(self, auction_id, resume=False):
        # First, obtain the acution (buyer) information from the platform:
        # auction = test_toolkit.Test_1.get_auction_info(auction_id)
        auction = self.data.my_auctions[auction_id]

        # Then, obtain the RPC address of all buyers:
        for buyer in auction.buyers:
            (got_address, result) = self.find_address_from_server(buyer)
            if got_address:
                channel = grpc.insecure_channel(result.ip + ":" + result.port)
                stub = auction_pb2_grpc.BuyerServiceStub(channel)
                with self.data.lock:
                    self.data.rpc_stubs[buyer] = stub
        
        # Then, change the auction to started stage
        with self.data.lock:
            self.data.my_auctions[auction_id] = auction
            auction.started = True
            if not resume:
                auction.round_id = 0
                auction.current_price = auction.base_price
            else: 
                # If the auction is resumed, no need to set round_id and current_price 
                auction.resume = False
        
        # Finally, start a loop to continuously increase the price
        threading.Thread(target=self.price_increment_loop, args=(auction_id,), daemon=True).start()

        return True, "Success"
    

    def create_auction(self, auction_name, item_name, base_price, period, increment):
        print("Trying to create auction:", auction_name, item_name, base_price, period, increment)
        return (False, "Create_auction funcion not impelemented. ")
    

    def find_address_from_server(self, username):
        return test_toolkit.Test_1.find_address_from_server(username)
    

    """ This function fetches all data (auctions & addresses) from the platform
        to update the local data. 
    """
    def fetch_data_from_server(self):
        # First, fetch all the auction data
        self.fetch_auctions_from_server()
        # Then, fetch the RPC addresses of all buyers
    

    """ This function fetches all auction data from the platform to update the local data. 
    """
    def fetch_auctions_from_server(self):
        auction_list_needs_update = False   # records whether the auciton list in the UI needs to be updated
        
        platform_auctions = self.get_all_auctions_from_server()
        
        for (id, pa) in platform_auctions.items():
            if pa.seller.username != self.data.username:
                # ignore auctions that are not this seller's
                continue

            with self.data.lock:
                if id in self.data.my_auctions:
                    # For an auction that is in both platforms and seller's data, 
                    #  - If the auction is finished: replace the seller's data with the platform's:
                    if pa.finished:
                        if DEBUG:
                            print(id, "finished")
                        self.data.my_auctions[id] = pa
                        continue
                    #  - If the auction is not started and not finished: replace the seller's data with the platform's:  
                    elif not pa.started:
                        if DEBUG:
                            print(id, "not started")
                        self.data.my_auctions[id] = pa
                        continue 
                    #  - Otherwise, the auction is started and not finished:
                    #    Do not change the seller's data because the auction is taken cared of by the seller now
                    else:
                        continue
                else:
                    # For an auction that is in the platform's data but in the seller's, 
                    # add this auction to the seller's auction list
                    if DEBUG: print(id, "new auction")
                    self.data.my_auctions[id] = pa
                    auction_list_needs_update = True
                    # If this auction has started, set "resume = True" so that the UI will show a "resume" button
                    if pa.started:
                        pa.resume = True
        
        # If the auction lists needs to update, update the entire UI, 
        if auction_list_needs_update:
            self.ui_update_all_signal.emit()
        else:
        # Otherwise, just update the auction part of the UI. 
            self.ui_update_auctions_signal.emit() 


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
        logging.debug(f"Seller received RPC: withdraw ( {auction_id}, {buyer_username} )")
        # call the parent object's withdraw() function to perform the operation
        success, message = self.parent.withdraw(auction_id, buyer_username)
        logging.debug(f"     RPC response: success = {success}, message = {message}")
        return pb2.SuccessMessage(success=success, message=message)


BOLD = QFont()
BOLD.setBold(True)

class SellerUI(QWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.data = None

        # record the id of auction selected by the user, namely, the auction to display on screen
        self.selected_auction = None

        mainlayout = QHBoxLayout()
        self.setLayout(mainlayout)

        column_1 = QVBoxLayout()
        
        self.username_label = QLabel()
        self.username_label.setFont(BOLD)
        column_1.addWidget(self.username_label)
        column_1.addWidget(QLabel("logged in as seller.\n"))

        column_1.addWidget(QLabel("Auctions you have:"))
        self.auction_list_widget = QListWidget()
        self.auction_list_widget.itemClicked.connect(self.auction_list_clicked)
        column_1.addWidget(self.auction_list_widget)
        self.auction_id_list = []   # record the id of the auctions in the list
        mainlayout.addLayout(column_1)

        self.create_button = QPushButton("Create new auction")
        self.create_button.clicked.connect(self.create_button_clicked)
        column_1.addWidget(self.create_button)

        column_2 = QVBoxLayout()
        self.auction_box = QGroupBox()
        self.stacked_layout = QStackedLayout()
        self.empty_page = QWidget()
        self.auction_starting_page = Auction_Starting_Page(self)
        self.auction_started_page  = Auction_Started_Page(self)
        self.auction_resume_page   = Auction_Resume_Page(self)
        self.auction_finished_page = Auction_Finished_Page(self)
        self.stacked_layout.addWidget(self.empty_page)
        self.stacked_layout.addWidget(self.auction_starting_page)
        self.stacked_layout.addWidget(self.auction_started_page)
        self.stacked_layout.addWidget(self.auction_resume_page)
        self.stacked_layout.addWidget(self.auction_finished_page)
        self.stacked_layout.setCurrentWidget(self.empty_page)
        self.auction_box.setLayout(self.stacked_layout)
        column_2.addWidget(self.auction_box)

        mainlayout.addLayout(column_2)
    

    """ When user clicks an auction in the auction list, do the following: """
    def auction_list_clicked(self):
        selected_row = self.auction_list_widget.currentRow()
        # records which auction is selected by the user
        self.selected_auction = self.auction_id_list[selected_row]
        # then display the selected auction
        self.update_displayed_auction()
    
    
    class Create_Auction_Dialog(QDialog):
        def __init__(self, parent, model):
            super().__init__(parent)
            self.model = model 
            self.setWindowTitle("Create a new auction")
            group_box = QGroupBox()
            layout = QFormLayout()
            self.auction_name_LE = QLineEdit()
            self.item_name_LE = QLineEdit()
            self.base_price_LE = QLineEdit("0.00")
            self.period_LE = QLineEdit("1.0")
            self.increment_LE = QLineEdit("0.01")
            layout.addRow(QLabel("Name of the auction:"), self.auction_name_LE)
            layout.addRow(QLabel("Name of the item for sale:"), self.item_name_LE)
            layout.addRow(QLabel("Base price:"), self.base_price_LE)
            layout.addRow(QLabel("The price increases once every ? seconds:"), self.period_LE)
            layout.addRow(QLabel("The increment of price each time (in dollars):"), self.increment_LE)
            group_box.setLayout(layout)

            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(self.ok_button_clicked)
            button_box.rejected.connect(self.reject)

            mainlayout = QVBoxLayout()
            mainlayout.addWidget(group_box)
            mainlayout.addWidget(button_box)

            self.setLayout(mainlayout)
        
        def ok_button_clicked(self):
            # Read user's input and check
            auction_name = self.auction_name_LE.text()
            if len(auction_name) > 1000:
                QMessageBox.critical(self, "", "Auction name is too long!")
                return
            
            item_name = self.item_name_LE.text()
            if len(item_name) > 10000:
                QMessageBox.critical(self, "", "Item name is too long!")
                return
            
            (valid, base_price, error_message) = utils.string_to_number_and_check_range(self.base_price_LE.text(), lb=0, ub=1000000)
            if not valid:
                QMessageBox.critical(self, "", error_message)
                return 
            
            (valid, period, error_message) = utils.string_to_number_and_check_range(self.period_LE.text(), lb=0.001, ub=100000)
            if not valid:
                QMessageBox.critical(self, "", error_message)
                return 
            
            (valid, increment, error_message) = utils.string_to_number_and_check_range(self.increment_LE.text(), lb=0.01, ub=100000)
            if not valid:
                QMessageBox.critical(self, "", error_message)
                return
            
            # check is done. Call the model's create_auction() function 
            period_in_ms = int( period * 1000 )
            (success, message) = self.model.create_auction(auction_name, item_name, base_price, period_in_ms, increment)
            if not success:
                QMessageBox.critical(self, "", message)
            print(" XXXXXXX Need to update UI here???? ")
            return 


    """ When user clicks the create auction button, do the following: """
    def create_button_clicked(self):
        dialog = self.Create_Auction_Dialog(self, self.model)
        dialog.show()


    
    """ Update the UI of the auction displayed on screen """
    def update_displayed_auction(self):
        w = self.empty_page
        if (self.auctions != None) and (self.selected_auction in self.auctions):
            # get the data of the selected auction
            a = self.auctions[self.selected_auction]

            if a.finished == True:
                w = self.auction_finished_page
            elif a.started == True:
                if a.resume == True:
                    w = self.auction_resume_page
                else:
                    w = self.auction_started_page
            else:
                w = self.auction_starting_page
            
            # update the widget using auction data "a"
            w.update(a)
            self.auction_box.setTitle(a.name)
        
        self.stacked_layout.setCurrentWidget(w)

    def switch_to_auction_started(self):
        self.auction_started_page.update(self.auction_data)
        self.stacked_layout.setCurrentWidget(self.auction_started_page)
    
    """ This function updates the entire UI, using the given new data
    """
    def update_all(self, data=None):
        if data == None:
            data = self.model.data
        
        self.username_label.setText(data.username)
        self.update_auction_list(data.my_auctions)
        self.update_auctions(data.my_auctions)
    
    """ This function only updates the auction list, given new auctions data
    """
    def update_auction_list(self, auctions):
        self.auction_list_widget.clear()
        self.auction_id_list = []
        for (auction_id, a) in auctions.items():
            self.auction_list_widget.addItem(a.name)
            self.auction_id_list.append(auction_id)
    
    """ This function only updates the auction UI, given new auctions data
    """
    def update_auctions(self, auctions):
        self.auctions = auctions
        self.update_displayed_auction()
        
    
    def display_message(self, message):
        QMessageBox.critical(self, "", message)


class Auction_Starting_Page(QWidget):
    def __init__(self, root_widget):
        super().__init__()
        self.root_widget = root_widget
        self.auction_id = None

        layout = QVBoxLayout()

        item_row = QHBoxLayout()
        item_row.addWidget(QLabel("Selling:"))
        self.item_label = QLabel()
        self.item_label.setFont(BOLD)
        item_row.addWidget(self.item_label)
        layout.addLayout(item_row)

        price_row = QHBoxLayout()
        price_row.addWidget(QLabel("at base price: "))
        self.base_price_label = QLabel()
        self.base_price_label.setFont(BOLD)
        price_row.addWidget(self.base_price_label)
        layout.addLayout(price_row)


        layout.addWidget(QLabel("Auction has not started yet."))

        self.increment_description = QLabel()
        layout.addWidget(self.increment_description)

        buyers_view = QVBoxLayout()
        buyers_view.addWidget(QLabel("Current buyers:"))
        self.buyers_list = QListWidget()
        buyers_view.addWidget(self.buyers_list)
        layout.addLayout(buyers_view)

        layout.addWidget(QLabel("Do you want to start this auction? "))

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_button_clicked)
        layout.addWidget(self.start_button)

        self.setLayout(layout)

    def start_button_clicked(self):
        auction_id = self.auction_id
        # call the model's start_auction() function to start the auction
        success, message = self.root_widget.model.start_auction(auction_id)
        if not success:
            # if not successful, display error message
            QMessageBox.critical(self, "", message)
    
    """ This function is called when we need to update the UI
        with new auction_data
    """
    def update(self, auction_data):
        self.auction_id = auction_data.id
        self.item_label.setText(auction_data.item.name)
        self.base_price_label.setText(price_to_string(auction_data.base_price))
        seconds = auction_data.price_increment_period / 1000
        increment_message = f"Once started, the price will increase by {price_to_string(auction_data.increment)} every {seconds} seconds."
        self.increment_description.setText(increment_message)

        self.buyers_list.clear()
        for b in auction_data.buyers:
            active_or_withdrew = "active" if auction_data.is_active(b) else "withdrew"
            self.buyers_list.addItem(b + "  :  " + active_or_withdrew)




class Auction_Started_Page(QWidget):
    def __init__(self, root_widget):
        super().__init__()
        self.root_widget = root_widget
        self.auction_id = None
        
        layout = QVBoxLayout()

        item_row = QHBoxLayout()
        item_row.addWidget(QLabel("Selling:"))
        self.item_label = QLabel()
        self.item_label.setFont(BOLD)
        item_row.addWidget(self.item_label)
        layout.addLayout(item_row)

        layout.addWidget(QLabel("Auction has started."))
        self.increment_description = QLabel()
        layout.addWidget(self.increment_description)
        
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

        waiting_label = QLabel("Waiting for the auction to finish.\n(Auction will finish when only one buyer is active.)")
        layout.addWidget(waiting_label)

        self.setLayout(layout)

    """ This function is called when we need to update the UI
        with new auction_data
    """
    def update(self, auction_data):
        self.auction_id = auction_data.id
        self.item_label.setText(auction_data.item.name)
        self.current_price_label.setText(price_to_string(auction_data.current_price))
        
        seconds = auction_data.price_increment_period / 1000
        increment_message = f"The price is increasing by {price_to_string(auction_data.increment)} every {seconds} seconds."
        self.increment_description.setText(increment_message)

        self.buyers_list.clear()
        for b in auction_data.buyers:
            active_or_withdrew = "active" if auction_data.is_active(b) else "withdrew"
            self.buyers_list.addItem(b + "  :  " + active_or_withdrew)


class Auction_Resume_Page(QWidget):
    def __init__(self, root_widget):
        super().__init__()
        self.root_widget = root_widget
        self.auction_id = None
        
        layout = QVBoxLayout()

        item_row = QHBoxLayout()
        item_row.addWidget(QLabel("Selling:"))
        self.item_label = QLabel()
        self.item_label.setFont(BOLD)
        item_row.addWidget(self.item_label)
        layout.addLayout(item_row)

        price_row = QHBoxLayout()
        price_row.addWidget(QLabel("Auction started previously and paused at price:"))
        self.current_price_label = QLabel()
        self.current_price_label.setFont(BOLD)
        price_row.addWidget(self.current_price_label)
        layout.addLayout(price_row)

        self.increment_description = QLabel()
        layout.addWidget(self.increment_description)
        
        buyers_view = QVBoxLayout()
        buyers_view.addWidget(QLabel("Current buyers:"))
        self.buyers_list = QListWidget()
        buyers_view.addWidget(self.buyers_list)
        layout.addLayout(buyers_view)
    
        layout.addWidget(QLabel("Do you want to resume this auction?"))
        
        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(self.resume_button_clicked)
        layout.addWidget(self.resume_button)

        self.setLayout(layout)

    def resume_button_clicked(self):
        auction_id = self.auction_id
        # call the model's start_auction() function to resume the auction
        success, message = self.root_widget.model.start_auction(auction_id, resume=True)
        if not success:
            # if not successful, display error message
            QMessageBox.critical(self, "", message)


    """ This function is called when we need to update the UI
        with new auction_data
    """
    def update(self, auction_data):
        self.auction_id = auction_data.id
        self.item_label.setText(auction_data.item.name)
        self.current_price_label.setText(price_to_string(auction_data.current_price))
        
        seconds = auction_data.price_increment_period / 1000
        increment_message = f"Once resumed, the price will increase by {price_to_string(auction_data.increment)} every {seconds} seconds."
        self.increment_description.setText(increment_message)

        self.buyers_list.clear()
        for b in auction_data.buyers:
            active_or_withdrew = "active" if auction_data.is_active(b) else "withdrew"
            self.buyers_list.addItem(b + "  :  " + active_or_withdrew)


class Auction_Finished_Page(QWidget):
    def __init__(self, root_widget):
        super().__init__()
        self.root_widget = root_widget
        self.auction_id = None
        
        layout = QVBoxLayout()

        item_row = QHBoxLayout()
        item_row.addWidget(QLabel("Sold:"))
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
        self.item_label.setText(auction_data.item.name)
        self.winner_label.setText(auction_data.winner_username)
        self.price_label.setText(price_to_string(auction_data.transaction_price))

