from PyQt6.QtWidgets import ( QApplication, QMainWindow,
    QMessageBox, QTextEdit, QListWidgetItem, QMenuBar,
    QTabWidget, QVBoxLayout, QWidget, QFileDialog, 
    QListWidget, QDialog, QPushButton, QPlainTextEdit, QProgressDialog
    )
from PyQt6.QtWebEngineWidgets import QWebEngineView  # For HTML rendering
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QEvent
import sys
import os
import extract_msg
import re

# pip install PyQt6-WebEngine PyQt6 extract-msg

application_name = "MSG Viewer"

replacement = str.maketrans({'<': '&lt;', '>': '&gt;'})  # Proper HTML escaping

icon_file = "app_icon.ico"

# --- Functions ---
def check_folder_path(folder_location):
    """Ensure the folder exists, create it if it doesn’t."""
    if not os.path.isdir(folder_location):
        os.makedirs(folder_location)
    return f"Path {folder_location} now exists."

def sanitize_name(name):
    """Sanitize a string to keep only letters, numbers, and basic punctuation; replace spaces with underscores."""
    try:
        if not name:
            return "Untitled"
        name = name.strip().replace(" ", "_")
        sanitized = re.sub(r'[^\w.,-]', '', name).strip('_')
        return sanitized if sanitized else "Unnamed"    
    except Exception as e:
        QMessageBox.critical(None, f"Error while cleaning subject name: {e}")

def extract_attachments(email_msg):
    try:
        """Extract attachments into memory and return message content with metadata."""
        attachment_info = {}
        saved_count = 0
        for attachment in email_msg.attachments:
            if not attachment.contentId:
                attach_name = attachment.longFilename or attachment.shortFilename or f"Unnamed_Attachment_{saved_count}"
                sanitized_attach_name = sanitize_name(attach_name)
                attachment_info[sanitized_attach_name] = (attachment, attachment.data)
                saved_count += 1

        line_break = "<br>" if email_msg.htmlBody else "\n"
        sender = email_msg.sender or "Unknown Sender"
        sender = sender.translate(replacement)
        to = ", ".join(recipient.formatted for recipient in email_msg.recipients) or "Unknown Recipient"
        to = to.translate(replacement)
        metadata = (
            f"From: {sender}{line_break}"
            f"To: {to}{line_break}"
            f"Subject: {email_msg.subject}{line_break}"
        )
        cc = ", ".join(recipient.email for recipient in email_msg.recipients if recipient.type == "cc")
        if cc:
            metadata += f"CC: {cc}{line_break}"
        bcc = ", ".join(recipient.email for recipient in email_msg.recipients if recipient.type == "bcc")
        if bcc:
            metadata += f"BCC: {bcc}{line_break}"
        date_str = email_msg.date.strftime("%d. %b %Y %H:%M")
        metadata += f"Date: {date_str}{line_break}{'_' * 65}{line_break}"

        attachments_list = ""
        if saved_count > 0:
            attachments_list = f"List of email attachments:{line_break}"
            for attach_name in attachment_info.keys():
                attachments_list += f"- {attach_name}{line_break}"
            attachments_list += f"{'_' * 65}{line_break}"

        message_content = email_msg.htmlBody.decode('utf-8') if email_msg.htmlBody else email_msg.body if email_msg.body else "No content available."
        full_content = metadata + attachments_list + message_content

        return full_content, saved_count, attachment_info
    except Exception as e:
        QMessageBox.critical(None, f"Error exporting attachment: {e}")

def batch_extract_emails(folder_path, parent=None):
    """Extract all .msg files from a folder to Downloads/exported_emails with progress feedback."""
    try:
        downloads_dir = os.path.expanduser("~/Downloads")
        export_base = os.path.join(downloads_dir, "exported_emails")
        check_folder_path(export_base)

        # Collect all .msg files
        msg_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(".msg"):
                    msg_files.append(os.path.join(root, file))

        if not msg_files:
            QMessageBox.information(parent, "Batch Export", "No .msg files found in the selected folder.")
            return

        total_files = len(msg_files)
        success_count = 0
        failed_files = []

        # Single progress dialog for both progress and result
        progress = QProgressDialog("Exporting emails...", "Cancel", 0, total_files, parent)
        progress.setWindowTitle("Batch Export Progress")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)  # Keep open until explicitly closed


        def process_next_email(index=0):
            nonlocal success_count, failed_files
            if progress.wasCanceled() or index >= total_files:
                # Update the dialog with final result
                message = f"Batch export completed!\n\nSuccessfully exported: {success_count}/{total_files} files\n"
                if failed_files:
                    message += "Failed files:\n" + "\n".join(f"- {os.path.basename(f)}" for f in failed_files[:5])
                    if len(failed_files) > 5:
                        message += f"\n...and {len(failed_files) - 5} more"
                message += f"\nExport location: {export_base}"
                progress.setLabelText(message)
                progress.setRange(0, 100)  # Switch to percentage
                progress.setValue(100)  # Indicate completion
                progress.setCancelButtonText("Ok")  # Rename Cancel to Ok
                progress.addAction
                progress.canceled.connect(progress.close)  # Close on Ok
                return

            progress.setValue(index)
            progress.setLabelText(f"Exporting {os.path.basename(msg_files[index])} ({index + 1}/{total_files})")

            msg_path = msg_files[index]
            try:
                msg = extract_msg.Message(msg_path)
                subject_folder = os.path.join(export_base, sanitize_name(msg.subject))
                check_folder_path(subject_folder)
                content, saved_count, attachment_info = extract_attachments(msg)
                for attach_name, (attachment, data) in attachment_info.items():
                    attach_path = os.path.join(subject_folder, sanitize_name(attach_name))
                    with open(attach_path, 'wb') as f:
                        f.write(data)
                pdf_path = os.path.join(subject_folder, f"aMSG-{sanitize_name(msg.subject)}.pdf")

                # Create hidden QWebEngineView
                temp_view = QWebEngineView()
                temp_view.setVisible(False)
                temp_view.setHtml(content if msg.htmlBody else f"<pre>{content}</pre>")

                def on_load_finished(ok):
                    if ok:
                        def on_pdf_finished(success):
                            nonlocal success_count, failed_files
                            if success:
                                success_count += 1
                                print(f"Extracted {os.path.basename(msg_path)} to {subject_folder}")
                            else:
                                failed_files.append(msg_path)
                                print(f"Failed to export PDF for {os.path.basename(msg_path)}")
                            temp_view.deleteLater()
                            process_next_email(index + 1)
                        temp_view.page().printToPdf(pdf_path)
                        temp_view.page().pdfPrintingFinished.connect(on_pdf_finished)
                    else:
                        failed_files.append(msg_path)
                        print(f"Failed to load HTML for {os.path.basename(msg_path)}")
                        temp_view.deleteLater()
                        process_next_email(index + 1)

                temp_view.loadFinished.connect(on_load_finished)

            except Exception as e:
                failed_files.append(msg_path)
                print(f"Error extracting {msg_path}: {e}")
                process_next_email(index + 1)

        # Start processing
        process_next_email(0)

    except Exception as e:
        QMessageBox.critical(parent, "Batch Export Error", f"Error during batch export: {e}")
        print(f"Batch export error: {e}")

# --- Attachment Dialog ---
class AttachmentDialog(QDialog):
    def __init__(self, attachment_info, subject, parent=None):
        super().__init__(parent)
        self.attachment_info = attachment_info
        self.subject = subject
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Attachments")
        self.setGeometry(100, 100, 400, 300)
        layout = QVBoxLayout(self)

        self.attachments_list = QListWidget(self)
        for attach_name, (attachment, data) in self.attachment_info.items():
            item = QListWidgetItem(attach_name)
            item.setData(Qt.ItemDataRole.UserRole, (attachment, data))
            self.attachments_list.addItem(item)
        self.attachments_list.itemDoubleClicked.connect(self.export_attachment)
        layout.addWidget(self.attachments_list)

        self.export_all_btn = QPushButton("Export All", self)
        self.export_all_btn.clicked.connect(self.export_all_attachments)
        layout.addWidget(self.export_all_btn)

        self.setLayout(layout)

    def export_attachment(self, item):
        attachment, data = item.data(Qt.ItemDataRole.UserRole)
        attach_name = item.text()
        dest_file, _ = QFileDialog.getSaveFileName(self, "Save Attachment", attach_name, "All Files (*)")
        if dest_file:
            try:
                with open(dest_file, 'wb') as f:
                    f.write(data)
                msg_box = QMessageBox()
                msg_box.setWindowTitle("Export Result")
                msg_box.setText(f"Attachment '{attach_name}' exported successfully to:\n{dest_file}")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Open)
                msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
                result = msg_box.exec()

                if result == QMessageBox.StandardButton.Open:
                    os.startfile(dest_file) if os.name == 'nt' else os.system(f"open {dest_file}" if sys.platform == "darwin" else f"xdg-open {dest_file}")
                print(f"Attachment exported to {dest_file}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Error exporting attachment '{attach_name}':\n{str(e)}")
                print(f"Error exporting attachment: {e}")

    def export_all_attachments(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if folder:
            try:
                subject_folder = os.path.join(folder, sanitize_name(self.subject))
                check_folder_path(subject_folder)
                exported_count = 0
                for attach_name, (attachment, data) in self.attachment_info.items():
                    attach_path = os.path.join(subject_folder, sanitize_name(attach_name))
                    with open(attach_path, 'wb') as f:
                        f.write(data)
                    exported_count += 1
                msg_box = QMessageBox()
                msg_box.setWindowTitle("Export Result")
                msg_box.setText(f"All {exported_count} attachments exported successfully to:\n{subject_folder}")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Open)
                msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
                result = msg_box.exec()

                if result == QMessageBox.StandardButton.Open:
                    os.startfile(subject_folder) if os.name == 'nt' else os.system(f"open {subject_folder}" if sys.platform == "darwin" else f"xdg-open {subject_folder}")
                print(f"All attachments exported to {subject_folder}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Error exporting all attachments:\n{str(e)}")
                print(f"Error exporting all attachments: {e}")

# --- Header Dialog ---
class HeadersDialog(QDialog):
    def __init__(self, header_info=None, parent=None):
        super().__init__(parent)
        self.header = header_info
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Header")
        self.setGeometry(100, 100, 600, 400)
        layout = QVBoxLayout(self)
        
        self.header_text = QPlainTextEdit(self)
        self.header_text.setPlainText(self.header if self.header else "No header available")
        self.header_text.setReadOnly(True)
        layout.addWidget(self.header_text)

        self.copy_btn = QPushButton("Copy to Clipboard", self)
        self.copy_btn.clicked.connect(self.copy_header)
        layout.addWidget(self.copy_btn)

        self.setLayout(layout)

    def copy_header(self):
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.header)
        except Exception as e:
            QMessageBox.critical(self, f"Error copying email header to clipboard: {e}")

# --- GUI Classes ---
class TabContent(QWidget):
    def __init__(self, msg=None, content="", attachment_info=None, header_info=None):
        super().__init__()
        self.msg = msg
        self.content = content
        self.attachment_info = attachment_info or {}
        self.header_info = header_info
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        if self.msg and self.msg.htmlBody:
            self.content_area = QWebEngineView(self)
            self.content_area.setHtml(self.content)
        else:
            self.content_area = QTextEdit(self)
            self.content_area.setObjectName("Container")
            self.content_area.setStyleSheet(
                """#Container {
                    background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 #051c2a stop:1 #44315f);
                    border-radius: 5px;
                }"""
            )
            self.content_area.setPlainText(self.content)
            self.content_area.setReadOnly(True)
        layout.addWidget(self.content_area, stretch=1)

        if self.attachment_info:
            self.view_attachments_btn = QPushButton("View Attachments", self)
            self.view_attachments_btn.clicked.connect(self.show_attachments)
            layout.addWidget(self.view_attachments_btn, stretch=0)

        self.setLayout(layout)

    def show_attachments(self):
        dialog = AttachmentDialog(self.attachment_info, self.msg.subject, self)
        dialog.exec()

class AppMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.tabs = QTabWidget(self)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.setCentralWidget(self.tabs)

        self.tabs.tabBar().installEventFilter(self)

        self.setWindowTitle(application_name)
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon(icon_file))

        self.createToolbar()

    def createToolbar(self):
        self.menuBar = QMenuBar()
        self.setMenuBar(self.menuBar)

        self.open_btn = QAction("Open", self)
        self.open_btn.triggered.connect(self.open_file)
        self.open_btn.setStatusTip("Open MSG file")
        self.menuBar.addAction(self.open_btn)

        self.header_btn = QAction("Header", self)
        self.header_btn.triggered.connect(self.show_header)
        self.header_btn.setStatusTip("View email header")
        self.header_btn.setVisible(False)
        self.menuBar.addAction(self.header_btn)

        self.export_btn = QAction("Export", self)
        self.export_btn.setStatusTip("Export email and attachments")
        self.export_btn.triggered.connect(self.export_file)
        self.export_btn.setVisible(False)
        self.menuBar.addAction(self.export_btn)

        self.batch_extract_btn = QAction("Batch Extract", self)
        self.batch_extract_btn.triggered.connect(self.batch_extract)
        self.batch_extract_btn.setStatusTip("Extract all .msg files from a folder")
        self.menuBar.addAction(self.batch_extract_btn)

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

    def show_header(self):
        try:
            current_tab = self.tabs.currentWidget()
            if current_tab and hasattr(current_tab, 'header_info'):
                header_dialog = HeadersDialog(str(current_tab.header_info), self)
                header_dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, f"Error getting headers: {e}")

    def open_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Open MSG File", "", "MSG Files (*.msg);;All Files (*)")
        if file:
            try:
                msg = extract_msg.Message(file)
                content, _, attachment_info = extract_attachments(msg)
                header_info = msg.header if msg.header else "No header available"
                tab_content = TabContent(msg, content, attachment_info, header_info)
                tab_index = self.tabs.addTab(tab_content, os.path.basename(file))
                self.tabs.setCurrentIndex(tab_index)
                self.export_btn.setVisible(True)
                self.header_btn.setVisible(True)
            except Exception as e:
                QMessageBox.critical(self, f"Error opening file: {e}")
                print(f"Error opening file: {e}")

    def export_file(self):
        current_tab = self.tabs.currentWidget()
        if not current_tab or not current_tab.msg:
            return

        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if folder:
            try:
                content, saved_count, attachment_info = extract_attachments(current_tab.msg)
                subject_folder = os.path.join(folder, sanitize_name(current_tab.msg.subject))
                check_folder_path(subject_folder)
                for attach_name, (attachment, data) in attachment_info.items():
                    attach_path = os.path.join(subject_folder, sanitize_name(attach_name))
                    with open(attach_path, 'wb') as f:
                        f.write(data)
                pdf_path = os.path.join(subject_folder, f"aMSG-{sanitize_name(current_tab.msg.subject)}.pdf")
                
                def on_pdf_finished(success):
                    if success:
                        msg_box = QMessageBox(self)
                        msg_box.setWindowTitle("Export Result")
                        msg_box.setText(f"Email and {saved_count} attachments exported successfully to:\n{subject_folder}\nPDF saved as: {os.path.basename(pdf_path)}")
                        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Open)
                        msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
                        result = msg_box.exec()
                        if result == QMessageBox.StandardButton.Open:
                            os.startfile(pdf_path) if os.name == 'nt' else os.system(f"open {pdf_path}" if sys.platform == "darwin" else f"xdg-open {pdf_path}")
                        print(f"Exported email as PDF and {saved_count} attachments to {subject_folder}")
                    else:
                        QMessageBox.critical(self, "Export Error", "Failed to save PDF")

                if isinstance(current_tab.content_area, QWebEngineView):
                    current_tab.content_area.page().printToPdf(pdf_path)
                    current_tab.content_area.page().pdfPrintingFinished.connect(on_pdf_finished)
                else:
                    temp_view = QWebEngineView()
                    temp_view.setHtml(f"<pre>{content}</pre>")
                    temp_view.page().printToPdf(pdf_path)
                    temp_view.page().pdfPrintingFinished.connect(on_pdf_finished)

            except Exception as e:
                QMessageBox.critical(self, f"Error exporting: {e}")
                print(f"Error exporting: {e}")

    def batch_extract(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with MSG Files")
        if folder:
            batch_extract_emails(folder, self)

    def close_tab(self, index):
        try:
            widget = self.tabs.widget(index)
            if widget:
                self.tabs.removeTab(index)
                widget.deleteLater()
        except Exception as e:
            QMessageBox.critical(self, f"Error Closing tab: {e}")

    def on_tab_changed(self, index):
        try:
            current_tab = self.tabs.widget(index)
            self.export_btn.setVisible(bool(current_tab and current_tab.msg))
            self.header_btn.setVisible(bool(current_tab and current_tab.msg))
        except Exception as e:
            QMessageBox.critical(self, f"Error Changing tabs: {e}")

    def eventFilter(self, source, event):
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
    app.setWindowIcon(QIcon(icon_file))
    app_window = AppMainWindow()
    app_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
