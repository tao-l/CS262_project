import auction_pb2 as pb2

import threading
import config


class StateMachine:

    """" The following is the code from Assignemnt 2 """


    def __init__(self):
        #  States/data of the state machine
        #    - a list of all existing accounts/users (identified by their usernames) 
        #    - a dictionary mapping users to the set of messages they received.
        #      Specifically, messages[user_a] is a list of (user, message) pairs
        #      recoding the messages user_a received (and from which user):  
        #          messages[user_a] = [ (user_1, message_1), (user_2, message_2), ..., ] 
        #    - a lock to ensure only one command can be excecued at a time . 
        self.accounts = []
        self.messages = {}
        self.lock = threading.Lock()
    
    
    # We define the functionality of different commands: 
    def create_account(self, request):
        """ Create account with username [request.username].
            Respond error message if the account cannot be created.
            - Input:
                request   :  pb2.ChatRequest
            - Return:
                response  :  pb2.ChatResponse  
        """
        assert self.lock.locked()

        username = request.username
        response = pb2.ChatResponse()

        if len(username) > USERNAME_LIMIT:
            response.status = INVALID_USERNAME
            response.messages.append("Username too long.")
            return response
        
        if username in self.accounts:
            response.status = GENERAL_ERROR
            response.messages.append( f"User [{username}] already exists!  Pick a different username.")
            print("    create_account: fail.")
        else:
            # Add the user to the account list.
            self.accounts.append(username)
            # Initialize the user's message list to be empty.
            self.messages[username] = []
            response.status = SUCCESS
            response.messages.append(f"Account [{username}] created successfully.  Please log in.")
            print("    create_account: success.")
 
        return response


    def check_account(self, request):
        """ Checks whether the account [request.username] exists in e account list. 
            Respond error message if the account cannot be created.
            - Input:
                request   :  pb2.ChatRequest
            - Return:
                response  :  pb2.ChatResponse  
        """
        assert self.lock.locked()

        response = pb2.ChatResponse()
        if request.username in self.accounts:
            response.status = SUCCESS
            response.messages.append( "Account exists." )
        else:
            response.status = ACCOUNT_NOT_EXIST
            response.messages.append( "Account does not exist." )
        
        return response


    def list_account(self, request):

        """ List accounts that match with the wildcard in [request.wildcard].
            Return a list of those accounts in a stream of users.
            - Input:
                request   :  pb2.ChatRequest
            - Return:
                response  :  pb2.ChatResponse  
        """
        assert self.lock.locked()
        
        wildcard = request.wildcard
        response = pb2.ChatResponse()
        for username in self.accounts:
            if fnmatch.fnmatch(username, wildcard):
                response.usernames.append(username)
        return response
    

    def delete_account(self, request):
        """ Delete the account with [request.username].
            All the messages received by this account are discarded (including undelivered ones). 
            - Input:
                request   :  pb2.ChatRequest
            - Return:
                response  :  pb2.ChatResponse  
        """
        assert self.lock.locked()

        username = request.username
        response = pb2.ChatResponse()

        if username not in self.accounts:
            response.status = ACCOUNT_NOT_EXIST
            response.messages.append( f"User [{username}] does not exist!" )
        else:
            # Remove the user from the account list
            self.accounts.remove(username)
            # Remove the user's message list.
            self.messages.pop(username)
            response.status = SUCCESS
            response.messages.append( f"Account [{username}] deleted.  All received messages are discarded." )
        
        return response


    def send_message(self, request):
        """ Send a message from [request.username] to [request.target_name]: 
            - If [request.username] or [request.target_name] does not exist, return error
            - If message is too long, return error
            - Otherwise, update shared_data.messages, return SUCCESS
            - Input:
                request   :  pb2.ChatRequest
            - Return:
                response  :  pb2.ChatResponse  
        """
        assert self.lock.locked()
        
        response = pb2.ChatResponse()
        username = request.username
        target_name = request.target_name
        msg = request.message

        if len(msg) > MESSAGE_LIMIT:
            response.status = MESSAGE_TOO_LONG
            response.messages.append( f"Message longer than {MESSAGE_LIMIT}, cannot be sent!" )
            return response
        
        if username not in self.accounts:
            response.status = ACCOUNT_NOT_EXIST
            response.messages.append( f"Your account [{username}] does not exist!" )
        elif target_name not in self.accounts:
            response.status = ACCOUNT_NOT_EXIST
            response.messages.append( f"Target user [{target_name}] does not exist!" )
        else:
            # add the pair (username, message) to the target user's message list
            self.messages[target_name].append( (username, msg) )
            response.status = SUCCESS
            response.messages.append( "Message sent succesfully." )
        
        return response


    def fetch_message(self, request):
        """ Client fetches message sent to the user [request.username].
            Client specifies a [msg_id] in [request.param_1]: 
            Server tries to return all the messages sent to the user starting from the [msg_id]-th one:   
            - If the client's username does not exist, return error. 
            - If [msg_id] < 1, return error. 
            - If [msg_id] > the number of messages the client received, return NO_ELEMENT
            - Otherwise, return a response with an array of of responses, where each response includes 
                
            Input:
                 request: pb2.ChatRequest
            Return:
                 response: pb2.ChatResponse
                 * for error, response.messages[0] contains error message. 
                 * if success, response.status = SUCCESS, 
                   the messages are in [response.messages]
                   the users who sent those messages are in [response.usernames]
        """
        assert self.lock.locked()

        username = request.username
        msg_id = request.param_1
        response = pb2.ChatResponse() 

        if msg_id < 1:
            response.status = GENERAL_ERROR
            response.messages.append( "Message id < 1" )
            return response
        else: 
            if username not in self.accounts:
                response.status = ACCOUNT_NOT_EXIST
                response.messages.append( f"Your account [{username}] does not exist!" )
                return response

            else:                                
                total_msg = len(self.messages[username])
                if msg_id > total_msg:
                    response.status = NO_ELEMENT
                    response.messages.append( f"Message id {msg_id} > total number of messages {total_msg}" )
                    return response
                
                response.status = SUCCESS
                for i in range(msg_id-1, total_msg):
                    (from_which_user, message) = self.messages[username][i]
                    response.messages.append( message )
                    response.usernames.append( from_which_user )
        
        return response


    """ apply a command to the state machine, return the response
        - Input:
               request   : pb2.ChatRequest
        - Return:
               resposne  : pb2.ChatResponse
    """
    def apply(self, request):
        dispatch = {
            CREATE_ACCOUNT : self.create_account, 
            CHECK_ACCOUNT  : self.check_account, 
            LIST_ACCOUNT   : self.list_account, 
            DELETE_ACCOUNT : self.delete_account, 
            SEND_MESSAGE   : self.send_message, 
            FETCH_MESSAGE  : self.fetch_message
        }

        with self.lock:
            if request.op not in dispatch:
                response = pb2.ChatResponse()
                response.op = request.op
                response.status = OPERATION_NOT_SUPPORTED
                response.messages.append(f"Operation {request.op} is not supported by the server.")
                return response
            else:
                return dispatch[request.op](request)
    


