# PROGRAM NAME - Tera Term UI

# PROGRAMMER - Armando Del Valle Tejada

# DESCRIPTION - Controls The application called Tera Term through a GUI interface to make the process of
# enrolling classes for the university of Puerto Rico at Bayamon easier

# DATE - Started 1/1/23, Current Build v0.9.0 - 1/11/24

# BUGS / ISSUES - The implementation of pytesseract could be improved, it sometimes fails to read the screen properly,
# depends a lot on the user's system and takes a bit time to process.
# Application sometimes feels sluggish/slow to use, could use some efficiency/performance improvements.
# The grid of the UI interface and placement of widgets could use some work.
# Option Menu of all tera terms screens requires more work

# FUTURE PLANS: Display more information in the app itself, which will make the app less reliant on Tera Term,
# refactor the architecture of the codebase, split things into multiple files, right now everything is in 1 file
# and with 8000 lines of codes, it definitely makes things harder to work with

import asyncio
import atexit
import ctypes
import customtkinter
import functools
import gc
import inspect
import json
import logging
import os
import psutil
import py7zr
import pygetwindow as gw
import pyperclip
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
import warnings
import webbrowser
import win32gui
import winsound
from collections import deque, defaultdict
from contextlib import closing
from Cryptodome.Hash import HMAC, SHA256
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from Cryptodome.Random import get_random_bytes
from CTkTable import CTkTable
from CTkToolTip import CTkToolTip
from CTkMessagebox import CTkMessagebox
from ctypes import wintypes
from datetime import datetime, timedelta
from filelock import FileLock, Timeout
from pathlib import Path
from pywinauto.application import Application, AppStartError
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.keyboard import send_keys
from pywinauto import timings
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image

# from memory_profiler import profile

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")
warnings.filterwarnings("ignore", message="32-bit application should be automated using 32-bit Python")


def measure_time(threshold):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            result = func(self, *args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"Elapsed time: {elapsed_time:.2f} seconds")
            if elapsed_time > threshold or TeraTermUI.checkIfProcessRunning("EpicGamesLauncher"):
                self.after(350, self.notice_user)
            return result

        return wrapper

    return decorator


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
        self.icon_path = "images/tera-term.ico"
        self.iconbitmap(self.icon_path)
        self.bind("<Button-3>", lambda event: self.focus_set())

        # creates a thread separate from the main application for check_idle and to monitor cpu usage
        self.last_activity = time.time()
        self.is_idle_thread_running = False
        self.stop_check_idle = threading.Event()
        self.is_check_process_thread_running = False
        self.stop_is_check_process = threading.Event()
        self.lock_thread = threading.Lock()

        # self.cpu_load_history = deque(maxlen=60)
        # self.stop_monitor = threading.Event()
        # self.monitor_thread = threading.Thread(target=self.cpu_monitor)
        # self.monitor_thread.start()

        # GitHub's information for feedback
        self.SERVICE_ACCOUNT_FILE = "feedback.zip"
        self.SPREADSHEET_ID = "1ffJLgp8p-goOlxC10OFEu0JefBgQDsgEo_suis4k0Pw"
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
        self.uprbay_window = None
        self.uprb = None
        self.uprb_32 = None
        self.server_status = None
        self.timer_window = None
        self.timer_label = None
        self.message_label = None
        self.cancel_button = None
        self.running_countdown = None
        self.progress_bar = None
        self.check_idle_thread = None
        self.check_process_thread = None
        self.idle_num_check = None
        self.idle_warning = None
        self.feedback_text = None
        self.feedback_send = None
        self.search_box = None
        self.class_list = None
        self.disable_idle = None
        self.disable_audio = None
        self.status_minimized = None
        self.help_minimized = None
        self.checkbox_state = None
        self.get_class_for_pdf = None
        self.get_semester_for_pdf = None
        self.show_all_sections = None
        self.download_pdf = None
        self.table_count_tooltip = None
        self.previous_button_tooltip = None
        self.next_button_tooltip = None
        self.remove_button_tooltip = None
        self.download_pdf_tooltip = None
        self.tooltip = None
        self.exit = None
        self.is_exit_dialog_open = False
        self.dialog = None
        self.dialog_input = None
        self.prev_dialog_input = None

        self.image_cache = {}

        # path for tesseract application
        self.zip_path = os.path.join(os.path.dirname(__file__), "Tesseract-OCR.7z")
        self.app_temp_dir = Path(tempfile.gettempdir()) / "TeraTermUI"
        self.app_temp_dir.mkdir(parents=True, exist_ok=True)

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        self.app_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.app_frame.grid(row=0, column=0, rowspan=5, columnspan=5, padx=(0, 0), pady=(0, 0), sticky="nsew")
        self.app_frame.bind("<Button-1>", lambda event: self.focus_set())

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="Tera Term UI",
                                                 font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.logo_label.bind("<Button-1>", lambda event: self.focus_set())
        self.status_button = CustomButton(self.sidebar_frame, text="     Status", image=self.get_image("status"),
                                          command=self.status_button_event, anchor="w")
        self.status_tooltip = CTkToolTip(self.status_button, message="See the status and the state\n"
                                                                     " of the application", bg_color="#1E90FF")
        self.status_button.grid(row=1, column=0, padx=20, pady=10)
        self.help_button = CustomButton(self.sidebar_frame, text="       Help", image=self.get_image("help"),
                                        command=self.help_button_event, anchor="w")
        self.help_tooltip = CTkToolTip(self.help_button, message="Contains useful utilities for the user",
                                       bg_color="#1E90FF")
        self.help_button.grid(row=2, column=0, padx=20, pady=10)
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="Language, Appearance and \n\n "
                                                                             "UI Scaling", anchor="w")
        self.scaling_label_tooltip = CTkToolTip(self.scaling_label, message="Change the language, the theme\nand"
                                                                            " the scaling of the widgets of the "
                                                                            "application\nthese settings are saved so"
                                                                            " next time\nyou log-in you wont have to"
                                                                            " reconfigured them", bg_color="#1E90FF")
        self.scaling_label.bind("<Button-1>", lambda event: self.focus_set())
        self.scaling_label.grid(row=5, column=0, padx=20, pady=(10, 10))
        self.language_menu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["English", "Español"],
                                                         command=self.change_language_event, corner_radius=15)
        self.language_menu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.language_menu_tooltip = CTkToolTip(self.language_menu, message="The language can only\n"
                                                                            "be changed in the main menu",
                                                bg_color="#A9A9A9")
        self.language_menu_tooltip.hide()
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, corner_radius=15,
                                                                       values=["Dark", "Light", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.set("System")
        self.appearance_mode_optionemenu.grid(row=7, column=0, padx=20, pady=(10, 10))
        self.scaling_slider = customtkinter.CTkSlider(self.sidebar_frame, from_=97, to=103, number_of_steps=2,
                                                      width=150, height=20, command=self.change_scaling_event)
        self.scaling_slider.set(100)
        self.scaling_tooltip = CTkToolTip(self.scaling_slider, message=str(self.scaling_slider.get()) + "%",
                                          bg_color="#1E90FF")
        self.current_scaling = self.scaling_slider.get()
        self.scaling_slider.grid(row=8, column=0, padx=20, pady=(10, 20))
        self.bind("<Left>", self.move_slider_left)
        self.bind("<Right>", self.move_slider_right)

        # create main entry
        self.home_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.home_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.home_frame.grid(row=0, column=1, rowspan=5, columnspan=5, padx=(0, 0), pady=(0, 0))
        self.introduction = customtkinter.CTkLabel(self.home_frame, text="UPRB Enrollment Process",
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        self.introduction.bind("<Button-1>", lambda event: self.focus_set())
        self.introduction.grid(row=0, column=1, columnspan=2, padx=(20, 0), pady=(20, 0))
        self.host = customtkinter.CTkLabel(self.home_frame, text="Host")
        self.host.grid(row=2, column=1, padx=(0, 170), pady=(15, 15))
        self.host_entry = CustomEntry(self.home_frame, self, self.language_menu.get(),
                                      placeholder_text="myhost.example.edu")
        self.host_entry.grid(row=2, column=1, padx=(20, 0), pady=(15, 15))
        self.host_tooltip = CTkToolTip(self.host_entry, message="Enter the name of the server\n of the university",
                                       bg_color="#1E90FF")
        self.log_in = CustomButton(self.home_frame, border_width=2, text="Log-In", text_color=("gray10", "#DCE4EE"),
                                   command=self.login_event_handler)
        self.log_in.grid(row=3, column=1, padx=(20, 0), pady=(15, 15))
        self.log_in.configure(state="disabled")
        self.slideshow_frame = ImageSlideshow(self.home_frame, "slideshow", interval=5, width=300,
                                              height=150)
        self.slideshow_frame.grid(row=1, column=1, padx=(20, 0), pady=(140, 0))
        self.intro_box = CustomTextBox(self.home_frame, self, read_only=True, lang=self.language_menu.get(),
                                       height=120, width=400)
        self.intro_box.insert("0.0", "Welcome to the Tera Term UI Application!\n\n" +
                              "The purpose of this application"
                              " is to facilitate the process enrolling and dropping classes, "
                              "since Tera Term uses Terminal interface, "
                              "it's hard for new users to use and learn how to navigate and do things in "
                              "Tera Term. "
                              "This application has a very nice and clean user interface that most users are "
                              "used to.\n\n" +
                              "There's a few things you should know before using this tool: \n\n" +
                              "The application is very early in development, which means it still got things to work, "
                              "fix and implement. "
                              "Right now, the applications lets you do the essentials like enrolling/dropping classes, "
                              "searching for the sections of the classes and modifying currently enrolled classes. "
                              "Other functionality will/might be implemented later down the road, "
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

        # Authentication Screen
        self.init_auth = False
        self.in_auth_frame = False
        self.authentication_frame = None
        self.a_buttons_frame = None
        self.title_login = None
        self.uprb_image = None
        self.uprb_image_grid = None
        self.disclaimer = None
        self.username = None
        self.username_entry = None
        self.username_tooltip = None
        self.auth = None
        self.back = None
        self.back_tooltip = None
        self.skip_auth = False
        self.ask_skip_auth = False

        # Student Information
        self.init_student = False
        self.in_student_frame = False
        self.student_frame = None
        self.s_buttons_frame = None
        self.title_student = None
        self.lock = None
        self.lock_grid = None
        self.student_id = None
        self.student_id_entry = None
        self.student_id_tooltip = None
        self.code = None
        self.code_entry = None
        self.code_tooltip = None
        self.show = None
        self.system = None
        self.back_student = None
        self.back_student_tooltip = None

        # Classes
        self.init_class = False
        self.tabview = None
        self.t_buttons_frame = None
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
        self.title_menu = None
        self.explanation_menu = None
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
        self.multiple_frame = None
        self.m_button_frame = None
        self.save_frame = None
        self.auto_frame = None
        self.init_multiple = False
        self.title_multiple = None
        self.m_class = None
        self.m_section = None
        self.m_semester = None
        self.m_choice = None
        self.m_num_class = None
        self.m_classes_entry = None
        self.m_section_entry = None
        self.m_semester_entry = None
        self.m_register_menu = None
        self.placeholder_texts_classes = None
        self.placeholder_texts_sections = None
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

        # My Classes
        self.enrolled_rows = None
        self.enrolled_classes_data = None
        self.my_classes_frame = None
        self.title_my_classes = None
        self.total_credits_label = None
        self.submit_my_classes = None
        self.modify_classes_frame = None
        self.back_my_classes = None
        self.enrolled_classes_table = None
        self.change_section_entries = None
        self.mod_selection_list = None
        self.mod_selection = None
        self.change_section_entry = None
        self.modify_classes_title = None

        # Status Window
        self.status_frame = None
        self.status_title = None
        self.version = None
        self.feedback_text = None
        self.feedback_send = None
        self.check_update_text = None
        self.check_update_btn = None
        self.website = None
        self.website_link = None
        self.notaso = None
        self.notaso_link = None
        self.faq = None
        self.faq_text = None
        self.qa_table = None

        # Help Window
        self.help_frame = None
        self.help_title = None
        self.notice = None
        self.searchbox_text = None
        self.search_box = None
        self.class_list = None
        self.curriculum_text = None
        self.curriculum = None
        self.terms_text = None
        self.terms = None
        self.terms_table = None
        self.keybinds_text = None
        self.keybinds = None
        self.keybinds_table = None
        self.skip_auth_text = None
        self.skip_auth_switch = None
        self.files_text = None
        self.files = None
        self.disable_idle_text = None
        self.disable_idle = None
        self.disable_audio_text = None
        self.disable_audio_val = None
        self.fix_text = None
        self.fix = None

        # Top level window management, flags and counters
        self.DEFAULT_SEMESTER = "C41"
        self.ignore = True
        self.error_occurred = False
        self.can_edit = False
        self.enrolled_classes_list = None
        self.dropped_classes_list = None
        self.class_table_pairs = []
        self.current_table_index = -1
        self.table_tooltips = {}
        self.table_count = None
        self.table = None
        self.current_class = None
        self.previous_button = None
        self.next_button = None
        self.remove_button = None
        self.renamed_tabs = None
        self.disable_feedback = False
        self.auto_enroll_bool = False
        self.countdown_running = False
        self.enrollment_error_check = False
        self.modify_error_check = False
        self.download = False
        self.status = None
        self.help = None
        self.error = None
        self.success = None
        self.loading_screen = None
        self.information = None
        self.run_fix = False
        self.teraterm_not_found = False
        self.tesseract_unzipped = False
        self.in_multiple_screen = False
        self.started_auto_enroll = False
        self.error_auto_enroll = False
        self.connection_error = False
        self.check_update = False
        self.disable_audio = False
        self.focus_or_not = False
        self.changed_location = False
        self.auto_search = False
        self.updating_app = False
        self.main_menu = True
        self.not_rebind = False
        self.a_counter = 0
        self.m_counter = 0
        self.e_counter = 0
        self.search_function_counter = 0
        self.last_switch_time = 0
        timings.Timings.fast()
        SPANISH = 0x0A
        language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        # default location of Tera Term
        self.location = "C:/Program Files (x86)/teraterm/ttermpro.exe"
        self.teraterm_file = "C:/Program Files (x86)/teraterm/TERATERM.ini"
        self.teraterm_directory = "C:/Program Files (x86)/teraterm"
        self.original_font = None
        # Storing translations for languages in cache to reuse
        self.translations_cache = {}
        # performs some operations in a separate thread when application starts up
        self.boot_up(self.teraterm_file)
        # Database
        appdata_path = os.environ.get("PROGRAMDATA")
        self.db_path = os.path.join(appdata_path, "TeraTermUI/database.db")
        self.ath = os.path.join(appdata_path, "TeraTermUI/feedback.zip")
        self.logs = os.path.join(appdata_path, "TeraTermUI/logs.txt")
        self.mode = "Portable"
        try:
            db_path = "database.db"
            if not os.path.isfile(db_path):
                raise Exception("Database file not found.")
            en_path = "translations/english.json"
            es_path = "translations/spanish.json"
            if not os.path.isfile(en_path) or not os.path.isfile(es_path):
                raise Exception("Language file not found.")
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.cursor = self.connection.cursor()
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.bind("<Control-space>", lambda event: self.focus_set())
            self.bind("<Escape>", lambda event: self.on_closing())
            self.bind("<Alt-F4>", lambda event: self.direct_close())
            user_data_fields = ["location", "config", "directory", "host", "language",
                                "appearance", "scaling", "welcome", "audio", "skip_auth"]
            results = {}
            for field in user_data_fields:
                query_user = f"SELECT {field} FROM user_data"
                result = self.cursor.execute(query_user).fetchone()
                results[field] = result[0] if result else None
            if results["host"]:
                self.host_entry.insert(0, results["host"])
            if results["location"]:
                if results["location"] != self.location:
                    self.location = results["location"]
            if results["directory"] and results["config"]:
                if results["directory"] != self.teraterm_directory and results["config"] != self.teraterm_file:
                    self.teraterm_file = results["config"]
                    self.teraterm_directory = results["directory"]
                    self.edit_teraterm_ini(self.teraterm_file)
                    self.can_edit = True
            if not results["language"] and language_id & 0xFF == SPANISH:
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
                if float(results["scaling"]) != 100.0:
                    x = (screen_width - width * scaling_factor) / 2
                    y = (screen_height - height * scaling_factor) / 2
                    self.geometry(f"{width}x{height}+{int(x) + 130}+{int(y + 50)}")
                    self.scaling_slider.set(float(results["scaling"]))
                    self.change_scaling_event(float(results["scaling"]))
                    self.current_scaling = self.scaling_slider.get()
            if results["audio"] == "Disabled":
                self.disable_audio = True
            if results["skip_auth"] == "Yes":
                self.skip_auth = True
            elif not results["skip_auth"]:
                self.ask_skip_auth = True
            if not results["welcome"]:
                self.help_button.configure(state="disabled")
                self.status_button.configure(state="disabled")
                self.intro_box.stop_autoscroll(event=None)

                # Pop up message that appears only the first time the user uses the application
                def show_message_box():
                    translation = self.load_language(self.language_menu.get())
                    if not self.disable_audio:
                        winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["welcome_title"],
                                  message=translation["welcome_message"], button_width=380)
                    self.slideshow_frame.go_to_first_image()
                    self.intro_box.restart_autoscroll()
                    self.status_button.configure(state="normal")
                    self.help_button.configure(state="normal")
                    self.log_in.configure(state="normal")
                    self.bind("<Return>", lambda event: self.login_event_handler())
                    row_exists_in_welcome = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
                    if not row_exists_in_welcome:
                        self.cursor.execute("INSERT INTO user_data (welcome) VALUES (?)", ("Checked",))
                    else:
                        self.cursor.execute("UPDATE user_data SET welcome=?", ("Checked",))
                    del row_exists_in_welcome, translation

                self.after(3500, show_message_box)
            else:
                # Binding events
                self.log_in.configure(state="normal")
                self.bind("<Return>", lambda event: self.login_event_handler())
                # Check for update for the application
                current_date = datetime.today().strftime("%Y-%m-%d")
                date_record = self.cursor.execute("SELECT update_date FROM user_data").fetchone()
                if date_record is None or date_record[0] != current_date:
                    try:
                        self.check_update = True
                        latest_version = self.get_latest_release()
                        if latest_version is None:
                            print("No latest release found. Starting app with the current version.")
                            latest_version = self.USER_APP_VERSION
                        if not TeraTermUI.compare_versions(latest_version, self.USER_APP_VERSION):
                            self.after(1000, self.update_app)
                        row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
                        if not row_exists:
                            self.cursor.execute("INSERT INTO user_data (update_date) VALUES (?)",
                                                (current_date,))
                        else:
                            self.cursor.execute("UPDATE user_data SET update_date=?", (current_date,))
                        self.connection.commit()
                    except requests.exceptions.RequestException as err:
                        print(f"Error occurred while fetching latest release information: {err}")
                        print("Please check your internet connection and try again.")
                    del latest_version, row_exists
                del current_date, date_record
        except Exception as e:
            db_path = "database.db"
            en_path = "translations/english.json"
            es_path = "translations/spanish.json"
            print(f"An unexpected error occurred: {e}")
            self.log_error(e)
            if not os.path.isfile(db_path):
                if language_id & 0xFF == SPANISH:
                    messagebox.showerror("Error", "¡Error Fatal! Problema en inicializar la base de"
                                                  " datos.\nEs posible que necesite reinstalar la aplicación")
                else:
                    messagebox.showerror("Error", "Fatal Error! Failed to initialize database.\n"
                                                  "Might need to reinstall the application")
            if not os.path.isfile(en_path) or not os.path.isfile(es_path):
                if language_id & 0xFF == SPANISH:
                    messagebox.showerror("Error", "¡Error Fatal! Problema en inicializar "
                                                  "los archivos de lenguajes.\nEs posible que necesite reinstalar"
                                                  " la aplicación")
                else:
                    messagebox.showerror("Error", "Fatal Error! Failed to initialize language files.\n"
                                                  "Might need to reinstall the application")
            sys.exit(1)

        atexit.register(self.cleanup_temp)
        atexit.register(self.restore_original_font, self.teraterm_file)
        self.after(0, self.unload_image("uprb"))
        self.after(0, self.unload_image("status"))
        self.after(0, self.unload_image("help"))
        self.after(0, self.set_focus_to_tkinter)
        del user_data_fields, results, SPANISH, language_id, scaling_factor, screen_width, screen_height, width, \
            height, x, y, db_path, en_path, es_path
        gc.collect()

    # function that when the user tries to close the application a confirm dialog opens up
    def on_closing(self):
        if hasattr(self, "is_exit_dialog_open") and self.is_exit_dialog_open or \
                (self.loading_screen is not None and self.loading_screen.winfo_exists()):
            return
        self.is_exit_dialog_open = True
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.exit = CTkMessagebox(master=self, title=translation["exit"], message=translation["exit_message"],
                                  icon="question", option_1=translation["close_tera_term"],
                                  option_2=translation["option_2"], option_3=translation["option_3"],
                                  icon_size=(65, 65), button_color=("#c30101", "#c30101", "#145DA0", "use_default"),
                                  option_1_type="checkbox", hover_color=("darkred", "darkred", "use_default"))
        on_exit = self.cursor.execute("SELECT exit FROM user_data").fetchone()
        if on_exit and on_exit[0] is not None and on_exit[0] == "1":
            self.exit.check_checkbox()
        response, self.checkbox_state = self.exit.get()
        self.is_exit_dialog_open = False
        if response == "Yes" or response == "Sí":
            if hasattr(self, "boot_up_thread") and self.boot_up_thread.is_alive():
                self.boot_up_thread.join()
            if hasattr(self, "check_idle_thread") and self.check_idle_thread is not None \
                    and self.check_idle_thread.is_alive():
                self.stop_check_idle.set()
            if hasattr(self, "check_process_thread") and self.check_process_thread is not None \
                    and self.check_process_thread.is_alive():
                self.stop_is_check_process.set()
            self.save_user_data()
            self.destroy()
            if self.checkbox_state:
                if TeraTermUI.checkIfProcessRunning("ttermpro"):
                    if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                        try:
                            self.uprb.kill(soft=True)
                        except Exception as e:
                            print("An error occurred: ", e)
                            try:
                                subprocess.run(["taskkill", "/f", "/im", "ttermpro.exe"],
                                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            except subprocess.CalledProcessError:
                                print("Could not terminate ttermpro.exe.")

                    elif TeraTermUI.window_exists("Tera Term - [disconnected] VT"):
                        try:
                            subprocess.run(["taskkill", "/f", "/im", "ttermpro.exe"],
                                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except subprocess.CalledProcessError:
                            print("Could not terminate ttermpro.exe.")
            sys.exit(0)

    def direct_close(self):
        if hasattr(self, "boot_up_thread") and self.boot_up_thread.is_alive():
            self.boot_up_thread.join()
        if hasattr(self, "check_idle_thread") and self.check_idle_thread is not None \
                and self.check_idle_thread.is_alive():
            self.stop_check_idle.set()
        if hasattr(self, "check_process_thread") and self.check_process_thread is not None \
                and self.check_process_thread.is_alive():
            self.stop_is_check_process.set()
        self.save_user_data(include_exit=False)
        self.destroy()
        sys.exit(0)

    def forceful_end_app(self):
        self.destroy()
        sys.exit(1)

    def log_error(self, e):
        try:
            # Get the current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Get the current call stack and extract the function or module name
            stack = inspect.stack()
            _, filename, _, function, _, _ = stack[1]
            function_info = f"{filename}:{function}"
            # Create a formatted error message with the app version and timestamp
            error_message = (f"[ERROR] [{self.mode}] [{self.USER_APP_VERSION}] [{timestamp}]"
                             f" [{function_info}] {str(e)}")
            # Calculate the length of the error message
            error_length = len(error_message)
            # Create a separator based on the length of the error message
            separator = "-" * error_length + "\n"
            if self.mode == "Installation":
                appdata_path = os.environ.get("PROGRAMDATA")
                tera_term_ui_path = os.path.join(appdata_path, "TeraTermUI")
                if not os.path.isdir(tera_term_ui_path):
                    raise Exception("Program Data directory not found.")
            # Write the formatted error message and separator to the log file
            with open("logs.txt", "a") as file:
                file.write(error_message + "\n" + separator)
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")

    def student_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.student_event, args=(task_done,))
        event_thread.start()

    # Enrolling/Searching classes Frame
    def student_event(self, task_done):
        try:
            self.automation_preparations()
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
                    student_id = self.student_id_entry.get().replace(" ", "").replace("-", "")
                    code = self.code_entry.get().replace(" ", "")
                    student_id_enc = aes_encrypt_then_mac(str(student_id), aes_key, iv, mac_key)
                    code_enc = aes_encrypt_then_mac(str(code), aes_key, iv, mac_key)
                    if ((re.match(r"^(?!000|666|9\d{2})\d{3}(?!00)\d{2}(?!0000)\d{4}$", student_id) or
                         re.match(r"^\d{9}$", student_id)) and code.isdigit() and len(code) == 4):
                        secure_delete(student_id)
                        secure_delete(code)
                        term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                        if term_window.isMinimized:
                            term_window.restore()
                        self.wait_for_window()
                        TeraTermUI.unfocus_tkinter()
                        send_keys("{TAB}")
                        self.uprb.UprbayTeraTermVt.type_keys(
                            aes_decrypt_and_verify_mac(student_id_enc, aes_key, iv, mac_key))
                        self.uprb.UprbayTeraTermVt.type_keys(
                            aes_decrypt_and_verify_mac(code_enc, aes_key, iv, mac_key))
                        send_keys("{ENTER}")
                        screenshot_thread = threading.Thread(target=self.capture_screenshot)
                        screenshot_thread.start()
                        screenshot_thread.join()
                        text_output = self.capture_screenshot()
                        if "SIGN-IN" in text_output:
                            self.reset_activity_timer(None)
                            self.start_check_idle_thread()
                            self.start_check_process_thread()
                            self.after(0, self.initialization_class)
                            self.after(100, self.student_info_frame)
                            self.run_fix = True
                            if self.help is not None and self.help.winfo_exists():
                                self.fix.configure(state="normal")
                            self.in_student_frame = False
                            secure_delete(student_id_enc)
                            secure_delete(code_enc)
                            secure_delete(aes_key)
                            secure_delete(mac_key)
                            secure_delete(iv)
                            del student_id, code, student_id_enc, code_enc, aes_key, mac_key
                            gc.collect()
                            self.switch_tab()
                        else:
                            self.bind("<Return>", lambda event: self.student_event_handler())
                            if "ON FILE" in text_output:
                                send_keys("{TAB 3}")
                            if "PIN NUMBER" in text_output:
                                send_keys("{TAB 2}")

                            self.after(100, self.show_error_message, 300, 215, translation["error_student_id"])
                    else:
                        self.bind("<Return>", lambda event: self.student_event_handler())
                        self.after(100, self.show_error_message, 300, 215, translation["error_student_id"])
                else:
                    self.bind("<Return>", lambda event: self.student_event_handler())
                    self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            else:
                self.bind("<Return>", lambda event: self.student_event_handler())
        except Exception as e:
            print("An error occurred: ", e)
            self.error_occurred = True
            self.log_error(e)
        finally:
            task_done.set()
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            self.after(100, self.set_focus_to_tkinter)
            self.after(100, self.show_sidebar_windows)
            if self.error_occurred:
                def error_automation():
                    self.destroy_windows()
                    if not self.disable_audio:
                        winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["automation_error_title"],
                                  message=translation["automation_error"],
                                  icon="warning", button_width=380)
                    self.bind("<Return>", lambda event: self.student_event_handler())
                    self.error_occurred = False

                self.after(0, error_automation)
            ctypes.windll.user32.BlockInput(False)

    def student_info_frame(self):
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
        self.e_classes.grid(row=1, column=1, padx=(0, 188), pady=(0, 0))
        self.e_classes_entry.grid(row=1, column=1, padx=(0, 0), pady=(0, 0))
        if lang == "English":
            self.e_section.grid(row=2, column=1, padx=(0, 199), pady=(20, 0))
        elif lang == "Español":
            self.e_section.grid(row=2, column=1, padx=(0, 202), pady=(20, 0))
        self.e_section_entry.grid(row=2, column=1, padx=(0, 0), pady=(20, 0))
        self.e_semester.grid(row=3, column=1, padx=(0, 211), pady=(20, 0))
        self.e_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0))
        self.register.grid(row=4, column=1, padx=(0, 60), pady=(15, 0))
        self.drop.grid(row=4, column=1, padx=(140, 0), pady=(15, 0))
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
        self.title_menu.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
        self.explanation_menu.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        if lang == "English":
            self.menu.grid(row=2, column=1, padx=(0, 184), pady=(10, 0))
        elif lang == "Español":
            self.menu.grid(row=2, column=1, padx=(0, 194), pady=(10, 0))
        self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0))
        self.menu_semester.grid(row=3, column=1, padx=(0, 211), pady=(20, 0))
        self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0))
        self.menu_submit.grid(row=5, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
        self.back_classes.grid(row=4, column=0, padx=(0, 10), pady=(0, 0), sticky="w")
        self.show_classes.grid(row=4, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        self.multiple.grid(row=4, column=2, padx=(10, 0), pady=(0, 0), sticky="e")
        self.bind("<Control-Tab>", lambda event: self.tab_switcher())
        if self.renamed_tabs is not None:
            if self.renamed_tabs == self.enroll_tab:
                self.tabview.set(self.enroll_tab)
            elif self.renamed_tabs == self.search_tab:
                self.tabview.set(self.search_tab)
            elif self.renamed_tabs == self.other_tab:
                self.tabview.set(self.other_tab)
            self.renamed_tabs = None
            self.after(0, self.switch_tab)
        self.destroy_student()

    def load_saved_classes(self):
        lang = self.language_menu.get()
        reverse_language_mapping = {
            "English": {
                "Registra": "Register",
                "Baja": "Drop"
            },
            "Español": {
                "Register": "Registra",
                "Drop": "Baja"
            }
        }
        save = self.cursor.execute("SELECT class, section, semester, action FROM save_classes"
                                   " WHERE class IS NOT NULL").fetchall()
        save_check = self.cursor.execute('SELECT "check" FROM save_classes').fetchone()

        if save_check and save_check[0] is not None:
            if save_check[0] == "Yes":
                self.save_data.select()

        if save:
            num_rows = len(save)
            for index, row in enumerate(save, start=1):
                class_value = row[0]
                section_value = row[1]
                semester_value = row[2]
                register_value = row[3]

                is_english = register_value in reverse_language_mapping["English"].values()
                is_spanish = register_value in reverse_language_mapping["Español"].values()

                if lang == "English" and is_spanish:
                    display_register_value = reverse_language_mapping["English"].get(register_value, "UNKNOWN")
                elif lang == "Español" and is_english:
                    display_register_value = reverse_language_mapping["Español"].get(register_value, "UNKNOWN")
                else:
                    display_register_value = register_value

                if index <= num_rows:
                    self.m_classes_entry[index - 1].delete(0, "end")
                    self.m_classes_entry[index - 1].insert(0, class_value)
                    self.m_section_entry[index - 1].delete(0, "end")
                    self.m_section_entry[index - 1].insert(0, section_value)
                    if index == 1:
                        self.m_semester_entry[index - 1].set(semester_value)
                    self.m_register_menu[index - 1].set(display_register_value)
                else:
                    break

    def submit_event_handler(self):
        msg = None
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        choice = self.radio_var.get()
        self.focus_set()
        if lang == "English":
            if choice == "register":
                msg = CTkMessagebox(master=self, title="Submit",
                                    message="Are you sure you are ready " + translation["register"].lower() +
                                            " this class?\n\nWARNING: Make sure the information is correct",
                                    icon="images/submit.png",
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "use_default", "use_default"))
            elif choice == "drop":
                msg = CTkMessagebox(master=self, title="Submit",
                                    message="Are you sure you are ready " + translation[
                                        "drop"].lower() + " this class?\n\nWARNING: Make sure the information "
                                                          "is correct",
                                    icon="images/submit.png",
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "use_default", "use_default"))
        elif lang == "Español":
            if choice == "register":
                msg = CTkMessagebox(master=self, title="Someter",
                                    message="¿Estás preparado para " + translation["register"].lower() + "r esta clase?"
                                            "\n\nWARNING: Asegúrese de que la información está correcta",
                                    icon="images/submit.png",
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "use_default", "use_default"),
                                    hover_color=("darkred", "use_default", "use_default"))
            elif choice == "drop":
                msg = CTkMessagebox(master=self, title="Someter",
                                    message="¿Estás preparado para darle de " + translation["drop"].lower() +
                                            " a esta clase?\n\nWARNING: Asegúrese de que la información está correcta",
                                    icon="images/submit.png",
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "use_default", "use_default"))
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
                self.automation_preparations()
                choice = self.radio_var.get()
                classes = self.e_classes_entry.get().upper().replace(" ", "").replace("-", "")
                section = self.e_section_entry.get().upper().replace(" ", "")
                semester = self.e_semester_entry.get().upper().replace(" ", "")
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if (choice == "register" and classes not in
                            self.enrolled_classes_list.values() and section not in self.enrolled_classes_list) \
                                or (choice == "drop" and classes
                                    not in self.dropped_classes_list.values() and section
                                    not in self.dropped_classes_list):
                            if (re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE)
                                    and re.fullmatch("^[A-Z]{2}[A-Z0-9]$", section, flags=re.IGNORECASE)
                                    and re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE)):
                                term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                                if term_window.isMinimized:
                                    term_window.restore()
                                self.wait_for_window()
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
                                        "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" \
                                        not in text_output and "ENTER REGISTRATION" in text_output and \
                                        count_enroll != 15:
                                    self.e_counter = 0
                                    send_keys("{TAB 3}")
                                    for i in range(count_enroll, 0, -1):
                                        send_keys("{TAB 2}")
                                    if choice == "register":
                                        self.uprb.UprbayTeraTermVt.type_keys("R")
                                    elif choice == "drop":
                                        self.uprb.UprbayTeraTermVt.type_keys("D")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes)
                                    self.uprb.UprbayTeraTermVt.type_keys(section)
                                    send_keys("{ENTER}")
                                    time.sleep(1.5)
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
                                        self.e_classes_entry.configure(state="normal")
                                        self.e_section_entry.configure(state="normal")
                                        self.e_classes_entry.delete(0, "end")
                                        self.e_section_entry.delete(0, "end")
                                        self.e_classes_entry.configure(state="disabled")
                                        self.e_section_entry.configure(state="disabled")
                                        for i in range(count_dropped, 0, -1):
                                            self.e_counter -= 1
                                        for i in range(count_enroll, 0, -1):
                                            self.e_counter += 1
                                        if choice == "register":
                                            send_keys("{ENTER}")
                                            time.sleep(1)
                                            self.add_enrolled_classes_list(section, classes)
                                            self.after(100, self.show_success_message, 350, 265,
                                                       translation["success_enrolled"])
                                        elif choice == "drop":
                                            self.add_dropped_classes_list(section, classes)
                                            self.after(100, self.show_success_message, 350, 265,
                                                       translation["success_dropped"])
                                        if self.e_counter + self.m_counter == 15:
                                            self.submit.configure(state="disabled")
                                            self.multiple.configure(state="disabled")
                                            self.after(2500, self.show_information_message, 350, 265,
                                                       translation["enrollment_limit"])
                                    else:
                                        self.after(100, self.show_error_message, 320, 235,
                                                   translation["failed_enroll"])
                                        self.submit.configure(state="disabled")
                                        self.unbind("<Return>")
                                        self.not_rebind = True
                                        self.after(2500, self.show_enrollment_error_information, text)
                                else:
                                    if count_enroll == 15:
                                        self.submit.configure(state="disabled")
                                        self.submit_multiple.configure(sate="disabled")
                                        self.after(100, self.show_information_message, 350, 265,
                                                   translation["enrollment_limit"])
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                    else:
                                        if "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" \
                                                not in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                            send_keys("{ENTER}")
                                            self.reset_activity_timer(None)
                                            self.after(100, self.show_error_message, 300, 210,
                                                       translation["failed_enroll"])
                                            if not self.enrollment_error_check:
                                                self.submit.configure(state="disabled")
                                                self.unbind("<Return>")
                                                self.not_rebind = True
                                                self.after(2500, self.show_enrollment_error_information)
                                                self.enrollment_error_check = True
                                        else:
                                            self.after(100, self.show_error_message, 315, 210,
                                                       translation["failed_enroll"])
                                            if not self.enrollment_error_check:
                                                self.submit.configure(state="disabled")
                                                self.unbind("<Return>")
                                                self.not_rebind = True
                                                self.after(2500, self.show_enrollment_error_information)
                                                self.enrollment_error_check = True
                            else:
                                if not classes or not section or not semester:
                                    self.after(100, self.show_error_message, 350, 230, translation["missing_info"])
                                elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE):
                                    self.after(100, self.show_error_message, 360, 230,
                                               translation["class_format_error"])
                                elif not re.fullmatch("^[A-Z]{2}[A-Z0-9]$", section, flags=re.IGNORECASE):
                                    self.after(100, self.show_error_message, 360, 230,
                                               translation["section_format_error"])
                                elif not re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE):
                                    self.after(100, self.show_error_message, 360, 230,
                                               translation["semester_format_error"])
                        else:
                            if classes in self.enrolled_classes_list.values() or section in self.enrolled_classes_list:
                                self.after(100, self.show_error_message, 335, 240, translation["already_enrolled"])
                            if classes in self.dropped_classes_list.values() or section in self.dropped_classes_list:
                                self.after(100, self.show_error_message, 335, 240, translation["already_dropped"])
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
                self.log_error(e)
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                self.after(100, self.show_sidebar_windows)
                if self.error_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                      message=translation["automation_error"],
                                      icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(0, error_automation)
                if not self.not_rebind:
                    self.bind("<Return>", lambda event: self.submit_event_handler())
                ctypes.windll.user32.BlockInput(False)

    def add_enrolled_classes_list(self, section, classes):
        if section in self.dropped_classes_list:
            del self.dropped_classes_list[section]
        if section not in self.enrolled_classes_list:
            self.enrolled_classes_list[section] = classes
        elif section in self.enrolled_classes_list:
            del self.enrolled_classes_list[section]

    def add_dropped_classes_list(self, section, classes):
        if section in self.enrolled_classes_list:
            del self.enrolled_classes_list[section]
        if section not in self.dropped_classes_list:
            self.dropped_classes_list[section] = classes
        elif section in self.dropped_classes_list:
            del self.dropped_classes_list[section]

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
                self.automation_preparations()
                classes = self.s_classes_entry.get().upper().replace(" ", "").replace("-", "")
                semester = self.s_semester_entry.get().upper().replace(" ", "")
                show_all = self.show_all.get()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if (re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE)
                                and re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE)):
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.wait_for_window()
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1CS")
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            send_keys("{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            if self.search_function_counter == 0 or semester != self.get_semester_for_pdf:
                                screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                screenshot_thread.start()
                                screenshot_thread.join()
                                text_output = self.capture_screenshot()
                                if "INVALID TERM SELECTION" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(100, self.show_error_message, 320, 235, translation["invalid_semester"])
                                    return
                            clipboard_content = None
                            try:
                                clipboard_content = self.clipboard_get()
                            except tk.TclError:
                                print("Clipboard contains non-text data, possibly an image or other formats")
                            except Exception as e:
                                print("Error handling clipboard content:", e)
                            if self.search_function_counter == 0:
                                ctypes.windll.user32.BlockInput(False)
                                self.automate_copy_class_data()
                                ctypes.windll.user32.BlockInput(True)
                                copy = pyperclip.paste()
                                data, course_found, invalid_action, y_n_found = TeraTermUI.extract_class_data(copy)
                                if "INVALID ACTION" in copy and "LISTA DE SECCIONES" not in copy:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(100, self.show_error_message, 320, 235, translation["failed_to_search"])
                                    return
                                if data or course_found or invalid_action or y_n_found:
                                    self.search_function_counter += 1
                                if classes in copy:
                                    self.get_class_for_pdf = classes
                                    self.get_semester_for_pdf = semester
                                    self.show_all_sections = self.show_all.get()
                                    self.after(0, self.display_data, data)
                                    self.clipboard_clear()
                                    if clipboard_content is not None:
                                        self.clipboard_append(clipboard_content)
                                    return
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
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            if "MORE SECTIONS" in text_output:
                                self.after(0, self.search_next_page_layout)
                            if "COURSE NOT IN" in text_output:
                                if lang == "English":
                                    self.after(100, self.show_error_message, 300, 215,
                                               "Error! Course: " + classes + " not found")
                                elif lang == "Español":
                                    self.after(100, self.show_error_message, 310, 215,
                                               "Error! Clase: " + classes + " \nno se encontro")
                                self.search_function_counter += 1
                            elif "INVALID ACTION" in text_output or "INVALID TERM SELECTION" in text_output:
                                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                send_keys("{ENTER}")
                                self.reset_activity_timer(None)
                                if "INVALID TERM SELECTION" in text_output:
                                    self.after(100, self.show_error_message, 320, 235, translation["invalid_semester"])
                                if "INVALID ACTION" in text_output:
                                    self.after(100, self.show_error_message, 320, 235, translation["failed_to_search"])
                                self.search_function_counter += 1
                            else:
                                ctypes.windll.user32.BlockInput(False)
                                self.search_function_counter += 1
                                self.automate_copy_class_data()
                                ctypes.windll.user32.BlockInput(True)
                                copy = pyperclip.paste()
                                data, course_found, invalid_action, y_n_found = TeraTermUI.extract_class_data(copy)
                                self.get_class_for_pdf = classes
                                self.get_semester_for_pdf = semester
                                self.show_all_sections = self.show_all.get()
                                self.after(0, self.display_data, data)
                                self.clipboard_clear()
                                if clipboard_content is not None:
                                    self.clipboard_append(clipboard_content)
                        else:
                            if not classes or not semester:
                                self.after(100, self.show_error_message, 350, 230, translation["missing_info_search"])
                            elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE):
                                self.after(100, self.show_error_message, 360, 230, translation["class_format_error"])
                            elif not re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE):
                                self.after(100, self.show_error_message, 360, 230, translation["semester_format_error"])
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
                self.log_error(e)
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                self.after(100, self.show_sidebar_windows)
                if self.error_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                      message=translation["automation_error"],
                                      icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(0, error_automation)
                self.bind("<Return>", lambda event: self.search_event_handler())
                ctypes.windll.user32.BlockInput(False)

    def search_next_page_layout(self):
        self.search_next_page_status = True
        self.search_next_page.configure(state="normal")
        self.search.configure(width=85)
        self.search.grid(row=1, column=1, padx=(285, 0), pady=(0, 5), sticky="n")
        self.search_next_page.grid(row=1, column=1, padx=(465, 0), pady=(0, 5), sticky="n")

    def my_classes_event_handler(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        dialog_width = 300
        dialog_height = 300
        dialog_x = main_window_x + (main_window_width - dialog_width) / 2
        dialog_y = main_window_y + (main_window_height - dialog_height) / 2
        self.dialog = SmoothFadeInputDialog(text=translation["dialog_message"], title=translation["dialog_title"],
                                            ok_text=translation["submit"], cancel_text=translation["option_1"],
                                            lang=lang)
        self.dialog.geometry("+%d+%d" % (dialog_x + 75, dialog_y + 60))
        self.dialog.iconbitmap(self.icon_path)
        self.dialog.bind("<Escape>", lambda event: self.dialog.destroy())
        self.prev_dialog_input = self.dialog_input
        self.dialog_input = self.dialog.get_input()
        if self.dialog_input is not None:
            task_done = threading.Event()
            loading_screen = self.show_loading_screen()
            self.update_loading_screen(loading_screen, task_done)
            event_thread = threading.Thread(target=self.my_classes_event, args=(task_done,))
            event_thread.start()
        else:
            self.dialog.destroy()

    # function for seeing the classes you are currently enrolled for
    def my_classes_event(self, task_done):
        with self.lock_thread:
            try:
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                dialog_input = self.dialog_input.upper().replace(" ", "")
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if re.fullmatch("^[A-Z][0-9]{2}$", dialog_input, flags=re.IGNORECASE):
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.wait_for_window()
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1CP")
                            self.uprb.UprbayTeraTermVt.type_keys(dialog_input)
                            send_keys("{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            if "INVALID TERM SELECTION" not in text_output and "INVALID ACTION" not in text_output:
                                clipboard_content = None
                                try:
                                    clipboard_content = self.clipboard_get()
                                except tk.TclError:
                                    print("Clipboard contains non-text data, possibly an image or other formats")
                                except Exception as e:
                                    print("Error handling clipboard content:", e)
                                ctypes.windll.user32.BlockInput(False)
                                self.automate_copy_class_data()
                                ctypes.windll.user32.BlockInput(True)
                                copy = pyperclip.paste()
                                enrolled_classes, total_credits = self.extract_my_enrolled_classes(copy)
                                self.after(0, self.display_enrolled_data, enrolled_classes, total_credits)
                                self.clipboard_clear()
                                if clipboard_content is not None:
                                    self.clipboard_append(clipboard_content)
                                self.tabview.grid_forget()
                            else:
                                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                send_keys("{ENTER}")
                                self.reset_activity_timer(None)
                                self.after(100, self.show_error_message, 300, 215, translation["invalid_semester"])
                        else:
                            self.after(100, self.show_error_message, 300, 215, translation["invalid_semester"])
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
                self.log_error(e)
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                self.after(100, self.show_sidebar_windows)
                if self.error_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                      message=translation["automation_error"],
                                      icon="warning", button_width=380)
                        self.switch_tab()
                        self.error_occurred = False

                    self.after(0, error_automation)
                ctypes.windll.user32.BlockInput(False)

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

    def move_up_scrollbar(self):
        if self.up_arrow_key_enabled:
            if self.enrolled_rows is None:
                self.search_scrollbar.scroll_more_up()
            else:
                self.my_classes_frame.scroll_more_up()

    def move_down_scrollbar(self):
        if self.down_arrow_key_enabled:
            if self.enrolled_rows is None:
                self.search_scrollbar.scroll_more_down()
            else:
                self.my_classes_frame.scroll_more_down()

    def move_top_scrollbar(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            if self.enrolled_rows is None:
                self.search_scrollbar.scroll_to_top()
            else:
                self.my_classes_frame.scroll_to_top()

    def move_bottom_scrollbar(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            if self.enrolled_rows is None:
                self.search_scrollbar.scroll_to_bottom()
            else:
                self.my_classes_frame.scroll_to_bottom()

    # multiple classes screen
    def multiple_classes_event(self):
        self.focus_set()
        self.in_enroll_frame = False
        self.in_search_frame = False
        self.in_multiple_screen = True
        self.unbind("<Control-Tab>")
        self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
        self.bind("<Up>", lambda event: self.add_event_up_arrow_key())
        self.bind("<Down>", lambda event: self.remove_event_down_arrow_key())
        self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_event2())
        self.bind("<space>", lambda event: self.keybind_auto_enroll())
        self.multiple_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 30))
        self.multiple_frame.grid_columnconfigure(2, weight=1)
        self.m_button_frame.grid(row=3, column=1, columnspan=4, rowspan=4, padx=(0, 0), pady=(0, 10))
        self.m_button_frame.grid_columnconfigure(2, weight=1)
        self.save_frame.grid(row=3, column=2, padx=(0, 50), pady=(0, 8), sticky="e")
        self.save_frame.grid_columnconfigure(2, weight=1)
        self.auto_frame.grid(row=3, column=1, padx=(50, 0), pady=(0, 8), sticky="w")
        self.auto_frame.grid_columnconfigure(2, weight=1)
        self.title_multiple.grid(row=0, column=1, padx=(0, 0), pady=(0, 20))
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
        if self.enrolled_rows is not None:
            self.my_classes_frame.grid_forget()
            self.modify_classes_frame.grid_forget()
            self.back_my_classes.grid_forget()
            self.after(0, self.destroy_enrolled_frame)

    def detect_change(self):
        check = self.save_data.get()
        if check == "on":
            self.save_data.deselect()

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
                                hover_color=("darkred", "use_default", "use_default"))
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
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                classes = []
                sections = []
                semester = self.m_semester_entry[0].get().upper().replace(" ", "")
                choices = []
                for i in range(self.a_counter + 1):
                    classes.append(self.m_classes_entry[i].get().upper().replace(" ", "").replace("-", ""))
                    sections.append(self.m_section_entry[i].get().upper().replace(" ", ""))
                    choices.append(self.m_register_menu[i].get())
                can_enroll_classes = self.e_counter + self.m_counter + self.a_counter + 1 <= 15
                if asyncio.run(self.test_connection(lang)) and self.check_server() and self.check_format():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if can_enroll_classes:
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.wait_for_window()
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
                                    "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" not in text_output \
                                    and "ENTER REGISTRATION" in text_output and count_enroll != 15:
                                self.e_counter = 0
                                self.m_counter = 0
                                send_keys("{TAB 3}")
                                for i in range(count_enroll, 0, -1):
                                    self.e_counter += 1
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
                                time.sleep(1.5)
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
                                        for i in range(self.a_counter + 1)
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
                                    self.submit_multiple.configure(state="disabled")
                                    self.unbind("<Return>")
                                    self.not_rebind = True
                                    self.after(0, self.show_enrollment_error_information_multiple, text)
                                    if "CONFIRMED" in text and "DROPPED" in text:
                                        send_keys("{ENTER}")
                                        time.sleep(1)
                                        self.after(100, self.show_success_message, 350, 265,
                                                   translation["enrolled_dropped_multiple_success"])
                                    elif "CONFIRMED" in text and "DROPPED" not in text:
                                        send_keys("{ENTER}")
                                        time.sleep(1)
                                        self.after(100, self.show_success_message, 350, 265,
                                                   translation["enrolled_multiple_success"])
                                    elif "DROPPED" in text and "CONFIRMED" not in text:
                                        self.after(100, self.show_success_message, 350, 265,
                                                   translation["dropped_multiple_success"])
                                    if self.e_counter + self.m_counter == 15:
                                        self.go_back_event2()
                                        self.submit.configure(state="disabled")
                                        self.multiple.configure(state="disabled")
                                        self.after(2500, self.show_information_message, 350, 265,
                                                   translation["enrollment_limit"])
                                else:
                                    self.after(100, self.show_error_message, 320, 235,
                                               translation["failed_enroll_multiple"])
                                    self.submit_multiple.configure(state="disabled")
                                    self.unbind("<Return>")
                                    self.not_rebind = True
                                    self.after(0, self.show_enrollment_error_information_multiple, text)
                                    self.m_counter = self.m_counter - self.a_counter - 1
                                    self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
                            else:
                                if count_enroll == 15:
                                    self.submit.configure(state="disabled")
                                    self.submit_multiple.configure(sate="disabled")
                                    self.after(100, self.show_information_message, 350, 265,
                                               translation["enrollment_limit"])
                                if "INVALID TERM SELECTION" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(100, self.show_error_message, 300, 215,
                                               translation["invalid_semester"])
                                else:
                                    if "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" not in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                    if "INVALID ACTION" in text_output and self.started_auto_enroll:
                                        self.after(0, self.submit_multiple_event_handler)
                                        self.error_auto_enroll = True
                                    else:
                                        self.after(100, self.show_error_message, 330, 210,
                                                   translation["failed_enroll_multiple"])
                                        if not self.enrollment_error_check:
                                            self.submit_multiple.configure(state="disabled")
                                            self.unbind("<Return>")
                                            self.not_rebind = True
                                            self.after(0, self.show_enrollment_error_information)
                                            self.enrollment_error_check = True
                        else:
                            self.after(100, self.show_error_message, 320, 235,
                                       translation["max_enroll"])
                            self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
                    self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
                self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
                self.log_error(e)
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                self.after(100, self.show_sidebar_windows)
                if not self.error_auto_enroll:
                    self.started_auto_enroll = False
                if self.error_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                      message=translation["automation_error"],
                                      icon="question", button_width=380)
                        self.error_occurred = False

                    self.after(0, error_automation)
                if not self.not_rebind:
                    self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
                ctypes.windll.user32.BlockInput(False)

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
                self.automation_preparations()
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
                menu = menu_dict.get(menu, menu).replace(" ", "")
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE) \
                                and menu in menu_dict.values():
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.wait_for_window()
                            match menu:
                                case "SRM":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                case "004":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("004")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                case "1GP":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("1GP")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
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
                                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0),
                                                                  sticky="n")
                                            self.go_next_1GP.grid(row=5, column=1, padx=(110, 0), pady=(40, 0),
                                                                  sticky="n")

                                        self.after(0, go_next_grid)
                                    else:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "118":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("118")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(100, self.show_error_message, 300, 215,
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
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys("004")
                                        self.uprb.UprbayTeraTermVt.type_keys(semester)
                                        send_keys("{ENTER}")
                                        self.after(100, self.show_information_message, 310, 225,
                                                   translation["hold_flag"])
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                    if "CONFLICT" not in text_output or "INVALID TERM SELECTION" not in text_output:
                                        def go_next_grid():
                                            self.go_next_1VE.configure(state="normal")
                                            self.go_next_1GP.grid_forget()
                                            self.go_next_409.grid_forget()
                                            self.go_next_683.grid_forget()
                                            self.go_next_4CM.grid_forget()
                                            self.menu_submit.configure(width=100)
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
                                    self.after(0, self.disable_go_next_buttons)
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(100, self.show_error_message, 300, 215,
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
                                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0),
                                                                  sticky="n")
                                            self.go_next_409.grid(row=5, column=1, padx=(110, 0), pady=(40, 0),
                                                                  sticky="n")

                                        self.after(0, go_next_grid)
                                    else:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(100, self.show_error_message, 300, 215,
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
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys("004")
                                        send_keys("{ENTER}")
                                        self.after(100, self.show_information_message, 310, 225,
                                                   translation["hold_flag"])
                                    if "CONFLICT" not in text_output:
                                        def go_next_grid():
                                            self.go_next_683.configure(state="normal")
                                            self.submit.configure(width=100)
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
                                    self.after(0, self.disable_go_next_buttons)
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "TERM OUTDATED" in text_output or "NO PUEDE REALIZAR CAMBIOS" in text_output or \
                                            "INVALID TERM SELECTION" in text_output:
                                        self.focus_or_not = True
                                        if "TERM OUTDATED" in text_output or "INVALID TERM SELECTION" in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                            send_keys("{ENTER}")
                                            self.reset_activity_timer(None)
                                        if lang == "English":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "Error! Failed to enter\n " + self.menu_entry.get()
                                                       + " screen")
                                        elif lang == "Español":
                                            self.after(100, self.show_error_message, 325, 240,
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
                                    if "TERM OUTDATED" not in text_output and \
                                            "NO PUEDE REALIZAR CAMBIOS" not in text_output and \
                                            "INVALID TERM SELECTION" not in text_output:
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
                                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0),
                                                                  sticky="n")
                                            self.go_next_4CM.grid(row=5, column=1, padx=(110, 0), pady=(40, 0),
                                                                  sticky="n")

                                        self.after(0, go_next_grid)
                                    if "TERM OUTDATED" in text_output or "NO PUEDE REALIZAR CAMBIOS" in text_output:
                                        self.focus_or_not = True
                                        if "TERM OUTDATED" in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                            send_keys("{ENTER}")
                                            self.reset_activity_timer(None)
                                        if lang == "English":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "Error! Failed to enter\n " + self.menu_entry.get() + " screen")
                                        elif lang == "Español":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "Error! No se pudo entrar"
                                                       "\n a la pantalla" + self.menu_entry.get())
                                case "4SP":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("4SP")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    send_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                    screenshot_thread.start()
                                    screenshot_thread.join()
                                    text_output = self.capture_screenshot()
                                    if "TERM OUTDATED" in text_output or "NO PUEDE REALIZAR CAMBIOS" in text_output:
                                        self.focus_or_not = True
                                        if "TERM OUTDATED" in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                            send_keys("{ENTER}")
                                            self.reset_activity_timer(None)
                                        if lang == "English":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "Error! Failed to enter\n " + self.menu_entry.get() + " screen")
                                        elif lang == "Español":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "Error! No se pudo entrar"
                                                       "\n a la pantalla" + self.menu_entry.get())
                                case "SO":
                                    self.focus_or_not = True
                                    self.after(0, self.sign_out)
                        else:
                            if not semester or not menu:
                                self.after(100, self.show_error_message, 350, 230,
                                           translation["menu_missing_info"])
                            elif not re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE):
                                self.after(100, self.show_error_message, 360, 230,
                                           translation["semester_format_error"])
                            elif menu not in menu_dict.values():
                                self.after(100, self.show_error_message, 340, 230,
                                           translation["menu_code_error"])
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
                self.log_error(e)
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if self.focus_or_not:
                    self.after(100, self.set_focus_to_tkinter)
                else:
                    self.after(100, TeraTermUI.unfocus_tkinter)
                self.after(100, self.show_sidebar_windows)
                self.focus_or_not = False
                if self.error_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                      message=translation["automation_error"],
                                      icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(0, error_automation)
                self.bind("<Return>", lambda event: self.option_menu_event_handler())
                ctypes.windll.user32.BlockInput(False)

    def sign_out(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        msg = CTkMessagebox(master=self, title=translation["so_title"],
                            message=translation["so_message"],
                            option_1=translation["option_1"],
                            option_2=translation["option_2"],
                            option_3=translation["option_3"],
                            icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if TeraTermUI.checkIfProcessRunning("ttermpro") and response[0] == "Yes" \
                or response[0] == "Sí":
            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
            if term_window.isMinimized:
                term_window.restore()
            self.wait_for_window()
            self.uprb.UprbayTeraTermVt.type_keys("SO")
            send_keys("{ENTER}")
        elif not TeraTermUI.checkIfProcessRunning("ttermpro") and response[0] == "Yes" \
                or response[0] == "Sí":
            self.focus_or_not = True
            self.after(100, self.show_error_message, 350, 265,
                       translation["tera_term_not_running"])

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
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        TeraTermUI.unfocus_tkinter()
                        if self._1VE_screen:
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.wait_for_window()
                            send_keys("{TAB 3}")
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                        elif self._1GP_screen:
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.wait_for_window()
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                        elif self._409_screen:
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.wait_for_window()
                            send_keys("{TAB 4}")
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                        elif self._683_screen:
                            self.submit.configure(state="disabled")
                            self.search.configure(state="disabled")
                            self.multiple.configure(state="disabled")
                            self.menu_submit.configure(state="disabled")
                            self.show_classes.configure(state="disabled")
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.wait_for_window()
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                        elif self._4CM_screen:
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.wait_for_window()
                            send_keys("{ENTER}")
                            self.reset_activity_timer(None)
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            if "RATE NOT ON ARFILE" in text_output:
                                self.focus_or_not = True
                                self.after(100, self.show_error_message, 310, 225, translation["unknown_error"])
                            else:
                                self.go_next_4CM.configure(state="disabled")
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])

            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
                self.log_error(e)
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.reset_activity_timer(None)
                if self.focus_or_not:
                    self.after(100, self.set_focus_to_tkinter)
                else:
                    self.after(100, TeraTermUI.unfocus_tkinter)
                self.after(100, self.show_sidebar_windows)
                if self.error_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                      message=translation["automation_error"],
                                      icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(0, error_automation)
                self.bind("<Return>", lambda event: self.option_menu_event_handler())
                ctypes.windll.user32.BlockInput(False)

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
                translation = self.load_language(lang)
                self.automation_preparations()
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                        if term_window.isMinimized:
                            term_window.restore()
                        self.wait_for_window()
                        TeraTermUI.unfocus_tkinter()
                        send_keys("{ENTER}")
                        clipboard_content = None
                        try:
                            clipboard_content = self.clipboard_get()
                        except tk.TclError:
                            print("Clipboard contains non-text data, possibly an image or other formats")
                        except Exception as e:
                            print("Error handling clipboard content:", e)
                        ctypes.windll.user32.BlockInput(False)
                        self.automate_copy_class_data()
                        ctypes.windll.user32.BlockInput(True)
                        copy = pyperclip.paste()
                        data, course_found, invalid_action, y_n_found = TeraTermUI.extract_class_data(copy)
                        self.ignore = False
                        self.after(0, self.display_data, data)
                        self.clipboard_clear()
                        if clipboard_content is not None:
                            self.clipboard_append(clipboard_content)
                        self.reset_activity_timer(None)
                        screenshot_thread = threading.Thread(target=self.capture_screenshot)
                        screenshot_thread.start()
                        screenshot_thread.join()
                        text_output = self.capture_screenshot()
                        if "MORE SECTIONS" not in text_output:
                            self.search_next_page.configure(state="disabled")
                            self.search_next_page_status = False
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
                self.log_error(e)
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                self.after(100, self.show_sidebar_windows)
                if self.error_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                      message=translation["automation_error"],
                                      icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(0, error_automation)
                self.bind("<Return>", lambda event: self.search_event_handler())
                ctypes.windll.user32.BlockInput(False)

    # disable these buttons if the user changed screen
    def disable_go_next_buttons(self):
        if self.init_class:
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
        self.reset_activity_timer(None)

    def auth_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.auth_event, args=(task_done,))
        event_thread.start()

    # Authentication required frame, where user is asked to input his username
    def auth_event(self, task_done):
        with self.lock_thread:
            try:
                self.automation_preparations()
                if not self.skip_auth:
                    username = self.username_entry.get().replace(" ", "").lower()
                else:
                    username = "students"
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if username == "students":
                            term_window = gw.getWindowsWithTitle("SSH Authentication")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.uprbay_window.wait("visible", timeout=5)
                            user = self.uprb.UprbayTeraTermVt.child_window(title="User name:",
                                                                           control_type="Edit").wrapper_object()
                            user.set_text(username)
                            check = self.uprb.UprbayTeraTermVt.child_window(title="Remember password in memory",
                                                                            control_type="CheckBox")
                            if check.get_toggle_state() == 0:
                                check.invoke()
                            self.uprb.UprbayTeraTermVt.child_window(title="Use plain password to log in",
                                                                    control_type="RadioButton").click()
                            self.hide_loading_screen()
                            conn = self.uprb.UprbayTeraTermVt.child_window(title="OK",
                                                                           control_type="Button").wrapper_object()
                            conn.click()
                            self.show_loading_screen_again()
                            self.server_status = self.wait_for_prompt(
                                "return to continue", "REGRESE PRONTO")
                            if self.server_status == "Maintenance message found":
                                def server_closed():
                                    self.unbind("<Return>")
                                    if not self.skip_auth:
                                        self.back.configure(state="disabled")
                                        self.auth.configure(state="disabled")
                                    if not self.disable_audio:
                                        winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                    CTkMessagebox(title=translation["server_maintenance_title"],
                                                  message=translation["server_maintenance"], icon="cancel",
                                                  button_width=380)
                                    self.error_occurred = True

                                self.after(0, server_closed)
                            elif self.server_status == "Prompt found":
                                send_keys("{ENTER 3}")
                                self.move_window()
                                self.bind("<Return>", lambda event: self.student_event_handler())
                                self.after(0, self.initialization_student)
                                self.after(100, self.auth_info_frame)
                                self.in_student_frame = True
                                if self.skip_auth:
                                    self.home_frame.grid_forget()
                                    self.intro_box.grid_forget()
                            elif self.server_status == "Timeout":
                                def timeout():
                                    self.unbind("<Return>")
                                    if not self.skip_auth:
                                        self.back.configure(state="disabled")
                                        self.auth.configure(state="disabled")
                                    if not self.disable_audio:
                                        winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                    CTkMessagebox(title="Error", message=translation["timeout_server"], icon="cancel",
                                                  button_width=380)
                                    self.error_occurred = True

                                self.after(0, timeout)
                        elif username != "students":
                            self.bind("<Return>", lambda event: self.auth_event_handler())
                            self.after(100, self.show_error_message, 300, 215, translation["invalid_username"])
                    else:
                        self.bind("<Return>", lambda event: self.auth_event_handler())
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
                else:
                    self.bind("<Return>", lambda event: self.auth_event_handler())
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
                self.log_error(e)
            finally:
                task_done.set()
                self.after(100, self.set_focus_to_tkinter)
                self.after(100, self.show_sidebar_windows)
                if self.server_status == "Maintenance message found" or self.server_status == "Timeout":
                    self.after(3500, self.go_back_event)
                elif self.error_occurred:
                    self.after(0, self.go_back_event)
                ctypes.windll.user32.BlockInput(False)

    def auth_info_frame(self):
        lang = self.language_menu.get()
        self.student_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 100))
        self.student_frame.grid_columnconfigure(2, weight=1)
        self.s_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(0, 0), pady=(0, 40))
        self.s_buttons_frame.grid_columnconfigure(2, weight=1)
        self.title_student.grid(row=0, column=1, padx=(20, 20), pady=(10, 20))
        self.lock_grid.grid(row=1, column=1, padx=(00, 0), pady=(0, 20))
        if lang == "English":
            self.student_id.grid(row=2, column=1, padx=(0, 150), pady=(0, 10))
            self.student_id_entry.grid(row=2, column=1, padx=(100, 0), pady=(0, 10))
            self.code.grid(row=3, column=1, padx=(0, 126), pady=(0, 10))
            self.code_entry.grid(row=3, column=1, padx=(100, 0), pady=(0, 10))
        elif lang == "Español":
            self.student_id.grid(row=2, column=1, padx=(0, 164), pady=(0, 10))
            self.student_id_entry.grid(row=2, column=1, padx=(120, 0), pady=(0, 10))
            self.code.grid(row=3, column=1, padx=(0, 125), pady=(0, 10))
            self.code_entry.grid(row=3, column=1, padx=(120, 0), pady=(0, 10))
        self.show.grid(row=4, column=1, padx=(10, 0), pady=(0, 10))
        self.back_student.grid(row=5, column=0, padx=(0, 10), pady=(0, 0))
        self.system.grid(row=5, column=1, padx=(10, 0), pady=(0, 0))
        self.destroy_auth()
        if self.ask_skip_auth:
            self.unbind("<Return>")
            self.unbind("<Control-BackSpace>")
            self.system.configure(state="disabled")
            self.back_student.configure(state="disabled")
            self.after(750, self.skip_auth_prompt)

    def skip_auth_prompt(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if not self.disable_audio:
            winsound.PlaySound("sounds/update.wav", winsound.SND_ASYNC)
        msg = CTkMessagebox(master=self, title=translation["skip_auth_title"],
                            message=translation["skip_auth"],
                            icon="question",
                            option_1=translation["option_1"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
        if response[0] == "Yes" or response[0] == "Sí":
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (skip_auth) VALUES (?)", ("Yes",))
            else:
                self.cursor.execute("UPDATE user_data SET skip_auth=?", ("Yes",))
            self.skip_auth = True
        else:
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (skip_auth) VALUES (?)", ("No",))
            else:
                self.cursor.execute("UPDATE user_data SET skip_auth=?", ("No",))
            self.skip_auth = False
        self.ask_skip_auth = False
        if self.help and self.help.winfo_exists():
            self.on_help_window_close()
            self.help_button_event()
        self.bind("<Return>", lambda event: self.student_event_handler())
        self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_event())
        self.system.configure(state="normal")
        self.back_student.configure(state="normal")
        self.ask_skip_auth = False

    def disable_enable_auth(self):
        row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
        if self.skip_auth_switch.get() == "on":
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (skip_auth) VALUES (?)", ("Yes",))
            else:
                self.cursor.execute("UPDATE user_data SET skip_auth=?", ("Yes",))
            self.skip_auth = True
        elif self.skip_auth_switch.get() == "off":
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (skip_auth) VALUES (?)", ("No",))
            else:
                self.cursor.execute("UPDATE user_data SET skip_auth=?", ("No",))
            self.skip_auth = False
        self.connection.commit()

    def notice_user(self):
        if self.error and self.error.winfo_exists():
            return
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.attributes("-topmost", True)
        self.tooltip.config(bg="#FFD700")
        self.tooltip.wm_geometry(f"+{main_window_x + 20}+{main_window_y + 20}")
        if TeraTermUI.checkIfProcessRunning("EpicGamesLauncher"):
            text = translation["epic_games"]
        else:
            text = translation["exec_time"]
        label = tk.Label(self.tooltip, text=text,
                         bg="#FFD700", fg="#000", font=("Verdana", 11, "bold"))
        label.pack(padx=5, pady=5)
        self.tooltip.after(12500, self.destroy_tooltip)
        self.tooltip.bind("<Button-1>", lambda e: self.destroy_tooltip())
        self.tooltip.bind("<Button-2>", lambda e: self.destroy_tooltip())
        self.tooltip.bind("<Button-3>", lambda e: self.destroy_tooltip())

    def login_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.login_event, args=(task_done,))
        event_thread.start()

    # Checks if host entry is true
    @measure_time(threshold=7.5)
    def login_event(self, task_done):
        dont_close = False
        with self.lock_thread:
            try:
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                host = self.host_entry.get().replace(" ", "").lower()
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if host == "uprbay.uprb.edu" or host == "uprbayuprbedu":
                        if TeraTermUI.checkIfProcessRunning("ttermpro"):
                            dont_close = True
                            self.login_to_existent_connection()
                        else:
                            try:
                                if self.download or self.teraterm_not_found:
                                    self.edit_teraterm_ini(self.teraterm_file)
                                self.uprb = Application(backend="uia").start(self.location) \
                                    .connect(title="Tera Term - [disconnected] VT", timeout=7)
                                self.uprb_32 = Application().connect(
                                    title="Tera Term - [disconnected] VT", timeout=5)
                                disconnected = self.uprb.window(title="Tera Term - [disconnected] VT")
                                disconnected.wait("visible", timeout=5)
                                host_input = \
                                    self.uprb.TeraTermDisconnectedVt.child_window(title="Host:",
                                                                                  control_type="Edit").wrapper_object()
                                host_input.set_text("uprbay.uprb.edu")
                                self.hide_loading_screen()
                                conn = \
                                    self.uprb.TeraTermDisconnectedVt.child_window(
                                        title="OK", control_type="Button").wrapper_object()
                                conn.click()
                                self.show_loading_screen_again()
                                self.uprbay_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                                self.uprbay_window.wait("visible", timeout=5)
                                if self.uprbay_window.child_window(title="Continue", control_type="Button").exists(
                                        timeout=1):
                                    self.hide_loading_screen()
                                    continue_button = \
                                        self.uprbay_window.child_window(title="Continue",
                                                                        control_type="Button").wrapper_object()
                                    continue_button.click()
                                    self.show_loading_screen_again()
                                self.bind("<Return>", lambda event: self.auth_event_handler())
                                if not self.skip_auth:
                                    self.after(0, self.initialization_auth)
                                self.after(100, self.login_frame)
                            except AppStartError as e:
                                print("An error occurred: ", e)
                                self.bind("<Return>", lambda event: self.login_event_handler())
                                self.after(100, self.show_error_message, 425, 330,
                                           translation["tera_term_failed_to_start"])
                                if not self.download:
                                    self.after(3500, self.download_teraterm)
                                    self.download = True
                    elif host != "uprbay.uprb.edu":
                        self.bind("<Return>", lambda event: self.login_event_handler())
                        self.after(100, self.show_error_message, 300, 215, translation["invalid_host"])
                else:
                    self.bind("<Return>", lambda event: self.login_event_handler())
            except Exception as e:
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                error_message = str(e)
                if "catching classes that do not inherit from BaseException is not allowed" in error_message:
                    print("Caught the specific error message: ", error_message)
                    self.destroy_windows()

                    def rare_error():
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                      message=translation["unexpected_error"], icon="warning", button_width=380)

                    self.error_occurred = False
                    self.after(0, rare_error)
                else:
                    print("An error occurred:", error_message)
                    self.error_occurred = True
                    self.log_error(e)
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                self.after(100, self.show_sidebar_windows)
                if self.error_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not dont_close:
                            try:
                                subprocess.run(["taskkill", "/f", "/im", "ttermpro.exe"],
                                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            except subprocess.CalledProcessError:
                                print("Could not terminate ttermpro.exe.")
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                      message=translation["tera_term_forced_to_close"], icon="warning",
                                      button_width=380)
                        self.bind("<Return>", lambda event: self.login_event_handler())
                        self.error_occurred = False

                    self.after(0, error_automation)
                ctypes.windll.user32.BlockInput(False)

    def login_frame(self):
        lang = self.language_menu.get()
        if not self.skip_auth:
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
            self.auth.grid(row=4, column=1, padx=(10, 0), pady=(0, 0))
            self.home_frame.grid_forget()
            self.intro_box.grid_forget()
        else:
            self.auth_event_handler()
            self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_event())
        self.main_menu = False
        if self.help is not None and self.help.winfo_exists():
            self.files.configure(state="disabled")
        self.language_menu.configure(state="disabled")
        self.intro_box.stop_autoscroll(event=None)
        self.language_menu_tooltip.show()
        self.slideshow_frame.pause_cycle()

    def login_to_existent_connection(self):
        timeout_counter = 0
        skip = False
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        while not self.tesseract_unzipped:
            time.sleep(1)
            timeout_counter += 1
            if timeout_counter > 5:
                skip = True
                break
        if (TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT")
                and not TeraTermUI.window_exists("SSH Authentication") and not skip):
            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
            if term_window.isMinimized:
                term_window.restore()
            screenshot_thread = threading.Thread(target=self.capture_screenshot)
            screenshot_thread.start()
            screenshot_thread.join()
            text_output = self.capture_screenshot()
            if (("STUDENTS REQ/DROP" in text_output or "HOLD FLAGS" in text_output or
                 "PROGRAMA DE CLASES" in text_output or "ACADEMIC STATISTICS" in text_output or
                 "SNAPSHOT" in text_output or "SOLICITUD DE PRORROGA" in text_output or
                 "LISTA DE SECCIONES") and "return to continue" not in text_output and
                    "SISTEMA DE INFORMACION" not in text_output):
                count = TeraTermUI.countRunningProcesses("ttermpro")
                if count > 1:
                    self.after(100, self.show_error_message, 450, 270, translation["count_processes"])
                    self.bind("<Return>", lambda event: self.login_event_handler())
                    return
                self.uprb = Application(backend="uia").connect(
                    title="uprbay.uprb.edu - Tera Term VT", timeout=5)
                self.uprb_32 = Application().connect(
                    title="uprbay.uprb.edu - Tera Term VT", timeout=5)
                self.uprbay_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                self.uprbay_window.wait("visible", timeout=5)
                send_keys("{VK_RIGHT}")
                send_keys("{VK_LEFT}")
                self.after(0, self.initialization_class)
                self.after(0, self.initialization_multiple)
                self.after(100, self.student_info_frame)
                self.main_menu = False
                if self.help is not None and self.help.winfo_exists():
                    self.files.configure(state="disabled")
                self.reset_activity_timer(None)
                self.start_check_idle_thread()
                self.start_check_process_thread()
                self.in_student_frame = False
                self.run_fix = True
                if self.help is not None and self.help.winfo_exists():
                    self.fix.configure(state="normal")
                self.language_menu.configure(state="disabled")
                self.intro_box.stop_autoscroll(event=None)
                self.language_menu_tooltip.show()
                self.home_frame.grid_forget()
                self.intro_box.grid_forget()
                self.slideshow_frame.pause_cycle()
                self.switch_tab()
                self.move_window()
            else:
                self.bind("<Return>", lambda event: self.login_event_handler())
                self.after(100, self.show_error_message, 450, 265,
                           translation["tera_term_already_running"])
        else:
            self.bind("<Return>", lambda event: self.login_event_handler())
            self.after(100, self.show_error_message, 450, 265,
                       translation["tera_term_already_running"])

    def keybind_go_back_event(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            self.go_back_event()

    # function that lets user go back to the initial screen
    def go_back_event(self):
        response = None
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.loading_screen is not None and self.loading_screen.winfo_exists():
            return
        if not self.error_occurred:
            msg = CTkMessagebox(master=self, title=translation["go_back_title"],
                                message=translation["go_back"],
                                icon="question",
                                option_1=translation["option_1"], option_2=translation["option_2"],
                                option_3=translation["option_3"],
                                icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "use_default", "use_default"))
            response = msg.get()
        if TeraTermUI.checkIfProcessRunning("ttermpro") and (
                self.error_occurred or (response and (response[0] == "Yes" or response[0] == "Sí"))):
            self.uprb.kill(soft=True)
        if self.error_occurred or (response and (response[0] == "Yes" or response[0] == "Sí")):
            self.is_idle_thread_running = False
            self.is_check_process_thread_running = False
            self.reset_activity_timer(None)
            self.unbind("<space>")
            self.unbind("<Up>")
            self.unbind("<Down>")
            self.unbind("<Home>")
            self.unbind("<End>")
            self.unbind("<Control-Tab>")
            self.unbind("<Control-BackSpace>")
            self.bind("<Return>", lambda event: self.login_event_handler())
            if not self.home_frame.grid_info():
                self.home_frame.grid(row=0, column=1, rowspan=5, columnspan=5, padx=(0, 0), pady=(10, 0))
                self.introduction.grid(row=0, column=1, columnspan=2, padx=(20, 0), pady=(20, 0))
                if lang == "English":
                    self.host.grid(row=2, column=1, padx=(0, 170), pady=(15, 15))
                elif lang == "Español":
                    self.host.grid(row=2, column=1, padx=(0, 190), pady=(15, 15))
                self.host_entry.grid(row=2, column=1, padx=(20, 0), pady=(15, 15))
                self.log_in.grid(row=3, column=1, padx=(20, 0), pady=(15, 15))
                self.slideshow_frame.grid(row=1, column=1, padx=(20, 0), pady=(140, 0))
                self.intro_box.grid(row=1, column=1, padx=(20, 0), pady=(0, 150))
            self.destroy_auth()
            self.destroy_student()
            if self.init_class:
                self.tabview.grid_forget()
                self.t_buttons_frame.grid_forget()
                self.multiple_frame.grid_forget()
                self.m_button_frame.grid_forget()
                self.multiple.configure(state="normal")
                self.submit.configure(state="normal")
                self.show_classes.configure(state="normal")
                self.search.configure(state="normal")
                self.search_function_counter = 0
                self.e_counter = 0
                self.m_counter = 0
                self.enrolled_classes_list.clear()
                self.dropped_classes_list.clear()
            self.language_menu.configure(state="normal")
            self.language_menu_tooltip.hide()
            self.slideshow_frame.resume_cycle()
            self.intro_box.reset_autoscroll()
            if not self.intro_box.disabled_autoscroll:
                self.intro_box.restart_autoscroll()
            self.run_fix = False
            if self.help is not None and self.help.winfo_exists():
                self.fix.configure(state="disabled")
            self.in_student_frame = False
            self.in_enroll_frame = False
            self.in_search_frame = False
            self.main_menu = True
            if self.help is not None and self.help.winfo_exists():
                self.files.configure(state="normal")
            if self.error_occurred:
                self.destroy_windows()
                if (self.server_status != "Maintenance message found" and self.server_status != "Timeout") \
                        and self.tesseract_unzipped:
                    if not self.disable_audio:
                        winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title=translation["automation_error_title"],
                                  message=translation["tera_term_forced_to_close"],
                                  icon="warning", button_width=380)
            self.error_occurred = False

    def keybind_go_back_event2(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            self.go_back_event2()

    # function that goes back to Enrolling frame screen
    def go_back_event2(self):
        self.unbind("<Return>")
        self.unbind("<space>")
        self.unbind("<Up>")
        self.unbind("<Down>")
        self.unbind("<Home>")
        self.unbind("<End>")
        self.bind("<Control-Tab>", lambda event: self.tab_switcher())
        self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_event())
        self.switch_tab()
        lang = self.language_menu.get()
        self.tabview.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 85))
        self.tabview.tab(self.enroll_tab).grid_columnconfigure(1, weight=2)
        self.tabview.tab(self.search_tab).grid_columnconfigure(1, weight=2)
        self.search_scrollbar.grid_columnconfigure(1, weight=2)
        self.tabview.tab(self.other_tab).grid_columnconfigure(1, weight=2)
        self.t_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(0, 0), pady=(0, 20))
        self.t_buttons_frame.grid_columnconfigure(1, weight=2)
        self.title_enroll.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
        self.e_classes.grid(row=1, column=1, padx=(0, 188), pady=(0, 0))
        self.e_classes_entry.grid(row=1, column=1, padx=(0, 0), pady=(0, 0))
        if lang == "English":
            self.e_section.grid(row=2, column=1, padx=(0, 199), pady=(20, 0))
        elif lang == "Español":
            self.e_section.grid(row=2, column=1, padx=(0, 202), pady=(20, 0))
        self.e_section_entry.grid(row=2, column=1, padx=(0, 0), pady=(20, 0))
        self.e_semester.grid(row=3, column=1, padx=(0, 211), pady=(20, 0))
        self.e_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0))
        self.register.grid(row=4, column=1, padx=(0, 60), pady=(15, 0))
        self.drop.grid(row=4, column=1, padx=(140, 0), pady=(15, 0))
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
            self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
            self.search_next_page.grid_forget()
        self.title_menu.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
        self.explanation_menu.grid(row=1, column=1, padx=(0, 0), pady=(0, 0), sticky="n")
        if lang == "English":
            self.menu.grid(row=2, column=1, padx=(0, 184), pady=(10, 0))
        elif lang == "Español":
            self.menu.grid(row=2, column=1, padx=(0, 194), pady=(10, 0))
        self.menu_entry.grid(row=2, column=1, padx=(0, 0), pady=(10, 0))
        self.menu_semester.grid(row=3, column=1, padx=(0, 211), pady=(20, 0))
        self.menu_semester_entry.grid(row=3, column=1, padx=(0, 0), pady=(20, 0))
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
        if not self.in_multiple_screen:
            self.my_classes_frame.grid_forget()
            self.modify_classes_frame.grid_forget()
            self.back_my_classes.grid_forget()
            self.after(0, self.destroy_enrolled_frame)
        self.in_multiple_screen = False

    def load_language(self, lang):
        # Check if the translations for the requested language are in the cache
        if lang in self.translations_cache:
            # If they are, return the cached translations without loading the file again
            return self.translations_cache[lang]

        # If the translations are not in the cache, identify the filename
        filename = None
        if lang == "English":
            filename = "translations/english.json"
        elif lang == "Español":
            filename = "translations/spanish.json"

        # Load the translations from the file and store them in the cache
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    translations = json.load(f)
                self.translations_cache[lang] = translations
                return translations
            except Exception as e:
                print("An error occurred: ", e)
                if lang == "English":
                    messagebox.showerror("Error",
                                         "A critical error occurred while loading the languages.\n"
                                         "Might need to reinstall the program.\n\n"
                                         "The application will now exit.")
                elif lang == "Español":
                    messagebox.showerror("Error",
                                         "Ocurrió un error crítico al cargar los idiomas.\n"
                                         "Puede ser que sea necesario reinstalar el programa.\n\n"
                                         "La aplicación se cerrará ahora.")
                # Exit the application
                self.destroy()
                sys.exit(1)

        # If the language is not supported, return an empty dictionary or raise an exception
        return {}

    def update_table_headers_tooltips(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        tooltip_messages = {
            translation["sec"]: translation["tooltip_sec"],
            translation["m"]: translation["tooltip_m"],
            translation["cred"]: translation["tooltip_cred"],
            translation["days"]: translation["tooltip_days"],
            translation["times"]: translation["tooltip_times"],
            translation["av"]: translation["tooltip_av"],
            translation["instructor"]: translation["tooltip_instructor"],
        }
        new_headers = [translation["sec"], translation["m"], translation["cred"],
                       translation["days"], translation["times"], translation["av"],
                       translation["instructor"]]

        for display_class, table, semester, show in self.class_table_pairs:
            table.update_headers(new_headers)
            for i, new_header in enumerate(new_headers):
                tooltip_message = tooltip_messages[new_header]
                header_cell = table.get_cell(0, i)
                if header_cell in self.table_tooltips:
                    self.table_tooltips[header_cell].configure(message=tooltip_message)

    # function for changing language
    def change_language_event(self, lang):
        translation = self.load_language(lang)
        appearance = self.appearance_mode_optionemenu.get()
        self.focus_set()
        self.status_button.configure(text=translation["status_button"])
        self.help_button.configure(text=translation["help_button"])
        self.scaling_label.configure(text=translation["option_label"])
        self.intro_box.configure(state="normal")
        self.intro_box.delete("1.0", "end")
        self.intro_box.insert("0.0", translation["intro_box"])
        self.intro_box.configure(state="disabled")
        self.language_menu_tooltip.configure(message=translation["language_tooltip"])
        self.appearance_mode_optionemenu.configure(values=[translation["light"], translation["dark"],
                                                           translation["default"]])
        if appearance == "Dark" or appearance == "Oscuro":
            self.appearance_mode_optionemenu.set(translation["dark"])
        elif appearance == "Light" or appearance == "Claro":
            self.appearance_mode_optionemenu.set(translation["light"])
        elif appearance == "System" or appearance == "Sistema":
            self.appearance_mode_optionemenu.set(translation["default"])
        self.introduction.configure(text=translation["introduction"])
        self.host.configure(text=translation["host"])
        self.host_entry.configure(placeholder_text=translation["host_placeholder"])
        self.log_in.configure(text=translation["log_in"])
        self.host_tooltip.configure(message=translation["host_tooltip"])
        self.status_tooltip.configure(message=translation["status_tooltip"])
        self.scaling_label_tooltip.configure(message=translation["option_label_tooltip"])
        self.help_tooltip.configure(message=translation["help_tooltip"])
        for entry in [self.host_entry, self.intro_box]:
            entry.lang = lang
        if lang == "English":
            self.host.grid(row=2, column=1, padx=(0, 170), pady=(15, 15))
        elif lang == "Español":
            self.host.grid(row=2, column=1, padx=(0, 190), pady=(15, 15))
        self.intro_box.reset_autoscroll()
        if self.status is not None and self.status.winfo_exists():
            self.status.title(translation["status"])
            self.status_title.configure(text=translation["status_title"])
            self.version.configure(text=translation["app_version"])
            self.feedback_send.configure(text=translation["feedback"])
            self.check_update_text.configure(text=translation["update_title"])
            self.check_update_btn.configure(text=translation["update"])
            self.website.configure(text=translation["website"])
            self.website_link.configure(text=translation["link"])
            self.notaso.configure(text=translation["notaso_title"])
            self.notaso_link.configure(text=translation["notaso_link"])
            self.faq_text.configure(text=translation["faq"])
            self.qa_table = [[translation["q"], translation["a"]],
                             [translation["q1"], translation["a1"]],
                             [translation["q2"], translation["a2"]]]
            self.faq.configure(values=self.qa_table)
            self.feedback_text.lang = lang
        if self.help is not None and self.help.winfo_exists():
            self.help.title(translation["help"])
            self.help_title.configure(text=translation["help"])
            self.notice.configure(text=translation["notice"])
            self.searchbox_text.configure(text=translation["searchbox_title"])
            self.search_box.configure(placeholder_text=translation["searchbox"])
            self.curriculum_text.configure(text=translation["curriculums_title"])
            self.curriculum.set(translation["dep"])
            self.curriculum.configure(values=[translation["dep"], translation["acc"], translation["finance"],
                                              translation["management"], translation["mark"], translation["g_biology"],
                                              translation["h_biology"], translation["c_science"], translation["it"],
                                              translation["s_science"], translation["physical"], translation["elec"],
                                              translation["equip"], translation["peda"], translation["che"],
                                              translation["nur"], translation["office"], translation["engi"]])
            if lang == "English":
                self.curriculum.pack(pady=(5, 0))
            elif lang == "Español":
                self.curriculum.pack(pady=(5, 20))
            self.terms_text.configure(text=translation["terms_title"])
            self.terms = [[translation["terms_year"], translation["terms_term"]],
                          ["2019", "B91, B92, B93"],
                          ["2020", "C01, C02, C03"],
                          ["2021", "C11, C12, C13"],
                          ["2022", "C21, C22, C23"],
                          ["2023", "C31, C32, C33"],
                          [translation["semester"], translation["seasons"]]]
            self.terms_table.configure(values=self.terms)
            self.keybinds_text.configure(text=translation["keybinds_title"])
            self.keybinds = [[translation["keybind"], translation["key_function"]],
                             ["<Return> / <Enter>", translation["return"]],
                             ["<Escape>", translation["escape"]],
                             ["<Ctrl-BackSpace>", translation["ctrl_backspace"]],
                             ["<Arrow-Keys>", translation["arrow_keys"]],
                             ["<SpaceBar>", translation["space_bar"]],
                             ["<Ctrl-Tab>", translation["ctrl_tab"]],
                             ["<Ctrl-Space>", translation["ctrl_space"]],
                             ["<Ctrl-C>", translation["ctrl_c"]],
                             ["<Ctrl-V>", translation["ctrl_v"]],
                             ["<Ctrl-X>", translation["ctrl_x"]],
                             ["<Ctrl-Z>", translation["ctrl_z"]],
                             ["<Ctrl-Y>", translation["ctrl_y"]],
                             ["<Ctrl-A>", translation["ctrl_a"]],
                             ["<Right-Click>", translation["mouse_2"]],
                             ["<Home>", translation["home"]],
                             ["<End>", translation["end"]],
                             ["<Alt-F4>", translation["alt_f4"]]]
            self.keybinds_table.configure(values=self.keybinds)
            self.skip_auth_text.configure(text=translation["skip_auth_text"])
            self.skip_auth_switch.configure(text=translation["skip_auth_switch"])
            self.files_text.configure(text=translation["files_title"])
            self.files.configure(text=translation["files_button"])
            self.disable_idle_text.configure(text=translation["idle_title"])
            self.disable_idle.configure(text=translation["idle"])
            self.disable_audio_text.configure(text=translation["audio_title"])
            self.disable_audio_val.configure(text=translation["audio"])
            self.fix_text.configure(text=translation["fix_title"])
            self.fix.configure(text=translation["fix"])
            self.search_box.lang = lang
        if self.init_multiple:
            self.update_table_headers_tooltips()
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
            self.explanation_menu.configure(text=translation["explanation_menu"])
            self.title_menu.configure(text=translation["title_menu"])
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
            self.title_multiple.configure(text=translation["title_multiple"])
            self.m_class.configure(text=translation["class"])
            self.m_section.configure(text=translation["section"])
            self.m_semester.configure(text=translation["semester"])
            self.m_choice.configure(text=translation["choice"])
            self.back_multiple.configure(text=translation["back"])
            self.submit_multiple.configure(text=translation["submit"])
            for i in range(6):
                self.m_register_menu[i].configure(values=[translation["register"], translation["drop"]])
                if self.m_register_menu[i].get() == "Choose":
                    self.m_register_menu[i].set(translation["choose"])
                elif self.m_register_menu[i].get() == "Register":
                    self.m_register_menu[i].set(translation["register"])
                elif self.m_register_menu[i].get() == "Drop":
                    self.m_register_menu[i].set(translation["drop"])
            self.auto_enroll.configure(text=translation["auto_enroll"])
            self.save_data.configure(text=translation["save_data"])
            self.register_tooltip.configure(message=translation["register_tooltip"])
            self.drop_tooltip.configure(message=translation["drop_tooltip"])
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
            for entry in [self.e_classes_entry, self.e_section_entry, self.s_classes_entry, self.m_classes_entry,
                          self.m_section_entry]:
                if isinstance(entry, list):
                    for sub_entry in entry:
                        sub_entry.lang = lang
                else:
                    entry.lang = lang
            if self.table is not None:
                self.previous_button.configure(text=translation["previous"])
                self.next_button.configure(text=translation["next"])
                self.remove_button.configure(text=translation["remove"])
                self.download_pdf.configure(text=translation["pdf_save_as"])
                self.table_count_tooltip.configure(message=translation["table_count_tooltip"])
                self.previous_button_tooltip.configure(message=translation["previous_tooltip"])
                self.next_button_tooltip.configure(message=translation["next_tooltip"])
                self.remove_button_tooltip.configure(message=translation["remove_tooltip"])
                self.download_pdf_tooltip.configure(message=translation["download_pdf_tooltip"])
            if self.enroll_tab != translation["enroll_tab"]:
                self.after(1000, self.rename_tabs)

    def rename_tabs(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.renamed_tabs = self.tabview.get()
        self.tabview.rename(self.enroll_tab, translation["enroll_tab"])
        self.enroll_tab = translation["enroll_tab"]
        self.tabview.rename(self.search_tab, translation["search_tab"])
        self.search_tab = translation["search_tab"]
        self.tabview.rename(self.other_tab, translation["other_tab"])
        self.other_tab = translation["other_tab"]

    def change_semester(self):
        self.focus_set()
        self.detect_change()
        for i in range(1, self.a_counter + 1):
            self.m_semester_entry[i].configure(state="normal")
            self.m_semester_entry[i].set("")
            self.m_semester_entry[i].set(self.m_semester_entry[0].get())
            self.m_semester_entry[i].configure(state="disabled")

    def keybind_auto_enroll(self):
        if self.loading_screen is not None and self.loading_screen.winfo_exists():
            return
        self.auto_enroll.select()
        self.auto_enroll_event_handler()

    def auto_enroll_event_handler(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.focus_set()
        idle = self.cursor.execute("SELECT idle FROM user_data").fetchone()
        if idle[0] != "Disabled":
            if self.auto_enroll.get() == "on":
                msg = CTkMessagebox(master=self, title=translation["auto_enroll"],
                                    message=translation["auto_enroll_prompt"],
                                    icon="images/submit.png",
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "use_default", "use_default"))
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
            if not self.disable_audio:
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
                self.automation_preparations()
                if self.auto_enroll.get() == "on":
                    self.auto_enroll_bool = True
                    if asyncio.run(self.test_connection(lang)) and self.check_server() and self.check_format():
                        if TeraTermUI.checkIfProcessRunning("ttermpro"):
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.wait_for_window()
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            if "OPCIONES PARA EL ESTUDIANTE" in text_output or "BALANCE CTA" in text_output or \
                                    "PANTALLAS MATRICULA" in text_output or "PANTALLAS GENERALES" in text_output or \
                                    "LISTA DE SECCIONES" in text_output:
                                if "LISTA DE SECCIONES" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                ctypes.windll.user32.BlockInput(False)
                                self.automate_copy_class_data()
                                ctypes.windll.user32.BlockInput(True)
                                copy = pyperclip.paste()
                                turno_index = copy.find("TURNO MATRICULA:")
                                sliced_text = copy[turno_index:]
                                parts = sliced_text.split(":", 1)
                                match = re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", parts[1])
                                if match:
                                    date_time_string = match.group()
                                    date_time_string += " AM"
                                else:
                                    self.after(100, self.show_error_message, 300, 215,
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
                                is_time_difference_within_8_hours = \
                                    timedelta(hours=8, minutes=15) >= time_difference >= timedelta()
                                is_more_than_one_day = (your_date.date() - current_date.date() > timedelta(days=1))
                                is_current_time_ahead = current_date.time() > your_date.time()
                                is_current_time_24_hours_ahead = time_difference >= timedelta(hours=-24)
                                # Comparing Dates
                                if (is_same_date and is_time_difference_within_8_hours) or \
                                        (is_next_date and is_time_difference_within_8_hours):
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
                                    if is_current_time_24_hours_ahead:
                                        self.running_countdown = customtkinter.BooleanVar()
                                        self.running_countdown.set(True)
                                        self.started_auto_enroll = True
                                        self.after(0, self.submit_multiple_event_handler)
                                        self.after(0, self.end_countdown)
                                    else:
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["date_past"])
                                        self.auto_enroll_bool = False
                                        self.auto_enroll.deselect()
                                elif (is_future_date or is_more_than_one_day) or \
                                        (is_same_date and not is_time_difference_within_8_hours) or \
                                        (is_next_date and not is_time_difference_within_8_hours):
                                    self.after(100, self.show_error_message, 320, 235,
                                               translation["date_not_within_8_hours"])
                                    self.auto_enroll_bool = False
                                    self.auto_enroll.deselect()
                                if ("INVALID ACTION" in text_output and "PANTALLAS MATRICULA" in text_output) or \
                                        ("LISTA DE SECCIONES" in text_output and "COURSE NOT" in text_output):
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(0, self.bring_back_timer_window)
                            else:
                                self.after(100, self.show_error_message, 300, 215,
                                           translation["failed_to_find_date"])
                                self.auto_enroll.deselect()
                                self.auto_enroll_bool = False
                        else:
                            self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
                            self.auto_enroll_bool = False
                            self.auto_enroll.deselect()
                elif self.auto_enroll.get() == "off":
                    self.countdown_running = False
                    self.auto_enroll_bool = False
                    self.after(0, self.disable_enable_gui)
                    if hasattr(self, "running_countdown") and self.running_countdown \
                            is not None and self.running_countdown.get():
                        self.after(0, self.end_countdown)
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
                self.log_error(e)
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                self.after(100, self.show_sidebar_windows)
                if self.error_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                        CTkMessagebox(master=self, title=translation["server_maintenance_title"],
                                      message=translation["server_maintenance"],
                                      icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(0, error_automation)
                self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
                ctypes.windll.user32.BlockInput(False)

    # Starts the countdown on when the auto-enroll process will occur
    def countdown(self, your_date):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        puerto_rico_tz = pytz.timezone("America/Puerto_Rico")
        current_date = datetime.now(puerto_rico_tz)
        time_difference = your_date - current_date
        total_seconds = time_difference.total_seconds()
        if self.running_countdown.get():
            if not TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                self.forceful_end_countdown()
            if total_seconds <= 0:
                # Call enrollment function here
                self.timer_label.configure(text=translation["performing_auto_enroll"], text_color="#32CD32",
                                           font=customtkinter.CTkFont(size=17))
                self.timer_label.pack(pady=30)
                self.timer_window.lift()
                self.timer_window.focus_force()
                self.timer_window.attributes("-topmost", 1)
                self.cancel_button.pack_forget()
                self.started_auto_enroll = True
                self.after(5000, self.submit_multiple_event_handler)
                self.after(5000, self.end_countdown)
                if TeraTermUI.window_exists(translation["exit"]):
                    self.after(5000, self.exit.close_messagebox)
                return
            else:
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                # If more than an hour remains
                if hours > 0:
                    if seconds > 0:
                        minutes += 1
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
                        self.timer_window.after(seconds_until_next_minute * 1000, lambda: self.countdown(your_date)
                                                if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT")
                                                else self.forceful_end_countdown())

                else:  # When there's less than an hour remaining
                    # If there's a part of minute left, consider it as a whole minute
                    if seconds > 0:
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
                        self.timer_window.after(seconds_until_next_minute * 1000, lambda: self.countdown(your_date)
                                                if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT")
                                                else self.forceful_end_countdown())
                    else:  # update every second if there's less than or equal to 60 seconds left
                        self.timer_window.after(1000, lambda: self.countdown(your_date)
                                                if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT")
                                                else self.forceful_end_countdown())

    def end_countdown(self):
        self.auto_enroll_bool = False
        self.countdown_running = False
        self.running_countdown.set(False)  # Stop the countdown
        if self.timer_window and self.timer_window.winfo_exists():
            self.timer_window.destroy()  # Destroy the countdown window
        self.auto_enroll.deselect()
        self.disable_enable_gui()

    def forceful_end_countdown(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.end_countdown()
        if not self.disable_audio:
            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
        CTkMessagebox(master=self, title=translation["automation_error_title"], icon="info",
                      message=translation["end_countdown"], button_width=380)

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
        self.timer_window = SmoothFadeToplevel(fade_duration=15)
        self.timer_window.title(translation["auto_enroll"])
        self.timer_window.geometry(f"{width}x{height}+{int(x) + 130}+{int(y)}")
        self.timer_window.attributes("-alpha", 0.90)
        self.timer_window.resizable(False, False)
        self.timer_window.iconbitmap(self.icon_path)
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
        TeraTermUI.enable_entries(self)
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

    @staticmethod
    def get_window_monitor(window_x, window_y, window_width=None, window_height=None):
        from screeninfo import get_monitors

        # If width and height are not provided, assume a small window size
        if window_width is None:
            window_width = 10
        if window_height is None:
            window_height = 10

        for monitor in get_monitors():
            corners = [
                (window_x, window_y),
                (window_x + window_width, window_y),
                (window_x, window_y + window_height),
                (window_x + window_width, window_y + window_height)
            ]

            for (x, y) in corners:
                if monitor.x <= x <= monitor.x + monitor.width and \
                        monitor.y <= y <= monitor.y + monitor.height:
                    return monitor

        return None

    def move_window(self):
        try:
            window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
        except IndexError:
            print("Window not found.")
            return
        # Get Tkinter window's current position
        tk_x = self.winfo_x()
        tk_y = self.winfo_y()
        # Identify which monitor the Tkinter window and Tera Term window are in
        tk_monitor = TeraTermUI.get_window_monitor(tk_x, tk_y, self.winfo_width(), self.winfo_height())
        tera_monitor = TeraTermUI.get_window_monitor(window.left, window.top, window.width, window.height)
        print(f"Tkinter window is on monitor {tk_monitor} at position ({tk_x}, {tk_y}).")
        print(f"Tera Term window is on monitor {tera_monitor} at position ({window.left}, {window.top}).")
        # If they're not on the same monitor, don't move the Tera Term window
        if tk_monitor != tera_monitor:
            print("Windows are on different monitors. Not moving Tera Term window.")
            return
        # Calculate the target position for the Tera Term window with an offset
        offset_x = 10
        offset_y = 10
        target_x = tk_x + offset_x
        target_y = tk_y + offset_y
        # Get current position of the Tera Term window
        current_x, current_y = window.left, window.top
        # Step size and delay time
        step_size = 25
        delay_time = 0.01
        # Move the Tera Term window
        while (current_x, current_y) != (target_x, target_y):
            if current_x < target_x:
                current_x += min(step_size, target_x - current_x)
            elif current_x > target_x:
                current_x -= min(step_size, current_x - target_x)
            if current_y < target_y:
                current_y += min(step_size, target_y - current_y)
            elif current_y > target_y:
                current_y -= min(step_size, current_y - target_y)
            window.moveTo(current_x, current_y)
            time.sleep(delay_time)

    def initialization_auth(self):
        # (Auth Screen)
        if not self.init_auth:
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            self.init_auth = True
            self.authentication_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.a_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.title_login = customtkinter.CTkLabel(master=self.authentication_frame,
                                                      text=translation["title_auth"],
                                                      font=customtkinter.CTkFont(size=20, weight="bold"))
            self.uprb_image = self.get_image("uprb")
            self.uprb_image_grid = CustomButton(self.authentication_frame, text="", image=self.uprb_image,
                                                command=self.uprb_event, fg_color="transparent", hover=False)
            self.disclaimer = customtkinter.CTkLabel(master=self.authentication_frame, text=translation["disclaimer"])
            self.username = customtkinter.CTkLabel(master=self.authentication_frame, text=translation["username"])
            self.username_entry = CustomEntry(self.authentication_frame, self, lang)
            self.username_tooltip = CTkToolTip(self.username_entry, message=translation["username_tooltip"],
                                               bg_color="#1E90FF")
            self.auth = CustomButton(master=self.a_buttons_frame, border_width=2, text=translation["authentication"],
                                     text_color=("gray10", "#DCE4EE"), command=self.auth_event_handler)
            self.back = CustomButton(master=self.a_buttons_frame, fg_color="transparent", border_width=2,
                                     text=translation["back"], hover_color="#4E4F50", text_color=("gray10", "#DCE4EE"),
                                     command=self.go_back_event)
            self.back_tooltip = CTkToolTip(self.back, message=translation["back_tooltip"], bg_color="#A9A9A9",
                                           alpha=0.90)
            self.username_entry.lang = lang
            self.title_login.bind("<Button-1>", lambda event: self.focus_set())
            self.authentication_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.a_buttons_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_event())

    def destroy_auth(self):
        if self.init_auth:
            self.init_auth = False
            self.authentication_frame.unbind("<Button-1>")
            self.a_buttons_frame.unbind("<Button-1>")
            self.title_login.unbind("<Button-1>")
            self.title_login.destroy()
            self.title_login = None
            self.uprb_image = None
            self.uprb_image_grid.destroy()
            self.uprb_image_grid = None
            self.disclaimer.destroy()
            self.disclaimer = None
            self.username.destroy()
            self.username = None
            self.username_entry.lang = None
            self.username_entry.destroy()
            self.username_entry = None
            self.username_tooltip.destroy()
            self.username_tooltip = None
            self.auth.destroy()
            self.auth = None
            self.back.destroy()
            self.back = None
            self.back_tooltip.destroy()
            self.back_tooltip = None
            self.authentication_frame.destroy()
            self.authentication_frame = None
            self.a_buttons_frame.destroy()
            self.a_buttons_frame = None

    def initialization_student(self):
        # Student Information
        if not self.init_student:
            self.init_student = True
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            self.student_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.s_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.title_student = customtkinter.CTkLabel(master=self.student_frame,
                                                        text=translation["title_security"],
                                                        font=customtkinter.CTkFont(size=20, weight="bold"))
            self.lock = self.get_image("lock")
            self.lock_grid = CustomButton(self.student_frame, text="", image=self.lock, command=self.lock_event,
                                          fg_color="transparent", hover=False)
            self.student_id = customtkinter.CTkLabel(master=self.student_frame, text=translation["student_id"])
            self.student_id_entry = CustomEntry(self.student_frame, self, lang, placeholder_text="#########", show="*")
            self.student_id_tooltip = CTkToolTip(self.student_id_entry, message=translation["student_id_tooltip"],
                                                 bg_color="#1E90FF")
            self.code = customtkinter.CTkLabel(master=self.student_frame, text=translation["code"])
            self.code_entry = CustomEntry(self.student_frame, self, lang, placeholder_text="####", show="*")
            self.code_tooltip = CTkToolTip(self.code_entry, message=translation["code_tooltip"], bg_color="#1E90FF")
            self.show = customtkinter.CTkSwitch(master=self.student_frame, text=translation["show"],
                                                command=self.show_event, onvalue="on", offvalue="off")
            self.bind("<space>", lambda event: self.spacebar_event())
            self.student_id_entry.bind("<Command-c>", lambda e: "break")
            self.student_id_entry.bind("<Control-c>", lambda e: "break")
            self.code_entry.bind("<Command-c>", lambda e: "break")
            self.code_entry.bind("<Control-c>", lambda e: "break")
            self.student_id_entry.bind("<Command-C>", lambda e: "break")
            self.student_id_entry.bind("<Control-C>", lambda e: "break")
            self.code_entry.bind("<Command-C>", lambda e: "break")
            self.code_entry.bind("<Control-C>", lambda e: "break")
            self.system = CustomButton(master=self.s_buttons_frame, border_width=2, text=translation["system"],
                                       text_color=("gray10", "#DCE4EE"), command=self.student_event_handler)
            self.back_student = CustomButton(master=self.s_buttons_frame, fg_color="transparent", border_width=2,
                                             text=translation["back"], hover_color="#4E4F50",
                                             text_color=("gray10", "#DCE4EE"), command=self.go_back_event)
            self.back_student_tooltip = CTkToolTip(self.back_student, message=translation["back_tooltip"],
                                                   bg_color="#A9A9A9", alpha=0.90)
            self.student_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.s_buttons_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.title_student.bind("<Button-1>", lambda event: self.focus_set())
            for entry in [self.student_id_entry, self.code_entry]:
                entry.lang = lang

    def destroy_student(self):
        if self.init_student:
            self.init_student = False
            self.student_frame.unbind("<Button-1>")
            self.s_buttons_frame.unbind("<Button-1>")
            self.title_student.unbind("<Button-1>")
            self.student_id_entry.unbind("<Command-c>")
            self.student_id_entry.unbind("<Control-c>")
            self.code_entry.unbind("<Command-c>")
            self.code_entry.unbind("<Control-c>")
            self.student_id_entry.unbind("<Command-C>")
            self.student_id_entry.unbind("<Control-C>")
            self.code_entry.unbind("<Command-C>")
            self.code_entry.unbind("<Control-C>")
            self.title_student.destroy()
            self.title_student = None
            self.lock = None
            self.lock_grid.destroy()
            self.lock_grid = None
            self.student_id.destroy()
            self.student_id = None
            for entry in [self.student_id_entry, self.code_entry]:
                entry.lang = None
            self.student_id_entry.destroy()
            self.student_id_entry = None
            self.student_id_tooltip.destroy()
            self.student_id_tooltip = None
            self.code.destroy()
            self.code = None
            self.code_entry.destroy()
            self.code_entry = None
            self.code_tooltip.destroy()
            self.code_tooltip = None
            self.show.destroy()
            self.show = None
            self.system.destroy()
            self.system = None
            self.back_student.destroy()
            self.back_student = None
            self.back_student_tooltip.destroy()
            self.back_student_tooltip = None
            self.student_frame.destroy()
            self.student_frame = None
            self.s_buttons_frame.destroy()
            self.s_buttons_frame = None

    def initialization_class(self):
        # Classes
        if not self.init_class:
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            self.enrolled_classes_list = {}
            self.dropped_classes_list = {}
            self.tabview = customtkinter.CTkTabview(self, corner_radius=10, command=self.switch_tab)
            self.t_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.init_class = True
            self.enroll_tab = translation["enroll_tab"]
            self.search_tab = translation["search_tab"]
            self.other_tab = translation["other_tab"]
            self.tabview.add(self.enroll_tab)
            self.tabview.add(self.search_tab)
            self.tabview.add(self.other_tab)

            # First Tab
            self.title_enroll = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab),
                                                       text=translation["title_enroll"],
                                                       font=customtkinter.CTkFont(size=20, weight="bold"))
            self.e_classes = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab), text=translation["class"])
            self.e_classes_entry = CustomEntry(self.tabview.tab(self.enroll_tab), self, lang,
                                               placeholder_text="MATE3032")
            self.e_section = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab),
                                                    text=translation["section"])
            self.e_section_entry = CustomEntry(self.tabview.tab(self.enroll_tab), self, lang, placeholder_text="LM1")
            self.e_semester = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab),
                                                     text=translation["semester"])
            self.e_semester_entry = CustomComboBox(self.tabview.tab(self.enroll_tab), self,
                                                   values=["C31", "C32", "C33", "C41", "C42", "C43"],
                                                   command=lambda value: self.set_focus())
            self.e_semester_entry.set(self.DEFAULT_SEMESTER)
            self.radio_var = tk.StringVar()
            self.register = customtkinter.CTkRadioButton(master=self.tabview.tab(self.enroll_tab),
                                                         text=translation["register"], value="register",
                                                         variable=self.radio_var, command=self.set_focus)
            self.register_tooltip = CTkToolTip(self.register, message=translation["register_tooltip"])
            self.drop = customtkinter.CTkRadioButton(master=self.tabview.tab(self.enroll_tab), text=translation["drop"],
                                                     value="drop", variable=self.radio_var,
                                                     command=self.set_focus)
            self.drop_tooltip = CTkToolTip(self.drop, message=translation["drop_tooltip"])
            self.register.select()
            self.tabview.tab(self.enroll_tab).bind("<Button-1>", lambda event: self.focus_set())
            self.title_enroll.bind("<Button-1>", lambda event: self.focus_set())

            # Second Tab
            self.search_scrollbar = customtkinter.CTkScrollableFrame(master=self.tabview.tab(self.search_tab),
                                                                     corner_radius=10)
            self.title_search = customtkinter.CTkLabel(self.search_scrollbar,
                                                       text=translation["title_search"],
                                                       font=customtkinter.CTkFont(size=20, weight="bold"))
            self.s_classes = customtkinter.CTkLabel(self.search_scrollbar, text=translation["class"])
            self.s_classes_entry = CustomEntry(self.search_scrollbar, self, lang, placeholder_text="MATE3032",
                                               width=80)
            self.s_semester = customtkinter.CTkLabel(self.search_scrollbar, text=translation["semester"])
            self.s_semester_entry = CustomComboBox(self.search_scrollbar, self,
                                                   values=["C01", "C02", "C03", "C11", "C12", "C13", "C21", "C22",
                                                           "C23", "C31", "C32", "C33", "C41", "C42", "C43"],
                                                   command=lambda value: self.set_focus(), width=80)
            self.s_semester_entry.set(self.DEFAULT_SEMESTER)
            self.show_all = customtkinter.CTkCheckBox(self.search_scrollbar, text=translation["show_all"],
                                                      onvalue="on", offvalue="off", command=self.set_focus)
            self.show_all_tooltip = CTkToolTip(self.show_all, message=translation["show_all_tooltip"],
                                               bg_color="#1E90FF")
            self.search_next_page = CustomButton(master=self.search_scrollbar, fg_color="transparent", border_width=2,
                                                 text=translation["search_next_page"], text_color=("gray10", "#DCE4EE"),
                                                 hover_color="#4E4F50", command=self.go_next_search_handler, width=85)
            self.search_next_page_tooltip = CTkToolTip(self.search_next_page,
                                                       message=translation["search_next_page_tooltip"],
                                                       bg_color="#A9A9A9", alpha=0.90)
            self.tabview.tab(self.search_tab).bind("<Button-1>", lambda event: self.focus_set())
            self.search_scrollbar.bind("<Button-1>", lambda event: self.focus_set())
            self.title_search.bind("<Button-1>", lambda event: self.focus_set())
            self.s_classes.bind("<Button-1>", lambda event: self.focus_set())
            self.s_semester.bind("<Button-1>", lambda event: self.focus_set())

            # Third Tab
            self.title_menu = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
                                                     text=translation["title_menu"],
                                                     font=customtkinter.CTkFont(size=20, weight="bold"))
            self.explanation_menu = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
                                                           text=translation["explanation_menu"])
            self.menu = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab), text=translation["menu"])
            self.menu_entry = CustomComboBox(self.tabview.tab(self.other_tab), self,
                                             values=[translation["SRM"], translation["004"], translation["1GP"],
                                                     translation["118"], translation["1VE"], translation["3DD"],
                                                     translation["409"], translation["683"], translation["1PL"],
                                                     translation["4CM"], translation["4SP"], translation["SO"]],
                                             command=lambda value: self.set_focus(), width=141)
            self.menu_entry.set(translation["SRM"])
            self.menu_semester = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
                                                        text=translation["semester"])
            self.menu_semester_entry = CustomComboBox(self.tabview.tab(self.other_tab), self,
                                                      values=["C01", "C02", "C03", "C11", "C12", "C13", "C21", "C22",
                                                              "C23", "C31", "C32", "C33", "C41", "C42", "C43"],
                                                      command=lambda value: self.set_focus(), width=141)
            self.menu_semester_entry.set(self.DEFAULT_SEMESTER)
            self.menu_submit = CustomButton(master=self.tabview.tab(self.other_tab), border_width=2,
                                            text=translation["submit"], text_color=("gray10", "#DCE4EE"),
                                            command=self.option_menu_event_handler, width=141)
            self.go_next_1VE = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text=translation["go_next"],
                                            text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                            command=self.go_next_page_handler, width=100)
            self.go_next_1GP = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text=translation["go_next"],
                                            text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                            command=self.go_next_page_handler, width=100)
            self.go_next_409 = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text=translation["go_next"],
                                            text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                            command=self.go_next_page_handler, width=100)
            self.go_next_683 = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text=translation["go_next"], hover_color="#4E4F50",
                                            text_color=("gray10", "#DCE4EE"),
                                            command=self.go_next_page_handler, width=100)
            self.go_next_4CM = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text=translation["go_next"],
                                            text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                            command=self.go_next_page_handler, width=100)
            self.tabview.tab(self.other_tab).bind("<Button-1>", lambda event: self.focus_set())
            self.title_menu.bind("<Button-1>", lambda event: self.focus_set())
            self.explanation_menu.bind("<Button-1>", lambda event: self.focus_set())

            # Bottom Buttons
            self.back_classes = CustomButton(master=self.t_buttons_frame, fg_color="transparent", border_width=2,
                                             text=translation["back"], hover_color="#4E4F50",
                                             text_color=("gray10", "#DCE4EE"), command=self.go_back_event)
            self.back_classes_tooltip = CTkToolTip(self.back_classes, alpha=0.90, message=translation["back_tooltip"],
                                                   bg_color="#A9A9A9")
            self.submit = CustomButton(master=self.tabview.tab(self.enroll_tab), border_width=2,
                                       text=translation["submit"], text_color=("gray10", "#DCE4EE"),
                                       command=self.submit_event_handler)
            self.search = CustomButton(self.search_scrollbar, border_width=2, text=translation["search"],
                                       text_color=("gray10", "#DCE4EE"), command=self.search_event_handler)
            self.show_classes = CustomButton(master=self.t_buttons_frame, border_width=2,
                                             text=translation["show_my_classes"],
                                             text_color=("gray10", "#DCE4EE"),
                                             command=self.my_classes_event_handler)
            self.show_classes_tooltip = CTkToolTip(self.show_classes, message=translation["show_classes_tooltip"],
                                                   bg_color="#1E90FF")
            self.multiple = CustomButton(master=self.t_buttons_frame, fg_color="transparent", border_width=2,
                                         text=translation["multiple"], hover_color="#4E4F50",
                                         text_color=("gray10", "#DCE4EE"), command=self.multiple_classes_event)
            self.multiple_tooltip = CTkToolTip(self.multiple, message=translation["multiple_tooltip"],
                                               bg_color="blue")
            self.t_buttons_frame.bind("<Button-1>", lambda event: self.focus_set())
            for entry in [self.e_classes_entry, self.e_section_entry, self.s_classes_entry]:
                entry.lang = lang
        else:
            self.search_next_page.grid_forget()
            self.search.configure(width=141)
            self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
            self.go_next_1VE.grid_forget()
            self.go_next_1GP.grid_forget()
            self.go_next_409.grid_forget()
            self.go_next_683.grid_forget()
            self.go_next_4CM.grid_forget()
            self.menu_submit.configure(width=140)
            self.menu_submit.grid(row=5, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
            self._1VE_screen = False
            self._1GP_screen = False
            self._409_screen = False
            self._683_screen = False
            self._4CM_screen = False
            self.search_next_page_status = False

    def initialization_multiple(self):
        # Multiple Classes Enrollment
        if not self.init_multiple:
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            self.init_multiple = True
            self.m_num_class = []
            self.m_classes_entry = []
            self.m_section_entry = []
            self.m_semester_entry = []
            self.m_register_menu = []
            self.placeholder_texts_classes = ["ESPA3101", "INGL3101", "BIOL3011", "MATE3001", "CISO3121", "HUMA3101"]
            self.placeholder_texts_sections = ["LM1", "KM1", "KH1", "LH1", "KN1", "LN1"]
            self.multiple_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.m_button_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.save_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.auto_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.title_multiple = customtkinter.CTkLabel(master=self.multiple_frame,
                                                         text=translation["title_multiple"],
                                                         font=customtkinter.CTkFont(size=20, weight="bold"))
            self.m_class = customtkinter.CTkLabel(master=self.multiple_frame, text=translation["class"])
            self.m_section = customtkinter.CTkLabel(master=self.multiple_frame, text=translation["section"])
            self.m_semester = customtkinter.CTkLabel(master=self.multiple_frame, text=translation["semester"])
            self.m_choice = customtkinter.CTkLabel(master=self.multiple_frame, text=translation["choice"])
            for i in range(6):
                self.m_num_class.append(customtkinter.CTkLabel(master=self.multiple_frame, text=f"{i + 1}."))
                self.m_classes_entry.append(CustomEntry(self.multiple_frame, self, lang,
                                                        placeholder_text=self.placeholder_texts_classes[i]))
                self.m_section_entry.append(CustomEntry(self.multiple_frame, self, lang,
                                                        placeholder_text=self.placeholder_texts_sections[i]))
                self.m_semester_entry.append(CustomComboBox(self.multiple_frame, self,
                                                            values=["C31", "C32", "C33", "C41", "C42", "C43"],
                                                            command=lambda value: self.change_semester()))
                self.m_semester_entry[i].set(self.DEFAULT_SEMESTER)
                self.m_register_menu.append(customtkinter.CTkOptionMenu(master=self.multiple_frame,
                                                                        values=[translation["register"],
                                                                                translation["drop"]],
                                                                        command=lambda value: self.detect_change()))
                self.m_register_menu[i].set(translation["choose"])
            self.m_add = CustomButton(master=self.m_button_frame, border_width=2, text="+",
                                      text_color=("gray10", "#DCE4EE"), command=self.add_event, height=40, width=50,
                                      fg_color="blue")
            self.m_add_tooltip = CTkToolTip(self.m_add, message=translation["add_tooltip"], bg_color="blue")
            self.m_remove = CustomButton(master=self.m_button_frame, border_width=2, text="-",
                                         text_color=("gray10", "#DCE4EE"), command=self.remove_event, height=40,
                                         width=50, fg_color="red", hover_color="darkred",
                                         state="disabled")
            self.m_remove_tooltip = CTkToolTip(self.m_remove, message=translation["m_remove_tooltip"], bg_color="red")
            self.back_multiple = CustomButton(master=self.m_button_frame, fg_color="transparent", border_width=2,
                                              text=translation["back"], height=40, width=70, hover_color="#4E4F50",
                                              text_color=("gray10", "#DCE4EE"), command=self.go_back_event2)
            self.back_multiple_tooltip = CTkToolTip(self.back_multiple, alpha=0.90,
                                                    message=translation["back_multiple"], bg_color="#A9A9A9")
            self.submit_multiple = CustomButton(master=self.m_button_frame, border_width=2, text=translation["submit"],
                                                text_color=("gray10", "#DCE4EE"),
                                                command=self.submit_multiple_event_handler, height=40, width=70)
            self.save_data = customtkinter.CTkCheckBox(master=self.save_frame, text=translation["save_data"],
                                                       command=self.save_classes, onvalue="on", offvalue="off")
            self.save_data_tooltip = CTkToolTip(self.save_data, message=translation["save_data_tooltip"],
                                                bg_color="#1E90FF")
            self.auto_enroll = customtkinter.CTkSwitch(master=self.auto_frame, text=translation["auto_enroll"],
                                                       onvalue="on", offvalue="off",
                                                       command=self.auto_enroll_event_handler)
            self.auto_enroll_tooltip = CTkToolTip(self.auto_enroll, message=translation["auto_enroll_tooltip"],
                                                  bg_color="#1E90FF")
            self.multiple_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.m_button_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.save_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.auto_frame.bind("<Button-1>", lambda event: self.focus_set())
            for entry in [self.m_classes_entry, self.m_section_entry]:
                for sub_entry in entry:
                    sub_entry.lang = lang
        self.load_saved_classes()

    # saves the information to the database when the app closes
    def save_user_data(self, include_exit=True):
        # Define the values for each field
        field_values = {
            "host": "uprbay.uprb.edu",
            "language": self.language_menu.get(),
            "appearance": self.appearance_mode_optionemenu.get(),
            "scaling": self.scaling_slider.get(),
            "exit": self.checkbox_state,
        }
        for field, value in field_values.items():
            # Skip 'exit' field if include_exit is False
            if field == "exit" and not include_exit:
                continue
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
        translation = self.load_language(lang)
        if save == "on":
            # Clear existing data from the table
            self.cursor.execute("DELETE FROM save_classes")
            self.connection.commit()
            is_empty = False  # Variable to track if any entry is empty
            is_invalid_format = False  # Variable to track if any entry has incorrect format
            # Iterate over the added entries based on self.a_counter
            for index in range(self.a_counter + 1):
                # Get the values from the entry fields and option menus
                class_value = self.m_classes_entry[index].get().upper()
                section_value = self.m_section_entry[index].get().upper()
                semester_value = self.m_semester_entry[index].get().upper()
                register_value = self.m_register_menu[index].get()
                if not class_value or not section_value or not semester_value or register_value in ("Choose", "Escoge"):
                    is_empty = True  # Set the flag if any field is empty or register is not selected
                elif (not re.fullmatch("^[A-Z]{4}[0-9]{4}$", class_value, flags=re.IGNORECASE) or
                      not re.fullmatch("^[A-Z]{2}[A-Z0-9]$", section_value, flags=re.IGNORECASE) or
                      not re.fullmatch("^[A-Z][0-9]{2}$", semester_value, flags=re.IGNORECASE)):
                    is_invalid_format = True  # Set the flag if any field has incorrect format
                else:
                    # Perform the insert operation
                    self.cursor.execute("INSERT INTO save_classes (class, section, semester, action, 'check')"
                                        " VALUES (?, ?, ?, ?, ?)",
                                        (class_value, section_value, semester_value, register_value, "Yes"))
                    self.connection.commit()
            if is_empty:
                self.show_error_message(330, 255, translation["failed_saved_lack_info"])
                self.save_data.deselect()
            elif is_invalid_format:
                self.show_error_message(330, 255, translation["failed_saved_invalid_info"])
                self.save_data.deselect()
            else:
                self.cursor.execute("SELECT COUNT(*) FROM save_classes")
                row_count = self.cursor.fetchone()[0]
                if row_count == 0:  # Check the counter after the loop
                    self.show_error_message(330, 255, translation["failed_saved_invalid_info"])
                    self.save_data.deselect()
                else:
                    self.show_success_message(350, 265, translation["saved_classes_success"])
        if save == "off":
            self.cursor.execute("DELETE FROM save_classes")
            self.connection.commit()

    # shows the important information window
    def show_loading_screen(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.loading_screen = customtkinter.CTkToplevel(self)
        self.loading_screen.title(translation["loading"])
        self.loading_screen.overrideredirect(True)
        self.loading_screen.grab_set()
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
        self.loading_screen.iconbitmap(self.icon_path)
        loading = customtkinter.CTkLabel(self.loading_screen, text=translation["loading"],
                                         font=customtkinter.CTkFont(size=20, weight="bold"))
        if self.auto_search or self.updating_app:
            loading.configure(text=translation["searching_exe"])
            self.auto_search = False
            self.updating_app = False
        loading.pack(pady=(48, 12))
        self.progress_bar = customtkinter.CTkProgressBar(self.loading_screen, mode="indeterminate",
                                                         height=15, width=230, indeterminate_speed=1.5)
        self.progress_bar.pack(pady=1)
        self.progress_bar.start()
        self.attributes("-disabled", True)
        TeraTermUI.disable_entries(self)
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
            self.attributes("-disabled", False)
            self.update_entries()
            self.hide_loading_screen()
            self.progress_bar.stop()
            loading_screen.destroy()
            self.loading_screen = None
        else:
            self.after(100, self.update_loading_screen, loading_screen, task_done)

    @staticmethod
    def disable_entries(container):
        for widget in container.winfo_children():
            if isinstance(widget, (tk.Entry, CustomEntry)):
                widget.configure(state="disabled")
            elif hasattr(widget, "winfo_children"):
                TeraTermUI.disable_entries(widget)

    @staticmethod
    def enable_entries(container):
        for widget in container.winfo_children():
            if isinstance(widget, (tk.Entry, CustomEntry)):
                widget.configure(state="normal")
            elif hasattr(widget, "winfo_children"):
                TeraTermUI.enable_entries(widget)

    def update_entries(self):
        if self.enrolled_rows is None and not self.countdown_running:
            TeraTermUI.enable_entries(self)
        if self.enrolled_rows is not None:
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            for row_index in range(min(len(self.mod_selection_list), self.enrolled_rows - 1)):
                mod_selection = self.mod_selection_list[row_index]
                change_section_entry = self.change_section_entries[row_index]
                if mod_selection is not None and change_section_entry is not None:
                    mod = mod_selection.get()
                    if mod == translation["section"]:
                        change_section_entry.configure(state="normal")
        if self.init_multiple:
            for i in range(1, self.a_counter + 1):
                self.m_semester_entry[i].configure(state="disabled")
        if self.help and self.help.winfo_exists():
            self.search_box.configure(state="normal")

    # function that lets user see/hide their input (hidden by default)
    def show_event(self):
        show = self.show.get()
        if show == "on":
            self.student_id_entry.unbind("<Command-c>")
            self.student_id_entry.unbind("<Control-c>")
            self.code_entry.unbind("<Command-c>")
            self.code_entry.unbind("<Control-c>")
            self.student_id_entry.unbind("<Command-C>")
            self.student_id_entry.unbind("<Control-C>")
            self.code_entry.unbind("<Command-C>")
            self.code_entry.unbind("<Control-C>")
            self.student_id_entry.configure(show="")
            self.code_entry.configure(show="")
        elif show == "off":
            self.student_id_entry.bind("<Command-c>", lambda e: "break")
            self.student_id_entry.bind("<Control-c>", lambda e: "break")
            self.code_entry.bind("<Command-c>", lambda e: "break")
            self.code_entry.bind("<Control-c>", lambda e: "break")
            self.student_id_entry.bind("<Command-C>", lambda e: "break")
            self.student_id_entry.bind("<Control-C>", lambda e: "break")
            self.code_entry.bind("<Command-C>", lambda e: "break")
            self.code_entry.bind("<Control-C>", lambda e: "break")
            self.student_id_entry.configure(show="*")
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

    @staticmethod
    def countRunningProcesses(processName):
        count = 0
        for proc in psutil.process_iter():
            try:
                if processName.lower() in proc.name().lower():
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logging.error(f"Exception occurred: {e}")
                pass
        return count

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
            self.after(100, self.show_error_message, 300, 215, translation["uprb_down"])
            return False

    # captures a screenshot of tera term and performs OCR
    def capture_screenshot(self):
        import pyautogui

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
            crop_margin = (2, 10, 10, 2)
            if self.loading_screen.winfo_exists():
                self.hide_loading_screen()
            original_position = pyautogui.position()
            screen_width, screen_height = pyautogui.size()
            offset = 30
            target_x = screen_width - offset
            target_y = screen_height - offset
            try:
                pyautogui.moveTo(target_x, target_y)
            except pyautogui.FailSafeException as e:
                print("An error occurred:", e)
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            if self.loading_screen.winfo_exists():
                self.show_loading_screen_again()
            try:
                pyautogui.moveTo(original_position.x, original_position.y)
            except pyautogui.FailSafeException as e:
                print("An error occurred:", e)
            screenshot = screenshot.crop(
                (crop_margin[0], crop_margin[1], width - crop_margin[2], height - crop_margin[3]))
            screenshot = screenshot.convert("L")
            # screenshot = screenshot.resize((screenshot.width * 2, screenshot.height * 2), resample=Image.BICUBIC)
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
                self.after(100, self.show_error_message, 320, 225, translation["tesseract_error"])
                return

    # creates pdf of the table containing for the searched class
    def create_pdf(self, data_list, classes_list, filepath, semesters_list):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak

        semester_header = None
        class_header = None
        lang = self.language_menu.get()
        pdf = SimpleDocTemplate(
            filepath,
            pagesize=letter
        )
        elems = []
        for idx, data in enumerate(data_list):
            current_class_name = classes_list[idx]  # Get the current class name
            current_semester = semesters_list[idx]  # Get the current semester
            table = Table(data)
            # Custom Colors
            blue = colors.Color(0, 0.5, 0.75)  # Lighter blue
            gray = colors.Color(0.7, 0.7, 0.7)  # Lighter gray
            # Define the table style
            style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), blue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 14),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), gray),
                ("GRID", (0, 0), (-1, -1), 1, colors.black)
            ])

            table.setStyle(style)
            # Get sample styles
            styles = getSampleStyleSheet()
            # Create and style the "Semester" header
            semester_style = styles["Heading1"]
            semester_style.alignment = 1
            if lang == "English":
                semester_header = Paragraph(f"Semester: {current_semester}", semester_style)
            elif lang == "Español":
                semester_header = Paragraph(f"Semestre: {current_semester}", semester_style)
            # Create and style the "Class" header
            class_style = styles["Heading2"]
            class_style.alignment = 1
            if lang == "English":
                class_header = Paragraph(f"<u>Class: {current_class_name}</u>", class_style)
            elif lang == "Español":
                class_header = Paragraph(f"<u>Clase: {current_class_name}</u>", class_style)
            # Add some space between the headers and the table
            smaller_space = Spacer(1, -15)
            space = Spacer(1, 20)
            # Add the headers, space, and table to the elements for this table
            table_elems = [semester_header, smaller_space, class_header, space, table, PageBreak()]
            # Add the elements for this table to the master list
            elems.extend(table_elems)
        # Create the PDF
        pdf.build(elems)

    @staticmethod
    def merge_tables(classes_list, data_list, semesters_list):
        grouped_data = defaultdict(lambda: [])
        merged_data_list = []
        merged_classes_list = []
        merged_semesters_list = []

        # Group Data and Merge Tables
        for class_name, data, semester in zip(classes_list, data_list, semesters_list):
            grouped_data[(class_name, semester)].append(data)

        for (class_name, semester), tables in grouped_data.items():
            merged_table = []
            if len(tables) > 1:
                headers = tables[0][0]  # Assuming the first row of the first table is the header
                merged_table.append(headers)  # Add headers only once
                for table in tables:
                    merged_table.extend(table[1:])  # Skip header after first table
            else:
                merged_table = tables[0]  # Only one table, no merge needed, keep headers

            merged_data_list.append(merged_table)
            merged_classes_list.append(class_name)
            merged_semesters_list.append(semester)

        return merged_classes_list, merged_data_list, merged_semesters_list

    # function for the user to download the created pdf to their computer
    def download_as_pdf(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)

        classes_list = []
        data = []
        semester_list = []

        # Loop through each table in self.class_table_pairs
        for display_class, table, semester, show in self.class_table_pairs:
            class_name = display_class.cget("text")
            table_data = table.get()

            classes_list.append(class_name)
            data.append(table_data)
            semester_list.append(semester)

        if len(self.class_table_pairs) == 1:
            initial_file_name = f"{semester_list[0]}_{classes_list[0]}_{translation['class_data']}.pdf"
        else:
            initial_file_name = f"{semester_list[0]}_{translation['classes_data']}.pdf"

        # Define where the PDF will be saved
        home = os.path.expanduser("~")
        downloads = os.path.join(home, "Downloads")
        filepath = filedialog.asksaveasfilename(
            title=translation["save_pdf"],
            defaultextension=".pdf",
            initialdir=downloads,
            filetypes=[("PDF Files", "*.pdf")],
            initialfile=initial_file_name
        )

        # Check if user cancelled the file dialog
        if not filepath:
            return

        classes_list, data, semester_list = TeraTermUI.merge_tables(classes_list, data, semester_list)
        self.create_pdf(data, classes_list, filepath, semester_list)
        self.show_success_message(350, 265, translation["pdf_save_success"])

    def copy_cell_data_to_clipboard(self, cell_data):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        cell_value = cell_data["value"]
        self.set_focus()
        self.clipboard_clear()
        self.clipboard_append(cell_value)
        self.update()

        # Close existing tooltip if any
        if self.tooltip:
            self.tooltip.destroy()

        # Create new tooltip
        x, y = self.winfo_pointerxy()
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.config(bg="#145DA0")
        self.tooltip.wm_geometry(f"+{x + 20}+{y + 20}")

        label = tk.Label(self.tooltip, text=translation["clipboard"],
                         bg="#145DA0", fg="#fff", font=("Arial", 10, "bold"))
        label.pack(padx=5, pady=5)

        # Auto-destroy after 1.5 seconds and reset the tooltip variable
        self.tooltip.after(1500, self.destroy_tooltip)

    def destroy_tooltip(self):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def transfer_class_data_to_enroll_tab(self, event, section_text):
        self.e_classes_entry.delete(0, "end")
        self.e_section_entry.delete(0, "end")
        self.e_classes_entry.insert(0, self.get_class_for_pdf)
        self.e_section_entry.insert(0, section_text)
        self.e_semester_entry.set(self.get_semester_for_pdf)
        self.register.select()
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.set_focus()

        # Close existing tooltip if any
        if self.tooltip:
            self.tooltip.destroy()

        # Create new tooltip
        x, y = self.winfo_pointerxy()
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.config(bg='#145DA0')
        self.tooltip.wm_geometry(f"+{x + 20}+{y + 20}")

        label = tk.Label(self.tooltip, text=translation["pasted"],
                         bg="#145DA0", fg="#fff", font=("Arial", 10, "bold"))
        label.pack(padx=5, pady=5)

        # Auto-destroy after 3.5 seconds and reset the tooltip variable
        self.tooltip.after(3500, self.destroy_tooltip)

    # displays the extracted data into a table
    def display_data(self, data):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        spec_data = TeraTermUI.specific_class_data(data)
        original_headers = ["SEC", "M", "CRED", "DAYS", "TIMES", "AV", "INSTRUCTOR"]
        headers = [translation["sec"], translation["m"], translation["cred"],
                   translation["days"], translation["times"], translation["av"],
                   translation["instructor"]]
        header_mapping = dict(zip(original_headers, headers))
        modified_data = []
        for item in spec_data:
            modified_item = {header_mapping[key]: value for key, value in item.items() if key in header_mapping}
            modified_data.append(modified_item)
        table_values = [headers] + [[item.get(header, "") for header in headers] for item in modified_data]
        num_rows = len(modified_data) + 1

        new_table = CTkTable(
            self.search_scrollbar,
            column=len(headers),
            row=num_rows,
            values=table_values,
            header_color="#145DA0",
            hover_color="#339CFF",
            command=self.copy_cell_data_to_clipboard,
        )
        for i in range(4):
            new_table.edit_column(i, width=55)
        new_table.edit_column(5, width=55)
        tooltip_messages = {
            translation["sec"]: translation["tooltip_sec"],
            translation["m"]: translation["tooltip_m"],
            translation["cred"]: translation["tooltip_cred"],
            translation["days"]: translation["tooltip_days"],
            translation["times"]: translation["tooltip_times"],
            translation["av"]: translation["tooltip_av"],
            translation["instructor"]: translation["tooltip_instructor"],
        }
        for i, header in enumerate(headers):
            cell = new_table.get_cell(0, i)
            tooltip_message = tooltip_messages[header]
            if cell in self.table_tooltips:
                self.table_tooltips[cell].configure(message=tooltip_message)
            else:
                tooltip = CTkToolTip(cell, message=tooltip_message, bg_color="#A9A9A9", alpha=0.90)
                self.table_tooltips[cell] = tooltip
        self.table = new_table

        for row in range(1, num_rows):
            section_cell = new_table.get_cell(row, 0)
            section_text = section_cell.cget("text")
            section_cell.bind("<Button-3>", lambda event, section=section_text: self.transfer_class_data_to_enroll_tab(
                event, section) if section.strip() else None)

        display_class = customtkinter.CTkLabel(self.search_scrollbar, text=self.get_class_for_pdf,
                                               font=customtkinter.CTkFont(size=15, weight="bold", underline=True))
        display_class.bind("<Button-1>", lambda event: self.focus_set())
        if self.table_count is None:
            table_count_label = f" {len(self.class_table_pairs)}/10"
            self.table_count = customtkinter.CTkLabel(self.search_scrollbar, text=table_count_label)
            self.previous_button = CustomButton(self.search_scrollbar, text=translation["previous"],
                                                command=self.show_previous_table)
            self.next_button = CustomButton(self.search_scrollbar, text=translation["next"],
                                            command=self.show_next_table)
            self.remove_button = CustomButton(self.search_scrollbar, text=translation["remove"], hover_color="darkred",
                                              fg_color="red", command=self.remove_current_table)
            self.download_pdf = CustomButton(self.search_scrollbar, text=translation["pdf_save_as"],
                                             hover_color="#173518", fg_color="#2e6930", command=self.download_as_pdf)
            self.table_count_tooltip = CTkToolTip(self.table_count, message=translation["table_count_tooltip"],
                                                  bg_color="#A9A9A9", alpha=0.90)
            self.previous_button_tooltip = CTkToolTip(self.previous_button, message=translation["previous_tooltip"],
                                                      bg_color="#1E90FF")
            self.next_button_tooltip = CTkToolTip(self.next_button, message=translation["next_tooltip"],
                                                  bg_color="#1E90FF")
            self.remove_button_tooltip = CTkToolTip(self.remove_button, message=translation["remove_tooltip"],
                                                    bg_color="red")
            self.download_pdf_tooltip = CTkToolTip(self.download_pdf, message=translation["download_pdf_tooltip"],
                                                   bg_color="green")

        if self.ignore:
            duplicate_index = self.find_duplicate(display_class, self.get_semester_for_pdf, self.show_all_sections)
            if duplicate_index is not None:
                self.current_table_index = duplicate_index
                self.display_current_table()
                self.update_buttons()
                return
        self.ignore = True

        self.class_table_pairs.append((display_class, new_table, self.get_semester_for_pdf, self.show_all_sections))
        self.current_table_index = len(self.class_table_pairs) - 1

        if len(self.class_table_pairs) > 10:
            display_class_to_remove, table_to_remove, semester, show = self.class_table_pairs[0]
            display_class_to_remove.unbind("<Button-1>")
            self.after(0, display_class_to_remove.destroy)
            self.after(0, table_to_remove.destroy)
            del self.class_table_pairs[0]
            self.current_table_index = max(0, self.current_table_index - 1)
            self.table_count.configure(text_color=("black", "white"))

        self.display_current_table()

        new_table.grid(row=2, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
        self.table_count.grid(row=4, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
        if len(self.class_table_pairs) > 1:
            self.previous_button.grid(row=5, column=1, padx=(0, 300), pady=(10, 0), sticky="n")
            self.next_button.grid(row=5, column=1, padx=(300, 0), pady=(10, 0), sticky="n")
            self.bind("<Left>", self.keybind_previous_table)
            self.bind("<Right>", self.keybind_next_table)
        if len(self.class_table_pairs) <= 1:
            self.previous_button.grid_forget()
            self.remove_button.grid_forget()
            self.next_button.grid_forget()
        self.remove_button.grid(row=5, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
        self.download_pdf.grid(row=6, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
        self.update_buttons()
        table_count_label = f"{translation['table_count']} {len(self.class_table_pairs)}/10"
        self.table_count.configure(text=table_count_label)
        if len(self.class_table_pairs) == 10:
            self.table_count.configure(text_color="red")

    def find_duplicate(self, new_display_class, new_semester, show_all_sections_state):
        for index, (display_class, table, semester, existing_show_all_sections_state) in enumerate(
                self.class_table_pairs):
            if (display_class.cget("text") == new_display_class.cget("text") and
                    semester == new_semester and
                    existing_show_all_sections_state == show_all_sections_state):
                return index
        return None

    def display_current_table(self):
        # Hide all tables and display_classes
        for display_class, table, semester, show in self.class_table_pairs:
            display_class.grid_forget()
            table.grid_forget()

        # Show the current display_class and table
        display_class, table, semester, show = self.class_table_pairs[self.current_table_index]
        display_class.grid(row=2, column=1, padx=(0, 0), pady=(8, 0), sticky="n")
        table.grid(row=2, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
        self.table = table
        self.current_class = display_class
        self.after(0, self.set_focus)

    def update_buttons(self):
        if self.current_table_index == 0:
            self.previous_button.configure(state="disabled")
        else:
            self.previous_button.configure(state="normal")

        if self.current_table_index == len(self.class_table_pairs) - 1:
            self.next_button.configure(state="disabled")
        else:
            self.next_button.configure(state="normal")

    def show_previous_table(self):
        if self.current_table_index > 0:
            self.current_table_index -= 1
            self.display_current_table()
            self.update_buttons()
            self.search_scrollbar.scroll_to_top()

    def show_next_table(self):
        if self.current_table_index < len(self.class_table_pairs) - 1:
            self.current_table_index += 1
            self.display_current_table()
            self.update_buttons()
            self.search_scrollbar.scroll_to_top()

    def keybind_previous_table(self, event):
        if self.move_slider_left_enabled:
            self.after(100, self.show_previous_table)

    def keybind_next_table(self, event):
        if self.move_slider_left_enabled:
            self.after(100, self.show_next_table)

    def remove_current_table(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        # Step 1: Remove the selected table
        if len(self.class_table_pairs) == 0:
            return

        display_class, table, semester, show = self.class_table_pairs[self.current_table_index]
        display_class.grid_forget()
        display_class.unbind("<Button-1>")
        table.grid_forget()
        self.after(0, display_class.destroy)
        self.after(0, table.destroy)
        if len(self.class_table_pairs) == 10:
            self.table_count.configure(text_color=("black", "white"))
        del self.class_table_pairs[self.current_table_index]

        # Step 2: Update the table count
        table_count_label = f"{translation['table_count']} {len(self.class_table_pairs)}/10"
        self.table_count.configure(text=table_count_label)

        # Step 3: Hide all GUI elements if no tables are left
        if len(self.class_table_pairs) == 1:
            self.previous_button.grid_forget()
            self.next_button.grid_forget()
            self.bind("<Left>", self.move_slider_left)
            self.bind("<Right>", self.move_slider_right)

        elif len(self.class_table_pairs) == 0:
            self.table = None
            self.current_class = None
            self.table_count.grid_forget()
            self.remove_button.grid_forget()
            self.download_pdf.grid_forget()
            self.search_scrollbar.scroll_to_top()
            self.after(0, display_class.destroy)
            self.after(0, table.destroy)
            self.after(0, self.set_focus)
            return

        # Step 4: Show the previous table
        self.current_table_index = max(0, self.current_table_index - 1)
        self.display_current_table()
        self.update_buttons()
        self.search_scrollbar.scroll_to_top()

    def automate_copy_class_data(self):
        import pyautogui

        max_retries = 3
        original_timeout = timings.Timings.window_find_timeout
        original_retry = timings.Timings.window_find_retry
        for attempt in range(max_retries):
            try:
                timings.Timings.window_find_timeout = 0.5
                timings.Timings.window_find_retry = 0.1
                edit_menu = self.uprb.UprbayTeraTermVt.child_window(
                    title="Edit", control_type="MenuItem", visible_only=False)
                edit_menu.invoke()
                select_screen_item = edit_menu.child_window(
                    title="Select screen", control_type="MenuItem", top_level_only=False)
                select_screen_item.invoke()
                break
            except ElementNotFoundError as e:
                print(f"An error occurred: {e}")
                if attempt < max_retries - 1:
                    pass
                else:
                    print("Max retries reached, raising exception.")
                    raise
            finally:
                timings.Timings.window_find_timeout = original_timeout
                timings.Timings.window_find_retry = original_retry
        self.uprb.UprbayTeraTermVt.type_keys("%c")
        self.hide_loading_screen()
        original_position = pyautogui.position()
        self.uprbay_window.click_input(button="left")
        try:
            pyautogui.moveTo(original_position.x, original_position.y)
        except pyautogui.FailSafeException as e:
            print("An error occurred:", e)
        self.show_loading_screen_again()

    @staticmethod
    def specific_class_data(data):
        modified_data = []
        for item in data:
            days = item["DAYS"].split(", ")
            times = item["TIMES"].split(", ")
            first = True  # Flag to identify the first day and time

            # Split instructor name for the first entry
            if "INSTRUCTOR" in item:
                parts = item["INSTRUCTOR"].split(",")
                item["INSTRUCTOR"] = "\n".join(parts)

            for day, time in zip(days, times):
                if first:
                    # For the first day and time, keep the item details intact but remove additional days and times
                    modified_item = item.copy()
                    modified_item["DAYS"] = day
                    modified_item["TIMES"] = time
                    first = False  # Unset the flag after the first iteration
                else:
                    # For additional days and times, create a new item with only the day and time
                    modified_item = {key: "" for key in item}  # Initialize all keys with empty strings
                    modified_item["DAYS"] = day
                    modified_item["TIMES"] = time

                # Process times to have proper format for each entry
                times_parts = modified_item["TIMES"].split("-")
                if len(times_parts) == 2:
                    start, end = times_parts
                    start = start.lstrip("0")
                    end = end.lstrip("0")
                    start = start[:-4] + ":" + start[-4:-2] + " " + start[-2:]
                    end = end[:-4] + ":" + end[-4:-2] + " " + end[-2:]
                    modified_item["TIMES"] = "\n".join([start, end])
                else:
                    modified_item["TIMES"] = modified_item["TIMES"].lstrip("0")

                modified_data.append(modified_item)

        return modified_data

    # extracts the text from the searched class to get the important information
    @staticmethod
    def extract_class_data(text):
        lines = text.split("\n")
        data = []
        course_found = False
        invalid_action = False
        y_n_found = False
        current_section = None

        for i, line in enumerate(lines):
            if "INVALID ACTION" in line:
                invalid_action = True

            if "COURSE NOT IN COURSE TERM FILE" in line:
                text_next_to_course = line.split("COURSE NOT IN COURSE TERM FILE")[-1].strip()
                if text_next_to_course:
                    course_found = True

            if "ALL (Y/N):" in line:
                y_n_value = line.split("ALL (Y/N):")[-1].strip()
                if y_n_value in ["Y", "N"]:
                    y_n_found = True

        # Regex pattern to match the course entries
        pattern = re.compile(
            r"(\w+)\s+(\w)\s+(LEC|LAB|INT|PRA|SEM)\s+(\d+\.\d+)\s+(\w+)\s+([\dAMP\-TBA]+)\s+([\d\s]+)?\s+.*?\s*(["
            r"NFUL\s]*.*)"
        )
        # Regex pattern to match additional time slots
        time_pattern = re.compile(
            r"^(\s+)(\w{2})\s+([\dAMP\-]+)\s*$"
        )
        for line in lines:
            if "LEC" in line or "LAB" in line or "INT" in line or "PRA" in line or "SEM" in line:
                match = pattern.search(line)
                if match:
                    instructor = match.group(8)
                    instructor = re.sub(r"\bN\b", "", instructor)  # remove standalone 'N'
                    instructor = re.sub(r"\bFULL\b", "", instructor)  # remove standalone 'FULL'
                    instructor = re.sub(r"\bRSVD\b", "", instructor)  # remove standalone 'RSVD'
                    instructor = re.sub(r"\bRSTR\b", "", instructor)  # remove standalone 'RSTR'
                    instructor = instructor.strip()  # remove leading and trailing whitespace
                    current_section = {
                        "SEC": match.group(1),
                        "M": match.group(2),
                        "CRED": match.group(4),
                        "DAYS": [match.group(5)],
                        "TIMES": [match.group(6)],
                        "AV": match.group(7).strip() if match.group(7) else "0",
                        "INSTRUCTOR": instructor
                    }
                    data.append(current_section)
            else:
                time_match = time_pattern.search(line)
                if time_match and current_section:
                    current_section["DAYS"].append(time_match.group(2))
                    current_section["TIMES"].append(time_match.group(3))
        # Combine days and times into single strings
        for section in data:
            section["DAYS"] = ", ".join(section["DAYS"])
            section["TIMES"] = ", ".join(section["TIMES"])

        return data, course_found, invalid_action, y_n_found

    def extract_my_enrolled_classes(self, text):
        lang = self.language_menu.get()
        translation = self.load_language(lang)

        # Adjusted regex pattern
        class_pattern = re.compile(
            r"\b\w\s+(\w+)\s+(.+?)\s+\w+\s+([A-FI-NPW]*)\s+(\w+)\s+(\d{4}\w{2}-\d{4}\w{2})"
            r"(?:\s+(\w+)\s+(\w+))?(?:\s+(\w+)\s+(\d{4}\w{2}-\d{4}\w{2}))?"
        )

        # Find all matches in the text
        matches = class_pattern.findall(text)

        # Structure the data into a list of dictionaries
        enrolled_classes = []
        for match in matches:
            curso_formatted = ""
            if match[0]:
                curso_formatted = f"{match[0][:4]}-{match[0][4:8]}-{match[0][8:]}"

            time_str = match[4]
            start_time, end_time = time_str.split("-")
            start_time = start_time.lstrip("0")
            end_time = end_time.lstrip("0")
            start_time = f"{start_time[:-4]}:{start_time[-4:-2]} {start_time[-2:]}"
            end_time = f"{end_time[:-4]}:{end_time[-4:-2]} {end_time[-2:]}"
            formatted_time = f"{start_time}\n{end_time}"

            class_info = {
                translation["course"]: curso_formatted,
                translation["grade"]: match[2],
                translation["days"]: match[3],
                translation["times"]: formatted_time,
                translation["room"]: match[6] if match[6] else ""
            }
            enrolled_classes.append(class_info)

            # Check for and add a new entry for additional DIAS and HORAS without the course name
            if match[7] and match[8]:
                additional_time_str = match[8]
                additional_start_time, additional_end_time = additional_time_str.split("-")
                additional_start_time = additional_start_time.lstrip("0")
                additional_end_time = additional_end_time.lstrip("0")
                additional_start_time = (f"{additional_start_time[:-4]}:{additional_start_time[-4:-2]}"
                                         f" {additional_start_time[-2:]}")
                additional_end_time = (f"{additional_end_time[:-4]}:{additional_end_time[-4:-2]}"
                                       f" {additional_end_time[-2:]}")
                additional_formatted_time = f"{additional_start_time}\n{additional_end_time}"

                additional_class_info = {
                    translation["course"]: "",  # Empty for additional rows
                    translation["grade"]: "",
                    translation["days"]: match[7],
                    translation["times"]: additional_formatted_time,
                    translation["room"]: ""
                }
                enrolled_classes.append(additional_class_info)

        # Search for total credits
        credits_pattern = re.compile(r"CREDITOS TOTAL:\s+(\d+\.\d+)")
        credits_match = credits_pattern.search(text)
        total_credits = credits_match.group(1) if credits_match else "0.00"

        return enrolled_classes, total_credits

    def display_enrolled_data(self, data, creds):
        self.unbind("<space>")
        self.unbind("<Control-Tab>")
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.enrolled_rows is not None:
            self.destroy_enrolled_frame()
        # Define the headers for the table based on the keys from enrolled_classes
        headers = [translation["course"], translation["grade"], translation["days"],
                   translation["times"], translation["room"]]
        # Create the table values, starting with headers
        table_values = [headers] + [[cls.get(header, "") for header in headers] for cls in data]
        # Calculate the number of rows
        self.enrolled_rows = len(data) + 1
        self.enrolled_classes_data = data

        semester = self.dialog_input.upper().replace(" ", "")
        self.my_classes_frame = customtkinter.CTkScrollableFrame(self, corner_radius=10, width=620, height=320)
        self.title_my_classes = customtkinter.CTkLabel(self.my_classes_frame,
                                                       text=translation["my_classes"] + semester,
                                                       font=customtkinter.CTkFont(size=20, weight="bold"))
        self.total_credits_label = customtkinter.CTkLabel(self.my_classes_frame,
                                                          text=translation["total_creds"] + creds)
        self.submit_my_classes = CustomButton(self.my_classes_frame, border_width=2,
                                              text=translation["submit"], text_color=("gray10", "#DCE4EE"),
                                              command=self.submit_modify_classes_handler)
        CTkToolTip(self.submit_my_classes, alpha=0.90, bg_color="#1E90FF", message=translation["submit_modify_tooltip"])
        self.modify_classes_frame = customtkinter.CTkFrame(self.my_classes_frame)
        self.back_my_classes = CustomButton(master=self.t_buttons_frame, fg_color="transparent", border_width=2,
                                            text=translation["back"], hover_color="#4E4F50",
                                            text_color=("gray10", "#DCE4EE"), command=self.go_back_event2)
        CTkToolTip(self.back_my_classes, alpha=0.90, bg_color="#A9A9A9", message=translation["back_multiple"])
        self.modify_classes_title = customtkinter.CTkLabel(self.modify_classes_frame,
                                                           text=translation["mod_classes_title"])
        self.back_classes.grid_forget()
        self.back_my_classes.grid(row=4, column=0, padx=(0, 10), pady=(0, 0), sticky="w")

        # Create the table widget
        self.enrolled_classes_table = CTkTable(
            self.my_classes_frame,
            column=len(headers),
            row=self.enrolled_rows,
            values=table_values,
            header_color="#145DA0",
            hover_color="#339CFF",
            command=self.copy_cell_data_to_clipboard,
        )
        column_widths = {
            translation["course"]: 100,
            translation["grade"]: 50,
            translation["days"]: 50,
            translation["times"]: 150,
            translation["room"]: 50
        }
        tooltip_messages = {
            translation["course"]: translation["tooltip_course"],
            translation["grade"]: translation["tooltip_grd"],
            translation["days"]: translation["tooltip_days"],
            translation["times"]: translation["tooltip_times"],
            translation["room"]: translation["tooltip_croom"]
        }

        for i, header in enumerate(headers):
            self.enrolled_classes_table.edit_column(i, width=column_widths[header])
            cell = self.enrolled_classes_table.get_cell(0, i)
            tooltip_message = tooltip_messages[header]
            CTkToolTip(cell, message=tooltip_message, bg_color="#A9A9A9", alpha=0.90)

        self.my_classes_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 100))
        self.my_classes_frame.grid_columnconfigure(2, weight=1)
        self.title_my_classes.grid(row=1, column=1, padx=(180, 0), pady=(10, 10))
        self.enrolled_classes_table.grid(row=2, column=1, pady=(0, 5))
        self.total_credits_label.grid(row=3, column=1, padx=(180, 0), pady=(0, 15))
        self.submit_my_classes.grid(row=4, column=1, padx=(180, 0))
        self.modify_classes_frame.grid(row=2, column=2, sticky="nw", padx=10)
        self.modify_classes_title.grid(row=0, column=0, padx=(0, 30), pady=(0, 30))

        self.change_section_entries = []
        self.mod_selection_list = []
        pad_y = 9

        for row_index in range(self.enrolled_rows - 1):
            if row_index == 0:
                pad_y = 30
            if self.enrolled_classes_data[row_index][translation["course"]] != "":
                if row_index < len(self.placeholder_texts_sections):
                    placeholder_text = self.placeholder_texts_sections[row_index]
                else:
                    extra_placeholder_text = ["KJ1", "LJ1", "KI1", "LI1", "VM1", "JM1"]
                    index_in_extra = (row_index - len(self.placeholder_texts_sections)) % len(extra_placeholder_text)
                    placeholder_text = extra_placeholder_text[index_in_extra]
                self.mod_selection = customtkinter.CTkOptionMenu(self.modify_classes_frame,
                                                                 values=[translation["choose"], translation["drop"],
                                                                         translation["section"]], width=80,
                                                                 command=lambda value, index=row_index:
                                                                 self.modify_enrolled_classes(value, index))
                self.change_section_entry = CustomEntry(self.modify_classes_frame, self, lang,
                                                        placeholder_text=placeholder_text,
                                                        width=50)
                self.mod_selection.grid(row=row_index, column=0, padx=(0, 100), pady=(pad_y, 0))
                self.change_section_entry.grid(row=row_index, column=0, padx=(50, 0), pady=(pad_y, 0))
                CTkToolTip(self.mod_selection, alpha=0.90, bg_color="#1E90FF",
                           message=translation["mod_selection"])
                CTkToolTip(self.change_section_entry, alpha=0.90, bg_color="#1E90FF",
                           message=translation["change_section_entry"])
                self.change_section_entry.configure(state="disabled")
                self.mod_selection_list.append(self.mod_selection)
                self.change_section_entries.append(self.change_section_entry)
                pad_y = 9
            else:
                self.mod_selection_list.append(None)
                self.change_section_entries.append(None)
                pad_y = 45
        self.my_classes_frame.grid(row=0, column=1)
        self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
        self.bind("<Up>", lambda event: self.move_up_scrollbar())
        self.bind("<Down>", lambda event: self.move_down_scrollbar())
        self.bind("<Home>", lambda event: self.move_top_scrollbar())
        self.bind("<End>", lambda event: self.move_bottom_scrollbar())
        self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_event2())
        self.my_classes_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.modify_classes_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.title_my_classes.bind("<Button-1>", lambda event: self.focus_set())

    def destroy_enrolled_frame(self):
        TeraTermUI.enable_entries(self)
        self.my_classes_frame.grid_forget()
        self.modify_classes_frame.grid_forget()
        self.my_classes_frame.unbind("<Button-1>")
        self.modify_classes_frame.unbind("<Button-1>")
        self.title_my_classes.unbind("<Button-1>")
        self.back_my_classes.grid_forget()
        self.enrolled_classes_table.destroy()
        self.title_my_classes.destroy()
        self.total_credits_label.destroy()
        self.submit_my_classes.destroy()
        self.back_my_classes.destroy()
        self.total_credits_label.destroy()
        self.modify_classes_title.destroy()
        for widget in self.mod_selection_list:
            if widget is not None:
                widget.destroy()
        for entry in self.change_section_entries:
            if entry is not None:
                entry.destroy()
        self.my_classes_frame.destroy()
        self.modify_classes_frame.destroy()
        self.change_section_entries = None
        self.mod_selection_list = None
        self.enrolled_rows = None

    def modify_enrolled_classes(self, mod, row_index):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        entry = self.change_section_entries[row_index]
        self.focus_set()
        if entry is not None:
            if mod == translation["section"]:
                entry.configure(state="normal")
            elif mod == translation["drop"] or mod == translation["choose"]:
                entry.configure(state="disabled")

    def submit_modify_classes_handler(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.focus_set()
        msg = CTkMessagebox(master=self, title=translation["submit"],
                            message=translation["submit_modify"],
                            icon="images/submit.png",
                            option_1=translation["option_1"], option_2=translation["option_2"],
                            option_3=translation["option_3"],
                            icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            task_done = threading.Event()
            loading_screen = self.show_loading_screen()
            self.update_loading_screen(loading_screen, task_done)
            event_thread = threading.Thread(target=self.submit_modify_classes, args=(task_done,))
            event_thread.start()

    def submit_modify_classes(self, task_done):
        with self.lock_thread:
            try:
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if self.dialog_input is not None:
                    dialog_input = self.dialog_input.upper().replace(" ", "")
                else:
                    dialog_input = self.prev_dialog_input.upper().replace(" ", "")
                show_error = False
                first_loop = True
                section_closed = False
                co_requisite = False
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        not_all_choose = False
                        section_pattern = True
                        edge_cases_bool = False
                        edge_cases_classes = ["FISI3011", "FISI3013", "FISI3012", "FISI3014", "BIOL3011", "BIOL3013",
                                              "BIOL3012", "BIOL3014", "QUIM3001", "QUIM3003", "QUIM3002", "QUIM3004"]
                        edge_cases_classes_met = []
                        for row_index in range(self.enrolled_rows - 1):
                            mod_selection = self.mod_selection_list[row_index]
                            change_section_entry = self.change_section_entries[row_index]
                            course_code_no_section = self.enrolled_classes_data[row_index][
                                                         translation["course"]].replace("-", "")[:8]
                            if mod_selection is not None and change_section_entry is not None:
                                mod = mod_selection.get()
                                section = change_section_entry.get().upper().replace(" ", "")
                                if mod != translation["choose"]:
                                    not_all_choose = True
                                if mod == translation["section"] and not re.fullmatch("^[A-Z]{2}[A-Z0-9]$",
                                                                                      section):
                                    section_pattern = False
                                if mod != translation["choose"] and course_code_no_section in edge_cases_classes:
                                    edge_cases_bool = True
                                    edge_cases_classes_met.append(course_code_no_section)
                        if not_all_choose and section_pattern and not edge_cases_bool:
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if term_window.isMinimized:
                                term_window.restore()
                            self.wait_for_window()
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            send_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1S4")
                            self.uprb.UprbayTeraTermVt.type_keys(dialog_input)
                            send_keys("{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            enrolled_classes = "ENROLLED"
                            count_enroll = text_output.count(enrolled_classes)
                            if "OUTDATED" not in text_output and "INVALID TERM SELECTION" not in text_output and \
                                    "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" \
                                    not in text_output and "ENTER REGISTRATION" in text_output:
                                for row_index in range(self.enrolled_rows - 1):
                                    mod_selection = self.mod_selection_list[row_index]
                                    change_section_entry = self.change_section_entries[row_index]
                                    if mod_selection is not None and change_section_entry is not None:
                                        mod = self.mod_selection_list[row_index].get()
                                        section = self.change_section_entries[row_index].get().upper().replace(" ", "")
                                        course_code = self.enrolled_classes_data[row_index][
                                            translation["course"]].replace("-", "")
                                        course_code_no_section = self.enrolled_classes_data[row_index][
                                                                     translation["course"]].replace("-", "")[:8]
                                        old_section = self.enrolled_classes_data[row_index][
                                                                     translation["course"]].replace("-", "")[8:]
                                    if mod == translation["drop"] or mod == translation["section"]:
                                        if not first_loop:
                                            time.sleep(1.5)
                                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                            screenshot_thread.start()
                                            screenshot_thread.join()
                                            text_output = self.capture_screenshot()
                                            enrolled_classes = "ENROLLED"
                                            count_enroll = text_output.count(enrolled_classes)
                                        first_loop = False
                                        send_keys("{TAB 3}")
                                        for i in range(count_enroll, 0, -1):
                                            send_keys("{TAB 2}")
                                        self.uprb.UprbayTeraTermVt.type_keys("D")
                                        self.uprb.UprbayTeraTermVt.type_keys(course_code)
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                        screenshot_thread.start()
                                        screenshot_thread.join()
                                        text_output = self.capture_screenshot()
                                        if "REQUIRED CO-REQUISITE" in text_output:
                                            co_requisite = True
                                        else:
                                            self.add_dropped_classes_list(old_section, course_code_no_section)
                                        send_keys("{ENTER 2}")
                                        self.reset_activity_timer(None)
                                        if mod == translation["section"]:
                                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                            screenshot_thread.start()
                                            screenshot_thread.join()
                                            text_output = self.capture_screenshot()
                                            enrolled_classes = "ENROLLED"
                                            count_enroll = text_output.count(enrolled_classes)
                                            send_keys("{TAB 3}")
                                            for i in range(count_enroll, 0, -1):
                                                send_keys("{TAB 2}")
                                            self.uprb.UprbayTeraTermVt.type_keys("R")
                                            self.uprb.UprbayTeraTermVt.type_keys(course_code_no_section)
                                            self.uprb.UprbayTeraTermVt.type_keys(section)
                                            send_keys("{ENTER}")
                                            self.reset_activity_timer(None)
                                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                            screenshot_thread.start()
                                            screenshot_thread.join()
                                            text_output = self.capture_screenshot()
                                            send_keys("{ENTER}")
                                            self.reset_activity_timer(None)
                                            if "INVALID COURSE ID" in text_output or "COURSE CLOSED" in text_output:
                                                show_error = True
                                                screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                                screenshot_thread.start()
                                                screenshot_thread.join()
                                                text_output = self.capture_screenshot()
                                                enrolled_classes = "ENROLLED"
                                                count_enroll = text_output.count(enrolled_classes)
                                                send_keys("{TAB 3}")
                                                for i in range(count_enroll, 0, -1):
                                                    send_keys("{TAB 2}")
                                                self.uprb.UprbayTeraTermVt.type_keys("R")
                                                self.uprb.UprbayTeraTermVt.type_keys(course_code)
                                                send_keys("{ENTER}")
                                                self.reset_activity_timer(None)
                                                screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                                screenshot_thread.start()
                                                screenshot_thread.join()
                                                text_output = self.capture_screenshot()
                                                send_keys("{ENTER}")
                                                self.reset_activity_timer(None)
                                                if "COURSE CLOSED" in text_output:
                                                    section_closed = True
                                                    self.add_dropped_classes_list(old_section, course_code_no_section)
                                                else:
                                                    self.add_enrolled_classes_list(old_section, course_code_no_section)
                                            else:
                                                self.add_enrolled_classes_list(section, course_code_no_section)
                                send_keys("{ENTER}")
                                self.reset_activity_timer(None)
                                time.sleep(1.5)
                                screenshot_thread = threading.Thread(target=self.capture_screenshot)
                                screenshot_thread.start()
                                screenshot_thread.join()
                                text_output = self.capture_screenshot()
                                self.reset_activity_timer(None)
                                if "CONFIRMED" in text_output:
                                    send_keys("{ENTER}")
                                if "DROPPED" in text_output:
                                    send_keys("{ENTER}")
                                try:
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("1CP")
                                    self.uprb.UprbayTeraTermVt.type_keys(dialog_input)
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    clipboard_content = None
                                    try:
                                        clipboard_content = self.clipboard_get()
                                    except tk.TclError:
                                        print("Clipboard contains non-text data, possibly an image or other formats")
                                    except Exception as e:
                                        print("Error handling clipboard content:", e)
                                    ctypes.windll.user32.BlockInput(False)
                                    self.automate_copy_class_data()
                                    ctypes.windll.user32.BlockInput(True)
                                    copy = pyperclip.paste()
                                    enrolled_classes, total_credits = self.extract_my_enrolled_classes(copy)
                                    self.after(0, self.display_enrolled_data, enrolled_classes, total_credits)
                                    self.clipboard_clear()
                                    if clipboard_content is not None:
                                        self.clipboard_append(clipboard_content)
                                    time.sleep(1)
                                except Exception as e:
                                    print("An error occurred: ", e)
                                    self.go_back_event2()
                                if show_error and not section_closed:
                                    self.after(100, self.show_error_message, 320, 240,
                                               translation["failed_change_section"])

                                    def explanation():
                                        self.destroy_windows()
                                        if self.enrolled_rows is not None:
                                            self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
                                            self.submit_my_classes.configure(state="normal")
                                        self.not_rebind = False
                                        if not self.disable_audio:
                                            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                                      icon="cancel",
                                                      message=translation["failed_change_section_exp"],
                                                      button_width=380)

                                    self.unbind("<Return>")
                                    self.submit_my_classes.configure(state="disabled")
                                    self.not_rebind = True
                                    self.after(2500, explanation)
                                elif section_closed:
                                    self.after(100, self.show_error_message, 320, 240,
                                               translation["failed_change_section"])

                                    def explanation():
                                        self.destroy_windows()
                                        if self.enrolled_rows is not None:
                                            self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
                                            self.submit_my_classes.configure(state="normal")
                                        self.not_rebind = False
                                        if not self.disable_audio:
                                            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                                      icon="cancel",
                                                      message=translation["section_closed"],
                                                      button_width=380)

                                    self.unbind("<Return>")
                                    self.submit_my_classes.configure(state="disabled")
                                    self.not_rebind = True
                                    self.after(2500, explanation)

                                elif co_requisite:
                                    self.after(100, self.show_error_message, 320, 240,
                                               translation["failed_change_section"])

                                    def explanation():
                                        self.destroy_windows()
                                        if self.enrolled_rows is not None:
                                            self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
                                            self.submit_my_classes.configure(state="normal")
                                        self.not_rebind = False
                                        if not self.disable_audio:
                                            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                                      icon="cancel",
                                                      message=translation["co_requisite"],
                                                      button_width=380)

                                    self.unbind("<Return>")
                                    self.submit_my_classes.configure(state="disabled")
                                    self.not_rebind = True
                                    self.after(2500, explanation)

                                else:
                                    self.after(100, self.show_success_message, 350, 265,
                                               translation["success_modify"])
                            else:
                                if "INVALID TERM SELECTION" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    send_keys("{ENTER}")
                                    self.reset_activity_timer(None)
                                    self.after(100, self.show_error_message, 300, 215,
                                               translation["invalid_semester"])
                                else:
                                    if "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" \
                                            not in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        send_keys("{ENTER}")
                                        self.reset_activity_timer(None)
                                        self.after(100, self.show_error_message, 315, 225,
                                                   translation["failed_modify"])
                                        if not self.modify_error_check:
                                            self.unbind("<Return>")
                                            self.submit_my_classes.configure(state="disabled")
                                            self.not_rebind = True
                                            self.after(2500, self.show_modify_classes_information)
                                            self.modify_error_check = True
                                    else:
                                        self.after(100, self.show_error_message, 315, 225,
                                                   translation["failed_modify"])
                                        if not self.modify_error_check:
                                            self.unbind("<Return>")
                                            self.submit_my_classes.configure(state="disabled")
                                            self.not_rebind = True
                                            self.after(2500, self.show_modify_classes_information)
                                            self.modify_error_check = True

                        else:
                            if not not_all_choose:
                                self.after(100, self.show_error_message, 360, 230,
                                           translation["choose_error"])
                            elif not section_pattern:
                                self.after(100, self.show_error_message, 360, 240,
                                           translation["section_format_error"])
                            elif edge_cases_bool:
                                def explanation():
                                    if not self.disable_audio:
                                        winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                    edge_case_classes_str = ", ".join(edge_cases_classes_met)
                                    CTkMessagebox(master=self, title=translation["automation_error_title"],
                                                  icon="warning",
                                                  message=translation["co_requisite_warning"] + edge_case_classes_str,
                                                  button_width=380)

                                self.after(0, explanation)
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
                self.log_error(e)
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                self.after(100, self.show_sidebar_windows)
                if self.error_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                      message=translation["automation_error"],
                                      icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(0, error_automation)
                if not self.not_rebind:
                    self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
                ctypes.windll.user32.BlockInput(False)

    # checks whether the program can continue its normal execution or if the server is on maintenance
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

    def wait_for_window(self):
        try:
            self.uprbay_window.wait("visible", timeout=5)
        except Exception as e:
            print("An error occurred: ", e)
            self.search_function_counter = 0
            self.uprb = Application(backend="uia").connect(
                title="uprbay.uprb.edu - Tera Term VT", timeout=5)
            self.uprb_32 = Application().connect(
                title="uprbay.uprb.edu - Tera Term VT", timeout=5)
            self.uprbay_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
            self.move_window()

    # checks whether the user has the requested file
    @staticmethod
    def is_file_in_directory(file_name, directory):
        # Join the directory path and file name
        full_path = os.path.join(directory, file_name)
        # Check if the file exists
        return os.path.isfile(full_path)

    # Necessary things to do while the application is booting, gets done on a separate thread
    def boot_up(self, file_path):
        threading.Thread(target=self.setup_tesseract).start()
        threading.Thread(target=self.backup_and_config_ini, args=(file_path,)).start()
        threading.Thread(target=self.setup_feedback).start()

    def setup_tesseract(self):
        # If Tesseract-OCR already in the temp folder dont unzip
        unzip_tesseract = True
        tesseract_dir_path = self.app_temp_dir / "Tesseract-OCR"
        if tesseract_dir_path.is_dir():
            tesseract_dir = Path(self.app_temp_dir) / "Tesseract-OCR"
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_dir / "tesseract.exe")
            unzip_tesseract = False
            self.tesseract_unzipped = True

        # Unzips Tesseract OCR
        if unzip_tesseract:
            try:
                with py7zr.SevenZipFile(self.zip_path, mode="r") as z:
                    z.extractall(self.app_temp_dir)
                tesseract_dir = Path(self.app_temp_dir) / "Tesseract-OCR"
                pytesseract.pytesseract.tesseract_cmd = str(tesseract_dir / "tesseract.exe")
                # tessdata_dir_config = f"--tessdata-dir {tesseract_dir / 'tessdata'}"
                self.tesseract_unzipped = True
                del tesseract_dir_path, tesseract_dir
                gc.collect()
            except Exception as e:
                SPANISH = 0x0A
                language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                print(f"Error occurred during unzipping: {str(e)}")
                self.tesseract_unzipped = False
                self.log_error(e)
                if "[Errno 2] No such file or directory" in str(e):
                    if language_id & 0xFF == SPANISH:
                        messagebox.showerror("Error", f"¡Error Fatal!\n\n{str(e)}")
                    else:
                        messagebox.showerror("Error", f"Fatal Error!\n\n{str(e)}")
                    self.after(0, self.forceful_end_app)

    def backup_and_config_ini(self, file_path):
        # backup for config file of tera term
        if TeraTermUI.is_file_in_directory("ttermpro.exe", self.teraterm_directory):
            backup_path = self.app_temp_dir / "TERATERM.ini.bak"
            if not os.path.exists(backup_path):
                backup_path = os.path.join(self.app_temp_dir, os.path.basename(file_path) + ".bak")
                try:
                    shutil.copyfile(file_path, backup_path)
                except FileNotFoundError as e:
                    self.log_error(e)
                    print("Tera Term Probably not installed\n"
                          "or installed in a different location from the default")

            # Edits the font that tera term uses to "Lucida Console" to mitigate the chance of the OCR mistaking words
            if not self.can_edit:
                try:
                    # Read lines once
                    with open(file_path, "r") as file:
                        lines = file.readlines()
                    # Edit in-place
                    for index, line in enumerate(lines):
                        if line.startswith("VTFont="):
                            current_value = line.strip().split("=")[1]
                            font_name = current_value.split(",")[0]
                            self.original_font = current_value
                            updated_value = "Lucida Console" + current_value[len(font_name):]
                            lines[index] = f"VTFont={updated_value}\n"
                            self.can_edit = True
                    # Write lines once
                    with open(file_path, "w") as file:
                        file.writelines(lines)
                    del line, lines
                except FileNotFoundError:
                    return
                except IOError as e:  # Replace with the specific exceptions you want to catch
                    print(f"Error occurred: {e}")
                    print("Restoring from backup...")
                    shutil.copyfile(backup_path, file_path)
                del backup_path

        else:
            self.teraterm_not_found = True

    def setup_feedback(self):
        from google.oauth2 import service_account

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
                del credentials_dict
                gc.collect()
        except Exception as e:
            print(f"Failed to load credentials: {str(e)}")
            self.log_error(str(e))
            self.credentials = None
            self.disable_feedback = True

    def update_app(self):
        translation = self.load_language(self.language_menu.get())
        if not self.disable_audio:
            winsound.PlaySound("sounds/update.wav", winsound.SND_ASYNC)
        msg = CTkMessagebox(master=self, title=translation["update_popup_title"],
                            message=translation["update_popup_message"],
                            icon="question", option_1=translation["option_1"],
                            option_2=translation["option_2"], option_3=translation["option_3"],
                            icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            webbrowser.open("https://github.com/Hanuwa/TeraTermUI/releases/latest")

    # Deletes Tesseract OCR and tera term config file from the temp folder
    def cleanup_temp(self):
        tesseract_dir = Path(self.app_temp_dir) / "Tesseract-OCR"
        backup_file_path = Path(self.app_temp_dir) / "TERATERM.ini.bak"
        if tesseract_dir.exists():
            for _ in range(10):  # Retry up to 10 times
                try:
                    shutil.rmtree(tesseract_dir)
                    break  # If the directory was deleted successfully, exit the loop
                except PermissionError:
                    time.sleep(1)  # Wait for 1 second before the next attempt
        # Delete the 'TERATERM.ini.bak' file
        if backup_file_path.exists() and not TeraTermUI.checkIfProcessRunning("ttermpro"):
            os.remove(backup_file_path)
            shutil.rmtree(self.app_temp_dir)

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
        if not self.disable_audio:
            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
        self.error = SmoothFadeToplevel(fade_duration=10)
        self.error.title("Error")
        self.error.geometry(window_geometry)
        self.error.resizable(False, False)
        self.error.iconbitmap(self.icon_path)
        my_image = self.get_image("error")
        image = customtkinter.CTkLabel(self.error, text="", image=my_image)
        image.pack(padx=10, pady=20)
        error_msg = customtkinter.CTkLabel(self.error,
                                           text=error_msg_text,
                                           font=customtkinter.CTkFont(size=15, weight="bold"))
        error_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)
        self.error.protocol("WM_DELETE_WINDOW", self.on_error_window_close)
        self.error.bind("<Escape>", lambda event: self.on_error_window_close())

    def on_error_window_close(self):
        self.unload_image("error")
        self.error.destroy()

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
        if not self.disable_audio:
            winsound.PlaySound("sounds/success.wav", winsound.SND_ASYNC)
        self.success = SmoothFadeToplevel(fade_duration=10)
        self.success.geometry(window_geometry)
        self.success.title(translation["success_title"])
        self.success.attributes("-topmost", True)
        self.success.resizable(False, False)
        self.success.iconbitmap(self.icon_path)
        my_image = self.get_image("success")
        image = customtkinter.CTkLabel(self.success, text="", image=my_image)
        image.pack(padx=10, pady=10)
        success_msg = customtkinter.CTkLabel(self.success, text=success_msg_text,
                                             font=customtkinter.CTkFont(size=15, weight="bold"))
        success_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)
        self.success.after(3500, lambda: self.on_success_window_close())
        self.success.protocol("WM_DELETE_WINDOW", self.on_success_window_close)
        self.success.bind("<Escape>", lambda event: self.on_success_window_close())

    def on_success_window_close(self):
        self.unload_image("success")
        self.success.destroy()
        if self.help and self.help.winfo_exists() and self.changed_location:
            self.after(250, self.help.lift)
            self.after(260, self.help.focus_set)
            self.changed_location = False

    # Pop window that shows the user more context on why they couldn't enroll their classes
    def show_enrollment_error_information(self, text="Error"):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        error_messages = {
            "INVALID COURSE ID": "INVALID COURSE ID",
            "COURSE RESERVED": "COURSE RESERVED",
            "COURSE CLOSED": "COURSE CLOSED",
            "CRS ALRDY TAKEN/PASSED": "CRS ALRDY TAKEN/PASSED",
            "Closed by Spec-Prog": "Closed by Spec-Prog",
            "Pre-Req": "Pre-Req Rqd",
            "Closed by College": "Closed by College",
            "Closed by Major": "Closed by Major",
            "TERM MAX HRS EXCEEDED": "TERM MAX HRS EXCEEDED",
            "REQUIRED CO-REQUISITE": "REQUIRED CO-REQUISITE",
            "ILLEGAL DROP-NOT ENR": "ILLEGAL DROP-NOT ENR",
            "NEW COURSE,NO FUNCTION": "NEW COURSE,NO FUNCTION",
            "PRESENTLY ENROLLED": "PRESENTLY ENROLLED",
            "COURSE IN PROGRESS": "COURSE IN PROGRESS",
            "R/TC": "R/TC"
        }
        # List to hold all error messages found in the text
        found_errors = []
        # Check each error message
        for code in error_messages:
            if code in text:
                found_errors.append(error_messages[code])
        # If errors were found, show them, otherwise show a default message
        if found_errors:
            self.destroy_windows()
            error_message_str = ", ".join(found_errors)
            if not self.disable_audio:
                winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
            CTkMessagebox(master=self, title=translation["automation_error_title"], icon="cancel",
                          message=translation["specific_enrollment_error"] + error_message_str,
                          button_width=380)
        self.submit.configure(state="normal")
        self.submit_multiple.configure(state="normal")
        self.not_rebind = False
        if self.in_multiple_screen:
            self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
        else:
            self.switch_tab()
        if self.enrollment_error_check:
            self.destroy_windows()
            if not self.disable_audio:
                winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
            CTkMessagebox(master=self, title=translation["automation_error_title"],
                          message=translation["enrollment_error"], button_width=380)

    # Pop window that shows the user more context on why they couldn't enroll their classes
    def show_enrollment_error_information_multiple(self, text="Error"):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        error_messages = {
            "INVALID COURSE ID": "INVALID COURSE ID",
            "COURSE RESERVED": "COURSE RESERVED",
            "COURSE CLOSED": "COURSE CLOSED",
            "CRS ALRDY TAKEN/PASSED": "CRS ALRDY TAKEN/PASSED",
            "Closed by Spec-Prog": "Closed by Spec-Prog",
            "Pre-Req": "Pre-Req Rqd",
            "Closed by College": "Closed by College",
            "Closed by Major": "Closed by Major",
            "TERM MAX HRS EXCEEDED": "TERM MAX HRS EXCEEDED",
            "REQUIRED CO-REQUISITE": "REQUIRED CO-REQUISITE",
            "ILLEGAL DROP-NOT ENR": "ILLEGAL DROP-NOT ENR",
            "NEW COURSE,NO FUNCTION": "NEW COURSE,NO FUNCTION",
            "PRESENTLY ENROLLED": "PRESENTLY ENROLLED",
            "COURSE IN PROGRESS": "COURSE IN PROGRESS",
            "R/TC": "R/TC"
        }
        # List to hold all error messages found in the text
        found_errors = []
        # Check each error message
        for code in error_messages:
            if code in text:
                found_errors.append(error_messages[code])
        # If errors were found, show them, otherwise show a default message
        if found_errors:

            def explanation():
                self.destroy_windows()
                error_message_str = ", ".join(found_errors)
                if not self.disable_audio:
                    winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                CTkMessagebox(master=self, title=translation["automation_error_title"], icon="cancel",
                              message=translation["specific_enrollment_error"] + error_message_str,
                              button_width=380)
                for counter in range(self.a_counter + 1, 0, -1):
                    if self.enrolled_classes_list:
                        self.enrolled_classes_list.popitem()
                    if self.dropped_classes_list:
                        self.dropped_classes_list.popitem()

            self.after(2500, explanation)
        if not found_errors and text != "Error":
            for i in range(self.a_counter + 1):
                self.m_classes_entry[i].configure(state="normal")
                self.m_section_entry[i].configure(state="normal")
                self.m_classes_entry[i].delete(0, "end")
                self.m_section_entry[i].delete(0, "end")
                self.m_classes_entry[i].configure(state="disabled")
                self.m_section_entry[i].configure(state="disabled")
            for i in range(6):
                self.m_classes_entry[i].configure(state="normal")
                self.m_section_entry[i].configure(state="normal")
                self.m_classes_entry[i].configure(
                    placeholder_text=self.placeholder_texts_classes[i])
                self.m_section_entry[i].configure(
                    placeholder_text=self.placeholder_texts_sections[i])
                self.m_classes_entry[i].configure(state="disabled")
                self.m_section_entry[i].configure(state="disabled")
        self.submit.configure(state="normal")
        self.submit_multiple.configure(state="normal")
        self.not_rebind = False
        if self.in_multiple_screen:
            self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
        else:
            self.switch_tab()
        if self.enrollment_error_check:

            def explanation():
                self.destroy_windows()
                if not self.disable_audio:
                    winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                CTkMessagebox(master=self, title=translation["automation_error_title"],
                              message=translation["enrollment_error"], button_width=380)

            self.after(2500, explanation)

    def show_modify_classes_information(self):
        self.destroy_windows()
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.modify_error_check:
            if self.enrolled_rows is not None:
                self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
                self.submit_my_classes.configure(state="normal")
            self.not_rebind = False
            if not self.disable_audio:
                winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
            CTkMessagebox(master=self, title=translation["automation_error_title"],
                          message=translation["modify_error"], button_width=380)

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
        if not self.disable_audio:
            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
        self.information = SmoothFadeToplevel(fade_duration=10)
        self.information.geometry(window_geometry)
        self.information.title(translation["information_title"])
        self.information.resizable(False, False)
        self.information.iconbitmap(self.icon_path)
        my_image = self.get_image("information")
        image = customtkinter.CTkLabel(self.information, text="", image=my_image)
        image.pack(padx=10, pady=10)
        information_msg = customtkinter.CTkLabel(self.information, text=success_msg_text,
                                                 font=customtkinter.CTkFont(size=15, weight="bold"))
        information_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)
        self.information.protocol("WM_DELETE_WINDOW", self.on_information_window_close)
        self.information.bind("<Escape>", lambda event: self.on_information_window_close())

    def on_information_window_close(self):
        self.unload_image("information")
        self.information.destroy()

    def automation_preparations(self):
        self.focus_set()
        self.destroy_windows()
        self.hide_sidebar_windows()
        self.unbind("<Return>")
        if self.tooltip and self.tooltip.winfo_exists():
            self.tooltip.destroy()
        ctypes.windll.user32.BlockInput(True)

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
        if self.tabview.get() == self.search_tab:
            if len(self.class_table_pairs) > 1:
                self.bind("<Left>", self.keybind_previous_table)
                self.bind("<Right>", self.keybind_next_table)

    def remove_key_bindings(self, event):
        self.unbind("<Left>")
        self.unbind("<Right>")

    # Moves the scaling slider to the left
    def move_slider_left(self, event):
        if self.move_slider_left_enabled:
            value = self.scaling_slider.get()
            if value != 97:
                value -= 3
                self.scaling_slider.set(value)
                self.change_scaling_event(value)
                self.scaling_tooltip.configure(message=str(self.scaling_slider.get()) + "%")

    # Moves the scaling slider to the right
    def move_slider_right(self, event):
        if self.move_slider_right_enabled:
            value = self.scaling_slider.get()
            if value != 103:
                value += 3
                self.scaling_slider.set(value)
                self.change_scaling_event(value)
                self.scaling_tooltip.configure(message=str(self.scaling_slider.get()) + "%")

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
                if choice == "register":
                    self.drop.select()
                elif choice == "drop":
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
        new_scaling_float = new_scaling / 100
        if new_scaling_float == self.current_scaling:
            return

        self.scaling_tooltip.hide()
        self.focus_set()
        customtkinter.set_widget_scaling(new_scaling_float)
        self.scaling_tooltip.configure(message=f"{new_scaling}%")
        self.current_scaling = new_scaling_float
        self.scaling_tooltip.show()

    # opens GitHub page
    def github_event(self):
        self.focus_set()
        webbrowser.open("https://github.com/Hanuwa/TeraTermUI")

    def notaso_event(self):
        self.focus_set()
        webbrowser.open("https://notaso.com/universities/uprb")

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
        if not self.disable_audio:
            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
        msg = CTkMessagebox(master=self, title=translation["download_title"],
                            message=translation["download_tera_term"],
                            icon="question",
                            option_1=translation["option_1"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            webbrowser.open("https://osdn.net/projects/ttssh2/releases")

    # links to each correspondant curriculum that the user chooses
    @staticmethod
    def curriculums(choice):
        links = {
            "Departments": "https://www.uprb.edu/sample-page/decanato-de-asuntos-academicos"
                           "/departamentos-academicos-2/",
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

    def check_update_app_handler(self):
        self.updating_app = True
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        event_thread = threading.Thread(target=self.check_update_app, args=(task_done,))
        event_thread.start()

    # will tell the user that there's a new update available for the application
    def check_update_app(self, task_done):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if asyncio.run(self.test_connection(lang)):
            latest_version = self.get_latest_release()
            current_date = datetime.today().strftime("%Y-%m-%d")
            row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (update_date) VALUES (?)",
                                    (current_date,))
            else:
                self.cursor.execute("UPDATE user_data SET update_date=?", (current_date,))
            if latest_version is None:
                task_done.set()

                def error():
                    print("No latest release found. Starting app with the current version.")
                    winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title="Error", icon="cancel",
                                  message=translation["failed_to_find_update"], button_width=380)

                self.after(0, error)
                return
            if not TeraTermUI.compare_versions(latest_version, self.USER_APP_VERSION):
                task_done.set()

                def update():
                    if not self.disable_audio:
                        winsound.PlaySound("sounds/update.wav", winsound.SND_ASYNC)
                    msg = CTkMessagebox(master=self, title=translation["update_popup_title"],
                                        message=translation["update_popup_message"],
                                        icon="question",
                                        option_1=translation["option_1"], option_2=translation["option_2"],
                                        option_3=translation["option_3"], icon_size=(65, 65),
                                        button_color=("#c30101", "#145DA0", "#145DA0"),
                                        hover_color=("darkred", "use_default", "use_default"))
                    response = msg.get()
                    if response[0] == "Yes" or response[0] == "Sí":
                        webbrowser.open("https://github.com/Hanuwa/TeraTermUI/releases/latest")

                self.after(0, update)
            else:
                task_done.set()

                def up_to_date():
                    if not self.disable_audio:
                        winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    CTkMessagebox(master=self, title="Info", message=translation["update_up_to_date"], button_width=380)

                self.after(0, up_to_date)
        else:
            self.updating_app = False
            task_done.set()

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
        if TeraTermUI.checkIfProcessRunning("ttermpro"):
            msg = CTkMessagebox(master=self, title=translation["fix_messagebox_title"],
                                message=translation["fix_messagebox"],
                                icon="warning",
                                option_1=translation["option_1"], option_2=translation["option_2"],
                                option_3=translation["option_3"], icon_size=(65, 65),
                                button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "use_default", "use_default"))
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
                self.automation_preparations()
                term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                if term_window.isMinimized:
                    term_window.restore()
                self.wait_for_window()
                TeraTermUI.unfocus_tkinter()
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
                self.enrolled_classes_list = {}
                self.dropped_classes_list = {}
                self.after(100, self.show_information_message, 370, 250,
                           translation["fix_after"])
            except Exception as e:
                print("An error occurred: ", e)
                self.error_occurred = True
                self.log_error(e)
            finally:
                task_done.set()
                lang = self.language_menu.get()
                self.after(100, self.set_focus_to_tkinter)
                self.after(0, self.switch_tab)
                self.after(100, self.show_sidebar_windows)
                translation = self.load_language(lang)
                if self.error_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                        CTkMessagebox(master=self, title=translation["automation_error_title"],
                                      message=translation["automation_error"],
                                      icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(0, error_automation)
                ctypes.windll.user32.BlockInput(False)

    def start_check_process_thread(self):
        self.is_check_process_thread_running = True
        self.check_process_thread = threading.Thread(target=self.check_process_periodically)
        self.check_process_thread.daemon = True
        self.check_process_thread.start()

    def check_process_periodically(self):
        time.sleep(30)
        not_running_count = 0
        while self.is_check_process_thread_running and not self.stop_is_check_process.is_set():
            if self.loading_screen is None:
                is_running = TeraTermUI.checkIfProcessRunning("ttermpro")
                if is_running and not self.is_idle_thread_running:
                    not_running_count = 0
                    self.start_check_idle_thread()
                else:
                    not_running_count += 1
                    if not_running_count == 1:
                        lang = self.language_menu.get()
                        translation = self.load_language(lang)

                        def not_running():
                            if not self.disable_audio:
                                winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                            CTkMessagebox(master=self, title=translation["automation_error_title"], icon="warning",
                                          message=translation["tera_term_stopped_running"],
                                          button_width=380)

                        self.after(0, not_running)
                    if not_running_count > 1:
                        self.is_idle_thread_running = False
            time.sleep(30)

    # Starts the check for idle thread
    def start_check_idle_thread(self):
        idle = self.cursor.execute("SELECT idle FROM user_data").fetchone()
        if idle[0] != "Disabled":
            self.is_idle_thread_running = True
            self.check_idle_thread = threading.Thread(target=self.check_idle)
            self.check_idle_thread.daemon = True
            self.check_idle_thread.start()

    # Checks if the user is idle for 5 minutes and does some action so that Tera Term doesn't close by itself
    def check_idle(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.idle_num_check = 0
        try:
            while self.is_idle_thread_running and not self.stop_check_idle.is_set():
                if time.time() - self.last_activity >= 300:
                    with self.lock_thread:
                        if TeraTermUI.checkIfProcessRunning("ttermpro") and \
                                TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                            lang = self.language_menu.get()
                            translation = self.load_language(lang)
                            if TeraTermUI.window_exists(translation["exit"]):
                                self.exit.close_messagebox()
                            if TeraTermUI.window_exists(translation["idle_warning_title"]):
                                self.idle_warning.close_messagebox()
                            try:
                                main_window = self.uprb_32.window(title="uprbay.uprb.edu - Tera Term VT")
                                main_window.wait("visible", timeout=5)
                            except Exception as e:
                                print("An error occurred: ", e)
                                self.search_function_counter = 0
                                self.uprb = Application(backend="uia").connect(
                                    title="uprbay.uprb.edu - Tera Term VT", timeout=5)
                                self.uprb_32 = Application().connect(
                                    title="uprbay.uprb.edu - Tera Term VT", timeout=5)
                                self.uprbay_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT")
                                main_window = self.uprb_32.window(title="uprbay.uprb.edu - Tera Term VT")
                                self.move_window()
                            main_window.send_keystrokes("{VK_RIGHT}")
                            main_window.send_keystrokes("{VK_LEFT}")
                            self.last_activity = time.time()
                            if not self.countdown_running:
                                self.idle_num_check += 1
                            if self.countdown_running:
                                self.idle_num_check = 1
                            if self.idle_num_check == 11:
                                def idle_warning():
                                    if not self.disable_audio:
                                        winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                                    self.idle_warning = CTkMessagebox(
                                        master=self, title=translation["idle_warning_title"],
                                        message=translation["idle_warning"], button_width=380)
                                    response = self.idle_warning.get()[0]
                                    if response == "OK":
                                        self.idle_num_check = 0

                                self.after(0, idle_warning)
                        else:
                            self.stop_check_idle.is_set()
                if self.idle_num_check == 12:
                    break
                time.sleep(3)
        except Exception as e:
            print("An error occurred: ", e)
            self.log_error(e)

    # resets the idle timer when user interacts with something within the application
    def reset_activity_timer(self, _):
        self.last_activity = time.time()
        self.idle_num_check = 0

    # Disables check_idle functionality
    def disable_enable_idle(self):
        row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
        if self.disable_idle.get() == "on":
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (idle) VALUES (?)", ("Disabled",))
            else:
                self.cursor.execute("UPDATE user_data SET idle=?", ("Disabled",))
            self.reset_activity_timer(None)
            self.is_idle_thread_running = False
        elif self.disable_idle.get() == "off":
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (idle) VALUES (?)", ("Enabled",))
            else:
                self.cursor.execute("UPDATE user_data SET idle=?", ("Enabled",))
            if self.auto_enroll is not None:
                self.auto_enroll.configure(state="normal")
            if self.run_fix and TeraTermUI.checkIfProcessRunning("ttermpro"):
                self.automation_preparations()
                term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                if term_window.isMinimized:
                    term_window.restore()
                self.wait_for_window()
                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                send_keys("{ENTER}")
                self.reset_activity_timer(None)
                self.start_check_idle_thread()
                if self.in_multiple_screen:
                    self.set_focus_to_tkinter()
                    self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
                elif not self.in_multiple_screen and self.enrolled_rows is None:
                    self.set_focus_to_tkinter()
                    self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
                else:
                    self.set_focus_to_tkinter()
                    self.switch_tab()
                self.show_sidebar_windows()
                ctypes.windll.user32.BlockInput(False)
        self.connection.commit()

    def disable_enable_audio(self):
        row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
        if self.disable_audio_val.get() == "on":
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (audio) VALUES (?)", ("Disabled",))
            else:
                self.cursor.execute("UPDATE user_data SET audio=?", ("Disabled",))
            self.disable_audio = True
        elif self.disable_audio_val.get() == "off":
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (audio) VALUES (?)", ("Enabled",))
            else:
                self.cursor.execute("UPDATE user_data SET audio=?", ("Enabled",))
            self.disable_audio = False
        self.connection.commit()

    @staticmethod
    async def fetch(session, url):
        import aiohttp

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
        import aiohttp

        translation = self.load_language(lang)
        urls = ["https://www.google.com/", "https://www.bing.com/", "https://www.yahoo.com/"]
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=3)) as session:
            tasks = [TeraTermUI.fetch(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
        connected = any(results)
        if not connected and not self.check_update:
            self.after(100, self.show_error_message, 300, 215, translation["no_internet"])
        if self.check_update:
            self.check_update = False
        return connected

    # Set focus on the UI application window
    def set_focus_to_tkinter(self):
        self.lift()
        self.focus_force()
        self.attributes("-topmost", 1)
        self.after_idle(self.attributes, "-topmost", 0)
        if self.error and self.error.winfo_exists():
            self.error.lift()
            self.error.focus_force()
            self.error.attributes("-topmost", 1)
            self.error.after_idle(self.attributes, "-topmost", 0)
        elif self.success and self.success.winfo_exists():
            self.success.focus_set()
        elif self.information and self.information.winfo_exists():
            self.information.lift()
            self.information.focus_force()
            self.information.attributes("-topmost", 1)
            self.information.after_idle(self.attributes, "-topmost", 0)
        elif self.timer_window and self.timer_window.winfo_exists():
            self.timer_window.lift()
            self.timer_window.focus_force()
            self.timer_window.attributes("-topmost", 1)
            self.timer_window.after_idle(self.timer_window.attributes, "-topmost", 0)

    # Set focus on Tera Term window
    @staticmethod
    def unfocus_tkinter():
        term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
        term_window.activate()

    def tab_switcher(self):
        current_time = time.time()
        if hasattr(self, "last_switch_time") and current_time - self.last_switch_time < 0.2 or \
                (self.loading_screen is not None and self.loading_screen.winfo_exists()):
            TeraTermUI.disable_entries(self)
            self.after(0, TeraTermUI.enable_entries, self)
            return

        self.last_switch_time = current_time

        if self.tabview.get() == self.enroll_tab:
            self.tabview.set(self.search_tab)
        elif self.tabview.get() == self.search_tab:
            self.tabview.set(self.other_tab)
        elif self.tabview.get() == self.other_tab:
            self.tabview.set(self.enroll_tab)
        self.after(0, self.switch_tab)

    # Changes keybind depending on the tab the user is currently on
    def switch_tab(self):
        self.destroy_tooltip()
        self.add_key_bindings(event=None)
        if self.tabview.get() == self.enroll_tab:
            self.search_scrollbar.configure(width=None, height=None)
            self.in_search_frame = False
            self.in_enroll_frame = True
            self.unbind("<Up>")
            self.unbind("<Down>")
            self.unbind("<Home>")
            self.unbind("<End>")
            if not self.not_rebind:
                self.bind("<Return>", lambda event: self.submit_event_handler())
            else:
                self.unbind("<Return>")
            self.bind("<space>", lambda event: self.spacebar_event())
        elif self.tabview.get() == self.search_tab:
            self.search_scrollbar.configure(width=600, height=293)
            if hasattr(self, "table") and self.table is not None:
                self.current_class.grid_forget()
                self.table.grid_forget()
                self.table_count.grid_forget()
                self.previous_button.grid_forget()
                self.next_button.grid_forget()
                self.remove_button.grid_forget()
                self.download_pdf.grid_forget()
                self.search_scrollbar.scroll_to_top()
                self.after(100, self.load_table)
            self.in_enroll_frame = False
            self.in_search_frame = True
            self.bind("<Return>", lambda event: self.search_event_handler())
            self.bind("<space>", lambda event: self.spacebar_event())
            self.search_scrollbar.bind("<Button-1>", lambda event: self.search_scrollbar.focus_set())
            self.bind("<Up>", lambda event: self.move_up_scrollbar())
            self.bind("<Down>", lambda event: self.move_down_scrollbar())
            self.bind("<Home>", lambda event: self.move_top_scrollbar())
            self.bind("<End>", lambda event: self.move_bottom_scrollbar())
        elif self.tabview.get() == self.other_tab:
            self.search_scrollbar.configure(width=None, height=None)
            self.in_enroll_frame = False
            self.in_search_frame = False
            self.unbind("<space>")
            self.unbind("<Up>")
            self.unbind("<Down>")
            self.unbind("<Home>")
            self.unbind("<End>")
            self.bind("<Return>", lambda event: self.option_menu_event_handler())
        self.after(0, self.focus_set)

    def load_table(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if hasattr(self, "table") and self.table is not None:
            self.current_class.grid(row=2, column=1, padx=(0, 0), pady=(8, 0), sticky="n")
            self.table.grid(row=2, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
            self.table_count.grid(row=4, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
            if len(self.class_table_pairs) > 1:
                self.previous_button.grid(row=5, column=1, padx=(0, 300), pady=(10, 0), sticky="n")
                self.next_button.grid(row=5, column=1, padx=(300, 0), pady=(10, 0), sticky="n")
            if len(self.class_table_pairs) <= 1:
                self.previous_button.grid_forget()
                self.remove_button.grid_forget()
                self.next_button.grid_forget()
            self.remove_button.grid(row=5, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
            self.download_pdf.grid(row=6, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
            table_count_label = f"{translation['table_count']} {len(self.class_table_pairs)}/10"
            self.table_count.configure(text=table_count_label)

    def status_widgets(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.status_frame = CustomScrollableFrame(self.status, width=475, height=280,
                                                  fg_color=("#e6e6e6", "#222222"))
        self.status_title = customtkinter.CTkLabel(self.status_frame, text=translation["status_title"],
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        self.version = customtkinter.CTkLabel(self.status_frame, text=translation["app_version"])
        self.feedback_text = CustomTextBox(self.status_frame,  self, enable_autoscroll=False, lang=lang,
                                           wrap="word", border_spacing=8, width=300, height=170,
                                           fg_color=("#ffffff", "#111111"))
        self.feedback_send = CustomButton(self.status_frame, text=translation["feedback"],
                                          text_color=("gray10", "#DCE4EE"), command=self.start_feedback_thread)
        self.check_update_text = customtkinter.CTkLabel(self.status_frame, text=translation["update_title"])
        self.check_update_btn = CustomButton(self.status_frame, image=self.get_image("update"),
                                             text=translation["update"], anchor="w", text_color=("gray10", "#DCE4EE"),
                                             command=self.check_update_app_handler)
        self.website = customtkinter.CTkLabel(self.status_frame, text=translation["website"])
        self.website_link = CustomButton(self.status_frame, image=self.get_image("link"), text=translation["link"],
                                         anchor="w", text_color=("gray10", "#DCE4EE"), command=self.github_event)
        self.notaso = customtkinter.CTkLabel(self.status_frame, text=translation["notaso_title"])
        self.notaso_link = CustomButton(self.status_frame, image=self.get_image("link"),
                                        text=translation["notaso_link"], anchor="w", text_color=("gray10", "#DCE4EE"),
                                        command=self.notaso_event)
        self.faq_text = customtkinter.CTkLabel(self.status_frame, text=translation["faq"],
                                               font=customtkinter.CTkFont(size=15, weight="bold"))
        self.qa_table = [[translation["q"], translation["a"]],
                         [translation["q1"], translation["a1"]],
                         [translation["q2"], translation["a2"]]]

    # Creates the status window
    def status_button_event(self):
        if self.status and self.status.winfo_exists():
            windows_status = gw.getWindowsWithTitle("Status") + gw.getWindowsWithTitle("Estado")
            self.status_minimized = windows_status[0].isMinimized
            if self.status_minimized:
                self.status.deiconify()
            self.status.lift()
            self.status.focus_set()
            return
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.status = SmoothFadeToplevel()
        self.status_widgets()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        scaling_factor = self.tk.call("tk", "scaling")
        x_position = int((screen_width - 475 * scaling_factor) / 2)
        y_position = int((screen_height - 275 * scaling_factor) / 2)
        window_geometry = f"{475}x{280}+{x_position + 130}+{y_position + 18}"
        self.status.geometry(window_geometry)
        self.status.title(translation["status"])
        self.status.iconbitmap(self.icon_path)
        self.status.resizable(False, False)
        self.status_frame.pack()
        self.status_title.pack()
        self.version.pack()
        self.feedback_text.pack(pady=10)
        self.feedback_send.pack()
        self.check_update_text.pack(pady=5)
        self.check_update_btn.pack()
        self.website.pack(pady=5)
        self.website_link.pack()
        self.notaso.pack(pady=5)
        self.notaso_link.pack()
        self.faq_text.pack()
        self.faq = CTkTable(self.status_frame, row=3, column=2, values=self.qa_table, hover=False)
        self.faq.pack(expand=True, fill="both", padx=20, pady=10)
        self.feedback_text.lang = lang
        self.status.focus_set()
        self.status_frame.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.status_frame.bind("<Button-3>", lambda event: self.status_frame.focus_set())
        self.status.bind("<Up>", lambda event: self.status_scroll_up())
        self.status.bind("<Down>", lambda event: self.status_scroll_down())
        self.status.bind("<Home>", lambda event: self.status_move_top_scrollbar())
        self.status.bind("<End>", lambda event: self.status_move_bottom_scrollbar())
        self.status.protocol("WM_DELETE_WINDOW", self.on_status_window_close)
        self.status.bind("<Escape>", lambda event: self.on_status_window_close())

    def on_status_window_close(self):
        self.unload_image("update")
        self.unload_image("link")
        self.move_slider_left_enabled = True
        self.move_slider_right_enabled = True
        self.spacebar_enabled = True
        self.up_arrow_key_enabled = True
        self.down_arrow_key_enabled = True
        self.status.destroy()

    def status_scroll_up(self):
        if self.up_arrow_key_enabled:
            self.status_frame.scroll_more_up()

    def status_scroll_down(self):
        if self.down_arrow_key_enabled:
            self.status_frame.scroll_more_down()

    def status_move_top_scrollbar(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            self.status_frame.scroll_to_top()

    def status_move_bottom_scrollbar(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            self.status_frame.scroll_to_bottom()

    # Function to call the Google Sheets API
    def call_sheets_api(self, values):
        from googleapiclient.errors import HttpError
        from googleapiclient.discovery import build

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
                "values": [[now, values[0][0]]]
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

    def start_feedback_thread(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.feedback_send.configure(state="disabled")
        msg = CTkMessagebox(master=self, title="Submit",
                            message=translation["submit_feedback"],
                            icon="question",
                            option_1=translation["option_1"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            feedback_thread = threading.Thread(target=self.submit_feedback)
            feedback_thread.start()
        else:
            self.feedback_send.configure(state="normal")

    # Submits feedback from the user to a Google sheet
    def submit_feedback(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if not self.disable_feedback:
            current_date = datetime.today().strftime("%Y-%m-%d")
            date_record = self.cursor.execute("SELECT feedback_date FROM user_data").fetchone()
            if date_record is None or date_record[0] != current_date:
                feedback = self.feedback_text.get("1.0", customtkinter.END).strip()
                word_count = len(feedback.split())
                if word_count < 1000:
                    feedback = self.feedback_text.get("1.0", customtkinter.END).strip()
                    if feedback:
                        result = self.call_sheets_api([[feedback]])
                        if result:
                            def show_success():
                                if not self.disable_audio:
                                    winsound.PlaySound("sounds/success.wav", winsound.SND_ASYNC)
                                CTkMessagebox(title=translation["success_title"], icon="check",
                                              message=translation["feedback_success"], button_width=380)

                            self.after(0, show_success)
                            row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
                            if not row_exists:
                                self.cursor.execute("INSERT INTO user_data (feedback_date) VALUES (?)",
                                                    (current_date,))
                            else:
                                self.cursor.execute("UPDATE user_data SET feedback_date=?",
                                                    (current_date,))
                            self.connection.commit()
                        else:
                            if not self.connection_error:
                                def show_error():
                                    if not self.disable_audio:
                                        winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                    CTkMessagebox(title="Error",
                                                  message=translation["feedback_error"],
                                                  icon="cancel", button_width=380)

                                self.after(0, show_error)
                    else:
                        if not self.connection_error:
                            def show_error():
                                if not self.disable_audio:
                                    winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                CTkMessagebox(title="Error", message=translation["feedback_empty"],
                                              icon="cancel", button_width=380)

                            self.after(0, show_error)
                else:
                    if not self.connection_error:
                        def show_error():
                            if not self.disable_audio:
                                winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                            CTkMessagebox(title="Error", message=translation["feedback_1000"],
                                          icon="cancel", button_width=380)

                        self.after(0, show_error)
            else:
                if not self.connection_error:
                    def show_error():
                        if not self.disable_audio:
                            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                        CTkMessagebox(title="Error", message=translation["feedback_day"],
                                      icon="cancel", button_width=380)

                    self.after(0, show_error)
        else:
            if not self.connection_error:
                def show_error():
                    if not self.disable_audio:
                        winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                    CTkMessagebox(title="Error", message=translation["feedback_unavailable"],
                                  icon="cancel", button_width=380)

                self.after(0, show_error)
        self.feedback_send.configure(state="normal")

    @staticmethod
    def find_ttermpro():
        # Prioritize common installation directories
        common_paths = [
            "C:/Program Files (x86)/",
            "C:/Program Files/",
            "C:/Users/*/AppData/Local/Programs/",
        ]

        # Function to search within a given path to a certain depth
        def search_within_path(search_root, depth=7):
            for root, dirs, files in os.walk(search_root, topdown=True):
                # If we've reached the maximum depth, stop descending
                if root[len(search_root):].count(os.sep) >= depth:
                    del dirs[:]
                else:
                    dirs[:] = [d for d in dirs if
                               d not in ["Recycler", "Recycled", "System Volume Information", "$RECYCLE.BIN"]]

                for file in files:
                    if file.lower() == "ttermpro.exe":
                        return os.path.join(root, file)
            return None

        for path in common_paths:
            result = search_within_path(os.path.expandvars(path))
            if result:
                return result
        # If not found, search the entire C drive with a limited depth
        return search_within_path("C:/")

    def change_location_auto_handler(self):
        lang = self.language_menu.get()
        self.files.configure(state="disabled")
        message_english = "Do you want to automatically search for Tera Term on the C drive? " \
                          "(click  the \"no\" button if your prefer to search for it manually)\n\n" \
                          "Might take a while and make app unresponsive for a bit"
        message_spanish = "¿Desea buscar automáticamente Tera Term en la unidad C? " \
                          "(hacer clic al botón \"no\" si desea buscarlo manualmente)\n\n" \
                          "Podría tardar un poco y hacer que la aplicación no responda durante ese tiempo."
        message = message_english if lang == "English" else message_spanish
        response = messagebox.askyesnocancel("Tera Term", message)
        if response is True:
            self.auto_search = True
            task_done = threading.Event()
            loading_screen = self.show_loading_screen()
            self.update_loading_screen(loading_screen, task_done)
            event_thread = threading.Thread(target=self.change_location_event, args=(task_done,))
            event_thread.start()
        elif response is False:
            self.manually_change_location()
        else:
            self.help.lift()
            self.help.focus_set()
            if self.help is not None and self.help.winfo_exists():
                self.files.configure(state="normal")

    # Automatically tries to find where the Tera Term application is located
    def change_location_event(self, task_done):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        tera_term_path = TeraTermUI.find_ttermpro()
        if tera_term_path:
            self.location = tera_term_path.replace("\\", "/")
            directory, filename = os.path.split(self.location)
            self.teraterm_directory = directory
            self.teraterm_file = self.teraterm_directory + "/TERATERM.ini"
            row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
            if not row_exists:
                self.cursor.execute(
                    "INSERT INTO user_data (location, config, directory) VALUES (?, ?)",
                    (self.location, self.teraterm_file, self.teraterm_directory)
                )
            else:
                self.cursor.execute("UPDATE user_data SET location=?", (self.location,))
                self.cursor.execute("UPDATE user_data SET config=?", (self.teraterm_file,))
                self.cursor.execute("UPDATE user_data SET directory=?", (self.teraterm_directory,))
            self.connection.commit()
            task_done.set()
            self.changed_location = True
            self.after(100, self.show_success_message, 350, 265, translation["tera_term_success"])
            self.edit_teraterm_ini(self.teraterm_file)
            if self.help is not None and self.help.winfo_exists():
                self.files.configure(state="normal")
        else:
            task_done.set()
            message_english = ("Tera Term executable was not found on the C drive.\n\n"
                               "the application is probably not installed\nor it's located on another drive")
            message_spanish = ("No se encontró el ejecutable de Tera Term en la unidad C.\n\n"
                               "Probablemente no tiene la aplicación instalada\no está localizada en otra unidad")
            message = message_english if lang == "English" else message_spanish
            messagebox.showinfo("Tera Term", message)
            self.manually_change_location()

    # Function that lets user select where their Tera Term application is located
    def manually_change_location(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.slideshow_frame.pause_cycle()
        filename = filedialog.askopenfilename(initialdir="C:/",
                                              title=translation["select_tera_term"],
                                              filetypes=(("Tera Term", "*ttermpro.exe"),))
        if re.search("ttermpro.exe", filename):
            self.location = filename.replace("\\", "/")
            directory, filename = os.path.split(self.location)
            self.teraterm_directory = directory
            self.teraterm_file = self.teraterm_directory + "/TERATERM.ini"
            row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
            if not row_exists:
                self.cursor.execute(
                    "INSERT INTO user_data (location, config, directory) VALUES (?, ?)",
                    (self.location, self.teraterm_file, self.teraterm_directory)
                )
            else:
                self.cursor.execute("UPDATE user_data SET location=?", (self.location,))
                self.cursor.execute("UPDATE user_data SET config=?", (self.teraterm_file,))
                self.cursor.execute("UPDATE user_data SET directory=?", (self.teraterm_directory,))
            self.connection.commit()
            self.changed_location = True
            self.show_success_message(350, 265, translation["tera_term_success"])
            self.edit_teraterm_ini(self.teraterm_file)
        if not re.search("ttermpro.exe", filename):
            self.help.lift()
            self.help.focus_set()
        self.slideshow_frame.resume_cycle()
        if self.help is not None and self.help.winfo_exists():
            self.files.configure(state="normal")

    def is_listbox_focused(self):
        return self.class_list == self.class_list.focus_get()

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
        translation = self.load_language(lang)
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
            self.class_list.insert(tk.END, translation["no_results"])
        else:
            for row in results:
                self.class_list.insert(tk.END, row[0])

    # query for searching for either class code or name
    def show_class_code(self, event):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        selection = self.class_list.curselection()
        if len(selection) == 0:
            return
        selected_class = self.class_list.get(self.class_list.curselection())
        query = "SELECT code FROM courses WHERE name = ? OR code = ?"
        result = self.cursor.execute(query, (selected_class, selected_class)).fetchone()
        if result is None:
            self.class_list.delete(0, tk.END)
            self.class_list.insert(tk.END, translation["no_results"])
        else:
            self.search_box.delete(0, tk.END)
            self.search_box.insert(0, result[0])

    def help_widgets(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        bg_color = "#0e95eb"
        fg_color = "#333333"
        listbox_font = ("Arial", 11)
        self.help_frame = customtkinter.CTkScrollableFrame(self.help, width=475, height=280,
                                                           fg_color=("#e6e6e6", "#222222"))
        self.help_title = customtkinter.CTkLabel(self.help_frame, text=translation["help"],
                                                 font=customtkinter.CTkFont(size=20, weight="bold"))
        self.notice = customtkinter.CTkLabel(self.help_frame, text=translation["notice"],
                                             font=customtkinter.CTkFont(weight="bold", underline=True))
        self.searchbox_text = customtkinter.CTkLabel(self.help_frame, text=translation["searchbox_title"])
        self.search_box = CustomEntry(self.help_frame, self, lang, placeholder_text=translation["searchbox"])
        self.search_box.is_listbox_entry = True
        self.class_list = tk.Listbox(self.help_frame, width=35, bg=bg_color, fg=fg_color, font=listbox_font)
        self.curriculum_text = customtkinter.CTkLabel(self.help_frame, text=translation["curriculums_title"])
        self.curriculum = customtkinter.CTkOptionMenu(self.help_frame,
                                                      values=[translation["dep"], translation["acc"],
                                                              translation["finance"], translation["management"],
                                                              translation["mark"], translation["g_biology"],
                                                              translation["h_biology"], translation["c_science"],
                                                              translation["it"], translation["s_science"],
                                                              translation["physical"], translation["elec"],
                                                              translation["equip"], translation["peda"],
                                                              translation["che"], translation["nur"],
                                                              translation["office"], translation["engi"]],
                                                      command=TeraTermUI.curriculums, height=30, width=150)
        self.keybinds_text = customtkinter.CTkLabel(self.help_frame, text=translation["keybinds_title"],
                                                    font=customtkinter.CTkFont(weight="bold", size=15))
        self.keybinds = [[translation["keybind"], translation["key_function"]],
                         ["<Return> / <Enter>", translation["return"]],
                         ["<Escape>", translation["escape"]],
                         ["<Ctrl-BackSpace>", translation["ctrl_backspace"]],
                         ["<Arrow-Keys>", translation["arrow_keys"]],
                         ["<SpaceBar>", translation["space_bar"]],
                         ["<Ctrl-Tab>", translation["ctrl_tab"]],
                         ["<Ctrl-Space>", translation["ctrl_space"]],
                         ["<Ctrl-C>", translation["ctrl_c"]],
                         ["<Ctrl-V>", translation["ctrl_v"]],
                         ["<Ctrl-X>", translation["ctrl_x"]],
                         ["<Ctrl-Z>", translation["ctrl_z"]],
                         ["<Ctrl-Y>", translation["ctrl_y"]],
                         ["<Ctrl-A>", translation["ctrl_a"]],
                         ["<Right-Click>", translation["mouse_2"]],
                         ["<Home>", translation["home"]],
                         ["<End>", translation["end"]],
                         ["<Alt-F4>", translation["alt_f4"]]]
        self.terms_text = customtkinter.CTkLabel(self.help_frame, text=translation["terms_title"],
                                                 font=customtkinter.CTkFont(weight="bold", size=15))
        self.terms = [[translation["terms_year"], translation["terms_term"]],
                      ["2019", "B91, B92, B93"],
                      ["2020", "C01, C02, C03"],
                      ["2021", "C11, C12, C13"],
                      ["2022", "C21, C22, C23"],
                      ["2023", "C31, C32, C33"],
                      [translation["semester"], translation["seasons"]]]
        self.skip_auth_text = customtkinter.CTkLabel(self.help_frame, text=translation["skip_auth_text"])
        self.skip_auth_switch = customtkinter.CTkSwitch(self.help_frame, text=translation["skip_auth_switch"],
                                                        onvalue="on", offvalue="off", command=self.disable_enable_auth)
        self.files_text = customtkinter.CTkLabel(self.help_frame, text=translation["files_title"])
        self.files = CustomButton(self.help_frame, image=self.get_image("folder"), text=translation["files_button"],
                                  anchor="w", text_color=("gray10", "#DCE4EE"),
                                  command=self.change_location_auto_handler)
        self.disable_idle_text = customtkinter.CTkLabel(self.help_frame, text=translation["idle_title"])
        self.disable_idle = customtkinter.CTkSwitch(self.help_frame, text=translation["idle"], onvalue="on",
                                                    offvalue="off", command=self.disable_enable_idle)
        self.disable_audio_text = customtkinter.CTkLabel(self.help_frame, text=translation["audio_title"])
        self.disable_audio_val = customtkinter.CTkSwitch(self.help_frame, text=translation["audio"], onvalue="on",
                                                         offvalue="off", command=self.disable_enable_audio)
        self.fix_text = customtkinter.CTkLabel(self.help_frame, text=translation["fix_title"])
        self.fix = CustomButton(self.help_frame, image=self.get_image("fix"), text=translation["fix"], anchor="w",
                                text_color=("gray10", "#DCE4EE"), command=self.fix_execution_event_handler)
        if not self.main_menu:
            self.files.configure(state="disabled")
        if not self.run_fix:
            self.fix.configure(state="disabled")

    # Creates the Help window
    def help_button_event(self):
        if self.help and self.help.winfo_exists():
            windows_help = gw.getWindowsWithTitle("Help") + gw.getWindowsWithTitle("Ayuda")
            self.help_minimized = windows_help[0].isMinimized
            if self.help_minimized:
                self.help.deiconify()
            self.help.lift()
            self.help.focus_set()
            return
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.help = SmoothFadeToplevel()
        self.help_widgets()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        scaling_factor = self.tk.call("tk", "scaling")
        x_position = int((screen_width - 475 * scaling_factor) / 2)
        y_position = int((screen_height - 275 * scaling_factor) / 2)
        window_geometry = f"{475}x{280}+{x_position + 130}+{y_position + 18}"
        self.help.geometry(window_geometry)
        self.help.title(translation["help"])
        self.help.iconbitmap(self.icon_path)
        self.help.resizable(False, False)
        self.help_frame.pack()
        self.help_title.pack()
        self.notice.pack()
        self.searchbox_text.pack()
        self.search_box.pack(pady=10)
        self.class_list.pack()
        self.curriculum_text.pack()
        if lang == "English":
            self.curriculum.pack(pady=(5, 0))
        elif lang == "Español":
            self.curriculum.pack(pady=(5, 20))
        self.terms_text.pack()
        self.terms_table = CTkTable(self.help_frame, column=2, row=7, values=self.terms, hover=False)
        self.terms_table.pack(expand=True, fill="both", padx=20, pady=10)
        self.keybinds_text.pack(pady=(20, 0))
        self.keybinds_table = CTkTable(self.help_frame, column=2, row=17, values=self.keybinds, hover=False)
        self.keybinds_table.pack(expand=True, fill="both", padx=20, pady=10)
        if not self.ask_skip_auth:
            self.skip_auth_text.pack()
            self.skip_auth_switch.pack()
        self.files_text.pack()
        self.files.pack(pady=5)
        self.disable_idle_text.pack()
        self.disable_idle.pack()
        self.disable_audio_text.pack()
        self.disable_audio_val.pack()
        self.fix_text.pack()
        self.fix.pack(pady=5)
        idle = self.cursor.execute("SELECT idle FROM user_data").fetchone()
        audio = self.cursor.execute("SELECT audio FROM user_data").fetchone()
        skip_auth = self.cursor.execute("SELECT skip_auth FROM user_data").fetchone()
        if idle and idle[0] is not None:
            if idle[0] == "Disabled":
                self.disable_idle.select()
        if audio and audio[0] is not None:
            if audio[0] == "Disabled":
                self.disable_audio_val.select()
        if skip_auth and skip_auth[0] is not None:
            if skip_auth[0] == "Yes":
                self.skip_auth_switch.select()
        self.search_box.lang = lang
        self.help.focus_set()
        self.class_list.bind("<<ListboxSelect>>", self.show_class_code)
        self.class_list.bind("<MouseWheel>", self.disable_scroll)
        self.search_box.bind("<KeyRelease>", self.search_classes)
        self.help_frame.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.help_frame.bind("<Button-3>", lambda event: self.help_frame.focus_set())
        self.help.bind("<Up>", lambda event: None if self.is_listbox_focused() else self.help_scroll_up())
        self.help.bind("<Down>", lambda event: None if self.is_listbox_focused() else self.help_scroll_down())
        self.help.bind("<Home>", lambda event: None if self.is_listbox_focused() else self.help_move_top_scrollbar())
        self.help.bind("<End>", lambda event: None if self.is_listbox_focused() else self.help_move_bottom_scrollbar())
        self.help.protocol("WM_DELETE_WINDOW", self.on_help_window_close)
        self.help.bind("<Escape>", lambda event: self.on_help_window_close())

    def on_help_window_close(self):
        self.unload_image("folder")
        self.unload_image("fix")
        self.move_slider_left_enabled = True
        self.move_slider_right_enabled = True
        self.spacebar_enabled = True
        self.up_arrow_key_enabled = True
        self.down_arrow_key_enabled = True
        self.help.destroy()

    def help_scroll_up(self):
        if self.up_arrow_key_enabled:
            self.help_frame.scroll_more_up()

    def help_scroll_down(self):
        if self.down_arrow_key_enabled:
            self.help_frame.scroll_more_down()

    def help_move_top_scrollbar(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            self.help_frame.scroll_to_top()

    def help_move_bottom_scrollbar(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            self.help_frame.scroll_to_bottom()

    # Gets the latest release of the application on GitHub
    def get_latest_release(self):
        lang = self.language_menu.get()
        if asyncio.run(self.test_connection(lang)):
            url = f"{self.GITHUB_REPO}/releases/latest"
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

    # Compares the current version that user is using with the latest available
    @staticmethod
    def compare_versions(latest_version, user_version):
        if latest_version is None or user_version is None:
            return False
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
        if TeraTermUI.is_file_in_directory("ttermpro.exe", self.teraterm_directory):
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
                for index, line in enumerate(lines):
                    if line.startswith("VTFont="):
                        current_value = line.strip().split("=")[1]
                        font_name = current_value.split(",")[0]
                        self.original_font = current_value
                        updated_value = "Lucida Console" + current_value[len(font_name):]
                        lines[index] = f"VTFont={updated_value}\n"
                        self.can_edit = True
                with open(file_path, "w") as file:
                    file.writelines(lines)
            except FileNotFoundError:
                return
            # If something goes wrong, restore the backup
            except Exception as e:
                print(f"Error occurred: {e}")
                print("Restoring from backup...")
                shutil.copyfile(backup_path, file_path)
            del line, lines
            gc.collect()

    # Restores the original font option the user had
    def restore_original_font(self, file_path):
        if not self.can_edit:
            return
        backup_path = self.app_temp_dir / "TERATERM.ini.bak"
        try:
            # Read lines once from the main file and the backup
            with open(file_path, "r") as file:
                lines = file.readlines()
            with open(backup_path, "r") as backup_file:
                backup_lines = backup_file.readlines()
            # Find the backup font
            backup_font = None
            for line in backup_lines:
                if line.startswith("VTFont="):
                    backup_font = line.strip().split("=")[1]
                    break
            # If backup font doesn't exist, return
            if backup_font is None:
                return
            # Edit lines in-place
            for index, line in enumerate(lines):
                if line.startswith("VTFont="):
                    if backup_font.split(",")[0].lower() != self.original_font.split(",")[0].lower():
                        lines[index] = f"VTFont={backup_font}\n"
                    else:
                        lines[index] = f"VTFont={self.original_font}\n"
            # Write lines back to the file
            with open(file_path, "w") as file:
                file.writelines(lines)
        except FileNotFoundError:
            print(f"File or backup not found.")
        except IOError as e:  # Replace with specific exceptions you want to catch
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
            self.status.iconify()

        if self.help is not None and self.help.winfo_exists() and not self.help_minimized:
            self.help.iconify()

    # When the user performs an action to do something in tera term it destroys windows that might get in the way
    def destroy_windows(self):
        if self.error and self.error.winfo_exists():
            self.error.destroy()
        if self.success and self.success.winfo_exists():
            self.success.destroy()
        if self.information and self.information.winfo_exists():
            self.information.destroy()

    def get_image(self, image_name):
        if image_name not in self.image_cache:
            if image_name == "folder":
                self.image_cache["folder"] = customtkinter.CTkImage(light_image=Image.open("images/folder.png"),
                                                                    size=(18, 18))
            elif image_name == "fix":
                self.image_cache["fix"] = customtkinter.CTkImage(light_image=Image.open("images/fix.png"),
                                                                 size=(15, 15))
            elif image_name == "error":
                self.image_cache["error"] = customtkinter.CTkImage(light_image=Image.open("images/error.png"),
                                                                   size=(100, 100))
            elif image_name == "information":
                self.image_cache["information"] = customtkinter.CTkImage(light_image=Image.open("images/info.png"),
                                                                         size=(100, 100))
            elif image_name == "success":
                self.image_cache["success"] = customtkinter.CTkImage(light_image=Image.open("images/success.png"),
                                                                     size=(200, 150))
            elif image_name == "status":
                self.image_cache["status"] = customtkinter.CTkImage(light_image=Image.open("images/home.png"),
                                                                    size=(20, 20))
            elif image_name == "help":
                self.image_cache["help"] = customtkinter.CTkImage(light_image=Image.open("images/setting.png"),
                                                                  size=(18, 18))
            elif image_name == "uprb":
                self.image_cache["uprb"] = customtkinter.CTkImage(light_image=Image.open("images/uprb.jpg"),
                                                                  size=(300, 100))
            elif image_name == "lock":
                self.image_cache["lock"] = customtkinter.CTkImage(light_image=Image.open("images/lock.png"),
                                                                  size=(75, 75))
            elif image_name == "update":
                self.image_cache["update"] = customtkinter.CTkImage(light_image=Image.open("images/update.png"),
                                                                    size=(15, 15))
            elif image_name == "link":
                self.image_cache["link"] = customtkinter.CTkImage(light_image=Image.open("images/link.png"),
                                                                  size=(15, 15))
        return self.image_cache.get(image_name)

    def unload_image(self, image_name):
        if image_name in self.image_cache:
            del self.image_cache[image_name]

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
            classes = self.m_classes_entry[i].get().upper().replace(" ", "").replace("-", "")
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
            elif not re.fullmatch("^[A-Z]{2}[A-Z0-9]$", sections, flags=re.IGNORECASE):
                error_msg_short = translation["multiple_section_format_error"]
                break
            elif not re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE):
                error_msg_short = translation["multiple_semester_format_error"]
                break
            if choices in ["Register", "Registra"]:
                if sections in self.enrolled_classes_list and self.enrolled_classes_list[sections] == classes:
                    error_msg_long = translation["multiple_already_enrolled"]
                    break
            elif choices in ["Drop", "Baja"]:
                if sections in self.dropped_classes_list and self.dropped_classes_list[sections] == classes:
                    error_msg_long = translation["multiple_already_dropped"]
                    break

        # Display error messages or proceed if no errors
        if error_msg_short:
            self.after(100, self.show_error_message, 345, 235, error_msg_short)
            if self.auto_enroll_bool:
                self.auto_enroll_bool = False
                self.auto_enroll.deselect()
            return False
        elif error_msg_medium:
            self.after(100, self.show_error_message, 355, 240, error_msg_medium)
            if self.auto_enroll_bool:
                self.auto_enroll_bool = False
                self.auto_enroll.deselect()
            return False
        elif error_msg_long:
            self.after(100, self.show_error_message, 390, 245, error_msg_long)
            if self.auto_enroll_bool:
                self.auto_enroll_bool = False
                self.auto_enroll.deselect()
            return False

        self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
        return True


class CustomButton(customtkinter.CTkButton):
    def __init__(self, master=None, command=None, **kwargs):
        super().__init__(master, cursor="hand2", **kwargs)
        self.text = kwargs.pop("text", None)
        self.image = kwargs.pop("image", None)

        self.is_pressed = False
        self.click_command = command
        if self.image and not self.text:
            self.configure(image=self.image)
        else:
            self.bind("<Enter>", self.on_enter)
            self.bind("<Leave>", self.on_leave)
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

    def on_enter(self, event):
        self.configure(cursor="hand2")

    def on_leave(self, event):
        self.configure(cursor="")


class CustomScrollableFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _mouse_wheel_all(self, event):
        # Get the currently focused widget
        focused_widget = self.focus_get()

        # Check if the focused widget is a tk.Text
        if isinstance(focused_widget, tk.Text):
            # Check if a scrollbar is needed for the text widget
            scrollbar_needed = CustomScrollableFrame._is_scrollbar_needed(focused_widget)

            # Check if the mouse is within the bounds of the text widget
            mouse_within_text_widget = CustomScrollableFrame._is_mouse_within_widget(focused_widget, event)

            if scrollbar_needed and mouse_within_text_widget:
                # Scroll the text widget
                CustomScrollableFrame._scroll_text_widget(focused_widget, event)
                return

        # Perform the normal scroll action for other cases
        super()._mouse_wheel_all(event)

    @staticmethod
    def _is_scrollbar_needed(text_widget):
        # Check if the content of the text widget exceeds its viewable area
        first, last = text_widget.yview()
        return first > 0 or last < 1

    @staticmethod
    def _is_mouse_within_widget(widget, event):
        # Get mouse position relative to the widget
        mouse_x = widget.winfo_pointerx() - widget.winfo_rootx()
        mouse_y = widget.winfo_pointery() - widget.winfo_rooty()
        # Check if the mouse is over the widget
        return 0 <= mouse_x < widget.winfo_width() and 0 <= mouse_y < widget.winfo_height()

    @staticmethod
    def _scroll_text_widget(text_widget, event):
        # Scroll the text widget based on the mouse wheel event
        if event.num == 5 or event.delta == -120:
            text_widget.yview_scroll(1, "units")
        elif event.num == 4 or event.delta == 120:
            text_widget.yview_scroll(-1, "units")


class CustomTextBox(customtkinter.CTkTextbox):
    def __init__(self, master, teraterm_ui_instance, enable_autoscroll=True, read_only=False, lang=None, **kwargs):
        super().__init__(master, **kwargs)
        self.auto_scroll = enable_autoscroll
        self.lang = lang
        self.read_only = read_only
        self.disabled_autoscroll = False
        self.after_id = None
        self.teraterm_ui = teraterm_ui_instance

        if self.auto_scroll:
            self.update_text()

        # Event binding
        self.bind("<Button-1>", self.stop_autoscroll)
        self.bind("<MouseWheel>", self.stop_autoscroll)
        self.bind("<FocusIn>", self.disable_slider_keys)
        self.bind("<FocusOut>", self.enable_slider_keys)

        if hasattr(self, "_y_scrollbar"):
            self._y_scrollbar.bind("<Button-1>", self.stop_autoscroll)
            self._y_scrollbar.bind("<B1-Motion>", self.stop_autoscroll)
        if hasattr(self, "_x_scrollbar"):
            self._x_scrollbar.bind("<Button-1>", self.stop_autoscroll)
            self._x_scrollbar.bind("<B1-Motion>", self.stop_autoscroll)

        initial_state = self.get("1.0", "end-1c")
        self._undo_stack = deque([initial_state], maxlen=100)
        self._redo_stack = deque(maxlen=100)

        # Bind Control-Z to undo and Control-Y to redo
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-Z>", self.undo)
        self.bind("<Control-y>", self.redo)
        self.bind("<Control-Y>", self.redo)

        self.bind("<Button-2>", self.select_all)
        self.bind("<Control-a>", self.select_all)
        self.bind("<Control-A>", self.select_all)

        # Update the undo stack every time the Entry content changes
        self.bind("<KeyRelease>", self.update_undo_stack)

        if self.read_only:
            self.bind("<Up>", self.scroll_more_up)
            self.bind("<Down>", self.scroll_more_down)

        # Context Menu
        self.context_menu = tk.Menu(self, tearoff=0, bg="#f0f0f0", fg="#333333", font=("Arial", 10))
        if not self.read_only:
            self.context_menu.add_command(label="Cut", command=self.cut)
        self.context_menu.add_command(label="Copy", command=self.copy)
        if not self.read_only:
            self.context_menu.add_command(label="Paste", command=self.paste)
        self.context_menu.add_command(label="Select All", command=self.select_all)
        self.bind("<Button-3>", self.show_menu)

        if self.read_only:
            self.bind("<Key>", CustomTextBox.readonly)

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

    def update_text(self):
        if self.after_id:
            self.after_cancel(self.after_id)

        if self.auto_scroll:
            _, yview_fraction = self.yview()
            if yview_fraction >= 1.0:
                self.yview_moveto(0)  # Reset to the top
            else:
                self.yview_scroll(1, "units")  # Scroll down 1 pixel
            self.after_id = self.after(8000, self.update_text)  # Store the ID

    def stop_autoscroll(self, event=None):
        self.auto_scroll = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None

        if event is not None:
            self.disabled_autoscroll = True

    def restart_autoscroll(self):
        self.auto_scroll = True
        if self.after_id:
            self.after_cancel(self.after_id)
        self.after_id = self.after(8000, self.update_text)

    def reset_autoscroll(self):
        if self.auto_scroll:
            if self.after_id:
                self.after_cancel(self.after_id)
        self.update_text()
        self.yview_moveto(0)

    def update_undo_stack(self, event=None):
        current_text = self.get("1.0", "end-1c")
        if current_text != self._undo_stack[-1]:
            self._undo_stack.append(current_text)
            self._redo_stack.clear()

    def undo(self, event=None):
        if len(self._undo_stack) > 1:
            self._redo_stack.append(self._undo_stack.pop())
            self.delete("1.0", "end")
            self.insert("1.0", self._undo_stack[-1])

    def redo(self, event=None):
        if self._redo_stack:
            redo_text = self._redo_stack.pop()
            self._undo_stack.append(redo_text)
            self.delete("1.0", "end")
            self.insert("1.0", redo_text)

    def show_menu(self, event):
        self.focus_set()
        self.mark_set(tk.INSERT, "end")
        self.stop_autoscroll(event=None)

        # Update the menu labels based on the current language
        if self.lang == "English" and not self.read_only:
            self.context_menu.entryconfigure(0, label="Cut")
            self.context_menu.entryconfigure(1, label="Copy")
            self.context_menu.entryconfigure(2, label="Paste")
            self.context_menu.entryconfigure(3, label="Select All")
        elif self.lang == "Español" and not self.read_only:
            self.context_menu.entryconfigure(0, label="Cortar")
            self.context_menu.entryconfigure(1, label="Copiar")
            self.context_menu.entryconfigure(2, label="Pegar")
            self.context_menu.entryconfigure(3, label="Seleccionar Todo")

        if self.lang == "English" and self.read_only:
            self.context_menu.entryconfigure(0, label="Copy")
            self.context_menu.entryconfigure(1, label="Select All")

        elif self.lang == "Español" and self.read_only:
            self.context_menu.entryconfigure(0, label="Copiar")
            self.context_menu.entryconfigure(1, label="Seleccionar Todo")

        # Update the label of the context menu based on the selection state
        if self.tag_ranges(tk.SEL):
            if self.lang == "English":
                self.context_menu.entryconfigure(3, label="Unselect All")
            elif self.lang == "Español":
                self.context_menu.entryconfigure(3, label="Deseleccionar Todo")
        else:
            if self.lang == "English":
                self.context_menu.entryconfigure(3, label="Select All")
            elif self.lang == "Español":
                self.context_menu.entryconfigure(3, label="Seleccionar Todo")

        self.context_menu.post(event.x_root, event.y_root)

    def cut(self):
        self.focus_set()
        if not self.tag_ranges(tk.SEL):
            self.tag_add(tk.SEL, "1.0", tk.END)
        try:
            selected_text = self.selection_get()  # Attempt to get selected text
            current_text = self.get("1.0", "end-1c")  # Existing text in the Text widget
            self._undo_stack.append(current_text)  # Save the current state to undo stack

            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.delete(tk.SEL_FIRST, tk.SEL_LAST)

            new_text = self.get("1.0", "end-1c")
            self._undo_stack.append(new_text)

            self._redo_stack = []
        except tk.TclError:
            print("No text selected to cut.")  # Log or inform the user accordingly

    def copy(self):
        self.focus_set()
        self.stop_autoscroll(event=None)
        if not self.tag_ranges(tk.SEL):
            self.tag_add(tk.SEL, "1.0", tk.END)
        try:
            selected_text = self.selection_get()  # Attempt to get selected text
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            print("No text selected to copy.")  # Log or inform the user accordingly

    def paste(self, event=None):
        self.focus_set()
        try:
            clipboard_text = self.clipboard_get()  # Get text from clipboard
            current_text = self.get("1.0", "end-1c")  # Existing text in the Text widget
            self._undo_stack.append(current_text)  # Save the current state to undo stack

            try:
                start_index = self.index(tk.SEL_FIRST)
                end_index = self.index(tk.SEL_LAST)
                self.delete(start_index, end_index)  # Remove selected text if any
            except tk.TclError:
                pass  # Nothing selected, which is fine

            self.insert(tk.INSERT, clipboard_text)  # Insert the clipboard text
            self._redo_stack.clear()  # Clear redo stack after a new operation

            new_text = self.get("1.0", "end-1c")
            if new_text != self._undo_stack[-1]:
                self._undo_stack.append(new_text)
        except tk.TclError:
            pass  # Clipboard empty or other issue

    def select_all(self, event=None):
        self.focus_set()
        self.stop_autoscroll(event=None)
        self.mark_set(tk.INSERT, "end")
        try:
            # Check if any text is currently selected
            if self.tag_ranges(tk.SEL):
                # Clear the selection if text is already selected
                self.tag_remove(tk.SEL, "1.0", tk.END)
                if self.read_only:
                    self.teraterm_ui.focus_set()
            else:
                # Select all text if nothing is selected
                self.tag_add(tk.SEL, "1.0", tk.END)
                self.mark_set(tk.INSERT, "1.0")
                self.see(tk.INSERT)
        except tk.TclError:
            pass  # Handle any exceptions if needed
        return "break"

    def scroll_more_up(self, event=None, scroll_units=1):
        current_view = self.yview()
        if current_view[0] > 0:
            self.yview_scroll(-scroll_units, "units")

    def scroll_more_down(self, event=None, scroll_units=1):
        current_view = self.yview()
        if current_view[1] < 1:
            self.yview_scroll(scroll_units, "units")

    @staticmethod
    def readonly(event):
        if event.keysym not in ("Control_R", "Control_L", "c"):
            return "break"


class CustomEntry(customtkinter.CTkEntry):
    def __init__(self, master, teraterm_ui_instance, lang=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        initial_state = self.get()
        self._undo_stack = deque([initial_state], maxlen=25)
        self._redo_stack = deque(maxlen=25)
        self.lang = lang
        self.is_listbox_entry = False

        self.teraterm_ui = teraterm_ui_instance
        self.bind("<FocusIn>", self.disable_slider_keys)
        self.bind("<FocusOut>", self.enable_slider_keys)

        # Bind Control-Z to undo and Control-Y to redo
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-Z>", self.undo)
        self.bind("<Control-y>", self.redo)
        self.bind("<Control-Y>", self.redo)

        self.bind("<Button-2>", self.select_all)
        self.bind("<Control-a>", self.select_all)
        self.bind("<Control-A>", self.select_all)

        # Update the undo stack every time the Entry content changes
        self.bind("<KeyRelease>", self.update_undo_stack)

        # Context Menu
        self.context_menu = tk.Menu(self, tearoff=0, bg="#f0f0f0", fg="#333333", font=("Arial", 10))
        self.context_menu.add_command(label="Cut", command=self.cut)
        self.context_menu.add_command(label="Copy", command=self.copy)
        self.context_menu.add_command(label="Paste", command=self.paste)
        self.context_menu.add_command(label="Select All", command=self.select_all)
        self.bind("<Control-v>", self.paste)
        self.bind("<Control-V>", self.paste)
        self.bind("<Button-3>", self.show_menu)

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
        if current_text != self._undo_stack[-1]:
            self._undo_stack.append(current_text)
            self._redo_stack.clear()  # Clear the redo stack whenever a new change is made

    def undo(self, event=None):
        if len(self._undo_stack) > 1:
            self._redo_stack.append(self._undo_stack.pop())
            previous_state = self._undo_stack[-1]
            self.delete(0, "end")
            self.insert(0, previous_state)
            if self.is_listbox_entry:
                self.update_listbox()

    def redo(self, event=None):
        if self._redo_stack:
            state_to_redo = self._redo_stack.pop()
            self._undo_stack.append(state_to_redo)
            self.delete(0, "end")
            self.insert(0, state_to_redo)
            if self.is_listbox_entry:
                self.update_listbox()

    def show_menu(self, event):
        if self.cget("state") == "disabled":
            return

        self.focus_set()
        self.icursor(tk.END)

        # Update the menu labels based on the current language
        if self.lang == "English":
            self.context_menu.entryconfigure(0, label="Cut")
            self.context_menu.entryconfigure(1, label="Copy")
            self.context_menu.entryconfigure(2, label="Paste")
            self.context_menu.entryconfigure(3, label="Select All")
        elif self.lang == "Español":
            self.context_menu.entryconfigure(0, label="Cortar")
            self.context_menu.entryconfigure(1, label="Copiar")
            self.context_menu.entryconfigure(2, label="Pegar")
            self.context_menu.entryconfigure(3, label="Seleccionar Todo")

        # Update the label of the context menu based on the selection state
        if self.select_present():
            if self.lang == "English":
                self.context_menu.entryconfigure(3, label="Unselect All")
            elif self.lang == "Español":
                self.context_menu.entryconfigure(3, label="Deseleccionar Todo")
        else:
            if self.lang == "English":
                self.context_menu.entryconfigure(3, label="Select All")
            elif self.lang == "Español":
                self.context_menu.entryconfigure(3, label="Seleccionar Todo")

        self.context_menu.post(event.x_root, event.y_root)

    def cut(self):
        self.focus_set()
        if not self.select_present():
            self.select_range(0, "end")
        try:
            selected_text = self.selection_get()  # Attempt to get selected text
            current_text = self.get()  # Existing text in the Entry widget

            # Save the current state to undo stack
            self._undo_stack.append(current_text)

            # Perform the cut operation
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.delete(tk.SEL_FIRST, tk.SEL_LAST)
            if self.is_listbox_entry:
                self.update_listbox()

            # Update the undo stack with the new state
            new_text = self.get()
            self._undo_stack.append(new_text)

            # Optionally, clear the redo stack
            self._redo_stack = []

        except tk.TclError:
            print("No text selected to cut.")  # Log or inform the user accordingly

    def copy(self):
        self.focus_set()
        if not self.select_present():
            self.select_range(0, "end")
        try:
            selected_text = self.selection_get()  # Attempt to get selected text
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            print("No text selected to copy.")  # Log or inform the user accordingly

    def paste(self, event=None):
        self.focus_set()
        try:
            clipboard_text = self.clipboard_get()  # Get text from clipboard
            max_paste_length = 1000  # Set a limit for the max paste length
            if len(clipboard_text) > max_paste_length:
                clipboard_text = clipboard_text[:max_paste_length]  # Truncate to max length
                print("Pasted content truncated to maximum length.")

            current_text = self.get()  # Existing text in the Entry widget
            # Save the current state to undo stack
            if len(self._undo_stack) == 0 or (len(self._undo_stack) > 0 and current_text != self._undo_stack[-1]):
                self._undo_stack.append(current_text)

            try:
                start_index = self.index(tk.SEL_FIRST)
                end_index = self.index(tk.SEL_LAST)
                self.delete(start_index, end_index)  # Remove selected text if any
            except tk.TclError:
                pass  # Nothing selected, which is fine

            self.insert(tk.INSERT, clipboard_text)  # Insert the clipboard text

            # Update undo stack here, after paste operation
            self.update_undo_stack()

            if self.is_listbox_entry:
                self.update_listbox()
        except tk.TclError:
            pass  # Clipboard empty or other issue
        return "break"

    def select_all(self, event=None):
        if self.cget("state") == "disabled":
            return

        self.focus_set()
        self.icursor(tk.END)
        try:
            # Check if any text is currently selected
            if self.select_present():
                # Clear the selection if text is already selected
                self.select_clear()
            else:
                # Select all text if nothing is selected
                self.select_range(0, "end")
                self.icursor("end")
        except tk.TclError:
            # No text was selected, so select all
            self.select_range(0, "end")
            self.icursor("end")
        return "break"

    def insert(self, index, string):
        super().insert(index, string)
        self.update_undo_stack()

    def update_listbox(self):
        self.teraterm_ui.search_classes(None)


class CustomComboBox(customtkinter.CTkComboBox):
    def __init__(self, master, teraterm_ui_instance, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        initial_state = self.get()
        self._undo_stack = deque([initial_state], maxlen=25)
        self._redo_stack = deque(maxlen=25)

        self.teraterm_ui = teraterm_ui_instance
        self.bind("<FocusIn>", self.disable_slider_keys)
        self.bind("<FocusOut>", self.enable_slider_keys)

        # Bind Control-Z to undo and Control-Y to redo
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-Z>", self.undo)
        self.bind("<Control-y>", self.redo)
        self.bind("<Control-Y>", self.redo)

        # Update the undo stack every time the Entry content changes
        self.bind("<KeyRelease>", self.update_undo_stack)

        self.bind("<Control-v>", self.paste)
        self.bind("<Control-V>", self.paste)

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

    def set(self, value):
        # Call the original set method
        super().set(value)
        # Explicitly update the undo stack after setting a new value
        self.update_undo_stack()

    def update_undo_stack(self, event=None):
        current_text = self.get()
        # Check for a change in text and avoid duplicating the last entry
        if len(self._undo_stack) == 0 or (current_text != self._undo_stack[-1]):
            self._undo_stack.append(current_text)
            self._redo_stack.clear()  # Clear the redo stack on a new change

    def _dropdown_callback(self, value: str):
        # Save current value to undo stack before changing
        current_text = self.get()
        if current_text != self._undo_stack[-1]:
            self._undo_stack.append(current_text)

        super()._dropdown_callback(value)  # Call the original dropdown callback

        # Update undo stack with new value
        new_text = self.get()
        if new_text != self._undo_stack[-1]:
            self._undo_stack.append(new_text)

    def undo(self, event=None):
        if len(self._undo_stack) > 1:
            last_text = self._undo_stack.pop()
            self._redo_stack.append(last_text)
            self.set(self._undo_stack[-1])

    def redo(self, event=None):
        if self._redo_stack:
            redo_text = self._redo_stack.pop()
            self._undo_stack.append(redo_text)
            self.set(redo_text)

    def paste(self, event=None):
        self.focus_set()
        try:
            clipboard_text = self.clipboard_get()  # Get text from clipboard
            max_paste_length = 1000  # Set a limit for the max paste length
            if len(clipboard_text) > max_paste_length:
                clipboard_text = clipboard_text[:max_paste_length]  # Truncate to max length
                print("Pasted content truncated to maximum length.")

            current_text = self.get()  # Existing text in the Entry widget

            if clipboard_text != current_text:  # Only proceed if there's an actual change
                self.set(clipboard_text)

                # Update undo stack here, after paste operation
                new_text = self.get()
                if len(self._undo_stack) == 0 or (new_text != self._undo_stack[-1]):
                    self._undo_stack.append(new_text)
                    self._redo_stack.clear()  # Clear the redo stack after a new change
        except tk.TclError:
            pass  # Clipboard empty or other issue
        return "break"


class SmoothFadeToplevel(customtkinter.CTkToplevel):
    def __init__(self, fade_duration=30, *args, **kwargs):
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


class SmoothFadeInputDialog(customtkinter.CTkInputDialog):
    def __init__(self, fade_duration=15, *args, **kwargs):
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
        self.image_files = []
        self.current_image = None

        self.load_images()
        self.index = 0  # Added index to keep track of the current position in the list

        self.label = customtkinter.CTkLabel(self.slideshow_frame, text="")
        self.label.bind("<Button-1>", lambda event: self.focus_set())
        self.label.grid(row=0, column=1)

        self.arrow_left = CustomButton(self.slideshow_frame, text="<", command=self.prev_image, width=25)
        self.arrow_left.bind("<Button-1>", lambda event: self.focus_set())
        self.arrow_left.grid(row=0, column=0)

        self.arrow_right = CustomButton(self.slideshow_frame, text=">", command=self.next_image, width=25)
        self.arrow_right.bind("<Button-1>", lambda event: self.focus_set())
        self.arrow_right.grid(row=0, column=2)

        self.after_id = self.slideshow_frame.after(1, lambda: None)
        self.slideshow_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.is_running = True
        self.show_image()

    def focus_set(self):
        self.slideshow_frame.focus_set()

    def grid(self, **kwargs):
        self.slideshow_frame.grid(**kwargs)

    def grid_forget(self):
        self.slideshow_frame.grid_forget()

    def load_images(self):
        image_files = [f for f in os.listdir(self.image_folder) if f.endswith(("png", "gif", "jpg", "jpeg"))]
        self.image_files = sorted(image_files)

    def show_image(self):
        # Delete the previous image from memory
        if hasattr(self, "current_image"):
            del self.current_image
            gc.collect()

        # Load and show the current image
        filepath = os.path.join(self.image_folder, self.image_files[self.index])
        self.current_image = customtkinter.CTkImage(
            light_image=Image.open(filepath).resize((self.width * 2, self.height * 2)),
            size=(self.width, self.height)
        )
        self.label.configure(image=self.current_image)

        self.slideshow_frame.after_cancel(self.after_id)  # Cancel the existing timer
        self.reset_timer()  # Reset the timer after showing the image

    def cycle_images(self):
        self.index = (self.index + 1) % len(self.image_files)  # Advance to the next image in the list
        self.show_image()  # Show the new image and reset the timer

    def prev_image(self):
        self.index = (self.index - 1) % len(self.image_files)  # Decrease index and wrap around if needed
        self.show_image()  # Show the new image and reset the timer

    def next_image(self):
        self.index = (self.index + 1) % len(self.image_files)  # Increase index and wrap around if needed
        self.show_image()  # Show the new image and reset the timer

    def go_to_first_image(self):
        self.index = 0  # Reset index to the first image
        self.show_image()  # Show the first image

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


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG)]


def get_window_rect(hwnd):
    rect = RECT()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    DwmGetWindowAttribute = ctypes.windll.dwmapi.DwmGetWindowAttribute
    DwmGetWindowAttribute.restype = wintypes.LONG
    DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.POINTER(RECT), wintypes.DWORD]
    DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def bring_to_front(window_title):
    try:
        win = gw.getWindowsWithTitle(window_title)[0]
        win.activate()
    except IndexError:
        print("Window not found.")


def main():
    import sys

    tera_term_temp_dir = os.path.join(tempfile.gettempdir(), "TeraTermUI")
    if not os.path.exists(tera_term_temp_dir):
        os.makedirs(tera_term_temp_dir)
    lock_file_temp = os.path.join(tera_term_temp_dir, "app_lock.lock")
    file_lock = FileLock(lock_file_temp, timeout=0)
    try:
        with file_lock.acquire():
            app = TeraTermUI()
            app.mainloop()
    except Timeout:
        bring_to_front("Tera Term UI")
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        SPANISH = 0x0A
        language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if language_id & 0xFF == SPANISH:
            messagebox.showerror("Error", "Ocurrió un error inesperado: " + str(e) + "\n\n"
                                          "Puede que necesite reinstalar la aplicación")
        else:
            messagebox.showerror("Error", "An unexpected error occurred: " + str(e) + "\n\n"
                                          "Might need to reinstall the application")
        sys.exit(1)


if __name__ == "__main__":
    main()
