# PROGRAM NAME - Tera Term UI

# PROGRAMMER - Armando Del Valle Tejada

# DESCRIPTION - Controls The application called Tera Term through a GUI interface to make the process of
# enrolling classes for the university of Puerto Rico at Bayamon easier

# DATE - Started 1/1/23, Current Build v0.9.5 - 8/18/24

# BUGS / ISSUES - The implementation of pytesseract could be improved, it sometimes fails to read the screen properly,
# depends a lot on the user's system and takes a bit time to process.
# Application sometimes feels sluggish/slow to use, could use some efficiency/performance improvements.
# The grid of the UI interface and placement of widgets could use some work.
# Option Menu of all tera term's screens requires more work, project needs more documentation.

# FUTURE PLANS: Display more information in the app itself, which will make the app less reliant on Tera Term,
# refactor the architecture of the codebase, split things into multiple files, right now everything is in 1 file
# and with over 11100 lines of codes, it definitely makes things harder to work with

import asyncio
import atexit
import ctypes
import customtkinter
import gc
import json
import os
import psutil
import pygetwindow as gw
import pyperclip
import pystray
import pytesseract
import random
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
from chardet import detect as chardet_detect
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing
from Cryptodome.Hash import HMAC, SHA256
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from Cryptodome.Random import get_random_bytes
from CTkMessagebox import CTkMessagebox
from CTkTable import CTkTable
from CTkToolTip import CTkToolTip
from ctypes import wintypes
from datetime import datetime, timedelta
from filelock import FileLock, Timeout
from functools import wraps
from itertools import groupby
from mss import mss
from pathlib import Path
from PIL import Image
from py7zr import SevenZipFile
from tkinter import filedialog
from tkinter import messagebox
from win32con import SW_HIDE, SW_SHOW, SW_RESTORE, WM_CLOSE
MAX_RESTARTS = 5
restart_count = 0
try:
    if len(sys.argv) > 2:
        try:
            restart_count = int(sys.argv[2])
        except ValueError:
            pass
    sys.coinit_flags = 2
    warnings.filterwarnings("ignore", message="Apply externally defined coinit_flags: 2")
    import comtypes.stream
    from pywinauto.application import Application, AppStartError
    from pywinauto.findwindows import ElementNotFoundError
    from pywinauto import timings
except Exception as e:
    print(f"Error occurred: {e}")
    if restart_count >= MAX_RESTARTS:
        sys.exit(1)
    temp_dir = tempfile.gettempdir()
    exe_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    comtypes_cache_dir = os.path.join(temp_dir, "comtypes_cache")
    cache_dirs = [d for d in os.listdir(comtypes_cache_dir) if
                  os.path.isdir(os.path.join(comtypes_cache_dir, d))]
    if len(cache_dirs) == 1 and cache_dirs[0].startswith(f"{exe_name}-"):
        if os.path.exists(comtypes_cache_dir):
            shutil.rmtree(comtypes_cache_dir)
    else:
        for cache_dir in cache_dirs:
            if cache_dir.startswith(f"{exe_name}-"):
                cache_dir_path = os.path.join(comtypes_cache_dir, cache_dir)
                if os.path.exists(cache_dir_path):
                    shutil.rmtree(cache_dir_path)
    current_executable = os.path.abspath(sys.argv[0])
    subprocess.run([sys.executable, current_executable, str(restart_count + 1)])
    sys.exit(0)

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")
warnings.filterwarnings("ignore", message="32-bit application should be automated using 32-bit Python")
gc.set_threshold(5000, 100, 100)
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def measure_time(threshold):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            result = func(self, *args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"Elapsed time: {elapsed_time:.2f} seconds")
            game_launchers = ["EpicGamesLauncher", "SteamWebHelper", "RockstarService"]
            running_launchers = TeraTermUI.checkMultipleProcessesRunning(*game_launchers)
            if elapsed_time > threshold or running_launchers:
                self.after(350, self.notice_user, running_launchers)
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
        self.geometry(f"{width}x{height}+{int(x) + 90}+{int(y + 50)}")
        self.icon_path = TeraTermUI.get_absolute_path("images/tera-term.ico")
        self.iconbitmap(self.icon_path)
        self.mode = "Portable"
        self.update_db = False
        self.bind("<Button-2>", lambda event: self.focus_set())
        self.bind("<Button-3>", lambda event: self.focus_set())

        # creates separate threads from the main application
        self.last_activity = None
        self.stop_check_idle = threading.Event()
        self.stop_check_process = threading.Event()
        self.thread_pool = ThreadPoolExecutor(max_workers=5)
        self.future_tesseract = None
        self.future_backup = None
        self.future_feedback = None
        self.lock_thread = threading.Lock()

        # GitHub's information for feedback
        self.SERVICE_ACCOUNT_FILE = TeraTermUI.get_absolute_path("feedback.zip")
        self.SPREADSHEET_ID = "1ffJLgp8p-goOlxC10OFEu0JefBgQDsgEo_suis4k0Pw"
        parts = ["$QojxnTKT8ecke49mf%bd", "U64m#8XaR$QNog$QdPL1Fp", "3%fHhv^ds7@CDDSag8PYt", "dM&R8fqu*&bUjmSZfgM^%"]
        os.environ["REAZIONE"] = TeraTermUI.purkaa_reazione(parts)
        self.REAZIONE = os.getenv("REAZIONE")
        self.RANGE_NAME = "Sheet1!A:A"
        self.credentials = None
        self.GITHUB_REPO = "https://api.github.com/repos/Hanuwa/TeraTermUI"
        self.USER_APP_VERSION = "0.9.5"
        # disabled/enables keybind events
        self.move_slider_left_enabled = True
        self.move_slider_right_enabled = True
        self.up_arrow_key_enabled = True
        self.down_arrow_key_enabled = True

        # Installer Directories
        if self.mode == "Installation":
            appdata_path = os.environ.get("PROGRAMDATA")
            self.db_path = os.path.join(appdata_path, "TeraTermUI/database.db")
            self.ath = os.path.join(appdata_path, "TeraTermUI/feedback.zip")
            self.logs = os.path.join(appdata_path, "TeraTermUI/logs.txt")

        # Instance variables not yet needed but defined
        # to avoid the instance attribute defined outside __init__ warning
        self.uprbay_window = None
        self.uprb = None
        self.uprb_32 = None
        self.tera_term_window = None
        self.select_screen_item = None
        self.server_status = None
        self.timer_window = None
        self.timer_label = None
        self.message_label = None
        self.cancel_button = None
        self.pr_date = None
        self.running_countdown = None
        self.progress_bar = None
        self.loading_label = None
        self.check_idle_thread = None
        self.check_process_thread = None
        self.idle_num_check = None
        self.idle_warning = None
        self.feedback_text = None
        self.feedback_send = None
        self.search_box = None
        self.class_list = None
        self.back_checkbox_state = None
        self.exit_checkbox_state = None
        self.get_class_for_pdf = None
        self.get_semester_for_pdf = None
        self.show_all_sections = None
        self.download_search_pdf = None
        self.download_enrolled_pdf = None
        self.sort_by = None
        self.sort_by_tooltip = None
        self.last_sort_option = ()
        self.download_enrolled_pdf_tooltip = None
        self.table_count_tooltip = None
        self.previous_button_tooltip = None
        self.next_button_tooltip = None
        self.remove_button_tooltip = None
        self.download_search_pdf_tooltip = None
        self.tooltip = None
        self.last_closing_time = None
        self.is_exit_dialog_open = False
        self.dialog = None
        self.dialog_input = None
        self.ask_semester_refresh = True
        self.move_tables_overlay = None
        self.move_title_label = None
        self.tables_container = None
        self.tables_checkboxes = []

        self.image_cache = {}

        # path for tesseract application
        self.zip_path = os.path.join(os.path.dirname(__file__),  TeraTermUI.get_absolute_path("Tesseract-OCR.7z"))
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
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="Language, Appearance and\n\n"
                                                                             "UI Scaling", anchor="w")
        self.scaling_label_tooltip = CTkToolTip(self.scaling_label, message="Change the language, the theme and "
                                                                            "the\nscaling of the widgets of the "
                                                                            "application.\nThese settings are saved so "
                                                                            "next time you open\nthe app you won't have"
                                                                            " to reconfigured them", bg_color="#1E90FF")
        self.scaling_label.bind("<Button-1>", lambda event: self.focus_set())
        self.scaling_label.grid(row=5, column=0, padx=20, pady=(10, 10))
        self.language_menu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["English", "Español"],
                                                         canvas_takefocus=False, command=self.change_language_event,
                                                         corner_radius=15)
        self.language_menu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, corner_radius=15,
                                                                       canvas_takefocus=False,
                                                                       values=["Dark", "Light", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.set("System")
        self.curr_appearance = self.appearance_mode_optionemenu.get()
        self.appearance_mode_optionemenu.grid(row=7, column=0, padx=20, pady=(10, 10))
        self.scaling_slider = customtkinter.CTkSlider(self.sidebar_frame, from_=97, to=103, number_of_steps=2,
                                                      width=150, height=20, command=self.change_scaling_event)
        self.scaling_slider.set(100)
        self.scaling_tooltip = CTkToolTip(self.scaling_slider, message=str(self.scaling_slider.get()) + "%",
                                          bg_color="#1E90FF")
        self.curr_scaling = self.scaling_slider.get() / 100
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
        self.host.bind("<Button-1>", lambda event: self.focus_set())
        self.host_entry = CustomEntry(self.home_frame, self, self.language_menu.get(),
                                      placeholder_text="myhost.example.edu")
        self.host_entry.grid(row=2, column=1, padx=(20, 0), pady=(15, 15))
        self.host_tooltip = CTkToolTip(self.host_entry, message="Enter the name of the server\n of the university",
                                       bg_color="#1E90FF")
        self.log_in = CustomButton(self.home_frame, border_width=2, text="Log-In", text_color=("gray10", "#DCE4EE"),
                                   command=self.login_event_handler)
        self.log_in.grid(row=3, column=1, padx=(20, 0), pady=(15, 15))
        self.log_in.configure(state="disabled")
        self.slideshow_frame = ImageSlideshow(self.home_frame, TeraTermUI.get_absolute_path("slideshow"),
                                              interval=5, width=300, height=150)
        self.slideshow_frame.grid(row=1, column=1, padx=(20, 0), pady=(140, 0))
        self.intro_box = CustomTextBox(self.home_frame, self, read_only=True, lang=self.language_menu.get(),
                                       height=120, width=400)
        self.intro_box.insert("0.0", "Welcome to the Tera Term UI Application!\n\n" +
                              "The purpose of this application"
                              " is to facilitate the process enrolling and dropping classes, "
                              "since Tera Term uses a terminal interface, "
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
                              "IMPORTANT: DO NOT USE WHILE HAVING ANOTHER INSTANCE OF THE APPLICATION OPENED.""")
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
        self.skipped_login = False

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
        self.e_section_tooltip = None
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
        self.went_to_1PL_screen = False
        self.went_to_683_screen = False

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
        self.m_num_class = []
        self.m_classes_entry = []
        self.m_section_entry = []
        self.m_semester_entry = []
        self.m_register_menu = []
        self.m_tooltips = []
        self.schedule_map = TeraTermUI.generate_schedule()
        self.placeholder_texts_classes = ("ESPA3101", "INGL3101", "ADMI4005", "BIOL3011", "MATE3001",
                                          "CISO3121", "HUMA3101", "MECU3031")
        self.placeholder_texts_sections = ("LM1", "KM1", "LH1", "KH1", "LN1", "KN1", "LJ1", "KJ1")
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
        self.changed_classes = None
        self.changed_sections = None
        self.changed_semesters = None
        self.changed_registers = None

        # My Classes
        self.enrolled_header_tooltips = {}
        self.enrolled_tooltips = []
        self.my_classes_frame = None
        self.enrolled_classes_table = None
        self.enrolled_classes_data = None
        self.enrolled_classes_credits = None
        self.title_my_classes = None
        self.total_credits_label = None
        self.submit_my_classes = None
        self.submit_my_classes_tooltip = None
        self.modify_classes_frame = None
        self.back_my_classes = None
        self.back_my_classes_tooltip = None
        self.change_section_entries = None
        self.mod_selection_list = None
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
        self.DEFAULT_SEMESTER = TeraTermUI.calculate_default_semester()
        self.semester_values = TeraTermUI.generate_semester_values(self.DEFAULT_SEMESTER)
        self.search_event_completed = True
        self.option_menu_event_completed = True
        self.go_next_event_completed = True
        self.search_go_next_event_completed = True
        self.my_classes_event_completed = True
        self.fix_execution_event_completed = True
        self.submit_feedback_event_completed = True
        self.found_latest_semester = False
        self.error_occurred = False
        self.timeout_occurred = False
        self.can_edit = False
        self.original_font = None
        self.original_color = None
        self.classes_status = {}
        self.class_table_pairs = []
        self.table_tooltips = {}
        self.original_table_data = {}
        self.current_table_index = -1
        self.table_count = None
        self.table = None
        self.current_class = None
        self.previous_button = None
        self.next_button = None
        self.remove_button = None
        self.renamed_tabs = None
        self.disable_feedback = False
        self.sending_feedback = False
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
        self.loading_screen_status = None
        self.loading_screen_start_time = None
        self.information = None
        self.run_fix = False
        self.teraterm_not_found = False
        self.teraterm5_first_boot = False
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
        self.notification_sent = False
        self.first_time_adding = True
        self.a_counter = 0
        self.m_counter = 0
        self.e_counter = 0
        self.search_function_counter = 0
        self.last_switch_time = 0
        self.last_remove_time = 0
        # Storing translations for languages in cache to reuse
        self.translations_cache = {}
        self.curr_lang = self.language_menu.get()
        SPANISH = 0x0A
        language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        # System tray for the application
        self.tray = pystray.Icon("tera-term", Image.open(self.icon_path), "Tera Term UI", self.create_tray_menu())
        self.tray.run_detached()
        # default location of Tera Term
        teraterm_directory = TeraTermUI.find_teraterm_directory()
        if teraterm_directory:
            self.location = os.path.join(teraterm_directory, "ttermpro.exe")
            self.teraterm_file = os.path.join(teraterm_directory, "TERATERM.ini")
            self.teraterm_directory = teraterm_directory
        else:
            main_drive = os.path.abspath(os.sep)
            self.location = os.path.join(main_drive, "Program Files (x86)", "teraterm", "ttermpro.exe")
            self.teraterm_file = os.path.join(main_drive, "Program Files (x86)", "teraterm", "TERATERM.ini")
            self.teraterm_directory = os.path.join(main_drive, "Program Files (x86)", "teraterm")
        # Database
        try:
            db_path = TeraTermUI.get_absolute_path("database.db")
            if not os.path.isfile(db_path) or not os.access(db_path, os.R_OK):
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
            user_data_fields = ["location", "config", "directory", "host", "language", "appearance", "scaling",
                                "welcome", "default_semester", "audio", "skip_auth", "win_pos_x", "win_pos_y"]
            results = {}
            for field in user_data_fields:
                query_user = f"SELECT {field} FROM user_data"
                result = self.cursor.execute(query_user).fetchone()
                results[field] = result[0] if result else None
            if results["location"]:
                if results["location"] != self.location:
                    self.location = results["location"]
            if results["directory"] and results["config"]:
                if results["directory"] != self.teraterm_directory and results["config"] != self.teraterm_file:
                    self.teraterm_file = results["config"]
                    self.teraterm_directory = results["directory"]
                    self.edit_teraterm_ini(self.teraterm_file)
                    self.can_edit = True

            # performs some operations on separate threads when application starts up
            self.boot_up(self.teraterm_file)

            if results["host"]:
                self.host_entry.insert(0, results["host"])
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
                if float(results["scaling"]) != 100:
                    self.scaling_slider.set(float(results["scaling"]))
                    self.change_scaling_event(float(results["scaling"]))
            if results["win_pos_x"] and results["win_pos_y"]:
                self.geometry(f"{width}x{height}+{results['win_pos_x']}+{results['win_pos_y']}")
            if results["audio"] == "Disabled":
                self.disable_audio = True
            if results["skip_auth"] == "Yes":
                self.skip_auth = True
            elif not results["skip_auth"]:
                self.ask_skip_auth = True
            if results["default_semester"]:
                values = TeraTermUI.generate_semester_values(self.DEFAULT_SEMESTER)
                if results["default_semester"] in values:
                    self.DEFAULT_SEMESTER = results["default_semester"]
                else:
                    self.cursor.execute("UPDATE user_data SET default_semester=NULL")
            if not results["welcome"]:
                self.help_button.configure(state="disabled")
                self.status_button.configure(state="disabled")
                self.intro_box.stop_autoscroll(event=None)

                # Pop up message that appears only the first time the user uses the application
                def show_message_box():
                    translation = self.load_language(self.language_menu.get())
                    if not self.disable_audio:
                        winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/welcome.wav"), winsound.SND_ASYNC)
                    CTkMessagebox(title=translation["welcome_title"], message=translation["welcome_message"],
                                  button_width=380)
                    self.slideshow_frame.go_to_first_image()
                    self.intro_box.restart_autoscroll()
                    self.status_button.configure(state="normal")
                    self.help_button.configure(state="normal")
                    self.log_in.configure(state="normal")
                    self.bind("<Return>", lambda event: self.login_event_handler())
                    self.bind("<F1>", lambda event: self.help_button_event())
                    row_check = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
                    if not row_check:
                        self.cursor.execute("INSERT INTO user_data (welcome) VALUES (?)", ("Done",))
                    else:
                        self.cursor.execute("UPDATE user_data SET welcome=?", ("Done",))
                    del row_check, translation

                self.after(3500, show_message_box)
            else:
                self.log_in.configure(state="normal")
                self.bind("<Return>", lambda event: self.login_event_handler())
                self.bind("<F1>", lambda event: self.help_button_event())
                # Check for update for the application
                current_date = datetime.today().strftime("%Y-%m-%d")
                date_record = self.cursor.execute("SELECT update_date FROM user_data").fetchone()
                if date_record is None or date_record[0] is None or not date_record[0].strip() or (
                        datetime.strptime(current_date, "%Y-%m-%d")
                        - datetime.strptime(date_record[0], "%Y-%m-%d")).days >= 14:
                    try:
                        self.check_update = True
                        latest_version = self.get_latest_release()

                        def enable():
                            self.log_in.configure(state="normal")
                            self.bind("<Return>", lambda event: self.login_event_handler())
                            self.bind("<F1>", lambda event: self.help_button_event())

                        if latest_version is None:
                            print("No latest release found. Starting app with the current version.")
                            latest_version = self.USER_APP_VERSION
                        if not TeraTermUI.compare_versions(latest_version, self.USER_APP_VERSION):
                            self.after(1000, self.update_app, latest_version)
                            self.after(1250, enable)
                        else:
                            enable()
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
        except Exception as err:
            db_path = TeraTermUI.get_absolute_path("database.db")
            en_path = TeraTermUI.get_absolute_path("translations/english.json")
            es_path = TeraTermUI.get_absolute_path("translations/spanish.json")
            print(f"An unexpected error occurred: {err}")
            self.log_error()
            if not os.path.isfile(db_path) or not os.access(db_path, os.R_OK):
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
            self.tray.stop()
            sys.exit(1)
        if TeraTermUI.is_admin():
            p = psutil.Process(os.getpid())
            p.nice(psutil.HIGH_PRIORITY_CLASS)
        atexit.register(self.cleanup_temp)
        atexit.register(self.restore_original_font, self.teraterm_file)
        self.after(0, self.unload_image("uprb"))
        self.after(0, self.unload_image("status"))
        self.after(0, self.unload_image("help"))
        self.after(0, self.set_focus_to_tkinter)
        del user_data_fields, results, SPANISH, language_id, scaling_factor, screen_width, screen_height, width, \
            height, x, y, db_path, en_path, es_path

    def create_tray_menu(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        return pystray.Menu(
            pystray.MenuItem(translation["hide_tray"], self.hide_all_windows),
            pystray.MenuItem(translation["show_tray"], self.show_all_windows, default=True),
            pystray.MenuItem(translation["exit_tray"], self.direct_close_on_tray)
        )

    def hide_all_windows(self):
        if self.state() == "withdrawn" or (self.loading_screen_status is not None and
                                           self.loading_screen_status.winfo_exists()):
            if self.timer_window is not None and self.timer_window.state() == "normal":
                self.timer_window.withdraw()
            return

        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.withdraw()
        self.destroy_windows()
        if TeraTermUI.window_exists(translation["dialog_title"]):
            my_classes_hwnd = win32gui.FindWindow(None, translation["dialog_title"])
            win32gui.PostMessage(my_classes_hwnd, WM_CLOSE, 0, 0)
        if TeraTermUI.window_exists("Tera Term"):
            file_dialog_hwnd = win32gui.FindWindow("#32770", "Tera Term")
            win32gui.PostMessage(file_dialog_hwnd, WM_CLOSE, 0, 0)
        if TeraTermUI.window_exists("Error"):
            file_dialog_hwnd = win32gui.FindWindow("#32770", "Error")
            win32gui.PostMessage(file_dialog_hwnd, WM_CLOSE, 0, 0)
        if TeraTermUI.window_exists(translation["save_pdf"]):
            file_dialog_hwnd = win32gui.FindWindow("#32770", translation["save_pdf"])
            win32gui.PostMessage(file_dialog_hwnd, WM_CLOSE, 0, 0)
        if TeraTermUI.window_exists(translation["select_tera_term"]):
            file_dialog_hwnd = win32gui.FindWindow("#32770", translation["select_tera_term"])
            win32gui.PostMessage(file_dialog_hwnd, WM_CLOSE, 0, 0)
        if self.status is not None and self.status.winfo_exists():
            self.status.withdraw()
        if self.help is not None and self.help.winfo_exists():
            self.help.withdraw()
        if self.timer_window is not None and self.timer_window.winfo_exists():
            self.timer_window.withdraw()
        for widget in self.winfo_children():
            if isinstance(widget, tk.Toplevel) and not hasattr(widget, "is_ctktooltip"):
                if hasattr(widget, "is_ctkmessagebox") and widget.is_ctkmessagebox:
                    widget.close_messagebox()
                elif widget is not self.status and widget is not self.help and widget is not self.timer_window:
                    widget.destroy()
        if not TeraTermUI.window_exists("Tera Term - [disconnected] VT") and \
                not TeraTermUI.window_exists("SSH Authentication") and not self.in_student_frame:
            hwnd = win32gui.FindWindow(None, "uprbay.uprb.edu - Tera Term VT")
            if hwnd and win32gui.IsWindowVisible(hwnd):
                win32gui.ShowWindow(hwnd, SW_HIDE)

    def show_all_windows(self):
        if self.state() == "normal" and (self.loading_screen_status is not None and
                                         self.loading_screen_status.winfo_exists()):
            return
        elif self.state() == "normal" and self.loading_screen_status is None:
            self.set_focus_to_tkinter()
            return

        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.iconify()
        if self.status is not None and self.status.winfo_exists():
            self.status.iconify()
        if self.help is not None and self.help.winfo_exists():
            self.help.iconify()
        if self.timer_window is not None and self.timer_window.winfo_exists():
            if self.timer_window.state() == "withdrawn":
                self.timer_window.iconify()
            timer = gw.getWindowsWithTitle(translation["auto_enroll"])[0]
            self.after(200, timer.restore)
        app = gw.getWindowsWithTitle("Tera Term UI")[0]
        self.after(150, app.restore)
        self.after(200, self.set_focus_to_tkinter)
        hwnd = win32gui.FindWindow(None, "uprbay.uprb.edu - Tera Term VT")
        if hwnd and not win32gui.IsWindowVisible(hwnd):
            win32gui.ShowWindow(hwnd, SW_SHOW)
            win32gui.ShowWindow(hwnd, SW_RESTORE)

    def direct_close_on_tray(self):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            return

        self.tray.stop()
        self.after(0, self.direct_close)

    # function that when the user tries to close the application a confirm dialog opens up
    def on_closing(self):
        current_time = time.time()
        if (self.last_closing_time is not None and (current_time - self.last_closing_time) < 0.25) or \
                (hasattr(self, "is_exit_dialog_open") and self.is_exit_dialog_open) or \
                (self.loading_screen_status is not None and self.loading_screen_status.winfo_exists()):
            return

        self.is_exit_dialog_open = True
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        msg = CTkMessagebox(title=translation["exit"], message=translation["exit_message"], icon="question",
                            option_1=translation["close_tera_term"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#c30101", "#145DA0", "use_default"),
                            option_1_type="checkbox", hover_color=("darkred", "darkred", "use_default"))
        on_exit = self.cursor.execute("SELECT exit FROM user_data").fetchone()
        if on_exit and on_exit[0] is not None and on_exit[0] == 1:
            msg.check_checkbox()
        response, self.exit_checkbox_state = msg.get()
        self.is_exit_dialog_open = False
        if response == "Yes" or response == "Sí":
            self.tray.stop()
            if all(future.done() for future in [self.future_tesseract, self.future_backup, self.future_feedback]):
                self.thread_pool.shutdown(wait=False)
            else:
                for future in as_completed([self.future_tesseract, self.future_backup, self.future_feedback]):
                    future.result()
            self.save_user_data()
            self.end_app()
            if self.exit_checkbox_state:
                if TeraTermUI.checkIfProcessRunning("ttermpro"):
                    if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                        try:
                            self.uprb.kill(soft=True)
                            if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                                TeraTermUI.terminate_process()
                        except Exception as err:
                            print("An error occurred: ", err)
                            TeraTermUI.terminate_process()
                    elif TeraTermUI.window_exists("Tera Term - [disconnected] VT") or \
                            TeraTermUI.window_exists("Tera Term - [connecting...] VT"):
                        TeraTermUI.terminate_process()
            sys.exit(0)
        self.last_closing_time = current_time

    def direct_close(self):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            return

        hwnd = win32gui.FindWindow(None, "uprbay.uprb.edu - Tera Term VT")
        if hwnd and not win32gui.IsWindowVisible(hwnd):
            win32gui.ShowWindow(hwnd, SW_SHOW)
            win32gui.ShowWindow(hwnd, SW_RESTORE)
        self.tray.stop()
        if all(future.done() for future in [self.future_tesseract, self.future_backup, self.future_feedback]):
            self.thread_pool.shutdown(wait=False)
        else:
            for future in as_completed([self.future_tesseract, self.future_backup, self.future_feedback]):
                future.result()
        self.save_user_data(include_exit=False)
        self.end_app()
        sys.exit(0)

    def end_app(self):
        try:
            for widget in self.winfo_children():
                if isinstance(widget, tk.Toplevel) and hasattr(widget, "is_ctkmessagebox") \
                        and widget.is_ctkmessagebox:
                    widget.close_messagebox()
            self.destroy()
        except Exception as err:
            print("Force closing due to an error:", err)
            self.log_error()
            sys.exit(1)

    def forceful_end_app(self):
        try:
            for widget in self.winfo_children():
                if isinstance(widget, tk.Toplevel) and hasattr(widget, "is_ctkmessagebox") \
                        and widget.is_ctkmessagebox:
                    widget.close_messagebox()
            self.tray.stop()
            self.destroy()
        except Exception as err:
            print("Force closing due to an error:", err)
            self.log_error()
        finally:
            sys.exit(1)

    @staticmethod
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() == 1
        except Exception as err:
            print(f"An error occurred: {err}")
            return False

    @staticmethod
    def get_absolute_path(relative_path):
        if os.path.isabs(relative_path):
            raise ValueError("The provided path is already an absolute path")
        try:
            absolute_path = os.path.abspath(os.path.join(os.path.dirname(__file__), relative_path))
            return absolute_path
        except Exception as err:
            print(f"Error converting path '{relative_path}' to absolute path: {err}")
            raise

    @staticmethod
    def terminate_process():
        try:
            subprocess.Popen(["taskkill", "/f", "/im", "ttermpro.exe"],
                             creationflags=subprocess.CREATE_NO_WINDOW,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("Could not terminate ttermpro.exe.")

    @staticmethod
    def check_tera_term_hidden():
        def enum_window_callback(hwnd_win, window_list):
            if "Tera Term" in win32gui.GetWindowText(hwnd_win):
                window_list.append(hwnd_win)

        windows = []
        win32gui.EnumWindows(enum_window_callback, windows)

        for hwnd in windows:
            window_text = win32gui.GetWindowText(hwnd)
            if re.search(r".* - Tera Term", window_text):
                if not win32gui.IsWindowVisible(hwnd):
                    TeraTermUI.terminate_process()
                    break

    def log_error(self):
        import inspect
        import traceback

        try:
            # Get the current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Get the current call stack and extract the function or module name
            stack = inspect.stack()
            _, filename, lineno, function, code_context, _ = stack[1]
            # Capture the full traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = traceback.extract_tb(exc_traceback)
            # Get the last frame in the traceback, to capture the exact line that cause the exception
            last_frame = tb[-1]
            lineno = last_frame.lineno
            function_info = f"{filename}:{function}:{lineno}"
            traceback_summary = traceback.format_exc().strip().split("\n")[-1]
            # Create a formatted error message with the app version and timestamp
            error_message = (f"[ERROR] [{self.mode}] [{self.USER_APP_VERSION}] [{timestamp}]"
                             f" [{function_info}] Traceback: {traceback_summary}")
            # Calculate the length of the error message
            error_length = len(error_message)
            # Create a separator based on the length of the error message
            separator = "-" * error_length + "\n"
            if self.mode == "Installation":
                appdata_path = os.environ.get("PROGRAMDATA")
                tera_term_ui_path = os.path.join(appdata_path, "TeraTermUI")
                if not os.path.isdir(tera_term_ui_path):
                    raise Exception("Program Data directory not found")
                with open(self.logs, "a") as file:
                    file.write(error_message + "\n" + separator)
            else:
                with open(TeraTermUI.get_absolute_path("logs.txt"), "a") as file:
                    file.write(error_message + "\n" + separator)
        except Exception as err:
            print(f"An unexpected error occurred: {str(err)}")

    def student_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        self.thread_pool.submit(self.student_event, task_done=task_done)

    # Enrolling/Searching classes Frame
    def student_event(self, task_done):
        # Deletes these encrypted variables from memory
        def secure_delete(variable):
            if isinstance(variable, bytes):
                variable_len = len(variable)
                new_value = secrets.token_bytes(variable_len)
                ctypes.memset(id(variable) + 0x10, 0, variable_len)
                variable = new_value
            elif isinstance(variable, int):
                new_value = secrets.randbits(variable.bit_length())
                variable = new_value
            return variable

        # Encrypt and compute MAC
        def aes_encrypt_then_mac(plaintext, key, inner_mac_key):
            # Generate a new IV for each encryption
            inner_iv = get_random_bytes(16)  # for AES CBC mode
            cipher = AES.new(key, AES.MODE_CBC, iv=inner_iv)
            ciphertext = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
            # Compute a MAC over the ciphertext
            hmac = HMAC.new(inner_mac_key, digestmod=SHA256)
            hmac.update(ciphertext)
            mac = hmac.digest()
            # Prepend the IV to the ciphertext and append the MAC
            return inner_iv + ciphertext + mac

        # Decrypt and verify MAC
        def aes_decrypt_and_verify_mac(ciphertext_with_iv_mac, key, inner_mac_key):
            # Extract the IV from the beginning of the data
            inner_iv = ciphertext_with_iv_mac[:16]
            ciphertext_with_mac = ciphertext_with_iv_mac[16:]
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

        with self.lock_thread:
            try:
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                aes_key = secrets.token_bytes(32)  # 256-bit key
                mac_key = secrets.token_bytes(32)  # separate 256-bit key for HMAC
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        student_id = self.student_id_entry.get().replace(" ", "").replace("-", "")
                        code = self.code_entry.get().replace(" ", "")
                        student_id_enc = aes_encrypt_then_mac(str(student_id), aes_key, mac_key)
                        code_enc = aes_encrypt_then_mac(str(code), aes_key, mac_key)
                        if ((re.match(r"^(?!000|666|9\d{2})\d{3}(?!00)\d{2}(?!0000)\d{4}$", student_id) or
                             (student_id.isdigit() and len(student_id) == 9)) and code.isdigit() and len(code) == 4):
                            secure_delete(student_id)
                            secure_delete(code)
                            self.wait_for_window()
                            self.uprb.UprbayTeraTermVt.type_keys("{TAB}")
                            self.uprb.UprbayTeraTermVt.type_keys(
                                aes_decrypt_and_verify_mac(student_id_enc, aes_key, mac_key))
                            self.uprb.UprbayTeraTermVt.type_keys(
                                aes_decrypt_and_verify_mac(code_enc, aes_key, mac_key))
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            text_output = self.wait_for_response(["SIGN-IN", "ON FILE", "PIN NUMBER",
                                                                  "ERRORS FOUND"], init_timeout=False, timeout=5)
                            if "SIGN-IN" in text_output:
                                self.reset_activity_timer()
                                self.start_check_idle_thread()
                                self.start_check_process_thread()
                                self.after(0, self.initialization_class)
                                self.after(0, self.destroy_student)
                                self.after(50, self.student_info_frame)
                                self.run_fix = True
                                if self.help is not None and self.help.winfo_exists():
                                    self.fix.configure(state="normal")
                                self.in_student_frame = False
                                secure_delete(student_id_enc)
                                secure_delete(code_enc)
                                secure_delete(aes_key)
                                secure_delete(mac_key)
                                del student_id, code, student_id_enc, code_enc, aes_key, mac_key
                                self.switch_tab()
                            else:
                                self.after(350, self.bind, "<Return>", lambda event: self.student_event_handler())
                                if "ON FILE" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys("{TAB 3}")
                                    self.after(0, self.student_id_entry.configure(border_color="#c30101"))
                                    self.after(100, self.show_error_message, 315, 230,
                                               translation["error_invalid_student_id"])
                                elif "PIN NUMBER" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}")
                                    self.after(0, self.code_entry.configure(border_color="#c30101"))
                                    self.after(100, self.show_error_message, 315, 230,
                                               translation["error_invalid_code"])
                                elif "ERRORS FOUND" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys("{TAB 3}")
                                    self.after(0, self.student_id_entry.configure(border_color="#c30101"))
                                    self.after(0, self.code_entry.configure(border_color="#c30101"))
                                    self.after(100, self.show_error_message, 300, 215,
                                               translation["error_student_id_code"])
                                else:
                                    self.after(100, self.show_error_message, 315, 230, translation["error_sign-in"])
                        else:
                            self.after(350, self.bind, "<Return>", lambda event: self.student_event_handler())
                            if (not student_id or not student_id.isdigit() or len(student_id) != 9) and \
                                    (not code.isdigit() or len(code) != 4):
                                self.after(0, self.student_id_entry.configure(border_color="#c30101"))
                                self.after(0, self.code_entry.configure(border_color="#c30101"))
                                self.after(100, self.show_error_message, 300, 215, translation["error_student_id_code"])
                            elif not student_id or not student_id.isdigit() or len(student_id) != 9:
                                self.after(0, self.student_id_entry.configure(border_color="#c30101"))
                                self.after(100, self.show_error_message, 315, 230, translation["error_student_id"])
                            elif not code.isdigit() or len(code) != 4:
                                self.after(0, self.code_entry.configure(border_color="#c30101"))
                                self.after(100, self.show_error_message, 315, 230, translation["error_code"])
                    else:
                        self.after(350, self.bind, "<Return>", lambda event: self.student_event_handler())
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
                else:
                    self.after(350, self.bind, "<Return>", lambda event: self.student_event_handler())
            except Exception as err:
                print("An error occurred: ", err)
                self.error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.reset_activity_timer()
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                               winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.after(350, self.bind, "<Return>", lambda event: self.student_event_handler())
                        self.error_occurred = False

                    self.after(50, error_automation)
                TeraTermUI.disable_user_input()

    def student_info_frame(self):
        if not self.init_multiple:
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
                self.show_all.grid(row=1, column=1, padx=(85, 0), pady=(0, 0), sticky="n")
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
        else:
            self.tabview.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 85))
            self.t_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(0, 0), pady=(0, 20))
        self.bind("<Control-Tab>", lambda event: self.on_ctrl_tab_pressed())
        if self.renamed_tabs is not None:
            if self.renamed_tabs == self.enroll_tab:
                self.tabview.set(self.enroll_tab)
            elif self.renamed_tabs == self.search_tab:
                self.tabview.set(self.search_tab)
            elif self.renamed_tabs == self.other_tab:
                self.tabview.set(self.other_tab)
            self.renamed_tabs = None
            self.after(0, self.switch_tab)
        self.initialization_multiple()

    def load_saved_classes(self):
        lang = self.language_menu.get()
        reverse_language_mapping = {
            "English": {
                "Registra": "Register",
                "Baja": "Drop",
                "Actual": "Current"
            },
            "Español": {
                "Register": "Registra",
                "Drop": "Baja",
                "Current": "Actual"
            }
        }
        save = self.cursor.execute("SELECT class, section, semester, action FROM saved_classes"
                                   " WHERE class IS NOT NULL").fetchall()
        save_check = self.cursor.execute('SELECT "id" FROM saved_classes').fetchone()
        semester = self.cursor.execute("SELECT semester FROM saved_classes ORDER BY id LIMIT 1").fetchone()
        if save_check and save_check[0] is not None:
            if semester[0] != self.DEFAULT_SEMESTER:
                self.cursor.execute("DELETE FROM saved_classes")
                self.connection.commit()
                return
            if save_check[0] == 1:
                self.save_data.select()
                self.changed_classes = set()
                self.changed_sections = set()
                self.changed_semesters = set()
                self.changed_registers = set()
                for i in range(8):
                    self.m_register_menu[i].configure(
                        command=lambda value, idx=i: self.detect_register_menu_change(value, idx))
                    self.m_classes_entry[i].bind("<FocusOut>", self.detect_change)
                    self.m_section_entry[i].bind("<FocusOut>", self.section_bind_wrapper)

        if save:
            num_rows = len(save)
            max_entries = 8
            for index, row in enumerate(save[:max_entries], start=1):
                class_value, section_value, semester_value, register_value = row
                display_register_value = reverse_language_mapping.get(lang, {}).get(register_value, register_value)
                display_semester_value = reverse_language_mapping.get(lang, {}).get(semester_value, semester_value)
                self.m_classes_entry[index - 1].delete(0, "end")
                self.m_classes_entry[index - 1].insert(0, class_value)
                self.m_section_entry[index - 1].delete(0, "end")
                self.m_section_entry[index - 1].insert(0, section_value)
                if index == 1:
                    self.m_semester_entry[index - 1].set(display_semester_value)
                self.m_register_menu[index - 1].set(display_register_value)

            for _ in range(min(num_rows - 1, 8)):
                self.add_event()

            self.check_class_conflicts()

    def submit_event_handler(self):
        if self.countdown_running:
            return

        msg = None
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        choice = self.radio_var.get()
        self.focus_set()
        if lang == "English":
            if choice == "register":
                msg = CTkMessagebox(title="Submit",
                                    message="Are you sure you are ready " + translation["register"].lower() +
                                            " this class?\n\nWARNING: Make sure the information is correct",
                                    icon=TeraTermUI.get_absolute_path("images/submit.png"),
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "use_default", "use_default"))
            elif choice == "drop":
                msg = CTkMessagebox(title="Submit",
                                    message="Are you sure you are ready " + translation[
                                        "drop"].lower() + " this class?\n\nWARNING: Make sure the information "
                                                          "is correct",
                                    icon=TeraTermUI.get_absolute_path("images/submit.png"),
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "use_default", "use_default"))
        elif lang == "Español":
            if choice == "register":
                msg = CTkMessagebox(title="Someter",
                                    message="¿Estás preparado para " + translation["register"].lower() +
                                            "r esta clase?\n\nWARNING: Asegúrese de que la información está correcta",
                                    icon=TeraTermUI.get_absolute_path("images/submit.png"),
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "use_default", "use_default"),
                                    hover_color=("darkred", "use_default", "use_default"))
            elif choice == "drop":
                msg = CTkMessagebox(title="Someter",
                                    message="¿Estás preparado para darle de " + translation["drop"].lower() +
                                            " a esta clase?\n\nWARNING: Asegúrese de que la información está correcta",
                                    icon=TeraTermUI.get_absolute_path("images/submit.png"),
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            task_done = threading.Event()
            loading_screen = self.show_loading_screen()
            self.update_loading_screen(loading_screen, task_done)
            self.thread_pool.submit(self.submit_event, task_done=task_done)

    # function for registering/dropping classes
    def submit_event(self, task_done):
        with self.lock_thread:
            try:
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                choice = self.radio_var.get()
                classes = self.e_classes_entry.get().upper().replace(" ", "").replace("-", "")
                curr_sem = translation["current"].upper()
                section = self.e_section_entry.get().upper().replace(" ", "")
                semester = self.e_semester_entry.get().upper().replace(" ", "")
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if (choice == "register" and (
                                section not in self.classes_status or
                                self.classes_status[section]["status"] != "ENROLLED" or
                                self.classes_status[section]["semester"] != semester)) \
                                or (choice == "drop" and (
                                section not in self.classes_status or
                                self.classes_status[section]["status"] != "DROPPED" or
                                self.classes_status[section]["semester"] != semester)):
                            if (re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE)
                                    and re.fullmatch("^[A-Z]{2}[A-Z0-9]$", section, flags=re.IGNORECASE)
                                    and (re.fullmatch("^[A-Z][0-9]{2}$", semester,
                                                      flags=re.IGNORECASE) or semester == curr_sem)):
                                self.wait_for_window()
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                self.uprb.UprbayTeraTermVt.type_keys("1S4")
                                if semester == curr_sem:
                                    result = self.handle_current_semester()
                                    if result == "error":
                                        self.after(100, self.show_error_message, 300, 210, translation["failed_enroll"])
                                        return
                                    elif result == "negative":
                                        return
                                    else:
                                        semester = result
                                self.uprb.UprbayTeraTermVt.type_keys(semester)
                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                self.after(0, self.disable_go_next_buttons)
                                text_output = self.capture_screenshot()
                                enrolled_classes = "ENROLLED"
                                count_enroll = text_output.count(enrolled_classes)
                                if "OUTDATED" not in text_output and "INVALID TERM SELECTION" not in text_output and \
                                        "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" \
                                        not in text_output and "ENTER REGISTRATION" in text_output and \
                                        count_enroll != 15:
                                    self.e_counter = 0
                                    self.uprb.UprbayTeraTermVt.type_keys("{TAB 3}")
                                    for i in range(count_enroll, 0, -1):
                                        self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}")
                                    if choice == "register":
                                        self.uprb.UprbayTeraTermVt.type_keys("R")
                                    elif choice == "drop":
                                        self.uprb.UprbayTeraTermVt.type_keys("D")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes)
                                    self.uprb.UprbayTeraTermVt.type_keys(section)
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    text_output = self.wait_for_response(["CONFIRMED", "DROPPED"])
                                    enrolled_classes = "ENROLLED"
                                    count_enroll = text_output.count(enrolled_classes)
                                    dropped_classes = "DROPPED"
                                    count_dropped = text_output.count(dropped_classes)
                                    self.reset_activity_timer()
                                    if "CONFIRMED" in text_output or "DROPPED" in text_output:
                                        self.e_classes_entry.configure(state="normal")
                                        self.e_section_entry.configure(state="normal")
                                        self.e_classes_entry.delete(0, "end")
                                        self.e_section_entry.delete(0, "end")
                                        self.e_classes_entry.configure(
                                            placeholder_text="MATE3032")
                                        self.e_section_entry.configure(
                                            placeholder_text="LM1")
                                        self.e_classes_entry.configure(state="disabled")
                                        self.e_section_entry.configure(state="disabled")
                                        self.e_counter -= count_dropped
                                        self.e_counter += count_enroll
                                        if choice == "register":
                                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                            time.sleep(1)
                                            self.classes_status[section] = {"classes": classes, "status": "ENROLLED",
                                                                            "semester": semester}
                                            self.after(100, self.show_success_message, 350, 265,
                                                       translation["success_enrolled"])
                                        elif choice == "drop":
                                            self.classes_status[section] = {"classes": classes, "status": "DROPPED",
                                                                            "semester": semester}
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
                                        self.after(2500, self.show_enrollment_error_information, text_output)
                                else:
                                    if count_enroll == 15:
                                        self.submit.configure(state="disabled")
                                        self.submit_multiple.configure(sate="disabled")
                                        self.after(100, self.show_information_message, 350, 265,
                                                   translation["enrollment_limit"])
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        self.reset_activity_timer()
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                    else:
                                        if "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" \
                                                not in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                            self.reset_activity_timer()
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
                                    if not classes:
                                        self.after(0, self.e_classes_entry.configure(border_color="#c30101"))
                                    if not section:
                                        self.after(0, self.e_section_entry.configure(border_color="#c30101"))
                                    if not semester:
                                        self.after(0, self.e_semester_entry.configure(border_color="#c30101"))
                                elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE):
                                    self.after(100, self.show_error_message, 360, 230,
                                               translation["class_format_error"])
                                    self.after(0, self.e_classes.configure(border_color="#c30101"))
                                elif not re.fullmatch("^[A-Z]{2}[A-Z0-9]$", section, flags=re.IGNORECASE):
                                    self.after(100, self.show_error_message, 360, 230,
                                               translation["section_format_error"])
                                    self.after(0, self.e_section_entry.configure(border_color="#c30101"))
                                elif not re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE) \
                                        and semester != curr_sem:
                                    self.after(100, self.show_error_message, 360, 230,
                                               translation["semester_format_error"])
                                    self.after(0, self.e_semester_entry.configure(border_color="#c30101"))
                        else:
                            if section in self.classes_status and self.classes_status[section]["status"] == "ENROLLED":
                                self.after(100, self.show_error_message, 335, 240, translation["already_enrolled"])
                            elif section in self.classes_status and self.classes_status[section]["status"] == "DROPPED":
                                self.after(100, self.show_error_message, 335, 240, translation["already_dropped"])
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as err:
                print("An error occurred: ", err)
                self.error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                               winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(50, error_automation)
                if not self.not_rebind:
                    self.after(350, self.bind, "<Return>", lambda event: self.submit_event_handler())
                TeraTermUI.disable_user_input()

    def search_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        self.thread_pool.submit(self.search_event, task_done=task_done)
        self.search_event_completed = False

    # function for searching for classes
    def search_event(self, task_done):
        with self.lock_thread:
            try:
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                classes = self.s_classes_entry.get().upper().replace(" ", "").replace("-", "")
                semester = self.s_semester_entry.get().upper().replace(" ", "")
                curr_sem = translation["current"].upper()
                show_all = self.show_all.get()
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if (re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE)
                                and (re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE)
                                     or semester == curr_sem)):
                            self.wait_for_window()
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1CS")
                            if semester == curr_sem:
                                result = self.handle_current_semester()
                                if result == "error":
                                    self.after(100, self.show_error_message, 320, 235, translation["failed_to_search"])
                                    return
                                elif result == "negative":
                                    return
                                else:
                                    semester = result
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            if self.search_function_counter == 0 or semester != self.get_semester_for_pdf:
                                text_output = self.capture_screenshot()
                                if "INVALID TERM SELECTION" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.reset_activity_timer()
                                    self.after(100, self.show_error_message, 320, 235, translation["invalid_semester"])
                                    return
                            clipboard_content = None
                            try:
                                clipboard_content = self.clipboard_get()
                            except tk.TclError:
                                pass
                                # print("Clipboard contains non-text data, possibly an image or other formats")
                            except Exception as err:
                                print("Error handling clipboard content:", err)
                                self.log_error()
                            if self.search_function_counter == 0 and "\"R-AOOO7" not in text_output and \
                                    "*R-A0007" not in text_output:
                                TeraTermUI.disable_user_input()
                                self.automate_copy_class_data()
                                TeraTermUI.disable_user_input("on")
                                copy = pyperclip.paste()
                                data, course_found, invalid_action, \
                                    y_n_found, y_n_value, term_value = TeraTermUI.extract_class_data(copy)
                                if "INVALID ACTION" in copy and "LISTA DE SECCIONES" not in copy:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.reset_activity_timer()
                                    self.after(100, self.show_error_message, 320, 235, translation["failed_to_search"])
                                    return
                                elif "INVALID ACTION" in copy and "LISTA DE SECCIONES" in copy:
                                    self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}")
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.reset_activity_timer()
                                    self.after(100, self.show_error_message, 320, 235, translation["failed_to_search"])
                                    return
                                if data or course_found or invalid_action or y_n_found:
                                    self.search_function_counter += 1
                                if classes in copy and show_all == y_n_value and semester == term_value:
                                    if "MORE SECTIONS" in text_output:
                                        self.after(0, self.search_next_page_layout)
                                    else:
                                        def hide_next_button():
                                            self.search_next_page.grid_forget()
                                            self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
                                            self.search.configure(width=140)
                                            self.search_next_page_status = False

                                        self.after(0, hide_next_button)
                                    self.get_class_for_pdf = classes
                                    self.get_semester_for_pdf = semester
                                    self.show_all_sections = show_all
                                    self.after(0, self.display_searched_class_data, data)
                                    self.clipboard_clear()
                                    if clipboard_content is not None:
                                        self.clipboard_append(clipboard_content)
                                    return
                            if not (self.get_class_for_pdf == classes and self.get_semester_for_pdf != semester and
                                    show_all == self.show_all_sections):
                                if self.search_function_counter == 0:
                                    self.uprb.UprbayTeraTermVt.type_keys(classes)
                                if self.search_function_counter >= 1:
                                    self.uprb.UprbayTeraTermVt.type_keys("1CS")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes)
                                self.uprb.UprbayTeraTermVt.type_keys("{TAB}")
                                if show_all == "on":
                                    self.uprb.UprbayTeraTermVt.type_keys("Y")
                                elif show_all == "off":
                                    self.uprb.UprbayTeraTermVt.type_keys("N")
                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            text_output = self.capture_screenshot()
                            if "MORE SECTIONS" in text_output:
                                self.after(0, self.search_next_page_layout)
                            else:
                                def hide_next_button():
                                    self.search_next_page.grid_forget()
                                    self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
                                    self.search.configure(width=140)
                                    self.search_next_page_status = False

                                self.after(0, hide_next_button)
                            if "COURSE NOT IN" in text_output:
                                if lang == "English":
                                    self.after(100, self.show_error_message, 300, 215,
                                               "Error! Course: " + classes + " not found")
                                elif lang == "Español":
                                    self.after(100, self.show_error_message, 310, 215,
                                               "Error! Clase: " + classes + " \nno se encontro")
                                self.search_function_counter += 1
                                self.after(0, self.s_classes_entry.configure(border_color="#c30101"))
                            elif "INVALID ACTION" in text_output or "INVALID TERM SELECTION" in text_output:
                                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                self.reset_activity_timer()
                                if "INVALID TERM SELECTION" in text_output:
                                    self.after(100, self.show_error_message, 320, 235, translation["invalid_semester"])
                                if "INVALID ACTION" in text_output:
                                    self.after(100, self.show_error_message, 320, 235, translation["failed_to_search"])
                                self.search_function_counter += 1
                            else:
                                TeraTermUI.disable_user_input()
                                self.search_function_counter += 1
                                self.automate_copy_class_data()
                                TeraTermUI.disable_user_input("on")
                                copy = pyperclip.paste()
                                data, course_found, invalid_action, \
                                    y_n_found, y_n_value, term_value = TeraTermUI.extract_class_data(copy)
                                self.get_class_for_pdf = classes
                                self.get_semester_for_pdf = semester
                                self.show_all_sections = show_all
                                self.after(0, self.display_searched_class_data, data)
                                self.clipboard_clear()
                                if clipboard_content is not None:
                                    self.clipboard_append(clipboard_content)
                        else:
                            if not classes or not semester:
                                self.after(100, self.show_error_message, 350, 230, translation["missing_info_search"])
                                if not classes:
                                    self.after(0, self.s_classes_entry.configure(border_color="#c30101"))
                                if not semester:
                                    self.after(0, self.s_semester_entry.configure(border_color="#c30101"))
                            elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE):
                                self.after(100, self.show_error_message, 360, 230, translation["class_format_error"])
                                self.after(0, self.s_classes_entry.configure(border_color="#c30101"))
                            elif not re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE) \
                                    and semester != curr_sem:
                                self.after(100, self.show_error_message, 360, 230, translation["semester_format_error"])
                                self.after(0, self.s_semester_entry.configure(border_color="#c30101"))
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as err:
                print("An error occurred: ", err)
                self.error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                               winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(50, error_automation)
                self.after(350, self.bind, "<Return>", lambda event: self.search_event_handler())
                TeraTermUI.disable_user_input()
                self.search_event_completed = True

    def search_next_page_layout(self):
        self.search_next_page_status = True
        self.search.configure(width=85)
        self.search.grid(row=1, column=1, padx=(285, 0), pady=(0, 5), sticky="n")
        self.search_next_page.grid(row=1, column=1, padx=(465, 0), pady=(0, 5), sticky="n")

    def check_refresh_semester(self):
        if self.enrolled_classes_table is None or not self.ask_semester_refresh:
            return False

        lang = self.language_menu.get()
        translation = self.load_language(lang)
        headers = [translation["course"], translation["grade"], translation["days"],
                   translation["times"], translation["room"]]
        enrolled_courses = set()
        discrepancies_found = False

        for row_index in range(1, len(self.enrolled_classes_data) + 1):
            cell = self.enrolled_classes_table.get_cell(row_index, headers.index(translation["course"]))
            course_info = cell.cget("text")
            course_parts = course_info.split("-")
            if len(course_parts) >= 3:
                course_name = f"{course_parts[0]}{course_parts[1]}"
                course_section = course_parts[2]
                enrolled_courses.add((course_name, course_section))

        for section, status_entry in self.classes_status.items():
            classes = status_entry["classes"]
            status = status_entry["status"]
            semester = status_entry["semester"]
            if semester == self.dialog_input:
                if (classes, section) not in enrolled_courses:
                    if status == "ENROLLED":
                        discrepancies_found = True
                        break
                elif (classes, section) in enrolled_courses:
                    if status == "DROPPED":
                        discrepancies_found = True
                        break
                elif any(classes == course and section != sec
                         for course, sec in enrolled_courses):
                    discrepancies_found = True
                    break

        if discrepancies_found:
            if not self.disable_audio:
                winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/update.wav"), winsound.SND_ASYNC)
            msg = CTkMessagebox(title=translation["submit"], icon="question",
                                message=translation["refresh_semester"].replace("{semester}", self.dialog_input),
                                option_1=translation["option_1"], option_2=translation["option_2"],
                                option_3=translation["option_3"], icon_size=(65, 65),
                                button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "use_default", "use_default"))
            response = msg.get()
            if response[0] == "Yes" or response[0] == "Sí":
                return True
            else:
                self.ask_semester_refresh = False
                return False

        return False

    def my_classes_event_handler(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.enrolled_classes_table is not None and not self.my_classes_frame.grid_info():
            self.tabview.grid_forget()
            self.back_classes.grid_forget()
            self.my_classes_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 100))
            self.modify_classes_frame.grid(row=2, column=2, sticky="nw", padx=(15, 0))
            self.back_my_classes.grid(row=4, column=0, padx=(0, 10), pady=(0, 0), sticky="w")
            if self.countdown_running:
                self.submit_my_classes.configure(state="disabled")
            self.show_classes.configure(text=translation["show_my_new"])
            self.in_enroll_frame = False
            self.in_search_frame = False
            self.add_key_bindings(event=None)
            self.my_classes_frame.scroll_to_top()
            self.unbind("<Control-Tab>")
            self.unbind("<Control-w>")
            self.unbind("<Control-W>")
            self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
            self.bind("<Up>", lambda event: self.move_up_scrollbar())
            self.bind("<Down>", lambda event: self.move_down_scrollbar())
            self.bind("<Home>", lambda event: self.move_top_scrollbar())
            self.bind("<End>", lambda event: self.move_bottom_scrollbar())
            self.bind("<Control-s>", lambda event: self.download_enrolled_classes_as_pdf(
                self.enrolled_classes_data, self.enrolled_classes_credits))
            self.bind("<Control-S>", lambda event: self.download_enrolled_classes_as_pdf(
                self.enrolled_classes_data, self.enrolled_classes_credits))
            self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_menu())

            def delayed_refresh_semester():
                refresh_semester = self.check_refresh_semester()
                if refresh_semester:
                    refresh_task_done = threading.Event()
                    refresh_loading_screen = self.show_loading_screen()
                    self.update_loading_screen(refresh_loading_screen, refresh_task_done)
                    self.thread_pool.submit(self.my_classes_event, self.dialog_input, task_done=refresh_task_done)
                    self.my_classes_event_completed = False

            self.after(500, delayed_refresh_semester)
        else:
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
            dialog_input = self.dialog.get_input()
            if dialog_input is not None:
                task_done = threading.Event()
                loading_screen = self.show_loading_screen()
                self.update_loading_screen(loading_screen, task_done)
                self.thread_pool.submit(self.my_classes_event, dialog_input, task_done=task_done)
                self.my_classes_event_completed = False
            else:
                self.dialog.destroy()

    # function for seeing the classes you are currently enrolled for
    def my_classes_event(self, dialog_input, task_done):
        with self.lock_thread:
            try:
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                dialog_input = dialog_input.upper().replace(" ", "")
                curr_sem = translation["current"].upper()
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if re.fullmatch("^[A-Z][0-9]{2}$", dialog_input, flags=re.IGNORECASE) or \
                                dialog_input == curr_sem:
                            self.wait_for_window()
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1CP")
                            if dialog_input == curr_sem:
                                result = self.handle_current_semester()
                                if result == "error":
                                    self.after(100, self.show_error_message, 300, 215, translation["invalid_semester"])
                                    return
                                elif result == "negative":
                                    return
                                else:
                                    dialog_input = result
                            self.uprb.UprbayTeraTermVt.type_keys(dialog_input)
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            text_output = self.capture_screenshot()
                            if "INVALID TERM SELECTION" not in text_output and "INVALID ACTION" not in text_output:
                                clipboard_content = None
                                try:
                                    clipboard_content = self.clipboard_get()
                                except tk.TclError:
                                    pass
                                    # print("Clipboard contains non-text data, possibly an image or other formats")
                                except Exception as err:
                                    print("Error handling clipboard content:", err)
                                    self.log_error()
                                TeraTermUI.disable_user_input()
                                self.automate_copy_class_data()
                                TeraTermUI.disable_user_input("on")
                                copy = pyperclip.paste()
                                enrolled_classes, total_credits = self.extract_my_enrolled_classes(copy)
                                self.after(0, self.enable_widgets, self)
                                self.after(0, self.display_enrolled_data, enrolled_classes,
                                           total_credits, dialog_input)
                                self.clipboard_clear()
                                if clipboard_content is not None:
                                    self.clipboard_append(clipboard_content)
                            else:
                                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                self.reset_activity_timer()
                                if "INVALID ACTION" in text_output:
                                    self.after(100, self.show_error_message, 320, 235, translation["failed_semester"])
                                else:
                                    self.after(100, self.show_error_message, 300, 215, translation["invalid_semester"])
                        else:
                            self.after(100, self.show_error_message, 300, 215, translation["invalid_semester"])
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as err:
                print("An error occurred: ", err)
                self.error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                               winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.switch_tab()
                        self.error_occurred = False

                    self.after(50, error_automation)
                TeraTermUI.disable_user_input()
                self.my_classes_event_completed = True

    # function that adds new entries
    def add_event(self):
        self.focus_set()
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        semester = self.m_semester_entry[0].get().upper().replace(" ", "")
        curr_sem = translation["current"].upper()
        if re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE) or semester == curr_sem:
            if self.a_counter + 1 < len(self.m_semester_entry):
                if self.a_counter == 0 and self.m_register_menu[0].get() == translation["register"] \
                        and self.first_time_adding:
                    register_menu_values = [menu.get() for menu in self.m_register_menu]
                    if all(value == translation["choose"] for value in register_menu_values[1:]):
                        for menu in self.m_register_menu:
                            menu.set(translation["register"])
                self.m_num_class[self.a_counter + 1].grid(row=self.a_counter + 2, column=0, padx=(0, 8), pady=(20, 0))
                self.m_classes_entry[self.a_counter + 1].grid(row=self.a_counter + 2, column=1, padx=(0, 500),
                                                              pady=(20, 0))
                self.m_section_entry[self.a_counter + 1].grid(row=self.a_counter + 2, column=1, padx=(0, 165),
                                                              pady=(20, 0))
                self.m_semester_entry[self.a_counter + 1].configure(state="normal")
                if semester == curr_sem:
                    self.m_semester_entry[self.a_counter + 1].set(translation["current"])
                else:
                    self.m_semester_entry[self.a_counter + 1].set(semester)
                self.m_semester_entry[self.a_counter + 1].configure(state="disabled")
                self.m_semester_entry[self.a_counter + 1].grid(row=self.a_counter + 2, column=1, padx=(165, 0),
                                                               pady=(20, 0))
                self.m_register_menu[self.a_counter + 1].grid(row=self.a_counter + 2, column=1, padx=(500, 0),
                                                              pady=(20, 0))
                self.a_counter += 1
                if self.m_register_menu[0].get() == translation["register"]:
                    self.first_time_adding = False
                if self.a_counter > 0:
                    self.m_remove.configure(state="normal")
                if self.a_counter == 7:
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
            if self.a_counter == 0:
                self.m_remove.configure(state="disabled")

    def add_event_up_arrow_key(self):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists() or \
                self.countdown_running or self.started_auto_enroll:
            return

        if self.up_arrow_key_enabled and self.a_counter != 7:
            self.add_event()

    def remove_event_down_arrow_key(self):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists() or \
                self.countdown_running or self.started_auto_enroll:
            return

        if self.down_arrow_key_enabled and self.a_counter != 0:
            self.remove_event()

    def move_up_scrollbar(self):
        if self.up_arrow_key_enabled:
            if self.enrolled_classes_table is not None and self.my_classes_frame.grid_info():
                self.my_classes_frame.scroll_more_up()
            else:
                self.search_scrollbar.scroll_more_up()

    def move_down_scrollbar(self):
        if self.down_arrow_key_enabled:
            if self.enrolled_classes_table is not None and self.my_classes_frame.grid_info():
                self.my_classes_frame.scroll_more_down()
            else:
                self.search_scrollbar.scroll_more_down()

    def move_top_scrollbar(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            if self.enrolled_classes_table is not None and self.my_classes_frame.grid_info():
                self.my_classes_frame.scroll_to_top()
            else:
                self.search_scrollbar.scroll_to_top()

    def move_bottom_scrollbar(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            if self.enrolled_classes_table is not None and self.my_classes_frame.grid_info():
                self.my_classes_frame.scroll_to_bottom()
            else:
                self.search_scrollbar.scroll_to_bottom()

    # multiple classes screen
    def multiple_classes_event(self):
        self.tabview.grid_forget()
        self.t_buttons_frame.grid_forget()
        if self.enrolled_classes_table is not None:
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            self.my_classes_frame.grid_forget()
            self.modify_classes_frame.grid_forget()
            self.back_my_classes.grid_forget()
            self.show_classes.configure(text=translation["show_my_classes"])
        self.in_enroll_frame = False
        self.in_search_frame = False
        self.in_multiple_screen = True
        self.add_key_bindings(event=None)
        self.unbind("<Control-Tab>")
        self.unbind("<Control-w>")
        self.unbind("<Control-W>")
        self.bind("<Control-s>", self.keybind_save_classes)
        self.bind("<Control-S>", self.keybind_save_classes)
        self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
        self.bind("<Up>", lambda event: self.add_event_up_arrow_key())
        self.bind("<Down>", lambda event: self.remove_event_down_arrow_key())
        self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_menu())
        self.destroy_tooltip()
        self.multiple_frame.grid(row=0, column=1, columnspan=4, rowspan=4, padx=(0, 0), pady=(0, 50))
        self.multiple_frame.grid_columnconfigure(2, weight=1)
        self.m_button_frame.grid(row=3, column=1, columnspan=4, rowspan=4, padx=(0, 0), pady=(0, 8))
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

    def detect_change(self, event=None):
        self.cursor.execute("SELECT COUNT(*) FROM saved_classes")
        count = self.cursor.fetchone()[0]
        if count == 0:
            return

        triggered_widget = event.widget if event is not None else None

        while triggered_widget:
            if triggered_widget in self.m_classes_entry:
                entry_list = self.m_classes_entry
                column_name = "class"
                changed_set = self.changed_classes
            elif triggered_widget in self.m_section_entry:
                entry_list = self.m_section_entry
                column_name = "section"
                changed_set = self.changed_sections
            elif triggered_widget in self.m_semester_entry:
                entry_list = self.m_semester_entry
                column_name = "semester"
                changed_set = self.changed_semesters
            elif triggered_widget in self.m_register_menu:
                entry_list = self.m_register_menu
                column_name = "action"
                changed_set = self.changed_registers
            else:
                triggered_widget = triggered_widget.master
                continue

            entry_index = entry_list.index(triggered_widget)
            entry_value = triggered_widget.get().upper().replace(" ", "").replace("-", "")
            if triggered_widget in self.m_semester_entry:
                if entry_value in ["CURRENT", "ACTUAL"]:
                    entry_value = "CURRENT"
            db_row_number = entry_index + 1
            query = f"SELECT {column_name} FROM saved_classes LIMIT 1 OFFSET ?"
            self.cursor.execute(query, (db_row_number - 1,))
            result = self.cursor.fetchone()
            if column_name == "semester" and result:
                db_value = result[0].upper().replace(" ", "").replace("-", "")
                if db_value in ["CURRENT", "ACTUAL"]:
                    db_value = "CURRENT"
                result = (db_value,)
            if result and entry_value != result[0]:
                changed_set.add(entry_index)
            else:
                changed_set.discard(entry_index)
            self.update_save_data_state()
            break

    def detect_register_menu_change(self, selected_value, index):
        self.focus_set()
        self.cursor.execute("SELECT COUNT(*) FROM saved_classes")
        count = self.cursor.fetchone()[0]
        if count == 0:
            return

        register_menu = self.m_register_menu[index]
        if register_menu.get() != selected_value:
            return

        db_row_number = index + 1
        self.cursor.execute("SELECT action FROM saved_classes LIMIT 1 OFFSET ?", (db_row_number - 1,))
        result = self.cursor.fetchone()

        if result:
            db_value = result[0]
            normalized_selected_value = "REGISTER" if selected_value.upper() in ["REGISTER", "REGISTRA"] else "DROP"
            normalized_db_value = "REGISTER" if db_value.upper() in ["REGISTER", "REGISTRA"] else "DROP"

            if normalized_selected_value != normalized_db_value:
                self.changed_registers.add(index)
            else:
                self.changed_registers.discard(index)
        self.update_save_data_state()

    def update_save_data_state(self):
        if any([self.changed_classes, self.changed_sections, self.changed_semesters, self.changed_registers]):
            if self.save_data.get() == "on":
                self.save_data.deselect()
        else:
            if self.save_data.get() == "off":
                self.save_data.select()

    def submit_multiple_event_handler(self):
        if self.started_auto_enroll and (not self.search_event_completed or not self.option_menu_event_completed or not
                                         self.go_next_event_completed or not self.search_go_next_event_completed or not
                                         self.my_classes_event_completed or not self.fix_execution_event_completed
                                         or not self.submit_feedback_event_completed):
            self.after(500, self.submit_multiple_event_handler)
        elif self.started_auto_enroll:
            self.end_countdown()
        if self.countdown_running:
            return

        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.focus_set()
        if not self.started_auto_enroll:
            msg = CTkMessagebox(title=translation["submit"], message=translation["enroll_multiple"],
                                icon=TeraTermUI.get_absolute_path("images/submit.png"),
                                option_1=translation["option_1"], option_2=translation["option_2"],
                                option_3=translation["option_3"], icon_size=(65, 65),
                                button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "use_default", "use_default"))
            response = msg.get()
            if response[0] != "Yes" and response[0] != "Sí":
                return
        self.error_auto_enroll = False
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        self.thread_pool.submit(self.submit_multiple_event, task_done=task_done)

    # function that enrolls multiple classes with one click
    def submit_multiple_event(self, task_done):
        with self.lock_thread:
            try:
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                classes = []
                sections = []
                choices = []
                semester = self.m_semester_entry[0].get().upper().replace(" ", "")
                curr_sem = translation["current"].upper()
                for i in range(self.a_counter + 1):
                    classes.append(self.m_classes_entry[i].get().upper().replace(" ", "").replace("-", ""))
                    sections.append(self.m_section_entry[i].get().upper().replace(" ", ""))
                    choices.append(self.m_register_menu[i].get())
                can_enroll_classes = self.e_counter + self.m_counter + self.a_counter + 1 <= 15
                if asyncio.run(self.test_connection(lang)) and self.check_server() and self.check_format():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if can_enroll_classes:
                            self.wait_for_window()
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1S4")
                            if semester == curr_sem:
                                result = self.handle_current_semester()
                                if result == "error":
                                    self.after(100, self.show_error_message, 320, 235,
                                               translation["failed_enroll_multiple"])
                                    return
                                elif result == "negative":
                                    return
                                else:
                                    semester = result
                            self.uprb.UprbayTeraTermVt.type_keys(semester)
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            text_output = self.capture_screenshot()
                            enrolled_classes = "ENROLLED"
                            count_enroll = text_output.count(enrolled_classes)
                            if "OUTDATED" not in text_output and "INVALID TERM SELECTION" not in text_output and \
                                    "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" not in text_output \
                                    and "ENTER REGISTRATION" in text_output and count_enroll != 15:
                                self.e_counter = 0
                                self.m_counter = 0
                                self.uprb.UprbayTeraTermVt.type_keys("{TAB 3}")
                                for i in range(count_enroll, 0, -1):
                                    self.e_counter += 1
                                    self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}")
                                for i in range(self.a_counter + 1):
                                    if choices[i] in ["Register", "Registra"]:
                                        self.uprb.UprbayTeraTermVt.type_keys("R")
                                    elif choices[i] in ["Drop", "Baja"]:
                                        self.uprb.UprbayTeraTermVt.type_keys("D")
                                    self.uprb.UprbayTeraTermVt.type_keys(classes[i])
                                    self.uprb.UprbayTeraTermVt.type_keys(sections[i])
                                    self.m_counter += 1
                                    if i == self.a_counter:
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    else:
                                        self.uprb.UprbayTeraTermVt.type_keys("{TAB}")
                                text_output = self.wait_for_response(["CONFIRMED", "DROPPED"])
                                dropped_classes = "DROPPED"
                                count_dropped = text_output.count(dropped_classes)
                                self.reset_activity_timer()
                                if "CONFIRMED" in text_output or "DROPPED" in text_output:
                                    self.m_counter -= count_dropped
                                    self.e_counter -= count_dropped
                                    choice = [
                                        (self.m_register_menu[i].get(), i,
                                         self.m_section_entry[i].get().upper().replace(" ", ""),
                                         self.m_classes_entry[i].get().upper().replace(" ", ""),
                                         self.m_semester_entry[i].get().upper().replace(" ", ""))
                                        for i in range(self.a_counter + 1)
                                    ]
                                    for c, cnt, sec, cls, sem in choice:
                                        if sec:
                                            if c in ["Register", "Registra"]:
                                                self.classes_status[sec] = {"classes": cls, "status": "ENROLLED",
                                                                            "semester": sem}
                                            elif c in ["Drop", "Baja"]:
                                                self.classes_status[sec] = {"classes": cls, "status": "DROPPED",
                                                                            "semester": sem}
                                    self.submit_multiple.configure(state="disabled")
                                    self.submit_multiple.configure(state="disabled")
                                    self.unbind("<Return>")
                                    self.not_rebind = True
                                    self.after(2500, self.show_enrollment_error_information_multiple, text_output)
                                    if "CONFIRMED" in text_output and "DROPPED" in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        time.sleep(1)
                                        self.after(100, self.show_success_message, 350, 265,
                                                   translation["enrolled_dropped_multiple_success"])
                                    elif "CONFIRMED" in text_output and "DROPPED" not in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        time.sleep(1)
                                        self.after(100, self.show_success_message, 350, 265,
                                                   translation["enrolled_multiple_success"])
                                    elif "DROPPED" in text_output and "CONFIRMED" not in text_output:
                                        self.after(100, self.show_success_message, 350, 265,
                                                   translation["dropped_multiple_success"])
                                    if self.e_counter + self.m_counter == 15:
                                        self.go_back_menu()
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
                                    self.after(2500, self.show_enrollment_error_information_multiple, text_output)
                                    self.m_counter = self.m_counter - self.a_counter - 1
                            else:
                                if count_enroll == 15:
                                    self.submit.configure(state="disabled")
                                    self.submit_multiple.configure(sate="disabled")
                                    self.after(100, self.show_information_message, 350, 265,
                                               translation["enrollment_limit"])
                                if "INVALID TERM SELECTION" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.reset_activity_timer()
                                    self.after(100, self.show_error_message, 300, 215,
                                               translation["invalid_semester"])
                                else:
                                    if "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" not in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        self.reset_activity_timer()
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
                                            self.after(2500, self.show_enrollment_error_information)
                                            self.enrollment_error_check = True
                        else:
                            self.after(100, self.show_error_message, 320, 235,
                                       translation["max_enroll"])
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as err:
                print("An error occurred: ", err)
                self.error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                if not self.error_auto_enroll:
                    self.started_auto_enroll = False
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                               winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="question", button_width=380)
                        self.error_occurred = False

                    self.after(50, error_automation)
                if not self.not_rebind:
                    self.after(350, self.bind, "<Return>", lambda event: self.submit_multiple_event_handler())
                TeraTermUI.disable_user_input()

    def option_menu_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        self.thread_pool.submit(self.option_menu_event, task_done=task_done)
        self.option_menu_event_completed = False

    # changes to the respective screen the user chooses
    def option_menu_event(self, task_done):
        with self.lock_thread:
            try:
                self.automation_preparations()
                menu = self.menu_entry.get()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                semester = self.menu_semester_entry.get().upper().replace(" ", "")
                curr_sem = translation["current"].upper()
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
                menu = menu_dict.get(menu, menu).replace(" ", "").upper()
                valid_menu_options = set(menu_dict.values())
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if menu and menu in valid_menu_options and (
                                re.fullmatch("^[A-Z][0-9]{2}$", semester,
                                             flags=re.IGNORECASE) or semester == curr_sem):
                            self.wait_for_window()
                            result = None
                            if semester == curr_sem:
                                if not self.found_latest_semester:
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                result = self.handle_current_semester()
                                if result == "error":
                                    self.focus_or_not = True
                                    self.after(100, self.show_error_message, 300, 215, translation["invalid_semester"])
                                    return
                                elif result == "negative":
                                    return
                                else:
                                    semester = result
                            match menu:
                                case "SRM":
                                    if result is None:
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                case "004":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("004")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                case "1GP":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("1GP")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" not in text_output:
                                        def go_next_grid():
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
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        self.reset_activity_timer()
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "118":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("118")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        self.reset_activity_timer()
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "1VE":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("1VE")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "CONFLICT" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys("004")
                                        self.uprb.UprbayTeraTermVt.type_keys(semester)
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        self.after(100, self.show_information_message, 310, 225,
                                                   translation["hold_flag"])
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        self.reset_activity_timer()
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                    if "CONFLICT" not in text_output or "INVALID TERM SELECTION" not in text_output:
                                        def go_next_grid():
                                            self._1VE_screen = True
                                            self._1GP_screen = False
                                            self._409_screen = False
                                            self._683_screen = False
                                            self._4CM_screen = False
                                            self.menu_submit.configure(width=100)
                                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0),
                                                                  sticky="n")
                                            self.go_next_1VE.grid(row=5, column=1, padx=(110, 0), pady=(40, 0),
                                                                  sticky="n")

                                        self.after(0, go_next_grid)
                                case "3DD":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("3DD")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        self.reset_activity_timer()
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "409":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("409")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" not in text_output:
                                        def go_next_grid():
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
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        self.reset_activity_timer()
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "683":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("683")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "CONFLICT" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys("004")
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        self.after(100, self.show_information_message, 310, 225,
                                                   translation["hold_flag"])
                                    if "CONFLICT" not in text_output:
                                        def go_next_grid():
                                            self._1VE_screen = False
                                            self._1GP_screen = False
                                            self._409_screen = False
                                            self._683_screen = True
                                            self._4CM_screen = False
                                            self.menu_submit.configure(width=100)
                                            self.menu_submit.grid(row=5, column=1, padx=(0, 110), pady=(40, 0),
                                                                  sticky="n")
                                            self.go_next_683.grid(row=5, column=1, padx=(110, 0), pady=(40, 0),
                                                                  sticky="n")

                                        self.after(0, go_next_grid)
                                case "1PL":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("1PL")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "TERM OUTDATED" in text_output or "NO PUEDE REALIZAR CAMBIOS" in text_output or \
                                            "INVALID TERM SELECTION" in text_output:
                                        self.focus_or_not = True
                                        if "TERM OUTDATED" in text_output or "INVALID TERM SELECTION" in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                            self.reset_activity_timer()
                                        if lang == "English":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "Error! Failed to enter\n " + self.menu_entry.get()
                                                       + " screen")
                                        elif lang == "Español":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "¡Error! No se pudo entrar \n a la pantalla" +
                                                       self.menu_entry.get())
                                    else:
                                        def warning():
                                            if not self.disable_audio:
                                                winsound.PlaySound(
                                                    TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                                    winsound.SND_ASYNC)
                                            CTkMessagebox(title=translation["warning_title"],
                                                          message=translation["1PL_pdata"], icon="warning",
                                                          button_width=380)
                                            self.went_to_1PL_screen = True

                                        self.focus_or_not = True
                                        self.after(100, warning)
                                case "4CM":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("4CM")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "TERM OUTDATED" not in text_output and \
                                            "NO PUEDE REALIZAR CAMBIOS" not in text_output and \
                                            "INVALID TERM SELECTION" not in text_output:
                                        def go_next_grid():
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
                                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                            self.reset_activity_timer()
                                        if lang == "English":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "Error! Failed to enter\n " + self.menu_entry.get() + " screen")
                                        elif lang == "Español":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "Error! No se pudo entrar"
                                                       "\n a la pantalla" + self.menu_entry.get())
                                case "4SP":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("4SP")
                                    self.uprb.UprbayTeraTermVt.type_keys(semester)
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "TERM OUTDATED" in text_output or "NO PUEDE REALIZAR CAMBIOS" in text_output:
                                        self.focus_or_not = True
                                        if "TERM OUTDATED" in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                            self.reset_activity_timer()
                                        if lang == "English":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "Error! Failed to enter\n " + self.menu_entry.get() + " screen")
                                        elif lang == "Español":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "Error! No se pudo entrar"
                                                       "\n a la pantalla" + self.menu_entry.get())
                                    else:
                                        def warning():
                                            if not self.disable_audio:
                                                winsound.PlaySound(
                                                    TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                                    winsound.SND_ASYNC)
                                            CTkMessagebox(title=translation["warning_title"],
                                                          message=translation["4SP_ext"], icon="warning",
                                                          button_width=380)

                                        self.focus_or_not = True
                                        self.after(100, warning)
                                case "SO":
                                    self.focus_or_not = True
                                    self.after(50, self.sign_out)
                        else:
                            self.focus_or_not = True
                            if not semester or not menu:
                                self.after(100, self.show_error_message, 350, 230,
                                           translation["menu_missing_info"])
                                if not semester:
                                    self.after(0, self.menu_semester_entry.configure(border_color="#c30101"))
                                if not menu:
                                    self.after(0, self.menu_entry.configure(border_color="#c30101"))
                            elif not re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE) \
                                    and semester != curr_sem:
                                self.after(100, self.show_error_message, 360, 230,
                                           translation["semester_format_error"])
                                self.after(0, self.menu_semester_entry.configure(border_color="#c30101"))
                            elif menu not in menu_dict.values():
                                self.after(100, self.show_error_message, 340, 230,
                                           translation["menu_code_error"])
                                self.after(0, self.menu_entry.configure(border_color="#c30101"))
                    else:
                        self.focus_or_not = True
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as err:
                print("An error occurred: ", err)
                self.error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if self.focus_or_not or self.error_occurred:
                    self.after(100, self.set_focus_to_tkinter)
                else:
                    self.after(100, self.focus_tera_term)
                self.focus_or_not = False
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                               winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(50, error_automation)
                self.after(350, self.bind, "<Return>", lambda event: self.option_menu_event_handler())
                TeraTermUI.disable_user_input()
                self.option_menu_event_completed = True

    def sign_out(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        msg = CTkMessagebox(title=translation["so_title"], message=translation["so_message"],
                            option_1=translation["option_1"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if TeraTermUI.checkIfProcessRunning("ttermpro") and response[0] == "Yes" \
                or response[0] == "Sí":
            self.wait_for_window()
            self.uprb.UprbayTeraTermVt.type_keys("SO")
            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
            self.after(0, self.disable_go_next_buttons)
        elif not TeraTermUI.checkIfProcessRunning("ttermpro") and response[0] == "Yes" \
                or response[0] == "Sí":
            self.focus_or_not = True
            self.after(100, self.show_error_message, 350, 265,
                       translation["tera_term_not_running"])

    def go_next_page_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        self.thread_pool.submit(self.go_next_page_event, task_done=task_done)
        self.go_next_event_completed = False

    # go through each page of the different screens
    def go_next_page_event(self, task_done):
        with self.lock_thread:
            try:
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        self.wait_for_window()
                        if self._1VE_screen:
                            self.uprb.UprbayTeraTermVt.type_keys("{TAB 3}")
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.reset_activity_timer()
                        elif self._1GP_screen:
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.reset_activity_timer()
                        elif self._409_screen:
                            self.uprb.UprbayTeraTermVt.type_keys("{TAB 4}")
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.reset_activity_timer()
                        elif self._683_screen:
                            self.went_to_683_screen = True
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.reset_activity_timer()
                        elif self._4CM_screen:
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.reset_activity_timer()
                            text_output = self.capture_screenshot()
                            if "RATE NOT ON ARFILE" in text_output:
                                self.focus_or_not = True
                                self.after(100, self.show_error_message, 310, 225, translation["unknown_error"])
                            else:
                                self.after(0, self.disable_go_next_buttons)
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as err:
                print("An error occurred: ", err)
                self.error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.reset_activity_timer()
                if self.focus_or_not:
                    self.after(100, self.set_focus_to_tkinter)
                else:
                    self.after(100, self.focus_tera_term)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                               winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(50, error_automation)
                self.after(350, self.bind, "<Return>", lambda event: self.option_menu_event_handler())
                TeraTermUI.disable_user_input()
                self.go_next_event_completed = True

    def go_next_search_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        self.thread_pool.submit(self.search_go_next, task_done=task_done)
        self.search_go_next_event_completed = False

    # Goes through more sections available for the searched class
    def search_go_next(self, task_done):
        with self.lock_thread:
            try:
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.automation_preparations()
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        self.wait_for_window()
                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                        time.sleep(0.5)
                        clipboard_content = None
                        try:
                            clipboard_content = self.clipboard_get()
                        except tk.TclError:
                            pass
                            # print("Clipboard contains non-text data, possibly an image or other formats")
                        except Exception as err:
                            print("Error handling clipboard content:", err)
                            self.log_error()
                        TeraTermUI.disable_user_input()
                        self.automate_copy_class_data()
                        TeraTermUI.disable_user_input("on")
                        copy = pyperclip.paste()
                        data, course_found, invalid_action, \
                            y_n_found, y_n_value, term_value = TeraTermUI.extract_class_data(copy)
                        self.after(0, self.display_searched_class_data, data)
                        self.clipboard_clear()
                        if clipboard_content is not None:
                            self.clipboard_append(clipboard_content)
                        self.reset_activity_timer()
                        text_output = self.capture_screenshot()
                        if "MORE SECTIONS" not in text_output:
                            def hide_next_button():
                                self.search_next_page.grid_forget()
                                self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
                                self.search.configure(width=140)
                                self.search_next_page_status = False

                            self.after(0, hide_next_button)
                        section = self.s_classes_entry.get().upper().replace(" ", "").replace("-", "")
                        if section != self.get_class_for_pdf:
                            self.s_classes_entry.configure(state="normal")
                            self.s_classes_entry.delete(0, "end")
                            self.s_classes_entry.insert(0, self.get_class_for_pdf)
                            self.s_classes_entry.configure(state="disabled")
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as err:
                print("An error occurred: ", err)
                self.error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                               winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(50, error_automation)
                self.after(350, self.bind, "<Return>", lambda event: self.search_event_handler())
                TeraTermUI.disable_user_input()
                self.search_go_next_event_completed = True

    # disable these buttons if the user changed screen
    def disable_go_next_buttons(self):
        if self.init_class:
            self.go_next_1VE.grid_forget()
            self.go_next_1GP.grid_forget()
            self.go_next_409.grid_forget()
            self.go_next_683.grid_forget()
            self.go_next_4CM.grid_forget()
            self.menu_submit.configure(width=140)
            self.menu_submit.grid(row=5, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
            self.search_next_page.grid_forget()
            self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
            self.search.configure(width=140)
            self.search_next_page_status = False
            self._1VE_screen = False
            self._1GP_screen = False
            self._409_screen = False
            self._683_screen = False
            self._4CM_screen = False
        self.reset_activity_timer()

    def auth_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        self.thread_pool.submit(self.auth_event, task_done=task_done)

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
                        allowed_roles = {"students", "student", "estudiantes", "estudiante"}
                        if username in allowed_roles:
                            username = "students"
                            self.wait_for_window()
                            TeraTermUI.check_window_exists("SSH Authentication")
                            user = self.uprb.UprbayTeraTermVt.child_window(title="User name:", control_type="Edit")
                            if user.get_value() != username:
                                user.set_text(username)
                            check = self.uprb.UprbayTeraTermVt.child_window(
                                title="Remember password in memory", control_type="CheckBox")
                            if check.get_toggle_state() == 0:
                                check.invoke()
                            radio = self.uprb.UprbayTeraTermVt.child_window(
                                title="Use plain password to log in", control_type="RadioButton")
                            if not radio.is_selected():
                                radio.invoke()
                            self.uprb.UprbayTeraTermVt.child_window(title="OK", control_type="Button").invoke()
                            self.server_status = self.wait_for_prompt(
                                "return to continue", "REGRESE PRONTO")
                            if self.server_status == "Maintenance message found":
                                def server_closed():
                                    if not self.skip_auth:
                                        self.back.configure(state="disabled")
                                        self.auth.configure(state="disabled")
                                    if not self.disable_audio:
                                        winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"),
                                                           winsound.SND_ASYNC)
                                    CTkMessagebox(title=translation["server_maintenance_title"],
                                                  message=translation["server_maintenance"], icon="cancel",
                                                  button_width=380)
                                    self.error_occurred = True

                                self.after(125, server_closed)
                            elif self.server_status == "Prompt found":
                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER 3}")
                                self.move_window()
                                self.bind("<Return>", lambda event: self.student_event_handler())
                                if self.skip_auth:
                                    self.after(0, self.home_frame.grid_forget)
                                self.after(0, self.initialization_student)
                                self.after(0, self.destroy_auth)
                                self.after(50, self.auth_info_frame)
                                self.in_auth_frame = False
                                self.in_student_frame = True
                            elif self.server_status == "Timeout":
                                def timeout():
                                    if not self.skip_auth:
                                        self.back.configure(state="disabled")
                                        self.auth.configure(state="disabled")
                                    if not self.disable_audio:
                                        winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"),
                                                           winsound.SND_ASYNC)
                                    CTkMessagebox(title="Error", message=translation["timeout_server"], icon="cancel",
                                                  button_width=380)
                                    self.error_occurred = True

                                self.after(125, timeout)
                        elif username != "students":
                            self.after(350, self.bind, "<Return>", lambda event: self.auth_event_handler())
                            self.after(100, self.show_error_message, 300, 215, translation["invalid_username"])
                            self.after(0, self.username_entry.configure(border_color="#c30101"))
                    else:
                        self.after(350, self.bind, "<Return>", lambda event: self.auth_event_handler())
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
                else:
                    self.after(350, self.bind, "<Return>", lambda event: self.auth_event_handler())
            except Exception as err:
                print("An error occurred: ", err)
                self.error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                self.reset_activity_timer()
                self.after(100, self.set_focus_to_tkinter)
                if self.server_status == "Maintenance message found" or self.server_status == "Timeout":
                    self.after(3500, self.go_back_home)
                elif self.error_occurred:
                    self.after(0, self.go_back_home)
                if self.log_in.cget("state") == "disabled":
                    self.log_in.configure(state="normal")
                TeraTermUI.disable_user_input()

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
        if self.ask_skip_auth and not self.skipped_login:
            self.unbind("<Return>")
            self.unbind("<Control-BackSpace>")
            self.system.configure(state="disabled")
            self.back_student.configure(state="disabled")
            self.after(750, self.skip_auth_prompt)

    def skip_auth_prompt(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if not self.disable_audio:
            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/update.wav"), winsound.SND_ASYNC)
        msg = CTkMessagebox(title=translation["skip_auth_title"], message=translation["skip_auth"],
                            icon="question", option_1=translation["option_1"], option_2=translation["option_2"],
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
        self.bind("<Return>", lambda event: self.student_event_handler())
        self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_home())
        self.system.configure(state="normal")
        self.back_student.configure(state="normal")
        self.ask_skip_auth = False

    def keybind_disable_enable_auth(self):
        if self.skip_auth_switch.get() == "on":
            self.skip_auth_switch.deselect()
        elif self.skip_auth_switch.get() == "off":
            self.skip_auth_switch.select()
        self.disable_enable_auth()

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

    def notice_user(self, running_launchers):
        if self.error is not None and self.error.winfo_exists():
            return
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.transient(self)
        self.tooltip.config(bg="#FFD700")
        self.tooltip.wm_geometry(f"+{main_window_x + 20}+{main_window_y + 20}")
        launcher_names = {
            "EpicGamesLauncher": "Epic",
            "SteamWebHelper": "Steam",
            "RockstarService": "Rockstar"
        }
        if running_launchers:
            launchers_list = ", ".join([launcher_names[launcher] for launcher in running_launchers])
            text = translation["game_launchers"].format(launchers_list)
        else:
            text = translation["exec_time"]
        label = tk.Label(self.tooltip, text=text, bg="#FFD700", fg="#000", font=("Verdana", 11, "bold"))
        label.pack(padx=5, pady=5)
        self.lift_tooltip()
        if not self.skip_auth:
            self.tooltip.after(15000, self.destroy_tooltip)
        else:
            self.tooltip.after(20000, self.destroy_tooltip)
        self.tooltip.bind("<Button-1>", lambda event: self.destroy_tooltip())
        self.tooltip.bind("<Button-2>", lambda event: self.destroy_tooltip())
        self.tooltip.bind("<Button-3>", lambda event: self.destroy_tooltip())

    def login_event_handler(self):
        task_done = threading.Event()
        loading_screen = self.show_loading_screen()
        self.update_loading_screen(loading_screen, task_done)
        self.thread_pool.submit(self.login_event, task_done=task_done)

    # logs in the user to the respective university, opens up Tera Term
    @measure_time(threshold=12)
    def login_event(self, task_done):
        with self.lock_thread:
            try:
                new_connection = False
                dont_close = False
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                host = self.host_entry.get().replace(" ", "").lower()
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if host in ["uprbay.uprb.edu", "uprbayuprbedu", "uprb"]:
                        TeraTermUI.check_tera_term_hidden()
                        if TeraTermUI.checkIfProcessRunning("ttermpro"):
                            count, is_multiple = TeraTermUI.countRunningProcesses("ttermpro")
                            if is_multiple:
                                self.after(100, self.show_error_message, 450, 270, translation["count_processes"])
                                self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
                                return
                            if TeraTermUI.window_exists("Tera Term: New connection"):
                                new_connection = True
                            else:
                                self.login_to_existent_connection()
                                dont_close = True
                                return
                        try:
                            if self.teraterm5_first_boot:
                                first_boot = Application(backend="uia").start(self.location, timeout=3)
                                timings.wait_until_passes(10, 1, lambda: first_boot.window(
                                    title="Tera Term - [disconnected] VT", class_name="VTWin32",
                                    control_type="Window").exists())
                                first_boot.connect(title="Tera Term - [disconnected] VT", class_name="VTWin32",
                                                   control_type="Window", timeout=3)
                                first_boot.kill(soft=True)
                                self.set_focus_to_tkinter()
                            if self.download or self.teraterm_not_found or self.teraterm5_first_boot:
                                self.edit_teraterm_ini(self.teraterm_file)
                            if not new_connection:
                                self.uprb = Application(backend="uia").start(self.location, timeout=3)
                                timings.wait_until_passes(10, 1, lambda: self.uprb.window(
                                    title="Tera Term - [disconnected] VT", class_name="VTWin32",
                                    control_type="Window").exists())
                                self.uprb.connect(title="Tera Term - [disconnected] VT", class_name="VTWin32",
                                                  control_type="Window", timeout=3)
                            else:
                                self.uprb = Application(backend="uia").connect(
                                    title="Tera Term - [disconnected] VT", timeout=3,
                                    class_name="VTWin32", control_type="Window")
                            self.uprb_32 = Application().connect(title="Tera Term - [disconnected] VT",
                                                                 timeout=3, class_name="VTWin32")
                            edit_menu = self.uprb.UprbayTeraTermVt.child_window(title="Edit", control_type="MenuItem")
                            self.select_screen_item = edit_menu.child_window(
                                title="Select screen", control_type="MenuItem", auto_id="50280")
                            disconnected = self.uprb.window(title="Tera Term - [disconnected] VT", class_name="VTWin32",
                                                            control_type="Window")
                            disconnected.wait("visible", timeout=3)
                            TeraTermUI.check_window_exists("Tera Term: New connection")
                            if new_connection:
                                TeraTermUI.new_connection(disconnected)
                            host_input = self.uprb.TeraTermDisconnectedVt.child_window(
                                title="Host:", control_type="Edit")
                            if host_input.get_value() != "uprbay.uprb.edu":
                                host_input.set_text("uprbay.uprb.edu")
                            self.uprb.TeraTermDisconnectedVt.child_window(title="OK", control_type="Button").invoke()
                            self.uprbay_window = self.uprb.window(
                                title="uprbay.uprb.edu - Tera Term VT", class_name="VTWin32", control_type="Window")
                            self.uprbay_window.wait("visible", timeout=3)
                            self.tera_term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            if self.uprbay_window.child_window(title="Continue", control_type="Button").exists(
                                    timeout=1):
                                self.uprbay_window.child_window(title="Continue", control_type="Button").invoke()
                            if not self.skip_auth:
                                self.bind("<Return>", lambda event: self.auth_event_handler())
                                self.after(0, self.initialization_auth)
                                self.in_auth_frame = True
                            else:
                                self.after(0, self.log_in.configure(state="disabled"))
                            self.after(50, self.login_frame)
                        except AppStartError as err:
                            print("An error occurred: ", err)
                            self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
                            self.after(100, self.show_error_message, 425, 330,
                                       translation["tera_term_failed_to_start"])
                            if not self.download:
                                self.after(3500, self.download_teraterm)
                                self.download = True
                    else:
                        self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
                        self.after(100, self.show_error_message, 300, 215, translation["invalid_host"])
                        self.after(0, self.host_entry.configure(border_color="#c30101"))
                else:
                    self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
            except Exception as err:
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                error_message = str(err)
                if "catching classes that do not inherit from BaseException is not allowed" in error_message:
                    print("Caught the specific error message: ", error_message)
                    self.destroy_windows()

                    def rare_error():
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"), winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["unexpected_error"], icon="warning", button_width=380)
                        self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())

                    self.error_occurred = False
                    self.after(50, rare_error)
                else:
                    print("An error occurred:", error_message)
                    self.error_occurred = True
                    self.log_error()
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not dont_close:
                            TeraTermUI.terminate_process()
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"), winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["tera_term_forced_to_close"], icon="warning",
                                      button_width=380)
                        self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
                        self.error_occurred = False

                    self.after(50, error_automation)
                TeraTermUI.disable_user_input()

    def login_frame(self):
        lang = self.language_menu.get()
        if not self.skip_auth:
            self.home_frame.grid_forget()
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
        else:
            self.after(100, self.auth_event_handler)
            self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_home())
        self.main_menu = False
        if self.help is not None and self.help.winfo_exists():
            self.files.configure(state="disabled")
        self.intro_box.stop_autoscroll(event=None)
        self.slideshow_frame.pause_cycle()

    def login_to_existent_connection(self):
        timeout_counter = 0
        skip = False
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        keywords = ["STUDENTS REQ/DROP", "HOLD FLAGS", "PROGRAMA DE CLASES", "ACADEMIC STATISTICS", "SNAPSHOT",
                    "SOLICITUD DE PRORROGA", "LISTA DE SECCIONES", "AYUDA ECONOMICA", "EXPEDIENTE ACADEMICO", "AUDIT",
                    "PERSONAL DATA", "COMPUTO DE MATRICULA"]
        while not self.tesseract_unzipped:
            time.sleep(0.5)
            timeout_counter += 1
            if timeout_counter > 10:
                skip = True
                break
        hwnd_uprb = win32gui.FindWindow(None, "uprbay.uprb.edu - Tera Term VT")
        hwnd_tt = win32gui.FindWindow(None, "Tera Term")
        if TeraTermUI.window_exists("SSH Authentication") and hwnd_uprb and not skip:
            self.connect_to_uprb()
            self.bind("<Return>", lambda event: self.auth_event_handler())
            self.after(0, self.initialization_auth)
            self.after(50, self.login_frame)
            self.in_auth_frame = True
        elif TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT") and not skip:
            self.connect_to_uprb()
            if self.tera_term_window.isMinimized:
                self.tera_term_window.restore()
            text_output = self.capture_screenshot()
            to_continue = "return to continue"
            count_to_continue = text_output.count(to_continue)
            if "REGRESE PRONTO" in text_output:
                def server_closed():
                    if not self.disable_audio:
                        winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"), winsound.SND_ASYNC)
                    CTkMessagebox(title=translation["server_maintenance_title"],
                                  message=translation["server_maintenance"], icon="cancel", button_width=380)
                    self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
                    self.uprb.kill(soft=True)

                self.after(125, server_closed)
                return
            elif "return to continue" in text_output or "INFORMACION ESTUDIANTIL" in text_output:
                if hwnd_tt:
                    win32gui.PostMessage(hwnd_tt, WM_CLOSE, 0, 0)
                if "return to continue" in text_output and "Loading" in text_output:
                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER 3}")
                elif count_to_continue == 2 or "ZZZ" in text_output:
                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER 2}")
                elif count_to_continue == 1 or "automaticamente" in text_output:
                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                else:
                    self.uprb.UprbayTeraTermVt.type_keys("{VK_RIGHT}")
                    self.uprb.UprbayTeraTermVt.type_keys("{VK_LEFT}")
                self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_home())
                self.bind("<Return>", lambda event: self.student_event_handler())
                self.home_frame.grid_forget()
                self.after(0, self.initialization_student)
                self.after(50, self.auth_info_frame)
                self.in_student_frame = True
                self.skipped_login = True
                self.main_menu = False
                if self.help is not None and self.help.winfo_exists():
                    self.files.configure(state="disabled")
                self.intro_box.stop_autoscroll(event=None)
                self.slideshow_frame.pause_cycle()
                self.move_window()
            elif any(keyword in text_output for keyword in keywords):
                if hwnd_tt:
                    win32gui.PostMessage(hwnd_tt, WM_CLOSE, 0, 0)
                self.uprb.UprbayTeraTermVt.type_keys("{VK_RIGHT}")
                self.uprb.UprbayTeraTermVt.type_keys("{VK_LEFT}")
                self.connect_to_uprb()
                self.home_frame.grid_forget()
                self.after(0, self.initialization_class)
                self.after(50, self.student_info_frame)
                self.after(100, self.initialization_multiple)
                self.reset_activity_timer()
                self.start_check_idle_thread()
                self.start_check_process_thread()
                self.run_fix = True
                self.main_menu = False
                if self.help is not None and self.help.winfo_exists():
                    self.files.configure(state="disabled")
                if self.help is not None and self.help.winfo_exists():
                    self.fix.configure(state="normal")
                self.intro_box.stop_autoscroll(event=None)
                self.slideshow_frame.pause_cycle()
                self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_home())
                self.switch_tab()
                self.move_window()
            else:
                self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
                self.after(100, self.show_error_message, 450, 265,
                           translation["tera_term_already_running"])
        else:
            self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
            self.after(100, self.show_error_message, 450, 265,
                       translation["tera_term_already_running"])

    def connect_to_uprb(self):
        self.uprb = Application(backend="uia").connect(
            title="uprbay.uprb.edu - Tera Term VT", timeout=3, class_name="VTWin32", control_type="Window")
        self.uprb_32 = Application().connect(
            title="uprbay.uprb.edu - Tera Term VT", timeout=3, class_name="VTWin32")
        self.uprbay_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT",
                                              class_name="VTWin32", control_type="Window")
        self.uprbay_window.wait("visible", timeout=3)
        edit_menu = self.uprb.UprbayTeraTermVt.child_window(title="Edit", control_type="MenuItem")
        self.select_screen_item = edit_menu.child_window(
            title="Select screen", control_type="MenuItem", auto_id="50280")
        self.tera_term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]

    @staticmethod
    def new_connection(window):
        new_connection = window.child_window(title="Tera Term: New connection")
        new_connection.wait("visible", timeout=5)
        tcp_ip_radio = new_connection.child_window(title="TCP/IP", control_type="RadioButton")
        if not tcp_ip_radio.is_selected():
            tcp_ip_radio.invoke()
        history_checkbox = new_connection.child_window(title="History", control_type="CheckBox")
        if not history_checkbox.get_toggle_state():
            history_checkbox.invoke()
        ssh_radio = new_connection.child_window(title="SSH", control_type="RadioButton")
        if not ssh_radio.is_selected():
            ssh_radio.invoke()
        tcp_port_edit = new_connection.child_window(title="TCP port#:", control_type="Edit")
        if tcp_port_edit.get_value() != "22":
            tcp_port_edit.set_text("22")
        ssh_version_combo = new_connection.child_window(title="SSH version:", control_type="ComboBox")
        if ssh_version_combo.selected_text() != "SSH2":
            ssh_version_combo.expand()
            ssh_version_combo.child_window(title="SSH2", control_type="ListItem").select()

    def keybind_go_back_home(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            self.go_back_home()

    # function that lets user go back to the home screen
    def go_back_home(self):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists() \
                and not self.error_occurred or self.countdown_running:
            return
        response = None
        checkbox = None
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if not self.error_occurred:
            msg = CTkMessagebox(title=translation["go_back_title"], message=translation["go_back"], icon="question",
                                option_1=translation["close_tera_term"], option_2=translation["option_2"],
                                option_3=translation["option_3"], icon_size=(65, 65), button_color=(
                                "#c30101", "#c30101", "#145DA0", "use_default"), option_1_type="checkbox",
                                hover_color=("darkred", "darkred", "use_default"))
            if self.back_checkbox_state == 1:
                msg.check_checkbox()
            response, checkbox = msg.get()
            self.back_checkbox_state = checkbox
        if TeraTermUI.checkIfProcessRunning("ttermpro") and (
                self.error_occurred or (response and (response == "Yes" or response == "Sí") and checkbox)):
            if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                try:
                    self.uprb.kill(soft=True)
                    if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                        TeraTermUI.terminate_process()
                except Exception as err:
                    print("An error occurred: ", err)
                    TeraTermUI.terminate_process()
            elif TeraTermUI.window_exists("Tera Term - [disconnected] VT") or \
                    TeraTermUI.window_exists("Tera Term - [connecting...] VT"):
                TeraTermUI.terminate_process()
        if self.error_occurred or (response and (response == "Yes" or response == "Sí")):
            self.stop_check_idle_thread()
            self.stop_check_process_thread()
            self.unbind("<Up>")
            self.unbind("<Down>")
            self.unbind("<Home>")
            self.unbind("<End>")
            self.unbind("<Control-s>")
            self.unbind("<Control-S>")
            self.unbind("<Control-w>")
            self.unbind("<Control-W>")
            self.unbind("<Control-Tab>")
            self.unbind("<Control-BackSpace>")
            self.bind("<Return>", lambda event: self.login_event_handler())
            self.destroy_tooltip()
            if self.in_auth_frame:
                self.destroy_auth()
            elif self.in_student_frame:
                self.destroy_student()
            elif self.init_class:
                self.tabview.grid_forget()
                self.t_buttons_frame.grid_forget()
                self.multiple_frame.grid_forget()
                self.m_button_frame.grid_forget()
                if self.submit.cget("state") == "disabled" or self.show_classes.cget("state") == "disabled":
                    self.multiple.configure(state="normal")
                    self.submit.configure(state="normal")
                    self.search.configure(state="normal")
                    self.menu_submit.configure(state="normal")
                    self.show_classes.configure(state="normal")
                self.search_function_counter = 0
                self.e_counter = 0
                self.m_counter = 0
                self.classes_status.clear()
            self.slideshow_frame.resume_cycle()
            self.intro_box.reset_autoscroll()
            if not self.intro_box.disabled_autoscroll:
                self.intro_box.restart_autoscroll()
            if not self.home_frame.grid_info():
                self.host_entry.configure(state="normal")
                self.home_frame.grid(row=0, column=1, rowspan=5, columnspan=5, padx=(0, 0), pady=(10, 0))
            if self.help is not None and self.help.winfo_exists():
                self.fix.configure(state="disabled")
                self.files.configure(state="normal")
            self.run_fix = False
            self.went_to_1PL_screen = False
            self.went_to_683_screen = False
            self.in_auth_frame = False
            self.in_student_frame = False
            self.in_enroll_frame = False
            self.in_search_frame = False
            self.skipped_login = False
            self.main_menu = True
            self.add_key_bindings(event=None)
            if self.error_occurred:
                self.destroy_windows()
                if self.server_status != "Maintenance message found" and self.server_status != "Timeout" \
                        and self.tesseract_unzipped:
                    def error():
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"), winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["tera_term_forced_to_close"],
                                      icon="warning", button_width=380)

                    self.after(50, error)
            self.error_occurred = False

    def keybind_go_back_menu(self):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            return

        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            self.go_back_menu()

    # function that goes back to the tabview frame screen
    def go_back_menu(self):
        self.unbind("<Return>")
        self.unbind("<Up>")
        self.unbind("<Down>")
        self.unbind("<Home>")
        self.unbind("<End>")
        self.unbind("<Control-s>")
        self.unbind("<Control-S>")
        self.bind("<Control-Tab>", lambda event: self.on_ctrl_tab_pressed())
        self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_home())
        self.destroy_tooltip()
        if self.in_multiple_screen:
            self.multiple_frame.grid_forget()
            self.m_button_frame.grid_forget()
            self.save_frame.grid_forget()
            self.auto_frame.grid_forget()
        if not self.in_multiple_screen:
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            self.my_classes_frame.grid_forget()
            self.modify_classes_frame.grid_forget()
            self.back_my_classes.grid_forget()
            self.show_classes.configure(text=translation["show_my_classes"])
        self.tabview.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 85))
        self.t_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(0, 0), pady=(0, 20))
        self.back_classes.grid(row=4, column=0, padx=(0, 10), pady=(0, 0), sticky="w")
        self.in_multiple_screen = False
        self.switch_tab()

    def load_language(self, lang):
        # Check if the translations for the requested language are in the cache
        if lang in self.translations_cache:
            # If they are, return the cached translations without loading the file again
            return self.translations_cache[lang]

        # If the translations are not in the cache, identify the filename
        filename = None
        if lang == "English":
            filename = TeraTermUI.get_absolute_path("translations/english.json")
        elif lang == "Español":
            filename = TeraTermUI.get_absolute_path("translations/spanish.json")

        # Load the translations from the file and store them in the cache
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    translations = json.load(f)
                self.translations_cache[lang] = translations
                return translations
            except Exception as err:
                print("An error occurred: ", err)
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
                self.forceful_end_app()

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

        for _, table, _, _, _, _ in self.class_table_pairs:
            table.update_headers(new_headers)
            for i, new_header in enumerate(new_headers):
                tooltip_message = tooltip_messages[new_header]
                header_cell = table.get_cell(0, i)
                if header_cell in self.table_tooltips:
                    self.table_tooltips[header_cell].configure(message=tooltip_message)

    def update_enrolled_classes_headers_tooltips(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        tooltip_messages = {
            translation["course"]: translation["tooltip_course"],
            translation["grade"]: translation["tooltip_grd"],
            translation["days"]: translation["tooltip_days"],
            translation["times"]: translation["tooltip_times"],
            translation["room"]: translation["tooltip_croom"]
        }
        new_headers = [translation["course"], translation["grade"], translation["days"],
                       translation["times"], translation["room"]]
        self.enrolled_classes_table.update_headers(new_headers)
        for i, new_header in enumerate(new_headers):
            tooltip_message = tooltip_messages[new_header]
            header_cell = self.enrolled_classes_table.get_cell(0, i)
            if header_cell in self.enrolled_header_tooltips:
                self.enrolled_header_tooltips[header_cell].configure(message=tooltip_message)

    # function for changing language
    def change_language_event(self, lang):
        if self.curr_lang == lang:
            return

        translation = self.load_language(lang)
        appearance = self.appearance_mode_optionemenu.get()
        self.curr_lang = lang
        self.focus_set()
        new_menu = pystray.Menu(
            pystray.MenuItem(translation["hide_tray"], self.hide_all_windows),
            pystray.MenuItem(translation["show_tray"], self.show_all_windows, default=True),
            pystray.MenuItem(translation["exit_tray"], self.direct_close_on_tray)
        )
        self.tray.menu = new_menu
        self.tray.update_menu()
        self.status_button.configure(text=translation["status_button"])
        self.help_button.configure(text=translation["help_button"])
        self.scaling_label.configure(text=translation["option_label"])
        self.intro_box.configure(state="normal")
        self.intro_box.delete("1.0", "end")
        self.intro_box.insert("0.0", translation["intro_box"])
        self.intro_box.configure(state="disabled")
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
            translation["app_version"] = translation["app_version"].replace("{version}", self.USER_APP_VERSION)
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
                             ["<Tab>", translation["tab"]],
                             ["<Ctrl-Tab>", translation["ctrl_tab"]],
                             ["<Ctrl-Space>", translation["ctrl_space"]],
                             ["<Ctrl-C>", translation["ctrl_c"]],
                             ["<Ctrl-V>", translation["ctrl_v"]],
                             ["<Ctrl-X>", translation["ctrl_x"]],
                             ["<Ctrl-Z>", translation["ctrl_z"]],
                             ["<Ctrl-Y>", translation["ctrl_y"]],
                             ["<Ctrl-A>", translation["ctrl_a"]],
                             ["<Ctrl-S>", translation["ctrl_s"]],
                             ["<Ctrl-W>", translation["ctrl_w"]],
                             ["<Right-Click>", translation["mouse_2"]],
                             ["<Home>", translation["home"]],
                             ["<End>", translation["end"]],
                             ["<F1>", translation["F1"]],
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
        if self.in_auth_frame:
            self.title_login.configure(text=translation["title_auth"])
            self.disclaimer.configure(text=translation["disclaimer"])
            self.username.configure(text=translation["username"])
            if lang == "English":
                self.username.grid(row=3, column=0, padx=(0, 125), pady=(0, 10))
                self.username_entry.grid(row=3, column=0, padx=(90, 0), pady=(0, 10))
            elif lang == "Español":
                self.username.grid(row=3, column=0, padx=(0, 140), pady=(0, 10))
                self.username_entry.grid(row=3, column=0, padx=(60, 0), pady=(0, 10))
            self.back.configure(text=translation["back"])
            self.auth.configure(text=translation["authentication"])
        elif self.in_student_frame:
            self.title_student.configure(text=translation["title_security"])
            self.student_id.configure(text=translation["student_id"])
            self.code.configure(text=translation["code"])
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
            self.show.configure(text=translation["show"])
            self.back_student.configure(text=translation["back"])
            self.system.configure(text=translation["system"])
        if self.init_multiple:
            self.rename_tabs()
            self.update_table_headers_tooltips()
            self.title_enroll.configure(text=translation["title_enroll"])
            self.e_classes.configure(text=translation["class"])
            self.e_section.configure(text=translation["section"])
            if lang == "English":
                self.e_section.grid(row=2, column=1, padx=(0, 199), pady=(20, 0))
            elif lang == "Español":
                self.e_section.grid(row=2, column=1, padx=(0, 202), pady=(20, 0))
            self.e_semester.configure(text=translation["semester"])
            self.e_semester_entry.configure(values=["C31", "C32", "C33", "C41", "C42", "C43", translation["current"]])
            self.register.configure(text=translation["register"])
            self.drop.configure(text=translation["drop"])
            self.update_section_tooltip(lang)
            self.title_search.configure(text=translation["title_search"])
            self.s_classes.configure(text=translation["class"])
            self.s_semester.configure(text=translation["semester"])
            self.s_semester_entry.configure(values=self.semester_values + [translation["current"]])
            self.show_all.configure(text=translation["show_all"])
            if lang == "English":
                self.show_all.grid(row=1, column=1, padx=(85, 0), pady=(2, 0), sticky="n")
            elif lang == "Español":
                self.show_all.grid(row=1, column=1, padx=(85, 0), pady=(0, 0), sticky="n")
            self.explanation_menu.configure(text=translation["explanation_menu"])
            self.title_menu.configure(text=translation["title_menu"])
            self.menu.configure(text=translation["menu"])
            if lang == "English":
                self.menu.grid(row=2, column=1, padx=(0, 184), pady=(10, 0))
            elif lang == "Español":
                self.menu.grid(row=2, column=1, padx=(0, 194), pady=(10, 0))
            self.menu_entry.configure(values=[translation["SRM"], translation["004"], translation["1GP"],
                                              translation["118"], translation["1VE"], translation["3DD"],
                                              translation["409"], translation["683"], translation["1PL"],
                                              translation["4CM"], translation["4SP"], translation["SO"]])
            self.menu_entry.set(translation["SRM"])
            self.menu_semester.configure(text=translation["semester"])
            self.menu_semester_entry.configure(values=self.semester_values + [translation["current"]])
            if self.e_semester_entry.get().upper().replace(" ", "") == "CURRENT" or \
                    self.e_semester_entry.get().upper().replace(" ", "") == "ACTUAL":
                self.e_semester_entry.set(translation["current"])
            if self.s_semester_entry.get().upper().replace(" ", "") == "CURRENT" or \
                    self.s_semester_entry.get().upper().replace(" ", "") == "ACTUAL":
                self.s_semester_entry.set(translation["current"])
            if self.menu_semester_entry.get().upper().replace(" ", "") == "CURRENT" or \
                    self.menu_semester_entry.get().upper().replace(" ", "") == "ACTUAL":
                self.menu_semester_entry.set(translation["current"])
            self.menu_submit.configure(text=translation["submit"])
            self.submit.configure(text=translation["submit"])
            self.search.configure(text=translation["search"])
            if self.enrolled_classes_table is not None and self.my_classes_frame.grid_info():
                self.show_classes.configure(text=translation["show_my_new"])
            else:
                self.show_classes.configure(text=translation["show_my_classes"])
            self.back_classes.configure(text=translation["back"])
            self.multiple.configure(text=translation["multiple"])
            self.title_multiple.configure(text=translation["title_multiple"])
            self.m_class.configure(text=translation["class"])
            self.m_section.configure(text=translation["section"])
            self.m_semester.configure(text=translation["semester"])
            self.m_semester_entry[0].configure(values=self.semester_values + [translation["current"]])
            self.m_choice.configure(text=translation["choice"])
            self.back_multiple.configure(text=translation["back"])
            self.submit_multiple.configure(text=translation["submit"])
            for i in range(8):
                self.m_register_menu[i].configure(values=[translation["register"], translation["drop"]])
                if self.m_section_entry[i].cget("border_color") == "#CC5500":
                    current_message = self.m_tooltips[i].cget("message")
                    conflict_time = current_message.split("*EST. ")[-1].strip()
                    self.m_tooltips[i].configure(message=f"{translation['conflict_tooltip']}{conflict_time}")
                if self.m_register_menu[i].get() == "Choose" or self.m_register_menu[i].get() == "Escoge":
                    self.m_register_menu[i].set(translation["choose"])
                elif self.m_register_menu[i].get() == "Register" or self.m_register_menu[i].get() == "Registra":
                    self.m_register_menu[i].set(translation["register"])
                elif self.m_register_menu[i].get() == "Drop" or self.m_register_menu[i].get() == "Baja":
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
            if self.timer_window is not None and self.timer_window.winfo_exists():
                self.timer_window.title(translation["auto_enroll"])
                self.message_label.configure(text=translation["auto_enroll_activated"])
                self.cancel_button.configure(text=translation["option_1"])
                self.countdown(self.pr_date)
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
                self.download_search_pdf.configure(text=translation["pdf_save_as"])
                table_count = self.table_count.cget("text").split(":")[1].strip()
                self.table_count.configure(text=translation["table_count"] + table_count)
                self.table_count_tooltip.configure(message=translation["table_count_tooltip"])
                self.previous_button_tooltip.configure(message=translation["previous_tooltip"])
                self.next_button_tooltip.configure(message=translation["next_tooltip"])
                self.remove_button_tooltip.configure(message=translation["remove_tooltip"])
                self.download_search_pdf_tooltip.configure(message=translation["download_pdf_search_tooltip"])
                self.sort_by.configure(values=[translation["time_asc"], translation["time_dec"], translation["av_asc"],
                                               translation["av_dec"], translation["original_data"]])
                self.sort_by.set(translation["sort_by"])
                self.sort_by_tooltip.configure(translation["sort_by_tooltip"])
            if self.enrolled_classes_table is not None:
                self.update_enrolled_classes_headers_tooltips()
                title_my_classes = self.title_my_classes.cget("text").split(":")[1].strip()
                self.title_my_classes.configure(text=translation["my_classes"] + title_my_classes)
                total_credits = float(self.total_credits_label.cget("text").split(":")[1].strip())
                self.total_credits_label.configure(text=translation["total_creds"] + str(total_credits) + "0")
                self.submit_my_classes.configure(text=translation["submit"])
                self.submit_my_classes_tooltip.configure(message=translation["submit_modify_tooltip"])
                self.download_enrolled_pdf.configure(text=translation["pdf_save_as"])
                self.download_enrolled_pdf_tooltip.configure(message=translation["download_pdf_enrolled_tooltip"])
                self.back_my_classes.configure(text=translation["back"])
                self.back_my_classes_tooltip.configure(message=translation["back_multiple"])
                self.modify_classes_title.configure(text=translation["mod_classes_title"])
                for option_menu in self.mod_selection_list:
                    if option_menu is not None:
                        option_menu.configure(values=[translation["choose"], translation["drop"],
                                                      translation["section"]])
                        if option_menu.get() == "Choose" or option_menu.get() == "Escoge":
                            option_menu.set(translation["choose"])
                        elif option_menu.get() == "Drop" or option_menu.get() == "Baja":
                            option_menu.set(translation["drop"])
                        elif option_menu.get() == "Section" or option_menu.get() == "Sección":
                            option_menu.set(translation["section"])
                for i in range(0, len(self.enrolled_tooltips), 2):
                    if i < len(self.enrolled_tooltips):
                        self.enrolled_tooltips[i].configure(translation["mod_selection"])
                    if i+1 < len(self.enrolled_tooltips):
                        self.enrolled_tooltips[i+1].configure(translation["change_section_entry"])

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

    def update_section_tooltip(self, new_lang):
        day_translations = {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sábado",
            "Sunday": "Domingo"
        }
        reverse_day_translations = {v: k for k, v in day_translations.items()}
        current_message = self.e_section_tooltip.cget("message")
        if not current_message:
            return
        lines = current_message.split("\n")
        if len(lines) != 2:
            return
        days, time_info = lines
        time_info = time_info.replace("*EST. ", "").strip()
        if new_lang == "Español":
            translated_days = ", ".join(day_translations.get(day, day) for day in days.split(", "))
        else:
            translated_days = ", ".join(reverse_day_translations.get(day, day) for day in days.split(", "))
        self.e_section_tooltip.configure(message=f"{translated_days}\n*EST. {time_info}", visibility=True)

    def change_semester(self, event_type=None):
        if event_type != "focus_out":
            self.focus_set()

        lang = self.language_menu.get()
        translation = self.load_language(lang)
        semester = self.m_semester_entry[0].get().upper().replace(" ", "")
        curr_sem = translation["current"].upper()
        dummy_event = type("Dummy", (object,), {"widget": self.m_semester_entry[0]})()
        self.detect_change(dummy_event)
        if re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE) or semester == curr_sem:
            for i in range(1, self.a_counter + 1):
                self.m_semester_entry[i].configure(state="normal")
                if semester == curr_sem:
                    self.m_semester_entry[i].set(translation["current"])
                else:
                    self.m_semester_entry[i].set(semester)
                self.m_semester_entry[i].configure(state="disabled")

    def section_bind_wrapper(self, event):
        self.detect_change(event)
        self.check_class_conflicts(event)

    @staticmethod
    def generate_schedule():
        days = {
            "Monday, Wednesday": "L",
            "Wednesday": "M",
            "Tuesday, Thursday": "K",
            "Thursday": "J",
            "Friday": "V"
        }
        standard_time_intervals = [
            ("07:00", "08:20", "G"),
            ("08:30", "09:50", "H"),
            ("09:00", "11:20", "I"),
            ("10:00", "11:20", "J"),
            ("11:30", "12:50", "K"),
            ("12:00", "12:50", "L"),
            ("13:00", "14:20", "M"),
            ("14:30", "15:50", "N"),
            ("15:00", "16:20", "O"),
            ("16:00", "17:20", "P"),
            ("17:00", "17:50", "Q"),
            ("18:00", "20:50", "R")
        ]
        special_time_intervals = [
            ("07:00", "09:50", "G"),
            ("08:30", "11:20", "H"),
            ("09:00", "09:50", "I"),
            ("10:30", "12:50", "J"),
            ("12:00", "12:50", "L"),
            ("13:00", "15:50", "M"),
            ("16:00", "18:50", "P"),
            ("17:00", "17:50", "Q"),
            ("18:00", "20:50", "R"),
        ]
        schedule_map = {}

        def overlaps(time_range, block_start, block_end):
            start, end = map(lambda t: int(t.replace(":", "")), time_range)
            block_start, block_end = int(block_start.replace(":", "")), int(block_end.replace(":", ""))
            return not (end <= block_start or start >= block_end)

        for day, prefix in days.items():
            if prefix in ["L", "K"]:
                for start_time, end_time, interval_code in standard_time_intervals:
                    if day in ["Tuesday, Thursday", "Thursday"] and overlaps(
                            (start_time, end_time), "11:30", "12:50"):
                        continue
                    section_code = f"{prefix}{interval_code}"
                    schedule_map[section_code] = (day, start_time, end_time)
            else:
                for start_time, end_time, interval_code in special_time_intervals:
                    if day in ["Tuesday, Thursday", "Thursday"] and overlaps(
                            (start_time, end_time), "11:30", "12:50"):
                        continue
                    section_code = f"{prefix}{interval_code}"
                    schedule_map[section_code] = (day, start_time, end_time)

        return schedule_map

    @staticmethod
    def convert_to_12_hour_format(time_str):
        time_obj = datetime.strptime(time_str, "%H:%M")
        return time_obj.strftime("%I:%M %p").lstrip("0")

    def check_class_time(self):
        lang = self.language_menu.get()
        day_translations = {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sábado",
            "Sunday": "Domingo"
        }
        section = self.e_section_entry.get().upper().replace(" ", "")
        schedule_map = self.schedule_map
        if section[:2] in schedule_map:
            days, start_time, end_time = schedule_map[section[:2]]
            start_time_12hr = TeraTermUI.convert_to_12_hour_format(start_time)
            end_time_12hr = TeraTermUI.convert_to_12_hour_format(end_time)
            if lang == "Español":
                translated_days = ", ".join(day_translations.get(day, day) for day in days.split(", "))
            else:
                translated_days = days
            self.e_section_tooltip.configure(message=f"{translated_days}\n *EST. {start_time_12hr} - {end_time_12hr}",
                                             visibility=True)
        else:
            self.e_section_tooltip.configure(message="", visibility=False)

    def check_class_conflicts(self, event=None):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        schedule_map = self.schedule_map
        sections = [entry.get().upper().replace(" ", "") for entry in self.m_section_entry if entry.get().strip()]
        schedule = []
        conflict_entries = set()
        if not sections:
            return

        for class_section in sections:
            if class_section[:2] in schedule_map:
                days, start_time, end_time = schedule_map[class_section[:2]]
                for day in days.split(", "):
                    schedule.append((day, start_time, end_time, class_section))

        def time_overlaps(start1, end1, start2, end2):
            return max(start1, start2) < min(end1, end2)

        schedule.sort(key=lambda x: (x[0], x[1]))

        for day, day_schedule in groupby(schedule, key=lambda x: x[0]):
            day_schedule = list(day_schedule)
            for i in range(len(day_schedule)):
                current_start, current_end, current_code = day_schedule[i][1:]
                for j in range(i + 1, len(day_schedule)):
                    next_start, next_end, next_code = day_schedule[j][1:]
                    if time_overlaps(current_start, current_end, next_start, next_end):
                        conflict_entries.add((current_code, current_start, current_end))
                        conflict_entries.add((next_code, next_start, next_end))

        for idx, entry in enumerate(self.m_section_entry):
            section = entry.get().upper().replace(" ", "")
            conflict = next((conflict for conflict in conflict_entries if conflict[0] == section), None)
            if conflict:
                conflict_time = (f"{TeraTermUI.convert_to_12_hour_format(conflict[1])} - "
                                 f"{TeraTermUI.convert_to_12_hour_format(conflict[2])}")
                current_message = self.m_tooltips[idx].cget("message")
                new_message = f"{translation['conflict_tooltip']}{conflict_time}"
                if entry.cget("border_color") != "#CC5500":
                    entry.configure(border_color="#CC5500")
                if current_message != new_message:
                    self.m_tooltips[idx].configure(message=new_message, visibility=True, bg_color="#CC5500")
            elif section and section[:2] in schedule_map:
                day, start_time, end_time = schedule_map[section[:2]]
                time_info = (f"{TeraTermUI.convert_to_12_hour_format(start_time)} - "
                             f"{TeraTermUI.convert_to_12_hour_format(end_time)}")
                current_message = self.m_tooltips[idx].cget("message")
                new_message = f"*EST. {time_info}"
                if entry.cget("border_color") == "#CC5500":
                    entry.configure(border_color=customtkinter.ThemeManager.theme["CTkEntry"]["border_color"])
                if current_message != new_message:
                    self.m_tooltips[idx].configure(message=new_message, visibility=True, bg_color="#1E90FF")
            else:
                current_message = self.m_tooltips[idx].cget("message")
                new_message = ""
                if entry.cget("border_color") == "#CC5500":
                    entry.configure(border_color=customtkinter.ThemeManager.theme["CTkEntry"]["border_color"])
                if current_message != new_message:
                    self.m_tooltips[idx].configure(message=new_message, visibility=False, bg_color="#1E90FF")

    def keybind_auto_enroll(self):
        if self.auto_enroll.get() == "on":
            self.auto_enroll.deselect()
            self.countdown_running = False
            self.auto_enroll_bool = False
            self.disable_enable_gui()
            if hasattr(self, "running_countdown") and self.running_countdown \
                    is not None and self.running_countdown.get():
                self.end_countdown()
        elif self.auto_enroll.get() == "off":
            self.auto_enroll.select()
            self.auto_enroll_event_handler()

    def auto_enroll_event_handler(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.focus_set()
        idle = self.cursor.execute("SELECT idle FROM user_data").fetchone()
        if idle[0] != "Disabled":
            if self.auto_enroll.get() == "on":
                msg = CTkMessagebox(title=translation["auto_enroll"], message=translation["auto_enroll_prompt"],
                                    icon=TeraTermUI.get_absolute_path("images/submit.png"),
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"], icon_size=(65, 65),
                                    button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "use_default", "use_default"))
                response = msg.get()
                if response[0] == "Yes" or response[0] == "Sí":
                    task_done = threading.Event()
                    loading_screen = self.show_loading_screen()
                    self.update_loading_screen(loading_screen, task_done)
                    self.thread_pool.submit(self.auto_enroll_event, task_done=task_done)
                else:
                    self.auto_enroll.deselect()
            elif self.auto_enroll.get() == "off":
                self.countdown_running = False
                self.auto_enroll_bool = False
                self.disable_enable_gui()
                if hasattr(self, "running_countdown") and self.running_countdown \
                        is not None and self.running_countdown.get():
                    self.end_countdown()
        else:
            if not self.disable_audio:
                winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"), winsound.SND_ASYNC)
            CTkMessagebox(title=translation["auto_enroll"], icon="cancel", button_width=380,
                          message=translation["auto_enroll_idle"])
            self.auto_enroll.deselect()
            self.auto_enroll.configure(state="disabled")

    # Auto-Enroll classes
    def auto_enroll_event(self, task_done):
        from pytz import timezone

        with self.lock_thread:
            try:
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                semester = self.m_semester_entry[0].get().upper().replace(" ", "")
                self.automation_preparations()
                self.auto_enroll_bool = True
                if asyncio.run(self.test_connection(lang)) and self.check_server() and self.check_format():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        self.wait_for_window()
                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                        self.after(0, self.disable_go_next_buttons)
                        text_output = self.capture_screenshot()
                        if "OPCIONES PARA EL ESTUDIANTE" in text_output or "BALANCE CTA" in text_output or \
                                "PANTALLAS MATRICULA" in text_output or "PANTALLAS GENERALES" in text_output or \
                                "LISTA DE SECCIONES" in text_output:
                            if "LISTA DE SECCIONES" in text_output:
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                self.reset_activity_timer()
                            TeraTermUI.disable_user_input()
                            self.automate_copy_class_data()
                            TeraTermUI.disable_user_input("on")
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
                                self.after(100, self.auto_enroll.deselect)
                                self.auto_enroll_bool = False
                                return
                            active_semesters = TeraTermUI.get_latest_term(copy)
                            date_time_string = re.sub(r"[^a-zA-Z0-9:/ ]", "", date_time_string)
                            date_time_naive = datetime.strptime(date_time_string, "%m/%d/%Y %I:%M %p")
                            puerto_rico_tz = timezone("America/Puerto_Rico")
                            self.pr_date = puerto_rico_tz.localize(date_time_naive, is_dst=None)
                            # Get current datetime
                            current_date = datetime.now(puerto_rico_tz)
                            time_difference = self.pr_date - current_date
                            # Dates
                            is_same_date = (current_date.date() == self.pr_date.date())
                            is_past_date = current_date > self.pr_date
                            is_future_date = current_date < self.pr_date
                            is_next_date = (self.pr_date.date() - current_date.date() == timedelta(days=1))
                            is_time_difference_within_12_hours = \
                                timedelta(hours=12, minutes=55) >= time_difference >= timedelta()
                            is_more_than_one_day = (self.pr_date.date() - current_date.date() > timedelta(days=1))
                            is_current_time_ahead = current_date.time() > self.pr_date.time()
                            is_current_time_24_hours_ahead = time_difference >= timedelta(hours=-24)
                            if active_semesters["percent"] and active_semesters["asterisk"] \
                                    and semester == active_semesters["percent"]:
                                self.after(100, self.show_error_message, 300, 215, translation["date_past"])
                                self.auto_enroll_bool = False
                                self.after(100, self.auto_enroll.deselect)
                                return
                            # Comparing Dates
                            if (is_same_date and is_time_difference_within_12_hours) or \
                                    (is_next_date and is_time_difference_within_12_hours):
                                self.countdown_running = True
                                self.after(0, self.disable_enable_gui)
                                # Create timer window
                                self.after(0, self.create_timer_window)
                                # Create a BooleanVar to control the countdown loop
                                self.running_countdown = customtkinter.BooleanVar()
                                self.running_countdown.set(True)
                                # Start the countdown
                                self.after(100, self.countdown, self.pr_date)
                            elif is_past_date or (is_same_date and is_current_time_ahead):
                                if is_current_time_24_hours_ahead:
                                    self.running_countdown = customtkinter.BooleanVar()
                                    self.running_countdown.set(True)
                                    self.started_auto_enroll = True
                                    self.after(150, self.submit_multiple_event_handler)
                                else:
                                    self.after(100, self.show_error_message, 300, 215,
                                               translation["date_past"])
                                    self.auto_enroll_bool = False
                                    self.after(100, self.auto_enroll.deselect)
                            elif (is_future_date or is_more_than_one_day) or \
                                    (is_same_date and not is_time_difference_within_12_hours) or \
                                    (is_next_date and not is_time_difference_within_12_hours):
                                self.after(100, self.show_error_message, 320, 235,
                                           translation["date_not_within_12_hours"])
                                self.auto_enroll_bool = False
                                self.after(100, self.auto_enroll.deselect)
                            if ("INVALID ACTION" in text_output and "PANTALLAS MATRICULA" in text_output) or \
                                    ("LISTA DE SECCIONES" in text_output and "COURSE NOT" in text_output):
                                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                self.reset_activity_timer()
                                self.after(0, self.bring_back_timer_window)
                        else:
                            self.after(100, self.show_error_message, 300, 215,
                                       translation["failed_to_find_date"])
                            self.after(100, self.auto_enroll.deselect)
                            self.auto_enroll_bool = False
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
                        self.auto_enroll_bool = False
                        self.after(100, self.auto_enroll.deselect)
            except Exception as err:
                print("An error occurred: ", err)
                self.error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                               winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.auto_enroll.deselect()
                        self.error_occurred = False

                    self.after(50, error_automation)
                self.after(350, self.bind, "<Return>", lambda event: self.submit_multiple_event_handler())
                TeraTermUI.disable_user_input()

    # Starts the countdown on when the auto-enroll process will occur
    def countdown(self, pr_date):
        from pytz import timezone

        lang = self.language_menu.get()
        translation = self.load_language(lang)
        puerto_rico_tz = timezone("America/Puerto_Rico")
        current_date = datetime.now(puerto_rico_tz)
        time_difference = pr_date - current_date
        total_seconds = time_difference.total_seconds()
        if self.running_countdown.get():
            if not TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                self.forceful_end_countdown()
            if total_seconds <= 0:
                # Enrollment function
                self.timer_label.configure(text=translation["performing_auto_enroll"], text_color="#32CD32",
                                           font=customtkinter.CTkFont(size=17))
                self.timer_label.pack(pady=30)
                self.cancel_button.pack_forget()
                if self.state() == "withdrawn":
                    if self.timer_window.state() == "withdrawn":
                        self.timer_window.iconify()
                    self.iconify()
                    hwnd = win32gui.FindWindow(None, "uprbay.uprb.edu - Tera Term VT")
                    if hwnd and not win32gui.IsWindowVisible(hwnd):
                        win32gui.ShowWindow(hwnd, SW_SHOW)
                        win32gui.ShowWindow(hwnd, SW_RESTORE)
                    app = gw.getWindowsWithTitle("Tera Term UI")[0]
                    app.restore()
                    timer = gw.getWindowsWithTitle(translation["auto_enroll"])[0]
                    timer.restore()
                self.timer_window.lift()
                self.timer_window.focus_force()
                self.timer_window.attributes("-topmost", 1)
                self.started_auto_enroll = True
                self.after(3000, self.submit_multiple_event_handler)
                if TeraTermUI.window_exists(translation["dialog_title"]):
                    self.after(2500, self.dialog.destroy)
                if TeraTermUI.window_exists(translation["save_pdf"]):
                    def close_file_dialog():
                        file_dialog_hwnd = win32gui.FindWindow("#32770", translation["save_pdf"])
                        win32gui.PostMessage(file_dialog_hwnd, WM_CLOSE, 0, 0)
                    self.after(2500, close_file_dialog)
                titles_to_close = [
                    translation["exit"],
                    translation["submit"],
                    translation["success_title"],
                    translation["error"],
                    translation["fix_messagebox_title"],
                    translation["update_popup_title"],
                    translation["so_title"],
                    translation["automation_error_title"]
                ]
                self.after(2500, TeraTermUI.close_matching_windows, titles_to_close)
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
                        self.timer_window.after(
                            seconds_until_next_minute * 1000, lambda: self.countdown(pr_date)
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
                        self.timer_window.after(
                            seconds_until_next_minute * 1000, lambda: self.countdown(pr_date)
                            if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT")
                            else self.forceful_end_countdown())
                    else:  # update every second if there's less than or equal to 60 seconds left
                        if not self.notification_sent:
                            self.tray.notify(translation["notif_countdown"].replace(
                                "{semester}", self.m_semester_entry[0].get()), title="Tera Term UI")
                            self.notification_sent = True
                        self.timer_window.after(
                            1000, lambda: self.countdown(pr_date)
                            if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT")
                            else self.forceful_end_countdown())

    def end_countdown(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.pr_date = None
        self.auto_enroll_bool = False
        self.countdown_running = False
        self.notification_sent = False
        self.running_countdown.set(False)
        if self.timer_window and self.timer_window.winfo_exists():
            if any(i.text == translation["countdown_win"] for i in self.tray.menu.items):
                updated_menu_items = [i for i in self.tray.menu.items if i.text != translation["countdown_win"]]
                self.tray.menu = pystray.Menu(*updated_menu_items)
                self.tray.update_menu()
            self.timer_window.destroy()
        self.disable_enable_gui()
        self.auto_enroll.deselect()

    def forceful_end_countdown(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.end_countdown()
        if not self.disable_audio:
            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"), winsound.SND_ASYNC)
        CTkMessagebox(title=translation["automation_error_title"], icon="info", message=translation["end_countdown"],
                      button_width=380)

    def create_timer_window(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        timer_window_width = 335
        timer_window_height = 160
        center_x = main_window_x + (main_window_width // 2) - (timer_window_width // 2)
        center_y = main_window_y + (main_window_height // 2) - (timer_window_height // 2)
        self.timer_window = SmoothFadeToplevel(fade_duration=15)
        self.timer_window.geometry(f"{timer_window_width}x{timer_window_height}+{center_x + 70}+{center_y - 15}")
        self.timer_window.title(translation["auto_enroll"])
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
        self.cancel_button.pack(pady=25)
        new_menu = pystray.Menu(
            pystray.MenuItem(translation["hide_tray"], self.hide_all_windows),
            pystray.MenuItem(translation["show_tray"], self.show_all_windows, default=True),
            pystray.MenuItem(translation["exit_tray"], self.direct_close_on_tray),
            pystray.MenuItem(translation["countdown_win"], self.bring_back_timer_window)
        )
        self.tray.menu = new_menu
        self.tray.update_menu()
        self.timer_window.bind("<Escape>", lambda event: self.end_countdown())
        self.timer_window.protocol("WM_DELETE_WINDOW", self.end_countdown)

    def bring_back_timer_window(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.timer_window is not None and self.timer_window.winfo_exists():
            if self.timer_window.state() == "withdrawn":
                self.timer_window.iconify()
                timer = gw.getWindowsWithTitle(translation["auto_enroll"])[0]
                self.after(200, timer.restore)
                return
            timer = gw.getWindowsWithTitle(translation["auto_enroll"])[0]
            if timer.isMinimized:
                timer.restore()
            try:
                timer.activate()
            except:
                pass
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
            self.auto_enroll.configure(state="normal")
            self.save_data.configure(state="normal")
            if self.enrolled_classes_table is not None:
                self.submit_my_classes.configure(state="disabled")
        else:
            self.submit_multiple.configure(state="normal")
            self.submit.configure(state="normal")
            self.back_classes.configure(state="normal")
            if self.a_counter > 0:
                self.m_remove.configure(state="normal")
            if self.a_counter < 7:
                self.m_add.configure(state="normal")
            for i in range(8):
                self.m_classes_entry[i].configure(state="normal")
                self.m_section_entry[i].configure(state="normal")
                self.m_register_menu[i].configure(state="normal")
            self.m_semester_entry[0].configure(state="normal")
            if self.enrolled_classes_table is not None:
                self.submit_my_classes.configure(state="normal")

    def move_window(self):
        try:
            window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
        except IndexError:
            print("Window not found.")
            return
        # Get Tkinter window's current position
        tk_x = self.winfo_x()
        tk_y = self.winfo_y()
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
                                     text=translation["back"], hover_color=("#BEBEBE", "#4E4F50"),
                                     text_color=("gray10", "#DCE4EE"), command=self.go_back_home)
            self.back_tooltip = CTkToolTip(self.back, message=translation["back_tooltip"], bg_color="#989898",
                                           alpha=0.90)
            self.username_entry.lang = lang
            self.authentication_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.a_buttons_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.title_login.bind("<Button-1>", lambda event: self.focus_set())
            self.disclaimer.bind("<Button-1>", lambda event: self.focus_set())
            self.username.bind("<Button-1>", lambda event: self.focus_set())
            self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_home())

    def destroy_auth(self):
        if self.init_auth:
            self.init_auth = False
            self.authentication_frame.grid_forget()
            self.a_buttons_frame.grid_forget()
            self.authentication_frame.unbind("<Button-1>")
            self.a_buttons_frame.unbind("<Button-1>")
            self.title_login.unbind("<Button-1>")
            self.disclaimer.unbind("<Button-1>")
            self.username.unbind("<Button-1>")

            def destroy():
                self.title_login.destroy()
                self.title_login = None
                self.uprb_image = None
                self.uprb_image_grid.configure(command=None)
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
                self.auth.configure(command=None)
                self.auth.destroy()
                self.auth = None
                self.back.configure(command=None)
                self.back.destroy()
                self.back = None
                self.back_tooltip.destroy()
                self.back_tooltip = None
                self.authentication_frame.destroy()
                self.authentication_frame = None
                self.a_buttons_frame.destroy()
                self.a_buttons_frame = None

            self.after(100, destroy)

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
            self.show.bind("<space>", lambda event: self.spacebar_event())
            self.student_id_entry.bind("<Command-c>", lambda event: "break")
            self.student_id_entry.bind("<Control-c>", lambda event: "break")
            self.code_entry.bind("<Command-c>", lambda event: "break")
            self.code_entry.bind("<Control-c>", lambda event: "break")
            self.student_id_entry.bind("<Command-C>", lambda event: "break")
            self.student_id_entry.bind("<Control-C>", lambda event: "break")
            self.code_entry.bind("<Command-C>", lambda event: "break")
            self.code_entry.bind("<Control-C>", lambda event: "break")
            self.system = CustomButton(master=self.s_buttons_frame, border_width=2, text=translation["system"],
                                       text_color=("gray10", "#DCE4EE"), command=self.student_event_handler)
            self.back_student = CustomButton(master=self.s_buttons_frame, fg_color="transparent", border_width=2,
                                             text=translation["back"], hover_color=("#BEBEBE", "#4E4F50"),
                                             text_color=("gray10", "#DCE4EE"), command=self.go_back_home)
            self.back_student_tooltip = CTkToolTip(self.back_student, message=translation["back_tooltip"],
                                                   bg_color="#989898", alpha=0.90)
            self.student_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.s_buttons_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.title_student.bind("<Button-1>", lambda event: self.focus_set())
            self.student_id.bind("<Button-1>", lambda event: self.focus_set())
            self.code.bind("<Button-1>", lambda event: self.focus_set())
            for entry in [self.student_id_entry, self.code_entry]:
                entry.lang = lang

    def destroy_student(self):
        if self.init_student:
            self.init_student = False
            self.student_frame.grid_forget()
            self.s_buttons_frame.grid_forget()
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
            self.student_id.unbind("<Button-1>")
            self.code.unbind("<Button-1>")
            self.show.unbind("<space>")

            def destroy():
                self.title_student.destroy()
                self.title_student = None
                self.lock = None
                self.lock_grid.configure(command=None)
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
                self.show.configure(command=None)
                self.show.destroy()
                self.show = None
                self.system.configure(command=None)
                self.system.destroy()
                self.system = None
                self.back_student.configure(command=None)
                self.back_student.destroy()
                self.back_student = None
                self.back_student_tooltip.destroy()
                self.back_student_tooltip = None
                self.student_frame.destroy()
                self.student_frame = None
                self.s_buttons_frame.destroy()
                self.s_buttons_frame = None

            self.after(100, destroy)

    def initialization_class(self):
        # Classes
        if not self.init_class:
            lang = self.language_menu.get()
            translation = self.load_language(lang)
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
            self.e_section_tooltip = CTkToolTip(self.e_section_entry, message="", bg_color="#1E90FF", visibility=False)
            self.e_semester = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab),
                                                     text=translation["semester"])
            self.e_semester_entry = CustomComboBox(self.tabview.tab(self.enroll_tab), self,
                                                   values=self.semester_values + [translation["current"]],
                                                   command=lambda value: self.focus_set())
            self.e_semester_entry.set(self.DEFAULT_SEMESTER)
            self.radio_var = tk.StringVar()
            self.register = customtkinter.CTkRadioButton(master=self.tabview.tab(self.enroll_tab),
                                                         text=translation["register"], value="register",
                                                         variable=self.radio_var, command=self.focus_set)
            self.register_tooltip = CTkToolTip(self.register, message=translation["register_tooltip"])
            self.drop = customtkinter.CTkRadioButton(master=self.tabview.tab(self.enroll_tab), text=translation["drop"],
                                                     value="drop", variable=self.radio_var, canvas_takefocus=False,
                                                     command=self.focus_set)
            self.drop_tooltip = CTkToolTip(self.drop, message=translation["drop_tooltip"])
            self.register.select()
            self.tabview.tab(self.enroll_tab).bind("<Button-1>", lambda event: self.focus_set())
            self.title_enroll.bind("<Button-1>", lambda event: self.focus_set())
            self.e_classes.bind("<Button-1>", lambda event: self.focus_set())
            self.e_section.bind("<Button-1>", lambda event: self.focus_set())
            self.e_section_entry.bind("<FocusOut>", lambda event: self.check_class_time())
            self.e_semester.bind("<Button-1>", lambda event: self.focus_set())
            self.register.bind("<space>", lambda event: self.spacebar_event())
            self.register.bind("<FocusOut>", lambda event: self.drop._on_leave())

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
                                                   values=self.semester_values + [translation["current"]],
                                                   command=lambda value: self.focus_set(), width=80)
            self.s_semester_entry.set(self.DEFAULT_SEMESTER)
            self.show_all = customtkinter.CTkCheckBox(self.search_scrollbar, text=translation["show_all"],
                                                      onvalue="on", offvalue="off", command=self.focus_set)
            self.show_all_tooltip = CTkToolTip(self.show_all, message=translation["show_all_tooltip"],
                                               bg_color="#1E90FF")
            self.search_next_page = CustomButton(master=self.search_scrollbar, fg_color="transparent", border_width=2,
                                                 text=translation["search_next_page"], text_color=("gray10", "#DCE4EE"),
                                                 hover_color=("#BEBEBE", "#4E4F50"),
                                                 command=self.go_next_search_handler, width=85)
            self.search_next_page_tooltip = CTkToolTip(self.search_next_page,
                                                       message=translation["search_next_page_tooltip"],
                                                       bg_color="#989898", alpha=0.90)
            self.tabview.tab(self.search_tab).bind("<Button-1>", lambda event: self.focus_set())
            self.search_scrollbar.bind("<Button-1>", lambda event: self.focus_set())
            self.title_search.bind("<Button-1>", lambda event: self.focus_set())
            self.s_classes.bind("<Button-1>", lambda event: self.focus_set())
            self.s_semester.bind("<Button-1>", lambda event: self.focus_set())
            self.s_classes_entry.bind("<FocusIn>", lambda event:
                                      self.search_scrollbar.scroll_to_widget(self.s_classes_entry))
            self.show_all.bind("<space>", lambda event: self.spacebar_event())

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
                                             command=lambda value: self.focus_set(), width=141)
            self.menu_entry.set(translation["SRM"])
            self.menu_semester = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
                                                        text=translation["semester"])
            self.menu_semester_entry = CustomComboBox(self.tabview.tab(self.other_tab), self,
                                                      values=self.semester_values + [translation["current"]],
                                                      command=lambda value: self.focus_set(), width=141)
            self.menu_semester_entry.set(self.DEFAULT_SEMESTER)
            self.menu_submit = CustomButton(master=self.tabview.tab(self.other_tab), border_width=2,
                                            text=translation["submit"], text_color=("gray10", "#DCE4EE"),
                                            command=self.option_menu_event_handler, width=141)
            self.go_next_1VE = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text=translation["go_next"],
                                            text_color=("gray10", "#DCE4EE"), hover_color=("#BEBEBE", "#4E4F50"),
                                            command=self.go_next_page_handler, width=100)
            self.go_next_1GP = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text=translation["go_next"],
                                            text_color=("gray10", "#DCE4EE"), hover_color=("#BEBEBE", "#4E4F50"),
                                            command=self.go_next_page_handler, width=100)
            self.go_next_409 = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text=translation["go_next"],
                                            text_color=("gray10", "#DCE4EE"), hover_color=("#BEBEBE", "#4E4F50"),
                                            command=self.go_next_page_handler, width=100)
            self.go_next_683 = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text=translation["go_next"],
                                            text_color=("gray10", "#DCE4EE"), hover_color=("#BEBEBE", "#4E4F50"),
                                            command=self.go_next_page_handler, width=100)
            self.go_next_4CM = CustomButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                            border_width=2, text=translation["go_next"],
                                            text_color=("gray10", "#DCE4EE"), hover_color=("#BEBEBE", "#4E4F50"),
                                            command=self.go_next_page_handler, width=100)
            self.tabview.tab(self.other_tab).bind("<Button-1>", lambda event: self.focus_set())
            self.title_menu.bind("<Button-1>", lambda event: self.focus_set())
            self.explanation_menu.bind("<Button-1>", lambda event: self.focus_set())
            self.menu.bind("<Button-1>", lambda event: self.focus_set())
            self.menu_semester.bind("<Button-1>", lambda event: self.focus_set())

            # Bottom Buttons
            self.back_classes = CustomButton(master=self.t_buttons_frame, fg_color="transparent", border_width=2,
                                             text=translation["back"], hover_color=("#BEBEBE", "#4E4F50"),
                                             text_color=("gray10", "#DCE4EE"), command=self.go_back_home)
            self.back_classes_tooltip = CTkToolTip(self.back_classes, alpha=0.90, message=translation["back_tooltip"],
                                                   bg_color="#989898")
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
                                         text=translation["multiple"], hover_color=("#BEBEBE", "#4E4F50"),
                                         text_color=("gray10", "#DCE4EE"), command=self.multiple_classes_event)
            self.multiple_tooltip = CTkToolTip(self.multiple, message=translation["multiple_tooltip"],
                                               bg_color="#0F52BA")
            self.t_buttons_frame.bind("<Button-1>", lambda event: self.focus_set())
            for entry in [self.e_classes_entry, self.e_section_entry, self.s_classes_entry]:
                entry.lang = lang
        else:
            self.go_next_1VE.grid_forget()
            self.go_next_1GP.grid_forget()
            self.go_next_409.grid_forget()
            self.go_next_683.grid_forget()
            self.go_next_4CM.grid_forget()
            self.menu_submit.configure(width=140)
            self.menu_submit.grid(row=5, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
            self.search_next_page.grid_forget()
            self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
            self.search.configure(width=140)
            self.search_next_page_status = False
            self._1VE_screen = False
            self._1GP_screen = False
            self._409_screen = False
            self._683_screen = False
            self._4CM_screen = False

    def initialization_multiple(self):
        # Multiple Classes Enrollment
        if not self.init_multiple:
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            self.init_multiple = True
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
            for i in range(8):
                self.m_num_class.append(customtkinter.CTkLabel(master=self.multiple_frame, text=f"{i + 1}.", height=26))
                self.m_classes_entry.append(CustomEntry(self.multiple_frame, self, lang,
                                                        placeholder_text=self.placeholder_texts_classes[i], height=26))
                self.m_section_entry.append(CustomEntry(self.multiple_frame, self, lang,
                                                        placeholder_text=self.placeholder_texts_sections[i], height=26))
                self.m_tooltips.append(CTkToolTip(self.m_section_entry[i], message="", bg_color="#1E90FF",
                                                  visibility=False))
                self.m_section_entry[i].bind("<FocusOut>", self.section_bind_wrapper)
                self.m_semester_entry.append(CustomComboBox(self.multiple_frame, self,
                                                            values=self.semester_values + [translation["current"]],
                                                            command=self.change_semester, height=26))
                self.m_semester_entry[i].set(self.DEFAULT_SEMESTER)
                self.m_register_menu.append(customtkinter.CTkOptionMenu(
                    master=self.multiple_frame, values=[translation["register"], translation["drop"]],
                    command=lambda value: self.focus_set(), height=26))
                self.m_register_menu[i].set(translation["choose"])
                self.m_num_class[i].bind("<Button-1>", lambda event: self.focus_set())
            self.m_semester_entry[0].bind(
                "<FocusOut>", lambda event: self.change_semester(event_type="focus_out"))
            self.m_add = CustomButton(master=self.m_button_frame, border_width=2, text="+",
                                      text_color=("gray10", "#DCE4EE"), command=self.add_event, height=38, width=50,
                                      fg_color="#0F52BA")
            self.m_add_tooltip = CTkToolTip(self.m_add, message=translation["add_tooltip"], bg_color="#0F52BA")
            self.m_remove = CustomButton(master=self.m_button_frame, border_width=2, text="-",
                                         text_color=("gray10", "#DCE4EE"), command=self.remove_event, height=38,
                                         width=50, fg_color="#DC143C", hover_color="darkred",
                                         state="disabled")
            self.m_remove_tooltip = CTkToolTip(self.m_remove, message=translation["m_remove_tooltip"],
                                               bg_color="#DC143C")
            self.back_multiple = CustomButton(master=self.m_button_frame, fg_color="transparent", border_width=2,
                                              text=translation["back"], height=40, width=70,
                                              hover_color=("#BEBEBE", "#4E4F50"), text_color=("gray10", "#DCE4EE"),
                                              command=self.go_back_menu)
            self.back_multiple_tooltip = CTkToolTip(self.back_multiple, alpha=0.90,
                                                    message=translation["back_multiple"], bg_color="#989898")
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
            self.save_data.bind("<space>", self.keybind_save_classes)
            self.auto_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.auto_enroll.bind("<space>", lambda event: self.keybind_auto_enroll())
            self.title_multiple.bind("<Button-1>", lambda event: self.focus_set())
            self.m_class.bind("<Button-1>", lambda event: self.focus_set())
            self.m_section.bind("<Button-1>", lambda event: self.focus_set())
            self.m_semester.bind("<Button-1>", lambda event: self.focus_set())
            self.m_choice.bind("<Button-1>", lambda event: self.focus_set())
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
            "win_pos_x": self.winfo_x() if not self.state() == "zoomed" else None,
            "win_pos_y": self.winfo_y() if not self.state() == "zoomed" else None,
            "exit": self.exit_checkbox_state,
        }
        for field, value in field_values.items():
            # Skip 'exit' field if include_exit is False
            if field == "exit" and not include_exit:
                continue
            if value is None:
                continue
            # Save 'host' no matter the result as 'uprbay.uprb.edu'
            if field == "host":
                host_entry_value = self.host_entry.get().replace(" ", "").lower()
                if host_entry_value not in ["uprbay.uprb.edu", "uprbayuprbedu", "uprb"]:
                    continue
            result = self.cursor.execute(f"SELECT {field} FROM user_data").fetchone()
            if result is None:
                self.cursor.execute(f"INSERT INTO user_data ({field}) VALUES (?)", (value,))
            elif result[0] != value:
                self.cursor.execute(f"UPDATE user_data SET {field} = ? ", (value,))
        with closing(sqlite3.connect(TeraTermUI.get_absolute_path("database.db"))) as connection:
            with closing(connection.cursor()) as self.cursor:
                self.connection.commit()

    def keybind_save_classes(self, event=None):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            return

        self.save_data.toggle()
        self.save_classes()
        if event and event.keysym == "space":
            self.save_data._on_enter()

    # saves class information for another session
    def save_classes(self):
        save = self.save_data.get()
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if save == "on":
            self.cursor.execute("DELETE FROM saved_classes")
            self.connection.commit()
            is_empty = False
            is_invalid_format = False
            for index in range(self.a_counter + 1):
                class_value = self.m_classes_entry[index].get().upper().replace(" ", "").replace("-", "")
                section_value = self.m_section_entry[index].get().upper().replace(" ", "").replace("-", "")
                semester_value = self.m_semester_entry[index].get().replace(" ", "").lower()
                curr_sem = translation["current"].replace(" ", "").lower()
                if semester_value == curr_sem:
                    semester_value = translation["current"]
                else:
                    semester_value = semester_value.upper()
                    valid_semester_format = re.fullmatch("^[A-Z][0-9]{2}$", semester_value, flags=re.IGNORECASE)
                    if not valid_semester_format:
                        semester_value = None
                register_value = self.m_register_menu[index].get()
                if not class_value or not section_value or not semester_value or register_value in ("Choose", "Escoge"):
                    is_empty = True
                elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", class_value, flags=re.IGNORECASE) or not re.fullmatch(
                        "^[A-Z]{2}[A-Z0-9]$", section_value, flags=re.IGNORECASE):
                    is_invalid_format = True
                else:
                    self.cursor.execute("INSERT INTO saved_classes (class, section, semester, action)"
                                        " VALUES (?, ?, ?, ?)",
                                        (class_value, section_value, semester_value, register_value))
                    self.connection.commit()

            if is_empty:
                self.show_error_message(330, 255, translation["failed_saved_lack_info"])
                self.save_data.deselect()
            elif is_invalid_format:
                self.show_error_message(330, 255, translation["failed_saved_invalid_info"])
                self.save_data.deselect()
            else:
                self.cursor.execute("SELECT COUNT(*) FROM saved_classes")
                row_count = self.cursor.fetchone()[0]
                if row_count == 0:
                    self.show_error_message(330, 255, translation["failed_saved_invalid_info"])
                    self.save_data.deselect()
                else:
                    self.changed_classes = set()
                    self.changed_sections = set()
                    self.changed_semesters = set()
                    self.changed_registers = set()
                    for i in range(8):
                        self.m_register_menu[i].configure(
                            command=lambda value, idx=i: self.detect_register_menu_change(value, idx))
                        self.m_classes_entry[i].bind("<FocusOut>", self.detect_change)
                        self.m_section_entry[i].bind("<FocusOut>", self.section_bind_wrapper)
                    self.show_success_message(350, 265, translation["saved_classes_success"])
        if save == "off":
            self.cursor.execute("DELETE FROM saved_classes")
            self.connection.commit()
            for i in range(8):
                self.m_register_menu[i].configure(command=lambda value: self.focus_set())
                self.m_classes_entry[i].unbind("<FocusOut>")
                self.m_section_entry[i].unbind("<FocusOut>")

    # shows the important information window
    def show_loading_screen(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.loading_screen is None or not self.loading_screen.winfo_exists():
            self.loading_screen = SmoothFadeToplevel(fade_duration=10, final_alpha=0.90)
            self.loading_screen_geometry()
            self.loading_screen.wm_overrideredirect(True)
            self.loading_screen.attributes("-topmost", True)
            self.loading_screen.iconbitmap(self.icon_path)
            self.loading_label = customtkinter.CTkLabel(self.loading_screen, text=translation["loading"],
                                                        font=customtkinter.CTkFont(size=20, weight="bold"))
            self.loading_label.pack(pady=(48, 12))
            self.progress_bar = customtkinter.CTkProgressBar(self.loading_screen, mode="indeterminate",
                                                             height=15, width=230, indeterminate_speed=1.5)
            self.progress_bar.pack(pady=1)
            self.loading_screen.protocol("WM_DELETE_WINDOW", TeraTermUI.disable_loading_screen_close)
        else:
            self.loading_screen_geometry()
            self.loading_screen.deiconify()
        self.loading_screen_status = self.loading_screen
        if self.auto_search or self.updating_app:
            self.loading_label.configure(text=translation["searching_exe"])
            self.auto_search = False
            self.updating_app = False
        elif self.sending_feedback:
            self.loading_label.configure(text=translation["sending_feedback"])
            self.sending_feedback = False
        else:
            self.loading_label.configure(text=translation["loading"])
        self.progress_bar.start()
        self.attributes("-disabled", True)
        self.disable_widgets(self)
        self.loading_screen_start_time = time.time()
        return self.loading_screen

    def loading_screen_geometry(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.loading_screen.title(translation["loading"])
        width = 275
        height = 150
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        loading_screen_width = width
        loading_screen_height = height
        center_x = main_window_x + (main_window_width // 2) - (loading_screen_width // 2)
        center_y = main_window_y + (main_window_height // 2) - (loading_screen_height // 2)
        self.loading_screen.geometry(f"{width}x{height}+{center_x + 105}+{center_y}")

    @staticmethod
    def disable_loading_screen_close():
        return "break"

    # tells the loading screen when it should stop and close
    def update_loading_screen(self, loading_screen, task_done):
        current_time = time.time()
        if task_done.is_set() or current_time - self.loading_screen_start_time > 60:
            self.attributes("-disabled", False)
            self.update_widgets()
            if self.loading_screen is not None and self.loading_screen.winfo_exists():
                self.loading_screen.withdraw()
            self.progress_bar.reset()
            self.loading_screen_status = None
            if current_time - self.loading_screen_start_time > 60:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.timeout_occurred = True
                if not self.disable_audio:
                    winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"), winsound.SND_ASYNC)
                CTkMessagebox(title=translation["automation_error_title"], message=translation["timeout_error"],
                              icon="warning", button_width=380)
                self.timeout_occurred = False
        else:
            self.after(100, self.update_loading_screen, loading_screen, task_done)

    def disable_widgets(self, container):
        stack = [container]
        while stack:
            current_container = stack.pop()
            for widget in current_container.winfo_children():
                if not widget.winfo_viewable() or widget in [self.language_menu, self.appearance_mode_optionemenu,
                                                             self.curriculum, self.search_box, self.skip_auth_switch,
                                                             self.disable_audio_val, self.disable_idle]:
                    continue

                widget_types = (tk.Entry, customtkinter.CTkCheckBox, customtkinter.CTkRadioButton,
                                customtkinter.CTkSwitch, customtkinter.CTkOptionMenu)
                if isinstance(widget, widget_types) and widget.cget("state") != "disabled":
                    widget.configure(state="disabled")
                elif hasattr(widget, "winfo_children"):
                    stack.append(widget)

    def enable_widgets(self, container):
        stack = [container]
        while stack:
            current_container = stack.pop()
            for widget in current_container.winfo_children():
                if not widget.winfo_viewable() or widget in [self.language_menu, self.appearance_mode_optionemenu,
                                                             self.curriculum, self.search_box, self.skip_auth_switch,
                                                             self.disable_audio_val, self.disable_idle]:
                    continue

                widget_types = (tk.Entry, customtkinter.CTkCheckBox, customtkinter.CTkRadioButton,
                                customtkinter.CTkSwitch, customtkinter.CTkOptionMenu)
                if isinstance(widget, widget_types) and widget.cget("state") != "normal":
                    widget.configure(state="normal")
                elif hasattr(widget, "winfo_children"):
                    stack.append(widget)

    def update_widgets(self):
        if self.countdown_running and self.in_multiple_screen:
            return

        self.enable_widgets(self)
        if self.enrolled_classes_table is not None:
            lang = self.language_menu.get()
            translation = self.load_language(lang)
            for row_index in range(min(len(self.mod_selection_list), len(self.enrolled_classes_data))):
                mod_selection = self.mod_selection_list[row_index]
                change_section_entry = self.change_section_entries[row_index]
                if mod_selection is not None and change_section_entry is not None:
                    mod = mod_selection.get()
                    if mod == translation["section"]:
                        change_section_entry.configure(state="normal")
                    else:
                        change_section_entry.configure(state="disabled")
        if self.init_multiple:
            for i in range(1, self.a_counter + 1):
                self.m_semester_entry[i].configure(state="disabled")

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
            self.student_id_entry.bind("<Command-c>", lambda event: "break")
            self.student_id_entry.bind("<Control-c>", lambda event: "break")
            self.code_entry.bind("<Command-c>", lambda event: "break")
            self.code_entry.bind("<Control-c>", lambda event: "break")
            self.student_id_entry.bind("<Command-C>", lambda event: "break")
            self.student_id_entry.bind("<Control-C>", lambda event: "break")
            self.code_entry.bind("<Command-C>", lambda event: "break")
            self.code_entry.bind("<Control-C>", lambda event: "break")
            self.student_id_entry.configure(show="*")
            self.code_entry.configure(show="*")

    # function that checks if the specified program is running or not
    @staticmethod
    def checkIfProcessRunning(processName):
        process = processName.lower()
        try:
            for proc in psutil.process_iter(attrs=["name"]):
                proc_info = proc.as_dict(attrs=["name"])
                proc_name = proc_info.get("name", "").lower()
                if process in proc_name:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
            print(f"Exception occurred: {err}")
        return False

    # function to check if multiple of the specified processes are running or not
    @staticmethod
    def checkMultipleProcessesRunning(*processNames):
        running_processes = []
        for processName in processNames:
            process = processName.lower()
            try:
                for proc in psutil.process_iter(attrs=["name"]):
                    proc_info = proc.as_dict(attrs=["name"])
                    proc_name = proc_info.get("name", "").lower()
                    if process in proc_name:
                        running_processes.append(processName)
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
                print(f"Exception occurred: {err}")
        return running_processes

    # function that checks if there's more than 1 instance of Tera Term running
    @staticmethod
    def countRunningProcesses(processName):
        count = 0
        process = processName.lower()
        try:
            for proc in psutil.process_iter(attrs=["name"]):
                proc_info = proc.as_dict(attrs=["name"])
                proc_name = proc_info.get("name", "").lower()
                if process in proc_name:
                    count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
            print(f"Exception occurred: {err}")
        return count, (count > 1)

    # checks if the specified window exists
    @staticmethod
    def window_exists(title):
        hwnd = win32gui.FindWindow(None, title)
        if hwnd == 0:
            return False
        return True

    @staticmethod
    def close_matching_windows(titles_to_close):

        def window_enum_handler(hwnd, titles):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) in titles:
                win32gui.SendMessage(hwnd, WM_CLOSE, 0, 0)

        win32gui.EnumWindows(window_enum_handler, titles_to_close)

    @staticmethod
    def check_window_exists(window_title, retries=5, delay=1):
        for _ in range(retries):
            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                return True
            time.sleep(delay)
        raise Exception(f"The window with title '{window_title}' was not found after {retries} retries.")

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
        time.sleep(1)
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        tesseract_dir_path = self.app_temp_dir / "Tesseract-OCR"
        default_tesseract_path = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
        if self.tesseract_unzipped and (tesseract_dir_path.is_dir() or default_tesseract_path.is_file()):
            window_title = "uprbay.uprb.edu - Tera Term VT"
            hwnd = win32gui.FindWindow(None, window_title)
            self.focus_tera_term()
            x, y, right, bottom = get_window_rect(hwnd)
            width = right - x
            height = bottom - y
            crop_margin = (2, 10, 10, 2)
            if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
                self.loading_screen.withdraw()
            with mss() as sct:
                monitor = {
                    "top": y,
                    "left": x,
                    "width": width,
                    "height": height
                }
                screenshot = sct.grab(monitor)
                img = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)
                if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
                    self.loading_screen.deiconify()
                img = img.crop((crop_margin[0], crop_margin[1], img.width - crop_margin[2],
                                img.height - crop_margin[3])).convert("L")
                img = img.resize((img.width * 2, img.height * 2), resample=Image.Resampling.LANCZOS)
                # img.save("screenshot.png")
                custom_config = r"--oem 3 --psm 6"
                text = pytesseract.image_to_string(img, config=custom_config)
                return text
        else:
            try:
                with SevenZipFile(self.zip_path, mode="r") as z:
                    z.extractall(self.app_temp_dir)
                tesseract_dir = Path(self.app_temp_dir) / "Tesseract-OCR"
                pytesseract.pytesseract.tesseract_cmd = str(tesseract_dir / "tesseract.exe")
                self.tesseract_unzipped = True
                del z, tesseract_dir, tesseract_dir_path
                gc.collect()
                return self.capture_screenshot()
            except Exception as err:
                print(f"Error occurred during unzipping: {str(err)}")
                self.tesseract_unzipped = False
                self.after(100, self.show_error_message, 320, 225, translation["tesseract_error"])
                return

    # creates pdf of the table containing for the searched class
    def create_search_pdf(self, data_list, classes_list, filepath, semesters_list):
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
    def download_search_classes_as_pdf(self):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            return

        lang = self.language_menu.get()
        translation = self.load_language(lang)

        classes_list = []
        data = []
        semester_list = []

        # Loop through each table in self.class_table_pairs
        for display_class, table, semester, _, _, _ in self.class_table_pairs:
            class_name = display_class.cget("text").split("-")[0].strip()
            table_data = table.get()

            classes_list.append(class_name)
            data.append(table_data)
            semester_list.append(semester)

        all_same_semester = all(semester == semester_list[0] for semester in semester_list)
        if len(self.class_table_pairs) == 1:
            initial_file_name = f"{semester_list[0]}_{classes_list[0]}_{translation['class_data']}.pdf"
        elif all_same_semester:
            initial_file_name = f"{semester_list[0]}_{translation['classes_data']}.pdf"
        else:
            initial_file_name = f"{translation['multiple_semesters']}_{translation['classes_data']}.pdf"

        # Define where the PDF will be saved
        home = os.path.expanduser("~")
        downloads = os.path.join(home, "Downloads")
        filepath = filedialog.asksaveasfilename(
            title=translation["save_pdf"], defaultextension=".pdf", initialdir=downloads,
            filetypes=[("PDF Files", "*.pdf")], initialfile=initial_file_name
        )

        # Check if user cancelled the file dialog
        if not filepath:
            return

        classes_list, data, semester_list = TeraTermUI.merge_tables(classes_list, data, semester_list)
        self.create_search_pdf(data, classes_list, filepath, semester_list)
        self.show_success_message(350, 265, translation["pdf_save_success"])

    def copy_cell_data_to_clipboard(self, cell_data):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        cell_value = re.sub(r"\n\s*", " ", cell_data["value"])
        if not cell_value.strip():
            return

        if re.match(r"\d{1,2}:\d{2} [APM]{2} \d{1,2}:\d{2} [APM]{2}", cell_value):
            cell_value = re.sub(r"([APM]{2}) (\d{1,2}:\d{2})", r"\1 - \2", cell_value)

        self.focus_set()
        self.clipboard_clear()
        self.clipboard_append(cell_value)

        # Close existing tooltip if any
        self.destroy_tooltip()

        # Create new tooltip
        x, y = self.winfo_pointerxy()
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.transient(self)
        self.tooltip.config(bg="#145DA0")
        self.tooltip.wm_geometry(f"+{x + 20}+{y + 20}")

        label = tk.Label(self.tooltip, text=translation["clipboard"],
                         bg="#145DA0", fg="#fff", font=("Arial", 10, "bold"))
        label.pack(padx=5, pady=5)
        self.lift_tooltip()

        # Auto-destroy after 1.5 seconds and reset the tooltip variable
        self.tooltip.after(1500, self.destroy_tooltip)

    def destroy_tooltip(self):
        if self.tooltip is not None and self.tooltip.winfo_exists():
            self.tooltip.destroy()
            self.tooltip = None

    def lift_tooltip(self):
        if self.tooltip is not None and self.tooltip.winfo_exists():
            self.tooltip.lift()

        self.after(100, self.lift_tooltip)

    def transfer_class_data_to_enroll_tab(self, event, cell):
        section_text = cell.cget("text")
        if not section_text.strip():
            return

        self.e_classes_entry.delete(0, "end")
        self.e_section_entry.delete(0, "end")
        display_class, _, semester_text, _, _, _ = self.class_table_pairs[self.current_table_index]
        self.e_classes_entry.insert(0, display_class.cget("text").split("-")[0].strip())
        self.e_section_entry.insert(0, section_text)
        self.e_semester_entry.set(semester_text)
        self.register.select()
        self.check_class_time()
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.focus_set()

        # Close existing tooltip if any
        self.destroy_tooltip()

        # Create new tooltip
        x, y = self.winfo_pointerxy()
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.transient(self)
        self.tooltip.config(bg='#145DA0')
        self.tooltip.wm_geometry(f"+{x + 20}+{y + 20}")

        label = tk.Label(self.tooltip, text=translation["pasted"],
                         bg="#145DA0", fg="#fff", font=("Arial", 10, "bold"))
        label.pack(padx=5, pady=5)
        self.lift_tooltip()

        # Auto-destroy after 3.5 seconds and reset the tooltip variable
        self.tooltip.after(3500, self.destroy_tooltip)

    @staticmethod
    def open_student_help(event, cell):
        av_value = cell.cget("text")
        if av_value == "RSVD":
            webbrowser.open("https://studenthelp.uprb.edu/")

    @staticmethod
    def open_professor_profile(event, cell):
        def remove_prefixes(p_names):
            return [name for name in p_names if name.lower() not in ["de", "del"]]

        def attempt_open_url(p_names):
            first_name = p_names[2].lower()
            last_names = [p_names[0].lower(), "-".join(p_names[:2]).lower()]
            urls = [f"https://notaso.com/professors/{first_name}-{ln}/" for ln in last_names]
            headers = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                      "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")}
            with requests.Session() as session:
                for url in urls:
                    try:
                        response = session.head(url, headers=headers, timeout=5)
                        if response.status_code == 200:
                            webbrowser.open(url)
                            return
                    except requests.exceptions.RequestException as err:
                        print(f"Failed to open URL: {url}, Error: {err}")

        instructor_text = cell.cget("text")
        if not instructor_text.strip():
            return

        url_mapping = {
            "LA LUZ CONCEPCION JOSE J": "https://notaso.com/professors/jose-la-luz/",
            "MARRERO CARRASQUILLO ALB": "https://notaso.com/professors/alberto-marrero/",
            "VAZQUEZ DE SERRANO EILEE": "https://notaso.com/professors/eileen-vazquez-de-serrano/",
            "GARCIA CUEVAS EUGENIO": "https://notaso.com/professors/eugenio-garcia-perez/",
            "MEDINA CRUZ OLGA L.": "https://notaso.com/professors/olga-l-medina-cruz/",
            "RODRIGUEZ VALENTIN JOSE A": "https://notaso.com/professors/jose-rodriguez-valentin-2/",
            "VILLARONGA SWEET LUIS G.": "https://notaso.com/professors/gabriel-villaronga-sweet/",
            "GONZALEZ GONZALEZ ORLAND": "https://notaso.com/professors/orlando-gonzalez/",
            "DE JESUS CARDONA HECTOR": "https://notaso.com/professors/hector-de-jesus-cardona/",
            "SEPULVEDA NIEVES FRANCIS": "https://notaso.com/professors/francisco-sepulveda/",
            "DE MOYA FIGUEROA DORIS C": "https://notaso.com/professors/doris-de-moya/",
            "LA TORRE RODRIGUEZ ANGEL": "https://notaso.com/professors/angel-la-torre/",
            "PABON BATLLE LUIS H.": "https://notaso.com/professors/luis-h-pabon-battle-3/",
            "VAZQUEZ LAZO NIEVE DE LO": "https://notaso.com/professors/nieves-vazquez/",
            "CRESPO KEBLER ELIZABETH": "https://notaso.com/professors/dra-elizabeth-crespo/",
            "LAUREANO MOLINA FRANCISC": "https://notaso.com/professors/francisco-laureano/",
            "FEBLES IGUINA ISABEL M.": "https://notaso.com/professors/prof-febles/",
            "MARICHAL LUGO CARLOS J.": "https://notaso.com/professors/carlos-j-marichal-lugo/",
            "COSTA COLON MARIA DEL RO": "https://notaso.com/professors/maria-del-rocio-costa/",
            "OLAVARRIA FULLERTON JENI": "https://notaso.com/professors/jenifier-olavarria/",
            "COUTIN RODICIO RICARDO": "https://notaso.com/professors/ricardo-coutin-rodicio-2/"
        }
        hardcoded_name = " ".join(instructor_text.split())
        if hardcoded_name in url_mapping:
            hard_coded_url = url_mapping[hardcoded_name]
            threading.Thread(target=webbrowser.open, args=(hard_coded_url,)).start()
            return

        names = remove_prefixes(instructor_text.split())
        if len(names) >= 3:
            threading.Thread(target=attempt_open_url, args=(names,)).start()

    # displays the extracted data of searched classes into a table
    def display_searched_class_data(self, data):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        spec_data = TeraTermUI.specific_class_data(data)
        original_headers = ["SEC", "M", "CRED", "DAYS", "TIMES", "AV", "INSTRUCTOR"]
        headers = [translation["sec"], translation["m"], translation["cred"],
                   translation["days"], translation["times"], translation["av"],
                   translation["instructor"]]
        header_mapping = dict(zip(original_headers, headers))
        modified_data = [{header_mapping[key]: value for key, value in item.items() if key in header_mapping}
                         for item in spec_data]
        if not modified_data:
            self.after(100, self.show_error_message, 320, 235, translation["failed_to_search"])
            return
        table_values = [headers] + [[item.get(header, "") for header in headers] for item in modified_data]
        original_table_values = table_values.copy()
        if self.sort_by is not None and self.sort_by.get() != translation["sort_by"] and \
                self.sort_by.get() != translation["original_data"]:
            sorted_data = self.sort_data(modified_data, self.sort_by.get())
            table_values = [headers] + [[item.get(header, "") for header in headers] for item in sorted_data]
        else:
            if self.sort_by is not None and self.sort_by.get() == translation["original_data"]:
                self.sort_by.set(translation["sort_by"])

        available_key = translation["av"]
        available_values = sorted([row[available_key] for row in modified_data])
        duplicate_index = self.find_duplicate(self.get_class_for_pdf, self.get_semester_for_pdf, self.show_all_sections,
                                              available_values)
        if duplicate_index is not None:
            _, _, _, _, existing_available_values, _ = self.class_table_pairs[duplicate_index]
            if sorted(existing_available_values) != available_values:
                _, table_update, _, _, _, _ = self.class_table_pairs[duplicate_index]
                new_row_count = len(table_values) - 1
                current_row_count = len(table_update.values) if table_update.values else 0
                if new_row_count > current_row_count:
                    table_update.refresh_table(table_values)
                else:
                    table_update.update_values(table_values)
            self.current_table_index = duplicate_index
            self.search_scrollbar.scroll_to_top()
            self.update_buttons()
            self.after(100, self.display_current_table)
            return

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
            if i < 4 or i == 5:
                new_table.edit_column(i, width=55)
            cell = new_table.get_cell(0, i)
            tooltip_message = tooltip_messages[header]
            if cell in self.table_tooltips:
                self.table_tooltips[cell].configure(message=tooltip_message)
            else:
                tooltip = CTkToolTip(cell, message=tooltip_message, bg_color="#989898", alpha=0.90)
                self.table_tooltips[cell] = tooltip
        self.table = new_table
        self.original_table_data[new_table] = original_table_values

        instructor_col_index = headers.index(translation["instructor"])
        av_col_index = headers.index(translation["av"])
        for row in range(1, num_rows):
            section_cell = new_table.get_cell(row, 0)
            new_table.bind_cell(row, 0, "<Button-3>", lambda event, t_cell=section_cell:
                                self.transfer_class_data_to_enroll_tab(event, t_cell))
            instructor_cell = new_table.get_cell(row, instructor_col_index)
            new_table.bind_cell(row, instructor_col_index, "<Button-3>", lambda event, t_cell=instructor_cell:
                                TeraTermUI.open_professor_profile(event, t_cell))
            av_cell = new_table.get_cell(row, av_col_index)
            new_table.bind_cell(row, av_col_index, "<Button-3>", lambda event, t_cell=av_cell:
                                TeraTermUI.open_student_help(event, t_cell))
        for col_index in range(len(headers)):
            new_table.bind_cell(0, col_index, "<Button-3>",
                                lambda event: self.move_tables_overlay_event())

        display_class = customtkinter.CTkLabel(self.search_scrollbar, text=self.get_class_for_pdf,
                                               font=customtkinter.CTkFont(size=15, weight="bold", underline=True))
        display_class.bind("<Button-1>", lambda event: self.focus_set())
        if self.table_count is None:
            table_count_label = f" {len(self.class_table_pairs)}/20"
            self.table_count = customtkinter.CTkLabel(self.search_scrollbar, text=table_count_label)
            self.previous_button = CustomButton(self.search_scrollbar, text=translation["previous"],
                                                command=self.show_previous_table)
            self.next_button = CustomButton(self.search_scrollbar, text=translation["next"],
                                            command=self.show_next_table)
            self.remove_button = CustomButton(self.search_scrollbar, text=translation["remove"], hover_color="darkred",
                                              fg_color="red", command=self.remove_current_table)
            self.download_search_pdf = CustomButton(self.search_scrollbar, text=translation["pdf_save_as"],
                                                    hover_color="#173518", fg_color="#2e6930",
                                                    command=self.download_search_classes_as_pdf)
            self.table_count_tooltip = CTkToolTip(self.table_count, message=translation["table_count_tooltip"],
                                                  bg_color="#989898", alpha=0.90)
            self.previous_button_tooltip = CTkToolTip(self.previous_button, message=translation["previous_tooltip"],
                                                      bg_color="#1E90FF")
            self.next_button_tooltip = CTkToolTip(self.next_button, message=translation["next_tooltip"],
                                                  bg_color="#1E90FF")
            self.remove_button_tooltip = CTkToolTip(self.remove_button, message=translation["remove_tooltip"],
                                                    bg_color="red")
            self.download_search_pdf_tooltip = CTkToolTip(self.download_search_pdf,
                                                          message=translation["download_pdf_search_tooltip"],
                                                          bg_color="green")
            self.sort_by = customtkinter.CTkOptionMenu(self.search_scrollbar, values=[
                translation["time_asc"], translation["time_dec"],
                translation["av_asc"], translation["av_dec"],
                translation["original_data"]], command=self.sort_tables)
            self.sort_by.set(translation["sort_by"])
            self.sort_by_tooltip = CTkToolTip(self.sort_by, message=translation["sort_by_tooltip"],
                                              bg_color="#1E90FF")
        self.class_table_pairs.append((display_class, new_table, self.get_semester_for_pdf,
                                       self.show_all_sections, available_values, self.search_next_page_status))
        self.check_and_update_labels()
        self.current_table_index = len(self.class_table_pairs) - 1
        if len(self.class_table_pairs) > 20:
            display_class_to_remove, table_to_remove, _, _, _, more_sections = self.class_table_pairs[0]
            display_class_to_remove.grid_forget()
            display_class_to_remove.unbind("<Button-1>")
            table_to_remove.grid_forget()
            for cell in table_to_remove.get_all_cells():
                if cell in self.table_tooltips:
                    self.table_tooltips[cell].destroy()
                    del self.table_tooltips[cell]
            if table_to_remove in self.original_table_data:
                del self.original_table_data[table_to_remove]
            if more_sections:
                self.search_next_page.grid_forget()
                self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
                self.search.configure(width=140)
                self.search_next_page_status = False
            del self.class_table_pairs[0]
            self.after(0, display_class_to_remove.destroy)
            self.after(0, table_to_remove.destroy)
            self.current_table_index = max(0, self.current_table_index - 1)
            self.table_count.configure(text_color=("black", "white"))

        self.display_current_table()

        new_table.grid(row=2, column=1, padx=(0, 15), pady=(40, 0), sticky="n")
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
        self.download_search_pdf.grid(row=6, column=1, padx=(157, 0), pady=(10, 0), sticky="n")
        self.sort_by.grid(row=6, column=1, padx=(0, 157), pady=(10, 0), sticky="n")
        self.update_buttons()
        self.search_scrollbar.scroll_to_top()
        table_count_label = f"{translation['table_count']}{len(self.class_table_pairs)}/20"
        self.table_count.configure(text=table_count_label)
        if len(self.class_table_pairs) == 20:
            self.table_count.configure(text_color="red")
        self.table_count.bind("<Button-1>", lambda event: self.focus_set())
        self.sort_by.bind("<FocusIn>", lambda event: self.search_scrollbar.scroll_to_widget(self.sort_by))
        self.bind("<Control-s>", lambda event: self.download_search_classes_as_pdf())
        self.bind("<Control-S>", lambda event: self.download_search_classes_as_pdf())
        self.bind("<Control-w>", lambda event: self.keybind_remove_current_table())
        self.bind("<Control-W>", lambda event: self.keybind_remove_current_table())

    def find_duplicate(self, new_display_class, new_semester, show_all_sections_state, available_values):
        for index, (display_class, table, semester, existing_show_all_sections_state,
                    existing_available_values, _) in enumerate(self.class_table_pairs):
            if (display_class.cget("text").split("-")[0].strip() == new_display_class
                    and semester == new_semester and existing_show_all_sections_state == show_all_sections_state
                    and sorted(existing_available_values) == sorted(available_values)):
                return index
        return None

    def sort_data(self, data, sort_by_option):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        headers = list(data[0].keys()) if data else []
        time_key = "TIMES" if "TIMES" in headers else None
        av_key = "AV" if "AV" in headers else None
        section_key = "SEC" if "SEC" in headers else None
        memoized_times = {}

        def get_time_minutes(t_row):
            if not time_key or not t_row.get(time_key) or t_row.get(time_key).strip().lower() == "tba":
                return float("inf")
            times_str = t_row.get(time_key, "")
            times_key = tuple(times_str.strip().split("\n"))
            if times_key in memoized_times:
                return memoized_times[times_key]
            total_minutes = 0
            for t in times_key:
                if t in memoized_times:
                    minutes = memoized_times[t]
                else:
                    try:
                        minutes = int(datetime.strptime(t, "%I:%M %p").strftime("%H")) * 60 + \
                                  int(datetime.strptime(t, "%I:%M %p").strftime("%M"))
                        memoized_times[t] = minutes
                    except ValueError:
                        minutes = float("inf")
                        memoized_times[t] = minutes
                if minutes == float("inf"):
                    return minutes
                total_minutes += minutes
            memoized_times[times_key] = total_minutes
            return total_minutes

        def parse_av_value(av_value):
            if av_value in ["998", "999"]:
                return float("inf")
            try:
                return int(av_value)
            except ValueError:
                return float("inf")

        entries_with_section = []
        entries_without_section = {}
        non_standard_positions = []
        last_section_key = None
        for i, row in enumerate(data):
            if section_key and row.get(section_key):
                section = row.get(section_key).strip()
                entries_with_section.append((section, row))
                last_section_key = section
            elif last_section_key:
                if last_section_key not in entries_without_section:
                    entries_without_section[last_section_key] = []
                entries_without_section[last_section_key].append(row)
            else:
                non_standard_positions.append((i, row))

        def sort_key(entry, primary_key, secondary_key):
            if primary_key == time_key:
                primary_value = get_time_minutes(entry[1])
            else:
                primary_value = parse_av_value(entry[1].get(primary_key, ""))

            if primary_value == float("inf"):
                primary_value = float("-inf") if reverse_sort else float("inf")

            if secondary_key == time_key:
                secondary_value = get_time_minutes(entry[1])
            else:
                secondary_value = parse_av_value(entry[1].get(secondary_key, ""))

            return primary_value, secondary_value

        if sort_by_option in [translation["time_asc"], translation["time_dec"]] and time_key:
            reverse_sort = (sort_by_option == translation["time_dec"])
            entries_with_section.sort(key=lambda x: sort_key(x, time_key, av_key), reverse=reverse_sort)
            non_standard_positions.sort(key=lambda x: sort_key(x, time_key, av_key), reverse=reverse_sort)
        elif sort_by_option in [translation["av_asc"], translation["av_dec"]] and av_key:
            reverse_sort = (sort_by_option == translation["av_dec"])
            entries_with_section.sort(key=lambda x: sort_key(x, av_key, time_key), reverse=reverse_sort)
            non_standard_positions.sort(key=lambda x: sort_key(x, av_key, time_key), reverse=reverse_sort)

        sorted_data = []
        for section, row in entries_with_section:
            sorted_data.append(row)
            if section in entries_without_section:
                sorted_data.extend(entries_without_section[section])
        for pos, row in non_standard_positions:
            sorted_data.append(row)

        return sorted_data

    def sort_tables(self, sort_by_option):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.last_sort_option == (sort_by_option, len(self.class_table_pairs)) or \
                not self.last_sort_option and sort_by_option == translation["original_data"]:
            return

        if sort_by_option == translation["original_data"]:
            for _, table, _, _, _, _ in self.class_table_pairs:
                original_data = self.original_table_data[table]
                table.update_values(original_data)
            self.last_sort_option = (sort_by_option, len(self.class_table_pairs))
            self.after(0, self.search_scrollbar.scroll_to_top)
            self.after(0, self.focus_set)
            return

        for _, table, _, _, _, _ in self.class_table_pairs:
            table_data = table.values
            headers = table_data[0]
            time_index = headers.index("TIMES") if "TIMES" in headers else -1
            av_index = headers.index("AV") if "AV" in headers else -1
            section_index = headers.index("SEC") if "SEC" in headers else -1
            memoized_times = {}

            def get_time_minutes(t_row):
                if time_index == -1 or not t_row[time_index] or t_row[time_index].strip().lower() == "tba":
                    return float("inf")
                times_key = tuple(t_row[time_index].strip().split("\n"))
                if times_key in memoized_times:
                    return memoized_times[times_key]
                total_minutes = 0
                for t in times_key:
                    if t in memoized_times:
                        minutes = memoized_times[t]
                    else:
                        try:
                            minutes = int(datetime.strptime(t, "%I:%M %p").strftime("%H")) * 60 + int(
                                datetime.strptime(t, "%I:%M %p").strftime("%M"))
                            memoized_times[t] = minutes
                        except ValueError:
                            minutes = float("inf")
                            memoized_times[t] = minutes
                    if minutes == float("inf"):
                        return minutes
                    total_minutes += minutes
                memoized_times[times_key] = total_minutes
                return total_minutes

            def parse_av_value(av_value):
                if av_value in ["998", "999"]:
                    return float("inf")
                try:
                    return int(av_value)
                except ValueError:
                    return float("inf")

            entries_with_section = []
            entries_without_section = {}
            non_standard_positions = []

            last_section_key = None
            for i, row in enumerate(table_data[1:]):
                if section_index != -1 and row[section_index].strip():
                    section_key = row[section_index].strip()
                    entries_with_section.append((section_key, row))
                    last_section_key = section_key
                elif last_section_key:
                    if last_section_key not in entries_without_section:
                        entries_without_section[last_section_key] = []
                    entries_without_section[last_section_key].append(row)
                else:
                    non_standard_positions.append((i + 1, row))

            def sort_key(entry, primary_index, secondary_index):
                if primary_index == time_index:
                    primary_value = get_time_minutes(entry[1])
                else:
                    primary_value = parse_av_value(entry[1][primary_index])

                if primary_value == float("inf"):
                    primary_value = float("-inf") if reverse_sort else float("inf")

                if secondary_index == time_index:
                    secondary_value = get_time_minutes(entry[1])
                else:
                    secondary_value = parse_av_value(entry[1][secondary_index])

                return primary_value, secondary_value

            if sort_by_option in [translation["time_asc"], translation["time_dec"]] and time_index != -1:
                reverse_sort = (sort_by_option == translation["time_dec"])
                entries_with_section.sort(key=lambda x: sort_key(x, time_index, av_index), reverse=reverse_sort)
                non_standard_positions.sort(key=lambda x: sort_key(x, time_index, av_index), reverse=reverse_sort)
            elif sort_by_option in [translation["av_asc"], translation["av_dec"]] and av_index != -1:
                reverse_sort = (sort_by_option == translation["av_dec"])
                entries_with_section.sort(key=lambda x: sort_key(x, av_index, time_index), reverse=reverse_sort)
                non_standard_positions.sort(key=lambda x: sort_key(x, av_index, time_index), reverse=reverse_sort)

            final_data = [headers]
            for section_key, row in entries_with_section:
                final_data.append(row)
                if section_key in entries_without_section:
                    final_data.extend(entries_without_section[section_key])
            for _, row in non_standard_positions:
                final_data.append(row)
            table.update_values(final_data)

            self.last_sort_option = (sort_by_option, len(self.class_table_pairs))
            self.after(0, self.search_scrollbar.scroll_to_top)
            self.after(0, self.focus_set)

    def check_and_update_labels(self):
        class_info = {}
        for display_class, _, semester, _, _, _ in self.class_table_pairs:
            display_class_text = display_class.cget("text").split("-")[0].strip()
            if display_class_text not in class_info:
                class_info[display_class_text] = []
            class_info[display_class_text].append((display_class, semester))

        for display_class_text, class_semesters in class_info.items():
            if len(class_semesters) > 1:
                for display_class, semester in class_semesters:
                    new_text = f"{display_class_text} - {semester}"
                    if display_class.cget("text") != new_text:
                        display_class.configure(text=new_text)
            else:
                display_class, _ = class_semesters[0]
                new_text = display_class_text
                if display_class.cget("text") != new_text:
                    display_class.configure(text=new_text)

    def display_current_table(self):
        # Hide all tables and display_classes
        for display_class, curr_table, _, _, _, _ in self.class_table_pairs:
            display_class.grid_forget()
            curr_table.grid_forget()

        # Show the current display_class and table
        display_class, curr_table, _, _, _, _ = self.class_table_pairs[self.current_table_index]
        display_class.grid(row=2, column=1, padx=(0, 0), pady=(8, 0), sticky="n")
        curr_table.grid(row=2, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
        self.table = curr_table
        self.current_class = display_class
        section = self.s_classes_entry.get().upper().replace(" ", "").replace("-", "")
        display_class_text = display_class.cget("text").split(" ")[0]
        if section != display_class_text and self.loading_screen_status is None:
            self.s_classes_entry.delete(0, "end")
            self.s_classes_entry.insert(0, display_class_text)
        self.after(0, self.focus_set)

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
            self.search_scrollbar.scroll_to_top()
            self.update_buttons()
            self.after(100, self.display_current_table)

    def show_next_table(self):
        if self.current_table_index < len(self.class_table_pairs) - 1:
            self.current_table_index += 1
            self.search_scrollbar.scroll_to_top()
            self.update_buttons()
            self.after(100, self.display_current_table)

    def keybind_previous_table(self, event):
        if self.move_slider_left_enabled:
            self.after(0, self.show_previous_table)

    def keybind_next_table(self, event):
        if self.move_slider_left_enabled:
            self.after(0, self.show_next_table)

    def move_tables_overlay_event(self):
        if len(self.class_table_pairs) == 1:
            return

        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.move_tables_overlay is None:
            self.move_tables_overlay = SmoothFadeToplevel(fade_duration=10, final_alpha=0.90)
            self.move_tables_overlay.wm_overrideredirect(True)
            self.move_title_label = customtkinter.CTkLabel(self.move_tables_overlay, text=translation["move_classes"],
                                                           font=customtkinter.CTkFont(size=16, weight="bold"))
            self.move_title_label.grid(row=0, column=1, padx=10, pady=(10, 0))
            self.tables_container = customtkinter.CTkFrame(self.move_tables_overlay, fg_color="transparent")
            self.tables_container.grid(row=1, column=1, padx=(7, 0), pady=(0, 10))
            self.tables_checkboxes = []
        self.update_table_checkboxes()
        self.highlight_selected_table_in_grid()
        self.move_tables_geometry()
        self.move_tables_overlay.deiconify()
        self.after(0, self.move_tables_overlay.focus_force)
        self.move_tables_overlay.bind("<FocusOut>", self.on_move_window_close)
        self.move_tables_overlay.bind("<Escape>", self.on_move_window_close)

    def move_tables_geometry(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.move_tables_overlay.title(translation["move_classes"])
        self.move_title_label.configure(text=translation["move_classes"])
        num_tables = len(self.class_table_pairs)
        checkbox_width = 30
        checkbox_padding = 2
        checkboxes_per_row = 10
        total_rows = (num_tables + checkboxes_per_row - 1) // checkboxes_per_row
        total_checkbox_width = min(num_tables, checkboxes_per_row) * (checkbox_width + checkbox_padding)
        total_width = total_checkbox_width + 110
        total_height = total_rows * 32 + 50
        self.move_tables_overlay.grid_rowconfigure(0, weight=1)
        self.move_tables_overlay.grid_rowconfigure(1, weight=1)
        self.move_tables_overlay.grid_columnconfigure(0, weight=1)
        self.move_tables_overlay.grid_columnconfigure(1, weight=0)
        self.move_tables_overlay.grid_columnconfigure(2, weight=1)
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        center_x = main_window_x + (main_window_width // 2) - (total_width // 2)
        center_y = main_window_y + (main_window_height // 2) - (total_height // 2)
        self.move_tables_overlay.geometry(f"{total_width}x{total_height}+{center_x + 103}+{center_y + 13}")

    def update_table_checkboxes(self):
        for widget in self.tables_container.winfo_children():
            widget.grid_remove()

        num_tables = len(self.class_table_pairs)
        checkbox_width = 30
        checkbox_padding = 2
        checkboxes_per_row = 10
        for index in range(num_tables):
            if index < len(self.tables_checkboxes):
                checkbox = self.tables_checkboxes[index]
            else:
                checkbox = customtkinter.CTkCheckBox(
                    self.tables_container, text="", width=checkbox_width, checkbox_width=30, checkbox_height=30,
                    command=lambda idx=index: self.select_new_position(idx))
                self.tables_checkboxes.append(checkbox)
            row = index // checkboxes_per_row
            column = index % checkboxes_per_row
            checkbox.grid(row=row, column=column, padx=checkbox_padding, pady=3)
            checkbox.bind("<space>", lambda event, idx=index: self.select_new_position(idx))

    def on_move_window_close(self, event):
        current_focus = self.move_tables_overlay.focus_get()
        if current_focus is None or event.keysym == "Escape":
            self.move_tables_overlay.withdraw()

    def highlight_selected_table_in_grid(self):
        for idx, checkbox in enumerate(self.tables_checkboxes):
            if idx == self.current_table_index:
                if not checkbox.get():
                    checkbox.select()
                checkbox.configure(state="disabled", canvas_takefocus=False)
            else:
                if checkbox.get():
                    checkbox.deselect()
                checkbox.configure(state="normal")

    def select_new_position(self, target_index):
        if target_index != self.current_table_index:
            self.rearrange_tables(self.current_table_index, target_index)
        self.move_tables_overlay.withdraw()

    def rearrange_tables(self, source_index, target_index):
        self.class_table_pairs[source_index], self.class_table_pairs[target_index] = \
            self.class_table_pairs[target_index], self.class_table_pairs[source_index]

        for _, table_widget, _, _, _, _ in self.class_table_pairs:
            table_widget.grid(row=2, column=1, padx=(0, 0), pady=(40, 0), sticky="n")

        if self.current_table_index == source_index:
            self.current_table_index = target_index
        elif self.current_table_index == target_index:
            self.current_table_index = source_index

        self.display_current_table()
        self.update_buttons()

    def keybind_remove_current_table(self):
        current_time = time.time()
        if hasattr(self, "last_remove_time") and current_time - self.last_remove_time < 0.250 or \
                (self.loading_screen_status is not None and self.loading_screen_status.winfo_exists()):
            return

        self.remove_current_table()
        self.last_remove_time = current_time

    def remove_current_table(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        display_class_to_remove, table_to_remove, _, _, _, more_sections \
            = self.class_table_pairs[self.current_table_index]
        display_class_to_remove.grid_forget()
        display_class_to_remove.unbind("<Button-1>")
        table_to_remove.grid_forget()

        for cell in table_to_remove.get_all_cells():
            if cell in self.table_tooltips:
                self.table_tooltips[cell].destroy()
                del self.table_tooltips[cell]

        if table_to_remove in self.original_table_data:
            del self.original_table_data[table_to_remove]

        if more_sections and self.search_next_page.grid_info():
            next_index = min(self.current_table_index + 1, len(self.class_table_pairs) - 1)
            prev_index = max(self.current_table_index - 1, 0)
            next_has_more = self.class_table_pairs[next_index][5] if next_index != self.current_table_index else False
            prev_has_more = self.class_table_pairs[prev_index][5] if prev_index != self.current_table_index else False
            if not next_has_more and not prev_has_more:
                self.search_next_page.grid_forget()
                self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
                self.search.configure(width=140)
                self.search_next_page_status = False

        self.after(0, display_class_to_remove.destroy)
        self.after(0, table_to_remove.destroy)

        if len(self.class_table_pairs) == 20:
            self.table_count.configure(text_color=("black", "white"))

        del self.class_table_pairs[self.current_table_index]

        table_count_label = f"{translation['table_count']}{len(self.class_table_pairs)}/20"
        self.table_count.configure(text=table_count_label)

        if len(self.class_table_pairs) == 1:
            self.previous_button.grid_forget()
            self.next_button.grid_forget()
            self.bind("<Left>", self.move_slider_left)
            self.bind("<Right>", self.move_slider_right)
        elif len(self.class_table_pairs) == 0:
            if self.sort_by.get() != translation["sort_by"]:
                self.sort_by.set(translation["sort_by"])
            self.table = None
            self.current_class = None
            self.last_sort_option = ()
            self.table_count.grid_forget()
            self.remove_button.grid_forget()
            self.download_search_pdf.grid_forget()
            self.sort_by.grid_forget()
            self.search_scrollbar.scroll_to_top()
            self.unbind("<Control-s>")
            self.unbind("<Control-S>")
            self.unbind("<Control-w>")
            self.unbind("<Control-W>")
            self.after(0, self.focus_set)
            return

        self.current_table_index = max(0, self.current_table_index - 1)
        self.table_count.grid_forget()
        self.remove_button.grid_forget()
        self.download_search_pdf.grid_forget()
        self.sort_by.grid_forget()
        self.search_scrollbar.scroll_to_top()
        self.check_and_update_labels()
        self.update_buttons()

        def reshow_widgets():
            self.table_count.grid(row=4, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
            if len(self.class_table_pairs) > 1:
                self.previous_button.grid(row=5, column=1, padx=(0, 300), pady=(10, 0), sticky="n")
                self.next_button.grid(row=5, column=1, padx=(300, 0), pady=(10, 0), sticky="n")
            self.remove_button.grid(row=5, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
            self.download_search_pdf.grid(row=6, column=1, padx=(157, 0), pady=(10, 0), sticky="n")
            self.sort_by.grid(row=6, column=1, padx=(0, 157), pady=(10, 0), sticky="n")

        self.after(100, self.display_current_table)
        self.after(125, reshow_widgets)

    def automate_copy_class_data(self):
        import pyautogui

        max_retries = 5
        original_timeout = timings.Timings.window_find_timeout
        original_retry = timings.Timings.window_find_retry
        for attempt in range(max_retries):
            try:
                timings.Timings.window_find_timeout = 0.5
                timings.Timings.window_find_retry = 0.1
                self.uprb.UprbayTeraTermVt.type_keys("%e")
                if attempt < 1:
                    self.uprb.UprbayTeraTermVt.type_keys("e")
                if attempt >= 1:
                    self.select_screen_item.invoke()
                break
            except ElementNotFoundError as err:
                print(f"An error occurred: {err}")
                if attempt < max_retries - 1:
                    pass
                else:
                    print("Max retries reached, raising exception.")
                    raise
            finally:
                timings.Timings.window_find_timeout = original_timeout
                timings.Timings.window_find_retry = original_retry
        self.uprb.UprbayTeraTermVt.type_keys("%c")
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            self.loading_screen.withdraw()
        pyautogui.FAILSAFE = False
        original_position = pyautogui.position()
        quarter_width = self.tera_term_window.width // 4
        center_x = self.tera_term_window.left + quarter_width
        center_y = self.tera_term_window.top + self.tera_term_window.height // 2
        pyautogui.click(center_x, center_y)
        pyautogui.moveTo(original_position)
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            self.loading_screen.deiconify()

    @staticmethod
    def get_latest_term(input_text):
        term_pattern = r"\b[A-Z][0-9]{2}[%*]"
        matches = re.findall(term_pattern, input_text, re.IGNORECASE)
        results = {"percent": None, "asterisk": None}

        for match in matches:
            if match.endswith("%"):
                results["percent"] = match[:-1]
            elif match.endswith("*"):
                results["asterisk"] = match[:-1]
        if not matches:
            if "OPCIONES PARA EL ESTUDIANTE" not in input_text:
                return "Latest term not found"
            else:
                return "No active semester"
        return results

    def handle_current_semester(self):
        if not self.found_latest_semester:
            time.sleep(1)
            TeraTermUI.disable_user_input()
            self.automate_copy_class_data()
            TeraTermUI.disable_user_input("on")
            copy = pyperclip.paste()
            latest_term = TeraTermUI.get_latest_term(copy)
            if latest_term == "Latest term not found":
                self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}")
                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                self.reset_activity_timer()
                return "error"
            elif latest_term == "No active semester":
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                if "INVALID ACTION" in copy:
                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                    self.reset_activity_timer()
                else:
                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                    self.reset_activity_timer()
                self.after(100, self.show_error_message, 320, 235, translation["no_active_semester"])
                return "negative"
            elif latest_term["percent"]:
                self.DEFAULT_SEMESTER = latest_term["percent"]
                row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
                if not row_exists:
                    self.cursor.execute("INSERT INTO user_data (default_semester) VALUES (?)",
                                        (self.DEFAULT_SEMESTER,))
                else:
                    self.cursor.execute("UPDATE user_data SET default_semester=?",
                                        (self.DEFAULT_SEMESTER,))
                self.found_latest_semester = True
                return latest_term["percent"]
            else:
                return self.DEFAULT_SEMESTER
        else:
            return self.DEFAULT_SEMESTER

    @staticmethod
    def calculate_default_semester():
        # Preset base year and starting letter
        base_year = 2000
        start_letter = "A"
        semester_part = "1"  # Default value

        # Current date
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        # Calculate the academic year
        academic_year = current_year - base_year

        # Adjust the academic year and semester part based on current month
        if current_month in [1, 2]:
            semester_part = "2"
            academic_year -= 1
        elif current_month in [3, 4, 5, 6, 7, 8, 9]:
            semester_part = "1"
        elif current_month in [10, 11, 12]:
            semester_part = "2"

        # Calculate the letter
        letter_index = (academic_year // 10) % 26
        letter = chr(ord(start_letter) + letter_index)

        return f"{letter}{academic_year % 10}{semester_part}"

    @staticmethod
    def generate_semester_values(default_semester):
        # Extracting letter and year part from default semester code
        letter = default_semester[0]
        year_digit = int(default_semester[1])

        # Initialize list to store generated semester values
        values = []

        # Looping through the current and previous year
        for year_iter in range(year_digit - 1, year_digit + 1):
            for semester_part in range(1, 4):
                # Handling the edge case for year '0' in the previous year
                if year_iter == year_digit - 1 and default_semester[1] == "0":
                    if letter == "A":
                        values.append(f"Z9{semester_part}")
                    else:
                        values.append(f"{chr(ord(letter) - 1)}9{semester_part}")
                else:
                    # Appending regular semester values
                    values.append(f"{letter}{year_iter % 10}{semester_part}")

        # Return the last six semester codes
        return values[-6:]

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

            for day, time_slot in zip(days, times):
                if first:
                    # For the first day and time, keep the item details intact but remove additional days and times
                    modified_item = item.copy()
                    modified_item["DAYS"] = day
                    modified_item["TIMES"] = time_slot
                    first = False  # Unset the flag after the first iteration
                else:
                    # For additional days and times, create a new item with only the day and time
                    modified_item = {key: "" for key in item}  # Initialize all keys with empty strings
                    modified_item["DAYS"] = day
                    modified_item["TIMES"] = time_slot

                # Check if the time is just a dash, handle it specifically
                if modified_item["TIMES"] == "-":
                    modified_item["TIMES"] = "-"
                else:
                    # Process times to have proper format for each entry
                    times_parts = modified_item["TIMES"].split("-")
                    if len(times_parts) == 2:
                        start, end = times_parts
                        start = start.lstrip("0")
                        end = end.lstrip("0")
                        if len(start) > 2:
                            start = start[:-4] + ":" + start[-4:-2] + " " + start[-2:]
                        if len(end) > 2:
                            end = end[:-4] + ":" + end[-4:-2] + " " + end[-2:]
                        modified_item["TIMES"] = "\n".join([start, end])
                    else:
                        # If it does not follow the expected pattern, leave it as is
                        modified_item["TIMES"] = modified_item["TIMES"]

                modified_data.append(modified_item)

        return modified_data

    # extracts the text from the searched class to get the important information
    @staticmethod
    def extract_class_data(text):
        from typing import List

        lines = text.split("\n")
        data: List[dict] = []
        course_found = False
        invalid_action = False
        y_n_found = False
        y_n_value = None
        current_section = None
        term_value = None

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
                if y_n_value == "Y":
                    y_n_value = "on"
                elif y_n_value == "N":
                    y_n_value = "off"

            if "TERM:" in line:
                term_value = line.split("TERM:")[-1].strip()[:3]

        session_types = ["LEC", "LAB", "INT", "PRA", "SEM"]
        session_pattern = "|".join(session_types)
        pattern = re.compile(
            rf"(\w+)\s+(\w)\s+({session_pattern})\s+(\d+\.\d+)\s+(\w+)\s+([\dAMP\-TBA]+)\s+([\d\s]+)?\s+.*?\s*(["
            r"NFUL\s]*.*)"
        )
        # Regex pattern to match additional time slots
        time_pattern = re.compile(
            r"^(\s+)(\w{2})\s+([\dAMP\-]+)\s*$"
        )
        for line in lines:
            if any(x in line for x in session_types):
                match = pattern.search(line)
                if match:
                    instructor = match.group(8)
                    instructor_cleaned = re.sub(r"\bN\b(?!\.)", "", instructor)
                    instructor_cleaned = re.sub(r"\bFULL\b", "", instructor_cleaned)
                    instructor_cleaned = re.sub(r"\bRSVD\b", "", instructor_cleaned)
                    instructor_cleaned = re.sub(r"\bRSTR\b", "", instructor_cleaned)
                    instructor_cleaned = instructor_cleaned.strip()
                    av_value = "RSVD" if "RSVD" in instructor else "RSTR" if "RSTR" in instructor else \
                               "999" if "999" in instructor else "998" if "998" in instructor else \
                               match.group(7).strip() if match.group(7) else "0"
                    current_section = {
                        "SEC": match.group(1),
                        "M": match.group(2),
                        "CRED": match.group(4),
                        "DAYS": [match.group(5)],
                        "TIMES": [match.group(6)],
                        "AV": av_value,
                        "INSTRUCTOR": instructor_cleaned
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

        return data, course_found, invalid_action, y_n_found, y_n_value, term_value

    def extract_my_enrolled_classes(self, text):
        lang = self.language_menu.get()
        translation = self.load_language(lang)

        class_pattern = re.compile(
            r"(\b[A-Z])\s+([A-Z]{4}\d{4}[A-Z]{2}\d)\s+([A-Z])?\s+(.*?)\s+([A-Z]{2})\s*([A-FI-NPW]*)\s+"
            r"([A-Z]{1,5}|TBA)\s+(\d{4}[AP]M-\d{4}[AP]M|TBA)\s*(?:\s+([\dA-Z]*?)\s+([A-Z\d]{3,4})?)?"
            r"(?:\s+([A-Z]{1,5}|TBA)\s+(\d{4}[AP]M-\d{4}[AP]M|TBA)\s*(?:\s+([\dA-Z]*?)\s+([A-Z\d]{3,4})?)?)"
            r"?(?=\s+\b[A-Z]|\s*$)",
            re.DOTALL
        )
        matches = class_pattern.findall(text)
        enrolled_classes = []
        for match in matches:
            course_code = f"{match[1][:4]}-{match[1][4:8]}-{match[1][8:]}"
            formatted_time = TeraTermUI.parse_time(match[7])
            class_info = {
                translation["course"]: course_code,
                translation["grade"]: match[5],
                translation["days"]: match[6],
                translation["times"]: formatted_time,
                translation["room"]: match[9]
            }
            enrolled_classes.append(class_info)

            # Check for and add a new entry for additional DIAS and HORAS without the course name
            if match[10]:
                additional_formatted_time = TeraTermUI.parse_time(match[11])
                additional_class_info = {
                    translation["course"]: "",
                    translation["grade"]: "",
                    translation["days"]: match[10],
                    translation["times"]: additional_formatted_time,
                    translation["room"]: match[13]
                }
                enrolled_classes.append(additional_class_info)

        # Search for total credits
        credits_pattern = re.compile(r"CREDITOS TOTAL:\s+(\d+\.\d+)")
        credits_match = credits_pattern.search(text)
        total_credits = credits_match.group(1) if credits_match else "0.00"

        return enrolled_classes, total_credits

    @staticmethod
    def parse_time(time_str):
        if time_str == "TBA":
            return "TBA"
        start_time, end_time = time_str.split("-")
        start_time = start_time.lstrip("0")
        end_time = end_time.lstrip("0")
        start_time = f"{start_time[:-4]}:{start_time[-4:-2]} {start_time[-2:]}"
        end_time = f"{end_time[:-4]}:{end_time[-4:-2]} {end_time[-2:]}"
        return f"{start_time}\n{end_time}"

    def create_enrolled_classes_pdf(self, data, creds, semester, filepath):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

        lang = self.language_menu.get()
        translation = self.load_language(lang)

        # Prepare the PDF document
        pdf = SimpleDocTemplate(filepath, pagesize=letter)
        elems = []

        # Extract and prepare table data with translated headers
        headers = [translation["course"], translation["grade"], translation["days"],
                   translation["times"], translation["room"]]
        table_data = [headers] + [[cls.get(header, "") for header in headers] for cls in data]

        # Create the table
        table = Table(table_data)

        # Define and set the same table style as in your create_pdf method
        blue = colors.Color(0, 0.5, 0.75)
        gray = colors.Color(0.7, 0.7, 0.7)
        table_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), blue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 14),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), gray),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ])
        table.setStyle(table_style)

        # Get sample styles and create the "Semester" header
        styles = getSampleStyleSheet()
        semester_style = styles["Heading1"]
        semester_style.alignment = 1
        semester_header = Paragraph(f"{translation['semester']}: {semester}", semester_style)

        # Add credits at the bottom of the table
        centered_style = ParagraphStyle(name="Centered", parent=styles["Normal"], alignment=1)
        credits_style = ParagraphStyle(name="CreditsStyle", parent=centered_style, fontSize=12, spaceAfter=10)
        credits_line = Paragraph(f"<b>{translation['total_creds']} {creds}</b>", credits_style)

        # Add the header, table, spacer, and credits to the elements
        elems.extend([semester_header, Spacer(1, 20), table, Spacer(1, 10), credits_line])

        # Build and save the PDF
        pdf.build(elems)

    def download_enrolled_classes_as_pdf(self, data, creds):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            return

        lang = self.language_menu.get()
        translation = self.load_language(lang)
        semester = self.dialog_input.upper().replace(" ", "")

        # Define where the PDF will be saved
        home = os.path.expanduser("~")
        downloads = os.path.join(home, "Downloads")
        filepath = filedialog.asksaveasfilename(
            title=translation["save_pdf"], defaultextension=".pdf", initialdir=downloads,
            filetypes=[("PDF Files", "*.pdf")], initialfile=f"{semester}_{translation['enrolled_classes']}"
        )

        # Check if user cancelled the file dialog
        if not filepath:
            return

        self.create_enrolled_classes_pdf(data, creds, semester, filepath)
        self.show_success_message(350, 265, translation["pdf_save_success"])

    def display_enrolled_data(self, data, creds, dialog_input):
        self.unbind("<Control-Tab>")
        self.unbind("<Control-w>")
        self.unbind("<Control-W>")
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        semester = dialog_input.upper().replace(" ", "")
        headers = [translation["course"], translation["grade"], translation["days"],
                   translation["times"], translation["room"]]
        if not data:
            self.after(100, self.show_error_message, 320, 235, translation["semester_no_data"] + semester)
            return
        self.dialog_input = dialog_input
        self.ask_semester_refresh = True
        table_values = [headers] + [[cls.get(header, "") for header in headers] for cls in data]
        enrolled_rows = len(data) + 1
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
        self.enrolled_classes_data = data
        self.enrolled_classes_credits = creds
        if self.enrolled_classes_table is not None:
            self.enrolled_classes_table.refresh_table(table_values)
            self.total_credits_label.configure(text=translation["total_creds"] + creds)
            self.title_my_classes.configure(text=translation["my_classes"] + semester)
            self.submit_my_classes.configure(command=self.submit_modify_classes_handler)
            self.modify_classes_title.configure(text=translation["mod_classes_title"])
            for i, header in enumerate(headers):
                self.enrolled_classes_table.edit_column(i, width=column_widths[header])
                cell = self.enrolled_classes_table.get_cell(0, i)
                tooltip_message = tooltip_messages[header]
                tooltip = self.enrolled_header_tooltips.get(cell)
                if tooltip:
                    tooltip.configure(message=tooltip_message)
                else:
                    tooltip = CTkToolTip(cell, message=tooltip_message, bg_color="#989898", alpha=0.90)
                    self.enrolled_header_tooltips[cell] = tooltip
            current_entries_count = len(self.change_section_entries)
            new_entries_count = len(data)
            previous_row_had_widgets = True
            pad_y = 9
            for row_index in range(min(current_entries_count, new_entries_count)):
                if row_index == 0:
                    pad_y = 30
                self.change_section_entries[row_index].grid(row=row_index, column=0, padx=(50, 0), pady=(pad_y, 0))
                self.mod_selection_list[row_index].grid(row=row_index, column=0, padx=(0, 100), pady=(pad_y, 0))
                self.change_section_entries[row_index].configure(state="normal")
                if self.change_section_entries[row_index].get():
                    self.change_section_entries[row_index].delete(0, "end")
                self.change_section_entries[row_index].configure(state="disabled")
                self.mod_selection_list[row_index].configure(state="normal")
                self.mod_selection_list[row_index].set(translation["choose"])
                pad_y = 9
            if new_entries_count > current_entries_count:
                for row_index in range(current_entries_count, new_entries_count):
                    if row_index == 0:
                        pad_y = 30
                    else:
                        pad_y = 9 if previous_row_had_widgets else 45

                    if data[row_index][translation["course"]] != "":
                        if row_index < len(self.placeholder_texts_sections):
                            placeholder_text = self.placeholder_texts_sections[row_index]
                        else:
                            extra_placeholder_text = ["KJ1", "LJ1", "KI1", "LI1", "VM1", "JM1"]
                            index_in_extra = (row_index - len(self.placeholder_texts_sections)) % len(
                                extra_placeholder_text)
                            placeholder_text = extra_placeholder_text[index_in_extra]

                        mod_selection = customtkinter.CTkOptionMenu(self.modify_classes_frame,
                                                                    values=[translation["choose"], translation["drop"],
                                                                            translation["section"]], width=80,
                                                                    command=lambda value, index=row_index:
                                                                    self.modify_enrolled_classes(value, index))
                        change_section_entry = CustomEntry(self.modify_classes_frame, self, lang,
                                                           placeholder_text=placeholder_text, width=50)
                        mod_selection.grid(row=row_index, column=0, padx=(0, 100), pady=(pad_y, 0))
                        change_section_entry.grid(row=row_index, column=0, padx=(50, 0), pady=(pad_y, 0))
                        mod_selection_tooltip = CTkToolTip(mod_selection, bg_color="#1E90FF",
                                                           message=translation["mod_selection"])
                        change_section_entry_tooltip = CTkToolTip(change_section_entry, bg_color="#1E90FF",
                                                                  message=translation["change_section_entry"])
                        change_section_entry.configure(state="disabled")
                        self.mod_selection_list.append(mod_selection)
                        self.change_section_entries.append(change_section_entry)
                        self.enrolled_tooltips.append(mod_selection_tooltip)
                        self.enrolled_tooltips.append(change_section_entry_tooltip)
                        previous_row_had_widgets = True
                    else:
                        self.mod_selection_list.append(None)
                        self.change_section_entries.append(None)
                        previous_row_had_widgets = False
            elif new_entries_count < current_entries_count:
                for row_index in range(new_entries_count, current_entries_count):
                    if self.change_section_entries[row_index] is not None:
                        self.change_section_entries[row_index].grid_forget()
                    if self.mod_selection_list[row_index] is not None:
                        self.mod_selection_list[row_index].grid_forget()
        else:
            self.change_section_entries = []
            self.mod_selection_list = []
            self.my_classes_frame = customtkinter.CTkScrollableFrame(self, corner_radius=10, width=620, height=320)
            self.title_my_classes = customtkinter.CTkLabel(self.my_classes_frame,
                                                           text=translation["my_classes"] + semester,
                                                           font=customtkinter.CTkFont(size=20, weight="bold"))
            self.total_credits_label = customtkinter.CTkLabel(self.my_classes_frame,
                                                              text=translation["total_creds"] + creds)
            self.submit_my_classes = CustomButton(self.my_classes_frame, border_width=2,
                                                  text=translation["submit"], text_color=("gray10", "#DCE4EE"),
                                                  command=self.submit_modify_classes_handler)
            self.submit_my_classes_tooltip = CTkToolTip(self.submit_my_classes, bg_color="#1E90FF",
                                                        message=translation["submit_modify_tooltip"])
            self.download_enrolled_pdf = CustomButton(self.my_classes_frame, text=translation["pdf_save_as"],
                                                      hover_color="#173518", fg_color="#2e6930",
                                                      command=lambda: self.download_enrolled_classes_as_pdf(
                                                          self.enrolled_classes_data, self.enrolled_classes_credits))
            self.download_enrolled_pdf_tooltip = CTkToolTip(self.download_enrolled_pdf,
                                                            message=translation["download_pdf_enrolled_tooltip"],
                                                            bg_color="green")
            self.modify_classes_frame = customtkinter.CTkFrame(self.my_classes_frame)
            self.back_my_classes = CustomButton(master=self.t_buttons_frame, fg_color="transparent", border_width=2,
                                                text=translation["back"], hover_color=("#BEBEBE", "#4E4F50"),
                                                text_color=("gray10", "#DCE4EE"), command=self.go_back_menu)
            self.back_my_classes_tooltip = CTkToolTip(self.back_my_classes, alpha=0.90, bg_color="#989898",
                                                      message=translation["back_multiple"])
            self.modify_classes_title = customtkinter.CTkLabel(self.modify_classes_frame,
                                                               text=translation["mod_classes_title"])
            self.enrolled_classes_table = CTkTable(
                self.my_classes_frame,
                column=len(headers),
                row=enrolled_rows,
                values=table_values,
                header_color="#145DA0",
                hover_color="#339CFF",
                command=self.copy_cell_data_to_clipboard,
            )
            for i, header in enumerate(headers):
                self.enrolled_classes_table.edit_column(i, width=column_widths[header])
                cell = self.enrolled_classes_table.get_cell(0, i)
                tooltip_message = tooltip_messages[header]
                tooltip = CTkToolTip(cell, message=tooltip_message, bg_color="#989898", alpha=0.90)
                self.enrolled_header_tooltips[cell] = tooltip

            self.tabview.grid_forget()
            self.back_classes.grid_forget()
            self.my_classes_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 100))
            self.my_classes_frame.grid_columnconfigure(2, weight=1)
            self.title_my_classes.grid(row=1, column=1, padx=(180, 0), pady=(10, 10))
            self.enrolled_classes_table.grid(row=2, column=1, pady=(0, 5), padx=(10, 0))
            self.total_credits_label.grid(row=3, column=1, padx=(180, 0), pady=(0, 15))
            self.submit_my_classes.grid(row=4, column=1, padx=(180, 0))
            self.download_enrolled_pdf.grid(row=5, column=1, padx=(180, 0), pady=(10, 0))
            self.modify_classes_frame.grid(row=2, column=2, sticky="nw", padx=(15, 0))
            self.modify_classes_title.grid(row=0, column=0, padx=(0, 30), pady=(0, 30))
            self.back_my_classes.grid(row=4, column=0, padx=(0, 10), pady=(0, 0), sticky="w")

            pad_y = 9
            for row_index in range(len(self.enrolled_classes_data)):
                if row_index == 0:
                    pad_y = 30
                if self.enrolled_classes_data[row_index][translation["course"]] != "":
                    if row_index < len(self.placeholder_texts_sections):
                        placeholder_text = self.placeholder_texts_sections[row_index]
                    else:
                        extra_placeholder_text = ["KJ1", "LJ1", "KI1", "LI1", "VM1", "JM1"]
                        index_in_extra = (row_index - len(self.placeholder_texts_sections)) % len(
                            extra_placeholder_text)
                        placeholder_text = extra_placeholder_text[index_in_extra]
                    mod_selection = customtkinter.CTkOptionMenu(self.modify_classes_frame,
                                                                values=[translation["choose"], translation["drop"],
                                                                        translation["section"]], width=80,
                                                                command=lambda value, index=row_index:
                                                                self.modify_enrolled_classes(value, index))
                    change_section_entry = CustomEntry(self.modify_classes_frame, self, lang,
                                                       placeholder_text=placeholder_text, width=50)
                    mod_selection.grid(row=row_index, column=0, padx=(0, 100), pady=(pad_y, 0))
                    change_section_entry.grid(row=row_index, column=0, padx=(50, 0), pady=(pad_y, 0))
                    mod_selection_tooltip = CTkToolTip(mod_selection, bg_color="#1E90FF",
                                                       message=translation["mod_selection"])
                    change_section_entry_tooltip = CTkToolTip(change_section_entry, bg_color="#1E90FF",
                                                              message=translation["change_section_entry"])
                    change_section_entry.configure(state="disabled")
                    self.mod_selection_list.append(mod_selection)
                    self.change_section_entries.append(change_section_entry)
                    self.enrolled_tooltips.append(mod_selection_tooltip)
                    self.enrolled_tooltips.append(change_section_entry_tooltip)
                    pad_y = 9
                else:
                    self.mod_selection_list.append(None)
                    self.change_section_entries.append(None)
                    pad_y = 45
            if self.countdown_running:
                self.submit_my_classes.configure(state="disabled")
            self.show_classes.configure(text=translation["show_my_new"])
            self.in_enroll_frame = False
            self.in_search_frame = False
            self.add_key_bindings(event=None)
            self.after(350, self.bind, "<Return>", lambda event: self.submit_modify_classes_handler())
            self.bind("<Up>", lambda event: self.move_up_scrollbar())
            self.bind("<Down>", lambda event: self.move_down_scrollbar())
            self.bind("<Home>", lambda event: self.move_top_scrollbar())
            self.bind("<End>", lambda event: self.move_bottom_scrollbar())
            self.bind("<Control-s>", lambda event: self.download_enrolled_classes_as_pdf(
                self.enrolled_classes_data, self.enrolled_classes_credits))
            self.bind("<Control-S>", lambda event: self.download_enrolled_classes_as_pdf(
                self.enrolled_classes_data, self.enrolled_classes_credits))
            self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_menu())
            self.my_classes_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.title_my_classes.bind("<Button-1>", lambda event: self.focus_set())
            self.modify_classes_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.total_credits_label.bind("<Button-1>", lambda event: self.focus_set())
        self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
        self.my_classes_frame.scroll_to_top()

    def modify_enrolled_classes(self, mod, row_index):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        entry = self.change_section_entries[row_index]
        self.focus_set()
        if entry is not None:
            if mod == translation["section"]:
                entry.configure(state="normal")
            elif mod == translation["drop"] or mod == translation["choose"]:
                if entry.get().strip() == "":
                    entry._activate_placeholder()
                entry.configure(state="disabled")

    def submit_modify_classes_handler(self):
        if self.countdown_running:
            return

        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.focus_set()
        msg = CTkMessagebox(title=translation["submit"], message=translation["submit_modify"],
                            icon=TeraTermUI.get_absolute_path("images/submit.png"), option_1=translation["option_1"],
                            option_2=translation["option_2"], option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            task_done = threading.Event()
            loading_screen = self.show_loading_screen()
            self.update_loading_screen(loading_screen, task_done)
            self.thread_pool.submit(self.submit_modify_classes, task_done=task_done)

    def submit_modify_classes(self, task_done):
        with self.lock_thread:
            try:
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                dialog_input = self.dialog_input.upper().replace(" ", "")
                show_error = False
                first_loop = True
                section_closed = False
                co_requisite = False
                if asyncio.run(self.test_connection(lang)) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        section_pattern = True
                        not_all_choose = False
                        edge_cases_bool = False
                        edge_cases_classes = ["FISI3011", "FISI3013", "FISI3012", "FISI3014", "BIOL3011", "BIOL3013",
                                              "BIOL3012", "BIOL3014", "QUIM3001", "QUIM3003", "QUIM3002", "QUIM3004"]
                        edge_cases_classes_met = []
                        for row_index in range(len(self.enrolled_classes_data)):
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
                                    self.after(0, change_section_entry.configure(border_color="#c30101"))
                                if mod != translation["choose"] and course_code_no_section in edge_cases_classes:
                                    edge_cases_bool = True
                                    edge_cases_classes_met.append(course_code_no_section)
                                    self.after(0, change_section_entry.configure(border_color="#c30101"))
                        if not_all_choose and section_pattern and not edge_cases_bool:
                            self.wait_for_window()
                            self.uprb.UprbayTeraTermVt.type_keys("SRM")
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.uprb.UprbayTeraTermVt.type_keys("1S4")
                            self.uprb.UprbayTeraTermVt.type_keys(dialog_input)
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            text_output = self.capture_screenshot()
                            enrolled_classes = "ENROLLED"
                            count_enroll = text_output.count(enrolled_classes)
                            if "OUTDATED" not in text_output and "INVALID TERM SELECTION" not in text_output and \
                                    "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" \
                                    not in text_output and "ENTER REGISTRATION" in text_output:
                                for row_index in range(len(self.enrolled_classes_data)):
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
                                            time.sleep(2)
                                            text_output = self.capture_screenshot()
                                            enrolled_classes = "ENROLLED"
                                            count_enroll = text_output.count(enrolled_classes)
                                        first_loop = False
                                        self.uprb.UprbayTeraTermVt.type_keys("{TAB 3}")
                                        for i in range(count_enroll, 0, -1):
                                            self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}")
                                        self.uprb.UprbayTeraTermVt.type_keys("D")
                                        self.uprb.UprbayTeraTermVt.type_keys(course_code)
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        self.reset_activity_timer()
                                        text_output = self.capture_screenshot()
                                        if "REQUIRED CO-REQUISITE" in text_output:
                                            co_requisite = True
                                        else:
                                            if old_section in self.classes_status:
                                                self.classes_status.pop(old_section)
                                            self.classes_status[old_section] = {
                                                "classes": course_code_no_section, "status": "DROPPED",
                                                "semester": dialog_input}
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER 2}")
                                        self.reset_activity_timer()
                                        if mod == translation["section"]:
                                            text_output = self.capture_screenshot()
                                            enrolled_classes = "ENROLLED"
                                            count_enroll = text_output.count(enrolled_classes)
                                            self.uprb.UprbayTeraTermVt.type_keys("{TAB 3}")
                                            for i in range(count_enroll, 0, -1):
                                                self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}")
                                            self.uprb.UprbayTeraTermVt.type_keys("R")
                                            self.uprb.UprbayTeraTermVt.type_keys(course_code_no_section)
                                            self.uprb.UprbayTeraTermVt.type_keys(section)
                                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                            self.reset_activity_timer()
                                            text_output = self.capture_screenshot()
                                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                            self.reset_activity_timer()
                                            if "INVALID COURSE ID" in text_output or "COURSE CLOSED" in text_output or \
                                                    "R/TC" in text_output or "Closed by Spec-Prog" in text_output or \
                                                    "COURSE RESERVED" in text_output:
                                                show_error = True
                                                text_output = self.capture_screenshot()
                                                enrolled_classes = "ENROLLED"
                                                count_enroll = text_output.count(enrolled_classes)
                                                self.uprb.UprbayTeraTermVt.type_keys("{TAB 3}")
                                                for i in range(count_enroll, 0, -1):
                                                    self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}")
                                                self.uprb.UprbayTeraTermVt.type_keys("R")
                                                self.uprb.UprbayTeraTermVt.type_keys(course_code)
                                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                                self.reset_activity_timer()
                                                text_output = self.capture_screenshot()
                                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                                self.reset_activity_timer()
                                                if "COURSE CLOSED" in text_output:
                                                    section_closed = True
                                                    if old_section in self.classes_status:
                                                        self.classes_status.pop(old_section)
                                                    self.classes_status[old_section] = {
                                                        "classes": course_code_no_section, "status": "DROPPED",
                                                        "semester": dialog_input}
                                                else:
                                                    if old_section in self.classes_status:
                                                        self.classes_status.pop(old_section)
                                                    self.classes_status[old_section] = {
                                                        "classes": course_code_no_section, "status": "ENROLLED",
                                                        "semester": dialog_input}
                                            else:
                                                if old_section in self.classes_status:
                                                    self.classes_status.pop(old_section)
                                                self.classes_status[old_section] = {
                                                    "classes": course_code_no_section, "status": "ENROLLED",
                                                    "semester": dialog_input}
                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                self.reset_activity_timer()
                                text_output = self.wait_for_response(["CONFIRMED", "DROPPED"], timeout=1.5)
                                if "CONFIRMED" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                if "DROPPED" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                try:
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.uprb.UprbayTeraTermVt.type_keys("1CP")
                                    self.uprb.UprbayTeraTermVt.type_keys(dialog_input)
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.reset_activity_timer()
                                    clipboard_content = None
                                    try:
                                        clipboard_content = self.clipboard_get()
                                    except tk.TclError:
                                        pass
                                        # print("Clipboard contains non-text data, possibly an image or other formats")
                                    except Exception as err:
                                        print("Error handling clipboard content:", err)
                                        self.log_error()
                                    time.sleep(1)
                                    TeraTermUI.disable_user_input()
                                    self.automate_copy_class_data()
                                    TeraTermUI.disable_user_input("on")
                                    copy = pyperclip.paste()
                                    enrolled_classes, total_credits = self.extract_my_enrolled_classes(copy)
                                    self.after(0, self.display_enrolled_data, enrolled_classes,
                                               total_credits, dialog_input)
                                    self.clipboard_clear()
                                    if clipboard_content is not None:
                                        self.clipboard_append(clipboard_content)
                                    time.sleep(1)
                                except Exception as err:
                                    print("An error occurred: ", err)
                                    self.go_back_menu()
                                if show_error and not section_closed:
                                    self.after(100, self.show_error_message, 320, 240,
                                               translation["failed_change_section"])

                                    def explanation():
                                        self.destroy_windows()
                                        if self.enrolled_classes_table is not None:
                                            self.after(350, self.bind, "<Return>",
                                                       lambda event: self.submit_modify_classes_handler())
                                            self.submit_my_classes.configure(state="normal")
                                        self.not_rebind = False
                                        if not self.disable_audio:
                                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"),
                                                               winsound.SND_ASYNC)
                                        CTkMessagebox(title=translation["automation_error_title"], icon="cancel",
                                                      message=translation["failed_change_section_exp"],
                                                      button_width=380)

                                    self.unbind("<Return>")
                                    self.submit_my_classes.configure(state="disabled")
                                    self.not_rebind = True
                                    self.after(3000, explanation)
                                elif section_closed:
                                    self.after(100, self.show_error_message, 320, 240,
                                               translation["failed_change_section"])

                                    def explanation():
                                        self.destroy_windows()
                                        if self.enrolled_classes_table is not None:
                                            self.after(350, self.bind, "<Return>",
                                                       lambda event: self.submit_modify_classes_handler())
                                            self.submit_my_classes.configure(state="normal")
                                        self.not_rebind = False
                                        if not self.disable_audio:
                                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"),
                                                               winsound.SND_ASYNC)
                                        CTkMessagebox(title=translation["automation_error_title"], icon="cancel",
                                                      message=translation["section_closed"], button_width=380)

                                    self.unbind("<Return>")
                                    self.submit_my_classes.configure(state="disabled")
                                    self.not_rebind = True
                                    self.after(3000, explanation)

                                elif co_requisite:
                                    self.after(100, self.show_error_message, 320, 240,
                                               translation["failed_change_section"])

                                    def explanation():
                                        self.destroy_windows()
                                        if self.enrolled_classes_table is not None:
                                            self.after(350, self.bind, "<Return>",
                                                       lambda event: self.submit_modify_classes_handler())
                                            self.submit_my_classes.configure(state="normal")
                                        self.not_rebind = False
                                        if not self.disable_audio:
                                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"),
                                                               winsound.SND_ASYNC)
                                        CTkMessagebox(title=translation["automation_error_title"], icon="cancel",
                                                      message=translation["co_requisite"], button_width=380)

                                    self.unbind("<Return>")
                                    self.submit_my_classes.configure(state="disabled")
                                    self.not_rebind = True
                                    self.after(3000, explanation)

                                else:
                                    self.after(100, self.show_success_message, 350, 265,
                                               translation["success_modify"])
                            else:
                                if "INVALID TERM SELECTION" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                    self.reset_activity_timer()
                                    self.after(100, self.show_error_message, 300, 215,
                                               translation["invalid_semester"])
                                else:
                                    if "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" \
                                            not in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                        self.reset_activity_timer()
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
                                        winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"),
                                                           winsound.SND_ASYNC)
                                    edge_case_classes_str = ", ".join(edge_cases_classes_met)
                                    CTkMessagebox(title=translation["automation_error_title"], icon="warning",
                                                  message=translation["co_requisite_warning"] + edge_case_classes_str,
                                                  button_width=380)

                                self.after(125, explanation)
                    else:
                        self.after(100, self.show_error_message, 300, 215, translation["tera_term_not_running"])
            except Exception as err:
                print("An error occurred: ", err)
                self.error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                               winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False

                    self.after(50, error_automation)
                if not self.not_rebind:
                    self.after(350, self.bind, "<Return>", lambda event: self.submit_modify_classes_handler())
                TeraTermUI.disable_user_input()

    # checks whether the program can continue its normal execution or if the server is on maintenance
    def wait_for_prompt(self, prompt_text, maintenance_text, timeout=15):
        time.sleep(1)
        start_time = time.time()
        while True:
            text_output = self.capture_screenshot()
            if maintenance_text in text_output:  # Prioritize the maintenance message
                return "Maintenance message found"
            elif prompt_text in text_output:
                return "Prompt found"
            elif time.time() - start_time > timeout:
                return "Timeout"
            time.sleep(0.5)  # Adjust the delay between screenshots as needed

    def wait_for_response(self, keywords, init_timeout=True, timeout=3.0):
        if init_timeout:
            time.sleep(1)
        start_time = time.time()
        last_text_output = ""
        while time.time() - start_time <= timeout:
            text_output = self.capture_screenshot()
            for keyword in keywords:
                if keyword in text_output:
                    return text_output
            last_text_output = text_output
            time.sleep(0.5)

        return last_text_output

    def wait_for_window(self):
        try:
            self.uprbay_window.wait("visible", timeout=3)
            self.focus_tera_term()
            if self.went_to_1PL_screen and self.run_fix:
                self.uprb.UprbayTeraTermVt.type_keys("X")
                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                self.went_to_1PL_screen = False
            elif self.went_to_683_screen and self.run_fix:
                self.uprb.UprbayTeraTermVt.type_keys("00")
                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                self.went_to_683_screen = False
        except Exception as err:
            print("An error occurred: ", err)
            self.search_function_counter = 0
            self.e_counter = 0
            self.m_counter = 0
            self.classes_status.clear()
            self.connect_to_uprb()
            if not TeraTermUI.window_exists("SSH Authentication") and \
                    not TeraTermUI.window_exists("Tera Term - [disconnected] VT"):
                text_output = self.capture_screenshot()
                to_continue = "return to continue"
                count_to_continue = text_output.count(to_continue)
                if "return to continue" in text_output or "INFORMACION ESTUDIANTIL" in text_output:
                    if "return to continue" in text_output and "Loading" in text_output:
                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER 3}")
                    elif count_to_continue == 2 or "ZZZ" in text_output:
                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER 2}")
                    elif count_to_continue == 1 or "automaticamente" in text_output:
                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                    else:
                        self.uprb.UprbayTeraTermVt.type_keys("{VK_RIGHT}")
                        self.uprb.UprbayTeraTermVt.type_keys("{VK_LEFT}")
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
        self.future_tesseract = self.thread_pool.submit(self.setup_tesseract)
        self.future_backup = self.thread_pool.submit(self.backup_and_config_ini, file_path)
        self.future_feedback = self.thread_pool.submit(self.setup_feedback)

    def setup_tesseract(self):
        unzip_tesseract = True
        tesseract_dir_path = self.app_temp_dir / "Tesseract-OCR"
        default_tesseract_path = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")

        def get_tesseract_version(location):
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                output = subprocess.check_output([location, "--version"], stderr=subprocess.STDOUT,
                                                 startupinfo=startupinfo)
                version_info = output.decode("utf-8")
                version_line = version_info.split("\n")[0]
                version_number = version_line.split()[1].lstrip("v")
                return version_number
            except subprocess.CalledProcessError:
                return None
            except FileNotFoundError:
                return None

        # Check if Tesseract is installed in the default location
        if default_tesseract_path.is_file():
            installed_version = get_tesseract_version(str(default_tesseract_path))
            if installed_version and tuple(map(int, installed_version.split("."))) >= (5, 0, 0):
                pytesseract.pytesseract.tesseract_cmd = str(default_tesseract_path)
                unzip_tesseract = False
                self.tesseract_unzipped = True
        # If Tesseract-OCR already in the temp folder don't unzip
        elif tesseract_dir_path.is_dir():
            tesseract_dir = tesseract_dir_path
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_dir / "tesseract.exe")
            unzip_tesseract = False
            self.tesseract_unzipped = True
        # Unzips Tesseract OCR
        if unzip_tesseract:
            try:
                with SevenZipFile(self.zip_path, mode="r") as z:
                    z.extractall(self.app_temp_dir)
                tesseract_dir = Path(self.app_temp_dir) / "Tesseract-OCR"
                pytesseract.pytesseract.tesseract_cmd = str(tesseract_dir / "tesseract.exe")
                # tessdata_dir_config = f"--tessdata-dir {tesseract_dir / 'tessdata'}"
                self.tesseract_unzipped = True
                del tesseract_dir_path, tesseract_dir
                gc.collect()
            except Exception as err:
                SPANISH = 0x0A
                language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                print(f"Error occurred during unzipping: {str(err)}")
                self.tesseract_unzipped = False
                self.log_error()
                if "[Errno 2] No such file or directory" in str(err):
                    if language_id & 0xFF == SPANISH:
                        messagebox.showerror("Error", f"¡Error Fatal!\n\n{str(err)}")
                    else:
                        messagebox.showerror("Error", f"Fatal Error!\n\n{str(err)}")
                    self.after(0, self.forceful_end_app)

    @staticmethod
    def find_appdata_teraterm_ini():
        appdata_path = os.path.join(os.environ.get("APPDATA", ""), "teraterm5")
        teraterm_ini_path = os.path.join(appdata_path, "TERATERM.ini")
        if os.path.isfile(teraterm_ini_path):
            return teraterm_ini_path
        return None

    def backup_and_config_ini(self, file_path):
        if "teraterm5" in file_path:
            appdata_ini_path = TeraTermUI.find_appdata_teraterm_ini()
            if appdata_ini_path:
                file_path = appdata_ini_path
            else:
                self.teraterm5_first_boot = True
                return

        # backup for config file of tera term
        if TeraTermUI.is_file_in_directory("ttermpro.exe", self.teraterm_directory):
            backup_path = self.app_temp_dir / "TERATERM.ini.bak"
            if not os.path.exists(backup_path):
                backup_path = os.path.join(self.app_temp_dir, os.path.basename(file_path) + ".bak")
                try:
                    shutil.copyfile(file_path, backup_path)
                except FileNotFoundError:
                    self.log_error()
                    print("Tera Term Probably not installed\n"
                          "or installed in a different location from the default")

            # Edits the font that tera term uses to "Lucida Console" to mitigate the chance of the OCR mistaking words
            if not self.can_edit:
                try:
                    with open(file_path, "rb") as file:
                        raw_data = file.read()
                        encoding_info = chardet_detect(raw_data)
                        detected_encoding = encoding_info["encoding"]

                    with open(file_path, "r", encoding=detected_encoding) as file:
                        lines = file.readlines()
                    for index, line in enumerate(lines):
                        if line.startswith("VTFont="):
                            current_value = line.strip().split("=")[1]
                            font_name = current_value.split(",")[0]
                            self.original_font = current_value
                            updated_value = "Lucida Console" + current_value[len(font_name):]
                            lines[index] = f"VTFont={updated_value}\n"
                        if line.startswith("VTColor=") and not line.startswith(";"):
                            current_value = line.strip().split("=")[1]
                            if current_value != "255,255,255,0,0,0":
                                self.original_color = current_value
                                lines[index] = "VTColor=255,255,255,0,0,0\n"
                        if line.startswith("AuthBanner="):
                            current_value = line.strip().split("=")[1]
                            if current_value not in ["0", "1"]:
                                lines[index] = "AuthBanner=1\n"
                        self.can_edit = True
                    with open(file_path, "w", encoding=detected_encoding) as file:
                        file.writelines(lines)
                    del line, lines
                except FileNotFoundError:
                    return
                except IOError as err:
                    print(f"Error occurred: {err}")
                    print("Restoring from backup...")
                    shutil.copyfile(backup_path, file_path)
                del backup_path

        else:
            self.teraterm_not_found = True

    @staticmethod
    def purkaa_reazione(scrambled_parts):
        original_parts = []
        ascii_to_remove = [106, 97, 49]
        for i, part in enumerate(scrambled_parts):
            for ascii_code in ascii_to_remove:
                part = part.replace(chr(ascii_code), "")
            char_list = list(part)
            original_order = list(range(len(char_list)))
            random.seed(i)
            random.shuffle(original_order)
            original_order = sorted(range(len(original_order)), key=lambda k: original_order[k])
            unscrambled_part = "".join(char_list[i] for i in original_order)
            original_parts.append(unscrambled_part)
        return "".join(original_parts)

    def setup_feedback(self):
        from google.oauth2 import service_account
        from pyzipper import AESZipFile

        # Reads from the feedback.json file to connect to Google's Sheets Api for user feedback
        try:
            with open(self.SERVICE_ACCOUNT_FILE, "rb"):
                archive = AESZipFile(self.SERVICE_ACCOUNT_FILE)
                archive.setpassword(self.REAZIONE.encode())
                file_contents = archive.read("feedback.json")
                credentials_dict = json.loads(file_contents.decode())
                self.credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
                del credentials_dict
        except Exception as err:
            print(f"Failed to load credentials: {str(err)}")
            self.log_error()
            self.credentials = None
            self.disable_feedback = True
        finally:
            if hasattr(self, "REAZIONE"):
                del self.REAZIONE
            os.environ.pop("REAZIONE", None)

    def update_app(self, latest_version):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        current = None
        latest = None
        if lang == "English":
            current = "Current"
            latest = "Latest"
        elif lang == "Español":
            current = "Actual"
            latest = "Nueva"
        if not self.disable_audio:
            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/update.wav"), winsound.SND_ASYNC)
        msg = CTkMessagebox(title=translation["update_popup_title"],
                            message=translation["update_popup_message"] + "\n\n" + current + ": v" +
                            self.USER_APP_VERSION + " ---> " + latest + ": v" + latest_version,
                            option_1=translation["option_1"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"), icon="question",
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            try:
                updater_exe_dest = None
                sys_path = Path(sys.path[0]).resolve()
                if self.mode == "Portable":
                    updater_exe_src = Path(sys.path[0]) / "updater.exe"
                    updater_exe_dest = Path(self.app_temp_dir) / "updater.exe"
                    shutil.copy2(str(updater_exe_src), str(updater_exe_dest))
                elif self.mode == "Installation":
                    appdata_path = os.environ.get("PROGRAMDATA")
                    updater_exe_dest = os.path.join(appdata_path, "TeraTermUI", "updater.exe")
                updater_args = [str(updater_exe_dest), self.mode, latest_version,
                                str(self.update_db), sys_path]
                subprocess.run(updater_args)
                self.direct_close()
            except Exception as err:
                print(f"Failed to launch the updater script: {err}")
                self.log_error()
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
                    time.sleep(0.5)  # Wait for half a second before the next attempt
        # Delete the 'TERATERM.ini.bak' file
        if backup_file_path.exists() and not TeraTermUI.checkIfProcessRunning("ttermpro"):
            os.remove(backup_file_path)
            shutil.rmtree(self.app_temp_dir)

    # error window pop up message
    def show_error_message(self, width, height, error_msg_text):
        if self.error is not None and self.error.winfo_exists():
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
            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"), winsound.SND_ASYNC)
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
        if self.success is not None and self.success.winfo_exists():
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
            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/success.wav"), winsound.SND_ASYNC)
        self.success = SmoothFadeToplevel(fade_duration=10)
        self.success.title(translation["success_title"])
        self.success.geometry(window_geometry)
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
        if self.help is not None and self.help.winfo_exists() and self.changed_location:
            self.after(250, self.help.lift)
            self.after(250, self.help.focus_set)
            self.after(250, self.files.configure(state="normal"))
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
                winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"), winsound.SND_ASYNC)
            CTkMessagebox(title=translation["automation_error_title"], icon="cancel",
                          message=translation["specific_enrollment_error"] + error_message_str, button_width=380)
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
                winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"), winsound.SND_ASYNC)
            CTkMessagebox(title=translation["automation_error_title"], message=translation["enrollment_error"],
                          button_width=380)

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
                    winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"), winsound.SND_ASYNC)
                CTkMessagebox(title=translation["automation_error_title"], icon="cancel",
                              message=translation["specific_enrollment_error"] + error_message_str, button_width=380)
                for counter in range(self.a_counter + 1, 0, -1):
                    if self.classes_status:
                        last_item = list(self.classes_status.keys())[-1]
                        self.classes_status.pop(last_item)

            self.after(3000, explanation)
        if not found_errors and text != "Error":
            for i in range(self.a_counter + 1):
                self.m_classes_entry[i].delete(0, "end")
                self.m_section_entry[i].delete(0, "end")
                self.m_classes_entry[i].configure(
                    placeholder_text=self.placeholder_texts_classes[i])
                self.m_section_entry[i].configure(
                    placeholder_text=self.placeholder_texts_sections[i])
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
                    winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"), winsound.SND_ASYNC)
                CTkMessagebox(title=translation["automation_error_title"], message=translation["enrollment_error"],
                              button_width=380)

            self.after(3000, explanation)

    def show_modify_classes_information(self):
        self.destroy_windows()
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.modify_error_check:
            if self.enrolled_classes_table is not None:
                self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
                self.submit_my_classes.configure(state="normal")
            self.not_rebind = False
            if not self.disable_audio:
                winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"), winsound.SND_ASYNC)
            CTkMessagebox(title=translation["automation_error_title"], message=translation["modify_error"],
                          button_width=380)

    # important information window pop up message
    def show_information_message(self, width, height, success_msg_text):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if self.information is not None and self.information.winfo_exists():
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
            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"), winsound.SND_ASYNC)
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

    @staticmethod
    def check_and_update_border_color(container):
        stack = [container]
        while stack:
            current_container = stack.pop()
            for widget in current_container.winfo_children():
                if widget.winfo_viewable():
                    if isinstance(widget, (CustomEntry, CustomComboBox)):
                        current_color = widget.cget("border_color")
                        if current_color == "#c30101" or current_color == "#CC5500":
                            widget.border_color = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"]
                            widget.configure(border_color=widget.border_color)
                    elif isinstance(widget, customtkinter.CTkOptionMenu):
                        current_color = widget.cget("button_color")
                        if current_color == "#c30101":
                            widget.button_color = customtkinter.ThemeManager.theme["CTkOptionMenu"]["button_color"]
                            widget.configure(button_color=widget.button_color)
                if hasattr(widget, "winfo_children"):
                    stack.append(widget)

    @staticmethod
    def disable_user_input(state="off"):
        if TeraTermUI.is_admin():
            if state == "on":
                ctypes.windll.user32.BlockInput(True)
            elif state == "off":
                ctypes.windll.user32.BlockInput(False)

    def automation_preparations(self):
        self.focus_set()
        self.destroy_windows()
        self.unbind("<Return>")
        TeraTermUI.check_and_update_border_color(self)
        self.destroy_tooltip()
        TeraTermUI.disable_user_input("on")

    # function that changes the theme of the application
    def change_appearance_mode_event(self, new_appearance_mode: str):
        if new_appearance_mode == "Oscuro":
            new_appearance_mode = "Dark"
        elif new_appearance_mode == "Claro":
            new_appearance_mode = "Light"
        elif new_appearance_mode == "Sistema":
            new_appearance_mode = "System"

        if new_appearance_mode == self.curr_appearance:
            return

        self.focus_set()
        customtkinter.set_appearance_mode(new_appearance_mode)
        self.curr_appearance = new_appearance_mode

    def add_key_bindings(self, event):
        if self.in_search_frame:
            if len(self.class_table_pairs) > 1:
                self.bind("<Left>", self.keybind_previous_table)
                self.bind("<Right>", self.keybind_next_table)
        else:
            self.bind("<Left>", self.move_slider_left)
            self.bind("<Right>", self.move_slider_right)

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
        if self.in_student_frame:
            show = self.show.get()
            if show == "on":
                self.show.deselect()
            elif show == "off":
                self.show.select()
            self.show_event()
            self.show._on_enter()
        elif self.in_enroll_frame:
            choice = self.radio_var.get()
            if choice == "register":
                self.drop.select()
                self.drop._on_enter()
            elif choice == "drop":
                self.register.select()
                self.register._on_enter()
        elif self.in_search_frame:
            check = self.show_all.get()
            if check == "on":
                self.show_all.deselect()
            elif check == "off":
                self.show_all.select()
            self.show_all._on_enter()

    # function that lets your increase/decrease the scaling of the GUI
    def change_scaling_event(self, new_scaling: float):
        new_scaling_float = new_scaling / 100
        if new_scaling_float == self.curr_scaling:
            return

        self.focus_set()
        self.scaling_tooltip.hide()
        customtkinter.set_widget_scaling(new_scaling_float)
        self.scaling_tooltip.configure(message=f"{new_scaling}%")
        self.curr_scaling = new_scaling_float
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
            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"), winsound.SND_ASYNC)
        msg = CTkMessagebox(title=translation["download_title"], message=translation["download_tera_term"],
                            icon="question", option_1=translation["option_1"], option_2=translation["option_2"],
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
        self.thread_pool.submit(self.check_update_app, task_done=task_done)

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
                    if not self.disable_audio:
                        winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"), winsound.SND_ASYNC)
                    CTkMessagebox(title=translation["error"], icon="cancel",
                                  message=translation["failed_to_find_update"], button_width=380)

                self.after(50, error)
                return
            if not TeraTermUI.compare_versions(latest_version, self.USER_APP_VERSION):
                task_done.set()

                def update():
                    current = None
                    latest = None
                    if lang == "English":
                        current = "Current"
                        latest = "Latest"
                    elif lang == "Español":
                        current = "Actual"
                        latest = "Nueva"
                    if not self.disable_audio:
                        winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/update.wav"), winsound.SND_ASYNC)
                    msg = CTkMessagebox(title=translation["update_popup_title"],
                                        message=translation["update_popup_message"] + "\n\n" + current + ": v" +
                                        self.USER_APP_VERSION + " ---> " + latest + ": v" + latest_version,
                                        option_1=translation["option_1"], option_2=translation["option_2"],
                                        option_3=translation["option_3"], icon_size=(65, 65),
                                        button_color=("#c30101", "#145DA0", "#145DA0"), icon="question",
                                        hover_color=("darkred", "use_default", "use_default"))
                    response = msg.get()
                    if response[0] == "Yes" or response[0] == "Sí":
                        try:
                            updater_exe_dest = None
                            sys_path = Path(sys.path[0]).resolve()
                            if self.mode == "Portable":
                                updater_exe_src = Path(sys.path[0]) / "updater.exe"
                                updater_exe_dest = Path(self.app_temp_dir) / "updater.exe"
                                shutil.copy2(str(updater_exe_src), str(updater_exe_dest))
                            elif self.mode == "Installation":
                                appdata_path = os.environ.get("PROGRAMDATA")
                                updater_exe_dest = os.path.join(appdata_path, "TeraTermUI", "updater.exe")
                            updater_args = [str(updater_exe_dest), self.mode, latest_version,
                                            str(self.update_db), sys_path]
                            subprocess.run(updater_args)
                            self.direct_close()
                        except Exception as err:
                            print(f"Failed to launch the updater script: {err}")
                            self.log_error()
                            webbrowser.open("https://github.com/Hanuwa/TeraTermUI/releases/latest")

                self.after(50, update)
            else:
                task_done.set()

                def up_to_date():
                    if not self.disable_audio:
                        winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                           winsound.SND_ASYNC)
                    CTkMessagebox(title=translation["update_popup_title"], message=translation["update_up_to_date"],
                                  button_width=380)

                self.after(50, up_to_date)
        else:
            self.updating_app = False
            task_done.set()

    def fix_execution_event_handler(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        if TeraTermUI.checkIfProcessRunning("ttermpro"):
            msg = CTkMessagebox(title=translation["fix_messagebox_title"],
                                message=translation["fix_messagebox"], icon="warning",
                                option_1=translation["option_1"], option_2=translation["option_2"],
                                option_3=translation["option_3"], icon_size=(65, 65),
                                button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "use_default", "use_default"))
            response = msg.get()
            if response[0] == "Yes" or response[0] == "Sí":
                task_done = threading.Event()
                loading_screen = self.show_loading_screen()
                self.update_loading_screen(loading_screen, task_done)
                self.thread_pool.submit(self.fix_execution, task_done=task_done)
                self.fix_execution_event_completed = False

    # If user messes up the execution of the program this can solve it and make program work as expected
    def fix_execution(self, task_done):
        with self.lock_thread:
            try:
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                self.automation_preparations()
                self.wait_for_window()
                if self.search_function_counter == 0:
                    text_output = self.capture_screenshot()
                    if "INVALID ACTION" in text_output and "LISTA DE SECCIONES" in text_output:
                        self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}")
                        self.uprb.UprbayTeraTermVt.type_keys("SRM")
                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                        self.reset_activity_timer()
                else:
                    self.uprb.UprbayTeraTermVt.type_keys("{TAB}")
                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                    self.reset_activity_timer()
                text_output = self.capture_screenshot()
                if "INVALID ACTION" in text_output:
                    self.uprb.UprbayTeraTermVt.type_keys("{TAB}")
                    self.uprb.UprbayTeraTermVt.type_keys("SRM")
                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER)
                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                    self.reset_activity_timer()
                elif "PF4" in text_output:
                    self.error_occurred = True
                    self.after(250, self.go_back_home)
                self.classes_status.clear()
                self.cursor.execute("UPDATE user_data SET default_semester=NULL")
                self.connection.commit()
                if not self.error_occurred:
                    self.after(100, self.show_information_message, 370, 250,
                               translation["fix_after"])
            except Exception as err:
                print("An error occurred: ", err)
                error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                lang = self.language_menu.get()
                self.after(100, self.set_focus_to_tkinter)
                self.after(0, self.switch_tab)
                translation = self.load_language(lang)
                if error_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                               winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)

                    self.after(50, error_automation)
                TeraTermUI.disable_user_input()
                self.fix_execution_event_completed = True

    @staticmethod
    def get_device_type():
        try:
            result = subprocess.run(
                ["powershell", "-Command", "(Get-WmiObject -Class Win32_Battery).Status"],
                stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            if "BatteryStatus" in result.stdout:
                return "laptop"
            else:
                return "desktop"
        except Exception as err:
            print(f"Error determining device type: {err}")
            return None

    @staticmethod
    def get_power_timeout():
        def query_timeout(subgroup, setting):
            try:
                result = subprocess.run(
                    ["powercfg", "/query", "SCHEME_CURRENT", subgroup, setting],
                    stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
                output = result.stdout
                ac_match = re.search(r"Current AC Power Setting Index: 0x([0-9a-fA-F]+)", output)
                dc_match = re.search(r"Current DC Power Setting Index: 0x([0-9a-fA-F]+)", output)
                if ac_match and dc_match:
                    ac_setting = int(ac_match.group(1), 16)
                    dc_setting = int(dc_match.group(1), 16)
                    if ac_setting == 0xffffffff and dc_setting == 0xffffffff:
                        return "off"

                    return {
                        "AC Power Setting": ac_setting,
                        "DC Power Setting": dc_setting
                    }
            except Exception as err:
                print(f"Error querying power settings: {err}")
                return None

        power_timeout = (query_timeout("SUB_VIDEO", "VIDEOIDLE") or
                         query_timeout("SUB_SLEEP", "HIBERNATEIDLE"))

        return power_timeout if power_timeout else None

    def stop_check_process_thread(self):
        if not self.stop_check_process.is_set():
            self.stop_check_process.set()
            self.reset_activity_timer()

    def start_check_process_thread(self):
        self.check_process_thread = threading.Thread(target=self.check_process_periodically)
        if self.stop_check_process.is_set():
            self.stop_check_process.clear()
        self.check_process_thread.daemon = True
        self.check_process_thread.start()

    def check_process_periodically(self):
        import pyautogui

        time.sleep(30 + random.uniform(5, 25))
        not_running_count = 0
        power_timeout = TeraTermUI.get_power_timeout()
        device_type = TeraTermUI.get_device_type()
        if power_timeout is None:
            threshold = 120
        elif power_timeout == "off":
            threshold = None
        else:
            if device_type == "laptop":
                threshold = power_timeout["DC Power Setting"] * 1 / 4
            elif device_type == "desktop":
                threshold = power_timeout["AC Power Setting"] * 1 / 4
            else:
                threshold = 120
        pyautogui.FAILSAFE = False
        while not self.stop_check_process.is_set():
            try:
                idle = self.cursor.execute("SELECT idle FROM user_data").fetchone()
            except Exception as err:
                idle = ["Disabled"]
                print("An error occurred: ", err)
                self.log_error()
            if self.loading_screen_status is None and idle[0] != "Disabled":
                if threshold is not None:
                    idle_time = get_idle_duration()
                    if idle_time >= threshold:
                        ES_DISPLAY_REQUIRED = 0x00000002
                        ctypes.windll.kernel32.SetThreadExecutionState(ES_DISPLAY_REQUIRED)
                        pyautogui.press("scrolllock")
                        time.sleep(1)
                        pyautogui.press("scrolllock")
                is_running = TeraTermUI.checkIfProcessRunning("ttermpro")
                if is_running:
                    if not_running_count > 1 and self.stop_check_idle.is_set():
                        self.start_check_idle_thread()
                    not_running_count = 0
                else:
                    not_running_count += 1
                    if not_running_count == 1:
                        lang = self.language_menu.get()
                        translation = self.load_language(lang)

                        def not_running():
                            if not self.disable_audio:
                                winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/notification.wav"),
                                                   winsound.SND_ASYNC)
                            CTkMessagebox(title=translation["automation_error_title"], icon="warning",
                                          message=translation["tera_term_stopped_running"], button_width=380)

                        self.after(50, not_running)
                    if not_running_count > 1:
                        self.stop_check_process_thread()
            time.sleep(30 + random.uniform(5, 15))

    def stop_check_idle_thread(self):
        if not self.stop_check_idle.is_set():
            self.stop_check_idle.set()
            self.reset_activity_timer()

    # Starts the check for idle thread
    def start_check_idle_thread(self):
        idle = self.cursor.execute("SELECT idle FROM user_data").fetchone()
        if idle[0] != "Disabled":
            self.check_idle_thread = threading.Thread(target=self.check_idle)
            if self.stop_check_idle.is_set():
                self.stop_check_idle.clear()
            self.check_idle_thread.daemon = True
            self.check_idle_thread.start()

    # Checks if the user is idle for 5 minutes and does some action so that Tera Term doesn't close by itself
    def check_idle(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.idle_num_check = 0
        self.last_activity = time.time()
        try:
            while not self.stop_check_idle.is_set():
                if time.time() - self.last_activity >= 210:
                    with self.lock_thread:
                        if TeraTermUI.checkIfProcessRunning("ttermpro"):
                            lang = self.language_menu.get()
                            translation = self.load_language(lang)
                            if TeraTermUI.window_exists(translation["idle_warning_title"]):
                                self.idle_warning.close_messagebox()
                            self.keep_teraterm_open()
                            self.last_activity = time.time()
                            if not self.countdown_running:
                                self.idle_num_check += 1
                            if self.countdown_running:
                                self.idle_num_check = 1
                            if self.idle_num_check == 32:
                                def idle_warning():
                                    if not self.disable_audio:
                                        winsound.PlaySound(
                                            TeraTermUI.get_absolute_path("sounds/notification.wav"), winsound.SND_ASYNC)
                                    self.idle_warning = CTkMessagebox(
                                        title=translation["idle_warning_title"], message=translation["idle_warning"],
                                        button_width=380)
                                    response = self.idle_warning.get()[0]
                                    if response == "OK":
                                        self.idle_num_check = 0

                                self.after(50, idle_warning)
                        else:
                            self.stop_check_idle_thread()
                if self.idle_num_check == 33:
                    self.stop_check_idle_thread()
                time.sleep(30)
        except Exception as err:
            print("An error occurred: ", err)
            self.log_error()

    def keep_teraterm_open(self):
        try:
            main_window = self.uprb_32.window(title="uprbay.uprb.edu - Tera Term VT")
            main_window.wait("exists", 3)
        except Exception as err:
            print("An error occurred: ", err)
            self.search_function_counter = 0
            self.uprb = Application(backend="uia").connect(
                title="uprbay.uprb.edu - Tera Term VT", timeout=3, class_name="VTWin32",
                control_type="Window")
            self.uprb_32 = Application().connect(
                title="uprbay.uprb.edu - Tera Term VT", timeout=3, class_name="VTWin32")
            self.uprbay_window = self.uprb.window(
                title="uprbay.uprb.edu - Tera Term VT", class_name="VTWin32", control_type="Window")
            main_window = self.uprb_32.window(
                title="uprbay.uprb.edu - Tera Term VT", class_name="VTWin32")
            edit_menu = self.uprb.UprbayTeraTermVt.child_window(
                title="Edit", control_type="MenuItem")
            self.select_screen_item = edit_menu.child_window(
                title="Select screen", control_type="MenuItem", auto_id="50280")
            self.tera_term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
            if self.state() != "withdrawn":
                self.move_window()
        main_window.send_keystrokes("{VK_RIGHT}")
        main_window.send_keystrokes("{VK_LEFT}")

    # resets the idle timer when user interacts with something within the application
    def reset_activity_timer(self):
        self.last_activity = time.time()
        self.idle_num_check = 0

    def keybind_disable_enable_idle(self):
        if self.disable_idle.get() == "on":
            self.disable_idle.deselect()
        elif self.disable_idle.get() == "off":
            self.disable_idle.select()
        self.disable_enable_idle()

    # Disables check_idle functionality
    def disable_enable_idle(self):
        row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
        if self.disable_idle.get() == "on":
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (idle) VALUES (?)", ("Disabled",))
            else:
                self.cursor.execute("UPDATE user_data SET idle=?", ("Disabled",))
            self.stop_check_idle_thread()
        elif self.disable_idle.get() == "off":
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (idle) VALUES (?)", ("Enabled",))
            else:
                self.cursor.execute("UPDATE user_data SET idle=?", ("Enabled",))
            if self.auto_enroll is not None:
                self.auto_enroll.configure(state="normal")
            if self.run_fix and TeraTermUI.checkIfProcessRunning("ttermpro"):
                self.start_check_idle_thread()
                self.keep_teraterm_open()
                self.reset_activity_timer()
        self.connection.commit()

    def keybind_disable_enable_audio(self):
        if self.disable_audio_val.get() == "on":
            self.disable_audio_val.deselect()
        elif self.disable_audio_val.get() == "off":
            self.disable_audio_val.select()
        self.disable_enable_audio()

    def disable_enable_audio(self):
        row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
        if self.disable_audio_val.get() == "on":
            self.set_beep_sound(self.teraterm_file)
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (audio) VALUES (?)", ("Disabled",))
            else:
                self.cursor.execute("UPDATE user_data SET audio=?", ("Disabled",))
            if not self.disable_audio:
                self.disable_audio = True
        elif self.disable_audio_val.get() == "off":
            self.set_beep_sound(self.teraterm_file, False)
            if not row_exists:
                self.cursor.execute("INSERT INTO user_data (audio) VALUES (?)", ("Enabled",))
            else:
                self.cursor.execute("UPDATE user_data SET audio=?", ("Enabled",))
            if self.disable_audio:
                self.disable_audio = False
        self.connection.commit()

    @staticmethod
    async def fetch(session, url):
        from aiohttp import ClientConnectionError

        try:
            async with session.get(url, timeout=5.0) as response:
                if response.status != 200:
                    print(f"Non-200 response code: {response.status}")
                    return False
                return True
        except ClientConnectionError:
            print(f"Failed to connect to {url}")
            return False
        except asyncio.TimeoutError:
            print(f"Request to {url} timed out")
            return False
        except Exception as err:
            print(f"An unexpected error occurred: {err}")
            return False

    async def test_connection(self, lang):
        from aiohttp import ClientSession, TCPConnector

        translation = self.load_language(lang)
        urls = ["https://www.google.com/", "https://www.bing.com/", "https://www.yahoo.com/"]
        async with ClientSession(connector=TCPConnector(limit=3)) as session:
            tasks = [self.fetch(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        connected = any(result for result in results if result is True)
        if not connected:
            if not self.check_update:
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
        if self.error is not None and self.error.winfo_exists():
            self.error.lift()
            self.error.focus_force()
            self.error.attributes("-topmost", 1)
            self.error.after_idle(self.attributes, "-topmost", 0)
        elif self.success is not None and self.success.winfo_exists():
            self.success.focus_set()
        elif self.information is not None and self.information.winfo_exists():
            self.information.lift()
            self.information.focus_force()
            self.information.attributes("-topmost", 1)
            self.information.after_idle(self.attributes, "-topmost", 0)
        elif self.timer_window is not None and self.timer_window.winfo_exists() and self.in_multiple_screen:
            self.timer_window.lift()
            self.timer_window.focus_force()
            self.timer_window.attributes("-topmost", 1)
            self.timer_window.after_idle(self.timer_window.attributes, "-topmost", 0)

    # Set focus on Tera Term window
    def focus_tera_term(self):
        if self.tera_term_window.isMinimized:
            self.tera_term_window.restore()
        try:
            self.tera_term_window.activate()
        except:
            for _ in range(5):
                self.uprbay_window.set_focus()
                time.sleep(0.1)
                foreground_window = win32gui.GetForegroundWindow()
                if self.uprbay_window.handle == foreground_window:
                    return
            raise Exception("Failed to set the window to the foreground")

    def on_ctrl_tab_pressed(self):
        self.tab_switcher()
        return "break"

    def tab_switcher(self):
        current_time = time.time()
        if hasattr(self, "last_switch_time") and current_time - self.last_switch_time < 0.150 or \
                (self.loading_screen_status is not None and self.loading_screen_status.winfo_exists()):
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
        if self.tabview.get() == self.enroll_tab:
            self.search_scrollbar.configure(width=None, height=None)
            self.in_search_frame = False
            self.in_enroll_frame = True
            self.unbind("<Up>")
            self.unbind("<Down>")
            self.unbind("<Home>")
            self.unbind("<End>")
            self.unbind("<Control-s>")
            self.unbind("<Control-S>")
            self.unbind("<Control-w>")
            self.unbind("<Control-W>")
            if not self.not_rebind:
                self.after(350, self.bind, "<Return>", lambda event: self.submit_event_handler())
            else:
                self.unbind("<Return>")
        elif self.tabview.get() == self.search_tab:
            self.search_scrollbar.configure(width=600, height=293)
            if hasattr(self, "table") and self.table is not None:
                self.current_class.grid_forget()
                self.table.grid_forget()
                self.table_count.grid_forget()
                self.previous_button.grid_forget()
                self.next_button.grid_forget()
                self.remove_button.grid_forget()
                self.download_search_pdf.grid_forget()
                self.sort_by.grid_forget()
                self.search_scrollbar.scroll_to_top()
                self.after(100, self.load_table)
                self.bind("<Control-s>", lambda event: self.download_search_classes_as_pdf())
                self.bind("<Control-S>", lambda event: self.download_search_classes_as_pdf())
                self.bind("<Control-w>", lambda event: self.keybind_remove_current_table())
                self.bind("<Control-W>", lambda event: self.keybind_remove_current_table())
            self.in_enroll_frame = False
            self.in_search_frame = True
            self.after(350, self.bind, "<Return>", lambda event: self.search_event_handler())
            self.search_scrollbar.bind("<Button-1>", lambda event: self.search_scrollbar.focus_set())
            self.bind("<Up>", lambda event: self.move_up_scrollbar())
            self.bind("<Down>", lambda event: self.move_down_scrollbar())
            self.bind("<Home>", lambda event: self.move_top_scrollbar())
            self.bind("<End>", lambda event: self.move_bottom_scrollbar())
        elif self.tabview.get() == self.other_tab:
            self.search_scrollbar.configure(width=None, height=None)
            self.in_enroll_frame = False
            self.in_search_frame = False
            self.unbind("<Up>")
            self.unbind("<Down>")
            self.unbind("<Home>")
            self.unbind("<End>")
            self.unbind("<Control-s>")
            self.unbind("<Control-S>")
            self.unbind("<Control-w>")
            self.unbind("<Control-W>")
            self.after(350, self.bind, "<Return>", lambda event: self.option_menu_event_handler())
        self.add_key_bindings(event=None)
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
            self.download_search_pdf.grid(row=6, column=1, padx=(157, 0), pady=(10, 0), sticky="n")
            self.sort_by.grid(row=6, column=1, padx=(0, 157), pady=(10, 0), sticky="n")
            table_count_label = f"{translation['table_count']}{len(self.class_table_pairs)}/20"
            self.table_count.configure(text=table_count_label)

    def status_widgets(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.status_frame = CustomScrollableFrame(self.status, width=475, height=280,
                                                  fg_color=("#e6e6e6", "#222222"))
        self.status_title = customtkinter.CTkLabel(self.status_frame, text=translation["status_title"],
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        translation["app_version"] = translation["app_version"].replace("{version}", self.USER_APP_VERSION)
        self.version = customtkinter.CTkLabel(self.status_frame, text=translation["app_version"])
        self.feedback_text = CustomTextBox(self.status_frame, self, enable_autoscroll=False, lang=lang,
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
        if self.status is not None and self.status.winfo_exists():
            windows_status = gw.getWindowsWithTitle("Status") + gw.getWindowsWithTitle("Estado")
            min_win = windows_status[0].isMinimized
            if min_win:
                self.status.deiconify()
            self.status.lift()
            self.status.focus_set()
            return
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.status = SmoothFadeToplevel()
        self.status_widgets()
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        help_window_width = 475
        help_window_height = 280
        center_x = main_window_x + (main_window_width // 2) - (help_window_width // 2)
        center_y = main_window_y + (main_window_height // 2) - (help_window_height // 2)
        self.status.geometry(f"{help_window_width}x{help_window_height}+{center_x + 70}+{center_y - 15}")
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
        self.status_frame.bind("<Button-2>", lambda event: self.status_frame.focus_set())
        self.status_frame.bind("<Button-3>", lambda event: self.status_frame.focus_set())
        self.status_title.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.version.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.check_update_text.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.website.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.notaso.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.faq_text.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.status.bind("<Control-space>", lambda event: self.status.focus_set())
        self.feedback_text.bind("<FocusIn>", lambda event: self.status_frame.scroll_to_widget(self.feedback_text))
        self.status.bind("<Up>", lambda event: self.status_scroll_up())
        self.status.bind("<Down>", lambda event: self.status_scroll_down())
        self.status.bind("<Home>", lambda event: self.status_move_top_scrollbar())
        self.status.bind("<End>", lambda event: self.status_move_bottom_scrollbar())
        self.status.protocol("WM_DELETE_WINDOW", self.on_status_window_close)
        self.status.bind("<Escape>", lambda event: self.on_status_window_close())

    def on_status_window_close(self):
        self.unload_image("update")
        self.unload_image("link")
        self.status_frame.unbind("<Button-1>")
        self.status_frame.unbind("<Button-2>")
        self.status_frame.unbind("<Button-3>")
        self.status_title.unbind("<Button-1>")
        self.version.unbind("<Button-1>")
        self.check_update_text.unbind("<Button-1>")
        self.website.unbind("<Button-1>")
        self.notaso.unbind("<Button-1>")
        self.faq_text.unbind("<Button-1>")
        self.status.unbind("<Control-space>")
        self.feedback_text.unbind("<FocusIn>")
        self.status.unbind("<Up>")
        self.status.unbind("<Down>")
        self.status.unbind("<Home>")
        self.status.unbind("<End>")
        self.status.unbind("<Escape>")
        self.move_slider_left_enabled = True
        self.move_slider_right_enabled = True
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
                self.log_error()
                return None
        else:
            self.connection_error = True

    def start_feedback_thread(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        msg = CTkMessagebox(title=translation["submit"], message=translation["submit_feedback"],
                            icon="question", option_1=translation["option_1"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            if not self.disable_feedback:
                current_date = datetime.today().strftime("%Y-%m-%d")
                date_record = self.cursor.execute("SELECT feedback_date FROM user_data").fetchone()
                if date_record is None or date_record[0] != current_date:
                    feedback = self.feedback_text.get("1.0", customtkinter.END).strip()
                    word_count = len(feedback.split())
                    if word_count < 1000:
                        feedback = self.feedback_text.get("1.0", customtkinter.END).strip()
                        if feedback:
                            self.sending_feedback = True
                            task_done = threading.Event()
                            loading_screen = self.show_loading_screen()
                            self.update_loading_screen(loading_screen, task_done)
                            self.thread_pool.submit(self.submit_feedback, task_done=task_done)
                            self.submit_feedback_event_completed = False
                        else:
                            if not self.connection_error:
                                def show_error():
                                    if not self.disable_audio:
                                        winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"),
                                                           winsound.SND_ASYNC)
                                    CTkMessagebox(title=translation["error"], message=translation["feedback_empty"],
                                                  icon="cancel", button_width=380)

                                self.after(50, show_error)
                    else:
                        if not self.connection_error:
                            def show_error():
                                if not self.disable_audio:
                                    winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"),
                                                       winsound.SND_ASYNC)
                                CTkMessagebox(title=translation["error"], message=translation["feedback_1000"],
                                              icon="cancel", button_width=380)

                            self.after(50, show_error)
                else:
                    if not self.connection_error:
                        def show_error():
                            if not self.disable_audio:
                                winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"),
                                                   winsound.SND_ASYNC)
                            CTkMessagebox(title=translation["error"], message=translation["feedback_day"],
                                          icon="cancel", button_width=380)

                        self.after(50, show_error)
            else:
                if not self.connection_error:
                    def show_error():
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"), winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["error"], message=translation["feedback_unavailable"],
                                      icon="cancel", button_width=380)

                    self.after(50, show_error)

    # Submits feedback from the user to a Google sheet
    def submit_feedback(self, task_done):
        with self.lock_thread:
            try:
                lang = self.language_menu.get()
                translation = self.load_language(lang)
                current_date = datetime.today().strftime("%Y-%m-%d")
                feedback = self.feedback_text.get("1.0", customtkinter.END).strip()
                result = self.call_sheets_api([[feedback]])
                if result:
                    def show_success():
                        if not self.disable_audio:
                            winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/success.wav"),
                                               winsound.SND_ASYNC)
                        CTkMessagebox(title=translation["success_title"], icon="check",
                                      message=translation["feedback_success"], button_width=380)

                    self.after(50, show_success)
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
                                winsound.PlaySound(TeraTermUI.get_absolute_path("sounds/error.wav"),
                                                   winsound.SND_ASYNC)
                            CTkMessagebox(title=translation["error"],  message=translation["feedback_error"],
                                          icon="cancel", button_width=380)

                        self.after(50, show_error)
            except Exception as err:
                print("An error occurred: ", err)
                self.error_occurred = True
                self.log_error()
            finally:
                task_done.set()
                self.submit_feedback_event_completed = True

    @staticmethod
    def find_ttermpro():
        main_drive = os.path.abspath(os.sep)
        # Prioritize common installation directories
        common_paths = [
            main_drive + "Program Files (x86)/",
            main_drive + "Program Files/",
            main_drive + "Users/*/AppData/Local/Programs/",
        ]

        # Function to search within a given path to a certain depth
        def search_within_path(search_root, depth=10):
            excluded_dirs = ["Recycler", "Recycled", "System Volume Information",
                             "$RECYCLE.BIN", "Prefetch", "Windows", "ProgramData",
                             "Temp", "System32", "SysWOW64", "Recovery", "Boot",
                             "Documents", "Pictures", "Music", "Videos"]

            for root, dirs, files in os.walk(search_root, topdown=True):
                # Exclude directories and stop descending after reaching the maximum depth
                if root[len(search_root):].count(os.sep) >= depth:
                    del dirs[:]
                else:
                    dirs[:] = [d for d in dirs if d not in excluded_dirs and not d.startswith('$')]

                for file in files:
                    if file.lower() == "ttermpro.exe":
                        return os.path.join(root, file)

            return None

        for path in common_paths:
            result = search_within_path(os.path.expandvars(path))
            if result:
                return result

        # If not found, search the entire main drive with a limited depth
        return search_within_path(main_drive)

    def change_location_auto_handler(self):
        lang = self.language_menu.get()
        self.files.configure(state="disabled")
        message_english = "Would you like the application to search for Tera Term on the main drive automatically? " \
                          "(click  the \"no\" button to search for it manually)\n\n" \
                          "Note: This process may take some time and make the application unresponsive briefly"
        message_spanish = "¿Desea que la aplicación busque automáticamente Tera Term en la unidad principal? " \
                          "(hacer clic al botón \"no\" para buscarlo manualmente)\n\n" \
                          "Nota:  Este proceso podría tardar un poco y causar que la aplicación brevemente no responda."
        message = message_english if lang == "English" else message_spanish
        response = messagebox.askyesnocancel("Tera Term", message)
        if response is True:
            self.auto_search = True
            task_done = threading.Event()
            loading_screen = self.show_loading_screen()
            self.update_loading_screen(loading_screen, task_done)
            self.thread_pool.submit(self.change_location_event, task_done=task_done)
        elif response is False:
            self.manually_change_location()
        else:
            if self.help is not None and self.help.winfo_exists():
                self.help.lift()
                self.help.focus_set()
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
                    "INSERT INTO user_data (location, config, directory) VALUES (?, ?, ?)",
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
            atexit.unregister(self.restore_original_font)
            atexit.register(self.restore_original_font, self.teraterm_file)
            if self.help is not None and self.help.winfo_exists():
                self.files.configure(state="normal")
        else:
            task_done.set()
            message_english = ("Tera Term executable was not found on the main drive.\n\n"
                               "the application is probably not installed\nor it's located on another drive")
            message_spanish = ("No se encontró el ejecutable de Tera Term en la unidad principal.\n\n"
                               "Probablemente no tiene la aplicación instalada\no está localizada en otra unidad")
            message = message_english if lang == "English" else message_spanish
            messagebox.showinfo("Tera Term", message)
            self.manually_change_location()

    @staticmethod
    def find_teraterm_directory():
        import glob

        main_drive = os.path.abspath(os.sep)
        base_path = os.path.join(main_drive, "Program Files (x86)")
        possible_dirs = glob.glob(os.path.join(base_path, "teraterm*"))
        original_teraterm = os.path.join(base_path, "teraterm")
        if original_teraterm in possible_dirs:
            return original_teraterm
        elif possible_dirs:
            return possible_dirs[0]
        return None

    # Function that lets user select where their Tera Term application is located
    def manually_change_location(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        filename = filedialog.askopenfilename(
            initialdir=os.path.abspath(os.sep), title=translation["select_tera_term"],
            filetypes=(("Tera Term", "*ttermpro.exe"),))
        if re.search("ttermpro.exe", filename):
            self.location = filename.replace("\\", "/")
            directory, filename = os.path.split(self.location)
            self.teraterm_directory = directory
            self.teraterm_file = self.teraterm_directory + "/TERATERM.ini"
            row_exists = self.cursor.execute("SELECT 1 FROM user_data").fetchone()
            if not row_exists:
                self.cursor.execute(
                    "INSERT INTO user_data (location, config, directory) VALUES (?, ?, ?)",
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
            atexit.unregister(self.restore_original_font)
            atexit.register(self.restore_original_font, self.teraterm_file)
        if not re.search("ttermpro.exe", filename):
            if self.help is not None and self.help.winfo_exists():
                self.help.lift()
                self.help.focus_set()
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
            query = "SELECT name, code FROM courses ORDER BY name"
        else:
            query_conditions = [f"LOWER(name) LIKE '%{search_term}%'", f"LOWER(code) LIKE '%{search_term}%'"]
            query_conditions_str = " OR ".join(query_conditions)
            query = f"SELECT name, code FROM courses WHERE {query_conditions_str}"

        results = self.cursor.execute(query).fetchall()
        if not results:  # if there are no results, display a message
            self.class_list.delete(0, tk.END)
            self.class_list.insert(tk.END, translation["no_results"])
            self.search_box.configure(border_color="#c30101")
        else:
            for row in results:
                default_border_color = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"]
                if self.search_box.border_color != default_border_color:
                    self.search_box.configure(border_color=default_border_color)
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
            self.search_box.configure(border_color="#c30101")
        else:
            self.search_box.delete(0, tk.END)
            self.search_box.insert(0, result[0])
            self.search_box.configure(border_color="#228B22")

    def help_widgets(self):
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.help_frame = customtkinter.CTkScrollableFrame(self.help, width=475, height=280,
                                                           fg_color=("#e6e6e6", "#222222"))
        self.help_title = customtkinter.CTkLabel(self.help_frame, text=translation["help"],
                                                 font=customtkinter.CTkFont(size=20, weight="bold"))
        self.notice = customtkinter.CTkLabel(self.help_frame, text=translation["notice"],
                                             font=customtkinter.CTkFont(weight="bold", underline=True))
        self.searchbox_text = customtkinter.CTkLabel(self.help_frame, text=translation["searchbox_title"])
        self.search_box = CustomEntry(self.help_frame, self, lang, placeholder_text=translation["searchbox"])
        self.search_box.is_listbox_entry = True
        self.class_list = tk.Listbox(self.help_frame, width=35, bg="#0e95eb", fg="#333333", font=("Roboto", 12))
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
                                                      command=TeraTermUI.curriculums,
                                                      height=30, width=150)
        self.keybinds_text = customtkinter.CTkLabel(self.help_frame, text=translation["keybinds_title"],
                                                    font=customtkinter.CTkFont(weight="bold", size=15))
        self.keybinds = [[translation["keybind"], translation["key_function"]],
                         ["<Return> / <Enter>", translation["return"]],
                         ["<Escape>", translation["escape"]],
                         ["<Ctrl-BackSpace>", translation["ctrl_backspace"]],
                         ["<Arrow-Keys>", translation["arrow_keys"]],
                         ["<SpaceBar>", translation["space_bar"]],
                         ["<Tab>", translation["tab"]],
                         ["<Ctrl-Tab>", translation["ctrl_tab"]],
                         ["<Ctrl-Space>", translation["ctrl_space"]],
                         ["<Ctrl-C>", translation["ctrl_c"]],
                         ["<Ctrl-V>", translation["ctrl_v"]],
                         ["<Ctrl-X>", translation["ctrl_x"]],
                         ["<Ctrl-Z>", translation["ctrl_z"]],
                         ["<Ctrl-Y>", translation["ctrl_y"]],
                         ["<Ctrl-A>", translation["ctrl_a"]],
                         ["<Ctrl-S>", translation["ctrl_s"]],
                         ["<Ctrl-W>", translation["ctrl_w"]],
                         ["<Right-Click>", translation["mouse_2"]],
                         ["<Home>", translation["home"]],
                         ["<End>", translation["end"]],
                         ["<F1>", translation["F1"]],
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
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            return

        if self.help is not None and self.help.winfo_exists():
            windows_help = gw.getWindowsWithTitle("Help") + gw.getWindowsWithTitle("Ayuda")
            min_win = windows_help[0].isMinimized
            if min_win:
                self.help.deiconify()
            self.help.lift()
            self.help.focus_set()
            return
        lang = self.language_menu.get()
        translation = self.load_language(lang)
        self.help = SmoothFadeToplevel()
        self.help_widgets()
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        help_window_width = 475
        help_window_height = 280
        center_x = main_window_x + (main_window_width // 2) - (help_window_width // 2)
        center_y = main_window_y + (main_window_height // 2) - (help_window_height // 2)
        self.help.geometry(f"{help_window_width}x{help_window_height}+{center_x + 70}+{center_y - 15}")
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
        self.keybinds_table = CTkTable(self.help_frame, column=2, row=21, values=self.keybinds, hover=False)
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
        self.help_frame.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.help_frame.bind("<Button-2>", lambda event: self.help_frame.focus_set())
        self.help_frame.bind("<Button-3>", lambda event: self.help_frame.focus_set())
        self.disable_idle.bind("<space>", lambda event: self.keybind_disable_enable_idle())
        self.disable_audio_val.bind("<space>", lambda event: self.keybind_disable_enable_audio())
        self.skip_auth_switch.bind("<space>", lambda event: self.keybind_disable_enable_auth())
        self.class_list.bind("<<ListboxSelect>>", self.show_class_code)
        self.class_list.bind("<MouseWheel>", self.disable_scroll)
        self.class_list.bind("<FocusIn>", lambda event: self.help_frame.scroll_to_widget(self.class_list))
        self.search_box.bind("<KeyRelease>", self.search_classes)
        self.search_box.bind("<FocusIn>", lambda event: self.help_frame.scroll_to_widget(self.search_box))
        self.help_title.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.notice.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.searchbox_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.curriculum_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.keybinds_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.terms_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.skip_auth_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.files_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.disable_idle_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.disable_audio_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.fix_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.curriculum.bind("<FocusIn>", lambda event: self.help_frame.scroll_to_widget(self.curriculum))
        self.skip_auth_switch.bind("<FocusIn>", lambda event: self.help_frame.scroll_to_widget(self.skip_auth_switch))
        self.disable_idle.bind("<FocusIn>", lambda event: self.help_frame.scroll_to_widget(self.disable_idle))
        self.disable_audio_val.bind("<FocusIn>", lambda event: self.help_frame.scroll_to_widget(self.disable_audio_val))
        self.help.bind("<Control-space>", lambda event: self.help.focus_set())
        self.help.bind("<Up>", lambda event: None if self.is_listbox_focused() else self.help_scroll_up())
        self.help.bind("<Down>", lambda event: None if self.is_listbox_focused() else self.help_scroll_down())
        self.help.bind("<Home>", lambda event: None if self.is_listbox_focused() else self.help_move_top_scrollbar())
        self.help.bind("<End>", lambda event: None if self.is_listbox_focused() else self.help_move_bottom_scrollbar())
        self.help.protocol("WM_DELETE_WINDOW", self.on_help_window_close)
        self.help.bind("<Escape>", lambda event: self.on_help_window_close())

    def on_help_window_close(self):
        self.unload_image("folder")
        self.unload_image("fix")
        self.help_frame.unbind("<Button-1>")
        self.help_frame.unbind("<Button-2>")
        self.help_frame.unbind("<Button-3>")
        self.disable_idle.unbind("<space>")
        self.disable_audio_val.unbind("<space>")
        self.skip_auth_switch.unbind("<space>")
        self.class_list.unbind("<<ListboxSelect>>")
        self.class_list.unbind("<MouseWheel>")
        self.class_list.unbind("<FocusIn>")
        self.search_box.unbind("<KeyRelease>")
        self.search_box.unbind("<FocusIn>")
        self.help_title.unbind("<Button-1>")
        self.notice.unbind("<Button-1>")
        self.searchbox_text.unbind("<Button-1>")
        self.curriculum_text.unbind("<Button-1>")
        self.keybinds_text.unbind("<Button-1>")
        self.terms_text.unbind("<Button-1>")
        self.skip_auth_text.unbind("<Button-1>")
        self.files_text.unbind("<Button-1>")
        self.disable_idle_text.unbind("<Button-1>")
        self.disable_audio_text.unbind("<Button-1>")
        self.fix_text.unbind("<Button-1>")
        self.curriculum.unbind("<FocusIn>")
        self.skip_auth_switch.unbind("<FocusIn>")
        self.disable_idle.unbind("<FocusIn>")
        self.disable_audio_val.unbind("<FocusIn>")
        self.help.unbind("<Control-space>")
        self.help.unbind("<Up>")
        self.help.unbind("<Down>")
        self.help.unbind("<Home>")
        self.help.unbind("<End>")
        self.help.unbind("<Escape>")
        self.move_slider_left_enabled = True
        self.move_slider_right_enabled = True
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
            headers = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                      "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")}
            try:
                with requests.get(url, headers=headers, timeout=3) as response:
                    if response.status_code != 200:
                        print(f"Error fetching release information: {response.status_code}")
                        return None

                    release_data = response.json()
                    latest_version = release_data.get("tag_name")
                    if latest_version and latest_version.startswith("v"):
                        latest_version = latest_version[1:]

                    return latest_version

            except requests.exceptions.RequestException as err:
                print(f"Request failed: {err}")
                return None
            except Exception as err:
                print(f"An error occurred while fetching the latest release: {err}")
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

    def set_beep_sound(self, file_path, disable_beep=True):
        if not self.can_edit:
            return

        if "teraterm5" in file_path:
            appdata_ini_path = TeraTermUI.find_appdata_teraterm_ini()
            if appdata_ini_path:
                file_path = appdata_ini_path
            else:
                return

        if TeraTermUI.is_file_in_directory("ttermpro.exe", self.teraterm_directory):
            backup_path = os.path.join(self.app_temp_dir, "TERATERM.ini.bak")
            if not os.path.exists(backup_path):
                backup_path = os.path.join(self.app_temp_dir, os.path.basename(file_path) + ".bak")
                try:
                    shutil.copyfile(file_path, backup_path)
                except FileNotFoundError:
                    print("Tera Term probably not installed or installed\n"
                          " in a different location from the default")
            try:
                with open(file_path, "rb") as file:
                    raw_data = file.read()
                    encoding_info = chardet_detect(raw_data)
                    detected_encoding = encoding_info["encoding"]
                with open(file_path, "r", encoding=detected_encoding) as file:
                    lines = file.readlines()
                beep_setting = "off" if disable_beep else "on"
                for index, line in enumerate(lines):
                    if line.startswith("Beep="):
                        lines[index] = f"Beep={beep_setting}\n"
                        self.disable_audio = disable_beep
                with open(file_path, "w", encoding=detected_encoding) as file:
                    file.writelines(lines)
            except FileNotFoundError:
                return
            except Exception as err:
                print(f"Error occurred: {err}")
                print("Restoring from backup...")
                shutil.copyfile(backup_path, file_path)
            del line, lines

    # Edits the font that tera term uses to "Terminal" to mitigate the chance of the OCR mistaking words
    def edit_teraterm_ini(self, file_path):
        if "teraterm5" in file_path:
            appdata_ini_path = TeraTermUI.find_appdata_teraterm_ini()
            if appdata_ini_path:
                file_path = appdata_ini_path
                self.teraterm5_first_boot = False
            else:
                self.teraterm5_first_boot = True
                return

        if TeraTermUI.is_file_in_directory("ttermpro.exe", self.teraterm_directory):
            backup_path = os.path.join(self.app_temp_dir, "TERATERM.ini.bak")
            if not os.path.exists(backup_path):
                backup_path = os.path.join(self.app_temp_dir, os.path.basename(file_path) + ".bak")
                try:
                    shutil.copyfile(file_path, backup_path)
                except FileNotFoundError:
                    print("Tera Term probably not installed or installed\n"
                          " in a different location from the default")
            try:
                with open(file_path, "rb") as file:
                    raw_data = file.read()
                    encoding_info = chardet_detect(raw_data)
                    detected_encoding = encoding_info["encoding"]
                with open(file_path, "r", encoding=detected_encoding) as file:
                    lines = file.readlines()
                for index, line in enumerate(lines):
                    if line.startswith("VTFont="):
                        current_value = line.strip().split("=")[1]
                        font_name = current_value.split(",")[0]
                        self.original_font = current_value
                        updated_value = "Lucida Console" + current_value[len(font_name):]
                        lines[index] = f"VTFont={updated_value}\n"
                    if line.startswith("VTColor=") and not line.startswith(";"):
                        current_value = line.strip().split("=")[1]
                        if current_value != "255,255,255,0,0,0":
                            self.original_color = current_value
                            lines[index] = "VTColor=255,255,255,0,0,0\n"
                    if line.startswith("AuthBanner="):
                        current_value = line.strip().split("=")[1]
                        if current_value not in ["0", "1"]:
                            lines[index] = "AuthBanner=1\n"
                    self.can_edit = True
                with open(file_path, "w", encoding=detected_encoding) as file:
                    file.writelines(lines)
                self.teraterm_not_found = False
                self.download = False
            except FileNotFoundError:
                return
            except Exception as err:
                print(f"Error occurred: {err}")
                print("Restoring from backup...")
                shutil.copyfile(backup_path, file_path)
            del line, lines
        else:
            self.teraterm_not_found = True

    # Restores the original font option the user had
    def restore_original_font(self, file_path):
        if not self.can_edit:
            return

        if "teraterm5" in file_path:
            appdata_ini_path = TeraTermUI.find_appdata_teraterm_ini()
            if appdata_ini_path:
                file_path = appdata_ini_path
            else:
                return

        backup_path = os.path.join(self.app_temp_dir, "TERATERM.ini.bak")
        try:
            with open(file_path, "rb") as file:
                raw_data = file.read()
                encoding_info = chardet_detect(raw_data)
                detected_encoding = encoding_info["encoding"]
            with open(file_path, "r", encoding=detected_encoding) as file:
                lines = file.readlines()
            with open(backup_path, "r", encoding=detected_encoding) as backup_file:
                backup_lines = backup_file.readlines()
            backup_font = None
            backup_color = None
            for line in backup_lines:
                if line.startswith("VTFont="):
                    backup_font = line.strip().split("=")[1]
                if line.startswith("VTColor=") and not line.startswith(";"):
                    backup_color = line.strip().split("=")[1]
            if backup_font is None or backup_color is None:
                return

            for index, line in enumerate(lines):
                if line.startswith("VTFont="):
                    lines[index] = f"VTFont={backup_font}\n"
                if line.startswith("VTColor=") and not line.startswith(";"):
                    lines[index] = f"VTColor={backup_color}\n"
            if self.disable_audio_val is not None and self.disable_audio_val.get() == "on":
                for index, line in enumerate(lines):
                    if line.startswith("Beep=") and line.strip() != "Beep=off":
                        lines[index] = "Beep=off\n"
            with open(file_path, "w", encoding=detected_encoding) as file:
                file.writelines(lines)
        except FileNotFoundError:
            print(f"File or backup not found.")
        except IOError as err:
            print(f"Error occurred: {err}")
            print("Restoring from backup...")
            try:
                shutil.copyfile(backup_path, file_path)
            except FileNotFoundError:
                print(f"The backup file at {backup_path} was not found.")

    # When the user performs an action to do something in tera term it destroys windows that might get in the way
    def destroy_windows(self):
        if self.error is not None and self.error.winfo_exists():
            self.error.destroy()
        if self.success is not None and self.success.winfo_exists():
            self.success.destroy()
        if self.information is not None and self.information.winfo_exists():
            self.information.destroy()

    def get_image(self, image_name):
        if image_name not in self.image_cache:
            if image_name == "folder":
                self.image_cache["folder"] = customtkinter.CTkImage(
                    light_image=Image.open(TeraTermUI.get_absolute_path("images/folder.png")), size=(18, 18))
            elif image_name == "fix":
                self.image_cache["fix"] = customtkinter.CTkImage(
                    light_image=Image.open(TeraTermUI.get_absolute_path("images/fix.png")), size=(15, 15))
            elif image_name == "error":
                self.image_cache["error"] = customtkinter.CTkImage(
                    light_image=Image.open(TeraTermUI.get_absolute_path("images/error.png")), size=(100, 100))
            elif image_name == "information":
                self.image_cache["information"] = customtkinter.CTkImage(
                    light_image=Image.open(TeraTermUI.get_absolute_path("images/info.png")), size=(100, 100))
            elif image_name == "success":
                self.image_cache["success"] = customtkinter.CTkImage(
                    light_image=Image.open(TeraTermUI.get_absolute_path("images/success.png")), size=(200, 150))
            elif image_name == "status":
                self.image_cache["status"] = customtkinter.CTkImage(
                    light_image=Image.open(TeraTermUI.get_absolute_path("images/home.png")), size=(20, 20))
            elif image_name == "help":
                self.image_cache["help"] = customtkinter.CTkImage(
                    light_image=Image.open(TeraTermUI.get_absolute_path("images/setting.png")), size=(18, 18))
            elif image_name == "uprb":
                self.image_cache["uprb"] = customtkinter.CTkImage(
                    light_image=Image.open(TeraTermUI.get_absolute_path("images/uprb.jpg")), size=(300, 100))
            elif image_name == "lock":
                self.image_cache["lock"] = customtkinter.CTkImage(
                    light_image=Image.open(TeraTermUI.get_absolute_path("images/lock.png")), size=(75, 75))
            elif image_name == "update":
                self.image_cache["update"] = customtkinter.CTkImage(
                    light_image=Image.open(TeraTermUI.get_absolute_path("images/update.png")), size=(15, 15))
            elif image_name == "link":
                self.image_cache["link"] = customtkinter.CTkImage(
                    light_image=Image.open(TeraTermUI.get_absolute_path("images/link.png")), size=(15, 15))
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
            choices = self.m_register_menu[i].get()
            entries.append((choices, classes, sections))
        semester = self.m_semester_entry[0].get().upper().replace(" ", "")
        curr_sem = translation["current"].upper()

        # Check for empty entries and format errors
        error_entries = []
        for i in range(self.a_counter + 1):
            (choices, classes, sections) = entries[i]
            if not classes or not sections or not semester:
                error_msg_long = translation["missing_info_multiple"]
                if not classes:
                    error_entries.append(self.m_classes_entry[i])
                if not sections:
                    error_entries.append(self.m_section_entry[i])
                if not semester:
                    error_entries.append(self.m_semester_entry[0])
                if choices not in ["Register", "Registra", "Drop", "Baja"]:
                    error_entries.append(self.m_register_menu[i])
                break
            elif choices not in ["Register", "Registra", "Drop", "Baja"]:
                error_msg_medium = translation["drop_or_enroll"]
                error_entries.append(self.m_register_menu[i])
                break
            elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes, flags=re.IGNORECASE):
                error_msg_short = translation["multiple_class_format_error"]
                error_entries.append(self.m_classes_entry[i])
                break
            elif not re.fullmatch("^[A-Z]{2}[A-Z0-9]$", sections, flags=re.IGNORECASE):
                error_msg_short = translation["multiple_section_format_error"]
                error_entries.append(self.m_section_entry[i])
                break
            if choices in ["Register", "Registra"]:
                if sections in self.classes_status:
                    status_entry = self.classes_status[sections]
                    if status_entry["status"] == "ENROLLED" and status_entry["classes"] == classes and \
                            status_entry["semester"] == semester:
                        error_msg_long = translation["multiple_already_enrolled"]
                        break
            elif choices in ["Drop", "Baja"]:
                if sections in self.classes_status:
                    status_entry = self.classes_status[sections]
                    if status_entry["status"] == "DROPPED" and status_entry["classes"] == classes and \
                            status_entry["semester"] == semester:
                        error_msg_long = translation["multiple_already_dropped"]
                        break

        if not re.fullmatch("^[A-Z][0-9]{2}$", semester, flags=re.IGNORECASE) and semester != curr_sem:
            error_msg_short = translation["multiple_semester_format_error"]
            error_entries.append(self.m_semester_entry[0])
        for error_widget in error_entries:
            if error_widget in self.m_register_menu:
                self.after(0, error_widget.configure(button_color="#c30101"))
            else:
                self.after(0, error_widget.configure(border_color="#c30101"))

        # Display error messages or proceed if no errors
        if error_msg_short:
            self.after(100, self.show_error_message, 345, 235, error_msg_short)
            if self.auto_enroll_bool:
                self.auto_enroll_bool = False
                self.after(100, self.auto_enroll.deselect)
            return False
        elif error_msg_medium:
            self.after(100, self.show_error_message, 355, 240, error_msg_medium)
            if self.auto_enroll_bool:
                self.auto_enroll_bool = False
                self.after(100, self.auto_enroll.deselect)
            return False
        elif error_msg_long:
            self.after(100, self.show_error_message, 390, 245, error_msg_long)
            if self.auto_enroll_bool:
                self.auto_enroll_bool = False
                self.after(100, self.auto_enroll.deselect)
            return False

        return True


class CustomButton(customtkinter.CTkButton):
    __slots__ = ("master", "command")

    def __init__(self, master=None, command=None, **kwargs):
        super().__init__(master, cursor="hand2", **kwargs)
        self.is_pressed = False
        self.click_command = command
        self.text = kwargs.pop("text", None)
        self.image = kwargs.pop("image", None)
        if self.image and not self.text:
            self.configure(image=self.image)
        else:
            self.bind("<Enter>", self.on_enter)
            self.bind("<Motion>", self.on_enter)
            self.bind("<Leave>", self.on_leave)
            self.bind("<B1-Motion>", self.on_motion)
        self.bind("<ButtonPress-1>", self.on_button_down)
        self.bind("<ButtonRelease-1>", self.on_button_up)

    def on_button_down(self, event):
        if self.cget("state") == "disabled":
            return
        self.is_pressed = True

    def on_button_up(self, event):
        if self.cget("state") == "disabled":
            return
        if self.is_pressed and self.is_mouse_over_widget():
            if self.click_command:
                if self.winfo_exists():
                    self.after(350, self._on_leave, event)
                self.click_command()
        self.is_pressed = False

    def is_mouse_over_widget(self):
        x, y = self.winfo_rootx(), self.winfo_rooty()
        width, height = self.winfo_width(), self.winfo_height()
        mouse_x, mouse_y = self.winfo_pointerx(), self.winfo_pointery()
        return x <= mouse_x < x + width and y <= mouse_y < y + height

    def on_enter(self, event):
        if self.cget("state") == "disabled":
            self.configure(cursor="")
            return
        if self.is_mouse_over_widget():
            self.configure(cursor="hand2")

    def on_leave(self, event):
        if self.cget("state") == "disabled":
            self.configure(cursor="")
            return
        self.configure(cursor="")
        if self.is_mouse_over_widget() and self.is_pressed:
            self._on_enter()
            self.configure(cursor="hand2")
        else:
            self._on_leave()
            self.configure(cursor="")

    def on_motion(self, event):
        if self.cget("state") == "disabled":
            self.configure(cursor="")
            return
        if self.is_mouse_over_widget() and self.is_pressed:
            self._on_enter()
            self.configure(cursor="hand2")
        else:
            self._on_leave()
            self.configure(cursor="")

    def destroy(self):
        self.text = None
        self.image = None
        self.is_pressed = None
        self.unbind("<Enter>")
        self.unbind("<Leave>")
        self.unbind("<ButtonPress-1>")
        self.unbind("<ButtonRelease-1>")
        self.unbind("<B1-Motion>")
        self.unbind("<Motion>")
        super().destroy()


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
    __slots__ = ("master", "teraterm_ui_instance", "enable_autoscroll", "read_only", "lang")

    def __init__(self, master, teraterm_ui_instance, enable_autoscroll=True, read_only=False, lang=None, **kwargs):
        super().__init__(master, **kwargs)
        self.auto_scroll = enable_autoscroll
        self.lang = lang
        self.read_only = read_only
        self.disabled_autoscroll = False
        self.after_id = None
        self.select = False
        self.saved_cursor_position = None

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

        # Bind Ctrl+V to custom paste method
        self.bind("<Control-v>", self.custom_paste)
        self.bind("<Control-V>", self.custom_paste)
        # Bind Ctrl+X to custom cut method
        self.bind("<Control-x>", self.custom_cut)
        self.bind("<Control-X>", self.custom_cut)

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
        self.bind("<Button-2>", self.custom_middle_mouse)
        self.bind("<Button-3>", self.show_menu)

    def disable_slider_keys(self, event=None):
        if self.tag_ranges(tk.SEL) and self.select:
            self.tag_remove(tk.SEL, "1.0", tk.END)
            if self.lang == "English" and not self.read_only:
                self.context_menu.entryconfigure(3, label="Select All")
            elif self.lang == "Español" and not self.read_only:
                self.context_menu.entryconfigure(3, label="Seleccionar Todo")

            if self.lang == "English" and self.read_only:
                self.context_menu.entryconfigure(1, label="Select All")
            elif self.lang == "Español" and self.read_only:
                self.context_menu.entryconfigure(1, label="Seleccionar Todo")

        self.teraterm_ui.move_slider_left_enabled = False
        self.teraterm_ui.move_slider_right_enabled = False
        self.teraterm_ui.up_arrow_key_enabled = False
        self.teraterm_ui.down_arrow_key_enabled = False

    def enable_slider_keys(self, event=None):
        if self.tag_ranges(tk.SEL) and not self.select:
            self.tag_remove(tk.SEL, "1.0", tk.END)

        self.select = False
        self.teraterm_ui.move_slider_left_enabled = True
        self.teraterm_ui.move_slider_right_enabled = True
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
        self.focus_set()
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
            cursor_position = self.index(tk.INSERT)
            self._redo_stack.append((self._undo_stack.pop(), cursor_position))
            self.delete("1.0", "end")
            self.insert("1.0", self._undo_stack[-1])
            self.mark_set(tk.INSERT, cursor_position)
            self.see(cursor_position)

    def redo(self, event=None):
        if self._redo_stack:
            redo_text, new_cursor_position = self._redo_stack.pop()
            self._undo_stack.append(redo_text)
            self.delete("1.0", "end")
            self.insert("1.0", redo_text)
            self.mark_set(tk.INSERT, new_cursor_position)
            self.see(new_cursor_position)

    def custom_middle_mouse(self, event=None):
        if self.tag_ranges(tk.SEL):
            self.mark_set(tk.INSERT, "@%d,%d" % (event.x, event.y))
            self.tag_remove(tk.SEL, "1.0", tk.END)
            return "break"
        if not self.tag_ranges(tk.SEL) and self.read_only:
            self.stop_autoscroll(event=None)
            self.tag_add(tk.SEL, "1.0", tk.END)
            return "break"

    def show_menu(self, event):
        self.saved_cursor_position = self.index(tk.INSERT)
        self.stop_autoscroll(event=None)
        self.mark_set(tk.INSERT, "end")
        self.select = True

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

    def custom_cut(self, event=None):
        self.cut()
        self.see(tk.INSERT)
        return "break"

    def cut(self):
        self.focus_set()
        if self.saved_cursor_position is not None:
            self.mark_set(tk.INSERT, self.saved_cursor_position)
            self.saved_cursor_position = None
        if not self.tag_ranges(tk.SEL):
            current_line = self.index(tk.INSERT).split(".")[0]
            self.tag_add(tk.SEL, f"{current_line}.0", f"{current_line}.end")
        try:
            selected_text = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.delete(tk.SEL_FIRST, tk.SEL_LAST)

            new_text = self.get("1.0", "end-1c")
            # Update the undo stack after the cut operation
            self._undo_stack.append(new_text)
            # Clear the redo stack
            self._redo_stack.clear()
            self.see(tk.INSERT)
        except tk.TclError:
            print("No text selected to cut.")

    def copy(self):
        self.stop_autoscroll(event=None)
        if not self.tag_ranges(tk.SEL):
            self.tag_add(tk.SEL, "1.0", tk.END)
        try:
            selected_text = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            print("No text selected to copy.")

    def custom_paste(self, event=None):
        self.paste()
        self.see(tk.INSERT)
        return "break"

    def paste(self, event=None):
        self.focus_set()
        if self.saved_cursor_position is not None:
            self.mark_set(tk.INSERT, self.saved_cursor_position)
            self.saved_cursor_position = None
        try:
            clipboard_text = self.clipboard_get()
            max_paste_length = 10000  # Set a limit for the max paste length
            if len(clipboard_text) > max_paste_length:
                clipboard_text = clipboard_text[:max_paste_length]  # Truncate to max length
                print("Pasted content truncated to maximum length.")

            # Save the current state to undo stack only if there is a change
            current_text = self.get("1.0", "end-1c")
            if len(self._undo_stack) == 0 or (len(self._undo_stack) > 0 and current_text != self._undo_stack[-1]):
                self._undo_stack.append(current_text)

            try:
                start_index = self.index(tk.SEL_FIRST)
                end_index = self.index(tk.SEL_LAST)
                self.delete(start_index, end_index)
            except tk.TclError:
                pass  # Nothing selected, which is fine

            self.insert(tk.INSERT, clipboard_text)
            self._redo_stack.clear()  # Clear redo stack after a new operation

            # Update undo stack here, after paste operation
            new_text = self.get("1.0", "end-1c")
            if new_text != self._undo_stack[-1]:
                self._undo_stack.append(new_text)
            self.see(tk.INSERT)
        except tk.TclError:
            pass  # Clipboard empty or other issue

    def select_all(self, event=None):
        self.stop_autoscroll(event=None)
        self.mark_set(tk.INSERT, "end")
        try:
            if self.tag_ranges(tk.SEL):
                self.tag_remove(tk.SEL, "1.0", tk.END)
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

    def destroy(self):
        self.unbind("<Button-1>")
        self.unbind("<MouseWheel>")
        self.unbind("<FocusIn>")
        self.unbind("<FocusOut>")
        if hasattr(self, "_y_scrollbar"):
            self._y_scrollbar.unbind("<Button-1>")
            self._y_scrollbar.unbind("<B1-Motion>")
        if hasattr(self, "_x_scrollbar"):
            self._x_scrollbar.unbind("<Button-1>")
            self._x_scrollbar.unbind("<B1-Motion>")
        self.unbind("<Control-z>")
        self.unbind("<Control-Z>")
        self.unbind("<Control-y>")
        self.unbind("<Control-Y>")
        self.unbind("<Control-v>")
        self.unbind("<Control-V>")
        self.unbind("<Control-x>")
        self.unbind("<Control-X>")
        self.unbind("<Control-a>")
        self.unbind("<Control-A>")
        self.unbind("<Button-2>")
        self.unbind("<Button-3>")
        self.unbind("<KeyRelease>")
        if self.read_only:
            self.unbind("<Up>")
            self.unbind("<Down>")
        self.auto_scroll = None
        self.lang = None
        self.read_only = None
        self.disabled_autoscroll = None
        self.after_id = None
        self.select = None
        self.teraterm_ui = None
        self.context_menu = None
        self.saved_cursor_position = None
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._undo_stack = None
        self._redo_stack = None
        super().destroy()


class CustomEntry(customtkinter.CTkEntry):
    __slots__ = ("master", "teraterm_ui_instance", "lang")

    def __init__(self, master, teraterm_ui_instance, lang=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        initial_state = self.get()
        self._undo_stack = deque([initial_state], maxlen=50)
        self._redo_stack = deque(maxlen=50)
        self.lang = lang
        self.is_listbox_entry = False
        self.select = False
        self.border_color = None

        self.teraterm_ui = teraterm_ui_instance
        self.bind("<FocusIn>", self.disable_slider_keys)
        self.bind("<FocusOut>", self.enable_slider_keys)

        # Bind Control-Z to undo and Control-Y to redo
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-Z>", self.undo)
        self.bind("<Control-y>", self.redo)
        self.bind("<Control-Y>", self.redo)

        # Bind Ctrl+V to custom paste method
        self.bind("<Control-v>", self.custom_paste)
        self.bind("<Control-V>", self.custom_paste)
        # Bind Ctrl+X to custom cut method
        self.bind("<Control-x>", self.custom_cut)
        self.bind("<Control-X>", self.custom_cut)

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
        self.bind("<Button-2>", self.custom_middle_mouse)
        self.bind("<Button-3>", self.show_menu)

    def disable_slider_keys(self, event=None):
        if self.cget("border_color") == "#c30101" or self.cget("border_color") == "#228B22":
            if self.border_color is None:
                self.border_color = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"]
            self.configure(border_color=self.border_color)

        if self.select_present() and self.select:
            self.select_clear()

            if self.lang == "English":
                self.context_menu.entryconfigure(3, label="Select All")
            elif self.lang == "Español":
                self.context_menu.entryconfigure(3, label="Seleccionar Todo")

        self.teraterm_ui.move_slider_left_enabled = False
        self.teraterm_ui.move_slider_right_enabled = False
        self.teraterm_ui.up_arrow_key_enabled = False
        self.teraterm_ui.down_arrow_key_enabled = False

    def enable_slider_keys(self, event=None):
        if self.select_present() and not self.select:
            self.select_clear()

        self.select = False
        self.teraterm_ui.move_slider_left_enabled = True
        self.teraterm_ui.move_slider_right_enabled = True
        self.teraterm_ui.up_arrow_key_enabled = True
        self.teraterm_ui.down_arrow_key_enabled = True

    def update_undo_stack(self, event=None):
        current_text = self.get()
        if current_text != self._undo_stack[-1]:
            self._undo_stack.append(current_text)
            self._redo_stack.clear()

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

    def custom_middle_mouse(self, event=None):
        if self.select_present():
            char_index = self.index("@%d" % event.x)
            self.icursor(char_index)
            self.select_clear()
            return "break"

    def show_menu(self, event):
        if self.cget("state") == "disabled":
            return

        self.focus_set()
        self.icursor(tk.END)
        self.select = True

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

    def custom_cut(self, event=None):
        self.cut()
        return "break"

    def cut(self):
        self.focus_set()
        if not self.select_present():
            self.select_range(0, "end")
        try:
            selected_text = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.delete(tk.SEL_FIRST, tk.SEL_LAST)

            new_text = self.get()
            # Update the undo stack after cut operation
            self._undo_stack.append(new_text)
            # Clear the redo stack
            self._redo_stack.clear()

            if self.is_listbox_entry:
                self.update_listbox()
        except tk.TclError:
            print("No text selected to cut.")

    def copy(self):
        self.focus_set()
        if not self.select_present():
            self.select_range(0, "end")
        try:
            selected_text = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            print("No text selected to copy.")

    def custom_paste(self, event=None):
        self.paste()
        return "break"

    def paste(self, event=None):
        self.focus_set()
        try:
            clipboard_text = self.clipboard_get()
            max_paste_length = 250  # Set a limit for the max paste length
            if len(clipboard_text) > max_paste_length:
                clipboard_text = clipboard_text[:max_paste_length]  # Truncate to max length
                print("Pasted content truncated to maximum length.")

            current_text = self.get()
            # Save the current state to undo stack
            if len(self._undo_stack) == 0 or (len(self._undo_stack) > 0 and current_text != self._undo_stack[-1]):
                self._undo_stack.append(current_text)

            try:
                start_index = self.index(tk.SEL_FIRST)
                end_index = self.index(tk.SEL_LAST)
                self.delete(start_index, end_index)
            except tk.TclError:
                pass  # Nothing selected, which is fine

            self.insert(tk.INSERT, clipboard_text)

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
            if self.select_present():
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

    def _activate_placeholder(self):
        entry_text = self._entry.get()
        if (entry_text == "" or entry_text.isspace()) and self._placeholder_text is not None and (
                self._textvariable is None or self._textvariable == ""):
            self._placeholder_text_active = True
            self._pre_placeholder_arguments = {"show": self._entry.cget("show")}
            self._entry.config(fg=self._apply_appearance_mode(self._placeholder_text_color),
                               disabledforeground=self._apply_appearance_mode(self._placeholder_text_color),
                               show="")
            self._entry.delete(0, tk.END)
            self._entry.insert(0, self._placeholder_text)

    def update_listbox(self):
        self.teraterm_ui.search_classes(None)

    def destroy(self):
        self.unbind("<FocusIn>")
        self.unbind("<FocusOut>")
        self.unbind("<Control-z>")
        self.unbind("<Control-Z>")
        self.unbind("<Control-y>")
        self.unbind("<Control-Y>")
        self.unbind("<Control-v>")
        self.unbind("<Control-V>")
        self.unbind("<Control-x>")
        self.unbind("<Control-X>")
        self.unbind("<Control-a>")
        self.unbind("<Control-A>")
        self.unbind("<Button-2>")
        self.unbind("<Button-3>")
        self.unbind("<KeyRelease>")
        self.lang = None
        self.is_listbox_entry = None
        self.select = None
        self.border_color = None
        self.teraterm_ui = None
        self.context_menu = None
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._undo_stack = None
        self._redo_stack = None
        super().destroy()


class CustomComboBox(customtkinter.CTkComboBox):
    __slots__ = ("master", "teraterm_ui_instance")

    def __init__(self, master, teraterm_ui_instance, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        initial_state = self.get()
        self._undo_stack = deque([initial_state], maxlen=25)
        self._redo_stack = deque(maxlen=25)
        self.border_color = None

        self.teraterm_ui = teraterm_ui_instance
        self.bind("<FocusIn>", self.disable_slider_keys)
        self.bind("<FocusOut>", self.enable_slider_keys)

        # Bind Control-Z to undo and Control-Y to redo
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-Z>", self.undo)
        self.bind("<Control-y>", self.redo)
        self.bind("<Control-Y>", self.redo)

        # Bind Ctrl+V to custom paste method
        self.bind("<Control-v>", self.custom_paste)
        self.bind("<Control-V>", self.custom_paste)
        # Bind Ctrl+X to custom cut method
        self.bind("<Control-x>", self.custom_cut)
        self.bind("<Control-X>", self.custom_cut)

        self.bind("<Control-a>", self.select_all)
        self.bind("<Control-A>", self.select_all)

        self.bind("<Button-2>", self.custom_middle_mouse)
        # Update the undo stack every time the Entry content changes
        self.bind("<KeyRelease>", self.update_undo_stack)

    def disable_slider_keys(self, event=None):
        if self.cget("border_color") == "#c30101":
            if self.border_color is None:
                self.border_color = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"]
            self.configure(border_color=self.border_color)

        self.teraterm_ui.move_slider_left_enabled = False
        self.teraterm_ui.move_slider_right_enabled = False
        self.teraterm_ui.up_arrow_key_enabled = False
        self.teraterm_ui.down_arrow_key_enabled = False

    def enable_slider_keys(self, event=None):
        self.teraterm_ui.move_slider_left_enabled = True
        self.teraterm_ui.move_slider_right_enabled = True
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

    def custom_middle_mouse(self, event=None):
        if self._entry.select_present():
            char_index = self._entry.index("@%d" % event.x)
            self._entry.icursor(char_index)
            self._entry.select_clear()
            return "break"

    def custom_cut(self, event=None):
        self.cut()
        return "break"

    def cut(self):
        self.focus_set()
        if not self._entry.select_present():
            self._entry.select_range(0, "end")
        try:
            selected_text = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self._entry.delete(tk.SEL_FIRST, tk.SEL_LAST)

            new_text = self.get()
            # Update the undo stack after cut operation
            self._undo_stack.append(new_text)
            # Clear the redo stack
            self._redo_stack.clear()
        except tk.TclError:
            print("No text selected to cut.")

    def copy(self):
        self.focus_set()
        if not self._entry.select_present():
            self._entry.select_range(0, "end")
        try:
            selected_text = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            print("No text selected to copy.")

    def select_all(self, event=None):
        if self.cget("state") == "disabled":
            return

        self.focus_set()
        self._entry.icursor(tk.END)
        try:
            if self._entry.select_present():
                self._entry.select_clear()
            else:
                # Select all text if nothing is selected
                self._entry.select_range(0, "end")
                self._entry.icursor("end")
        except tk.TclError:
            # No text was selected, so select all
            self._entry.select_range(0, "end")
            self._entry.icursor("end")
        return "break"

    def custom_paste(self, event=None):
        self.paste()
        return "break"

    def paste(self, event=None):
        self.focus_set()
        try:
            clipboard_text = self.clipboard_get()
            max_paste_length = 250  # Set a limit for the max paste length
            if len(clipboard_text) > max_paste_length:
                clipboard_text = clipboard_text[:max_paste_length]  # Truncate to max length
                print("Pasted content truncated to maximum length.")

            current_text = self.get()
            # Save the current state to undo stack
            if len(self._undo_stack) == 0 or (len(self._undo_stack) > 0 and current_text != self._undo_stack[-1]):
                self._undo_stack.append(current_text)

            try:
                start_index = self._entry.index(tk.SEL_FIRST)
                end_index = self._entry.index(tk.SEL_LAST)
                self._entry.delete(start_index, end_index)
            except tk.TclError:
                pass  # Nothing selected, which is fine

            self._entry.insert(tk.INSERT, clipboard_text)

            # Update undo stack here, after paste operation
            self.update_undo_stack()

        except tk.TclError:
            pass  # Clipboard empty or other issue
        return "break"

    def destroy(self):
        self.unbind("<FocusIn>")
        self.unbind("<FocusOut>")
        self.unbind("<Control-z>")
        self.unbind("<Control-Z>")
        self.unbind("<Control-y>")
        self.unbind("<Control-Y>")
        self.unbind("<Control-v>")
        self.unbind("<Control-V>")
        self.unbind("<Control-x>")
        self.unbind("<Control-X>")
        self.unbind("<Control-a>")
        self.unbind("<Control-A>")
        self.unbind("<Button-2>")
        self.unbind("<KeyRelease>")
        self.border_color = None
        self.teraterm_ui = None
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._undo_stack = None
        self._redo_stack = None
        super().destroy()


class SmoothFadeToplevel(customtkinter.CTkToplevel):
    __slots__ = "fade_duration", "final_alpha", "alpha", "fade_direction"

    def __init__(self, fade_duration=30, final_alpha=1.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fade_duration = fade_duration
        self.final_alpha = final_alpha
        self.alpha = 0.0
        self.fade_direction = 1  # 1 for fade-in, -1 for fade-out
        self.after_idle(self._start_fade_in)

    def _start_fade_in(self):
        self.fade_direction = 1
        self._fade()

    def _fade(self):
        self.alpha += self.fade_direction * (self.final_alpha / self.fade_duration)
        self.alpha = max(0.0, min(self.alpha, self.final_alpha))
        self.attributes("-alpha", self.alpha)
        if 0.0 < self.alpha < self.final_alpha:
            self.after(5, self._fade)
        elif self.alpha <= 0.0:
            self.destroy()

    def button_event(self):
        self.fade_direction = -1
        self._fade()


class SmoothFadeInputDialog(customtkinter.CTkInputDialog):
    __slots__ = "fade_duration", "final_alpha", "alpha", "fade_direction"

    def __init__(self, fade_duration=15, final_alpha=1.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fade_duration = fade_duration
        self.final_alpha = final_alpha
        self.alpha = 0.0
        self.fade_direction = 1  # 1 for fade-in, -1 for fade-out
        self.after_idle(self._start_fade_in)

    def _start_fade_in(self):
        self.fade_direction = 1
        self._fade()

    def _fade(self):
        self.alpha += self.fade_direction * (self.final_alpha / self.fade_duration)
        self.alpha = max(0.0, min(self.alpha, self.final_alpha))
        self.attributes("-alpha", self.alpha)
        if 0.0 < self.alpha < self.final_alpha:
            self.after(5, self._fade)
        elif self.alpha <= 0.0:
            self.destroy()

    def button_event(self):
        self.fade_direction = -1
        self._fade()


class ImageSlideshow(customtkinter.CTkFrame):
    __slots__ = ("parent", "image_folder", "interval", "width", "height")

    def __init__(self, parent, image_folder, interval=3, width=300, height=200, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.slideshow_frame = parent
        self.image_folder = image_folder
        self.interval = interval
        self.width = width
        self.height = height
        self.image_files = []
        self.current_image = None

        self.load_images()
        self.index = 0  # Added index to keep track of the current position in the list

        self.label = customtkinter.CTkLabel(self, text="")
        self.label.bind("<Button-1>", lambda event: self.focus_set())
        self.label.grid(row=0, column=1)

        self.arrow_left = CustomButton(self, text="<", command=self.prev_image, width=25)
        self.arrow_left.bind("<Button-1>", lambda event: self.focus_set())
        self.arrow_left.grid(row=0, column=0)

        self.arrow_right = CustomButton(self, text=">", command=self.next_image, width=25)
        self.arrow_right.bind("<Button-1>", lambda event: self.focus_set())
        self.arrow_right.grid(row=0, column=2)

        self.after_id = self.after(1, lambda: None)
        self.bind("<Button-1>", lambda event: self.focus_set())
        self.is_running = True
        self.show_image()

    def load_images(self):
        image_files = [f for f in os.listdir(self.image_folder) if f.endswith(("png", "jpg", "jpeg"))]
        random.shuffle(image_files)
        self.image_files = image_files

    def show_image(self):
        # Delete the previous image from memory
        if hasattr(self, "current_image"):
            del self.current_image

        # Load and show the current image
        filepath = os.path.join(self.image_folder, self.image_files[self.index])
        self.current_image = customtkinter.CTkImage(
            light_image=Image.open(filepath).resize((self.width * 2, self.height * 2)),
            size=(self.width, self.height)
        )
        self.label.configure(image=self.current_image)

        self.after_cancel(self.after_id)  # Cancel the existing timer
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
        self.after_cancel(self.after_id)  # Cancel the existing timer
        self.is_running = False  # Set the flag to indicate that the slideshow is not running

    def resume_cycle(self):
        if not self.is_running:  # Only resume if it is not already running
            self.is_running = True  # Set the flag to indicate that the slideshow is running
            self.reset_timer()  # Reset the timer to resume cycling of images

    def reset_timer(self):
        if self.is_running:  # Only reset the timer if the slideshow is running
            self.after_cancel(self.after_id)  # Cancel the existing timer if any
            # Set a new timer to cycle images
            self.after_id = self.after(self.interval * 1000, self.cycle_images)


def get_window_rect(hwnd):
    class RECT(ctypes.Structure):
        _fields_ = [("left", wintypes.LONG),
                    ("top", wintypes.LONG),
                    ("right", wintypes.LONG),
                    ("bottom", wintypes.LONG)]

    rect = RECT()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    DwmGetWindowAttribute = ctypes.windll.dwmapi.DwmGetWindowAttribute
    DwmGetWindowAttribute.restype = wintypes.LONG
    DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.POINTER(RECT), wintypes.DWORD]
    DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def get_idle_duration():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint),
                    ("dwTime", ctypes.c_uint)]

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        raise ctypes.WinError()
    millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return millis / 1000.0


def bring_to_front():
    def restore_window(title_win):
        t_hwnd = win32gui.FindWindow(None, title_win)
        if t_hwnd:
            if not win32gui.IsWindowVisible(t_hwnd):
                win32gui.ShowWindow(t_hwnd, SW_SHOW)
            win32gui.ShowWindow(t_hwnd, SW_RESTORE)
        return t_hwnd

    window_titles = {
        "main_app": ["Tera Term UI", "Tera Term UI"],
        "loading_screen": ["Processing...", "Procesando..."],
        "status": ["Status", "Estado"],
        "help": ["Help", "Ayuda"],
        "timer": ["Auto-Enroll", "Auto-Matrícula"],
        "tera_term_vt": ["uprbay.uprb.edu - Tera Term VT", "uprbay.uprb.edu - Tera Term VT"]
    }

    for title in window_titles["loading_screen"]:
        loading_screen_hwnd = win32gui.FindWindow(None, title)
        if loading_screen_hwnd and win32gui.IsWindowVisible(loading_screen_hwnd):
            return

    for title in window_titles["main_app"]:
        main_window_hwnd = win32gui.FindWindow(None, title)
        if main_window_hwnd:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                window = windows[0]
                if window.visible:
                    if window.isMinimized:
                        window.restore()
                    try:
                        window.activate()
                    except:
                        pass
                    return

    for window_type, titles in window_titles.items():
        for title in titles:
            hwnd = restore_window(title)
            if window_type == "main_app" and hwnd:
                main_window_hwnd = hwnd
                try:
                    win32gui.SetForegroundWindow(main_window_hwnd)
                except:
                    pass


def main():
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
        bring_to_front()
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as error:
        SPANISH = 0x0A
        language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if language_id & 0xFF == SPANISH:
            messagebox.showerror("Error", "Ocurrió un error inesperado: " + str(error) +
                                 "\n\nPuede que necesite reinstalar la aplicación")
        else:
            messagebox.showerror("Error", "An unexpected error occurred: " + str(error) +
                                 "\n\nMight need to reinstall the application")
        sys.exit(1)


if __name__ == "__main__":
    main()
