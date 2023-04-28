import logging

from concurrent import futures
import grpc
import auction_pb2
import auction_pb2_grpc

import sys
import threading
import queue

from server_state_machine import StateMachine

import raft

import config

""" The server class:
    A server instance contains a state_machine and a RAFT instance, 
    and provide RPC service to the client. 

    Workflow: 
     - The server takes client's request from RPC. 
     - The server then puts this request to a log maintained by the RAFT instance.
       RAFT will replicate this request to other serves. 
     - When a request is committed (replicated on a majority of servers),
       the RAFT instance will notify the server. 
     - Then, the server applies this request to the state_machine,
       and responds to the client. 
"""
class PlatformServiceServicer(auction_pb2_grpc.PlatformServiceServicer):

    """ Customized initialization """
    def my_init(self, replicas, my_id, need_persistent):
        self.replicas = replicas
        self.my_id = my_id

        self.state_machine = StateMachine()   # state_machine
        self.results = dict()   # a dictionary that stores the response for each client request

        self.lock = threading.Lock()

        # a queue of requests that have been commited by RAFT but not applied to the state machine yet. 
        self.apply_queue = queue.Queue()

        # create a RAFT instance
        self.rf = raft.RaftServiceServicer(replicas, my_id, self.apply_queue, need_persistent)
    



    """ This function needs to be  re-written """
    """ This function needs to be  re-written """
    """ This function needs to be  re-written """
    """ This function needs to be  re-written """
    """ This function needs to be  re-written """
    """ This function needs to be  re-written """
    """ The RPC service provided to the client.
        Input:
            request  : a pb2.ChatRequest object
        Return:
            response : a pb2.ChatResponse ojbect
    """
    def rpc_chat_serve(self, request, context):
        logging.info(f" Platform: receives: op={request.op}, username = {request.username}, message = " + request.message)

        # Try to add the request to the log, using RAFT:
        #   RAFT returns the index of the request in the log, 
        #   and whether the current server is the leader 
        (index, _, is_leader) = self.rf.new_entry(request)

        # If this request cannot be added because this server is not the leader, 
        # then return error message to the client
        if not is_leader:
            response = rpc_service_pb2.ChatResponse(op=request.op)
            response.status = config.SERVER_ERROR
            response.messages.append("Server is not leader.")
            return response
        
        # Now, we know that the server was the leader. 
        # Wait until the request is applied to the state machine. 
        #   Create an event to indicate whether this request has been applied or not
        with self.lock:
            assert index not in self.results
            self.results[index] = [ threading.Event(), None ]

        logging.info(f" Chat: waiting for event, index = {index}")
        self.results[index][0].wait()         # wait for the event
        response = self.results[index][1]     # get the response
        logging.info(f" Chat: got event, index = {index}")
        return response
    


    """ A loop that continuously applies requests that have been commited by RAFT
    """
    def apply_request_loop(self):
        while True:
            log_entry = self.apply_queue.get()
            index = log_entry.index
            comand = log_entry.command      # the Command object in raft.proto
            

            """ The following needs to be re-written """
            """ The following needs to be re-written """
            """ The following needs to be re-written """
            """ The following needs to be re-written """
            """ The following needs to be re-written """
            """ The following needs to be re-written """
            """ The following needs to be re-written """
            with self.lock:
                logging.info(f"     Apply request index = {index},  op = {request.op}, username = {request.username}, message = {request.message}")
                # apply the request, and (if needed) record the result and notify the waiting thread. 
                if index not in self.results:
                    # This case means that the request is not initiated by the current server; 
                    # it is replicated from other servers' logs instead.
                    # So, we don't need to record the result and respond to client. 
                    # We just need to apply the request to the state machine
                    logging.info("       replicated")
                    self.state_machine.apply(request)
                else:
                    # Otherwise, we need to record the results and notify the current server
                    logging.info("       need to respond to client")
                    self.results[index][1] = self.state_machine.apply(request)
                    # set the event to notify the waiting thread
                    self.results[index][0].set()
        

    """ Customized start of the RPC server """
    def my_start(self):
        # First, start the RAFT instance
        self.rf.my_start()

        # Then, start the request applying loop
        threading.Thread(target=self.apply_request_loop, daemon=True).start()
        
        # Finally, start the RPC server for the clients
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=128))
        auction_pb2_grpc.add_PlatformServiceServicer_to_server( self, server )
        id = self.my_id
        my_ip_addr = self.replicas[id].ip_addr
        my_client_port = self.replicas[id].client_port
        server.add_insecure_port(my_ip_addr + ":" + my_client_port)
        server.start()
        print(f" ====== Chat server [{id}] starts at {my_ip_addr}:{my_client_port} =======")
        server.wait_for_termination()


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("ERROR: Please use 'python3 server.py id' where id (starting from 0) is the id of the server replica")
        sys.exit()
    
    id = int(sys.argv[1])
    assert 0 <= id < config.n_replicas

    servicer = PlatformServiceServicer()
    servicer.my_init(config.replicas, id, need_persistent=config.need_persistent)
    servicer.my_start()

