""" The RAFT algorithm: used to maintain a consistent log among the replicas
"""
import logging
logging.basicConfig(level=logging.INFO)

from concurrent import futures
import grpc
import raft_pb2
import raft_pb2_grpc

import threading
import queue
import random

import os
from time import sleep
import config

Follower = 0
Candidate = 1
Leader = 2

class DEBUG:
    def logs_to_string(logs):
        s = []
        for i in range(len(logs)):
            s.append([i, logs[i].term])
        return str(s)


class RaftServiceServicer(raft_pb2_grpc.RaftServiceServicer):

    """" Initialization of a RAFT server:
         - Input:
             replicas    : List of the addresses and ports of all replicas
             my_id       : The id of the current server replica
             apply_queue : Given by the High-layer server. 
                           RAFT server puts to this queue log entries that have been commited.
                           The upper-layer server will pick entires from this queue to execute. 
    """
    def __init__(self, replicas, my_id, apply_queue, need_persistent=True):
        super().__init__()

        self.lock = threading.Lock()
        self.apply_queue = apply_queue  

        ## Persistent states: 
        self.current_term = 0
        self.voted_for = -1
        dummy_command = raft_pb2.Command()
        self.logs = [raft_pb2.LogEntry(term=0, index=0, command=dummy_command)]
        # (index of the first "real" log entry is 1)

        ## Volatile states: 
        self.commit_index = 0  # index of highest log entry known to be committed
        self.last_applied = 0  # index of the highest log entry applied to state machine
        
        self.state = Follower

        ## Set up information for other replicas
        self.my_id = my_id
        self.replicas = replicas
        self.n_replicas = len(replicas)     # number of replicas
        self.replica_stubs = []
        for i in range(self.n_replicas):
            if (i != my_id):
                channel = grpc.insecure_channel(replicas[i].ip_addr + ':' + replicas[i].raft_port)
                s = raft_pb2_grpc.RaftServiceStub(channel)
                self.replica_stubs.append(s)
            else:
                self.replica_stubs.append(None)
        
        # Leader's states: reinitialized after election
        self.match_index = None
        self.next_index = None

        # events: used to notify the main loop
        self.heard_heartbeat = False
        self.grant_vote = False
        self.received_majority_vote = threading.Event()

        ## Deal with persistency:
        #  record whether we need persistency or not 
        self.need_persistent = need_persistent
        #  the file where the persistent states are saved
        if not os.path.exists("./RAFT_records"):
            os.makedirs("./RAFT_records")
        self.filename = f"./RAFT_records/record{self.my_id}"
        if self.need_persistent:
            with self.lock:
                self.retrieve()
    

    """ This function saves the persistent states of the RAFT server
        to disk file [self.filename], if need_persistent = True
        *** Lock must be acquired before calling this function ***
    """
    def save(self): 
        assert self.lock.locked()
        if not self.need_persistent:
            return
        # [persistent] is a gRPC object used to record all the states
        # that need to be saved
        persistent = raft_pb2.Persistent(
                                        current_term = self.current_term, 
                                        voted_for = self.voted_for, 
                                        logs = self.logs
                                    )
        try: 
            with open(self.filename, "wb") as f:
                # use gRPC object's own serializing function
                # to convert this object into a binary string to write to file f
                f.write(persistent.SerializeToString())
        except:
            print("   save() fails\n")
    

    """ This function retrieve the persistent states from disk
        *** Lock must be acquired before calling this function ***
    """
    def retrieve(self):
        assert self.lock.locked()
        if not self.need_persistent:
            return
        # [persistent] is a gRPC object used to record all the states
        # that need to be retrived
        persistent = raft_pb2.Persistent()
        try: 
            with open(self.filename, "rb") as f:
                # use gRPC object's own parsing function to parse from
                # the binary string read from file f
                persistent.ParseFromString(f.read())
        except:
            print("   retrieve() fails.\n")
            return
        # copy the states from [persistent]
        self.current_term = persistent.current_term
        self.voted_for = persistent.voted_for
        self.logs = [x for x in persistent.logs]
        print(f"  Retrieved!  current_term = {self.current_term}, voted_for = {self.voted_for}, log_len = {len(self.logs)}")
    

    """ Get the index of the last entry in the log """
    def get_last_index(self):
        return len(self.logs) - 1
    
    """ Get the term of the last log entry """
    def get_last_term(self):
        return self.logs[self.get_last_index()].term
    

    """ When receiving a new client request, the upper-layer server calls
        this function to try to add the request/command to RAFT's log. 
        RAFT verifies whether this server is the current Leader:
          - if yes, adds the request and replicates it to other RAFT servers. 
          - otherwise, does not add the request
        - Input: 
            command   :  raft_pb2.Command object
        - Return: (index, term, is_leader):
            index     :  index of the command in the log if the command is committed
            term      :  current term
            is_leader :  whether this server is the current Leader.
                         If no, the command is not added to the log. 
    """
    def new_entry(self, command):
        logging.info(f"  RAFT [{self.my_id}] - new entry: " + command.json)   
        with self.lock:
            if self.state != Leader:
                logging.info(f"      RAFT [{self.my_id}]: not leader, cannot add entry")
                return (-1, self.current_term, False)
            
            term = self.current_term
            index = self.get_last_index() + 1
            log_entry = raft_pb2.LogEntry(term=term,
                                          index=index,
                                          command=command)
            self.logs.append( log_entry )
            logging.info(f"  RAFT [{self.my_id}] adds entry {term, index} to log")

            self.save()
            return (index, term, True)
    

    """ Append_entries RPC.  See RAFT paper for details
        - Input:
            request  : pb2.AE_Request object, the request from the RAFT client that calls this RPC
        - Return:
            response : pb2.AE_Response object, RPC response to the client. 
    """
    def rpc_append_entries(self, request, context):
        logging.debug(f"  RAFT [{self.my_id}] - AE - from Leader {request.leader_id},    my state={self.state}")
        self.lock.acquire()
        try:
            response = raft_pb2.AE_Response()
            
            # Step 1: Reply False if term < current_term
            logging.debug(f"     request.term = {request.term}, my current term = {self.current_term}.")
            if request.term < self.current_term:
                response.term = self.current_term
                response.success = False
                return response
            
            if request.term > self.current_term:
                self.convert_to_follower(request.term)
            
            self.heard_heartbeat = True
            last_index = self.get_last_index()

            response.term = self.current_term
            response.success = False

            # print(f"        logs before AE: " + DEBUG.logs_to_string(self.logs))
            # print(f"        comming entries: " + DEBUG.logs_to_string(request.entries))
            # logging.info(f"         prev_log_index = {request.prev_log_index},  prev_log_term = {request.prev_log_term}")

            # Step 2: Reply False if Follower's log doesn't contain an entry at prev_log_index
            #         whose term matches prev_log_term
            #   - case 1: Follower's log is shorter than prev_log_index
            if request.prev_log_index > last_index:
                return response
            #   - case 2: term doesn't match
            if self.logs[request.prev_log_index].term != request.prev_log_term:
                return response
            
            # Step 3: If an existing entry conflicts with a new one (same index but different terms),
            #         Delete the existing entry and all that follow it. 
            i = request.prev_log_index + 1;  j = 0
            while i<=last_index and j<len(request.entries):
                if self.logs[i].term != request.entries[j].term:
                    break
                i+=1; j+=1
            # print("    last_index =", last_index, "   i =", i, "    j =", j)
            self.logs = self.logs[:i]   # keep log[0, ..., i-1]. Delete i and after
            
            # Step 4: Append any new entries not already in the log
            self.logs.extend( request.entries[j:] )

            # Step 5: If leader_commit > commit_index,
            #         set commit_index = min(leader_commit, index of last new entry)
            if request.leader_commit > self.commit_index:
                last_index = self.get_last_index()
                self.commit_index = min(request.leader_commit, last_index)
                # upon comit_index changes, apply logs:
                logging.debug(f"      commit_index = {self.commit_index}" ) 
                threading.Thread(target=self.apply_logs, daemon=True).start()
            
            # logging.info(f"    logs after AE: " + DEBUG.logs_to_string(self.logs))

            response.success = True
            return response
        
        finally:
            self.save()     # current_term and logs might chagne, so we need to save
            self.lock.release()
    

    """ Send append_entries RPC to a RAFT server,
        wait for response, and handle response
        - Input: id      : id of the target RAFT server, 
                 request : append_entries request to send
    """
    def send_append_entries(self, id, request):
        try:
            response = self.replica_stubs[id].rpc_append_entries(request)
        except grpc.RpcError:
            # RPC fails: does nothing and return
            return
        logging.debug(f"    Sent to {id}, term = {request.term}")
        
        with self.lock:
            if (self.state != Leader or request.term != self.current_term
                                     or response.term < self.current_term):
                return
            
            if response.term > self.current_term:
                # If the target server has a newer term, turn myself to a Follower
                self.convert_to_follower(response.term)
                return
            
            if response.success:
                # If success: update next_index[id] and match_index[id]
                new_match_index = request.prev_log_index + len(request.entries)
                logging.debug(f"       Success, match_index[{id}]: {self.match_index[id]} -> {new_match_index}")
                if new_match_index > self.match_index[id]:
                    self.match_index[id] = new_match_index
                self.next_index[id] = self.match_index[id] + 1
            else:
                # Not success: decrement next_index[id] (and retry in the next broadcast)
                self.next_index[id] -= 1
                """  is this safe?  What if multiple threads call send_append_entries(), and then 
                     all decrement self.next_index[id] ?? 
                """
            
            # RAFT paper:
            #   "If   there exists an N such that N > commit_index,
            #         a majority of mathch_index[id] >= N,
            #         and log[N].term == current_term, 
            #    then set commit_index = N"
            N = self.get_last_index()
            while (N > self.commit_index):
                if self.logs[N].term == self.current_term:
                    count = 1
                    for i in range(self.n_replicas):
                        if i != self.my_id and self.match_index[i] >= N:
                            count += 1
                    if count > self.n_replicas // 2:
                        self.commit_index = N
                        # upon comit_index changes, apply logs:
                        logging.debug(f"       commit_index = {N}")
                        threading.Thread(target=self.apply_logs, daemon=True).start()
                        break 
                N -= 1


    """ Broadcast append_entries RPCs to all other RAFT servers
        *** Lock must be acquired before calling this function ***
    """
    def broadcast_append_entries(self):
        logging.debug(f"  RAFT [{self.my_id}] - broadcast AE:")
        assert self.lock.locked()
        if self.state != Leader:
            return
        
        for i in range(self.n_replicas):
            if i != self.my_id:
                request = raft_pb2.AE_Request()
                request.term = self.current_term
                request.leader_id = self.my_id
                request.prev_log_index = self.next_index[i] - 1
                request.prev_log_term = self.logs[request.prev_log_index].term
                request.leader_commit = self.commit_index
                entries = self.logs[self.next_index[i] : ]
                request.entries.extend( entries )  # use extend to deep copy entries to request.entries
                threading.Thread(target = self.send_append_entries, args=(i, request), daemon=True).start()
    

    """ check if candidate's log is as least as up-to-date as mine: 
        *** Lock must be held before calling this function ***
    """
    def is_up_to_date(self, last_log_index, last_log_term):
        assert self.lock.locked
        my_last_index = self.get_last_index()
        my_last_term = self.get_last_term()
        if last_log_term == my_last_term:
            return last_log_index >= my_last_index
        return last_log_term > my_last_term


    """ request_vote RPC handler.
        See RAFT paper for details.
        - Input: request : pb2.RV_Reuqest object
    """
    def rpc_request_vote(self, request, context):
        logging.debug(f"  RAFT [{self.my_id}] - RV - receives from [{request.candidate_id}] with term {request.term}")
        self.lock.acquire()
        try:
            response = raft_pb2.RV_Response()

            if request.term < self.current_term:
                response.term = self.current_term
                response.vote_granted = False
                return response
            
            if request.term > self.current_term:
                self.convert_to_follower(request.term)
            
            response.term = self.current_term
            response.vote_granted = False

            # RAFT paper: if voted_for is null or candidate_id, 
            #             and candidate's log is at least as-up-todate as mine, grant vote
            logging.debug(f"       voted_for = {self.voted_for}")
            if self.voted_for == -1  or  self.voted_for == request.candidate_id:
                if self.is_up_to_date(request.last_log_index, request.last_log_term):
                    response.vote_granted = True
                    self.voted_for = request.candidate_id
                    self.grant_vote = True
                    logging.debug(f"           grant vote to [{request.candidate_id}]")

            return response
        
        finally:
            self.save()   # current_term and voted_for might change, need to save
            self.lock.release()
    
    
    """ Send request_vote RPC to a RAFT server,
        wait for response, and handle response
        - Input: id      : id of the target RAFT server, 
                 request : RV_request
    """
    def send_request_vote(self, id, request):
        logging.debug(f"    RAFT [{self.my_id}] - sending RV from [{self.my_id}] to [{id}] with my term = {request.term}")

        try:
            response = self.replica_stubs[id].rpc_request_vote(request)
        except grpc.RpcError:
            logging.debug(f"       no response from {id}")
            return
        
        with self.lock:
            logging.debug(f"      got response from {id}: vote_granted = {response.vote_granted},  term = {response.term}")
            if (self.state != Candidate  or  request.term != self.current_term
                                         or  response.term < self.current_term):
                return 
            
            if response.term > self.current_term:
                self.convert_to_follower(response.term)
                return
            
            if response.vote_granted:
                self.vote_count += 1
                if self.vote_count == self.n_replicas // 2 + 1:
                    # votes reach majority. Ready to convert to leader. Do this only once. 
                    self.received_majority_vote.set()
    

    """ Broadcast request_vote RPC to all Raft replicas.
        If receive a majority of vote, will set the event to notify the main loop
        *** Lock must be acquired before calling this function ***
    """
    def broadcast_request_vote(self):
        logging.debug(f"  RAFT [{self.my_id, self.state}] - broadcast request vote - current_term = {self.current_term}")
        assert self.lock.locked()
        if self.state != Candidate:
            return
        request = raft_pb2.RV_Request()
        request.term = self.current_term
        request.candidate_id = self.my_id
        request.last_log_index = self.get_last_index()
        request.last_log_term = self.get_last_term()
        for i in range(self.n_replicas):
            if i != self.my_id:
                threading.Thread(target=self.send_request_vote, args=(i, request), daemon=True).start()
    

    """ 'Apply' the committed logs:
        namely, put the committed log entries to apply_queue to notify the upper-level server
    """
    def apply_logs(self):
        with self.lock:
            for i in range(self.last_applied+1, self.commit_index+1):
                logging.info(f"    RAFT [{self.my_id}] puts log entry [{i}] to apply_queue,  commit_index={self.commit_index}")
                self.apply_queue.put(self.logs[i])
                self.last_applied = i
    

    def DEBUG_information(self):
        return (   f"    RAFT [{self.my_id}], state = [{self.state}], "
                 + f"last_applied=[{self.last_applied}], commit_index=[{self.commit_index}], "
                 + f"log length = [{self.get_last_index()}], term=[{self.current_term}]")


    """ Convert the current RAFT server to Follower
        - Input: the new term number
        *** Lock must be acquired before calling this function ***
    """
    def convert_to_follower(self, term):
        assert self.lock.locked
        self.state = Follower
        self.current_term = term
        self.voted_for = -1
        logging.info(self.DEBUG_information())
        logging.info(f"  RAFT [{self.my_id, self.state}] - convert to Follower")
        self.save()    ## Persistent states chagne. Need to save. 
        

    """ Convert the current RAFT server to Candidate
    """
    def convert_to_candidate(self, from_state):
        logging.info(f"  RAFT [{self.my_id}] - convert to Candidate from state {from_state}")
        logging.info(self.DEBUG_information())
        with self.lock:
            # state may change (from Candidate to Follower) before this function is called, 
            # so need to check this case
            if self.state != from_state:
                logging.info(f"       fail to convert because current state = {self.state}")
                return 
            
            self.state = Candidate
            self.reset_events()
            self.current_term += 1
            self.voted_for = self.my_id
            self.vote_count = 1
            
            self.broadcast_request_vote()

            self.save()     ## Persistent states chagne. Need to save.
    
    
    """ (Try to) convert the current RAFT server to Leader
    """
    def convert_to_leader(self):
        with self.lock:
            # state may change (to Follower) before this function is called, 
            # so need to check the state
            if self.state != Candidate:
                return 

            self.state = Leader
            self.reset_events()

            last_log_index = self.get_last_index()
            self.next_index = [last_log_index + 1 for i in range(self.n_replicas)]
            self.match_index = [0 for i in range(self.n_replicas)]

            self.broadcast_append_entries()

            logging.info(self.DEBUG_information())
            logging.info(f"  RAFT [{self.my_id, self.state}] - convert to Leader")


    """ Reset events. 
        *** Lock must be acquired before calling this function ***
    """
    def reset_events(self):
        assert self.lock.locked()
        self.heard_heartbeat = False
        self.grant_vote = False
        self.received_majority_vote.clear()
    

    """ function that returns a randomzied election timeout (in seconds)"""
    def get_random_election_timeout_second(self):
        return random.randint(config.election_timeout_lower_bound,
                              config.election_timeout_upper_bound) / 1000
    

    """ Main loop of RAFT server """
    def main_loop(self):
        print(f"  RAFT [{self.my_id}] main loop starts.")
        
        while True:
            state = self.state
            
            if state == Leader:
                sleep(config.leader_broadcast_interval / 1000)
                # sleep(0.5)
                # At this point, the state of the server may already change (to Follower).
                with self.lock:
                    if self.state == Leader:
                        self.broadcast_append_entries()

            elif state == Follower:
                sleep( self.get_random_election_timeout_second() )
                logging.debug(f"     heartbeat = {self.heard_heartbeat}")
                with self.lock:
                    to_convert_to_candidate =  (not self.heard_heartbeat) and (not self.grant_vote)
                    self.heard_heartbeat = False
                    self.grant_vote = False
                if to_convert_to_candidate:
                    self.convert_to_candidate(state)
            
            elif state == Candidate:
                if self.received_majority_vote.wait( self.get_random_election_timeout_second() ): 
                    # received majority vote, can convert to leader
                    self.convert_to_leader()
                else:
                    # Didn't receive enough votes, convert to candidate again. 
                    # If self.state already become Follower (which is different from state),
                    # then convert_to_candidate will directly return 
                    self.convert_to_candidate(state)
    

    """ Customized start of RAFT server"""
    def my_start(self):
        # Start the RPC server
        my_ip_addr = self.replicas[self.my_id].ip_addr
        raft_port = self.replicas[self.my_id].raft_port
        rpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=128))
        raft_pb2_grpc.add_RaftServiceServicer_to_server(self, rpc_server)
        rpc_server.add_insecure_port(my_ip_addr + ":" + raft_port)
        rpc_server.start()   # calls the gRPC start() function 
        print(f"  RAFT [{self.my_id}] RPC server starts at {my_ip_addr}:{raft_port}")
        threading.Thread(target=rpc_server.wait_for_termination, daemon=True).start()
        
        # Start the main loop
        threading.Thread(target=self.main_loop, daemon=True).start()

