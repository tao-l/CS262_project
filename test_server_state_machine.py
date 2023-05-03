import unittest
import json
import config
from server_state_machine import StateMachine

class StateMachineTestSellerRelated(unittest.TestCase):
    """
    Testing buyer called state machine functions
    """

    def setUp(self):
        self.sm = StateMachine()
        self.sm.accounts = {"buyer1":"127.0.0.1:2048","buyer2":"127.0.0.1:2049","buyer3":"127.0.0.1:4050", "test_seller":"127.0.0.1:4051"}
        auction_to_create = {
                "seller_username":"test_seller",
                "auction_name":"test_auction",
                "item_name":"test_item",
                "base_price":0,
                "price_increment_period":300,
                "increment":1,
                "item_description":"test_description",
                "auction_id": "1",
                "created": True,
                "finished": False,
                "started": False,
                "buyers":["buyer1","buyer2"],
                "round_id":-1,
                "current_price": 0,
                "transaction_price": -1,
                "winner_username":""}
        self.sm.auctions = [auction_to_create]
    
    def test_seller_fetch_auctions(self):
        # owner of auction
        request = {"op":config.SELLER_FETCH_AUCTIONS, "username":"test_seller"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertTrue("buyers" in js["message"][0])

        # test access control
        request = {"op":config.BUYER_FETCH_AUCTIONS, "username":"buyer3"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertFalse("buyers" in js["message"][0])

    def test_seller_create_auction(self):
        # successful creation 
        request = {
                "seller_username":"buyer3",
                "auction_name":"selling fake item",
                "item_name": "fake item",
                "base_price": 0,
                "price_increment_period": 300,
                "increment":1,
                "item_description": "fake item description"
        }
        request["op"] = config.SELLER_CREATE_AUCTION
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertTrue(js["success"])
 
        # identical with previous auction
        request = {
                "seller_username":"test_seller",
                "auction_name":"test_auction",
                "item_name": "test_item",
                "base_price": 0,
                "price_increment_period": 300,
                "increment":1,
                "item_description": "test_description"
        }
        request["op"] = config.SELLER_CREATE_AUCTION
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertFalse(js["success"])
        self.assertTrue("fully match" in js["message"])
    
    # same with seller_finish_auction
    def test_seller_start_auction(self):
        # success case
        request = {"op":config.SELLER_START_AUCTION, "username":"test_seller", "auction_id":"1"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertTrue(js["success"])
        self.assertTrue("buyers" in js["message"])

        # start a started case
        self.sm.auctions[0]["started"] = True
        request = {"op":config.SELLER_START_AUCTION, "username":"test_seller", "auction_id":"1"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertTrue(js["success"])
        self.assertTrue("has already started" in js["message"])

        # start a finished case
        self.sm.auctions[0]["finished"] = True
        request = {"op":config.SELLER_START_AUCTION, "username":"test_seller", "auction_id":"1"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertFalse(js["success"])
        self.assertTrue("has already finished" in js["message"])

class StateMachineTestBuyerRelated(unittest.TestCase):
    """
    Testing buyer called state machine functions
    """

    def setUp(self):
        self.sm = StateMachine()
        self.sm.accounts = {"buyer1":"127.0.0.1:2048","buyer2":"127.0.0.1:2049","buyer3":"127.0.0.1:2050"}
        auction_to_create = {
                "seller_username":"test_seller",
                "auction_name":"test_auction",
                "item_name":"test_item",
                "base_price":0,
                "price_increment_period":300,
                "increment":1,
                "item_description":"test_description",
                "auction_id": "1",
                "created": True,
                "finished": False,
                "started": False,
                "buyers":["buyer1","buyer2"],
                "round_id":-1,
                "current_price": 0,
                "transaction_price": -1,
                "winner_username":""}
        self.sm.auctions = [auction_to_create]

    
    def test_check_buyer_in_auction(self):
        self.assertEqual(self.sm.check_buyer_in_auction("buyer1",1),True) 
        with self.assertRaises(AssertionError):
            self.sm.check_buyer_in_auction("buyer0",1)
        with self.assertRaises(AssertionError):
            self.sm.check_buyer_in_auction("buyer1",2)
        self.assertEqual(self.sm.check_buyer_in_auction("buyer3",1),False)

    def test_check_login(self):
        self.assertEqual(self.sm.accounts["buyer1"],"127.0.0.1:2048")
        request = {"op":config.LOGIN, "username":"buyer0","address":"127.0.0.1:2047"}
        self.assertFalse("buyer0" in self.sm.accounts)
        self.sm.apply(request) 
        self.assertEqual(self.sm.accounts["buyer0"],"127.0.0.1:2047")

    def test_get_user_address(self):

        request = {"op":config.GET_USER_ADDRESS, "username":"buyer1"}
        response = self.sm.apply(request) #get_user_address({"username":"buyer1"})
        js = json.loads(response.json)
        self.assertEqual(js["message"],"127.0.0.1:2048")

        request = {"op":config.GET_USER_ADDRESS, "username":"buyer0"}
        response = self.sm.apply(request) #get_user_address({"username":"buyer0"})
        js = json.loads(response.json)
        #print(js["message"])
        self.assertFalse(js["success"])
    
    def test_buyer_fetch_auctions(self):
        request = {"op":config.BUYER_FETCH_AUCTIONS, "username":"buyer1"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        #print(js["message"])
        self.assertTrue("buyers" in js["message"][0])

        # test access control
        request = {"op":config.BUYER_FETCH_AUCTIONS, "username":"buyer3"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        #print(js["message"])
        self.assertFalse("buyers" in js["message"][0])

    def test_buyer_join_auction(self):
        # "wrong auction ID number"
        request = {"op":config.BUYER_JOIN_AUCTION, "username":"buyer3","auction_id":"2"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertFalse(js["success"])
        self.assertTrue("does not exist" in js["message"])
        
        # user already joined
        request = {"op":config.BUYER_JOIN_AUCTION, "username":"buyer2","auction_id":"1"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertTrue(js["success"])
        self.assertTrue("already in auction" in js["message"])
        
        # success case
        request = {"op":config.BUYER_JOIN_AUCTION, "username":"buyer3","auction_id":"1"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertTrue(js["success"])
        self.assertEqual("Added user buyer3 to auction 1.", js["message"])

        # auction already started
        self.sm.accounts["buyer4"] = "127.0.0.1:4050"
        self.sm.auctions[0]["started"] = True
        request = {"op":config.BUYER_JOIN_AUCTION, "username":"buyer4","auction_id":"1"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertFalse(js["success"])
        self.assertTrue("has started or finished" in js["message"])
        
    def test_buyer_quit_auction(self):
        # buyer not in auction quit
        request = {"op":config.BUYER_QUIT_AUCTION, "username":"buyer3","auction_id":"1"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertFalse(js["success"])
        self.assertTrue("not in auction" in js["message"])

        # successful quit
        request = {"op":config.BUYER_QUIT_AUCTION, "username":"buyer2","auction_id":"1"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertTrue(js["success"])

        # auction already started
        self.sm.auctions[0]["started"] = True
        request = {"op":config.BUYER_QUIT_AUCTION, "username":"buyer1","auction_id":"1"}
        response = self.sm.apply(request)
        js = json.loads(response.json)
        self.assertFalse(js["success"])
        self.assertTrue("has started or finished" in js["message"])




if __name__ == "__main__":
    unittest.main()
