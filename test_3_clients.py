
import logging

from PyQt6.QtWidgets import QApplication

from client import MainWindow

if __name__ == "__main__":
    app = QApplication([])
    w1 = MainWindow()
    w1.show()
    w2 = MainWindow()
    w2.show()
    w3 = MainWindow()
    w3.show()
    app.exec()