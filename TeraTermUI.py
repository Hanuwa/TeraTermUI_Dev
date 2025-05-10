# PROGRAM NAME - Tera Term UI

# PROGRAMMER - Armando Del Valle Tejada

# DESCRIPTION - Controls The application called Tera Term through a GUI interface to make the process of
# enrolling classes for the university of Puerto Rico at Bayamon easier

# DATE - Started 1/1/23, Current Build v0.92.0 - 5/10/25

# BUGS / ISSUES:
# pytesseract integration is inconsistent across systems, sometimes failing to read the screen
# accurately and processing slowly.
# The application can feel sluggish and would benefit from performance optimizations.
# UI layout (widget grid and placement) needs refinement for better usability.
# Option Menu does not yet support all Tera Term screens.
# Project lacks sufficient documentation for contributors.

# FUTURE PLANS:
# Display more in-app information to reduce reliance on Tera Term.
# Refactor the codebase into multiple files; current single-file structure (14,400+ lines) hinders maintainability.
# Redesign UI layout for clarity and better user experience.
# Expand documentation to support development and onboarding.

import asyncio
import atexit
import base64
import ctypes
import customtkinter
import gc
import json
import locale
import logging
import os
import platform
import psutil
import pygetwindow as gw
import pyperclip
import pystray
import pytesseract
import pytz
import random
import re
import requests
import shutil
import socket
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import time
import traceback
import unicodedata
import warnings
import weakref
import webbrowser
import win32clipboard
import win32con
import win32cred
import win32crypt
import win32gui
import win32security
import winsound
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from Cryptodome.Cipher import AES
from Cryptodome.Hash import HMAC, SHA256
from Cryptodome.Protocol.KDF import HKDF
from Cryptodome.Random import get_random_bytes
from CTkMessagebox import CTkMessagebox
from CTkTable import CTkTable
from CTkToolTip import CTkToolTip
from ctypes import wintypes
from datetime import datetime, timedelta, UTC
from difflib import SequenceMatcher, get_close_matches
from filelock import FileLock, Timeout
from functools import wraps, lru_cache
from hmac import compare_digest
from mss import mss
from pathlib import Path
from PIL import Image
from py7zr import SevenZipFile
from tkinter import filedialog
from tkinter import messagebox

MAX_RESTARTS = 3
restart_count = 0
try:
    if len(sys.argv) > 1:
        try:
            restart_count = int(sys.argv[1])
        except ValueError:
            pass
    sys.coinit_flags = 2
    warnings.filterwarnings("ignore", message="Apply externally defined coinit_flags: 2")
    import comtypes.stream
    from pywinauto.application import Application, AppStartError
    from pywinauto.findwindows import ElementNotFoundError
    from pywinauto import timings
except Exception as e:
    logging.error(f"Error occurred: {e}")
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
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
gc.set_threshold(5000, 100, 100)
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Measures the time it takes for the app to log-in
def measure_time(threshold):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            result = func(self, *args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            logging.info(f"Elapsed startup time: {elapsed_time:.2f} seconds")
            game_launchers = ["EpicGamesLauncher.exe", "SteamWebHelper.exe",
                              "RiotClientServices.exe", "RockstarService.exe"]
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
        offset_x = 90
        offset_y = 50
        x = (screen_width - width * scaling_factor) / 2 + offset_x
        y = (screen_height - height * scaling_factor) / 2 + offset_y
        self.geometry(f"{width}x{height}+{int(x)}+{int(y)}")
        self.icon_path = TeraTermUI.get_absolute_path("images/tera-term.ico")
        self.iconbitmap(self.icon_path)
        self.bind("<Button-2>", lambda event: self.focus_set())
        self.bind("<Button-3>", lambda event: self.focus_set())

        # creates separate threads from the main application
        self.last_activity = None
        self.idle_threshold = None
        self.use_temp_threshold = False
        self.stop_check_idle = threading.Event()
        self.stop_check_process = threading.Event()
        self.thread_pool = ThreadPoolExecutor(max_workers=5)
        self.future_tesseract = None
        self.future_backup = None
        self.future_feedback = None
        self.lock_thread = threading.Lock()

        # GitHub's information for feedback and key data for updating app
        self.SERVICE_ACCOUNT_FILE = TeraTermUI.get_absolute_path("feedback.zip")
        self.REAZIONE = self.ottenere_protetta_salasana()
        self.USER_APP_VERSION = "0.92.0"
        self.mode = "Portable"
        self.updater_hash = "5f6f57ad40db84e67c80d6e290c86c722b4a66a2188d697dc089326c3643ee62"
        self.running_updater = False
        self.credentials = None
        # disabled/enables keybind events
        self.move_slider_left_enabled = True
        self.move_slider_right_enabled = True
        self.debounce_slider = None
        self.up_arrow_key_enabled = True
        self.down_arrow_key_enabled = True

        # Installer Directories
        scope, _ = TeraTermUI.get_installation_scope()
        if self.mode == "Installation":
            if scope in ["all_users", "current_user"]:
                appdata_path = os.environ.get("PROGRAMDATA") if scope == "all_users" else os.environ.get("APPDATA")
                tera_path = os.path.join(appdata_path, "TeraTermUI")
                self.db_path = os.path.join(tera_path, "database.db")
                self.ath = os.path.join(tera_path, "feedback.zip")
                self.logs = os.path.join(tera_path, "logs.txt")
                self.crypto = SecureDataStore(key_path=os.path.join(tera_path, "masterkey.json"))
        else:
            self.crypto = SecureDataStore()

        # Instance variables not yet needed but defined
        # to avoid the instance attribute defined outside __init__ warning
        self.uprbay_window = None
        self.host_entry_saved = None
        self.uprb = None
        self.uprb_32 = None
        self.tera_term_window = None
        self.select_screen_item = None
        self.server_status = None
        self.timer_window = None
        self.timer_label = None
        self.timer_header = None
        self.server_rating = None
        self.cancel_button = None
        self.pr_date = None
        self.running_countdown = None
        self.booting_in_progress = False
        self.progress_bar = None
        self.loading_label = None
        self.check_idle_thread = None
        self.check_process_thread = None
        self.idle_num_check = None
        self.idle_warning = None
        self.back_checkbox_state = None
        self.exit_checkbox_state = None
        self.get_class_for_table = None
        self.get_semester_for_table = None
        self.show_all_sections = None
        self.download_search_pdf = None
        self.download_enrolled_pdf = None
        self.sort_by = None
        self.sort_by_tooltip = None
        self.last_sort_option = ()
        self.download_enrolled_pdf_tooltip = None
        self.table_count_tooltip = None
        self.table_position_tooltip = None
        self.previous_button_tooltip = None
        self.next_button_tooltip = None
        self.remove_button_tooltip = None
        self.download_search_pdf_tooltip = None
        self.tooltip = None
        self.notice_user_text = None
        self.notice_user_msg = None
        self.last_closing_time = None
        self.is_exit_dialog_open = False
        self.dialog = None
        self.dialog_input = None
        self.ask_semester_refresh = True

        self.images = {
            "folder": {"path": os.path.join("images", "folder.png"), "size": (18, 18)},
            "fix": {"path": os.path.join("images", "fix.png"), "size": (15, 15)},
            "error": {"path": os.path.join("images", "error.png"), "size": (100, 100)},
            "information": {"path": os.path.join("images", "info.png"), "size": (100, 100)},
            "success": {"path": os.path.join("images", "success.png"), "size": (200, 150)},
            "status": {"path": os.path.join("images", "home.png"), "size": (20, 20)},
            "help": {"path": os.path.join("images", "setting.png"), "size": (18, 18)},
            "uprb": {"path": os.path.join("images", "uprb.jpg"), "size": (300, 100)},
            "lock": {"path": os.path.join("images", "lock.png"), "size": (75, 75)},
            "update": {"path": os.path.join("images", "update.png"), "size": (15, 15)},
            "link": {"path": os.path.join("images", "link.png"), "size": (15, 15)},
            "plane": {"path": os.path.join("images", "plane.png"), "size": (18, 18)},
            "arrows": {"path": os.path.join("images", "arrows.png"), "size": (18, 18)}
        }
        self.loaded_images= {}
        self.url_cache = {}

        # path for tesseract application
        self.zip_path = os.path.join(os.path.dirname(__file__), TeraTermUI.get_absolute_path("Tesseract-OCR.7z"))
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
        self.language_menu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["English", "Español"],
                                                         canvas_takefocus=False, command=self.change_language_event,
                                                         corner_radius=13)
        self.language_menu.grid(row=6, column=0, padx=20, pady=(10, 10))
        # Storing translations for languages in cache to reuse
        SPANISH = 0x0A
        language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if language_id & 0xFF == SPANISH:
            self.language_menu.set("Español")
        self.translations_cache = {}
        self.curr_lang = self.language_menu.get()
        translation = self.load_language()
        self.status_button = CustomButton(master=self.sidebar_frame, text=translation["status_button"],
                                          image=self.get_image("status"), command=self.status_button_event, anchor="w")
        self.status_tooltip = CTkToolTip(self.status_button, message="See the status and the state\n"
                                                                     " of the application", bg_color="#1E90FF")
        self.status_button.grid(row=1, column=0, padx=20, pady=10)
        self.help_button = CustomButton(master=self.sidebar_frame, text=translation["help_button"],
                                        image=self.get_image("help"), command=self.help_button_event, anchor="w")
        self.help_tooltip = CTkToolTip(self.help_button, message=translation["help_tooltip"],
                                       bg_color="#1E90FF")
        self.help_button.grid(row=2, column=0, padx=20, pady=10)
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text=translation["option_label"], anchor="w")
        self.scaling_label_tooltip = CTkToolTip(self.scaling_label, message=translation["option_label_tooltip"],
                                                bg_color="#1E90FF")
        self.scaling_label.bind("<Button-1>", lambda event: self.focus_set())
        self.scaling_label.grid(row=5, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame, corner_radius=13, canvas_takefocus=False, values=[
                translation["dark"], translation["light"], translation["default"]],
            command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.set(translation["default"])
        self.curr_appearance = self.appearance_mode_optionemenu.get()
        self.appearance_mode_optionemenu.grid(row=7, column=0, padx=20, pady=(10, 10))
        self.scaling_slider = customtkinter.CTkSlider(self.sidebar_frame, from_=97, to=103, number_of_steps=2,
                                                      width=150, height=20, command=self.change_scaling_event)
        self.scaling_slider.set(100)
        self.scaling_tooltip = CTkToolTip(self.scaling_slider, message=f"{self.scaling_slider.get():.0f}%",
                                          bg_color="#1E90FF")
        self.curr_scaling = self.scaling_slider.get() / 100
        self.last_scaling_value = self.curr_scaling
        self.last_scaling_update = 0
        self.scaling_slider.grid(row=8, column=0, padx=20, pady=(10, 20))
        self.bind("<Left>", self.move_slider_left)
        self.bind("<Right>", self.move_slider_right)
        self.bind("<Control-MouseWheel>", self.move_slider)

        # create main entry
        self.home_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.home_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.home_frame.grid(row=0, column=1, rowspan=5, columnspan=5, padx=(0, 0), pady=(0, 0))
        self.introduction = customtkinter.CTkLabel(self.home_frame, text=translation["introduction"],
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        self.introduction.bind("<Button-1>", lambda event: self.focus_set())
        self.introduction.grid(row=0, column=1, columnspan=2, padx=(20, 0), pady=(20, 0))
        self.host = customtkinter.CTkLabel(self.home_frame, text=translation["host"])
        self.host.grid(row=2, column=1, padx=(0, 170), pady=(15, 15))
        self.host.bind("<Button-1>", lambda event: self.focus_set())
        self.host_entry = CustomEntry(self.home_frame, self, self.language_menu.get(),
                                      placeholder_text=translation["host_placeholder"])
        self.host_entry.grid(row=2, column=1, padx=(20, 0), pady=(15, 15))
        self.host_tooltip = CTkToolTip(self.host_entry, message=translation["host_tooltip"],
                                       bg_color="#1E90FF")
        self.log_in = CustomButton(master=self.home_frame, border_width=2, text=translation["log_in"],
                                   text_color=("gray10", "#DCE4EE"), command=self.login_event_handler)
        self.log_in.grid(row=3, column=1, padx=(20, 0), pady=(15, 15))
        self.log_in.configure(state="disabled")
        self.slideshow_frame = ImageSlideshow(self.home_frame, TeraTermUI.get_absolute_path("slideshow"),
                                              interval=5, width=300, height=150)
        self.slideshow_frame.grid(row=1, column=1, padx=(20, 0), pady=(140, 0))
        self.intro_box = CustomTextBox(self.home_frame, self, read_only=True, lang=self.language_menu.get(),
                                       height=120, width=400)
        self.intro_box.insert("0.0", translation["intro_box"])
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
        self.curr_skipping_auth = False

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
        self.remember_me = None
        self.remember_me_tooltip = None
        self.system = None
        self.back_student = None
        self.back_student_tooltip = None
        self.save_timer = None
        self.focus_screen = True
        self.must_save_user_data = False
        self.last_save_time = 0

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
        self.e_class = None
        self.e_class_entry = None
        self.e_section = None
        self.e_section_entry = None
        self.e_section_tooltip = None
        self.e_semester = None
        self.e_semester_entry = None
        self.semesters_tooltips = None
        self.radio_var = None
        self.register = None
        self.register_tooltip = None
        self.drop = None
        self.drop_tooltip = None
        self.submit = None
        self.enrollment_error_messages = {
            "INVALID COURSE ID": "INVALID COURSE ID", "COURSE RESERVED": "COURSE RESERVED",
            "COURSE CLOSED": "COURSE CLOSED", "CRS ALRDY TAKEN/PASSED": "CRS ALRDY TAKEN/PASSED",
            "Closed by Spec-Prog": "Closed by Spec-Prog", "Pre-Req": "Pre-Req Rqd",
            "Closed by College": "Closed by College", "Closed by Major": "Closed by Major",
            "TERM MAX HRS EXCEEDED": "TERM MAX HRS EXCEEDED", "REQUIRED CO-REQUISITE": "REQUIRED CO-REQUISITE",
            "CO-REQUISITE MISSING": "CO-REQUISITE MISSING", "ILLEGAL DROP-NOT ENR": "ILLEGAL DROP-NOT ENR",
            "NEW COURSE,NO FUNCTION": "NEW COURSE, NO FUNCTION", "PRESENTLY ENROLLED": "PRESENTLY ENROLLED",
            "PRESENTLY RECOMMENDED": "PRESENTLY RECOMMENDED", "COURSE IN PROGRESS": "COURSE IN PROGRESS", "R/TC": "R/TC"
        }

        # Second Tab
        self.class_table_pairs = []
        self.hidden_tables = []
        self.hidden_labels = []
        self.tables_checkboxes = []
        self.classes_status = {}
        self.table_tooltips = {}
        self.original_table_data = {}
        self.current_table_index = -1
        self.in_search_frame = False
        self.search_scrollbar = None
        self.title_search = None
        self.image_search = None
        self.notice_search = None
        self.s_classes = None
        self.s_class_entry = None
        self.s_semester = None
        self.s_semester_entry = None
        self.show_all = None
        self.show_all_tooltip = None
        self.search = None
        self.search_next_page = None
        self.move_tables_overlay = None
        self.move_title_label = None
        self.tables_container = None
        self.table_count = None
        self.table_pipe = None
        self.table_position = None
        self.table = None
        self.current_class = None
        self.previous_button = None
        self.next_button = None
        self.remove_button = None
        self.search_next_page_tooltip = None
        self.search_next_page_status = False

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
        self.m_swap_buttons = []
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
        self.save_class_data = None
        self.save_data_tooltip = None
        self.saved_classes = False
        self.auto_enroll = None
        self.auto_enroll_tooltip = None
        self.changed_classes = None
        self.changed_sections = None
        self.changed_semesters = None
        self.changed_registers = None

        # My Classes
        self.enrolled_header_tooltips = {}
        self.enrolled_entry_cache = {}
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
        self.keybinds_text = None
        self.keybinds = None
        self.keybinds_table = None
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
        self.courses_db_cache = None
        self.normalized_courses_cache = None
        self.curriculum_text = None
        self.curriculum = None
        self.terms_text = None
        self.enrollment_error_text = None
        self.enroll_error = None
        self.enroll_error_table = None
        self.terms = None
        self.terms_table = None
        self.delete_data_text = None
        self.delete_data = None
        self.skip_auth_text = None
        self.skip_auth_switch = None
        self.files_text = None
        self.files = None
        self.disable_idle_text = None
        self.disable_idle = None
        self.disable_audio_text = None
        self.disable_audio_tera = None
        self.disable_audio_app = None
        self.fix_text = None
        self.fix = None
        self.last_delete_time = 0

        # Top level window management, flags and counters
        self.DEFAULT_SEMESTER = TeraTermUI.calculate_default_semester()
        self.semester_values = TeraTermUI.generate_semester_values(self.DEFAULT_SEMESTER)
        self.clipboard_handler = ClipboardHandler()
        self.ssh_monitor = SSHMonitor("uprbay.uprb.edu")
        self.prev_sample_count = None
        self.search_event_completed = True
        self.option_menu_event_completed = True
        self.go_next_event_completed = True
        self.search_go_next_event_completed = True
        self.my_classes_event_completed = True
        self.fix_execution_event_completed = True
        self.submit_feedback_event_completed = True
        self.update_event_completed = True
        self.found_latest_semester = False
        self.error_occurred = False
        self.timeout_occurred = False
        self.show_fix_exe = False
        self.can_edit = False
        self.renamed_tabs = None
        self.disable_feedback = False
        self.sending_feedback = False
        self.auto_enroll_flag = False
        self.auto_enroll_focus = False
        self.auto_enroll_status = "Not Auto-Enrolling"
        self.countdown_running = False
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
        self.forceful_countdown_end = False
        self.connection_error = False
        self.check_update = False
        self.delete_tesseract_dir = False
        self.muted_tera = False
        self.beep_off_default = False
        self.muted_app = False
        self.focus_or_not = False
        self.changed_location = False
        self.auto_search = False
        self.updating_app = False
        self.main_menu = True
        self.not_rebind = False
        self.notification_sent = False
        self.boot_notified = False
        self.first_time_adding = True
        self.last_save_pdf_dir = None
        self.saved_host = None
        self.a_counter = 0
        self.m_counter = 0
        self.e_counter = 0
        self.search_function_counter = 0
        self.last_switch_time = 0
        self.last_remove_time = 0
        self.enrollment_error_check = 0
        # System tray for the application
        self.tray = pystray.Icon("tera-term", Image.open(self.icon_path), "Tera Term UI", self.create_tray_menu())
        self.tray.run_detached()
        # default location of Tera Term
        teraterm_directory = TeraTermUI.find_teraterm_directory()
        if teraterm_directory:
            self.teraterm_exe_location = os.path.join(teraterm_directory, "ttermpro.exe")
            self.teraterm_config = os.path.join(teraterm_directory, "TERATERM.ini")
            self.teraterm_directory = teraterm_directory
        else:
            main_drive = os.environ["SystemRoot"][:3]
            self.teraterm_exe_location = os.path.join(main_drive, "Program Files (x86)", "teraterm", "ttermpro.exe")
            self.teraterm_config = os.path.join(main_drive, "Program Files (x86)", "teraterm", "TERATERM.ini")
            self.teraterm_directory = os.path.join(main_drive, "Program Files (x86)", "teraterm")
        # Database
        try:
            db_path = TeraTermUI.get_absolute_path("database.db")
            if not os.path.isfile(db_path) or not os.access(db_path, os.R_OK):
                raise Exception("Database file not found")
            en_path = "translations/english.json"
            es_path = "translations/spanish.json"
            if not os.path.isfile(en_path) or not os.path.isfile(es_path):
                raise Exception("Language file not found")
            self.connection_db = sqlite3.connect(db_path, check_same_thread=False)
            self.cursor_db = self.connection_db.cursor()
            self.check_database_lock()
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.bind("<Control-space>", lambda event: self.focus_set())
            self.bind("<Escape>", lambda event: self.on_closing())
            self.bind("<Alt-F4>", lambda event: self.direct_close())
            user_data_fields = ["directory", "location", "config", "pdf_dir", "host", "language", "appearance",
                                "audio_tera", "audio_app", "scaling", "welcome", "default_semester", "skip_auth",
                                "win_pos_x", "win_pos_y"]
            results = {}
            for field in user_data_fields:
                query_user = f"SELECT {field} FROM user_config"
                result = self.cursor_db.execute(query_user).fetchone()
                results[field] = result[0] if result else None
            if results["location"]:
                if results["location"] != self.teraterm_exe_location:
                    if os.path.exists(results["location"]):
                        self.teraterm_exe_location = results["location"]
                    else:
                        self.cursor_db.execute("UPDATE user_config SET location=NULL")
            if results["directory"] and results["config"]:
                if results["directory"] != self.teraterm_directory or results["config"] != self.teraterm_config:
                    if os.path.exists(results["directory"]) and os.path.exists(results["config"]):
                        self.teraterm_config = results["config"]
                        self.teraterm_directory = results["directory"]
                        self.edit_teraterm_ini(self.teraterm_config)
                        self.can_edit = True
                    else:
                        if not os.path.exists(results["directory"]):
                            self.cursor_db.execute("UPDATE user_config SET directory=NULL")
                        if not os.path.exists(results["config"]):
                            self.cursor_db.execute("UPDATE user_config SET config=NULL")

            # performs some operations on separate threads when application starts up
            self.boot_up(self.teraterm_config)

            if results["host"]:
                self.host_entry.insert(0, results["host"])
            valid_languages = {"English", "Español"}
            valid_appearance = {"System", "Sistema", "Dark", "Oscuro", "Light", "Claro"}
            language_to_set = None
            if results["language"] and results["language"] != self.language_menu.get():
                if results["language"] in valid_languages:
                    language_to_set = results["language"]
            if language_to_set:
                self.language_menu.set(language_to_set)
                self.change_language_event(lang=language_to_set)
            if results["appearance"]:
                if results["appearance"] in valid_appearance:
                    current_appearance = self.appearance_mode_optionemenu.get()
                    if results["appearance"] != current_appearance:
                        self.appearance_mode_optionemenu.set(results["appearance"])
                        self.change_appearance_mode_event(results["appearance"])
            if results["scaling"]:
                scaling_str = str(results["scaling"]).strip()
                is_numeric = scaling_str.replace(".", "", 1).isdigit() \
                    if "." in scaling_str else scaling_str.isdigit()
                if is_numeric:
                    scale_value = float(scaling_str)
                    if scale_value != 100:
                        self.scaling_slider.set(scale_value)
                        self.change_scaling_event(scale_value)
            if results["win_pos_x"] and results["win_pos_y"]:
                if results["win_pos_x"] is not None and results["win_pos_y"] is not None:
                    x_str = str(results["win_pos_x"]).strip()
                    y_str = str(results["win_pos_y"]).strip()
                    x_is_numeric = x_str.lstrip("-").isdigit()
                    y_is_numeric = y_str.lstrip("-").isdigit()
                    if x_is_numeric and y_is_numeric:
                        x_pos = int(x_str)
                        y_pos = int(y_str)
                        screen_width = self.winfo_screenwidth()
                        screen_height = self.winfo_screenheight()
                        x_pos = max(0, min(x_pos, screen_width - width))
                        y_pos = max(0, min(y_pos, screen_height - height))
                        self.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
            if results["audio_tera"] == "Disabled":
                self.muted_tera = True
            if results["audio_app"] == "Disabled":
                self.muted_app = True
            if results["pdf_dir"]:
                if os.path.isdir(results["pdf_dir"]):
                    self.last_save_pdf_dir = results["pdf_dir"]
                else:
                    self.cursor_db.execute("UPDATE user_config SET pdf_dir=NULL")
            if results["skip_auth"] == "Yes":
                self.skip_auth = True
            elif not results["skip_auth"]:
                self.ask_skip_auth = True
            if results["default_semester"]:
                values = TeraTermUI.generate_semester_values(self.DEFAULT_SEMESTER)
                if results["default_semester"] in values:
                    self.DEFAULT_SEMESTER = results["default_semester"]
                else:
                    self.cursor_db.execute("UPDATE user_config SET default_semester=NULL")
            if results["welcome"] != "Done":
                self.help_button.configure(state="disabled")
                self.status_button.configure(state="disabled")
                self.intro_box.stop_autoscroll(event=None)
                # Pop up a message that appears only the first time the user uses the application
                def show_message_box():
                    self.play_sound("welcome.wav")
                    CTkMessagebox(title=translation["welcome_title"], message=translation["welcome_message"],
                                  button_width=380)
                    self.slideshow_frame.go_to_first_image()
                    self.intro_box.restart_autoscroll()
                    self.status_button.configure(state="normal")
                    self.help_button.configure(state="normal")
                    self.log_in.configure(state="normal")
                    self.after(150, self.bind, "<Return>", lambda event: self.login_event_handler())
                    self.after(150, self.bind, "<F1>", lambda event: self.help_button_event())
                    row_check = self.cursor_db.execute("SELECT 1 FROM user_config").fetchone()
                    if not row_check:
                        self.cursor_db.execute("INSERT INTO user_config (welcome) VALUES (?)", ("Done",))
                    else:
                        self.cursor_db.execute("UPDATE user_config SET welcome=?", ("Done",))

                self.after(3500, show_message_box)
            else:
                self.log_in.configure(state="normal")
                self.bind("<Return>", lambda event: self.login_event_handler())
                self.bind("<F1>", lambda event: self.help_button_event())
                if self.crypto.creating_key_file:
                    self.creating_key_file = False
                    if self.has_saved_user_data():
                        self.cursor_db.execute("DELETE FROM user_data")
                        self.connection_db.commit()
                # Check for update for the application
                current_date = datetime.today().strftime("%Y-%m-%d")
                date_record = self.cursor_db.execute("SELECT update_date FROM user_config").fetchone()
                if date_record is None or date_record[0] is None or not date_record[0].strip() or (
                        datetime.strptime(current_date, "%Y-%m-%d")
                        - datetime.strptime(date_record[0], "%Y-%m-%d")).days >= 7:
                    try:
                        self.check_update = True
                        if asyncio.run(self.test_connection()):
                            latest_version = self.get_latest_release()
                            def enable():
                                self.log_in.configure(state="normal")
                                self.bind("<Return>", lambda event: self.login_event_handler())
                                self.bind("<F1>", lambda event: self.help_button_event())

                            if latest_version is None:
                                logging.warning("No latest release found. Starting app with the current version")
                                latest_version = self.USER_APP_VERSION
                            if not TeraTermUI.compare_versions(latest_version, self.USER_APP_VERSION):
                                self.after(1000, self.update_app, latest_version)
                                self.after(1250, enable)
                            else:
                                enable()
                    except requests.exceptions.RequestException as err:
                        logging.warning(f"Error occurred while fetching latest release information: {err}")
                        logging.warning("Please check your internet connection and try again")
        except Exception as err:
            db_path = TeraTermUI.get_absolute_path("database.db")
            en_path = TeraTermUI.get_absolute_path("translations/english.json")
            es_path = TeraTermUI.get_absolute_path("translations/spanish.json")
            logging.error(f"An unexpected error occurred: {err}")
            self.log_error()
            if not os.path.isfile(db_path) or not os.access(db_path, os.R_OK) or "database is locked" in str(err):
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
            self.end_app(forced=True)
        if TeraTermUI.is_admin():
            p = psutil.Process(os.getpid())
            p.nice(psutil.HIGH_PRIORITY_CLASS)
        atexit.register(self.cleanup_temp)
        atexit.register(self.restore_teraterm_ini, self.teraterm_config)
        self.after(0, self.unload_image("status"))
        self.after(0, self.unload_image("help"))
        self.after(0, self.set_focus_to_tkinter)

    # creates taskbar icon for the app and its options
    def create_tray_menu(self):
        translation = self.load_language()
        return pystray.Menu(
            pystray.MenuItem(translation["hide_tray"], self.hide_all_windows),
            pystray.MenuItem(translation["show_tray"], self.show_all_windows, default=True),
            pystray.MenuItem(translation["exit_tray"], self.direct_close_on_tray)
        )

    # taskbar function to hide the app completely from view
    def hide_all_windows(self):
        if self.state() == "withdrawn" or (self.loading_screen_status is not None and
                                           self.loading_screen_status.winfo_exists()):
            if self.timer_window is not None and self.timer_window.state() == "normal":
                self.timer_window.withdraw()
            return

        translation = self.load_language()
        self.withdraw()
        self.destroy_windows()
        self.slideshow_frame.pause_cycle()
        self.intro_box.stop_autoscroll(event=None)
        self.bind("<Visibility>", self.on_visibility)
        if TeraTermUI.window_exists(translation["dialog_title"]):
            my_classes_hwnd = win32gui.FindWindow(None, translation["dialog_title"])
            win32gui.PostMessage(my_classes_hwnd, win32con.WM_CLOSE, 0, 0)
        if TeraTermUI.window_exists("Tera Term"):
            file_dialog_hwnd = win32gui.FindWindow("#32770", "Tera Term")
            win32gui.PostMessage(file_dialog_hwnd, win32con.WM_CLOSE, 0, 0)
        if TeraTermUI.window_exists("Error"):
            file_dialog_hwnd = win32gui.FindWindow("#32770", "Error")
            win32gui.PostMessage(file_dialog_hwnd, win32con.WM_CLOSE, 0, 0)
        if TeraTermUI.window_exists(translation["save_pdf"]):
            file_dialog_hwnd = win32gui.FindWindow("#32770", translation["save_pdf"])
            win32gui.PostMessage(file_dialog_hwnd, win32con.WM_CLOSE, 0, 0)
        if TeraTermUI.window_exists(translation["select_tera_term"]):
            file_dialog_hwnd = win32gui.FindWindow("#32770", translation["select_tera_term"])
            win32gui.PostMessage(file_dialog_hwnd, win32con.WM_CLOSE, 0, 0)
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
        if (not TeraTermUI.window_exists("Tera Term - [disconnected] VT") and
                not TeraTermUI.window_exists("SSH Authentication") and not self.in_student_frame):
            hwnd = win32gui.FindWindow(None, "uprbay.uprb.edu - Tera Term VT")
            if hwnd and win32gui.IsWindowVisible(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)

    # taskbar function to bring back the app
    def show_all_windows(self):
        if self.state() == "normal" and (self.loading_screen_status is not None and
                                         self.loading_screen_status.winfo_exists()):
            return
        elif self.state() == "normal" and self.loading_screen_status is None:
            self.set_focus_to_tkinter()
            return

        translation = self.load_language()
        self.unbind("<Visibility>")
        self.iconify()
        if self.main_menu:
            self.slideshow_frame.resume_cycle()
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
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    def on_visibility(self, event):
        if self.main_menu:
            self.slideshow_frame.resume_cycle()

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
        translation = self.load_language()
        msg = CTkMessagebox(title=translation["exit"], message=translation["exit_message"], icon="question",
                            option_1=translation["close_tera_term"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65), delay_destroy=True,
                            button_color=("#c30101", "#c30101", "#145DA0", "use_default"),
                            option_1_type="checkbox", hover_color=("darkred", "darkred", "use_default"))
        on_exit = self.cursor_db.execute("SELECT exit FROM user_config").fetchone()
        if on_exit and on_exit[0] is not None and on_exit[0] == 1:
            msg.check_checkbox()
        self.destroy_tooltip()
        response, self.exit_checkbox_state = msg.get()
        self.is_exit_dialog_open = False
        if response == "Yes" or response == "Sí":
            self.tray.stop()
            if all(future.done() for future in [self.future_tesseract, self.future_backup, self.future_feedback]):
                self.thread_pool.shutdown(wait=False)
            else:
                for future in as_completed([self.future_tesseract, self.future_backup, self.future_feedback]):
                    future.result()
            self.stop_check_process_thread()
            self.stop_check_idle_thread()
            self.clipboard_handler.close()
            self.save_user_config()
            self.end_app()
            if self.exit_checkbox_state:
                if TeraTermUI.checkIfProcessRunning("ttermpro"):
                    if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                        try:
                            self.uprb.kill(soft=True)
                            if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                                TeraTermUI.terminate_process()
                        except Exception as err:
                            logging.warning("An error occurred: %s", err)
                            TeraTermUI.terminate_process()
                    elif (TeraTermUI.window_exists("Tera Term - [disconnected] VT") or
                          TeraTermUI.window_exists("Tera Term - [connecting...] VT")):
                        TeraTermUI.terminate_process()
            sys.exit(0)
        self.last_closing_time = current_time

    # close app without messagebox
    def direct_close(self):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            return

        hwnd = win32gui.FindWindow(None, "uprbay.uprb.edu - Tera Term VT")
        if hwnd and not win32gui.IsWindowVisible(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        self.tray.stop()
        if all(future.done() for future in [self.future_tesseract, self.future_backup, self.future_feedback]):
            self.thread_pool.shutdown(wait=False)
        else:
            for future in as_completed([self.future_tesseract, self.future_backup, self.future_feedback]):
                future.result()
        self.save_user_config(include_exit=False)
        self.end_app()
        sys.exit(0)

    def end_app(self, forced=False):
        try:
            if forced:
                self.tray.stop()
            self.destroy()
        except Exception as err:
            logging.error("Force closing due to an error: %s", err)
            self.log_error()
        finally:
            if forced:
                sys.exit(1)

    @staticmethod
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() == 1
        except Exception as err:
            logging.error(f"An error occurred: {err}")
            return False

    @staticmethod
    def get_absolute_path(relative_path):
        if os.path.isabs(relative_path):
            raise ValueError("The provided path is already an absolute path")
        try:
            absolute_path = os.path.abspath(os.path.join(os.path.dirname(__file__), relative_path))
            return absolute_path
        except Exception as err:
            logging.error(f"Error converting path '{relative_path}' to absolute path: {err}")
            raise

    @staticmethod
    def get_monitor_bounds(window_x, window_y):
        from screeninfo import get_monitors

        for monitor in get_monitors():
            if (monitor.x <= window_x < monitor.x + monitor.width and
                    monitor.y <= window_y < monitor.y + monitor.height):
                return monitor
        return get_monitors()[0]

    @staticmethod
    def set_focus_tabview(event):
        if (str(event.widget) == ".!ctktabview.!ctkframe2.!ctkframe.!canvas" or
            str(event.widget) == ".!ctktabview.!ctkcanvas" or
            str(event.widget) == ".!ctktabview.!ctkframe2.!ctkframe.!ctkcanvas"):
            event.widget.focus_set()

    @staticmethod
    def terminate_process():
        try:
            subprocess.Popen(["taskkill", "/f", "/im", "ttermpro.exe"],
                             creationflags=subprocess.CREATE_NO_WINDOW,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            logging.error("Could not terminate ttermpro.exe")

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

    @staticmethod
    def get_installation_scope():
        common_appdata_path = os.environ.get("PROGRAMDATA")
        common_install_path = os.path.join(common_appdata_path, "TeraTermUI")

        user_appdata_path = os.environ.get("APPDATA")
        user_install_path = os.path.join(user_appdata_path, "TeraTermUI")

        if os.path.exists(common_install_path):
            return "all_users", common_install_path
        elif os.path.exists(user_install_path):
            return "current_user", user_install_path
        else:
            return "not_installed", None

    def check_database_lock(self):
        try:
            self.cursor_db.execute("SELECT 1")
        except sqlite3.OperationalError as err:
            if "database is locked" in str(err):
                raise Exception("Database is locked")
            else:
                raise err

    # creates a txt file file containing logs for critical erros encountered in the app
    def log_error(self):
        import inspect

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            full_traceback = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)).strip()
            stack = inspect.stack()
            current_frame = stack[1] if len(stack) > 1 else None
            filename = current_frame.filename if current_frame else "UnknownFile"
            function = current_frame.function if current_frame else "UnknownFunction"
            lineno = current_frame.lineno if current_frame else -1

            function_info = f"{filename}:{function}:{lineno}"
            error_message = (f"[ERROR] [{self.mode}] [{self.USER_APP_VERSION}] [{timestamp}]\n"
                             f"Location: {function_info}\n{full_traceback}")
            separator = "-" * 125 + "\n"

            if self.mode == "Installation":
                scope, install_path = TeraTermUI.get_installation_scope()
                if scope in ["all_users", "current_user"]:
                    tera_term_ui_path = install_path
                else:
                    raise Exception("TeraTermUI is not installed")
                if not os.path.isdir(tera_term_ui_path):
                    raise Exception(f"Program Data directory not found at {tera_term_ui_path}")
                logs_path = os.path.join(tera_term_ui_path, "logs.txt")
            else:
                logs_path = TeraTermUI.get_absolute_path("logs.txt")

            with open(logs_path, "a", encoding="utf-8") as file:
                file.write(f"{error_message}\n{separator}")

        except Exception as err:
            logging.error(f"[LOG_ERROR_FAILURE] [{timestamp}] Could not write error log: {str(err)}")

    @staticmethod
    def secure_zeroize_string(value):
        if value:
            try:
                val_bytes = bytearray(value.encode())
                ctypes.memset(ctypes.addressof(ctypes.c_char.from_buffer(val_bytes)), 0, len(val_bytes))
            except Exception as error:
                logging.warning(f"Secure zeroize failed: {error}")

    def student_event_handler(self):
        loading_screen = self.show_loading_screen()
        future = self.thread_pool.submit(self.student_event)
        self.update_loading_screen(loading_screen, future)

    # Enter the Enrolling/Searching/Other classes screen
    def student_event(self):
        with self.lock_thread:
            try:
                self.automation_preparations()
                translation = self.load_language()
                if asyncio.run(self.test_connection()) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        student_id = self.student_id_entry.get().replace(" ", "").replace("-", "")
                        code = self.code_entry.get().replace(" ", "")
                        if ((re.match(r"^(?!000|666|9\d{2})\d{3}(?!00)\d{2}(?!0000)\d{4}$", student_id) or
                             (student_id.isdigit() and len(student_id) == 9)) and code.isdigit() and len(code) == 4):
                            if not self.wait_for_window():
                                return

                            self.uprb.UprbayTeraTermVt.type_keys("{TAB}" + student_id + code + "{ENTER}")
                            text_output = self.wait_for_response(["SIGN-IN", "ON FILE", "PIN NUMBER",
                                                                  "ERRORS FOUND"], init_timeout=False, timeout=7)
                            if "SIGN-IN" in text_output:
                                if self.remember_me.get() == "on" and self.must_save_user_data:
                                    self.encrypt_data_db(student_id, code)
                                    self.connection_db.commit()
                                TeraTermUI.secure_zeroize_string(student_id)
                                TeraTermUI.secure_zeroize_string(code)
                                self.reset_activity_timer()
                                self.start_check_idle_thread()
                                self.start_check_process_thread()
                                self.after(0, self.initialization_class)
                                self.after(0, self.destroy_student)
                                self.after(100, self.student_info_frame)
                                self.run_fix = True
                                if self.help is not None and self.help.winfo_exists():
                                    self.fix.configure(state="normal")
                                self.in_student_frame = False
                                self.switch_tab()
                            else:
                                self.after(350, self.bind, "<Return>",
                                           lambda event: self.student_event_handler())
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
                                    self.after(100, self.show_error_message, 305, 225,
                                               translation["error_student_id_code"])
                                else:
                                    self.after(100, self.show_error_message, 315, 230,
                                               translation["error_sign-in"])
                        else:
                            self.after(350, self.bind, "<Return>",
                                       lambda event: self.student_event_handler())
                            if (not student_id or not student_id.isdigit() or len(student_id) != 9) and \
                                    (not code.isdigit() or len(code) != 4):
                                self.after(0, self.student_id_entry.configure(border_color="#c30101"))
                                self.after(0, self.code_entry.configure(border_color="#c30101"))
                                self.after(100, self.show_error_message, 305, 225,
                                           translation["error_student_id_code"])
                            elif not student_id or not student_id.isdigit() or len(student_id) != 9:
                                self.after(0, self.student_id_entry.configure(border_color="#c30101"))
                                self.after(100, self.show_error_message, 315, 230,
                                           translation["error_student_id"])
                            elif not code.isdigit() or len(code) != 4:
                                self.after(0, self.code_entry.configure(border_color="#c30101"))
                                self.after(100, self.show_error_message, 315, 230, translation["error_code"])
                    else:
                        self.after(350, self.bind, "<Return>", lambda event: self.student_event_handler())
                        self.after(100, self.show_error_message, 300, 215,
                                   translation["tera_term_not_running"])
                else:
                    self.after(350, self.bind, "<Return>", lambda event: self.student_event_handler())
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                self.reset_activity_timer()
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        self.play_sound("notification.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.after(350, self.bind, "<Return>", lambda event: self.student_event_handler())
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_automation)
                TeraTermUI.manage_user_input()

    def student_info_frame(self):
        if not self.init_multiple:
            lang = self.language_menu.get()
            self.tabview.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 85))
            self.tabview.tab(self.enroll_tab).grid_columnconfigure(1, weight=2)
            self.tabview.tab(self.search_tab).grid_columnconfigure(1, weight=2)
            self.search_scrollbar.grid_columnconfigure(1, weight=2)
            self.tabview.tab(self.other_tab).grid_columnconfigure(1, weight=2)
            self.t_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(5, 0), pady=(0, 20))
            self.t_buttons_frame.grid_columnconfigure(1, weight=2)
            self.title_enroll.grid(row=0, column=1, padx=(0, 0), pady=(10, 20), sticky="n")
            self.e_class.grid(row=1, column=1, padx=(0, 188), pady=(0, 0))
            self.e_class_entry.grid(row=1, column=1, padx=(0, 0), pady=(0, 0))
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
            self.image_search.grid(row=2, column=1, padx=(0, 0), pady=(35, 0), sticky="n")
            self.notice_search.grid(row=2, column=1, padx=(0, 0), pady=(130, 0), sticky="n")
            self.s_classes.grid(row=1, column=1, padx=(0, 550), pady=(0, 0), sticky="n")
            self.s_class_entry.grid(row=1, column=1, padx=(0, 425), pady=(0, 0), sticky="n")
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
            self.t_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(5, 0), pady=(0, 20))
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
        save = self.cursor_db.execute("SELECT class, section, semester, action FROM saved_classes"
                                   " WHERE class IS NOT NULL").fetchall()
        save_check = self.cursor_db.execute('SELECT "id" FROM saved_classes').fetchone()
        semester = self.cursor_db.execute("SELECT semester FROM saved_classes ORDER BY id LIMIT 1").fetchone()
        if save_check and save_check[0] is not None:
            if semester[0] != self.DEFAULT_SEMESTER:
                cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
                old_entries = self.cursor_db.execute("SELECT id FROM saved_classes WHERE timestamp "
                                                  "IS NULL OR timestamp < ?", (cutoff,)).fetchall()
                if old_entries:
                    self.cursor_db.execute("DELETE FROM saved_classes")
                    self.connection_db.commit()
                    return
            if save_check[0] == 1:
                self.save_class_data.select()
                self.changed_classes = set()
                self.changed_sections = set()
                self.changed_semesters = set()
                self.changed_registers = set()
                for i in range(8):
                    self.m_register_menu[i].configure(
                        command=lambda value, idx=i: self.detect_register_menu_change(value, idx))
                    self.m_classes_entry[i].bind("<FocusOut>", self.detect_change)
                    self.m_section_entry[i].bind("<FocusOut>", self.m_sections_bind_wrapper)

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
        translation = self.load_language()
        choice = self.radio_var.get()
        self.focus_set()
        if lang == "English":
            if choice == "register":
                msg = CTkMessagebox(title="Submit",
                                    message="Are you sure you are ready to " + translation["register"].lower() +
                                            " this class?\n\nREMINDER: Please make sure the information is correct",
                                    icon=TeraTermUI.get_absolute_path("images/submit.png"),
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "use_default", "use_default"))
            elif choice == "drop":
                msg = CTkMessagebox(title="Submit",
                                    message="Are you sure you are ready to " + translation[
                                        "drop"].lower() + " this class?\n\nREMINDER: Please make sure the information "
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
                                            "r esta clase?\n\nRECORDATORIO: Favor de asegurarse de que la información "
                                            "está correcta", icon=TeraTermUI.get_absolute_path("images/submit.png"),
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "use_default", "use_default"),
                                    hover_color=("darkred", "use_default", "use_default"))
            elif choice == "drop":
                msg = CTkMessagebox(title="Someter",
                                    message="¿Estás preparado para darle de " + translation["drop"].lower() +
                                            " a esta clase?\n\nRECORDATORIO: Favor de asegurarse de que la información "
                                            "está correcta", icon=TeraTermUI.get_absolute_path("images/submit.png"),
                                    option_1=translation["option_1"], option_2=translation["option_2"],
                                    option_3=translation["option_3"],
                                    icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            loading_screen = self.show_loading_screen()
            future = self.thread_pool.submit(self.submit_event)
            self.update_loading_screen(loading_screen, future)

    # function for registering/dropping classes
    def submit_event(self):
        with self.lock_thread:
            try:
                self.automation_preparations()
                translation = self.load_language()
                choice = self.radio_var.get()
                course = self.e_class_entry.get().upper().replace(" ", "").replace("-", "")
                curr_sem = translation["current"].upper()
                section = self.e_section_entry.get().upper().replace(" ", "")
                semester = self.e_semester_entry.get().upper().replace(" ", "")
                if asyncio.run(self.test_connection()) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if (choice == "register" and (
                                section not in self.classes_status or
                                self.classes_status[section]["status"] != "ENROLLED" or
                                self.classes_status[section]["semester"] != semester)) \
                                or (choice == "drop" and (
                                section not in self.classes_status or
                                self.classes_status[section]["status"] != "DROPPED" or
                                self.classes_status[section]["semester"] != semester)):
                            if (re.fullmatch("^[A-Z]{4}[0-9]{4}$", course)
                                    and re.fullmatch("^[A-Z0-9]{3}$", section)
                                    and (re.fullmatch("^[A-Z][0-9]{2}$", semester) or semester == curr_sem)):
                                if not self.wait_for_window():
                                    return
                                self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}1S4")
                                if semester == curr_sem:
                                    result = self.handle_current_semester()
                                    if result == "error":
                                        self.after(100, self.show_error_message, 300, 210,
                                                   translation["failed_enroll"])
                                        return
                                    elif result == "negative":
                                        return
                                    else:
                                        semester = result
                                self.uprb.UprbayTeraTermVt.type_keys(semester + "{ENTER}")
                                self.after(0, self.disable_go_next_buttons)
                                text_output = self.capture_screenshot()
                                count_enroll = text_output.count("ENROLLED") + text_output.count("RECOMMENDED")
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
                                    self.uprb.UprbayTeraTermVt.type_keys(course + section + "{ENTER}")
                                    text_output = self.wait_for_response(["CONFIRMED", "DROPPED"])
                                    count_enroll = text_output.count("ENROLLED") + text_output.count("RECOMMENDED")
                                    dropped_classes = "DROPPED"
                                    count_dropped = text_output.count(dropped_classes)
                                    self.reset_activity_timer()
                                    if "CONFIRMED" in text_output or "DROPPED" in text_output:
                                        self.e_class_entry.configure(state="normal")
                                        self.e_section_entry.configure(state="normal")
                                        self.e_class_entry.delete(0, "end")
                                        self.e_section_entry.delete(0, "end")
                                        self.e_class_entry.configure(state="disabled")
                                        self.e_section_entry.configure(state="disabled")
                                        self.e_counter -= count_dropped
                                        self.e_counter += count_enroll
                                        if choice == "register":
                                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                            time.sleep(1)
                                            self.classes_status[section] = {"classes": course, "status": "ENROLLED",
                                                                            "semester": semester}
                                            self.after(100, self.show_success_message, 350, 265,
                                                       translation["success_enrolled"])
                                        elif choice == "drop":
                                            self.classes_status[section] = {"classes": course, "status": "DROPPED",
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
                                        self.after(2500, self.show_enrollment_error_information,
                                                   text_output, course)
                                else:
                                    if count_enroll == 15:
                                        self.submit.configure(state="disabled")
                                        self.submit_multiple.configure(sate="disabled")
                                        self.after(100, self.show_information_message, 350, 265,
                                                   translation["enrollment_limit"])
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(
                                            self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                        self.reset_activity_timer()
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                    else:
                                        if "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" \
                                                not in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(
                                                self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                            self.reset_activity_timer()
                                            self.after(100, self.show_error_message, 300, 210,
                                                       translation["failed_enroll"])
                                            if not self.enrollment_error_check:
                                                self.submit.configure(state="disabled")
                                                self.unbind("<Return>")
                                                self.not_rebind = True
                                                self.after(2500, self.show_enrollment_error_information)
                                                self.enrollment_error_check += 1
                                        else:
                                            self.after(100, self.show_error_message, 315, 210,
                                                       translation["failed_enroll"])
                                            if not self.enrollment_error_check:
                                                self.submit.configure(state="disabled")
                                                self.unbind("<Return>")
                                                self.not_rebind = True
                                                self.after(2500, self.show_enrollment_error_information)
                                                self.enrollment_error_check += 1
                            else:
                                if not course or not section or not semester:
                                    self.after(100, self.show_error_message, 350, 230,
                                               translation["missing_info"])
                                    if not course:
                                        self.after(0, self.e_class_entry.configure(border_color="#c30101"))
                                    if not section:
                                        self.after(0, self.e_section_entry.configure(border_color="#c30101"))
                                    if not semester:
                                        self.after(0, self.e_semester_entry.configure(border_color="#c30101"))
                                elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", course):
                                    self.after(100, self.show_error_message, 360, 230,
                                               translation["class_format_error"])
                                    self.after(0, self.e_class_entry.configure(border_color="#c30101"))
                                elif not re.fullmatch("^[A-Z0-9]{3}$", section):
                                    self.after(100, self.show_error_message, 360, 230,
                                               translation["section_format_error"])
                                    self.after(0, self.e_section_entry.configure(border_color="#c30101"))
                                elif not re.fullmatch("^[A-Z][0-9]{2}$", semester) and semester != curr_sem:
                                    self.after(100, self.show_error_message, 360, 230,
                                               translation["semester_format_error"])
                                    self.after(0, self.e_semester_entry.configure(border_color="#c30101"))
                        else:
                            if section in self.classes_status and self.classes_status[section]["status"] == "ENROLLED":
                                self.after(100, self.show_error_message, 335, 240,
                                           translation["already_enrolled"])
                            elif section in self.classes_status and self.classes_status[section]["status"] == "DROPPED":
                                self.after(100, self.show_error_message, 335, 240,
                                           translation["already_dropped"])
                    else:
                        self.after(100, self.show_error_message, 300, 215,
                                   translation["tera_term_not_running"])
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                translation = self.load_language()
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        self.play_sound("notification.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_automation)
                if not self.not_rebind:
                    self.after(350, self.bind, "<Return>", lambda event: self.submit_event_handler())
                TeraTermUI.manage_user_input()

    def search_event_handler(self):
        loading_screen = self.show_loading_screen()
        future = self.thread_pool.submit(self.search_event)
        self.update_loading_screen(loading_screen, future)
        self.search_event_completed = False

    # function for searching for classes
    def search_event(self):
        with self.lock_thread:
            try:
                self.automation_preparations()
                lang = self.language_menu.get()
                translation = self.load_language()
                course = self.s_class_entry.get().upper().replace(" ", "").replace("-", "")
                semester = self.s_semester_entry.get().upper().replace(" ", "")
                curr_sem = translation["current"].upper()
                show_all = self.show_all.get()
                if asyncio.run(self.test_connection()) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if (re.fullmatch("^[A-Z]{4}[0-9]{4}$", course) and (
                                re.fullmatch("^[A-Z][0-9]{2}$", semester) or semester == curr_sem)):
                            if not self.wait_for_window():
                                return
                            self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}1CS")
                            if semester == curr_sem:
                                result = self.handle_current_semester()
                                if result == "error":
                                    self.after(100, self.show_error_message, 320, 235,
                                               translation["failed_to_search"])
                                    return
                                elif result == "negative":
                                    return
                                else:
                                    semester = result
                            self.uprb.UprbayTeraTermVt.type_keys(semester + "{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            if self.search_function_counter == 0 or semester != self.get_semester_for_table:
                                text_output = self.capture_screenshot()
                                if "INVALID TERM SELECTION" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                    self.reset_activity_timer()
                                    self.after(100, self.show_error_message, 320, 235,
                                               translation["invalid_semester"])
                                    return
                            try:
                                with self.clipboard_handler.saving():
                                    self.clipboard_handler.save_clipboard_content()
                            except Exception as err:
                                logging.error(f"An error occurred while saving clipboard content: {err}")
                            if self.search_function_counter == 0 and "\"R-AOOO7" not in text_output and \
                                    "*R-A0007" not in text_output:
                                TeraTermUI.manage_user_input()
                                self.automate_copy_class_data()
                                TeraTermUI.manage_user_input("on")
                                copy = pyperclip.paste()
                                data, course_found, invalid_action, \
                                    y_n_found, y_n_value, term_value = TeraTermUI.extract_class_data(copy)
                                if "INVALID ACTION" in copy and "LISTA DE SECCIONES" not in copy:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                    self.reset_activity_timer()
                                    self.after(100, self.show_error_message, 320, 235,
                                               translation["failed_to_search"])
                                    return
                                elif "INVALID ACTION" in copy and "LISTA DE SECCIONES" in copy:
                                    self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}SRM{ENTER}")
                                    self.reset_activity_timer()
                                    self.after(100, self.show_error_message, 320, 235,
                                               translation["failed_to_search"])
                                    return
                                if data or course_found or invalid_action or y_n_found:
                                    self.search_function_counter += 1
                                if course in copy and show_all == y_n_value and semester == term_value:
                                    if "MORE SECTIONS" in text_output:
                                        self.after(0, self.search_next_page_layout)
                                    else:
                                        def hide_next_button():
                                            self.search_next_page.grid_forget()
                                            self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
                                            self.search.configure(width=140)
                                            self.search_next_page_status = False

                                        self.after(0, hide_next_button)
                                    self.get_class_for_table = course
                                    self.get_semester_for_table = semester
                                    self.show_all_sections = show_all
                                    self.after(0, self.display_searched_class_data, data)
                                    self.clipboard_clear()
                                    try:
                                        with self.clipboard_handler.restoring():
                                            self.clipboard_handler.restore_clipboard_content()
                                    except Exception as err:
                                        logging.error(f"An error occurred while restoring clipboard content: {err}")
                                    return
                            if not (self.get_class_for_table == course and self.get_semester_for_table != semester and
                                    show_all == self.show_all_sections):
                                if self.search_function_counter == 0:
                                    self.uprb.UprbayTeraTermVt.type_keys(course)
                                if self.search_function_counter >= 1:
                                    self.uprb.UprbayTeraTermVt.type_keys("1CS" + course)
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
                                    self.after(100, self.show_error_message, 300, 220,
                                               "Error! Course: " + course + " not found")
                                elif lang == "Español":
                                    self.after(100, self.show_error_message, 310, 220,
                                               "Error! Clase: " + course + " \nno se encontro")
                                self.search_function_counter += 1
                                self.after(0, self.s_class_entry.configure(border_color="#c30101"))
                            elif "INVALID ACTION" in text_output or "INVALID TERM SELECTION" in text_output:
                                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                self.reset_activity_timer()
                                if "INVALID TERM SELECTION" in text_output:
                                    self.after(100, self.show_error_message, 320, 235,
                                               translation["invalid_semester"])
                                if "INVALID ACTION" in text_output:
                                    self.after(100, self.show_error_message, 320, 235,
                                               translation["failed_to_search"])
                                self.search_function_counter += 1
                            else:
                                TeraTermUI.manage_user_input()
                                self.automate_copy_class_data()
                                TeraTermUI.manage_user_input("on")
                                copy = pyperclip.paste()
                                data, course_found, invalid_action, y_n_found, \
                                y_n_value, term_value = TeraTermUI.extract_class_data(copy)
                                if data or course_found or invalid_action or y_n_found:
                                    self.search_function_counter += 1
                                if course in copy and show_all == y_n_value and semester == term_value:
                                    self.get_class_for_table = course
                                    self.get_semester_for_table = semester
                                    self.show_all_sections = show_all
                                self.after(0, self.display_searched_class_data, data)
                                self.clipboard_clear()
                                try:
                                    with self.clipboard_handler.restoring():
                                        self.clipboard_handler.restore_clipboard_content()
                                except Exception as err:
                                    logging.error(f"An error occurred while restoring clipboard content: {err}")
                        else:
                            if not course or not semester:
                                self.after(100, self.show_error_message, 350, 230,
                                           translation["missing_info_search"])
                                if not course:
                                    self.after(0, self.s_class_entry.configure(border_color="#c30101"))
                                if not semester:
                                    self.after(0, self.s_semester_entry.configure(border_color="#c30101"))
                            elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", course):
                                self.after(100, self.show_error_message, 360, 230,
                                           translation["class_format_error"])
                                self.after(0, self.s_class_entry.configure(border_color="#c30101"))
                            elif not re.fullmatch("^[A-Z][0-9]{2}$", semester) and semester != curr_sem:
                                self.after(100, self.show_error_message, 360, 230,
                                           translation["semester_format_error"])
                                self.after(0, self.s_semester_entry.configure(border_color="#c30101"))
                    else:
                        self.after(100, self.show_error_message, 300, 215,
                                   translation["tera_term_not_running"])
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                translation = self.load_language()
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        self.play_sound("notification.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_automation)
                self.after(350, self.bind, "<Return>", lambda event: self.search_event_handler())
                TeraTermUI.manage_user_input()
                self.search_event_completed = True

    def search_next_page_layout(self):
        self.search_next_page_status = True
        self.search.configure(width=85)
        self.search.grid(row=1, column=1, padx=(285, 0), pady=(0, 5), sticky="n")
        self.search_next_page.grid(row=1, column=1, padx=(465, 0), pady=(0, 5), sticky="n")

    def check_refresh_semester(self):
        if self.enrolled_classes_data is None or not self.ask_semester_refresh:
            return False

        translation = self.load_language()
        headers = [translation["course"], translation["m"], translation["grade"], translation["days"],
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
            self.play_sound("update.wav")
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
        translation = self.load_language()
        self.destroy_tooltip()
        if self.enrolled_classes_data is not None and not self.my_classes_frame.grid_info():
            self.tabview.grid_forget()
            self.back_classes.grid_forget()
            self.my_classes_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 100))
            self.modify_classes_frame.grid(row=2, column=2, sticky="nw", padx=(12, 0))
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
                    refresh_loading_screen = self.show_loading_screen()
                    refresh_future = self.thread_pool.submit(self.my_classes_event, self.dialog_input)
                    self.update_loading_screen(refresh_loading_screen, refresh_future)
                    self.my_classes_event_completed = False

            self.after(500, delayed_refresh_semester)
        else:
            main_window_x = self.winfo_x()
            main_window_y = self.winfo_y()
            main_window_width = self.winfo_width()
            main_window_height = self.winfo_height()
            dialog_width = 300
            dialog_height = 300
            dialog_x = main_window_x + (main_window_width // 2) - (dialog_width // 2)
            dialog_y = main_window_y + (main_window_height // 2) - (dialog_height // 2)
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            screen_x = self.winfo_vrootx()
            screen_y = self.winfo_vrooty()
            dialog_x = max(screen_x, min(dialog_x + 75, screen_width - dialog_width))
            dialog_y = max(screen_y, min(dialog_y + 60, screen_height - dialog_height))
            example = None
            if lang == "English":
                example = "   Ex. \""
            elif lang == "Español":
                example = "   Ej. \""
            self.show_classes_tooltip.hide()
            self.dialog = SmoothFadeInputDialog(
                text=f'{translation["dialog_message"]}{example}{self.DEFAULT_SEMESTER}"', lang=lang,
                title=translation["dialog_title"], ok_text=translation["submit"], cancel_text=translation["option_1"])
            self.dialog.geometry("+%d+%d" % (dialog_x, dialog_y))
            self.dialog.iconbitmap(self.icon_path)
            self.show_classes_tooltip.show()
            self.dialog.bind("<Escape>", lambda event: self.dialog.destroy())
            dialog_input = self.dialog.get_input()
            if dialog_input is not None:
                loading_screen = self.show_loading_screen()
                future = self.thread_pool.submit(self.my_classes_event, dialog_input)
                self.update_loading_screen(loading_screen, future)
                self.my_classes_event_completed = False

    # function for seeing the classes you are currently enrolled for
    def my_classes_event(self, dialog_input):
        with self.lock_thread:
            try:
                self.automation_preparations()
                translation = self.load_language()
                dialog_input = dialog_input.upper().replace(" ", "")
                curr_sem = translation["current"].upper()
                if asyncio.run(self.test_connection()) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if re.fullmatch("^[A-Z][0-9]{2}$", dialog_input) or dialog_input == curr_sem:
                            if not self.wait_for_window():
                                return
                            self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}1CP")
                            if dialog_input == curr_sem:
                                result = self.handle_current_semester()
                                if result == "error":
                                    self.after(100, self.show_error_message, 300, 215,
                                               translation["invalid_semester"])
                                    return
                                elif result == "negative":
                                    return
                                else:
                                    dialog_input = result
                            self.uprb.UprbayTeraTermVt.type_keys(dialog_input + "{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            text_output = self.capture_screenshot()
                            if "INVALID TERM SELECTION" not in text_output and "INVALID ACTION" not in text_output:
                                try:
                                    with self.clipboard_handler.saving():
                                        self.clipboard_handler.save_clipboard_content()
                                except Exception as err:
                                    logging.error(f"An error occurred while saving clipboard content: {err}")
                                TeraTermUI.manage_user_input()
                                self.automate_copy_class_data()
                                TeraTermUI.manage_user_input("on")
                                copy = pyperclip.paste()
                                enrolled_classes, total_credits = self.extract_my_enrolled_classes(copy)
                                self.after(0, self.enable_widgets, self)
                                self.after(0, self.display_enrolled_data, enrolled_classes,
                                           total_credits, dialog_input)
                                self.clipboard_clear()
                                try:
                                    with self.clipboard_handler.restoring():
                                        self.clipboard_handler.restore_clipboard_content()
                                except Exception as err:
                                    logging.error(f"An error occurred while restoring clipboard content: {err}")
                            else:
                                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                self.reset_activity_timer()
                                if "INVALID ACTION" in text_output:
                                    self.after(100, self.show_error_message, 320, 235,
                                               translation["failed_semester"])
                                else:
                                    self.after(100, self.show_error_message, 300, 215,
                                               translation["invalid_semester"])
                        else:
                            self.after(100, self.show_error_message, 300, 215,
                                       translation["invalid_semester"])
                    else:
                        self.after(100, self.show_error_message, 300, 215,
                                   translation["tera_term_not_running"])
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                translation = self.load_language()
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        self.play_sound("notification.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.switch_tab()
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_automation)
                TeraTermUI.manage_user_input()
                self.my_classes_event_completed = True

    def swap_rows(self, idx):
        if idx == 0:
            swap_idx = idx + 1
        else:
            swap_idx = idx - 1
        if swap_idx < 0 or swap_idx >= len(self.m_classes_entry):
            return

        class_text_1 = self.m_classes_entry[idx].get()
        class_text_2 = self.m_classes_entry[swap_idx].get()
        self.m_classes_entry[idx].delete(0, "end")
        self.m_classes_entry[idx].insert(0, class_text_2)
        self.m_classes_entry[idx]._activate_placeholder()
        self.m_classes_entry[swap_idx].delete(0, "end")
        self.m_classes_entry[swap_idx].insert(0, class_text_1)
        self.m_classes_entry[swap_idx]._activate_placeholder()

        section_text_1 = self.m_section_entry[idx].get()
        section_text_2 = self.m_section_entry[swap_idx].get()
        self.m_section_entry[idx].delete(0, "end")
        self.m_section_entry[idx].insert(0, section_text_2)
        self.m_section_entry[idx]._activate_placeholder()
        self.m_section_entry[swap_idx].delete(0, "end")
        self.m_section_entry[swap_idx].insert(0, section_text_1)
        self.m_section_entry[swap_idx]._activate_placeholder()

        semester_text_1 = self.m_semester_entry[idx].get()
        semester_text_2 = self.m_semester_entry[swap_idx].get()
        self.m_semester_entry[idx].set(semester_text_2)
        self.m_semester_entry[swap_idx].set(semester_text_1)

        register_text_1 = self.m_register_menu[idx].get()
        register_text_2 = self.m_register_menu[swap_idx].get()
        self.m_register_menu[idx].set(register_text_2)
        self.m_register_menu[swap_idx].set(register_text_1)

        self.check_class_conflicts()
        dummy_event_idx = type("Dummy", (object,), {"widget": self.m_section_entry[idx]})()
        dummy_event_swap_idx = type("Dummy", (object,), {"widget": self.m_section_entry[swap_idx]})()
        self.detect_change(dummy_event_idx)
        self.detect_change(dummy_event_swap_idx)

    # function that adds new entries
    def add_event(self):
        self.focus_set()
        translation = self.load_language()
        semester = self.m_semester_entry[0].get().upper().replace(" ", "")
        curr_sem = translation["current"].upper()
        if re.fullmatch("^[A-Z][0-9]{2}$", semester) or semester == curr_sem:
            if self.a_counter + 1 < len(self.m_semester_entry):
                if self.a_counter == 0 and self.m_register_menu[0].get() \
                    in [translation["register"], translation["drop"]] and self.first_time_adding:
                    if all(menu.get() == translation["choose"] for menu in self.m_register_menu[1:]):
                        action = self.m_register_menu[0].get()
                        for menu in self.m_register_menu:
                            menu.set(action)
                self.m_swap_buttons[self.a_counter + 1].grid(row=self.a_counter + 2, column=0, padx=(0, 20),
                                                             pady=(20, 0))
                self.m_num_class[self.a_counter + 1].grid(row=self.a_counter + 2, column=0, padx=(42, 0), pady=(20, 0))
                self.m_classes_entry[self.a_counter + 1].grid(row=self.a_counter + 2, column=1, padx=(0, 470),
                                                              pady=(20, 0))
                self.m_section_entry[self.a_counter + 1].grid(row=self.a_counter + 2, column=1, padx=(0, 155),
                                                              pady=(20, 0))
                self.m_semester_entry[self.a_counter + 1].configure(state="normal")
                if semester == curr_sem:
                    self.m_semester_entry[self.a_counter + 1].set(translation["current"])
                else:
                    self.m_semester_entry[self.a_counter + 1].set(semester)
                self.m_semester_entry[self.a_counter + 1].configure(state="disabled")
                self.m_semester_entry[self.a_counter + 1].grid(row=self.a_counter + 2, column=1, padx=(160, 0),
                                                               pady=(20, 0))
                self.m_register_menu[self.a_counter + 1].grid(row=self.a_counter + 2, column=1, padx=(475, 0),
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
            self.m_swap_buttons[self.a_counter + 1].grid_forget()
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
            if self.enrolled_classes_data is not None and self.my_classes_frame.grid_info():
                self.my_classes_frame.scroll_more_up()
            else:
                self.search_scrollbar.scroll_more_up()

    def move_down_scrollbar(self):
        if self.down_arrow_key_enabled:
            if self.enrolled_classes_data is not None and self.my_classes_frame.grid_info():
                self.my_classes_frame.scroll_more_down()
            else:
                self.search_scrollbar.scroll_more_down()

    def move_top_scrollbar(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            if self.enrolled_classes_data is not None and self.my_classes_frame.grid_info():
                self.my_classes_frame.scroll_to_top()
            else:
                self.search_scrollbar.scroll_to_top()

    def move_bottom_scrollbar(self):
        if self.move_slider_right_enabled or self.move_slider_left_enabled:
            if self.enrolled_classes_data is not None and self.my_classes_frame.grid_info():
                self.my_classes_frame.scroll_to_bottom()
            else:
                self.search_scrollbar.scroll_to_bottom()

    # multiple classes screen
    def multiple_classes_event(self):
        self.tabview.grid_forget()
        self.t_buttons_frame.grid_forget()
        if self.enrolled_classes_data is not None:
            translation = self.load_language()
            self.my_classes_frame.grid_forget()
            self.modify_classes_frame.grid_forget()
            self.back_my_classes.grid_forget()
            self.show_classes.configure(text=translation["show_my_classes"])
        self.destroy_tooltip()
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
        self.m_button_frame.grid(row=3, column=1, columnspan=4, rowspan=4, padx=(0, 0), pady=(0, 11))
        self.m_button_frame.grid_columnconfigure(2, weight=1)
        self.save_frame.grid(row=3, column=2, padx=(0, 50), pady=(0, 8), sticky="e")
        self.save_frame.grid_columnconfigure(2, weight=1)
        self.auto_frame.grid(row=3, column=1, padx=(50, 0), pady=(0, 8), sticky="w")
        self.auto_frame.grid_columnconfigure(2, weight=1)
        self.title_multiple.grid(row=0, column=1, padx=(0, 50), pady=(0, 20))
        self.m_class.grid(row=0, column=1, padx=(0, 470), pady=(32, 0))
        self.m_section.grid(row=0, column=1, padx=(0, 155), pady=(32, 0))
        self.m_semester.grid(row=0, column=1, padx=(160, 0), pady=(32, 0))
        self.m_choice.grid(row=0, column=1, padx=(475, 0), pady=(32, 0))
        self.m_swap_buttons[0].grid(row=1, column=0, padx=(0, 20), pady=(0, 0))
        self.m_num_class[0].grid(row=1, column=0, padx=(42, 0), pady=(0, 0))
        self.m_classes_entry[0].grid(row=1, column=1, padx=(0, 470), pady=(0, 0))
        self.m_section_entry[0].grid(row=1, column=1, padx=(0, 155), pady=(0, 0))
        self.m_semester_entry[0].grid(row=1, column=1, padx=(160, 0), pady=(0, 0))
        self.m_register_menu[0].grid(row=1, column=1, padx=(475, 0), pady=(0, 0))
        self.m_add.grid(row=3, column=0, padx=(0, 20), pady=(0, 0))
        self.back_multiple.grid(row=3, column=1, padx=(0, 20), pady=(0, 0))
        self.submit_multiple.grid(row=3, column=2, padx=(0, 0), pady=(0, 0))
        self.m_remove.grid(row=3, column=3, padx=(20, 0), pady=(0, 0))
        self.save_class_data.grid(row=0, column=0, padx=(0, 0), pady=(0, 0))
        self.auto_enroll.grid(row=0, column=0, padx=(0, 0), pady=(0, 0))

    def detect_change(self, event=None):
        self.cursor_db.execute("SELECT COUNT(*) FROM saved_classes")
        count = self.cursor_db.fetchone()[0]
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
            self.cursor_db.execute(query, (db_row_number - 1,))
            result = self.cursor_db.fetchone()
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
        self.cursor_db.execute("SELECT COUNT(*) FROM saved_classes")
        count = self.cursor_db.fetchone()[0]
        if count == 0:
            return

        register_menu = self.m_register_menu[index]
        if register_menu.get() != selected_value:
            return

        db_row_number = index + 1
        self.cursor_db.execute("SELECT action FROM saved_classes LIMIT 1 OFFSET ?", (db_row_number - 1,))
        result = self.cursor_db.fetchone()

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
            if self.save_class_data.get() == "on":
                self.save_class_data.deselect()
        else:
            if self.save_class_data.get() == "off":
                self.save_class_data.select()

    def submit_multiple_event_handler(self):
        if self.started_auto_enroll and (not self.search_event_completed or not self.option_menu_event_completed or not
                                         self.go_next_event_completed or not self.search_go_next_event_completed or not
                                         self.my_classes_event_completed or not self.fix_execution_event_completed or
                                         not self.submit_feedback_event_completed or not self.update_event_completed):
            self.after(500, self.submit_multiple_event_handler)
        elif self.started_auto_enroll:
            self.end_countdown()
            self.auto_enroll_status = "Auto-Enrolling"
            self.idle_num_check = 32
        if self.countdown_running:
            return

        translation = self.load_language()
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
        loading_screen = self.show_loading_screen()
        future = self.thread_pool.submit(self.submit_multiple_event)
        self.update_loading_screen(loading_screen, future)

    # function that enrolls multiple classes with one click
    def submit_multiple_event(self):
        with self.lock_thread:
            try:
                self.automation_preparations()
                translation = self.load_language()
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
                if asyncio.run(self.test_connection()) and self.check_server() and self.check_format():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if can_enroll_classes:
                            if not self.wait_for_window():
                                return
                            self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}1S4")
                            if semester == curr_sem:
                                result = self.handle_current_semester()
                                if result == "error":
                                    self.after(100, self.show_error_message, 330, 235,
                                               translation["failed_enroll_multiple"])
                                    return
                                elif result == "negative":
                                    return
                                else:
                                    semester = result
                            self.uprb.UprbayTeraTermVt.type_keys(semester + "{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            text_output = self.capture_screenshot()
                            count_enroll = text_output.count("ENROLLED") + text_output.count("RECOMMENDED")
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
                                    self.uprb.UprbayTeraTermVt.type_keys(classes[i] + sections[i])
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
                                    detected_errors = [msg for code, msg in self.enrollment_error_messages.items() if
                                                       code in text_output]
                                    if len(detected_errors) == 1 and "NEW COURSE,NO FUNCTION" in detected_errors:
                                        return
                                    self.submit_multiple.configure(state="disabled")
                                    self.submit_multiple.configure(state="disabled")
                                    self.unbind("<Return>")
                                    self.not_rebind = True
                                    self.after(2500, self.show_enrollment_error_information_multiple,
                                               text_output, classes)
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
                                    self.after(100, self.show_error_message, 330, 235,
                                               translation["failed_enroll_multiple"])
                                    self.submit_multiple.configure(state="disabled")
                                    self.unbind("<Return>")
                                    self.not_rebind = True
                                    self.after(2500, self.show_enrollment_error_information_multiple,
                                               text_output, classes)
                                    self.m_counter = self.m_counter - self.a_counter - 1
                            else:
                                if count_enroll == 15:
                                    self.submit.configure(state="disabled")
                                    self.submit_multiple.configure(sate="disabled")
                                    self.after(100, self.show_information_message, 350, 265,
                                               translation["enrollment_limit"])
                                if "INVALID TERM SELECTION" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                    self.reset_activity_timer()
                                    self.after(100, self.show_error_message, 300, 215,
                                               translation["invalid_semester"])
                                else:
                                    if "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" not in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                        self.reset_activity_timer()
                                    if "INVALID ACTION" in text_output and self.started_auto_enroll:
                                        self.after(0, self.submit_multiple_event_handler)
                                        self.error_auto_enroll = True
                                    else:
                                        self.after(100, self.show_error_message, 330, 235,
                                                   translation["failed_enroll_multiple"])
                                        if not self.enrollment_error_check:
                                            self.submit_multiple.configure(state="disabled")
                                            self.unbind("<Return>")
                                            self.not_rebind = True
                                            self.after(2500, self.show_enrollment_error_information)
                                            self.enrollment_error_check += 1
                        else:
                            self.after(100, self.show_error_message, 320, 235,
                                       translation["max_enroll"])
                    else:
                        self.after(100, self.show_error_message, 300, 215,
                                   translation["tera_term_not_running"])
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                translation = self.load_language()
                self.after(100, self.set_focus_to_tkinter)
                if self.auto_enroll_status == "Auto-Enrolling":
                    self.auto_enroll_status = "Not Auto-Enrolling"
                if not self.error_auto_enroll:
                    self.started_auto_enroll = False
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        self.play_sound("notification.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="question", button_width=380)
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_automation)
                if not self.not_rebind:
                    self.after(350, self.bind, "<Return>", lambda event: self.submit_multiple_event_handler())
                TeraTermUI.manage_user_input()

    def option_menu_event_handler(self):
        loading_screen = self.show_loading_screen()
        future = self.thread_pool.submit(self.option_menu_event)
        self.update_loading_screen(loading_screen, future)
        self.option_menu_event_completed = False

    # changes to the respective screen the user chooses
    def option_menu_event(self):
        with self.lock_thread:
            try:
                self.automation_preparations()
                menu = self.menu_entry.get()
                lang = self.language_menu.get()
                translation = self.load_language()
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
                if asyncio.run(self.test_connection()) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if menu and menu in valid_menu_options and (
                                re.fullmatch("^[A-Z][0-9]{2}$", semester) or semester == curr_sem):
                            if menu != "SO":
                                if not self.wait_for_window():
                                    return
                            result = None
                            if semester == curr_sem:
                                if not self.found_latest_semester:
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}")
                                result = self.handle_current_semester()
                                if result == "error":
                                    self.focus_or_not = True
                                    self.after(100, self.show_error_message, 300, 215,
                                               translation["invalid_semester"])
                                    return
                                elif result == "negative":
                                    return
                                else:
                                    semester = result
                            match menu:
                                case "SRM":
                                    if result is None:
                                        self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                case "004":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}004" + semester + "{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                case "1GP":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}1GP" + semester + "{ENTER}")
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
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                        self.reset_activity_timer()
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "118":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}118" + semester + "{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                        self.reset_activity_timer()
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "1VE":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}1VE" + semester + "{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "CONFLICT" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys("004" + semester + "{ENTER}")
                                        self.after(100, self.show_information_message, 310, 225,
                                                   translation["hold_flag"])
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
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
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}3DD" + semester + "{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "INVALID TERM SELECTION" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                        self.reset_activity_timer()
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "409":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}409" + semester + "{ENTER}")
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
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                        self.reset_activity_timer()
                                        self.after(100, self.show_error_message, 300, 215,
                                                   translation["invalid_semester"])
                                case "683":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}683" + semester + "{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "CONFLICT" in text_output:
                                        self.focus_or_not = True
                                        self.uprb.UprbayTeraTermVt.type_keys("004{ENTER}")
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
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}1PL" + semester + "{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "TERM OUTDATED" in text_output or "NO PUEDE REALIZAR CAMBIOS" in text_output or \
                                           "NO PUEDE HACER CAMBIOS" in text_output or "INVALID TERM SELECTION" \
                                            in text_output:
                                        self.focus_or_not = True
                                        if "TERM OUTDATED" in text_output or "INVALID TERM SELECTION" in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
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
                                            self.play_sound("notification.wav")
                                            CTkMessagebox(title=translation["warning_title"],
                                                          message=translation["1PL_pdata"], icon="warning",
                                                          button_width=380)
                                            self.went_to_1PL_screen = True

                                        self.focus_or_not = True
                                        self.after(100, warning)
                                case "4CM":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}4CM" + semester + "{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "TERM OUTDATED" not in text_output and "NO PUEDE REALIZAR CAMBIOS" not in \
                                            text_output and "NO PUEDE HACER CAMBIOS" not in text_output and \
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
                                    if "TERM OUTDATED" in text_output or "NO PUEDE REALIZAR CAMBIOS" in text_output or \
                                            "NO PUEDE HACER CAMBIOS" in text_output:
                                        self.focus_or_not = True
                                        if "TERM OUTDATED" in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                            self.reset_activity_timer()
                                        if lang == "English":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "Error! Failed to enter\n " + self.menu_entry.get() + " screen")
                                        elif lang == "Español":
                                            self.after(100, self.show_error_message, 325, 240,
                                                       "Error! No se pudo entrar"
                                                       "\n a la pantalla" + self.menu_entry.get())
                                case "4SP":
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}4SP" + semester + "{ENTER}")
                                    self.after(0, self.disable_go_next_buttons)
                                    text_output = self.capture_screenshot()
                                    if "TERM OUTDATED" in text_output or "NO PUEDE REALIZAR CAMBIOS" in text_output or \
                                            "NO PUEDE HACER CAMBIOS" in text_output:
                                        self.focus_or_not = True
                                        if "TERM OUTDATED" in text_output:
                                            self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
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
                                            self.play_sound("notification.wav")
                                            CTkMessagebox(title=translation["warning_title"],
                                                          message=translation["4SP_ext"], icon="warning",
                                                          button_width=380)

                                        self.focus_or_not = True
                                        self.after(100, warning)
                                case "SO":
                                    self.focus_or_not = True
                                    self.after(100, self.sign_out)
                        else:
                            self.focus_or_not = True
                            if not semester or not menu:
                                self.after(100, self.show_error_message, 350, 230,
                                           translation["menu_missing_info"])
                                if not semester:
                                    self.after(0, self.menu_semester_entry.configure(border_color="#c30101"))
                                if not menu:
                                    self.after(0, self.menu_entry.configure(border_color="#c30101"))
                            elif not re.fullmatch("^[A-Z][0-9]{2}$", semester) and semester != curr_sem:
                                self.after(100, self.show_error_message, 360, 230,
                                           translation["semester_format_error"])
                                self.after(0, self.menu_semester_entry.configure(border_color="#c30101"))
                            elif menu not in menu_dict.values():
                                self.after(100, self.show_error_message, 340, 230,
                                           translation["menu_code_error"])
                                self.after(0, self.menu_entry.configure(border_color="#c30101"))
                    else:
                        self.focus_or_not = True
                        self.after(100, self.show_error_message, 300, 215,
                                   translation["tera_term_not_running"])
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                translation = self.load_language()
                if self.focus_or_not or self.error_occurred:
                    self.after(100, self.set_focus_to_tkinter)
                else:
                    self.after(100, self.focus_tera_term)
                self.focus_or_not = False
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        self.play_sound("notification.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_automation)
                self.after(350, self.bind, "<Return>", lambda event: self.option_menu_event_handler())
                TeraTermUI.manage_user_input()
                self.option_menu_event_completed = True

    def sign_out(self):
        translation = self.load_language()
        msg = CTkMessagebox(title=translation["so_title"], message=translation["so_message"],
                            option_1=translation["option_1"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if TeraTermUI.checkIfProcessRunning("ttermpro") and response[0] == "Yes" \
                or response[0] == "Sí":
            if not self.wait_for_window():
                return
            self.uprb.UprbayTeraTermVt.type_keys("SO{ENTER}")
            self.after(0, self.disable_go_next_buttons)
        elif not TeraTermUI.checkIfProcessRunning("ttermpro") and response[0] == "Yes" \
                or response[0] == "Sí":
            self.focus_or_not = True
            self.after(100, self.show_error_message, 350, 265,
                       translation["tera_term_not_running"])

    def go_next_page_handler(self):
        loading_screen = self.show_loading_screen()
        future = self.thread_pool.submit(self.go_next_page_event)
        self.update_loading_screen(loading_screen, future)
        self.go_next_event_completed = False

    # go through each page of the different screens
    def go_next_page_event(self):
        with self.lock_thread:
            try:
                self.automation_preparations()
                translation = self.load_language()
                if asyncio.run(self.test_connection()) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if not self.wait_for_window():
                            return
                        if self._1VE_screen:
                            self.uprb.UprbayTeraTermVt.type_keys("{TAB 3}{ENTER}")
                            self.reset_activity_timer()
                        elif self._1GP_screen:
                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                            self.reset_activity_timer()
                        elif self._409_screen:
                            self.uprb.UprbayTeraTermVt.type_keys("{TAB 4}{ENTER}")
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
                                self.after(100, self.show_error_message, 310, 225,
                                           translation["unknown_error"])
                            else:
                                self.after(0, self.disable_go_next_buttons)
                    else:
                        self.after(100, self.show_error_message, 300, 215,
                                   translation["tera_term_not_running"])
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                translation = self.load_language()
                self.reset_activity_timer()
                if self.focus_or_not:
                    self.after(100, self.set_focus_to_tkinter)
                else:
                    self.after(100, self.focus_tera_term)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        self.play_sound("notification.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_automation)
                self.after(350, self.bind, "<Return>", lambda event: self.option_menu_event_handler())
                TeraTermUI.manage_user_input()
                self.go_next_event_completed = True

    def go_next_search_handler(self):
        loading_screen = self.show_loading_screen()
        future = self.thread_pool.submit(self.search_go_next)
        self.update_loading_screen(loading_screen, future)
        self.search_go_next_event_completed = False

    # Goes through more sections available for the searched class
    def search_go_next(self):
        with self.lock_thread:
            try:
                translation = self.load_language()
                self.automation_preparations()
                if asyncio.run(self.test_connection()) and self.check_server():
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if not self.wait_for_window():
                            return
                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                        time.sleep(0.5)
                        try:
                            with self.clipboard_handler.saving():
                                self.clipboard_handler.save_clipboard_content()
                        except Exception as err:
                            logging.error(f"An error occurred while saving clipboard content: {err}")
                        TeraTermUI.manage_user_input()
                        self.automate_copy_class_data()
                        TeraTermUI.manage_user_input("on")
                        copy = pyperclip.paste()
                        data, course_found, invalid_action, y_n_found \
                        , y_n_value, term_value = TeraTermUI.extract_class_data(copy)
                        self.after(0, self.display_searched_class_data, data)
                        self.clipboard_clear()
                        try:
                            with self.clipboard_handler.restoring():
                                self.clipboard_handler.restore_clipboard_content()
                        except Exception as err:
                            logging.error(f"An error occurred while restoring clipboard content: {err}")
                        self.reset_activity_timer()
                        text_output = self.capture_screenshot()
                        if "MORE SECTIONS" not in text_output:
                            def hide_next_button():
                                self.search_next_page.grid_forget()
                                self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
                                self.search.configure(width=140)
                                self.search_next_page_status = False

                            self.after(0, hide_next_button)
                        section = self.s_class_entry.get().upper().replace(" ", "").replace("-", "")
                        if section != self.get_class_for_table:
                            self.s_class_entry.configure(state="normal")
                            self.s_class_entry.delete(0, "end")
                            self.s_class_entry.insert(0, self.get_class_for_table)
                            self.s_class_entry.configure(state="disabled")
                    else:
                        self.after(100, self.show_error_message, 300, 215,
                                   translation["tera_term_not_running"])
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                translation = self.load_language()
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        self.play_sound("notification.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_automation)
                self.after(350, self.bind, "<Return>", lambda event: self.search_event_handler())
                TeraTermUI.manage_user_input()
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
        loading_screen = self.show_loading_screen()
        future = self.thread_pool.submit(self.auth_event)
        self.update_loading_screen(loading_screen, future)

    # Authentication required frame, where user is asked to input his username
    def auth_event(self):
        with self.lock_thread:
            try:
                self.automation_preparations()
                if not self.skip_auth:
                    username = self.username_entry.get().replace(" ", "").lower()
                else:
                    username = "students"
                translation = self.load_language()
                if self.skip_auth or (asyncio.run(self.test_connection()) and self.check_server()):
                    if self.skip_auth or TeraTermUI.checkIfProcessRunning("ttermpro"):
                        allowed_roles = {"students", "student", "estudiantes", "estudiante"}
                        if username in allowed_roles:
                            username = "students"
                            if not self.wait_for_window():
                                return
                            TeraTermUI.check_window_exists("SSH Authentication")
                            ssh_auth_window = self.uprb.UprbayTeraTermVt
                            user_field = ssh_auth_window.child_window(title="User name:", control_type="Edit")
                            remember_checkbox = ssh_auth_window.child_window(title="Remember password in memory",
                                                                             control_type="CheckBox")
                            plain_password_radio = ssh_auth_window.child_window(title="Use plain password to log in",
                                                                                control_type="RadioButton")
                            ok_button = ssh_auth_window.child_window(title="OK", control_type="Button")
                            user_field.set_text(username)
                            if not remember_checkbox.get_toggle_state():
                                remember_checkbox.invoke()
                            if not plain_password_radio.is_selected():
                                plain_password_radio.invoke()
                            ok_button.invoke()
                            self.server_status = self.wait_for_prompt(
                                "return to continue", "REGRESE PRONTO")
                            if self.server_status == "Maintenance message found":
                                def server_closed():
                                    if not self.skip_auth:
                                        self.back.configure(state="disabled")
                                        self.auth.configure(state="disabled")
                                    self.play_sound("error.wav")
                                    CTkMessagebox(title=translation["server_maintenance_title"],
                                                  message=translation["server_maintenance"], icon="cancel",
                                                  button_width=380)
                                    self.error_occurred = True

                                self.after(125, server_closed)
                            elif self.server_status == "Prompt found":
                                self.uprb.UprbayTeraTermVt.type_keys("^q")
                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER 3}")
                                self.move_window()
                                self.bind("<Return>", lambda event: self.student_event_handler())
                                if self.skip_auth:
                                    self.after(0, self.home_frame.grid_forget)
                                self.after(0, self.initialization_student)
                                self.after(0, self.destroy_auth)
                                self.after(100, self.auth_info_frame)
                                self.in_auth_frame = False
                                self.in_student_frame = True
                            elif self.server_status == "Timeout":
                                def timeout():
                                    if not self.skip_auth:
                                        self.back.configure(state="disabled")
                                        self.auth.configure(state="disabled")
                                    self.play_sound("error.wav")
                                    CTkMessagebox(title="Error", message=translation["timeout_server"], icon="cancel",
                                                  button_width=380)
                                    self.error_occurred = True

                                self.after(125, timeout)
                        elif username != "students":
                            self.after(350, self.bind, "<Return>", lambda event: self.auth_event_handler())
                            self.after(100, self.show_error_message, 300, 215,
                                       translation["invalid_username"])
                            self.after(0, self.username_entry.configure(border_color="#c30101"))
                    else:
                        self.after(350, self.bind, "<Return>", lambda event: self.auth_event_handler())
                        self.after(100, self.show_error_message, 300, 215,
                                   translation["tera_term_not_running"])
                else:
                    self.after(350, self.bind, "<Return>", lambda event: self.auth_event_handler())
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                self.after(125, self.set_focus_to_tkinter)
                self.reset_activity_timer()
                if self.server_status == "Maintenance message found" or self.server_status == "Timeout":
                    self.after(3500, self.go_back_home)
                elif self.error_occurred:
                    self.after(0, self.go_back_home)
                if self.log_in.cget("state") == "disabled":
                    self.log_in.configure(state="normal")
                TeraTermUI.manage_user_input()
                self.curr_skipping_auth = False

    def auth_info_frame(self):
        lang = self.language_menu.get()
        self.home_frame.grid_forget()
        self.intro_box.grid_forget()
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
            self.show.grid(row=4, column=1, padx=(0, 90), pady=(0, 10))
            self.remember_me.grid(row=4, column=1, padx=(115, 0), pady=(0, 10))
        elif lang == "Español":
            self.student_id.grid(row=2, column=1, padx=(0, 164), pady=(0, 10))
            self.student_id_entry.grid(row=2, column=1, padx=(120, 0), pady=(0, 10))
            self.code.grid(row=3, column=1, padx=(0, 125), pady=(0, 10))
            self.code_entry.grid(row=3, column=1, padx=(120, 0), pady=(0, 10))
            self.show.grid(row=4, column=1, padx=(0, 100), pady=(0, 10))
            self.remember_me.grid(row=4, column=1, padx=(125, 0), pady=(0, 10))
        self.back_student.grid(row=5, column=0, padx=(0, 10), pady=(0, 0))
        self.system.grid(row=5, column=1, padx=(10, 0), pady=(0, 0))
        self.cursor_db.execute("SELECT student_id, code, nonce_student_id, nonce_code, tag_student_id, tag_code "
                               "FROM user_data WHERE id = 1")
        row = self.cursor_db.fetchone()
        if row and all(isinstance(x, bytes) for x in row):
            student_ct, code_ct, nonce_sid, nonce_code, tag_sid, tag_code = row
            if len(nonce_sid) == 16 and len(nonce_code) == 16 and len(tag_sid) == 16 and len(tag_code) == 16:
                if os.path.exists(self.crypto.key_path):
                    try:
                        student_id = self.crypto.decrypt(student_ct, nonce_sid, tag_sid)
                        code = self.crypto.decrypt(code_ct, nonce_code, tag_code)
                        self.student_id_entry.insert(0, student_id)
                        self.code_entry.insert(0, code)
                        self.remember_me.toggle()
                    except Exception as err:
                        logging.warning(f"Decryption failed: {err}")
                        if self.has_saved_user_data():
                            self.cursor_db.execute("DELETE FROM user_data")
                            self.connection_db.commit()
                        self.crypto.reset()
                else:
                    if self.has_saved_user_data():
                        self.cursor_db.execute("DELETE FROM user_data")
                        self.connection_db.commit()
                    self.crypto.create_new_key_file()
        if self.ask_skip_auth and not self.skipped_login:
            self.unbind("<Return>")
            self.unbind("<Control-BackSpace>")
            self.system.configure(state="disabled")
            self.back_student.configure(state="disabled")
            self.after(750, self.skip_auth_prompt)

    def skip_auth_prompt(self):
        translation = self.load_language()
        self.play_sound("update.wav")
        msg = CTkMessagebox(title=translation["skip_auth_title"], message=translation["skip_auth"],
                            icon="question", option_1=translation["option_1"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        row_exists = self.cursor_db.execute("SELECT 1 FROM user_config").fetchone()
        if response[0] == "Yes" or response[0] == "Sí":
            if not row_exists:
                self.cursor_db.execute("INSERT INTO user_config (skip_auth) VALUES (?)", ("Yes",))
            else:
                self.cursor_db.execute("UPDATE user_config SET skip_auth=?", ("Yes",))
            self.skip_auth = True
        else:
            if not row_exists:
                self.cursor_db.execute("INSERT INTO user_config (skip_auth) VALUES (?)", ("No",))
            else:
                self.cursor_db.execute("UPDATE user_config SET skip_auth=?", ("No",))
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
        row_exists = self.cursor_db.execute("SELECT 1 FROM user_config").fetchone()
        if self.skip_auth_switch.get() == "on":
            if not row_exists:
                self.cursor_db.execute("INSERT INTO user_config (skip_auth) VALUES (?)", ("Yes",))
            else:
                self.cursor_db.execute("UPDATE user_config SET skip_auth=?", ("Yes",))
            self.skip_auth = True
        elif self.skip_auth_switch.get() == "off":
            if not row_exists:
                self.cursor_db.execute("INSERT INTO user_config (skip_auth) VALUES (?)", ("No",))
            else:
                self.cursor_db.execute("UPDATE user_config SET skip_auth=?", ("No",))
            self.skip_auth = False
        self.connection_db.commit()

    def notice_user(self, running_launchers):
        if self.error is not None and self.error.winfo_exists():
            return
        translation = self.load_language()
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.transient(self)
        self.tooltip.config(bg="#FFD700")
        self.tooltip.wm_geometry(f"+{main_window_x + 20}+{main_window_y + 20}")
        launcher_names = {
            "epicgameslauncher.exe": "Epic",
            "steamwebhelper.exe": "Steam",
            "riotclientservices.exe": "Riot",
            "rockstarservice.exe": "Rockstar"
        }
        if running_launchers:
            launchers_list = ", ".join([launcher_names[launcher] for launcher in running_launchers])
            text = translation["game_launchers"].format(launchers_list)
            self.notice_user_text = ("launchers", launchers_list)
        else:
            text = translation["exec_time"]
            self.notice_user_text = ("exec", translation["exec_time"])
        self.notice_user_msg = tk.Label(self.tooltip, text=text, bg="#FFD700", fg="#000", font=("Verdana", 11, "bold"))
        self.notice_user_msg.pack(padx=5, pady=5)
        self.lift_tooltip()
        if not self.skip_auth:
            self.tooltip.after(15000, self.destroy_tooltip)
        else:
            self.tooltip.after(30000, self.destroy_tooltip)
        self.tooltip.bind("<Button-1>", lambda event: self.destroy_tooltip())
        self.tooltip.bind("<Button-2>", lambda event: self.destroy_tooltip())
        self.tooltip.bind("<Button-3>", lambda event: self.destroy_tooltip())

    @staticmethod
    def check_host(host, threshold=0.8):
        def normalize_string(s):
            return "".join(
                c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn"
            ).lower().replace(",", "").replace(" ", "")

        allowed_hosts = ["uprbay.uprb.edu", "uprb", "bayamon"]
        host_normalized = normalize_string(host)

        for allowed_host in allowed_hosts:
            allowed_host_normalized = normalize_string(allowed_host)
            similarity_ratio = SequenceMatcher(None, host_normalized, allowed_host_normalized).ratio()
            if similarity_ratio >= threshold:
                return True
        return False

    def login_event_handler(self):
        loading_screen = self.show_loading_screen()
        future = self.thread_pool.submit(self.login_event)
        self.update_loading_screen(loading_screen, future)

    # logs in the user to the respective university, opens up Tera Term
    @measure_time(threshold=12)
    def login_event(self):
        with self.lock_thread:
            try:
                new_connection = False
                dont_close = False
                self.automation_preparations()
                translation = self.load_language()
                host = self.host_entry.get().replace(" ", "").lower()
                if asyncio.run(self.test_connection()) and self.check_server():
                    if TeraTermUI.check_host(host):
                        self.saved_host = host
                        TeraTermUI.check_tera_term_hidden()
                        if TeraTermUI.checkIfProcessRunning("ttermpro"):
                            count, is_multiple = TeraTermUI.countRunningProcesses("ttermpro")
                            if is_multiple:
                                self.after(100, self.show_error_message, 450, 270,
                                           translation["count_processes"])
                                self.after(350, self.bind, "<Return>",
                                           lambda event: self.login_event_handler())
                                return
                            if TeraTermUI.window_exists("Tera Term: New connection"):
                                new_connection = True
                            else:
                                self.login_to_existent_connection()
                                dont_close = True
                                return
                        try:
                            if self.teraterm5_first_boot:
                                first_boot = Application(backend="uia").start(self.teraterm_exe_location, timeout=3)
                                first_boot.window(title="Tera Term - [disconnected] VT", class_name="VTWin32",
                                                  control_type="Window").wait("visible", timeout=10)
                                first_boot.connect(title="Tera Term - [disconnected] VT", class_name="VTWin32",
                                                   control_type="Window", timeout=3)
                                first_boot.kill(soft=True)
                                self.set_focus_to_tkinter()
                            if self.download or self.teraterm_not_found or self.teraterm5_first_boot:
                                self.edit_teraterm_ini(self.teraterm_config)
                            if not new_connection:
                                self.uprb = Application(backend="uia").start(self.teraterm_exe_location, timeout=3)
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
                            if self.host_entry_saved != "uprbay.uprb.edu":
                                if self.uprbay_window.child_window(
                                        title="Continue", control_type="Button").exists(timeout=2):
                                    self.uprbay_window.child_window(title="Continue", control_type="Button").invoke()
                            if not self.skip_auth:
                                self.bind("<Return>", lambda event: self.auth_event_handler())
                                self.after(0, self.initialization_auth)
                                self.in_auth_frame = True
                            else:
                                self.after(0, self.log_in.configure(state="disabled"))
                                self.curr_skipping_auth = True
                            self.after(50, self.login_frame)
                        except AppStartError as err:
                            logging.error("An error occurred: %s", err)
                            self.after(100, self.show_error_message, 425, 330,
                                       translation["tera_term_failed_to_start"])
                            if not self.download:
                                self.after(3500, self.download_teraterm)
                                self.log_in.configure(state="disabled")
                                self.unbind("<Return>")
                                self.download = True
                            else:
                                self.after(350, self.bind, "<Return>",
                                           lambda event: self.login_event_handler())
                    else:
                        self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
                        self.after(100, self.show_error_message, 300, 215, translation["invalid_host"])
                        self.after(0, self.host_entry.configure(border_color="#c30101"))
                else:
                    self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
            except Exception as err:
                error_message = str(err)
                if "catching classes that do not inherit from BaseException is not allowed" in error_message:
                    logging.warning("Caught the specific error message: %s", error_message)
                    self.destroy_windows()
                    def rare_error():
                        self.destroy_windows()
                        self.play_sound("error.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["unexpected_error"], icon="warning", button_width=380)
                        self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())

                    self.error_occurred = False
                    self.after(100, rare_error)
                else:
                    logging.error("An error occurred: %s", error_message)
                    self.error_occurred = True
                    self.log_error()
                self.curr_skipping_auth = False
            finally:
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        if not dont_close:
                            TeraTermUI.terminate_process()
                        self.play_sound("notification.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["tera_term_forced_to_close"], icon="warning",
                                      button_width=380)
                        self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_automation)
                TeraTermUI.manage_user_input()

    def login_frame(self):
        lang = self.language_menu.get()
        if not self.skip_auth:
            self.home_frame.grid_forget()
            self.intro_box.grid_forget()
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
        translation = self.load_language()
        keywords = ["STUDENTS REQ/DROP", "HOLD FLAGS", "PROGRAMA DE CLASES", "ACADEMIC STATISTICS", "SNAPSHOT",
                    "SOLICITUD DE PRORROGA", "LISTA DE SECCIONES", "AYUDA ECONOMICA", "EXPEDIENTE ACADEMICO", "AUDIT",
                    "PERSONAL DATA", "COMPUTO DE MATRICULA", "SIGN-IN", "MORE SECTIONS EXIST"]
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
            text_output = self.capture_screenshot()
            if "PF4=exit" in text_output or "press PF4" in text_output:
                self.uprb.UprbayTeraTermVt.type_keys("^v")
                text_output = self.capture_screenshot()
            to_continue = "return to continue"
            count_to_continue = text_output.count(to_continue)
            if "REGRESE PRONTO" in text_output:
                def server_closed():
                    self.play_sound("error.wav")
                    CTkMessagebox(title=translation["server_maintenance_title"],
                                  message=translation["server_maintenance"], icon="cancel", button_width=380)
                    self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
                    self.uprb.kill(soft=True)

                self.after(125, server_closed)
                return
            elif "return to continue" in text_output or "INFORMACION ESTUDIANTIL" in text_output:
                if hwnd_tt:
                    win32gui.PostMessage(hwnd_tt, win32con.WM_CLOSE, 0, 0)
                self.uprb.UprbayTeraTermVt.type_keys("^q")
                if "return to continue" in text_output and "Loading" in text_output:
                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER 3}")
                elif count_to_continue == 2 or "ZZZ" in text_output:
                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER 2}")
                elif count_to_continue == 1 or "automaticamente" in text_output:
                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                else:
                    self.uprb.UprbayTeraTermVt.type_keys("{VK_RIGHT}{VK_LEFT}")
                self.bind("<Control-BackSpace>", lambda event: self.keybind_go_back_home())
                self.bind("<Return>", lambda event: self.student_event_handler())
                self.home_frame.grid_forget()
                self.intro_box.grid_forget()
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
                    win32gui.PostMessage(hwnd_tt, win32con.WM_CLOSE, 0, 0)
                self.uprb.UprbayTeraTermVt.type_keys("^q")
                self.uprb.UprbayTeraTermVt.type_keys("{VK_RIGHT}{VK_LEFT}")
                self.connect_to_uprb()
                self.home_frame.grid_forget()
                self.intro_box.grid_forget()
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
                self.after(100, self.show_error_message, 315, 235,
                           translation["tera_term_failed_to_connect"])
        else:
            self.after(350, self.bind, "<Return>", lambda event: self.login_event_handler())
            self.after(100, self.show_error_message, 315, 235,
                       translation["tera_term_failed_to_connect"])

    def connect_to_uprb(self):
        self.uprb = Application(backend="uia").connect(
            title="uprbay.uprb.edu - Tera Term VT", timeout=3, class_name="VTWin32", control_type="Window")
        self.uprb_32 = Application().connect(
            title="uprbay.uprb.edu - Tera Term VT", timeout=3, class_name="VTWin32")
        self.uprbay_window = self.uprb.window(title="uprbay.uprb.edu - Tera Term VT",
                                              class_name="VTWin32", control_type="Window")
        self.tera_term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
        edit_menu = self.uprb.UprbayTeraTermVt.child_window(title="Edit", control_type="MenuItem")
        self.select_screen_item = edit_menu.child_window(
            title="Select screen", control_type="MenuItem", auto_id="50280")
        self.focus_tera_term()
        self.uprbay_window.wait("visible", timeout=3)

    @staticmethod
    def new_connection(window):
        new_connection = window.child_window(title="Tera Term: New connection")
        new_connection.wait("visible", timeout=5)
        tcp_ip_radio = new_connection.child_window(title="TCP/IP", control_type="RadioButton")
        history_checkbox = new_connection.child_window(title="History", control_type="CheckBox")
        ssh_radio = new_connection.child_window(title="SSH", control_type="RadioButton")
        tcp_port_edit = new_connection.child_window(title="TCP port#:", control_type="Edit")
        ssh_version_combo = new_connection.child_window(title="SSH version:", control_type="ComboBox")
        if not tcp_ip_radio.is_selected():
            tcp_ip_radio.invoke()
        if not history_checkbox.get_toggle_state():
            history_checkbox.invoke()
        if not ssh_radio.is_selected():
            ssh_radio.invoke()
        if tcp_port_edit.get_value() != "22":
            tcp_port_edit.set_text("22")
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
        auth_err = False
        translation = self.load_language()
        if not self.error_occurred:
            msg = CTkMessagebox(title=translation["go_back_title"], message=translation["go_back"], icon="question",
                                option_1=translation["close_tera_term"], option_2=translation["option_2"],
                                option_3=translation["option_3"], icon_size=(65, 65), button_color=(
                                "#c30101", "#c30101", "#145DA0", "use_default"), option_1_type="checkbox",
                                hover_color=("darkred", "darkred", "use_default"))
            if self.back_checkbox_state == 1:
                msg.check_checkbox()
            self.destroy_tooltip()
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
                    logging.warning("An error occurred: %s", err)
                    TeraTermUI.terminate_process()
            elif (TeraTermUI.window_exists("Tera Term - [disconnected] VT") or
                  TeraTermUI.window_exists("Tera Term - [connecting...] VT")):
                if not TeraTermUI.window_exists("SSH Authentication"):
                    def error():
                        self.play_sound("error.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["auth_error"],
                                      icon="warning", button_width=380)

                    auth_err = True
                    self.after(100, error)
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
                self.intro_box.grid(row=1, column=1, padx=(20, 0), pady=(0, 150))
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
            if self.must_save_user_data and self.in_student_frame:
                student_id = self.student_id_entry.get().replace(" ", "").replace("-", "")
                code = self.code_entry.get().replace(" ", "")
                self.encrypt_data_db(student_id, code)
                self.connection_db.commit()
            if self.error_occurred:
                self.destroy_windows()
                if self.server_status != "Maintenance message found" and self.server_status != "Timeout" \
                        and self.tesseract_unzipped and not auth_err:
                    def error():
                        self.play_sound("error.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["tera_term_forced_to_close"],
                                      icon="warning", button_width=380)

                    self.after(100, error)
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
            translation = self.load_language()
            self.my_classes_frame.grid_forget()
            self.modify_classes_frame.grid_forget()
            self.back_my_classes.grid_forget()
            self.show_classes.configure(text=translation["show_my_classes"])
        self.tabview.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 85))
        self.t_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(5, 0), pady=(0, 20))
        self.back_classes.grid(row=4, column=0, padx=(0, 10), pady=(0, 0), sticky="w")
        self.in_multiple_screen = False
        self.switch_tab()

    def load_language(self):
        lang = self.language_menu.get()
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
                with open(filename, "r", encoding="utf-8") as file:
                    translations = json.load(file)
                self.translations_cache[lang] = translations
                return translations
            except Exception as err:
                logging.error("An error occurred: %s", err)
                if lang == "English":
                    messagebox.showerror("Error",
                                         "A critical error occurred while loading the languages.\n"
                                         "Might need to reinstall the program.\n\n"
                                         "The application will now exit")
                elif lang == "Español":
                    messagebox.showerror("Error",
                                         "Ocurrió un error crítico al cargar los idiomas.\n"
                                         "Puede ser que sea necesario reinstalar el programa.\n\n"
                                         "La aplicación se cerrará ahora")
                # Exit the application
                self.end_app(forced=True)

        # If the language is not supported, return an empty dictionary or raise an exception
        return {}

    def update_searched_classes_headers_tooltips(self):
        translation = self.load_language()
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
            if table.values:
                table.values[0] = new_headers
            for i, new_header in enumerate(new_headers):
                tooltip_message = tooltip_messages[new_header]
                header_cell = table.get_cell(0, i)
                if header_cell in self.table_tooltips:
                    self.table_tooltips[header_cell].configure(message=tooltip_message)

    def update_enrolled_classes_headers_tooltips(self):
        translation = self.load_language()
        tooltip_messages = {
            translation["course"]: translation["tooltip_course"],
            translation["m"]: translation["tooltip_m"],
            translation["grade"]: translation["tooltip_grd"],
            translation["days"]: translation["tooltip_days"],
            translation["times"]: translation["tooltip_times"],
            translation["room"]: translation["tooltip_croom"]
        }
        new_headers = [translation["course"], translation["m"], translation["grade"], translation["days"],
                       translation["times"], translation["room"]]
        self.enrolled_classes_table.update_headers(new_headers)
        if self.enrolled_classes_table.values:
            self.enrolled_classes_table.values[0] = new_headers
        for i, new_header in enumerate(new_headers):
            tooltip_message = tooltip_messages[new_header]
            header_cell = self.enrolled_classes_table.get_cell(0, i)
            if header_cell in self.enrolled_header_tooltips:
                self.enrolled_header_tooltips[header_cell].configure(message=tooltip_message)

    # function for changing language
    def change_language_event(self, lang):
        if self.curr_lang == lang:
            return

        translation = self.load_language()
        appearance = self.appearance_mode_optionemenu.get()
        self.curr_lang = lang
        self.focus_set()
        tray_menu_items = [
            pystray.MenuItem(translation["hide_tray"], self.hide_all_windows),
            pystray.MenuItem(translation["show_tray"], self.show_all_windows, default=True),
            pystray.MenuItem(translation["exit_tray"], self.direct_close_on_tray)
        ]
        if self.timer_window is not None and self.timer_window.winfo_exists():
            tray_menu_items.append(pystray.MenuItem(translation["countdown_win"], self.bring_back_timer_window))
        self.tray.menu = pystray.Menu(*tray_menu_items)
        self.tray.update_menu()
        self.status_button.configure(text=translation["status_button"])
        self.help_button.configure(text=translation["help_button"])
        self.scaling_label.configure(text=translation["option_label"])
        self.intro_box.configure(state="normal")
        self.intro_box.delete("1.0", "end")
        self.intro_box.insert("0.0", translation["intro_box"])
        self.intro_box.configure(state="disabled")
        self.appearance_mode_optionemenu.configure(values=[translation["dark"], translation["light"],
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
                             ["<Ctrl-MouseWheel>", translation["ctrl_mwheel"]],
                             ["<Right-Click>", translation["mouse_2"]],
                             ["<Home>", translation["home"]],
                             ["<End>", translation["end"]],
                             ["<F1>", translation["F1"]],
                             ["<Alt-F4>", translation["alt_f4"]]]
            self.keybinds_table.configure(values=self.keybinds)
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
            curriculum_mapping = {
                "Departments": "dep", "Accounting": "acc",
                "Finance": "finance", "Management": "management",
                "Marketing": "mark", "General Biology": "g_biology",
                "Biology-Human Focus": "h_biology", "Computer Science": "c_science",
                "Information Systems": "it", "Social Sciences": "s_science",
                "Physical Education": "physical", "Electronics": "elec",
                "Equipment Management": "equip", "Pedagogy": "peda",
                "Chemistry": "che", "Nursing": "nur",
                "Office Systems": "office", "Information Engineering": "engi",
                "Departamentos": "dep", "Contabilidad": "acc",
                "Finanzas": "finance", "Gerencia": "management",
                "Mercadeo": "mark", "Biología General": "g_biology",
                "Biología-Enfoque Humano": "h_biology", "Ciencias de Computadoras": "c_science",
                "Sistemas de Información": "it", "Ciencias Sociales": "s_science",
                "Educación Física": "physical", "Electrónica": "elec",
                "Gerencia de Materiales": "equip", "Pedagogía": "peda",
                "Química": "che", "Enfermería": "nur",
                "Sistemas de Oficina": "office", "Ingeniería de la Información": "engi"
            }
            current_selection = self.curriculum.get()
            translated_values = [translation["dep"], translation["acc"], translation["finance"],
                                 translation["management"], translation["mark"], translation["g_biology"],
                                 translation["h_biology"], translation["c_science"], translation["it"],
                                 translation["s_science"], translation["physical"], translation["elec"],
                                 translation["equip"], translation["peda"], translation["che"], translation["nur"],
                                 translation["office"], translation["engi"]]
            self.curriculum.configure(values=translated_values)
            selection_key = curriculum_mapping.get(current_selection)
            if selection_key and selection_key in translation:
                translated_selection = translation[selection_key]
                self.curriculum.set(translated_selection)
            else:
                self.curriculum.set(translation["dep"])
            if lang == "English":
                self.curriculum.pack(pady=(5, 0))
            elif lang == "Español":
                self.curriculum.pack(pady=(5, 20))
            self.enrollment_error_text.configure(text=translation["course_errors_title"])
            self.enroll_error = [[translation["course_error_msg"], translation["course_error_explained"]],
                                 ["INVALID COURSE ID", translation["invalid_course"]],
                                 ["COURSE RESERVED", translation["course_reserved"]],
                                 ["COURSE CLOSED", translation["course_closed"]],
                                 ["CRS ALRDY TAKEN/PASSED", translation["course_taken"]],
                                 ["Closed by Spec-Prog", translation["closed_spec"]],
                                 ["Pre-Req", translation["pre_req"]],
                                 ["Closed by College", translation["closed_college"]],
                                 ["Closed by Major", translation["closed_major"]],
                                 ["TERM MAX HRS EXCEEDED", translation["terms_max"]],
                                 ["REQUIRED CO-REQUISITE", translation["req_co_requisite"]],
                                 ["CO-REQUISITE MISSING", translation["co_requisite_missing"]],
                                 ["ILLEGAL DROP-NOT ENR", translation["illegal_drop"]],
                                 ["NEW COURSE, NO FUNCTION", translation["no_course"]],
                                 ["PRESENTLY ENROLLED", translation["presently_enrolled"]],
                                 ["PRESENTLY RECOMMENDED", translation["presently_recommended"]],
                                 ["COURSE IN PROGRESS", translation["course_progress"]],
                                 ["R/TC", translation["rtc"]]]
            self.enroll_error_table.configure(values=self.enroll_error)
            self.terms_text.configure(text=translation["terms_title"])
            self.terms = self.get_last_five_terms()
            self.terms_table.configure(values=self.terms)
            self.delete_data_text.configure(text=translation["del_data_title"])
            self.delete_data.configure(text=translation["del_data"])
            self.skip_auth_text.configure(text=translation["skip_auth_text"])
            self.skip_auth_switch.configure(text=translation["skip_auth_switch"])
            self.files_text.configure(text=translation["files_title"])
            self.files.configure(text=translation["files_button"])
            self.disable_idle_text.configure(text=translation["idle_title"])
            self.disable_idle.configure(text=translation["idle"])
            self.disable_audio_text.configure(text=translation["audio_title"])
            self.disable_audio_tera.configure(text=translation["audio_tera"])
            self.disable_audio_app.configure(text=translation["audio_app"])
            self.fix_text.configure(text=translation["fix_title"])
            self.fix.configure(text=translation["fix"])
            self.search_box.lang = lang
        if self.notice_user_text is not None:
            key, value = self.notice_user_text
            new_text = None
            if key == "launchers":
                new_text = translation["game_launchers"].format(value)
            elif key == "exec":
                new_text = translation["exec_time"]
            self.notice_user_msg.configure(text=new_text)
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
            self.username_tooltip.configure(message=translation["username_tooltip"])
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
                self.show.grid(row=4, column=1, padx=(0, 90), pady=(0, 10))
                self.remember_me.grid(row=4, column=1, padx=(115, 0), pady=(0, 10))
            elif lang == "Español":
                self.student_id.grid(row=2, column=1, padx=(0, 164), pady=(0, 10))
                self.student_id_entry.grid(row=2, column=1, padx=(120, 0), pady=(0, 10))
                self.code.grid(row=3, column=1, padx=(0, 125), pady=(0, 10))
                self.code_entry.grid(row=3, column=1, padx=(120, 0), pady=(0, 10))
                self.show.grid(row=4, column=1, padx=(0, 100), pady=(0, 10))
                self.remember_me.grid(row=4, column=1, padx=(125, 0), pady=(0, 10))
            self.student_id_tooltip.configure(message=translation["student_id_tooltip"])
            self.code_tooltip.configure(message=translation["code_tooltip"])
            self.remember_me_tooltip.configure(message=translation["remember_me_tooltip"])
            self.show.configure(text=translation["show"])
            self.remember_me.configure(text=translation["remember_me"])
            self.back_student.configure(text=translation["back"])
            self.system.configure(text=translation["system"])
        if self.init_multiple:
            self.rename_tabs()
            self.title_enroll.configure(text=translation["title_enroll"])
            self.e_class.configure(text=translation["class"])
            self.e_section.configure(text=translation["section"])
            if lang == "English":
                self.e_section.grid(row=2, column=1, padx=(0, 199), pady=(20, 0))
            elif lang == "Español":
                self.e_section.grid(row=2, column=1, padx=(0, 202), pady=(20, 0))
            self.e_semester.configure(text=translation["semester"])
            self.e_semester_entry.configure(values=["C31", "C32", "C33", "C41", "C42", "C43", translation["current"]])
            for widget in [self.e_semester_entry, self.s_semester_entry,
                           self.menu_semester_entry, self.m_semester_entry[0]]:
                if widget in self.semesters_tooltips:
                    selected_semester = widget.get().upper().replace(" ", "")
                    self.semesters_tooltips[widget].configure(message=self.get_semester_season(selected_semester))
            self.register.configure(text=translation["register"])
            self.drop.configure(text=translation["drop"])
            self.update_section_tooltip(lang)
            self.title_search.configure(text=translation["title_search"])
            self.notice_search.configure(text=translation["notice_search"])
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
            menu_mapping = {
                "SRM (Main Menu)": "SRM", "004 (Hold Flags)": "004",
                "1GP (Class Schedule)": "1GP", "118 (Academic Statistics)": "118",
                "1VE (Academic Record)": "1VE", "3DD (Scholarship Payment Record)": "3DD",
                "409 (Account Balance)": "409", "683 (Academic Evaluation)": "683",
                "1PL (Basic Personal Data)": "1PL", "4CM (Tuition Calculation)": "4CM",
                "4SP (Apply for Extension)": "4SP", "SO (Sign out)": "SO",
                "SRM (Menú Principal)": "SRM", "004 (Flags de Retención)": "004",
                "1GP (Programa de Clases)": "1GP", "118 (Estadísticas Académicas)": "118",
                "1VE (Expediente Académico)": "1VE", "3DD (Historial de Pagos de Beca)": "3DD",
                "409 (Balance de Cuenta)": "409", "683 (Evaluación Académica)": "683",
                "1PL (Datos Básicos)": "1PL", "4CM (Cómputo de Matrícula)": "4CM",
                "4SP (Solicitud de Prórroga)": "4SP", "SO (Cerrar Sesión)": "SO"
            }
            current_menu_selection = self.menu_entry.get()
            translated_menu_values = [translation["SRM"], translation["004"], translation["1GP"], translation["118"],
                                      translation["1VE"], translation["3DD"], translation["409"], translation["683"],
                                      translation["1PL"], translation["4CM"], translation["4SP"], translation["SO"]]
            self.menu_entry.configure(values=translated_menu_values)
            selection_key = menu_mapping.get(current_menu_selection)
            if selection_key and selection_key in translation:
                translated_selection = translation[selection_key]
                self.menu_entry.set(translated_selection)
            else:
                self.menu_entry.set(translation["SRM"])
            self.menu_semester.configure(text=translation["semester"])
            self.menu_semester_entry.configure(values=self.semester_values + [translation["current"]])
            if (self.e_semester_entry.get().upper().replace(" ", "") == "CURRENT" or
                    self.e_semester_entry.get().upper().replace(" ", "") == "ACTUAL"):
                self.e_semester_entry.set(translation["current"])
            if (self.s_semester_entry.get().upper().replace(" ", "") == "CURRENT" or
                    self.s_semester_entry.get().upper().replace(" ", "") == "ACTUAL"):
                self.s_semester_entry.set(translation["current"])
            if (self.menu_semester_entry.get().upper().replace(" ", "") == "CURRENT" or
                    self.menu_semester_entry.get().upper().replace(" ", "") == "ACTUAL"):
                self.menu_semester_entry.set(translation["current"])
            self.menu_submit.configure(text=translation["submit"])
            self.submit.configure(text=translation["submit"])
            self.search.configure(text=translation["search"])
            if self.enrolled_classes_data is not None and self.my_classes_frame.grid_info():
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
            semester_multiple = self.m_semester_entry[0].get().upper().replace(" ", "")
            if semester_multiple == "CURRENT" or semester_multiple == "ACTUAL":
                self.m_semester_entry[0].set(translation["current"])
                self.change_semester(translation["current"])
            self.m_choice.configure(text=translation["choice"])
            self.back_multiple.configure(text=translation["back"])
            self.submit_multiple.configure(text=translation["submit"])
            for i in range(8):
                self.m_register_menu[i].configure(values=[translation["register"], translation["drop"]])
                if self.m_register_menu[i].get() == "Choose" or self.m_register_menu[i].get() == "Escoge":
                    self.m_register_menu[i].set(translation["choose"])
                elif self.m_register_menu[i].get() == "Register" or self.m_register_menu[i].get() == "Registra":
                    self.m_register_menu[i].set(translation["register"])
                elif self.m_register_menu[i].get() == "Drop" or self.m_register_menu[i].get() == "Baja":
                    self.m_register_menu[i].set(translation["drop"])
            self.update_sections_multiple_tooltips(lang)
            self.auto_enroll.configure(text=translation["auto_enroll"])
            self.save_class_data.configure(text=translation["save_data"])
            self.register_tooltip.configure(message=translation["register_tooltip"])
            self.drop_tooltip.configure(message=translation["drop_tooltip"])
            self.back_classes_tooltip.configure(message=translation["back_tooltip"])
            self.back_multiple_tooltip.configure(message=translation["back_multiple"])
            self.show_all_tooltip.configure(message=translation["show_all_tooltip"])
            self.show_classes_tooltip.configure(message=translation["show_classes_tooltip"])
            self.m_add_tooltip.configure(message=translation["add_tooltip"])
            self.m_remove_tooltip.configure(message=translation["m_remove_tooltip"])
            self.multiple_tooltip.configure(message=translation["multiple_tooltip"])
            self.save_data_tooltip.configure(message=translation["save_data_tooltip"])
            self.auto_enroll_tooltip.configure(message=translation["auto_enroll_tooltip"])
            self.search_next_page_tooltip.configure(message=translation["search_next_page_tooltip"])
            if self.timer_window is not None and self.timer_window.winfo_exists():
                self.timer_window.title(translation["auto_enroll"])
                self.timer_header.configure(text=translation["auto_enroll_activated"])
                self.cancel_button.configure(text=translation["option_1"])
                rating, color = self.ssh_monitor.get_reliability_rating(lang)
                puerto_rico_tz = pytz.timezone("America/Puerto_Rico")
                current_date = datetime.now(puerto_rico_tz)
                time_difference = self.pr_date - current_date
                total_seconds = time_difference.total_seconds()
                self.server_rating.configure(text=f"{translation["server_status_rating"]}{rating}", text_color=color)
                self.timer_label.configure(text=self.get_countdown_message(total_seconds))
            for entry in [self.e_class_entry, self.e_section_entry, self.s_class_entry, self.m_classes_entry,
                          self.m_section_entry, self.e_semester_entry, self.s_semester_entry, self.menu_entry,
                          self.menu_semester_entry, self.m_semester_entry]:
                if isinstance(entry, list):
                    for sub_entry in entry:
                        sub_entry.lang = lang
                else:
                    entry.lang = lang
            if self.table is not None:
                self.update_searched_classes_headers_tooltips()
                self.previous_button.configure(text=translation["previous"])
                self.next_button.configure(text=translation["next"])
                self.remove_button.configure(text=translation["remove"])
                self.download_search_pdf.configure(text=translation["pdf_save_as"])
                table_count = self.table_count.cget("text").split(":")[1].strip()
                table_position = self.table_position.cget("text").split(":")[1].strip()
                self.table_count.configure(text=translation["table_count"] + table_count)
                self.table_position.configure(text=translation["table_position"] + table_position)
                self.table_count_tooltip.configure(message=translation["table_count_tooltip"])
                self.table_position_tooltip.configure(message=translation["table_position_tooltip"])
                self.previous_button_tooltip.configure(message=translation["previous_tooltip"])
                self.next_button_tooltip.configure(message=translation["next_tooltip"])
                self.remove_button_tooltip.configure(message=translation["remove_tooltip"])
                self.download_search_pdf_tooltip.configure(message=translation["download_pdf_search_tooltip"])
                sort_mapping = {
                    "Time Ascending ↑": "time_asc",
                    "Time Descending ↓": "time_dec",
                    "Av. Ascending ↑": "av_asc",
                    "Av. Descending ↓": "av_dec",
                    "Original Table": "original_data",
                    "Horas Ascendente ↑": "time_asc",
                    "Horas Descendente ↓": "time_dec",
                    "Disp. Ascendente ↑": "av_asc",
                    "Disp. Descendente ↓": "av_dec",
                    "Tabla Original": "original_data"
                }
                current_selection = self.sort_by.get()
                translated_values = [translation["time_asc"], translation["time_dec"], translation["av_asc"],
                                     translation["av_dec"], translation["original_data"]]
                self.sort_by.configure(values=translated_values)
                selection_key = sort_mapping.get(current_selection)
                if selection_key and selection_key in translation:
                    translated_selection = translation[selection_key]
                    self.sort_by.set(translated_selection)
                else:
                    self.sort_by.set(translation["sort_by"])
                if self.last_sort_option:
                    sort_by, _ = self.last_sort_option
                    last_sort_key = sort_mapping.get(sort_by)
                    if last_sort_key and last_sort_key in translation:
                        self.last_sort_option = (translation[last_sort_key], len(self.class_table_pairs))
                self.sort_by_tooltip.configure(translation["sort_by_tooltip"])
            if self.enrolled_classes_data is not None:
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
                self.update_sections_enrolled_tooltips(lang)
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

    def rename_tabs(self):
        translation = self.load_language()
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
            "Sunday": "Domingo",
            "Online": "En Línea"
        }
        reverse_day_translations = {v: k for k, v in day_translations.items()}
        translation = self.load_language()
        current_message = self.e_section_tooltip.cget("message")
        if not current_message:
            return

        if self.e_section_entry.get().upper().startswith("EL"):
            self.e_section_tooltip.configure(message=translation["online_class"], visibility=True)
            return

        lines = current_message.split("\n")
        if len(lines) != 2:
            return

        days, time_info = lines
        if new_lang == "Español":
            translated_days = ", ".join(day_translations.get(day, day) for day in days.split(", "))
            time_label = "*Aprox"
        else:
            translated_days = ", ".join(reverse_day_translations.get(day, day) for day in days.split(", "))
            time_label = "*Approx"

        time_info = time_info.replace("*Aprox", "").replace("*Approx", "").strip()
        if time_info.startswith("."):
            combined_time = f"{time_label}{time_info}"
        else:
            combined_time = f"{time_label} {time_info}"

        self.e_section_tooltip.configure(message=f"{translated_days}\n{combined_time}", visibility=True)

    def update_sections_multiple_tooltips(self, new_lang):
        day_translations = {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sábado",
            "Sunday": "Domingo",
            "Online": "En Línea"
        }
        reverse_day_translations = {v: k for k, v in day_translations.items()}
        translation = self.load_language()

        for idx, tooltip in enumerate(self.m_tooltips):
            current_message = tooltip.cget("message")
            if not current_message:
                continue

            if self.m_section_entry[idx].get().upper().startswith("EL"):
                tooltip.configure(message=translation["online_class"])
                continue

            lines = current_message.split("\n")
            if len(lines) == 4:
                day_line = lines[2]
                day_list = [day.strip() for day in day_line.split(",")]
                if new_lang == "Español":
                    translated_days = [day_translations.get(day, day) for day in day_list]
                    lines[2] = ", ".join(translated_days)
                    time_label = "*Aprox"
                else:
                    un_translated_days = [reverse_day_translations.get(day, day) for day in day_list]
                    lines[2] = ", ".join(un_translated_days)
                    time_label = "*Approx"
                raw_time = lines[-1].replace("*Aprox", "").replace("*Approx", "").strip()
                if raw_time.startswith("."):
                    combined_time = f"{time_label}{raw_time}"
                else:
                    combined_time = f"{time_label} {raw_time}"
                lines[-1] = combined_time

                tooltip.configure(message="\n".join(lines))

            elif len(lines) == 2:
                days, time_info = lines
                day_list = [day.strip() for day in days.split(",")]
                if new_lang == "Español":
                    translated_days = [day_translations.get(day, day) for day in day_list]
                    days = ", ".join(translated_days)
                    time_label = "*Aprox"
                else:
                    un_translated_days = [reverse_day_translations.get(day, day) for day in day_list]
                    days = ", ".join(un_translated_days)
                    time_label = "*Approx"
                time_info = time_info.replace("*Aprox", "").replace("*Approx", "").strip()
                if time_info.startswith("."):
                    combined_time = f"{time_label}{time_info}"
                else:
                    combined_time = f"{time_label} {time_info}"
                tooltip.configure(message=f"{days}\n{combined_time}")

    def update_sections_enrolled_tooltips(self, new_lang):
        day_translations = {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sábado",
            "Sunday": "Domingo",
            "Online": "En Línea"
        }
        reverse_day_translations = {v: k for k, v in day_translations.items()}
        translation = self.load_language()

        if not self.enrolled_tooltips:
            return

        for idx, tooltip in enumerate(self.enrolled_tooltips):
            current_message = tooltip.cget("message")
            if not current_message:
                continue

            if idx % 2 == 1:
                entry_idx = idx // 2
                if self.change_section_entries[entry_idx].get().upper().startswith("EL"):
                    tooltip.configure(message=translation["online_class"])
                    continue

            lines = current_message.split("\n")
            if len(lines) >= 4 and ("*Aprox" in lines[-1] or "*Approx" in lines[-1]):
                is_table_conflict = len(lines) > 4 or "in your currently enrolled classes" in current_message
                tooltip_key = "conflict_table_tooltip" if is_table_conflict else "conflict_tooltip"
                conflict_tooltip = translation.get(
                    tooltip_key, "Section potentially conflicting with\nthe schedule of another section\n").strip()
                tooltip_lines = conflict_tooltip.split("\n")
                day_line = lines[-2]
                day_list = [day.strip() for day in day_line.split(",")]
                if new_lang == "Español":
                    translated_days = [day_translations.get(day, day) for day in day_list]
                    translated_days_line = ", ".join(translated_days)
                    time_label = "*Aprox"
                else:
                    un_translated_days = [reverse_day_translations.get(day, day) for day in day_list]
                    translated_days_line = ", ".join(un_translated_days)
                    time_label = "*Approx"
                raw_time = lines[-1].replace("*Aprox", "").replace("*Approx", "").strip()
                if raw_time.startswith("."):
                    combined_time = f"{time_label}{raw_time}"
                else:
                    combined_time = f"{time_label} {raw_time}"
                new_message = "\n".join(tooltip_lines)
                new_message += f"\n{translated_days_line}\n{combined_time}"
                tooltip.configure(message=new_message)

            elif len(lines) == 2 and ("*Aprox" in lines[1] or "*Approx" in lines[1]):
                days, time_info = lines
                day_list = [day.strip() for day in days.split(",")]
                if new_lang == "Español":
                    translated_days = [day_translations.get(day, day) for day in day_list]
                    days = ", ".join(translated_days)
                    time_label = "*Aprox"
                else:
                    un_translated_days = [reverse_day_translations.get(day, day) for day in day_list]
                    days = ", ".join(un_translated_days)
                    time_label = "*Approx"
                time_info = time_info.replace("*Aprox", "").replace("*Approx", "").strip()
                if time_info.startswith("."):
                    combined_time = f"{time_label}{time_info}"
                else:
                    combined_time = f"{time_label} {time_info}"
                tooltip.configure(message=f"{days}\n{combined_time}")

            elif len(lines) == 2 and "*Aprox" not in current_message and "*Approx" not in current_message:
                tooltip.configure(message=translation["change_section_entry"])

    def change_semester(self, semester):
        translation = self.load_language()
        self.update_semester_tooltip(self.m_semester_entry[0])
        semester = self.m_semester_entry[0].get().upper().replace(" ", "")
        curr_sem = translation["current"].upper()
        dummy_event = type("Dummy", (object,), {"widget": self.m_semester_entry[0]})()
        self.detect_change(dummy_event)
        if re.fullmatch("^[A-Z][0-9]{2}$", semester) or semester == curr_sem:
            for i in range(1, self.a_counter + 1):
                self.m_semester_entry[i].configure(state="normal")
                if semester == curr_sem:
                    self.m_semester_entry[i].set(translation["current"])
                else:
                    self.m_semester_entry[i].set(semester)
                self.m_semester_entry[i].configure(state="disabled")

    def m_sections_bind_wrapper(self, event):
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
            ("14:00", "14:50", "N"),
            ("15:00", "16:50", "O"),
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

        schedule_map["EL"] = ("Online", "", "")

        return schedule_map

    @staticmethod
    def convert_to_12_hour_format(time_str):
        time_obj = datetime.strptime(time_str, "%H:%M")
        return time_obj.strftime("%I:%M %p").lstrip("0")

    def check_class_time(self):
        lang = self.language_menu.get()
        translation = self.load_language()
        day_translations = {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sábado",
            "Sunday": "Domingo",
            "Online": "En Línea"
        }

        section = self.e_section_entry.get().upper().replace(" ", "")
        schedule_map = self.schedule_map

        if section[:2] == "EL" or section[:2] in schedule_map:
            days, start_time, end_time = schedule_map.get(section[:2], ("", "", ""))
            if days == "Online" or section[:2] == "EL":
                message = translation["online_class"]
            else:
                start_time_12hr = TeraTermUI.convert_to_12_hour_format(start_time)
                end_time_12hr = TeraTermUI.convert_to_12_hour_format(end_time)
                translated_days = ", ".join(
                    day_translations.get(day, day) for day in days.split(", ")) if lang == "Español" else days
                if lang == "Español":
                    message = f"{translated_days}\n *Aprox. {start_time_12hr} - {end_time_12hr}"
                else:
                    message = f"{translated_days}\n *Approx. {start_time_12hr} - {end_time_12hr}"

            self.e_section_tooltip.configure(message=message, visibility=True)
        else:
            self.e_section_tooltip.configure(message="", visibility=False)

    def check_class_conflicts(self, event=None):
        current_translation = self.load_language()
        current_schedule_map = self.schedule_map
        day_translation_map = {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sábado",
            "Sunday": "Domingo",
            "Online": "En Línea"
        }

        enrolled_section_codes = set(
            row.get(current_translation["course"], "").split("-")[-1].strip()
            for row in (self.enrolled_classes_data or []) if row.get(current_translation["course"], ""))

        def collect_valid_entries(entries):
            return [(entry.get().upper().replace(" ", ""), entry) for entry in entries if entry and entry.get().strip()]

        valid_main_entries = collect_valid_entries(self.m_section_entry)
        valid_change_entries = collect_valid_entries(self.change_section_entries or [])

        @lru_cache(maxsize=None)
        def resolve_schedule_info(section_codes):
            return current_schedule_map.get(section_codes, current_schedule_map.get(section_codes[:2], ("", "", "")))

        def compile_schedule(entry_data, with_enrolled=False):
            compiled = {}
            for code, _ in entry_data:
                sched_days, sched_start, sched_end = resolve_schedule_info(code)
                if sched_days == "Online" or code.startswith("EL"):
                    continue
                for sched_day in sched_days.split(", "):
                    compiled.setdefault(sched_day, []).append((sched_start, sched_end, code))

            if with_enrolled:
                for enrolled_code in enrolled_section_codes:
                    sched_days, sched_start, sched_end = resolve_schedule_info(enrolled_code)
                    if sched_days == "Online" or enrolled_code.startswith("EL"):
                        continue
                    for sched_day in sched_days.split(", "):
                        compiled.setdefault(sched_day, []).append((sched_start, sched_end, enrolled_code))

            for entries in compiled.values():
                entries.sort()
            return compiled

        def detect_internal_conflicts(schedule_dict):
            conflict_set = set()
            for time_group in schedule_dict.values():
                for i, (start_1, end_1, code_1) in enumerate(time_group[:-1]):
                    for start_2, end_2, code_2 in time_group[i + 1:]:
                        if start_1 < end_2 and start_2 < end_1:
                            conflict_set.update({(code_1, start_1, end_1), (code_2, start_2, end_2)})
            return conflict_set

        def detect_cross_conflicts(base_sched, comp_sched):
            cross_set = set()
            for sched_day, base_blocks in base_sched.items():
                if sched_day not in comp_sched:
                    continue
                for base_start, base_end, base_code in base_blocks:
                    for comp_start, comp_end, comp_code in comp_sched[sched_day]:
                        if base_start < comp_end and comp_start < base_end:
                            cross_set.update({(base_code, base_start, base_end), (comp_code, comp_start, comp_end)})
            return cross_set

        sched_main = compile_schedule(valid_main_entries)
        sched_change = compile_schedule(valid_change_entries)
        sched_enrolled = compile_schedule([], with_enrolled=True)

        main_conflicts = detect_internal_conflicts(sched_main)
        change_conflicts = detect_internal_conflicts(sched_change)
        cross_conflicts = detect_cross_conflicts(sched_change, sched_enrolled)

        default_border = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"]
        ui_lang = self.language_menu.get()
        fmt_time = TeraTermUI.convert_to_12_hour_format

        def format_tooltip_text(sections_code, is_conflict, prefix_label):
            day_block, start_block, end_block = resolve_schedule_info(sections_code)
            is_onlines = day_block == "Online" or sections_code.startswith("EL")
            if is_onlines:
                return current_translation["online_class"], "#1E90FF", True
            human_time = f"{fmt_time(start_block)} - {fmt_time(end_block)}"
            human_days = ", ".join(
                day_translation_map.get(d, d) for d in day_block.split(", ")) if ui_lang == "Español" else day_block
            text = f"{prefix_label}{human_days}\n*{'Aprox.' if ui_lang == 'Español' else 'Approx.'} {human_time}"
            return text, "#CC5500" if is_conflict else "#1E90FF", False

        def apply_tooltip_visuals(entry_group, conflict_set, tooltip_group, is_change=False):
            for index, inputs_entry in enumerate(entry_group):
                code_raw = inputs_entry.get().upper().replace(" ", "")
                tooltips_pos = idx * 2 + 1 if is_change else index
                if not code_raw:
                    inputs_entry.configure(border_color=default_border)
                    tooltip_group[tooltips_pos].configure(message="", visibility=False)
                    continue

                if any(conf[0] == code_raw for conf in conflict_set):
                    tips_msg, tips_color, is_onlines = format_tooltip_text(code_raw, True,
                                                                        current_translation["conflict_tooltip"])
                    inputs_entry.configure(border_color=default_border if is_onlines else "#CC5500")
                elif code_raw in current_schedule_map or code_raw[:2] in current_schedule_map:
                    tips_msg, tips_color, _ = format_tooltip_text(code_raw, False, "")
                    inputs_entry.configure(border_color=default_border)
                else:
                    inputs_entry.configure(border_color=default_border)
                    tooltip_group[tooltips_pos].configure(
                        message=current_translation["change_section_entry"] if is_change else "",
                        visibility=bool(is_change), bg_color="#1E90FF"
                    )
                    continue

                tooltip_group[tooltips_pos].configure(message=tips_msg, visibility=True, bg_color=tips_color)

        apply_tooltip_visuals(self.m_section_entry, main_conflicts, self.m_tooltips)

        if self.change_section_entries:
            for idx, input_entry in enumerate(self.change_section_entries):
                if input_entry is None:
                    continue

                section_code = input_entry.get().upper().replace(" ", "")
                tooltip_pos = idx * 2 + 1

                if not section_code:
                    input_entry.configure(border_color=default_border)
                    self.enrolled_tooltips[tooltip_pos].configure(message=current_translation["change_section_entry"],
                                                                  bg_color="#1E90FF")
                    continue

                if section_code in enrolled_section_codes:
                    tip_msg, tip_color, is_online = format_tooltip_text(section_code, True,
                                                                        current_translation["conflict_table_tooltip"])
                    input_entry.configure(border_color=default_border if is_online else "#CC5500")
                elif any(conf[0] == section_code for conf in cross_conflicts):
                    tip_msg, tip_color, is_online = format_tooltip_text(section_code, True,
                                                                        current_translation["conflict_table_tooltip"])
                    input_entry.configure(border_color=default_border if is_online else "#CC5500")
                elif any(conf[0] == section_code for conf in change_conflicts):
                    tip_msg, tip_color, is_online = format_tooltip_text(section_code, True,
                                                                        current_translation["conflict_tooltip"])
                    input_entry.configure(border_color=default_border if is_online else "#CC5500")
                elif section_code in current_schedule_map or section_code[:2] in current_schedule_map:
                    tip_msg, tip_color, _ = format_tooltip_text(section_code, False, "")
                    input_entry.configure(border_color=default_border)
                else:
                    input_entry.configure(border_color=default_border)
                    self.enrolled_tooltips[tooltip_pos].configure(message=current_translation["change_section_entry"],
                                                                  bg_color="#1E90FF")
                    continue

                self.enrolled_tooltips[tooltip_pos].configure(message=tip_msg, bg_color=tip_color)

    def keybind_auto_enroll(self):
        if self.auto_enroll.get() == "on":
            self.auto_enroll.deselect()
            self.countdown_running = False
            self.auto_enroll_flag = False
            self.auto_enroll_focus = False
            self.disable_enable_gui()
            if self.running_countdown:
                self.end_countdown()
        elif self.auto_enroll.get() == "off":
            self.auto_enroll_focus = True
            self.auto_enroll.select()
            self.auto_enroll_event_handler()

    def auto_enroll_event_handler(self):
        translation = self.load_language()
        self.focus_set()
        idle = self.cursor_db.execute("SELECT idle FROM user_config").fetchone()
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
                    loading_screen = self.show_loading_screen()
                    future = self.thread_pool.submit(self.auto_enroll_event)
                    self.update_loading_screen(loading_screen, future)
                else:
                    self.auto_enroll.deselect()
                    if self.auto_enroll_focus:
                        self.auto_enroll.focus_set()
            elif self.auto_enroll.get() == "off":
                self.countdown_running = False
                self.auto_enroll_flag = False
                self.disable_enable_gui()
                if self.running_countdown:
                    self.end_countdown()
        else:
            self.play_sound("error.wav")
            CTkMessagebox(title=translation["auto_enroll"], icon="cancel", button_width=380,
                          message=translation["auto_enroll_idle"])
            self.auto_enroll.deselect()
            self.auto_enroll.configure(state="disabled")
        self.auto_enroll_focus = False

    # Auto-Enroll classes
    def auto_enroll_event(self):
        with self.lock_thread:
            try:
                translation = self.load_language()
                semester = self.m_semester_entry[0].get().upper().replace(" ", "")
                self.automation_preparations()
                self.auto_enroll_flag = True
                if asyncio.run(self.test_connection()) and self.check_server() and self.check_format():
                    self.ssh_monitor.sample(count=50, force=True)
                    if not self.ssh_monitor.is_responsive():
                        def deny_auto_enroll():
                            self.play_sound("error.wav")
                            CTkMessagebox(title=translation["auto_enroll"], icon="cancel", button_width=380,
                                          message=translation["auto_enroll_denied"])
                            self.auto_enroll_flag = False
                            self.auto_enroll.deselect()

                        self.after(100, deny_auto_enroll)
                        return
                    if TeraTermUI.checkIfProcessRunning("ttermpro"):
                        if not self.wait_for_window():
                            return
                        self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}")
                        self.after(0, self.disable_go_next_buttons)
                        text_output = self.capture_screenshot()
                        if "OPCIONES PARA EL ESTUDIANTE" in text_output or "BALANCE CTA" in text_output or \
                                "PANTALLAS MATRICULA" in text_output or "PANTALLAS GENERALES" in text_output or \
                                "LISTA DE SECCIONES" in text_output:
                            if "LISTA DE SECCIONES" in text_output:
                                self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}")
                                self.reset_activity_timer()
                            TeraTermUI.manage_user_input()
                            self.automate_copy_class_data()
                            TeraTermUI.manage_user_input("on")
                            copy = pyperclip.paste()
                            turno_index = copy.find("TURNO MATRICULA:")
                            sliced_text = copy[turno_index:]
                            parts = sliced_text.split(":", 1)
                            match = re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", parts[1])
                            if match:
                                date_time_string = match.group()
                                date_time_string += " AM"
                            else:
                                self.after(100, self.show_error_message, 305, 220,
                                           translation["failed_to_find_date"])
                                self.auto_enroll_flag = False
                                self.after(125, self.auto_enroll.deselect)
                                return
                            active_semesters = TeraTermUI.get_latest_term(copy)
                            date_time_string = re.sub(r"[^a-zA-Z0-9:/ ]", "", date_time_string)
                            date_time_naive = datetime.strptime(date_time_string, "%m/%d/%Y %I:%M %p")
                            puerto_rico_tz = pytz.timezone("America/Puerto_Rico")
                            self.pr_date = puerto_rico_tz.localize(date_time_naive, is_dst=None)
                            # Get current datetime
                            current_date = datetime.now(puerto_rico_tz)
                            time_difference = self.pr_date - current_date
                            # Dates
                            is_same_date = (current_date.date() == self.pr_date.date())
                            is_past_date = current_date > self.pr_date
                            is_future_date = current_date < self.pr_date
                            is_next_date = (self.pr_date.date() - current_date.date() == timedelta(days=1))
                            is_time_difference_within_12_hours = timedelta(
                                hours=12, minutes=55) >= time_difference >= timedelta()
                            is_more_than_one_day = (self.pr_date.date() - current_date.date() > timedelta(days=1))
                            is_current_time_ahead = current_date.time() > self.pr_date.time()
                            is_current_time_24_hours_ahead = time_difference >= timedelta(hours=-24)
                            if active_semesters["percent"] and active_semesters["asterisk"] \
                                    and semester == active_semesters["percent"]:
                                self.after(100, self.show_error_message, 325, 235,
                                           translation["date_unknown"])
                                self.auto_enroll_flag = False
                                self.after(125, self.auto_enroll.deselect)
                                return
                            # Comparing Dates
                            if (is_same_date and is_time_difference_within_12_hours) or \
                                    (is_next_date and is_time_difference_within_12_hours):
                                self.countdown_running = True
                                self.after(0, self.disable_enable_gui)
                                # Create timer window
                                self.after(0, self.create_timer_window)
                                self.running_countdown = True
                                self.after(100, self.countdown, self.pr_date)
                            elif is_past_date or (is_same_date and is_current_time_ahead):
                                if is_current_time_24_hours_ahead:
                                    self.running_countdown = True
                                    self.started_auto_enroll = True
                                    self.after(150, self.submit_multiple_event_handler)
                                else:
                                    self.after(100, self.show_error_message, 305, 220,
                                               translation["date_past"])
                                    self.auto_enroll_flag = False
                                    self.after(125, self.auto_enroll.deselect)
                            elif (is_future_date or is_more_than_one_day) or \
                                    (is_same_date and not is_time_difference_within_12_hours) or \
                                    (is_next_date and not is_time_difference_within_12_hours):
                                self.after(100, self.show_error_message, 320, 235,
                                           translation["date_not_within_12_hours"])
                                self.auto_enroll_flag = False
                                self.after(125, self.auto_enroll.deselect)
                            if ("INVALID ACTION" in text_output and "PANTALLAS MATRICULA" in text_output) or \
                                    ("LISTA DE SECCIONES" in text_output and "COURSE NOT" in text_output):
                                self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                self.reset_activity_timer()
                                self.after(0, self.bring_back_timer_window)
                        else:
                            self.after(100, self.show_error_message, 305, 220,
                                       translation["failed_to_find_date"])
                            self.auto_enroll_flag = False
                            self.after(125, self.auto_enroll.deselect)
                    else:
                        self.after(100, self.show_error_message, 305, 215,
                                   translation["tera_term_not_running"])
                        self.auto_enroll_flag = False
                        self.after(125, self.auto_enroll.deselect)
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                translation = self.load_language()
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        self.play_sound("notification.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.auto_enroll.deselect()
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_automation)
                self.after(350, self.bind, "<Return>", lambda event: self.submit_multiple_event_handler())
                TeraTermUI.manage_user_input()

    # Starts the enrollment countdown when the auto-enroll process is activated
    def countdown(self, pr_date):
        translation = self.load_language()
        puerto_rico_tz = pytz.timezone("America/Puerto_Rico")
        current_date = datetime.now(puerto_rico_tz)
        total_seconds = (pr_date - current_date).total_seconds()
        bootup_threshold_low = 15 * 60
        bootup_threshold_high = 30 * 60
        skip_boot_feature_threshold_high = 45 * 60

        def check_boot_process():
            if (not self.has_saved_user_data() or getattr(self, "booting_in_progress", False)
                    or not self.running_countdown):
                return

            seconds_left = (self.pr_date - datetime.now(puerto_rico_tz)).total_seconds()
            if bootup_threshold_low <= seconds_left <= bootup_threshold_high:
                self.booting_in_progress = True
                max_delay_sec = seconds_left - bootup_threshold_low
                delay_ms = int(random.uniform(0, max_delay_sec) * 1000)
                self.after(delay_ms, self.boot_be_ready_for_auto_enroll)
            else:
                self.after(30000, check_boot_process)

        if self.running_countdown:
            if self.has_saved_user_data():
                if total_seconds > skip_boot_feature_threshold_high:
                    self.stop_check_process_thread()
                    self.stop_check_idle_thread()
                    self.after(1000, check_boot_process)
                    if not self.boot_notified:
                        self.after(3500, self.notify_boot_up)
                        self.boot_notified = True

            if total_seconds <= 0:
                self.timer_label.configure(text=self.get_countdown_message(total_seconds),
                                           text_color="#32CD32", font=customtkinter.CTkFont(size=17))
                self.timer_label.pack(pady=25)
                self.cancel_button.pack_forget()

                if self.state() == "withdrawn":
                    if self.timer_window.state() == "withdrawn":
                        self.timer_window.iconify()
                    self.iconify()
                    hwnd = win32gui.FindWindow(None, "uprbay.uprb.edu - Tera Term VT")
                    if hwnd and not win32gui.IsWindowVisible(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    gw.getWindowsWithTitle("Tera Term UI")[0].restore()
                    gw.getWindowsWithTitle(translation["auto_enroll"])[0].restore()

                self.timer_window.lift()
                self.timer_window.focus_force()
                self.timer_window.attributes("-topmost", 1)
                self.started_auto_enroll = True
                self.after(3000, self.submit_multiple_event_handler)

                if TeraTermUI.window_exists(translation["dialog_title"]):
                    self.after(2500, self.dialog.destroy)

                if TeraTermUI.window_exists(translation["save_pdf"]):
                    def close_file_dialog():
                        pdf_hwnd = win32gui.FindWindow("#32770", translation["save_pdf"])
                        win32gui.PostMessage(pdf_hwnd, win32con.WM_CLOSE, 0, 0)

                    self.after(2500, close_file_dialog)

                self.after(2500, TeraTermUI.close_matching_windows, [
                    translation["exit"], translation["submit"], translation["success_title"],
                    translation["error"], translation["fix_messagebox_title"],
                    translation["update_popup_title"], translation["so_title"],
                    translation["automation_error_title"]])
                return

            if self.has_saved_user_data():
                lang = self.language_menu.get()
                stats = self.ssh_monitor.get_stats()
                host = self.ssh_monitor.host
                rating, color = self.ssh_monitor.get_reliability_rating(lang)
                sample_count = (40 if not stats or stats["samples"] < 10 else 30 if stats["std_dev"] > 100
                                or stats["max"] > 1000 or stats["average"] > 400 else 20)
                self.ssh_monitor.sample(count=sample_count)
                if self.prev_sample_count != stats.get("samples"):
                    self.server_rating.configure(text=f"{translation['server_status_rating']}{rating}",
                                                 text_color=color)
                    logging.info(f"Server \"{host}\" Response Time Statistics (ms):\n       {stats}")
                    self.prev_sample_count = stats.get("samples")

            self.timer_label.configure(text=self.get_countdown_message(total_seconds))
            if total_seconds > 60:
                self.timer_window.after(5000, lambda: self.countdown_status(pr_date))
            else:
                if not self.notification_sent:
                    self.tray.notify(translation["notif_countdown"].replace(
                        "{semester}", self.m_semester_entry[0].get()), title="Tera Term UI")
                    self.notification_sent = True
                self.timer_window.after(1000, lambda: self.countdown_status(pr_date))

    def countdown_status(self, pr_date):
        puerto_rico_tz = pytz.timezone("America/Puerto_Rico")
        total_seconds = (pr_date - datetime.now(puerto_rico_tz)).total_seconds()
        bootup_threshold_low = 15 * 60
        if self.has_saved_user_data():
            if total_seconds <= bootup_threshold_low:
                if not TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                    if not getattr(self, "booting_in_progress", False):
                        self.forceful_end_countdown()
                        return

        else:
            if not TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                self.forceful_end_countdown()
                return

        self.countdown(pr_date)

    def get_countdown_message(self, total_seconds):
        lang = self.language_menu.get()
        translation = self.load_language()
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if total_seconds <= 0:
            return translation["performing_auto_enroll"]

        if hours > 0:
            if seconds > 0:
                minutes += 1
            if lang == "English":
                if minutes == 0:
                    return f"{int(hours)} hours remaining\nuntil enrollment"
                elif hours == 1 and minutes == 1:
                    return f"{int(hours)} hour and {int(minutes)} minute remaining\nuntil enrollment"
                elif hours == 1:
                    return f"{int(hours)} hour and {int(minutes)} minutes remaining\nuntil enrollment"
                elif minutes == 1:
                    return f"{int(hours)} hours and {int(minutes)} minute remaining\nuntil enrollment"
                else:
                    return f"{int(hours)} hours and {int(minutes)} minutes remaining\nuntil enrollment"
            elif lang == "Español":
                if minutes == 0:
                    return f"{int(hours)} horas restantes\nhasta la matrícula"
                elif hours == 1 and minutes == 1:
                    return f"{int(hours)} hora y {int(minutes)} minuto restante\nhasta la matrícula"
                elif hours == 1:
                    return f"{int(hours)} hora y {int(minutes)} minutos restantes\nhasta la matrícula"
                elif minutes == 1:
                    return f"{int(hours)} horas y {int(minutes)} minuto restante\nhasta la matrícula"
                else:
                    return f"{int(hours)} horas y {int(minutes)} minutos restantes\nhasta la matrícula"
            return None
        else:
            if seconds > 0:
                minutes += 1
            if lang == "English":
                if minutes >= 60:
                    return "1 hour remaining until enrollment"
                elif minutes > 1:
                    return f"{int(minutes)} minutes remaining until enrollment"
                elif total_seconds > 31:
                    return "1 minute remaining until enrollment"
                elif total_seconds >= 2:
                    return f"{int(total_seconds)} seconds remaining until enrollment"
                else:
                    return "1 second remaining until enrollment"
            elif lang == "Español":
                if minutes >= 60:
                    return "1 hora restante hasta la matrícula"
                elif minutes > 1:
                    return f"{int(minutes)} minutos restantes hasta la matrícula"
                elif total_seconds > 31:
                    return "1 minuto restante hasta la matrícula"
                elif total_seconds >= 2:
                    return f"{int(total_seconds)} segundos restantes hasta la matrícula"
                else:
                    return "1 segundo restante hasta la matrícula"
            return None

    def end_countdown(self):
        translation = self.load_language()
        self.pr_date = None
        self.auto_enroll_flag = False
        self.countdown_running = False
        self.notification_sent = False
        self.running_countdown = False
        self.booting_in_progress = False
        if self.idle_num_check >= 34:
            self.idle_num_check = 33
        self.idle_num_check = max(0, self.idle_num_check // 2)
        if self.timer_window and self.timer_window.winfo_exists():
            if any(i.text == translation["countdown_win"] for i in self.tray.menu.items):
                updated_menu_items = [i for i in self.tray.menu.items if i.text != translation["countdown_win"]]
                self.tray.menu = pystray.Menu(*updated_menu_items)
                self.tray.update_menu()
            self.timer_window.destroy()
        self.disable_enable_gui()
        self.auto_enroll.deselect()

    def forceful_end_countdown(self):
        translation = self.load_language()
        self.end_countdown()
        self.play_sound("notification.wav")
        self.forceful_countdown_end = True
        CTkMessagebox(title=translation["automation_error_title"], icon="info", message=translation["end_countdown"],
                      button_width=380)

    def notify_boot_up(self):
        translation = self.load_language()
        self.play_sound("notification.wav")
        CTkMessagebox(title=translation["notif_auto_boot"], icon="info", message=translation["auto_boot_up"],
                      button_width=380)

    def create_timer_window(self):
        lang = self.language_menu.get()
        translation = self.load_language()
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        timer_window_width = 345
        timer_window_height = 175
        center_x = main_window_x + (main_window_width // 2) - (timer_window_width // 2)
        center_y = main_window_y + (main_window_height // 2) - (timer_window_height // 2)
        center_x += 70
        center_y -= 15
        monitor = TeraTermUI.get_monitor_bounds(main_window_x, main_window_y)
        monitor_x, monitor_y, monitor_width, monitor_height = monitor.x, monitor.y, monitor.width, monitor.height
        center_x = max(monitor_x, min(center_x, monitor_x + monitor_width - timer_window_width))
        center_y = max(monitor_y, min(center_y, monitor_y + monitor_height - timer_window_height))
        window_geometry = f"{timer_window_width}x{timer_window_height}+{center_x}+{center_y}"
        self.timer_window = SmoothFadeToplevel(fade_duration=15)
        self.timer_window.geometry(window_geometry)
        self.timer_window.title(translation["auto_enroll"])
        self.timer_window.attributes("-alpha", 0.90)
        self.timer_window.resizable(False, False)
        self.timer_window.iconbitmap(self.icon_path)
        rating, color = self.ssh_monitor.get_reliability_rating(lang)
        self.timer_header = customtkinter.CTkLabel(self.timer_window, font=customtkinter.CTkFont(
            size=20, weight="bold"), text=translation["auto_enroll_activated"])
        self.timer_header.pack()
        self.server_rating = customtkinter.CTkLabel(
            self.timer_window, text=f"{translation["server_status_rating"]}{rating}", text_color=color,
            font=customtkinter.CTkFont(size=15))
        self.server_rating.pack(pady=(4, 0))
        self.timer_label = customtkinter.CTkLabel(self.timer_window, text="", font=customtkinter.CTkFont(size=15))
        self.timer_label.pack()
        self.cancel_button = CustomButton(master=self.timer_window, text=translation["option_1"], width=260, height=28,
                                          hover_color="darkred", fg_color="red", command=self.end_countdown)
        self.cancel_button.pack(pady=(16, 0))
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
        translation = self.load_language()
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

    def boot_be_ready_for_auto_enroll(self):
        MAX_BOOT_RETRIES = 3
        retry_delay = 2.5
        for attempt in range(1, MAX_BOOT_RETRIES + 1):
            try:
                TeraTermUI.manage_user_input("on")
                if TeraTermUI.checkIfProcessRunning("ttermpro"):
                    keywords = ["STUDENTS REQ/DROP", "HOLD FLAGS", "PROGRAMA DE CLASES", "ACADEMIC STATISTICS",
                                "SNAPSHOT", "SOLICITUD DE PRORROGA", "LISTA DE SECCIONES", "AYUDA ECONOMICA",
                                "EXPEDIENTE ACADEMICO", "AUDIT", "PERSONAL DATA", "COMPUTO DE MATRICULA", "SIGN-IN",
                                "MORE SECTIONS EXIST"]
                    text_output = self.capture_screenshot()
                    hwnd_tt = win32gui.FindWindow(None, "Tera Term")
                    count, is_multiple = TeraTermUI.countRunningProcesses("ttermpro")
                    if any(keyword in text_output for keyword in keywords) and not is_multiple:
                        if hwnd_tt:
                            win32gui.PostMessage(hwnd_tt, win32con.WM_CLOSE, 0, 0)
                        self.uprb.UprbayTeraTermVt.type_keys("^q")
                        self.uprb.UprbayTeraTermVt.type_keys("{VK_RIGHT}{VK_LEFT}")
                        self.connect_to_uprb()
                    else:
                        if attempt < MAX_BOOT_RETRIES:
                            raise RuntimeError("Tera Term running but not at expected screen")
                        else:
                            self.forceful_end_countdown()
                            return
                else:
                    self.uprb = Application(backend="uia").start(self.teraterm_exe_location, timeout=3)
                    timings.wait_until_passes(10, 1, lambda: self.uprb.window(
                        title="Tera Term - [disconnected] VT", class_name="VTWin32",
                        control_type="Window").exists())
                    self.uprb.connect(title="Tera Term - [disconnected] VT", class_name="VTWin32",
                                      control_type="Window", timeout=3)
                    self.uprb_32 = Application().connect(title="Tera Term - [disconnected] VT",
                                                         timeout=3, class_name="VTWin32")
                    edit_menu = self.uprb.UprbayTeraTermVt.child_window(title="Edit", control_type="MenuItem")
                    self.select_screen_item = edit_menu.child_window(
                        title="Select screen", control_type="MenuItem", auto_id="50280")
                    disconnected = self.uprb.window(title="Tera Term - [disconnected] VT", class_name="VTWin32",
                                                    control_type="Window")
                    disconnected.wait("visible", timeout=3)
                    TeraTermUI.check_window_exists("Tera Term: New connection")
                    host_input = self.uprb.TeraTermDisconnectedVt.child_window(
                        title="Host:", control_type="Edit")
                    if host_input.get_value() != "uprbay.uprb.edu":
                        host_input.set_text("uprbay.uprb.edu")
                    self.uprb.TeraTermDisconnectedVt.child_window(title="OK", control_type="Button").invoke()
                    self.uprbay_window = self.uprb.window(
                        title="uprbay.uprb.edu - Tera Term VT", class_name="VTWin32", control_type="Window")
                    self.uprbay_window.wait("visible", timeout=3)
                    self.tera_term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                    TeraTermUI.check_window_exists("SSH Authentication")
                    ssh_auth_window = self.uprb.UprbayTeraTermVt
                    user_field = ssh_auth_window.child_window(title="User name:", control_type="Edit")
                    remember_checkbox = ssh_auth_window.child_window(title="Remember password in memory",
                                                                     control_type="CheckBox")
                    plain_password_radio = ssh_auth_window.child_window(title="Use plain password to log in",
                                                                        control_type="RadioButton")
                    ok_button = ssh_auth_window.child_window(title="OK", control_type="Button")
                    user_field.set_text("students")
                    if not remember_checkbox.get_toggle_state():
                        remember_checkbox.invoke()
                    if not plain_password_radio.is_selected():
                        plain_password_radio.invoke()
                    ok_button.invoke()
                    self.server_status = self.wait_for_prompt("return to continue",
                                                              "REGRESE PRONTO")
                    if self.server_status == "Prompt found":
                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER 3}")
                        self.move_window()
                    else:
                        if attempt == MAX_BOOT_RETRIES:
                            if attempt < MAX_BOOT_RETRIES:
                                raise RuntimeError("Prompt not found after SSH auth")
                            else:
                                self.forceful_end_countdown()
                                return
                    self.cursor_db.execute("SELECT student_id, code, nonce_student_id, nonce_code, tag_student_id, "
                                           "tag_code FROM user_data WHERE id = 1")
                    row = self.cursor_db.fetchone()
                    student_ct, code_ct, nonce_sid, nonce_code, tag_sid, tag_code = row
                    student_id = self.crypto.decrypt(student_ct, nonce_sid, tag_sid)
                    code = self.crypto.decrypt(code_ct, nonce_code, tag_code)
                    self.uprb.UprbayTeraTermVt.type_keys("{TAB}" + student_id + code + "{ENTER}")
                    text_output = self.wait_for_response(["SIGN-IN", "ON FILE",  "PIN NUMBER", "ERRORS FOUND"],
                                                         init_timeout=False, timeout=7)
                    if "SIGN-IN" in text_output:
                        TeraTermUI.secure_zeroize_string(student_id)
                        TeraTermUI.secure_zeroize_string(code)
                        self.reset_activity_timer()
                        self.start_check_idle_thread()
                        self.start_check_process_thread()
                        if self.state() == "withdrawn":
                            hwnd = win32gui.FindWindow(None, "uprbay.uprb.edu - Tera Term VT")
                            if hwnd and win32gui.IsWindowVisible(hwnd):
                                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                        return
                    else:
                        if attempt < MAX_BOOT_RETRIES:
                            raise RuntimeError("SIGN-IN screen not detected")
                        else:
                            self.forceful_end_countdown()
                            return
            except Exception as err:
                logging.warning(f"[Boot Attempt {attempt}] Failed: {err}")
                self.log_error()
                if TeraTermUI.checkIfProcessRunning("ttermpro"):
                    logging.info("Terminating stuck Tera Term instances after failed boot.")
                    if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                        try:
                            self.uprb.kill(soft=True)
                            if TeraTermUI.window_exists("uprbay.uprb.edu - Tera Term VT"):
                                TeraTermUI.terminate_process()
                        except Exception as kill_err:
                            logging.warning("Force kill fallback: %s", kill_err)
                            TeraTermUI.terminate_process()
                    elif (TeraTermUI.window_exists("Tera Term - [disconnected] VT") or
                          TeraTermUI.window_exists("Tera Term - [connecting...] VT")):
                        TeraTermUI.terminate_process()
                if attempt < MAX_BOOT_RETRIES:
                    time.sleep(retry_delay)
                else:
                    self.forceful_end_countdown()
            finally:
                self.set_focus_to_tkinter()
                TeraTermUI.manage_user_input()

    def disable_enable_gui(self):
        if self.countdown_running:
            self.submit_multiple.configure(state="disabled")
            self.submit.configure(state="disabled")
            self.back_classes.configure(state="disabled")
            self.m_add.configure(state="disabled")
            self.m_remove.configure(state="disabled")
            self.auto_enroll.configure(state="normal")
            self.save_class_data.configure(state="normal")
            for i in range(self.a_counter + 1):
                self.m_swap_buttons[i].configure(state="disabled")
            if self.enrolled_classes_data is not None:
                self.submit_my_classes.configure(state="disabled")
        else:
            self.submit_multiple.configure(state="normal")
            self.submit.configure(state="normal")
            self.back_classes.configure(state="normal")
            if self.a_counter > 0:
                self.m_remove.configure(state="normal")
            if self.a_counter < 7:
                self.m_add.configure(state="normal")
            for i in range(self.a_counter + 1):
                self.m_swap_buttons[i].configure(state="normal")
            for i in range(8):
                self.m_classes_entry[i].configure(state="normal")
                self.m_section_entry[i].configure(state="normal")
                self.m_register_menu[i].configure(state="normal")
            self.m_semester_entry[0].configure(state="normal")
            if self.enrolled_classes_data is not None:
                self.submit_my_classes.configure(state="normal")

    def move_window(self):
        try:
            window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
        except IndexError:
            logging.error("Window not found")
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
        # Check if the window is already in the correct position
        if (current_x, current_y) == (target_x, target_y):
            return
        # Move the Tera Term window
        while (current_x, current_y) != (target_x, target_y):
            distance = abs(target_x - current_x) + abs(target_y - current_y)
            step_size = max(5, min(40, distance // 12))
            delay_time = max(0.003, min(0.010, distance / 4000))
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
            translation = self.load_language()
            self.init_auth = True
            self.authentication_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.a_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.title_login = customtkinter.CTkLabel(master=self.authentication_frame,
                                                      text=translation["title_auth"],
                                                      font=customtkinter.CTkFont(size=20, weight="bold"))
            self.uprb_image = self.get_image("uprb")
            self.uprb_image_grid = CustomButton(master=self.authentication_frame, text="", image=self.uprb_image,
                                                width=322, height=115, command=self.uprb_event, fg_color="transparent",
                                                hover=False)
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
                self.unload_image("uprb")
                self.title_login = None
                self.uprb_image = None
                self.uprb_image_grid.image = None
                self.uprb_image_grid.configure(command=None)
                self.uprb_image_grid = None
                self.disclaimer = None
                self.username = None
                self.username_entry.lang = None
                self.username_entry = None
                self.username_tooltip.destroy()
                self.username_tooltip.widget = None
                self.username_tooltip.message = None
                self.username_tooltip = None
                self.auth.configure(command=None)
                self.auth = None
                self.back.configure(command=None)
                self.back = None
                self.back_tooltip.destroy()
                self.back_tooltip.widget = None
                self.back_tooltip.message = None
                self.back_tooltip = None
                self.authentication_frame.destroy()
                self.authentication_frame = None
                self.a_buttons_frame.destroy()
                self.a_buttons_frame = None
                gc.collect()

            self.after(100, destroy)

    def initialization_student(self):
        # Student Information
        if not self.init_student:
            self.init_student = True
            lang = self.language_menu.get()
            translation = self.load_language()
            self.student_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.s_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.title_student = customtkinter.CTkLabel(master=self.student_frame,
                                                        text=translation["title_security"],
                                                        font=customtkinter.CTkFont(size=20, weight="bold"))
            self.lock = self.get_image("lock")
            self.lock_grid = CustomButton(master=self.student_frame, text="", image=self.lock, command=self.lock_event,
                                          width=92, height=85, fg_color="transparent", hover=False)
            self.student_id = customtkinter.CTkLabel(master=self.student_frame, text=translation["student_id"])
            self.student_id_entry = CustomEntry(self.student_frame, self, lang, placeholder_text="#########", show="*")
            self.student_id_tooltip = CTkToolTip(self.student_id_entry, message=translation["student_id_tooltip"],
                                                 bg_color="#1E90FF")
            self.code = customtkinter.CTkLabel(master=self.student_frame, text=translation["code"])
            self.code_entry = CustomEntry(self.student_frame, self, lang, placeholder_text="####", show="*")
            self.code_tooltip = CTkToolTip(self.code_entry, message=translation["code_tooltip"], bg_color="#1E90FF")
            self.show = customtkinter.CTkSwitch(master=self.student_frame, text=translation["show"],
                                                command=self.show_event, onvalue="on", offvalue="off")
            self.remember_me = customtkinter.CTkCheckBox(self.student_frame, text=translation["remember_me"],
                                                         onvalue="on", offvalue="off", command=self.save_user_data)
            self.remember_me_tooltip = CTkToolTip(self.remember_me, message=translation["remember_me_tooltip"],
                                                  bg_color="#1E90FF")
            self.show.bind("<space>", lambda event: self.spacebar_event())
            self.remember_me.bind("<space>", self.keybind_save_user_data)
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
            self.remember_me.unbind("<space>")
            def destroy():
                self.unload_image("lock")
                self.title_student = None
                self.lock = None
                self.lock_grid.image = None
                self.lock_grid.configure(command=None)
                self.lock_grid = None
                self.student_id = None
                for entry in [self.student_id_entry, self.code_entry]:
                    entry.lang = None
                self.student_id_entry = None
                self.student_id_tooltip.destroy()
                self.student_id_tooltip.widget = None
                self.student_id_tooltip.message = None
                self.student_id_tooltip = None
                self.code = None
                self.code_entry = None
                self.code_tooltip.destroy()
                self.code_tooltip.widget = None
                self.code_tooltip.message = None
                self.code_tooltip = None
                self.show.configure(command=None)
                self.show = None
                self.remember_me.configure(command=None)
                self.remember_me = None
                self.remember_me_tooltip.destroy()
                self.remember_me_tooltip.widget = None
                self.remember_me_tooltip.message = None
                self.system.configure(command=None)
                self.system = None
                self.back_student.configure(command=None)
                self.back_student = None
                self.back_student_tooltip.destroy()
                self.back_student_tooltip.widget = None
                self.back_student_tooltip.message = None
                self.back_student_tooltip = None
                self.student_frame.destroy()
                self.student_frame = None
                self.s_buttons_frame.destroy()
                self.s_buttons_frame = None
                gc.collect()

            self.after(100, destroy)

    def initialization_class(self):
        # Classes
        if not self.init_class:
            lang = self.language_menu.get()
            translation = self.load_language()
            self.tabview = customtkinter.CTkTabview(self, corner_radius=10, command=self.switch_tab)
            self.t_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.semesters_tooltips = {}
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
            self.e_class = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab), text=translation["class"])
            query = "SELECT code FROM courses ORDER BY RANDOM() LIMIT 1"
            result = self.cursor_db.execute(query).fetchone()
            if result is not None:
                class_code = result[0]
            else:
                class_code = "ESPA3101"
            self.e_class_entry = CustomEntry(self.tabview.tab(self.enroll_tab), self, lang,
                                             placeholder_text=class_code)
            self.e_section = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab),
                                                    text=translation["section"])
            self.e_section_entry = CustomEntry(self.tabview.tab(self.enroll_tab), self, lang, placeholder_text="LM1")
            self.e_section_tooltip = CTkToolTip(self.e_section_entry, message="", bg_color="#1E90FF", visibility=False)
            self.e_semester = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab),
                                                     text=translation["semester"])
            self.e_semester_entry = CustomComboBox(self.tabview.tab(self.enroll_tab), self, lang,
                                                   values=self.semester_values + [translation["current"]])
            self.e_semester_entry.configure(command=lambda event: self.update_semester_tooltip(self.e_semester_entry))
            self.e_semester_entry.bind("<FocusOut>", lambda event: self.update_semester_tooltip(
                self.e_semester_entry))
            self.e_semester_entry.set(self.DEFAULT_SEMESTER)
            self.semesters_tooltips[self.e_semester_entry] = CTkToolTip(
                self.e_semester_entry, message=self.get_semester_season(self.DEFAULT_SEMESTER), bg_color="#1E90FF")
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
            self.e_class.bind("<Button-1>", lambda event: self.focus_set())
            self.e_section.bind("<Button-1>", lambda event: self.focus_set())
            self.e_section_entry.bind("<FocusOut>", lambda event: self.check_class_time())
            self.e_semester.bind("<Button-1>", lambda event: self.focus_set())
            self.register.bind("<space>", lambda event: self.spacebar_event())
            self.register.bind("<FocusOut>", lambda event: self.drop._on_leave())

            # Second Tab
            self.search_scrollbar = customtkinter.CTkScrollableFrame(master=self.tabview.tab(self.search_tab),
                                                                     corner_radius=10)
            self.title_search = customtkinter.CTkLabel(self.search_scrollbar, text=translation["title_search"],
                                                       font=customtkinter.CTkFont(size=20, weight="bold"))
            calendar_img = customtkinter.CTkImage(light_image=Image.open(
                TeraTermUI.get_absolute_path("images/calendar.png")), size=(75, 75))
            self.image_search = customtkinter.CTkLabel(self.search_scrollbar, text="", image=calendar_img)
            self.notice_search = customtkinter.CTkLabel(self.search_scrollbar, text=translation["notice_search"],
                                                        font=customtkinter.CTkFont(size=16, weight="bold"))
            self.s_classes = customtkinter.CTkLabel(self.search_scrollbar, text=translation["class"])
            query = "SELECT code FROM courses ORDER BY RANDOM() LIMIT 1"
            result = self.cursor_db.execute(query).fetchone()
            if result is not None:
                class_code = result[0]
            else:
                class_code = "INGL3101"
            self.s_class_entry = CustomEntry(self.search_scrollbar, self, lang, placeholder_text=class_code,
                                             width=80)
            self.s_semester = customtkinter.CTkLabel(self.search_scrollbar, text=translation["semester"])
            self.s_semester_entry = CustomComboBox(self.search_scrollbar, self, lang, width=80,
                                                   values=self.semester_values + [translation["current"]])
            self.s_semester_entry.set(self.DEFAULT_SEMESTER)
            self.s_semester_entry.configure(command=lambda event: self.update_semester_tooltip(
                self.s_semester_entry))
            self.s_semester_entry.bind("<FocusOut>", lambda event: self.update_semester_tooltip(
                self.s_semester_entry))
            self.semesters_tooltips[self.s_semester_entry] = CTkToolTip(
                self.s_semester_entry, message=self.get_semester_season(self.DEFAULT_SEMESTER), bg_color="#1E90FF")
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
            self.bind("<Button-1>", TeraTermUI.set_focus_tabview)
            self.tabview.tab(self.search_tab).bind("<Button-1>", lambda event: self.focus_set())
            self.search_scrollbar.bind("<Button-1>", lambda event: self.focus_set())
            self.title_search.bind("<Button-1>", lambda event: self.focus_set())
            self.image_search.bind("<Button-1>", lambda event: self.focus_set())
            self.notice_search.bind("<Button-1>", lambda event: self.focus_set())
            self.s_classes.bind("<Button-1>", lambda event: self.focus_set())
            self.s_semester.bind("<Button-1>", lambda event: self.focus_set())
            self.s_class_entry.bind("<FocusIn>", lambda event:
            self.search_scrollbar.scroll_to_widget(self.s_class_entry))
            self.show_all.bind("<space>", lambda event: self.spacebar_event())

            # Third Tab
            self.title_menu = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
                                                     text=translation["title_menu"],
                                                     font=customtkinter.CTkFont(size=20, weight="bold"))
            self.explanation_menu = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
                                                           text=translation["explanation_menu"])
            self.menu = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab), text=translation["menu"])
            self.menu_entry = CustomComboBox(self.tabview.tab(self.other_tab), self, lang, width=141,
                                             values=[translation["SRM"], translation["004"], translation["1GP"],
                                                     translation["118"], translation["1VE"], translation["3DD"],
                                                     translation["409"], translation["683"], translation["1PL"],
                                                     translation["4CM"], translation["4SP"], translation["SO"]])
            self.menu_entry.set(translation["SRM"])
            self.menu_semester = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
                                                        text=translation["semester"])
            self.menu_semester_entry = CustomComboBox(self.tabview.tab(self.other_tab), self, lang, width=141,
                                                      values=self.semester_values + [translation["current"]])
            self.menu_semester_entry.set(self.DEFAULT_SEMESTER)
            self.menu_semester_entry.configure(command=lambda event: self.update_semester_tooltip(
                self.menu_semester_entry))
            self.menu_semester_entry.bind("<FocusOut>", lambda event: self.update_semester_tooltip(
                self.menu_semester_entry))
            self.semesters_tooltips[self.menu_semester_entry] = CTkToolTip(
                self.menu_semester_entry, message=self.get_semester_season(self.DEFAULT_SEMESTER), bg_color="#1E90FF")
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
            for entry in [self.e_class_entry, self.e_section_entry, self.s_class_entry, self.e_semester_entry,
                          self.s_semester_entry, self.menu_entry, self.menu_semester_entry]:
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
            translation = self.load_language()
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
                self.m_swap_buttons.append(CustomButton(master=self.multiple_frame, text="", width=36, height=26,
                                                        image=self.get_image("arrows"),
                                                        command=lambda idx=i: self.swap_rows(idx)))
                self.m_num_class.append(customtkinter.CTkLabel(master=self.multiple_frame, text=f"{i + 1}.", height=26))
                self.m_classes_entry.append(CustomEntry(self.multiple_frame, self, lang,
                                                        placeholder_text=self.placeholder_texts_classes[i], height=26))
                self.m_section_entry.append(CustomEntry(self.multiple_frame, self, lang,
                                                        placeholder_text=self.placeholder_texts_sections[i], height=26))
                self.m_tooltips.append(CTkToolTip(self.m_section_entry[i], message="", bg_color="#1E90FF",
                                                  visibility=False))
                self.m_section_entry[i].bind("<FocusOut>", self.m_sections_bind_wrapper)
                self.m_semester_entry.append(CustomComboBox(self.multiple_frame, self, lang, height=26,
                                                            values=self.semester_values + [translation["current"]]))
                self.m_semester_entry[i].set(self.DEFAULT_SEMESTER)
                self.m_register_menu.append(customtkinter.CTkOptionMenu(
                    master=self.multiple_frame, values=[translation["register"], translation["drop"]], height=26))
                self.m_register_menu[i].set(translation["choose"])
                self.m_num_class[i].bind("<Button-1>", lambda event: self.focus_set())
            self.m_semester_entry[0].bind("<FocusOut>", self.change_semester)
            self.m_semester_entry[0].configure(command=self.change_semester)
            self.semesters_tooltips[self.m_semester_entry[0]] = CTkToolTip(
                self.m_semester_entry[0], message=self.get_semester_season(self.DEFAULT_SEMESTER), bg_color="#1E90FF")
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
            self.save_class_data = customtkinter.CTkCheckBox(master=self.save_frame, text=translation["save_data"],
                                                             command=self.save_classes, onvalue="on", offvalue="off")
            self.save_data_tooltip = CTkToolTip(self.save_class_data, message=translation["save_data_tooltip"],
                                                bg_color="#1E90FF")
            self.auto_enroll = customtkinter.CTkSwitch(master=self.auto_frame, text=translation["auto_enroll"],
                                                       onvalue="on", offvalue="off",
                                                       command=self.auto_enroll_event_handler)
            self.auto_enroll_tooltip = CTkToolTip(self.auto_enroll, message=translation["auto_enroll_tooltip"],
                                                  bg_color="#1E90FF")
            self.multiple_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.m_button_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.save_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.save_class_data.bind("<space>", self.keybind_save_classes)
            self.auto_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.auto_enroll.bind("<space>", lambda event: self.keybind_auto_enroll())
            self.title_multiple.bind("<Button-1>", lambda event: self.focus_set())
            self.m_class.bind("<Button-1>", lambda event: self.focus_set())
            self.m_section.bind("<Button-1>", lambda event: self.focus_set())
            self.m_semester.bind("<Button-1>", lambda event: self.focus_set())
            self.m_choice.bind("<Button-1>", lambda event: self.focus_set())
            for entry in [self.m_classes_entry, self.m_section_entry, self.m_semester_entry]:
                if isinstance(entry, list):
                    for sub_entry in entry:
                        sub_entry.lang = lang
                else:
                    entry.lang = lang
            self.load_saved_classes()

    def has_saved_user_data(self):
        self.cursor_db.execute("SELECT COUNT(*) FROM user_data")
        count = self.cursor_db.fetchone()[0]
        return count > 0

    # saves the config information to the database when the app closes
    def save_user_config(self, include_exit=True):
        field_values = {
            "host": "uprbay.uprb.edu",
            "language": self.language_menu.get(),
            "appearance": self.appearance_mode_optionemenu.get(),
            "scaling": self.scaling_slider.get(),
            "pdf_dir": self.last_save_pdf_dir,
            "win_pos_x": self.winfo_x() if not self.state() == "zoomed" else None,
            "win_pos_y": self.winfo_y() if not self.state() == "zoomed" else None,
            "exit": self.exit_checkbox_state,
        }
        try:
            for field, value in field_values.items():
                # Skip 'exit' field if include_exit is False
                if field == "exit" and not include_exit:
                    continue
                if value is None:
                    continue
                # Save 'host' no matter the result as 'uprbay.uprb.edu'
                if field == "host":
                    if self.saved_host is not None:
                        host_entry_value = self.saved_host
                    else:
                        host_entry_value = self.host_entry.get().replace(" ", "").lower()
                    if not TeraTermUI.check_host(host_entry_value):
                        continue
                result = self.cursor_db.execute(f"SELECT {field} FROM user_config").fetchone()
                if result is None:
                    self.cursor_db.execute(f"INSERT INTO user_config ({field}) VALUES (?)", (value,))
                elif result[0] != value:
                    self.cursor_db.execute(f"UPDATE user_config SET {field} = ? ", (value,))
            if self.must_save_user_data and self.in_student_frame:
                student_id = self.student_id_entry.get().replace(" ", "").replace("-", "")
                code = self.code_entry.get().replace(" ", "")
                self.encrypt_data_db(student_id, code)
            self.cursor_db.execute("SELECT COUNT(*) FROM user_data")
            count = self.cursor_db.fetchone()[0]
            if count == 0:
                self.crypto.reset()
            self.connection_db.commit()
            if not self.saved_classes and self.init_multiple:
                self.delete_saved_classes()
        except sqlite3.Error as err:
            logging.error(f"Database error occurred: {err}")
            self.log_error()
        finally:
            self.connection_db.close()

    def keybind_save_user_data(self, event=None):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            return

        self.remember_me.toggle()
        self.save_user_data()
        if event and event.keysym == "space":
            self.remember_me._on_enter()

    def save_user_data(self):
        now = time.time()
        save_threshold = 1.25
        delay = 1.0
        if now - self.last_save_time > save_threshold:
            if self.save_timer is not None:
                self.save_timer.cancel()
                self.save_timer = None
            self.perform_user_data_save()
            self.last_save_time = time.time()
        else:
            if self.save_timer is not None:
                self.save_timer.cancel()
            self.focus_screen = False
            self.save_timer = threading.Timer(delay, self.perform_user_data_save)
            self.save_timer.start()

    def perform_user_data_save(self):
        self.last_save_time = time.time()
        if self.remember_me.get() == "on":
            student_id = self.student_id_entry.get().replace(" ", "").replace("-", "")
            code = self.code_entry.get().replace(" ", "")
            if ((re.match(r"^(?!000|666|9\d{2})\d{3}(?!00)\d{2}(?!0000)\d{4}$", student_id) or
                 (student_id.isdigit() and len(student_id) == 9)) and code.isdigit() and len(code) == 4):
                if self.focus_screen:
                    self.focus_set()
                    self.focus_screen = True
                self.encrypt_data_db(student_id, code)
                self.connection_db.commit()
            else:
                self.must_save_user_data = True
        else:
            if self.has_saved_user_data():
                self.cursor_db.execute("DELETE FROM user_data")
                self.connection_db.commit()
                self.crypto.reset()

    def encrypt_data_db(self, st_id, code):
        self.must_save_user_data = False
        sid_cipher, sid_nonce, sid_tag = self.crypto.encrypt(st_id)
        code_cipher, code_nonce, code_tag = self.crypto.encrypt(code)
        self.cursor_db.execute(
            "INSERT INTO user_data (id, student_id, code, nonce_student_id, nonce_code, tag_student_id, tag_code) "
            "VALUES (1, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET student_id = excluded.student_id, "
            "code = excluded.code, nonce_student_id = excluded.nonce_student_id, nonce_code = excluded.nonce_code, "
            "tag_student_id = excluded.tag_student_id, tag_code = excluded.tag_code",
            (sid_cipher, code_cipher, sid_nonce, code_nonce, sid_tag, code_tag))

    def keybind_save_classes(self, event=None):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            return

        self.save_class_data.toggle()
        self.save_classes()
        if event and event.keysym == "space":
            self.save_class_data._on_enter()

    # saves class information for another session
    def save_classes(self):
        save = self.save_class_data.get()
        translation = self.load_language()
        if save == "on":
            self.cursor_db.execute("DELETE FROM saved_classes")
            self.connection_db.commit()
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
                    valid_semester_format = re.fullmatch("^[A-Z][0-9]{2}$", semester_value)
                    if not valid_semester_format:
                        semester_value = None
                register_value = self.m_register_menu[index].get()
                if not class_value or not section_value or not semester_value or register_value in ("Choose", "Escoge"):
                    is_empty = True
                elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", class_value) or not re.fullmatch(
                        "^[A-Z0-9]{3}$", section_value):
                    is_invalid_format = True
                else:
                    self.cursor_db.execute("INSERT INTO saved_classes (class, section, semester, action, timestamp) "
                                        "VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                                           (class_value, section_value, semester_value, register_value))
                    self.connection_db.commit()
                    self.saved_classes = True

            if is_empty:
                self.show_error_message(330, 255, translation["failed_saved_lack_info"])
                self.save_class_data.deselect()
            elif is_invalid_format:
                self.show_error_message(330, 255, translation["failed_saved_invalid_info"])
                self.save_class_data.deselect()
            else:
                self.cursor_db.execute("SELECT COUNT(*) FROM saved_classes")
                row_count = self.cursor_db.fetchone()[0]
                if row_count == 0:
                    self.show_error_message(330, 255, translation["failed_saved_invalid_info"])
                    self.save_class_data.deselect()
                else:
                    self.changed_classes = set()
                    self.changed_sections = set()
                    self.changed_semesters = set()
                    self.changed_registers = set()
                    for i in range(8):
                        self.m_register_menu[i].configure(
                            command=lambda value, idx=i: self.detect_register_menu_change(value, idx))
                        self.m_classes_entry[i].bind("<FocusOut>", self.detect_change)
                        self.m_section_entry[i].bind("<FocusOut>", self.m_sections_bind_wrapper)
                    self.show_success_message(350, 265, translation["saved_classes_success"])
        if save == "off":
            self.cursor_db.execute("DELETE FROM saved_classes")
            self.connection_db.commit()
            self.saved_classes = False
            for i in range(8):
                self.m_register_menu[i].configure(command=lambda value: self.focus_set())
                self.m_classes_entry[i].unbind("<FocusOut>")
                self.m_section_entry[i].unbind("<FocusOut>")

    # Compares the saved classes in the database with the current entries in the application
    def delete_saved_classes(self):
        saved_data = self.cursor_db.execute(
            "SELECT class, section, semester, action FROM saved_classes WHERE class IS NOT NULL").fetchall()

        if not saved_data:
            return

        normalized_saved_data = []
        for class_value, section_value, semester_value, action_value in saved_data:
            normalized_class = class_value.upper().replace(" ", "").replace("-", "")
            normalized_section = section_value.upper().replace(" ", "").replace("-", "")
            normalized_semester = semester_value.upper().replace(" ", "")
            normalized_action = action_value.upper().replace(" ", "")
            normalized_saved_data.append((normalized_class, normalized_section, normalized_semester, normalized_action))

        entry_data = []
        num_saved_entries = len(normalized_saved_data)
        for index in range(num_saved_entries):
            class_value = self.m_classes_entry[index].get().upper().replace(" ", "").replace("-", "")
            section_value = self.m_section_entry[index].get().upper().replace(" ", "").replace("-", "")
            semester_value = self.m_semester_entry[index].get().upper().replace(" ", "")
            action_value = self.m_register_menu[index].get().upper().replace(" ", "")
            entry_data.append((class_value, section_value, semester_value, action_value))

        num_field_differences = 0
        total_fields_compared = 0
        fields = ["class", "section", "semester", "action"]
        num_fields = len(fields)

        # Compare only the number of saved entries
        for i in range(num_saved_entries):
            saved_item = normalized_saved_data[i]
            entry_item = entry_data[i]

            # Compare individual fields
            for j in range(num_fields):
                saved_value = saved_item[j]
                entry_value = entry_item[j]

                # Skip comparison if both values are empty
                if not saved_value and not entry_value:
                    continue

                # Increment total fields compared
                total_fields_compared += 1
                if saved_value != entry_value:
                    num_field_differences += 1

        if total_fields_compared == 0:
            # No meaningful data to compare
            return

        difference_ratio = num_field_differences / total_fields_compared
        if difference_ratio > 0.5:
            # Data is mostly different; delete from database
            self.cursor_db.execute("DELETE FROM saved_classes")
            self.connection_db.commit()

    # shows the important information window
    def show_loading_screen(self):
        translation = self.load_language()
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
        if self.help is not None and self.help.winfo_exists():
            self.help.attributes("-disabled", True)
        if self.status is not None and self.status.winfo_exists():
            self.status.attributes("-disabled", True)
        if self.timer_window is not None and self.timer_window.winfo_exists():
            self.timer_window.attributes("-disabled", True)
        self.disable_widgets(self, self.help, self.status)
        self.loading_screen_start_time = time.time()
        return self.loading_screen

    def loading_screen_geometry(self):
        translation = self.load_language()
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
        center_x += 105
        monitor = TeraTermUI.get_monitor_bounds(main_window_x, main_window_y)
        monitor_x, monitor_y, monitor_width, monitor_height = monitor.x, monitor.y, monitor.width, monitor.height
        center_x = max(monitor_x, min(center_x, monitor_x + monitor_width - loading_screen_width))
        center_y = max(monitor_y, min(center_y, monitor_y + monitor_height - loading_screen_height))
        window_geometry = f"{loading_screen_width}x{loading_screen_height}+{center_x}+{center_y}"
        self.loading_screen.geometry(window_geometry)

    @staticmethod
    def disable_loading_screen_close():
        return "break"

    def lift_loading_screen(self):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            if self.winfo_viewable():
                self.loading_screen.lift()

            self.after(100, lambda: self.lift_loading_screen())

    # tells the loading screen when it should stop and close
    def update_loading_screen(self, loading_screen, future):
        current_time = time.time()
        if current_time - self.loading_screen_start_time > 30:
            if self.loading_screen.attributes("-topmost"):
                self.loading_screen.attributes("-topmost", False)
                self.loading_screen.lower()
                self.loading_screen.lift()
                self.lift_loading_screen()
        if (not self.curr_skipping_auth and future.done()) or (current_time - self.loading_screen_start_time > 90):
            self.attributes("-disabled", False)
            if self.help is not None and self.help.winfo_exists():
                self.help.attributes("-disabled", False)
            if self.status is not None and self.status.winfo_exists():
                self.status.attributes("-disabled", False)
            if self.timer_window is not None and self.timer_window.winfo_exists():
                self.timer_window.attributes("-disabled", False)
            self.after(0, self.update_widgets)
            if self.loading_screen is not None and self.loading_screen.winfo_exists():
                self.loading_screen.withdraw()
            self.progress_bar.reset()
            self.loading_screen_status = None
            if current_time - self.loading_screen_start_time > 90:
                translation = self.load_language()
                self.timeout_occurred = True
                self.play_sound("error.wav")
                CTkMessagebox(title=translation["automation_error_title"], message=translation["timeout_error"],
                              icon="warning", button_width=380)
        else:
            self.after(100, self.update_loading_screen, loading_screen, future)

    def disable_widgets(self, *containers):
        valid_containers = [container for container in containers if container is not None]
        stack = list(valid_containers)
        while stack:
            current_container = stack.pop()
            for widget in current_container.winfo_children():
                if not widget.winfo_viewable() or widget in [self.language_menu, self.appearance_mode_optionemenu]:
                    continue

                widget_types = (tk.Entry, tk.Text, customtkinter.CTkCheckBox, customtkinter.CTkRadioButton,
                                customtkinter.CTkSwitch, customtkinter.CTkOptionMenu)
                if isinstance(widget, widget_types) and widget.cget("state") != "disabled":
                    widget.configure(state="disabled")
                elif hasattr(widget, "winfo_children"):
                    stack.append(widget)

    def enable_widgets(self, *containers):
        valid_containers = [container for container in containers if container is not None]
        stack = list(valid_containers)
        while stack:
            current_container = stack.pop()
            for widget in current_container.winfo_children():
                if not widget.winfo_viewable() or widget in [self.language_menu, self.appearance_mode_optionemenu]:
                    continue

                widget_types = (tk.Entry, tk.Text, customtkinter.CTkCheckBox, customtkinter.CTkRadioButton,
                                customtkinter.CTkSwitch, customtkinter.CTkOptionMenu)
                if isinstance(widget, widget_types) and widget.cget("state") != "normal":
                    widget.configure(state="normal")
                elif hasattr(widget, "winfo_children"):
                    stack.append(widget)

    def update_widgets(self):
        if self.countdown_running and self.in_multiple_screen:
            self.auto_enroll.configure(state="normal")
            self.save_class_data.configure(state="normal")
            return

        self.enable_widgets(self, self.help, self.status)
        if self.intro_box._textbox.cget("state") == "normal":
            self.intro_box.configure(state="disabled")
        if self.enrolled_classes_data is not None:
            translation = self.load_language()
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
        for proc in psutil.process_iter(attrs=["name"]):
            try:
                proc_info = proc.as_dict(attrs=["name"])
                proc_name = proc_info.get("name", "").lower()
                if process in proc_name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
                logging.error(f"Exception while processing {proc}: {err}")
                continue
        return False

    # function to check if multiple of the specified processes are running or not
    @staticmethod
    def checkMultipleProcessesRunning(*processNames):
        processNames = [p.lower() for p in processNames]
        running_process_names = set()
        for proc in psutil.process_iter(attrs=["name"]):
            try:
                proc_name = proc.info["name"].lower()
                running_process_names.add(proc_name)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
                logging.error(f"Exception while processing {proc}: {err}")
                continue
        running_processes = [name for name in processNames if name in running_process_names]
        return running_processes

    # function that checks if there's more than 1 instance of Tera Term running
    @staticmethod
    def countRunningProcesses(processName):
        count = 0
        process = processName.lower()
        for proc in psutil.process_iter(attrs=["name"]):
            try:
                proc_info = proc.as_dict(attrs=["name"])
                proc_name = proc_info.get("name", "").lower()
                if process in proc_name:
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
                logging.error(f"Exception while processing {proc}: {err}")
                continue
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
                win32gui.SendMessage(hwnd, win32con.WM_CLOSE, 0, 0)

        win32gui.EnumWindows(window_enum_handler, titles_to_close)

    @staticmethod
    def check_window_exists(window_title, retries=5, delay=1):
        for _ in range(retries):
            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                return True
            time.sleep(delay)
        raise Exception(f"The window with title '{window_title}' was not found after {retries} retries")

    # function that checks if UPRB server is currently running
    def check_server(self):
        translation = self.load_language()
        HOST = "uprbay.uprb.edu"
        PORT = 22
        timeout = 3

        try:
            with socket.create_connection((HOST, PORT), timeout=timeout):
                try:
                    idle = self.cursor_db.execute("SELECT idle FROM user_config").fetchone()
                except Exception as err:
                    idle = ["Disabled"]
                    logging.error("An error occurred: %s", err)
                    self.log_error()
                if idle[0] != "Disabled":
                    self.after(500, self.ssh_monitor.sample)
                # the connection attempt succeeded
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            # the connection attempt failed
            self.after(100, self.show_error_message, 385, 245, translation["uprb_down"])
            return False

    # captures a screenshot of tera term and performs OCR
    def capture_screenshot(self):
        max_retries = 3
        retries = 0
        expected_menu_keywords = ["File", "Edit", "Setup", "Control", "Window", "Help"]
        while retries < max_retries:
            time.sleep(1)
            translation = self.load_language()
            tesseract_dir_path = self.app_temp_dir / "Tesseract-OCR"
            default_tesseract_path = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
            alternate_tesseract_path = Path("C:/Users/arman/AppData/Local/Programs/Tesseract-OCR/tesseract.exe")
            if self.tesseract_unzipped and (tesseract_dir_path.is_dir() or default_tesseract_path.is_file()
                                            or alternate_tesseract_path.is_file()):
                window_title = "uprbay.uprb.edu - Tera Term VT"
                hwnd = win32gui.FindWindow(None, window_title)
                self.focus_tera_term()
                x, y, right, bottom = get_window_rect(hwnd)
                width = right - x
                height = bottom - y
                crop_margin = (2, 10, 10, 2)
                if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
                    self.loading_screen.attributes("-topmost", False)
                    self.loading_screen.lower()
                    self.loading_screen.lift()
                with mss() as sct:
                    monitor = {
                        "top": y,
                        "left": x,
                        "width": width,
                        "height": height
                    }
                    screenshot = sct.grab(monitor)
                    img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)
                    if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
                        self.after(150, self.loading_screen.attributes, "-topmost", True)
                    img = img.crop((crop_margin[0], crop_margin[1], img.width - crop_margin[2],
                                    img.height - crop_margin[3])).convert("L")
                    img = img.resize((img.width * 2, img.height * 2), resample=Image.Resampling.LANCZOS)
                    # img.save("screenshot.png")
                    custom_config = r"--oem 3 --psm 6"
                    text = pytesseract.image_to_string(img, config=custom_config)
                    matches = sum(1 for keyword in expected_menu_keywords if keyword in text)
                    if matches >= 3:
                        return text
                    retries += 1
            else:
                try:
                    with SevenZipFile(self.zip_path, mode="r") as z:
                        z.extractall(self.app_temp_dir)
                    tesseract_dir = Path(self.app_temp_dir) / "Tesseract-OCR"
                    pytesseract.pytesseract.tesseract_cmd = str(tesseract_dir / "tesseract.exe")
                    self.tesseract_unzipped = True
                    gc.collect()
                    return self.capture_screenshot()
                except Exception as err:
                    logging.error(f"Error occurred during unzipping: {str(err)}")
                    self.tesseract_unzipped = False
                    self.after(100, self.show_error_message, 320, 225, translation["tesseract_error"])
                    return

        return text

    # creates pdf of the table containing for the searched class
    def create_search_pdf(self, data_list, classes_list, filepath, semesters_list):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak

        title = None
        semester_header = None
        class_header = None
        lang = self.language_menu.get()
        # Prepare the PDF document
        pdf = SimpleDocTemplate(filepath,pagesize=letter)
        # Add metadata to the PDF
        if len(classes_list) == 1:
            if lang == "English":
                title = f"Class Data for {classes_list[0]}"
            elif lang == "Español":
                title = f"Datos de la Clase para {classes_list[0]}"
        else:
            if len(set(semesters_list)) == 1:
                if lang == "English":
                    title = f"Data for Classes for {semesters_list[0]} Semester"
                elif lang == "Español":
                    title = f"Datos de las Clases para el Semestre {semesters_list[0]}"
            else:
                if lang == "English":
                    title = "Data for Classes Across Multiple Semesters"
                elif lang == "Español":
                    title = "Datos de las Clases para Varios Semestres"
        pdf.title = title
        pdf.author = "Tera Term UI"
        pdf.subject = (f"Classes information for semesters: {', '.join(set(semesters_list))}"
                       if lang == "English" else f"Información de las clases para los semestres: "
                                                 f"{', '.join(set(semesters_list))}")
        pdf.creator = "Tera Term UI PDF Generator"
        pdf.producer = "ReportLab PDF Library"
        pdf.keywords = ["class data", "academic", "schedule"] + classes_list + semesters_list
        pdf.creation_date = datetime.now()
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
                ("BACKGROUND", (0, 0), (-1, 0), blue),  # Header background color
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),  # Text color
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),  # Center text horizontally
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),  # Center text vertically
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # Bold font for headers
                ("FONTSIZE", (0, 0), (-1, 0), 14),  # Header font size
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),  # Padding for headers
                ("BACKGROUND", (0, 1), (-1, -1), gray),  # Background color for data rows
                ("GRID", (0, 0), (-1, -1), 1, colors.black),  # Add grid lines
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

    @staticmethod
    def get_unique_filename(directory, filename):
        base, ext = os.path.splitext(filename)
        filepath = os.path.join(directory, filename)

        counter = 1
        while os.path.exists(filepath):
            filepath = os.path.join(directory, f"{base} ({counter}){ext}")
            counter += 1

        return os.path.basename(filepath)

    # function for the user to download the created pdf to their computer
    def download_search_classes_as_pdf(self):
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            return

        translation = self.load_language()
        self.focus_set()

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
            base_filename = f"{semester_list[0]}_{classes_list[0]}_{translation['class_data']}.pdf"
        elif all_same_semester:
            base_filename = f"{semester_list[0]}_{translation['classes_data']}.pdf"
        else:
            base_filename = f"{translation['multiple_semesters']}_{translation['classes_data']}.pdf"

        # Define default save directory
        if self.last_save_pdf_dir is not None:
            initial_dir = self.last_save_pdf_dir
        else:
            home = os.path.expanduser("~")
            initial_dir = os.path.join(home, "Downloads")

        unique_filename = TeraTermUI.get_unique_filename(initial_dir, base_filename)
        filepath = filedialog.asksaveasfilename(
            title=translation["save_pdf"], defaultextension=".pdf", initialdir=initial_dir,
            filetypes=[("PDF Files", "*.pdf")], initialfile=unique_filename)

        # Check if user cancelled the file dialog
        if not filepath:
            self.focus_set()
            return

        self.last_save_pdf_dir = os.path.dirname(filepath)
        classes_list, data, semester_list = TeraTermUI.merge_tables(classes_list, data, semester_list)
        self.create_search_pdf(data, classes_list, filepath, semester_list)
        self.show_success_message(350, 265, translation["pdf_save_success"])

    def copy_cell_data_to_clipboard(self, cell_data):
        translation = self.load_language()
        cell_value = cell_data.cget("text").strip()
        if not cell_value:
            return

        cell_value = re.sub(r"\n\s*", " ", cell_value)
        if re.match(r"\d{1,2}:\d{2} [APM]{2} \d{1,2}:\d{2} [APM]{2}", cell_value):
            cell_value = re.sub(r"([APM]{2}) (\d{1,2}:\d{2})", r"\1 - \2", cell_value)

        self.focus_set()
        self.clipboard_clear()
        self.clipboard_append(cell_value)
        self.update_idletasks()

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
            self.notice_user_text = None
            if self.notice_user_msg is not None:
                self.notice_user_msg.destroy()
            self.notice_user_msg = None
            gc.collect()

    def lift_tooltip(self):
        if self.tooltip is not None and self.tooltip.winfo_exists():
            self.tooltip.lift()

            self.after(100, self.lift_tooltip)

    def transfer_class_data_to_enroll_tab(self, event, cell):
        section_text = cell.cget("text")
        if not section_text.strip():
            return

        self.e_class_entry.delete(0, "end")
        self.e_section_entry.delete(0, "end")
        display_class, _, semester_text, _, _, _ = self.class_table_pairs[self.current_table_index]
        class_text = display_class.cget("text").split("-")[0].strip()
        self.e_class_entry.insert(0, class_text)
        self.e_section_entry.insert(0, section_text)
        self.e_semester_entry.set(semester_text)
        self.register.select()
        self.check_class_time()

        translation = self.load_language()
        added_multiple = False
        duplicate_exists = False
        replaced_section = False
        msg = None
        delay = None

        first_entry_semester = self.m_semester_entry[0].get() if self.m_classes_entry[0].get().strip() else None
        if first_entry_semester and first_entry_semester != semester_text:
            msg = translation["pasted"]
            delay = 3500
        else:
            existing_index = -1
            for i in range(8):
                existing_class = self.m_classes_entry[i].get().strip()
                existing_section = self.m_section_entry[i].get().strip()
                if existing_class == class_text:
                    if existing_section == section_text:
                        duplicate_exists = True
                        break
                    elif self.m_semester_entry[i].get() == semester_text:
                        existing_index = i
                        break

            if not duplicate_exists:
                if existing_index >= 0:
                    self.m_classes_entry[existing_index].delete(0, "end")
                    self.m_section_entry[existing_index].delete(0, "end")
                    self.m_classes_entry[existing_index].insert(0, class_text)
                    self.m_section_entry[existing_index].insert(0, section_text)
                    self.m_register_menu[existing_index].set(translation["register"])
                    replaced_section = True
                    current_visible = sum(1 for j in range(8) if self.m_classes_entry[j].winfo_viewable())
                    if existing_index >= current_visible:
                        while self.a_counter < existing_index:
                            self.add_event()

                    self.check_class_conflicts()
                    dummy_event = type("Dummy", (object,), {"widget": self.m_section_entry[existing_index]})()
                    self.detect_change(dummy_event)
                    msg = translation["pasted_mult"]
                    delay = 5000
                else:
                    for i in range(8):
                        if not self.m_classes_entry[i].get().strip() and not self.m_section_entry[i].get().strip():
                            self.m_classes_entry[i].insert(0, class_text)
                            self.m_section_entry[i].insert(0, section_text)
                            if i == 0:
                                self.m_semester_entry[i].set(semester_text)
                            self.m_register_menu[i].set(translation["register"])
                            added_multiple = True
                            current_visible = sum(1 for j in range(8) if self.m_classes_entry[j].winfo_viewable())
                            if i >= current_visible:
                                while self.a_counter < i:
                                    self.add_event()

                            self.check_class_conflicts()
                            dummy_event_class = type("Dummy", (object,), {"widget": self.m_classes_entry[i]})()
                            self.detect_change(dummy_event_class)
                            dummy_event_section = type("Dummy", (object,), {"widget": self.m_section_entry[i]})()
                            self.detect_change(dummy_event_section)
                            break
                if added_multiple:
                    msg = translation["pasted_mult"]
                    delay = 5000
                elif not replaced_section:
                    msg = translation["pasted"]
                    delay = 3500
            else:
                msg = translation["pasted"]
                delay = 3500

        self.focus_set()
        # Close existing tooltip if any
        self.destroy_tooltip()

        # Create new tooltip
        x, y = self.winfo_pointerxy()
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.transient(self)
        self.tooltip.config(bg="#145DA0")
        self.tooltip.wm_geometry(f"+{x + 20}+{y + 20}")

        label = tk.Label(self.tooltip, text=msg, bg="#145DA0", fg="#fff", font=("Arial", 10, "bold"))
        label.pack(padx=5, pady=5)
        self.lift_tooltip()

        # Auto-destroy after a couple seconds and reset the tooltip variable
        self.tooltip.after(delay, self.destroy_tooltip)

    @staticmethod
    def open_student_help(event, cell):
        av_value = cell.cget("text")
        if av_value == "RSVD":
            webbrowser.open("https://studenthelp.uprb.edu/")

    def open_professor_profile(self, event, cell):
        def remove_prefixes(name_parts):
            return [part for part in name_parts if part.lower() not in ["de", "del"]]

        def attempt_open_url(prof_names, cache_key):
            first_name = prof_names[2].lower()
            prioritized_last_names = [prof_names[0].lower(), "-".join(prof_names[:2]).lower()]
            urls = [f"https://notaso.com/professors/{first_name}-{ln}/" for ln in prioritized_last_names]
            headers = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                      "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")}
            found_event = threading.Event()

            def head_request(url, session_in):
                if found_event.is_set():
                    return None, url
                try:
                    head_respond = session_in.head(url, headers=headers, timeout=5)
                    return head_respond, url
                except requests.exceptions.RequestException as err:
                    logging.warning(f"Failed to open URL: {url}, Error: {err}")
                    return None, url

            with requests.Session() as session_obj:
                future_to_url = {self.thread_pool.submit(head_request, url, session_obj) for url in urls}
                for future in as_completed(future_to_url):
                    head_resp, url = future.result()
                    if head_resp and head_resp.status_code == 200:
                        found_event.set()
                        self.url_cache[cache_key] = url
                        self.thread_pool.submit(lambda: webbrowser.open(url))
                        for fut in future_to_url:
                            fut.cancel()
                        break

        instructor_text = cell.cget("text")
        if not instructor_text.strip():
            return

        norm_name = " ".join(instructor_text.split())
        if norm_name in self.url_cache:
            cached_url = self.url_cache[norm_name]
            self.thread_pool.submit(lambda: webbrowser.open(cached_url))
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
            "COUTIN RODICIO RICARDO": "https://notaso.com/professors/ricardo-coutin-rodicio-2/",
            "GONZALEZ GONZALEZ JOSE": "https://notaso.com/professors/jose-m-gonzalez-gonzalez/",
            "ROBLES GARCIA, F": "https://notaso.com/professors/francheska-robles/",
            "SEXTO SANTIAGO MARIELIS": "https://notaso.com/professors/marie-sexto/",
            "ALEMAN JIMENEZ": "https://notaso.com/professors/keila-aleman/",
            "SIERRA PADILLA": "https://notaso.com/professors/javier-sierra-padilla-2/",
            "CORREA ROSADO ALVARO R.": "https://notaso.com/professors/alvaro-correa-2/",
            "QUINONES CRUZ MIRIAM I.": "https://notaso.com/professors/miriam-quinonez/",
            "BEAUCHAMP RODRIGUEZ ELIA": "https://notaso.com/professors/elias-beauchamp-2/"
        }
        if norm_name in url_mapping:
            hard_coded_url = url_mapping[norm_name]
            self.url_cache[norm_name] = hard_coded_url
            self.thread_pool.submit(lambda: webbrowser.open(hard_coded_url))
            return

        processed_parts = remove_prefixes(instructor_text.split())
        if len(processed_parts) >= 3:
            self.thread_pool.submit(attempt_open_url, processed_parts, norm_name)

    # displays the extracted data of searched classes into a table
    def display_searched_class_data(self, data):
        translation = self.load_language()
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

        self.image_search.grid_forget()
        self.notice_search.grid_forget()
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
        duplicate_index = self.find_duplicate(self.get_class_for_table, self.get_semester_for_table,
                                              self.show_all_sections, available_values)
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

        tooltip_messages = {
            translation["sec"]: translation["tooltip_sec"],
            translation["m"]: translation["tooltip_m"],
            translation["cred"]: translation["tooltip_cred"],
            translation["days"]: translation["tooltip_days"],
            translation["times"]: translation["tooltip_times"],
            translation["av"]: translation["tooltip_av"],
            translation["instructor"]: translation["tooltip_instructor"],
        }

        new_table = None
        display_class = None
        if self.hidden_tables and self.hidden_labels:
            matched_index = None
            for i, hidden_table in enumerate(self.hidden_tables):
                if hidden_table.values == table_values:
                    matched_index = i
                    break
            if matched_index is not None:
                display_class = self.hidden_labels.pop(matched_index)
                new_table = self.hidden_tables.pop(matched_index)
                display_class.configure(text=self.get_class_for_table)
                instructor_col_index = headers.index(translation["instructor"])
                new_table.edit_column(instructor_col_index, width=140)
                last_column_index = new_table.columns - 1
                new_table.unhover_cell(0, last_column_index)
            else:
                if self.hidden_tables and self.hidden_labels:
                    target_rows = len(table_values)
                    best_index = len(self.hidden_tables) - 1
                    smallest_row_change = float("inf")
                    for i, table in enumerate(self.hidden_tables):
                        diff = abs(table.cget("row") - target_rows)
                        if diff < smallest_row_change:
                            smallest_row_change = diff
                            best_index = i
                            if diff == 0:
                                break
                    display_class = self.hidden_labels.pop(best_index)
                    new_table = self.hidden_tables.pop(best_index)
                    display_class.configure(text=self.get_class_for_table)
                    new_table.refresh_table(table_values)
        else:
            new_table = CTkTable(self.search_scrollbar, column=len(headers), row=len(table_values),
                                 values=table_values, header_color="#145DA0", hover_color="#339CFF", command=lambda row,
                                 col: self.copy_cell_data_to_clipboard(new_table.get_cell(row, col)))
            display_class = customtkinter.CTkLabel(self.search_scrollbar, text=self.get_class_for_table,
                                                   font=customtkinter.CTkFont(size=15, weight="bold", underline=True))
            display_class.bind("<Button-1>", lambda event: self.focus_set())

        self.table = new_table
        self.original_table_data[new_table] = original_table_values

        for i, header in enumerate(headers):
            cell = new_table.get_cell(0, i)
            tooltip_message = tooltip_messages[header]
            tooltip = CTkToolTip(cell, message=tooltip_message, bg_color="#989898", alpha=0.90)
            self.table_tooltips[cell] = tooltip

        for i, header in enumerate(headers):
            if i < 4 or i == 5:
                new_table.edit_column(i, width=55)
        instructor_col_index = headers.index(translation["instructor"])
        av_col_index = headers.index(translation["av"])
        for row in range(1, len(table_values)):
            section_cell = new_table.get_cell(row, 0)
            new_table.bind_cell(row, 0, "<Button-3>", lambda event, t_cell=section_cell:
            self.transfer_class_data_to_enroll_tab(event, t_cell))
            instructor_cell = new_table.get_cell(row, instructor_col_index)
            new_table.bind_cell(row, instructor_col_index, "<Button-3>", lambda event, t_cell=instructor_cell:
            self.open_professor_profile(event, t_cell))
            av_cell = new_table.get_cell(row, av_col_index)
            new_table.bind_cell(row, av_col_index, "<Button-3>", lambda event, t_cell=av_cell:
            TeraTermUI.open_student_help(event, t_cell))
        for col_index in range(len(headers)):
            new_table.bind_cell(0, col_index, "<Button-3>",
                                lambda event: self.move_tables_overlay_event())

        if self.table_count is None:
            table_count_label = f"{translation['table_count']}{len(self.class_table_pairs)}/20"
            table_position_label = (f" {translation['table_position']}{self.current_table_index + 1}"
                                    f"/{len(self.class_table_pairs)}")
            self.table_pipe = customtkinter.CTkLabel(self.search_scrollbar, text="|")
            self.table_count = customtkinter.CTkLabel(self.search_scrollbar, text=table_count_label)
            self.table_position = customtkinter.CTkLabel(self.search_scrollbar, text=table_position_label)
            self.previous_button = CustomButton(master=self.search_scrollbar, text=translation["previous"],
                                                command=self.show_previous_table)
            self.next_button = CustomButton(master=self.search_scrollbar, text=translation["next"],
                                            command=self.show_next_table)
            self.remove_button = CustomButton(master=self.search_scrollbar, text=translation["remove"],
                                              hover_color="darkred", fg_color="red", command=self.remove_current_table)
            self.download_search_pdf = CustomButton(master=self.search_scrollbar, text=translation["pdf_save_as"],
                                                    hover_color="#173518", fg_color="#2e6930",
                                                    command=self.download_search_classes_as_pdf)
            self.table_count_tooltip = CTkToolTip(self.table_count, message=translation["table_count_tooltip"],
                                                  bg_color="#989898", alpha=0.90)
            self.table_position_tooltip = CTkToolTip(self.table_position, message=translation["table_position_tooltip"],
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

        self.class_table_pairs.append((display_class, new_table, self.get_semester_for_table, self.show_all_sections,
                                       available_values, self.search_next_page_status))
        if self.sort_by is not None and self.sort_by.get() != translation["sort_by"] and \
                self.sort_by.get() != translation["original_data"]:
            self.last_sort_option = (self.sort_by.get(), len(self.class_table_pairs))
        self.check_and_update_labels()
        self.current_table_index = len(self.class_table_pairs) - 1
        self.table_position.configure(text=f"{self.current_table_index + 1}")

        if len(self.class_table_pairs) > 20:
            display_class_to_remove, table_to_remove, _, _, _, more_sections = self.class_table_pairs[0]
            display_class_to_remove.grid_remove()
            table_to_remove.grid_remove()
            for i in range(table_to_remove.rows):
                for j in range(table_to_remove.columns):
                    cell = table_to_remove.get_cell(i, j)
                    if cell in self.table_tooltips:
                        self.table_tooltips[cell].destroy()
                        self.table_tooltips[cell].widget = None
                        self.table_tooltips[cell].message = None
                        del self.table_tooltips[cell]
                    table_to_remove.unbind_cell(i, j)
            self.hidden_tables.append(table_to_remove)
            self.hidden_labels.append(display_class_to_remove)

            if table_to_remove in self.original_table_data:
                del self.original_table_data[table_to_remove]

            if more_sections:
                self.search_next_page.grid_forget()
                self.search.grid(row=1, column=1, padx=(385, 0), pady=(0, 5), sticky="n")
                self.search.configure(width=140)
                self.search_next_page_status = False

            del self.class_table_pairs[0]
            self.current_table_index = max(0, self.current_table_index - 1)
            self.table_count.configure(text_color=("black", "white"))

        self.display_current_table()

        self.table_count.grid(row=4, column=1, padx=(0, 95), pady=(10, 0), sticky="n")
        self.table_pipe.grid(row=4, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
        self.table_position.grid(row=4, column=1, padx=(95, 0), pady=(10, 0), sticky="n")
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
        table_position_label = (f" {translation['table_position']}{self.current_table_index + 1}"
                                f"/{len(self.class_table_pairs)}")
        self.table_count.configure(text=table_count_label)
        self.table_position.configure(text=table_position_label)
        if len(self.class_table_pairs) == 20:
            self.table_count.configure(text_color="red")
        self.table_count.bind("<Button-1>", lambda event: self.focus_set())
        self.table_pipe.bind("<Button-1>", lambda event: self.focus_set())
        self.table_position.bind("<Button-1>", lambda event: self.focus_set())
        self.sort_by.bind("<FocusIn>", lambda event: self.search_scrollbar.scroll_to_widget(self.sort_by))
        self.bind("<Control-s>", lambda event: self.download_search_classes_as_pdf())
        self.bind("<Control-S>", lambda event: self.download_search_classes_as_pdf())
        self.bind("<Control-w>", lambda event: self.keybind_remove_current_table())
        self.bind("<Control-W>", lambda event: self.keybind_remove_current_table())

    def find_duplicate(self, new_display_class, new_semester, show_all_sections_state, available_values):
        for index, (display_class, table, semester, existing_show_all_sections_state,
                    existing_available_values, _) in enumerate(self.class_table_pairs):
            if (display_class.cget("text").split("-")[0].strip().split(" #")[0] == new_display_class
                    and semester == new_semester and existing_show_all_sections_state == show_all_sections_state
                    and sorted(existing_available_values) == sorted(available_values)):
                return index
        return None

    def sort_data(self, data, sort_by_option):
        translation = self.load_language()
        headers = list(data[0].keys()) if data else []
        time_key = translation["times"] if translation["times"] in headers else None
        av_key = translation["av"] if translation["av"] in headers else None
        section_key = translation["sec"] if translation["sec"] in headers else None
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
            try:
                av_int = int(av_value)
                if 100 <= av_int <= 999:
                    return float("inf")
                return av_int
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
            primary_value = get_time_minutes(entry[1]) if primary_key == time_key else parse_av_value(
                entry[1].get(primary_key, ""))
            secondary_value = get_time_minutes(entry[1]) if secondary_key == time_key else parse_av_value(
                entry[1].get(secondary_key, ""))

            if primary_value == float("inf"):
                primary_value = float("-inf") if reverse_sort else float("inf")
            if secondary_value == float("inf"):
                secondary_value = float("-inf") if reverse_sort else float("inf")

            return primary_value, secondary_value

        reverse_sort = False
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
        for _, row in non_standard_positions:
            sorted_data.append(row)

        return sorted_data

    def sort_tables(self, sort_by_option):
        translation = self.load_language()

        if self.last_sort_option == (sort_by_option, len(self.class_table_pairs)) or \
                (not self.last_sort_option and sort_by_option == translation["original_data"]):
            return

        if sort_by_option == translation["original_data"]:
            for _, table, _, _, _, _ in self.class_table_pairs:
                original_data = self.original_table_data[table]
                table.update_values(original_data)
            self.last_sort_option = (sort_by_option, len(self.class_table_pairs))
            self.after(0, self.search_scrollbar.scroll_to_top)
            self.after(0, self.focus_set)
            return

        headers = None
        time_index = av_index = section_index = -1

        for _, table, _, _, _, _ in self.class_table_pairs:
            table_data = table.values
            if not headers:
                headers = table_data[0]
                time_index = headers.index(translation["times"]) if translation["times"] in headers else -1
                av_index = headers.index(translation["av"]) if translation["av"] in headers else -1
                section_index = headers.index(translation["sec"]) if translation["sec"] in headers else -1

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
                            minutes = int(datetime.strptime(t, "%I:%M %p").strftime("%H")) * 60 + \
                                      int(datetime.strptime(t, "%I:%M %p").strftime("%M"))
                            memoized_times[t] = minutes
                        except ValueError:
                            minutes = float("inf")
                            memoized_times[t] = minutes
                    total_minutes += minutes
                    if minutes == float("inf"):
                        return minutes

                memoized_times[times_key] = total_minutes
                return total_minutes

            def parse_av_value(av_value):
                try:
                    av_int = int(av_value)
                    if 100 <= av_int <= 999:
                        return float("inf")
                    return av_int
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
                primary_value = get_time_minutes(entry[1]) if primary_index == time_index else parse_av_value(
                    entry[1][primary_index])
                secondary_value = get_time_minutes(entry[1]) if secondary_index == time_index else parse_av_value(
                    entry[1][secondary_index])

                if primary_value == float("inf"):
                    primary_value = float("-inf") if reverse_sort else float("inf")
                if secondary_value == float("inf"):
                    secondary_value = float("-inf") if reverse_sort else float("inf")

                return primary_value, secondary_value

            reverse_sort = False
            if sort_by_option in [translation["time_asc"], translation["time_dec"]] and time_index != -1:
                reverse_sort = (sort_by_option == translation["time_dec"])
                sort_key_func = lambda x: sort_key(x, time_index, av_index)
            elif sort_by_option in [translation["av_asc"], translation["av_dec"]] and av_index != -1:
                reverse_sort = (sort_by_option == translation["av_dec"])
                sort_key_func = lambda x: sort_key(x, av_index, time_index)

            with ThreadPoolExecutor() as executor:
                future1 = executor.submit(lambda: entries_with_section.sort(key=sort_key_func, reverse=reverse_sort))
                future2 = executor.submit(lambda: non_standard_positions.sort(key=sort_key_func, reverse=reverse_sort))

            future1.result()
            future2.result()

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
        all_semesters = set()
        for display_class, _, semester, _, _, _ in self.class_table_pairs:
            base_name = display_class.cget("text").split("-")[0].strip().split(" #")[0]
            key = (base_name, semester)
            if key not in class_info:
                class_info[key] = []
            class_info[key].append(display_class)
            all_semesters.add(semester)

        multiple_semesters_exist = len(all_semesters) > 1
        updated_labels = []
        for (base_name, semester), labels in class_info.items():
            add_suffix = len(labels) > 1
            for idx, display_class in enumerate(labels, 1):
                suffix = f" #{idx}" if add_suffix else ""
                new_text = f"{base_name}{suffix}"
                if multiple_semesters_exist:
                    new_text += f" - {semester}"
                current_text = display_class.cget("text")
                if current_text != new_text:
                    updated_labels.append((display_class, new_text))

        for display_class, new_text in updated_labels:
            display_class.configure(text=new_text)

    def display_current_table(self):
        translation = self.load_language()
        # Hide all tables and display_classes
        for display_class, curr_table, _, _, _, _ in self.class_table_pairs:
            display_class.grid_forget()
            curr_table.grid_forget()

        # Show the current display_class and table
        display_class, curr_table, semester, _, _, _ = self.class_table_pairs[self.current_table_index]
        table_position_label = (f" {translation['table_position']}{self.current_table_index + 1}"
                                f"/{len(self.class_table_pairs)}")
        if self.table_position.cget("text") != table_position_label:
            self.table_position.configure(text=table_position_label)
        display_class.grid(row=2, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
        curr_table.grid(row=2, column=1, padx=(0, 15), pady=(40, 0), sticky="n")
        self.table = curr_table
        self.current_class = display_class
        section = self.s_class_entry.get().upper().replace(" ", "").replace("-", "")
        display_class_text = display_class.cget("text").split(" ")[0]
        if section != display_class_text and self.loading_screen_status is None:
            if self.s_class_entry.get() != display_class_text:
                self.s_class_entry.delete(0, "end")
                self.s_class_entry.insert(0, display_class_text)
            if self.s_semester_entry.get() != semester:
                self.s_semester_entry.set(semester)
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
            translation = self.load_language()
            table_position_label = (f" {translation['table_position']}{self.current_table_index + 1}"
                                    f"/{len(self.class_table_pairs)}")
            self.table_position.configure(text=table_position_label)
            self.search_scrollbar.scroll_to_top()
            self.update_buttons()
            self.after(100, self.display_current_table)

    def show_next_table(self):
        if self.current_table_index < len(self.class_table_pairs) - 1:
            self.current_table_index += 1
            translation = self.load_language()
            table_position_label = (f" {translation['table_position']}{self.current_table_index + 1}"
                                    f"/{len(self.class_table_pairs)}")
            self.table_position.configure(text=table_position_label)
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

        translation = self.load_language()
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
        translation = self.load_language()
        self.move_tables_overlay.title(translation["move_classes"])
        self.move_title_label.configure(text=translation["move_classes"])
        num_tables = len(self.class_table_pairs)
        checkbox_width = 30
        checkbox_padding = 2
        checkboxes_per_row = 10
        total_rows = (num_tables + checkboxes_per_row - 1) // checkboxes_per_row
        total_checkbox_width = min(num_tables, checkboxes_per_row) * (checkbox_width + checkbox_padding)
        move_window_width = total_checkbox_width + 110
        move_window_height = total_rows * 32 + 50
        self.move_tables_overlay.grid_rowconfigure(0, weight=1)
        self.move_tables_overlay.grid_rowconfigure(1, weight=1)
        self.move_tables_overlay.grid_columnconfigure(0, weight=1)
        self.move_tables_overlay.grid_columnconfigure(1, weight=0)
        self.move_tables_overlay.grid_columnconfigure(2, weight=1)
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        center_x = main_window_x + (main_window_width // 2) - (move_window_width // 2)
        center_y = main_window_y + (main_window_height // 2) - (move_window_height // 2)
        center_x += 105
        center_y -= 13
        monitor = TeraTermUI.get_monitor_bounds(main_window_x, main_window_y)
        monitor_x, monitor_y, monitor_width, monitor_height = monitor.x, monitor.y, monitor.width, monitor.height
        center_x = max(monitor_x, min(center_x, monitor_x + monitor_width - move_window_width))
        center_y = max(monitor_y, min(center_y, monitor_y + monitor_height - move_window_height))
        window_geometry = f"{move_window_width}x{move_window_height}+{center_x}+{center_y}"
        self.move_tables_overlay.geometry(window_geometry)

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
        translation = self.load_language()
        self.class_table_pairs[source_index], self.class_table_pairs[target_index] = \
            self.class_table_pairs[target_index], self.class_table_pairs[source_index]

        for _, table_widget, _, _, _, _ in self.class_table_pairs:
            table_widget.grid(row=2, column=1, padx=(0, 0), pady=(40, 0), sticky="n")

        if self.current_table_index == source_index:
            self.current_table_index = target_index
        elif self.current_table_index == target_index:
            self.current_table_index = source_index

        self.display_current_table()
        table_position = f"{self.current_table_index + 1}/{len(self.class_table_pairs)}"
        self.table_position.configure(text=f"{translation['table_position']} {table_position}")
        self.update_buttons()

    def keybind_remove_current_table(self):
        current_time = time.time()
        if hasattr(self, "last_remove_time") and current_time - self.last_remove_time < 0.250 or \
                (self.loading_screen_status is not None and self.loading_screen_status.winfo_exists()):
            return

        self.remove_current_table()
        self.last_remove_time = current_time

    def remove_current_table(self):
        translation = self.load_language()
        display_class_to_remove, table_to_remove, _, _, _, more_sections \
            = self.class_table_pairs[self.current_table_index]

        display_class_to_remove.grid_remove()
        table_to_remove.grid_remove()
        for i in range(table_to_remove.rows):
            for j in range(table_to_remove.columns):
                cell = table_to_remove.get_cell(i, j)
                if cell in self.table_tooltips:
                    self.table_tooltips[cell].destroy()
                    self.table_tooltips[cell].widget = None
                    self.table_tooltips[cell].message = None
                    del self.table_tooltips[cell]
                table_to_remove.unbind_cell(i, j)
        self.hidden_tables.append(table_to_remove)
        self.hidden_labels.append(display_class_to_remove)

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

        if len(self.class_table_pairs) == 20:
            self.table_count.configure(text_color=("black", "white"))

        del self.class_table_pairs[self.current_table_index]

        self.current_table_index = max(0, self.current_table_index - 1)
        table_count_label = f"{translation['table_count']}{len(self.class_table_pairs)}/20"
        if len(self.class_table_pairs) > 0:
            table_position_label = (f" {translation['table_position']}{self.current_table_index + 1}"
                                    f"/{len(self.class_table_pairs)}")
        else:
            table_position_label = f" {translation['table_position']}0/{len(self.class_table_pairs)}"
        self.table_count.configure(text=table_count_label)
        self.table_position.configure(text=table_position_label)

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
            self.table_pipe.grid_forget()
            self.table_position.grid_forget()
            self.remove_button.grid_forget()
            self.download_search_pdf.grid_forget()
            self.sort_by.grid_forget()
            self.image_search.grid(row=2, column=1, padx=(0, 0), pady=(35, 0), sticky="n")
            self.notice_search.grid(row=2, column=1, padx=(0, 0), pady=(130, 0), sticky="n")
            self.search_scrollbar.scroll_to_top()
            self.unbind("<Control-s>")
            self.unbind("<Control-S>")
            self.unbind("<Control-w>")
            self.unbind("<Control-W>")
            self.after(0, self.focus_set)
            return

        self.table_count.grid_forget()
        self.table_pipe.grid_forget()
        self.table_position.grid_forget()
        self.remove_button.grid_forget()
        self.previous_button.grid_forget()
        self.next_button.grid_forget()
        self.download_search_pdf.grid_forget()
        self.sort_by.grid_forget()
        self.search_scrollbar.scroll_to_top()
        self.check_and_update_labels()
        self.update_buttons()

        def reshow_widgets():
            self.table_count.grid(row=4, column=1, padx=(0, 95), pady=(10, 0), sticky="n")
            self.table_pipe.grid(row=4, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
            self.table_position.grid(row=4, column=1, padx=(95, 0), pady=(10, 0), sticky="n")
            self.remove_button.grid(row=5, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
            if len(self.class_table_pairs) > 1:
                self.previous_button.grid(row=5, column=1, padx=(0, 300), pady=(10, 0), sticky="n")
                self.next_button.grid(row=5, column=1, padx=(300, 0), pady=(10, 0), sticky="n")
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
                logging.warning(f"An error occurred: {err}")
                if attempt < max_retries - 1:
                    pass
                else:
                    logging.error("Max retries reached, raising exception")
                    raise
            finally:
                timings.Timings.window_find_timeout = original_timeout
                timings.Timings.window_find_retry = original_retry
        self.uprb.UprbayTeraTermVt.type_keys("%c")
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            self.loading_screen.attributes("-topmost", False)
            self.loading_screen.lower()
            self.loading_screen.lift()
        pyautogui.FAILSAFE = False
        original_position = pyautogui.position()
        quarter_width = self.tera_term_window.width // 4
        center_x = self.tera_term_window.left + quarter_width
        center_y = self.tera_term_window.top + self.tera_term_window.height // 2
        pyautogui.click(center_x, center_y)
        pyautogui.moveTo(original_position)
        if self.loading_screen_status is not None and self.loading_screen_status.winfo_exists():
            self.after(0, self.loading_screen.attributes, "-topmost", True)

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
            TeraTermUI.manage_user_input()
            self.automate_copy_class_data()
            TeraTermUI.manage_user_input("on")
            copy = pyperclip.paste()
            latest_term = TeraTermUI.get_latest_term(copy)
            if latest_term == "Latest term not found":
                self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}SRM{ENTER}")
                self.reset_activity_timer()
                return "error"
            elif latest_term == "No active semester":
                translation = self.load_language()
                if "INVALID ACTION" in copy:
                    self.uprb.UprbayTeraTermVt.type_keys("SRM" + self.DEFAULT_SEMESTER + "{ENTER}")
                    self.reset_activity_timer()
                else:
                    self.uprb.UprbayTeraTermVt.type_keys("{TAB}SRM" + self.DEFAULT_SEMESTER + "{ENTER}")
                    self.reset_activity_timer()
                self.after(100, self.show_error_message, 320, 235, translation["no_active_semester"])
                return "negative"
            elif latest_term["percent"] or latest_term["asterisk"]:
                if latest_term["percent"]:
                    self.DEFAULT_SEMESTER = latest_term["percent"]
                elif latest_term["asterisk"]:
                    self.DEFAULT_SEMESTER = latest_term["asterisk"]
                row_exists = self.cursor_db.execute("SELECT 1 FROM user_config").fetchone()
                if not row_exists:
                    self.cursor_db.execute("INSERT INTO user_config (default_semester) VALUES (?)",
                                           (self.DEFAULT_SEMESTER,))
                else:
                    self.cursor_db.execute("UPDATE user_config SET default_semester=?",
                                           (self.DEFAULT_SEMESTER,))
                self.found_latest_semester = True
                self.update_all_semester_tooltips()
                return self.DEFAULT_SEMESTER
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

    def get_last_five_terms(self):
        translation = self.load_language()
        current_semester = TeraTermUI.calculate_default_semester()
        letter = current_semester[0]
        year_digit = int(current_semester[1])

        decade_index = ord(letter) - ord("A")
        current_year_number = decade_index * 10 + year_digit
        base_year = 2000
        terms = [[translation["terms_year"], translation["terms_term"]]]
        for offset in range(4, -1, -1):
            y = current_year_number - offset
            full_year = base_year + y
            letter = chr(ord("A") + (y // 10))
            digit = y % 10
            semesters = f"{letter}{digit}1, {letter}{digit}2, {letter}{digit}3"
            terms.append([str(full_year), semesters])

        terms.append([translation["semester"], translation["seasons"]])
        return terms

    def get_semester_season(self, semester_code):
        lang = self.language_menu.get()
        translation = self.load_language()
        if semester_code in ["CURRENT", "ACTUAL"]:
            current_tooltip = translation["current_tooltip"]
            if self.found_latest_semester:
                latest_semester_text = self.get_semester_season(self.DEFAULT_SEMESTER)
                current_tooltip += f"\n{self.DEFAULT_SEMESTER} - {latest_semester_text}"
            return current_tooltip

        if len(semester_code) != 3 or not semester_code[0].isalpha() or not semester_code[1:].isdigit():
            return ""

        letter = semester_code[0]
        year_digit = int(semester_code[1])
        semester_part = semester_code[2]
        base_year = 2000 + (ord(letter.upper()) - ord("A")) * 10
        full_year = base_year + year_digit
        if semester_part in ["2", "3"]:
            full_year += 1

        semester_map = {"English": {"1": "Fall", "2": "Spring", "3": "Summer"},
                        "Español": {"1": "Otoño", "2": "Primavera", "3": "Verano"}}
        semester_names = semester_map.get(lang, semester_map["English"])
        semester_name = semester_names.get(semester_part, "")
        if not semester_name:
            return ""

        return f"{semester_name} {full_year}"

    def update_semester_tooltip(self, widget):
        selected_semester = widget.get().upper().replace(" ", "")
        new_tooltip_text = self.get_semester_season(selected_semester)
        if widget in self.semesters_tooltips:
            self.semesters_tooltips[widget].configure(message=new_tooltip_text)
            if new_tooltip_text:
                self.semesters_tooltips[widget].show()
            else:
                self.semesters_tooltips[widget].hide()

    def update_all_semester_tooltips(self):
        entries = [self.e_semester_entry, self.s_semester_entry,
                   self.menu_semester_entry, self.m_semester_entry[0]]
        for widget in entries:
            self.update_semester_tooltip(widget)

    @staticmethod
    def specific_class_data(data):
        modified_data = []
        for item in data:
            days = item["DAYS"].split(", ")
            times = item["TIMES"].split(", ")
            first = True  # Flag to identify the first day and time

            # Split instructor name for the first entry
            if "INSTRUCTOR" in item:
                instructor_name = item["INSTRUCTOR"].strip()
                # Check if there is a comma indicating multiple names
                if "," in instructor_name:
                    # Split on comma and format properly
                    parts = [part.strip() for part in instructor_name.split(",") if part.strip()]
                    # Check if the last part is a single letter
                    if len(parts[-1]) == 1 and len(parts) > 1:
                        # If it's a standalone initial without a period, move to the next line
                        if not parts[-1].endswith("."):
                            item["INSTRUCTOR"] = "\n".join(parts)
                        else:
                            # If it has a period, keep it in the same line
                            parts[-2] = f"{parts[-2]}, {parts[-1]}"
                            parts.pop()
                            item["INSTRUCTOR"] = "\n".join(parts)
                    else:
                        # If there's no single-letter issue, format normally
                        item["INSTRUCTOR"] = "\n".join(parts)
                else:
                    # If there's no comma, just ensure the name is clean with no extra newlines
                    item["INSTRUCTOR"] = instructor_name

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
            rf"(\w+)\s+(\w)\s+({session_pattern})\s+(\d+\.\d+)\s+(?:\w{{1,2}})?\s+(\w+)\s+([\dAMP\-TBA]+)\s+"
            rf"([\d\s]+)?\s+.*?\s*([NFUL\s]*.*)"
        )
        # Regex pattern to match additional time slots
        time_pattern = re.compile(
            r"^(\s+)(\w{2})\s+([\dAMP\-]+)\s*$"
        )
        for line in lines:
            if any(x in line for x in session_types):
                match = pattern.search(line)
                if match:
                    instructor = match.group(8).strip()
                    instructor_cleaned = re.sub(r"\b(N|FULL|RSVD|RSTR|CANC)\b", "", instructor).strip()
                    av_value = next(
                        (val for val in ["RSVD", "RSTR", "CANC", "999", "998"] if val in instructor),
                        match.group(7).strip() if match.group(7) else "0")
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
        translation = self.load_language()

        class_pattern = re.compile(
            r"(\b[A-Z])\s+([A-Z]{4}\d{4}[A-Z0-9]{3})\s+([A-Z])?\s+(.*?)\s+([A-Z]{2})\s*([A-FI-NPW]*)\s+"
            r"([A-Z]{1,5}|TBA)\s+(\d{4}[AP]M-\d{4}[AP]M|TBA)\s*(?:\s+([\dA-Z]*?)\s+([A-Z\d]{3,4})?)?"
            r"(?:\s+([A-Z]{1,5}|TBA)\s+(\d{4}[AP]M-\d{4}[AP]M|TBA)\s*(?:\s+([\dA-Z]*?)\s+([A-Z\d]{3,4})?)?)"
            r"?(?=\s+\b[A-Z]|\s*$)", re.DOTALL)

        matches = class_pattern.findall(text)
        enrolled_classes = []
        for match in matches:
            course_code = f"{match[1][:4]}-{match[1][4:8]}-{match[1][8:]}"
            modality = match[2] if match[2] else ""
            formatted_time = TeraTermUI.parse_time(match[7])
            class_info = {
                translation["course"]: course_code,
                translation["m"]: modality,
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
                    translation["m"]: modality,
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

        translation = self.load_language()
        lang = self.language_menu.get()
        # Prepare the PDF document
        pdf = SimpleDocTemplate(filepath, pagesize=letter)
        # Add metadata to the PDF
        if lang == "English":
            pdf.title = f"Enrolled Classes - {semester}"
            pdf.subject = f"Enrolled classes information for {semester}"
        elif lang == "Español":
            pdf.title = f"Clases Matriculadas - {semester}"
            pdf.subject = f"Información de clases matriculadas para el semestre {semester}"
        pdf.author = "Tera Term UI"
        pdf.creator = "Tera Term UI PDF Generator"
        pdf.producer = "ReportLab PDF Library"
        pdf.keywords = ["enrolled classes", "academic", "schedule", semester, str(creds) + " credits"]
        pdf.creation_date = datetime.now()
        elems = []

        # Extract and prepare table data with translated headers
        headers = [translation["course"], translation["m"], translation["grade"], translation["days"],
                   translation["times"], translation["room"]]
        table_data = [headers] + [[cls.get(header, "") for header in headers] for cls in data]

        column_widths = [120, 50, 60, 55, 120, 55]
        # Create the table
        table = Table(table_data, colWidths=column_widths)

        # Define and set the same table style as in your create_pdf method
        blue = colors.Color(0, 0.5, 0.75)
        gray = colors.Color(0.7, 0.7, 0.7)
        table_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), blue),  # Header background color
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),  # Text color
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),  # Center text horizontally
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),  # Center text vertically
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # Bold font for headers
            ("FONTSIZE", (0, 0), (-1, 0), 14),  # Header font size
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),  # Padding for headers
            ("BACKGROUND", (0, 1), (-1, -1), gray),  # Background color for data rows
            ("GRID", (0, 0), (-1, -1), 1, colors.black),  # Add grid lines
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

        translation = self.load_language()
        semester = self.dialog_input.upper().replace(" ", "")
        self.focus_set()

        # Define default save directory
        if self.last_save_pdf_dir is not None:
            initial_dir = self.last_save_pdf_dir
        else:
            home = os.path.expanduser("~")
            initial_dir = os.path.join(home, "Downloads")

        base_filename = f"{semester}_{translation['enrolled_classes']}.pdf"
        unique_filename = TeraTermUI.get_unique_filename(initial_dir, base_filename)
        filepath = filedialog.asksaveasfilename(
            title=translation["save_pdf"], defaultextension=".pdf", initialdir=initial_dir,
            filetypes=[("PDF Files", "*.pdf")], initialfile=unique_filename)

        # Check if user cancelled the file dialog
        if not filepath:
            self.focus_set()
            return

        self.last_save_pdf_dir = os.path.dirname(filepath)
        self.create_enrolled_classes_pdf(data, creds, semester, filepath)
        self.show_success_message(350, 265, translation["pdf_save_success"])

    def display_enrolled_data(self, data, creds, dialog_input):
        lang = self.language_menu.get()
        translation = self.load_language()
        semester = dialog_input.upper().replace(" ", "")
        if not data:
            self.after(100, self.show_error_message, 320, 235, translation["semester_no_data"] + semester)
            self.after(150, self.switch_tab)
            return
        self.unbind("<Control-Tab>")
        self.unbind("<Control-w>")
        self.unbind("<Control-W>")
        headers = [translation["course"], translation["m"], translation["grade"], translation["days"],
                   translation["times"], translation["room"]]
        self.dialog_input = dialog_input
        self.ask_semester_refresh = True
        table_values = [headers] + [[cls.get(header, "") for header in headers] for cls in data]
        enrolled_rows = len(data) + 1
        column_widths = {
            translation["course"]: 112,
            translation["m"]: 50,
            translation["grade"]: 50,
            translation["days"]: 50,
            translation["times"]: 112,
            translation["room"]: 50
        }
        tooltip_messages = {
            translation["course"]: translation["tooltip_course"],
            translation["m"]: translation["tooltip_m"],
            translation["grade"]: translation["tooltip_grd"],
            translation["days"]: translation["tooltip_days"],
            translation["times"]: translation["tooltip_times"],
            translation["room"]: translation["tooltip_croom"]
        }
        self.enrolled_classes_credits = creds
        if self.enrolled_classes_data is not None:
            self.enrolled_classes_data = data
            if self.enrolled_classes_table.values == table_values:
                self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
                self.my_classes_frame.scroll_to_top()
                return
            self.my_classes_frame.grid_forget()
            self.modify_classes_frame.grid_forget()
            self.enrolled_classes_table.refresh_table(table_values)
            for tooltip in self.enrolled_header_tooltips.values():
                tooltip.destroy()
                tooltip.widget = None
                tooltip.message = None
            self.enrolled_header_tooltips.clear()
            self.total_credits_label.configure(text=translation["total_creds"] + creds)
            self.title_my_classes.configure(text=translation["my_classes"] + semester)
            self.submit_my_classes.configure(command=self.submit_modify_classes_handler)
            self.modify_classes_title.configure(text=translation["mod_classes_title"])
            for i, header in enumerate(headers):
                self.enrolled_classes_table.edit_column(i, width=column_widths[header])
                cell = self.enrolled_classes_table.get_cell(0, i)
                tooltip_message = tooltip_messages[header]
                tooltip = CTkToolTip(cell, message=tooltip_message, bg_color="#989898", alpha=0.90)
                self.enrolled_header_tooltips[cell] = tooltip
            while len(self.mod_selection_list) < len(data):
                self.mod_selection_list.append(None)
                self.change_section_entries.append(None)
            previous_row_had_widgets = True
            for row_index, row_data in enumerate(data):
                if row_index == 0:
                    pad_y = 28
                else:
                    pad_y = 6 if previous_row_had_widgets else 40
                if row_data[translation["course"]] != "":
                    if self.mod_selection_list[row_index] is None:
                        combined_placeholders = self.placeholder_texts_sections + (
                            "KJ1", "LJ1", "KI1", "LI1", "VM1", "JM1")
                        placeholder_text = combined_placeholders[row_index % len(combined_placeholders)]
                        mod_selection = customtkinter.CTkOptionMenu(
                            self.modify_classes_frame, values=[translation["choose"], translation["drop"],
                                                               translation["section"]], width=80,
                            command=lambda value, index=row_index: self.modify_enrolled_classes(value, index))
                        change_section_entry = CustomEntry(self.modify_classes_frame, self, lang,
                                                           placeholder_text=placeholder_text, width=50)
                        change_section_entry.bind("<FocusOut>", self.check_class_conflicts)
                        self.mod_selection_list[row_index] = mod_selection
                        self.change_section_entries[row_index] = change_section_entry
                        mod_selection_tooltip = CTkToolTip(mod_selection, bg_color="#1E90FF",
                                                           message=translation["mod_selection"])
                        change_section_entry_tooltip = CTkToolTip(change_section_entry, bg_color="#1E90FF",
                                                                  message=translation["change_section_entry"])
                        self.enrolled_tooltips.append(mod_selection_tooltip)
                        self.enrolled_tooltips.append(change_section_entry_tooltip)
                    else:
                        mod_selection = self.mod_selection_list[row_index]
                        change_section_entry = self.change_section_entries[row_index]
                        mod_selection.configure(state="normal")
                        mod_selection.set(translation["choose"])
                        change_section_entry.configure(state="normal")
                        if change_section_entry.get():
                            change_section_entry.delete(0, "end")
                        change_section_entry.configure(state="disabled")
                        self.check_class_conflicts()
                    mod_selection.grid(row=row_index, column=0, padx=(0, 100), pady=(pad_y, 0))
                    change_section_entry.grid(row=row_index, column=0, padx=(56, 0), pady=(pad_y, 0))
                    change_section_entry.configure(state="disabled")
                    previous_row_had_widgets = True
                else:
                    if self.mod_selection_list[row_index] is not None:
                        self.mod_selection_list[row_index].grid_forget()
                    if self.change_section_entries[row_index] is not None:
                        self.change_section_entries[row_index].grid_forget()
                    previous_row_had_widgets = False
            for extra_index in range(len(data), len(self.mod_selection_list)):
                if self.mod_selection_list[extra_index] is not None:
                    self.mod_selection_list[extra_index].grid_forget()
                if self.change_section_entries[extra_index] is not None:
                    self.change_section_entries[extra_index].grid_forget()
        else:
            self.change_section_entries = []
            self.mod_selection_list = []
            self.enrolled_classes_data = data
            self.my_classes_frame = customtkinter.CTkScrollableFrame(self, corner_radius=10, width=620, height=320)
            self.title_my_classes = customtkinter.CTkLabel(self.my_classes_frame,
                                                           text=translation["my_classes"] + semester,
                                                           font=customtkinter.CTkFont(size=20, weight="bold"))
            self.total_credits_label = customtkinter.CTkLabel(self.my_classes_frame,
                                                              text=translation["total_creds"] + creds)
            self.submit_my_classes = CustomButton(master=self.my_classes_frame, border_width=2,
                                                  text=translation["submit"], text_color=("gray10", "#DCE4EE"),
                                                  command=self.submit_modify_classes_handler)
            self.submit_my_classes_tooltip = CTkToolTip(self.submit_my_classes, bg_color="#1E90FF",
                                                        message=translation["submit_modify_tooltip"])
            self.download_enrolled_pdf = CustomButton(master=self.my_classes_frame, text=translation["pdf_save_as"],
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
            self.enrolled_classes_table = CTkTable(self.my_classes_frame, column=len(headers), row=enrolled_rows,
                                                   values=table_values, header_color="#145DA0", hover_color="#339CFF",
                                                   command=lambda row, col: self.copy_cell_data_to_clipboard(
                                                       self.enrolled_classes_table.get_cell(row, col)))
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
            self.enrolled_classes_table.grid(row=2, column=1, pady=(0, 5), padx=(5, 0))
            self.total_credits_label.grid(row=3, column=1, padx=(180, 0), pady=(0, 15))
            self.submit_my_classes.grid(row=4, column=1, padx=(180, 0))
            self.download_enrolled_pdf.grid(row=5, column=1, padx=(180, 0), pady=(10, 0))
            self.modify_classes_frame.grid(row=2, column=2, sticky="nw", padx=(12, 0))
            self.modify_classes_title.grid(row=0, column=0, padx=(0, 40), pady=(0, 25))
            self.back_my_classes.grid(row=4, column=0, padx=(0, 10), pady=(0, 0), sticky="w")

            pad_y = 6
            for row_index in range(len(self.enrolled_classes_data)):
                if row_index == 0:
                    pad_y = 28
                if self.enrolled_classes_data[row_index][translation["course"]] != "":
                    combined_placeholders = self.placeholder_texts_sections + ("KJ1", "LJ1", "KI1", "LI1", "VM1", "JM1")
                    placeholder_text = combined_placeholders[row_index % len(combined_placeholders)]
                    mod_selection = customtkinter.CTkOptionMenu(self.modify_classes_frame,
                                                                values=[translation["choose"], translation["drop"],
                                                                        translation["section"]], width=85,
                                                                command=lambda value, index=row_index:
                                                                self.modify_enrolled_classes(value, index))
                    change_section_entry = CustomEntry(self.modify_classes_frame, self, lang,
                                                       placeholder_text=placeholder_text, width=50)
                    change_section_entry.bind("<FocusOut>", self.check_class_conflicts)
                    mod_selection.grid(row=row_index, column=0, padx=(0, 100), pady=(pad_y, 0))
                    change_section_entry.grid(row=row_index, column=0, padx=(56, 0), pady=(pad_y, 0))
                    mod_selection_tooltip = CTkToolTip(mod_selection, bg_color="#1E90FF",
                                                       message=translation["mod_selection"])
                    change_section_entry_tooltip = CTkToolTip(change_section_entry, bg_color="#1E90FF",
                                                              message=translation["change_section_entry"])
                    change_section_entry.configure(state="disabled")
                    self.mod_selection_list.append(mod_selection)
                    self.change_section_entries.append(change_section_entry)
                    self.enrolled_tooltips.append(mod_selection_tooltip)
                    self.enrolled_tooltips.append(change_section_entry_tooltip)
                    pad_y = 6
                else:
                    self.mod_selection_list.append(None)
                    self.change_section_entries.append(None)
                    pad_y = 40
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
        self.my_classes_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 100))
        self.modify_classes_frame.grid(row=2, column=2, sticky="nw", padx=(12, 0))
        self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
        self.enrolled_entry_cache.clear()
        self.my_classes_frame.scroll_to_top()

    def modify_enrolled_classes(self, mod, row_index):
        translation = self.load_language()
        entry = self.change_section_entries[row_index]
        if entry is not None:
            if mod == translation["section"]:
                if row_index in self.enrolled_entry_cache and self.enrolled_entry_cache[row_index].strip():
                    entry.configure(state="normal")
                    entry.delete(0, "end")
                    entry.insert(0, self.enrolled_entry_cache[row_index])
                    self.check_class_conflicts()
                else:
                    entry.configure(state="normal")
            elif mod == translation["drop"] or mod == translation["choose"]:
                if entry.get().strip():
                    self.enrolled_entry_cache[row_index] = entry.get()
                entry.delete(0, "end")
                entry._activate_placeholder()
                entry.configure(state="disabled")
                self.check_class_conflicts()

    def submit_modify_classes_handler(self):
        if self.countdown_running:
            return

        translation = self.load_language()
        self.focus_set()
        msg = CTkMessagebox(title=translation["submit"], message=translation["submit_modify"],
                            icon=TeraTermUI.get_absolute_path("images/submit.png"), option_1=translation["option_1"],
                            option_2=translation["option_2"], option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        self.destroy_tooltip()
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            loading_screen = self.show_loading_screen()
            future = self.thread_pool.submit(self.submit_modify_classes)
            self.update_loading_screen(loading_screen, future)

    def submit_modify_classes(self):
        with self.lock_thread:
            try:
                self.automation_preparations()
                translation = self.load_language()
                dialog_input = self.dialog_input.upper().replace(" ", "")
                show_error = False
                first_loop = True
                section_closed = False
                co_requisite = False
                if asyncio.run(self.test_connection()) and self.check_server():
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
                                if mod == translation["section"] and not re.fullmatch("^[A-Z0-9]{3}$", section):
                                    section_pattern = False
                                    self.after(0, change_section_entry.configure(border_color="#c30101"))
                                if mod != translation["choose"] and course_code_no_section in edge_cases_classes:
                                    edge_cases_bool = True
                                    edge_cases_classes_met.append(course_code_no_section)
                                    self.after(0, mod_selection.configure(button_color="#c30101"))
                        if not_all_choose and section_pattern and not edge_cases_bool:
                            if not self.wait_for_window():
                                return
                            self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}1S4" + dialog_input + "{ENTER}")
                            self.after(0, self.disable_go_next_buttons)
                            text_output = self.capture_screenshot()
                            count_enroll = text_output.count("ENROLLED") + text_output.count("RECOMMENDED")
                            if "OUTDATED" not in text_output and "INVALID TERM SELECTION" not in text_output and \
                                    "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" \
                                    not in text_output and "ENTER REGISTRATION" in text_output:
                                for row_index, enrolled_class in enumerate(self.enrolled_classes_data):
                                    mod_selection = self.mod_selection_list[row_index]
                                    change_section_entry = self.change_section_entries[row_index]
                                    is_final = row_index == len(self.enrolled_classes_data) - 1
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
                                            text_output = self.wait_for_response(["ENROLLED"])
                                            count_enroll = (text_output.count("ENROLLED") +
                                                            text_output.count("RECOMMENDED"))
                                        first_loop = False
                                        self.uprb.UprbayTeraTermVt.type_keys("{TAB 3}")
                                        for i in range(count_enroll, 0, -1):
                                            self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}")
                                        self.uprb.UprbayTeraTermVt.type_keys("D" + course_code + "{ENTER}")
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
                                        if not is_final or mod == translation["section"]:
                                            self.uprb.UprbayTeraTermVt.type_keys("{ENTER 2}")
                                            self.reset_activity_timer()
                                        if mod == translation["section"]:
                                            text_output = self.capture_screenshot()
                                            count_enroll = (text_output.count("ENROLLED") +
                                                            text_output.count("RECOMMENDED"))
                                            self.uprb.UprbayTeraTermVt.type_keys("{TAB 3}")
                                            for i in range(count_enroll, 0, -1):
                                                self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}")
                                            self.uprb.UprbayTeraTermVt.type_keys(
                                                "R" + course_code_no_section + section + "{ENTER}")
                                            self.reset_activity_timer()
                                            text_output = self.capture_screenshot()
                                            error_classes = text_output
                                            if not is_final:
                                                self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                                self.reset_activity_timer()
                                            if "INVALID COURSE ID" in text_output or "COURSE CLOSED" in text_output or \
                                                    "R/TC" in text_output or "Closed by Spec-Prog" in text_output or \
                                                    "COURSE RESERVED" in text_output:
                                                show_error = True
                                                text_output = self.capture_screenshot()
                                                count_enroll = (text_output.count("ENROLLED") +
                                                                text_output.count("RECOMMENDED"))
                                                self.uprb.UprbayTeraTermVt.type_keys("{TAB 3}")
                                                for i in range(count_enroll, 0, -1):
                                                    self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}")
                                                self.uprb.UprbayTeraTermVt.type_keys("R" + course_code + "{ENTER}")
                                                self.reset_activity_timer()
                                                text_output = self.capture_screenshot()
                                                closed_error = text_output
                                                if not is_final:
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
                                text_output = self.wait_for_response(["CONFIRMED", "DROPPED"],
                                                                     init_timeout=False)
                                if "CONFIRMED" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                if "DROPPED" in text_output:
                                    self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                                try:
                                    self.uprb.UprbayTeraTermVt.type_keys("SRM{ENTER}1CP" + dialog_input + "{ENTER}")
                                    self.reset_activity_timer()
                                    try:
                                        with self.clipboard_handler.saving():
                                            self.clipboard_handler.save_clipboard_content()
                                    except Exception as err:
                                        logging.error(f"An error occurred while saving clipboard content: {err}")
                                    time.sleep(1)
                                    TeraTermUI.manage_user_input()
                                    self.automate_copy_class_data()
                                    TeraTermUI.manage_user_input("on")
                                    copy = pyperclip.paste()
                                    enrolled_classes, total_credits = self.extract_my_enrolled_classes(copy)
                                    if not enrolled_classes and (not total_credits or total_credits == "0.00"):
                                        self.ask_semester_refresh = False
                                        self.enrolled_classes_data = None
                                        self.dialog_input = None
                                        self.after(0, self.go_back_menu)
                                    else:
                                        self.after(0, self.display_enrolled_data, enrolled_classes,
                                                   total_credits, dialog_input)
                                    self.clipboard_clear()
                                    try:
                                        with self.clipboard_handler.restoring():
                                            self.clipboard_handler.restore_clipboard_content()
                                    except Exception as err:
                                        logging.error(f"An error occurred while restoring clipboard content: {err}")
                                    time.sleep(1)
                                except Exception as err:
                                    logging.error("An error occurred: %s", err)
                                    self.after(0, self.go_back_menu)
                                if show_error and not section_closed:
                                    self.after(100, self.show_error_message, 320, 240,
                                               translation["failed_change_section"])
                                    def explanation():
                                        self.destroy_windows()
                                        if self.enrolled_classes_data is not None:
                                            self.after(350, self.bind, "<Return>",
                                                       lambda event: self.submit_modify_classes_handler())
                                            self.submit_my_classes.configure(state="normal")
                                        self.not_rebind = False
                                        self.play_sound("notification.wav")
                                        CTkMessagebox(title=translation["automation_error_title"], icon="info",
                                                      message=msg, button_width=380)

                                    failed_classes = self.parse_enrollment_errors(error_classes, course_code_no_section)
                                    class_list = [error.split(":")[0].rsplit("-", 1)[0] for error in failed_classes]
                                    class_list = list(dict.fromkeys(class_list))
                                    class_str = ", ".join(f"{i + 1}. {cls}" for i, cls in enumerate(class_list))
                                    if len(class_list) == 1:
                                        msg = f"{translation['failed_change_section_exp_s']}\n{class_str}"
                                    else:
                                        msg = f"{translation['failed_change_section_exp_p']}\n{class_str}"
                                    self.unbind("<Return>")
                                    self.submit_my_classes.configure(state="disabled")
                                    self.not_rebind = True
                                    self.after(3000, explanation)
                                elif section_closed:
                                    self.after(100, self.show_error_message, 320, 240,
                                               translation["failed_change_section"])
                                    def explanation():
                                        self.destroy_windows()
                                        if self.enrolled_classes_data is not None:
                                            self.after(350, self.bind, "<Return>",
                                                       lambda event: self.submit_modify_classes_handler())
                                            self.submit_my_classes.configure(state="normal")
                                        self.not_rebind = False
                                        self.play_sound("error.wav")
                                        CTkMessagebox(title=translation["automation_error_title"], icon="cancel",
                                                      message=msg, button_width=380)

                                    failed_classes = self.parse_enrollment_errors(closed_error, course_code_no_section)
                                    class_list = [error.split(":")[0].rsplit("-", 1)[0] for error in failed_classes]
                                    class_list = list(dict.fromkeys(class_list))
                                    class_str = ", ".join(f"{i + 1}. {cls}" for i, cls in enumerate(class_list))
                                    if len(class_list) == 1:
                                        msg = f"{translation['"section_closed_s"']}\n\n{class_str}"
                                    else:
                                        msg = f"{translation['"section_closed_p"']}\n\n{class_str}"
                                    self.unbind("<Return>")
                                    self.submit_my_classes.configure(state="disabled")
                                    self.not_rebind = True
                                    self.after(3000, explanation)

                                elif co_requisite:
                                    self.after(100, self.show_error_message, 320, 240,
                                               translation["failed_change_section"])
                                    def explanation():
                                        self.destroy_windows()
                                        if self.enrolled_classes_data is not None:
                                            self.after(350, self.bind, "<Return>",
                                                       lambda event: self.submit_modify_classes_handler())
                                            self.submit_my_classes.configure(state="normal")
                                        self.not_rebind = False
                                        self.play_sound("error.wav")
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
                                    self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
                                    self.reset_activity_timer()
                                    self.after(100, self.show_error_message, 300, 215,
                                               translation["invalid_semester"])
                                else:
                                    if "USO INTERNO" not in text_output and "TERMINO LA MATRICULA" \
                                            not in text_output:
                                        self.uprb.UprbayTeraTermVt.type_keys(self.DEFAULT_SEMESTER + "SRM{ENTER}")
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
                                    self.play_sound("error.wav")
                                    edge_case_classes_str = ", ".join(edge_cases_classes_met)
                                    CTkMessagebox(title=translation["automation_error_title"], icon="warning",
                                                  message=translation["co_requisite_warning"] + edge_case_classes_str,
                                                  button_width=380)

                                self.after(125, explanation)
                    else:
                        self.after(100, self.show_error_message, 300, 215,
                                   translation["tera_term_not_running"])
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                translation = self.load_language()
                self.after(100, self.set_focus_to_tkinter)
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        self.play_sound("notification.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_automation)
                if not self.not_rebind:
                    self.after(350, self.bind, "<Return>", lambda event: self.submit_modify_classes_handler())
                TeraTermUI.manage_user_input()

    # checks whether the program can continue its normal execution or if the server is on maintenance
    def wait_for_prompt(self, prompt_text, maintenance_text, timeout=15):
        time.sleep(1)
        start_time = time.time()
        while True:
            text_output = self.capture_screenshot()
            if maintenance_text in text_output:
                return "Maintenance message found"
            elif prompt_text in text_output:
                return "Prompt found"
            elif time.time() - start_time > timeout:
                return "Timeout"
            time.sleep(0.5)

    def wait_for_response(self, keywords, init_timeout=True, timeout=2.5):
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
            self.focus_tera_term()
            self.uprbay_window.wait("visible", timeout=3)
            if self.run_fix or self.in_student_frame:
                self.uprb.UprbayTeraTermVt.type_keys("^q")
            if self.went_to_1PL_screen and self.run_fix:
                self.uprb.UprbayTeraTermVt.type_keys("X{ENTER}")
                self.went_to_1PL_screen = False
            elif self.went_to_683_screen and self.run_fix:
                self.uprb.UprbayTeraTermVt.type_keys("00{ENTER}")
                self.went_to_683_screen = False
            return True
        except Exception as err:
            logging.error("An error occurred: %s", err)
            translation = self.load_language()
            self.search_function_counter = 0
            self.e_counter = 0
            self.m_counter = 0
            self.classes_status.clear()
            count, is_multiple = TeraTermUI.countRunningProcesses("ttermpro")
            if is_multiple:
                self.after(100, self.show_error_message, 450, 270,
                           translation["count_processes"])
                return False
            self.connect_to_uprb()
            if (not TeraTermUI.window_exists("SSH Authentication") and
                    not TeraTermUI.window_exists("Tera Term - [disconnected] VT")):
                text_output = self.capture_screenshot()
                to_continue = "return to continue"
                count_to_continue = text_output.count(to_continue)
                if "return to continue" in text_output or "INFORMACION ESTUDIANTIL" in text_output:
                    self.uprb.UprbayTeraTermVt.type_keys("^q")
                    if "return to continue" in text_output and "Loading" in text_output:
                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER 3}")
                    elif count_to_continue == 2 or "ZZZ" in text_output:
                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER 2}")
                    elif count_to_continue == 1 or "automaticamente" in text_output:
                        self.uprb.UprbayTeraTermVt.type_keys("{ENTER}")
                    else:
                        self.uprb.UprbayTeraTermVt.type_keys("{VK_RIGHT}{VK_LEFT}")
            self.move_window()
            return True

    # checks whether the user has the requested file
    @staticmethod
    def is_file_in_directory(file_name, directory):
        try:
            # Normalize the path using Path from pathlib
            full_path = Path(directory).resolve() / file_name
            # Check if the file exists
            return full_path.is_file()
        except Exception as err:
            logging.error(f"Error accessing the directory or file: {err}")
            return False

    # Necessary things to do while the application is booting, gets done on a separate thread
    def boot_up(self, file_path):
        self.future_tesseract = self.thread_pool.submit(self.setup_tesseract)
        self.future_backup = self.thread_pool.submit(self.backup_and_config_ini, file_path, self.geometry())
        self.future_feedback = self.thread_pool.submit(self.setup_feedback)

    def setup_tesseract(self):
        unzip_tesseract = True
        tesseract_dir_path = self.app_temp_dir / "Tesseract-OCR"
        default_tesseract_path = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
        alternate_tesseract_path = Path("C:/Users/arman/AppData/Local/Programs/Tesseract-OCR/tesseract.exe")

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

        # Check if Tesseract is installed in the default or alternate location
        tesseract_path = None
        for path in [default_tesseract_path, alternate_tesseract_path]:
            if path.is_file():
                installed_version = get_tesseract_version(str(path))
                if installed_version and tuple(map(int, installed_version.split("."))) >= (5, 0, 0):
                    pytesseract.pytesseract.tesseract_cmd = str(path)
                    tesseract_path = path
                    unzip_tesseract = False
                    break
        if tesseract_path:
            self.tesseract_unzipped = True
            self.delete_tesseract_dir = True
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
                gc.collect()
            except Exception as err:
                SPANISH = 0x0A
                language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                logging.error(f"Error occurred during unzipping: {str(err)}")
                self.tesseract_unzipped = False
                self.log_error()
                if "[Errno 2] No such file or directory" in str(err):
                    if language_id & 0xFF == SPANISH:
                        messagebox.showerror("Error", f"¡Error Fatal!\n\n{str(err)}")
                    else:
                        messagebox.showerror("Error", f"Fatal Error!\n\n{str(err)}")
                    self.after(0, self.end_app(forced=True))

    @staticmethod
    def get_teraterm_version(executable_path):
        import win32api

        try:
            info = win32api.GetFileVersionInfo(executable_path, "\\")
            ms = info["FileVersionMS"]
            ls = info["FileVersionLS"]
            version = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
            return version
        except Exception as err:
            return f"Unable to retrieve version: {err}"

    @staticmethod
    def find_appdata_teraterm_ini():
        import fnmatch

        appdata_path = os.environ.get("APPDATA", "")
        if os.path.isdir(appdata_path):
            for folder in os.listdir(appdata_path):
                if fnmatch.fnmatch(folder.lower(), "teraterm*"):
                    teraterm_ini_path = os.path.join(appdata_path, folder, "TERATERM.ini")
                    if os.path.isfile(teraterm_ini_path):
                        return teraterm_ini_path
        return None

    def has_write_permission(self):
        try:
            test_file = os.path.join(os.path.dirname(self.teraterm_directory), "temp_test_file.txt")
            with open(test_file, "w") as temp_file:
                temp_file.write("test")
            os.remove(test_file)
            return True
        except PermissionError:
            return False

    @staticmethod
    def detect_encoding(file_path, sample_size=4096):
        import chardet

        with open(file_path, "rb") as f:
            raw_data = f.read(sample_size)
        result = chardet.detect(raw_data)
        return result["encoding"]

    def backup_and_config_ini(self, file_path, geometry):
        # backup for config file of tera term
        if TeraTermUI.is_file_in_directory("ttermpro.exe", self.teraterm_directory):
            minimum_required_version = "5.0.0.0"
            version = TeraTermUI.get_teraterm_version(self.teraterm_exe_location)
            version_parts = list(map(int, version.split(".")))
            compare_version_parts = list(map(int, minimum_required_version.split(".")))
            if version and version_parts >= compare_version_parts:
                appdata_ini_path = TeraTermUI.find_appdata_teraterm_ini()
                if appdata_ini_path and not os.path.isfile(os.path.join(self.teraterm_directory, "portable.ini")):
                    file_path = appdata_ini_path
                elif (os.path.isfile(os.path.join(self.teraterm_directory, "TERATERM.ini"))
                      and self.has_write_permission()):
                    file_path = os.path.join(self.teraterm_directory, "TERATERM.ini")
                else:
                    self.teraterm5_first_boot = True
                    return

            backup_path = self.app_temp_dir / "TERATERM.ini.bak"
            if not os.path.exists(backup_path):
                backup_path = os.path.join(self.app_temp_dir, os.path.basename(file_path) + ".bak")
                try:
                    shutil.copy2(file_path, backup_path)
                except FileNotFoundError:
                    self.log_error()
                    logging.error("Tera Term Probably not installed\nor installed"
                                  " in a different location from the default")

            known_hosts_path = os.path.join(os.path.dirname(file_path), "ssh_known_hosts")
            if os.path.exists(known_hosts_path):
                try:
                    detected_encoding = TeraTermUI.detect_encoding(known_hosts_path) or "utf-8"
                    with open(known_hosts_path, "r", encoding=detected_encoding) as file:
                        for line in file:
                            parts = line.strip().split()
                            if not parts or parts[0].startswith("#"):
                                continue
                            self.host_entry_saved = parts[0]
                            break
                except Exception as err:
                    self.log_error()
                    logging.error(f"Error reading ssh_known_hosts file: {err}")

            # Edits the font that tera term uses to "Lucida Console" to mitigate the chance of the OCR mistaking words
            if not self.can_edit:
                try:
                    detected_encoding = TeraTermUI.detect_encoding(file_path) or "utf-8"
                    with open(file_path, "r", encoding=detected_encoding) as file:
                        lines = file.readlines()
                    for index, line in enumerate(lines):
                        if line.startswith("VTFont="):
                            lines[index] = "VTFont=Lucida Console,0,-12,255\n"
                        if line.startswith("VTColor=") and not line.startswith(";"):
                            current_value = line.strip().split("=")[1]
                            if current_value != "255,255,255,0,0,0":
                                lines[index] = "VTColor=255,255,255,0,0,0\n"
                        _, x_pos, y_pos = geometry.split("+")
                        if line.startswith("VTPos="):
                            lines[index] = f"VTPos={int(x_pos)},{int(y_pos)}\n"
                        if line.startswith("TEKPos="):
                            lines[index] = f"TEKPos={int(x_pos)},{int(y_pos)}\n"
                        if line.startswith("TermIsWin="):
                            current_value = line.strip().split("=")[1]
                            if current_value != "on":
                                lines[index] = "TermIsWin=on\n"
                        if line.startswith("AuthBanner="):
                            current_value = line.strip().split("=")[1]
                            if current_value not in ["0", "1"]:
                                lines[index] = "AuthBanner=1\n"
                        if line.startswith("Beep="):
                            current_beep_value = line.strip().split("=", 1)[1]
                            if current_beep_value == "off":
                                self.beep_off_default = True
                            else:
                                self.beep_off_default = False
                        self.can_edit = True
                    with open(file_path, "w", encoding=detected_encoding) as file:
                        file.writelines(lines)
                except FileNotFoundError:
                    return
                except IOError as err:
                    logging.error(f"Error occurred: {err}")
                    logging.info("Restoring from backup...")
                    shutil.copy2(backup_path, file_path)
        else:
            self.teraterm_not_found = True

    def ottenere_protetta_salasana(self):
        parts = ["$QojxnTKT8ecke49mf%bd", "U64m#8XaR$QNog$QdPL1Fp", "3%fHhv^ds7@CDDSag8PYt", "dM&R8fqu*&bUjmSZfgM^%"]
        scrambled_password = self.purkaa_reazione(parts)
        runtime_key = os.getenv("DURATA_FUSCAZIONE_AVAIN", "oletuksena_segreto").encode()
        encoded_password = base64.b64encode(scrambled_password.encode())
        return base64.b64encode(runtime_key + encoded_password).decode()

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
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
        from pyzipper import AESZipFile

        # Reads from the feedback.json file to connect to Google's Sheets Api for user feedback
        try:
            encoded_password = base64.b64decode(self.REAZIONE.encode())
            runtime_key = os.getenv("DURATA_FUSCAZIONE_AVAIN", "oletuksena_segreto").encode()
            actual_password = base64.b64decode(encoded_password[len(runtime_key):]).decode()
            with AESZipFile(self.SERVICE_ACCOUNT_FILE) as archive:
                archive.setpassword(actual_password.encode())
                file_contents = archive.read("feedback.json")
                credentials_dict = json.loads(file_contents.decode())
            self.credentials = service_account.Credentials.from_service_account_info(
                credentials_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
            if self.credentials.expired or not self.credentials.valid:
                self.credentials.refresh(Request())
        except Exception as err:
            logging.warning(f"Failed to load credentials: {str(err)}")
            self.log_error()
            self.credentials = None
            self.disable_feedback = True
        finally:
            if hasattr(self, "REAZIONE"):
                del self.REAZIONE
            os.environ.pop("REAZIONE", None)
            os.environ.pop("DURATA_FUSCAZIONE_AVAIN", None)
            os.environ.pop("oletuksena_segreto", None)

    def update_app(self, latest_version):
        lang = self.language_menu.get()
        translation = self.load_language()
        current = None
        latest = None
        if lang == "English":
            current = "Current"
            latest = "Latest"
        elif lang == "Español":
            current = "Actual"
            latest = "Nueva"
        self.play_sound("update.wav")
        msg = CTkMessagebox(title=translation["update_popup_title"],
                            message=translation["update_popup_message_1"] + "\n\n" + current + ": v" +
                            self.USER_APP_VERSION + " ---> " + latest + ": v" + latest_version,
                            option_1=translation["option_1"], option_3=translation["update_now"],
                            option_2=translation["download_title"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"), icon="question",
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if response[0] == translation["update_now"]:
            self.cursor_db.execute("UPDATE user_config SET update_date = NULL")
            self.run_updater(latest_version)
        elif response[0] == translation["download_title"]:
            self.cursor_db.execute("UPDATE user_config SET update_date = NULL")
            webbrowser.open("https://github.com/Hanuwa/TeraTermUI/releases/latest")

    # Deletes Tesseract OCR and tera term config file from the temp folder
    def cleanup_temp(self):
        tesseract_dir = Path(self.app_temp_dir) / "Tesseract-OCR"
        backup_file_path = Path(self.app_temp_dir) / "TERATERM.ini.bak"
        if self.mode == "Portable":
            if tesseract_dir.exists():
                for _ in range(10): # Retry up to 10 times
                    try:
                        shutil.rmtree(tesseract_dir)
                        break
                    except PermissionError:
                        time.sleep(0.5)
        elif self.mode == "Installation":
            if tesseract_dir.exists() and self.delete_tesseract_dir:
                for _ in range(10):  # Retry up to 10 times
                    try:
                        shutil.rmtree(tesseract_dir)
                        break
                    except PermissionError:
                        time.sleep(0.5)
        # Delete the 'TERATERM.ini.bak' file
        if backup_file_path.exists() and not TeraTermUI.checkIfProcessRunning("ttermpro"):
            os.remove(backup_file_path)
        if self.mode == "Portable" or (self.mode == "Installation" and self.delete_tesseract_dir) \
                and not TeraTermUI.checkIfProcessRunning("ttermpro"):
            if not self.running_updater:
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
        center_x += 100
        center_y -= 20
        monitor = TeraTermUI.get_monitor_bounds(main_window_x, main_window_y)
        monitor_x, monitor_y, monitor_width, monitor_height = monitor.x, monitor.y, monitor.width, monitor.height
        center_x = max(monitor_x, min(center_x, monitor_x + monitor_width - top_level_width))
        center_y = max(monitor_y, min(center_y, monitor_y + monitor_height - top_level_height))
        window_geometry = f"{width}x{height}+{center_x}+{center_y}"
        self.play_sound("error.wav")
        self.error = SmoothFadeToplevel(fade_duration=10)
        self.error.title("Error")
        self.error.geometry(window_geometry)
        self.error.resizable(False, False)
        self.error.iconbitmap(self.icon_path)
        my_image = self.get_image("error")
        image = customtkinter.CTkLabel(self.error, text="", image=my_image)
        image.pack(padx=10, pady=20)
        error_msg = customtkinter.CTkLabel(self.error, text=error_msg_text,
                                           font=customtkinter.CTkFont(size=15, weight="bold"))
        error_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)
        self.error.protocol("WM_DELETE_WINDOW", self.on_error_window_close)
        self.error.bind("<Escape>", lambda event: self.on_error_window_close())

    def on_error_window_close(self):
        self.error.unbind("<Escape>")
        self.unload_image("error")
        self.error.destroy()
        self.error = None
        gc.collect()

    # success window pop up message
    def show_success_message(self, width, height, success_msg_text):
        translation = self.load_language()
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
        center_x += 100
        center_y -= 20
        monitor = TeraTermUI.get_monitor_bounds(main_window_x, main_window_y)
        monitor_x, monitor_y, monitor_width, monitor_height = monitor.x, monitor.y, monitor.width, monitor.height
        center_x = max(monitor_x, min(center_x, monitor_x + monitor_width - top_level_width))
        center_y = max(monitor_y, min(center_y, monitor_y + monitor_height - top_level_height))
        window_geometry = f"{width}x{height}+{center_x}+{center_y}"
        self.play_sound("success.wav")
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
        self.success.unbind("<Escape>")
        self.unload_image("success")
        self.success.destroy()
        self.success = None
        if self.help is not None and self.help.winfo_exists() and self.changed_location:
            self.after(250, self.files.configure(state="normal"))
            self.after(250, self.help.lift)
            self.after(250, self.help.focus_set)
            self.changed_location = False
        gc.collect()

    def parse_enrollment_errors(self, text_output, submitted_classes=None):
        translation = self.load_language()
        found_errors = []
        lines = text_output.splitlines()

        course_section_pattern = re.compile(r"([A-Z]{4})([0-9@]{4})([A-Z0-9]{3})")
        for line in lines:
            for code, message in self.enrollment_error_messages.items():
                if code in line:
                    match = course_section_pattern.search(line)
                    if match:
                        subject, number, section = match.groups()
                        number = number.replace("@", "0")
                        formatted = f"{subject}-{number}-{section}"
                        found_errors.append(f"{formatted}: {message}")
                    else:
                        if submitted_classes:
                            cleaned_line = re.sub(r"[^A-Z0-9]", "", line.upper())
                            match = get_close_matches(cleaned_line, [cls.upper().replace("-", "") for cls in
                                                                     submitted_classes], n=1, cutoff=0.6)
                            if match:
                                formatted_match = match[0]
                                found_errors.append(f"{formatted_match}: {message}")
                            else:
                                found_errors.append(f"{translation['unknown_class_status']}: {message}")
                        else:
                            found_errors.append(f"{translation['unknown_class_status']}: {message}")

        return found_errors

    # Pop window that shows the user more context on why they couldn't enroll their classes
    def show_enrollment_error_information(self, text="Error", submitted_class=None):
        translation = self.load_language()
        found_errors = self.parse_enrollment_errors(text, submitted_class)
        if found_errors:
            self.destroy_windows()
            error_message_str = "\n".join(f"{i+1}. {error}" for i, error in enumerate(found_errors))
            self.play_sound("notification.wav")
            CTkMessagebox(title=translation["automation_error_title"], icon="cancel",
                          message=translation["specific_enrollment_error_s"] + error_message_str, button_width=380)
            self.clipboard_clear()
            self.clipboard_append(error_message_str)
        self.submit.configure(state="normal")
        self.submit_multiple.configure(state="normal")
        self.not_rebind = False
        if self.in_multiple_screen:
            self.after(150, self.bind, "<Return>", lambda event: self.submit_multiple_event_handler())
        else:
            self.switch_tab()
        if self.enrollment_error_check == 1:
            self.destroy_windows()
            self.play_sound("notification.wav")
            self.enrollment_error_check += 1
            CTkMessagebox(title=translation["automation_error_title"], message=translation["enrollment_error"],
                          button_width=380)

    # Pop window that shows the user more context on why they couldn't enroll their classes
    def show_enrollment_error_information_multiple(self, text="Error", submitted_classes=None):
        translation = self.load_language()
        found_errors = self.parse_enrollment_errors(text, submitted_classes)
        if found_errors:
            self.destroy_windows()
            error_message_str = "\n".join(f"{i+1}. {error}" for i, error in enumerate(found_errors))
            self.play_sound("notification.wav")
            if len(found_errors) == 1:
                msg = translation["specific_enrollment_error_s"]
            else:
                msg = translation["specific_enrollment_error_p"]
            CTkMessagebox(title=translation["automation_error_title"], icon="cancel", button_width=380,
                          message=msg + error_message_str)
            self.clipboard_clear()
            self.clipboard_append(error_message_str)
            for counter in range(self.a_counter + 1, 0, -1):
                if self.classes_status:
                    last_item = list(self.classes_status.keys())[-1]
                    self.classes_status.pop(last_item)
        elif text != "Error":
            for i in range(self.a_counter + 1):
                self.m_classes_entry[i].delete(0, "end")
                self.m_section_entry[i].delete(0, "end")
                self.m_classes_entry[i].configure(
                    placeholder_text=self.placeholder_texts_classes[i])
                self.m_section_entry[i].configure(
                    placeholder_text=self.placeholder_texts_sections[i])
                dummy_event_classes = type("Dummy", (object,), {"widget": self.m_classes_entry[i]})()
                self.detect_change(dummy_event_classes)
                dummy_event_sections = type("Dummy", (object,), {"widget": self.m_section_entry[i]})()
                self.detect_change(dummy_event_sections)
                self.check_class_conflicts()
        self.submit.configure(state="normal")
        self.submit_multiple.configure(state="normal")
        self.not_rebind = False
        if self.in_multiple_screen:
            self.bind("<Return>", lambda event: self.submit_multiple_event_handler())
        else:
            self.switch_tab()
        if self.enrollment_error_check == 1:
            self.destroy_windows()
            self.play_sound("notification.wav")
            self.enrollment_error_check += 1
            CTkMessagebox(title=translation["automation_error_title"], message=translation["enrollment_error"],
                          button_width=380)

    def show_modify_classes_information(self):
        self.destroy_windows()
        translation = self.load_language()
        if self.modify_error_check:
            if self.enrolled_classes_data is not None:
                self.bind("<Return>", lambda event: self.submit_modify_classes_handler())
                self.submit_my_classes.configure(state="normal")
            self.not_rebind = False
            self.play_sound("notification.wav")
            CTkMessagebox(title=translation["automation_error_title"], message=translation["modify_error"],
                          button_width=380)

    # important information window pop up message
    def show_information_message(self, width, height, success_msg_text):
        translation = self.load_language()
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
        center_x += 100
        center_y -= 20
        monitor = TeraTermUI.get_monitor_bounds(main_window_x, main_window_y)
        monitor_x, monitor_y, monitor_width, monitor_height = monitor.x, monitor.y, monitor.width, monitor.height
        center_x = max(monitor_x, min(center_x, monitor_x + monitor_width - top_level_width))
        center_y = max(monitor_y, min(center_y, monitor_y + monitor_height - top_level_height))
        window_geometry = f"{width}x{height}+{center_x}+{center_y}"
        self.play_sound("notification.wav")
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
        self.information.unbind("<Escape>")
        self.unload_image("information")
        self.information.destroy()
        self.information = None
        gc.collect()

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
    def manage_user_input(state="off"):
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
        TeraTermUI.manage_user_input("on")
        self.timeout_occurred = False

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

        customtkinter.set_appearance_mode(new_appearance_mode)
        self.curr_appearance = new_appearance_mode
        self.focus_set()

    def add_key_bindings(self, event):
        if self.in_search_frame:
            if len(self.class_table_pairs) > 1:
                self.bind("<Left>", self.keybind_previous_table)
                self.bind("<Right>", self.keybind_next_table)
        else:
            self.bind("<Left>", self.move_slider_left)
            self.bind("<Right>", self.move_slider_right)

    def move_slider(self, event):
        if self.debounce_slider:
            self.after_cancel(self.debounce_slider)

        self.debounce_slider = self.after(50, lambda: self._execute_slider(event))

    def _execute_slider(self, event):
        if event.delta > 0:
            self.move_slider_right(event)
        else:
            self.move_slider_left(event)

    # Moves the scaling slider to the left
    def move_slider_left(self, event):
        if self.move_slider_left_enabled:
            value = self.scaling_slider.get()
            if value != 97:
                value -= 3
                self.scaling_slider.set(value)
                self.change_scaling_event(value)
                self.scaling_tooltip.configure(message=f"{self.scaling_slider.get():.0f}%")

    # Moves the scaling slider to the right
    def move_slider_right(self, event):
        if self.move_slider_right_enabled:
            value = self.scaling_slider.get()
            if value != 103:
                value += 3
                self.scaling_slider.set(value)
                self.change_scaling_event(value)
                self.scaling_tooltip.configure(message=f"{self.scaling_slider.get():.0f}%")

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

        current_time = time.time()
        time_since_last_update = current_time - self.last_scaling_update
        if time_since_last_update < 0.1:
            return

        scaling_change = abs(new_scaling_float - self.last_scaling_value)
        if scaling_change > 0.25:
            direction = 1 if new_scaling_float > self.last_scaling_value else -1
            new_scaling_float = self.last_scaling_value + (direction * 0.25)
            new_scaling = new_scaling_float * 100

        self.scaling_tooltip.hide()
        customtkinter.set_widget_scaling(new_scaling_float)
        self.scaling_tooltip.configure(message=f"{new_scaling:.0f}%")
        self.curr_scaling = new_scaling_float
        self.last_scaling_value = new_scaling_float
        self.last_scaling_update = current_time
        self.scaling_tooltip.show()
        self.focus_set()

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
        translation = self.load_language()
        self.play_sound("notification.wav")
        msg = CTkMessagebox(title=translation["download_title"], message=translation["download_tera_term"],
                            icon="question", option_1=translation["option_1"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            webbrowser.open("https://teratermproject.github.io/index-en.html")
        self.log_in.configure(state="nornal")
        self.bind("<Return>", lambda event: self.login_event_handler())

    # links to each correspondant curriculum that the user chooses
    def curriculums_link(self, choice):
        translation = self.load_language()
        links = {
            translation["dep"]: "https://www.uprb.edu/sobre-uprb/decanato-de-asuntos-academicos/departamentos-academicos-2/",
            translation["acc"]: "https://drive.google.com/file/d/0BzdErxfu_JSCSDA0NHMyYVNhdXA3V1ZqX2c1aUlIT21Oc1RF/view",
            translation["finance"]: "https://drive.google.com/file/d/0BzdErxfu_JSCR2gyNzJOeHA2c2EwTklRYmZYZ0Zfck9UT3E0/view",
            translation["management"]: "https://drive.google.com/file/d/0BzdErxfu_JSCVllhTWJGMzRYd3JoemtObDkzX3I5MHNqU3V3/view",
            translation["mark"]: "https://drive.google.com/file/d/0BzdErxfu_JSCa3BIWnZyQmlHa0hGcEVtSlV2d2gxN0dENVcw/view",
            translation["g_biology"]: "https://drive.google.com/file/d/11yfoYqXYPybDZmeEmgW8osgSCCmxzjQl/view",
            translation["h_biology"]: "https://drive.google.com/file/d/1z-aphTwLLwAY5-G3O7_SXG3ZvvRSN6p9/view",
            translation["c_science"]: "https://docs.uprb.edu/deptsici/CIENCIAS-DE-COMPUTADORAS-2016.pdf",
            translation["it"]: "https://docs.uprb.edu/deptsici/SISTEMAS-INFORMACION-2016.pdf",
            translation["s_science"]: "https://drive.google.com/file/d/1cZnD6EhBsu7u6U8IVZoeK0VHgQmYt3sf/view",
            translation["physical"]: "https://drive.google.com/file/d/0BzdErxfu_JSCQWFEWlpCSnRFMVFGQnZoTXRyZHJiMzBkc2dZ/view",
            translation["elec"]: "https://drive.google.com/file/d/1tfzaHKilu5iQccD2sBzD8O_6UlXtSREF/view",
            translation["equip"]: "https://drive.google.com/file/d/13ohtab5ns6qO2QIHouScKtrFHrM7X3zl/view",
            translation["peda"]: "https://www.upr.edu/bayamon/wp-content/uploads/sites/9/2015/06/Secuencia-curricular-aprobada-en-mayo-de-2013.pdf",
            translation["che"]: "https://drive.google.com/file/d/0BzdErxfu_JSCNHJENWNaY1JmZjNSSU5mR2U5SnVOc1gxUTVJ/view",
            translation["nur"]: "https://drive.google.com/file/d/0BzdErxfu_JSCaF9tMFc3Y0hnRGpsZ1dMTXFPRjRMUlVEQ1ZZ/view",
            translation["office"]: "https://docs.uprb.edu/deptsofi/curriculo-BA-SOFI-agosto-2016.pdf",
            translation["engi"]: "https://drive.google.com/file/d/1mYCHmCy3Mb2fDyp9EiFEtR0j4-rsDdlN/view"}
        url = links.get(choice, None)
        if url:
            webbrowser.open(url)

    def check_update_app_handler(self):
        self.updating_app = True
        loading_screen = self.show_loading_screen()
        future = self.thread_pool.submit(self.check_update_app)
        self.update_loading_screen(loading_screen, future)
        self.update_event_completed = False

    # will tell the user that there's a new update available for the application
    def check_update_app(self):
        with self.lock_thread:
            try:
                lang = self.language_menu.get()
                translation = self.load_language()
                if asyncio.run(self.test_connection()):
                    latest_version = self.get_latest_release()
                    if latest_version is None:
                        def error():
                            logging.warning("No latest release found. Continuing with the current version")
                            self.play_sound("error.wav")
                            CTkMessagebox(title=translation["error"], icon="cancel",
                                          message=translation["failed_to_find_update"], button_width=380)

                        self.after(50, error)
                        return
                    if not TeraTermUI.compare_versions(latest_version, self.USER_APP_VERSION):
                        def update():
                            current = None
                            latest = None
                            if lang == "English":
                                current = "Current"
                                latest = "Latest"
                            elif lang == "Español":
                                current = "Actual"
                                latest = "Nueva"
                            self.play_sound("update.wav")
                            msg = CTkMessagebox(title=translation["update_popup_title"],
                                                message=translation["update_popup_message_2"] + "\n\n" + current + ": v" +
                                                self.USER_APP_VERSION + " ---> " + latest + ": v" + latest_version,
                                                option_1=translation["option_1"], option_3=translation["update_now"],
                                                option_2=translation["download_title"], icon_size=(65, 65),
                                                button_color=("#c30101", "#145DA0", "#145DA0"), icon="question",
                                                hover_color=("darkred", "use_default", "use_default"))
                            response = msg.get()
                            if response[0] == translation["update_now"]:
                                self.cursor_db.execute("UPDATE user_config SET update_date = NULL")
                                self.run_updater(latest_version)
                            elif response[0] == translation["download_title"]:
                                self.cursor_db.execute("UPDATE user_config SET update_date = NULL")
                                webbrowser.open("https://github.com/Hanuwa/TeraTermUI/releases/latest")

                        self.after(50, update)
                    else:
                        def up_to_date():
                            self.play_sound("notification.wav")
                            CTkMessagebox(title=translation["update_popup_title"],
                                          message=translation["update_up_to_date"],
                                          button_width=380)

                        self.after(50, up_to_date)
                else:
                    self.updating_app = False
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                if self.error_occurred and not self.timeout_occurred:
                    def error_update():
                        self.play_sound("error.wav")
                        CTkMessagebox(title=translation["error"], icon="cancel",
                                      message=translation["failed_to_find_update"], button_width=380)
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(50, error_update)
                else:
                    self.status.focus_set()
                self.update_event_completed = True

    @staticmethod
    def verify_file_integrity(file_path, expected_hash):
        import hashlib

        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            actual_hash = hasher.hexdigest()

            if actual_hash != expected_hash:
                raise ValueError(f"Hash mismatch for {file_path}. Expected: {expected_hash}, Got: {actual_hash}")
            return True
        except Exception as err:
            logging.error(f"Failed to compute hash for {file_path}: {err}")
            raise

    def run_updater(self, latest_version):
        try:
            current_exe = sys.executable
            sys_path = Path(current_exe).parent.resolve()
            app_temp_dir = Path(self.app_temp_dir)
            updater_exe_dest = app_temp_dir / "updater.exe"
            if self.mode == "Portable":
                updater_exe_src = sys_path / "updater.exe"
                db_folder = sys_path
                shutil.copy2(str(updater_exe_src), str(updater_exe_dest))
            elif self.mode == "Installation":
                appdata_path = None
                scope, _ = TeraTermUI.get_installation_scope()
                if scope == "all_users":
                    appdata_path = os.environ.get("PROGRAMDATA")
                elif scope == "current_user":
                    appdata_path = os.environ.get("APPDATA")
                if appdata_path:
                    updater_exe_src = Path(appdata_path) / "TeraTermUI" / "updater.exe"
                    db_folder = Path(appdata_path) / "TeraTermUI"
                    shutil.copy2(str(updater_exe_src), str(updater_exe_dest))
            if not TeraTermUI.verify_file_integrity(updater_exe_dest, self.updater_hash):
                return
            updater_args = [str(updater_exe_dest), self.mode, latest_version, str(sys_path), str(db_folder)]
            subprocess.Popen(updater_args)
            self.running_updater = True
            self.direct_close()
        except Exception as err:
            logging.error(f"Failed to launch the updater script: {err}")
            self.log_error()
            webbrowser.open("https://github.com/Hanuwa/TeraTermUI/releases/latest")

    def del_user_data(self):
        translation = self.load_language()
        now = time.time()
        if now - self.last_delete_time < 3:
            return

        self.last_delete_time = now
        if self.has_saved_user_data():
            self.cursor_db.execute("DELETE FROM user_data")
            self.connection_db.commit()
            self.crypto.reset()
            if self.in_student_frame:
                if self.remember_me.get() == "on":
                    self.remember_me.toggle()
            self.show_success_message(340, 255, translation["del_data_success"])

    def fix_execution_event_handler(self):
        translation = self.load_language()
        if TeraTermUI.checkIfProcessRunning("ttermpro"):
            msg = CTkMessagebox(title=translation["fix_messagebox_title"],
                                message=translation["fix_messagebox"], icon="warning",
                                option_1=translation["option_1"], option_2=translation["option_2"],
                                option_3=translation["option_3"], icon_size=(65, 65),
                                button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "use_default", "use_default"))
            response = msg.get()
            if response[0] == "Yes" or response[0] == "Sí":
                loading_screen = self.show_loading_screen()
                future = self.thread_pool.submit(self.fix_execution)
                self.update_loading_screen(loading_screen, future)
                self.fix_execution_event_completed = False

    # If user messes up the execution of the program this can solve it and make program work as expected
    def fix_execution(self):
        with self.lock_thread:
            try:
                translation = self.load_language()
                self.automation_preparations()
                if not self.wait_for_window():
                    return
                if self.search_function_counter == 0:
                    text_output = self.capture_screenshot()
                    if "INVALID ACTION" in text_output and "LISTA DE SECCIONES" in text_output:
                        self.uprb.UprbayTeraTermVt.type_keys("{TAB 2}SRM{ENTER}")
                        self.reset_activity_timer()
                else:
                    self.uprb.UprbayTeraTermVt.type_keys("{TAB}SRM" + self.DEFAULT_SEMESTER + "{ENTER}")
                    self.reset_activity_timer()
                text_output = self.capture_screenshot()
                if "INVALID ACTION" in text_output:
                    self.uprb.UprbayTeraTermVt.type_keys("{TAB}SRM" + self.DEFAULT_SEMESTER + "{ENTER}")
                    self.reset_activity_timer()
                elif "PF4=exit" in text_output or "press PF4" in text_output:
                    self.uprb.UprbayTeraTermVt.type_keys("^v")
                    self.reset_activity_timer()
                self.classes_status.clear()
                self.cursor_db.execute("UPDATE user_config SET default_semester=NULL")
                self.connection_db.commit()
                if not self.error_occurred and not self.show_fix_exe:
                    self.after(100, self.show_information_message, 355, 235,
                               translation["fix_after"])
                    self.show_fix_exe = True
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                self.after(100, self.set_focus_to_tkinter)
                self.after(0, self.switch_tab)
                translation = self.load_language()
                if self.error_occurred and not self.timeout_occurred:
                    def error_automation():
                        self.destroy_windows()
                        self.play_sound("notification.wav")
                        CTkMessagebox(title=translation["automation_error_title"],
                                      message=translation["automation_error"], icon="warning", button_width=380)
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_automation)
                TeraTermUI.manage_user_input()
                self.fix_execution_event_completed = True

    @staticmethod
    def get_device_type():
        try:
            result = subprocess.run(["powershell", "-Command", "(Get-WmiObject -Class Win32_Battery).Status"],
                                    stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if "BatteryStatus" in result.stdout:
                return "laptop"
            else:
                return "desktop"
        except Exception as err:
            logging.error(f"Error determining device type: {err}")
            return None

    @staticmethod
    def get_power_timeout():
        def query_timeout(subgroup, setting):
            try:
                result = subprocess.run(["powercfg", "/query", "SCHEME_CURRENT", subgroup, setting],
                                        stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
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
                return None
            except Exception as err:
                logging.error(f"Error querying power settings: {err}")
                return None

        power_timeout = (query_timeout("SUB_VIDEO", "VIDEOIDLE") or
                         query_timeout("SUB_SLEEP", "HIBERNATEIDLE"))

        return power_timeout if power_timeout else None

    @staticmethod
    def is_win_session_interactive():
        try:
            WTSQuerySessionInformation = ctypes.windll.Wtsapi32.WTSQuerySessionInformationW
            WTSFreeMemory = ctypes.windll.Wtsapi32.WTSFreeMemory
            WTS_CONNECTSTATE_CLASS = 0
            WTSActive = 0

            session_id = ctypes.windll.kernel32.WTSGetActiveConsoleSessionId()
            buffer = ctypes.c_void_p()
            bytes_returned = wintypes.DWORD()

            result = WTSQuerySessionInformation(None, session_id, WTS_CONNECTSTATE_CLASS,
                                                ctypes.byref(buffer), ctypes.byref(bytes_returned))
            is_active = False
            if result:
                value = ctypes.cast(buffer, ctypes.POINTER(wintypes.DWORD)).contents.value
                WTSFreeMemory(buffer)
                is_active = (value == WTSActive)

            desktop = ctypes.windll.user32.OpenInputDesktop(0, False, 0x100)
            is_unlocked = desktop != 0
            if is_unlocked:
                ctypes.windll.user32.CloseDesktop(desktop)

            return is_active and is_unlocked

        except Exception as err:
            logging.warning(f"Unable to determine session state: {err}")
            return True

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

        lang = self.language_menu.get()
        translation = self.load_language()
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
                idle = self.cursor_db.execute("SELECT idle FROM user_config").fetchone()
            except Exception as err:
                idle = ["Disabled"]
                logging.error("An error occurred: %s", err)
                self.log_error()
            if self.loading_screen_status is None and idle[0] != "Disabled":
                if threshold is not None:
                    idle_time = get_idle_duration()
                    if idle_time >= threshold and TeraTermUI.is_win_session_interactive():
                        ES_DISPLAY_REQUIRED = 0x00000002
                        ctypes.windll.kernel32.SetThreadExecutionState(ES_DISPLAY_REQUIRED)
                        pyautogui.press("scrolllock")
                        time.sleep(1)
                        pyautogui.press("scrolllock")
                stats = self.ssh_monitor.get_stats()
                host = self.ssh_monitor.host
                rating, color = self.ssh_monitor.get_reliability_rating(lang)
                sample_count = (40 if not stats or stats["samples"] < 10 else 30 if stats["std_dev"] > 100
                                or stats["max"] > 1000 or stats["average"] > 400 else 20)
                self.ssh_monitor.sample(count=sample_count)
                new_sample_count = stats.get("samples")
                has_new_data = (self.prev_sample_count != new_sample_count)
                if self.timer_window is not None and self.timer_window.winfo_exists() and has_new_data:
                    self.server_rating.configure(text=f"{translation['server_status_rating']}{rating}",
                                                 text_color=color)
                if has_new_data:
                    logging.info(f'Server "{host}" Response Time Statistics (ms):\n       {stats}')
                    self.prev_sample_count = new_sample_count
                is_running = TeraTermUI.checkIfProcessRunning("ttermpro")
                if is_running:
                    if not_running_count > 1 and self.stop_check_idle.is_set():
                        self.start_check_idle_thread()
                    not_running_count = 0
                    self.forceful_countdown_end = False
                else:
                    not_running_count += 1
                    if not_running_count == 1:
                        def not_running():
                            self.play_sound("notification.wav")
                            CTkMessagebox(title=translation["automation_error_title"], icon="warning",
                                          message=translation["tera_term_stopped_running"], button_width=380)

                        if not self.forceful_countdown_end:
                            self.after(50, not_running)
                        self.forceful_countdown_end = False
                    if not_running_count > 1:
                        self.stop_check_process_thread()
            time.sleep(30 + random.uniform(5, 15))

    def stop_check_idle_thread(self):
        if not self.stop_check_idle.is_set():
            self.stop_check_idle.set()
            self.reset_activity_timer()

    # Starts the check for idle thread
    def start_check_idle_thread(self):
        idle = self.cursor_db.execute("SELECT idle FROM user_config").fetchone()
        if idle[0] != "Disabled":
            self.check_idle_thread = threading.Thread(target=self.check_idle)
            if self.stop_check_idle.is_set():
                self.stop_check_idle.clear()
            self.check_idle_thread.daemon = True
            self.check_idle_thread.start()

    # Checks if the user is idle for 3 minutes and does some action so that Tera Term doesn't close by itself
    def check_idle(self):
        translation = self.load_language()
        self.idle_num_check = 0
        self.last_activity = time.time()
        self.idle_threshold = 180
        self.use_temp_threshold = False
        try:
            while not self.stop_check_idle.is_set():
                threshold = self.idle_threshold * 0.75 if self.use_temp_threshold else self.idle_threshold
                if time.time() - self.last_activity >= threshold:
                    with self.lock_thread:
                        if TeraTermUI.checkIfProcessRunning("ttermpro"):
                            translation = self.load_language()
                            if TeraTermUI.window_exists(translation["idle_warning_title"]):
                                self.idle_warning.close_messagebox()
                            if TeraTermUI.is_win_session_interactive():
                                self.keep_teraterm_open()
                            self.last_activity = time.time()
                            self.idle_num_check += 1
                            if self.use_temp_threshold:
                                self.use_temp_threshold = False
                            if self.idle_num_check % 5 == 0:
                                self.use_temp_threshold = True
                            if self.idle_num_check == 34 and not self.countdown_running:
                                def idle_warning():
                                    self.play_sound("notification.wav")
                                    self.idle_warning = CTkMessagebox(
                                        title=translation["idle_warning_title"], message=translation["idle_warning"],
                                        button_width=380)
                                    self.idle_warning.lift()
                                    self.idle_warning.focus_force()
                                    self.idle_warning.attributes("-topmost", 1)
                                    self.idle_warning.after_idle(self.idle_warning.attributes, "-topmost", 0)
                                    response = self.idle_warning.get()[0]
                                    if response == "OK":
                                        self.idle_num_check = max(0, self.idle_num_check // 2)

                                self.after(50, idle_warning)
                        else:
                            self.stop_check_idle_thread()
                if self.idle_num_check == 35 and not self.countdown_running:
                    self.stop_check_idle_thread()
                time.sleep(25)
        except Exception as err:
            logging.error("An error occurred: %s", err)
            self.log_error()

    def keep_teraterm_open(self):
        try:
            main_window = self.uprb_32.window(title="uprbay.uprb.edu - Tera Term VT")
            main_window.wait("exists", 3)
        except Exception as err:
            logging.error("An error occurred: %s", err)
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
        if self.auto_enroll_status == "Not Auto-Enrolling":
            self.last_activity = time.time()
            if not isinstance(self.idle_num_check, int):
                self.idle_num_check = 0
            self.idle_num_check = max(0, self.idle_num_check // 2)

    def keybind_disable_enable_idle(self):
        if self.disable_idle.get() == "on":
            self.disable_idle.deselect()
        elif self.disable_idle.get() == "off":
            self.disable_idle.select()
        self.disable_enable_idle()

    # Disables check_idle functionality
    def disable_enable_idle(self):
        row_exists = self.cursor_db.execute("SELECT 1 FROM user_config").fetchone()
        if self.disable_idle.get() == "on":
            if not row_exists:
                self.cursor_db.execute("INSERT INTO user_config (idle) VALUES (?)", ("Disabled",))
            else:
                self.cursor_db.execute("UPDATE user_config SET idle=?", ("Disabled",))
            self.stop_check_idle_thread()
        elif self.disable_idle.get() == "off":
            if not row_exists:
                self.cursor_db.execute("INSERT INTO user_config (idle) VALUES (?)", ("Enabled",))
            else:
                self.cursor_db.execute("UPDATE user_config SET idle=?", ("Enabled",))
            if self.auto_enroll is not None:
                self.auto_enroll.configure(state="normal")
            if self.run_fix and TeraTermUI.checkIfProcessRunning("ttermpro"):
                self.start_check_idle_thread()
                self.keep_teraterm_open()
                self.reset_activity_timer()
        self.connection_db.commit()

    def keybind_disable_enable_audio(self, source):
        if source == "tera":
            switch = self.disable_audio_tera
        elif source == "app":
            switch = self.disable_audio_app
        else:
            return
        if switch.get() == "on":
            switch.deselect()
        else:
            switch.select()
        self.disable_enable_audio(source)

    def disable_enable_audio(self, source):
        row_exists = self.cursor_db.execute("SELECT 1 FROM user_config").fetchone()
        if source == "tera":
            is_on = self.disable_audio_tera.get() == "on"
            column_name = "audio_tera"
        elif source == "app":
            is_on = self.disable_audio_app.get() == "on"
            column_name = "audio_app"
        else:
            return
        new_value = "Disabled" if is_on else "Enabled"
        if not row_exists:
            self.cursor_db.execute(f"INSERT INTO user_config ({column_name}) VALUES (?)", (new_value,))
        else:
            self.cursor_db.execute(f"UPDATE user_config SET {column_name}=?", (new_value,))
        self.connection_db.commit()
        if source == "tera":
            self.set_beep_sound(self.teraterm_config, is_on)
            self.muted_tera = is_on
        elif source == "app":
            self.muted_app = is_on

    @staticmethod
    async def fetch(session, url):
        from aiohttp import ClientConnectionError

        headers = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")}
        try:
            async with session.head(url, timeout=5.0, headers=headers) as response:
                if response.status == 200:
                    return True
                logging.error(f"Non-200 response code with HEAD: {response.status}")
        except ClientConnectionError:
            logging.error(f"Failed to connect to {url} with HEAD request")
        except asyncio.TimeoutError:
            logging.error(f"HEAD request to {url} timed out")
        except Exception as err:
            logging.error(f"An unexpected error occurred during HEAD request: {err}")
        delay = 1
        retries = 5
        for attempt in range(retries):
            try:
                async with session.get(url, timeout=5.0, headers=headers) as response:
                    if response.status == 200:
                        return True
                    elif response.status == 429:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            delay = int(retry_after)
                        logging.warning(f"GET request to {url} rate-limited. Retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    logging.error(f"Non-200 response code with GET: {response.status}")
                    return False
            except ClientConnectionError:
                logging.error(f"Failed to connect to {url} with GET request")
                return False
            except asyncio.TimeoutError:
                logging.error(f"GET request to {url} timed out")
                return False
            except Exception as err:
                logging.error(f"An unexpected error occurred during GET request: {err}")
                return False
        return False

    async def test_connection(self):
        from aiohttp import ClientSession, TCPConnector

        translation = self.load_language()
        urls = ["https://www.google.com/", "https://www.bing.com/", "https://duckduckgo.com/"]
        async with ClientSession(connector=TCPConnector(limit=5)) as session:
            tasks = [asyncio.create_task(TeraTermUI.fetch(session, url)) for url in urls]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            connected = any(task.result() for task in done if not task.exception()
                            and isinstance(task.result(), bool) and task.result())
            for task in pending:
                task.cancel()
            if not connected:
                if not self.check_update:
                    await asyncio.sleep(1)
                    self.after(100, self.show_error_message, 300, 215, translation["no_internet"])
                if self.check_update:
                    self.check_update = False
        return connected

    # Set focus on the UI application window
    def set_focus_to_tkinter(self):
        self.lift()
        self.focus_force()
        if not self.error_occurred and not self.timeout_occurred:
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
                self.after(150, self.bind, "<Return>", lambda event: self.submit_event_handler())
            else:
                self.unbind("<Return>")
        elif self.tabview.get() == self.search_tab:
            self.search_scrollbar.configure(width=600, height=293)
            if hasattr(self, "table") and self.table is not None:
                self.current_class.grid_forget()
                self.table.grid_forget()
                self.table_count.grid_forget()
                self.table_pipe.grid_forget()
                self.table_position.grid_forget()
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
            self.after(150, self.bind, "<Return>", lambda event: self.search_event_handler())
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
            self.after(150, self.bind, "<Return>", lambda event: self.option_menu_event_handler())
        self.add_key_bindings(event=None)
        self.after(0, self.focus_set)

    def load_table(self):
        translation = self.load_language()
        if hasattr(self, "table") and self.table is not None:
            self.current_class.grid(row=2, column=1, padx=(0, 0), pady=(8, 0), sticky="n")
            self.table.grid(row=2, column=1, padx=(0, 0), pady=(40, 0), sticky="n")
            self.table_count.grid(row=4, column=1, padx=(0, 95), pady=(10, 0), sticky="n")
            self.table_pipe.grid(row=4, column=1, padx=(0, 0), pady=(10, 0), sticky="n")
            self.table_position.grid(row=4, column=1, padx=(95, 0), pady=(10, 0), sticky="n")
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
            table_position_label = (f" {translation['table_position']}{self.current_table_index + 1}"
                                    f"/{len(self.class_table_pairs)}")
            self.table_count.configure(text=table_count_label)
            self.table_position.configure(text=table_position_label)

    def status_widgets(self):
        lang = self.language_menu.get()
        translation = self.load_language()
        self.status_frame = CustomScrollableFrame(self.status, width=475, height=280,
                                                  fg_color=("#e6e6e6", "#222222"))
        self.status_title = customtkinter.CTkLabel(self.status_frame, text=translation["status_title"],
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        translation["app_version"] = translation["app_version"].replace("{version}", self.USER_APP_VERSION)
        self.version = customtkinter.CTkLabel(self.status_frame, text=translation["app_version"])
        self.feedback_text = CustomTextBox(self.status_frame, self, enable_autoscroll=False, lang=lang,
                                           wrap="word", border_spacing=8, width=340, height=200,
                                           fg_color=("#ffffff", "#111111"))
        self.feedback_send = CustomButton(master=self.status_frame, text=translation["feedback"], anchor="w", width=150,
                                          image=self.get_image("plane"), text_color=("gray10", "#DCE4EE"),
                                          command=self.start_feedback_thread)
        self.check_update_text = customtkinter.CTkLabel(self.status_frame, text=translation["update_title"])
        self.check_update_btn = CustomButton(master=self.status_frame, image=self.get_image("update"), width=150,
                                             text=translation["update"], anchor="w", text_color=("gray10", "#DCE4EE"),
                                             command=self.check_update_app_handler)
        self.website = customtkinter.CTkLabel(self.status_frame, text=translation["website"])
        self.website_link = CustomButton(master=self.status_frame, image=self.get_image("link"), text=translation["link"],
                                         anchor="w", text_color=("gray10", "#DCE4EE"), width=150,
                                         command=self.github_event)
        self.notaso = customtkinter.CTkLabel(self.status_frame, text=translation["notaso_title"])
        self.notaso_link = CustomButton(master=self.status_frame, image=self.get_image("link"), width=150,
                                        text=translation["notaso_link"], anchor="w", text_color=("gray10", "#DCE4EE"),
                                        command=self.notaso_event)
        self.keybinds_text = customtkinter.CTkLabel(self.status_frame, text=translation["keybinds_title"],
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
                         ["<Ctrl-MouseWheel>", translation["ctrl_mwheel"]],
                         ["<Right-Click>", translation["mouse_2"]],
                         ["<Home>", translation["home"]],
                         ["<End>", translation["end"]],
                         ["<F1>", translation["F1"]],
                         ["<Alt-F4>", translation["alt_f4"]]]
        self.faq_text = customtkinter.CTkLabel(self.status_frame, text=translation["faq"],
                                               font=customtkinter.CTkFont(size=15, weight="bold"))
        self.qa_table = [[translation["q"], translation["a"]],
                         [translation["q1"], translation["a1"]],
                         [translation["q2"], translation["a2"]]]

    # Creates the status window
    def status_button_event(self):
        if self.status is not None and self.status.winfo_exists():
            windows_status = gw.getWindowsWithTitle("Status") + gw.getWindowsWithTitle("Estado")
            if windows_status:
                min_win = windows_status[0].isMinimized
                if min_win:
                    self.status.deiconify()
                self.status.lift()
                self.status.focus_set()
            return
        lang = self.language_menu.get()
        translation = self.load_language()
        self.destroy_tooltip()
        self.status_tooltip.hide()
        self.status = SmoothFadeToplevel()
        self.status_widgets()
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()
        status_window_width = 475
        status_window_height = 280
        center_x = main_window_x + (main_window_width // 2) - (status_window_width // 2)
        center_y = main_window_y + (main_window_height // 2) - (status_window_height // 2)
        center_x += 70
        center_y -= 15
        monitor = TeraTermUI.get_monitor_bounds(main_window_x, main_window_y)
        monitor_x, monitor_y, monitor_width, monitor_height = monitor.x, monitor.y, monitor.width, monitor.height
        center_x = max(monitor_x, min(center_x, monitor_x + monitor_width - status_window_width))
        center_y = max(monitor_y, min(center_y, monitor_y + monitor_height - status_window_height))
        self.status.geometry(f"{status_window_width}x{status_window_height}+{center_x}+{center_y}")
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
        self.keybinds_text.pack(pady=(25, 0))
        self.keybinds_table = CTkTable(self.status_frame, column=2, row=22, values=self.keybinds, hover=False)
        self.keybinds_table.pack(expand=True, fill="both", padx=20)
        self.faq_text.pack()
        self.faq = CTkTable(self.status_frame, row=3, column=2, values=self.qa_table, hover=False)
        self.faq.pack(expand=True, fill="both", padx=20, pady=10)
        self.feedback_text.lang = lang
        self.status.focus_set()
        self.status_tooltip.show()
        self.status_frame.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.status_frame.bind("<Button-2>", lambda event: self.status_frame.focus_set())
        self.status_frame.bind("<Button-3>", lambda event: self.status_frame.focus_set())
        self.status_title.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.version.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.check_update_text.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.website.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.notaso.bind("<Button-1>", lambda event: self.status_frame.focus_set())
        self.keybinds_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
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
        if self.status:
            bindings = self.status.bind()
            if isinstance(bindings, (list, tuple)):
                for binding in bindings:
                    self.status.unbind(binding)

        def clear_commands(widget_s):
            if widget_s and hasattr(widget_s, "children"):
                for child in list(widget_s.children.values()):
                    widget_name_s = str(child).lower()
                    if hasattr(child, "configure") and ("button" in widget_name_s or "menu" in widget_name_s):
                        child.configure(command=None)
                    clear_commands(child)

        def safe_destroy(widget_s):
            try:
                if hasattr(widget_s, "bindings"):
                    if isinstance(widget_s.bindings, (list, tuple)):
                        widget_s.bindings = []
                widget_s.destroy()
            except Exception:
                pass

        if self.status:
            clear_commands(self.status)

        if self.status_frame:
            children = list(self.status_frame.winfo_children())
            for widget in children:
                widget_name = str(widget).lower()
                if "ctktable" in widget_name:
                    if hasattr(widget, "_values"):
                        widget._values = None
                elif "entry" in widget_name or "listbox" in widget_name or "text" in widget_name:
                    if hasattr(widget, "delete"):
                        try:
                            widget.delete(0, "end")
                        except Exception:
                            pass
                elif hasattr(widget, "set"):
                    try:
                        widget.set("")
                    except Exception:
                        pass
                if hasattr(widget, "_image"):
                    widget._image = None

                safe_destroy(widget)

        if hasattr(self, "unload_image"):
            for img_name in ["update", "link", "plane"]:
                self.unload_image(img_name)
                if hasattr(self, f"_{img_name}_image"):
                    setattr(self, f"_{img_name}_image", None)

        attrs_to_clear = ["status_frame", "status_title", "version", "feedback_text", "feedback_send",
                          "check_update_text", "check_update_btn", "website", "website_link", "notaso", "notaso_link",
                          "keybinds_text", "keybinds_table", "keybinds", "faq_text", "qa_table", "faq"]
        for attr in attrs_to_clear:
            if hasattr(self, attr):
                obj = getattr(self, attr)
                if obj is not None and hasattr(obj, "destroy"):
                    safe_destroy(obj)
                setattr(self, attr, None)

        navigation_flags = ["move_slider_left_enabled", "move_slider_right_enabled",
                            "up_arrow_key_enabled", "down_arrow_key_enabled"]
        for flag in navigation_flags:
            setattr(self, flag, True)

        if self.status:
            safe_destroy(self.status)
            self.status = None

        gc.collect()

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

    @staticmethod
    def get_cpu_info():
        try:
            result = subprocess.run(
                ["powershell", "-command", "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.stdout.strip() or "Unknown"
        except Exception:
            return "Unknown"

    @staticmethod
    def get_os_info():
        os_name = platform.system()
        os_version = platform.release()
        os_build = platform.version()
        return f"{os_name} {os_version} (Build {os_build})"

    # Function to call the Google Sheets API
    def call_sheets_api(self, values):
        from google.auth.transport.requests import Request
        from googleapiclient.errors import HttpError
        from googleapiclient.discovery import build

        if self.credentials.expired or not self.credentials.valid:
            try:
                self.credentials.refresh(Request())
            except Exception as refresh_error:
                logging.error(f"Failed to refresh OAuth token: {refresh_error}")
                return None

        if asyncio.run(self.test_connection()):
            self.connection_error = False
            try:
                service = build("sheets", "v4", credentials=self.credentials, cache_discovery=False)
            except:
                DISCOVERY_SERVICE_URL = "https://sheets.googleapis.com/$discovery/rest?version=v4"
                service = build("sheets", "v4", credentials=self.credentials,
                                discoveryServiceUrl=DISCOVERY_SERVICE_URL, cache_discovery=False)
            body = {"values": values}

            try:
                result = service.spreadsheets().values().append(
                    spreadsheetId="1ffJLgp8p-goOlxC10OFEu0JefBgQDsgEo_suis4k0Pw", range="Sheet1!A:E",
                    valueInputOption="RAW", insertDataOption="INSERT_ROWS", body=body).execute()
                return result
            except HttpError as error:
                logging.error(f"Google Sheets API error: {error}")
                self.log_error()
                return None
        else:
            self.connection_error = True

    def start_feedback_thread(self):
        translation = self.load_language()
        msg = CTkMessagebox(title=translation["submit"], message=translation["submit_feedback"],
                            icon="question", option_1=translation["option_1"], option_2=translation["option_2"],
                            option_3=translation["option_3"], icon_size=(65, 65),
                            button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "use_default", "use_default"))
        self.destroy_tooltip()
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            if not self.disable_feedback:
                current_date = datetime.today().strftime("%Y-%m-%d")
                date_record = self.cursor_db.execute("SELECT feedback_date FROM user_config").fetchone()
                if date_record is None or date_record[0] != current_date:
                    feedback = self.feedback_text.get("1.0", customtkinter.END).strip()
                    feedback = re.sub(r"[\u200B-\u200D\u2060\uFEFF]", "", feedback)
                    word_count = len(feedback.split())
                    if word_count < 1250:
                        if feedback:
                            self.sending_feedback = True
                            loading_screen = self.show_loading_screen()
                            future = self.thread_pool.submit(self.submit_feedback)
                            self.update_loading_screen(loading_screen, future)
                            self.submit_feedback_event_completed = False
                        else:
                            if not self.connection_error:
                                def show_error():
                                    self.play_sound("error.wav")
                                    CTkMessagebox(title=translation["error"], message=translation["feedback_empty"],
                                                  icon="cancel", button_width=380)

                                self.after(50, show_error)
                    else:
                        if not self.connection_error:
                            def show_error():
                                self.play_sound("error.wav")
                                CTkMessagebox(title=translation["error"], message=f"{translation['feedback_1000']}"
                                              f"\n\nWord count: {word_count}", icon="cancel", button_width=380)

                            self.after(50, show_error)
                else:
                    if not self.connection_error:
                        def show_error():
                            self.play_sound("error.wav")
                            CTkMessagebox(title=translation["error"], message=translation["feedback_day"],
                                          icon="cancel", button_width=380)

                        self.after(50, show_error)
            else:
                if not self.connection_error:
                    def show_error():
                        self.play_sound("error.wav")
                        CTkMessagebox(title=translation["error"], message=translation["feedback_unavailable"],
                                      icon="cancel", button_width=380)

                    self.after(50, show_error)

    # Submits feedback from the user to a Google sheet
    def submit_feedback(self):
        with self.lock_thread:
            try:
                translation = self.load_language()
                current_date = datetime.today().strftime("%Y-%m-%d")
                current_exact_time = datetime.today().strftime("%m/%d/%Y %I:%M %p")
                feedback = self.feedback_text.get("1.0", customtkinter.END).strip()
                cpu_model = TeraTermUI.get_cpu_info()
                os_info = TeraTermUI.get_os_info()
                app_version = self.USER_APP_VERSION
                result = self.call_sheets_api([[current_exact_time, cpu_model, os_info, app_version, feedback]])
                if result:
                    def show_success():
                        self.play_sound("success.wav")
                        CTkMessagebox(title=translation["success_title"], icon="check",
                                      message=translation["feedback_success"], button_width=380)

                    self.after(50, show_success)
                    row_exists = self.cursor_db.execute("SELECT 1 FROM user_config").fetchone()
                    if not row_exists:
                        self.cursor_db.execute("INSERT INTO user_config (feedback_date) VALUES (?)",
                                               (current_date,))
                    else:
                        self.cursor_db.execute("UPDATE user_config SET feedback_date=?",
                                               (current_date,))
                    self.connection_db.commit()
                else:
                    if not self.connection_error:
                        def show_error():
                            self.play_sound("error.wav")
                            CTkMessagebox(title=translation["error"], message=translation["feedback_error"],
                                          icon="cancel", button_width=380)

                        self.after(50, show_error)
            except Exception as err:
                logging.error("An error occurred: %s", err)
                self.error_occurred = True
                self.log_error()
            finally:
                if self.error_occurred and not self.timeout_occurred:
                    def error_feedback():
                        self.play_sound("error.wav")
                        CTkMessagebox(title=translation["error"], message=translation["feedback_error"],
                                      icon="cancel", button_width=380)
                        self.error_occurred = False
                        self.timeout_occurred = False

                    self.after(100, error_feedback)
                else:
                    self.status.focus_set()
                self.submit_feedback_event_completed = True

    @staticmethod
    def get_file_version_info(file_path):
        size = ctypes.windll.version.GetFileVersionInfoSizeW(file_path, None)
        if size == 0:
            return None

        buffer = ctypes.create_string_buffer(size)
        ctypes.windll.version.GetFileVersionInfoW(file_path, None, size, buffer)

        def query_value(subblock):
            result = wintypes.LPVOID()
            length = wintypes.UINT()
            if ctypes.windll.version.VerQueryValueW(buffer, subblock, ctypes.byref(result), ctypes.byref(length)):
                return ctypes.wstring_at(result, length.value)
            return None

        company = query_value(r"\StringFileInfo\040904b0\CompanyName")
        product = query_value(r"\StringFileInfo\040904b0\ProductName")

        return {"CompanyName": company.strip("\x00") if company else None,
                "ProductName": product.strip("\x00") if product else None}

    @staticmethod
    def is_valid_teraterm_exe(exe_path):
        if not os.path.exists(exe_path):
            return False

        metadata = TeraTermUI.get_file_version_info(exe_path)
        if not metadata:
            return False

        return metadata.get("ProductName", "").lower() == "tera term"

    @staticmethod
    def find_ttermpro():
        main_drive = os.environ["SystemRoot"][:3]

        # Prioritize common installation directories with recommended depth limits
        common_paths = {
            os.path.join(main_drive, "Program Files (x86)"): 5,
            os.path.join(main_drive, "Program Files"): 5,
            os.path.expandvars(r"%LOCALAPPDATA%\Programs"): 3,
        }
        # Exclude certain system & user directories during full scan
        excluded_dirs = {name.lower() for name in [
            "Recycler", "Recycled", "$RECYCLE.BIN", "System Volume Information",
            "Recovery", "Boot", "EFI", "Windows", "WinSxS", "ProgramData",
            "System32", "SysWOW64", "Prefetch", "Temp", "Users\\Default", "PerfLogs",
            "Pictures", "Music", "Videos", "Saved Games"
        ]}

        def search_in_path(search_path, search_depth=None):
            if not os.path.exists(path):
                return None

            stack = [(search_path, 0)]  # (directory, current depth)
            while stack:
                current_path, current_depth = stack.pop()
                if search_depth is not None and current_depth > search_depth:
                    continue
                try:
                    with os.scandir(current_path) as entries:
                        for entry in entries:
                            if entry.is_dir(follow_symlinks=False):
                                # Skip symbolic links to avoid potential cycles
                                if entry.is_symlink():
                                    continue
                                if entry.name.lower() in excluded_dirs:
                                    continue
                            if entry.is_file() and entry.name.lower() == "ttermpro.exe":
                                exe_path = entry.path
                                if TeraTermUI.is_valid_teraterm_exe(exe_path):
                                    return exe_path
                            elif entry.is_dir(follow_symlinks=False):
                                stack.append((entry.path, current_depth + 1))
                except (PermissionError, FileNotFoundError):
                    continue

            return None

        for path, depth in common_paths.items():
            result = search_in_path(path, search_depth=depth)
            if result:
                return result

        # If not found, scan the entire main drive
        full_drive_result = search_in_path(main_drive, search_depth=None)
        if full_drive_result:
            return full_drive_result
        else:
            return None

    def change_location_auto_handler(self):
        lang = self.language_menu.get()
        self.files.configure(state="disabled")
        message_english = "Would you like the application to search for Tera Term on the main drive automatically? " \
                          "(click  the \"no\" button to search for it manually)\n\n" \
                          "NOTE: This process may take some time and make the application unresponsive briefly"
        message_spanish = "¿Desea que la aplicación busque automáticamente Tera Term en la unidad principal? " \
                          "(hacer clic al botón \"no\" para buscarlo manualmente)\n\n" \
                          "NOTA:  Este proceso podría tardar un poco y causar que la aplicación brevemente no responda"
        message = message_english if lang == "English" else message_spanish
        response = messagebox.askyesnocancel("Tera Term", message)
        if response is True:
            self.auto_search = True
            loading_screen = self.show_loading_screen()
            future = self.thread_pool.submit(self.change_location_event)
            self.update_loading_screen(loading_screen, future)
        elif response is False:
            self.manually_change_location()
        else:
            if self.help is not None and self.help.winfo_exists():
                self.files.configure(state="normal")
                self.help.lift()
                self.help.focus_set()

    # Automatically tries to find where the Tera Term application is located
    def change_location_event(self):
        lang = self.language_menu.get()
        translation = self.load_language()
        tera_term_path = TeraTermUI.find_ttermpro()
        if tera_term_path is not None:
            self.teraterm_exe_location = os.path.normpath(tera_term_path)
            directory, filename = os.path.split(self.teraterm_exe_location)
            self.teraterm_directory = directory
            minimum_required_version = "5.0.0.0"
            version = TeraTermUI.get_teraterm_version(self.teraterm_exe_location)
            version_parts = list(map(int, version.split(".")))
            compare_version_parts = list(map(int, minimum_required_version.split(".")))
            if version and version_parts >= compare_version_parts:
                ini_location = TeraTermUI.find_appdata_teraterm_ini()
                if ini_location and not os.path.isfile(os.path.join(self.teraterm_directory, "portable.ini")):
                    self.teraterm_config = ini_location
                else:
                    if (os.path.isfile(os.path.join(self.teraterm_directory, "TERATERM.ini"))
                            and self.has_write_permission()):
                        self.teraterm_config = os.path.join(self.teraterm_directory, "TERATERM.ini")
                    else:
                        self.teraterm5_first_boot = True
            else:
                if (os.path.isfile(os.path.join(self.teraterm_directory, "TERATERM.ini"))
                        and self.has_write_permission()):
                    self.teraterm_config = os.path.join(self.teraterm_directory, "TERATERM.ini")
                else:
                    self.teraterm5_first_boot = True
            row_exists = self.cursor_db.execute("SELECT 1 FROM user_config").fetchone()
            if not row_exists:
                self.cursor_db.execute(
                    "INSERT INTO user_config (directory, location, config) VALUES (?, ?, ?)",
                    (self.teraterm_directory, self.teraterm_exe_location, self.teraterm_config)
                )
            else:
                self.cursor_db.execute("UPDATE user_config SET directory=?", (self.teraterm_directory,))
                self.cursor_db.execute("UPDATE user_config SET location=?", (self.teraterm_exe_location,))
                self.cursor_db.execute("UPDATE user_config SET config=?", (self.teraterm_config,))
            self.connection_db.commit()
            self.changed_location = True
            self.edit_teraterm_ini(self.teraterm_config)
            self.after(100, self.show_success_message, 350, 265, translation["tera_term_success"])
            atexit.unregister(self.restore_teraterm_ini)
            atexit.register(self.restore_teraterm_ini, self.teraterm_config)
            if self.help is not None and self.help.winfo_exists():
                self.files.configure(state="normal")
        else:
            def handle_not_found():
                message_english = ("Tera Term executable was not found on the main drive.\n\n"
                                   "the application is probably not installed\nor it's located on another drive")
                message_spanish = ("No se encontró el ejecutable de Tera Term en la unidad principal.\n\n"
                                   "Probablemente no tiene la aplicación instalada\no está localizada en otra unidad")
                message = message_english if lang == "English" else message_spanish
                messagebox.showinfo("Tera Term", message)
                self.manually_change_location()

            self.after(0, handle_not_found)

    @staticmethod
    def find_teraterm_directory():
        import glob

        main_drive = os.environ["SystemRoot"][:3]
        base_paths = [
            os.path.join(main_drive, "Program Files (x86)"),
            os.path.join(main_drive, "Program Files")
        ]
        possible_dirs = []

        for base_path in base_paths:
            if not os.path.exists(base_path):
                continue
            try:
                with os.scandir(base_path) as entries:
                    for entry in entries:
                        if entry.is_dir() and entry.name.lower().startswith("teraterm"):
                            possible_dirs.append(entry.path)
            except PermissionError:
                continue

        teraterm5 = os.path.join(base_paths[0], "teraterm5")
        original_teraterm = os.path.join(base_paths[0], "teraterm")
        if teraterm5 in possible_dirs:
            return teraterm5
        elif original_teraterm in possible_dirs:
            return original_teraterm
        elif possible_dirs:
            return possible_dirs[0]

        full_search_path = os.path.join(main_drive, "teraterm*")
        full_possible_dirs = glob.glob(full_search_path, recursive=True)

        for directory in full_possible_dirs:
            if "teraterm5" in directory:
                return directory

        if full_possible_dirs:
            return full_possible_dirs[0]

        return None

    # Function that lets user select where their Tera Term application is located
    def manually_change_location(self):
        translation = self.load_language()
        filename = filedialog.askopenfilename(
            initialdir=os.environ["SystemRoot"][:3], title=translation["select_tera_term"],
            filetypes=(("Tera Term", "*ttermpro.exe"),))
        if re.search("ttermpro.exe", filename):
            self.teraterm_exe_location = os.path.normpath(filename)
            directory, filename = os.path.split(self.teraterm_exe_location)
            self.teraterm_directory = directory
            minimum_required_version = "5.0.0.0"
            version = TeraTermUI.get_teraterm_version(self.teraterm_exe_location)
            version_parts = list(map(int, version.split(".")))
            compare_version_parts = list(map(int, minimum_required_version.split(".")))
            if version and version_parts >= compare_version_parts:
                ini_location = TeraTermUI.find_appdata_teraterm_ini()
                if ini_location and not os.path.isfile(os.path.join(self.teraterm_directory, "portable.ini")):
                    self.teraterm_config = ini_location
                else:
                    if (os.path.isfile(os.path.join(self.teraterm_directory, "TERATERM.ini"))
                            and self.has_write_permission()):
                        self.teraterm_config = os.path.join(self.teraterm_directory, "TERATERM.ini")
                    else:
                        self.teraterm5_first_boot = True
            else:
                if (os.path.isfile(os.path.join(self.teraterm_directory, "TERATERM.ini"))
                        and self.has_write_permission()):
                    self.teraterm_config = os.path.join(self.teraterm_directory, "TERATERM.ini")
                else:
                    self.teraterm5_first_boot = True
            row_exists = self.cursor_db.execute("SELECT 1 FROM user_config").fetchone()
            if not row_exists:
                self.cursor_db.execute(
                    "INSERT INTO user_config (directory, location, config) VALUES (?, ?, ?)",
                    (self.teraterm_directory, self.teraterm_exe_location, self.teraterm_config)
                )
            else:
                self.cursor_db.execute("UPDATE user_config SET directory=?", (self.teraterm_directory,))
                self.cursor_db.execute("UPDATE user_config SET location=?", (self.teraterm_exe_location,))
                self.cursor_db.execute("UPDATE user_config SET config=?", (self.teraterm_config,))
            self.connection_db.commit()
            self.changed_location = True
            self.edit_teraterm_ini(self.teraterm_config)
            self.show_success_message(350, 265, translation["tera_term_success"])
            atexit.unregister(self.restore_teraterm_ini)
            atexit.register(self.restore_teraterm_ini, self.teraterm_config)
        if not re.search("ttermpro.exe", filename):
            if self.help is not None and self.help.winfo_exists():
                self.files.configure(state="normal")
                self.help.lift()
                self.help.focus_set()

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

    # Search function query for searching for either class code or name
    def search_classes(self, event):

        def normalize_string(s):
            s = unicodedata.normalize("NFD", s)
            s = s.encode("ascii", "ignore").decode("utf-8")
            return s.lower()

        def tokenize(s):
            return re.findall(r"\w+", normalize_string(s))

        def match_score(words, target):
            if words == target:
                return 2.0
            elif target.startswith(words):
                return 1.5
            elif words in target:
                return 1.2
            elif SequenceMatcher(None, words, target).ratio() >= 0.7:
                return 1.0
            return 0.0

        translation = self.load_language()
        self.class_list.delete(0, tk.END)
        search_term = self.search_box.get().strip()
        if not search_term:
            return

        normalized_search = normalize_string(search_term)
        search_words = tokenize(search_term)

        try:
            if self.courses_db_cache is None:
                self.courses_db_cache = self.cursor_db.execute("SELECT name, code FROM courses").fetchall()
                self.normalized_courses_cache = [(name, code, tokenize(name), tokenize(code))
                                                 for name, code in self.courses_db_cache]

            if normalized_search in ["all", "todo", "todos", "todas"]:
                results = sorted(self.courses_db_cache, key=lambda x: x[0])
            else:
                results = []
                for name, code, tokens_name, tokens_code in self.normalized_courses_cache:
                    total_score = 0
                    for word in search_words:
                        scores = [match_score(word, token) for token in tokens_name + tokens_code]
                        total_score += max(scores, default=0)
                    if total_score >= len(search_words):
                        results.append((total_score, name, code))

                results = sorted(results, key=lambda x: -x[0])
                results = [(name, code) for _, name, code in results]

            if not results:
                self.class_list.insert(tk.END, translation["no_results"])
                self.search_box.configure(border_color="#c30101")
            else:
                default_border_color = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"]
                self.search_box.configure(border_color=default_border_color)
                for name, code in results:
                    self.class_list.insert(tk.END, name)
        except sqlite3.Error as err:
            logging.error(f"Database search error: {err}")
            self.class_list.delete(0, tk.END)
            self.class_list.insert(tk.END, translation["no_results"])
            self.search_box.configure(border_color="#c30101")

    def show_class_code(self, event):
        translation = self.load_language()
        selection = self.class_list.curselection()
        if len(selection) == 0:
            return
        selected_class = self.class_list.get(selection[0])

        query = "SELECT code FROM courses WHERE name = ? OR code = ?"
        result = self.cursor_db.execute(query, (selected_class, selected_class)).fetchone()
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
        translation = self.load_language()
        self.help_frame = customtkinter.CTkScrollableFrame(self.help, width=475, height=280,
                                                           fg_color=("#e6e6e6", "#222222"))
        self.help_title = customtkinter.CTkLabel(self.help_frame, text=translation["help"],
                                                 font=customtkinter.CTkFont(size=20, weight="bold"))
        self.notice = customtkinter.CTkLabel(self.help_frame, text=translation["notice"],
                                             font=customtkinter.CTkFont(weight="bold", underline=True))
        self.searchbox_text = customtkinter.CTkLabel(self.help_frame, text=translation["searchbox_title"])
        self.search_box = CustomEntry(self.help_frame, self, lang, placeholder_text=translation["searchbox"])
        self.search_box.is_listbox_entry = True
        self.class_list = tk.Listbox(self.help_frame, width=38, bg="#0e95eb", fg="#333333", font=("Roboto", 12))
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
                                                      command=self.curriculums_link,
                                                      height=30, width=150)
        self.enrollment_error_text = customtkinter.CTkLabel(self.help_frame, text=translation["course_errors_title"],
                                                             font=customtkinter.CTkFont(weight="bold", size=15))
        self.enroll_error = [[translation["course_error_msg"], translation["course_error_explained"]],
                             ["INVALID COURSE ID", translation["invalid_course"]],
                             ["COURSE RESERVED", translation["course_reserved"]],
                             ["COURSE CLOSED", translation["course_closed"]],
                             ["CRS ALRDY TAKEN/PASSED", translation["course_taken"]],
                             ["Closed by Spec-Prog", translation["closed_spec"]],
                             ["Pre-Req", translation["pre_req"]],
                             ["Closed by College", translation["closed_college"]],
                             ["Closed by Major", translation["closed_major"]],
                             ["TERM MAX HRS EXCEEDED", translation["terms_max"]],
                             ["REQUIRED CO-REQUISITE", translation["req_co_requisite"]],
                             ["CO-REQUISITE MISSING", translation["co_requisite_missing"]],
                             ["ILLEGAL DROP-NOT ENR", translation["illegal_drop"]],
                             ["NEW COURSE, NO FUNCTION", translation["no_course"]],
                             ["PRESENTLY ENROLLED", translation["presently_enrolled"]],
                             ["PRESENTLY RECOMMENDED", translation["presently_recommended"]],
                             ["COURSE IN PROGRESS", translation["course_progress"]],
                             ["R/TC", translation["rtc"]]]
        self.terms_text = customtkinter.CTkLabel(self.help_frame, text=translation["terms_title"],
                                                 font=customtkinter.CTkFont(weight="bold", size=15))
        self.terms = self.get_last_five_terms()
        self.skip_auth_text = customtkinter.CTkLabel(self.help_frame, text=translation["skip_auth_text"])
        self.skip_auth_switch = customtkinter.CTkSwitch(self.help_frame, text=translation["skip_auth_switch"],
                                                        onvalue="on", offvalue="off", command=self.disable_enable_auth)
        self.files_text = customtkinter.CTkLabel(self.help_frame, text=translation["files_title"])
        self.files = CustomButton(master=self.help_frame, image=self.get_image("folder"),
                                  text=translation["files_button"], anchor="w", text_color=("gray10", "#DCE4EE"),
                                  command=self.change_location_auto_handler)
        self.delete_data_text = customtkinter.CTkLabel(self.help_frame, text=translation["del_data_title"])
        self.delete_data = CustomButton(master=self.help_frame, image=self.get_image("fix"), text=translation["del_data"],
                                        anchor="w", text_color=("gray10", "#DCE4EE"), command=self.del_user_data)
        self.disable_idle_text = customtkinter.CTkLabel(self.help_frame, text=translation["idle_title"])
        self.disable_idle = customtkinter.CTkSwitch(self.help_frame, text=translation["idle"], onvalue="on",
                                                    offvalue="off", command=self.disable_enable_idle)
        self.disable_audio_text = customtkinter.CTkLabel(self.help_frame, text=translation["audio_title"])
        self.disable_audio_tera = customtkinter.CTkSwitch(self.help_frame, text=translation["audio_tera"], onvalue="on",
                                                          offvalue="off", command=lambda:
                                                          self.disable_enable_audio("tera"))
        self.disable_audio_app = customtkinter.CTkSwitch(self.help_frame, text=translation["audio_app"], onvalue="on",
                                                         offvalue="off", command=lambda:
                                                         self.disable_enable_audio("app"))
        self.fix_text = customtkinter.CTkLabel(self.help_frame, text=translation["fix_title"])
        self.fix = CustomButton(master=self.help_frame, image=self.get_image("fix"), text=translation["fix"],
                                anchor="w", text_color=("gray10", "#DCE4EE"), command=self.fix_execution_event_handler)
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
            if windows_help:
                min_win = windows_help[0].isMinimized
                if min_win:
                    self.help.deiconify()
                self.help.lift()
                self.help.focus_set()
            return
        lang = self.language_menu.get()
        translation = self.load_language()
        self.destroy_tooltip()
        self.help_tooltip.hide()
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
        center_x += 70
        center_y -= 15
        monitor = TeraTermUI.get_monitor_bounds(main_window_x, main_window_y)
        monitor_x, monitor_y, monitor_width, monitor_height = monitor.x, monitor.y, monitor.width, monitor.height
        center_x = max(monitor_x, min(center_x, monitor_x + monitor_width - help_window_width))
        center_y = max(monitor_y, min(center_y, monitor_y + monitor_height - help_window_height))
        self.help.geometry(f"{help_window_width}x{help_window_height}+{center_x}+{center_y}")
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
        self.enrollment_error_text.pack(pady=(20, 0))
        self.enroll_error_table = CTkTable(self.help_frame, column=2, row=17, values=self.enroll_error,
                                           hover=False)
        self.enroll_error_table.pack(expand=True, fill="both", padx=20, pady=10)
        self.delete_data_text.pack()
        self.delete_data.pack(pady=5)
        if not self.ask_skip_auth:
            self.skip_auth_text.pack()
            self.skip_auth_switch.pack()
        self.files_text.pack()
        self.files.pack(pady=5)
        self.disable_idle_text.pack()
        self.disable_idle.pack()
        self.disable_audio_text.pack()
        self.disable_audio_tera.pack()
        self.disable_audio_app.pack()
        self.fix_text.pack()
        self.fix.pack(pady=5)
        idle = self.cursor_db.execute("SELECT idle FROM user_config").fetchone()
        audio_tera = self.cursor_db.execute("SELECT audio_tera FROM user_config").fetchone()
        audio_app = self.cursor_db.execute("SELECT audio_app FROM user_config").fetchone()
        skip_auth = self.cursor_db.execute("SELECT skip_auth FROM user_config").fetchone()
        if idle and idle[0] is not None:
            if idle[0] == "Disabled":
                self.disable_idle.select()
        if audio_tera and audio_tera[0] is not None or self.beep_off_default:
            if audio_tera[0] == "Disabled" or self.beep_off_default:
                self.disable_audio_tera.select()
        if audio_app and audio_app[0] is not None:
            if audio_app[0] == "Disabled":
                self.disable_audio_app.select()
        if skip_auth and skip_auth[0] is not None:
            if skip_auth[0] == "Yes":
                self.skip_auth_switch.select()
        self.search_box.lang = lang
        self.help.focus_set()
        self.help_tooltip.show()
        self.help_frame.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.help_frame.bind("<Button-2>", lambda event: self.help_frame.focus_set())
        self.help_frame.bind("<Button-3>", lambda event: self.help_frame.focus_set())
        self.disable_idle.bind("<space>", lambda event: self.keybind_disable_enable_idle())
        self.disable_audio_tera.bind("<space>", lambda event: self.keybind_disable_enable_audio("tera"))
        self.disable_audio_app.bind("<space>", lambda event: self.keybind_disable_enable_audio("app"))
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
        self.terms_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.enrollment_error_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.delete_data.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.skip_auth_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.files_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.disable_idle_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.disable_audio_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.fix_text.bind("<Button-1>", lambda event: self.help_frame.focus_set())
        self.curriculum.bind("<FocusIn>", lambda event: self.help_frame.scroll_to_widget(self.curriculum))
        self.skip_auth_switch.bind("<FocusIn>", lambda event: self.help_frame.scroll_to_widget(self.skip_auth_switch))
        self.disable_idle.bind("<FocusIn>", lambda event: self.help_frame.scroll_to_widget(self.disable_idle))
        self.disable_audio_tera.bind("<FocusIn>", lambda event: self.help_frame.scroll_to_widget(
            self.disable_audio_tera))
        self.disable_audio_app.bind("<FocusIn>", lambda event: self.help_frame.scroll_to_widget(
            self.disable_audio_tera))
        self.help.bind("<Control-space>", lambda event: self.help.focus_set())
        self.help.bind("<Up>", lambda event: None if self.is_listbox_focused() else self.help_scroll_up())
        self.help.bind("<Down>", lambda event: None if self.is_listbox_focused() else self.help_scroll_down())
        self.help.bind("<Home>", lambda event: None if self.is_listbox_focused() else self.help_move_top_scrollbar())
        self.help.bind("<End>", lambda event: None if self.is_listbox_focused() else self.help_move_bottom_scrollbar())
        self.help.protocol("WM_DELETE_WINDOW", self.on_help_window_close)
        self.help.bind("<Escape>", lambda event: self.on_help_window_close())

    def on_help_window_close(self):
        if self.help:
            bindings = self.help.bind()
            if isinstance(bindings, (list, tuple)):
                for binding in bindings:
                    self.help.unbind(binding)

        def clear_commands(widget_h):
            if widget_h and hasattr(widget_h, "children"):
                for child in list(widget_h.children.values()):
                    widget_name_h = str(child).lower()
                    if hasattr(child, "configure") and ("button" in widget_name_h or "menu" in widget_name_h):
                        child.configure(command=None)
                    clear_commands(child)

        def safe_destroy(widget_h):
            try:
                if hasattr(widget_h, "bindings"):
                    if isinstance(widget_h.bindings, (list, tuple)):
                        widget_h.bindings = []
                widget_h.destroy()
            except Exception:
                pass

        if self.help:
            clear_commands(self.help)

        if self.help_frame:
            children = list(self.help_frame.winfo_children())
            for widget in children:
                widget_name = str(widget).lower()
                if "ctktable" in widget_name:
                    if hasattr(widget, "_values"):
                        widget._values = None
                elif "entry" in widget_name or "listbox" in widget_name or "text" in widget_name:
                    if hasattr(widget, "delete"):
                        try:
                            widget.delete(0, "end")
                        except Exception:
                            pass
                elif hasattr(widget, "set"):
                    try:
                        widget.set("")
                    except Exception:
                        pass
                if hasattr(widget, "_image"):
                    widget._image = None

                safe_destroy(widget)

        if hasattr(self, "unload_image"):
            for img_name in ["folder", "fix"]:
                self.unload_image(img_name)
                if hasattr(self, f"_{img_name}_image"):
                    setattr(self, f"_{img_name}_image", None)

        attrs_to_clear = ["help_frame", "help_title", "notice", "search_box", "class_list", "curriculum", "terms_text",
                          "terms", "terms_table", "enrollment_error_text", "enroll_error_table", "enroll_error",
                          "delete_data_text", "delete_data" "terms_table", "files", "disable_idle", "disable_audio_val",
                          "fix", "skip_auth_switch", "terms"]
        for attr in attrs_to_clear:
            if hasattr(self, attr):
                obj = getattr(self, attr)
                if obj is not None and hasattr(obj, "destroy"):
                    safe_destroy(obj)
                setattr(self, attr, None)

        navigation_flags = ["move_slider_left_enabled", "move_slider_right_enabled",
                            "up_arrow_key_enabled", "down_arrow_key_enabled"]
        for flag in navigation_flags:
            setattr(self, flag, True)

        if self.help:
            safe_destroy(self.help)
            self.help = None

        gc.collect()

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
        url = "https://api.github.com/repos/Hanuwa/TeraTermUI/releases/latest"
        headers = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")}
        try:
            with requests.get(url, headers=headers, timeout=3) as response:
                if response.status_code != 200:
                    logging.error(f"Error fetching release information: {response.status_code}")
                    return None

                release_data = response.json()
                latest_version = release_data.get("tag_name")
                if latest_version and latest_version.startswith("v"):
                    latest_version = latest_version[1:]
                current_date = datetime.today().strftime("%Y-%m-%d")
                row_exists = self.cursor_db.execute("SELECT 1 FROM user_config").fetchone()
                if not row_exists:
                    self.cursor_db.execute("INSERT INTO user_config (update_date) VALUES (?)",
                                           (current_date,))
                else:
                    self.cursor_db.execute("UPDATE user_config SET update_date=?", (current_date,))

                return latest_version

        except requests.exceptions.RequestException as err:
            logging.error(f"Request failed: {err}")
            return None
        except Exception as err:
            logging.error(f"An error occurred while fetching the latest release: {err}")
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

    def play_sound(self, audio_file):
        if not self.muted_app:
            winsound.PlaySound(None, winsound.SND_PURGE)
            winsound.PlaySound(TeraTermUI.get_absolute_path(f"sounds/{audio_file}"),
                               winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NOWAIT)

    def set_beep_sound(self, file_path, disable_beep=True):
        if not self.can_edit:
            return

        if TeraTermUI.is_file_in_directory("ttermpro.exe", self.teraterm_directory):
            minimum_required_version = "5.0.0.0"
            version = TeraTermUI.get_teraterm_version(self.teraterm_exe_location)
            version_parts = list(map(int, version.split(".")))
            compare_version_parts = list(map(int, minimum_required_version.split(".")))
            if version and version_parts >= compare_version_parts:
                appdata_ini_path = TeraTermUI.find_appdata_teraterm_ini()
                if appdata_ini_path and not os.path.isfile(os.path.join(self.teraterm_directory, "portable.ini")):
                    file_path = appdata_ini_path
                elif (os.path.isfile(os.path.join(self.teraterm_directory, "TERATERM.ini"))
                      and self.has_write_permission()):
                    file_path = os.path.join(self.teraterm_directory, "TERATERM.ini")
                else:
                    self.teraterm5_first_boot = True
                    return

            backup_path = os.path.join(self.app_temp_dir, "TERATERM.ini.bak")
            if not os.path.exists(backup_path):
                backup_path = os.path.join(self.app_temp_dir, os.path.basename(file_path) + ".bak")
                try:
                    shutil.copy2(file_path, backup_path)
                except FileNotFoundError:
                    logging.error("Tera Term probably not installed or installed\n"
                                  " in a different location from the default")
            try:
                detected_encoding = TeraTermUI.detect_encoding(file_path) or "utf-8"
                with open(file_path, "r", encoding=detected_encoding) as file:
                    lines = file.readlines()
                beep_setting = "off" if disable_beep else "on"
                for index, line in enumerate(lines):
                    if line.startswith("Beep="):
                        lines[index] = f"Beep={beep_setting}\n"
                        self.muted_tera = disable_beep
                        if beep_setting == "on":
                            self.beep_off_default = False
                        else:
                            self.beep_off_default = True
                with open(file_path, "w", encoding=detected_encoding) as file:
                    file.writelines(lines)
            except FileNotFoundError:
                return
            except Exception as err:
                logging.error(f"Error occurred: {err}")
                logging.info("Restoring from backup...")
                shutil.copy2(backup_path, file_path)

    # Edits the font that tera term uses to "Lucida Console" to mitigate the chance of the OCR mistaking words
    def edit_teraterm_ini(self, file_path):
        if TeraTermUI.is_file_in_directory("ttermpro.exe", self.teraterm_directory):
            minimum_required_version = "5.0.0.0"
            version = TeraTermUI.get_teraterm_version(self.teraterm_exe_location)
            version_parts = list(map(int, version.split(".")))
            compare_version_parts = list(map(int, minimum_required_version.split(".")))
            if version and version_parts >= compare_version_parts:
                appdata_ini_path = TeraTermUI.find_appdata_teraterm_ini()
                if appdata_ini_path and not os.path.isfile(os.path.join(self.teraterm_directory, "portable.ini")):
                    file_path = appdata_ini_path
                elif (os.path.isfile(os.path.join(self.teraterm_directory, "TERATERM.ini"))
                      and self.has_write_permission()):
                    file_path = os.path.join(self.teraterm_directory, "TERATERM.ini")
                else:
                    self.teraterm5_first_boot = True
                    return

            backup_path = os.path.join(self.app_temp_dir, "TERATERM.ini.bak")
            if not os.path.exists(backup_path):
                backup_path = os.path.join(self.app_temp_dir, os.path.basename(file_path) + ".bak")
                try:
                    shutil.copy2(file_path, backup_path)
                except FileNotFoundError:
                    logging.error("Tera Term probably not installed or installed\n"
                                  " in a different location from the default")

            known_hosts_path = os.path.join(os.path.dirname(file_path), "ssh_known_hosts")
            if os.path.exists(known_hosts_path):
                try:
                    detected_encoding = TeraTermUI.detect_encoding(known_hosts_path) or "utf-8"
                    with open(known_hosts_path, "r", encoding=detected_encoding) as file:
                        for line in file:
                            parts = line.strip().split()
                            if not parts or parts[0].startswith("#"):
                                continue
                            self.host_entry_saved = parts[0]
                            break
                except Exception as err:
                    self.log_error()
                    logging.error(f"Error reading ssh_known_hosts file: {err}")

            try:
                detected_encoding = TeraTermUI.detect_encoding(file_path) or "utf-8"
                with open(file_path, "r", encoding=detected_encoding) as file:
                    lines = file.readlines()
                for index, line in enumerate(lines):
                    if line.startswith("VTFont="):
                        lines[index] = "VTFont=Lucida Console,0,-12,255\n"
                    if line.startswith("VTColor=") and not line.startswith(";"):
                        current_value = line.strip().split("=")[1]
                        if current_value != "255,255,255,0,0,0":
                            lines[index] = "VTColor=255,255,255,0,0,0\n"
                    geometry = self.geometry()
                    _, x_pos, y_pos = geometry.split("+")
                    if line.startswith("VTPos="):
                        lines[index] = f"VTPos={int(x_pos)},{int(y_pos)}\n"
                    if line.startswith("TEKPos="):
                        lines[index] = f"TEKPos={int(x_pos)},{int(y_pos)}\n"
                    if line.startswith("TermIsWin="):
                        current_value = line.strip().split("=")[1]
                        if current_value != "on":
                            lines[index] = "TermIsWin=on\n"
                    if line.startswith("AuthBanner="):
                        current_value = line.strip().split("=")[1]
                        if current_value not in ["0", "1"]:
                            lines[index] = "AuthBanner=1\n"
                    if line.startswith("Beep="):
                        current_beep_value = line.strip().split("=", 1)[1]
                        if current_beep_value == "off":
                            self.beep_off_default = True
                        else:
                            self.beep_off_default = False
                    self.can_edit = True
                with open(file_path, "w", encoding=detected_encoding) as file:
                    file.writelines(lines)
                self.teraterm_not_found = False
                self.download = False
            except FileNotFoundError:
                return
            except Exception as err:
                logging.error(f"Error occurred: {err}")
                logging.info("Restoring from backup...")
                shutil.copy2(backup_path, file_path)
        else:
            self.teraterm_not_found = True

    # Restores the original font option the user had
    def restore_teraterm_ini(self, file_path):
        if not self.can_edit:
            return

        if TeraTermUI.is_file_in_directory("ttermpro.exe", self.teraterm_directory):
            minimum_required_version = "5.0.0.0"
            version = TeraTermUI.get_teraterm_version(self.teraterm_exe_location)
            version_parts = list(map(int, version.split(".")))
            compare_version_parts = list(map(int, minimum_required_version.split(".")))
            if version and version_parts >= compare_version_parts:
                appdata_ini_path = TeraTermUI.find_appdata_teraterm_ini()
                if appdata_ini_path and not os.path.isfile(os.path.join(self.teraterm_directory, "portable.ini")):
                    file_path = appdata_ini_path
                elif (os.path.isfile(os.path.join(self.teraterm_directory, "TERATERM.ini"))
                      and self.has_write_permission()):
                    file_path = os.path.join(self.teraterm_directory, "TERATERM.ini")
                else:
                    self.teraterm5_first_boot = True
                    return

        backup_path = os.path.join(self.app_temp_dir, "TERATERM.ini.bak")
        try:
            if not os.path.exists(backup_path):
                logging.warning(f"Backup file not found at {backup_path}")
                return
            shutil.copy2(backup_path, file_path)

            if self.disable_audio_tera is not None and self.disable_audio_tera.get() == "on":
                detected_encoding = TeraTermUI.detect_encoding(file_path) or "utf-8"
                with open(file_path, "r", encoding=detected_encoding) as file:
                    lines = file.readlines()
                for index, line in enumerate(lines):
                    if line.startswith("Beep=") and line.strip() != "Beep=off":
                        lines[index] = "Beep=off\n"
                with open(file_path, "w", encoding=detected_encoding) as file:
                    file.writelines(lines)
        except FileNotFoundError:
            logging.warning(f"File or backup not found: {file_path} or {backup_path}")
        except IOError as err:
            logging.error(f"Error occurred while restoring: {err}")
            logging.info("Restoring from backup...")
            try:
                shutil.copy2(backup_path, file_path)
            except FileNotFoundError:
                logging.error(f"The backup file at {backup_path} was not found")

    # When the user performs an action to do something in tera term it destroys windows that might get in the way
    def destroy_windows(self):
        if self.error is not None and self.error.winfo_exists():
            self.error.destroy()
            self.error = None
            gc.collect()
        if self.success is not None and self.success.winfo_exists():
            self.success.destroy()
            self.success = None
            gc.collect()
        if self.information is not None and self.information.winfo_exists():
            self.information.destroy()
            self.information = None
            gc.collect()

    def get_image(self, image_name):
        if image_name not in self.images:
            logging.error(f"Unknown image name: {image_name}")
            return None

        if image_name not in self.loaded_images:
            try:
                image_data = self.images[image_name]
                with Image.open(TeraTermUI.get_absolute_path(image_data["path"])) as img:
                    if img.mode not in ("RGB", "RGBA"):
                        img = img.convert("RGBA" if img.mode == "P" and "transparency" in img.info else "RGB")
                    if img.size != image_data["size"]:
                        img = img.resize(image_data["size"], Image.Resampling.LANCZOS)
                    self.loaded_images[image_name] = customtkinter.CTkImage(light_image=img, size=image_data["size"])
            except Exception as err:
                logging.error(f"Failed to load image {image_name}: {err}")
                return None

        return self.loaded_images.get(image_name)

    def unload_image(self, image_name):
        if image_name in self.loaded_images:
            del self.loaded_images[image_name]

    # checks if there is no problems with the information in the entries
    def check_format(self):
        translation = self.load_language()
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
            elif not re.fullmatch("^[A-Z]{4}[0-9]{4}$", classes):
                error_msg_short = translation["multiple_class_format_error"]
                error_entries.append(self.m_classes_entry[i])
                break
            elif not re.fullmatch("^[A-Z0-9]{3}$", sections):
                error_msg_short = translation["multiple_section_format_error"]
                error_entries.append(self.m_section_entry[i])
                break
            if choices in ["Register", "Registra"]:
                if sections in self.classes_status:
                    status_entry = self.classes_status[sections]
                    if (status_entry["status"] == "ENROLLED" and status_entry["classes"] == classes and
                            status_entry["semester"] == semester):
                        error_msg_long = translation["multiple_already_enrolled"]
                        break
            elif choices in ["Drop", "Baja"]:
                if sections in self.classes_status:
                    status_entry = self.classes_status[sections]
                    if (status_entry["status"] == "DROPPED" and status_entry["classes"] == classes and
                            status_entry["semester"] == semester):
                        error_msg_long = translation["multiple_already_dropped"]
                        break

        if not re.fullmatch("^[A-Z][0-9]{2}$", semester) and semester != curr_sem:
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
            if self.auto_enroll_flag:
                self.auto_enroll_flag = False
                self.after(125, self.auto_enroll.deselect)
            return False
        elif error_msg_medium:
            self.after(100, self.show_error_message, 355, 240, error_msg_medium)
            if self.auto_enroll_flag:
                self.auto_enroll_flag = False
                self.after(125, self.auto_enroll.deselect)
            return False
        elif error_msg_long:
            self.after(100, self.show_error_message, 390, 245, error_msg_long)
            if self.auto_enroll_flag:
                self.auto_enroll_flag = False
                self.after(125, self.auto_enroll.deselect)
            return False

        return True


class CustomButton(customtkinter.CTkButton):
    __slots__ = ("master", "command", "text", "image", "is_pressed", "click_command", "bindings")

    def __init__(self, master=None, command=None, **kwargs):
        super().__init__(master, cursor="hand2", **kwargs)
        self.text = kwargs.pop("text", None)
        self.image = kwargs.pop("image", None)

        self.is_pressed = False
        self.click_command = command
        self.bindings = []

        self.setup_bindings()

        if self.image and not self.text:
            self.configure(image=self.image)

    def setup_bindings(self):
        bindings = [("<ButtonPress-1>", self.on_button_down), ("<ButtonRelease-1>", self.on_button_up),
                    ("<Enter>", self.on_enter), ("<Motion>", self.on_enter), ("<Leave>", self.on_leave),
                    ("<B1-Motion>", self.on_motion)]
        for event, callback in bindings:
            bind_id = self.bind(event, callback)
            self.bindings.append((event, bind_id))

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
        if hasattr(self, "bindings"):
            for event, bind_id in self.bindings:
                try:
                    self.unbind(event, bind_id)
                except Exception as err:
                    logging.error(f"Error unbinding event {event}: {err}")
        self.text = None
        self.image = None
        self.is_pressed = None
        self.click_command = None
        self.bindings = None
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
    __slots__ = ("master", "teraterm_ui_instance", "enable_autoscroll", "read_only", "lang", "max_length",
                 "disabled_autoscroll", "after_id", "auto_scroll", "selected_text", "saved_cursor_position",
                 "y_scrollbar_bindings", "x_scrollbar_bindings", "context_menu", "_undo_stack", "_redo_stack",
                 "bindings")

    def __init__(self, master, teraterm_ui_instance, enable_autoscroll=True,
                 read_only=False, lang=None, max_length=10000, **kwargs):
        if "cursor" not in customtkinter.CTkTextbox._valid_tk_text_attributes:
            customtkinter.CTkTextbox._valid_tk_text_attributes.add("cursor")
        super().__init__(master, cursor="xterm", **kwargs)
        self.teraterm_ui = weakref.proxy(teraterm_ui_instance)

        self.auto_scroll = enable_autoscroll
        self.lang = lang
        self.read_only = read_only
        self.max_length = max_length
        self.disabled_autoscroll = False
        self.after_id = None
        self.selected_text = False
        self.saved_cursor_position = None
        self.y_scrollbar_bindings = None
        self.x_scrollbar_bindings = None
        self.context_menu = None

        initial_state = self.get("1.0", "end-1c")
        initial_cursor = self.index(tk.INSERT)
        self._undo_stack = deque([(initial_state, initial_cursor)], maxlen=500)
        self._redo_stack = deque(maxlen=500)

        self.bindings = []
        self.setup_bindings()

        if self.auto_scroll:
            self.update_text()

    def setup_bindings(self):
        bindings = [("<Button-1>", self.stop_autoscroll), ("<MouseWheel>", self.stop_autoscroll),
                    ("<FocusIn>", self.disable_slider_keys), ("<FocusOut>", self.enable_slider_keys),
                    ("<Enter>", self.on_enter), ("<Motion>", self.on_motion), ("<Leave>", self.on_leave),
                    ("<Control-z>", self.undo), ("<Control-Z>", self.undo), ("<Control-y>", self.redo),
                    ("<Control-Y>", self.redo), ("<Control-v>", self.custom_paste), ("<Control-V>", self.custom_paste),
                    ("<Control-x>", self.custom_cut), ("<Control-X>", self.custom_cut),
                    ("<Control-a>", self.select_all), ("<Control-A>", self.select_all),
                    ("<Button-2>", self.custom_middle_mouse), ("<Button-3>", self.show_menu),
                    ("<KeyRelease>", self.update_undo_stack)]
        if self.read_only:
            bindings.extend([("<Up>", self.scroll_more_up), ("<Down>", self.scroll_more_down),
                             ("<Left>", self.teraterm_ui.move_slider_left),
                             ("<Right>", self.teraterm_ui.move_slider_right)])
        if hasattr(self, "_y_scrollbar"):
            self.y_scrollbar_bindings = [("<Button-1>", self.stop_autoscroll), ("<B1-Motion>", self.stop_autoscroll)]
            for event, callback in self.y_scrollbar_bindings:
                self._y_scrollbar.bind(event, callback)
        if hasattr(self, "_x_scrollbar"):
            self.x_scrollbar_bindings = [("<Button-1>", self.stop_autoscroll), ("<B1-Motion>", self.stop_autoscroll)]
            for event, callback in self.x_scrollbar_bindings:
                self._x_scrollbar.bind(event, callback)
        for event, callback in bindings:
            bind_id = self.bind(event, callback)
            self.bindings.append((event, bind_id))

    def disable_slider_keys(self, event=None):
        if self.tag_ranges(tk.SEL) and self.selected_text:
            self.tag_remove(tk.SEL, "1.0", tk.END)
            if self.lang == "English" and not self.read_only:
                self.context_menu.entryconfigure(3, label="Select All")
            elif self.lang == "Español" and not self.read_only:
                self.context_menu.entryconfigure(3, label="Seleccionar Todo")

            if self.lang == "English" and self.read_only:
                self.context_menu.entryconfigure(1, label="Select All")
            elif self.lang == "Español" and self.read_only:
                self.context_menu.entryconfigure(1, label="Seleccionar Todo")

        if not self.read_only:
            self.teraterm_ui.move_slider_left_enabled = False
            self.teraterm_ui.move_slider_right_enabled = False
        self.teraterm_ui.up_arrow_key_enabled = False
        self.teraterm_ui.down_arrow_key_enabled = False

    def enable_slider_keys(self, event=None):
        if self.tag_ranges(tk.SEL) and not self.selected_text:
            self.tag_remove(tk.SEL, "1.0", tk.END)

        self.selected_text = False
        self.teraterm_ui.move_slider_left_enabled = True
        self.teraterm_ui.move_slider_right_enabled = True
        self.teraterm_ui.up_arrow_key_enabled = True
        self.teraterm_ui.down_arrow_key_enabled = True

    def on_enter(self, event):
        if self.find_context_menu():
            self.configure(cursor="arrow")
        else:
            self.configure(cursor="xterm")
        self._canvas.configure(cursor="hand2")

    def on_motion(self, event):
        current_cursor = str(self.cget("cursor"))
        if self.find_context_menu():
            if current_cursor != "arrow":
                self.configure(cursor="arrow")
        elif current_cursor:
            self.configure(cursor="xterm")

    def on_leave(self, event):
        if self.find_context_menu():
            self.configure(cursor="xterm")
        else:
            self.configure(cursor="arrow")
        self._canvas.configure(cursor="arrow")

    def update_text(self):
        if self.after_id:
            self.after_cancel(self.after_id)

        if self.auto_scroll:
            _, yview_fraction = self.yview()
            if yview_fraction >= 1.0:
                self.yview_moveto(0)
            else:
                self.yview_scroll(1, "units")  # Scroll down 1 unit
            self.after_id = self.after(8000, self.update_text)

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
        cursor_position = self.index(tk.INSERT)
        if current_text != self._undo_stack[-1][0]:
            self._undo_stack.append((current_text, cursor_position))
            self._redo_stack.clear()

    def undo(self, event=None):
        self.focus_set()
        if len(self._undo_stack) > 1:
            # Remove the current state from the undo stack and add it to the redo stack
            current_text, current_cursor = self._undo_stack.pop()
            self._redo_stack.append((current_text, current_cursor))

            # Get the previous state from the undo stack
            previous_text, previous_cursor = self._undo_stack[-1]

            # Apply the previous text state
            self.delete("1.0", tk.END)
            self.insert("1.0", previous_text)
            self.mark_set(tk.INSERT, previous_cursor)
            self.see(previous_cursor)

    def redo(self, event=None):
        self.focus_set()
        if self._redo_stack:
            # Get the next state from the redo stack and add it to the undo stack
            next_text, next_cursor = self._redo_stack.pop()
            self._undo_stack.append((next_text, next_cursor))

            # Apply the next text state
            self.delete("1.0", tk.END)
            self.insert("1.0", next_text)
            self.mark_set(tk.INSERT, next_cursor)
            self.see(next_cursor)

    @staticmethod
    def find_context_menu():
        import win32process

        try:
            windows = []
            win32gui.EnumWindows(lambda hwnd_win, results: results.append(hwnd_win), windows)
            for hwnd in windows:
                class_name = win32gui.GetClassName(hwnd)
                if class_name == "#32768":
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid == os.getpid():
                        return hwnd
            return None
        except Exception as err:
            logging.warning(f"Unexpected error in find_context_menu: {err}")
        return None

    def custom_middle_mouse(self, event=None):
        if self.find_context_menu():
            return "break"
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
        self.selected_text = True

        if self.context_menu is None:
            self.context_menu = tk.Menu(self, tearoff=0, font=("Arial", 10), relief="flat", background="gray40",
                                        fg="snow")
            if not self.read_only:
                self.context_menu.add_command(label="Cut", command=self.cut)
                self.context_menu.add_command(label="Copy", command=self.copy)
                self.context_menu.add_command(label="Paste", command=self.paste)
                self.context_menu.add_command(label="Select All", command=self.select_all)
                self.context_menu.add_command(label="Undo", command=self.undo)
                self.context_menu.add_command(label="Redo", command=self.redo)
            else:
                self.context_menu.add_command(label="Copy", command=self.copy)
                self.context_menu.add_command(label="Select All", command=self.select_all)

        if self.lang == "English" and not self.read_only:
            self.context_menu.entryconfigure(0, label="Cut")
            self.context_menu.entryconfigure(1, label="Copy")
            self.context_menu.entryconfigure(2, label="Paste")
            self.context_menu.entryconfigure(3, label="Select All")
            self.context_menu.entryconfigure(4, label="Undo")
            self.context_menu.entryconfigure(5, label="Redo")
        elif self.lang == "Español" and not self.read_only:
            self.context_menu.entryconfigure(0, label="Cortar")
            self.context_menu.entryconfigure(1, label="Copiar")
            self.context_menu.entryconfigure(2, label="Pegar")
            self.context_menu.entryconfigure(3, label="Seleccionar Todo")
            self.context_menu.entryconfigure(4, label="Deshacer")
            self.context_menu.entryconfigure(5, label="Rehacer")

        if self.lang == "English" and self.read_only:
            self.context_menu.entryconfigure(0, label="Copy")
            self.context_menu.entryconfigure(1, label="Select All")
        elif self.lang == "Español" and self.read_only:
            self.context_menu.entryconfigure(0, label="Copiar")
            self.context_menu.entryconfigure(1, label="Seleccionar Todo")

        if self.tag_ranges(tk.SEL):
            if self.lang == "English":
                idx = 3 if not self.read_only else 1
                self.context_menu.entryconfigure(idx, label="Deselect All")
            elif self.lang == "Español":
                idx = 3 if not self.read_only else 1
                self.context_menu.entryconfigure(idx, label="Deseleccionar Todo")
        else:
            if self.lang == "English":
                idx = 3 if not self.read_only else 1
                self.context_menu.entryconfigure(idx, label="Select All")
            elif self.lang == "Español":
                idx = 3 if not self.read_only else 1
                self.context_menu.entryconfigure(idx, label="Seleccionar Todo")

        self.context_menu.post(event.x_root, event.y_root)
        self.context_menu.bind("<Unmap>", lambda evt: self.configure(cursor="xterm"))

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

            # Save the current state to the undo stack before deletion
            current_text = self.get("1.0", "end-1c")
            current_cursor = self.index(tk.INSERT)
            self._undo_stack.append((current_text, current_cursor))
            self._redo_stack.clear()

            self.delete(tk.SEL_FIRST, tk.SEL_LAST)

            new_text = self.get("1.0", "end-1c")
            new_cursor = self.index(tk.INSERT)
            self._undo_stack.append((new_text, new_cursor))
            self._redo_stack.clear()
            self.see(tk.INSERT)
        except tk.TclError:
            logging.info("No text selected to cut")

    def copy(self):
        self.stop_autoscroll(event=None)
        if not self.tag_ranges(tk.SEL):
            self.tag_add(tk.SEL, "1.0", tk.END)
        try:
            selected_text = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.update_idletasks()
        except tk.TclError:
            logging.info("No text selected to copy")

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
            clipboard_text = pyperclip.paste()
            max_paste_length = self.max_length  # Maximum length for pasted content
            if len(clipboard_text) > max_paste_length:
                clipboard_text = clipboard_text[:max_paste_length]
                logging.info("Pasted content truncated to maximum length")

            # Save the current state to the undo stack before pasting
            current_text = self.get("1.0", "end-1c")
            current_cursor = self.index(tk.INSERT)
            self._undo_stack.append((current_text, current_cursor))
            self._redo_stack.clear()

            # Handle any selected text replacement
            try:
                start_index = self.index(tk.SEL_FIRST)
                end_index = self.index(tk.SEL_LAST)
                self.delete(start_index, end_index)
            except tk.TclError:
                pass  # Nothing selected to delete

            self.insert(tk.INSERT, clipboard_text)
            new_cursor = self.index(tk.INSERT)
            self._undo_stack.append((self.get("1.0", "end-1c"), new_cursor))
            self._redo_stack.clear()
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
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        if hasattr(self, "bindings"):
            for event, bind_id in self.bindings:
                self.unbind(event, bind_id)
        if hasattr(self, "_y_scrollbar"):
            self._y_scrollbar.unbind("<Button-1>")
            self._y_scrollbar.unbind("<B1-Motion>")
        if hasattr(self, "_x_scrollbar"):
            self._x_scrollbar.unbind("<Button-1>")
            self._x_scrollbar.unbind("<B1-Motion>")
        if self.read_only:
            self.unbind("<Up>")
            self.unbind("<Down>")
            self.unbind("<Left>")
            self.unbind("<Right>")

        if hasattr(self, "context_menu") and self.context_menu:
            last_index = self.context_menu.index("end")
            if last_index is not None:
                for i in range(last_index + 1):
                    self.context_menu.entryconfigure(i, command=None)
            self.context_menu.destroy()
        if hasattr(self, "_undo_stack"):
            self._undo_stack.clear()
        if hasattr(self, "_redo_stack"):
            self._redo_stack.clear()

        self.teraterm_ui = None
        self.context_menu = None
        self._undo_stack = None
        self._redo_stack = None
        self.bindings = None
        self.auto_scroll = None
        self.lang = None
        self.read_only = None
        self.disabled_autoscroll = None
        self.selected_text = None
        self.saved_cursor_position = None
        super().destroy()


class CustomEntry(customtkinter.CTkEntry):
    __slots__ = ("master", "teraterm_ui", "lang", "max_length", "is_listbox_entry", "selected_text", "border_color",
                 "focus_out_bind_id", "context_menu", "bindings", "_undo_stack", "_redo_stack")

    def __init__(self, master, teraterm_ui_instance, lang=None, max_length=250, *args, **kwargs):
        if "cursor" not in customtkinter.CTkEntry._valid_tk_entry_attributes:
            customtkinter.CTkEntry._valid_tk_entry_attributes.add("cursor")
        super().__init__(master, cursor="xterm", *args, **kwargs)
        self.teraterm_ui = weakref.proxy(teraterm_ui_instance)

        initial_state = self.get()
        initial_cursor = self.index(tk.INSERT)
        self.root = self.winfo_toplevel()
        self._undo_stack = deque([(initial_state, initial_cursor)], maxlen=100)
        self._redo_stack = deque(maxlen=100)

        self.max_length = max_length
        self.lang = lang
        self.is_listbox_entry = False
        self.selected_text = False
        self.border_color = None
        self.focus_out_bind_id = None
        self.context_menu = None

        self.bindings = []
        self.setup_bindings()

    def setup_bindings(self):
        self.focus_out_bind_id = self.root.bind("<FocusOut>", self._on_window_focus_out, add="+")
        bindings = [("<FocusIn>", self.disable_slider_keys), ("<FocusOut>", self.enable_slider_keys),
                    ("<Enter>", self.on_enter), ("<Motion>", self.on_motion), ("<Leave>", self.on_leave),
                    ("<Control-z>", self.undo), ("<Control-Z>", self.undo), ("<Control-y>", self.redo),
                    ("<Control-Y>", self.redo), ("<Control-v>", self.custom_paste), ("<Control-V>", self.custom_paste),
                    ("<Control-x>", self.custom_cut), ("<Control-X>", self.custom_cut),
                    ("<Control-a>", self.select_all), ("<Control-A>", self.select_all),
                    ("<KeyRelease>", self.update_undo_stack), ("<Button-2>", self.custom_middle_mouse),
                    ("<Button-3>", self.show_menu)]
        for event, callback in bindings:
            bind_id = self.bind(event, callback)
            self.bindings.append((event, bind_id))

    def _on_window_focus_out(self, event=None):
        if self.get() == "" or self.get().isspace():
            self._activate_placeholder()

    def disable_slider_keys(self, event=None):
        if self.cget("border_color") == "#c30101" or self.cget("border_color") == "#228B22":
            if self.border_color is None:
                self.border_color = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"]
            self.configure(border_color=self.border_color)

        if self.select_present() and self.selected_text:
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
        if self.select_present() and not self.selected_text:
            self.select_clear()

        self.selected_text = False
        self.teraterm_ui.move_slider_left_enabled = True
        self.teraterm_ui.move_slider_right_enabled = True
        self.teraterm_ui.up_arrow_key_enabled = True
        self.teraterm_ui.down_arrow_key_enabled = True

    def on_enter(self, event):
        if self.find_context_menu():
            self._entry.configure(cursor="arrow")
        else:
            self._entry.configure(cursor="xterm")
        self._canvas.configure(cursor="hand2")

    def on_motion(self, event):
        if self.find_context_menu():
            self._entry.configure(cursor="arrow")
        else:
            self._entry.configure(cursor="xterm")

    def on_leave(self, event):
        if self.find_context_menu():
            self._entry.configure(cursor="xterm")
        else:
            self._entry.configure(cursor="arrow")
        self._canvas.configure(cursor="arrow")

    def update_undo_stack(self, event=None):
        current_text = self.get()
        cursor_position = self.index(tk.INSERT)
        if current_text != self._undo_stack[-1][0]:
            self._undo_stack.append((current_text, cursor_position))
            self._redo_stack.clear()

    def undo(self, event=None):
        self.focus_set()
        if len(self._undo_stack) > 1:
            # Remove the current state from the undo stack and add it to the redo stack
            current_text, current_cursor = self._undo_stack.pop()
            self._redo_stack.append((current_text, current_cursor))

            # Get the previous state from the undo stack
            previous_text, previous_cursor = self._undo_stack[-1]

            # Apply the previous text state
            self.delete(0, "end")
            self.insert(0, previous_text, enforce_length_check=False)
            self.icursor(previous_cursor)

            # Reset border color if needed
            if self.cget("border_color") in ["#c30101", "#228B22"]:
                default_color = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"]
                self.configure(border_color=default_color)

            # Adjust the view position
            self.xview_moveto(previous_cursor / len(previous_text) if len(previous_text) > 0 else 0)

            if self.is_listbox_entry:
                self.update_listbox()

    def redo(self, event=None):
        self.focus_set()
        if self._redo_stack:
            # Get the next state from the redo stack and add it to the undo stack
            next_text, next_cursor = self._redo_stack.pop()
            self._undo_stack.append((next_text, next_cursor))

            # Apply the next text state
            self.delete(0, "end")
            self.insert(0, next_text, enforce_length_check=False)
            self.icursor(next_cursor)

            # Reset border color if needed
            if self.cget("border_color") in ["#c30101", "#228B22"]:
                default_color = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"]
                self.configure(border_color=default_color)

            # Adjust the view position
            self.xview_moveto(next_cursor / len(next_text) if len(next_text) > 0 else 0)

            if self.is_listbox_entry:
                self.update_listbox()

    @staticmethod
    def find_context_menu():
        import win32process

        try:
            windows = []
            win32gui.EnumWindows(lambda hwnd_win, results: results.append(hwnd_win), windows)
            for hwnd in windows:
                class_name = win32gui.GetClassName(hwnd)
                if class_name == "#32768":
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid == os.getpid():
                        return hwnd
            return None
        except Exception as err:
            logging.warning(f"Unexpected error in find_context_menu: {err}")
        return None

    def custom_middle_mouse(self, event=None):
        if self.find_context_menu() or (self.get() == "" and not self._placeholder_text_active):
            return "break"
        if self.select_present():
            char_index = self.index("@%d" % event.x)
            self.icursor(char_index)
            self.select_clear()
            return "break"

    def show_menu(self, event):
        if self.cget("state") == "disabled":
            return

        self.focus_set()
        self.selected_text = True

        if self.context_menu is None:
            self.context_menu = tk.Menu(self, tearoff=0, font=("Arial", 10), relief="flat", background="gray40",
                                        fg="snow")
            menu_items = [("Cut", lambda: self.cut()), ("Copy", lambda: self.copy()), ("Paste", lambda: self.paste()),
                          ("Select All", lambda: self.select_all()), ("Undo", lambda: self.undo()),
                          ("Redo", lambda: self.redo())]
            for label, command in menu_items:
                self.context_menu.add_command(label=label, command=command)

        if self.lang == "English":
            self.context_menu.entryconfigure(0, label="Cut")
            self.context_menu.entryconfigure(1, label="Copy")
            self.context_menu.entryconfigure(2, label="Paste")
            self.context_menu.entryconfigure(3, label="Select All")
            self.context_menu.entryconfigure(4, label="Undo")
            self.context_menu.entryconfigure(5, label="Redo")
        elif self.lang == "Español":
            self.context_menu.entryconfigure(0, label="Cortar")
            self.context_menu.entryconfigure(1, label="Copiar")
            self.context_menu.entryconfigure(2, label="Pegar")
            self.context_menu.entryconfigure(3, label="Seleccionar Todo")
            self.context_menu.entryconfigure(4, label="Deshacer")
            self.context_menu.entryconfigure(5, label="Rehacer")

        if self.select_present():
            if self.lang == "English":
                self.context_menu.entryconfigure(3, label="Deselect All")
            elif self.lang == "Español":
                self.context_menu.entryconfigure(3, label="Deseleccionar Todo")
        else:
            if self.lang == "English":
                self.context_menu.entryconfigure(3, label="Select All")
            elif self.lang == "Español":
                self.context_menu.entryconfigure(3, label="Seleccionar Todo")

        self.context_menu.post(event.x_root, event.y_root)
        self.context_menu.bind("<Unmap>", lambda evt: self.configure(cursor="xterm"))

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

            # Save current state to undo stack before deletion
            current_text = self.get()
            current_cursor = self.index(tk.INSERT)
            self._undo_stack.append((current_text, current_cursor))
            self._redo_stack.clear()

            self.delete(tk.SEL_FIRST, tk.SEL_LAST)

            if self.is_listbox_entry:
                self.update_listbox()
        except tk.TclError:
            logging.info("No text selected to cut")

    def copy(self):
        self.focus_set()
        if not self.select_present():
            self.select_range(0, "end")
        try:
            selected_text = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.update_idletasks()
        except tk.TclError:
            logging.info("No text selected to copy")

    def custom_paste(self, event=None):
        self.paste()
        return "break"

    def paste(self, event=None):
        self.focus_set()
        try:
            clipboard_text = pyperclip.paste()
            max_paste_length = self.max_length  # Set a limit for the max paste length
            if len(clipboard_text) > max_paste_length:
                clipboard_text = clipboard_text[:max_paste_length]  # Truncate to max length
                logging.info("Pasted content truncated to maximum length")

                # Save the current state to the undo stack before the paste operation
                current_text = self.get()
                current_cursor = self.index(tk.INSERT)
                self._undo_stack.append((current_text, current_cursor))
                self._redo_stack.clear()

            insert_index = self.index(tk.INSERT)
            try:
                start_index = self.index(tk.SEL_FIRST)
                end_index = self.index(tk.SEL_LAST)
                self.delete(start_index, end_index)
                insert_index = start_index
            except tk.TclError:
                pass  # Nothing selected, which is fine

            space_left = self.max_length - len(self.get())
            if len(clipboard_text) > space_left:
                clipboard_text = clipboard_text[:space_left]

            self.insert(insert_index, clipboard_text)

            # Move the cursor to the end of the pasted content
            new_cursor_position = insert_index + len(clipboard_text)
            self.icursor(new_cursor_position)
            self.xview_moveto(new_cursor_position / len(self.get()) if len(self.get()) > 0 else 0)

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

    def insert(self, index, string, enforce_length_check=True):
        if enforce_length_check:
            current_length = len(self.get())
            if current_length + len(string) <= self.max_length:
                super().insert(index, string)
                self.update_undo_stack()
            else:
                # Truncate the string if it exceeds the maximum length
                allowed_length = self.max_length - current_length
                if allowed_length > 0:
                    super().insert(index, string[:allowed_length])
                    self.update_undo_stack()
                logging.info("Input limited to the maximum allowed length")
        else:
            super().insert(index, string)
            self.update_undo_stack()

    def _activate_placeholder(self):
        entry_text = self._entry.get()
        if (entry_text == "" or entry_text.isspace()) and self._placeholder_text is not None and (
                self._textvariable is None or self._textvariable.get() == ""):
            self._placeholder_text_active = True
            self._pre_placeholder_arguments = {"show": self._entry.cget("show")}
            self._entry.config(fg=self._apply_appearance_mode(self._placeholder_text_color),
                               disabledforeground=self._apply_appearance_mode(self._placeholder_text_color), show="")
            self._entry.delete(0, tk.END)
            self._entry.insert(0, self._placeholder_text)

    def update_listbox(self):
        self.teraterm_ui.search_classes(None)

    def destroy(self):
        if hasattr(self, "bindings"):
            for event, bind_id in self.bindings:
                self.unbind(event, bind_id)
        if hasattr(self, "focus_out_bind_id") and self.focus_out_bind_id:
            self.root.unbind("<FocusOut>", self.focus_out_bind_id)

        if hasattr(self, "context_menu") and self.context_menu:
            last_index = self.context_menu.index("end")
            if last_index is not None:
                for i in range(last_index + 1):
                    self.context_menu.entryconfigure(i, command=None)
            self.context_menu.destroy()
        if hasattr(self, "_undo_stack"):
            self._undo_stack.clear()
        if hasattr(self, "_redo_stack"):
            self._redo_stack.clear()

        self.teraterm_ui = None
        self.context_menu = None
        self._undo_stack = None
        self._redo_stack = None
        self.bindings = None
        self.max_length = None
        self.lang = None
        self.is_listbox_entry = None
        self.selected_text = None
        self.border_color = None
        super().destroy()


class CustomComboBox(customtkinter.CTkComboBox):
    __slots__ = ("master", "teraterm_ui_instance", "lang", "max_length", "selected_text", "border_color",
                 "context_menu", "bindings", "_undo_stack", "_redo_stack")

    def __init__(self, master, teraterm_ui_instance, lang=None, max_length=250, *args, **kwargs):
        if "cursor" not in customtkinter.CTkEntry._valid_tk_entry_attributes:
            customtkinter.CTkEntry._valid_tk_entry_attributes.add("cursor")
        super().__init__(master, cursor="xterm", *args, **kwargs)
        self.teraterm_ui = weakref.proxy(teraterm_ui_instance)

        initial_state = self.get()
        initial_cursor = self._entry.index(tk.INSERT)
        self._undo_stack = deque([(initial_state, initial_cursor)], maxlen=100)
        self._redo_stack = deque(maxlen=100)

        self.bindings = []
        self.setup_bindings()

        self.max_length = max_length
        self.lang = lang
        self.border_color = None
        self.selected_text = False
        self.context_menu = None

    def setup_bindings(self):
        bindings = [("<FocusIn>", self.disable_slider_keys), ("<FocusOut>", self.enable_slider_keys),
                    ("<Enter>", self.on_enter), ("<Motion>", self.on_motion), ("<Leave>", self.on_leave),
                    ("<Control-z>", self.undo), ("<Control-Z>", self.undo), ("<Control-y>", self.redo),
                    ("<Control-Y>", self.redo), ("<Control-v>", self.custom_paste), ("<Control-V>", self.custom_paste),
                    ("<Control-x>", self.custom_cut), ("<Control-X>", self.custom_cut),
                    ("<Control-a>", self.select_all), ("<Control-A>", self.select_all),
                    ("<Button-2>", self.custom_middle_mouse), ("<Button-3>", self.show_menu),
                    ("<KeyRelease>", self.update_undo_stack)]
        for event, callback in bindings:
            bind_id = self.bind(event, callback)
            self.bindings.append((event, bind_id))

    def disable_slider_keys(self, event=None):
        if self.cget("border_color") == "#c30101":
            if self.border_color is None:
                self.border_color = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"]
            self.configure(border_color=self.border_color)

        if self._entry.select_present() and self.selected_text:
            self._entry.select_clear()

            if self.lang == "English":
                self.context_menu.entryconfigure(3, label="Select All")
            elif self.lang == "Español":
                self.context_menu.entryconfigure(3, label="Seleccionar Todo")

        self.teraterm_ui.move_slider_left_enabled = False
        self.teraterm_ui.move_slider_right_enabled = False
        self.teraterm_ui.up_arrow_key_enabled = False
        self.teraterm_ui.down_arrow_key_enabled = False

    def enable_slider_keys(self, event=None):
        if self._entry.select_present() and not self.selected_text:
            self._entry.select_clear()

        self.selected_text = False
        self.teraterm_ui.move_slider_left_enabled = True
        self.teraterm_ui.move_slider_right_enabled = True
        self.teraterm_ui.up_arrow_key_enabled = True
        self.teraterm_ui.down_arrow_key_enabled = True

    def on_enter(self, event):
        if self.find_context_menu():
            self._entry.configure(cursor="arrow")
        else:
            self._entry.configure(cursor="xterm")
        self._canvas.configure(cursor="hand2")

    def on_motion(self, event):
        if self.find_context_menu():
            self._entry.configure(cursor="arrow")
        else:
            self._entry.configure(cursor="xterm")

    def on_leave(self, event):
        if self.find_context_menu():
            self._entry.configure(cursor="xterm")
        else:
            self._entry.configure(cursor="arrow")
        self._canvas.configure(cursor="arrow")

    def set(self, value, enforce_length_check=True):
        if enforce_length_check:
            if len(value) <= self.max_length:
                super().set(value)
                self.update_undo_stack()
            else:
                # Truncate the string if it exceeds the maximum length
                value = value[:self.max_length]
                super().set(value)
                self.update_undo_stack()
                logging.info("Input limited to the maximum allowed length")
        else:
            super().set(value)
            self.update_undo_stack()

    def _dropdown_callback(self, value: str):
        # Save current value to undo stack before changing
        current_text = self.get()
        current_cursor = self._entry.index(tk.INSERT)
        if current_text != self._undo_stack[-1][0]:
            self._undo_stack.append((current_text, current_cursor))

        super()._dropdown_callback(value)  # Call the original dropdown callback

        # Update undo stack with new value
        new_text = self.get()
        new_cursor = self._entry.index(tk.INSERT)
        if new_text != self._undo_stack[-1][0]:
            self._undo_stack.append((new_text, new_cursor))

    def update_undo_stack(self, event=None):
        current_text = self.get()
        cursor_position = self._entry.index(tk.INSERT)
        if current_text != self._undo_stack[-1][0]:
            self._undo_stack.append((current_text, cursor_position))
            self._redo_stack.clear()

    def undo(self, event=None):
        self.focus_set()
        if len(self._undo_stack) > 1:
            # Remove the current state from the undo stack and add it to the redo stack
            current_text, current_cursor = self._undo_stack.pop()
            self._redo_stack.append((current_text, current_cursor))

            # Get the previous state from the undo stack
            previous_text, previous_cursor = self._undo_stack[-1]

            # Apply the previous text state
            self.set(previous_text, enforce_length_check=False)
            self._entry.icursor(previous_cursor)

            # Adjust the view position
            self._entry.xview_moveto(previous_cursor / len(previous_text) if len(previous_text) > 0 else 0)

    def redo(self, event=None):
        self.focus_set()
        if self._redo_stack:
            # Get the next state from the redo stack and add it to the undo stack
            next_text, next_cursor = self._redo_stack.pop()
            self._undo_stack.append((next_text, next_cursor))

            # Apply the next text state
            self.set(next_text, enforce_length_check=False)
            self._entry.icursor(next_cursor)

            # Adjust the view position
            self._entry.xview_moveto(next_cursor / len(next_text) if len(next_text) > 0 else 0)

    @staticmethod
    def find_context_menu():
        import win32process

        try:
            windows = []
            win32gui.EnumWindows(lambda hwnd_win, results: results.append(hwnd_win), windows)
            for hwnd in windows:
                class_name = win32gui.GetClassName(hwnd)
                if class_name == "#32768":
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid == os.getpid():
                        return hwnd
            return None
        except Exception as err:
            logging.warning(f"Unexpected error in find_context_menu: {err}")
        return None

    def custom_middle_mouse(self, event=None):
        if self.find_context_menu():
            return "break"
        if self._entry.select_present():
            char_index = self._entry.index("@%d" % event.x)
            self._entry.icursor(char_index)
            self._entry.select_clear()
            return "break"

    def show_menu(self, event):
        if self.cget("state") == "disabled":
            return

        self.focus_set()
        self.selected_text = True

        if self.context_menu is None:
            self.context_menu = tk.Menu(self, tearoff=0, font=("Arial", 10), relief="flat", background="gray40",
                                        fg="snow")
            menu_items = [("Cut", lambda: self.cut()), ("Copy", lambda: self.copy()), ("Paste", lambda: self.paste()),
                          ("Select All", lambda: self.select_all()), ("Undo", lambda: self.undo()),
                          ("Redo", lambda: self.redo())]
            for label, command in menu_items:
                self.context_menu.add_command(label=label, command=command)

        if self.lang == "English":
            self.context_menu.entryconfigure(0, label="Cut")
            self.context_menu.entryconfigure(1, label="Copy")
            self.context_menu.entryconfigure(2, label="Paste")
            self.context_menu.entryconfigure(3, label="Select All")
            self.context_menu.entryconfigure(4, label="Undo")
            self.context_menu.entryconfigure(5, label="Redo")
        elif self.lang == "Español":
            self.context_menu.entryconfigure(0, label="Cortar")
            self.context_menu.entryconfigure(1, label="Copiar")
            self.context_menu.entryconfigure(2, label="Pegar")
            self.context_menu.entryconfigure(3, label="Seleccionar Todo")
            self.context_menu.entryconfigure(4, label="Deshacer")
            self.context_menu.entryconfigure(5, label="Rehacer")

        if self._entry.select_present():
            if self.lang == "English":
                self.context_menu.entryconfigure(3, label="Deselect All")
            elif self.lang == "Español":
                self.context_menu.entryconfigure(3, label="Deseleccionar Todo")
        else:
            if self.lang == "English":
                self.context_menu.entryconfigure(3, label="Select All")
            elif self.lang == "Español":
                self.context_menu.entryconfigure(3, label="Seleccionar Todo")

        self.context_menu.post(event.x_root, event.y_root)
        self.context_menu.bind("<Unmap>", lambda evt: self.configure(cursor="xterm"))

    def custom_cut(self, event=None):
        self.cut()
        return "break"

    def cut(self):
        self.focus_set()
        if not self._entry.select_present():
            self._entry.select_range(0, "end")
        try:
            selected_text = self._entry.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)

            # Save current state to undo stack before deletion
            current_text = self.get()
            current_cursor = self._entry.index(tk.INSERT)
            self._undo_stack.append((current_text, current_cursor))
            self._redo_stack.clear()

            self._entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            logging.info("No text selected to cut")

    def copy(self):
        self.focus_set()
        if not self._entry.select_present():
            self._entry.select_range(0, "end")
        try:
            selected_text = self._entry.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.update_idletasks()
        except tk.TclError:
            logging.info("No text selected to copy")

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
            clipboard_text = pyperclip.paste()
            max_paste_length = self.max_length

            # Truncate clipboard text if it exceeds max length
            if len(clipboard_text) > max_paste_length:
                clipboard_text = clipboard_text[:max_paste_length]
                logging.info("Pasted content truncated to maximum length")

            # Save the current state to undo stack before the paste operation
            current_text = self.get()
            current_cursor = self._entry.index(tk.INSERT)
            self._undo_stack.append((current_text, current_cursor))
            self._redo_stack.clear()

            insert_index = self._entry.index(tk.INSERT)
            try:
                start_index = self._entry.index(tk.SEL_FIRST)
                end_index = self._entry.index(tk.SEL_LAST)
                self._entry.delete(start_index, end_index)
                insert_index = start_index
            except tk.TclError:
                pass  # No selection to delete

            space_left = self.max_length - len(self.get())
            if len(clipboard_text) > space_left:
                clipboard_text = clipboard_text[:space_left]

            self._entry.insert(insert_index, clipboard_text)

            # Move the cursor to the end of the pasted content
            final_cursor_position = insert_index + len(clipboard_text)
            self._entry.icursor(final_cursor_position)
            self._entry.xview_moveto(final_cursor_position / len(self.get()) if len(self.get()) > 0 else 0)
        except tk.TclError:
            pass  # Clipboard empty or other issue
        return "break"

    def destroy(self):
            if hasattr(self, "bindings"):
                for event, bind_id in self.bindings:
                    self.unbind(event, bind_id)

            if hasattr(self, "context_menu") and self.context_menu:
                last_index = self.context_menu.index("end")
                if last_index is not None:
                    for i in range(last_index + 1):
                        self.context_menu.entryconfigure(i, command=None)
                self.context_menu.destroy()
            if hasattr(self, "_undo_stack"):
                self._undo_stack.clear()
            if hasattr(self, "_redo_stack"):
                self._redo_stack.clear()

            self.teraterm_ui = None
            self.context_menu = None
            self._undo_stack = None
            self._redo_stack = None
            self.bindings = None
            self.border_color = None
            self.max_length = None
            self.lang = None
            self.selected_text = None
            super().destroy()


class SmoothFadeToplevel(customtkinter.CTkToplevel):
    __slots__ = ("fade_duration", "final_alpha", "alpha", "fade_direction", "alpha", "fade_direction", "_fade_after_id")

    def __init__(self, fade_duration=30, final_alpha=1.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fade_duration = fade_duration
        self.final_alpha = final_alpha
        self.alpha = 0.0
        self.fade_direction = 1  # 1 for fade-in, -1 for fade-out
        self._fade_after_id = None  # Initialize the fade callback ID
        self.withdraw()
        self.after(0, self._setup_geometry)

    def _setup_geometry(self):
        self.deiconify()
        self._start_fade_in()

    def _start_fade_in(self):
        self.fade_direction = 1
        self._fade()

    def _fade(self):
        self.alpha += self.fade_direction * (self.final_alpha / self.fade_duration)
        self.alpha = max(0.0, min(self.alpha, self.final_alpha))
        self.attributes("-alpha", self.alpha)
        if 0.0 < self.alpha < self.final_alpha:
            self._fade_after_id = self.after(5, self._fade)
        elif self.alpha <= 0.0:
            self.destroy()

    def button_event(self):
        self.fade_direction = -1
        if self._fade_after_id is not None:
            self.after_cancel(self._fade_after_id)
            self._fade_after_id = None
        self._fade()

    def destroy(self):
        if self._fade_after_id is not None:
            self.after_cancel(self._fade_after_id)
            self._fade_after_id = None
        super().destroy()

class SmoothFadeInputDialog(customtkinter.CTkInputDialog):
    __slots__ = ("fade_duration", "final_alpha", "alpha", "fade_direction", "alpha", "fade_direction", "_fade_after_id")

    def __init__(self, fade_duration=30, final_alpha=1.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fade_duration = fade_duration
        self.final_alpha = final_alpha
        self.alpha = 0.0
        self.fade_direction = 1  # 1 for fade-in, -1 for fade-out
        self._fade_after_id = None  # Initialize the fade callback ID
        self.withdraw()
        self.after(0, self._setup_geometry)

    def _setup_geometry(self):
        self.deiconify()
        self._start_fade_in()

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
        if self._fade_after_id is not None:
            self.after_cancel(self._fade_after_id)
            self._fade_after_id = None
        self._fade()

    def destroy(self):
        if self._fade_after_id is not None:
            self.after_cancel(self._fade_after_id)
            self._fade_after_id = None
        super().destroy()


class ImageSlideshow(customtkinter.CTkFrame):
    __slots__ = ("slideshow_frame", "image_folder", "interval", "width", "height", "image_files", "_current_image",
                 "index", "label", "arrow_left", "arrow_right", "after_id", "is_running")

    def __init__(self, parent, image_folder, interval=3, width=300, height=200, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.slideshow_frame = parent
        self.image_folder = image_folder
        self.interval = interval
        self.width = width
        self.height = height
        self.image_files = []
        self._current_image = None
        self.after_id = None
        self.is_running = True

        self._setup_ui()

        self.load_images()
        self.index = 0
        self.show_image()

    def _setup_ui(self):
        self.label = customtkinter.CTkLabel(self, text="")
        self.label.bind("<Button-1>", lambda event: self.focus_set())
        self.label.grid(row=0, column=1)

        self.arrow_left = CustomButton(self, text="<", command=self.prev_image, width=25)
        self.arrow_right = CustomButton(self, text=">", command=self.next_image, width=25)

        for arrow in (self.arrow_left, self.arrow_right):
            arrow.bind("<Button-1>", lambda event: self.focus_set())

        self.arrow_left.grid(row=0, column=0)
        self.arrow_right.grid(row=0, column=2)

        self.bind("<Button-1>", lambda event: self.focus_set())

    def load_images(self):
        try:
            image_files = [f for f in os.listdir(self.image_folder)
                           if f.lower().endswith(("png", "jpg", "jpeg"))]
            if not image_files:
                logging.warning(f"No valid images found in {self.image_folder}")
                return

            random.seed(time.time())
            random.shuffle(image_files)
            self.image_files = image_files
        except Exception as err:
            logging.error(f"Error loading images from {self.image_folder}: {err}")
            self.image_files = []

    def _load_and_resize_image(self, filepath):
        try:
            with Image.open(filepath) as img:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA" if img.mode == "P" and "transparency" in img.info else "RGB")
                resized = img.resize((self.width * 2, self.height * 2), Image.Resampling.LANCZOS)
                return customtkinter.CTkImage(light_image=resized, size=(self.width, self.height))
        except Exception as err:
            logging.error(f"Error loading image {filepath}: {err}")
            return None

    def show_image(self):
        if not self.image_files:
            return

        if hasattr(self, "_current_image") and self._current_image is not None:
            if hasattr(self.label, "_last_image"):
                del self.label._last_image
            self._current_image = None

        filepath = os.path.join(self.image_folder, self.image_files[self.index])
        new_image = self._load_and_resize_image(filepath)

        if new_image is not None:
            self._current_image = new_image
            self.label.configure(image=self._current_image)

        self._reset_timer()

    def cycle_images(self):
        if self._current_image:
            if hasattr(self.label, "_last_image"):
                del self.label._last_image
            self._current_image = None

        self.index = (self.index + 1) % len(self.image_files)
        self.show_image()

    def prev_image(self):
        self.index = (self.index - 1) % len(self.image_files)
        self.show_image()

    def next_image(self):
        self.index = (self.index + 1) % len(self.image_files)
        self.show_image()

    def go_to_first_image(self):
        self.index = 0
        self.show_image()

    def _reset_timer(self):
        if self.after_id is not None:
            self.after_cancel(self.after_id)
            self.after_id = None

        if self.is_running:
            self.after_id = self.after(self.interval * 1000, self.cycle_images)

    def pause_cycle(self):
        if self.after_id is not None:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.is_running = False

    def resume_cycle(self):
        if not self.is_running:
            self.is_running = True
            self._reset_timer()

    def destroy(self):
        if self.after_id is not None:
            self.after_cancel(self.after_id)
            self.after_id = None

        if hasattr(self, "_current_image") and self._current_image is not None:
            if hasattr(self.label, "_last_image"):
                del self.label._last_image
            self._current_image = None

        if hasattr(self, "arrow_left"):
            self.arrow_left.destroy()
        if hasattr(self, "arrow_right"):
            self.arrow_right.destroy()
        if hasattr(self, "label"):
            self.label.destroy()

        self.image_files.clear()
        super().destroy()


class SSHMonitor:
    def __init__(self, host, port=22):
        self.host = host
        self.port = port
        self.latencies = []
        self.failures = 0
        self.failure_streak = 0
        self.last_sample_time = 0

    def measure_latency(self, timeout=5):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            start = time.time()
            result = sock.connect_ex((self.host, self.port))
            end = time.time()
            sock.close()
            if result == 0:
                return (end - start) * 1000
        except (socket.timeout, ConnectionRefusedError, OSError):
            pass
        return None

    def sample(self, count=30, concurrent=True, force=False, cooldown=25):
        now = time.time()
        if now - self.last_sample_time < cooldown and not force:
            return

        self.last_sample_time = now
        if concurrent:
            with ThreadPoolExecutor(max_workers=count) as executor:
                futures = [executor.submit(self.measure_latency) for _ in range(count)]
                for future in as_completed(futures):
                    latency = future.result()
                    if latency is not None:
                        self.latencies.append(latency)
                        self.failure_streak = 0
                    else:
                        self.failures += 1
                        self.failure_streak += 1
        else:
            for _ in range(count):
                latency = self.measure_latency()
                if latency is not None:
                    self.latencies.append(latency)
                    self.failure_streak = 0
                else:
                    self.failures += 1
                    self.failure_streak += 1
                time.sleep(0.3)

    def get_stats(self):
        total_attempts = len(self.latencies) + self.failures
        if total_attempts == 0:
            return None

        stats = {
            "samples": len(self.latencies),
            "failures": self.failures,
            "failure_rate": round((self.failures / total_attempts) * 100, 2),
            "failure_streak": self.failure_streak,
        }

        if self.latencies:
            min_latency = min(self.latencies)
            max_latency = max(self.latencies)
            avg_latency = statistics.mean(self.latencies)
            std_dev = statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0.0

            stats.update({
                "min": round(min_latency, 2),
                "max": round(max_latency, 2),
                "average": round(avg_latency, 2),
                "std_dev": round(std_dev, 2)
            })
            score = 100
            score -= stats["failure_rate"] * 0.5
            score -= min(avg_latency, 1000) * 0.05
            score -= min(std_dev, 300) * 0.1
            stats["reliability_score"] = max(0, round(score, 2))

        else:
            stats["reliability_score"] = 0.0

        return stats

    def get_reliability_rating(self, lang):
        stats = self.get_stats()
        if not stats or stats["samples"] == 0:
            return ("Unknown", "black") if lang == "English" else ("Desconocido", "black")

        score = stats["reliability_score"]
        thresholds = [
            (90, {"English": "Excellent", "Español": "Excelente"}, "#4CAF50"),
            (75, {"English": "Good", "Español": "Buena"}, "#8BC34A"),
            (60, {"English": "Fair", "Español": "Regular"}, "#FFEB3B"),
            (40, {"English": "Poor", "Español": "Deficiente"}, "#FF9800"),
            (0, {"English": "Unreliable", "Español": "No confiable"}, "red"),
        ]

        for threshold, labels, color in thresholds:
            if score >= threshold:
                return labels.get(lang, labels["English"]), color

        return ("Unknown", "black") if lang == "English" else ("Desconocido", "black")

    def is_responsive(self, avg_cutoff=800, max_cutoff=1500, max_failure_rate=20):
        stats = self.get_stats()
        if not stats or stats["samples"] == 0:
            return False
        if stats["average"] > avg_cutoff or stats["max"] > max_cutoff or stats["failure_rate"] > max_failure_rate:
            return False
        return True


class SecureDataStore:
    def __init__(self, key_path=None, auto_rotate_days=30):
        self.key_path = key_path or os.path.join(os.getcwd(), "masterkey.json")
        self.auto_rotate_days = auto_rotate_days
        self.cred_name = f"TeraTermUI/Passphrase/{os.getlogin()}@{platform.node()}"
        self.aes_key = None
        self.creating_key_file = False
        self.initialize_keys()

    # Load and validate the encrypted key file, verify HMAC, derive AES
    def initialize_keys(self):
        try:
            if not os.path.exists(self.key_path):
                self.creating_key_file = True
                self.create_new_key_file()

            with open(self.key_path, "r") as f:
                raw = json.load(f)

            metadata = json.dumps({
                "version": raw["version"],
                "key_id": raw["key_id"],
                "created_at": raw["created_at"],
                "expires_at": raw["expires_at"],
                "last_used": raw["last_used"],
                "encrypted_key": raw["encrypted_key"],
                "os_username": raw["os_username"],
                "user_sid": raw["user_sid"],
                "machine_id": raw["machine_id"],
                "key_usage": raw["key_usage"],
                "key_algorithm": raw["key_algorithm"],
                "protected_by": raw["protected_by"]
            }, separators=(",", ":")).encode()

            hmac_stored = base64.b64decode(raw["hmac"])
            hmac_calc = HMAC.new(self.get_dynamic_hmac_key(), digestmod=SHA256)
            hmac_calc.update(metadata)

            if not compare_digest(hmac_stored, hmac_calc.digest()):
                raise ValueError("HMAC verification failed on masterkey.json")

            if self.is_expired():
                logging.info("Master key expired — rotating key")
                self.reset()
                self.creating_key_file = True
                self.create_new_key_file()
                return

            encrypted_key = base64.b64decode(raw["encrypted_key"])
            master_key = win32crypt.CryptUnprotectData(encrypted_key, None,
                                                       None, None, 0)[1]
            passphrase = self.retrieve_passphrase()
            hybrid_key = bytes(a ^ b for a, b in zip(master_key, passphrase))
            self.aes_key = HKDF(hybrid_key, 32, salt=b"student_event_salt", hashmod=SHA256)

        except Exception as err:
            logging.error("Key initialization failed: %s", str(err))
            self.reset()
            self.creating_key_file = True
            self.create_new_key_file()

    # Generate new master key, encrypt using DPAPI, store with metadata and HMAC
    def create_new_key_file(self):
        master_key = get_random_bytes(32)
        encrypted = win32crypt.CryptProtectData(master_key, None, None,
                                                None, None, 0)
        key_id = str(os.urandom(16).hex())
        user_sid, _, _ = win32security.LookupAccountName(None, os.getlogin())
        user_sid_str = win32security.ConvertSidToStringSid(user_sid)

        passphrase = get_random_bytes(32)
        self.store_passphrase(passphrase)

        metadata = {
            "version": "1.1.0",
            "key_id": key_id,
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(days=self.auto_rotate_days)).isoformat(),
            "last_used": None,
            "encrypted_key": base64.b64encode(encrypted).decode(),
            "os_username": os.getlogin(),
            "user_sid": user_sid_str,
            "machine_id": platform.node(),
            "key_usage": "encryption",
            "key_algorithm": "AES-GCM-256-HKDF-SHA256",
            "protected_by": "DPAPI-SID"
        }
        hmac_obj = HMAC.new(self.get_dynamic_hmac_key(), digestmod=SHA256)
        hmac_obj.update(json.dumps(metadata, separators=(",", ":")).encode())
        metadata["hmac"] = base64.b64encode(hmac_obj.digest()).decode()

        with open(self.key_path, "w") as f:
            json.dump(metadata, f, indent=2)

        self.lock_file_to_user(self.key_path)
        self.hide_file(self.key_path)

    # Securely store passphrase in Windows Credential Manager
    def store_passphrase(self, passphrase):
        encoded = base64.b64encode(passphrase).decode("utf-8")
        win32cred.CredWrite({
            "Type": win32cred.CRED_TYPE_GENERIC,
            "TargetName": self.cred_name,
            "UserName": os.getlogin(),
            "CredentialBlob": encoded,
            "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE
        }, 0)

    def retrieve_passphrase(self):
        cred = win32cred.CredRead(self.cred_name, win32cred.CRED_TYPE_GENERIC)
        return base64.b64decode(cred["CredentialBlob"])

    def delete_passphrase(self):
        try:
            win32cred.CredRead(self.cred_name, win32cred.CRED_TYPE_GENERIC)
            win32cred.CredDelete(self.cred_name, win32cred.CRED_TYPE_GENERIC, 0)
        except Exception as err:
            if err.args[0] == 1168:
                pass
            else:
                logging.warning(f"Could not delete passphrase from Credential Manager: {err}")

    @contextmanager
    def unlock_aes_key(self):
        if self.aes_key is None:
            self.initialize_keys()

        key = bytearray(self.aes_key)
        try:
            yield key
        finally:
            self.zeroize(key)

    # Encrypt plaintext string using AES-GCM and return ciphertext, nonce, tag
    def encrypt(self, plaintext):
        with self.unlock_aes_key() as key:
            cipher = AES.new(bytes(key), AES.MODE_GCM)
            ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode())
            self.update_last_used()
            return ciphertext, cipher.nonce, tag

    # Decrypt ciphertext using AES-GCM, verify tag, and return plaintext
    def decrypt(self, ciphertext, nonce, tag):
        try:
            with self.unlock_aes_key() as key:
                cipher = AES.new(bytes(key), AES.MODE_GCM, nonce=nonce)
                return cipher.decrypt_and_verify(ciphertext, tag).decode()
        except (ValueError, KeyError) as err:
            logging.error("Decryption failed or tag mismatch: %s", str(err))
            raise ValueError("Decryption failed or data integrity check failed")
        finally:
            self.update_last_used()

    def update_last_used(self):
        if not os.path.exists(self.key_path):
            logging.warning("Key file missing — skipping last_used update")
            return

        try:
            with open(self.key_path, "r+") as f:
                raw = json.load(f)
                raw["last_used"] = datetime.now(UTC).isoformat()
                metadata = json.dumps({
                    k: raw[k] for k in ["version", "key_id", "created_at", "expires_at", "last_used",
                                        "encrypted_key", "os_username", "user_sid", "machine_id", "key_usage",
                                        "key_algorithm", "protected_by"]},
                    separators=(",", ":")).encode()

                hmac_obj = HMAC.new(self.get_dynamic_hmac_key(), digestmod=SHA256)
                hmac_obj.update(metadata)
                raw["hmac"] = base64.b64encode(hmac_obj.digest()).decode()
                f.seek(0)
                f.truncate()
                json.dump(raw, f, indent=2)
        except Exception as err:
            logging.warning("Could not update last_used timestamp: %s", str(err))

    # Check if the key has expired based on created_at and rotation period
    def is_expired(self):
        with open(self.key_path, "r") as f:
            created_at = json.load(f)["created_at"]
        created = datetime.fromisoformat(created_at)
        return (datetime.now(UTC) - created).days > self.auto_rotate_days

    # Verify the integrity of the key file using its HMAC
    def verify_integrity(self):
        with open(self.key_path, "r") as f:
            raw = json.load(f)
        metadata = json.dumps({
            "version": raw["version"],
            "key_id": raw["key_id"],
            "created_at": raw["created_at"],
            "expires_at": raw["expires_at"],
            "last_used": raw["last_used"],
            "encrypted_key": raw["encrypted_key"],
            "os_username": raw["os_username"],
            "user_sid": raw["user_sid"],
            "machine_id": raw["machine_id"],
            "key_usage": raw["key_usage"],
            "key_algorithm": raw["key_algorithm"],
            "protected_by": raw["protected_by"]
        }, separators=(",", ":")).encode()
        expected_hmac = base64.b64decode(raw["hmac"])
        actual_hmac = HMAC.new(self.get_dynamic_hmac_key(), digestmod=SHA256)
        actual_hmac.update(metadata)
        return compare_digest(expected_hmac, actual_hmac.digest())

    def get_dynamic_hmac_key(self) -> bytes:
        seed = f"{self.cred_name}:{platform.node()}:{os.getlogin()}".encode()
        return SHA256.new(seed).digest()

    def reset(self):
        self.zeroize(self.aes_key)
        self.aes_key = None
        if os.path.exists(self.key_path):
            os.remove(self.key_path)
        self.delete_passphrase()

    @staticmethod
    def hide_file(path):
        FILE_ATTRIBUTE_HIDDEN = 0x02
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs == -1:
                raise OSError("Invalid file or folder path")
            if not attrs & FILE_ATTRIBUTE_HIDDEN:
                ctypes.windll.kernel32.SetFileAttributesW(str(path), attrs | FILE_ATTRIBUTE_HIDDEN)
        except Exception as err:
            logging.warning(f"Could not hide file {path}: {err}")

    # Set ACL to restrict access to the current user only
    @staticmethod
    def lock_file_to_user(path):
        import ntsecuritycon as con

        try:
            user_sid, _, _ = win32security.LookupAccountName(None, os.getlogin())
            sd = win32security.GetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION)
            dacl = win32security.ACL()
            dacl.AddAccessAllowedAceEx(win32security.ACL_REVISION, 0, con.FILE_GENERIC_READ
                                       | con.FILE_GENERIC_WRITE, user_sid)
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION, sd)
        except Exception as err:
            logging.warning(f"Could not lock file ACL for {path}: {err}")

    # Attempt to zero out memory for a bytes value.
    @staticmethod
    def zeroize(value):
        if value:
            try:
                if isinstance(value, bytes):
                    value = bytearray(value)
                ctypes.memset(ctypes.addressof(ctypes.c_char.from_buffer(value)), 0, len(value))
            except Exception as err:
                logging.warning("Failed to zero memory: %s", str(err))


class ClipboardHandler:
    def __init__(self, max_data_size=100 * 1024 * 1024, retention_time=timedelta(minutes=30),
                 key_rotation_interval=timedelta(hours=24)):
        # General configuration settings for size, retention, and key rotation
        self.MAX_DATA_SIZE = max_data_size
        self.RETENTION_TIME = retention_time
        self.KEY_ROTATION_INTERVAL = key_rotation_interval

        # Resource tracking
        self.gdi_handles = set()  # Track all GDI handles
        self._active = True  # Track if handler is active

        # Synchronization
        self.clipboard_lock = threading.Lock()
        self.key_rotation_lock = threading.Lock()

        # Data storage
        self.clipboard_data = {}
        self.current_key = self.generate_new_key()
        self.last_key_rotation = datetime.now()

        # Register additional clipboard formats
        self.CF_HTML = win32clipboard.RegisterClipboardFormat("HTML Format")
        self.CF_RTF = win32clipboard.RegisterClipboardFormat("Rich Text Format")
        self.CF_PNG = win32clipboard.RegisterClipboardFormat("PNG")
        self.CF_TIFF = win32clipboard.RegisterClipboardFormat("TIFF")
        self.CF_GIF = win32clipboard.RegisterClipboardFormat("GIF")
        self.CF_JFIF = win32clipboard.RegisterClipboardFormat("JFIF")
        self.CF_JPEG = win32clipboard.RegisterClipboardFormat("JPEG")
        self.CF_WEBP = win32clipboard.RegisterClipboardFormat("image/webp")
        self.CF_SVG = win32clipboard.RegisterClipboardFormat("image/svg+xml")
        self.CF_SHELLURL = win32clipboard.RegisterClipboardFormat("UniformResourceLocator")
        self.CF_FILENAME = win32clipboard.RegisterClipboardFormat("FileName")

        # Allowed formats and their readable names
        self.allowed_formats = [win32con.CF_TEXT, win32con.CF_UNICODETEXT, win32con.CF_DIB, win32con.CF_BITMAP,
                                win32con.CF_HDROP, win32con.CF_LOCALE, self.CF_HTML, self.CF_RTF, self.CF_PNG,
                                self.CF_TIFF, self.CF_GIF, self.CF_JFIF, self.CF_JPEG, self.CF_WEBP, self.CF_SVG,
                                self.CF_SHELLURL, self.CF_FILENAME]
        self._format_names = {win32con.CF_TEXT: "Text", win32con.CF_UNICODETEXT: "Unicode Text",
                              win32con.CF_DIB: "DIB", win32con.CF_BITMAP: "Bitmap",  win32con.CF_HDROP: "File Drop",
                              win32con.CF_LOCALE: "Locale", self.CF_HTML: "HTML", self.CF_RTF: "RTF",
                              self.CF_PNG: "PNG", self.CF_TIFF: "TIFF", self.CF_GIF: "GIF", self.CF_JFIF: "JPEG (JFIF)",
                              self.CF_JPEG: "JPEG", self.CF_WEBP: "WebP", self.CF_SVG: "SVG", self.CF_SHELLURL: "URL",
                              self.CF_FILENAME: "Filename"}

        # Default system encoding for text
        self.default_encoding = locale.getpreferredencoding()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    @contextmanager
    def saving(self):
        if not self._active:
            raise RuntimeError("ClipboardHandler is closed")
        try:
            self.save_clipboard_content()
            yield
        finally:
            pass

    @contextmanager
    def restoring(self):
        if not self._active:
            raise RuntimeError("ClipboardHandler is closed")
        try:
            yield
            self.restore_clipboard_content()
        finally:
            pass

    def close(self):
        if not self._active:
            return

        self._active = False
        try:
            if self.clipboard_lock.locked():
                self.clipboard_lock.release()
        except Exception as error:
            logging.warning(f"Error releasing clipboard lock: {error}")

        self.cleanup_all_resources()

    @contextmanager
    def handle_gdi_resource(self, handle):
        if not handle:
            yield None
            return
        try:
            if handle and win32gui.GetObjectType(handle):  # Validate handle
                self.gdi_handles.add(handle)
                logging.debug(f"Tracking new GDI handle: {handle}")
            yield handle
        finally:
            try:
                if handle in self.gdi_handles:
                    win32gui.DeleteObject(handle)
                    self.gdi_handles.remove(handle)
            except Exception as error:
                logging.warning(f"Failed to cleanup GDI handle {handle}: {error}")

    @staticmethod
    def generate_new_key():
        master_key = get_random_bytes(32)
        salt = get_random_bytes(16)
        return HKDF(master_key, 32, salt=salt, hashmod=SHA256)

    def _rotate_keys(self):
        current_time = datetime.now()
        with self.key_rotation_lock:
            if current_time - self.last_key_rotation >= self.KEY_ROTATION_INTERVAL:
                old_key = self.current_key
                self.current_key = self.generate_new_key()
                self.last_key_rotation = current_time
                self.secure_erase(old_key)
                logging.info("Encryption key rotated")

    def encrypt_data(self, plaintext):
        if not plaintext:
            raise ValueError("Cannot encrypt empty data")
        self._rotate_keys()
        iv = get_random_bytes(16)
        try:
            cipher = AES.new(self.current_key, AES.MODE_CFB, iv=iv)
            ciphertext = cipher.encrypt(plaintext)
            return iv + ciphertext
        finally:
            self.secure_erase(plaintext)

    def decrypt_data(self, encrypted_data):
        if len(encrypted_data) < 16:
            raise ValueError("Encrypted data too short")
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        try:
            cipher = AES.new(self.current_key, AES.MODE_CFB, iv=iv)
            return cipher.decrypt(ciphertext)
        finally:
            self.secure_erase(ciphertext)

    @staticmethod
    def secure_erase(data):
        if isinstance(data, (bytes, bytearray)):
            try:
                buffer_obj = ctypes.create_string_buffer(len(data))
                ctypes.memset(ctypes.addressof(buffer_obj), 0, len(data))
            except Exception as error:
                logging.warning(f"Failed to securely erase data: {error}")

    @contextmanager
    def clipboard_access(self):
        if not self.clipboard_lock.acquire(timeout=1.0):
            raise TimeoutError("Could not acquire clipboard lock")
        try:
            if not self.open_clipboard_with_retries():
                raise RuntimeError("Failed to open clipboard")
            yield
        finally:
            try:
                win32clipboard.CloseClipboard()
            except Exception as error:
                logging.warning(f"Failed to close clipboard: {error}")
            self.clipboard_lock.release()

    @staticmethod
    def open_clipboard_with_retries(max_retries=3, retry_delay=0.1):
        for attempt in range(max_retries):
            try:
                win32clipboard.OpenClipboard()
                return True
            except Exception as error:
                if attempt == max_retries - 1:
                    logging.warning(f"Failed to open clipboard after {max_retries} attempts: {error}")
                    return False
                time.sleep(retry_delay)
        return False

    def check_data_size(self, data, format_name="Unknown"):
        try:
            if isinstance(data, (int, bool)):
                return True
            if hasattr(data, "__len__"):
                size = len(data)
                if size > self.MAX_DATA_SIZE:
                    logging.warning(f"Data for format {format_name} exceeds size limit "
                                    f"({size} > {self.MAX_DATA_SIZE} bytes)")
                    return False
            return True
        except Exception as error:
            logging.warning(f"Error checking size for format {format_name}: {error}")
            return False

    def cleanup_all_resources(self):
        # Clean up GDI handles
        handles = self.gdi_handles.copy()
        for handle in handles:
            try:
                if win32gui.GetObjectType(handle):
                    win32gui.DeleteObject(handle)
                self.gdi_handles.remove(handle)
            except Exception as error:
                logging.warning(f"Failed to delete GDI handle {handle}: {error}")

        # Clean up clipboard data
        items = list(self.clipboard_data.items())
        for fmt, (data, _) in items:
            try:
                if fmt == win32con.CF_BITMAP and win32gui.GetObjectType(data):
                    win32gui.DeleteObject(data)
                self.secure_erase(data)
            except Exception as error:
                logging.warning(f"Failed to cleanup format {fmt}: {error}")

        self.clipboard_data.clear()
        gc.collect()

    @staticmethod
    def sanitize_file_paths(paths):
        sanitized = []
        for path in paths:
            clean_path = os.path.normpath(path.replace("\0", ""))
            if os.path.exists(clean_path):
                sanitized.append(clean_path)
        return sanitized

    def cleanup_expired_data(self):
        current_time = datetime.now()
        expired_formats = [fmt for fmt, (_, timestamp) in self.clipboard_data.items()
                           if current_time - timestamp > self.RETENTION_TIME]
        for fmt in expired_formats:
            try:
                data = self.clipboard_data[fmt][0]
                if fmt == win32con.CF_BITMAP and win32gui.GetObjectType(data):
                    win32gui.DeleteObject(data)
                del self.clipboard_data[fmt]
            except Exception as error:
                logging.warning(f"Error cleaning up expired format {fmt}: {error}")

    def save_clipboard_content(self):
        import struct

        if not self._active:
            raise RuntimeError("ClipboardHandler is closed")

        self.cleanup_expired_data()
        clipboard_cache = {}

        try:
            with self.clipboard_access():
                formats = []
                fmt = win32clipboard.EnumClipboardFormats(0)
                while fmt:
                    if fmt in self.allowed_formats:
                        formats.append(fmt)
                    fmt = win32clipboard.EnumClipboardFormats(fmt)

                # First pass: collect all data
                for format_id in formats:
                    try:
                        data = win32clipboard.GetClipboardData(format_id)
                        if data is not None:  # Skip if no data
                            clipboard_cache[format_id] = data
                    except Exception as error:
                        logging.warning(
                            f"Failed to get clipboard data for format {self._format_names.get(format_id)}: {error}")
                        continue

            # Second pass: process and encrypt
            for format_id, data in clipboard_cache.items():
                try:
                    if not self.check_data_size(data, self._format_names.get(format_id, "Unknown")):
                        continue

                    # Handle text formats - GetClipboardData handles encoding
                    if format_id in (win32con.CF_TEXT, win32con.CF_UNICODETEXT):
                        if not data or (isinstance(data, str) and not data.strip()):
                            continue  # Skip empty or whitespace-only text
                        if isinstance(data, str):
                            data = data.encode(
                                "utf-16le" if format_id == win32con.CF_UNICODETEXT else self.default_encoding)

                    # Handle bitmap handle
                    elif format_id == win32con.CF_BITMAP:
                        try:
                            with self.handle_gdi_resource(data):
                                continue
                        except Exception as error:
                            logging.warning(f"Failed to process bitmap handle: {error}")
                            continue

                    # Handle HTML format
                    elif format_id == self.CF_HTML and isinstance(data, str):
                        # Extract the HTML fragment with header
                        start_html = data.find("<html>")
                        end_html = data.find("</html>")
                        if start_html != -1 and end_html != -1:
                            html_content = data[start_html:end_html + 7]
                            # Create standard clipboard HTML header
                            header = ("Version:0.9\r\n"
                                      f"StartHTML:{start_html}\r\n"
                                      f"EndHTML:{end_html + 7}\r\n"
                                      f"StartFragment:{start_html}\r\n"
                                      f"EndFragment:{end_html}\r\n\r\n")
                            data = (header + html_content).encode("utf-8")
                        else:
                            continue

                    # Handle RTF format
                    elif format_id == self.CF_RTF and isinstance(data, str):
                        if not data.startswith("{\\rtf1"):
                            continue
                        data = data.encode("utf-8")

                    # Handle image formats
                    elif format_id in (self.CF_PNG, self.CF_GIF, self.CF_JFIF, self.CF_TIFF, self.CF_JPEG, self.CF_WEBP):
                        if isinstance(data, str):
                            data = data.encode("utf-8")
                        if isinstance(data, bytes):
                            # Validate image headers
                            if format_id == self.CF_PNG and not data.startswith(b"\x89PNG\r\n\x1a\n"):
                                continue
                            if format_id == self.CF_JPEG and not data.startswith(b"\xff\xd8"):
                                continue
                            elif format_id == self.CF_GIF and not data.startswith((b"GIF87a", b"GIF89a")):
                                continue
                            elif format_id == self.CF_JFIF and not data.startswith(b"\xff\xd8"):
                                continue
                            elif format_id == self.CF_TIFF and not (data.startswith(b"II*\x00") or
                                                                    data.startswith(b"MM\x00*")):
                                continue
                            elif format_id == self.CF_WEBP and not data.startswith(b"RIFF"):
                                continue

                    elif format_id == self.CF_SVG and isinstance(data, str):
                        if "<svg" not in data.lower() or "</svg>" not in data.lower():
                            continue
                        data = data.encode("utf-8")

                    # Handle file drops
                    elif format_id == win32con.CF_HDROP and isinstance(data, tuple):
                        sanitized_paths = self.sanitize_file_paths(data)
                        if not sanitized_paths:
                            continue

                        # Create DROPFILES structure
                        file_list = b""
                        for path in sanitized_paths:
                            encoded_path = path.encode("utf-16le") + b"\0\0"
                            file_list += encoded_path
                        file_list += b"\0\0"
                        data = struct.pack("Iiii", 20, 0, 0, 1) + file_list
                        # 20 is DROPFILES size, 1 for unicode

                    # Handle URL
                    elif format_id == self.CF_SHELLURL and isinstance(data, str):
                        url = data.strip()
                        if not url.startswith(("http://", "https://", "ftp://")):
                            continue
                        if len(url) > 2083:  # Maximum URL length for IE
                            continue
                        data = url.encode("utf-8") + b"\0"

                    # Handle filename
                    elif format_id == self.CF_FILENAME and isinstance(data, str):
                        filename = data.strip()
                        invalid_chars = '<>:"/\\|?*'
                        for char in invalid_chars:
                            filename = filename.replace(char, "")
                        if not filename:
                            continue
                        data = filename.encode("utf-8") + b"\0"

                    # Handle locale
                    elif format_id == win32con.CF_LOCALE:
                        if isinstance(data, bytes):
                            lcid = int.from_bytes(data, byteorder="little")
                        elif isinstance(data, int):
                            lcid = data
                        else:
                            lcid = int(data)
                        if not 0 <= lcid <= 0xFFFF:
                            continue
                        data = struct.pack("i", lcid)

                    # Process and store valid data
                    if data is not None:
                        encrypted_data = self.encrypt_data(data)
                        self.clipboard_data[format_id] = (encrypted_data, datetime.now())

                except Exception as error:
                    logging.warning(f"Error processing format {self._format_names.get(format_id)}: {error}")
                    continue

        except (RuntimeError, TimeoutError) as error:
            logging.error(f"Failed to access clipboard: {error}")
            raise
        finally:
            gc.collect()

    def restore_clipboard_content(self):
        if not self.clipboard_data:
            return

        if not self._active:
            raise RuntimeError("ClipboardHandler is closed")

        self.cleanup_expired_data()
        import struct

        try:
            with self.clipboard_access():
                win32clipboard.EmptyClipboard()
                items = list(self.clipboard_data.items())

                for fmt, (encrypted_data, _) in items:
                    try:
                        decrypted_data = self.decrypt_data(encrypted_data)

                        # Handle text formats with empty check
                        if fmt in (win32con.CF_TEXT, win32con.CF_UNICODETEXT):
                            if not decrypted_data or (
                                    isinstance(decrypted_data, (str, bytes)) and not decrypted_data.strip()):
                                continue
                            if fmt == win32con.CF_TEXT:
                                if not isinstance(decrypted_data, bytes):
                                    continue
                            else:  # CF_UNICODETEXT
                                if isinstance(decrypted_data, bytes):
                                    try:
                                        decrypted_data = decrypted_data.decode("utf-16le").strip()
                                    except UnicodeError:
                                        continue

                        # Handle bitmap handle
                        elif fmt == win32con.CF_BITMAP and isinstance(decrypted_data, int):
                            with self.handle_gdi_resource(decrypted_data):
                                win32clipboard.SetClipboardData(fmt, decrypted_data)
                            continue

                        # Handle HTML format
                        elif fmt == self.CF_HTML:
                            if not isinstance(decrypted_data, bytes):
                                continue
                            try:
                                content = decrypted_data.decode("utf-8")
                                if "<html>" not in content or "</html>" not in content:
                                    continue
                            except UnicodeError:
                                continue

                        # Handle RTF format
                        elif fmt == self.CF_RTF:
                            if not isinstance(decrypted_data, bytes):
                                continue
                            try:
                                content = decrypted_data.decode("utf-8")
                                if not content.startswith("{\\rtf1"):
                                    continue
                            except UnicodeError:
                                continue

                        # Handle image formats
                        elif fmt in (self.CF_PNG, self.CF_GIF, self.CF_JFIF, self.CF_TIFF, self.CF_JPEG, self.CF_WEBP):
                            if not isinstance(decrypted_data, bytes):
                                continue
                            # Basic header validation
                            if fmt == self.CF_PNG and not decrypted_data.startswith(b"\x89PNG\r\n\x1a\n"):
                                continue
                            elif fmt == self.CF_JPEG and not decrypted_data.startswith(b"\xff\xd8"):
                                continue
                            elif fmt == self.CF_GIF and not decrypted_data.startswith((b"GIF87a", b"GIF89a")):
                                continue
                            elif fmt == self.CF_JFIF and not decrypted_data.startswith(b"\xff\xd8"):
                                continue
                            elif fmt == self.CF_TIFF and not (decrypted_data.startswith(b"II*\x00") or
                                                              decrypted_data.startswith(b"MM\x00*")):
                                continue
                            elif fmt == self.CF_WEBP and not decrypted_data.startswith(b"RIFF"):
                                continue

                        elif fmt == self.CF_SVG:
                            if not isinstance(decrypted_data, bytes):
                                continue
                            try:
                                content = decrypted_data.decode("utf-8")
                                if "<svg" not in content.lower() or "</svg>" not in content.lower():
                                    continue
                            except UnicodeError:
                                continue

                        # Handle HDROP
                        elif fmt == win32con.CF_HDROP:
                            if not isinstance(decrypted_data, bytes) or len(decrypted_data) < 20:
                                continue
                            # Validate DROPFILES structure
                            try:
                                offset, = struct.unpack("I", decrypted_data[:4])
                                is_unicode, = struct.unpack("I", decrypted_data[16:20])
                                if offset != 20 or not is_unicode:
                                    continue
                            except struct.error:
                                continue

                        # Handle URL and filename
                        elif fmt in (self.CF_SHELLURL, self.CF_FILENAME):
                            if not isinstance(decrypted_data, bytes):
                                continue
                            try:
                                # Both should be null-terminated UTF-8 strings
                                if not decrypted_data.endswith(b"\0"):
                                    continue
                                text = decrypted_data[:-1].decode("utf-8")
                                if not text.strip():
                                    continue
                            except UnicodeError:
                                continue

                        # Handle locale
                        elif fmt == win32con.CF_LOCALE:
                            if not isinstance(decrypted_data, bytes) or len(decrypted_data) != 4:
                                continue
                            try:
                                lcid = int.from_bytes(decrypted_data, byteorder="little")
                                if not 0 <= lcid <= 0xFFFF:
                                    continue
                            except ValueError:
                                continue

                        # Set clipboard data
                        win32clipboard.SetClipboardData(fmt, decrypted_data)

                    except Exception as error:
                        logging.warning(f"Error restoring format {self._format_names.get(fmt)}: {error}")
                        continue

        except (RuntimeError, TimeoutError) as error:
            logging.error(f"Failed to restore clipboard content: {error}")
            raise
        finally:
            self.cleanup_all_resources()


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


def has_write_permission():
    testfile_path = os.path.join(os.getcwd(), ".write_test")
    try:
        with open(testfile_path, "w") as testfile:
            testfile.write("test")
        os.remove(testfile_path)
        return True
    except (OSError, IOError):
        return False


def bring_to_front():
    def restore_window(title_win):
        t_hwnd = win32gui.FindWindow(None, title_win)
        if t_hwnd:
            if not win32gui.IsWindowVisible(t_hwnd):
                win32gui.ShowWindow(t_hwnd, win32con.SW_SHOW)
            win32gui.ShowWindow(t_hwnd, win32con.SW_RESTORE)
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
    mode = "Portable"
    SPANISH = 0x0A
    language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    os.chdir(os.path.dirname(sys.argv[0]))
    temporary_dir = os.path.join(tempfile.gettempdir(), "TeraTermUI")
    lock_file = os.path.join(temporary_dir, "TeraTermUI_Updater.lock")
    if os.path.exists(lock_file):
        logging.error(f"The updater is currently running. Application cannot be launched")
        sys.exit(1)
    if mode == "Portable" and not has_write_permission():
        if language_id & 0xFF == SPANISH:
            messagebox.showerror("Permiso denegado",
                                 "No tienes permiso para escribir en el directorio actual. "
                                 "Ejecuta la aplicación desde un directorio diferente")
        else:
            messagebox.showerror("Permission Denied",
                                 "You don't have permission to write to the current directory. "
                                 "Please run the application from a different directory")
        sys.exit(1)
    tera_term_temp_dir = os.path.join(tempfile.gettempdir(), "TeraTermUI")
    if not os.path.exists(tera_term_temp_dir):
        os.makedirs(tera_term_temp_dir)
    lock_file_temp = os.path.join(tera_term_temp_dir, "TeraTermUI.lock")
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
        logging.error("A fatal error occurred: %s", error)
        traceback.print_exc()
        if language_id & 0xFF == SPANISH:
            messagebox.showerror("Error", "Ocurrió un error inesperado: " + str(error) +
                                 "\n\nPuede que necesite reinstalar la aplicación")
        else:
            messagebox.showerror("Error", "An unexpected error occurred: " + str(error) +
                                 "\n\nMight need to reinstall the application")
        sys.exit(1)


if __name__ == "__main__":
    main()
