# PROGRAM NAME - Tera Term UI

# PROGRAMMER - Armando Del Valle Tejada

# DESCRIPTION - Controls The application called Tera Term through a GUI interface to make the process of
# enrolling classes for the university of Puerto Rico at Bayamon easier

# DATE - Started 1/1/23, Current Build v0.9.0 - 5/3/23

# BUGS - The implementation of pytesseract could be improved, it sometimes fails to read the screen properly,
# depends a lot on the user's system and takes a bit time to process.
# Application sometimes feels sluggish/slow to use, could use some efficiency/performance improvements.
# The grid of the UI interface and placement of widgets could use some work.

# FUTURE PLANS: Display more information in the app itself, which will make the app less reliant on Tera Term, like
# when you search for classes it would be nice if they appear on this app

import customtkinter
import tkinter as tk
from tkinter import *
import webbrowser
import socket
from contextlib import closing
from tkinter import filedialog
import gc
import pyautogui
import requests
import win32gui
import pygetwindow as gw
from collections import deque
from customtkinter import ctktable
from CTkToolTip import CTkToolTip
from CTkMessagebox import CTkMessagebox
from pywinauto.application import Application
from pywinauto.keyboard import send_keys
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from filelock import FileLock, Timeout
from datetime import datetime
import json
import subprocess
import pyzipper
import pytesseract
import sqlite3
import ctypes
import winsound
import threading
from PIL import Image
import sys
import cv2
import numpy as np
import rsa
import psutil
import time
import re
import os

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")


class TeraTermUI(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Tera Term UI")
        # determines screen size to put application in the middle of the screen
        width = 860
        height = 480
        scaling_factor = self.tk.call("tk", "scaling")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width * scaling_factor) / 2
        y = (screen_height - height * scaling_factor) / 2
        self.geometry(f"{width}x{height}+{int(x) + 175}+{int(y + 50)}")

        # creates a thread separate from the main application for check_idle and to monitor cpu usage
        self.last_activity = time.time()
        self.is_running = True
        self.stop_check_idle = threading.Event()
        self.cpu_load_history = deque(maxlen=60)
        self.stop_monitor = threading.Event()
        self.monitor_thread = threading.Thread(target=self.cpu_monitor)
        self.SERVICE_ACCOUNT_FILE = "feedback.zip"
        self.SPREADSHEET_ID = '1ffJLgp8p-goOlxC10OFEu0JefBgQDsgEo_suis4k0Pw'
        self.RANGE_NAME = 'Sheet1!A:A'
        self.PASSWORD = 'F_QL^B#O_/r9|Rl0i=x),;!@en|V5qR%W(9;2^+f=lRPcw!+4'
        self.credentials = None
        self.GITHUB_REPO = "https://api.github.com/repos/Hanuwa/TeraTermUI"
        self.USER_APP_VERSION = "0.9.0"
        # self.monitor_thread.start()

        # path for tesseract application
        tesseract_path = os.path.join(os.path.dirname(__file__), "Tesseract-OCR")
        pytesseract.pytesseract.tesseract_cmd = os.path.join(tesseract_path, "tesseract.exe")
        self.tessdata_dir_config = f"--tessdata-dir {os.path.join(tesseract_path, 'tessdata')}"

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="Tera Term UI",
                                                 font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.sidebar_button_1 = customtkinter.CTkButton(self.sidebar_frame, text="     Status",
                                                        image=customtkinter.CTkImage(light_image=
                                                                                     Image.open('images/home.png'),
                                                                                     size=(20, 20)),
                                                        command=self.sidebar_button_event, anchor="w")
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)
        self.sidebar_button_2 = customtkinter.CTkButton(self.sidebar_frame, text="       Help",
                                                        image=customtkinter.CTkImage(light_image=
                                                                                     Image.open('images/setting.png'),
                                                                                     size=(18, 18)),
                                                        command=self.sidebar_button_event2, anchor="w")
        self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="Language, Appearance and \n\n "
                                                                             "UI Scaling:", anchor="w")
        self.scaling_label.grid(row=5, column=0, padx=20, pady=(10, 10))
        self.language_menu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["English", "Español"],
                                                         command=self.change_language_event)
        self.language_menu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame,
                                                                       values=["Dark", "Light", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.set("System")
        self.appearance_mode_optionemenu.grid(row=7, column=0, padx=20, pady=(10, 10))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame,
                                                               values=["90%", "95%", "100%", "105%", "110%"],
                                                               command=self.change_scaling_event)
        self.scaling_optionemenu.set("100%")
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

        # create main entry
        self.introduction = customtkinter.CTkLabel(self, text="UPRB Enrollment Process",
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        self.introduction.grid(row=0, column=1, columnspan=2, padx=(20, 0), pady=(20, 0))
        self.host = customtkinter.CTkLabel(self, text="Host: ")
        self.host.grid(row=2, column=0, columnspan=2, padx=(30, 0), pady=(20, 20))
        self.host_entry = customtkinter.CTkEntry(self, placeholder_text="myhost.example.edu")
        self.host_entry.grid(row=2, column=1, padx=(20, 0), pady=(20, 20))
        self.host_tooltip = CTkToolTip(self.host_entry, message="Enter the name of the server\n of the university")
        self.log_in = customtkinter.CTkButton(self, border_width=2, text="Log-In",
                                              text_color=("gray10", "#DCE4EE"), command=self.login_event_handler)
        self.log_in.grid(row=3, column=1, padx=(20, 0), pady=(20, 20))
        self.intro_box = customtkinter.CTkTextbox(self, height=245, width=400)
        self.intro_box.grid(row=1, column=1, padx=(20, 0), pady=(0, 0))
        # set default values
        self.intro_box.insert("0.0", "Welcome to the Tera Term UI Application!\n\n" + "The purpose of this application"
                              " is to facilitate the process enrolling and dropping classes, "
                              "since Tera Term uses Terminal interface, "
                              "it's hard for new users to use and learn how to navigate and do stuff in "
                              "Tera Term. "
                              "This application has a very nice and clean user interface that most users are "
                              "used to.\n\n" +
                              "There's a few things you should know before using this tool: \n\n" +
                              "The application is very early in development, which means it still got things to work, "
                              "fix and implement. "
                              "Right now, the applications lets you do the essentials like enrolling and dropping "
                              " classes"
                              ", searching for classes and other functionally will be implemented later down the road "
                              " the priority right now is getting the user experience right, everything must looks nice"
                              " and be easy to understand. "
                              + "Everything you input here is stored locally, meaning only you can access the "
                                "information"
                                " so you will not have to worry about securities issues plus for sensitive information "
                                "like the Social Security Number it's encrypted using a asymmetric-key. \n\n" +
                              "Thanks for using our application, for more information, help and to customize your "
                              "experience"
                              " make sure to click the buttons on the sidebar, the application is also open source "
                              "for anyone who is interested in working/seeing the project. \n\n" +
                              "IMPORTANT: DO NOT USE WHILE HAVING ANOTHER INSTANCE OF THE APPLICATION OPENED.")
        self.intro_box.configure(state="disabled", wrap="word", border_spacing=8)

        # (Log-in Screen)
        self.authentication_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.a_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.explanation = customtkinter.CTkLabel(master=self.authentication_frame,
                                                  text="Connected to the server successfully",
                                                  font=customtkinter.CTkFont(size=20, weight="bold"))
        self.uprb_image = customtkinter.CTkImage(light_image=Image.open("images/uprb.jpg"),
                                                 dark_image=Image.open("images/uprb.jpg"),
                                                 size=(300, 100))
        self.uprb_image_grid = customtkinter.CTkButton(self.authentication_frame, text="", image=self.uprb_image,
                                                       command=self.uprb_event, fg_color="transparent", hover=False)
        self.explanation2 = customtkinter.CTkLabel(master=self.authentication_frame, text="Authentication required")
        self.username = customtkinter.CTkLabel(master=self.authentication_frame, text="Username: ")
        self.username_entry = customtkinter.CTkEntry(master=self.authentication_frame)
        self.username_tooltip = CTkToolTip(self.username_entry, message="The university requires this to\n"
                                                                        " enter and access the system")
        self.student = customtkinter.CTkButton(master=self.a_buttons_frame, border_width=2,
                                               text="Next",
                                               text_color=("gray10", "#DCE4EE"), command=self.student_event_handler)
        self.back = customtkinter.CTkButton(master=self.a_buttons_frame, fg_color="transparent", border_width=2,
                                            text="Back",
                                            text_color=("gray10", "#DCE4EE"), command=self.go_back_event)
        self.back_tooltip = CTkToolTip(self.back, message="Go back to the main menu\n"
                                                          "of the application")

        # Student Information
        self.student_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.s_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.explanation3 = customtkinter.CTkLabel(master=self.student_frame, text="Information to enter the System",
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        self.lock = customtkinter.CTkImage(light_image=Image.open("images/lock.png"),
                                           dark_image=Image.open("images/lock.png"),
                                           size=(75, 75))
        self.lock_grid = customtkinter.CTkButton(self.student_frame, text="", image=self.lock,
                                                 command=self.lock_event, fg_color="transparent", hover=False)
        self.ssn = customtkinter.CTkLabel(master=self.student_frame, text="Social Security Number: ")
        self.ssn_entry = customtkinter.CTkEntry(master=self.student_frame, placeholder_text="#########", show="*")
        self.ssn_tooltip = CTkToolTip(self.ssn_entry, message="Required to log-in,\n"
                                                              "information gets encrypted")
        self.code = customtkinter.CTkLabel(master=self.student_frame, text="Code of Personal Information: ")
        self.code_entry = customtkinter.CTkEntry(master=self.student_frame, placeholder_text="####", show="*")
        self.code_tooltip = CTkToolTip(self.code_entry, message="4 digit code included in the\n"
                                                                "pre-enrollment ticket email")
        self.show = customtkinter.CTkSwitch(master=self.student_frame, text="Show?", command=self.show_event,
                                            onvalue="on", offvalue="off")
        self.system = customtkinter.CTkButton(master=self.s_buttons_frame, border_width=2,
                                              text="Enter",
                                              text_color=("gray10", "#DCE4EE"), command=self.tuition_event_handler)
        self.back2 = customtkinter.CTkButton(master=self.s_buttons_frame, fg_color="transparent", border_width=2,
                                             text="Back",
                                             text_color=("gray10", "#DCE4EE"), command=self.go_back_event)
        self.back2_tooltip = CTkToolTip(self.back2, message="Go back to the main menu\n"
                                                            "of the application")

        # Classes
        self.tabview = customtkinter.CTkTabview(self, corner_radius=10)
        self.t_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.enroll_tab = "Enroll/Matricular"
        self.search_tab = "Search/Buscar"
        self.other_tab = "Other/Otros"
        self.tabview.add(self.enroll_tab)
        self.tabview.add(self.search_tab)
        self.tabview.add(self.other_tab)
        # First Tab
        self.explanation4 = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab),
                                                   text="Enroll for Classes: ",
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        self.e_classes = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab), text="Class:")
        self.e_classes_entry = customtkinter.CTkEntry(master=self.tabview.tab(self.enroll_tab))
        self.section = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab), text="Section:")
        self.section_entry = customtkinter.CTkEntry(master=self.tabview.tab(self.enroll_tab))
        self.e_semester = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab), text="Semester:")
        self.e_semester_entry = customtkinter.CTkComboBox(master=self.tabview.tab(self.enroll_tab),
                                                          values=["C23", "C31", "C32", "C33"])
        self.e_semester_entry.set("C31")
        self.register_menu = customtkinter.CTkOptionMenu(master=self.tabview.tab(self.enroll_tab),
                                                         values=["Register", "Drop"])
        self.register_menu.set("Register")
        # Second Tab
        self.explanation5 = customtkinter.CTkLabel(master=self.tabview.tab(self.search_tab),
                                                   text="Search for Classes: ",
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        self.s_classes = customtkinter.CTkLabel(master=self.tabview.tab(self.search_tab), text="Class:")
        self.s_classes_entry = customtkinter.CTkEntry(master=self.tabview.tab(self.search_tab))
        self.s_semester = customtkinter.CTkLabel(master=self.tabview.tab(self.search_tab), text="Semester:")
        self.s_semester_entry = customtkinter.CTkComboBox(master=self.tabview.tab(self.search_tab),
                                                          values=["B91", "B92", "B93", "C01", "C02", "C03", "C11",
                                                                  "C12", "C13", "C21", "C22", "C23", "C31"])
        self.s_semester_entry.set("C31")
        self.show_all = customtkinter.CTkCheckBox(master=self.tabview.tab(self.search_tab), text="Show All?",
                                                  onvalue="on", offvalue="off")
        self.show_all_tooltip = CTkToolTip(self.show_all, message="Display all sections or\n"
                                                                  "only ones with spaces")
        self.back3 = customtkinter.CTkButton(master=self.t_buttons_frame, fg_color="transparent", border_width=2,
                                             text="Back",
                                             text_color=("gray10", "#DCE4EE"), command=self.go_back_event)
        self.back3_tooltip = CTkToolTip(self.back3, message="Go back to the main menu\n"
                                                            "of the application")
        self.submit = customtkinter.CTkButton(master=self.tabview.tab(self.enroll_tab), border_width=2,
                                              text="Submit",
                                              text_color=("gray10", "#DCE4EE"), command=self.submit_event_handler)
        self.search = customtkinter.CTkButton(master=self.tabview.tab(self.search_tab), border_width=2,
                                              text="Search",
                                              text_color=("gray10", "#DCE4EE"), command=self.search_event_handler)
        self.show_classes = customtkinter.CTkButton(master=self.t_buttons_frame, border_width=2,
                                                    text="Show My Classes",
                                                    text_color=("gray10", "#DCE4EE"),
                                                    command=self.my_classes_event)
        self.show_classes_tooltip = CTkToolTip(self.show_classes, message="Shows the classes you are\n "
                                                                          "enrolled in for a \n"
                                                                          "specific semester")
        self.multiple = customtkinter.CTkButton(master=self.t_buttons_frame, fg_color="transparent", border_width=2,
                                                text="Multiple Classes",
                                                text_color=("gray10", "#DCE4EE"),
                                                command=self.multiple_classes_event)
        self.multiple_tooltip = CTkToolTip(self.multiple, message="Enroll Multiple Classes\nat once",
                                           bg_color="blue")
        # Third Tab
        self.explanation6 = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
                                                   text="Option Menu: ",
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        self.menu_intro = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
                                                 text="Select code for the screen\n you want to go to: ")
        self.menu = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab), text="Code:")
        self.menu_entry = customtkinter.CTkComboBox(master=self.tabview.tab(self.other_tab),
                                                    values=["SRM (Main Menu)", "004 (Hold Flags)",
                                                            "1GP (Class Schedule)", "118 (Academic Staticstics)",
                                                            "1VE (Academic Record)", "3DD (Scholarship Payment Record)",
                                                            "409 (Account Balance)", "683 (Academic Evaluation)",
                                                            "1PL (Basic Personal Data)", "4CM (Tuition Calculation)",
                                                            "4SP (Apply for Extension)", "SO (Sign out)"])
        self.menu_semester = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab), text="Semester:")
        self.menu_semester_entry = customtkinter.CTkComboBox(master=self.tabview.tab(self.other_tab),
                                                             values=["B91", "B92", "B93", "C01", "C02", "C03", "C11",
                                                                     "C12", "C13", "C21", "C22", "C23", "C31"])
        self.menu_semester_entry.set("C31")
        self.menu_submit = customtkinter.CTkButton(master=self.tabview.tab(self.other_tab), border_width=2,
                                                   text="Submit", text_color=("gray10", "#DCE4EE"),
                                                   command=self.option_menu_event_handler)
        self.go_next_1VE = customtkinter.CTkButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                                   border_width=2, text="Next Page", text_color=("gray10", "#DCE4EE"),
                                                   command=self.go_next_event_EV1, width=100)
        self.go_next_1GP = customtkinter.CTkButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                                   border_width=2, text="Next Page", text_color=("gray10", "#DCE4EE"),
                                                   command=self.go_next_event_1GP, width=100)
        self.go_next_409 = customtkinter.CTkButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                                   border_width=2, text="Next Page", text_color=("gray10", "#DCE4EE"),
                                                   command=self.go_next_event_409, width=100)
        self.go_next_683 = customtkinter.CTkButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                                   border_width=2, text="Next Page", text_color=("gray10", "#DCE4EE"),
                                                   command=self.go_next_event_683, width=100)
        self.go_next_4CM = customtkinter.CTkButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                                   border_width=2, text="Next Page", text_color=("gray10", "#DCE4EE"),
                                                   command=self.go_next_event_4CM, width=100)

        # Multiple Classes Enrollment
        self.multiple_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.m_button_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.explanation7 = customtkinter.CTkLabel(master=self.multiple_frame,
                                                   text="Enroll Multiple Classes at once:",
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        self.warning = customtkinter.CTkLabel(master=self.multiple_frame, text="*You can only submit once!*")
        self.m_classes_entry = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Class", height=30)
        self.m_section_entry = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Section", height=30)
        self.m_semester_entry = customtkinter.CTkComboBox(master=self.multiple_frame,
                                                          values=["C23", "C31", "C32", "C33"], height=30)
        self.m_semester_entry.set("C31")
        self.m_register_menu = customtkinter.CTkOptionMenu(master=self.multiple_frame, values=["Register", "Drop"],
                                                           height=30)
        self.m_register_menu.set("Choose")
        self.m_add = customtkinter.CTkButton(master=self.m_button_frame, border_width=2, text="+",
                                             text_color=("gray10", "#DCE4EE"), command=self.add_event, height=40,
                                             width=50, hover=True, fg_color="blue")
        self.m_add_tooltip = CTkToolTip(self.m_add, message="Add more classes", resampling=True, bg_color="blue")
        self.m_remove = customtkinter.CTkButton(master=self.m_button_frame, border_width=2, text="-",
                                                text_color=("gray10", "#DCE4EE"), command=self.remove_event,
                                                height=40, width=50, fg_color="red", hover=True, hover_color="darkred")
        self.m_remove_tooltip = CTkToolTip(self.m_remove, message="Remove classes", resampling=True, bg_color="red")
        self.back4 = customtkinter.CTkButton(master=self.m_button_frame, fg_color="transparent", border_width=2,
                                             text="Back", height=40, width=70,
                                             text_color=("gray10", "#DCE4EE"), command=self.go_back_event2)
        self.back4_tooltip = CTkToolTip(self.back4, message="Go back to the previous "
                                                            "\nscreen")
        self.submit_multiple = customtkinter.CTkButton(master=self.m_button_frame, border_width=2,
                                                       text="Submit", text_color=("gray10", "#DCE4EE"),
                                                       command=self.submit_multiple_event_handler, height=40, width=70)

        # Extras
        self.m_classes_entry2 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Class",
                                                       height=30)
        self.m_section_entry2 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Section",
                                                       height=30)
        self.m_semester_entry2 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Semester",
                                                        height=30)
        self.m_register_menu2 = customtkinter.CTkOptionMenu(master=self.multiple_frame, values=["Register", "Drop"],
                                                            height=30)
        self.m_register_menu2.set("Choose")
        self.m_classes_entry3 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Class",
                                                       height=30)
        self.m_section_entry3 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Section",
                                                       height=30)
        self.m_semester_entry3 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Semester",
                                                        height=30)
        self.m_register_menu3 = customtkinter.CTkOptionMenu(master=self.multiple_frame, values=["Register", "Drop"],
                                                            height=30)
        self.m_register_menu3.set("Choose")
        self.m_classes_entry4 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Class",
                                                       height=30)
        self.m_section_entry4 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Section",
                                                       height=30)
        self.m_semester_entry4 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Semester",
                                                        height=30)
        self.m_register_menu4 = customtkinter.CTkOptionMenu(master=self.multiple_frame, values=["Register", "Drop"],
                                                            height=30)
        self.m_register_menu4.set("Choose")
        self.m_classes_entry5 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Class",
                                                       height=30)
        self.m_section_entry5 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Section",
                                                       height=30)
        self.m_semester_entry5 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Semester",
                                                        height=30)
        self.m_register_menu5 = customtkinter.CTkOptionMenu(master=self.multiple_frame, values=["Register", "Drop"],
                                                            height=30)
        self.m_register_menu5.set("Choose")
        self.m_classes_entry6 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Class",
                                                       height=30)
        self.m_section_entry6 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Section",
                                                       height=30)
        self.m_semester_entry6 = customtkinter.CTkEntry(master=self.multiple_frame, placeholder_text="Semester",
                                                        height=30)
        self.m_register_menu6 = customtkinter.CTkOptionMenu(master=self.multiple_frame, values=["Register", "Drop"],
                                                            height=30)
        self.m_register_menu6.set("Choose")
        # Get the current display settings

        # Top level window management, flags and counters
        self.default_semester = "C31"
        self.enrolled_classes_list = {}
        self.dropped_classes_list = {}
        self.check = False
        self.status = None
        self.help = None
        self.error = None
        self.success = None
        self.loading_screen = None
        self.information = None
        self.flag = False
        self.flag2 = False
        self.flag3 = False
        self.flag4 = False
        self.flag5 = False
        self.screenshot_skip = False
        self.error_occurred = False
        self.run_fix = False
        self.submit_feedback_button = True
        self.a_counter = 0
        self.m_counter = 0
        self.e_counter = 0
        # closing event dialog
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        # enables keyboard input events
        self.bind("<Return>", lambda event: self.login_event_handler())
        self.bind("<Escape>", lambda event: self.on_closing())
        # default location of Tera Term
        self.location = "C:/Program Files (x86)/teraterm/ttermpro.exe"
        self.teraterm_file = "C:/Program Files (x86)/teraterm/TERATERM.ini"
        self.original_font = None
        self.edit_teraterm_ini(self.teraterm_file)
        # Database
        appdata_path = os.getenv("APPDATA")
        self.db_path = os.path.join(appdata_path, "TeraTermUI/database.db")
        self.ath = os.path.join(appdata_path, "TeraTermUI/feedback.zip")
        self.authenticate()
        self.connection = sqlite3.connect("database.db")
        self.cursor = self.connection.cursor()
        location = self.cursor.execute("SELECT location FROM user_data WHERE location IS NOT NULL").fetchall()
        host = self.cursor.execute("SELECT host FROM user_data WHERE host IS NOT NULL").fetchall()
        language = self.cursor.execute("SELECT language FROM user_data WHERE language IS NOT NULL").fetchall()
        appearance = self.cursor.execute("SELECT appearance FROM user_data WHERE appearance IS NOT NULL").fetchall()
        scaling = self.cursor.execute("SELECT scaling FROM user_data WHERE scaling IS NOT NULL").fetchall()
        welcome = self.cursor.execute("SELECT welcome FROM user_data WHERE welcome IS NOT NULL").fetchall()
        teraterm_config = self.cursor.execute("SELECT config FROM user_data WHERE config IS NOT NULL").fetchall()
        if host:
            self.host_entry.insert(0, host)
        if location:
            if location[0][0] != self.location:
                self.location = location[0][0]
        if teraterm_config:
            if teraterm_config[0][0] != self.teraterm_file:
                self.teraterm_file = teraterm_config[0][0]
                self.edit_teraterm_ini(self.teraterm_file)
        if language:
            if language[0][0] != "English":
                self.language_menu.set(language[0][0])
                self.change_language_event(lang=language[0][0])
        if appearance:
            if appearance[0][0] != "System":
                self.appearance_mode_optionemenu.set(appearance[0][0])
                self.change_appearance_mode_event(appearance[0][0])
        if scaling:
            if appearance[0][0] != "100%":
                self.scaling_optionemenu.set(scaling[0][0])
                self.change_scaling_event(scaling[0][0])
        if len(welcome) == 0:
            self.sidebar_button_2.configure(state="disabled")

            def show_message_box():
                if self.language_menu.get() == "English":
                    self.show_information_message(375, 250, "Make sure to not interact with Tera Term\n\n"
                                                            " while the application is performing tasks")
                    self.sidebar_button_2.configure(state="normal")
                    self.after(10000, lambda: self.information.destroy())
                if self.language_menu.get() == "Español":
                    self.show_information_message(375, 250, "Asegúrese de no interactuar con Tera Term\n\n"
                                                            "mientras la aplicación está realizando tareas")
                    self.sidebar_button_2.configure(state="normal")
                    self.after(10000, lambda: self.information.destroy())
                if len(welcome) == 0:
                    self.cursor.execute("INSERT INTO user_data (welcome) VALUES (?)", ("Checked",))
                elif len(welcome) == 1:
                    self.cursor.execute("UPDATE user_data SET welcome=?", ("Checked",))
            self.after(5000, show_message_box)

        def update_app():
            lang = self.language_menu.get()
            try:
                latest_version = self.get_latest_release()
                if not self.compare_versions(latest_version, self.USER_APP_VERSION):
                    if lang == "English":
                        msg = CTkMessagebox(master=self, title="Exit",
                                            message="A newer version of the application is available, "
                                                    "would you like to update?",
                                            icon="question",
                                            option_1="Cancel", option_2="No", option_3="Yes", icon_size=(65, 65),
                                            button_color=("#c30101", "#145DA0", "#145DA0"),
                                            hover_color=("darkred", "darkblue", "darkblue"))
                    elif lang == "Español":
                        msg = CTkMessagebox(master=self, title="Salir",
                                            message="Una nueva de versión de la aplicación esta disponible, "
                                                    "¿desea actualizar?",
                                            icon="question",
                                            option_1="Cancelar", option_2="No", option_3="Sí", icon_size=(65, 65),
                                            button_color=("#c30101", "#145DA0", "#145DA0"),
                                            hover_color=("darkred", "darkblue", "darkblue"))
                    response = msg.get()
                    if response == "Yes" or response == "Sí" and self.test_connection(lang):
                        webbrowser.open("https://github.com/Hanuwa/TeraTermUI/releases/latest")
            except requests.exceptions.RequestException as e:
                print(f"Error occurred while fetching latest release information: {e}")
                print("Please check your internet connection and try again.")
        self.after(1500, update_app)

    # function that when the user tries to close the application a confirm dialog opens up
    def on_closing(self):
        lang = self.language_menu.get()
        if lang == "English":
            msg = CTkMessagebox(master=self, title="Exit", message="Are you sure you want to exit the application?"
                                                                   " ""\n\nWARNING: (Tera Term will close)",
                                icon="question",
                                option_1="Cancel", option_2="No", option_3="Yes", icon_size=(65, 65),
                                button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
        elif lang == "Español":
            msg = CTkMessagebox(master=self, title="Salir", message="¿Estás seguro que quieres salir de la aplicación?"
                                                                    " ""\n\nWARNING: (Tera Term va a cerrar)",
                                icon="question",
                                option_1="Cancelar", option_2="No", option_3="Sí", icon_size=(65, 65),
                                button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
        response = msg.get()
        if response == "Yes" or response == "Sí":
            if hasattr(self, 'thread') and self.thread.is_alive():
                self.stop_check_idle.set()
                self.thread.join()
            if self.checkIfProcessRunning("ttermpro") and self.window_exists("uprbay.uprb.edu - Tera Term VT"):
                uprb = Application(backend='uia').connect(title="uprbay.uprb.edu - Tera Term VT", timeout=100)
                uprb.kill(soft=False)
            if self.checkIfProcessRunning("ttermpro") and self.window_exists("Tera Term - [disconnected] VT"):
                subprocess.run(["taskkill", "/f", "/im", "ttermpro.exe"],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.restore_original_font(self.teraterm_file)
            self.save_user_data()
            self.destroy()
            exit(0)

    def tuition_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.tuition_event, args=(task_done,))
        event_thread.start()

    # Enrolling/Searching classes Frame
    def tuition_event(self, task_done):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        lang = self.language_menu.get()
        self.error_occurred = False
        if self.test_connection(lang) and self.check_server():
            if self.checkIfProcessRunning("ttermpro"):
                if not self.screenshot_skip:
                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                    screenshot_thread.start()
                    screenshot_thread.join()
                    text = self.capture_screenshot()
                    if "ACCESO AL SISTEMA" not in text and "Press return" in text:
                        send_keys("{ENTER 3}")
                        self.screenshot_skip = True
                    if "ACCESO AL SISTEMA" not in text and "Press return" not in text:
                        self.error_occurred = True
                        if lang == "English":
                            self.show_error_message(300, 215, "Unknown Error! Please try again")
                        if lang == "Español":
                            self.show_error_message(310, 220, "¡Error Desconocido! Por favor \n"
                                                              "intente de nuevo")
                if not self.error_occurred:
                    try:
                        ssn = int(self.ssn_entry.get().replace(" ", ""))
                        code = int(self.code_entry.get().replace(" ", ""))
                        if re.match("^(?!666|000|9\\d{2})\\d{3}(?!00)\\d{2}(?!0{4})\\d{4}$", str(ssn)) \
                                and len(str(code)) == 4:
                            publicKey1, privateKey1 = rsa.newkeys(1024)
                            publicKey2, privateKey2 = rsa.newkeys(1024)
                            ssnEnc = rsa.encrypt(str(ssn).encode(), publicKey1)
                            codeEnc = rsa.encrypt(str(code).encode(), publicKey2)
                            ctypes.windll.user32.BlockInput(True)
                            uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                            uprb_window.wait('visible', timeout=100)
                            self.uprb.UprbayTeraTermVt.type_keys(rsa.decrypt(ssnEnc, privateKey1).decode())
                            self.uprb.UprbayTeraTermVt.type_keys(rsa.decrypt(codeEnc, privateKey2).decode())
                            send_keys("{ENTER}")
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text = self.capture_screenshot()
                            if "ID NOT ON FILE" in text or "PASS" in text:
                                self.bind("<Return>", lambda event: self.tuition_event_handler())
                                if "PASS" in text:
                                    send_keys("{TAB 2}")
                                if lang == "English":
                                    self.show_error_message(300, 215, "Error! Invalid SSN or Code")
                                if lang == "Español":
                                    self.show_error_message(300, 215, "¡Error! SSN o Código Incorrecto")
                                self.screenshot_skip = True
                            elif "ID NOT ON FILE" not in text or "PASS" not in text:
                                self.set_focus_to_tkinter()
                                self.reset_activity_timer(None)
                                self.start_check_idle_thread()
                                self.tabview.grid(row=0, column=1, padx=(20, 20), pady=(20, 0), sticky="n")
                                self.tabview.tab(self.enroll_tab).grid_columnconfigure(1, weight=2)
                                self.tabview.tab(self.search_tab).grid_columnconfigure(1, weight=2)
                                self.tabview.tab(self.other_tab).grid_columnconfigure(1, weight=2)
                                self.t_buttons_frame.grid(row=2, column=1, padx=(20, 20), pady=(20, 0), sticky="n")
                                self.t_buttons_frame.grid_columnconfigure(2, weight=1)
                                self.explanation4.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
                                if lang == "English":
                                    self.e_classes.grid(row=1, column=1, padx=(41, 0), pady=(0, 0), sticky="w")
                                elif lang == "Español":
                                    self.e_classes.grid(row=1, column=1, padx=(44, 0), pady=(0, 0), sticky="w")
                                self.e_classes_entry.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                                self.section.grid(row=2, column=1, padx=(30, 0), pady=(20, 0), sticky="w")
                                self.section_entry.grid(row=2, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
                                if lang == "English":
                                    self.e_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0), sticky="w")
                                elif lang == "Español":
                                    self.e_semester.grid(row=3, column=1, padx=(21, 0), pady=(20, 0), sticky="w")
                                self.e_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
                                self.register_menu.grid(row=4, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
                                self.submit.grid(row=5, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
                                self.explanation5.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
                                if lang == "English":
                                    self.s_classes.grid(row=1, column=1, padx=(42, 0), pady=(0, 0), sticky="w")
                                elif lang == "Español":
                                    self.s_classes.grid(row=1, column=1, padx=(43, 0), pady=(0, 0), sticky="w")
                                self.s_classes_entry.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                                self.s_semester.grid(row=2, column=1, padx=(20, 0), pady=(20, 0), sticky="w")
                                self.s_semester_entry.grid(row=2, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
                                self.show_all.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
                                self.search.grid(row=4, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
                                self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
                                self.menu_intro.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                                if lang == "English":
                                    self.menu.grid(row=2, column=1, padx=(44, 0), pady=(10, 0), sticky="w")
                                elif lang == "Español":
                                    self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
                                self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
                                self.menu_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0), sticky="w")
                                self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
                                self.menu_submit.grid(row=5, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
                                self.back3.grid(row=4, column=0, padx=(0, 10), pady=(0, 0), sticky="w")
                                self.show_classes.grid(row=4, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                                self.multiple.grid(row=4, column=2, padx=(10, 0), pady=(0, 0), sticky="s")
                                self.student_frame.grid_forget()
                                self.s_buttons_frame.grid_forget()
                                self.ssn_entry.delete(0, "end")
                                self.code_entry.delete(0, "end")
                                self.screenshot_skip = False
                                self.run_fix = True
                                self.unbind("<Return>")
                                del ssn, code, publicKey1, privateKey1, publicKey2, privateKey2, ssnEnc, codeEnc
                                gc.collect()
                        else:
                            self.bind("<Return>", lambda event: self.tuition_event_handler())
                            if lang == "English":
                                self.show_error_message(300, 215, "Error! Invalid SSN or Code")
                            elif lang == "Español":
                                self.show_error_message(300, 215, "¡Error! SSN o Código Incorrecto")
                            self.screenshot_skip = True
                    except ValueError:
                        self.bind("<Return>", lambda event: self.tuition_event_handler())
                        if lang == "English":
                            self.show_error_message(300, 215, "Error! Invalid SSN or Code")
                        elif lang == "Español":
                            self.show_error_message(300, 215, "¡Error! SSN o Código Incorrecto")
                        self.screenshot_skip = True
            else:
                self.bind("<Return>", lambda event: self.tuition_event_handler())
                if lang == "English":
                    self.show_error_message(300, 215, "Error! Tera Term isn't running")
                elif lang == "Español":
                    self.show_error_message(300, 215, "¡Error! Tera Term no esta corriendo")
        ctypes.windll.user32.BlockInput(False)
        block_window.destroy()
        task_done.set()

    def submit_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.submit_event, args=(task_done,))
        event_thread.start()

    # function for registering/dropping classes for the first time
    def submit_event(self, task_done):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        classes = self.e_classes_entry.get().upper().replace(" ", "")
        section = self.section_entry.get().upper().replace(" ", "")
        semester = self.e_semester_entry.get().upper().replace(" ", "")
        choice = self.register_menu.get()
        lang = self.language_menu.get()

        if self.test_connection(lang) and self.check_server():
            if self.checkIfProcessRunning("ttermpro"):
                if (re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE)
                        and re.fullmatch("^[A-Z]{2}1$", section, flags=re.IGNORECASE)
                        and re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE)
                        and (semester == "C23" or semester == "C31" or semester == "C41"
                             or semester == "C32" or semester == "C33")):
                    ctypes.windll.user32.BlockInput(True)
                    uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                    uprb_window.wait('visible', timeout=100)
                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                    send_keys("{ENTER}")
                    self.uprb.UprbayTeraTermVt.type_keys("1S4")
                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                    send_keys("{ENTER}")
                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                    screenshot_thread.start()
                    screenshot_thread.join()
                    text_output = self.capture_screenshot()
                    if "OUTDATED" not in text_output:
                        enrolled_classes = "ENROLLED"
                        count_enroll = text_output.count(enrolled_classes)
                        send_keys("{TAB 2}")
                        for i in range(count_enroll, 0, -1):
                            send_keys("{TAB 2}")
                        if choice == "Register" or choice == "Registra":
                            self.uprb.UprbayTeraTermVt.type_keys("R")
                        elif choice == "Drop" or choice == "Baja":
                            self.uprb.UprbayTeraTermVt.type_keys("D")
                        self.uprb.UprbayTeraTermVt.type_keys(classes)
                        self.uprb.UprbayTeraTermVt.type_keys(section)
                        send_keys("{ENTER}")
                        screenshot_thread = threading.Thread(target=self.capture_screenshot)
                        screenshot_thread.start()
                        screenshot_thread.join()
                        text = self.capture_screenshot()
                        self.reset_activity_timer(None)
                        self.go_next_1VE.configure(state="disabled")
                        self.go_next_1GP.configure(state="disabled")
                        self.go_next_409.configure(state="disabled")
                        self.go_next_683.configure(state="disabled")
                        self.go_next_4CM.configure(state="disabled")
                        if "CONFIRMED" in text or "DROPPED" in text:
                            self.submit.configure(command=self.submit2_event_handler)
                            self.e_classes_entry.delete(0, "end")
                            self.section_entry.delete(0, "end")
                            if choice == "Register" or choice == "Registra":
                                send_keys("{ENTER}")
                                self.e_counter += 1
                                if classes not in self.enrolled_classes_list:
                                    self.enrolled_classes_list[section] = classes
                                elif classes in self.enrolled_classes_list:
                                    del self.enrolled_classes_list[section]
                                if lang == "English":
                                    self.show_success_message(350, 265, "Enrolled class successfully")
                                elif lang == "Español":
                                    self.show_success_message(350, 265, "Clase registrada exitósamente")
                            elif choice == "Drop" or choice == "Baja":
                                if classes not in self.dropped_classes_list:
                                    self.dropped_classes_list[section] = classes
                                elif classes in self.dropped_classes_list:
                                    del self.dropped_classes_list[section]
                                if lang == "English":
                                    self.show_success_message(350, 265, "Dropped class successfully")
                                elif lang == "Español":
                                    self.show_success_message(350, 265, "Clase abandonada exitósamente")
                        else:
                            self.reset_activity_timer(None)
                            self.set_focus_to_tkinter()
                            if lang == "English":
                                self.show_error_message(300, 210, "Error! Unable to enroll class")
                                self.after(2500, self.show_enrollment_error_information)
                            elif lang == "Español":
                                self.show_error_message(320, 210, "¡Error! No se puede matricular la clase")
                                self.after(2500, self.show_enrollment_error_information)
                    else:
                        send_keys("{TAB}")
                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                        self.uprb.UprbayTeraTermVt.type_keys(semester.replace(" ", ""))
                        send_keys("{ENTER}")
                        self.reset_activity_timer(None)
                        self.set_focus_to_tkinter()
                        if lang == "English":
                            self.show_error_message(300, 210, "Error! Unable to enroll class")
                            self.after(2500, self.show_enrollment_error_information)
                        elif lang == "Español":
                            self.show_error_message(320, 210, "¡Error! No se puede matricular la clase")
                            self.after(2500, self.show_enrollment_error_information)
                else:
                    self.reset_activity_timer(None)
                    self.set_focus_to_tkinter()
                    if lang == "English":
                        self.show_error_message(350, 265, "Error! Wrong Class or Section \n\n"
                                                          " or Semester Format")
                    elif lang == "Español":
                        self.show_error_message(350, 265, "¡Error! Formato Incorrecto para Clase o "
                                                          "\n\n Sección o Semestre")
            else:
                if lang == "English":
                    self.show_error_message(300, 215, "Error! Tera Term is disconnected")
                elif lang == "Español":
                    self.show_error_message(300, 215, "¡Error! Tera Term esta desconnectado")
        ctypes.windll.user32.BlockInput(False)
        block_window.destroy()
        task_done.set()

    def submit2_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.submit2_event, args=(task_done,))
        event_thread.start()

    # function for registering/dropping classes after the first time
    def submit2_event(self, task_done):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        choice = self.register_menu.get().replace(" ", "")
        classes = self.e_classes_entry.get().upper().replace(" ", "")
        section = self.section_entry.get().upper().replace(" ", "")
        semester = self.e_semester_entry.get().upper().replace(" ", "")
        lang = self.language_menu.get()

        if self.test_connection(lang) and self.check_server():
            if self.checkIfProcessRunning("ttermpro"):
                if ((choice == "Register" or choice == "Registra") and classes not in
                    self.enrolled_classes_list.values() and section not in self.enrolled_classes_list) \
                        or ((choice == "Drop" or choice == "Baja") and classes
                            not in self.dropped_classes_list.values() and section not in self.dropped_classes_list):
                    if (re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE)
                            and re.fullmatch("^[A-Z]{2}1$", section, flags=re.IGNORECASE)
                            and re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE)
                            and (semester == "C23" or semester == "C31" or semester == "C41"
                                 or semester == "C32" or semester == "C33")):
                        ctypes.windll.user32.BlockInput(True)
                        uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                        uprb_window.wait('visible', timeout=100)
                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                        send_keys("{ENTER}")
                        self.uprb.UprbayTeraTermVt.type_keys("1S4")
                        self.uprb.UprbayTeraTermVt.type_keys(semester)
                        send_keys("{ENTER}")
                        screenshot_thread = threading.Thread(target=self.capture_screenshot)
                        screenshot_thread.start()
                        screenshot_thread.join()
                        text_output = self.capture_screenshot()
                        if "OUTDATED" not in text_output:
                            enrolled_classes = "ENROLLED"
                            count_enroll = text_output.count(enrolled_classes)
                            send_keys("{TAB 2}")
                            for i in range(count_enroll, 0, -1):
                                send_keys("{TAB 2}")
                            if choice == "Register" or choice == "Registra":
                                self.uprb.UprbayTeraTermVt.type_keys("R")
                            elif choice == "Drop" or choice == "Baja":
                                self.uprb.UprbayTeraTermVt.type_keys("D")
                            self.uprb.UprbayTeraTermVt.type_keys(classes)
                            self.uprb.UprbayTeraTermVt.type_keys(section)
                            send_keys("{ENTER}")
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text = self.capture_screenshot()
                            self.reset_activity_timer(None)
                            self.go_next_1VE.configure(state="disabled")
                            self.go_next_1GP.configure(state="disabled")
                            self.go_next_409.configure(state="disabled")
                            self.go_next_683.configure(state="disabled")
                            self.go_next_4CM.configure(state="disabled")
                            if "CONFIRMED" in text or "DROPPED" in text:
                                self.e_classes_entry.delete(0, "end")
                                self.section_entry.delete(0, "end")
                                if choice == "Register" or choice == "Registra":
                                    send_keys("{ENTER}")
                                    self.e_counter += 1
                                    if classes in self.dropped_classes_list:
                                        del self.dropped_classes_list[section]
                                    if classes not in self.enrolled_classes_list:
                                        self.enrolled_classes_list[section] = classes
                                    elif classes in self.enrolled_classes_list:
                                        del self.enrolled_classes_list[section]
                                    if lang == "English":
                                        self.show_success_message(350, 265, "Enrolled class successfully")
                                    elif lang == "Español":
                                        self.show_success_message(350, 265, "Clase registrada exitósamente")
                                elif choice == "Drop" or choice == "Baja":
                                    if section in self.enrolled_classes_list:
                                        del self.enrolled_classes_list[section]
                                    if section not in self.dropped_classes_list:
                                        self.dropped_classes_list[section] = classes
                                    elif section in self.dropped_classes_list:
                                        del self.dropped_classes_list[section]
                                    if lang == "English":
                                        self.show_success_message(350, 265, "Dropped class successfully")
                                    elif lang == "Español":
                                        self.show_success_message(350, 265, "Clase abandonada exitósamente")
                                if self.e_counter + self.m_counter == 15:
                                    time.sleep(3.2)
                                    self.submit.configure(state="disabled")
                                    self.multiple.configure(state="disabled")
                                    if lang == "English":
                                        self.show_information_message(350, 265, "Reached Enrollment limit!")
                                    elif lang == "Español":
                                        self.show_information_message(350, 265, "Llegó al Límite de Matrícula")
                            else:
                                self.reset_activity_timer(None)
                                self.set_focus_to_tkinter()
                                if lang == "English":
                                    self.show_error_message(320, 235, "Error! Unable to enroll class")
                                    self.after(2500, self.show_enrollment_error_information)
                                elif lang == "Español":
                                    self.show_error_message(320, 235, "¡Error! No se pudo matricular la clase")
                                    self.after(2500, self.show_enrollment_error_information)
                        else:
                            send_keys("{TAB}")
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            self.uprb.UprbayTeraTermVt.type_keys(semester.replace(" ", ""))
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            self.set_focus_to_tkinter()
                            if lang == "English":
                                self.show_error_message(300, 210, "Error! Unable to enroll class")
                                self.after(2500, self.show_enrollment_error_information)
                            elif lang == "Español":
                                self.show_error_message(320, 210, "¡Error! No se puede matricular la clase")
                                self.after(2500, self.show_enrollment_error_information)
                    else:
                        if lang == "English":
                            self.show_error_message(350, 265, "Error! Wrong Class or Section \n\n"
                                                              " or Semester Format")
                        elif lang == "Español":
                            self.show_error_message(350, 265, "¡Error! Formato Incorrecto para Clase o "
                                                              "\n\n Sección o Semestre")
                else:
                    if classes in self.enrolled_classes_list.values() or section in self.enrolled_classes_list:
                        if lang == "English":
                            self.show_error_message(335, 245, "Error! Class or section already registered")
                        elif lang == "Español":
                            self.show_error_message(335, 245, "¡Error! Ya la clase o la sección está registrada")
                    if classes in self.dropped_classes_list.values() or section in self.dropped_classes_list:
                        if lang == "English":
                            self.show_error_message(335, 245, "Error! Class or section already dropped")
                        elif lang == "Español":
                            self.show_error_message(335, 245, "¡Error! Ya se dio de baja de esa clase o sección")
            else:
                if lang == "English":
                    self.show_error_message(300, 215, "Error! Tera Term is disconnected")
                elif lang == "Español":
                    self.show_error_message(300, 215, "¡Error! Tera Term esta desconnectado")
        ctypes.windll.user32.BlockInput(False)
        block_window.destroy()
        task_done.set()

    def search_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.search_event, args=(task_done,))
        event_thread.start()

    # function for searching for classes for the first time
    def search_event(self, task_done):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        classes2 = self.s_classes_entry.get().replace(" ", "")
        semester2 = self.s_semester_entry.get().upper().replace(" ", "")
        show_all = self.show_all.get()
        lang = self.language_menu.get()
        if self.test_connection(lang) and self.check_server():
            if self.checkIfProcessRunning("ttermpro"):
                if (re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes2, flags=re.IGNORECASE)
                        and re.fullmatch("^[A-Z][0-9]{2}$", semester2, flags=re.IGNORECASE)
                        and semester2 in ("B61", "B62", "B63", "B71", "B72", "B73", "B81", "B82", "B83", "B91", "B92",
                                          "B93", "C01", "C02", "C03", "C11", "C12", "C13", "C21", "C22", "C23", "C31")):
                    ctypes.windll.user32.BlockInput(True)
                    uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                    uprb_window.wait('visible', timeout=100)
                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                    send_keys("{ENTER}")
                    self.uprb.UprbayTeraTermVt.type_keys("1CS")
                    self.uprb.UprbayTeraTermVt.type_keys(semester2)
                    send_keys("{ENTER}")
                    self.uprb.UprbayTeraTermVt.type_keys(classes2)
                    send_keys("{TAB}")
                    if show_all == "on":
                        self.uprb.UprbayTeraTermVt.type_keys("Y")
                    elif show_all == "off":
                        self.uprb.UprbayTeraTermVt.type_keys("N")
                    send_keys("{ENTER}")
                    ctypes.windll.user32.BlockInput(False)
                    self.reset_activity_timer(None)
                    self.go_next_1VE.configure(state="disabled")
                    self.go_next_1GP.configure(state="disabled")
                    self.go_next_409.configure(state="disabled")
                    self.go_next_683.configure(state="disabled")
                    self.go_next_4CM.configure(state="disabled")
                    self.s_classes_entry.delete(0, "end")
                    self.search.configure(command=self.search2_event_handler)
                else:
                    if lang == "English":
                        self.show_error_message(350, 265, "Error! Wrong Class or Section \n\n"
                                                          " or Semester Format")
                    elif lang == "Español":
                        self.show_error_message(350, 265, "¡Error! Formato Incorrecto para Clase o "
                                                          "\n\n Semestre")
            else:
                if lang == "English":
                    self.show_error_message(300, 215, "Error! Tera Term is disconnected")
                elif lang == "Español":
                    self.show_error_message(300, 215, "¡Error! Tera Term esta desconnectado")
        block_window.destroy()
        task_done.set()

    def search2_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.search2_event, args=(task_done,))
        event_thread.start()

    # function for searching for classes after the first time
    def search2_event(self, task_done):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        classes2 = self.s_classes_entry.get().replace(" ", "")
        semester2 = self.s_semester_entry.get().upper().replace(" ", "")
        show_all = self.show_all.get()
        lang = self.language_menu.get()
        if self.test_connection(lang) and self.check_server():
            if self.checkIfProcessRunning("ttermpro"):
                if (re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes2, flags=re.IGNORECASE)
                        and re.fullmatch("^[A-Z][0-9]{2}$", semester2, flags=re.IGNORECASE)
                        and semester2 in ("B61", "B62", "B63", "B71", "B72", "B73", "B81", "B82", "B83", "B91", "B92",
                                          "B93", "C01", "C02", "C03", "C11", "C12", "C13", "C21", "C22", "C23", "C31")):
                    ctypes.windll.user32.BlockInput(True)
                    uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                    uprb_window.wait('visible', timeout=100)
                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                    send_keys("{ENTER}")
                    self.uprb.UprbayTeraTermVt.type_keys("1CS")
                    self.uprb.UprbayTeraTermVt.type_keys(semester2)
                    send_keys("{ENTER}")
                    self.uprb.UprbayTeraTermVt.type_keys("1CS")
                    self.uprb.UprbayTeraTermVt.type_keys(classes2)
                    send_keys("{TAB}")
                    if show_all == "on":
                        self.uprb.UprbayTeraTermVt.type_keys("Y")
                    elif show_all == "off":
                        self.uprb.UprbayTeraTermVt.type_keys("N")
                    send_keys("{ENTER}")
                    ctypes.windll.user32.BlockInput(False)
                    self.reset_activity_timer(None)
                    self.go_next_1VE.configure(state="disabled")
                    self.go_next_1GP.configure(state="disabled")
                    self.go_next_409.configure(state="disabled")
                    self.go_next_683.configure(state="disabled")
                    self.go_next_4CM.configure(state="disabled")
                    self.s_classes_entry.delete(0, "end")
                else:
                    if lang == "English":
                        self.show_error_message(350, 265, "Error! Wrong Class or Section "
                                                          "\n\n or Semester Format")
                    elif lang == "Español":
                        self.show_error_message(350, 265, "¡Error! Formato Incorrecto para Clase o "
                                                          "\n\n Semestre")
            else:
                if lang == "English":
                    self.show_error_message(300, 215, "Error! Tera Term is disconnected")
                elif lang == "Español":
                    self.show_error_message(300, 215, "¡Error! Tera Term esta desconnectado")
        block_window.destroy()
        task_done.set()

    # function for seeing the classes you are currently enrolled for
    def my_classes_event(self):
        lang = self.language_menu.get()
        if lang == "Español":
            dialog = customtkinter.CTkInputDialog(text="Escriba el semestre:", title="Enseñar Mis Classes")
            dialog.geometry("1100+225")
            dialog.attributes("-topmost", True)
            dialog.after(201, lambda: dialog.iconbitmap("images/tera-term.ico"))
            dialog_input = dialog.get_input()
            if self.test_connection(lang) and self.check_server():
                if self.checkIfProcessRunning("ttermpro"):
                    if (re.fullmatch("^[A-Z][0-9]{2}$", dialog_input, flags=re.IGNORECASE)
                            and dialog_input in ("B61", "B62", "B63", "B71", "B72", "B73", "B81", "B82", "B83",
                                                 "B91", "B92", "B93", "C01", "C02", "C03", "C11", "C12", "C13",
                                                 "C21", "C22", "C23", "C31")):
                        block_window = customtkinter.CTkToplevel()
                        block_window.attributes("-alpha", 0.0)
                        block_window.grab_set()
                        ctypes.windll.user32.BlockInput(True)
                        uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                        uprb_window.wait('visible', timeout=100)
                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                        send_keys("{ENTER}")
                        self.uprb.UprbayTeraTermVt.type_keys("1CP")
                        self.uprb.UprbayTeraTermVt.type_keys(dialog_input.replace(" ", "").upper())
                        send_keys("{ENTER}")
                        ctypes.windll.user32.BlockInput(False)
                        self.reset_activity_timer(None)
                        self.go_next_1VE.configure(state="disabled")
                        self.go_next_1GP.configure(state="disabled")
                        self.go_next_409.configure(state="disabled")
                        self.go_next_683.configure(state="disabled")
                        self.go_next_4CM.configure(state="disabled")
                        block_window.destroy()
                    else:
                        self.show_error_message(300, 215, "¡Error! Semestre Incorrecto")
                else:
                    if self.language_menu.get() == "English":
                        self.show_error_message(300, 215, "Error! Tera Term is disconnected")
                    elif self.language_menu.get() == "Español":
                        self.show_error_message(300, 215, "¡Error! Tera Term esta desconnectado")

        elif lang == "English":
            dialog = customtkinter.CTkInputDialog(text="Enter the semester:", title="Show My Classes")
            dialog.geometry("1100+225")
            dialog.attributes("-topmost", True)
            dialog.after(201, lambda: dialog.iconbitmap("images/tera-term.ico"))
            dialog_input = dialog.get_input().replace(" ", "").upper()
            if self.test_connection(lang) and self.check_server():
                if self.checkIfProcessRunning("ttermpro"):
                    if (re.match("^[A-Z][0-9]{2}$", dialog_input, flags=re.IGNORECASE)
                            and dialog_input in ("B61", "B62", "B63", "B71", "B72", "B73", "B81", "B82", "B83",
                                                 "B91", "B92", "B93", "C01", "C02", "C03", "C11", "C12", "C13",
                                                 "C21", "C22", "C23", "C31")):
                        block_window = customtkinter.CTkToplevel()
                        block_window.attributes("-alpha", 0.0)
                        block_window.grab_set()
                        ctypes.windll.user32.BlockInput(True)
                        uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                        uprb_window.wait('visible', timeout=100)
                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                        send_keys("{ENTER}")
                        self.uprb.UprbayTeraTermVt.type_keys("1CP")
                        self.uprb.UprbayTeraTermVt.type_keys(dialog_input)
                        send_keys("{ENTER}")
                        ctypes.windll.user32.BlockInput(False)
                        self.reset_activity_timer(None)
                        self.go_next_1VE.configure(state="disabled")
                        self.go_next_1GP.configure(state="disabled")
                        self.go_next_409.configure(state="disabled")
                        self.go_next_683.configure(state="disabled")
                        self.go_next_4CM.configure(state="disabled")
                        block_window.destroy()
                    else:
                        self.show_error_message(300, 215, "Error! Wrong Semester")
                else:
                    if self.language_menu.get() == "English":
                        self.show_error_message(300, 215, "Error! Tera Term is disconnected")
                    elif self.language_menu.get() == "Español":
                        self.show_error_message(300, 215, "¡Error! Tera Term esta desconnectado")

    # function that adds new entries
    def add_event(self):
        lang = self.language_menu.get()
        semester = self.m_semester_entry.get().upper()
        if len(semester) != 0 and (semester == "C23" or semester == "C31" or semester == "C41"
                                   or semester == "C32" or semester == "C33"):
            self.a_counter += 1
            self.m_remove.configure(state="normal")
            if self.a_counter == 5:
                self.m_add.configure(state="disabled")
            elif self.a_counter != 5:
                self.m_add.configure(state="normal")
            if self.a_counter == 1:
                self.m_classes_entry2.grid(row=2, column=1, padx=(0, 500), pady=(20, 0))
                self.m_section_entry2.grid(row=2, column=1, padx=(0, 165), pady=(20, 0))
                self.m_semester_entry2.grid(row=2, column=1, padx=(165, 0), pady=(20, 0))
                if self.flag is False:
                    self.m_semester_entry2.insert(0, self.m_semester_entry.get())
                    self.m_semester_entry2.configure(state="disabled")
                self.m_register_menu2.grid(row=2, column=1, padx=(500, 0), pady=(20, 0))
            elif self.a_counter == 2:
                self.m_classes_entry3.grid(row=3, column=1, padx=(0, 500), pady=(20, 0))
                self.m_section_entry3.grid(row=3, column=1, padx=(0, 165), pady=(20, 0))
                self.m_semester_entry3.grid(row=3, column=1, padx=(165, 0), pady=(20, 0))
                if self.flag2 is False:
                    self.m_semester_entry3.insert(0, self.m_semester_entry.get())
                    self.m_semester_entry3.configure(state="disabled")
                self.m_register_menu3.grid(row=3, column=1, padx=(500, 0), pady=(20, 0))
            elif self.a_counter == 3:
                self.m_classes_entry4.grid(row=4, column=1, padx=(0, 500), pady=(20, 0))
                self.m_section_entry4.grid(row=4, column=1, padx=(0, 165), pady=(20, 0))
                self.m_semester_entry4.grid(row=4, column=1, padx=(165, 0), pady=(20, 0))
                if self.flag3 is False:
                    self.m_semester_entry4.insert(0, self.m_semester_entry.get())
                    self.m_semester_entry4.configure(state="disabled")
                self.m_register_menu4.grid(row=4, column=1, padx=(500, 0), pady=(20, 0))
            elif self.a_counter == 4:
                self.m_classes_entry5.grid(row=5, column=1, padx=(0, 500), pady=(20, 0))
                self.m_section_entry5.grid(row=5, column=1, padx=(0, 165), pady=(20, 0))
                self.m_semester_entry5.grid(row=5, column=1, padx=(165, 0), pady=(20, 0))
                if self.flag4 is False:
                    self.m_semester_entry5.insert(0, self.m_semester_entry.get())
                    self.m_semester_entry5.configure(state="disabled")
                self.m_register_menu5.grid(row=5, column=1, padx=(500, 0), pady=(20, 0))
            elif self.a_counter == 5:
                self.m_classes_entry6.grid(row=6, column=1, padx=(0, 500), pady=(20, 0))
                self.m_section_entry6.grid(row=6, column=1, padx=(0, 165), pady=(20, 0))
                self.m_semester_entry6.grid(row=6, column=1, padx=(165, 0), pady=(20, 0))
                if self.flag5 is False:
                    self.m_semester_entry6.insert(0, self.m_semester_entry.get())
                    self.m_semester_entry6.configure(state="disabled")
                self.m_register_menu6.grid(row=6, column=1, padx=(500, 0), pady=(20, 0))
        else:
            if lang == "English":
                self.show_error_message(350, 265, "Error! Must at least enter \n\n a valid semester")
            elif lang == "Español":
                self.show_error_message(350, 265, "¡Error! Debe escribir al menos \n\n un semestre válido")

    # function that removes existing entries
    def remove_event(self):
        self.m_add.configure(state="normal")
        if self.a_counter == 1 or self.a_counter == 0:
            self.m_remove.configure(state="disabled")
        elif self.a_counter != 1:
            self.m_remove.configure(state="normal")
        if self.a_counter == 1:
            self.a_counter -= 1
            self.m_classes_entry2.grid_forget()
            self.m_section_entry2.grid_forget()
            self.m_semester_entry2.grid_forget()
            self.m_register_menu2.grid_forget()
            self.m_semester_entry2.configure(state="normal")
            self.m_semester_entry2.delete(0, "end")
        elif self.a_counter == 2:
            self.a_counter -= 1
            self.m_classes_entry3.grid_forget()
            self.m_section_entry3.grid_forget()
            self.m_semester_entry3.grid_forget()
            self.m_register_menu3.grid_forget()
            self.m_semester_entry3.configure(state="normal")
            self.m_semester_entry3.delete(0, "end")
        elif self.a_counter == 3:
            self.a_counter -= 1
            self.m_classes_entry4.grid_forget()
            self.m_section_entry4.grid_forget()
            self.m_semester_entry4.grid_forget()
            self.m_register_menu4.grid_forget()
            self.m_semester_entry4.configure(state="normal")
            self.m_semester_entry4.delete(0, "end")
        elif self.a_counter == 4:
            self.a_counter -= 1
            self.m_classes_entry5.grid_forget()
            self.m_section_entry5.grid_forget()
            self.m_semester_entry5.grid_forget()
            self.m_register_menu5.grid_forget()
            self.m_semester_entry5.configure(state="normal")
            self.m_semester_entry5.delete(0, "end")
        elif self.a_counter == 5:
            self.a_counter -= 1
            self.m_classes_entry6.grid_forget()
            self.m_section_entry6.grid_forget()
            self.m_semester_entry6.grid_forget()
            self.m_register_menu6.grid_forget()
            self.m_semester_entry6.configure(state="normal")
            self.m_semester_entry6.delete(0, "end")

    # multiple classes screen
    def multiple_classes_event(self):
        scaling = self.scaling_optionemenu.get()
        self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
        if scaling not in ("90%", "95%", "100%"):
            self.change_scaling_event("100%")
        if self.a_counter == 1 or self.a_counter == 0:
            self.m_remove.configure(state="disabled")
        if self.a_counter == 5:
            self.m_add.configure(state="disabled")
        self.scaling_optionemenu.configure(state="disabled")
        self.multiple_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 35))
        self.multiple_frame.grid_columnconfigure(2, weight=1)
        self.m_button_frame.grid(row=3, column=1, columnspan=4, rowspan=4, padx=(0, 0), pady=(0, 0))
        self.m_button_frame.grid_columnconfigure(2, weight=1)
        self.explanation7.grid(row=0, column=1, padx=(0, 0), pady=(0, 20))
        self.warning.grid(row=0, column=1, padx=(0, 0), pady=(30, 0))
        self.m_classes_entry.grid(row=1, column=1, padx=(0, 500), pady=(0, 0))
        self.m_section_entry.grid(row=1, column=1, padx=(0, 165), pady=(0, 0))
        self.m_semester_entry.grid(row=1, column=1, padx=(165, 0), pady=(0, 0))
        self.m_register_menu.grid(row=1, column=1, padx=(500, 0), pady=(0, 0))
        self.m_add.grid(row=3, column=0, padx=(0, 20), pady=(0, 0))
        self.back4.grid(row=3, column=1, padx=(0, 20), pady=(0, 0))
        self.submit_multiple.grid(row=3, column=2, padx=(0, 0), pady=(0, 0))
        self.m_remove.grid(row=3, column=3, padx=(20, 0), pady=(0, 0))
        self.go_next_1VE.grid_forget()
        self.go_next_1GP.grid_forget()
        self.go_next_683.grid_forget()
        self.go_next_4CM.grid_forget()
        self.go_next_1GP.configure(state="disabled")
        self.go_next_683.configure(state="disabled")
        self.go_next_1VE.configure(state="disabled")
        self.go_next_4CM.configure(state="disabled")
        self.tabview.grid_forget()
        self.t_buttons_frame.grid_forget()

    def submit_multiple_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.submit_multiple_event, args=(task_done,))
        event_thread.start()

    # function that enrolls multiple classes with one click
    def submit_multiple_event(self, task_done):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        counter = self.a_counter
        classes = self.m_classes_entry.get().upper().replace(" ", "")
        section = self.m_section_entry.get().upper().replace(" ", "")
        semester = self.m_semester_entry.get().upper().replace(" ", "")
        choice = self.m_register_menu.get()
        classes2 = self.m_classes_entry2.get().upper().replace(" ", "")
        section2 = self.m_section_entry2.get().upper().replace(" ", "")
        choice2 = self.m_register_menu2.get()
        classes3 = self.m_classes_entry3.get().upper().replace(" ", "")
        section3 = self.m_section_entry3.get().upper().replace(" ", "")
        choice3 = self.m_register_menu3.get()
        classes4 = self.m_classes_entry4.get().upper().replace(" ", "")
        section4 = self.m_section_entry4.get().upper().replace(" ", "")
        choice4 = self.m_register_menu4.get()
        classes5 = self.m_classes_entry5.get().upper().replace(" ", "")
        section5 = self.m_section_entry5.get().upper().replace(" ", "")
        choice5 = self.m_register_menu5.get()
        classes6 = self.m_classes_entry6.get().upper().replace(" ", "")
        section6 = self.m_section_entry6.get().upper().replace(" ", "")
        choice6 = self.m_register_menu6.get()
        lang = self.language_menu.get()

        if lang == "English":
            msg = CTkMessagebox(master=self, title="Submit",
                                message="Are you sure you are ready submit the data?"
                                        " \n\nWARNING: Make sure the information is correct", icon="images/submit.png",
                                option_1="Cancel", option_2="No", option_3="Yes",
                                icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
        elif lang == "Español":
            msg = CTkMessagebox(master=self, title="Someter",
                                message="¿Estás preparado para somester la data?"
                                        " \n\nWARNING: Asegúrese de que la información está correcta",
                                icon="images/submit.png",
                                option_1="Cancelar", option_2="No", option_3="Sí",
                                icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
        response = msg.get()
        if response == "Yes" or response == "Sí":
            if self.test_connection(lang) and self.check_server():
                if self.checkIfProcessRunning("ttermpro"):
                    if counter == 0:
                        self.check = True
                    if counter == 1 and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes2, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section2, flags=re.IGNORECASE) \
                            and (choice2 != "Choose" and choice2 != "Escoge") \
                            and ((choice2 == "Register" or choice2 == "Registra") and classes2
                                 not in self.enrolled_classes_list.values() and section2
                                 not in self.enrolled_classes_list) \
                            or ((choice2 == "Drop" or choice2 == "Baja") and classes2
                                not in self.dropped_classes_list.values() and section2
                                not in self.dropped_classes_list):
                        self.check = True
                    elif counter == 2 and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes3, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section3, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes2, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section2, flags=re.IGNORECASE) \
                            and (choice3 != "Choose" and choice3 != "Escoge"
                                 and choice2 != "Choose" and choice2 != "Escoge") \
                            and ((choice3 == "Register" or choice3 == "Registra") and classes3
                                 not in self.enrolled_classes_list.values() and section3
                                 not in self.enrolled_classes_list) \
                            or ((choice3 == "Drop" or choice3 == "Baja") and classes3
                                not in self.dropped_classes_list.values() and section3
                                not in self.dropped_classes_list) \
                            and ((choice2 == "Register" or choice2 == "Registra") and classes2
                                 not in self.enrolled_classes_list.values() and section2
                                 not in self.enrolled_classes_list) \
                            or ((choice2 == "Drop" or choice2 == "Baja") and classes2
                                not in self.dropped_classes_list and section2
                                not in self.dropped_classes_list):
                        self.check = True
                    elif counter == 3 and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes4, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section4, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes3, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section3, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes2, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section2, flags=re.IGNORECASE) \
                            and (choice4 != "Choose" and choice4 != "Escoge"
                                 and choice3 != "Choose" and choice3 != "Escoge"
                                 and choice2 != "Choose" and choice2 != "Escoge") \
                            and ((choice4 == "Register" or choice4 == "Registra") and classes4 not in
                                 self.enrolled_classes_list.values() and section4
                                 not in self.enrolled_classes_list) \
                            or ((choice4 == "Drop" or choice4 == "Baja") and classes4 not in
                                self.dropped_classes_list.values() and section4
                                not in self.dropped_classes_list) \
                            and ((choice3 == "Register" or choice3 == "Registra") and classes3 not in
                                 self.enrolled_classes_list.values() and section3
                                 not in self.enrolled_classes_list) \
                            or ((choice3 == "Drop" or choice3 == "Baja") and classes3 not in
                                self.dropped_classes_list.values() and section3
                                not in self.dropped_classes_list) \
                            and ((choice2 == "Register" or choice2 == "Registra") and classes2 not in
                                 self.enrolled_classes_list.values() and section2
                                 not in self.enrolled_classes_list) \
                            or ((choice2 == "Drop" or choice2 == "Baja") and classes2 not in
                                self.dropped_classes_list.values() and section2
                                not in self.dropped_classes_list):
                        self.check = True
                    elif counter == 4 and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes5, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section5, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes4, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section4, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes3, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section3, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes2, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section2, flags=re.IGNORECASE) \
                            and (choice5 != "Choose" and choice5 != "Escoge"
                                 and choice4 != "Choose" and choice4 != "Escoge"
                                 and choice3 != "Choose" and choice3 != "Escoge"
                                 and choice2 != "Choose" and choice2 != "Escoge") \
                            and ((choice5 == "Register" or choice5 == "Registra") and classes5 not in
                                 self.enrolled_classes_list.values() and section5
                                 not in self.enrolled_classes_list) \
                            or ((choice5 == "Drop" or choice5 == "Baja") and classes5 not in
                                self.dropped_classes_list.values() and section5
                                not in self.dropped_classes_list) \
                            and ((choice4 == "Register" or choice4 == "Registra") and classes4 not in
                                 self.enrolled_classes_list.values() and section4
                                 not in self.enrolled_classes_list) \
                            or ((choice4 == "Drop" or choice4 == "Baja") and classes4 not in
                                self.dropped_classes_list.values() and section4
                                not in self.dropped_classes_list) \
                            and ((choice3 == "Register" or choice3 == "Registra") and classes3 not in
                                 self.enrolled_classes_list.values() and section3
                                 not in self.enrolled_classes_list) \
                            or ((choice3 == "Drop" or choice3 == "Baja") and classes3 not in
                                self.dropped_classes_list.values() and section3
                                not in self.dropped_classes_list) \
                            and ((choice2 == "Register" or choice2 == "Registra") and classes2 not in
                                 self.enrolled_classes_list.values() and section2
                                 not in self.enrolled_classes_list) \
                            or ((choice2 == "Drop" or choice2 == "Baja") and classes2 not in
                                self.dropped_classes_list.values() and section2
                                not in self.dropped_classes_list):
                        self.check = True
                    elif counter == 5 and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes6, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section6, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes5, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section5, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes4, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section4, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes3, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section3, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes2, flags=re.IGNORECASE) \
                            and re.fullmatch("^[A-Z]{2}1$", section2, flags=re.IGNORECASE) \
                            and (choice6 != "Choose" and choice6 != "Escoge"
                                 and choice5 != "Choose" and choice5 != "Escoge"
                                 and choice4 != "Choose" and choice4 != "Escoge"
                                 and choice3 != "Choose" and choice3 != "Escoge"
                                 and choice2 != "Choose" and choice2 != "Escoge") \
                            and ((choice6 == "Register" or choice6 == "Registra") and classes6 not in
                                 self.enrolled_classes_list.values() and section6
                                 not in self.enrolled_classes_list) \
                            or ((choice6 == "Drop" or choice6 == "Baja") and classes6 not in
                                self.dropped_classes_list.values() and section6
                                not in self.dropped_classes_list) \
                            and ((choice5 == "Register" or choice5 == "Registra") and classes5 not in
                                 self.enrolled_classes_list.values() and section5
                                 not in self.enrolled_classes_list) \
                            or ((choice5 == "Drop" or choice5 == "Baja") and classes5 not in
                                self.dropped_classes_list.values() and section5
                                not in self.dropped_classes_list) \
                            and ((choice4 == "Register" or choice4 == "Registra") and classes4 not in
                                 self.enrolled_classes_list.values() and section4
                                 not in self.enrolled_classes_list) \
                            or ((choice4 == "Drop" or choice4 == "Baja") and classes4 not in
                                self.dropped_classes_list.values() and section4
                                not in self.dropped_classes_list) \
                            and ((choice3 == "Register" or choice3 == "Registra") and classes3 not in
                                 self.enrolled_classes_list.values() and section3
                                 not in self.enrolled_classes_list) \
                            or ((choice3 == "Drop" or choice3 == "Baja") and classes3 not in
                                self.dropped_classes_list.values() and section3
                                not in self.dropped_classes_list) \
                            and ((choice2 == "Register" or choice2 == "Registra") and classes2 not in
                                 self.enrolled_classes_list.values() and section2
                                 not in self.enrolled_classes_list) \
                            or ((choice2 == "Drop" or choice2 == "Baja") and classes2 not in
                                self.dropped_classes_list.values() and section2
                                not in self.dropped_classes_list):
                        self.check = True
                    if self.check is True and (re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE)
                                               and re.fullmatch("^[A-Z]{2}1$", section, flags=re.IGNORECASE)
                                               and re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE)
                                               and (choice != "Choose" and choice != "Escoge")
                                               and ((choice == "Register" or choice == "Registra") and classes
                                                    not in self.enrolled_classes_list.values() and section
                                                    not in self.enrolled_classes_list)
                                               or ((choice == "Drop" or choice == "Baja") and classes
                                                   not in self.dropped_classes_list.values() and section
                                                   not in self.dropped_classes_list)
                                               and (semester == "C23" or semester == "C31" or semester == "C41"
                                                    or semester == "C32" or semester == "C33")):
                        if self.e_counter + self.m_counter + counter + 1 <= 15:
                            ctypes.windll.user32.BlockInput(True)
                            uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                            uprb_window.wait('visible', timeout=100)
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1S4")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            if "OUTDATED" not in text_output:
                                enrolled_classes = "ENROLLED"
                                count_enroll = text_output.count(enrolled_classes)
                                send_keys("{TAB 2}")
                                for i in range(count_enroll, 0, -1):
                                    send_keys("{TAB 2}")
                                if choice == "Register" or choice == "Registra":
                                    self.uprb.UprbayTeraTermVt.type_keys("R")
                                elif choice == "Drop" or choice == "Baja":
                                    self.uprb.UprbayTeraTermVt.type_keys("D")
                                self.uprb.UprbayTeraTermVt.type_keys(classes)
                                self.uprb.UprbayTeraTermVt.type_keys(section)
                                self.m_counter += 1
                                if counter == 0:
                                    send_keys("{ENTER}")
                                elif counter >= 1:
                                    send_keys("{TAB}")
                                if counter >= 1 and choice2 == "Register" or choice2 == "Registra":
                                    self.uprb.UprbayTeraTermVt.type_keys("R")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes2)
                                    self.uprb.UprbayTeraTermVt.type_keys(section2)
                                    if counter == 1:
                                        send_keys("{ENTER}")
                                    if counter >= 1:
                                        send_keys("{TAB}")
                                    self.m_counter += 1
                                elif counter >= 1 and choice2 == "Drop" or choice2 == "Baja":
                                    self.uprb.UprbayTeraTermVt.type_keys("D")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes2)
                                    self.uprb.UprbayTeraTermVt.type_keys(section2)
                                    if counter == 1:
                                        send_keys("{ENTER}")
                                    elif counter >= 1:
                                        send_keys("{TAB}")
                                    self.m_counter += 1
                                if counter >= 2 and choice3 == "Register" or choice3 == "Registra":
                                    self.uprb.UprbayTeraTermVt.type_keys("R")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes3)
                                    self.uprb.UprbayTeraTermVt.type_keys(section3)
                                    if counter == 2:
                                        send_keys("{ENTER}")
                                    elif counter >= 2:
                                        send_keys("{TAB}")
                                    self.m_counter += 1
                                elif counter >= 2 and choice3 == "Drop" or choice3 == "Baja":
                                    self.uprb.UprbayTeraTermVt.type_keys("D")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes3)
                                    self.uprb.UprbayTeraTermVt.type_keys(section3)
                                    if counter == 2:
                                        send_keys("{ENTER}")
                                    elif counter >= 2:
                                        send_keys("{TAB}")
                                    self.m_counter += 1
                                if counter >= 3 and choice4 == "Register" or choice4 == "Registra":
                                    self.uprb.UprbayTeraTermVt.type_keys("R")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes4)
                                    self.uprb.UprbayTeraTermVt.type_keys(section4)
                                    if counter == 3:
                                        send_keys("{ENTER}")
                                    elif counter >= 3:
                                        send_keys("{TAB}")
                                    self.m_counter += 1
                                elif counter >= 3 and choice4 == "Drop" or choice4 == "Baja":
                                    self.uprb.UprbayTeraTermVt.type_keys("D")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes4)
                                    self.uprb.UprbayTeraTermVt.type_keys(section4)
                                    if counter == 3:
                                        send_keys("{ENTER}")
                                    elif counter >= 3:
                                        send_keys("{TAB}")
                                    self.m_counter += 1
                                if counter >= 4 and choice5 == "Register" or choice5 == "Registra":
                                    self.uprb.UprbayTeraTermVt.type_keys("R")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes5)
                                    self.uprb.UprbayTeraTermVt.type_keys(section5)
                                    if counter == 4:
                                        send_keys("{ENTER}")
                                    elif counter >= 4:
                                        send_keys("{TAB}")
                                    self.m_counter += 1
                                elif counter >= 4 and choice5 == "Drop" or choice5 == "Baja":
                                    self.uprb.UprbayTeraTermVt.type_keys("D")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes5)
                                    self.uprb.UprbayTeraTermVt.type_keys(section5)
                                    if counter == 4:
                                        send_keys("{ENTER}")
                                    elif counter >= 4:
                                        send_keys("{TAB}")
                                    self.m_counter += 1
                                if counter == 5 and choice6 == "Register" or choice6 == "Registra":
                                    self.uprb.UprbayTeraTermVt.type_keys("R")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes6)
                                    self.uprb.UprbayTeraTermVt.type_keys(section6)
                                    send_keys("{ENTER}")
                                    self.m_counter += 1
                                elif counter == 5 and choice6 == "Drop" or choice6 == "Baja":
                                    self.uprb.UprbayTeraTermVt.type_keys("D")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes6)
                                    self.uprb.UprbayTeraTermVt.type_keys(section6)
                                    send_keys("{ENTER}")
                                    self.m_counter += 1
                                screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                screenshot_thread.start()
                                screenshot_thread.join()
                                text = self.capture_screenshot()
                                self.reset_activity_timer(None)
                                self.go_next_1VE.configure(state="disabled")
                                self.go_next_1GP.configure(state="disabled")
                                self.go_next_409.configure(state="disabled")
                                self.go_next_683.configure(state="disabled")
                                self.go_next_4CM.configure(state="disabled")
                                if "CONFIRMED" in text or "DROPPED" not in text:
                                    if choice == "Register":
                                        send_keys("{ENTER}")
                                        classes_list = [classes, classes2, classes3, classes4, classes5, classes6]
                                        section_list = [section, section2, section3, section4, section5, section6]
                                        for i in range(len(classes_list)):
                                            current_classes = classes_list[i]
                                            current_section = section_list[i]
                                            if current_section:
                                                if current_classes in self.dropped_classes_list:
                                                    del self.dropped_classes_list[current_section]
                                                if current_classes not in self.enrolled_classes_list:
                                                    self.enrolled_classes_list[current_section] = current_classes
                                                elif current_classes in self.enrolled_classes_list:
                                                    del self.enrolled_classes_list[current_section]
                                        if lang == "English":
                                            self.show_success_message(350, 265, "Enrolled classes successfully")
                                        elif lang == "Español":
                                            self.show_success_message(350, 265, "Clases registradas exitósamente")
                                    elif choice == "Drop":
                                        classes_list = [classes, classes2, classes3, classes4, classes5, classes6]
                                        section_list = [section, section2, section3, section4, section5, section6]
                                        for i in range(len(classes_list)):
                                            current_classes = classes_list[i]
                                            current_section = section_list[i]
                                            if current_classes in self.enrolled_classes_list:
                                                del self.enrolled_classes_list[current_section]
                                            if current_classes not in self.dropped_classes_list:
                                                self.dropped_classes_list[current_section] = current_classes
                                            elif current_classes in self.dropped_classes_list:
                                                del self.dropped_classes_list[current_section]
                                        if lang == "English":
                                            self.show_success_message(350, 265, "Dropped classes successfully")
                                        elif lang == "Español":
                                            self.show_success_message(350, 265, "Clases abandonadas exitósamente")
                                    if "INVALID COURSE ID" in text or "COURSE RESERVED" in text or "COURSE CLOSED" or \
                                            "CRS ALRDY TAKEN/PASSED" in text or "Closed by Spec-Prog" in text or \
                                            "Pre-Req" in text or "ILLEGAL DROP-NOT ENR" in text or \
                                            "NEW COURSE,NO FUNCTION" in text or "PRESENTLY ENROLLED" in text:
                                        for i in range(counter, -1, -1):
                                            self.enrolled_classes_list.popitem()
                                            self.dropped_classes_list.popitem()
                                    if self.e_counter + self.m_counter == 15:
                                        self.go_back_event2()
                                        self.submit.configure(state="disabled")
                                        self.multiple.configure(state="disabled")
                                        time.sleep(3.2)
                                        if lang == "English":
                                            self.show_information_message(350, 265, "Reached Enrollment limit!")
                                        elif lang == "Español":
                                            self.show_information_message(350, 265, "Llegó al Límite de Matrícula")
                                    self.submit.configure(command=self.submit2_event_handler)
                                    self.m_classes_entry.delete(0, "end")
                                    self.m_section_entry.delete(0, "end")
                                    self.m_classes_entry2.delete(0, "end")
                                    self.m_section_entry2.delete(0, "end")
                                    self.m_classes_entry3.delete(0, "end")
                                    self.m_section_entry3.delete(0, "end")
                                    self.m_classes_entry4.delete(0, "end")
                                    self.m_section_entry4.delete(0, "end")
                                    self.m_classes_entry5.delete(0, "end")
                                    self.m_section_entry5.delete(0, "end")
                                    self.m_classes_entry6.delete(0, "end")
                                    self.m_section_entry6.delete(0, "end")
                                    if lang == "English":
                                        self.m_classes_entry.configure(placeholder_text="Class")
                                        self.m_section_entry.configure(placeholder_text="Section")
                                        self.m_classes_entry2.configure(placeholder_text="Class")
                                        self.m_section_entry2.configure(placeholder_text="Section")
                                        self.m_classes_entry3.configure(placeholder_text="Class")
                                        self.m_section_entry3.configure(placeholder_text="Section")
                                        self.m_classes_entry4.configure(placeholder_text="Class")
                                        self.m_section_entry4.configure(placeholder_text="Section")
                                        self.m_classes_entry5.configure(placeholder_text="Class")
                                        self.m_section_entry5.configure(placeholder_text="Section")
                                        self.m_classes_entry6.configure(placeholder_text="Class")
                                        self.m_section_entry6.configure(placeholder_text="Section")
                                    if lang == "Español":
                                        self.m_classes_entry.configure(placeholder_text="Clase")
                                        self.m_section_entry.configure(placeholder_text="Sección")
                                        self.m_classes_entry2.configure(placeholder_text="Clase")
                                        self.m_section_entry2.configure(placeholder_text="Sección")
                                        self.m_classes_entry3.configure(placeholder_text="Clase")
                                        self.m_section_entry3.configure(placeholder_text="Sección")
                                        self.m_classes_entry4.configure(placeholder_text="Clase")
                                        self.m_section_entry4.configure(placeholder_text="Sección")
                                        self.m_classes_entry6.configure(placeholder_text="Clase")
                                        self.m_section_entry6.configure(placeholder_text="Sección")
                                else:
                                    self.reset_activity_timer(None)
                                    self.set_focus_to_tkinter()
                                    if lang == "English":
                                        self.show_error_message(320, 235, "Error! Unable to enroll classes")
                                        self.after(2500, self.show_enrollment_error_information)
                                    if lang == "Español":
                                        self.show_error_message(320, 235, "¡Error! No se pudo "
                                                                          "matricular las clases")
                                        self.after(2500, self.show_enrollment_error_information)
                                    self.check = False
                                    self.m_counter = self.m_counter - counter - 1
                                    self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
                            else:
                                self.uprb.UprbayTeraTermVt.type_keys(semester.replace(" ", ""))
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                send_keys("{ENTER}")
                                send_keys("{TAB 2}")
                                self.reset_activity_timer(None)
                                self.set_focus_to_tkinter()
                                if lang == "English":
                                    self.show_error_message(300, 210, "Error! Unable to enroll class")
                                    self.after(2500, self.show_enrollment_error_information)
                                elif lang == "Español":
                                    self.show_error_message(320, 210, "¡Error! No se puede matricular la clase")
                                    self.after(2500, self.show_enrollment_error_information)
                        else:
                            if lang == "English":
                                self.show_error_message(320, 235, "Error! Can only enroll up to 15 classes")
                            if lang == "Español":
                                self.show_error_message(320, 235, "¡Error! Solamente puede matricular\n\n"
                                                                  " hasta 15 clases")
                            self.check = False
                            self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
                    else:
                        if lang == "English":
                            self.show_error_message(400, 300, "Error! Wrong Format for Classes, Sections, \n\n "
                                                              "Semester or you are trying to enroll \n\n"
                                                              "a class or a section \n\n"
                                                              " that has already been enrolled")
                        elif lang == "Español":
                            self.show_error_message(400, 300, "¡Error! Formato Incorrecto para Clases, "
                                                              "\n\n Secciones, Semestre o estás intentando de"
                                                              "\n\n matricular una clase o sección "
                                                              "\n\n que ya ha sido matriculada")
                        self.check = False
                        self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
                else:
                    if lang == "English":
                        self.show_error_message(300, 215, "Error! Tera Term is disconnected")
                    elif lang == "Español":
                        self.show_error_message(300, 215, "¡Error! Tera Term esta desconnectado")
                    self.check = False
                    self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
        ctypes.windll.user32.BlockInput(False)
        block_window.destroy()
        task_done.set()

    def option_menu_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.option_menu_event, args=(task_done,))
        event_thread.start()

    # changes to the respective screen the user chooses
    def option_menu_event(self, task_done):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        menu = self.menu_entry.get()
        lang = self.language_menu.get()
        semester = self.menu_semester_entry.get().upper().replace(" ", "")
        if menu == "SRM (Main Menu)" or menu == "SRM (Menú Principal)":
            menu = "SRM"
        if menu == "004 (Hold Flags)":
            menu = "004"
        if menu == "1GP (Class Schedule)" or menu == "1GP (Programa de Clases)":
            menu = "1GP"
        if menu == "118 (Academic Staticstics)" or menu == "118 (Estadísticas Académicas)":
            menu = "118"
        if menu == "1VE (Academic Record)" or menu == "1VE (Expediente Académico)":
            menu = "1VE"
        if menu == "3DD (Scholarship Payment Record)" or menu == "3DD (Historial de Pagos de Beca)":
            menu = "3DD"
        if menu == "409 (Account Balance)" or menu == "409 (Balance de Cuenta)":
            menu = "409"
        if menu == "683 (Academic Evaluation)" or menu == "683 (Evaluación Académica)":
            menu = "683"
        if menu == "1PL (Basic Personal Data)" or menu == "1PL (Datos Básicos)":
            menu = "1PL"
        if menu == "4CM (Tuition Calculation)" or menu == "4CM (Cómputo de Matrícula)":
            menu = "4CM"
        if menu == "4SP (Apply for Extension)" or menu == "4SP (Solicitud de Prórroga)":
            menu = "4SP"
        if menu == "SO (Sign out)" or menu == "SO (Cerrar Sesión)":
            menu = "SO"
        if self.test_connection(lang) and self.check_server():
            if self.checkIfProcessRunning("ttermpro"):
                if (re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE)
                        and len(semester) != 0 and semester in ("B61", "B62", "B63", "B71", "B72", "B73", "B81", "B82",
                                                                "B83", "B91", "B92", "B93", "C01", "C02", "C03", "C11",
                                                                "C12", "C13", "C21", "C22", "C23", "C31")):
                    ctypes.windll.user32.BlockInput(True)
                    uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                    uprb_window.wait('visible', timeout=100)
                    match menu.replace(" ", ""):
                        case "SRM":
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            self.unfocus_tkinter()
                            self.go_next_1VE.configure(state="disabled")
                            self.go_next_1GP.configure(state="disabled")
                            self.go_next_409.configure(state="disabled")
                            self.go_next_683.configure(state="disabled")
                            self.go_next_4CM.configure(state="disabled")
                        case "004":
                            self.uprb.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("004")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            self.unfocus_tkinter()
                            self.go_next_1VE.configure(state="disabled")
                            self.go_next_1GP.configure(state="disabled")
                            self.go_next_409.configure(state="disabled")
                            self.go_next_683.configure(state="disabled")
                            self.go_next_4CM.configure(state="disabled")
                        case "1GP":
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1GP")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            self.unfocus_tkinter()
                            self.go_next_1GP.configure(state="normal")
                            self.go_next_1VE.grid_forget()
                            self.go_next_409.grid_forget()
                            self.go_next_683.grid_forget()
                            self.go_next_1VE.configure(state="disabled")
                            self.go_next_409.configure(state="disabled")
                            self.go_next_683.configure(state="disabled")
                            self.go_next_4CM.configure(state="disabled")
                            self.menu_submit.configure(width=95)
                            self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
                            self.menu_intro.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                            if lang == "English":
                                self.menu.grid(row=2, column=1, padx=(44, 0), pady=(10, 0), sticky="w")
                            elif lang == "Español":
                                self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
                            self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
                            self.menu_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0), sticky="w")
                            self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0), sticky="n")
                            self.go_next_1GP.grid(row=5, column=1, padx=(110, 0), pady=(40, 0), sticky="n")
                        case "118":
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("118")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            self.unfocus_tkinter()
                            self.go_next_1VE.configure(state="disabled")
                            self.go_next_1GP.configure(state="disabled")
                            self.go_next_409.configure(state="disabled")
                            self.go_next_683.configure(state="disabled")
                            self.go_next_4CM.configure(state="disabled")
                        case "1VE":
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1VE")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            self.unfocus_tkinter()
                            self.reset_activity_timer(None)
                            self.go_next_1VE.configure(state="disabled")
                            self.go_next_1GP.configure(state="disabled")
                            self.go_next_409.configure(state="disabled")
                            self.go_next_683.configure(state="disabled")
                            self.go_next_4CM.configure(state="disabled")
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text = self.capture_screenshot()
                            if "CONFLICT" in text:
                                if lang == "English":
                                    self.show_information_message(310, 225, "Student has a hold flag")
                                if lang == "Español":
                                    self.show_information_message(310, 225, "Estudiante tine un hold flag")
                                self.uprb.UprbayTeraTermVt.type_keys("004")
                                self.uprb.UprbayTeraTermVt.type_keys(semester)
                                send_keys("{ENTER}")
                            if "CONFLICT" not in text:
                                self.go_next_1VE.configure(state="normal")
                                self.go_next_1GP.grid_forget()
                                self.go_next_409.grid_forget()
                                self.go_next_683.grid_forget()
                                self.go_next_4CM.grid_forget()
                                self.menu_submit.configure(width=95)
                                self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
                                self.menu_intro.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                                if lang == "English":
                                    self.menu.grid(row=2, column=1, padx=(44, 0), pady=(10, 0), sticky="w")
                                elif lang == "Español":
                                    self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
                                self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
                                self.menu_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0), sticky="w")
                                self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
                                self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0), sticky="n")
                                self.go_next_1VE.grid(row=5, column=1, padx=(110, 0), pady=(40, 0), sticky="n")
                        case "3DD":
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("3DD")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            self.unfocus_tkinter()
                            self.go_next_1VE.configure(state="disabled")
                            self.go_next_1GP.configure(state="disabled")
                            self.go_next_409.configure(state="disabled")
                            self.go_next_683.configure(state="disabled")
                            self.go_next_4CM.configure(state="disabled")
                        case "409":
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("409")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            self.unfocus_tkinter()
                            self.go_next_409.configure(state="normal")
                            self.go_next_1VE.grid_forget()
                            self.go_next_1GP.grid_forget()
                            self.go_next_683.grid_forget()
                            self.go_next_4CM.grid_forget()
                            self.go_next_1GP.configure(state="disabled")
                            self.go_next_683.configure(state="disabled")
                            self.go_next_1VE.configure(state="disabled")
                            self.go_next_4CM.configure(state="disabled")
                            self.menu_submit.configure(width=95)
                            self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
                            self.menu_intro.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                            if lang == "English":
                                self.menu.grid(row=2, column=1, padx=(44, 0), pady=(10, 0), sticky="w")
                            elif lang == "Español":
                                self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
                            self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
                            self.menu_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0), sticky="w")
                            self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0), sticky="n")
                            self.go_next_409.grid(row=5, column=1, padx=(110, 0), pady=(40, 0), sticky="n")
                        case "683":
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("683")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            self.unfocus_tkinter()
                            self.go_next_1VE.grid_forget()
                            self.go_next_1GP.grid_forget()
                            self.go_next_409.grid_forget()
                            self.go_next_4CM.grid_forget()
                            self.go_next_1VE.configure(state="disabled")
                            self.go_next_1GP.configure(state="disabled")
                            self.go_next_409.configure(state="disabled")
                            self.go_next_4CM.configure(state="disabled")
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text = self.capture_screenshot()
                            if "CONFLICT" in text:
                                if lang == "English":
                                    self.show_information_message(310, 225, "Student has a hold flag")
                                if lang == "Español":
                                    self.show_information_message(310, 225, "Estudiante tine un hold flag")
                                self.uprb.UprbayTeraTermVt.type_keys("004")
                                send_keys("{ENTER}")
                            if "CONFLICT" not in text:
                                self.go_next_683.configure(state="normal")
                                self.submit.configure(width=95)
                                self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
                                self.menu_intro.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                                if lang == "English":
                                    self.menu.grid(row=2, column=1, padx=(44, 0), pady=(10, 0), sticky="w")
                                elif lang == "Español":
                                    self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
                                self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
                                self.menu_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0), sticky="w")
                                self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
                                self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0), sticky="n")
                                self.go_next_683.grid(row=5, column=1, padx=(110, 0), pady=(40, 0), sticky="n")
                        case "1PL":
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1PL")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            self.unfocus_tkinter()
                            self.go_next_1VE.configure(state="disabled")
                            self.go_next_1GP.configure(state="disabled")
                            self.go_next_409.configure(state="disabled")
                            self.go_next_683.configure(state="disabled")
                            self.go_next_4CM.configure(state="disabled")
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text = self.capture_screenshot()
                            if "TERM OUTDATED" in text or "NO PUEDE REALIZAR CAMBIOS" in text:
                                if "TERM OUTDATED" in text:
                                    send_keys("{TAB}")
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                if lang == "English":
                                    self.show_error_message(325, 240, "Error! Unable to enter\n "
                                                            + self.menu_entry.get() + " screen")
                                if lang == "Español":
                                    self.show_error_message(325, 240, "¡Error! No se pudo entrar"
                                                                      "\n a la pantalla" + self.menu_entry.get())
                        case "4CM":
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("4CM")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            self.unfocus_tkinter()
                            self.go_next_4CM.configure(state="normal")
                            self.go_next_1VE.grid_forget()
                            self.go_next_1GP.grid_forget()
                            self.go_next_409.grid_forget()
                            self.go_next_4CM.grid_forget()
                            self.go_next_1VE.configure(state="disabled")
                            self.go_next_1GP.configure(state="disabled")
                            self.go_next_409.configure(state="disabled")
                            self.menu_submit.configure(width=95)
                            self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
                            self.menu_intro.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                            if lang == "English":
                                self.menu.grid(row=2, column=1, padx=(44, 0), pady=(10, 0), sticky="w")
                            elif lang == "Español":
                                self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
                            self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
                            self.menu_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0), sticky="w")
                            self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0), sticky="n")
                            self.go_next_4CM.grid(row=5, column=1, padx=(110, 0), pady=(40, 0), sticky="n")
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text = self.capture_screenshot()
                            if "TERM OUTDATED" in text:
                                send_keys("{TAB}")
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                send_keys("{ENTER}")
                                self.reset_activity_timer(None)
                                if lang == "English":
                                    self.show_error_message(325, 240, "Error! Unable to enter\n "
                                                            + self.menu_entry.get() + " screen")
                                if lang == "Español":
                                    self.show_error_message(325, 240, "¡Error! No se pudo entrar"
                                                                      "\n a la pantalla" + self.menu_entry.get())
                        case "4SP":
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("4SP")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            self.unfocus_tkinter()
                            self.go_next_1VE.configure(state="disabled")
                            self.go_next_1GP.configure(state="disabled")
                            self.go_next_409.configure(state="disabled")
                            self.go_next_683.configure(state="disabled")
                            self.go_next_4CM.configure(state="disabled")
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text = self.capture_screenshot()
                            if "TERM OUTDATED" in text or "NO PUEDE REALIZAR CAMBIOS" in text:
                                if "TERM OUTDATED" in text:
                                    send_keys("{TAB}")
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                if lang == "English":
                                    self.show_error_message(325, 240, "Error! Unable to enter\n "
                                                            + self.menu_entry.get() + " screen")
                                if lang == "Español":
                                    self.show_error_message(325, 240, "Error! No se pudo entrar"
                                                                      "\n a la pantalla"
                                                            + self.menu_entry.get())
                        case "SO":
                            lang = self.language_menu.get()
                            if lang == "English":
                                msg = CTkMessagebox(master=self, title="Exit",
                                                    message="Are you sure you want to sign out"
                                                            " and exit Tera Term?", icon="question",
                                                    option_1="Cancel", option_2="No", option_3="Yes",
                                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                                    hover_color=("darkred", "darkblue", "darkblue"))
                            elif lang == "Español":
                                msg = CTkMessagebox(master=self, title="Salir",
                                                    message="¿Estás seguro que quieres salir y cerrar "
                                                            " la sesión de Tera Term?",
                                                    icon="question",
                                                    option_1="Cancelar", option_2="No", option_3="Sí",
                                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                                    hover_color=("darkred", "darkblue", "darkblue"))
                            response = msg.get()
                            if self.checkIfProcessRunning("ttermpro") and response == "Yes" or response == "Sí":
                                self.uprb.UprbayTeraTermVt.type_keys("SO")
                                send_keys("{ENTER}")
                            if not self.checkIfProcessRunning("ttermpro") and response == "Yes" or response == "Sí":
                                if lang == "English":
                                    self.show_error_message(350, 265, "Error! Tera Term isn't running")
                                elif lang == "Español":
                                    self.show_error_message(350, 265,
                                                            "¡Error! Tera Term no esta corriendo")
                else:
                    if lang == "English":
                        self.show_error_message(350, 265, "Error! Wrong Code or Semester Format")
                    elif lang == "Español":
                        self.show_error_message(350, 265, "¡Error! Formato Código o Semestre Incorrecto")
            else:
                if lang == "English":
                    self.show_error_message(300, 215, "Error! Tera Term is disconnected")
                elif lang == "Español":
                    self.show_error_message(300, 215, "¡Error! Tera Term esta desconnectado")
        ctypes.windll.user32.BlockInput(False)
        block_window.destroy()
        task_done.set()

    # go through each page of the 1VE screen
    def go_next_event_EV1(self):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        lang = self.language_menu.get()
        if self.test_connection(lang) and self.check_server():
            if self.checkIfProcessRunning("ttermpro"):
                ctypes.windll.user32.BlockInput(True)
                uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                uprb_window.wait('visible', timeout=100)
                self.unfocus_tkinter()
                send_keys("{TAB 3}")
                send_keys("{ENTER}")
                ctypes.windll.user32.BlockInput(False)
                self.unfocus_tkinter()
                self.reset_activity_timer(None)
        block_window.destroy()

    # go through each page of the 1GP screen
    def go_next_event_1GP(self):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        lang = self.language_menu.get()
        if self.test_connection(lang) and self.check_server():
            if self.checkIfProcessRunning("ttermpro"):
                ctypes.windll.user32.BlockInput(True)
                uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                uprb_window.wait('visible', timeout=100)
                self.unfocus_tkinter()
                send_keys("{ENTER}")
                self.unfocus_tkinter()
                ctypes.windll.user32.BlockInput(False)
                self.reset_activity_timer(None)
        block_window.destroy()

    # go through each page of the 409 screen
    def go_next_event_409(self):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        lang = self.language_menu.get()
        if self.test_connection(lang) and self.check_server():
            if self.checkIfProcessRunning("ttermpro"):
                ctypes.windll.user32.BlockInput(True)
                uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                uprb_window.wait('visible', timeout=100)
                self.unfocus_tkinter()
                send_keys("{TAB 4}")
                send_keys("{ENTER}")
                self.unfocus_tkinter()
                ctypes.windll.user32.BlockInput(False)
                self.reset_activity_timer(None)
        block_window.destroy()

    # go through each page of the 683 screen
    def go_next_event_683(self):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        self.submit.configure(state="disabled")
        self.search.configure(state="disabled")
        self.multiple.configure(state="disabled")
        self.menu_submit.configure(state="disabled")
        self.show_classes.configure(state="disabled")
        self.unbind("<Return>")
        lang = self.language_menu.get()
        if self.test_connection(lang) and self.check_server():
            if self.checkIfProcessRunning("ttermpro"):
                ctypes.windll.user32.BlockInput(True)
                uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                uprb_window.wait('visible', timeout=100)
                self.unfocus_tkinter()
                send_keys("{ENTER}")
                self.unfocus_tkinter()
                ctypes.windll.user32.BlockInput(False)
                self.reset_activity_timer(None)
        block_window.destroy()

    # go through each page of the 4CM screen
    def go_next_event_4CM(self):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        lang = self.language_menu.get()
        if self.test_connection(lang) and self.check_server():
            if self.checkIfProcessRunning("ttermpro"):
                ctypes.windll.user32.BlockInput(True)
                uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                uprb_window.wait('visible', timeout=100)
                self.unfocus_tkinter()
                send_keys("{ENTER}")
                self.unfocus_tkinter()
                ctypes.windll.user32.BlockInput(False)
                self.reset_activity_timer(None)
                screenshot_thread = threading.Thread(target=self.capture_screenshot)
                screenshot_thread.start()
                screenshot_thread.join()
                text = self.capture_screenshot()
                if "RATE NOT ON ARFILE" in text:
                    if lang == "English":
                        self.show_error_message(310, 225, "Unknown Error!")
                    if lang == "Español":
                        self.show_error_message(310, 225, "¡Error Desconocido!")
                else:
                    self.go_next_4CM.configure(state="disabled")
        block_window.destroy()

    def student_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.student_event, args=(task_done,))
        event_thread.start()

    # Authentication required frame, where user is asked to input his username
    def student_event(self, task_done):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        username = self.username_entry.get().replace(" ", "").lower()
        lang = self.language_menu.get()
        self.bind("<Return>", lambda event: self.tuition_event_handler())
        if self.test_connection(lang) and self.check_server():
            if self.checkIfProcessRunning("ttermpro"):
                if username == "students":
                    self.unfocus_tkinter()
                    ctypes.windll.user32.BlockInput(True)

                    uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                    uprb_window.wait('visible', timeout=100)
                    user = self.uprb.UprbayTeraTermVt.child_window(title="User name:",
                                                                   control_type="Edit").wrapper_object()
                    time.sleep(0.2)
                    user.type_keys('students', with_spaces=False)
                    self.hide_loading_screen()
                    okConn2 = self.uprb.UprbayTeraTermVt.child_window(title="OK",
                                                                      control_type="Button").wrapper_object()
                    okConn2.click_input()
                    self.show_loading_screen_again()
                    time.sleep(3)
                    send_keys("{ENTER 3}")
                    self.set_focus_to_tkinter()
                    self.student_frame.grid(row=0, column=1, padx=(20, 20), pady=(20, 0))
                    self.student_frame.grid_columnconfigure(2, weight=1)
                    self.s_buttons_frame.grid(row=2, column=1, padx=(20, 20), pady=(20, 0))
                    self.s_buttons_frame.grid_columnconfigure(2, weight=1)
                    self.explanation3.grid(row=0, column=1, padx=12, pady=(10, 20))
                    self.lock_grid.grid(row=1, column=1, padx=(0, 0), pady=(0, 20))
                    if lang == "English":
                        self.ssn.grid(row=2, column=1, padx=(0, 128), pady=(0, 10))
                        self.ssn_entry.grid(row=2, column=1, padx=(160, 0), pady=(0, 10))
                        self.code_entry.grid(row=3, column=1, padx=(160, 0), pady=(0, 10))
                    elif lang == "Español":
                        self.ssn.grid(row=2, column=1, padx=(0, 136), pady=(0, 10))
                        self.ssn_entry.grid(row=2, column=1, padx=(170, 0), pady=(0, 10))
                        self.code_entry.grid(row=3, column=1, padx=(170, 0), pady=(0, 10))
                    self.code.grid(row=3, column=1, padx=(0, 165), pady=(0, 10))
                    self.show.grid(row=4, column=1, padx=(10, 0), pady=(0, 10))
                    self.back2.grid(row=5, column=0, padx=(0, 10), pady=(0, 0))
                    self.system.grid(row=5, column=1, padx=(10, 0), pady=(0, 0))
                    self.a_buttons_frame.grid_forget()
                    self.authentication_frame.grid_forget()
                elif username != "students":
                    self.bind("<Return>", lambda event: self.student_event_handler())
                    if lang == "English":
                        self.show_error_message(300, 215, "Error! Invalid username")
                    elif lang == "Español":
                        self.show_error_message(300, 215, "¡Error! Usuario Incorrecto")
            else:
                self.bind("<Return>", lambda event: self.student_event_handler())
                if lang == "English":
                    self.show_error_message(300, 215, "Error! Tera Term is disconnected")
                elif lang == "Español":
                    self.show_error_message(300, 215, "¡Error! Tera Term esta desconnectado")
        block_window.destroy()
        task_done.set()

    def login_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.login_event, args=(task_done,))
        event_thread.start()

    # Checks if host entry is true
    def login_event(self, task_done):
        block_window = customtkinter.CTkToplevel()
        block_window.attributes("-alpha", 0.0)
        block_window.grab_set()
        if self.information and self.information.winfo_exists():
            if self.information:
                self.information.destroy()
        lang = self.language_menu.get()
        host = self.host_entry.get().replace(" ", "").lower()
        self.bind("<Return>", lambda event: self.student_event_handler())
        if self.test_connection(lang) and self.check_server():
            if host == "uprbay.uprb.edu" or host == "uprbayuprbedu":
                if self.checkIfProcessRunning("ttermpro"):
                    self.bind("<Return>", lambda event: self.login_event_handler())
                    if lang == "English":
                        self.show_error_message(450, 265, "Error! Cannot connect to server \n\n"
                                                          " if another instance of Tera Term"
                                                          " is already running")
                    elif lang == "Español":
                        self.show_error_message(450, 265, "¡Error! No es posible"
                                                          " conectarse al servidor \n\n"
                                                          " si otra instancia de Tera Term ya esta corriendo")
                else:
                    try:
                        ctypes.windll.user32.BlockInput(True)
                        self.uprb = Application(backend="uia").start(self.location) \
                            .connect(title="Tera Term - [disconnected] VT", timeout=100)
                        uprb_window = self.uprb.window(title="Tera Term - [disconnected] VT")
                        uprb_window.wait('visible', timeout=100)
                        hostText = self.uprb.TeraTermDisconnectedVt.child_window(title="Host:",
                                                                                 control_type="Edit").wrapper_object()
                        hostText.type_keys('uprbay.uprb.edu', with_spaces=False)
                        self.hide_loading_screen()
                        okConn1 = self.uprb.TeraTermDisconnectedVt.child_window(title="OK",
                                                                                control_type="Button").wrapper_object()
                        okConn1.click_input()
                        self.show_loading_screen_again()
                        uprb_window_new = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                        uprb_window_new.wait('visible', timeout=100)
                        continue_button = uprb_window_new.child_window(title="Continue", control_type="Button")
                        if continue_button.exists():
                            self.hide_loading_screen()
                            continue_button = continue_button.wrapper_object()
                            continue_button.click_input()
                            self.show_loading_screen_again()
                        ctypes.windll.user32.BlockInput(False)
                        self.set_focus_to_tkinter()
                        self.authentication_frame.grid(row=0, column=1, columnspan=2, padx=(20, 20), pady=(20, 0))
                        self.authentication_frame.grid_columnconfigure(2, weight=1)
                        self.a_buttons_frame.grid(row=2, column=1, columnspan=2, padx=(20, 20), pady=(20, 0))
                        self.a_buttons_frame.grid_columnconfigure(2, weight=1)
                        self.explanation.grid(row=0, column=0, padx=12, pady=10)
                        self.uprb_image_grid.grid(row=1, column=0, padx=12, pady=10)
                        self.explanation2.grid(row=2, column=0, padx=12, pady=(30, 0))
                        if lang == "English":
                            self.username.grid(row=3, column=0, padx=(0, 130), pady=(0, 10))
                            self.username_entry.grid(row=3, column=0, padx=(90, 0), pady=(0, 10))
                        elif lang == "Español":
                            self.username.grid(row=3, column=0, padx=(0, 140), pady=(0, 10))
                            self.username_entry.grid(row=3, column=0, padx=(60, 0), pady=(0, 10))
                        self.back.grid(row=4, column=0, padx=(0, 10), pady=(0, 0))
                        self.student.grid(row=4, column=1, padx=(10, 0), pady=(0, 0))
                        self.language_menu.configure(state="disabled")
                        self.host.grid_forget()
                        self.host_entry.grid_forget()
                        self.log_in.grid_forget()
                        self.intro_box.grid_forget()
                        self.introduction.grid_forget()
                    except Exception as e:
                        if e.__class__.__name__ == "AppStartError":
                            self.bind("<Return>", lambda event: self.login_event_handler())
                            if lang == "English":
                                self.show_error_message(450, 330, "Error! Cannot start application.\n\n "
                                                                  "The location of your Tera Term \n\n"
                                                                  " might be different from the default,\n\n "
                                                                  "click the \"Help\" button "
                                                                  "to find it the location")
                            elif lang == "Español":
                                self.show_error_message(450, 330, "¡Error! No se pudo iniciar la aplicación."
                                                                  "\n\n La localización de tu "
                                                                  "Tera Term\n\n"
                                                                  " es diferente de la normal, \n\n "
                                                                  "presiona el botón de \"Ayuda\""
                                                                  "para encontrarlo")
                    except Application.timings.TimeoutError:
                        self.bind("<Return>", lambda event: self.login_event_handler())
                        if lang == "English":
                            self.show_error_message(450, 265, "Error! Unable to find Tera Term window.")
                        elif lang == "Español":
                            self.show_error_message(450, 265, "¡Error! No se puede encontrar la ventana de Tera Term.")
            elif host != "uprbay.uprb.edu":
                self.bind("<Return>", lambda event: self.login_event_handler())
                if lang == "English":
                    self.show_error_message(300, 215, "Error! Invalid host")
                elif lang == "Español":
                    self.show_error_message(300, 215, "¡Error! Servidor Incorrecto")
        block_window.destroy()
        task_done.set()

    # function that lets user go back to the initial screen
    def go_back_event(self):
        lang = self.language_menu.get()
        if lang == "English":
            msg = CTkMessagebox(master=self, title="Go back?",
                                message="Are you sure you want to go back? "
                                        " \n\n""WARNING: (Tera Term will close)",
                                icon="question",
                                option_1="Cancel", option_2="No", option_3="Yes",
                                icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
        elif lang == "Español":
            msg = CTkMessagebox(master=self, title="¿Ir atrás?",
                                message="¿Estás seguro que quieres ir atrás?"
                                        " \n\n""WARNING: (Tera Term va a cerrar)",
                                icon="question",
                                option_1="Cancelar", option_2="No", option_3="Sí",
                                icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
        response = msg.get()
        if self.checkIfProcessRunning("ttermpro") and response == "Yes" or response == "Sí":
            uprb = Application(backend='uia').connect(title="uprbay.uprb.edu - Tera Term VT", timeout=100)
            uprb.kill(soft=False)
        if response == "Yes" or response == "Sí":
            self.stop_thread()
            self.reset_activity_timer(None)
            self.bind("<Return>", lambda event: self.login_event_handler())
            if self.language_menu.get() == "Español":
                self.host.grid(row=2, column=0, columnspan=2, padx=(0, 5), pady=(20, 20))
            elif self.language_menu.get() == "English":
                self.host.grid(row=2, column=0, columnspan=2, padx=(30, 0), pady=(20, 20))
            self.go_next_1VE.configure(state="disabled")
            self.go_next_1GP.configure(state="disabled")
            self.go_next_409.configure(state="disabled")
            self.go_next_683.configure(state="disabled")
            self.go_next_4CM.configure(state="disabled")
            self.introduction.grid(row=0, column=1, columnspan=2, padx=(20, 0), pady=(20, 0))
            self.host_entry.grid(row=2, column=1, padx=(20, 0), pady=(20, 20))
            self.log_in.grid(row=3, column=1, padx=(20, 0), pady=(20, 20))
            self.intro_box.grid(row=1, column=1, padx=(20, 0), pady=(0, 0))
            self.authentication_frame.grid_forget()
            self.student_frame.grid_forget()
            self.a_buttons_frame.grid_forget()
            self.s_buttons_frame.grid_forget()
            self.tabview.grid_forget()
            self.t_buttons_frame.grid_forget()
            self.multiple_frame.grid_forget()
            self.m_button_frame.grid_forget()
            self.username_entry.delete(0, "end")
            self.ssn_entry.delete(0, "end")
            self.code_entry.delete(0, "end")
            self.ssn_entry.configure(placeholder_text="#########")
            self.code_entry.configure(placeholder_text="####")
            self.ssn_entry.configure(show="*")
            self.code_entry.configure(show="*")
            self.language_menu.configure(state="normal")
            self.multiple.configure(state="normal")
            self.submit.configure(state="normal")
            self.show_classes.configure(state="normal")
            self.search.configure(state="normal")
            self.multiple.configure(state="normal")
            self.show.deselect()
            self.screenshot_skip = False
            self.error_occurred = False
            self.run_fix = False

    # function that goes back to Enrolling frame screen
    def go_back_event2(self):
        self.unbind("<Return>")
        scaling = self.scaling_optionemenu.get()
        lang = self.language_menu.get()
        self.scaling_optionemenu.configure(state="normal")
        if scaling not in ("90%", "95%", "100%"):
            self.change_scaling_event(scaling)
        self.tabview.grid(row=0, column=1, padx=(20, 20), pady=(20, 0), sticky="n")
        self.tabview.tab(self.enroll_tab).grid_columnconfigure(1, weight=2)
        self.tabview.tab(self.search_tab).grid_columnconfigure(1, weight=2)
        self.tabview.tab(self.other_tab).grid_columnconfigure(1, weight=2)
        self.t_buttons_frame.grid(row=2, column=1, padx=(20, 20), pady=(20, 0), sticky="n")
        self.t_buttons_frame.grid_columnconfigure(2, weight=1)
        self.explanation4.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
        if lang == "English":
            self.e_classes.grid(row=1, column=1, padx=(41, 0), pady=(0, 0), sticky="w")
        elif lang == "Español":
            self.e_classes.grid(row=1, column=1, padx=(44, 0), pady=(0, 0), sticky="w")
        self.e_classes_entry.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        self.section.grid(row=2, column=1, padx=(30, 0), pady=(20, 0), sticky="w")
        self.section_entry.grid(row=2, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
        if lang == "English":
            self.e_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0), sticky="w")
        elif lang == "Español":
            self.e_semester.grid(row=3, column=1, padx=(21, 0), pady=(20, 0), sticky="w")
        self.e_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
        self.register_menu.grid(row=4, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
        self.submit.grid(row=5, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
        self.explanation5.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
        if lang == "English":
            self.s_classes.grid(row=1, column=1, padx=(42, 0), pady=(0, 0), sticky="w")
        elif lang == "Español":
            self.s_classes.grid(row=1, column=1, padx=(43, 0), pady=(0, 0), sticky="w")
        self.s_classes_entry.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        self.s_semester.grid(row=2, column=1, padx=(20, 0), pady=(20, 0), sticky="w")
        self.s_semester_entry.grid(row=2, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
        self.show_all.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
        self.search.grid(row=4, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
        self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
        self.menu_intro.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        if lang == "English":
            self.menu.grid(row=2, column=1, padx=(44, 0), pady=(10, 0), sticky="w")
        elif lang == "Español":
            self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
        self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
        self.menu_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0), sticky="w")
        self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
        self.menu_submit.grid(row=5, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
        self.back3.grid(row=4, column=0, padx=(0, 10), pady=(0, 0), sticky="w")
        self.show_classes.grid(row=4, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        self.multiple.grid(row=4, column=2, padx=(10, 0), pady=(0, 0), sticky="s")
        self.go_next_409.grid_forget()
        self.go_next_683.grid_forget()
        self.go_next_1GP.grid_forget()
        self.go_next_1VE.grid_forget()
        self.go_next_4CM.grid_forget()
        self.multiple_frame.grid_forget()
        self.m_button_frame.grid_forget()

    # function for changing language
    def change_language_event(self, lang):
        if lang == "Español":
            self.sidebar_button_1.configure(text="     Estado")
            self.sidebar_button_2.configure(text="      Ayuda")
            self.scaling_label.configure(text="Lenguaje, Apariencia y \n\n "
                                              "Ajuste de UI:")
            self.intro_box.configure(state="normal")
            self.intro_box.delete("1.0", "end")
            self.intro_box.insert("0.0", "¡Bienvenido a la aplicación de interfaz de usuario de Tera Term!\n\n" +
                                  "El propósito de esta aplicación"
                                  " es facilitar el proceso de inscripción y baja de clases, "
                                  "dado que Tera Term usa la interfaz de terminal, "
                                  "es difícil nuevos usuarios usar y "
                                  "aprender a navegar y hacer cosas en "
                                  "Tera Term. "
                                  "Esta aplicación tiene una interfaz de usuario muy agradable "
                                  "y limpia que la mayoría de los usuarios conocen.\n\n" +
                                  "Hay algunas cosas que debes saber antes de usar esta app: \n\n" +
                                  "La aplicación se encuentra en una etapa muy temprana de desarrollo, "
                                  "lo que significa que aún le faltan cosas que"
                                  "arreglar e implementar. "
                                  "En este momento, las aplicaciones te permiten hacer "
                                  "lo esencial como inscribirte y darte de baja"
                                  "clases"
                                  ", la búsqueda de clases y otras funciones se implementará más adelante en el camino"
                                  "la prioridad en este momento es obtener la experiencia del usuario correcta, "
                                  "todo debe verse bien"
                                  " y fácil de entender. "
                                  + "Todo lo que se ingrese aquí se almacena localmente, "
                                    "lo que significa que solo usted puede acceder la "
                                    "información"
                                    "a sí que no tendrás que preocuparte"
                                    "por información sensible ya que cosas"
                                    "como el Número de Seguro Social, está "
                                    "encriptado usando una clave asimétrica. \n\n" +
                                  "Gracias por usar nuestra aplicación, para más información, "
                                  "ayuda y para personalizar tu"
                                  "experiencia"
                                  "asegúrese de hacer clic en los botones de la barra lateral, "
                                  "la aplicación también es de código abierto"
                                  "para cualquiera que esté interesado en trabajar/ver el proyecto. \n\n" +
                                  "IMPORTANTE: NO UTILIZAR MIENTRAS TENGA OTRA INSTANCIA DE LA APLICACIÓN ABIERTA. ")
            self.intro_box.configure(state="disabled")
            self.introduction.configure(text="UPRB Proceso de Matrícula")
            self.host.configure(text="Servidor: ")
            self.host.grid(row=2, column=0, columnspan=2, padx=(0, 5), pady=(20, 20))
            self.log_in.configure(text="Iniciar Sesión")
            self.explanation.configure(text="Conectado al servidor éxitosamente")
            self.explanation2.configure(text="Autenticación requerida")
            self.username.configure(text="Usuario: ")
            self.student.configure(text="Próximo")
            self.back.configure(text="Atrás")
            self.explanation3.configure(text="Información para entrar al Sistema")
            self.ssn.configure(text="Número de Seguro Social: ")
            self.code.configure(text="Código Identificación Personal: ")
            self.show.configure(text="¿Enseñar?")
            self.system.configure(text="Entrar")
            self.back2.configure(text="Atrás")
            self.explanation4.configure(text="Matricular Clases: ")
            self.e_classes.configure(text="Clase: ")
            self.section.configure(text="Sección: ")
            self.e_semester.configure(text="Semestre: ")
            self.register_menu.configure(values=["Registra", "Baja"])
            self.register_menu.set("Registra")
            self.explanation5.configure(text="Buscar Clases: ")
            self.s_classes.configure(text="Clase: ")
            self.s_semester.configure(text="Semestre: ")
            self.show_all.configure(text="¿Enseñar Todas?")
            self.explanation6.configure(text="Menú de Opciones: ")
            self.menu_intro.configure(text="Selecciona el Código de la pantalla \n"
                                           "A la que quieres acceder")
            self.menu.configure(text="Código:")
            self.menu_entry.configure(values=["SRM (Menú Principal)", "004 (Hold Flags)", "1GP (Programa de Clases)",
                                              "118 (Estadísticas Académicas)", "1VE (Expediente Académico)",
                                              "3DD (Historial de Pagos de Beca)", "409 (Balance de Cuenta)",
                                              "683 (Evaluación Académica)", "1PL (Datos Básicos)",
                                              "4CM (Cómputo de Matrícula)", "4SP (Solicitud de Prórroga)",
                                              "SO (Cerrar Sesión)"])
            self.menu_entry.set("SRM (Menú Principal)")
            self.menu_semester.configure(text="Semestre:")
            self.menu_submit.configure(text="Someter")
            self.go_next_1VE.configure(text="Próxima Página")
            self.go_next_1GP.configure(text="Próxima Página")
            self.go_next_409.configure(text="Próxima Página")
            self.go_next_683.configure(text="Próxima Página")
            self.go_next_4CM.configure(text="Próxima Página")
            self.submit.configure(text="Someter")
            self.search.configure(text="Buscar")
            self.show_classes.configure(text="Enseñar Mis Clases")
            self.back3.configure(text="Atrás")
            self.multiple.configure(text="Múltiples Clases")
            self.explanation7.configure(text="Matricular Múltiples Clases a la misma vez:")
            self.warning.configure(text="*¡Solamente puedes someter una vez!*")
            self.back4.configure(text="Atrás")
            self.submit_multiple.configure(text="Someter")
            self.m_classes_entry.configure(placeholder_text="Clase")
            self.m_section_entry.configure(placeholder_text="Sección")
            self.m_register_menu.configure(values=["Registra", "Baja"])
            self.m_register_menu.set("Escoge")
            self.m_classes_entry2.configure(placeholder_text="Clase")
            self.m_section_entry2.configure(placeholder_text="Sección")
            self.m_register_menu2.configure(values=["Registra", "Baja"])
            self.m_register_menu2.set("Escoge")
            self.m_classes_entry3.configure(placeholder_text="Clase")
            self.m_section_entry3.configure(placeholder_text="Sección")
            self.m_register_menu3.configure(values=["Registra", "Baja"])
            self.m_register_menu3.set("Escoge")
            self.m_classes_entry4.configure(placeholder_text="Clase")
            self.m_section_entry4.configure(placeholder_text="Sección")
            self.m_register_menu4.configure(values=["Registra", "Baja"])
            self.m_register_menu4.set("Escoge")
            self.m_classes_entry5.configure(placeholder_text="Clase")
            self.m_section_entry5.configure(placeholder_text="Sección")
            self.m_register_menu5.configure(values=["Registra", "Baja"])
            self.m_register_menu5.set("Escoge")
            self.m_classes_entry6.configure(placeholder_text="Clase")
            self.m_section_entry6.configure(placeholder_text="Sección")
            self.m_register_menu6.configure(values=["Registra", "Baja"])
            self.m_register_menu6.set("Escoge")
            self.host_tooltip.configure(message="Ingrese el nombre del servidor\n de la universidad")
            self.username_tooltip.configure(message="La universidad requiere esto \npara entrar y acceder \nel sistema")
            self.ssn_tooltip.configure(message="Requerido para iniciar sesión,\n la información se encripta")
            self.code_tooltip.configure(message="Código de 4 dígitos incluido en\n"
                                                " el correo electrónico del \nticket de pre-matrícula")
            self.back_tooltip.configure(message="Volver al menú principal\n"
                                                " de la aplicación")
            self.back2_tooltip.configure(message="Volver al menú principal\n"
                                                 " de la aplicación")
            self.back3_tooltip.configure(message="Volver al menú principal\n"
                                                 " de la aplicación")
            self.back4_tooltip.configure(message="Volver a la pantalla "
                                                 "\nanterior")
            self.show_all_tooltip.configure(message="Muestre todas las secciones\n"
                                                    "o solamente las que están\n"
                                                    "abiertas")
            self.show_classes_tooltip.configure(message="Enseña las clases que tienes\n"
                                                        "matriculadas en un semestre")
            self.m_add_tooltip.configure(message="Añade más clases")
            self.m_remove_tooltip.configure(message="Eliminar clases")
            self.multiple_tooltip.configure(message="Matricula múltiples \nclases"
                                                    " a la misma vez")
        elif lang == "English":
            self.sidebar_button_1.configure(text="     Status")
            self.sidebar_button_2.configure(text="       Help")
            self.scaling_label.configure(text="Language, Appearance and \n\n "
                                              "UI Scaling ")
            self.intro_box.configure(state="normal")
            self.intro_box.delete("1.0", "end")
            self.intro_box.insert("0.0", "Welcome to the Tera Term UI Application!\n\n" +
                                  "The purpose of this application"
                                  " is to facilitate the process enrolling and dropping classes, "
                                  "since Tera Term uses Terminal interface, "
                                  "it's hard for new users to use and learn how to navigate and do stuff in "
                                  "Tera Term. "
                                  "This application has a very nice and clean user interface that most users are "
                                  "used to.\n\n" +
                                  "There's a few things you should know before using this tool: \n\n" +
                                  "The application is very early in development, "
                                  "which means it still got things to work, "
                                  "fix and implement. "
                                  "Right now, the applications lets you do the essentials like enrolling and dropping "
                                  " classes"
                                  ", searching for classes other functionally will be implemented later down the road "
                                  " the priority right now is getting the user experience right, "
                                  "everything must looks nice"
                                  " and be easy to understand. "
                                  + "Everything you input here is stored locally meaning only you can access the "
                                    "information"
                                    " so you will not have to worry about securities issues "
                                    "plus for sensitive information "
                                    "like the Social Security Number it's encrypted using a asymmetric-key. \n\n" +
                                  "Thanks for using our application, for more information, help and to customize your "
                                  "experience"
                                  " make sure to click the buttons on the sidebar, the application is also open source"
                                  " for anyone who is interested in working/seeing the project. \n\n" +
                                  "IMPORTANT: DO NOT USE WHILE HAVING ANOTHER INSTANCE OF THE APPLICATION OPENED.")
            self.intro_box.configure(state="disabled")
            self.appearance_mode_optionemenu.configure(values=["Light", "Dark", "System"])
            self.introduction.configure(text="UPRB Enrollment Process")
            self.host.configure(text="Host: ")
            self.host.grid(row=2, column=0, columnspan=2, padx=(30, 0), pady=(20, 20))
            self.log_in.configure(text="Log-In")
            self.explanation.configure(text="Connected to the server successfully")
            self.explanation2.configure(text="Authentication required")
            self.username.configure(text="Username: ")
            self.student.configure(text="Next")
            self.back.configure(text="Back")
            self.explanation3.configure(text="Information to enter the System")
            self.ssn.configure(text="Social Security Number: ")
            self.code.configure(text="Code of Personal Information: ")
            self.show.configure(text="Show?")
            self.system.configure(text="Enter")
            self.back2.configure(text="Back")
            self.explanation4.configure(text="Enroll for Classes: ")
            self.e_classes.configure(text="Class: ")
            self.section.configure(text="Section: ")
            self.e_semester.configure(text="Semester: ")
            self.register_menu.configure(values=["Register", "Drop"])
            self.register_menu.set("Register")
            self.explanation5.configure(text="Search for Classes: ")
            self.s_classes.configure(text="Class: ")
            self.s_semester.configure(text="Semester: ")
            self.show_all.configure(text="Show All?")
            self.submit.configure(text="Submit")
            self.search.configure(text="Search")
            self.explanation6.configure(text="Option Menu: ")
            self.menu_intro.configure(text="Select code for the screen\n"
                                           " you want to go to: ")
            self.menu.configure(text="Code:")
            self.menu_entry.configure(values=["SRM (Main Menu)", "004 (Hold Flags)",
                                              "1GP (Class Schedule)", "118 (Academic Staticstics)",
                                              "1VE (Academic Record)", "3DD (Scholarship Payment Record)",
                                              "409 (Account Balance)", "683 (Academic Evaluation)",
                                              "1PL (Basic Personal Data)", "4CM (Tuition Calculation)",
                                              "4SP (Apply for Extension)", "SO (Sign out)"])
            self.menu_entry.set("SRM (Main Menu)")
            self.menu_semester.configure(text="Semester:")
            self.menu_submit.configure(text="Submit")
            self.go_next_1VE.configure(text="Next Page")
            self.go_next_1GP.configure(text="Next Page")
            self.go_next_409.configure(text="Next Page")
            self.go_next_683.configure(text="Next Page")
            self.go_next_4CM.configure(text="Next Page")
            self.show_classes.configure(text="Show My Classes")
            self.back3.configure(text="Back")
            self.multiple.configure(text="Multiple Classes")
            self.explanation7.configure(text="Enroll Multiple Classes at once:")
            self.warning.configure(text="*You can only submit once!*")
            self.back4.configure(text="Back")
            self.submit_multiple.configure(text="Submit")
            self.m_classes_entry.configure(placeholder_text="Class")
            self.m_section_entry.configure(placeholder_text="Section")
            self.m_register_menu.configure(values=["Register", "Drop"])
            self.m_register_menu.set("Choose")
            self.m_classes_entry2.configure(placeholder_text="Class")
            self.m_section_entry2.configure(placeholder_text="Section")
            self.m_register_menu2.configure(values=["Register", "Drop"])
            self.m_register_menu2.set("Choose")
            self.m_classes_entry3.configure(placeholder_text="Class")
            self.m_section_entry3.configure(placeholder_text="Section")
            self.m_register_menu3.configure(values=["Register", "Drop"])
            self.m_register_menu3.set("Choose")
            self.m_classes_entry4.configure(placeholder_text="Class")
            self.m_section_entry4.configure(placeholder_text="Section")
            self.m_register_menu4.configure(values=["Register", "Drop"])
            self.m_register_menu4.set("Choose")
            self.m_classes_entry5.configure(placeholder_text="Class")
            self.m_section_entry5.configure(placeholder_text="Section")
            self.m_register_menu5.configure(values=["Register", "Drop"])
            self.m_register_menu5.set("Choose")
            self.m_classes_entry6.configure(placeholder_text="Class")
            self.m_section_entry6.configure(placeholder_text="Section")
            self.m_register_menu6.configure(values=["Register", "Drop"])
            self.m_register_menu6.set("Choose")
            self.host_tooltip.configure(message="Enter the name of the server\n of the university")
            self.username_tooltip.configure(message="The university requires this to\n"
                                                    " enter and access the system")
            self.ssn_tooltip.configure(message="Required to log-in,\n"
                                               "information gets encrypted")
            self.code_tooltip.configure(message="4 digit code included in the\n"
                                                "pre-enrollment ticket email")
            self.back_tooltip.configure(message="Go back to the main menu\n"
                                                "of the application")
            self.back2_tooltip.configure(message="Go back to the main menu\n"
                                                 "of the application")
            self.back3_tooltip.configure(message="Go back to the main menu\n"
                                                 "of the application")
            self.back4_tooltip.configure(message="Go back to the previous "
                                                 "\nscreen")
            self.show_classes_tooltip.configure(message="Shows the classes you are\n "
                                                        "enrolled in for a \n"
                                                        "specific semester")
            self.show_all_tooltip.configure(message="Display all sections or\n"
                                                    "only ones with spaces")
            self.m_add_tooltip.configure(message="Add more classes")
            self.m_remove_tooltip.configure(message="Remove classes")
            self.multiple_tooltip.configure(message="Enroll multiple classes\nat once")

    # saves the information to the database when the app closes
    def save_user_data(self):
        host = self.host_entry.get()
        resultWelcome = self.cursor.execute("SELECT welcome FROM user_data").fetchall()
        if len(resultWelcome) == 0:
            self.cursor.execute("INSERT INTO user_data (welcome) VALUES (?)", ("Checked",))
        elif len(resultWelcome) == 1:
            self.cursor.execute("UPDATE user_data SET welcome=?", ("Checked",))
        resultHost = self.cursor.execute("SELECT host FROM user_data").fetchall()
        if len(resultHost) == 0 and host == "uprbay.uprb.edu":
            self.cursor.execute("INSERT INTO user_data (host) VALUES (?) ", (host,))
        elif len(resultHost) == 1 and host == "uprbay.uprb.edu":
            self.cursor.execute("UPDATE user_data SET host=?", (host,))
        resultLang = self.cursor.execute("SELECT language FROM user_data").fetchall()
        if len(resultLang) == 0:
            self.cursor.execute("INSERT INTO user_data (language) VALUES (?) ", (self.language_menu.get(),))
        elif len(resultLang) == 1:
            self.cursor.execute("UPDATE user_data SET language=?", (self.language_menu.get(),))
        resultAppearance = self.cursor.execute("SELECT appearance FROM user_data").fetchall()
        if len(resultAppearance) == 0:
            self.cursor.execute("INSERT INTO user_data (appearance) VALUES (?) ",
                                (self.appearance_mode_optionemenu.get(),))
        elif len(resultAppearance) == 1:
            self.cursor.execute("UPDATE user_data SET appearance=?", (self.appearance_mode_optionemenu.get(),))
        resultScaling = self.cursor.execute("SELECT scaling FROM user_data").fetchall()
        if len(resultScaling) == 0:
            self.cursor.execute("INSERT INTO user_data (scaling) VALUES (?) ",
                                (self.scaling_optionemenu.get(),))
        elif len(resultScaling) == 1:
            self.cursor.execute("UPDATE user_data SET scaling=?", (self.scaling_optionemenu.get(),))
        with closing(sqlite3.connect("database.db")) as connection:
            with closing(connection.cursor()) as self.cursor:
                self.connection.commit()

    # shows the important information window
    def show_loading_screen(self):
        lang = self.language_menu.get()
        self.loading_screen = customtkinter.CTkToplevel(self)
        self.loading_screen.grab_set()
        if lang == "English":
            self.loading_screen.title("Loading...")
        if lang == "Español":
            self.loading_screen.title("Cargando...")
        self.loading_screen.overrideredirect(True)
        width = 275
        height = 150
        self.loading_screen.update_idletasks()
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        loading_screen_width = width
        loading_screen_height = height
        center_x = main_window_x + (main_window_width // 2) - (loading_screen_width // 2)
        center_y = main_window_y + (main_window_height // 2) - (loading_screen_height // 2)
        self.loading_screen.geometry(f"{width}x{height}+{center_x + 105}+{center_y}")
        self.loading_screen.attributes("-topmost", True, "-alpha", 0.90)
        self.loading_screen.resizable(False, False)
        self.loading_screen.after(256, lambda: self.loading_screen.iconbitmap("images/tera-term.ico"))
        if lang == "English":
            loading = customtkinter.CTkLabel(self.loading_screen, text="Loading...",
                                             font=customtkinter.CTkFont(size=20, weight="bold"))
            loading.pack(pady=30)
        if lang == "Español":
            loading = customtkinter.CTkLabel(self.loading_screen, text="Cargando...",
                                             font=customtkinter.CTkFont(size=20, weight="bold"))
            loading.pack(pady=30)
        self.progress_bar = customtkinter.CTkProgressBar(self.loading_screen, mode="indeterminate",
                                                         height=15, width=230, indeterminate_speed=1.5)
        self.progress_bar.pack(pady=1)
        self.progress_bar.start()
        return self.loading_screen

    # hides the loading screen
    def hide_loading_screen(self):
        self.loading_screen.withdraw()

    # bring the loading screen back
    def show_loading_screen_again(self):
        self.loading_screen.deiconify()

    # tells the loading screen when it should stop and close
    def update_loading_screen(self, loading_screen, task_done):
        if task_done.is_set():
            self.progress_bar.stop()
            loading_screen.destroy()
        else:
            self.after(100, self.update_loading_screen, loading_screen, task_done)

    # function that lets user see/hide their input (hidden by default)
    def show_event(self):
        show = self.show.get()
        if show == "on":
            self.ssn_entry.configure(show="")
            self.code_entry.configure(show="")
        elif show == "off":
            self.ssn_entry.configure(show="*")
            self.code_entry.configure(show="*")

    # function that checks if Tera Term is running or not
    def checkIfProcessRunning(self, processName):
        for proc in psutil.process_iter():
            try:
                if processName.lower() in proc.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    # checks if the specified window exists
    def window_exists(self, title):
        try:
            window = gw.getWindowsWithTitle(title)[0]
            return True
        except IndexError:
            return False

    # function that checks if UPRB server is currently running
    def check_server(self):
        lang = self.language_menu.get()
        HOST = "uprbay.uprb.edu"
        PORT = 22
        timeout = 3

        try:
            with socket.create_connection((HOST, PORT), timeout=timeout) as sock:
                # the connection attempt succeeded
                return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            # the connection attempt failed
            if lang == "English":
                self.show_error_message(300, 215, "Error! UPRB server is currently down")
            elif lang == "Español":
                self.show_error_message(300, 215, "¡Error! El servidor de la UPRB\nestá actualmente caído")
            return False

    # captures a screenshot of tera term and performs OCR
    def capture_screenshot(self):
        window_title = "uprbay.uprb.edu - Tera Term VT"
        hwnd = win32gui.FindWindow(None, window_title)
        win32gui.SetForegroundWindow(hwnd)
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        x, y = win32gui.ClientToScreen(hwnd, (left, top))
        width = right - left
        height = bottom - top
        self.hide_loading_screen()
        time.sleep(0.2)
        screenshot = pyautogui.screenshot(region=(x, y - 50, width + 150, height + 150))
        self.show_loading_screen_again()
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        img = Image.fromarray(img)
        # img.save("img.png")
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img, config=custom_config)
        return text

    # error window pop up message
    def show_error_message(self, width, height, error_msg_text):
        if self.error and self.error.winfo_exists():
            self.error.lift()
            return
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        scaling_factor = self.tk.call("tk", "scaling")
        x_position = int((screen_width - width * scaling_factor) / 2)
        y_position = int((screen_height - height * scaling_factor) / 2)
        window_geometry = f"{width}x{height}+{x_position + 175}+{y_position - 75}"
        winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
        self.error = customtkinter.CTkToplevel(self)
        self.error.title("Error")
        self.error.geometry(window_geometry)
        self.error.attributes("-topmost", True)
        self.error.resizable(False, False)
        self.error.after(256, lambda: self.error.iconbitmap("images/tera-term.ico"))

        my_image = customtkinter.CTkImage(light_image=Image.open("images/error.png"),
                                          dark_image=Image.open("images/error.png"),
                                          size=(100, 100))
        image = customtkinter.CTkLabel(self.error, text="", image=my_image)
        image.pack(padx=10, pady=20)
        error_msg = customtkinter.CTkLabel(self.error,
                                           text=error_msg_text,
                                           font=customtkinter.CTkFont(size=15, weight="bold"))
        error_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)

    # success window pop up message
    def show_success_message(self, width, height, success_msg_text):
        if self.success and self.success.winfo_exists():
            self.success.lift()
            return
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        scaling_factor = self.tk.call("tk", "scaling")
        x_position = int((screen_width - width * scaling_factor) / 2)
        y_position = int((screen_height - height * scaling_factor) / 2)
        window_geometry = f"{width}x{height}+{x_position + 175}+{y_position - 75}"
        winsound.PlaySound("sounds/success.wav", winsound.SND_ASYNC)
        self.success = customtkinter.CTkToplevel()
        self.success.geometry(window_geometry)
        self.success.title("Success")
        self.success.attributes("-topmost", True)
        self.success.resizable(False, False)
        self.success.after(256, lambda: self.success.iconbitmap("images/tera-term.ico"))
        my_image = customtkinter.CTkImage(light_image=Image.open("images/success.png"),
                                          dark_image=Image.open("images/success.png"),
                                          size=(200, 150))
        image = customtkinter.CTkLabel(self.success, text="", image=my_image)
        image.pack(padx=10, pady=10)
        success_msg = customtkinter.CTkLabel(self.success, text=success_msg_text,
                                             font=customtkinter.CTkFont(size=15, weight="bold"))
        success_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)
        self.success.after(3000, lambda: self.success.destroy())

    def show_enrollment_error_information(self):
        lang = self.language_menu.get()
        winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
        if lang == "English":
            CTkMessagebox(master=self, title="Error Information",
                          message="This is error is usually caused because it isn't time "
                                  "yet for you to be able to enroll classes or because the "
                                  "TERM you selected is outdated", icon="question", button_width=380)
        if lang == "Español":
            CTkMessagebox(master=self, title="Información del Error",
                          message="Este error generalmente se debe a que todavía "
                                  "no es su turno para inscribirse en clases o porque el "
                                  "término que seleccionó está desactualizado", icon="question", button_width=380)

    # important information window pop up message
    def show_information_message(self, width, height, success_msg_text):
        if self.information and self.information.winfo_exists():
            self.information.lift()
            return
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        scaling_factor = self.tk.call("tk", "scaling")
        x_position = int((screen_width - width * scaling_factor) / 2)
        y_position = int((screen_height - height * scaling_factor) / 2)
        window_geometry = f"{width}x{height}+{x_position + 175}+{y_position - 75}"
        winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
        self.information = customtkinter.CTkToplevel()
        self.information.geometry(window_geometry)
        self.information.title("Information")
        self.information.attributes("-topmost", True)
        self.information.resizable(False, False)
        self.information.after(256, lambda: self.information.iconbitmap("images/tera-term.ico"))
        my_image = customtkinter.CTkImage(light_image=Image.open("images/info.png"),
                                          dark_image=Image.open("images/info.png"),
                                          size=(100, 100))
        image = customtkinter.CTkLabel(self.information, text="", image=my_image)
        image.pack(padx=10, pady=10)
        information_msg = customtkinter.CTkLabel(self.information, text=success_msg_text,
                                                 font=customtkinter.CTkFont(size=15, weight="bold"))
        information_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)

    def total_classes_enrolled(self):
        lang = self.language_menu.get()
        if lang == "English":
            while True:
                classes_enrolled = customtkinter.CTkInputDialog(text="Type the number of classes you have enrolled for "
                                                                     "this semester \n(Type 0 if you haven't enroll "
                                                                     "any classes yet)",
                                                                title="Test")
                input_value = classes_enrolled.get_input()
                try:
                    return int(input_value)
                except ValueError:
                    # Show an error message and try again
                    customtkinter.CTkMessageBox.showerror("Error", "Please enter a valid integer.")
        if lang == "Español":
            while True:
                classes_enrolled = customtkinter.CTkInputDialog(text="Escriba el número de clases que ha inscrito para "
                                                                     "este semestre \n(Escriba 0 si aún no se ha inscrito "
                                                                     "en ninguna clase)", title="Test")
                input_value = classes_enrolled.get_input()
                try:
                    return int(input_value)
                except ValueError:
                    # Show an error message and try again
                    customtkinter.CTkMessageBox.showerror("Error", "Por favor, ingrese un número entero válido.")

    # function that changes the theme of the application
    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    # function that lets your increase/decrease the scaling of the GUI
    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

    # opens GitHub page
    def github_event(self):
        webbrowser.open("https://github.com/Hanuwa/TeraTermUI")

    # opens UPRB main page
    def uprb_event(self):
        webbrowser.open("https://www.uprb.edu")

    # opens a web page containing information about security information
    def lock_event(self):
        webbrowser.open("https://www.techtarget.com/searchsecurity/definition/"
                        "asymmetric-cryptography#:~:text=Asymmetric%20cryptography%2C%20also%20known%20as,"
                        "from%20unauthorized%20access%20or%20use.")

    def update_app(self):
        lang = self.language_menu.get()
        latest_version = self.get_latest_release()
        if not self.compare_versions(latest_version, self.USER_APP_VERSION):
            if lang == "English":
                msg = CTkMessagebox(master=self, title="Update",
                                    message="A newer version of the application is available,"
                                            "would you like to update?",
                                    icon="question",
                                    option_1="Cancel", option_2="No", option_3="Yes", icon_size=(65, 65),
                                    button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "darkblue", "darkblue"))
            elif lang == "Español":
                msg = CTkMessagebox(master=self, title="Actualizar",
                                    message="Una nueva de versión de la aplicación esta disponible,"
                                            "¿desea actualizar?",
                                    icon="question",
                                    option_1="Cancelar", option_2="No", option_3="Sí", icon_size=(65, 65),
                                    button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "darkblue", "darkblue"))
            response = msg.get()
            if response == "Yes" or response == "Sí" and self.test_connection(lang):
                webbrowser.open("https://github.com/Hanuwa/TeraTermUI/releases/latest")
        else:
            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
            if lang == "English":
                CTkMessagebox(master=self, title="Info", message="Application is up to date", button_width=380)
            elif lang == "Español":
                CTkMessagebox(master=self, title="Info", message="La Aplicación está actualizada", button_width=380)

    # determines the hardware of the users' computer and change the time.sleep seconds respectively
    def get_sleep_time(self):
        cpu_count = psutil.cpu_count()
        self.avg_cpu_load = sum(self.cpu_load_history) / len(self.cpu_load_history)
        if cpu_count >= 8 and self.avg_cpu_load <= 50:
            sleep_time = 0.5
        elif cpu_count >= 6 and self.avg_cpu_load <= 50:
            sleep_time = 0.75
        elif cpu_count >= 4 and self.avg_cpu_load <= 50:
            sleep_time = 1
        elif cpu_count >= 8 and self.avg_cpu_load >= 50:
            sleep_time = 0.90
        elif cpu_count >= 6 and self.avg_cpu_load >= 50:
            sleep_time = 1.2
        elif cpu_count >= 4 and self.avg_cpu_load >= 50:
            sleep_time = 1.5
        elif not self.cpu_load_history:
            sleep_time = 2
        else:
            sleep_time = 2

        return sleep_time

    # (Unused) Monitors the usage of the CPU of the user to determine the time.sleep of how long should the function
    # take before executing something
    def cpu_monitor(self, interval=1):
        while not self.stop_monitor.is_set():
            cpu_percent = psutil.cpu_percent(interval=interval)
            self.cpu_load_history.append(cpu_percent)

    # If user messes up the execution of the program this can solve it and make program work as expected
    def fix_execution(self):
        lang = self.language_menu.get()
        if self.checkIfProcessRunning("ttermpro") and self.run_fix:
            if lang == "English":
                msg = CTkMessagebox(master=self, title="Exit", message="This button is only made to fix the issue "
                                                                       "mentioned, are you sure you want to do it?",
                                    icon="question",
                                    option_1="Cancel", option_2="No", option_3="Yes", icon_size=(65, 65),
                                    button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "darkblue", "darkblue"))
            elif lang == "Español":
                msg = CTkMessagebox(master=self, title="Salir", message="Este botón solo se creó para solucionar "
                                                                        "el problema mencionado"
                                                                        " ¿Estás seguro de que quieres hacerlo?",
                                    icon="question",
                                    option_1="Cancelar", option_2="No", option_3="Sí", icon_size=(65, 65),
                                    button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "darkblue", "darkblue"))
            response = msg.get()
            if response == "Yes" or response == "Sí":
                self.reset_activity_timer(None)
                uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                uprb_window.wait('visible', timeout=100)
                self.unfocus_tkinter()
                send_keys("{TAB}")
                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                self.uprb.UprbayTeraTermVt.type_keys(self.default_semester)
                send_keys("{ENTER}")
                if lang == "English":
                    self.show_information_message(375, 250, "The problem is usually caused because"
                                                            "\n of user pressing buttons in Tera Term")
                if lang == "Español":
                    self.show_information_message(375, 250, "El problema suele ser causado porque"
                                                            "\n el usuario presiona botones en Tera Term")

    # Starts the check for idle thread
    def start_check_idle_thread(self):
        self.is_running = True
        self.thread = threading.Thread(target=self.check_idle)
        self.thread.start()

    # Checks if the user is idle for 4 minutes so that Tera Term doesn't close by itself
    def check_idle(self):
        self.num_checks = 0
        while self.is_running and not self.stop_check_idle.is_set():
            if time.time() - self.last_activity >= 240:
                if self.checkIfProcessRunning("ttermpro"):
                    uprb_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                    uprb_window.wait('visible', timeout=100)
                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                    send_keys("{ENTER}")
                    self.last_activity = time.time()
                    self.num_checks += 1
                else:
                    pass
            if self.num_checks == 8:
                break
            time.sleep(3)

    # Stops the check for idle thread
    def stop_thread(self):
        self.is_running = False

    # resets the idle timer when user interacts with something within the application
    def reset_activity_timer(self, _):
        self.last_activity = time.time()
        self.num_checks = 0

    # Check if user has an internet connection
    def test_connection(self, lang):
        try:
            sock = socket.create_connection(("Google.com", 80))
            if sock is not None:
                sock.close()
            return True
        except OSError:
            if self.error and self.error.winfo_exists():
                self.error.lift()
                return
            if lang == "English":
                self.show_error_message(300, 215, "Error! Not Connected to the internet")
            elif lang == "Español":
                self.show_error_message(300, 215, "¡Error! No Conectado al internet")

    # Set focus on the UI application window
    def set_focus_to_tkinter(self):
        tk_handle = win32gui.FindWindow(None, "Tera Term UI")
        win32gui.SetForegroundWindow(tk_handle)

    # Set focus on Tera Term window
    def unfocus_tkinter(self):
        pywinauto_handle = self.uprb.top_window().handle
        win32gui.SetForegroundWindow(pywinauto_handle)

    # Creates the status window
    def sidebar_button_event(self):
        if self.status and self.status.winfo_exists():
            self.status.lift()
            return
        lang = self.language_menu.get()
        if lang == "English":
            self.status = customtkinter.CTkToplevel(self)
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            scaling_factor = self.tk.call("tk", "scaling")
            x_position = int((screen_width - 475 * scaling_factor) / 2)
            y_position = int((screen_height - 275 * scaling_factor) / 2)
            window_geometry = f"{475}x{275}+{x_position + 190}+{y_position - 30}"
            self.status.geometry(window_geometry)
            self.status.title("Status")
            self.status.after(256, lambda: self.status.iconbitmap("images/tera-term.ico"))
            self.status.resizable(False, False)
            self.status.attributes("-topmost", True)
            scrollable_frame = customtkinter.CTkScrollableFrame(self.status, width=475, height=275,
                                                                fg_color=("#e6e6e6", "#222222"))
            scrollable_frame.pack()
            title = customtkinter.CTkLabel(scrollable_frame, text="Status of the application",
                                           font=customtkinter.CTkFont(size=20, weight="bold"))
            title.pack()
            version = customtkinter.CTkLabel(scrollable_frame, text="\n0.9.0 Version \n"
                                                                    "--Testing Phase-- \n\n"
                                                                    "Any feedback is greatly appreciated!")
            version.pack()
            self.feedbackText = customtkinter.CTkTextbox(scrollable_frame, wrap="word", border_spacing=8, width=300,
                                                         height=170, fg_color=("#ffffff", "#111111"))
            self.feedbackText.pack(pady=10)
            feedbackSend = customtkinter.CTkButton(scrollable_frame, border_width=2,
                                                        text="Send Feedback",
                                                        text_color=("gray10", "#DCE4EE"), command=self.submit_feedback)
            feedbackSend.pack()
            checkUpdateText = customtkinter.CTkLabel(scrollable_frame, text="\n\n Check if application has a new update"
                                                                            " available")
            checkUpdateText.pack(pady=5)
            checkUpdate = customtkinter.CTkButton(scrollable_frame, border_width=2,
                                                  text="Update",
                                                  text_color=("gray10", "#DCE4EE"), command=self.update_app)
            checkUpdate.pack()
            website = customtkinter.CTkLabel(scrollable_frame, text="\n\nGitHub Repository:")
            website.pack(pady=5)
            link = customtkinter.CTkButton(scrollable_frame, border_width=2,
                                           text="Link",
                                           text_color=("gray10", "#DCE4EE"), command=self.github_event)
            link.pack()
            faqText = customtkinter.CTkLabel(scrollable_frame, text="\n\nFrequently Asked Questions",
                                             font=customtkinter.CTkFont(size=15, weight="bold"))
            faqText.pack()
            qaTable = [["Question", "Answer"],
                       ["Is putting information \nhere safe?", "Yes, the application doesn't\n store your personal "
                                                               "data\n anywhere but, if you are still\n skeptical then "
                                                               "you can see\n which information we do store\n by "
                                                               "accessing the file called\n database.db and things "
                                                               "like the\n ssn are encrypted using\n an "
                                                               "asymmetrical key."]]
            faq = ctktable.CTkTable(scrollable_frame, row=2, column=2, values=qaTable)
            faq.pack(expand=True, fill="both", padx=20, pady=20)

        elif lang == "Español":
            self.status = customtkinter.CTkToplevel(self)
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            scaling_factor = self.tk.call("tk", "scaling")
            x_position = int((screen_width - 475 * scaling_factor) / 2)
            y_position = int((screen_height - 275 * scaling_factor) / 2)
            window_geometry = f"{475}x{275}+{x_position + 190}+{y_position - 30}"
            self.status.geometry(window_geometry)
            self.status.title("Estado")
            self.status.after(256, lambda: self.status.iconbitmap("images/tera-term.ico"))
            self.status.resizable(False, False)
            self.status.attributes("-topmost", True)
            scrollable_frame = customtkinter.CTkScrollableFrame(self.status, width=475, height=275, corner_radius=10,
                                                                fg_color=("#e6e6e6", "#222222"))
            scrollable_frame.pack()
            title = customtkinter.CTkLabel(scrollable_frame, text="Estado de la aplicación",
                                           font=customtkinter.CTkFont(size=20, weight="bold"))
            title.pack()
            version = customtkinter.CTkLabel(scrollable_frame, text="\nVersión 0.9.0 \n"
                                                                    "--Fase de Pruebas-- \n\n"
                                                                    "¡Cualquier comentario es muy apreciado!")
            version.pack()
            self.feedbackText = customtkinter.CTkTextbox(scrollable_frame, wrap="word", border_spacing=8, width=300,
                                                         height=170, fg_color=("#ffffff", "#111111"))
            self.feedbackText.pack(pady=10)
            feedbackSend = customtkinter.CTkButton(scrollable_frame, border_width=2,
                                                   text="Enviar Comentario",
                                                   text_color=("gray10", "#DCE4EE"), command=self.submit_feedback)
            feedbackSend.pack()
            checkUpdateText = customtkinter.CTkLabel(scrollable_frame, text="\n\n Revisa sí la aplicación tiene una"
                                                                            " actualización nueva")
            checkUpdateText.pack(pady=5)
            checkUpdate = customtkinter.CTkButton(scrollable_frame, border_width=2,
                                                  text="Actualizar",
                                                  text_color=("gray10", "#DCE4EE"), command=self.update_app)
            checkUpdate.pack()
            website = customtkinter.CTkLabel(scrollable_frame, text="\n\nRepositorio de GitHub:")
            website.pack(pady=5)
            link = customtkinter.CTkButton(scrollable_frame, border_width=2,
                                           text="Enlace",
                                           text_color=("gray10", "#DCE4EE"), command=self.github_event)
            link.pack()
            faqText = customtkinter.CTkLabel(scrollable_frame, text="\n\nPreguntas y Respuestas",
                                             font=customtkinter.CTkFont(size=15, weight="bold"))
            faqText.pack()
            qaTable = [["Pregunta", "Respuesta"],
                       ["¿Es seguro poner \nmi información aquí?", "Sí, la aplicación no almacena\n su "
                                                                   "data personal pero, si\n todavía estás "
                                                                   "escéptico,\n entonces puedes ver "
                                                                   "que\n información sí almacenamos \naccediendo "
                                                                   "al archivo llamado\n database.db y cosas como el "
                                                                   "\nssn son encriptado usando\n una"
                                                                   " llave asimétrica."]]
            faq = ctktable.CTkTable(scrollable_frame, row=2, column=2, values=qaTable)
            faq.pack(expand=True, fill="both", padx=20, pady=20)

    # Reads from the feedback.json file
    def authenticate(self):
        try:
            with open(self.SERVICE_ACCOUNT_FILE, 'rb') as f:
                archive = pyzipper.AESZipFile(self.SERVICE_ACCOUNT_FILE)
                archive.setpassword(self.PASSWORD.encode())
                file_contents = archive.read('feedback.json')
                credentials_dict = json.loads(file_contents.decode())
                self.credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
        except Exception as e:
            print(f"Failed to load credentials: {str(e)}")
            self.credentials = None

    # Function to call the Google Sheets API
    def call_sheets_api(self, values):
        lang = self.language_menu.get()
        if self.test_connection(lang):
            try:
                service = build('sheets', 'v4', credentials=self.credentials)
            except:
                DISCOVERY_SERVICE_URL = 'https://sheets.googleapis.com/$discovery/rest?version=v4'
                service = build('sheets', 'v4', credentials=self.credentials, discoveryServiceUrl=DISCOVERY_SERVICE_URL)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            body = {
                'values': [[now, values[0][0]]]
            }

            try:
                result = service.spreadsheets().values().append(
                    spreadsheetId=self.SPREADSHEET_ID, range=self.RANGE_NAME,
                    valueInputOption='RAW', insertDataOption='INSERT_ROWS',
                    body=body).execute()
                return result
            except HttpError as error:
                print(f"An error occurred: {error}")
                return None

    def submit_feedback(self):
        lang = self.language_menu.get()
        if self.submit_feedback_button:
            feedback = self.feedbackText.get("1.0", tk.END).strip()
            word_count = len(feedback.split())
            if word_count > 1000:
                winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                if lang == "English":
                    CTkMessagebox(title="Error", message="Error! Feedback cannot exceed 1000 words", icon="cancel",
                                  button_width=380)
                elif lang == "Español":
                    CTkMessagebox(title="Error", message="¡Error! El comentario no puede exceder 1000 palabras",
                                  icon="cancel",
                                  button_width=380)
                return
            if lang == "English":
                msg = CTkMessagebox(master=self, title="Submit", message="Are you ready to submit your feedback?"
                                                                         " \n\n(SUBMISSION IS COMPLETELY ANONYMOUS)",
                                    icon="question",
                                    option_1="Cancel", option_2="No", option_3="Yes", icon_size=(65, 65),
                                    button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "darkblue", "darkblue"))
            elif lang == "Español":
                msg = CTkMessagebox(master=self, title="Someter", message="¿Estás preparado para mandar to comentario?"
                                                                          " \n\n(EL ENVÍO ES COMPLETAMENTE ANÓNIMO)",
                                    icon="question",
                                    option_1="Cancelar", option_2="No", option_3="Sí", icon_size=(65, 65),
                                    button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "darkblue", "darkblue"))
            response = msg.get()
            if response == "Yes" or response == "Sí" and self.test_connection(lang):
                feedback = self.feedbackText.get("1.0", tk.END).strip()
                if not feedback:
                    winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                    if lang == "English":
                        CTkMessagebox(title="Error", message="Error! Feedback cannot be empty", icon="cancel",
                                      button_width=380)
                    elif lang == "Español":
                        CTkMessagebox(title="Error", message="¡Error! El comentario no puede estar vacio",
                                      icon="cancel", button_width=380)
                    return
                result = self.call_sheets_api([[feedback]])
                if result:
                    winsound.PlaySound("sounds/success.wav", winsound.SND_ASYNC)
                    if lang == "English":
                        CTkMessagebox(title="Success", icon="check", message="Feedback submitted successfully!",
                                      button_width=380)
                    elif lang == "Español":
                        CTkMessagebox(title="Success", icon="check", message="¡Comentario sometido éxitosamente!",
                                      button_width=380)
                    self.feedbackText.delete("1.0", tk.END)
                    self.submit_feedback_button = False
                else:
                    winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                    if lang == "English":
                        CTkMessagebox(title="Error", message="Error! An error occurred while submitting feedback",
                                      icon="cancel", button_width=380)
                    elif lang == "Español":
                        CTkMessagebox(title="Error", message="¡Error! Un error ocurrio mientras se sometia comentario",
                                      icon="cancel", button_width=380)
        else:
            if lang == "English":
                CTkMessagebox(title="Error", message="Error! Cannot submit more than one feedback", icon="cancel",
                              button_width=380)
            elif lang == "Español":
                CTkMessagebox(title="Error", message="¡Error! No se puede enviar más de un comentario",
                              icon="cancel", button_width=380)

    # Function that lets user select where their Tera Term application is located
    def change_location_event(self):
        lang = self.language_menu.get()
        if lang == "English":
            filename = filedialog.askopenfilename(initialdir="C:/",
                                                  title="Choose where Tera Term is located",
                                                  filetypes=(("Tera Term", "*ttermpro.exe"),))
            if re.search("ttermpro.exe", filename):
                self.location = filename
                directory, filename = os.path.split(filename)
                self.teraterm_file = directory + "/TERATERM.ini"
                location = self.cursor.execute("SELECT location FROM user_data").fetchall()
                teraterm_config = self.cursor.execute("SELECT config FROM user_data").fetchall()
                if len(location) == 0:
                    self.cursor.execute("INSERT INTO user_data (location) VALUES (?)", (self.location,))
                elif len(location) == 1:
                    self.cursor.execute("UPDATE user_data SET location=?", (self.location,))
                if len(teraterm_config) == 0:
                    self.cursor.execute("INSERT INTO user_data (config) VALUES (?)", (self.teraterm_file,))
                elif len(teraterm_config) == 1:
                    self.cursor.execute("UPDATE user_data SET config=?", (self.teraterm_file,))
                self.show_success_message(350, 265, "Tera Term has been located successfully")
                self.edit_teraterm_ini(self.teraterm_file)
        if lang == "Español":
            filename = filedialog.askopenfilename(initialdir="C:/",
                                                  title="Escoge donde Tera Term esta localizado",
                                                  filetypes=(("Tera Term", "*ttermpro.exe"),))
            if re.search("ttermpro.exe", filename):
                self.location = filename
                directory, filename = os.path.split(filename)
                self.teraterm_file = directory + "/TERATERM.ini"
                location = self.cursor.execute("SELECT location FROM user_data").fetchall()
                teraterm_config = self.cursor.execute("SELECT config FROM user_data").fetchall()
                if len(location) == 0:
                    self.cursor.execute("INSERT INTO user_data (location) VALUES (?)", (self.location,))
                elif len(location) == 1:
                    self.cursor.execute("UPDATE user_data SET location=?", (self.location,))
                if len(teraterm_config) == 0:
                    self.cursor.execute("INSERT INTO user_data (config) VALUES (?)", (self.teraterm_file,))
                elif len(teraterm_config) == 1:
                    self.cursor.execute("UPDATE user_data SET config=?", (self.teraterm_file,))
                self.show_success_message(350, 265, "Tera Term localizado exitósamente")
                self.edit_teraterm_ini(self.teraterm_file)

    # disables scrolling for the class list
    def disable_scroll(self, event):
        if self.class_list.focus_get() == self.class_list:
            self.class_list.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"
        else:
            return None

    # list of classes available for all departments in the university
    def search_classes(self, event):
        self.class_list.delete(0, tk.END)
        search_term = self.search_box.get().strip().lower()
        if search_term == "":
            return
        if search_term == "all":
            query = "SELECT name, code FROM courses"
        else:
            search_words = search_term.split()
            query_conditions = []
            for word in search_words:
                query_conditions.append(f"LOWER(name) LIKE '%{word}%'")
                query_conditions.append(f"LOWER(code) LIKE '%{word}%'")
            query_conditions_str = " OR ".join(query_conditions)
            query = f"SELECT name, code FROM courses WHERE {query_conditions_str}"
        results = self.cursor.execute(query).fetchall()
        for row in results:
            self.class_list.insert(tk.END, row[0])

    # query for searching for either class code or name
    def show_class_code(self, event):
        selection = self.class_list.curselection()
        if len(selection) == 0:
            return
        selected_class = self.class_list.get(self.class_list.curselection())

        query = "SELECT code FROM courses WHERE name = ? OR code = ?"
        result = self.cursor.execute(query, (selected_class, selected_class)).fetchone()

        if result is not None:
            self.search_box.delete(0, tk.END)
            self.search_box.insert(0, result[0])

    # Creates the Help window
    def sidebar_button_event2(self):
        if self.help and self.help.winfo_exists():
            self.help.lift()
            return
        lang = self.language_menu.get()
        bg_color = "#0e95eb"
        fg_color = "#333333"
        listbox_font = ("Arial", 11)
        if lang == "English":
            self.help = customtkinter.CTkToplevel(self)
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            scaling_factor = self.tk.call("tk", "scaling")
            x_position = int((screen_width - 475 * scaling_factor) / 2)
            y_position = int((screen_height - 275 * scaling_factor) / 2)
            window_geometry = f"{475}x{275}+{x_position + 190}+{y_position - 30}"
            self.help.geometry(window_geometry)
            self.help.title("Help")
            self.help.after(256, lambda: self.help.iconbitmap("images/tera-term.ico"))
            self.help.resizable(False, False)
            self.help.attributes("-topmost", True)
            scrollable_frame = customtkinter.CTkScrollableFrame(self.help, width=475, height=275,
                                                                fg_color=("#e6e6e6", "#222222"))
            scrollable_frame.pack()
            title = customtkinter.CTkLabel(scrollable_frame, text="Help",
                                           font=customtkinter.CTkFont(size=20, weight="bold"))
            title.pack()
            notice = customtkinter.CTkLabel(scrollable_frame, text="*Don't interact/touch Tera Term\n "
                                                                   "while using this application*",
                                            font=customtkinter.CTkFont(weight="bold", underline=True))
            notice.pack()
            searchboxText = customtkinter.CTkLabel(scrollable_frame, text="\n\nFind the code of the class you need:"
                                                                          "\n (Use arrow keys to scroll)")
            searchboxText.pack()
            self.search_box = customtkinter.CTkEntry(scrollable_frame, placeholder_text="Class")
            self.search_box.pack(pady=10)
            self.class_list = tk.Listbox(scrollable_frame, width=32, bg=bg_color, fg=fg_color, font=listbox_font)
            self.class_list.pack()
            termsText = customtkinter.CTkLabel(scrollable_frame, text="\n\nList of Terms:",
                                               font=customtkinter.CTkFont(weight="bold", size=15))
            termsText.pack()
            terms = [["Year", "Term"],
                     ["2019", "B91, B92, B93"],
                     ["2020", "C01, C02, C03"],
                     ["2021", "C11, C12, C13"],
                     ["2022", "C21, C22, C23"],
                     ["2023", "C31, C32, C33"],
                     ["Semester", "Fall, Spring, Summer"]]
            termsTable = ctktable.CTkTable(scrollable_frame, column=2, row=7, values=terms)
            termsTable.pack(expand=True, fill="both", padx=20, pady=20)
            filesText = customtkinter.CTkLabel(scrollable_frame, text="\nChoose your Tera Term's Location: ")
            filesText.pack()
            files = customtkinter.CTkButton(scrollable_frame, border_width=2,
                                            text="Choose",
                                            text_color=("gray10", "#DCE4EE"), command=self.change_location_event)
            files.pack(pady=5)
            fixText = customtkinter.CTkLabel(scrollable_frame, text="\nFix the program not executing things properly")
            fixText.pack()
            fix = customtkinter.CTkButton(scrollable_frame, border_width=2,
                                          text="Fix it",
                                          text_color=("gray10", "#DCE4EE"), command=self.fix_execution)
            fix.pack(pady=5)

        elif lang == "Español":
            self.help = customtkinter.CTkToplevel(self)
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            scaling_factor = self.tk.call("tk", "scaling")
            x_position = int((screen_width - 475 * scaling_factor) / 2)
            y_position = int((screen_height - 275 * scaling_factor) / 2)
            window_geometry = f"{475}x{275}+{x_position + 190}+{y_position - 30}"
            self.help.geometry(window_geometry)
            self.help.title("Ayuda")
            self.help.after(256, lambda: self.help.iconbitmap("images/tera-term.ico"))
            self.help.resizable(False, False)
            self.help.attributes("-topmost", True)
            scrollable_frame = customtkinter.CTkScrollableFrame(self.help, width=450, height=250,
                                                                fg_color=("#e6e6e6", "#222222"))
            scrollable_frame.pack()
            title = customtkinter.CTkLabel(scrollable_frame, text="Ayuda",
                                           font=customtkinter.CTkFont(size=20, weight="bold"))
            title.pack()
            notice = customtkinter.CTkLabel(scrollable_frame, text="*No toque Tera Term\n "
                                                                   "mientras use esta aplicación*",
                                            font=customtkinter.CTkFont(weight="bold", underline=True))
            notice.pack()
            searchboxText = customtkinter.CTkLabel(scrollable_frame, text="\n\nEncuentra el código de tu clase:"
                                                                          "\n(Usa las teclas de flecha)")
            searchboxText.pack()
            self.search_box = customtkinter.CTkEntry(scrollable_frame, placeholder_text="Clase")
            self.search_box.pack(pady=10)
            self.class_list = tk.Listbox(scrollable_frame, width=32, bg=bg_color, fg=fg_color, font=listbox_font)
            self.class_list.pack()
            termsText = customtkinter.CTkLabel(scrollable_frame, text="\n\nLista de Términos:",
                                               font=customtkinter.CTkFont(weight="bold", size=15))
            termsText.pack()
            terms = [["Año", "Términos"],
                     ["2019", "B91, B92, B93"],
                     ["2020", "C01, C02, C03"],
                     ["2021", "C11, C12, C13"],
                     ["2022", "C21, C22, C23"],
                     ["2023", "C31, C32, C33"],
                     ["Semestre", "Otoño, Primavera, Verano"]]
            termsTable = ctktable.CTkTable(scrollable_frame, column=2, row=7, values=terms)
            termsTable.pack(expand=True, fill="both", padx=20, pady=20)
            filesText = customtkinter.CTkLabel(scrollable_frame, text="\nEscoge donde esta localizado tu Tera Term: ")
            filesText.pack()
            files = customtkinter.CTkButton(scrollable_frame, border_width=2,
                                            text="Escoge",
                                            text_color=("gray10", "#DCE4EE"), command=self.change_location_event)
            files.pack(pady=5)
            fixText = customtkinter.CTkLabel(scrollable_frame, text="\nArreglar el programa que no ejecuta"
                                                                    "\n las cosas correctamente")
            fixText.pack()
            fix = customtkinter.CTkButton(scrollable_frame, border_width=2,
                                          text="Arreglalo",
                                          text_color=("gray10", "#DCE4EE"), command=self.fix_execution)
            fix.pack(pady=5)
        self.class_list.bind('<<ListboxSelect>>', self.show_class_code)
        self.class_list.bind("<MouseWheel>", self.disable_scroll)
        self.search_box.bind('<KeyRelease>', self.search_classes)

    def get_latest_release(self):
        url = f"{self.GITHUB_REPO}/releases/latest"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Error fetching release information: {response.status_code}")

        release_data = response.json()
        latest_version = release_data["tag_name"]

        if latest_version.startswith("v"):
            latest_version = latest_version[1:]

        return latest_version

    def compare_versions(self, latest_version, user_version):
        latest_version_parts = [int(part) for part in latest_version.split(".")]
        user_version_parts = [int(part) for part in user_version.split(".")]

        for latest, user in zip(latest_version_parts, user_version_parts):
            if latest > user:
                return False
            elif latest < user:
                return True
        return len(latest_version_parts) <= len(user_version_parts)

    def edit_teraterm_ini(self, file_path):
        if self.original_font is None:
            try:
                with open(file_path, "r") as file:
                    lines = file.readlines()
            except FileNotFoundError:
                return

            with open(file_path, "w") as file:
                for line in lines:
                    if line.startswith("VTFont="):
                        current_value = line.strip().split('=')[1]
                        font_name = current_value.split(',')[0]
                        if font_name.lower() != 'terminal':
                            self.original_font = current_value
                            updated_value = 'Terminal' + current_value[len(font_name):]
                            line = f"VTFont={updated_value}\n"

                    file.write(line)

    def restore_original_font(self, file_path):
        if self.original_font is not None:
            with open(file_path, "r") as file:
                lines = file.readlines()

            with open(file_path, "w") as file:
                for line in lines:
                    if line.startswith("VTFont="):
                        current_value = line.strip().split('=')[1]
                        font_name = current_value.split(',')[0]
                        if font_name.lower() != 'terminal':
                            line = f"VTFont={self.original_font}\n"
                    file.write(line)

            self.original_font = None


if __name__ == "__main__":
    appdata_folder = os.path.join(os.getenv('APPDATA'), 'TeraTermUI')
    lock_file = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), "app_lock.lock")
    lock_file_appdata = os.path.join(appdata_folder, "app_lock.lock")
    file_lock = FileLock(lock_file, timeout=0)
    try:
        with file_lock.acquire(poll_interval=0.1):
            app = TeraTermUI()
            app.after(1, lambda: app.iconbitmap("images/tera-term.ico"))
            app.mainloop()
    except Timeout:
        sys.exit(0)
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
