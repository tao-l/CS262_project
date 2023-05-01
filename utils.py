import auction_pb2 as pb2

class UserData():
    def __init__(self, username=""):
        # For simplicity, we use username as the id of a user.
        # This means that a username should be unique. 
        self.username = username     

class ItemData():
    def __init__(self, name = "", description = ""):
        self.name = name
        self.description = description
        

class AuctionData():
    def __init__(self, name="", id=None, seller=None, item=None,
                 base_price=0, price_increment_period=1000, increment=0):
        self.name = name
        self.id = id
        if seller == None:
            self.seller = UserData()
        else:
            self.seller = seller
        if item == None:
            self.item = ItemData()
        else:
            self.item = item

        # Base price:
        # Note : prices are represented by integers. 
        #        e.g., $12.34 is represneted as 1234
        self.base_price = base_price
        
        # the frequency (period) and increment of price adjustment
        self.price_increment_period = price_increment_period    # Period of price increment in milliseconds (int). 
        self.increment = increment       # the amount by which the price is increased each time (int)

        # record whether the auction has started and finished
        self.started = False
        self.finished = False
        
        self.resume = False  # If a seller application restarts and fetches from the platform a previously started auction, this auction needs to be resumed.

        # For auction that has been started, need current_price and round_id
        self.current_price = base_price
        self.round_id = -1

        # For auction that has finished, need transaction_price and winner
        self.transaction_price = base_price
        self.winner_username = None

        # A dictionary that records the (usernames of) buyers that have joined this auction
        # and whether they are active, e.g., buyers[username] = True (active)
        self.buyers = {}
    

    
    def is_active(self, username):
        """ Return whether buyer [username] is active in this auction. """
        if username not in self.buyers:
            return False
        return self.buyers[username]

    
    def n_active_buyers(self):
        """ Return the number of buyers that are active in this auction. 
        (Can be used to check whether this auction is finished.)
        """
        active = 0
        for b in self.buyers:
            if self.is_active(b):
                active += 1
        return active
    
    
    def withdraw(self, username):
        """ Withdraw buyer [username] from the auction.
            Return False if the buyer is not in the auction
        """
        if username not in self.buyers:
            return False
        self.buyers[username] = False
        return True
    
    
    def update_buyer_status(self, buyer_status):
        """ Update the status of buyers in this auction
            - Input: a repeated pb2.BuyerStatus object
        """
        self.buyers = {}
        for x in buyer_status:
            self.buyers[x.username] = x.active
    
    
    def get_buyer_status_list(self):
        res = []
        for b in self.buyers:
            res.append(pb2.BuyerStatus(username=b, active=self.is_active(b)))
        return res
    

    def get_winner(self):
        """ Return the username of the winner of the auction,
            None if no winner
        """
        for buyer in self.buyers:
            if self.is_active(buyer):
                return buyer
        return None


def price_to_string(price):
    return "${:.2f}".format(price / 100)



def string_to_number_and_check_range(s, lb, ub):
    """ Convert string s to a number and check whether it is in range [lb, ub].
    Will return successful or not and error message.

    - Input: (s : str,  lb : lower bound (float) ,  ub : upper bound (float))
    - Return: ( valid : bool,  number : float,  message : str )
    """
    try:
        number = float(s)
    except:
        return (False, None, f'"{s}" is not a number!')
    if number < lb or number > ub:
        return (False, None, f"Number {number} is invalid.\nIt should be >= {lb} and <= {ub}.")
    return (True, number, "good")


class RPC_Address:
    def __init__(self, ip="", port=""):
        self.ip = ip
        self.port = port


def find_address_from_server(username):
    # return test_toolkit.Example_1.find_address_from_server(username)
    pass
    