import logging

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox
from PyQt6.QtWidgets import QMainWindow, QLabel, QPushButton, QLineEdit
from PyQt6.QtGui import QFont

from buyer import Buyer
from seller import Seller

import utils
import test_toolkit
rpc_to_server = test_toolkit.test_1.rpc_to_server


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
    # Write that port number to the file
    with open("used_port_list.txt", "a") as f:
        f.write(str(port) + "\n")
    
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
        server_ok, response = rpc_to_server(request)

        # If not successful, display an error message and return 
        if not server_ok:
            QMessageBox.critical(self, "", "Cannot login: Server Error!")
            return 
        if response["success"] == False:
            QMessageBox.critical(self, "", "Cannot login: " + response["message"])
            return
        
        # Log in successfully. Display a Buyer window or a Seller window 
        if type == "buyer":
            buyer = Buyer(username, rpc_address)
            self.setCentralWidget(buyer.ui)
        elif type == "seller":
            seller = Seller(username, rpc_address)
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
        rpc_address = self.ip_LE.text() + ":" + self.port_LE.text() 
        # Call the MainWindow object's login() function 
        self.root.login(username, rpc_address, "buyer")
        
    def seller_button_clicked(self):
        # Get the input username 
        username = self.line_edit.text()
        # Get the input IP address and port number
        rpc_address = self.ip_LE.text() + ":" + self.port_LE.text() 
        # Call the MainWindow object's login() function 
        self.root.login(username, rpc_address, "seller")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()