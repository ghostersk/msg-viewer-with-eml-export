View, export and convert .MSG email files without Outlook
=========================================================
- tested on python 3.12.3
- the source project is fork of [JoshData MSG convertor](https://github.com/JoshData/convert-outlook-msg-file) - to convert .msg to .eml (yet to implement)
- the console option to export to .eml is for now commented out for a time.
- it also using [TeamMsgExtractor](https://github.com/TeamMsgExtractor/msg-extractor) to view content of .msg
- I have PyQt6 application what can view (no export to eml) and save to pdf + export attachments using msg-extractor and PyQt6-Webview
- The HTML formated emails have some links not working and embeded images in body can be missing in exported PDF
- But I am working on more light weigh version where webview is not necessary as the .exe file has about 155MB when compiled
- Also now I am trying to use only PyQt6 lybrary to access and export the emails to PDF/HTML
- The bellow is the first version of GUI app (no eml export) it is in: [extra-options/Gui-MSG-Viewer.py`](https://github.com/ghostersk/msg-viewer-with-eml-export/blob/primary/extra-options/Gui-MSG-Viewer.py)

![image](https://github.com/user-attachments/assets/741af835-272e-4e19-ac96-eef4cca6ee0d)


# Install

Install the dependencies with:

    pip install -r requirements.txt

## MSG-EML-Convertor.py use:
```
import msg-eml-convertor
# to export one message:
msg_file="emails/test1.msg" # only msg_file is required.
dest_folder = "../msg-viewer/tests" # this is just file path (no file name)
dest_file = "aaaatest.eml" # this can be just name or with path

print(convert_msg_to_eml(msg_file, dest_folder, dest_file))
# This returns string - new file location and 1 for success.
# if it fails it returns string with error and 0 for fail

# to export all msgs in folder:
src_folder="tests" # this is where to look for .msg, including subfolders
# if dst_folder missing, then it creates folder in src_folder/exported_msgs and saves it all there
dst_folder # if provided will serve as export location ( is created if not exists)

print(convert_all_msg_in_folder(src_folder, dst_folder=None))
# sample output when failed:
(0, [], {'ERR': 'No MSG files found in: /home/user/Projects/msg-viewer/testsSSS'})
# sample output when success:
(1, ['/home/user/Projects/msg-viewer/emails/The latest highlights.msg', '/home/user/Projects/msg-viewer/emails/test1.msg'], {})
```

## Original MSG convertor use:
To use it in your application

    import outlookmsgfile
    eml = outlookmsgfile.load('my_email_sample.msg')
    
The ``load()`` function returns an [EmailMessage](https://docs.python.org/3/library/email.message.html#email.message.EmailMessage) instance.
