from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QTextDocument, QImage
from PyQt6.QtCore import QMarginsF
from PyQt6.QtWidgets import QApplication,QMainWindow
import extract_msg
import re
import sys
import os
import base64

application_name = "MSG Viewer"
replacement = str.maketrans({'<': '&lt;', '>': '&gt;'})  # Proper HTML escaping

# --- Functions ---
def check_folder_path(folder_location):
    """
    Ensure only a folder is created from the given path.
    If the path includes a filename, remove the file and create only the folder structure.
    """
    try:
        if os.path.exists(folder_location):
            return f"Path {folder_location} already exists."
        # Extract directory path (remove filename if present)
        folder_path = folder_location
        if os.path.splitext(folder_location)[1]:  # Checks if there's a file extension
            folder_path = os.path.dirname(folder_location)  # Get only the folder path
        # Ensure the directory exists
        os.makedirs(folder_path, exist_ok=True)
        return f"Path {folder_path} now exists."
    except Exception as err:
        print(f'Error checking file path: {folder_location} - {err}')

def sanitize_name(name):
    """
    Sanitize a string to keep only letters, numbers, and basic punctuation; 
    replace spaces with underscores.
    """
    try:
        if not name:
            return "Untitled"
        name = name.strip().replace(" ", "_")
        sanitized = re.sub(r'[^\w.,-]', '', name).strip('_')
        return sanitized if sanitized else "Unnamed"
    except Exception as e:
        print(f"Error while cleaning subject name: {e}")
        return "Unnamed"

def clean_html_colors(html_content):
    """ Convert invalid color formats to standard hex codes """
    # Convert `rgb(r, g, b)` to `#RRGGBB`
    def rgb_to_hex(match):
        r, g, b = map(int, match.groups())
        return f'#{r:02X}{g:02X}{b:02X}'  # Convert to uppercase hex (e.g., #FFFFFF)

    html_content = re.sub(r'rgb\(\s*(\d+),\s*(\d+),\s*(\d+)\s*\)', rgb_to_hex, html_content)

    # Replace any remaining invalid colors (like #rgba) with black
    html_content = re.sub(r'#rgba\b', '#000000', html_content)

    return html_content


def extract_images(msg):
    """ Extract images from an MSG file and store them in memory (QImage) """
    image_dict = {}
    for attachment in msg.attachments:
        if attachment.longFilename.lower().endswith(('png', 'jpg', 'jpeg', 'gif')):
            cid = attachment.cid or attachment.longFilename  # Content ID or filename
            image_data = attachment.data  # Raw image data
            
            # Convert image data to Base64 (for embedding)
            base64_data = base64.b64encode(image_data).decode('utf-8')

            # Detect MIME type based on extension
            mime_type = "image/png" if attachment.longFilename.lower().endswith("png") else "image/jpeg"
            image_dict[cid] = f"data:{mime_type};base64,{base64_data}"

    return image_dict

def replace_img_src(html, image_dict):
    """ 
    Replace Content-ID references with Base64 images 
    Some images will be preserved in PDF, those not refferenced by links.    
    """
    for cid, base64_data in image_dict.items():
        html = re.sub(rf'cid:{re.escape(cid)}', base64_data, html)
    return html

def export_to_pdf(content, pdf_path):
    try:
        doc = QTextDocument()
        # Basic sanitization: Remove invalid #rgba-like patterns
        if "<" in content and ">" in content:
            doc.setHtml(content)
        else:
            doc.setPlainText(content)
        
        printer = QPrinter()
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(pdf_path)
        printer.setPageMargins(QMarginsF(10, 10, 10, 10))
        doc.print(printer)
        return True
    except Exception as e:
        print(f"Error in export_to_pdf: {e}")
        return False

source_file = "emails/The latest Infinigate Cloud news and highlights.msg"
pdf_path = "tests/out_pdf.pdf"


## Accessing emails:
def get_msg_content(msg_file):
    """
    By passing .msg file you will get 3 values:
        1. Is the content of body as string - in html format if the message was html
        2. list of attachment names, if any available ( this should ignore embeded images)
        3. Dictionary of all attachments content - accessed by using attachment name
    To get the attachment you can use:
        content = get_msg_content(msg_file)
        content[2][content[1][0]]
    Or if you know the name:
        content[2]['attachment name.pdf']
    """
    msg = extract_msg.Message(msg_file)
    line_break = "<br>" if msg.htmlBody else "\n"
    content = msg.htmlBody if msg.htmlBody else msg.body

    # Extract images and replace CID references
    image_dict = extract_images(msg)
    if msg.htmlBody:
        content = replace_img_src(msg.htmlBody.decode('utf-8', errors='ignore'), image_dict)
    # Get sender, recipients and prepare them to be passed to use
    sender = msg.sender or "Unknown Sender"
    sender = sender.translate(replacement)
    to = ", ".join(recipient.formatted for recipient in msg.recipients) or "Unknown Recipient"
    to = to.translate(replacement)

    metadata = (
        f"From: {sender}{line_break}"
        f"To: {to}{line_break}"
        f"Subject: {msg.subject}{line_break}"
    )

    cc = ", ".join(recipient.email for recipient in msg.recipients if recipient.type == "cc")
    if cc:
        metadata += f"CC: {cc}{line_break}"
    bcc = ", ".join(recipient.email for recipient in msg.recipients if recipient.type == "bcc")
    if bcc:
        metadata += f"BCC: {bcc}{line_break}"
    date_str = msg.date.strftime("%d. %b %Y %H:%M")
    metadata += f"Date: {date_str}{line_break}{'_' * 65}{line_break}"

    # Attachments:
    attachment_info, attachments_list, attachments_sumary = {}, "", []
    saved_count = 0

    for attachment in msg.attachments:
        if not attachment.contentId:
            attach_name = attachment.longFilename or attachment.shortFilename or f"Unnamed_Attachment_{saved_count}"
            sanitized_attach_name = sanitize_name(attach_name)
            attachment_info[sanitized_attach_name] = (attachment, attachment.data)
            saved_count += 1
    if saved_count > 0:
        attachments_list = f"In this email were {saved_count} attachments:{line_break}"
        for attach_name in attachment_info.keys():
            attachments_list += f"- {attach_name}{line_break}"
            attachments_sumary.append(attach_name)
        attachments_list += f"{'_' * 65}{line_break}"
        content = metadata + attachments_list + line_break + clean_html_colors(str(content))
        return content, attachments_sumary, attachment_info
    else:
        content = metadata + line_break + clean_html_colors(str(content))
        return content, [], {}


def msg_to_pdf(msg_file, pdf_path=None):
    msg = extract_msg.Message(msg_file)
    content = get_msg_content(msg_file)

    if pdf_path == None:
        pdf_path = f'exported-msg/msg-{sanitize_name(msg.subject)}.pdf'
    # example how to get an attachment: content[2][content[1][0]]

    check_folder_path(pdf_path)
    # Saves message in .HTML format as the PyQt does not handle links on its own
    with open(pdf_path.replace('.pdf', '.html'),"w") as f:
        f.write(content[0])
    # Saves mesage in .PDF for general use (missing links and web images)
    export_to_pdf(content[0], pdf_path)
    print("Exported")

# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        #content_msg = get_msg_content(source_file)
        #print(get_msg_content(source_file))
        msg_to_pdf(source_file,pdf_path)
        sys.exit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec())
