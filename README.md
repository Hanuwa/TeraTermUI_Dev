# TeraTermUI_Dev
Dev Environment for Tera Term UI

**Important** modules of ctkmessagebox.py, ctk_input_dialog.py and ctk_toplevel.py are included here because they have some modifications,
make sure to also put ctk_table.py on the customtkinter folder.

Priorities of the development of the application is working on improving the UI since it's  a bit too simple and not polished,
funtionalty wise the application is pretty fleshed out

# Must Install Tesseract OCR
Link: https://digi.bib.uni-mannheim.de/tesseract/

# GUI Framework
The whole GUI is made using customtinter, read wiki to familiarize yourself with it, can work in conjunction with the normal tkinter too

Links: https://github.com/TomSchimansky/CustomTkinter
       https://customtkinter.tomschimansky.com
      
# Convert from .py to .exe
We convert the application to an executable using Nuantic, is a program that basically compiles your code into C and then bundles your application together,
is really good tool and improves booting times of the app drastically https://github.com/Nuitka/Nuitka

# UPX 
After bundling up our application we use this tool that basically reduces the storage size of the executable at the cost of some extra ram
comsumption

