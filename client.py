import logging

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox
from PyQt6.QtWidgets import QMainWindow, QLabel, QPushButton, QLineEdit
from PyQt6.QtGui import QFont

from buyer import Buyer
from seller import Seller

import grpc
import auction_pb2_grpc

import utils

def get_server_stubs():
    """ Get the RPC service stubs of the platform server replicas """
    # First, get the ip addresses and ports of all replicas from the configuration file
    import config
    replicas  = config.replicas
    n_replicas = len(replicas)
    
    # Then, for each pair of (ip, port), create a stub
    stubs = []
    for i in range(n_replicas):
        channel = grpc.insecure_channel(replicas[i].ip_addr + ':' + replicas[i].client_port)
        s = auction_pb2_grpc.PlatformServiceStub(channel)
        stubs.append(s)
    
    return stubs

def get_my_ip_and_port():
    """ This function is only for demonstration. It should not be used in a real system. 

        It finds the IP address of this computer and finds a port that is not used by other clients.
        When logged in, this IP address and port will be sent to our server for demonstration.  
    """
    # Get the IP address of this computer 
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1)) 
    ip_address = s.getsockname()[0]

    # Read the port numbers used by other client programs from a file
    try: 
        with open("used_port_list.txt", "r") as f:
            used_ports = f.readlines()
    except:
        used_ports = []
    # Searching for a port number that is not used, starting from 40000
    port = 40000
    while True:
        if str(port) + "\n" not in used_ports:
            break
        port += 1
    
    # Return the IP address and the port (in string)
    return (ip_address, str(port))


class MainWindow(QMainWindow):
    """ The main window of the application """
    def __init__(self):
        super().__init__()
        # Upon start, show a login page
        self.setCentralWidget( LoginPage(self) )
    
    def login(self, username, rpc_address, type):
        """ Client tries to login. """

        # Send a login RPC request to the server
        request = { "op" : "LOGIN",
                    "username" : username,
                    "address":rpc_address  }
        stubs = get_server_stubs()
        server_ok, response = utils.rpc_to_server_stubs(request, stubs)

        # If not successful, display an error message and return 
        if not server_ok:
            QMessageBox.critical(self, "", "Cannot login: Server Error!")
            return 
        if response["success"] == False:
            QMessageBox.critical(self, "", "Cannot login: " + response["message"])
            return
        
        # Log in successfully. Display a Buyer window or a Seller window 
        if type == "buyer":
            buyer = Buyer(username, rpc_address, stubs)
            self.setCentralWidget(buyer.ui)
        elif type == "seller":
            seller = Seller(username, rpc_address, stubs)
            self.setCentralWidget(seller.ui)


class LoginPage(QWidget):
    """ The login page UI -- The entry point of the application """
    def __init__(self, root=None):
        super().__init__()
        self.root = root
        layout = QVBoxLayout()

        form = QFormLayout()
        
        self.line_edit = QLineEdit()
        form.addRow(QLabel("Username:"), self.line_edit)

        # Show my IP address and a port number chosen by the application 
        ip_address, port = get_my_ip_and_port()
        self.ip_LE = QLineEdit(ip_address)
        form.addRow(QLabel("My IP address:"), self.ip_LE)
        self.port_LE = QLineEdit(port)
        form.addRow(QLabel("Port:"), self.port_LE)

        layout.addLayout(form)

        layout.addWidget(QLabel("Login (or create account) as:"))
        buyer_button = QPushButton("Buyer")
        buyer_button.clicked.connect(self.buyer_button_clicked)
        seller_button = QPushButton("Seller")
        seller_button.clicked.connect(self.seller_button_clicked)
        
        buttons_row = QHBoxLayout()
        buttons_row.addWidget(buyer_button)
        buttons_row.addWidget(seller_button)

        layout.addLayout(buttons_row)
        self.setLayout(layout)
    
    def buyer_button_clicked(self):
        # Get the input username 
        username = self.line_edit.text()
        # Get the input IP address and port number
        port = self.port_LE.text()
        rpc_address = self.ip_LE.text() + ":" + port
        # Write that port number to the file
        with open("used_port_list.txt", "a") as f:
            f.write(port + "\n")
        # Call the MainWindow object's login() function 
        self.root.login(username, rpc_address, "buyer")
        
    def seller_button_clicked(self):
        # Get the input username 
        username = self.line_edit.text()
        # Get the input IP address and port number
        port = self.port_LE.text()
        rpc_address = self.ip_LE.text() + ":" + port
        # Write that port number to the file
        with open("used_port_list.txt", "a") as f:
            f.write(port + "\n")
        # Call the MainWindow object's login() function 
        self.root.login(username, rpc_address, "seller")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = QApplication([])
    app.setStyleSheet("QLabel{font-size: 18pt;}")
    # custom_font = QFont()
    # custom_font.setWeight(40)
    # QApplication.setFont(custom_font, "QLabel")

    window = MainWindow()
    window.show()
    app.exec()