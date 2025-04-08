# Tera Term UI Development

## Overview

**App Version:** `0.9.0` | **Python Version:** `3.12.9` | **Tesseract Version:** `5.5.0` | **C Compiler:** `MSVC (14.3)` | **Inno Setup:** `6.4.2`

This repository contains the development environment and source code for a GUI automation tool designed specifically for interaction with Tera Term (compatible with versions 4 and 5). The main focus is on refining the user interface (UI), enhancing performance, and ensuring smooth interaction.
An application designed to automate and streamline the class enrollment process for the University of Puerto Rico at Bayamón through Tera Term, featuring an intuitive and user-friendly interface.

---

## What is Tera Term?
Not to be confused with our app `Tera Term UI`. Tera Term is a terminal emulator program, in which University of Puerto Rico at Bayamón (among others) relies on for their SIS, you connect to their server via SSH and you enroll the classes through this system

---

## Setup Environment

**Note:** This setup is intended to be executed immediately after cloning the repository.

A `setup.py` script is provided to automate:
- Creation of the virtual environment.
- Installation of necessary dependencies.
- Organization of project directories and files.

### Manual Extraction (Optional)
For manual interaction with the `Tesseract-OCR.7z` archive, download and install [7-Zip](https://www.7-zip.org/).

---

## Tesseract OCR

[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) is integrated into this project for Optical Character Recognition (OCR), enabling:
- Capturing and analyzing screenshots from Tera Term.
- Identifying errors or user input validation issues.
- Displaying real-time error messages within the application.

**Key Use Case:**
- Validating sensitive input like Social Security Numbers (SSNs) by interpreting error messages directly from Tera Term.
- Validating whether the classes that the user tried to enroll/drop were done succesfully, if there were any errors it identifies them, shows it to the user and it will perform any rollbacks if necessary

---

## GUI Framework

The GUI utilizes [CustomTkinter](https://customtkinter.tomschimansky.com), a modern variant of Tkinter, offering enhanced aesthetics and versatility. Due to performance limitations and incomplete functionalities, significant customizations and optimizations have been implemented within the following key modules:

- `ctkmessagebox.py`, `ctk_input_dialog.py`, `ctk_frame.py`, `ctk_scrollable_frame.py`, `ctk_tabview.py`, `ctk_toplevel.py`, `ctk_textbox.py`, `ctk_scrollbar.py`, `ctk_button.py`, `ctk_checkbox.py`, `ctk_radiobutton.py`, `ctk_switch.py`, `ctk_combobox.py`, `ctk_optionmenu.py`, `appearance_mode_tracker.py`, `dropdown_menu.py`, `scaling_tracker.py`, `scaling_base_class.py`, `ctk_base_class.py`, `ctk_canvas.py`, `ctk_image.py`, `ctk_font.py`, `ctk_tk.py`, `theme_manager.py`, and `draw_engine.py`.

Refer to the following resources for more details:
- [CustomTkinter GitHub](https://github.com/TomSchimansky/CustomTkinter)
- [Official Documentation](https://customtkinter.tomschimansky.com)

---

## Installation and Portable Modes

This application can be used in two distinct modes:

### Portable Mode

Run directly from the executable without needing installation, suitable for USB drives or temporary environments.

### Installation Mode (Inno Setup)

The installer version is created using [Inno Setup](https://jrsoftware.org/isinfo.php), packaging Tera Term directly within the installer for convenience.

- Provides easy integration and configuration.
- Ensures a consistent deployment environment.

Visit the [Inno Setup website](https://jrsoftware.org/isinfo.php) for additional details.

---

## Converting `.py` to `.exe`

To build the executable application, the [Nuitka](https://github.com/Nuitka/Nuitka) library is utilized. Nuitka converts Python code into optimized C code, subsequently compiling it into a standalone executable.

### Requirements:
- MSVC compiler (included in Visual Studio Build Tools).
- Windows 10/11 SDK.

### Compilation:
Run `ExecutableScript.bat` to initiate the build process.

**Performance Note:**
- Link-Time Optimization (LTO) significantly enhances performance but increases build times. Disable LTO for rapid test builds.

---

## Performance and Optimization

While the application is largely feature-complete, ongoing optimization efforts are addressing occasional sluggishness to enhance responsiveness in both UI Automation tasks and the graphical user interface itself.

### Codebase Improvement
The existing codebase is primarily centralized within a single file and class, resulting in a challenging and messy structure. Future improvements should include re-architecting and modularizing the codebase, dividing functionalities into clearly defined, maintainable components.
