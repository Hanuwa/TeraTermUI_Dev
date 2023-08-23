import asyncio
import ctypes
import subprocess
import time

import customtkinter
import winsound
from pywinauto.application import Application
from pywinauto.keyboard import send_keys
from CTkMessagebox import CTkMessagebox
import pygetwindow as gw
from UserInterface import MainMenu
from Utilities import Network
import threading


class AutomatedTasks():
    def __init__(self):
        super().__init__()
        self.download = None
        self.uprbay_window = None
        self.uprb = None
        self.run_fix = None
        self.in_student_frame = None
        self.passed = None

    def login_to_server(self, host, lang):
        dont_close = False
        try:
            self.gui.preparing()
            timeout_counter = 0
            skip = False
            host = host.replace(" ", "").lower()
            if asyncio.run(self.test_connection(lang)) and self.check_server():
                if host == "uprbay.uprb.edu" or host == "uprbayuprbedu":
                    if self.checkIfProcessRunning("ttermpro"):
                        while not self.tesseract_unzipped:
                            time.sleep(1)
                            timeout_counter += 1
                            if timeout_counter > 5:
                                skip = True
                                break
                        if self.window_exists("uprbay.uprb.edu - Tera Term VT") and not skip:
                            term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                            dont_close = True
                            if term_window.isMinimized:
                                term_window.restore()
                            screenshot_thread = threading.Thread(target=self.capture_screenshot)
                            screenshot_thread.start()
                            screenshot_thread.join()
                            text_output = self.capture_screenshot()
                            if ("MENU DE OPCIONES" in text_output or "STUDENTS REQ/DROP" in text_output or "HOLD FLAGS"
                                in text_output or "PROGRAMA DE CLASES" in text_output or "ACADEMIC STATISTICS" in
                                text_output or "SNAPSHOT" in text_output or "SOLICITUD DE PRORROGA" in text_output) \
                                    and "IDENTIFICACION PERSONAL" not in text_output:
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
                                self.host.grid_forget()
                                self.host_entry.grid_forget()
                                self.log_in.grid_forget()
                                self.intro_box.grid_forget()
                                self.introduction.grid_forget()
                                self.switch_tab()
                                self.set_focus_to_tkinter()
                            else:
                                self.bind("<Return>", lambda event: self.login_event_handler())
                                if lang == "English":
                                    self.after(0, self.show_error_message, 450, 265,
                                               "Error! Cannot connect to server \n\n"
                                               " if another instance of Tera Term"
                                               " is already running")
                                elif lang == "Español":
                                    self.after(0, self.show_error_message, 450, 265,
                                               "¡Error! No es posible"
                                               " conectarse al servidor \n\n"
                                               " si otra instancia de Tera Term"
                                               " ya está corriendo")
                        else:
                            self.bind("<Return>", lambda event: self.login_event_handler())
                            if lang == "English":
                                self.after(0, self.show_error_message, 450, 265,
                                           "Error! Cannot connect to server \n\n"
                                           " if another instance of Tera Term"
                                           " is already running")
                            elif lang == "Español":
                                self.after(0, self.show_error_message, 450, 265,
                                           "¡Error! No es posible"
                                           " conectarse al servidor \n\n"
                                           " si otra instancia de Tera Term"
                                           " ya está corriendo")
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
                            hostText.type_keys("uprbay.uprb.edu", with_spaces=False, pause=0.02)
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
                                if lang == "English":
                                    self.after(0, self.show_error_message, 425, 330,
                                               "Error! Cannot start application.\n\n "
                                               "The location of your Tera Term \n\n"
                                               " might be different "
                                               "from the default,\n\n "
                                               "click the \"Help\" button "
                                               "to set it's location")
                                elif lang == "Español":
                                    self.after(0, self.show_error_message, 425, 330,
                                               "¡Error! No se pudo iniciar la aplicación."
                                               "\n\n La localización de tu "
                                               "Tera Term\n\n"
                                               " es diferente de la normal, \n\n "
                                               "presiona el botón de \"Ayuda\""
                                               "para encontrarlo")
                                if not self.download:
                                    self.after(3500, self.download_teraterm)
                                    self.download = True
                elif host != "uprbay.uprb.edu":
                    self.bind("<Return>", lambda event: self.login_event_handler())
                    if lang == "English":
                        self.after(0, self.show_error_message, 300, 215, "Error! Invalid host")
                    elif lang == "Español":
                        self.after(0, self.show_error_message, 300, 215, "¡Error! Servidor Incorrecto")
            self.show_sidebar_windows()
        except Exception as e:
            print("An error occurred: ", e)
            self.error_occurred = True
        finally:
            lang = self.language_menu.get()
            task_done.set()
            if self.error_occurred:
                self.destroy_windows()
                if not dont_close:
                    winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                    subprocess.run(["taskkill", "/f", "/im", "ttermpro.exe"],
                                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if lang == "English":
                    CTkMessagebox(master=self, title="Error Information",
                                  message="Error while performing and automating tasks! "
                                          "Please make sure not to interrupt the execution of the applications\n\n "
                                          "Tera Term was forced to close",
                                  icon="warning", button_width=380)
                if lang == "Español":
                    CTkMessagebox(master=self, title="Información del Error",
                                  message="¡Error mientras se realizaban y automatizaban tareas!"
                                          "Por favor trate de no interrumpir la ejecución de las aplicaciones\n\n "
                                          "Tera Term fue forzado a cerrar",
                                  icon="warning", button_width=380)
                self.error_occurred = False


