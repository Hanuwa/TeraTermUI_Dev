# TeraTermUI_Dev
Dev Environment for Tera Term UI

**Important** modules of ctkmessagebox.py, ctk_input_dialog.py and ctk_toplevel.py are included here because they have some modifications,
make sure to also put ctk_table.py on the customtkinter folder.

Priorities of the development of the application is working on improving the UI since it's  a bit too simple and not polished,
funtionalty wise the application is pretty fleshed out.

# Tesseract OCR
Must install this application under a folder within the TeraTermUI.py app called "Tesseract-OCR".
This application is for OCR scanning, basically reading text from images, the reason we need this is
because we don't have access to the database of the University and to error proof the application for things like
the Social Security Number we have no way of validating that information so what we do is after the action is performed on Tera Term,
we take a screenshot of it and perform OCR using tesseract to see if an error occured withing Tera Term. 
Using this we can now stop the execution of code and show error message within our app if the user did something wrong. 
Link: https://digi.bib.uni-mannheim.de/tesseract/

# GUI Framework
The whole GUI is made using customtinter, read wiki to familiarize yourself with it, can work in conjunction with the normal tkinter too.

Links: https://github.com/TomSchimansky/CustomTkinter
       https://customtkinter.tomschimansky.com
      
# Convert from .py to .exe
We convert the application to an executable using Nuitka, is a program that basically compiles your code into C and then bundles your application together,
it's a really good tool and improves booting times of the app drastically https://github.com/Nuitka/Nuitka .

# UPX 
After bundling up our application we use this tool that basically reduces the storage size of the executable at the cost of some extra ram
comsumption.

