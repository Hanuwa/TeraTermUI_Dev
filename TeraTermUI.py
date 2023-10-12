# PROGRAM NAME - Tera Term UI

# PROGRAMMER - Armando Del Valle Tejada

# DESCRIPTION - Controls The application called Tera Term through a GUI interface to make the process of
# enrolling classes for the university of Puerto Rico at Bayamon easier

# DATE - Started 1/1/23, Current Build v0.9.0 - 10/12/23

# BUGS / ISSUES - The implementation of pytesseract could be improved, it sometimes fails to read the screen properly,
# depends a lot on the user's system and takes a bit time to process.
# Application sometimes feels sluggish/slow to use, could use some efficiency/performance improvements.
# The grid of the UI interface and placement of widgets could use some work.
# Option Menu of all tera terms screens requires more work

# FUTURE PLANS: Display more information in the app itself, which will make the app less reliant on Tera Term,
# refactor the architecture of the codebase, split things into multiple files, right now everything is in 1 file
# and with 6000 lines of codes, it definitely makes things harder to work with

import aiohttp
import asyncio
import atexit
import clipboard
import ctypes
import customtkinter
import gc
import json
import logging
import os
import pyautogui
import psutil
import py7zr
import pygetwindow as gw
import pytz
import pyzipper
import pytesseract
import re
import requests
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import time
import uuid
import webbrowser
import win32gui
import winsound
from contextlib import closing
from Cryptodome.Hash import HMAC, SHA256
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from Cryptodome.Random import get_random_bytes
from CTkToolTip import CTkToolTip
from CTkMessagebox import CTkMessagebox
from ctypes import wintypes
from customtkinter import ctktable
from datetime import datetime, timedelta
from filelock import FileLock, Timeout
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from pathlib import Path
from pywinauto.application import Application
from pywinauto.keyboard import send_keys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, \
    TableStyle, Paragraph, Spacer
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image, ImageOps

# from collections import deque
# from memory_profiler import profile

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")


class TeraTermUI(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Tera Term UI")
        # determines screen size to put application in the middle of the screen
        width = 910
        height = 485
        scaling_factor = self.tk.call("tk", "scaling")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width * scaling_factor) / 2
        y = (screen_height - height * scaling_factor) / 2
        self.geometry(f"{width}x{height}+{int(x) + 130}+{int(y + 50)}")
        self.iconbitmap("images/tera-term.ico")

        # creates a thread separate from the main application for check_idle and to monitor cpu usage
        self.last_activity = time.time()
        self.is_idle_thread_running = False
        self.stop_check_idle = threading.Event()
        self.lock_thread = threading.Lock()
        # self.cpu_load_history = deque(maxlen=60)
        # self.stop_monitor = threading.Event()
        # self.monitor_thread = threading.Thread(target=self.cpu_monitor)
        # self.monitor_thread.start()
        # GitHub information for feedback
        self.SERVICE_ACCOUNT_FILE = "feedback.zip"
        self.SPREADSHEET_ID = "1ffJLgp8p-goOlxC10OFEu0JefBgQDsgEo_suis4k0Pw"
        self.SPREADSHEET_BANNED_ID = "1JGDSyB-tE7gH5ozZ1MBlr9uMGcAWRgN7CyqK-QDQRxg"
        self.RANGE_NAME = "Sheet1!A:A"
        os.environ["Feedback"] = "F_QL^B#O_/r9|Rl0i=x),;!@en|V5qR%W(9;2^+f=lRPcw!+4"
        self.FEEDBACK = os.getenv("Feedback")
        self.credentials = None
        self.GITHUB_REPO = "https://api.github.com/repos/Hanuwa/TeraTermUI"
        self.USER_APP_VERSION = "0.9.0"
        # disabled/enables keybind events
        self.move_slider_left_enabled = True
        self.move_slider_right_enabled = True
        self.spacebar_enabled = True
        self.up_arrow_key_enabled = True
        self.down_arrow_key_enabled = True

        # Instance variables not yet needed but defined
        # to avoid the instance attribute defined outside __init__ warning
        self.user_id = None
        self.uprbay_window = None
        self.uprb = None
        self.table = None
        self.display_class = None
        self.server_status = None
        self.timer_window = None
        self.timer_label = None
        self.message_label = None
        self.cancel_button = None
        self.running_countdown = None
        self.progress_bar = None
        self.check_idle_thread = None
        self.idle_num_check = None
        self.feedbackText = None
        self.feedbackSend = None
        self.search_box = None
        self.class_list = None
        self.disableIdle = None
        self.status_minimized = None
        self.help_minimized = None
        self.checkbox_state = None
        self.get_class_for_pdf = None
        self.download_pdf = None
        self.previous_table_values = None
        self.table_rows = None
        self.is_banned = None
        self.is_banned_flag = False
        self.connection_error = False

        self.images = {
            "folder": customtkinter.CTkImage(light_image=Image.open("images/folder.png"), size=(18, 18)),
            "fix": customtkinter.CTkImage(light_image=Image.open("images/fix.png"), size=(15, 15)),
            "tera_term": Image.open("images/tera-term.ico"),
            "error": customtkinter.CTkImage(light_image=Image.open("images/error.png"), size=(100, 100)),
            "information": customtkinter.CTkImage(light_image=Image.open("images/info.png"), size=(100, 100)),
            "success": customtkinter.CTkImage(light_image=Image.open("images/success.png"), size=(200, 150)),
            "status": customtkinter.CTkImage(light_image=Image.open("images/home.png"), size=(20, 20)),
            "help": customtkinter.CTkImage(light_image=Image.open("images/setting.png"), size=(18, 18)),
            "uprb": customtkinter.CTkImage(light_image=Image.open("images/uprb.jpg"), size=(300, 100)),
            "lock": customtkinter.CTkImage(light_image=Image.open("images/lock.png"), size=(75, 75)),
            "update": customtkinter.CTkImage(light_image=Image.open("images/update.png"), size=(15, 15)),
            "link": customtkinter.CTkImage(light_image=Image.open("images/link.png"), size=(15, 15)),
        }

        # path for tesseract application
        self.zip_path = os.path.join(os.path.dirname(__file__), "Tesseract-OCR.7z")
        self.app_temp_dir = Path(tempfile.gettempdir()) / "TeraTermUI"
        self.app_temp_dir.mkdir(parents=True, exist_ok=True)

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="Tera Term UI",
                                                 font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.status_button = CustomButton(self.sidebar_frame, text="     Status", image=self.images["status"],
                                          command=self.status_button_event, anchor="w")
        self.status_button.grid(row=1, column=0, padx=20, pady=10)
        self.help_button = CustomButton(self.sidebar_frame, text="       Help", image=self.images["help"],
                                        command=self.help_button_event, anchor="w")
        self.help_button.grid(row=2, column=0, padx=20, pady=10)
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="Language, Appearance and \n\n "
                                                                             "UI Scaling:", anchor="w")
        self.scaling_label.grid(row=5, column=0, padx=20, pady=(10, 10))
        self.language_menu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["English", "Español"],
                                                         command=self.change_language_event, corner_radius=15)
        self.language_menu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, corner_radius=15,
                                                                       values=["Dark", "Light", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.set("System")
        self.appearance_mode_optionemenu.grid(row=7, column=0, padx=20, pady=(10, 10))
        self.scaling_optionemenu = customtkinter.CTkSlider(self.sidebar_frame, from_=97, to=103, number_of_steps=2,
                                                           width=150, height=20, command=self.change_scaling_event)
        self.scaling_optionemenu.set(100)
        self.scaling_tooltip = CTkToolTip(self.scaling_optionemenu, message=str(self.scaling_optionemenu.get()) + "%",
                                          bg_color="#1E90FF")
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))
        self.bind("<Left>", self.move_slider_left)
        self.bind("<Right>", self.move_slider_right)

        # create main entry
        self.introduction = customtkinter.CTkLabel(self, text="UPRB Enrollment Process",
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        self.introduction.grid(row=0, column=1, columnspan=2, padx=(20, 0), pady=(20, 0))
        self.host = customtkinter.CTkLabel(self, text="Host ")
        self.host.grid(row=2, column=0, columnspan=2, padx=(30, 0), pady=(20, 20))
        self.host_entry = CustomEntry(self, self, placeholder_text="myhost.example.edu")
        self.host_entry.grid(row=2, column=1, padx=(20, 0), pady=(20, 20))
        self.host_tooltip = CTkToolTip(self.host_entry, message="Enter the name of the server\n of the university",
                                       bg_color="#1E90FF")
        self.log_in = CustomButton(self, border_width=2, text="Log-In", text_color=("gray10", "#DCE4EE"),
                                   command=self.login_event_handler)
        self.log_in.grid(row=3, column=1, padx=(20, 0), pady=(20, 20))
        self.log_in.configure(state="disabled")
        self.slideshow_frame = ImageSlideshow(self, 'slideshow', interval=5, width=300, height=150)
        self.intro_box = customtkinter.CTkTextbox(self, height=120, width=400)
        self.intro_box.insert("0.0", "Welcome to the Tera Term UI Application!\n\n" +
                              "The purpose of this application"
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
                              "classes"
                              ", searching for classes and other functionally will be implemented later down the road "
                              "the priority right now is getting the user experience right, everything must looks nice"
                              " and be easy to understand. "
                              + "Everything you input here is stored locally, meaning only you can access the "
                                "information"
                                " so you will not have to worry about securities issues plus for sensitive information "
                                "like the Social Security Number, they get encrypted using AES. \n\n" +
                              "Thanks for using our application, for more information, help and to customize your "
                              "experience"
                              " make sure to click the buttons on the sidebar, the application is also planned to be"
                              " open source for anyone who is interested in working/seeing the project. \n\n" +
                              "IMPORTANT: DO NOT USE WHILE HAVING ANOTHER INSTANCE OF THE APPLICATION OPENED.  "
                              "")
        self.intro_box.configure(state="disabled", wrap="word", border_spacing=7)
        self.intro_box.grid(row=1, column=1, padx=(20, 0), pady=(0, 150))
        self.slideshow_frame.grid(row=1, column=1, padx=(20, 0), pady=(140, 0))

        # (Log-in Screen)
        self.authentication_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.authentication_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.a_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.a_buttons_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.title_login = customtkinter.CTkLabel(master=self.authentication_frame,
                                                  text="Connected to the server successfully",
                                                  font=customtkinter.CTkFont(size=20, weight="bold"))
        self.uprb_image = self.images["uprb"]
        self.uprb_image_grid = CustomButton(self.authentication_frame, text="", image=self.uprb_image,
                                            command=self.uprb_event, fg_color="transparent", hover=False)
        self.disclaimer = customtkinter.CTkLabel(master=self.authentication_frame, text="Authentication required")
        self.username = customtkinter.CTkLabel(master=self.authentication_frame, text="Username ")
        self.username_entry = CustomEntry(self.authentication_frame, self)
        self.username_tooltip = CTkToolTip(self.username_entry, message="The university requires this to\n"
                                                                        " enter and access the system",
                                           bg_color="#1E90FF")
        self.student = CustomButton(master=self.a_buttons_frame, border_width=2, text="Next",
                                    text_color=("gray10", "#DCE4EE"), command=self.student_event_handler)
        self.back = CustomButton(master=self.a_buttons_frame, fg_color="transparent", border_width=2, text="Back",
                                 hover_color="#4E4F50", text_color=("gray10", "#DCE4EE"), command=self.go_back_event)
        self.back_tooltip = CTkToolTip(self.back, message="Go back to the main menu\n"
                                                          "of the application", bg_color="#A9A9A9", alpha=0.90)

        # Student Information
        self.init_student = False
        self.in_student_frame = False
        self.student_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.student_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.s_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.s_buttons_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.title_student = None
        self.lock = None
        self.lock_grid = None
        self.ssn = None
        self.ssn_entry = None
        self.ssn_tooltip = None
        self.code = None
        self.code_entry = None
        self.code_tooltip = None
        self.show = None
        self.system = None
        self.back_student = None
        self.back_student_tooltip = None

        # Classes
        self.init_class = False
        self.tabview = customtkinter.CTkTabview(self, corner_radius=10, command=self.switch_tab)
        self.t_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.t_buttons_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.enroll_tab = None
        self.search_tab = None
        self.other_tab = None

        # First Tab
        self.in_enroll_frame = False
        self.title_enroll = None
        self.e_classes = None
        self.e_classes_entry = None
        self.e_section = None
        self.e_section_entry = None
        self.e_semester = None
        self.e_semester_entry = None
        self.radio_var = None
        self.register = None
        self.register_tooltip = None
        self.drop = None
        self.drop_tooltip = None
        self.submit = None

        # Second Tab
        self.in_search_frame = False
        self.search_scrollbar = None
        self.title_search = None
        self.s_classes = None
        self.s_classes_entry = None
        self.s_semester = None
        self.s_semester_entry = None
        self.show_all = None
        self.show_all_tooltip = None
        self.search = None
        self.search_next_page = None
        self.search_next_page_status = False
        self.search_next_page_tooltip = None

        # Third Tab
        self.explanation6 = None
        self.title_menu = None
        self.menu = None
        self.menu_entry = None
        self.menu_semester = None
        self.menu_semester_entry = None
        self.menu_submit = None
        self.go_next_1VE = None
        self.go_next_1GP = None
        self.go_next_409 = None
        self.go_next_683 = None
        self.go_next_4CM = None
        self._1VE_screen = False
        self._1GP_screen = False
        self._409_screen = False
        self._683_screen = False
        self._4CM_screen = False

        # Bottom Screen Buttons
        self.back_classes = None
        self.back_classes_tooltip = None
        self.show_classes = None
        self.show_classes_tooltip = None
        self.multiple = None
        self.multiple_tooltip = None

        # Multiple Classes Enrollment
        self.init_multiple = False
        self.multiple_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.multiple_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.m_button_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.m_button_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.save_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.save_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.auto_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.auto_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.explanation7 = None
        self.m_class = None
        self.m_section = None
        self.m_semester = None
        self.m_choice = None
        self.m_num_class = []
        self.m_classes_entry = []
        self.m_section_entry = []
        self.m_semester_entry = []
        self.m_register_menu = []
        self.placeholder_texts_classes = ["ESPA3101", "INGL3101", "BIOL3011", "MATE3001", "CISO3121", "HUMA3101"]
        self.placeholder_texts_sections = ["LM1", "KM1", "KH1", "LH1", "KN1", "LN1"]
        self.m_add = None
        self.m_add_tooltip = None
        self.m_remove = None
        self.m_remove_tooltip = None
        self.back_multiple = None
        self.back_multiple_tooltip = None
        self.submit_multiple = None
        self.save_data = None
        self.save_data_tooltip = None
        self.auto_enroll = None
        self.auto_enroll_tooltip = None

        # Top level window management, flags and counters
        self.DEFAULT_SEMESTER = "C31"
        self.welcome = False
        self.error_occurred = False
        self.can_edit = False
        self.enrolled_classes_list = {}
        self.dropped_classes_list = {}
        self.disable_feedback = False
        self.auto_enroll_bool = False
        self.countdown_running = False
        self.enrollment_error_check = False
        self.download = False
        self.status = None
        self.help = None
        self.error = None
        self.success = None
        self.loading_screen = None
        self.information = None
        self.run_fix = False
        self.teraterm_not_found = False
        self.idle = None
        self.passed = False
        self.tesseract_unzipped = False
        self.in_multiple_screen = False
        self.started_auto_enroll = False
        self.error_auto_enroll = False
        self.a_counter = 0
        self.m_counter = 0
        self.e_counter = 0
        self.search_function_counter = 0
        SPANISH = 0x0A
        language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        # default location of Tera Term
        self.location = "C:/Program Files (x86)/teraterm/ttermpro.exe"
        self.teraterm_file = "C:/Program Files (x86)/teraterm/TERATERM.ini"
        self.original_font = None
        # Database
        self.translations_cache = {}
        translation = self.load_language(self.language_menu.get())
        appdata_path = os.getenv("APPDATA")
        self.db_path = os.path.join(appdata_path, "TeraTermUI/database.db")
        self.ath = os.path.join(appdata_path, "TeraTermUI/feedback.zip")
        atexit.register(self.cleanup_temp)
        atexit.register(self.restore_original_font, self.teraterm_file)
        try:
            db_path = "database.db"
            if not os.path.isfile(db_path):
                raise Exception("Database file not found.")
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.cursor = self.connection.cursor()
            self.save = self.cursor.execute("SELECT class, section, semester, action FROM save_classes"
                                            " WHERE class IS NOT NULL").fetchall()
            self.saveCheck = self.cursor.execute('SELECT "check" FROM save_classes'
                                                 ' WHERE "check" IS NOT NULL').fetchall()
            user_data_fields = ["location", "host", "language", "appearance", "scaling", "idle", "welcome", "config"]
            results = {}
            for field in user_data_fields:
                query_user = f"SELECT {field} FROM user_data WHERE {field} IS NOT NULL"
                result = self.cursor.execute(query_user).fetchone()
                results[field] = result[0] if result else None
            if results["host"]:
                self.host_entry.insert(0, results["host"])
            if results["location"]:
                if results["location"] != self.location:
                    self.location = results["location"]
            if results["config"]:
                if results["config"] != self.teraterm_file:
                    self.teraterm_file = results["config"]
                    self.edit_teraterm_ini(self.teraterm_file)
                    self.can_edit = True
            if language_id & 0xFF == SPANISH:
                self.language_menu.set("Español")
                self.change_language_event(lang="Español")
            if results["language"]:
                if results["language"] != self.language_menu.get():
                    self.language_menu.set(results["language"])
                    self.change_language_event(lang=results["language"])
            if results["appearance"]:
                if results["appearance"] != "System" or results["appearance"] != "Sistema":
                    self.appearance_mode_optionemenu.set(results["appearance"])
                    self.change_appearance_mode_event(results["appearance"])
            if results["scaling"]:
                if results["scaling"] != 100.0:
                    self.scaling_optionemenu.set(float(results["scaling"]))
                    self.change_scaling_event(float(results["scaling"]))
            if not results["welcome"]:
                self.help_button.configure(state="disabled")
                self.status_button.configure(state="disabled")
                self.welcome = True

                # Pop up message that appears only the first time the user uses the application
                def show_message_box():
                    winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["welcome_title"],
                                  message=translation["welcome_message"], button_width=380)
                    self.status_button.configure(state="normal")
                    self.help_button.configure(state="normal")
                    self.log_in.configure(state="normal")
                    # closing event dialog
                    self.protocol("WM_DELETE_WINDOW", self.on_closing)
                    # enables keyboard input events
                    self.bind("<Escape>", lambda event: self.on_closing())
                    self.bind("<Return>", lambda event: self.login_event_handler())
                    if not results["welcome"]:
                        self.cursor.execute("INSERT INTO user_data (welcome) VALUES (?)", ("Checked",))
                    elif results["welcome"]:
                        self.cursor.execute("UPDATE user_data SET welcome=?", ("Checked",))

                self.after(3500, show_message_box)
            else:
                # closing event dialog
                self.protocol("WM_DELETE_WINDOW", self.on_closing)
                # enables closing app keyboard input event
                self.bind("<Escape>", lambda event: self.on_closing())

            # performs some operations in a separate thread when application starts up
            self.boot_up_thread = threading.Thread(target=self.boot_up, args=(self.teraterm_file,))
            self.boot_up_thread.start()

            self.mainloop()
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            if language_id & 0xFF == SPANISH:
                messagebox.showerror("Error", "¡Error Fatal! Problema en inicializar la base de datos.\n"
                                              "Es posible que necesite reinstalar la aplicación")
            else:
                messagebox.showerror("Error", "Fatal Error! Failed to initialize database.\n"
                                              "Might need to reinstall the application")
            exit(1)

        # Asks the user if they want to update to the latest version of the application
        def update_app():
            current_date = datetime.today().strftime("%Y-%m-%d")
            date = self.cursor.execute("SELECT date FROM user_data WHERE date IS NOT NULL").fetchall()
            dates_list = [record[0] for record in date]
            if current_date not in dates_list:
                try:
                    latest_version = self.get_latest_release()
                    if not TeraTermUI.compare_versions(latest_version, self.USER_APP_VERSION) and results["welcome"]:
                        winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                        msg = CTkMessagebox(master=self, title=translation["update_popup_title"],
                                            message=translation["update_popup_message"],
                                            icon="question", option_1=translation["option_1"],
                                            option_2=translation["option_2"], option_3=translation["option_3"],
                                            icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                            hover_color=("darkred", "darkblue", "darkblue"))
                        response = msg.get()
                        if response[0] == "Yes" or response[0] == "Sí":
                            webbrowser.open("https://github.com/Hanuwa/TeraTermUI/releases/latest")
                        resultDate = self.cursor.execute("SELECT date FROM user_data").fetchall()
                        if len(resultDate) == 0:
                            self.cursor.execute("INSERT INTO user_data (date) VALUES (?)", (current_date,))
                        elif len(resultDate) == 1:
                            self.cursor.execute("UPDATE user_data SET date=?", (current_date,))
                        self.connection.commit()
                except requests.exceptions.RequestException as err:
                    print(f"Error occurred while fetching latest release information: {err}")
                    print("Please check your internet connection and try again.")
                del dates_list, date, current_date

        self.after(100, update_app)
        del user_data_fields, results, SPANISH, language_id, \
            scaling_factor, screen_width, screen_height, width, height, x, y, db_path
        gc.collect()

    # function that when the user tries to close the application a confirm dialog opens up
    def on_closing(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        msg = CTkMessagebox(master=self, title=translation["exit"], message=translation["exit_message"],
                            icon="question", option_1=translation["close_tera_term"],
                            option_2=translation["option_2"], option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#c30101", "#145DA0"), option_1_type="checkbox",
                            hover_color=("darkred", "darkred", "darkblue"))
        on_exit = self.cursor.execute("SELECT exit FROM user_data").fetchall()
        if on_exit[0][0] == "1":
            msg.check_checkbox()
        response, self.checkbox_state = msg.get()
        if response == "Yes" or response == "Sí":
            if hasattr(self, "boot_up_thread") and self.boot_up_thread.is_alive():
                self.boot_up_thread.join()
            if hasattr(self, "check_idle_thread") and self.check_idle_thread is not None \
                    and self.check_idle_thread.is_alive():
                self.stop_check_idle.set()
                self.check_idle_thread.join()
            if TeraTermUI.checkIfProcessRunning("ttermpro") and \
                    TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT") \
                    and self.checkbox_state:
                uprb = Application(backend="uia").connect(title="uprbay.uprb.edu - Tera Term VT", timeout=10)
                uprb.kill(soft=False)
            elif TeraTermUI.checkIfProcessRunning("ttermpro") and \
                    TeraTermUI.window_exists("Tera Term - [disconnected] VT") \
                    and self.checkbox_state:
                subprocess.run(["taskkill", "/f", "/im", "ttermpro.exe"],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.save_user_data()
            self.destroy()
            exit(0)

    def tuition_event_handler(self):
        self.idle = self.cursor.execute("SELECT idle FROM user_data").fetchall()
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.tuition_event, args=(task_done,))
        event_thread.start()

    # Enrolling/Searching classes Frame
    def tuition_event(self, task_done):
        try:
            self.focus_set()
            self.destroy_windows()
            self.hide_sidebar_windows()
            self.unbind("<Return>")
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            aes_key = secrets.token_bytes(32)  # 256-bit key
            mac_key = secrets.token_bytes(32)  # separate 256-bit key for HMAC
            iv = get_random_bytes(16)  # for AES CBC mode

            # Deletes these encrypted variables from memory
            def secure_delete(variable):
                if isinstance(variable, bytes):
                    variable_len = len(variable)
                    variable = secrets.token_bytes(variable_len)
                    ctypes.memset(id(variable) + 0x10, 0, variable_len)
                elif isinstance(variable, int):
                    variable = secrets.randbits(variable.bit_length())
                del variable

            # Encrypt and compute MAC
            def aes_encrypt_then_mac(plaintext, key, inner_iv, inner_mac_key):
                cipher = AES.new(key, AES.MODE_CBC, iv=inner_iv)
                ciphertext = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
                # Compute a MAC over the ciphertext
                hmac = HMAC.new(inner_mac_key, digestmod=SHA256)
                hmac.update(ciphertext)
                mac = hmac.digest()
                # Append the MAC to the ciphertext
                return ciphertext + mac

            # Decrypt and verify MAC
            def aes_decrypt_and_verify_mac(ciphertext_with_mac, key, inner_iv, inner_mac_key):
                # Separate the MAC from the ciphertext
                ciphertext = ciphertext_with_mac[:-SHA256.digest_size]
                mac = ciphertext_with_mac[-SHA256.digest_size:]
                # Compute the expected MAC over the ciphertext
                hmac = HMAC.new(inner_mac_key, digestmod=SHA256)
                hmac.update(ciphertext)
                expected_mac = hmac.digest()
                # Verify the MAC
                if expected_mac != mac:
                    raise ValueError("MAC check failed")
                # If the MAC is valid, decrypt the ciphertext
                cipher = AES.new(key, AES.MODE_CBC, iv=inner_iv)
                plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size).decode()
                return plaintext

            if asyncio.run(self.test_connection(lang)) and self.check_server():
                if TeraTermUI.checkIfProcessRunning("ttermpro"):
                    try:
                        ssn = self.ssn_entry.get().replace(" ", "")
                        ssn = ssn.replace("-", "")
                        code = self.code_entry.get().replace(" ", "")
                        ssn_enc = aes_encrypt_then_mac(str(ssn), aes_key, iv, mac_key)
                        code_enc = aes_encrypt_then_mac(str(code), aes_key, iv, mac_key)
                        if re.match("^(?!000|666|9\d{2})\d{3}(?!00)\d{2}(?!0000)\d{4}$", ssn) and code.isdigit() \
                                and len(code) == 4:
                            secure_delete(ssn)
                            secure_delete(code)
                            ctypes.windll.user32.BlockInput(True)
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.uprbay_window.wait("visible", timeout=10)
                            self.uprb.UprbayTeraTermVt.type_keys(
                                aes_decrypt_and_verify_mac(ssn_enc, aes_key, iv, mac_key))
                            self.uprb.UprbayTeraTermVt.type_keys(
                                aes_decrypt_and_verify_mac(code_enc, aes_key, iv, mac_key))
                            send_keys("{ENTER}")
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            if "ID NOT ON FILE" in text_output or "PASS" in text_output:
                                self.bind("<Return>", lambda event: self.tuition_event_handler())
                                if "PASS" in text_output:
                                    send_keys("{TAB 2}")
                                self.after(0, self.show_error_message, 300, 215, translation["error_ssn"])
                            elif "ID NOT ON FILE" not in text_output or "PASS" not in text_output:
                                self.reset_activity_timer(None)
                                self.start_check_idle_thread()
                                self.after(0, self.tuition_frame)
                                self.run_fix = True
                                self.in_student_frame = False
                                secure_delete(ssn_enc)
                                secure_delete(code_enc)
                                secure_delete(aes_key)
                                secure_delete(mac_key)
                                secure_delete(iv)
                                del ssn, code, ssn_enc, code_enc, aes_key, mac_key
                                gc.collect()
                                self.switch_tab()
                                self.set_focus_to_tkinter()
                        else:
                            self.bind("<Return>", lambda event: self.tuition_event_handler())
                            self.after(0, self.show_error_message, 300, 215, translation["error_ssn"])
                    except ValueError:
                        self.bind("<Return>", lambda event: self.tuition_event_handler())
                        self.after(0, self.show_error_message, 300, 215, translation["error_ssn"])
                else:
                    self.bind("<Return>", lambda event: self.tuition_event_handler())
                    self.after(0, self.show_error_message, 300, 215, translation["tera_term_not_running"])

                    def server_maintenance():
                        self.destroy_windows()
                        winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["server_maintenance_title"],
                                      message=translation["server_maintenance"], button_width=380)

                    self.after(2500, server_maintenance)
            ctypes.windll.user32.BlockInput(False)
            self.show_sidebar_windows()
        except Exception as e:
            print("An error occurred: ", e)
            self.error_occurred = True
        finally:
            task_done.set()
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            if self.error_occurred:
                self.destroy_windows()
                winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                CTkMessagebox(master=self, title=translation["automation_error_title"],
                              message=translation["automation_error"],
                              icon="warning", button_width=380)
                self.error_occurred = False

    def tuition_frame(self):
        lang = self.language_menu.get()
        self.initialization_multiple()
        self.tabview.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 85))
        self.tabview.tab(self.enroll_tab).grid_columnconfigure(1, weight=2)
        self.tabview.tab(self.search_tab).grid_columnconfigure(1, weight=2)
        self.search_scrollbar.grid_columnconfigure(1, weight=2)
        self.tabview.tab(self.other_tab).grid_columnconfigure(1, weight=2)
        self.t_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(0, 0), pady=(0, 20))
        self.t_buttons_frame.grid_columnconfigure(1, weight=2)
        self.title_enroll.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
        self.e_classes.grid(row=1, column=1, padx=(32, 0), pady=(0, 0), sticky="w")
        self.e_classes_entry.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        if lang == "English":
            self.e_section.grid(row=2, column=1, padx=(21, 0), pady=(20, 0), sticky="w")
        elif lang == "Español":
            self.e_section.grid(row=2, column=1, padx=(18, 0), pady=(20, 0), sticky="w")
        self.e_section_entry.grid(row=2, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
        self.e_semester.grid(row=3, column=1, padx=(9, 0), pady=(20, 0), sticky="w")
        self.e_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
        self.register.grid(row=4, column=1, padx=(65, 0), pady=(20, 0), sticky="w")
        self.drop.grid(row=4, column=1, padx=(0, 25), pady=(20, 0), sticky="e")
        self.submit.grid(row=5, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
        self.search_scrollbar.grid(row=0, column=1, padx=(0, 0), pady=(0, 0), sticky="nsew")
        self.title_search.grid(row=0, column=1, padx=(0, 0), pady=(0, 20), sticky="n")
        self.s_classes.grid(row=1, column=1, padx=(0, 550), pady=(0, 0), sticky="n")
        self.s_classes_entry.grid(row=1, column=1, padx=(0, 425), pady=(0, 0), sticky="n")
        self.s_semester.grid(row=1, column=1, padx=(0, 270), pady=(0, 0), sticky="n")
        self.s_semester_entry.grid(row=1, column=1, padx=(0, 120), pady=(0, 0), sticky="n")
        if lang == "English":
            self.show_all.grid(row=1, column=1, padx=(85, 0), pady=(2, 0), sticky="n")
        elif lang == "Español":
            self.show_all.grid(row=1, column=1, padx=(85, 0), pady=(0, 7), sticky="n")
        self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
        self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
        self.title_menu.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        if lang == "English":
            self.menu.grid(row=2, column=1, padx=(35, 0), pady=(10, 0), sticky="w")
        elif lang == "Español":
            self.menu.grid(row=2, column=1, padx=(24, 0), pady=(10, 0), sticky="w")
        self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
        self.menu_semester.grid(row=3, column=1, padx=(9, 0), pady=(20, 0), sticky="w")
        self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
        self.menu_submit.grid(row=5, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
        self.back_classes.grid(row=4, column=0, padx=(0, 10), pady=(0, 0), sticky="w")
        self.show_classes.grid(row=4, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        self.multiple.grid(row=4, column=2, padx=(10, 0), pady=(0, 0), sticky="e")
        self.tabview.set(self.enroll_tab)
        self.bind("<Control-Tab>", lambda event: self.tab_switcher())
        self.ssn_entry.delete(0, "end")
        self.code_entry.delete(0, "end")
        self.ssn_entry.configure(placeholder_text="#########")
        self.code_entry.configure(placeholder_text="####")
        self.ssn_entry.configure(show="*")
        self.code_entry.configure(show="*")
        self.student_frame.grid_forget()
        self.s_buttons_frame.grid_forget()

    def submit_event_handler(self):
        msg = None
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        choice = self.radio_var.get().lower()
        self.focus_set()
        if lang == "English":
            msg = CTkMessagebox(master=self, title="Submit",
                                message="Are you sure you are ready " + choice + " this class?"
                                                                                 "\n\nWARNING: Make sure the "
                                                                                 "information is correct",
                                icon="images/submit.png",
                                option_1=translation["option_1"], option_2=translation["option_2"],
                                option_3=translation["option_3"],
                                icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
        elif lang == "Español":
            if choice == "register":
                choice = "registra"
                msg = CTkMessagebox(master=self, title="Someter",
                                    message="¿Estás preparado para " + choice + "r esta clase?"
                                                                                "\n\nWARNING: Asegúrese de que la "
                                                                                "información está correcta",
                                    icon="images/submit.png",
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "darkblue", "darkblue"))
            if choice == "drop":
                choice = "baja"
                msg = CTkMessagebox(master=self, title="Someter",
                                    message="¿Estás preparado para darle de " + choice + " a esta clase?"
                                                                                         "\n\nWARNING: Asegúrese de "
                                                                                         "que la información está "
                                                                                         "correcta",
                                    icon="images/submit.png",
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "darkblue", "darkblue"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            task_done = threading.Event()
            loading_screen = self.show_loading_screen()
            self.update_loading_screen(loading_screen, task_done)
            event_thread = threading.Thread(target=self.submit_event, args=(task_done,))
            event_thread.start()

    # function for registering/dropping classes
    def submit_event(self, task_done):
        with self.lock_thread:
            try:
                self.unbind("<Return>")
                self.focus_set()
                self.hide_sidebar_windows()
                self.destroy_windows()
                choice = self.radio_var.get()
                classes = self.e_classes_entry.get().upper().replace(" ", "")
                section = self.e_section_entry.get().upper().replace(" ", "")
                semester = self.e_semester_entry.get().upper().replace(" ", "")
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro") or self.passed:
                        if (choice == "Register" and classes not in
                            self.enrolled_classes_list.values() and section not in self.enrolled_classes_list) \
                                or (choice == "Drop" and classes
                                    not in self.dropped_classes_list.values() and section
                                    not in self.dropped_classes_list):
                            if (re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE)
                                    and re.fullmatch("^[A-Z]{2}1$", section, flags=re.IGNORECASE)
                                    and re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE)):
                                ctypes.windll.user32.BlockInput(True)
                                term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                                if term_window.isMinimized:
                                    term_window.restore()
                                self.uprbay_window.wait("visible", timeout=10)
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                send_keys("{ENTER}")
                                self.uprb.UprbayTeraTermVt.type_keys("1S4")
                                self.uprb.UprbayTeraTermVt.type_keys(semester)
                                send_keys("{ENTER}")
                                self.reset_activity_timer(None)
                                self.after(0, self.disable_go_next_buttons)
                                screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                screenshot_thread.start()
                                screenshot_thread.join()
                                text_output = self.capture_screenshot()
                                enrolled_classes = "ENROLLED"
                                count_enroll = text_output.count(enrolled_classes)
                                if "OUTDATED" not in text_output and "INVALID TERM SELECTION" not in text_output and \
                                        "VUELVA LUEGO" not in text_output and "REGISTRATION DATA" in text_output and \
                                        count_enroll != 15:
                                    self.e_counter = 0
                                    send_keys("{TAB 2}")
                                    for i in range(count_enroll, 0, -1):
                                        send_keys("{TAB 2}")
                                    if choice == "Register":
                                        self.uprb.UprbayTeraTermVt.type_keys("R")
                                    elif choice == "Drop":
                                        self.uprb.UprbayTeraTermVt.type_keys("D")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes)
                                    self.uprb.UprbayTeraTermVt.type_keys(section)
                                    send_keys("{ENTER}")
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text = self.capture_screenshot()
                                    enrolled_classes = "ENROLLED"
                                    count_enroll = text.count(enrolled_classes)
                                    dropped_classes = "DROPPED"
                                    count_dropped = text.count(dropped_classes)
                                    self.reset_activity_timer(None)
                                    if "CONFIRMED" in text or "DROPPED" in text:
                                        self.e_classes_entry.delete(0, "end")
                                        self.e_section_entry.delete(0, "end")
                                        for i in range(count_dropped, 0, -1):
                                            self.e_counter -= 1
                                        for i in range(count_enroll, 0, -1):
                                            self.e_counter += 1
                                        if choice == "Register":
                                            send_keys("{ENTER}")
                                            if section in self.dropped_classes_list:
                                                del self.dropped_classes_list[section]
                                            if section not in self.enrolled_classes_list:
                                                self.enrolled_classes_list[section] = classes
                                            elif section in self.enrolled_classes_list:
                                                del self.enrolled_classes_list[section]
                                            self.after(0, self.show_success_message, 350, 265,
                                                       translation["success_enrolled"])
                                        elif choice == "Drop":
                                            if section in self.enrolled_classes_list:
                                                del self.enrolled_classes_list[section]
                                            if section not in self.dropped_classes_list:
                                                self.dropped_classes_list[section] = classes
                                            elif section in self.dropped_classes_list:
                                                del self.dropped_classes_list[section]
                                            self.after(0, self.show_success_message, 350, 265,
                                                       translation["success_dropped"])
                                        if self.e_counter + self.m_counter == 15:
                                            time.sleep(3.2)
                                            self.submit.configure(state="disabled")
                                            self.multiple.configure(state="disabled")
                                            self.after(0, self.show_information_message, 350, 265,
                                                       translation["enrollment_limit"])
                                        self.set_focus_to_tkinter()
                                    else:
                                        self.after(0, self.show_error_message, 320, 235,
                                                   translation["failed_enroll"])
                                        self.set_focus_to_tkinter()
                                else:
                                    if count_enroll == 15:
                                        self.submit.configure(state="disabled")
                                        self.submit_multiple.configure(sate="disabled")
                                        self.after(0, self.show_information_message, 350, 265,
                                                   translation["enrollment_limit"])
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(0, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                    else:
                                        if "VUELVA LUEGO" not in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                            send_keys("{ENTER}")
                                            self.reset_activity_timer(None)
                                            self.after(0, self.show_error_message, 300, 210,
                                                       translation["failed_enroll"])
                                            if not self.enrollment_error_check:
                                                self.after(2500, self.show_enrollment_error_information)
                                                self.enrollment_error_check = True
                                    self.set_focus_to_tkinter()
                            else:
                                if not classes or not section or not semester:
                                    self.after(0, self.show_error_message, 350, 230, translation["missing_info"])
                                elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE):
                                    self.after(0, self.show_error_message, 360, 230, translation["class_format_error"])
                                elif not re.fullmatch("^[A-Z]{2}1$", section, flags=re.IGNORECASE):
                                    self.after(0, self.show_error_message, 360, 230,
                                               translation["section_format_error"])
                                elif not re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE):
                                    self.after(0, self.show_error_message, 360, 230,
                                               translation["semester_format_error"])
                        else:
                            if classes in self.enrolled_classes_list.values() or section in self.enrolled_classes_list:
                                self.after(0, self.show_error_message, 335, 240, translation["already_enrolled"])
                            if classes in self.dropped_classes_list.values() or section in self.dropped_classes_list:
                                self.after(0, self.show_error_message, 335, 240, translation["already_dropped"])
                    else:
                        self.after(0, self.show_error_message, 300, 215, translation["tera_term_not_running"])
                ctypes.windll.user32.BlockInput(False)
                self.show_sidebar_windows()
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if self.error_occurred:
                    self.destroy_windows()
                    winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["automation_error_title"],
                                  message=translation["automation_error"],
                                  icon="warning", button_width=380)
                    self.error_occurred = False
                self.bind("<Return>", lambda event: self.submit_event_handler())

    def search_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.search_event, args=(task_done,))
        event_thread.start()

    # function for searching for classes
    def search_event(self, task_done):
        with self.lock_thread:
            try:
                self.unbind("<Return>")
                self.focus_set()
                self.destroy_windows()
                self.hide_sidebar_windows()
                classes = self.s_classes_entry.get().upper().replace(" ", "")
                semester = self.s_semester_entry.get().upper().replace(" ", "")
                show_all = self.show_all.get()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro") or self.passed:
                        if (re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE)
                                and re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE)):
                            ctypes.windll.user32.BlockInput(True)
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.uprbay_window.wait("visible", timeout=10)
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1CS")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            if self.passed and self.search_function_counter == 0:
                                self.uprb.window().menu_select("Edit")
                                self.uprb.window().menu_select("Edit->Select screen")
                                self.uprb.UprbayTeraTermVt.type_keys("%c")
                                self.uprbay_window.click_input(button="left")
                                copy = clipboard.paste()
                                data, course_found, invalid_action = TeraTermUI.extract_class_data(copy)
                                if data or course_found or invalid_action:
                                    self.search_function_counter = 1
                            if self.search_function_counter == 0:
                                self.uprb.UprbayTeraTermVt.type_keys(classes)
                            if self.search_function_counter >= 1:
                                self.uprb.UprbayTeraTermVt.type_keys("1CS")
                                self.uprb.UprbayTeraTermVt.type_keys(classes)
                            send_keys("{TAB}")
                            if show_all == "on":
                                self.uprb.UprbayTeraTermVt.type_keys("Y")
                            elif show_all == "off":
                                self.uprb.UprbayTeraTermVt.type_keys("N")
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            ctypes.windll.user32.BlockInput(False)
                            self.after(0, self.disable_go_next_buttons)
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            if "MORE SECTIONS" in text_output:
                                self.after(0, self.search_next_page_layout)
                            if "COURSE NOT IN" in text_output:
                                if lang == "English":
                                    self.after(0, self.show_error_message, 300, 215,
                                               "Error! Course: " + classes + " not found")
                                elif lang == "Español":
                                    self.after(0, self.show_error_message, 310, 215,
                                               "Error! Clase: " + classes + " \nno se encontro")
                            elif "INVALID ACTION" in text_output or "INVALID TERM SELECTION" in text_output:
                                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                send_keys("{ENTER}")
                                self.reset_activity_timer(None)
                                if "INVALID TERM SELECTION" in text_output:
                                    self.after(0, self.show_error_message, 320, 235, translation["invalid_semester"])
                                if "INVALID ACTION" in text_output:
                                    self.after(0, self.show_error_message, 320, 235, translation["failed_to_search"])
                                self.search_function_counter += 1
                            else:
                                self.search_function_counter += 1
                                self.uprb.window().menu_select("Edit")
                                self.uprb.window().menu_select("Edit->Select screen")
                                self.uprb.UprbayTeraTermVt.type_keys("%c")
                                self.uprbay_window.click_input(button="left")
                                copy = clipboard.paste()
                                data, course_found, invalid_action = TeraTermUI.extract_class_data(copy)
                                self.get_class_for_pdf = self.s_classes_entry.get().replace(" ", "").upper()
                                self.after(0, self.display_data, data)
                                self.clipboard_clear()
                        else:
                            if not classes or not semester:
                                self.after(0, self.show_error_message, 350, 230, translation["missing_info_search"])
                            elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE):
                                self.after(0, self.show_error_message, 360, 230, translation["class_format_error"])
                            elif not re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE):
                                self.after(0, self.show_error_message, 360, 230, translation["semester_format_error"])
                    else:
                        self.after(0, self.show_error_message, 300, 215, translation["tera_term_not_running"])
                self.show_sidebar_windows()
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if self.error_occurred:
                    self.destroy_windows()
                    winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["automation_error_title"],
                                  message=translation["automation_error"],
                                  icon="warning", button_width=380)
                    self.error_occurred = False
                self.bind("<Return>", lambda event: self.search_event_handler())

    def search_next_page_layout(self):
        self.search_next_page_status = True
        self.search_next_page.configure(state="normal")
        self.search.configure(width=85)
        self.search.grid(row=1, column=1, padx=(285, 0), pady=(0, 5), sticky="n")
        self.search_next_page.grid(row=1, column=1, padx=(465, 0), pady=(0, 5), sticky="n")

    # function for seeing the classes you are currently enrolled for
    def my_classes_event(self):
        with self.lock_thread:
            self.destroy_windows()
            self.hide_sidebar_windows()
            self.focus_set()
            self.unbind("<Return>")
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            width = 910
            height = 485
            scaling_factor = self.tk.call("tk", "scaling")
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = (screen_width - width * scaling_factor) / 2
            y = (screen_height - height * scaling_factor) / 2
            dialog = customtkinter.CTkInputDialog(text=translation["dialog_message"],
                                                  title=translation["dialog_title"])
            dialog.geometry(f"{int(x) + 512}+{int(y + 225)}")
            dialog.after(201, lambda: dialog.iconbitmap("images/tera-term.ico"))
            dialog_input = dialog.get_input()
            if dialog_input is not None:
                dialog_input = dialog_input.replace(" ", "").upper()
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro") or self.passed:
                        if re.fullmatch("^[A-Z][0-9]{2}$", dialog_input, flags=re.IGNORECASE):
                            block_window = customtkinter.CTkToplevel()
                            block_window.attributes("-alpha", 0.0)
                            block_window.grab_set()
                            ctypes.windll.user32.BlockInput(True)
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.uprbay_window.wait("visible", timeout=10)
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1CP")
                            self.uprb.UprbayTeraTermVt.type_keys(dialog_input.replace(" ", "").upper())
                            send_keys("{ENTER}")
                            text_output = self.capture_screenshot()
                            if "INVALID TERM SELECTION" in text_output:
                                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                send_keys("{ENTER}")
                                self.reset_activity_timer(None)
                                self.show_error_message(300, 215, translation["invalid_semester"])
                            ctypes.windll.user32.BlockInput(False)
                            self.reset_activity_timer(None)
                            self.disable_go_next_buttons()
                            block_window.destroy()
                            self.after(100, self.unfocus_tkinter)
                        else:
                            self.show_error_message(300, 215, translation["invalid_semester"])
                    else:
                        self.show_error_message(300, 215, translation["tera_term_not_running"])
            else:
                dialog.destroy()
        self.show_sidebar_windows()
        self.switch_tab()

    # function that adds new entries
    def add_event(self):
        self.focus_set()
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        semester = self.m_semester_entry[0].get().upper()
        if re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE):
            if self.a_counter + 1 < len(self.m_semester_entry):  # Making sure we don't exceed the list index
                self.m_semester_entry[self.a_counter + 1].configure(state="normal")
                self.m_num_class[self.a_counter + 1].grid(row=self.a_counter + 2, column=0, padx=(0, 8), pady=(20, 0))
                self.m_classes_entry[self.a_counter + 1].grid(row=self.a_counter + 2, column=1, padx=(0, 500),
                                                              pady=(20, 0))
                self.m_section_entry[self.a_counter + 1].grid(row=self.a_counter + 2, column=1, padx=(0, 165),
                                                              pady=(20, 0))
                self.m_semester_entry[self.a_counter + 1].set(semester)
                self.m_semester_entry[self.a_counter + 1].configure(state="disabled")
                self.m_semester_entry[self.a_counter + 1].grid(row=self.a_counter + 2, column=1, padx=(165, 0),
                                                               pady=(20, 0))
                self.m_register_menu[self.a_counter + 1].grid(row=self.a_counter + 2, column=1, padx=(500, 0),
                                                              pady=(20, 0))
                self.a_counter += 1
                if self.a_counter > 0:
                    self.m_remove.configure(state="normal")

                if self.a_counter == 5:
                    self.m_add.configure(state="disabled")
        else:
            if not semester:
                self.show_error_message(350, 255, translation["add_no_semester"])
            else:
                self.show_error_message(350, 255, translation["add_invalid_semester"])

    # function that removes existing entries
    def remove_event(self):
        self.focus_set()
        self.m_add.configure(state="normal")
        if self.a_counter <= 0:
            self.m_remove.configure(state="disabled")
        else:
            self.a_counter -= 1
            self.m_remove.configure(state="normal")
            self.m_num_class[self.a_counter + 1].grid_forget()
            self.m_classes_entry[self.a_counter + 1].grid_forget()
            self.m_section_entry[self.a_counter + 1].grid_forget()
            self.m_semester_entry[self.a_counter + 1].grid_forget()
            self.m_register_menu[self.a_counter + 1].grid_forget()
            self.m_semester_entry[self.a_counter + 1].configure(state="normal")
            self.m_semester_entry[self.a_counter + 1].set("")
            self.m_semester_entry[self.a_counter + 1].configure(state="disabled")
            if self.a_counter == 0:
                self.m_remove.configure(state="disabled")

    def add_event_up_arrow_key(self):
        if self.up_arrow_key_enabled and self.a_counter != 5:
            self.add_event()

    def remove_event_down_arrow_key(self):
        if self.down_arrow_key_enabled and self.a_counter != 0:
            self.remove_event()

    # multiple classes screen
    def multiple_classes_event(self):
        self.focus_set()
        self.in_enroll_frame = False
        self.in_search_frame = False
        self.in_multiple_screen = True
        self.unbind("<space>")
        self.unbind("<Control-Tab>")
        self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
        self.bind("<Up>", lambda event: self.add_event_up_arrow_key())
        self.bind("<Down>", lambda event: self.remove_event_down_arrow_key())
        self.multiple_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 30))
        self.multiple_frame.grid_columnconfigure(2, weight=1)
        self.m_button_frame.grid(row=3, column=1, columnspan=4, rowspan=4, padx=(0, 0), pady=(0, 10))
        self.m_button_frame.grid_columnconfigure(2, weight=1)
        self.save_frame.grid(row=3, column=2, padx=(0, 50), pady=(0, 8), sticky="e")
        self.save_frame.grid_columnconfigure(2, weight=1)
        self.auto_frame.grid(row=3, column=1, padx=(50, 0), pady=(0, 8), sticky="w")
        self.auto_frame.grid_columnconfigure(2, weight=1)
        self.explanation7.grid(row=0, column=1, padx=(0, 0), pady=(0, 20))
        self.m_class.grid(row=0, column=1, padx=(0, 500), pady=(32, 0))
        self.m_section.grid(row=0, column=1, padx=(0, 165), pady=(32, 0))
        self.m_semester.grid(row=0, column=1, padx=(165, 0), pady=(32, 0))
        self.m_choice.grid(row=0, column=1, padx=(500, 0), pady=(32, 0))
        self.m_num_class[0].grid(row=1, column=0, padx=(0, 8), pady=(0, 0))
        self.m_classes_entry[0].grid(row=1, column=1, padx=(0, 500), pady=(0, 0))
        self.m_section_entry[0].grid(row=1, column=1, padx=(0, 165), pady=(0, 0))
        self.m_semester_entry[0].grid(row=1, column=1, padx=(165, 0), pady=(0, 0))
        self.m_register_menu[0].grid(row=1, column=1, padx=(500, 0), pady=(0, 0))
        self.m_add.grid(row=3, column=0, padx=(0, 20), pady=(0, 0))
        self.back_multiple.grid(row=3, column=1, padx=(0, 20), pady=(0, 0))
        self.submit_multiple.grid(row=3, column=2, padx=(0, 0), pady=(0, 0))
        self.m_remove.grid(row=3, column=3, padx=(20, 0), pady=(0, 0))
        self.save_data.grid(row=0, column=0, padx=(0, 0), pady=(0, 0))
        self.auto_enroll.grid(row=0, column=0, padx=(0, 0), pady=(0, 0))
        self.tabview.grid_forget()
        self.t_buttons_frame.grid_forget()

    def submit_multiple_event_handler(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.focus_set()
        if not self.started_auto_enroll:
            msg = CTkMessagebox(master=self, title=translation["submit"],
                                message=translation["enroll_multiple"],
                                icon="images/submit.png",
                                option_1=translation["option_1"], option_2=translation["option_2"],
                                option_3=translation["option_3"],
                                icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
            response = msg.get()
            if response[0] != "Yes" and response[0] != "Sí":
                return
        self.error_auto_enroll = False
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.submit_multiple_event, args=(task_done,))
        event_thread.start()

    # function that enrolls multiple classes with one click
    def submit_multiple_event(self, task_done):
        with self.lock_thread:
            try:
                self.focus_set()
                self.destroy_windows()
                self.hide_sidebar_windows()
                self.unbind("<Return>")
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                classes = []
                sections = []
                semester = self.m_semester_entry[0].get().upper().replace(" ", "")
                choices = []
                for i in range(self.a_counter):
                    classes.append(self.m_classes_entry[i].get().upper().replace(" ", ""))
                    sections.append(self.m_section_entry[i].get().upper().replace(" ", ""))
                    choices.append(self.m_register_menu[i].get())
                can_enroll_classes = self.e_counter + self.m_counter + self.a_counter + 1 <= 15
                if asyncio.run(self.test_connection(lang)) and self.check_server() and self.check_format():
                    if TeraTermUI.checkIfProcessRunning("ttermpro") or self.passed:
                        if can_enroll_classes:
                            ctypes.windll.user32.BlockInput(True)
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.uprbay_window.wait("visible", timeout=10)
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1S4")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            enrolled_classes = "ENROLLED"
                            count_enroll = text_output.count(enrolled_classes)
                            if "OUTDATED" not in text_output and "INVALID TERM SELECTION" not in text_output and \
                                    "VUELVA LUEGO" not in text_output and "REGISTRATION DATA" \
                                    in text_output and count_enroll != 15:
                                self.e_counter = 0
                                self.m_counter = 0
                                for i in range(count_enroll, 0, -1):
                                    self.e_counter += 1
                                send_keys("{TAB 2}")
                                for i in range(count_enroll, 0, -1):
                                    send_keys("{TAB 2}")
                                for i in range(self.a_counter + 1):
                                    if choices[i] in ["Register", "Registra"]:
                                        self.uprb.UprbayTeraTermVt.type_keys("R")
                                    elif choices[i] in ["Drop", "Baja"]:
                                        self.uprb.UprbayTeraTermVt.type_keys("D")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes[i])
                                    self.uprb.UprbayTeraTermVt.type_keys(sections[i])
                                    self.m_counter += 1
                                    if i == self.a_counter:
                                        send_keys("{ENTER}")
                                    else:
                                        send_keys("{TAB}")
                                screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                screenshot_thread.start()
                                screenshot_thread.join()
                                text = self.capture_screenshot()
                                dropped_classes = "DROPPED"
                                count_dropped = text.count(dropped_classes)
                                self.reset_activity_timer(None)
                                if "CONFIRMED" in text or "DROPPED" in text:
                                    for i in range(count_dropped, 0, -1):
                                        self.m_counter -= 1
                                        self.e_counter -= 1
                                    choice = [
                                        (self.m_register_menu[i].get(), i,
                                         self.m_section_entry[i].get().upper().replace(" ", ""),
                                         self.m_classes_entry[i].get().upper().replace(" ", ""))
                                        for i in range(self.a_counter)
                                    ]
                                    for c, cnt, sec, cls in choice:
                                        if sec:
                                            if c == "Register" or c == "Registra":
                                                if sec in self.dropped_classes_list:
                                                    del self.dropped_classes_list[sec]
                                                if sec not in self.enrolled_classes_list:
                                                    self.enrolled_classes_list[sec] = cls
                                            elif c == "Drop" or c == "Baja":
                                                if sec in self.enrolled_classes_list:
                                                    del self.enrolled_classes_list[sec]
                                                if sec not in self.dropped_classes_list:
                                                    self.dropped_classes_list[sec] = cls
                                    if "CONFIRMED" in text and "DROPPED" in text:
                                        send_keys("{ENTER}")
                                        self.after(0, self.show_success_message, 350, 265,
                                                   translation["enrolled_dropped_multiple_success"])
                                    elif "CONFIRMED" in text and "DROPPED" not in text:
                                        send_keys("{ENTER}")
                                        self.after(0, self.show_success_message, 350, 265,
                                                   translation["enrolled_multiple_success"])
                                    elif "DROPPED" in text and "CONFIRMED" not in text:
                                        self.after(0, self.show_success_message, 350, 265,
                                                   translation["dropped_multiple_success"])
                                    if "INVALID COURSE ID" in text or "COURSE RESERVED" in text or "COURSE CLOSED" in \
                                            text or "CRS ALRDY TAKEN/PASSED" in text or "Closed by Spec-Prog" in text \
                                            or "ILLEGAL DROP-NOT ENR" in text or "NEW COURSE,NO FUNCTION" in text or \
                                            "PRESENTLY ENROLLED" in text or "R/TC" in text:
                                        for i in range(self.a_counter + 1, 0, -1):
                                            if self.enrolled_classes_list:
                                                self.enrolled_classes_list.popitem()
                                            if self.dropped_classes_list:
                                                self.dropped_classes_list.popitem()
                                    if self.e_counter + self.m_counter == 15:
                                        self.go_back_event2()
                                        self.submit.configure(state="disabled")
                                        self.multiple.configure(state="disabled")
                                        time.sleep(3.2)
                                        self.after(0, self.show_information_message, 350, 265,
                                                   translation["enrollment_limit"])
                                    self.set_focus_to_tkinter()
                                    for i in range(self.a_counter):
                                        self.m_classes_entry[i].delete(0, "end")
                                        self.m_section_entry[i].delete(0, "end")
                                    for i in range(6):
                                        self.m_classes_entry[i].configure(
                                            placeholder_text=self.placeholder_texts_classes[i])
                                        self.m_section_entry[i].configure(
                                            placeholder_text=self.placeholder_texts_sections[i])
                                else:
                                    self.after(0, self.show_error_message, 320, 235,
                                               translation["failed_enroll_multiple"])
                                    self.m_counter = self.m_counter - self.a_counter - 1
                                    self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
                                    self.set_focus_to_tkinter()
                            else:
                                if count_enroll == 15:
                                    self.submit.configure(state="disabled")
                                    self.submit_multiple.configure(sate="disabled")
                                    self.after(0, self.show_information_message, 350, 265,
                                               translation["enrollment_limit"])
                                if "INVALID TERM SELECTION" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(0, self.show_error_message, 300, 215,
                                               translation["invalid_semester"])
                                else:
                                    if "VUELVA LUEGO" not in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                    if "INVALID ACTION" in text_output and self.started_auto_enroll:
                                        self.after(0, self.submit_multiple_event_handler)
                                        self.error_auto_enroll = True
                                    else:
                                        self.after(0, self.show_error_message, 300, 210,
                                                   translation["failed_enroll_multiple"])
                                        if not self.enrollment_error_check:
                                            self.after(2500, self.show_enrollment_error_information)
                                            self.enrollment_error_check = True
                                self.set_focus_to_tkinter()
                        else:
                            self.after(0, self.show_error_message, 320, 235,
                                       translation["max_enroll"])
                            self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
                    else:
                        self.after(0, self.show_error_message, 300, 215, translation["tera_term_not_running"])
                    self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
                ctypes.windll.user32.BlockInput(False)
                self.show_sidebar_windows()
                self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if not self.error_auto_enroll:
                    self.started_auto_enroll = False
                if self.error_occurred:
                    self.destroy_windows()
                    winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["automation_error_title"],
                                  message=translation["automation_error"],
                                  icon="question", button_width=380)
                    self.error_occurred = False
                self.bind("<Return>", lambda event: self.submit_multiple_event_handler())

    def option_menu_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.option_menu_event, args=(task_done,))
        event_thread.start()

    # changes to the respective screen the user chooses
    def option_menu_event(self, task_done):
        with self.lock_thread:
            try:
                self.unbind("<Return>")
                self.focus_set()
                self.destroy_windows()
                self.hide_sidebar_windows()
                menu = self.menu_entry.get()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                semester = self.menu_semester_entry.get().upper().replace(" ", "")
                menu_dict = {
                    "SRM (Main Menu)": "SRM",
                    "SRM (Menú Principal)": "SRM",
                    "004 (Hold Flags)": "004",
                    "1GP (Class Schedule)": "1GP",
                    "1GP (Programa de Clases)": "1GP",
                    "118 (Academic Staticstics)": "118",
                    "118 (Estadísticas Académicas)": "118",
                    "1VE (Academic Record)": "1VE",
                    "1VE (Expediente Académico)": "1VE",
                    "3DD (Scholarship Payment Record)": "3DD",
                    "3DD (Historial de Pagos de Beca)": "3DD",
                    "409 (Account Balance)": "409",
                    "409 (Balance de Cuenta)": "409",
                    "683 (Academic Evaluation)": "683",
                    "683 (Evaluación Académica)": "683",
                    "1PL (Basic Personal Data)": "1PL",
                    "1PL (Datos Básicos)": "1PL",
                    "4CM (Tuition Calculation)": "4CM",
                    "4CM (Cómputo de Matrícula)": "4CM",
                    "4SP (Apply for Extension)": "4SP",
                    "4SP (Solicitud de Prórroga)": "4SP",
                    "SO (Sign out)": "SO",
                    "SO (Cerrar Sesión)": "SO"
                }
                menu = menu_dict.get(menu, menu)
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro") or self.passed:
                        if re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE) \
                                and menu in menu_dict.values():
                            ctypes.windll.user32.BlockInput(True)
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.uprbay_window.wait("visible", timeout=10)
                            match menu.replace(" ", ""):
                                case "SRM":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(0, self.disable_go_next_buttons)
                                case "004":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("004")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(0, self.disable_go_next_buttons)
                                case "1GP":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("1GP")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(0, self.disable_go_next_buttons)
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" not in text_output:
                                        def go_next_grid():
                                            self.go_next_1GP.configure(state="normal")
                                            self.go_next_1VE.grid_forget()
                                            self.go_next_409.grid_forget()
                                            self.go_next_683.grid_forget()
                                            self.go_next_4CM.grid_forget()
                                            self.go_next_1VE.configure(state="disabled")
                                            self.go_next_409.configure(state="disabled")
                                            self.go_next_683.configure(state="disabled")
                                            self.go_next_4CM.configure(state="disabled")
                                            self._1VE_screen = False
                                            self._1GP_screen = True
                                            self._409_screen = False
                                            self._683_screen = False
                                            self._4CM_screen = False
                                            self.menu_submit.configure(width=100)
                                            self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20),
                                                                   sticky="n")
                                            self.title_menu.grid(row=1, column=1, padx=(0, 0), pady=(0, 0),
                                                                 sticky="n")
                                            if lang == "English":
                                                self.menu.grid(row=2, column=1, padx=(44, 0), pady=(10, 0), sticky="w")
                                            elif lang == "Español":
                                                self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
                                            self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
                                            self.menu_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0),
                                                                    sticky="w")
                                            self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0),
                                                                          sticky="n")
                                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0),
                                                                  sticky="n")
                                            self.go_next_1GP.grid(row=5, column=1, padx=(110, 0), pady=(40, 0),
                                                                  sticky="n")

                                        self.after(0, go_next_grid)
                                    else:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(0, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "118":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("118")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(0, self.disable_go_next_buttons)
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(0, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "1VE":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("1VE")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.go_next_1VE.configure(state="disabled")
                                    self.go_next_1GP.configure(state="disabled")
                                    self.go_next_409.configure(state="disabled")
                                    self.go_next_683.configure(state="disabled")
                                    self.go_next_4CM.configure(state="disabled")
                                    self._1VE_screen = True
                                    self._1GP_screen = False
                                    self._409_screen = False
                                    self._683_screen = False
                                    self._4CM_screen = False
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "CONFLICT" in text_output:
                                        self.after(0, self.show_information_message, 310, 225,
                                                   translation["hold_flag"])
                                        self.uprb.UprbayTeraTermVt.type_keys("004")
                                        self.uprb.UprbayTeraTermVt.type_keys(semester)
                                        send_keys("{ENTER}")
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(0, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                    if "CONFLICT" not in text_output or "INVALID TERM SELECTION" not in text_output:
                                        def go_next_grid():
                                            self.go_next_1VE.configure(state="normal")
                                            self.go_next_1GP.grid_forget()
                                            self.go_next_409.grid_forget()
                                            self.go_next_683.grid_forget()
                                            self.go_next_4CM.grid_forget()
                                            self.menu_submit.configure(width=100)
                                            self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20),
                                                                   sticky="n")
                                            self.title_menu.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                                            if lang == "English":
                                                self.menu.grid(row=2, column=1, padx=(44, 0), pady=(10, 0), sticky="w")
                                            elif lang == "Español":
                                                self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
                                            self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
                                            self.menu_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0),
                                                                    sticky="w")
                                            self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0),
                                                                          sticky="n")
                                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0),
                                                                  sticky="n")
                                            self.go_next_1VE.grid(row=5, column=1, padx=(110, 0), pady=(40, 0),
                                                                  sticky="n")

                                        self.after(0, go_next_grid)
                                case "3DD":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("3DD")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(0, self.disable_go_next_buttons)
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(0, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "409":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("409")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" not in text_output:
                                        def go_next_grid():
                                            self.go_next_409.configure(state="normal")
                                            self.go_next_1VE.grid_forget()
                                            self.go_next_1GP.grid_forget()
                                            self.go_next_683.grid_forget()
                                            self.go_next_4CM.grid_forget()
                                            self.go_next_1GP.configure(state="disabled")
                                            self.go_next_683.configure(state="disabled")
                                            self.go_next_1VE.configure(state="disabled")
                                            self.go_next_4CM.configure(state="disabled")
                                            self._1VE_screen = False
                                            self._1GP_screen = False
                                            self._409_screen = True
                                            self._683_screen = False
                                            self._4CM_screen = False
                                            self.menu_submit.configure(width=100)
                                            self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20),
                                                                   sticky="n")
                                            self.title_menu.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                                            if lang == "English":
                                                self.menu.grid(row=2, column=1, padx=(44, 0), pady=(10, 0), sticky="w")
                                            elif lang == "Español":
                                                self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
                                            self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
                                            self.menu_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0),
                                                                    sticky="w")
                                            self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0),
                                                                          sticky="n")
                                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0),
                                                                  sticky="n")
                                            self.go_next_409.grid(row=5, column=1, padx=(110, 0), pady=(40, 0),
                                                                  sticky="n")

                                        self.after(0, go_next_grid)
                                    else:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(0, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "683":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("683")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.go_next_1VE.grid_forget()
                                    self.go_next_1GP.grid_forget()
                                    self.go_next_409.grid_forget()
                                    self.go_next_4CM.grid_forget()
                                    self.go_next_1VE.configure(state="disabled")
                                    self.go_next_1GP.configure(state="disabled")
                                    self.go_next_409.configure(state="disabled")
                                    self.go_next_4CM.configure(state="disabled")
                                    self._1VE_screen = False
                                    self._1GP_screen = False
                                    self._409_screen = False
                                    self._683_screen = True
                                    self._4CM_screen = False
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "CONFLICT" in text_output:
                                        self.after(0, self.show_information_message, 310, 225,
                                                   translation["hold_flag"])
                                        self.uprb.UprbayTeraTermVt.type_keys("004")
                                        send_keys("{ENTER}")
                                    if "CONFLICT" not in text_output:
                                        def go_next_grid():
                                            self.go_next_683.configure(state="normal")
                                            self.submit.configure(width=100)
                                            self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20),
                                                                   sticky="n")
                                            self.title_menu.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                                            if lang == "English":
                                                self.menu.grid(row=2, column=1, padx=(44, 0), pady=(10, 0), sticky="w")
                                            elif lang == "Español":
                                                self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
                                            self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
                                            self.menu_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0),
                                                                    sticky="w")
                                            self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0),
                                                                          sticky="n")
                                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0),
                                                                  sticky="n")
                                            self.go_next_683.grid(row=5, column=1, padx=(110, 0), pady=(40, 0),
                                                                  sticky="n")

                                        self.after(0, go_next_grid)
                                case "1PL":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("1PL")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(0, self.disable_go_next_buttons)
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "TERM OUTDATED" in text_output or "NO PUEDE REALIZAR CAMBIOS" in text_output or \
                                            "INVALID TERM SELECTION" in text_output:
                                        if "TERM OUTDATED" in text_output or "INVALID TERM SELECTION" in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                            send_keys("{ENTER}")
                                            self.reset_activity_timer(None)
                                        if lang == "English":
                                            self.after(0, self.show_error_message, 325, 240,
                                                       "Error! Failed to enter\n " + self.menu_entry.get()
                                                       + " screen")
                                        elif lang == "Español":
                                            self.after(0, self.show_error_message, 325, 240,
                                                       "¡Error! No se pudo entrar \n a la pantalla" +
                                                       self.menu_entry.get())
                                case "4CM":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("4CM")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" not in text_output and \
                                            "TERM OUTDATED" not in text_output:
                                        def go_next_grid():
                                            self.go_next_4CM.configure(state="normal")
                                            self.go_next_1VE.grid_forget()
                                            self.go_next_1GP.grid_forget()
                                            self.go_next_409.grid_forget()
                                            self.go_next_4CM.grid_forget()
                                            self.go_next_1VE.configure(state="disabled")
                                            self.go_next_1GP.configure(state="disabled")
                                            self.go_next_409.configure(state="disabled")
                                            self.go_next_683.configure(state="disabled")
                                            self._1VE_screen = False
                                            self._1GP_screen = False
                                            self._409_screen = False
                                            self._683_screen = False
                                            self._4CM_screen = True
                                            self.menu_submit.configure(width=100)
                                            self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20),
                                                                   sticky="n")
                                            self.title_menu.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
                                            if lang == "English":
                                                self.menu.grid(row=2, column=1, padx=(44, 0), pady=(10, 0), sticky="w")
                                            elif lang == "Español":
                                                self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
                                            self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
                                            self.menu_semester.grid(row=3, column=1, padx=(20, 0), pady=(20, 0),
                                                                    sticky="w")
                                            self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0),
                                                                          sticky="n")
                                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0),
                                                                  sticky="n")
                                            self.go_next_4CM.grid(row=5, column=1, padx=(110, 0), pady=(40, 0),
                                                                  sticky="n")

                                        self.after(0, go_next_grid)
                                    if "TERM OUTDATED" in text_output or "INVALID TERM SELECTION" in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        if lang == "English":
                                            self.after(0, self.show_error_message, 325, 240,
                                                       "Error! Failed to enter\n " + self.menu_entry.get() + " screen")
                                        elif lang == "Español":
                                            self.after(0, self.show_error_message, 325, 240,
                                                       "¡Error! No se pudo entrar"
                                                       "\n a la pantalla" + self.menu_entry.get())
                                case "4SP":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("4SP")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(0, self.disable_go_next_buttons)
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "TERM OUTDATED" in text_output or "NO PUEDE REALIZAR CAMBIOS" in text_output:
                                        if "TERM OUTDATED" in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                            send_keys("{ENTER}")
                                            self.reset_activity_timer(None)
                                        if lang == "English":
                                            self.after(0, self.show_error_message, 325, 240,
                                                       "Error! Failed to enter\n " + self.menu_entry.get() + " screen")
                                        elif lang == "Español":
                                            self.after(0, self.show_error_message, 325, 240,
                                                       "Error! No se pudo entrar"
                                                       "\n a la pantalla" + self.menu_entry.get())
                                case "SO":
                                    lang = self.language_menu.get()
                                    self.hide_loading_screen()
                                    msg = CTkMessagebox(master=self, title=translation["error"],
                                                        message=translation["error_message"],
                                                        option_1=translation["option_1"],
                                                        option_2=translation["option_2"],
                                                        option_3=translation["option_3"],
                                                        icon_size=(65, 65),
                                                        button_color=("#c30101", "#145DA0", "#145DA0"),
                                                        hover_color=("darkred", "darkblue", "darkblue"))
                                    response = msg.get()
                                    self.show_loading_screen_again()
                                    if TeraTermUI.checkIfProcessRunning("ttermpro") and response[0] == "Yes" \
                                            or response[0] == "Sí":
                                        self.uprb.UprbayTeraTermVt.type_keys("SO")
                                        send_keys("{ENTER}")
                                    if not TeraTermUI.checkIfProcessRunning("ttermpro") and response[0] == "Yes" \
                                            or response[0] == "Sí":
                                        self.after(0, self.show_error_message, 350, 265,
                                                   translation["tera_term_not_running"])
                        else:
                            if not semester or not menu:
                                self.after(0, self.show_error_message, 350, 230,
                                           translation["menu_missing_info"])
                            elif not re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE):
                                self.after(0, self.show_error_message, 360, 230,
                                           translation["semester_format_error"])
                            elif menu not in menu_dict.values():
                                self.after(0, self.show_error_message, 340, 230,
                                           translation["menu_code_error"])
                    else:
                        self.after(0, self.show_error_message, 300, 215, translation["tera_term_not_running"])
                ctypes.windll.user32.BlockInput(False)
                self.show_sidebar_windows()
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if self.error_occurred:
                    self.destroy_windows()
                    winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["automation_error_title"],
                                  message=translation["automation_error"],
                                  icon="warning", button_width=380)
                    self.error_occurred = False
                self.bind("<Return>", lambda event: self.option_menu_event_handler())
                self.unfocus_tkinter()

    def go_next_page_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.go_next_page_event, args=(task_done,))
        event_thread.start()

    # go through each page of the different screens
    def go_next_page_event(self, task_done):
        with self.lock_thread:
            try:
                self.unbind("<Return>")
                self.focus_set()
                self.destroy_windows()
                self.hide_sidebar_windows()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro") or self.passed:
                        self.unfocus_tkinter()
                        if self._1VE_screen:
                            ctypes.windll.user32.BlockInput(True)
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.uprbay_window.wait("visible", timeout=10)
                            send_keys("{TAB 3}")
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            ctypes.windll.user32.BlockInput(False)
                        elif self._1GP_screen:
                            ctypes.windll.user32.BlockInput(True)
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.uprbay_window.wait("visible", timeout=10)
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            ctypes.windll.user32.BlockInput(False)
                        elif self._409_screen:
                            ctypes.windll.user32.BlockInput(True)
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.uprbay_window.wait("visible", timeout=10)
                            send_keys("{TAB 4}")
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            ctypes.windll.user32.BlockInput(False)
                        elif self._683_screen:
                            self.submit.configure(state="disabled")
                            self.search.configure(state="disabled")
                            self.multiple.configure(state="disabled")
                            self.menu_submit.configure(state="disabled")
                            self.show_classes.configure(state="disabled")
                            ctypes.windll.user32.BlockInput(True)
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.uprbay_window.wait("visible", timeout=10)
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            ctypes.windll.user32.BlockInput(False)
                        elif self._4CM_screen:
                            ctypes.windll.user32.BlockInput(True)
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.uprbay_window.wait("visible", timeout=10)
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            ctypes.windll.user32.BlockInput(False)
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            if "RATE NOT ON ARFILE" in text_output:
                                self.after(0, self.show_error_message, 310, 225, translation["unknown_error"])
                            else:
                                self.go_next_4CM.configure(state="disabled")
                        self.reset_activity_timer(None)
                        self.show_sidebar_windows()
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if self.error_occurred:
                    self.destroy_windows()
                    winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["automation_error_title"],
                                  message=translation["automation_error"],
                                  icon="warning", button_width=380)
                    self.error_occurred = False
                self.bind("<Return>", lambda event: self.option_menu_event_handler())
                self.unfocus_tkinter()

    def go_next_search_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.search_go_next, args=(task_done,))
        event_thread.start()

    # Goes through more sections available for the searched class
    def search_go_next(self, task_done):
        with self.lock_thread:
            try:
                lang = self.language_menu.get()
                self.unbind("<Return>")
                self.focus_set()
                self.destroy_windows()
                self.hide_sidebar_windows()
                self.unfocus_tkinter()
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro") or self.passed:
                        ctypes.windll.user32.BlockInput(True)
                        term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                        if term_window.isMinimized:
                            term_window.restore()
                        self.uprbay_window.wait("visible", timeout=10)
                        send_keys("{ENTER}")
                        self.uprb.window().menu_select("Edit->Select screen")
                        self.uprb.UprbayTeraTermVt.type_keys("%c")
                        self.uprbay_window.click_input(button="left")
                        copy = clipboard.paste()
                        data, course_found, invalid_action = TeraTermUI.extract_class_data(copy)
                        self.after(0, self.display_data, data)
                        self.clipboard_clear()
                        self.reset_activity_timer(None)
                        ctypes.windll.user32.BlockInput(False)
                        screenshot_thread = threading.Thread(target=self.capture_screenshot)
                        screenshot_thread.start()
                        screenshot_thread.join()
                        text_output = self.capture_screenshot()
                        if "MORE SECTIONS" not in text_output:
                            self.search_next_page.configure(state="disabled")
                            self.search_next_page_status = False
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if self.error_occurred:
                    self.destroy_windows()
                    winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["automation_error_title"],
                                  message=translation["automation_error"],
                                  icon="warning", button_width=380)
                    self.error_occurred = False
                self.bind("<Return>", lambda event: self.search_event_handler())
                self.show_sidebar_windows()

    # disable these buttons if the user changed screen
    def disable_go_next_buttons(self):
        self.go_next_1VE.configure(state="disabled")
        self.go_next_1GP.configure(state="disabled")
        self.go_next_409.configure(state="disabled")
        self.go_next_683.configure(state="disabled")
        self.go_next_4CM.configure(state="disabled")
        self.search_next_page.configure(state="disabled")
        self._1VE_screen = False
        self._1GP_screen = False
        self._409_screen = False
        self._683_screen = False
        self._4CM_screen = False
        self.search_next_page_status = False

    def student_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.student_event, args=(task_done,))
        event_thread.start()

    # Authentication required frame, where user is asked to input his username
    def student_event(self, task_done):
        try:
            self.focus_set()
            self.destroy_windows()
            self.hide_sidebar_windows()
            self.unbind("<Return>")
            username = self.username_entry.get().replace(" ", "").lower()
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            if asyncio.run(self.test_connection(lang)) and self.check_server():
                if TeraTermUI.checkIfProcessRunning("ttermpro"):
                    if username == "students":
                        self.unfocus_tkinter()
                        ctypes.windll.user32.BlockInput(True)
                        term_window = gw.getWindowsWithTitle("SSH Authentication")[0]
                        if term_window.isMinimized:
                            term_window.restore()
                        self.uprbay_window.wait("visible", timeout=10)
                        user = self.uprb.UprbayTeraTermVt.child_window(title="User name:",
                                                                       control_type="Edit").wrapper_object()
                        user.set_text(username)
                        check = self.uprb.UprbayTeraTermVt.child_window(title="Remember password in memory",
                                                                        control_type="CheckBox")
                        if check.get_toggle_state() == 0:
                            check.click()
                        self.uprb.UprbayTeraTermVt.child_window(title="Use plain password to log in",
                                                                control_type="RadioButton").click()
                        self.hide_loading_screen()
                        okConn2 = self.uprb.UprbayTeraTermVt.child_window(title="OK",
                                                                          control_type="Button").wrapper_object()
                        okConn2.click()
                        self.show_loading_screen_again()
                        self.server_status = self.wait_for_prompt("return to continue", "REGRESE PRONTO")
                        if self.server_status == "Maintenance message found":
                            def server_closed():
                                self.unbind("<Return>")
                                self.back.configure(state="disabled")
                                self.student.configure(state="disabled")
                                winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                CTkMessagebox(title=translation["server_maintenance_title"],
                                              message=translation["server_maintenance"],
                                              icon="cancel",
                                              button_width=380)
                                self.error_occurred = True

                            self.after(0, server_closed)
                        elif self.server_status == "Prompt found":
                            send_keys("{ENTER 3}")
                            self.bind("<Return>", lambda event: self.tuition_event_handler())
                            self.after(0, self.student_info_frame)
                            self.in_student_frame = True
                            self.set_focus_to_tkinter()
                        elif self.server_status == "Timeout":
                            def timeout():
                                winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                CTkMessagebox(title="Error", message=translation["timeout_server"],
                                              icon="cancel",
                                              button_width=380)
                                self.error_occurred = True

                            self.after(0, timeout)
                    elif username != "students":
                        self.bind("<Return>", lambda event: self.student_event_handler())
                        self.after(0, self.show_error_message, 300, 215, translation["invalid_username"])
                else:
                    self.bind("<Return>", lambda event: self.student_event_handler())
                    self.after(0, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            self.show_sidebar_windows()
        except Exception as e:
            print("An error occurred: ", e)
            self.error_occurred = True
        finally:
            task_done.set()
            if self.server_status == "Maintenance message found" or self.server_status == "Timeout":
                self.after(3500, self.go_back_event)
            elif self.error_occurred:
                self.after(0, self.go_back_event)

    def student_info_frame(self):
        lang = self.language_menu.get()
        self.initialization_class()
        self.student_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 100))
        self.student_frame.grid_columnconfigure(2, weight=1)
        self.s_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(0, 0), pady=(0, 40))
        self.s_buttons_frame.grid_columnconfigure(2, weight=1)
        self.title_student.grid(row=0, column=1, padx=(20, 20), pady=(10, 20))
        self.lock_grid.grid(row=1, column=1, padx=(00, 0), pady=(0, 20))
        if lang == "English":
            self.ssn.grid(row=2, column=1, padx=(0, 112), pady=(0, 10))
            self.ssn_entry.grid(row=2, column=1, padx=(175, 0), pady=(0, 10))
            self.code.grid(row=3, column=1, padx=(0, 146), pady=(0, 10))
            self.code_entry.grid(row=3, column=1, padx=(175, 0), pady=(0, 10))
        elif lang == "Español":
            self.ssn.grid(row=2, column=1, padx=(0, 123), pady=(0, 10))
            self.ssn_entry.grid(row=2, column=1, padx=(175, 0), pady=(0, 10))
            self.code.grid(row=3, column=1, padx=(0, 153), pady=(0, 10))
            self.code_entry.grid(row=3, column=1, padx=(175, 0), pady=(0, 10))
        self.show.grid(row=4, column=1, padx=(10, 0), pady=(0, 10))
        self.back_student.grid(row=5, column=0, padx=(0, 10), pady=(0, 0))
        self.system.grid(row=5, column=1, padx=(10, 0), pady=(0, 0))
        self.username_entry.delete(0, "end")
        self.a_buttons_frame.grid_forget()
        self.authentication_frame.grid_forget()

    def login_event_handler(self):
        self.idle = self.cursor.execute("SELECT idle FROM user_data").fetchall()
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.login_event, args=(task_done,))
        event_thread.start()

    # Checks if host entry is true
    def login_event(self, task_done):
        dont_close = False
        try:
            self.focus_set()
            self.destroy_windows()
            self.hide_sidebar_windows()
            self.unbind("<Return>")
            timeout_counter = 0
            skip = False
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            host = self.host_entry.get().replace(" ", "").lower()
            if asyncio.run(self.test_connection(lang)) and self.check_server():
                if host == "uprbay.uprb.edu" or host == "uprbayuprbedu":
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        while not self.tesseract_unzipped:
                            time.sleep(1)
                            timeout_counter += 1
                            if timeout_counter > 5:
                                skip = True
                                break
                        if (TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT")
                                and not TeraTermUI.window_exists("SSH Authentication") and not skip):
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            dont_close = True
                            if term_window.isMinimized:
                                term_window.restore()
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            if (("MENU DE OPCIONES" in text_output or "STUDENTS REQ/DROP" in text_output or "HOLD FLAGS"
                                 in text_output or "PROGRAMA DE CLASES" in text_output or "ACADEMIC STATISTICS" in
                                 text_output or "SNAPSHOT" in text_output or "SOLICITUD DE PRORROGA" in text_output
                                 or "LISTA DE SECCIONES") and "IDENTIFICACION PERSONAL" not in text_output):
                                self.uprb = Application(backend="uia").connect(title="uprbay.uprb.edu - Tera Term VT",
                                                                               timeout=10)
                                self.uprbay_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                                self.uprbay_window.wait("visible", timeout=10)
                                self.after(0, self.initialization_student)
                                self.after(0, self.initialization_class)
                                self.after(0, self.initialization_multiple)
                                self.after(0, self.tuition_frame)
                                self.passed = True
                                self.reset_activity_timer(None)
                                self.start_check_idle_thread()
                                self.in_student_frame = False
                                self.run_fix = True
                                self.language_menu.configure(state="disabled")
                                self.slideshow_frame.pause_cycle()
                                self.host.grid_forget()
                                self.host_entry.grid_forget()
                                self.log_in.grid_forget()
                                self.intro_box.grid_forget()
                                self.introduction.grid_forget()
                                self.slideshow_frame.grid_forget()
                                self.switch_tab()
                                self.set_focus_to_tkinter()
                            else:
                                self.bind("<Return>", lambda event: self.login_event_handler())
                                self.after(0, self.show_error_message, 450, 265,
                                           translation["tera_term_already_running"])
                        else:
                            self.bind("<Return>", lambda event: self.login_event_handler())
                            self.after(0, self.show_error_message, 450, 265,
                                       translation["tera_term_already_running"])
                    else:
                        try:
                            ctypes.windll.user32.BlockInput(True)
                            if self.download or self.teraterm_not_found:
                                self.edit_teraterm_ini(self.teraterm_file)
                            self.uprb = Application(backend="uia").start(self.location) \
                                .connect(title="Tera Term - [disconnected] VT", timeout=10)
                            disconnected = self.uprb.window(title="Tera Term - [disconnected] VT")
                            disconnected.wait("visible", timeout=10)
                            hostText = \
                                self.uprb.TeraTermDisconnectedVt.child_window(title="Host:",
                                                                              control_type="Edit").wrapper_object()
                            hostText.set_text("uprbay.uprb.edu")
                            self.hide_loading_screen()
                            okConn = \
                                self.uprb.TeraTermDisconnectedVt.child_window(title="OK",
                                                                              control_type="Button").wrapper_object()
                            okConn.click()
                            self.show_loading_screen_again()
                            self.uprbay_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                            self.uprbay_window.wait("visible", timeout=10)
                            if self.uprbay_window.child_window(title="Continue", control_type="Button").exists(
                                    timeout=1):
                                self.hide_loading_screen()
                                continue_button = \
                                    self.uprbay_window.child_window(title="Continue",
                                                                    control_type="Button").wrapper_object()
                                continue_button.click()
                                self.show_loading_screen_again()
                            ctypes.windll.user32.BlockInput(False)
                            self.bind("<Return>", lambda event: self.student_event_handler())
                            self.after(0, self.login_frame)
                            self.set_focus_to_tkinter()
                        except Exception as e:
                            if e.__class__.__name__ == "AppStartError":
                                self.bind("<Return>", lambda event: self.login_event_handler())
                                self.after(0, self.show_error_message, 425, 330,
                                           translation["tera_term_failed_to_start"])
                                if not self.download:
                                    self.after(3500, self.download_teraterm)
                                    self.download = True
                elif host != "uprbay.uprb.edu":
                    self.bind("<Return>", lambda event: self.login_event_handler())
                    self.after(0, self.show_error_message, 300, 215, translation["invalid_host"])
            self.show_sidebar_windows()
        except Exception as e:
            print("An error occurred: ", e)
            self.error_occurred = True
        finally:
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            task_done.set()
            if self.error_occurred:
                self.destroy_windows()
                if not dont_close:
                    winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                    subprocess.run(["taskkill", "/f", "/im", "ttermpro.exe"],
                                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                CTkMessagebox(master=self, title="Error Information",
                              message=translation["tera_term_forced_to_close"],
                              icon="warning", button_width=380)
                self.error_occurred = False

    def login_frame(self):
        lang = self.language_menu.get()
        self.initialization_student()
        self.authentication_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 100))
        self.authentication_frame.grid_columnconfigure(2, weight=1)
        self.a_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(0, 0), pady=(0, 40))
        self.a_buttons_frame.grid_columnconfigure(2, weight=1)
        self.title_login.grid(row=0, column=0, padx=(20, 20), pady=10)
        self.uprb_image_grid.grid(row=1, column=0, padx=(0, 0), pady=10)
        self.disclaimer.grid(row=2, column=0, padx=(0, 0), pady=(30, 0))
        if lang == "English":
            self.username.grid(row=3, column=0, padx=(0, 125), pady=(0, 10))
            self.username_entry.grid(row=3, column=0, padx=(90, 0), pady=(0, 10))
        elif lang == "Español":
            self.username.grid(row=3, column=0, padx=(0, 140), pady=(0, 10))
            self.username_entry.grid(row=3, column=0, padx=(60, 0), pady=(0, 10))
        self.back.grid(row=4, column=0, padx=(0, 10), pady=(0, 0))
        self.student.grid(row=4, column=1, padx=(10, 0), pady=(0, 0))
        self.language_menu.configure(state="disabled")
        self.slideshow_frame.pause_cycle()
        self.host.grid_forget()
        self.host_entry.grid_forget()
        self.log_in.grid_forget()
        self.intro_box.grid_forget()
        self.introduction.grid_forget()
        self.slideshow_frame.grid_forget()

    # function that lets user go back to the initial screen
    def go_back_event(self):
        response = None
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if not self.error_occurred:
            msg = CTkMessagebox(master=self, title=translation["go_back_title"],
                                message=translation["go_back"],
                                icon="question",
                                option_1=translation["option_1"], option_2=translation["option_2"],
                                option_3=translation["option_3"],
                                icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
            response = msg.get()
        if TeraTermUI.checkIfProcessRunning("ttermpro") and (
                self.error_occurred or (response and (response[0] == "Yes" or response[0] == "Sí"))):
            self.uprb.kill(soft=True)
        elif TeraTermUI.checkIfProcessRunning("ttermpro") and (
                self.error_occurred or (response and (response[0] == "Yes" or response[0] == "Sí"))):
            subprocess.run(["taskkill", "/f", "/im", "ttermpro.exe"])
        if self.error_occurred or (response and (response[0] == "Yes" or response[0] == "Sí")):
            self.stop_idle_thread()
            self.reset_activity_timer(None)
            self.unbind("<space>")
            self.unbind("<Up>")
            self.unbind("<Down>")
            self.unbind("<Control-Tab>")
            self.bind("<Return>", lambda event: self.login_event_handler())
            self.initialization_class()
            self.initialization_multiple()
            if lang == "Español":
                self.host.grid(row=2, column=0, columnspan=2, padx=(5, 0), pady=(20, 20))
            elif lang == "English":
                self.host.grid(row=2, column=0, columnspan=2, padx=(30, 0), pady=(20, 20))
            self.disable_go_next_buttons()
            self.introduction.grid(row=0, column=1, columnspan=2, padx=(20, 0), pady=(20, 0))
            self.host_entry.grid(row=2, column=1, padx=(20, 0), pady=(20, 20))
            self.log_in.grid(row=3, column=1, padx=(20, 0), pady=(20, 20))
            self.intro_box.grid(row=1, column=1, padx=(20, 0), pady=(0, 150))
            self.slideshow_frame.grid(row=1, column=1, padx=(20, 0), pady=(140, 0))
            self.authentication_frame.grid_forget()
            self.student_frame.grid_forget()
            self.a_buttons_frame.grid_forget()
            self.s_buttons_frame.grid_forget()
            self.tabview.grid_forget()
            self.t_buttons_frame.grid_forget()
            self.multiple_frame.grid_forget()
            self.m_button_frame.grid_forget()
            self.language_menu.configure(state="normal")
            self.multiple.configure(state="normal")
            self.submit.configure(state="normal")
            self.show_classes.configure(state="normal")
            self.search.configure(state="normal")
            self.show.deselect()
            self.search_function_counter = 0
            self.e_counter = 0
            self.m_counter = 0
            self.enrolled_classes_list.clear()
            self.dropped_classes_list.clear()
            self.slideshow_frame.resume_cycle()
            self.run_fix = False
            self.in_student_frame = False
            self.in_enroll_frame = False
            self.in_search_frame = False
            self.idle = None
            if self.error_occurred:
                self.destroy_windows()
                self.username_entry.delete(0, "end")
                self.back.configure(state="normal")
                self.student.configure(state="normal")
                if (self.server_status != "Maintenance message found" and self.server_status != "Timeout") \
                        and self.tesseract_unzipped:
                    winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["automation_error_title"],
                                  message=translation["tera_term_forced_to_close"],
                                  icon="warning", button_width=380)
            self.error_occurred = False

    # function that goes back to Enrolling frame screen
    def go_back_event2(self):
        self.focus_set()
        self.unbind("<Return>")
        self.unbind("<Up>")
        self.unbind("<Down>")
        self.bind("<Control-Tab>", lambda event: self.tab_switcher())
        self.switch_tab()
        lang = self.language_menu.get()
        self.in_multiple_screen = False
        self.tabview.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 85))
        self.tabview.tab(self.enroll_tab).grid_columnconfigure(1, weight=2)
        self.tabview.tab(self.search_tab).grid_columnconfigure(1, weight=2)
        self.search_scrollbar.grid_columnconfigure(1, weight=2)
        self.tabview.tab(self.other_tab).grid_columnconfigure(1, weight=2)
        self.t_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(0, 0), pady=(0, 20))
        self.t_buttons_frame.grid_columnconfigure(1, weight=2)
        self.title_enroll.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
        self.e_classes.grid(row=1, column=1, padx=(44, 0), pady=(0, 0), sticky="w")
        self.e_classes_entry.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        if lang == "English":
            self.e_section.grid(row=2, column=1, padx=(33, 0), pady=(20, 0), sticky="w")
        elif lang == "Español":
            self.e_section.grid(row=2, column=1, padx=(30, 0), pady=(20, 0), sticky="w")
        self.e_section_entry.grid(row=2, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
        self.e_semester.grid(row=3, column=1, padx=(21, 0), pady=(20, 0), sticky="w")
        self.e_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
        self.register.grid(row=4, column=1, padx=(75, 0), pady=(20, 0), sticky="w")
        self.drop.grid(row=4, column=1, padx=(0, 35), pady=(20, 0), sticky="e")
        self.submit.grid(row=5, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
        self.search_scrollbar.grid(row=0, column=1, padx=(0, 0), pady=(0, 0), sticky="nsew")
        self.title_search.grid(row=0, column=1, padx=(0, 0), pady=(0, 20), sticky="n")
        self.s_classes.grid(row=1, column=1, padx=(0, 550), pady=(0, 0), sticky="n")
        self.s_classes_entry.grid(row=1, column=1, padx=(0, 425), pady=(0, 0), sticky="n")
        self.s_semester.grid(row=1, column=1, padx=(0, 270), pady=(0, 0), sticky="n")
        self.s_semester_entry.grid(row=1, column=1, padx=(0, 120), pady=(0, 0), sticky="n")
        if lang == "English":
            self.show_all.grid(row=1, column=1, padx=(85, 0), pady=(2, 0), sticky="n")
        elif lang == "Español":
            self.show_all.grid(row=1, column=1, padx=(85, 0), pady=(0, 7), sticky="n")
        self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
        if self.search_next_page_status:
            self.search.configure(width=85)
            if lang == "English":
                self.search.grid(row=1, column=1, padx=(290, 0), pady=(0, 5), sticky="n")
                self.search_next_page.grid(row=1, column=1, padx=(470, 0), pady=(0, 5), sticky="n")
            elif lang == "Español":
                self.search.grid(row=1, column=1, padx=(285, 0), pady=(0, 5), sticky="n")
                self.search_next_page.grid(row=1, column=1, padx=(465, 0), pady=(0, 5), sticky="n")
        else:
            self.search.configure(width=141)
            self.search.grid(row=1, column=1, padx=(430, 0), pady=(0, 5), sticky="n")
        self.explanation6.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
        self.title_menu.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        if lang == "English":
            self.menu.grid(row=2, column=1, padx=(47, 0), pady=(10, 0), sticky="w")
        elif lang == "Español":
            self.menu.grid(row=2, column=1, padx=(36, 0), pady=(10, 0), sticky="w")
        self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
        self.menu_semester.grid(row=3, column=1, padx=(21, 0), pady=(20, 0), sticky="w")
        self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0), sticky="n")
        if self._1VE_screen:
            self.menu_submit.configure(width=100)
            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0), sticky="n")
            self.go_next_1VE.grid(row=5, column=1, padx=(110, 0), pady=(40, 0), sticky="n")
        elif self._1GP_screen:
            self.menu_submit.configure(width=100)
            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0), sticky="n")
            self.go_next_1GP.grid(row=5, column=1, padx=(110, 0), pady=(40, 0), sticky="n")
        elif self._409_screen:
            self.menu_submit.configure(width=100)
            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0), sticky="n")
            self.go_next_409.grid(row=5, column=1, padx=(110, 0), pady=(40, 0), sticky="n")
        elif self._683_screen:
            self.menu_submit.configure(width=100)
            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0), sticky="n")
            self.go_next_683.grid(row=5, column=1, padx=(110, 0), pady=(40, 0), sticky="n")
        elif self._4CM_screen:
            self.menu_submit.configure(width=100)
            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0), sticky="n")
            self.go_next_1VE.grid(row=5, column=1, padx=(110, 0), pady=(40, 0), sticky="n")
        else:
            self.menu_submit.configure(width=140)
            self.menu_submit.grid(row=5, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
            self.go_next_1VE.grid_forget()
            self.go_next_1GP.grid_forget()
            self.go_next_409.grid_forget()
            self.go_next_683.grid_forget()
            self.go_next_4CM.grid_forget()
        self.back_classes.grid(row=4, column=0, padx=(0, 10), pady=(0, 0), sticky="w")
        self.show_classes.grid(row=4, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        self.multiple.grid(row=4, column=2, padx=(10, 0), pady=(0, 0), sticky="e")
        self.multiple_frame.grid_forget()
        self.m_button_frame.grid_forget()
        self.save_frame.grid_forget()
        self.auto_frame.grid_forget()

    def load_language(self, lang):
        # Check if the translations for the requested language are in the cache
        if lang in self.translations_cache:
            # If they are, return the cached translations without loading the file again
            return self.translations_cache[lang]

        # If the translations are not in the cache, identify the filename
        filename = None
        if lang == "English":
            filename = "english.json"
        elif lang == "Español":
            filename = "spanish.json"

        # Load the translations from the file and store them in the cache
        if filename:
            with open(filename, "r", encoding='utf-8') as f:
                translations = json.load(f)
            self.translations_cache[lang] = translations
            # Return the newly loaded translations
            return translations

        # If the language is not supported, return an empty dictionary or raise an exception
        return {}

    # function for changing language
    def change_language_event(self, lang):
        translation = self.load_language(lang)
        self.focus_set()
        self.initialization_student()
        self.initialization_class()
        self.initialization_multiple()
        self.status_button.configure(text=translation["status_button"])
        self.help_button.configure(text=translation["help_button"])
        self.scaling_label.configure(text=translation["option_label"])
        self.intro_box.configure(state="normal")
        self.intro_box.delete("1.0", "end")
        self.intro_box.insert("0.0", translation["intro_box"])
        self.intro_box.configure(state="disabled")
        self.appearance_mode_optionemenu.configure(values=[translation["light"], translation["dark"],
                                                           translation["default"]])
        self.appearance_mode_optionemenu.set(translation["dark"])
        self.appearance_mode_optionemenu.set(translation["light"])
        self.appearance_mode_optionemenu.set(translation["default"])
        self.introduction.configure(text=translation["introduction"])
        self.host.configure(text=translation["host"])
        self.log_in.configure(text=translation["log_in"])
        self.title_login.configure(text=translation["title_auth"])
        self.disclaimer.configure(text=translation["disclaimer"])
        self.username.configure(text=translation["username"])
        self.student.configure(text=translation["authentication"])
        self.back.configure(text=translation["back"])
        self.title_student.configure(text=translation["title_security"])
        self.ssn.configure(text=translation["ssn"])
        self.code.configure(text=translation["code"])
        self.show.configure(text=translation["show"])
        self.system.configure(text=translation["system"])
        self.back_student.configure(text=translation["back"])
        self.title_enroll.configure(text=translation["title_enroll"])
        self.e_classes.configure(text=translation["class"])
        self.e_section.configure(text=translation["section"])
        self.e_semester.configure(text=translation["semester"])
        self.register.configure(text=translation["register"])
        self.drop.configure(text=translation["drop"])
        self.title_search.configure(text=translation["title_search"])
        self.s_classes.configure(text=translation["class"])
        self.s_semester.configure(text=translation["semester"])
        self.show_all.configure(text=translation["show_all"])
        self.title_menu.configure(text=translation["explanation_menu"])
        self.explanation6.configure(text=translation["title_menu"])
        self.menu.configure(text=translation["menu"])
        self.menu_entry.configure(values=[translation["SRM"], translation["004"], translation["1GP"],
                                          translation["118"], translation["1VE"], translation["3DD"],
                                          translation["409"], translation["683"], translation["1PL"],
                                          translation["4CM"], translation["4SP"], translation["SO"]])
        self.menu_entry.set(translation["SRM"])
        self.menu_semester.configure(text=translation["semester"])
        self.menu_submit.configure(text=translation["submit"])
        self.go_next_1VE.configure(text=translation["go_next"])
        self.go_next_1GP.configure(text=translation["go_next"])
        self.go_next_409.configure(text=translation["go_next"])
        self.go_next_683.configure(text=translation["go_next"])
        self.go_next_4CM.configure(text=translation["go_next"])
        self.search_next_page.configure(text=translation["search_next_page"])
        self.submit.configure(text=translation["submit"])
        self.search.configure(text=translation["search"])
        self.show_classes.configure(text=translation["show_my_classes"])
        self.back_classes.configure(text=translation["back"])
        self.multiple.configure(text=translation["multiple"])
        self.explanation7.configure(text=translation["title_multiple"])
        self.m_class.configure(text=translation["class"])
        self.m_section.configure(text=translation["section"])
        self.m_semester.configure(text=translation["semester"])
        self.m_choice.configure(text=translation["choice"])
        self.back_multiple.configure(text=translation["back"])
        self.submit_multiple.configure(text=translation["submit"])
        for i in range(6):
            self.m_register_menu[i].configure(values=[translation["register"], translation["drop"]])
            self.m_register_menu[i].set(translation["choose"])
        self.auto_enroll.configure(text=translation["auto_enroll"])
        self.save_data.configure(text=translation["save_data"])
        self.register_tooltip.configure(message=translation["register_tooltip"])
        self.drop_tooltip.configure(message=translation["drop_tooltip"])
        self.host_tooltip.configure(message=translation["host_tooltip"])
        self.username_tooltip.configure(message=translation["username_tooltip"])
        self.ssn_tooltip.configure(message=translation["ssn_tooltip"])
        self.code_tooltip.configure(message=translation["code_tooltip"])
        self.back_tooltip.configure(message=translation["back_tooltip"])
        self.back_student_tooltip.configure(message=translation["back_tooltip"])
        self.back_classes_tooltip.configure(message=translation["back_tooltip"])
        self.back_multiple_tooltip.configure(message=translation["back_multiple"])
        self.show_all_tooltip.configure(message=translation["show_all_tooltip"])
        self.show_classes_tooltip.configure(message=translation["show_classes_tooltip"])
        self.m_add_tooltip.configure(message=translation["add_tooltip"])
        self.m_remove_tooltip.configure(message=translation["remove_tooltip"])
        self.multiple_tooltip.configure(message=translation["multiple_tooltip"])
        self.save_data_tooltip.configure(message=translation["save_data_tooltip"])
        self.auto_enroll_tooltip.configure(message=translation["auto_enroll_tooltip"])
        self.search_next_page_tooltip.configure(message=translation["search_next_page_tooltip"])
        if self.enroll_tab != translation["enroll_tab"]:
            self.after(1000, self.rename_tabs)
        if lang == "English":
            self.host.grid(row=2, column=0, columnspan=2, padx=(30, 0), pady=(20, 20))
        elif lang == "Español":
            self.host.grid(row=2, column=0, columnspan=2, padx=(5, 0), pady=(20, 20))

    def rename_tabs(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.tabview.rename(self.enroll_tab, translation["enroll_tab"])
        self.enroll_tab = translation["enroll_tab"]
        self.tabview.rename(self.search_tab, translation["search_tab"])
        self.search_tab = translation["search_tab"]
        self.tabview.rename(self.other_tab, translation["other_tab"])
        self.other_tab = translation["other_tab"]

    def change_semester(self):
        for i in range(1, self.a_counter + 1):
            self.m_semester_entry[i].configure(state="normal")
            self.m_semester_entry[i].set("")
            self.m_semester_entry[i].set(self.m_semester_entry[0].get())
            self.m_semester_entry[i].configure(state="disabled")

    def auto_enroll_event_handler(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.focus_set()
        idle = self.cursor.execute("SELECT idle FROM user_data").fetchall()
        if idle[0][0] != "Disabled":
            if self.auto_enroll.get() == "on":
                msg = CTkMessagebox(master=self, title=translation["submit"],
                                    message=translation["enroll_multiple"],
                                    icon="images/submit.png",
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "darkblue", "darkblue"))
                response = msg.get()
                if response[0] != "Yes" and response[0] != "Sí":
                    self.auto_enroll.deselect()
                    return
            task_done = threading.Event()
            loading_screen = self.show_loading_screen()
            self.update_loading_screen(loading_screen, task_done)
            event_thread = threading.Thread(target=self.auto_enroll_event, args=(task_done,))
            event_thread.start()
        else:
            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
            CTkMessagebox(master=self, title="Auto-Enroll", icon="cancel", button_width=380,
                          message=translation["auto_enroll_idle"])
            self.auto_enroll.deselect()
            self.auto_enroll.configure(state="disabled")

    # Auto-Enroll classes
    def auto_enroll_event(self, task_done):
        with self.lock_thread:
            try:
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.unbind("<Return>")
                self.focus_set()
                self.hide_sidebar_windows()
                self.destroy_windows()
                if self.auto_enroll.get() == "on":
                    self.auto_enroll_bool = True
                    if asyncio.run(self.test_connection(lang)) and self.check_server() and self.check_format():
                        if TeraTermUI.checkIfProcessRunning("ttermpro") or self.passed:
                            ctypes.windll.user32.BlockInput(True)
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.uprbay_window.wait("visible", timeout=10)
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            self.reset_activity_timer(None)
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            ctypes.windll.user32.BlockInput(False)
                            self.set_focus_to_tkinter()
                            turno_index = text_output.find("TURNO MATRICULA:")
                            if turno_index != -1:
                                sliced_text = text_output[turno_index:]
                                parts = sliced_text.split(":", 1)
                                match = re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", parts[1])
                                if match:
                                    date_time_string = match.group()
                                    date_time_string += " AM"
                                else:
                                    self.after(0, self.show_error_message, 300, 215,
                                               translation["failed_to_find_date"])
                                    self.auto_enroll.deselect()
                                    self.auto_enroll_bool = False
                                    return
                            else:
                                if "LISTA DE SECCIONES" not in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(0, self.show_error_message, 300, 215,
                                               translation["failed_to_find_date"])
                                self.auto_enroll.deselect()
                                self.auto_enroll_bool = False
                                return
                            date_time_string = re.sub(r"[^a-zA-Z0-9:/ ]", "", date_time_string)
                            date_time_naive = datetime.strptime(date_time_string, "%m/%d/%Y %I:%M %p")
                            puerto_rico_tz = pytz.timezone("America/Puerto_Rico")
                            your_date = puerto_rico_tz.localize(date_time_naive, is_dst=None)
                            # Get current datetime
                            current_date = datetime.now(puerto_rico_tz)
                            time_difference = your_date - current_date
                            # Dates
                            is_same_date = (current_date.date() == your_date.date())
                            is_past_date = current_date > your_date
                            is_future_date = current_date < your_date
                            is_next_date = (your_date.date() - current_date.date() == timedelta(days=1))
                            is_time_difference_within_6_hours = \
                                timedelta(hours=6, minutes=15) >= time_difference >= timedelta()
                            is_more_than_one_day = (your_date.date() - current_date.date() > timedelta(days=1))
                            is_current_time_ahead = current_date.time() > your_date.time()
                            is_current_time_6_hours_ahead = time_difference >= timedelta(hours=-6)
                            # Comparing Dates
                            if (is_same_date and is_time_difference_within_6_hours) or \
                                    (is_next_date and is_time_difference_within_6_hours):
                                self.countdown_running = True
                                self.after(0, self.disable_enable_gui)
                                # Create timer window
                                self.after(0, self.create_timer_window)
                                # Create a BooleanVar to control the countdown loop
                                self.running_countdown = customtkinter.BooleanVar()
                                self.running_countdown.set(True)
                                # Start the countdown
                                self.after(100, self.countdown, your_date)
                            elif is_past_date or (is_same_date and is_current_time_ahead):
                                if is_current_time_6_hours_ahead:
                                    self.running_countdown = customtkinter.BooleanVar()
                                    self.running_countdown.set(True)
                                    self.started_auto_enroll = True
                                    self.after(0, self.submit_multiple_event_handler)
                                    self.after(0, self.end_countdown)
                                else:
                                    self.after(0, self.show_error_message, 300, 215,
                                               translation["date_past"])
                                    self.auto_enroll_bool = False
                                    self.auto_enroll.deselect()
                            elif (is_future_date or is_more_than_one_day) or \
                                    (is_same_date and not is_time_difference_within_6_hours) or \
                                    (is_next_date and not is_time_difference_within_6_hours):
                                self.after(0, self.show_error_message, 320, 235,
                                           translation["date_not_within_6_hours"])
                                self.auto_enroll_bool = False
                                self.auto_enroll.deselect()
                            if "INVALID ACTION" in text_output:
                                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                send_keys("{ENTER}")
                                self.reset_activity_timer(None)
                                self.after(0, self.bring_back_timer_window)
                        else:
                            self.after(0, self.show_error_message, 300, 215, translation["tera_term_not_running"])
                            self.auto_enroll_bool = False
                            self.auto_enroll.deselect()
                elif self.auto_enroll.get() == "off":
                    self.countdown_running = False
                    self.auto_enroll_bool = False
                    self.after(0, self.disable_enable_gui)
                    # If the countdown is running, stop it and destroy the timer window
                    if hasattr(self, "running_countdown") and self.running_countdown \
                            is not None and self.running_countdown.get():
                        self.after(0, self.end_countdown)
                self.show_sidebar_windows()
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if self.error_occurred:
                    self.destroy_windows()
                    winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["server_maintenance_title"],
                                  message=translation["server_maintenance"],
                                  icon="warning", button_width=380)
                    self.error_occurred = False
                self.bind("<Return>", lambda event: self.submit_multiple_event_handler())

    # Starts the countdown on when the auto-enroll process will occur
    def countdown(self, your_date):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        puerto_rico_tz = pytz.timezone("America/Puerto_Rico")
        current_date = datetime.now(puerto_rico_tz)
        time_difference = your_date - current_date
        total_seconds = time_difference.total_seconds()
        if self.running_countdown.get():
            if total_seconds <= 0:
                # Call enrollment function here
                self.timer_label.configure(text=translation["performing_auto_enroll"])
                self.started_auto_enroll = True
                self.after(5000, self.submit_multiple_event_handler)
                self.after(5000, self.end_countdown)
                return
            else:
                hours, remainder = divmod(total_seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                # If more than an hour remains
                if hours > 0:
                    if lang == "English":
                        if minutes == 0:
                            self.timer_label.configure(
                                text=f"{int(hours)} hours remaining until enrollment")
                        elif hours == 1 and minutes == 1:
                            self.timer_label.configure(
                                text=f"{int(hours)} hour and {int(minutes)} minute \nremaining until enrollment")
                        elif hours == 1:
                            self.timer_label.configure(
                                text=f"{int(hours)} hour and {int(minutes)} minutes \nremaining until enrollment")
                        elif minutes == 1:
                            self.timer_label.configure(
                                text=f"{int(hours)} hours and {int(minutes)} minute \nremaining until enrollment")
                        else:
                            self.timer_label.configure(
                                text=f"{int(hours)} hours and {int(minutes)} minutes \nremaining until enrollment")
                    elif lang == "Español":
                        if minutes == 0:
                            self.timer_label.configure(
                                text=f"{int(hours)} horas restantes hasta la matrícula")
                        elif hours == 1 and minutes == 1:
                            self.timer_label.configure(text=f"{int(hours)} hora y {int(minutes)} "
                                                            f"minuto \nrestante hasta la matrícula")
                        elif hours == 1:
                            self.timer_label.configure(text=f"{int(hours)} hora y {int(minutes)} "
                                                            f"minutos \nrestantes hasta la matrícula")
                        elif minutes == 1:
                            self.timer_label.configure(text=f"{int(hours)} horas y {int(minutes)} "
                                                            f"minuto \nrestante hasta la matrícula")
                        else:
                            self.timer_label.configure(text=f"{int(hours)} horas y {int(minutes)} "
                                                            f"minutos \nrestantes hasta la matrícula")
                    if total_seconds > 3600:
                        seconds_until_next_minute = 60 - current_date.second
                        self.timer_window.after(seconds_until_next_minute * 1000, lambda: self.countdown(your_date))

                else:  # When there's less than an hour remaining
                    # If there's a part of minute left, consider it as a whole minute
                    if _ > 0:
                        minutes += 1
                    if lang == "English":
                        if minutes >= 60:
                            self.timer_label.configure(text="1 hour remaining until enrollment")
                        elif minutes > 1:  # if more than one minute left
                            self.timer_label.configure(
                                text=f"{int(minutes)} minutes remaining until enrollment")
                        else:  # else case for less than or equal to one minute or 60 seconds
                            if total_seconds > 31:  # still display as 1 minute if more than 30 seconds left
                                self.timer_label.configure(text=f"1 minute remaining until enrollment")
                            elif total_seconds >= 2:  # display as seconds if less than or equal to 30 seconds
                                # left but more than or equal to 2 seconds
                                self.timer_label.configure(
                                    text=f"{int(total_seconds)} seconds remaining until enrollment")
                            else:  # exactly 1 second left
                                self.timer_label.configure(text="1 second remaining until enrollment")
                    elif lang == "Español":
                        if minutes >= 60:
                            self.timer_label.configure(text="1 hora restante hasta la matrícula")
                        elif minutes > 1:  # if more than one minute left
                            self.timer_label.configure(
                                text=f"{int(minutes)} minutos restantes hasta la matrícula")
                        else:  # else case for less than or equal to one minute or 60 seconds
                            if total_seconds > 31:  # still display as 1 minute if more than 30 seconds left
                                self.timer_label.configure(text=f"1 minuto restante hasta la matrícula")
                            elif total_seconds >= 2:  # display as seconds if less than or equal to 30 seconds
                                # left but more than or equal to 2 seconds
                                self.timer_label.configure(
                                    text=f"{int(total_seconds)} segundos restantes hasta la matrícula")
                            else:  # exactly 1 second left
                                self.timer_label.configure(text="1 segundo restante hasta la matrícula")

                    # update every minute if there's more than 60 seconds left
                    if total_seconds > 60:
                        seconds_until_next_minute = 60 - current_date.second
                        self.timer_window.after(seconds_until_next_minute * 1000,
                                                lambda: self.countdown(your_date))
                    else:  # update every second if there's less than or equal to 60 seconds left
                        self.timer_window.after(1000, lambda: self.countdown(your_date))

    def end_countdown(self):
        self.auto_enroll_bool = False
        self.countdown_running = False
        self.running_countdown.set(False)  # Stop the countdown
        if self.timer_window and self.timer_window.winfo_exists():
            self.timer_window.destroy()  # Destroy the countdown window
        self.auto_enroll.deselect()
        self.disable_enable_gui()

    def create_timer_window(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        width = 335
        height = 160
        scaling_factor = self.tk.call("tk", "scaling")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width * scaling_factor) / 2
        y = (screen_height - height * scaling_factor) / 2
        self.timer_window = customtkinter.CTkToplevel(self)
        self.timer_window.title(translation["loading"])
        self.timer_window.geometry(f"{width}x{height}+{int(x) + 130}+{int(y)}")
        self.timer_window.attributes("-alpha", 0.90)
        self.timer_window.resizable(False, False)
        self.timer_window.after(256, lambda: self.timer_window.iconbitmap("images/tera-term.ico"))
        self.message_label = customtkinter.CTkLabel(self.timer_window,
                                                    font=customtkinter.CTkFont(
                                                        size=20, weight="bold"),
                                                    text=translation["auto_enroll_activated"])
        self.message_label.pack()
        self.timer_label = customtkinter.CTkLabel(self.timer_window, text="",
                                                  font=customtkinter.CTkFont(size=15))
        self.timer_label.pack()
        self.cancel_button = CustomButton(self.timer_window, text=translation["option_1"], width=260, height=32,
                                          hover_color="darkred", fg_color="red",
                                          command=self.end_countdown)
        self.timer_window.bind("<Escape>", lambda event: self.end_countdown())
        self.cancel_button.pack(pady=25)
        self.timer_window.protocol("WM_DELETE_WINDOW", self.end_countdown)

    def bring_back_timer_window(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.window_exists(translation["auto_enroll"]):
            handle = win32gui.FindWindow(None, translation["auto_enroll"])
            self.timer_window.deiconify()
            win32gui.SetForegroundWindow(handle)
            self.timer_window.focus_force()
            self.timer_window.lift()
            self.timer_window.attributes("-topmost", 1)
            self.timer_window.after_idle(self.timer_window.attributes, "-topmost", 0)

    def disable_enable_gui(self):
        if self.countdown_running:
            self.submit_multiple.configure(state="disabled")
            self.submit.configure(state="disabled")
            self.back_classes.configure(state="disabled")
            self.m_add.configure(state="disabled")
            self.m_remove.configure(state="disabled")
            for i in range(6):
                self.m_classes_entry[i].configure(state="disabled")
                self.m_section_entry[i].configure(state="disabled")
                self.m_register_menu[i].configure(state="disabled")
            self.m_semester_entry[0].configure(state="disabled")
        else:
            self.submit_multiple.configure(state="normal")
            self.submit.configure(state="normal")
            self.back_classes.configure(state="normal")
            if self.a_counter > 0:
                self.m_remove.configure(state="normal")
            if self.a_counter < 5:
                self.m_add.configure(state="normal")
            for i in range(6):
                self.m_classes_entry[i].configure(state="normal")
                self.m_section_entry[i].configure(state="normal")
                self.m_register_menu[i].configure(state="normal")
            self.m_semester_entry[0].configure(state="normal")

    def initialization_student(self):
        # Student Information
        if not self.init_student:
            self.init_student = True
            self.title_student = customtkinter.CTkLabel(master=self.student_frame,
                                                        text="Information to enter the System",
                                                        font=customtkinter.CTkFont(size=20, weight="bold"))
            self.lock = self.images["lock"]
            self.lock_grid = CustomButton(self.student_frame, text="", image=self.lock, command=self.lock_event,
                                          fg_color="transparent", hover=False)
            self.ssn = customtkinter.CTkLabel(master=self.student_frame, text="Social Security Number ")
            self.ssn_entry = CustomEntry(self.student_frame, self, placeholder_text="#########", show="*")
            self.ssn_tooltip = CTkToolTip(self.ssn_entry, message="Required to log-in,\n"
                                                                  "information gets encrypted", bg_color="#1E90FF")
            self.code = customtkinter.CTkLabel(master=self.student_frame, text="Code of Personal Information ")
            self.code_entry = CustomEntry(self.student_frame, self, placeholder_text="####", show="*")
            self.code_tooltip = CTkToolTip(self.code_entry, message="4 digit code included in the\n"
                                                                    "pre-enrollment ticket email", bg_color="#1E90FF")
            self.show = customtkinter.CTkSwitch(master=self.student_frame, text="Show?", command=self.show_event,
                                                onvalue="on", offvalue="off")
            self.bind("<space>", lambda event: self.spacebar_event())
            self.ssn_entry.bind("<Command-c>", lambda e: "break")
            self.ssn_entry.bind("<Control-c>", lambda e: "break")
            self.code_entry.bind("<Command-c>", lambda e: "break")
            self.code_entry.bind("<Control-c>", lambda e: "break")
            self.system = CustomButton(master=self.s_buttons_frame, border_width=2, text="Enter",
                                       text_color=("gray10", "#DCE4EE"), command=self.tuition_event_handler)
            self.back_student = CustomButton(master=self.s_buttons_frame, fg_color="transparent", border_width=2,
                                             text="Back", hover_color="#4E4F50", text_color=("gray10", "#DCE4EE"),
                                             command=self.go_back_event)
            self.back_student_tooltip = CTkToolTip(self.back_student, message="Go back to the main menu\n"
                                                                              "of the application", bg_color="#A9A9A9",
                                                   alpha=0.90)

    def initialization_class(self):
        # Classes
        if not self.init_class:
            self.init_class = True
            self.enroll_tab = "Enroll"
            self.search_tab = "Search"
            self.other_tab = "Other"
            self.tabview.add(self.enroll_tab)
            self.tabview.add(self.search_tab)
            self.tabview.add(self.other_tab)

            # First Tab
            self.title_enroll = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab),
                                                       text="Enroll Classes ",
                                                       font=customtkinter.CTkFont(size=20, weight="bold"))
            self.e_classes = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab), text="Class")
            self.e_classes_entry = CustomEntry(self.tabview.tab(self.enroll_tab), self, placeholder_text="MATE3032")
            self.e_section = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab), text="Section")
            self.e_section_entry = CustomEntry(self.tabview.tab(self.enroll_tab), self, placeholder_text="LM1")
            self.e_semester = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab), text="Semester")
            self.e_semester_entry = CustomComboBox(self.tabview.tab(self.enroll_tab), self,
                                                   values=["C31", "C32", "C33", "C41", "C42", "C43"])
            self.e_semester_entry.set(self.DEFAULT_SEMESTER)
            self.radio_var = tk.StringVar()
            self.register = customtkinter.CTkRadioButton(master=self.tabview.tab(self.enroll_tab), text="Register",
                                                         value="Register", variable=self.radio_var,
                                                         command=self.set_focus)
            self.register_tooltip = CTkToolTip(self.register, message="Enroll class")
            self.drop = customtkinter.CTkRadioButton(master=self.tabview.tab(self.enroll_tab), text="Drop",
                                                     value="Drop", variable=self.radio_var, command=self.set_focus)
            self.drop_tooltip = CTkToolTip(self.drop, message="Drop class")
            self.register.select()

            # Second Tab
            self.search_scrollbar = customtkinter.CTkScrollableFrame(master=self.tabview.tab(self.search_tab),
                                                                     corner_radius=10, fg_color="transparent",
                                                                     width=600, height=300)
            self.search_scrollbar.bind("<Button-1>", lambda event: self.search_scrollbar.focus_set())
            self.title_search = customtkinter.CTkLabel(self.search_scrollbar,
                                                       text="Search Classes ",
                                                       font=customtkinter.CTkFont(size=20, weight="bold"))
            self.s_classes = customtkinter.CTkLabel(self.search_scrollbar, text="Class")
            self.s_classes_entry = CustomEntry(self.search_scrollbar, self, placeholder_text="MATE3032",
                                               width=80)
            self.s_semester = customtkinter.CTkLabel(self.search_scrollbar, text="Semester")
            self.s_semester_entry = CustomComboBox(self.search_scrollbar, self,
                                                   values=["B91", "B92", "B93", "C01", "C02", "C03", "C11",
                                                           "C12", "C13", "C21", "C22", "C23", "C31"], width=80)
            self.s_semester_entry.set(self.DEFAULT_SEMESTER)
            self.show_all = customtkinter.CTkCheckBox(self.search_scrollbar, text="Show All?",
                                                      onvalue="on", offvalue="off", command=self.set_focus)
            self.show_all_tooltip = CTkToolTip(self.show_all, message="Display all sections or\n"
                                                                      "only ones with spaces", bg_color="#1E90FF")
            self.search_next_page = CustomButton(master=self.search_scrollbar, fg_color="transparent", border_width=2,
                                                 text="Next Page", text_color=("gray10", "#DCE4EE"),
                                                 hover_color="#4E4F50", command=self.go_next_search_handler, width=85)
            self.search_next_page_tooltip = CTkToolTip(self.search_next_page, message="There's more sections\n"
                                                                                      "available",
                                                       bg_color="#A9A9A9", alpha=0.90)

            # Third Tab
            self.explanation6 = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
                                                       text="Option Menu ",
                                                       font=customtkinter.CTkFont(size=20, weight="bold"))
            self.title_menu = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
                                                     text="Select code for the screen\n you want to go to: ")
            self.menu = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab), text="Code")
            self.menu_entry = CustomComboBox(self.tabview.tab(self.other_tab), self,
                                             values=["SRM (Main Menu)", "004 (Hold Flags)",
                                                     "1GP (Class Schedule)", "118 (Academic Staticstics)",
                                                     "1VE (Academic Record)", "3DD (Scholarship Payment Record)",
                                                     "409 (Account Balance)", "683 (Academic Evaluation)",
                                                     "1PL (Basic Personal Data)", "4CM (Tuition Calculation)",
                                                     "4SP (Apply for Extension)", "SO (Sign out)"], width=141)
            self.menu_semester = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab), text="Semester")
            self.menu_semester_entry = CustomComboBox(self.tabview.tab(self.other_tab), self,
                                                      values=["B91", "B92", "B93", "C01", "C02", "C03",
                                                              "C11", "C12", "C13", "C21", "C22", "C23", "C31"],
                                                      width=141)
            self.menu_semester_entry.set(self.DEFAULT_SEMESTER)
            self.menu_submit = CustomButton(master=self.tabview.tab(self.other_tab), border_width=2, text="Submit",
                                            text_color=("gray10", "#DCE4EE"), command=self.option_menu_event_handler,
                                            width=141)
            self.go_next_1VE = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text="Next Page",
                                            text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                            command=self.go_next_page_handler, width=100)
            self.go_next_1GP = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text="Next Page",
                                            text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                            command=self.go_next_page_handler, width=100)
            self.go_next_409 = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text="Next Page",
                                            text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                            command=self.go_next_page_handler, width=100)
            self.go_next_683 = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text="Next Page", hover_color="#4E4F50",
                                            text_color=("gray10", "#DCE4EE"),
                                            command=self.go_next_page_handler, width=100)
            self.go_next_4CM = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text="Next Page",
                                            text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                            command=self.go_next_page_handler, width=100)

            # Bottom Buttons
            self.back_classes = CustomButton(master=self.t_buttons_frame, fg_color="transparent", border_width=2,
                                             text="Back", hover_color="#4E4F50", text_color=("gray10", "#DCE4EE"),
                                             command=self.go_back_event)
            self.back_classes_tooltip = CTkToolTip(self.back_classes, alpha=0.90,
                                                   message="Go back to the main menu\n of the application",
                                                   bg_color="#A9A9A9")
            self.submit = CustomButton(master=self.tabview.tab(self.enroll_tab), border_width=2, text="Submit",
                                       text_color=("gray10", "#DCE4EE"), command=self.submit_event_handler)
            self.search = CustomButton(self.search_scrollbar, border_width=2, text="Search",
                                       text_color=("gray10", "#DCE4EE"), command=self.search_event_handler)
            self.show_classes = CustomButton(master=self.t_buttons_frame, border_width=2, text="Show My Classes",
                                             text_color=("gray10", "#DCE4EE"),
                                             command=self.my_classes_event)
            self.show_classes_tooltip = CTkToolTip(self.show_classes, message="Shows the classes you are\n "
                                                                              "enrolled in for a \n"
                                                                              "specific semester", bg_color="#1E90FF")
            self.multiple = CustomButton(master=self.t_buttons_frame, fg_color="transparent", border_width=2,
                                         text="Multiple Classes", hover_color="#4E4F50",
                                         text_color=("gray10", "#DCE4EE"), command=self.multiple_classes_event)
            self.multiple_tooltip = CTkToolTip(self.multiple, message="Enroll Multiple Classes\nat once",
                                               bg_color="blue")

    def initialization_multiple(self):
        # Multiple Classes Enrollment
        if not self.init_multiple:
            self.init_multiple = True
            self.explanation7 = customtkinter.CTkLabel(master=self.multiple_frame,
                                                       text="Enroll Multiple Classes ",
                                                       font=customtkinter.CTkFont(size=20, weight="bold"))
            self.m_class = customtkinter.CTkLabel(master=self.multiple_frame, text="Class")
            self.m_section = customtkinter.CTkLabel(master=self.multiple_frame, text="Section")
            self.m_semester = customtkinter.CTkLabel(master=self.multiple_frame, text="Semester")
            self.m_choice = customtkinter.CTkLabel(master=self.multiple_frame, text="Register/Drop")
            for i in range(6):
                self.m_num_class.append(customtkinter.CTkLabel(master=self.multiple_frame, text=f"{i + 1}."))
                self.m_classes_entry.append(CustomEntry(self.multiple_frame, self,
                                                        placeholder_text=self.placeholder_texts_classes[i]))
                self.m_section_entry.append(CustomEntry(self.multiple_frame, self,
                                                        placeholder_text=self.placeholder_texts_sections[i]))
                self.m_semester_entry.append(CustomComboBox(self.multiple_frame, self,
                                                            values=["C31", "C32", "C33", "C41", "C42", "C43"],
                                                            command=lambda value: self.change_semester()))
                self.m_semester_entry[i].set(self.DEFAULT_SEMESTER)
                self.m_register_menu.append(customtkinter.CTkOptionMenu(master=self.multiple_frame,
                                                                        values=["Register", "Drop"]))
                self.m_register_menu[i].set("Choose")
            self.m_add = CustomButton(master=self.m_button_frame, border_width=2, text="+",
                                      text_color=("gray10", "#DCE4EE"), command=self.add_event, height=40, width=50,
                                      hover=True, fg_color="blue")
            self.m_add_tooltip = CTkToolTip(self.m_add, message="Add more classes", bg_color="blue")
            self.m_remove = CustomButton(master=self.m_button_frame, border_width=2, text="-",
                                         text_color=("gray10", "#DCE4EE"), command=self.remove_event, height=40,
                                         width=50, fg_color="red", hover=True, hover_color="darkred",
                                         state="disabled")
            self.m_remove_tooltip = CTkToolTip(self.m_remove, message="Remove classes", bg_color="red")
            self.back_multiple = CustomButton(master=self.m_button_frame, fg_color="transparent", border_width=2,
                                              text="Back", height=40, width=70, hover_color="#4E4F50",
                                              text_color=("gray10", "#DCE4EE"), command=self.go_back_event2)
            self.back_multiple_tooltip = CTkToolTip(self.back_multiple, alpha=0.90,
                                                    message="Go back to the previous \nscreen", bg_color="#A9A9A9")
            self.submit_multiple = CustomButton(master=self.m_button_frame, border_width=2, text="Submit",
                                                text_color=("gray10", "#DCE4EE"),
                                                command=self.submit_multiple_event_handler, height=40, width=70)
            self.save_data = customtkinter.CTkCheckBox(master=self.save_frame, text="Save Classes ",
                                                       command=self.save_classes, onvalue="on", offvalue="off")
            self.save_data_tooltip = CTkToolTip(self.save_data,
                                                message="Next time you log-in, the classes\n you saved will"
                                                        " already be there!", bg_color="#1E90FF")
            self.auto_enroll = customtkinter.CTkSwitch(master=self.auto_frame, text="Auto-Enroll ", onvalue="on",
                                                       offvalue="off", command=self.auto_enroll_event_handler)
            self.auto_enroll_tooltip = CTkToolTip(self.auto_enroll, message="Will Automatically enroll the classes\n"
                                                                            " you selected at the exact time\n"
                                                                            " the enrollment process becomes\n"
                                                                            " available for you", bg_color="#1E90FF")
            if self.saveCheck:
                if self.saveCheck[0][0] == "Yes":
                    self.save_data.select()
            if self.save:
                num_rows = len(self.save)
                for index, row in enumerate(self.save, start=1):
                    class_value = row[0]
                    section_value = row[1]
                    semester_value = row[2]
                    register_value = row[3]

                    if index <= num_rows:
                        self.m_classes_entry[index - 1].insert(0, class_value)
                        self.m_section_entry[index - 1].insert(0, section_value)
                        if index == 1:
                            self.m_semester_entry[index - 1].set(semester_value)
                        self.m_register_menu[index - 1].set(register_value)
                    else:
                        break

    # saves the information to the database when the app closes
    def save_user_data(self):
        field_values = {
            "welcome": "Checked",
            "host": "uprbay.uprb.edu",
            "language": self.language_menu.get(),
            "appearance": self.appearance_mode_optionemenu.get(),
            "scaling": self.scaling_optionemenu.get(),
            "exit": self.checkbox_state,
        }
        for field, value in field_values.items():
            # for 'host' field, only update or insert when host is "uprbay.uprb.edu"
            if field == "host" and (self.host_entry.get().replace(" ", "").lower() != "uprbay.uprb.edu" and
                                    self.host_entry.get().replace(" ", "").lower() != "uprbayuprbedu"):
                continue
            result = self.cursor.execute(f"SELECT {field} FROM user_data").fetchone()
            if result is None:
                self.cursor.execute(f"INSERT INTO user_data ({field}) VALUES (?)", (value,))
            elif result[0] != value:
                self.cursor.execute(f"UPDATE user_data SET {field} = ? ", (value,))
        with closing(sqlite3.connect("database.db")) as connection:
            with closing(connection.cursor()) as self.cursor:
                self.connection.commit()

    # saves class information for another session
    def save_classes(self):
        save = self.save_data.get()
        lang = self.language_menu.get()
        if save == "on":
            # Clear existing data from the table
            self.cursor.execute("DELETE FROM save_classes")
            self.connection.commit()
            is_empty = False  # Variable to track if any entry is empty
            is_invalid_format = False  # Variable to track if any entry has incorrect format
            # Iterate over the added entries based on self.a_counter
            for index in range(self.a_counter + 1):
                # Get the values from the entry fields and option menus
                class_value = self.m_classes_entry[index].get()
                section_value = self.m_section_entry[index].get()
                semester_value = self.m_semester_entry[index].get()
                register_value = self.m_register_menu[index].get()
                if not class_value or not section_value or not semester_value or register_value in ("Choose", "Escoge"):
                    is_empty = True  # Set the flag if any field is empty or register is not selected
                elif (not re.fullmatch("^[A-Z]{4}[0-9]{4}$", class_value, flags=re.IGNORECASE) or
                      not re.fullmatch("^[A-Z]{2}1$", section_value, flags=re.IGNORECASE) or
                      not re.fullmatch("^[A-Z][0-9]{2}$", semester_value, flags=re.IGNORECASE)):
                    is_invalid_format = True  # Set the flag if any field has incorrect format
                else:
                    # Perform the insert operation
                    self.cursor.execute("INSERT INTO save_classes (class, section, semester, action, 'check')"
                                        " VALUES (?, ?, ?, ?, ?)",
                                        (class_value, section_value, semester_value, register_value, "Yes"))
                    self.connection.commit()
            if is_empty:
                if lang == "English":
                    self.show_error_message(330, 255, "No classes were saved\n"
                                                      " due to missing information")
                elif lang == "Español":
                    self.show_error_message(330, 255, "No se guardaron clases debido\n"
                                                      " a que falta información")
                self.save_data.deselect()
            if is_invalid_format:
                if lang == "English":
                    self.show_error_message(330, 255, "No classes were saved\n"
                                                      " due to incorrect information")
                elif lang == "Español":
                    self.show_error_message(330, 255, "No se guardaron clases debido\n"
                                                      " a que la información está incorrecta")
                self.save_data.deselect()
            else:
                self.cursor.execute("SELECT COUNT(*) FROM save_classes")
                row_count = self.cursor.fetchone()[0]
                if row_count == 0:  # Check the counter after the loop
                    if lang == "English":
                        self.show_error_message(330, 255, "No classes were saved\n"
                                                          " due to incorrect information")
                    elif lang == "Español":
                        self.show_error_message(330, 255, "No se guardaron clases debido\n"
                                                          " a información incorrecta")
                    self.save_data.deselect()
                else:
                    if lang == "English":
                        self.show_success_message(350, 265, "Saved classes successfully")
                    elif lang == "Español":
                        self.show_success_message(350, 265, "Clases guardadas con éxito")
        if save == "off":
            self.cursor.execute("DELETE FROM save_classes")
            self.connection.commit()

    # shows the important information window
    def show_loading_screen(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.loading_screen = customtkinter.CTkToplevel(self)
        self.loading_screen.grab_set()
        self.loading_screen.title(translation["loading"])
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
        loading = customtkinter.CTkLabel(self.loading_screen, text=translation["loading"],
                                         font=customtkinter.CTkFont(size=20, weight="bold"))
        loading.pack(pady=(48, 12))
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
            self.hide_loading_screen()
            self.progress_bar.stop()
            loading_screen.destroy()
        else:
            self.after(100, self.update_loading_screen, loading_screen, task_done)

    # function that lets user see/hide their input (hidden by default)
    def show_event(self):
        self.focus_set()
        show = self.show.get()
        if show == "on":
            self.ssn_entry.unbind("<Command-c>")
            self.ssn_entry.unbind("<Control-c>")
            self.code_entry.unbind("<Command-c>")
            self.code_entry.unbind("<Control-c>")
            self.ssn_entry.configure(show="")
            self.code_entry.configure(show="")
        elif show == "off":
            self.ssn_entry.bind("<Command-c>", lambda e: "break")
            self.ssn_entry.bind("<Control-c>", lambda e: "break")
            self.code_entry.bind("<Command-c>", lambda e: "break")
            self.code_entry.bind("<Control-c>", lambda e: "break")
            self.ssn_entry.configure(show="*")
            self.code_entry.configure(show="*")

    # function that checks if Tera Term is running or not
    @staticmethod
    def checkIfProcessRunning(processName):
        for proc in psutil.process_iter():
            try:
                if processName.lower() in proc.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logging.error(f"Exception occurred: {e}")
                pass
        return False

    # checks if the specified window exists
    @staticmethod
    def window_exists(title):
        try:
            window = gw.getWindowsWithTitle(title)[0]
            return True
        except IndexError:
            return False

    # function that checks if UPRB server is currently running
    def check_server(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        HOST = "uprbay.uprb.edu"
        PORT = 22
        timeout = 3

        try:
            with socket.create_connection((HOST, PORT), timeout=timeout):
                # the connection attempt succeeded
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            # the connection attempt failed
            self.after(0, self.show_error_message, 300, 215, translation["uprb_down"])
            return False

    # captures a screenshot of tera term and performs OCR
    def capture_screenshot(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        tesseract_dir_path = self.app_temp_dir / "Tesseract-OCR"
        if self.tesseract_unzipped and tesseract_dir_path.is_dir():
            window_title = "uprbay.uprb.edu - Tera Term VT"
            hwnd = win32gui.FindWindow(None, window_title)
            win32gui.SetForegroundWindow(hwnd)
            x, y, right, bottom = get_window_rect(hwnd)
            width = right - x
            height = bottom - y
            if self.loading_screen.winfo_exists():
                self.hide_loading_screen()
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            if self.loading_screen.winfo_exists():
                self.show_loading_screen_again()
            screenshot = screenshot.convert('L')
            screenshot = ImageOps.autocontrast(screenshot, cutoff=5)
            # screenshot.save("screenshot.png")
            custom_config = r"--oem 3 --psm 11"
            text = pytesseract.image_to_string(screenshot, config=custom_config)
            return text
        else:
            try:
                with py7zr.SevenZipFile(self.zip_path, mode="r") as z:
                    z.extractall(self.app_temp_dir)
                tesseract_dir = Path(self.app_temp_dir) / "Tesseract-OCR"
                pytesseract.pytesseract.tesseract_cmd = str(tesseract_dir / "tesseract.exe")
                self.tesseract_unzipped = True
                del z, tesseract_dir, tesseract_dir_path
                gc.collect()
                return self.capture_screenshot()
            except Exception as e:
                print(f"Error occurred during unzipping: {str(e)}")
                self.tesseract_unzipped = False
                self.after(0, self.show_error_message, 320, 225, translation["tesseract_error"])
                return

    # creates pdf of the table containing for the searched class
    def create_pdf(self, data, filename, class_name):
        header = None
        lang = self.language_menu.get()
        pdf = SimpleDocTemplate(
            filename,
            pagesize=letter
        )
        table = Table(data)
        # Custom Colors
        blue = colors.Color(0, 0.5, 0.75)  # Lighter blue
        gray = colors.Color(0.7, 0.7, 0.7)  # Lighter gray
        # Define the table style
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), gray),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        table.setStyle(style)
        # Add a header paragraph with the class name
        styles = getSampleStyleSheet()
        header_style = styles["Heading1"]
        header_style.alignment = 1  # Center alignment
        if lang == "English":
            header = Paragraph(f"Class: {class_name}", header_style)
        elif lang == "Español":
            header = Paragraph(f"Clase: {class_name}", header_style)
        # Add some space between the header and the table
        space = Spacer(1, 20)
        # Add the header, space, and table to the elements to be added to the PDF
        elems = [header, space, table]
        # Create the PDF
        pdf.build(elems)

    # function for the user to download the created pdf to their computer
    def download_as_pdf(self):
        filepath = None
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        # Get the class name from the user input
        class_name = self.get_class_for_pdf
        # Gather the table data
        data = self.table.get()
        # Get the path to the user's home directory
        home = os.path.expanduser("~")
        # Append "Downloads" to the home directory path
        downloads = os.path.join(home, "Downloads")
        # Open a dialog for the user to choose the save location and filename
        filepath = filedialog.asksaveasfilename(title=translation["save_pdf"],
                                                defaultextension=".pdf", initialdir=downloads,
                                                filetypes=[('PDF Files', '*.pdf')],
                                                initialfile=f"{class_name}_class_data.pdf")
        if not filepath:
            # User cancelled the dialog, stop the function
            return
        else:
            self.show_success_message(350, 265, translation["pdf_save_success"])
        # Call create_pdf with the chosen filepath
        self.create_pdf(data, filepath, class_name)

    # dipslays the extracted data into a table
    def display_data(self, data):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        modified_data = []
        for item in data:
            if 'TIMES' in item:
                times_parts = item['TIMES'].split('-')
                if len(times_parts) == 2:
                    start, end = times_parts
                    start = start.lstrip('0')
                    end = end.lstrip('0')
                    start = start[:-4] + ":" + start[-4:-2] + " " + start[-2:]
                    end = end[:-4] + ":" + end[-4:-2] + " " + end[-2:]
                    item['TIMES'] = '\n'.join([start, end])
                else:
                    item['TIMES'] = item['TIMES'].lstrip('0')

            if 'INSTRUCTOR' in item:
                parts = item['INSTRUCTOR'].split(',')
                item['INSTRUCTOR'] = '\n'.join(parts)

            modified_data.append(item)

        headers = ['SEC', 'M', 'CRED', 'DAYS', 'TIMES', 'AV', 'INSTRUCTOR']

        table_values = [headers]
        for item in modified_data:
            row = [item.get(header, '') for header in headers]
            table_values.append(row)

        num_rows = len(modified_data) + 1

        # Update the display_class every time, irrespective of whether the table dimensions have changed or not.
        if hasattr(self, 'display_class') and self.display_class is not None:
            self.display_class.grid_forget()
            del self.display_class

        self.display_class = customtkinter.CTkLabel(self.search_scrollbar, text=self.get_class_for_pdf,
                                                    font=customtkinter.CTkFont(size=15, weight="bold", underline=True))
        self.display_class.grid(row=2, column=1, padx=(0, 0), pady=(8, 0), sticky="n")

        if not hasattr(self, 'table') or self.table is None or num_rows != self.table_rows:
            if hasattr(self, 'table') and self.table is not None:
                self.table.grid_forget()
                del self.table

            self.table = ctktable.CTkTable(
                self.search_scrollbar,
                column=len(headers),
                row=num_rows,
                values=table_values,
                header_color="#145DA0"
            )
            self.table.grid(row=2, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
            for i in range(4):
                self.table.edit_column(i, width=55)
            self.table.edit_column(5, width=55)
            tooltip_messages = {
                'SEC': translation["tooltip_sec"],
                'M': translation["tooltip_m"],
                'CRED': translation["tooltip_cred"],
                'DAYS': translation["tooltip_days"],
                'TIMES': translation["tooltip_times"],
                'AV': translation["tooltip_av"],
                'INSTRUCTOR': translation["tooltip_instructor"],
            }
            for i, header in enumerate(headers):
                cell = self.table.get_cell(0, i)
                tooltip_message = tooltip_messages[header]
                tooltip = CTkToolTip(cell, message=tooltip_message, bg_color="#A9A9A9", alpha=0.90)
            self.previous_table_values = table_values
            self.table_rows = num_rows
        else:
            for i, (new_row, old_row) in enumerate(zip(table_values, self.previous_table_values)):
                for j, (new_value, old_value) in enumerate(zip(new_row, old_row)):
                    if new_value != old_value:
                        self.table.insert(i, j, new_value)
            self.previous_table_values = table_values
            self.update_idletasks()

        self.download_pdf = CustomButton(self.search_scrollbar, text=translation["pdf_save_as"],
                                         command=self.download_as_pdf)
        self.download_pdf.grid(row=3, column=1, padx=(0, 0), pady=(10, 0), sticky="n")

    # extracts the text from the searched class to get the important information
    @staticmethod
    def extract_class_data(text):
        lines = text.split("\n")
        data = []
        course_found = False
        invalid_action = False

        for i, line in enumerate(lines):
            if "INVALID ACTION" in line:
                invalid_action = True

            if "COURSE NOT IN COURSE TERM FILE" in line:
                text_next_to_course = line.split("COURSE NOT IN COURSE TERM FILE")[-1].strip()
                if text_next_to_course:
                    course_found = True

        pattern = re.compile(
            r"(\w+)\s+(\w)\s+LEC\s+(\d+\.\d+)\s+(\w+)\s+([\dAMP\-TBA]+)\s+([\d\s]+)?\s+.*?\s*([NFUL\s]*.*)"
        )

        for line in lines:
            match = pattern.search(line)
            if match:
                instructor = match.group(7)
                instructor = re.sub(r'\bN\b', '', instructor)  # remove standalone 'N'
                instructor = re.sub(r'\bFULL\b', '', instructor)  # remove standalone 'FULL'
                instructor = re.sub(r'\bRSVD\b', '', instructor)  # remove standalone 'RSVD'
                instructor = re.sub(r'\bRSTR\b', '', instructor)  # remove standalone 'RSTR'
                instructor = instructor.strip()  # remove leading and trailing whitespace
                data.append({
                    "SEC": match.group(1),
                    "M": match.group(2),
                    "CRED": match.group(3),
                    "DAYS": match.group(4),
                    "TIMES": match.group(5),
                    "AV": match.group(6).strip() if match.group(6) else "0",
                    "INSTRUCTOR": instructor
                })
        return data, course_found, invalid_action

    # checks whether the program can continue it's normal execution or if the server is on maintenance
    def wait_for_prompt(self, prompt_text, maintenance_text, timeout=15):
        start_time = time.time()
        while True:
            text_output = self.capture_screenshot()
            if maintenance_text in text_output:  # Prioritize the maintenance message
                return "Maintenance message found"
            elif prompt_text in text_output:
                return "Prompt found"
            elif time.time() - start_time > timeout:
                return "Timeout"
            time.sleep(1)  # Adjust the delay between screenshots as needed

    # checks whether the user has the requested file
    @staticmethod
    def is_file_in_directory(file_name, directory):
        # Join the directory path and file name
        full_path = os.path.join(directory, file_name)
        # Check if the file exists
        return os.path.isfile(full_path)

    # Necessary things to do while the application is booting, gets done on a separate thread
    def boot_up(self, file_path):
        # Cleanup any leftover files/directories if they exist in any directory under temp_dir
        unzip_tesseract = True
        tesseract_dir_path = self.app_temp_dir / "Tesseract-OCR"
        if tesseract_dir_path.is_dir():
            tesseract_dir = Path(self.app_temp_dir) / "Tesseract-OCR"
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_dir / "tesseract.exe")
            unzip_tesseract = False
            self.tesseract_unzipped = True

        if TeraTermUI.is_file_in_directory("ttermpro.exe", r"C:/Program Files (x86)/teraterm"):
            backup_path = self.app_temp_dir / "TERATERM.ini.bak"
            if not os.path.exists(backup_path):
                backup_path = os.path.join(self.app_temp_dir, os.path.basename(file_path) + ".bak")
                try:
                    shutil.copyfile(file_path, backup_path)
                except FileNotFoundError:
                    print("Tera Term Probably not installed\n"
                          "or installed in a different location from the default")
            # Edits the font that tera term uses to "Lucida Console" to mitigate the chance of the OCR mistaking words
            if not self.can_edit:
                try:
                    with open(file_path, "r") as file:
                        lines = file.readlines()
                except FileNotFoundError:
                    return
                try:
                    with open(file_path, "w") as file:
                        for line in lines:
                            if line.startswith("VTFont="):
                                current_value = line.strip().split("=")[1]
                                font_name = current_value.split(",")[0]
                                self.original_font = current_value
                                updated_value = "Lucida Console" + current_value[len(font_name):]
                                line = f"VTFont={updated_value}\n"
                                self.can_edit = True
                            file.write(line)
                # If something goes wrong, restore the backup
                except Exception as e:
                    print(f"Error occurred: {e}")
                    print("Restoring from backup...")
                    shutil.copyfile(backup_path, file_path)
        else:
            self.teraterm_not_found = True

        if not self.welcome:
            self.log_in.configure(state="normal")
            self.bind("<Return>", lambda event: self.login_event_handler())

        # Unzips Teserract OCR
        if unzip_tesseract:
            try:
                with py7zr.SevenZipFile(self.zip_path, mode="r") as z:
                    z.extractall(self.app_temp_dir)
                tesseract_dir = Path(self.app_temp_dir) / "Tesseract-OCR"
                pytesseract.pytesseract.tesseract_cmd = str(tesseract_dir / "tesseract.exe")
                # tessdata_dir_config = f"--tessdata-dir {tesseract_dir / 'tessdata'}"
                self.tesseract_unzipped = True
            except Exception as e:
                print(f"Error occurred during unzipping: {str(e)}")
                self.tesseract_unzipped = False

        # Generating user_id to ban user from sending feedback if needed
        # If the file doesn't already exist, generate a new UUID and write it to the file
        user_path = Path(self.app_temp_dir) / "user_id.zip"
        if not user_path.is_file():
            user_id = str(uuid.uuid4())
            # Create a new password-protected zip archive and add the text file to it
            with pyzipper.AESZipFile(user_path, "w", encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(self.FEEDBACK.encode())
                zf.writestr("user_id.txt", user_id)

        # Read the user_id from the text file in the password-protected zip archive
        try:
            with pyzipper.AESZipFile(user_path, "r") as zf:
                zf.setpassword(self.FEEDBACK.encode())
                with zf.open("user_id.txt") as f:
                    self.user_id = f.read().decode().strip()
        except Exception as e:
            print(f"Failed to read user_id: {str(e)}")
            self.disable_feedback = True

        # Reads from the feedback.json file to connect to Google's Sheets Api for user feedback
        try:
            with open(self.SERVICE_ACCOUNT_FILE, "rb"):
                archive = pyzipper.AESZipFile(self.SERVICE_ACCOUNT_FILE)
                archive.setpassword(self.FEEDBACK.encode())
                file_contents = archive.read("feedback.json")
                credentials_dict = json.loads(file_contents.decode())
                self.credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
        except Exception as e:
            print(f"Failed to load credentials: {str(e)}")
            self.credentials = None
            self.disable_feedback = True
        del tesseract_dir_path, tesseract_dir, backup_path, line, lines, credentials_dict, user_path
        gc.collect()

    # Deletes Tesseract OCR and tera term config file from the temp folder
    def cleanup_temp(self):
        tesseract_dir = Path(self.app_temp_dir) / "Tesseract-OCR"
        backup_file_path = Path(self.app_temp_dir) / "TERATERM.ini.bak"
        if tesseract_dir == Path(self.app_temp_dir) / "Tesseract-OCR" and tesseract_dir.exists():
            for _ in range(10):  # Retry up to 10 times
                try:
                    shutil.rmtree(tesseract_dir)
                    break  # If the directory was deleted successfully, exit the loop
                except PermissionError:
                    time.sleep(1)  # Wait for 1 second before the next attempt
            # Delete the 'TERATERM.ini.bak' file
            if backup_file_path.exists():
                os.remove(backup_file_path)

    # error window pop up message
    def show_error_message(self, width, height, error_msg_text):
        if self.error and self.error.winfo_exists():
            self.error.lift()
            return
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        top_level_width = width
        top_level_height = height
        center_x = main_window_x + (main_window_width // 2) - (top_level_width // 2)
        center_y = main_window_y + (main_window_height // 2) - (top_level_height // 2)
        window_geometry = f"{width}x{height}+{center_x + 100}+{center_y - 20}"
        winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
        self.error = customtkinter.CTkToplevel(self)
        self.error.title("Error")
        self.error.geometry(window_geometry)
        self.error.attributes("-topmost", True)
        self.error.resizable(False, False)
        self.error.after(256, lambda: self.error.iconbitmap("images/tera-term.ico"))
        my_image = self.images["error"]
        image = customtkinter.CTkLabel(self.error, text="", image=my_image)
        image.pack(padx=10, pady=20)
        error_msg = customtkinter.CTkLabel(self.error,
                                           text=error_msg_text,
                                           font=customtkinter.CTkFont(size=15, weight="bold"))
        error_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)
        self.error.bind("<Escape>", lambda event: self.error.destroy())

    # success window pop up message
    def show_success_message(self, width, height, success_msg_text):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.success and self.success.winfo_exists():
            self.success.lift()
            return
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        top_level_width = width
        top_level_height = height
        center_x = main_window_x + (main_window_width // 2) - (top_level_width // 2)
        center_y = main_window_y + (main_window_height // 2) - (top_level_height // 2)
        window_geometry = f"{width}x{height}+{center_x + 100}+{center_y - 20}"
        winsound.PlaySound("sounds/success.wav", winsound.SND_ASYNC)
        self.success = customtkinter.CTkToplevel()
        self.success.geometry(window_geometry)
        self.success.title(translation["success_title"])
        self.success.attributes("-topmost", True)
        self.success.resizable(False, False)
        self.success.after(256, lambda: self.success.iconbitmap("images/tera-term.ico"))
        my_image = self.images["success"]
        image = customtkinter.CTkLabel(self.success, text="", image=my_image)
        image.pack(padx=10, pady=10)
        success_msg = customtkinter.CTkLabel(self.success, text=success_msg_text,
                                             font=customtkinter.CTkFont(size=15, weight="bold"))
        success_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)
        self.success.after(3500, lambda: self.success.destroy())
        self.success.bind("<Escape>", lambda event: self.success.destroy())

    # Pop window that shows the user more context on why they couldn't enroll their classes
    def show_enrollment_error_information(self):
        self.destroy_windows()
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
        CTkMessagebox(master=self, title=translation["automation_error_title"],
                      message=translation["enrollment_error"], button_width=380)

    # important information window pop up message
    def show_information_message(self, width, height, success_msg_text):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.information and self.information.winfo_exists():
            self.information.lift()
            return
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        top_level_width = width
        top_level_height = height
        center_x = main_window_x + (main_window_width // 2) - (top_level_width // 2)
        center_y = main_window_y + (main_window_height // 2) - (top_level_height // 2)
        window_geometry = f"{width}x{height}+{center_x + 100}+{center_y - 20}"
        winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
        self.information = customtkinter.CTkToplevel()
        self.information.geometry(window_geometry)
        self.information.title(translation["information_title"])
        self.information.resizable(False, False)
        self.information.after(256, lambda: self.information.iconbitmap("images/tera-term.ico"))
        my_image = self.images["information"]
        image = customtkinter.CTkLabel(self.information, text="", image=my_image)
        image.pack(padx=10, pady=10)
        information_msg = customtkinter.CTkLabel(self.information, text=success_msg_text,
                                                 font=customtkinter.CTkFont(size=15, weight="bold"))
        information_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)
        self.information.bind("<Escape>", lambda event: self.information.destroy())

    # function that changes the theme of the application
    def change_appearance_mode_event(self, new_appearance_mode: str):
        self.focus_set()
        if new_appearance_mode == "Oscuro":
            new_appearance_mode = "Dark"
        elif new_appearance_mode == "Claro":
            new_appearance_mode = "Light"
        elif new_appearance_mode == "Sistema":
            new_appearance_mode = "System"
        customtkinter.set_appearance_mode(new_appearance_mode)

    def add_key_bindings(self, event):
        self.bind("<Left>", self.move_slider_left)
        self.bind("<Right>", self.move_slider_right)

    def remove_key_bindings(self, event):
        self.unbind("<Left>")
        self.unbind("<Right>")

    # Moves the scaling slider to the left
    def move_slider_left(self, event):
        if self.move_slider_left_enabled:
            value = self.scaling_optionemenu.get()
            if value != 97:
                value -= 3
                self.scaling_optionemenu.set(value)
                self.change_scaling_event(value)
                self.scaling_tooltip.configure(message=str(self.scaling_optionemenu.get()) + "%")

    # Moves the scaling slider to the right
    def move_slider_right(self, event):
        if self.move_slider_right_enabled:
            value = self.scaling_optionemenu.get()
            if value != 103:
                value += 3
                self.scaling_optionemenu.set(value)
                self.change_scaling_event(value)
                self.scaling_tooltip.configure(message=str(self.scaling_optionemenu.get()) + "%")

    # Keybindings for different widgets
    def spacebar_event(self):
        if self.spacebar_enabled:
            if self.in_student_frame:
                show = self.show.get()
                if show == "on":
                    self.show.deselect()
                elif show == "off":
                    self.show.select()
                self.show_event()
            elif self.in_enroll_frame:
                choice = self.radio_var.get()
                if choice == "Register":
                    self.drop.select()
                elif choice == "Drop":
                    self.register.select()
            elif self.in_search_frame:
                check = self.show_all.get()
                if check == "on":
                    self.show_all.deselect()
                elif check == "off":
                    self.show_all.select()

    def set_focus(self):
        self.focus_set()

    # function that lets your increase/decrease the scaling of the GUI
    def change_scaling_event(self, new_scaling: float):
        self.focus_set()
        new_scaling_float = new_scaling / 100
        customtkinter.set_widget_scaling(new_scaling_float)
        self.scaling_tooltip.configure(message=str(self.scaling_optionemenu.get()) + "%")

    # opens GitHub page
    def github_event(self):
        self.focus_set()
        webbrowser.open("https://github.com/Hanuwa/TeraTermUI")

    def notaso_event(self):
        self.focus_set()
        webbrowser.open("https://notaso.com")

    # opens UPRB main page
    def uprb_event(self):
        self.focus_set()
        webbrowser.open("https://www.uprb.edu")

    # opens a web page containing information about security information
    def lock_event(self):
        self.focus_set()
        webbrowser.open("https://www.techtarget.com/searchsecurity/definition/Advanced-Encryption-Standard")

    # link to download tera term
    def download_teraterm(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
        msg = CTkMessagebox(master=self, title=translation["download_title"],
                            message=translation["download_tera_term"],
                            icon="question",
                            option_1=translation["option_1"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "darkblue", "darkblue"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            webbrowser.open("https://osdn.net/projects/ttssh2/releases/")

    # links to each correspondant curriculum that the user chooses
    def curriculums(self, choice):
        links = {
            "Departments": "https://www.uprb.edu/sample-page/decanato-de-asuntos-academicos/departamentos-academicos-2/",
            "Departamentos": "https://www.uprb.edu/sample-page/decanato-de-asuntos-academicos/departamentos"
                             "-academicos-2/",
            "Accounting": "https://drive.google.com/file/d/0BzdErxfu_JSCSDA0NHMyYVNhdXA3V1ZqX2c1aUlIT21Oc1RF/view"
                          "?resourcekey=0-S2WGur2snYQ0UVIHABbdKg",
            "Contabilidad": "https://drive.google.com/file/d/0BzdErxfu_JSCSDA0NHMyYVNhdXA3V1ZqX2c1aUlIT21Oc1RF/view"
                            "?resourcekey=0-S2WGur2snYQ0UVIHABbdKg",
            "Finance": "https://drive.google.com/file/d/0BzdErxfu_JSCR2gyNzJOeHA2c2EwTklRYmZYZ0Zfck9UT3E0/view"
                       "?resourcekey=0-jizC_JvFrbYxmb9ZScl8RA",
            "Finanzas": "https://drive.google.com/file/d/0BzdErxfu_JSCR2gyNzJOeHA2c2EwTklRYmZYZ0Zfck9UT3E0/view"
                        "?resourcekey=0-jizC_JvFrbYxmb9ZScl8RA",
            "Management": "https://drive.google.com/file/d/0BzdErxfu_JSCVllhTWJGMzRYd3JoemtObDkzX3I5MHNqU3V3/view"
                          "?resourcekey=0-368G697L5iz5EjZ_DCngHQ",
            "Gerencia": "https://drive.google.com/file/d/0BzdErxfu_JSCVllhTWJGMzRYd3JoemtObDkzX3I5MHNqU3V3/view"
                        "?resourcekey=0-368G697L5iz5EjZ_DCngHQ",
            "Marketing": "https://drive.google.com/file/d/0BzdErxfu_JSCa3BIWnZyQmlHa0hGcEVtSlV2d2gxN0dENVcw/view"
                         "?resourcekey=0-hve5FwLHcBdt0K6Je5hMSg",
            "Mercadeo": "https://drive.google.com/file/d/0BzdErxfu_JSCa3BIWnZyQmlHa0hGcEVtSlV2d2gxN0dENVcw/view"
                        "?resourcekey=0-hve5FwLHcBdt0K6Je5hMSg",
            "General Biology": "https://drive.google.com/file/d/11yfoYqXYPybDZmeEmgW8osgSCCmxzjQl/view",
            "Biología General": "https://drive.google.com/file/d/11yfoYqXYPybDZmeEmgW8osgSCCmxzjQl/view",
            "Biology-Human Focus": "https://drive.google.com/file/d/1z-aphTwLLwAY5-G3O7_SXG3ZvvRSN6p9/view",
            "Biología-Enfoque Humano": "https://drive.google.com/file/d/1z-aphTwLLwAY5-G3O7_SXG3ZvvRSN6p9/view",
            "Computer Science": "https://docs.uprb.edu/deptsici/CIENCIAS-DE-COMPUTADORAS-2016.pdf",
            "Ciencias de Computadoras": "https://docs.uprb.edu/deptsici/CIENCIAS-DE-COMPUTADORAS-2016.pdf",
            "Information Systems": "https://docs.uprb.edu/deptsici/SISTEMAS-INFORMACION-2016.pdf",
            "Sistemas de Información": "https://docs.uprb.edu/deptsici/SISTEMAS-INFORMACION-2016.pdf",
            "Social Sciences": "https://drive.google.com/file/d/1cZnD6EhBsu7u6U8IVZoeK0VHgQmYt3sf/view",
            "Ciencias Sociales": "https://drive.google.com/file/d/1cZnD6EhBsu7u6U8IVZoeK0VHgQmYt3sf/view",
            "Physical Education": "https://drive.google.com/file/d/0BzdErxfu_JSCQWFEWlpCSnRFMVFGQnZoTXRyZHJiMzBkc2dZ"
                                  "/view?resourcekey=0-zLsz0IP1Ajy853kM9I2PQg",
            "Educación Física": "https://drive.google.com/file/d/0BzdErxfu_JSCQWFEWlpCSnRFMVFGQnZoTXRyZHJiMzBkc2dZ/view"
                                "?resourcekey=0-zLsz0IP1Ajy853kM9I2PQg",
            "Electronics": "https://drive.google.com/file/d/1tfzaHKilu5iQccD2sBzD8O_6UlXtSREF/view",
            "Electrónica": "https://drive.google.com/file/d/1tfzaHKilu5iQccD2sBzD8O_6UlXtSREF/view",
            "Equipment Management": "https://drive.google.com/file/d/13ohtab5ns6qO2QIHouScKtrFHrM7X3zl/view",
            "Gerencia de Materiales": "https://drive.google.com/file/d/13ohtab5ns6qO2QIHouScKtrFHrM7X3zl/view",
            "Pedagogy": "https://www.upr.edu/bayamon/wp-content/uploads/sites/9/2015/06/Secuencia-curricular-aprobada"
                        "-en-mayo-de-2013.pdf",
            "Pedagogía": "https://www.upr.edu/bayamon/wp-content/uploads/sites/9/2015/06/Secuencia-curricular"
                         "-aprobada-en-mayo-de-2013.pdf",
            "Chemistry": "https://drive.google.com/file/d/0BzdErxfu_JSCNHJENWNaY1JmZjNSSU5mR2U5SnVOc1gxUTVJ/view"
                         "?resourcekey=0-CWkQQfEczPuV0Rx4KQnkBA",
            "Química": "https://drive.google.com/file/d/0BzdErxfu_JSCNHJENWNaY1JmZjNSSU5mR2U5SnVOc1gxUTVJ/view"
                       "?resourcekey=0-CWkQQfEczPuV0Rx4KQnkBA",
            "Nursing": "https://drive.google.com/file/d/0BzdErxfu_JSCaF9tMFc3Y0hnRGpsZ1dMTXFPRjRMUlVEQ1ZZ/view"
                       "?resourcekey=0-JQUivKyxJQlXP-2K008d_Q",
            "Enfermería": "https://drive.google.com/file/d/0BzdErxfu_JSCaF9tMFc3Y0hnRGpsZ1dMTXFPRjRMUlVEQ1ZZ/view"
                          "?resourcekey=0-JQUivKyxJQlXP-2K008d_Q",
            "Office Systems": "https://docs.uprb.edu/deptsofi/curriculo-BA-SOFI-agosto-2016.pdf",
            "Sistemas de Oficina": "https://docs.uprb.edu/deptsofi/curriculo-BA-SOFI-agosto-2016.pdf",
            "Information Engineering": "https://drive.google.com/file/d/1mYCHmCy3Mb2fDyp9EiFEtR0j4-rsDdlN/view",
            "Ingeniería de la Información": "https://drive.google.com/file/d/1mYCHmCy3Mb2fDyp9EiFEtR0j4-rsDdlN/view"}

        url = links.get(choice, None)
        if url:
            webbrowser.open(url)

    # will tell the user that there's a new update available for the application
    def update_app(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        latest_version = self.get_latest_release()
        if not self.connection_error:
            if not TeraTermUI.compare_versions(latest_version, self.USER_APP_VERSION):
                winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                msg = CTkMessagebox(master=self, title=translation["update_popup_title"],
                                    message=translation["update_popup_message"],
                                    icon="question",
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"], icon_size=(65, 65),
                                    button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "darkblue", "darkblue"))
                response = msg.get()
                if response[0] == "Yes" or response[0] == "Sí":
                    webbrowser.open("https://github.com/Hanuwa/TeraTermUI/releases/latest")
            else:
                winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                CTkMessagebox(master=self, title="Info", message=translation["update_up_to_date"], button_width=380)

    # (Unused) determines the hardware of the users' computer and change the time.sleep seconds respectively
    # def get_sleep_time(self):
    # cpu_count = psutil.cpu_count()
    # self.avg_cpu_load = sum(self.cpu_load_history) / len(self.cpu_load_history)
    # if cpu_count >= 8 and self.avg_cpu_load <= 50:
    # sleep_time = 0.5
    # elif cpu_count >= 6 and self.avg_cpu_load <= 50:
    # sleep_time = 0.75
    # elif cpu_count >= 4 and self.avg_cpu_load <= 50:
    # sleep_time = 1
    # elif cpu_count >= 8 and self.avg_cpu_load >= 50:
    # sleep_time = 0.90
    # elif cpu_count >= 6 and self.avg_cpu_load >= 50:
    # sleep_time = 1.2
    # elif cpu_count >= 4 and self.avg_cpu_load >= 50:
    # sleep_time = 1.5
    # elif not self.cpu_load_history:
    # sleep_time = 2
    # else:
    # sleep_time = 2

    # return sleep_time

    # (Unused) Monitors the usage of the CPU of the user to determine the time.sleep of how long should the function
    # take before executing something
    # def cpu_monitor(self, interval=1):
    # while not self.stop_monitor.is_set():
    # cpu_percent = psutil.cpu_percent(interval=interval)
    # self.cpu_load_history.append(cpu_percent)

    def fix_execution_event_handler(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if TeraTermUI.checkIfProcessRunning("ttermpro") and self.run_fix:
            msg = CTkMessagebox(master=self, title=translation["fix_messagebox_title"],
                                message=translation["fix_messagebox"],
                                icon="warning",
                                option_1=translation["option_1"], option_2=translation["option_2"],
                                option_3=translation["option_3"], icon_size=(65, 65),
                                button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
            response = msg.get()
            if response[0] == "Yes" or response[0] == "Sí":
                task_done = threading.Event()
                loading_screen = self.show_loading_screen()
                self.update_loading_screen(loading_screen, task_done)
                event_thread = threading.Thread(target=self.fix_execution, args=(task_done,))
                event_thread.start()

    # If user messes up the execution of the program this can solve it and make program work as expected
    def fix_execution(self, task_done):
        with self.lock_thread:
            try:
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.unbind("<Return>")
                self.focus_set()
                self.hide_sidebar_windows()
                self.destroy_windows()
                ctypes.windll.user32.BlockInput(True)
                term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                if term_window.isMinimized:
                    term_window.restore()
                self.uprbay_window.wait("visible", timeout=10)
                send_keys("{TAB}")
                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                send_keys("{ENTER}")
                self.reset_activity_timer(None)
                screenshot_thread = threading.Thread(target=self.capture_screenshot)
                screenshot_thread.start()
                screenshot_thread.join()
                text_output = self.capture_screenshot()
                if "INVALID ACTION" in text_output:
                    send_keys("{TAB}")
                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                    send_keys("{ENTER}")
                    self.reset_activity_timer(None)
                ctypes.windll.user32.BlockInput(False)
                self.after(0, self.show_information_message, 370, 250,
                           translation["fix_after"])
                self.show_sidebar_windows()
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if self.error_occurred:
                    self.destroy_windows()
                    winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["automation_error_title"],
                                  message=translation["automation_error"],
                                  icon="warning", button_width=380)
                    self.error_occurred = False
                self.switch_tab()

    # Starts the check for idle thread
    def start_check_idle_thread(self):
        if self.idle[0][0] != "Disabled":
            self.is_idle_thread_running = True
            self.check_idle_thread = threading.Thread(target=self.check_idle)
            self.check_idle_thread.start()

    # Checks if the user is idle for 5 minutes and does some action so that Tera Term doesn't close by itself
    def check_idle(self):
        self.idle_num_check = 0
        while self.is_idle_thread_running and not self.stop_check_idle.is_set():
            with self.lock_thread:
                if time.time() - self.last_activity >= 300:
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        self.unbind("<Return>")
                        self.focus_set()
                        self.hide_sidebar_windows()
                        self.destroy_windows()
                        ctypes.windll.user32.BlockInput(True)
                        term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                        if term_window.isMinimized:
                            term_window.restore()
                        self.uprbay_window.wait("visible", timeout=10)
                        self.unfocus_tkinter()
                        if self.idle_num_check == 0:
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            if "INVALID ACTION" in text_output:
                                send_keys("{TAB}")
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                send_keys("{ENTER}")
                            term_window.minimize()
                            self.after(0, self.disable_go_next_buttons)
                        elif self.idle_num_check > 0:
                            send_keys("{TAB 2}")
                            term_window.minimize()
                        ctypes.windll.user32.BlockInput(False)
                        self.last_activity = time.time()
                        if not self.countdown_running:
                            self.idle_num_check += 1
                        if self.countdown_running:
                            self.idle_num_check = 1
                        self.show_sidebar_windows()
                        if not self.in_multiple_screen:
                            self.switch_tab()
                        self.bring_back_timer_window()
                    else:
                        self.stop_check_idle.is_set()
            if self.idle_num_check == 6:
                break
            time.sleep(3)

    # Stops the check for idle thread
    def stop_idle_thread(self):
        self.is_idle_thread_running = False

    # resets the idle timer when user interacts with something within the application
    def reset_activity_timer(self, _):
        self.last_activity = time.time()
        self.idle_num_check = 0

    # Disables check_idle functionality
    def disable_enable_idle(self):
        if self.disableIdle.get() == "on":
            idle = self.cursor.execute("SELECT idle FROM user_data").fetchall()
            if len(idle) == 0:
                self.cursor.execute("INSERT INTO user_data (idle) VALUES (?)", ("Disabled",))
            elif len(idle) == 1:
                self.cursor.execute("UPDATE user_data SET idle=?", ("Disabled",))
            self.reset_activity_timer(None)
            self.stop_idle_thread()
        if self.disableIdle.get() == "off":
            idle = self.cursor.execute("SELECT idle FROM user_data").fetchall()
            if len(idle) == 0:
                self.cursor.execute("INSERT INTO user_data (idle) VALUES (?)", ("Enabled",))
            elif len(idle) == 1:
                self.cursor.execute("UPDATE user_data SET idle=?", ("Enabled",))
            if self.auto_enroll is not None:
                self.auto_enroll.configure(state="normal")
            if self.run_fix and TeraTermUI.checkIfProcessRunning("ttermpro"):
                self.hide_sidebar_windows()
                self.destroy_windows()
                ctypes.windll.user32.BlockInput(True)
                term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                if term_window.isMinimized:
                    term_window.restore()
                self.uprbay_window.wait("visible", timeout=30)
                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                send_keys("{ENTER}")
                ctypes.windll.user32.BlockInput(False)
                self.reset_activity_timer(None)
                self.start_check_idle_thread()
                self.show_sidebar_windows()
        self.connection.commit()

    @staticmethod
    async def fetch(session, url):
        try:
            async with session.get(url, timeout=3.0) as response:
                if response.status != 200:
                    print(f"Non-200 response code: {response.status}")
                    return False
                return True
        except aiohttp.ClientConnectionError:
            print(f"Failed to connect to {url}")
            return False
        except aiohttp.ClientTimeout:
            print(f"Request to {url} timed out")
            return False
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False

    async def test_connection(self, lang):
        translation = self.load_language(lang)
        urls = ["http://www.google.com/", "http://www.bing.com/", "http://www.yahoo.com/"]
        async with aiohttp.ClientSession() as session:
            tasks = [TeraTermUI.fetch(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
        connected = any(results)
        if not connected:
            self.after(0, self.show_error_message, 300, 215, translation["no_internet"])
        return connected

    # Set focus on the UI application window
    def set_focus_to_tkinter(self):
        tk_handle = win32gui.FindWindow(None, "Tera Term UI")
        win32gui.SetForegroundWindow(tk_handle)
        self.focus_force()
        self.lift()
        self.attributes("-topmost", 1)
        self.after_idle(self.attributes, "-topmost", 0)

    # Set focus on Tera Term window
    def unfocus_tkinter(self):
        pywinauto_handle = self.uprb.top_window().handle
        win32gui.SetForegroundWindow(pywinauto_handle)

    def tab_switcher(self):
        if self.tabview.get() == self.enroll_tab:
            self.tabview.set(self.search_tab)
        elif self.tabview.get() == self.search_tab:
            self.tabview.set(self.other_tab)
        elif self.tabview.get() == self.other_tab:
            self.tabview.set(self.enroll_tab)
        self.switch_tab()

    # Changes keybind depending on the tab the user is currently on
    def switch_tab(self):
        self.focus_set()
        enroll_frame = self.tabview.tab(self.enroll_tab)
        other_frame = self.tabview.tab(self.other_tab)
        if self.tabview.get() == self.enroll_tab:
            self.in_search_frame = False
            self.in_enroll_frame = True
            self.bind("<Return>", lambda event: self.submit_event_handler())
            self.bind("<space>", lambda event: self.spacebar_event())
            enroll_frame.bind("<Button-1>", lambda event: enroll_frame.focus_set())
        elif self.tabview.get() == self.search_tab:
            if hasattr(self, 'table') and self.table is not None:
                self.display_class.grid_forget()
                self.table.grid_forget()
                self.download_pdf.grid_forget()
                self.after(350, self.load_table)
            self.in_enroll_frame = False
            self.in_search_frame = True
            self.bind("<Return>", lambda event: self.search_event_handler())
            self.bind("<space>", lambda event: self.spacebar_event())
        elif self.tabview.get() == self.other_tab:
            self.in_enroll_frame = False
            self.in_search_frame = False
            self.bind("<Return>", lambda event: self.option_menu_event_handler())
            other_frame.bind("<Button-1>", lambda event: other_frame.focus_set())

    def load_table(self):
        self.display_class.grid(row=2, column=1, padx=(0, 0), pady=(8, 0), sticky="n")
        self.table.grid(row=2, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
        self.download_pdf.grid(row=3, column=1, padx=(0, 0), pady=(10, 0), sticky="n")

    # Creates the status window
    def status_button_event(self):
        if self.status and self.status.winfo_exists():
            self.status.lift()
            return
        self.focus_set()
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.status = SmoothFadeToplevel()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        scaling_factor = self.tk.call("tk", "scaling")
        x_position = int((screen_width - 475 * scaling_factor) / 2)
        y_position = int((screen_height - 275 * scaling_factor) / 2)
        window_geometry = f"{475}x{280}+{x_position + 130}+{y_position + 18}"
        self.status.geometry(window_geometry)
        self.status.title(translation["status"])
        self.status.after(256, lambda: self.status.iconbitmap("images/tera-term.ico"))
        self.status.resizable(False, False)
        scrollable_frame = customtkinter.CTkScrollableFrame(self.status, width=475, height=280,
                                                            fg_color=("#e6e6e6", "#222222"))
        scrollable_frame.pack()
        title = customtkinter.CTkLabel(scrollable_frame, text=translation["status_title"],
                                       font=customtkinter.CTkFont(size=20, weight="bold"))
        title.pack()
        version = customtkinter.CTkLabel(scrollable_frame, text=translation["app_version"])
        version.pack()
        self.feedbackText = customtkinter.CTkTextbox(scrollable_frame, wrap="word", border_spacing=8, width=300,
                                                     height=170, fg_color=("#ffffff", "#111111"))
        self.feedbackText.pack(pady=10)
        self.feedbackSend = CustomButton(scrollable_frame, border_width=2, text=translation["feedback"],
                                         text_color=("gray10", "#DCE4EE"), command=self.start_feedback_thread)
        self.feedbackSend.pack()
        checkUpdateText = customtkinter.CTkLabel(scrollable_frame, text=translation["update_title"])
        checkUpdateText.pack(pady=5)
        checkUpdate = CustomButton(scrollable_frame, border_width=2, image=self.images["update"],
                                   text=translation["update"], anchor="w", text_color=("gray10", "#DCE4EE"),
                                   command=self.update_app)
        checkUpdate.pack()
        website = customtkinter.CTkLabel(scrollable_frame, text=translation["website"])
        website.pack(pady=5)
        link = CustomButton(scrollable_frame, border_width=2, image=self.images["link"], text=translation["link"],
                            anchor="w", text_color=("gray10", "#DCE4EE"), command=self.github_event)
        link.pack()
        notaso = customtkinter.CTkLabel(scrollable_frame, text=translation["notaso_title"])
        notaso.pack(pady=5)
        notasoLink = CustomButton(scrollable_frame, border_width=2, image=self.images["link"],
                                  text=translation["notaso_link"], anchor="w", text_color=("gray10", "#DCE4EE"),
                                  command=self.notaso_event)
        notasoLink.pack()
        faqText = customtkinter.CTkLabel(scrollable_frame, text=translation["faq"],
                                         font=customtkinter.CTkFont(size=15, weight="bold"))
        faqText.pack()
        qaTable = [[translation["q"], translation["a"]],
                   [translation["q1"], translation["a1"]],
                   [translation["q2"], translation["a2"]]]
        faq = ctktable.CTkTable(scrollable_frame, row=3, column=2, values=qaTable)
        faq.pack(expand=True, fill="both", padx=20, pady=20)
        self.status.bind("<Escape>", lambda event: self.status.destroy())

    # Function to call the Google Sheets API
    def call_sheets_api(self, values):
        lang = self.language_menu.get()
        if asyncio.run(self.test_connection(lang)):
            self.connection_error = False
            try:
                service = build("sheets", "v4", credentials=self.credentials)
            except:
                DISCOVERY_SERVICE_URL = "https://sheets.googleapis.com/$discovery/rest?version=v4"
                service = build("sheets", "v4", credentials=self.credentials,
                                discoveryServiceUrl=DISCOVERY_SERVICE_URL)
            now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
            body = {
                "values": [[now, self.user_id, values[0][0]]]
            }

            try:
                result = service.spreadsheets().values().append(
                    spreadsheetId=self.SPREADSHEET_ID, range=self.RANGE_NAME,
                    valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                    body=body).execute()
                return result
            except HttpError as error:
                print(f"An error occurred: {error}")
                return None
        else:
            self.connection_error = True

    def is_user_banned(self, user_id):
        lang = self.language_menu.get()
        if asyncio.run(self.test_connection(lang)):
            self.connection_error = False
            try:
                service = build("sheets", "v4", credentials=self.credentials)
            except:
                DISCOVERY_SERVICE_URL = "https://sheets.googleapis.com/$discovery/rest?version=v4"
                service = build("sheets", "v4", credentials=self.credentials,
                                discoveryServiceUrl=DISCOVERY_SERVICE_URL)
            try:
                # Get all values in column A from the banned users spreadsheet
                result = service.spreadsheets().values().get(
                    spreadsheetId=self.SPREADSHEET_BANNED_ID, range=self.RANGE_NAME).execute()
                values = result.get("values", [])
                # Check if the user_id is in the values
                flat_values = [item for sublist in values for item in sublist]
                if user_id in flat_values:
                    return True
                else:
                    return False
            except HttpError as error:
                print(f"An error occurred: {error}")
                return False
        else:
            self.connection_error = True

    def start_feedback_thread(self):
        timeout_counter = 0
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.feedbackSend.configure(state="disabled")
        while self.user_id is None:
            time.sleep(1)
            timeout_counter += 1
            if timeout_counter > 5:
                break
        if self.user_id is None:
            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
            CTkMessagebox(title="Error", message=translation["feedback_unavailable"],
                          icon="cancel", button_width=380)
        else:
            msg = CTkMessagebox(master=self, title="Submit",
                                message=translation["submit_feedback"],
                                icon="question",
                                option_1=translation["option_1"], option_2=translation["option_2"],
                                option_3=translation["option_3"], icon_size=(65, 65),
                                button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
            response = msg.get()
            if response[0] == "Yes" or response[0] == "Sí":
                feedback_thread = threading.Thread(target=self.submit_feedback)
                feedback_thread.start()
            else:
                self.feedbackSend.configure(state="normal")

    # Submits feedback from the user to a Google sheet
    def submit_feedback(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if not self.is_banned_flag:
            self.is_banned = self.is_user_banned(self.user_id)
            if not self.connection_error:
                self.is_banned_flag = True
        if not self.disable_feedback and not self.is_banned:
            current_date = datetime.today().strftime("%Y-%m-%d")
            date = self.cursor.execute("SELECT date FROM user_data WHERE date IS NOT NULL").fetchall()
            dates_list = [record[0] for record in date]
            if current_date not in dates_list:
                feedback = self.feedbackText.get("1.0", customtkinter.END).strip()
                word_count = len(feedback.split())
                if word_count < 1000:
                    feedback = self.feedbackText.get("1.0", customtkinter.END).strip()
                    if feedback:
                        result = self.call_sheets_api([[feedback]])
                        if result:
                            def show_success():
                                winsound.PlaySound("sounds/success.wav", winsound.SND_ASYNC)
                                CTkMessagebox(title=translation["success_title"], icon="check",
                                              message=translation["feedback_success"], button_width=380)

                            self.after(0, show_success)
                            resultDate = self.cursor.execute("SELECT date FROM user_data").fetchall()
                            if len(resultDate) == 0:
                                self.cursor.execute("INSERT INTO user_data (date) VALUES (?)", (current_date,))
                            elif len(resultDate) == 1:
                                self.cursor.execute("UPDATE user_data SET date=?", (current_date,))
                            self.connection.commit()
                            self.feedbackText.delete("1.0", customtkinter.END)
                        else:
                            if not self.connection_error:
                                def show_error():
                                    winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                    CTkMessagebox(title="Error",
                                                  message=translation["feedback_error"],
                                                  icon="cancel", button_width=380)

                                self.after(0, show_error)
                    else:
                        if not self.connection_error:
                            def show_error():
                                winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                CTkMessagebox(title="Error", message=translation["feedback_empty"],
                                              icon="cancel", button_width=380)

                            self.after(0, show_error)
                else:
                    if not self.connection_error:
                        def show_error():
                            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                            CTkMessagebox(title="Error", message=translation["feedback_1000"],
                                          icon="cancel", button_width=380)

                        self.after(0, show_error)
            else:
                if not self.connection_error:
                    def show_error():
                        winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                        CTkMessagebox(title="Error", message=translation["feedback_day"],
                                      icon="cancel", button_width=380)

                    self.after(0, show_error)
        else:
            if not self.connection_error:
                def show_error():
                    winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                    CTkMessagebox(title="Error", message=translation["feedback_unavailable"],
                                  icon="cancel", button_width=380)

                self.after(0, show_error)
        self.feedbackSend.configure(state="normal")

    # Function that lets user select where their Tera Term application is located
    def change_location_event(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        filename = filedialog.askopenfilename(initialdir="C:/",
                                              title=translation["select_tera_term"],
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
            self.connection.commit()
            self.show_success_message(350, 265, translation["tera_term_success"])
            self.edit_teraterm_ini(self.teraterm_file)
        self.help.lift()

    # disables scrolling for the class list
    def disable_scroll(self, event):
        widget = self.help.winfo_containing(event.x_root, event.y_root)
        if widget is self.class_list:
            # if Listbox is empty, allow scrolling of the main frame
            if self.class_list.size() == 0:
                return None
            else:
                self.class_list.yview_scroll(int(-1 * (event.delta / 120)), "units")
                return "break"
        else:
            return None

    # list of classes available for all departments in the university
    def search_classes(self, event):
        lang = self.language_menu.get()
        self.class_list.delete(0, tk.END)  # always clear the list box first
        search_term = self.search_box.get().strip().lower()
        if search_term == "" or len(search_term) == 0:  # if the search term is empty, do not return any records
            return
        if search_term in ["all", "todo", "todos"]:
            query = "SELECT name, code FROM courses"
        else:
            query_conditions = [f"LOWER(name) LIKE '%{search_term}%'", f"LOWER(code) LIKE '%{search_term}%'"]
            query_conditions_str = " OR ".join(query_conditions)
            query = f"SELECT name, code FROM courses WHERE {query_conditions_str}"

        results = self.cursor.execute(query).fetchall()
        if not results:  # if there are no results, display a message
            self.class_list.delete(0, tk.END)
            if lang == "English":
                self.class_list.insert(tk.END, "NO RESULTS FOUND")
            elif lang == "Español":
                self.class_list.insert(tk.END, "NO SE ENCONTRARON RESULTADOS")
        else:
            for row in results:
                self.class_list.insert(tk.END, row[0])

    # query for searching for either class code or name
    def show_class_code(self, event):
        lang = self.language_menu.get()
        selection = self.class_list.curselection()
        if len(selection) == 0:
            return
        selected_class = self.class_list.get(self.class_list.curselection())
        query = "SELECT code FROM courses WHERE name = ? OR code = ?"
        result = self.cursor.execute(query, (selected_class, selected_class)).fetchone()
        if result is None:
            self.class_list.delete(0, tk.END)
            if lang == "English":
                self.class_list.insert(tk.END, "NO RESULTS FOUND")
            elif lang == "Español":
                self.class_list.insert(tk.END, "NO SE ENCONTRARON RESULTADOS")
        else:
            self.search_box.delete(0, tk.END)
            self.search_box.insert(0, result[0])

    # Creates the Help window
    def help_button_event(self):
        if self.help and self.help.winfo_exists():
            self.help.lift()
            return
        self.focus_set()
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        bg_color = "#0e95eb"
        fg_color = "#333333"
        listbox_font = ("Arial", 11)
        self.help = SmoothFadeToplevel()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        scaling_factor = self.tk.call("tk", "scaling")
        x_position = int((screen_width - 475 * scaling_factor) / 2)
        y_position = int((screen_height - 275 * scaling_factor) / 2)
        window_geometry = f"{475}x{280}+{x_position + 130}+{y_position + 18}"
        self.help.geometry(window_geometry)
        self.help.title(translation["help"])
        self.help.after(256, lambda: self.help.iconbitmap("images/tera-term.ico"))
        self.help.resizable(False, False)
        scrollable_frame = customtkinter.CTkScrollableFrame(self.help, width=475, height=280,
                                                            fg_color=("#e6e6e6", "#222222"))
        scrollable_frame.pack()
        title = customtkinter.CTkLabel(scrollable_frame, text=translation["help"],
                                       font=customtkinter.CTkFont(size=20, weight="bold"))
        title.pack()
        notice = customtkinter.CTkLabel(scrollable_frame, text=translation["notice"],
                                        font=customtkinter.CTkFont(weight="bold", underline=True))
        notice.pack()
        searchboxText = customtkinter.CTkLabel(scrollable_frame, text=translation["searchbox_title"])
        searchboxText.pack()
        self.search_box = CustomEntry(scrollable_frame, self, placeholder_text=translation["searchbox"])
        self.search_box.pack(pady=10)
        self.class_list = tk.Listbox(scrollable_frame, width=35, bg=bg_color, fg=fg_color, font=listbox_font)
        self.class_list.pack()
        curriculumText = customtkinter.CTkLabel(scrollable_frame, text=translation["curriculums_title"])
        curriculumText.pack()
        curriculum = customtkinter.CTkOptionMenu(scrollable_frame,
                                                 values=[translation["dep"], translation["acc"],
                                                         translation["finance"], translation["management"],
                                                         translation["mark"], translation["g_biology"],
                                                         translation["h_biology"], translation["c_science"],
                                                         translation["it"], translation["s_science"],
                                                         translation["physical"], translation["elec"],
                                                         translation["equip"], translation["peda"],
                                                         translation["che"], translation["nur"],
                                                         translation["office"], translation["engi"]],
                                                 command=self.curriculums, height=30, width=150)
        curriculum.pack(pady=5)
        termsText = customtkinter.CTkLabel(scrollable_frame, text=translation["terms_title"],
                                           font=customtkinter.CTkFont(weight="bold", size=15))
        termsText.pack()
        terms = [[translation["terms_year"], translation["terms_term"]],
                 ["2019", "B91, B92, B93"],
                 ["2020", "C01, C02, C03"],
                 ["2021", "C11, C12, C13"],
                 ["2022", "C21, C22, C23"],
                 ["2023", "C31, C32, C33"],
                 [translation["semester"], translation["seasons"]]]
        termsTable = ctktable.CTkTable(scrollable_frame, column=2, row=7, values=terms)
        termsTable.pack(expand=True, fill="both", padx=20, pady=20)
        filesText = customtkinter.CTkLabel(scrollable_frame, text=translation["files_title"])
        filesText.pack()
        files = CustomButton(scrollable_frame, border_width=2, image=self.images["folder"],
                             text=translation["files_button"], anchor="w", text_color=("gray10", "#DCE4EE"),
                             command=self.change_location_event)
        files.pack(pady=5)
        disableIdleText = customtkinter.CTkLabel(scrollable_frame, text=translation["idle_title"])
        disableIdleText.pack()
        self.disableIdle = customtkinter.CTkSwitch(scrollable_frame, text=translation["idle"], onvalue="on",
                                                   offvalue="off", command=self.disable_enable_idle)
        self.disableIdle.pack()
        fixText = customtkinter.CTkLabel(scrollable_frame, text=translation["fix_title"])
        fixText.pack()
        fix = CustomButton(scrollable_frame, border_width=2, image=self.images["fix"], text=translation["fix"],
                           anchor="w", text_color=("gray10", "#DCE4EE"), command=self.fix_execution_event_handler)
        fix.pack(pady=5)
        idle = self.cursor.execute("SELECT idle FROM user_data").fetchall()
        if idle:
            if idle[0][0] == "Disabled":
                self.disableIdle.select()
        self.class_list.bind("<<ListboxSelect>>", self.show_class_code)
        self.class_list.bind("<MouseWheel>", self.disable_scroll)
        self.search_box.bind("<KeyRelease>", self.search_classes)
        self.help.bind("<Escape>", lambda event: self.help.destroy())

    # Gets the latest release of the application on GitHub
    def get_latest_release(self):
        lang = self.language_menu.get()
        if asyncio.run(self.test_connection(lang)):
            url = f"{self.GITHUB_REPO}/releases/latest"
            self.connection_error = False
            try:
                response = requests.get(url)

                if response.status_code != 200:
                    print(f"Error fetching release information: {response.status_code}")
                    return None

                release_data = response.json()
                latest_version = release_data.get("tag_name")

                if latest_version and latest_version.startswith("v"):
                    latest_version = latest_version[1:]

                return latest_version

            except requests.exceptions.RequestException as e:
                print(f"Request failed: {e}")
                return None
            except Exception as e:
                print(f"An error occurred while fetching the latest release: {e}")
                return None
        else:
            self.connection_error = True

    # Compares the current version that user is using with the latest available
    @staticmethod
    def compare_versions(latest_version, user_version):
        latest_version_parts = [int(part) for part in latest_version.split(".")]
        user_version_parts = [int(part) for part in user_version.split(".")]

        for latest, user in zip(latest_version_parts, user_version_parts):
            if latest > user:
                return False
            elif latest < user:
                return True
        return len(latest_version_parts) <= len(user_version_parts)

    # Edits the font that tera term uses to "Terminal" to mitigate the chance of the OCR mistaking words
    def edit_teraterm_ini(self, file_path):
        if TeraTermUI.is_file_in_directory("ttermpro.exe", r"C:/Program Files (x86)/teraterm"):
            backup_path = self.app_temp_dir / "TERATERM.ini.bak"
            if not os.path.exists(backup_path):
                backup_path = os.path.join(self.app_temp_dir, os.path.basename(file_path) + ".bak")
                try:
                    shutil.copyfile(file_path, backup_path)
                except FileNotFoundError:
                    print("Tera Term Probably not installed\n"
                          "or installed in a different location from the default")
            try:
                with open(file_path, "r") as file:
                    lines = file.readlines()
            except FileNotFoundError:
                return
            try:
                with open(file_path, "w") as file:
                    for line in lines:
                        if line.startswith("VTFont="):
                            current_value = line.strip().split("=")[1]
                            font_name = current_value.split(",")[0]
                            self.original_font = current_value
                            updated_value = "Lucida Console" + current_value[len(font_name):]
                            line = f"VTFont={updated_value}\n"
                        file.write(line)
                        self.can_edit = True
            # If something goes wrong, restore the backup
            except Exception as e:
                print(f"Error occurred: {e}")
                print("Restoring from backup...")
                shutil.copyfile(backup_path, file_path)
            del line, lines
            gc.collect()

    # Restores the original font option the user had
    def restore_original_font(self, file_path):
        if self.can_edit:
            backup_path = self.app_temp_dir / "TERATERM.ini.bak"
            try:
                with open(file_path, "r") as file:
                    lines = file.readlines()

                with open(file_path, "w") as file:
                    for line in lines:
                        if line.startswith("VTFont="):
                            line = f"VTFont={self.original_font}\n"
                        file.write(line)

                with open(backup_path, "r") as backup_file:
                    backup_lines = backup_file.readlines()

                backup_font = None
                backup_font_name = None
                for line in backup_lines:
                    if line.startswith("VTFont="):
                        backup_font = line.strip().split("=")[1]
                        backup_font_name = backup_font.split(",")[0]
                        break
                if backup_font_name and self.original_font.split(",")[0]:
                    if backup_font_name.lower() != self.original_font.split(",")[0].lower():
                        with open(file_path, "w") as file:
                            for line in lines:
                                if line.startswith("VTFont="):
                                    line = f"VTFont={backup_font}\n"
                                file.write(line)
            # If something goes wrong, restore the backup
            except FileNotFoundError:
                print(f"Backup file at {backup_path} not found.")
            except Exception as e:
                print(f"Error occurred: {e}")
                print("Restoring from backup...")
                try:
                    shutil.copyfile(backup_path, file_path)
                except FileNotFoundError:
                    print(f"The backup file at {backup_path} was not found.")

    # When the user performs an action to do something in tera term it hides the sidebar windows, so they don't
    # interfere with the execution on tera term
    def hide_sidebar_windows(self):
        if gw.getWindowsWithTitle("Status") or gw.getWindowsWithTitle("Estado"):
            windows_status = gw.getWindowsWithTitle("Status") + gw.getWindowsWithTitle("Estado")
            if windows_status:
                self.status_minimized = windows_status[0].isMinimized
            else:
                self.status_minimized = False
        if gw.getWindowsWithTitle("Help") or gw.getWindowsWithTitle("Ayuda"):
            windows_help = gw.getWindowsWithTitle("Help") + gw.getWindowsWithTitle("Ayuda")
            if windows_help:
                self.help_minimized = windows_help[0].isMinimized
            else:
                self.help_minimized = False
        if self.status and self.status.winfo_exists() and not self.status_minimized:
            self.status.withdraw()
        if self.help and self.help.winfo_exists() and not self.help_minimized:
            self.help.withdraw()

    # Makes the sidebar reappear again
    def show_sidebar_windows(self):
        if self.status is not None and self.status.winfo_exists() and not self.status_minimized:
            self.status.deiconify()
        if self.help is not None and self.help.winfo_exists() and not self.help_minimized:
            self.help.deiconify()
        self.set_focus_to_tkinter()

    # When the user performs an action to do something in tera term it destroys windows that might get in the way
    def destroy_windows(self):
        if self.error and self.error.winfo_exists():
            self.error.destroy()
        if self.success and self.success.winfo_exists():
            self.success.destroy()
        if self.information and self.information.winfo_exists():
            self.information.destroy()

    # checks if there is no problems with the information in the entries
    def check_format(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        entries = []
        error_msg_short = ""
        error_msg_medium = ""
        error_msg_long = ""

        # Get the choices from the entries
        for i in range(self.a_counter + 1):
            classes = self.m_classes_entry[i].get().upper().replace(" ", "")
            sections = self.m_section_entry[i].get().upper().replace(" ", "")
            semester = self.m_semester_entry[i].get().upper().replace(" ", "")
            choices = self.m_register_menu[i].get()
            entries.append((choices, classes, sections, semester))

        # Check for empty entries and format errors
        for i in range(self.a_counter + 1):
            (choices, classes, sections, semester) = entries[i]
            if not classes or not sections or not semester:
                error_msg_long = translation["missing_info_multiple"]
                break
            elif choices not in ["Register", "Registra", "Drop", "Baja"]:
                error_msg_medium = translation["drop_or_enroll"]
                break
            elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE):
                error_msg_short = translation["multiple_class_format_error"]
                break
            elif not re.fullmatch("^[A-Z]{2}1$", sections, flags=re.IGNORECASE):
                error_msg_short = translation["multiple_section_format_error"]
                break
            elif not re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE):
                error_msg_short = translation["multiple_semester_format_error"]
                break
            elif ((choices == "Register" or choices == "Registra") and
                  (classes in self.enrolled_classes_list.values() or sections in self.enrolled_classes_list)):
                error_msg_long = translation["multiple_already_enrolled"]
                break
            elif ((choices == "Drop" or choices == "Baja") and
                  (classes in self.dropped_classes_list.values() or sections in self.dropped_classes_list)):
                error_msg_long = translation["multiple_already_dropped"]
                break

        # Display error messages or proceed if no errors
        if error_msg_short:
            self.after(0, self.show_error_message, 345, 235, error_msg_short)
            if self.auto_enroll_bool:
                self.auto_enroll_bool = False
                self.auto_enroll.deselect()
            return False
        elif error_msg_medium:
            self.after(0, self.show_error_message, 355, 240, error_msg_medium)
            if self.auto_enroll_bool:
                self.auto_enroll_bool = False
                self.auto_enroll.deselect()
            return False
        elif error_msg_long:
            self.after(0, self.show_error_message, 390, 245, error_msg_long)
            if self.auto_enroll_bool:
                self.auto_enroll_bool = False
                self.auto_enroll.deselect()
            return False

        self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
        return True


class CustomButton(customtkinter.CTkButton):
    def __init__(self, master=None, command=None, **kwargs):
        super().__init__(master, cursor="hand2", **kwargs)
        self.is_pressed = False
        self.click_command = command
        self.bind("<ButtonPress-1>", self.on_button_down)
        self.bind("<ButtonRelease-1>", self.on_button_up)

    def on_button_down(self, event):
        if self.cget("state") == "disabled":
            return
        self.is_pressed = True

    def on_button_up(self, event):
        if self.cget("state") == "disabled":
            return
        width = self.winfo_width()
        height = self.winfo_height()
        if self.is_pressed and 0 <= event.x <= width and 0 <= event.y <= height:
            if self.click_command:
                self.click_command()
        self.is_pressed = False


class CustomEntry(customtkinter.CTkEntry):
    def __init__(self, master, teraterm_ui_instance, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self._undo_stack = []
        self._redo_stack = []

        self.teraterm_ui = teraterm_ui_instance
        self.bind("<FocusIn>", self.disable_slider_keys)
        self.bind("<FocusOut>", self.enable_slider_keys)

        # Bind Control-Z to undo and Control-Y to redo
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-y>", self.redo)
        # Update the undo stack every time the Entry content changes
        self.bind("<KeyRelease>", self.update_undo_stack)

    def disable_slider_keys(self, event=None):
        self.teraterm_ui.move_slider_left_enabled = False
        self.teraterm_ui.move_slider_right_enabled = False
        self.teraterm_ui.spacebar_enabled = False
        self.teraterm_ui.up_arrow_key_enabled = False
        self.teraterm_ui.down_arrow_key_enabled = False

    def enable_slider_keys(self, event=None):
        self.teraterm_ui.move_slider_left_enabled = True
        self.teraterm_ui.move_slider_right_enabled = True
        self.teraterm_ui.spacebar_enabled = True
        self.teraterm_ui.up_arrow_key_enabled = True
        self.teraterm_ui.down_arrow_key_enabled = True

    def update_undo_stack(self, event=None):
        current_text = self.get()
        if len(self._undo_stack) == 0 or (len(self._undo_stack) > 0 and current_text != self._undo_stack[-1]):
            self._undo_stack.append(current_text)
        self._redo_stack = []

    def undo(self, event=None):
        if len(self._undo_stack) > 1:
            last_text = self._undo_stack.pop()
            self._redo_stack.append(last_text)
            self.delete(0, "end")
            self.insert(0, self._undo_stack[-1])

    def redo(self, event=None):
        if len(self._redo_stack) > 0:
            redo_text = self._redo_stack.pop()
            self._undo_stack.append(redo_text)
            self.delete(0, "end")
            self.insert(0, redo_text)


class CustomComboBox(customtkinter.CTkComboBox):
    def __init__(self, master, teraterm_ui_instance, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self._undo_stack = []
        self._redo_stack = []

        self.teraterm_ui = teraterm_ui_instance
        self.bind("<FocusIn>", self.disable_slider_keys)
        self.bind("<FocusOut>", self.enable_slider_keys)

        # Bind Control-Z to undo and Control-Y to redo
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-y>", self.redo)
        # Update the undo stack every time the Entry content changes
        self.bind("<KeyRelease>", self.update_undo_stack)

    def disable_slider_keys(self, event=None):
        self.teraterm_ui.move_slider_left_enabled = False
        self.teraterm_ui.move_slider_right_enabled = False
        self.teraterm_ui.spacebar_enabled = False
        self.teraterm_ui.up_arrow_key_enabled = False
        self.teraterm_ui.down_arrow_key_enabled = False

    def enable_slider_keys(self, event=None):
        self.teraterm_ui.move_slider_left_enabled = True
        self.teraterm_ui.move_slider_right_enabled = True
        self.teraterm_ui.spacebar_enabled = True
        self.teraterm_ui.up_arrow_key_enabled = True
        self.teraterm_ui.down_arrow_key_enabled = True

    def update_undo_stack(self, event=None):
        current_text = self.get()
        if len(self._undo_stack) == 0 or (len(self._undo_stack) > 0 and current_text != self._undo_stack[-1]):
            self._undo_stack.append(current_text)
        self._redo_stack = []

    def undo(self, event=None):
        if len(self._undo_stack) > 1:
            last_text = self._undo_stack.pop()
            self._redo_stack.append(last_text)
            self.set("")
            self.set(self._undo_stack[-1])

    def redo(self, event=None):
        if len(self._redo_stack) > 0:
            redo_text = self._redo_stack.pop()
            self._undo_stack.append(redo_text)
            self.set("")
            self.set(redo_text)


class SmoothFadeToplevel(customtkinter.CTkToplevel):
    def __init__(self, fade_duration=25, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fade_duration = fade_duration
        self.alpha = 0.0
        self.fade_direction = 1  # 1 for fade-in, -1 for fade-out
        self.after_idle(self._start_fade_in)

    def _start_fade_in(self):
        self.fade_direction = 1
        self._fade()

    def _fade(self):
        self.alpha += self.fade_direction / self.fade_duration
        self.attributes("-alpha", self.alpha)
        if 0 < self.alpha < 1:
            self.after(5, self._fade)  # Adjust the update interval to make the fade-in faster
        elif self.alpha <= 0:
            self.destroy()

    def button_event(self, event=None):
        self.fade_direction = -1
        self._fade()


class ImageSlideshow:
    def __init__(self, parent, image_folder, interval=3, width=300, height=200):
        self.slideshow_frame = customtkinter.CTkFrame(parent)
        self.image_folder = image_folder
        self.interval = interval
        self.width = width
        self.height = height

        self.load_images()
        self.index = 0  # Added index to keep track of the current position in the list

        self.label = customtkinter.CTkLabel(self.slideshow_frame, text="")
        self.label.grid(row=0, column=1)

        self.arrow_left = CustomButton(self.slideshow_frame, text='<', command=self.prev_image, width=25)
        self.arrow_left.grid(row=0, column=0)

        self.arrow_right = CustomButton(self.slideshow_frame, text='>', command=self.next_image, width=25)
        self.arrow_right.grid(row=0, column=2)

        self.after_id = self.slideshow_frame.after(1, lambda: None)
        self.is_running = True
        self.show_image()

    def grid(self, **kwargs):
        self.slideshow_frame.grid(**kwargs)

    def grid_forget(self):
        self.slideshow_frame.grid_forget()

    def load_images(self):
        image_files = [f for f in os.listdir(self.image_folder) if f.endswith(('png', 'gif', 'jpg', 'jpeg'))]
        self.images = [
            customtkinter.CTkImage(
                light_image=Image.open(os.path.join(self.image_folder, f)).resize((self.width * 2, self.height * 2)),
                size=(self.width, self.height))
            for f in sorted(image_files)
        ]

    def show_image(self):
        self.slideshow_frame.after_cancel(self.after_id)  # Cancel the existing timer
        self.label.configure(image=self.images[self.index])  # Show the current image
        self.reset_timer()  # Reset the timer after showing the image

    def cycle_images(self):
        self.index = (self.index + 1) % len(self.images)  # Advance to the next image in the list
        self.show_image()  # Show the new image and reset the timer

    def prev_image(self):
        self.index = (self.index - 1) % len(self.images)  # Decrease index and wrap around if needed
        self.show_image()  # Show the new image and reset the timer

    def next_image(self):
        self.index = (self.index + 1) % len(self.images)  # Increase index and wrap around if needed
        self.show_image()  # Show the new image and reset the timer

    def pause_cycle(self):
        self.slideshow_frame.after_cancel(self.after_id)  # Cancel the existing timer
        self.is_running = False  # Set the flag to indicate that the slideshow is not running

    def resume_cycle(self):
        if not self.is_running:  # Only resume if it is not already running
            self.is_running = True  # Set the flag to indicate that the slideshow is running
            self.reset_timer()  # Reset the timer to resume cycling of images

    def reset_timer(self):
        if self.is_running:  # Only reset the timer if the slideshow is running
            self.slideshow_frame.after_cancel(self.after_id)  # Cancel the existing timer if any
            # Set a new timer to cycle images
            self.after_id = self.slideshow_frame.after(self.interval * 1000, self.cycle_images)


DWMWA_EXTENDED_FRAME_BOUNDS = 9


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG)]


def get_window_rect(hwnd):
    rect = RECT()
    DwmGetWindowAttribute = ctypes.windll.dwmapi.DwmGetWindowAttribute
    DwmGetWindowAttribute.restype = wintypes.LONG
    DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.POINTER(RECT), wintypes.DWORD]
    DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def main():
    appdata_folder = os.path.join(os.getenv("APPDATA"), "TeraTermUI")
    lock_file = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), "app_lock.lock")
    lock_file_appdata = os.path.join(appdata_folder, "app_lock.lock")
    file_lock = FileLock(lock_file, timeout=10)

    try:
        with file_lock.acquire(poll_interval=0.1):
            app = TeraTermUI()
            app.after(1, lambda: app.iconbitmap("images/tera-term.ico"))
            app.mainloop()
    except Timeout:
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
