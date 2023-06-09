from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedLayout, QFormLayout, QGroupBox
from PyQt6.QtWidgets import QListWidget, QLabel, QPushButton, QMessageBox
from PyQt6.QtGui import QFont
from PyQt6.QtCore import pyqtSignal, QObject, Qt

from concurrent import futures
import grpc
import auction_pb2_grpc
import auction_pb2 as pb2

import time
import threading
import copy

import utils
from utils import UserData, AuctionData, ItemData, price_to_string

# import test_toolkit
import logging

DEMON = True

class Data():
    """ Define the data a buyer has """
    def __init__(self):
        self.username = None   # Buyer's username
        self.auctions = {}     # A mapping from aution's id to AuctionData
        
        if DEMON == True:
            # This data is used only for demonstration purposes
            # It is a dictionary that maps each user's username to their RPC address.
            # When the address changes, a message will be displayed on screen
            self.addresses = {} 
              
        self.rpc_stubs = {}    # A dictionary that maps each user's username to their RPC service stub
        self.lock = threading.Lock()  # A lock to prevent data from being modified by multiple threads simultaneously. 


class Buyer(QObject):
    """ The main Buyer object. At a high level, the object contains 4 components:

        1. self.data : contains all the data the buyer has (like auction data)
        2. self.ui   : manages the UI window
        3. self.rpc  : provides RPC services to sellers
        4. self      : contains functions that take input from the UI part and the RPC part,
                       manipulate the data, tell the UI part to update, and return responses for RPCs
        
        The buyer object takes input both from the user via the UI component (self.ui)
        and from sellers via the RPC component (self.rpc), manipuates the data, 
        and then notifies the UI component to update by self.ui_update() function, 
        or returns results to the RPC component which then returns responses to the sellers.

        The buyer also makes RPC requests to the platform server, using the given server_stubs.  
    """
    ui_update_all_signal = pyqtSignal()
    ui_update_auctions_signal = pyqtSignal()
    ui_display_message_signal = pyqtSignal()

    def __init__(self, username, rpc_address, server_stubs):
        super().__init__()

        self.data = Data()
        self.data.username = username

        self.server_stubs = server_stubs

        self.ui = BuyerUI(self)
        self.ui_update_all_signal.connect(lambda : self.ui_update(mode="all"))
        self.ui_update_auctions_signal.connect(lambda : self.ui_update(mode="auctions"))

        if DEMON == True:
            self.message_to_display = ""
            self.ui_display_message_signal.connect(lambda : self.ui.display_message(self.message_to_display))

        # Start buyer's RPC service 
        self.rpc = Buyer_RPC_Servicer(self)
        rpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=64))
        auction_pb2_grpc.add_BuyerServiceServicer_to_server(self.rpc, rpc_server)
        rpc_server.add_insecure_port(rpc_address)
        rpc_server.start()
        threading.Thread(target=rpc_server.wait_for_termination, daemon=True).start()
        print(f"Buyer {self.data.username} RPC server started at {rpc_address}.")

        # Start a loop to periodically fetch data from the platform and update the UI.
        threading.Thread(target = self.data_fetch_loop, daemon=True).start()

        # Finally, update UI (by emitting signal to notify the UI component)
        self.ui_update_all_signal.emit()
    
    
    def ui_update(self, mode):
        """ This function updates the UI 

            Parameter: 
            - mode (str) : can be "all" or "auctions",
                indicating whether to update the entire UI or just the auction page part of the UI. 
        """
        # Copy the data and give them to the UI object, 
        # so that the data will not change when the UI is updating. 
        data_copy = Data()
        with self.data.lock:
            data_copy.username = copy.deepcopy(self.data.username)
            data_copy.auctions = copy.deepcopy(self.data.auctions)
        
        if mode == "all":
            self.ui.update_all(data_copy)
        elif mode == "auctions":
            self.ui.update_auctions(data_copy)
    

    def handle_announce_price(self, request):
        """ Handle seller's announce_price RPC request
            
            Input: 
             - request : an [auction_pb2.AnnouncePriceRequest] object
        """
        auction_id = request.auction_id
        round_id = request.round_id
        price = request.price
        buyer_status = request.buyer_status
        logging.info(f"Buyer {self.data.username} receives annouce_price [{auction_id}], price=[{price}]")

        # Acquire lock before modifying data
        with self.data.lock:
            if auction_id not in self.data.auctions:
                return
            auction = self.data.auctions[auction_id]

            # If seller's round_id  <  buyer's round_id on record: 
            #   This means that the seller's annouce_price request is out-of-date, just ignore the request
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
            # Update the status of buyers in this auction (some buyers may have withdrawn)
            auction.update_buyer_status(buyer_status)
        
        # After the operation, the UI needs to be updated. 
        # So, we emit a signal to notify the UI to update.
        # We use a signal because the UI update is time-consuming and is done in another thread. 
        self.ui_update_auctions_signal.emit()
    

    def handle_finish_auction(self, request):
        """ Handle seller's finish_auction RPC request
            
            Input: 
            - request : an [auction_pb2.FinishAuctionRequest] object
        """
        # Obtain information from the request
        auction_id = request.auction_id
        winner_username = request.winner_username
        transaction_price = request.price
        buyer_status = request.buyer_status
        logging.info(f"Buyer {self.data.username} receives finish_auction RPC, auction = {auction_id}")
        
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
        # We use a signal because the UI update is time-consuming and is done in another thread. 
        self.ui_update_auctions_signal.emit()
    
    
    def withdraw(self, auction_id):
        """ Perform the operation that the buyer (self) withdraw from an auction
            - Input:
                - auction_id (str)  : the id of the auction the buyer is withdrawing from
            - Return:
                - success    (bool) : whether this operation is successful or not
                - message    (str)  : error message if not successful
        """
        if auction_id not in self.data.auctions:
            return False, f"Auction {auction_id} does not exists!"
        
        # get this auction's seller's username and RPC stub
        with self.data.lock:
            seller_username = self.data.auctions[auction_id].seller.username
            if seller_username not in self.data.rpc_stubs:
                return False, f"Cannot find seller's network address."
            stub = self.data.rpc_stubs[seller_username]
        
        # Send a withdraw request to the seller using the stub and return the response 
        request = pb2.UserAuctionPair()
        request.auction_id = auction_id
        request.username = self.data.username
        try:
            response = stub.withdraw(request)
            success, message = response.success, response.message
        except grpc.RpcError as e:
            print(e)
            success, message = False, f"Cannot withdraw. Network error!"
        
        return success, message


    def join_auction(self, auction_id):
        logging.info(f"Buyer [{self.data.username}] tries to join auction [{auction_id}]")
        request = {"op": "BUYER_JOIN_AUCTION", 
                   "username": self.data.username, 
                   "auction_id": auction_id }
        server_ok, response = self.rpc_to_server(request)
        if not server_ok:
            return False, "Server error. Please try again." 
        if response["success"] == False:
            return False, "Cannot join this auction. Reason:" + response["message"]
        logging.info(f" Buyer [{self.data.username}] tries to join auction [{auction_id}]: success")
        # At this point, the operation is successful. Fetch auction data from server to update the UI.
        self.fetch_auctions_from_server_and_update()
        return True, "success"
    

    def quit_auction(self, auction_id):
        logging.info(f" Buyer [{self.data.username}] tries to quit from auction [{auction_id}]")
        request = {"op": "BUYER_QUIT_AUCTION", 
                   "username": self.data.username,
                   "auction_id": auction_id }
        server_ok, response = self.rpc_to_server(request)
        if not server_ok:
            return False, "Server error. Please try again." 
        if response["success"] == False:
            return False, "Cannot quit from this auction. Reason:" + response["message"]
        logging.info(f"  Buyer [{self.data.username}] tries to quit from auction [{auction_id}]: success")
        # At this point, the operation is successful. Fetch auction data from server to update the UI.
        self.fetch_auctions_from_server_and_update()
        return True, "success"
    

    def rpc_to_server(self, request):
        # return test_toolkit.test_1.rpc_to_server(request)
        return utils.rpc_to_server_stubs(request, self.server_stubs)


    def data_fetch_loop(self):
        while True:
            self.fetch_auctions_from_server_and_update()  # first, fetch all auctions from server
            self.update_seller_address_in_all_auctions()  # then, update the addresses of sellers in those auctions
            time.sleep(1)
    

    def fetch_auctions_from_server_and_update(self):
        """ Fetch all auctions from the platform to update the local data. """
        auction_list_needs_update = False   # records whether the auciton list in the UI needs to be updated
        ok, platform_auctions = self.get_all_auctions_from_server()
        if not ok: return 

        for pa in platform_auctions:
            with self.data.lock:
                if pa.id in self.data.auctions:
                    # For an auction that is in both platforms and buyer's data, 
                    #  - If the auction is finished: replace the buyer's data with the platform's:
                    if pa.finished:
                        logging.debug(f" Buyer [{self.data.username}] fetch: update auction [{pa.id}]: finished")
                        self.data.auctions[pa.id] = pa
                        continue
                    #  - If the auction is not started and not finished: replace the buyer's data with the platform's:  
                    elif not pa.started:
                        logging.debug(f" Buyer [{self.data.username}] fetch: update auction [{pa.id}]: not started")
                        self.data.auctions[pa.id] = pa
                        continue 
                    #  - Otherwise, the auction is started and not finished:
                    #    Do not change the buyer's data because the auction is taken cared of by the seller now
                    else:
                        continue
                else:
                    # For an auction that is in the platform's data but in the buyer's, 
                    # add this auction to the buyer's auction list
                    logging.debug(f" Buyer [{self.data.username}] fetch: update auction [{pa.id}]: new auction")
                    self.data.auctions[pa.id] = pa
                    auction_list_needs_update = True
        
        # If the auction lists needs to update, update the entire UI, 
        if auction_list_needs_update:
            self.ui_update_all_signal.emit()
        else:
        # Otherwise, just update the auction part of the UI. 
            self.ui_update_auctions_signal.emit() 
    

    def get_all_auctions_from_server(self):
        request = { "op": "BUYER_FETCH_AUCTIONS",
                    "username": self.data.username }
        server_ok, response = self.rpc_to_server(request)
        if not server_ok:
            logging.info(f"Buyer [{self.data.username}] tries to fetch auctions from server: FAIL, server error")
            return False, None
        if response["success"] == False:
            logging.info(f"Buyer [{self.data.username}] tries to fetch auctions from server: FAIL, reason:" + response["message"])
            return False, None
        list_of_auctions = []
        for d in response["message"]:
            a = AuctionData()
            a.update_from_dict(d)
            list_of_auctions.append(a)
        return True, list_of_auctions
    

    def get_address_from_server(self, username):
        request = { "op": "GET_USER_ADDRESS", 
                    "username": username }
        server_ok, response = self.rpc_to_server(request)
        if not server_ok:
            return False, f"Cannot get the address of {username}: Server Error."
        if response["success"] == False:
            return False, f"Cannot get the address of {username}: " + response["message"]
        
        # Get the address from response["message"]
        address = response["message"]

        # If we are in the demonstration mode, then display a message on screen if the user's address changes: 
        if DEMON == True:
            with self.data.lock:
                if username not in self.data.addresses or address != self.data.addresses[username]:
                    self.message_to_display = f"User [{username}] changes RPC address to {address}"
                    print(self.message_to_display)
                    self.ui_display_message_signal.emit()
                self.data.addresses[username] = address
                
        # At this point, the operation is successful. Return success and the result.  
        return True, address
    

    def update_seller_address_in_all_auctions(self):
        for auction in self.data.auctions.values():
            seller_username = auction.seller.username
            ok, address = self.get_address_from_server(seller_username)
            if ok:
                # if got the address, create a RPC stub with the address
                channel = grpc.insecure_channel(address)
                stub = auction_pb2_grpc.SellerServiceStub(channel)
                with self.data.lock:
                    self.data.rpc_stubs[seller_username] = stub


class Buyer_RPC_Servicer(auction_pb2_grpc.BuyerServiceServicer):
    """ The RPC servicer on a buyer client.

        - Provides two RPC services to a seller:
            1. announce_price()
            2. finish_auction()
        * Note:
            The RPC services are multi-threaded.
            Implementation of the RPC request handlers should be careful.  
    """
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

class BuyerUI(QWidget):
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
        column_1.addWidget(QLabel("logged in as buyers.\n"))

        column_1.addWidget(QLabel("Auctions on the platform:"))
        self.auction_list_widget = QListWidget()
        self.auction_list_widget.itemClicked.connect(self.auction_list_clicked)
        column_1.addWidget(self.auction_list_widget)
        self.auction_id_list = []   # record the id of the auctions in the list
        mainlayout.addLayout(column_1)

        column_2 = QVBoxLayout()
        self.auction_box = QGroupBox()
        self.stacked_layout = QStackedLayout()
        self.empty_page = QWidget()
        self.stacked_layout.addWidget(self.empty_page)
        self.stacked_layout.setCurrentWidget(self.empty_page)
        self.auction_box.setLayout(self.stacked_layout)
        column_2.addWidget(self.auction_box)

        mainlayout.addLayout(column_2)
    

    def auction_list_clicked(self):
        """ UI: handle user clicking an auction in the auction list """
        selected_row = self.auction_list_widget.currentRow()
        # records which auction is selected by the user
        self.selected_auction = self.auction_id_list[selected_row]
        # then display the selected auction
        self.update_displayed_auction()

    
    def update_displayed_auction(self):
        """ Update the UI of the auction displayed on screen """
        w = self.empty_page
        if (self.data != None) and (self.selected_auction in self.data.auctions):
            # get the data of the selected auction
            a = self.data.auctions[self.selected_auction]
            # create a new page based on auction status
            if a.finished == True:
                w = Auction_Finished_Page(self, a) 
            elif a.started == False:
                w = Auction_Prestarted_Page(self, a)
            else:
                w = Auction_Started_Page(self, a)
        # remove the current page and add the new page
        self.stacked_layout.removeWidget(self.stacked_layout.currentWidget())
        self.stacked_layout.addWidget(w)
        self.stacked_layout.setCurrentWidget(w)
    
    
    def update_all(self, data):
        """ Updates the entire UI, using the given new data """
        self.data = data
        self.username_label.setText(data.username)
        self.update_auction_list(data.auctions)
        self.update_auctions(data)
    

    def update_auction_list(self, auctions):
        """ This function only updates the auction list, given new auction data """
        self.auction_list_widget.clear()
        self.auction_id_list = []
        for (auction_id, a) in auctions.items():
            self.auction_list_widget.addItem(a.name)
            self.auction_id_list.append(auction_id)
    

    def update_auctions(self, data):
        """ This function only updates the auction page UI, given new data """
        self.data = data
        self.update_displayed_auction()
    

    def display_message(self, message):
        QMessageBox.critical(self, "", message)


class Auction_Page_Base(QWidget):
    def __init__(self, root_widget, auction_data):
        super().__init__()
        self.root_widget = root_widget
        self.auction_id = auction_data.id
        
        self.mainlayout = QVBoxLayout()
        self.setLayout(self.mainlayout)

        auction_name_label = QLabel(auction_data.name)
        auction_name_font = QFont()
        auction_name_font.setPointSize(23)
        auction_name_label.setFont(auction_name_font)
        auction_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mainlayout.addWidget(auction_name_label)

        seller_item_form = QFormLayout()
        seller_label = QLabel(auction_data.seller.username)
        BOLD = QFont()
        BOLD.setBold(True)
        seller_label.setFont(BOLD)
        item_name_label = QLabel(auction_data.item.name)
        item_name_label.setFont(BOLD)
        item_description_label = QLabel(auction_data.item.description)
        seller_item_form.addRow(QLabel("seller:"), seller_label)
        seller_item_form.addRow(QLabel("Item:"),   item_name_label)
        seller_item_form.addRow(QLabel("Description:"), item_description_label)
        self.mainlayout.addLayout(seller_item_form)


class Auction_Prestarted_Page(Auction_Page_Base):
    def __init__(self, root_widget, auction_data):
        super().__init__(root_widget, auction_data)
        self.mainlayout.addWidget(QLabel("Auction has not started."))
        seconds = auction_data.price_increment_period / 1000
        increment_message = f"Once started, the price will increase by {price_to_string(auction_data.increment)} every {seconds} seconds."
        self.mainlayout.addWidget(QLabel(increment_message))

        buyers_view = QVBoxLayout()
        if self.root_widget.data.username not in auction_data.buyers:
            buyers_view.addWidget(QLabel("You cannot see the list of buyers because you haven't joined the auction."))
        else:
            buyers_view.addWidget(QLabel("Current buyers in the auction:"))
            self.buyers_list = utils.UI_tools.make_buyer_list(auction_data, need_status=False)
            buyers_view.addWidget(self.buyers_list)
        self.mainlayout.addLayout(buyers_view)

        if self.root_widget.data.username not in auction_data.buyers:
            self.mainlayout.addWidget(QLabel("Do you want to join this auction? "))
            self.join_button = QPushButton("Join")
            self.join_button.clicked.connect(self.join_button_clicked)
            self.mainlayout.addWidget(self.join_button)
        else:
            self.mainlayout.addWidget(QLabel("You are in the auction, waiting for the seller to start...."))
            self.mainlayout.addWidget(QLabel("Do you want to quit from the auction? "))
            self.quit_button = QPushButton("Quit")
            self.quit_button.clicked.connect(self.quit_button_clicked)
            self.mainlayout.addWidget(self.quit_button)

    def join_button_clicked(self):
        auction_id = self.auction_id
        success, message = self.root_widget.model.join_auction(auction_id)
        if not success:
            QMessageBox.critical(self, "", message)
    
    def quit_button_clicked(self):
        auction_id = self.auction_id
        success, message = self.root_widget.model.quit_auction(auction_id)
        if not success:
            QMessageBox.critical(self, "", message)
        

class Auction_Started_Page(Auction_Page_Base):
    def __init__(self, root_widget, auction_data):
        super().__init__(root_widget, auction_data)
        self.mainlayout.addWidget(QLabel("Auction has started."))

        # If this buyer does not join this auction. Do not show any information.
        if self.root_widget.data.username not in auction_data.buyers:
            self.mainlayout.addWidget(QLabel("You did not join this auction, so cannot see other information of this auction."))
            return
        
        # Otherwise (the buyer joined the auction), show the current price and the status of participating buyers.
        price_row = QHBoxLayout()
        price_row.addWidget(QLabel("Current price: "))
        self.current_price_label = QLabel(price_to_string(auction_data.current_price))
        self.current_price_label.setFont(BOLD)
        price_row.addWidget(self.current_price_label)
        self.mainlayout.addLayout(price_row)

        seconds = auction_data.price_increment_period / 1000
        increment_message = f"The price is increasing by {price_to_string(auction_data.increment)} every {seconds} seconds."
        self.mainlayout.addWidget(QLabel(increment_message))

        buyers_view = QVBoxLayout()
        buyers_view.addWidget(QLabel("Current buyers:"))
        self.buyers_list = utils.UI_tools.make_buyer_list(auction_data, need_status=True)
        buyers_view.addWidget(self.buyers_list)
        self.mainlayout.addLayout(buyers_view)

        # If the buyer has withdawn, do not show a withdraw button
        if auction_data.is_active(self.root_widget.data.username) == False:
            withdrawn_info = QLabel("\nYou have withdrawn from the auction.")
            self.mainlayout.addWidget(withdrawn_info)
            return
        
        # Otherwise, show a withdraw button 
        self.mainlayout.addWidget(QLabel("\nDo you want to withdraw from the auction?\n(Once withdrawn, you cannot re-join the auction.)"))
        self.withdraw_button = QPushButton("Withdraw")
        self.withdraw_button.clicked.connect(self.withdraw_button_clicked)
        self.mainlayout.addWidget(self.withdraw_button)

    def withdraw_button_clicked(self):
        """ UI: handle the case that the user clickes the withdraw button """
        auction_id = self.auction_id
        success, message = self.root_widget.model.withdraw(auction_id)
        if not success:
            self.root_widget.display_message(message)


class Auction_Finished_Page(Auction_Page_Base):
    def __init__(self, root_widget, auction_data):
        super().__init__(root_widget, auction_data)
        self.mainlayout.addWidget(QLabel("Auction has finished."))
        
        winner_info = QVBoxLayout()
        if auction_data.winner_username in {"", None}:
            winner_info.addWidget(QLabel("This auction does not have a winner."))
        else:
            winner_row = QHBoxLayout()
            winner_row.addWidget(QLabel("Winner:"))
            self.winner_label = QLabel(auction_data.winner_username)
            BOLD = QFont();  BOLD.setBold(True)
            self.winner_label.setFont(BOLD)
            winner_row.addWidget(self.winner_label)
            price_row = QHBoxLayout()
            price_row.addWidget(QLabel("Transaction price: "))
            self.price_label = QLabel(price_to_string(auction_data.transaction_price))
            self.price_label.setFont(BOLD)
            price_row.addWidget(self.price_label)
            winner_info.addLayout(winner_row)
            winner_info.addLayout(price_row)
        self.mainlayout.addLayout(winner_info)

        # Depending on whether the buyer were in the auction, display the information of buyers in the auction or not 
        if self.root_widget.data.username in auction_data.buyers:
            self.mainlayout.addWidget(QLabel("Participated buyers:"))
            self.mainlayout.addWidget(utils.UI_tools.make_buyer_list(auction_data, need_status=False, gray_background=True))
        else:
            self.mainlayout.addWidget(QLabel("You cannot see the other buyers because you didn't join the auction."))

        
