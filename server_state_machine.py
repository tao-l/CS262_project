import auction_pb2 as pb2

import threading
import config
from config import *
import copy
import json

## //TODO: auction["created"], auction["started"] auction["finished"]

class StateMachine:

    def __init__(self):
        #  States/data of the state machine
        self.accounts = {} # a dictionary that maps users to their RPC service addresses.
        self.auctions = [] # auction id starts from 1, each being a dictionary
        self.lock = threading.Lock() #  a lock to ensure that only one command is excecued at a time, only used for debugging.  
    
    def check_buyer_in_auction(self, username, auction_id):
        """ Check if buyer is a participant of the auction
            Both the buyer and the auction id must exist
            - Input:
                username   : string, the username to be queried, string
                auction_id : string,    the auction index from 1 to ...
        """
        auction_id = int(auction_id)
        assert username in self.accounts and auction_id <= len(self.auctions)
        if username not in self.auctions[auction_id-1]["buyers"]: 
            return False
        return True


    # We define the functionality of different commands: 
    def login(self, request):
        """ Create account with username [request[username]] if username does not exist
            If account already exists, log the ip address and port
            Client logging in from two terminal will disconnect one.
            - Input:
                request   : json string converted dictionary
            - Return:
                response  : auction_pb2.PlatformServiceResponse
        """
        assert self.lock.locked()
        username = request["username"]
        
        self.accounts[username] = request["address"]
        js = {"success": True, "message": "Login successful"}
        response = pb2.PlatformServiceResponse(json=json.dumps(js))
        print(f"Account [{username}] logged in")
        return response
        

    def get_user_address(self, request):
        """ Retrieve ip address:port associated with [request.username]
            Respond error message if the account does not exist
            - Input:
                request  :  json string converted dictionary
                response :  pb2.PlatformServiceResponse
        """
        assert self.lock.locked()
        username = request["username"]
        
        response = pb2.PlatformServiceResponse()
        # return error if username does not exist
        if username not in self.accounts:
            msg= f"User {username} does not exist."
            js = {"success": False,
                    "message":msg}
        else:
            msg = self.accounts[username]
            js = {"success": True,
                    "message":msg}

        response.json = json.dumps(js)
        return response
    
    def buyer_fetch_auctions(self, request):
        """ Retrieve all auctions. Detailed info provided for auctions that [request.username]
            have joined. Only meta info provided for auctions that [request.username] has not 
            joined
            - Input:
                request  : json string converted dictionary
                response : pb2.PlatformServiceResponse
        """
        assert self.lock.locked()
        username = request["username"]
        response = pb2.PlatformServiceResponse()

        if username not in self.accounts:
            msg= f"User {username} does not exist."
            js = {"success": False,
                    "message":msg}
            response.json = json.dumps(js)
            return response

        msg = []
        for auction in self.auctions: # a list of dictionaries, each holding an auction
            if username in auction["buyers"]:
                msg.append(auction)
            else:
                # buyer not participating 
                auction_copy = {k:v for k,v in auction.items() if k not in config.AUCTION_SHIELD_KEYS}
                msg.append(auction_copy)
        js = {"success":True, "message":msg}
        response.json = json.dumps(js)
        return response
    
    def seller_fetch_auctions(self, request):
        """ Seller retrieves all auctions that this seller runs
            - Input:
                request  : json string converted dictionary, username
                response : pb2.PlatformServiceResponse
        """
        assert self.lock.locked()
        username = request["username"]
        response = pb2.PlatformServiceResponse()

        if username not in self.accounts:
            msg= f"User {username} does not exist."
            js = {"success": False,
                    "message":msg}
            response.json = json.dumps(js)
            return response

        msg = []
        for auction in self.auctions: # a list of dictionaries, each holding an auction
            if auction["seller_username"] == username:
                msg.append(auction)
            else:
                # seller does not own this auction
                auction_copy = {k:v for k,v in auction.items() if k not in config.AUCTION_SHIELD_KEYS}
                msg.append(auction_copy)
        
        js = {"success":True, "message":msg}
        response.json = json.dumps(js)
        return response


    def buyer_join_auction(self, request):
        """ Buyer join auction requested. Can only successfully join when
            username exists, auction exists, auction has not started or finished
            - Input:
                request  : json string converted dictionary
                response : pb2.PlatformServiceResponse
        """
        assert self.lock.locked()
        username = request["username"]
        auction_id = int(request["auction_id"])
        response = pb2.PlatformServiceResponse()
        

        if username not in self.accounts:
            msg = f"User {username} does not exist."
            js = {"success": False,
                    "message":msg}
        elif auction_id > len(self.auctions):
            msg = f"Auction {auction_id} does not exist."
            js = {"success": False,
                    "message":msg}
        elif self.auctions[auction_id-1]["started"] or self.auctions[auction_id-1]["finished"]:
            msg = f"Auction {auction_id} has started or finished."
            js = {"success": False, "message":msg}
        elif self.check_buyer_in_auction(username, auction_id):
            msg = f"User {username} already in auction {auction_id}."
            js = {"success":True, "message":msg}
        else:
            # user not in auction buyer list. Add
            self.auctions[auction_id-1]["buyers"].append(username)
            msg = f"Added user {username} to auction {auction_id}."
            js = {"success":True, "message":msg}

        response.json = json.dumps(js)
        return response
    
    def buyer_quit_auction(self, request):
        """ Buyer quit auction prior to auction starts.
            - Input:
                request  : json string converted dictionary
                response : pb2.PlatformServiceResponse
        """
        assert self.lock.locked()
        username = request["username"]
        auction_id = int(request["auction_id"])
        response = pb2.PlatformServiceResponse()

        if username not in self.accounts:
            msg = f"User {username} does not exist."
            js = {"success": False, "message":msg}
        elif auction_id > len(self.auctions):
            msg = f"Auction {auction_id} does not exist."
            js = {"success": False, "message":msg}
        elif self.auctions[auction_id-1]["started"] or self.auctions[auction_id-1]["finished"]:
            msg = f"Auction {auction_id} has started or finished."
            js = {"success": False, "message":msg}
        elif not self.check_buyer_in_auction(username, auction_id):
            msg = f"User {username} not in auction {auction_id} yet."
            js = {"success":False, "message":msg}
        else:
            # buyer in the auction, withdrawl
            self.auctions[auction_id-1]["buyers"].remove(username)
            msg = f"User {username} quitted from auction {auction_id}."
            js = {"success":True, "message":msg}

        response.json = json.dumps(js)
        return response


    def seller_create_auction(self, request):
        """ Seller creates auction. If the entire entry is identical to a
             previous item, then this attempt has failed
            - Input:
                request  : json string, containing auction fields
                response : pb2.PlatformServiceResponse
        """
        assert self.lock.locked()
        
        response = pb2.PlatformServiceResponse()
        username = request["seller_username"]
        if username not in self.accounts:
            msg = f"User {username} does not exist."
            js = {"success": False, "message":msg}
            response.json = json.dumps(js)
            return response

        # create the auction dictionary
        auction_to_create = {
                "seller_username":username,
                "auction_name":request["auction_name"],
                "item_name":request["item_name"],
                "base_price":request["base_price"],
                "price_increment_period":request["price_increment_period"],
                "increment":request["increment"],
                "item_description":request["item_description"]
                }
        
        # check auction identity
        if self.auction_exists(auction_to_create):
            msg = f"Auction requested fully match with a previous auction. Auction already exists."
            js = {"success":False, "message":msg}
        else: # creating auction
            auction_id = len(self.auctions)+1
            auction_to_create["auction_id"] = auction_id # starts from 1
            auction_to_create["created"] = True
            auction_to_create["started"] = False
            auction_to_create["finished"] = False
            auction_to_create["buyers"] = [] # use a list instead of set for json format
            auction_to_create["round_id"] = -1
            auction_to_create["current_price"] = request["base_price"]
            auction_to_create["transaction_price"] = -1
            auction_to_create["winner_username"] = ""
            self.auctions.append(auction_to_create)
            msg = f"Auction {auction_id} successfully created."
            js = {"success":True, "message":msg}
        
        response.json = json.dumps(js)
        return response
    
    def seller_start_auction(self, request):
        """ Seller starts the auction.
            - Input:
                request  : json string converted dictionary
                response : pb2.PlatformServiceResponse
        """
        assert self.lock.locked()
        username = request["username"]
        auction_id = int(request["auction_id"])
        response = pb2.PlatformServiceResponse()

        if username not in self.accounts:
            msg = f"User {username} does not exist."
            js = {"success": False, "message":msg}
        elif auction_id > len(self.auctions):
            msg = f"Auction {auction_id} does not exist."
            js = {"success": False, "message":msg}
        elif self.auctions[auction_id-1]["finished"]:
            msg = f"Auction {auction_id} has already finished."
            js = {"success":False, "message":msg}
        elif self.auctions[auction_id-1]["started"]:
            msg = f"Auction {auction_id} has already started."
            js = {"success": True, "message":msg}
        else: # created status, write request
            self.auctions[auction_id-1]["started"] = True
            js = {"success":True, "message":self.auctions[auction_id-1]}
        response.json = json.dumps(js)
        return response
    
    def seller_finish_auction(self, request):
        """ Seller finish the auction. Can finish an auction before it starts
            - Input:
                request  : json string converted dictionary
                response : pb2.PlatformServiceResponse
        """
        assert self.lock.locked()
        username = request["username"]
        auction_id = int(request["auction_id"])
        response = pb2.PlatformServiceResponse()

        if username not in self.accounts:
            msg = f"User {username} does not exist."
            js = {"success": False, "message":msg}
        elif auction_id > len(self.auctions):
            msg = f"Auction {auction_id} does not exist."
            js = {"success": False, "message":msg}
        elif self.auctions[auction_id-1]["finished"]:
            msg = f"Auction {auction_id} has already finished."
            js = {"success": True, "message":msg}
        else:
            # start write request
            self.auctions[auction_id-1]["finished"] = True
            msg = f"Auction {auction_id} successfully finished"
            js = {"success":True, "message":msg}
        response.json = json.dumps(js)
        return response

    def seller_update_auction(self, request):
        """ Seller update auction, sending a heartbeat. 
            - Input:
                request  : json string converted dictionary, an auction sent
                response : pb2.PlatformServiceResponse
        """
        assert self.lock.locked()
        username = request["seller_username"]
        auction_id = int(request["auction_id"])
        response = pb2.PlatformServiceResponse()

        if username not in self.accounts:
            msg = f"User {username} does not exist."
            js = {"success": False, "message":msg}
        elif auction_id > len(self.auctions):
            msg = f"Auction {auction_id} does not exist."
            js = {"success": False, "message":msg}
        else: # change the status as seller demands
            self.auctions[auction_id-1] = request
            msg = f"Auction {auction_id} successfully updated."
            js = {"success":True, "message":msg}
        response.json = json.dumps(js)
        return response
        

    def auction_exists(self, auction):
        """ Check if an auction is identical to one of the existing auctions
            - Input:
                auction  : a dictionary of auction to create
        """
        for auction_existing in self.auctions:
            if all(auction_existing.get(key,None) == val for key, val in auction.items()):
                return True
        return False


    """ apply a command to the state machine, return the response
        - Input:
               request   : a json string converted to dictionary
        - Return:
               response  : pb2.PlatformServiceResponse
    """
    def apply(self, request):
        dispatch = {
            LOGIN                 : self.login,
            GET_USER_ADDRESS      : self.get_user_address,
            BUYER_FETCH_AUCTIONS  : self.buyer_fetch_auctions,
            BUYER_JOIN_AUCTION    : self.buyer_join_auction,
            BUYER_QUIT_AUCTION    : self.buyer_quit_auction,
            SELLER_CREATE_AUCTION : self.seller_create_auction,
            SELLER_START_AUCTION  : self.seller_start_auction,
            SELLER_FINISH_AUCTION : self.seller_finish_auction,
            SELLER_UPDATE_AUCTION : self.seller_update_auction,
            SELLER_FETCH_AUCTIONS : self.seller_fetch_auctions
        }
        
        op = request["op"]
        with self.lock:
            if op not in dispatch:
                response = pb2.PlatformServiceResponse()
                msg= f"Operation {request[op]} is not supported by the server."
                js = {"success": False,
                        "message":msg}
                response.json = json.dumps(js)
                return response
            else:
                del request["op"]
                return dispatch[op](request)
    


