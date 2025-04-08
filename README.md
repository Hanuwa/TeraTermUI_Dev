# Tera Term UI Dev
Dev Environment for Tera Term UI (Virtualenv)

**App Version:** "0.9.0" | **Python Version:** "3.12.9" | **Tesseract Version:** "5.5.0" | **C Compiler:** "MSVC (14.3)" | **Inno Setup:** "6.4.2"

**Important** modules of "**ctkmessagebox.py, ctk_input_dialog.py, ctk_frame.py, ctk_scrollable_frame.py, ctk_tabview.py, ctk_toplevel.py,
ctk_textbox.py, ctk_scrollbar.py, ctk_button.py, ctk_checkbox.py, ctk_radiobutton.py, ctk_switch.py, ctk_combobox.py, ctk_optionmenu.py, 
appearance_mode_tracker.py, dropdown_menu.py, scaling_tracker.py, scaling_base_class.py, ctk_base_class.py, ctk_canvas.py, 
ctk_image.py, ctk_font.py, ctk_tk.py, theme_manager.py and draw_engine.py**" 
are included here because they have some modifications.

Priorities of the development of the application is working on improving the UI since it's a bit too simple and not polished,
funtionality wise the application is mostly feature-complete but it could use some performance/optimization improvements since
the application sometimes suffers from slowdows which can make it feel sluggish to use. Works on both Tera Term 5 and 4 
which is worth noting because there are some significant changes between the two.

# Setting up the environment
**This tool is only intended to be used right after cloning the project**

To automate the building process, this project includes a "**setup.py**" file that will create the dev environment, download and install anything that is necessary 
and organize the files and folders properly. if you want to interact directly with the"**Tesseract-OCR.7z**" compressed folder you will need to download 7-zip, 
a file archiver and extractor. https://www.7-zip.org/

# Tesseract OCR
This tool is used for OCR scanning, basically reading text from images, the reason we need this is
because we don't have access to the database of the University and to error proof the application for things like
the Social Security Number we have no way of validating that information so what we do is after the action is performed on Tera Term,
we take a screenshot of the result and perform OCR using Tesseract to see if an error occured within Tera Term. 
Now using this tool we can now stop the execution of code and show error message within our app if the user did something wrong. 
https://github.com/UB-Mannheim/tesseract/wiki

# GUI Framework
The whole GUI is made using customtkinter, read wiki to familiarize yourself with it, can work in conjunction with the normal tkinter too.
It is versatile and really good looking but also very incomplete and its performance is lackluster, which is why I have customized it and modified it quite a lot and
https://github.com/TomSchimansky/CustomTkinter & https://customtkinter.tomschimansky.com
      
# Convert from .py to .exe
We convert the application to an executable using Nuitka, which is a library that basically coverts your python code into C then it compiles and bundles your application together
and makes the .py file into an executable **(C compiler required)**, it's a really good tool and it even increases the performance of some tasks. 
Be aware that the application is compiled using LTO,  which is very demanding, for doing test builds make sure to disable it. Also the Window 10/11 SDK is needed.
Run the "**ExecutableScript.bat**" to start the process https://github.com/Nuitka/Nuitka 
