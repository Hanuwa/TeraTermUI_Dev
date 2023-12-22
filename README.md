# TeraTermUI_Dev
Dev Environment for Tera Term UI

**Python Version:** "3.11.7"

**Important** modules of "**ctkmessagebox.py, ctk_input_dialog.py, ctk_scrollable_frame.py, ctk_tabview.py and ctk_toplevel.py**" are included here because they have some modifications.

Priorities of the development of the application is working on improving the UI since it's  a bit too simple and not polished,
funtionality wise the application is pretty fleshed out.

# Tesseract OCR
Must install this application under a folder within the TeraTermUI.py app called "Tesseract-OCR".
This application is for OCR scanning, basically reading text from images, the reason we need this is
because we don't have access to the database of the University and to error proof the application for things like
the Social Security Number we have no way of validating that information so what we do is after the action is performed on Tera Term,
we take a screenshot of it and perform OCR using tesseract to see if an error occured within Tera Term. 
Using this we can now stop the execution of code and show error message within our app if the user did something wrong. 
Link: https://github.com/UB-Mannheim/tesseract/wiki

# GUI Framework
The whole GUI is made using customtinter, read wiki to familiarize yourself with it, can work in conjunction with the normal tkinter too.

Links: https://github.com/TomSchimansky/CustomTkinter
       https://customtkinter.tomschimansky.com
      
# Convert from .py to .exe
We convert the application to an executable using Nuitka, is a program that basically compiles your code into C and then bundles your application together,
it's a really good tool and it even increases the performance of some tasks https://github.com/Nuitka/Nuitka .
