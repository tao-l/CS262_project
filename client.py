from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtWidgets import QMainWindow, QLabel, QPushButton, QLineEdit
from PyQt6.QtGui import QFont

from buyer import Buyer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setCentralWidget( LoginPage(self) )
    
    def login(self, username, type):
        if type == "buyer":
            buyer = Buyer(username)
            self.setCentralWidget(buyer.ui)
        elif type == "seller":
            print("Seller login")


class LoginPage(QWidget):
    def __init__(self, root=None):
        super().__init__()
        self.root = root
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Username:"))
        self.line_edit = QLineEdit()
        layout.addWidget(self.line_edit)
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
        username = self.line_edit.text()
        self.root.login(username, "buyer")
        
    def seller_button_clicked(self):
        username = self.line_edit.text()
        self.root.login(username, "seller")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()