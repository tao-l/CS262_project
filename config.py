F = 1      # number of faulty servers we want to tolerate

need_persistent = True      # whether we need our servers to be persistent

local = True        # whether to run the system locally

class ServerInfo():
    def __init__(self, id, ip_addr, client_port, raft_port):
        self.id = id, 
        self.ip_addr = ip_addr
        self.client_port = client_port
        self.raft_port = raft_port

replicas = ( ServerInfo(0, "127.0.0.1", "20000", "30000"), 
             ServerInfo(1, "127.0.0.1", "20010", "30010"), 
             ServerInfo(2, "127.0.0.1", "20020", "30020"), 
           )

if local:
    for x in replicas:
        x.ip_addr = "127.0.0.1"

n_replicas = len(replicas)
# assert n_replicas > 2*F


leader_broadcast_interval = 40  # millisecond
election_timeout_lower_bound = 200
election_timeout_upper_bound = 400

SERVER_ERROR = 190


# Platform rpc service operation
LOGIN = "LOGIN"
GET_USER_ADDRESS = "GET_USER_ADDRESS"
BUYER_FETCH_AUCTIONS = "BUYER_FETCH_AUCTIONS"
BUYER_JOIN_AUCTION = "BUYER_JOIN_AUCTION"
BUYER_QUIT_AUCTION = "BUYER_QUIT_AUCTION"
SELLER_CREATE_AUCTION = "SELLER_CREATE_AUCTION"
SELLER_START_AUCTION = "SELLER_START_AUCTION"
SELLER_FINISH_AUCTION = "SELLER_FINISH_AUCTION"
SELLER_FETCH_AUCTIONS = "SELLER_FETCH_AUCTIONS"
SELLER_UPDATE_AUCTION = "SELLER_UPDATE_AUCTION"
PLATFORM_READ_ONLY_OP = [GET_USER_ADDRESS, BUYER_FETCH_AUCTIONS, SELLER_FETCH_AUCTIONS]

OPERATION_NOT_SUPPORTED = 404

# AUCTION_SHIELD_KEYS = ["buyers", "current_price", "round_id", "transaction_price", "winner_username"]
AUCTION_SHIELD_KEYS = ["buyers", "current_price", "round_id"]   # The fields that a buyer who does not join an auction cannnot see
