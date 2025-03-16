from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QMenuBar
from PyQt6.QtWidgets import QTabWidget, QVBoxLayout, QWidget, QFileDialog, QTabBar
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QEvent
import os, sys

application_name = "MSG Viewer"

"""
This is simple PyQt6 interface to open text files in tabs.
"""

class TabContent(QWidget):
    def __init__(self):
        super().__init__()
        # Create the text editor for each tab
        self.text_area = QTextEdit(self)
        self.text_area.setObjectName("Container")
        self.text_area.setStyleSheet(
            """#Container {
                background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 #051c2a stop:1 #44315f);
                border-radius: 5px;
            }"""
        )
        layout = QVBoxLayout(self)
        layout.addWidget(self.text_area)
        self.setLayout(layout)
        
    def setText(self, text):
        self.text_area.setPlainText(text)
    
    def getText(self):
        return self.text_area.toPlainText()
    
    def setReadOnly(self, readonly):
        self.text_area.setReadOnly(readonly)
    
    def isReadOnly(self):
        return self.text_area.isReadOnly()


class AppMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Create the tab widget that will hold the tabs
        self.tabs = QTabWidget(self)
        self.tabs.setTabsClosable(True)  # Enable the close button on tabs
        self.tabs.setMovable(True)  # Enable the moving (reordering) of tabs
        self.tabs.tabCloseRequested.connect(self.close_tab)  # Connect to tab close event
        self.tabs.currentChanged.connect(self.on_tab_changed)  # Listen for tab change event
        self.setCentralWidget(self.tabs)

        # Enable middle-click closing for tabs
        self.tabs.tabBar().installEventFilter(self)

        # Set the window title and size
        self.setWindowTitle(application_name)
        self.setGeometry(100, 100, 800, 600)

        # Create the menu bar with toolbar buttons
        self.createToolbar()

    def createToolbar(self):
        # Create a menu bar
        self.menuBar = QMenuBar()
        self.setMenuBar(self.menuBar)

        # Action to open a file
        self.open_btn = QAction("Open", self)
        self.open_btn.triggered.connect(self.open_file)
        self.open_btn.setStatusTip("Open MSG file")
        self.menuBar.addAction(self.open_btn)
        
        # Action to toggle between Edit and Read-Only modes
        self.edit_btn = QAction("ReadOnly", self)  # Default to "ReadOnly"
        self.edit_btn.setStatusTip("Make message read-only")
        self.edit_btn.triggered.connect(self.edit_file)
        self.edit_btn.setVisible(False)
        self.menuBar.addAction(self.edit_btn)

        # Action to save the file
        self.save_btn = QAction("Extract", self)
        self.save_btn.setStatusTip("Save current file")
        self.save_btn.triggered.connect(self.save_file)
        self.save_btn.setVisible(False)
        self.menuBar.addAction(self.save_btn)

        self.menuBar.setStyleSheet("""
            QMenuBar {
                background-color: #9a9c9a;
                border-bottom: 1px solid #000000;
                padding: 2px;
            }
            QMenuBar::item {
                background-color: #292626;
                padding: 5px 10px;
                border: 1px solid transparent;
                margin: 2px;
                font-weight: bold;
            }
            QMenuBar::item:selected {
                background-color: #d0d0d0;
                border: 1px solid #999999;
                color: black;
                border-radius: 3px;
            }
            QMenuBar::item:pressed {
                background-color: #b0b0b0;
            }
        """)

    def open_file(self):
        # Open a file using a file dialog
        file, _ = QFileDialog.getOpenFileName(
            self, 
            "Open File", 
            "", 
            "All Files (*);;HTML Files (*.html);;Text Files (*.txt)"
        )        
        if file:
            try:
                # Read the content of the file
                with open(file, 'r', encoding="utf-8") as f:
                    file_content = f.read()

                    # Create a new tab
                    tab_content = TabContent()
                    tab_content.setText(file_content)
                    tab_index = self.tabs.addTab(tab_content, os.path.basename(file))
                    self.tabs.setCurrentIndex(tab_index)

                    # Enable save and edit actions
                    self.save_btn.setVisible(True)
                    self.edit_btn.setVisible(True)
                    
                    # Set the editor to Read-Only mode by default
                    tab_content.setReadOnly(True)
                    self.edit_btn.setText("Edit")

            except Exception as e:
                print(f"Error opening file: {e}")

    def edit_file(self):
        # Get the current active tab
        current_tab = self.tabs.currentWidget()

        # Toggle between Edit and ReadOnly modes
        if self.edit_btn.text() == "Edit":
            current_tab.setReadOnly(False)  # Allow editing
            self.edit_btn.setText("ReadOnly")
            self.edit_btn.setStatusTip("Make message read-only")
        else:
            current_tab.setReadOnly(True)  # Make read-only
            self.edit_btn.setText("Edit")
            self.edit_btn.setStatusTip("Allows Editing of the message")

    def save_file(self):
        # Get the current active tab
        current_tab = self.tabs.currentWidget()

        # Open a file dialog to save the file
        file, _ = QFileDialog.getSaveFileName(
            self, 
            "Save File", 
            "", 
            "All Files (*);;HTML Files (*.html);;Text Files (*.txt)"
        )
        if file:
            try:
                # Save the content of the text area to the file
                with open(file, 'w', encoding="utf-8") as f:
                    f.write(current_tab.getText())
                    self.setWindowTitle(f"{application_name} - {os.path.basename(file)}")
            except Exception as e:
                print(f"Error saving file: {e}")

    def close_tab(self, index):
        # This function will be triggered when a user clicks on the "X" button of a tab
        widget = self.tabs.widget(index)
        if widget:
            self.tabs.removeTab(index)
            widget.deleteLater()  # Free up the memory of the widget

    def on_tab_changed(self, index):
        # This function is called when the user switches between tabs
        current_tab = self.tabs.widget(index)
        if current_tab:
            # Set the "Edit/ReadOnly" button text based on the current tab's state
            if current_tab.isReadOnly():
                self.edit_btn.setText("Edit")
                self.edit_btn.setStatusTip("Allows Editing of the message")
            else:
                self.edit_btn.setText("ReadOnly")
                self.edit_btn.setStatusTip("Make message read-only")

    def eventFilter(self, source, event):
        # Listen for middle mouse button clicks to close tabs
        if source == self.tabs.tabBar() and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.MiddleButton:
                index = self.tabs.tabBar().tabAt(event.pos())
                if index != -1:
                    self.tabs.removeTab(index)
                return True
        return super().eventFilter(source, event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")    
    app_window = AppMainWindow()
    app_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
