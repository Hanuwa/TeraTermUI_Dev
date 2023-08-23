import threading
import time
import customtkinter
import win32gui
import winsound
from CTkMessagebox import CTkMessagebox
from CTkToolTip import CTkToolTip
from customtkinter import ctktable
import pygetwindow as gw
import tkinter as tk
from PIL import Image
from Utilities import OsOperations
from Utilities import Network
from Utilities import DatabaseOperations
from datetime import datetime


class MainWindow(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        # disabled/enables keybind events
        self.move_slider_left_enabled = True
        self.move_slider_right_enabled = True
        self.spacebar_enabled = True
        self.up_arrow_key_enabled = True
        self.down_arrow_key_enabled = True
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
        self.os = OsOperations()
        self.network = Network()
        # default location of Tera Term
        self.teraterm_location = "C:/Program Files (x86)/teraterm/ttermpro.exe"
        self.teraterm_config_location = "C:/Program Files (x86)/teraterm/TERATERM.ini"
        self.boot_up_thread = threading.Thread(target=self.boot_up_operations, args=(self.teraterm_config_location,))
        self.boot_up_thread.start()

    def window(self):
        self.title("Tera Term UI")
        self.iconbitmap("images/tera-term.ico")
        # determines screen size to put application in the middle of the screen
        width = 910
        height = 485
        scaling_factor = self.tk.call("tk", "scaling")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width * scaling_factor) / 2
        y = (screen_height - height * scaling_factor) / 2
        self.geometry(f"{width}x{height}+{int(x) + 130}+{int(y + 50)}")

    # Necessary things to do while the application is booting, gets done on a separate thread
    def boot_up_operations(self):
        self.os.cleanup_tesseract()
        self.os.edit_teraterm_config(self.teraterm_config_location)
        self.os.unzip_tesseract()
        self.os.generate_user_id()
        self.network.read_feedback_file()

    def set_focus(self):
        self.focus_set()


class Sidebar(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.is_banned = None
        self.is_banned_flag = False
        self.class_list = None
        self.search_box = None
        self.disableIdle = None
        self.help = None
        self.feedbackSend = None
        self.feedbackText = None
        self.status = None
        self.scaling_tooltip = None
        self.scaling_optionemenu = None
        self.appearance_mode_optionemenu = None
        self.language_menu = None
        self.option_label = None
        self.help_button = None
        self.status_button = None
        self.logo_label = None
        self.sidebar_frame = None
        self.os = OsOperations()
        self.network = Network()
        self.main_window = MainWindow()
        self.db = DatabaseOperations("database.db")
        self.top_level = TopLevelWindows()
        self.main_menu = MainMenu()

    # create sidebar frame with widgets
    def sidebar_widgets(self, lang):
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))
        self.main_window.bind("<Left>", self.move_slider_left)
        self.main_window.bind("<Right>", self.move_slider_right)

    # Creates the status window
    def status_button_event(self, lang):
        if self.status and self.status.winfo_exists():
            self.status.lift()
            return
        self.main_window.set_focus()
        self.top_level.status_widgets(lang)
        translations = self.os.load_language(lang)
        screen_width = self.main_window.winfo_screenwidth()
        screen_height = self.main_window.winfo_screenheight()
        scaling_factor = self.main_window.tk.call("tk", "scaling")
        x_position = int((screen_width - 475 * scaling_factor) / 2)
        y_position = int((screen_height - 275 * scaling_factor) / 2)
        window_geometry = f"{475}x{280}+{x_position + 130}+{y_position + 18}"
        self.status.geometry(window_geometry)
        self.status.title(translations["status_button"])
        self.status.after(256, lambda: self.status.iconbitmap("images/tera-term.ico"))
        self.status.resizable(False, False)
        self.status.bind("<Escape>", lambda event: self.status.destroy())
        self.top_level.status_widgets(lang)

    # Creates the Help window
    def help_button_event(self, lang):
        translations = self.os.load_language(lang)
        if self.help and self.help.winfo_exists():
            self.help.lift()
            return
        self.main_window.set_focus()
        self.top_level.help_pack()
        screen_width = self.main_window.winfo_screenwidth()
        screen_height = self.main_window.winfo_screenheight()
        scaling_factor = self.main_window.tk.call("tk", "scaling")
        x_position = int((screen_width - 475 * scaling_factor) / 2)
        y_position = int((screen_height - 275 * scaling_factor) / 2)
        window_geometry = f"{475}x{280}+{x_position + 130}+{y_position + 18}"
        self.help.geometry(window_geometry)
        self.help.title(translations["help_button"])
        self.help.after(256, lambda: self.help.iconbitmap("images/tera-term.ico"))
        self.help.resizable(False, False)
        self.top_level.help_widgets(lang)
        idle = self.db.cursor.execute("SELECT idle FROM user_data").fetchall()
        if idle:
            if idle[0][0] == "Disabled":
                self.disableIdle.select()
        self.class_list.bind("<<ListboxSelect>>", self.db.show_class_code)
        self.class_list.bind("<MouseWheel>", self.disable_scroll)
        self.search_box.bind("<KeyRelease>", self.db.search_classes)
        self.help.bind("<Escape>", lambda event: self.help.destroy())

    # function for changing language
    def change_language_event(self, lang):
        translation = self.os.load_language(lang)
        self.main_window.set_focus()
        self.status_button.configure(text=translation["status_button"])
        self.help_button.configure(text=translation["help_button"])
        self.option_label.configure(text=translation["option_label"])
        self.main_menu.intro_box.configure(state="normal")
        self.main_menu.intro_box.delete("1.0", "end")
        self.main_menu.intro_box.insert("0.0", translation["intro_box"])
        self.main_menu.intro_box.configure(state="disabled")
        self.appearance_mode_optionemenu.configure(values=[translation["light"], translation["dark"],
                                                           translation["default"]])
        self.appearance_mode_optionemenu.set(translation["dark"])
        self.appearance_mode_optionemenu.set(translation["light"])
        self.appearance_mode_optionemenu.set(translation["default"])
        self.main_menu.introduction.configure(text=translation["introduction"])
        self.main_menu.host.configure(text=translation["host"])
        self.main_menu.log_in.configure(text=translation["log_in"])
        self.title_auth.configure(text=translation["title_auth"])
        self.disclaimer.configure(text=translation["disclaimer"])
        self.username.configure(text=translation["username"])
        self.authentication.configure(text=translation["authentication"])
        self.back.configure(text=translation["back"])
        self.title_security.configure(text=translation["title_security"])
        self.ssn.configure(text=translation["ssn"])
        self.code.configure(text=translation["code"])
        self.show.configure(text=translation["show"])
        self.system.configure(text=translation["system"])
        self.back_student.configure(text=translation["back"])
        self.title_enroll.configure(text=translation["title_enroll"])
        self.e_class.configure(text=translation["class"])
        self.e_section.configure(text=translation["section"])
        self.e_semester.configure(text=translation["semester"])
        self.register.configure(text=translation["register"])
        self.drop.configure(text=translation["drop"])
        self.title_search.configure(text=translation["title_search"])
        self.s_classes.configure(text=translation["class"])
        self.s_semester.configure(text=translation["semester"])
        self.show_all.configure(text=translation["show_all"])
        self.title_menu.configure(text=translation["title_menu"])
        self.explanation_menu.configure(text=translation["explanation_menu"])
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

    def start_feedback_thread(self, lang):
        msg = None
        timeout_counter = 0
        self.feedbackSend.configure(state="disabled")
        while self.os.user_id is None:
            time.sleep(1)
            timeout_counter += 1
            if timeout_counter > 5:
                break
        if self.os.user_id is None:
            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
            if lang == "English":
                CTkMessagebox(title="Error", message="Error! Feedback submission not currently available",
                              icon="cancel", button_width=380)
            elif lang == "Español":
                CTkMessagebox(title="Error", message="¡Error! Mandar comentarios no esta disponible ahora mismo",
                              icon="cancel", button_width=380)
        else:
            if lang == "English":
                msg = CTkMessagebox(master=self, title="Submit",
                                    message="Are you ready to submit your feedback?"
                                            " \n\n(SUBMISSION IS COMPLETELY ANONYMOUS)",
                                    icon="question",
                                    option_1="Cancel", option_2="No", option_3="Yes", icon_size=(65, 65),
                                    button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "darkblue", "darkblue"))
            elif lang == "Español":
                msg = CTkMessagebox(master=self, title="Someter",
                                    message="¿Estás preparado para mandar to comentario?"
                                            " \n\n(EL ENVÍO ES COMPLETAMENTE ANÓNIMO)",
                                    icon="question",
                                    option_1="Cancelar", option_2="No", option_3="Sí", icon_size=(65, 65),
                                    button_color=("#c30101", "#145DA0", "#145DA0"),
                                    hover_color=("darkred", "darkblue", "darkblue"))
            response = msg.get()
            if response[0] == "Yes" or response[0] == "Sí":
                feedback_thread = threading.Thread(target=self.submit_feedback)
                feedback_thread.start()
            else:
                self.feedbackSend.configure(state="normal")

    # Submits feedback from the user to a Google sheet
    def submit_feedback(self, lang):
        if not self.is_banned_flag:
            self.is_banned = self.network.is_user_banned(self.network.user_id, lang)
            if not self.network.connection_error:
                self.is_banned_flag = True
        if not self.network.disable_feedback and not self.is_banned:
            current_date = datetime.today().strftime("%Y-%m-%d")
            date = self.db.cursor.execute("SELECT date FROM user_data WHERE date IS NOT NULL").fetchall()
            dates_list = [record[0] for record in date]
            if current_date not in dates_list:
                feedback = self.feedbackText.get("1.0", customtkinter.END).strip()
                word_count = len(feedback.split())
                if word_count < 1000:
                    feedback = self.feedbackText.get("1.0", customtkinter.END).strip()
                    if feedback:
                        result = self.network.call_sheets_api([[feedback]])
                        if result:
                            def show_success():
                                winsound.PlaySound("sounds/success.wav", winsound.SND_ASYNC)
                                if lang == "English":
                                    CTkMessagebox(title="Success", icon="check",
                                                  message="Feedback submitted successfully!", button_width=380)
                                elif lang == "Español":
                                    CTkMessagebox(title="Success", icon="check",
                                                  message="¡Comentario sometido éxitosamente!", button_width=380)

                            self.after(0, show_success)
                            resultDate = self.db.cursor.execute("SELECT date FROM user_data").fetchall()
                            if len(resultDate) == 0:
                                self.db.cursor.execute("INSERT INTO user_data (date) VALUES (?)", (current_date,))
                            elif len(resultDate) == 1:
                                self.db.cursor.execute("UPDATE user_data SET date=?", (current_date,))
                            self.db.connection.commit()
                            self.feedbackText.delete("1.0", customtkinter.END)
                        else:
                            if not self.network.connection_error:
                                def show_error():
                                    winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                    if lang == "English":
                                        CTkMessagebox(title="Error",
                                                      message="Error! An error occurred while submitting feedback",
                                                      icon="cancel", button_width=380)
                                    elif lang == "Español":
                                        CTkMessagebox(title="Error",
                                                      message="¡Error! Un error ocurrio mientras se sometia comentario",
                                                      icon="cancel", button_width=380)

                                self.after(0, show_error)
                    else:
                        if not self.network.connection_error:
                            def show_error():
                                winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                                if lang == "English":
                                    CTkMessagebox(title="Error", message="Error! Feedback cannot be empty",
                                                  icon="cancel", button_width=380)
                                elif lang == "Español":
                                    CTkMessagebox(title="Error",
                                                  message="¡Error! El comentario no puede estar vacio",
                                                  icon="cancel", button_width=380)

                            self.after(0, show_error)
                else:
                    if not self.network.connection_error:
                        def show_error():
                            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                            if lang == "English":
                                CTkMessagebox(title="Error", message="Error! Feedback cannot exceed 1000 words",
                                              icon="cancel", button_width=380)
                            elif lang == "Español":
                                CTkMessagebox(title="Error",
                                              message="¡Error! El comentario no puede exceder 1000 palabras",
                                              icon="cancel",
                                              button_width=380)

                        self.after(0, show_error)
            else:
                if not self.network.connection_error:
                    def show_error():
                        winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                        if lang == "English":
                            CTkMessagebox(title="Error", message="Error! Cannot submit more than one feedback per day",
                                          icon="cancel", button_width=380)
                        elif lang == "Español":
                            CTkMessagebox(title="Error",
                                          message="¡Error! No se puede enviar más de un comentario por día",
                                          icon="cancel", button_width=380)

                    self.after(0, show_error)
        else:
            if not self.network.connection_error:
                def show_error():
                    winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
                    if lang == "English":
                        CTkMessagebox(title="Error", message="Error! Feedback submission not currently available",
                                      icon="cancel", button_width=380)
                    elif lang == "Español":
                        CTkMessagebox(title="Error",
                                      message="¡Error! Mandar comentarios no esta disponible ahora mismo",
                                      icon="cancel", button_width=380)

                self.after(0, show_error)
        self.feedbackSend.configure(state="normal")

    # query for searching for either class code or name
    def show_class_code(self, event):
        lang = self.language_menu.get()
        selection = self.class_list.curselection()
        if len(selection) == 0:
            return
        selected_class = self.class_list.get(self.class_list.curselection())
        query = "SELECT code FROM courses WHERE name = ? OR code = ?"
        result = self.db.cursor.execute(query, (selected_class, selected_class)).fetchone()
        if result is None:
            self.class_list.delete(0, tk.END)
            if lang == "English":
                self.class_list.insert(tk.END, "NO RESULTS FOUND")
            elif lang == "Español":
                self.class_list.insert(tk.END, "NO SE ENCONTRARON RESULTADOS")
        else:
            self.search_box.delete(0, tk.END)
            self.search_box.insert(0, result[0])

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

    # function that changes the theme of the application
    def change_appearance_mode_event(self, new_appearance_mode: str):
        self.main_window.set_focus()
        if new_appearance_mode == "Oscuro":
            new_appearance_mode = "Dark"
        elif new_appearance_mode == "Claro":
            new_appearance_mode = "Light"
        elif new_appearance_mode == "Sistema":
            new_appearance_mode = "System"
        customtkinter.set_appearance_mode(new_appearance_mode)

    # function that lets your increase/decrease the scaling of the GUI
    def change_scaling_event(self, new_scaling: float):
        self.main_window.set_focus()
        new_scaling_float = new_scaling / 100
        customtkinter.set_widget_scaling(new_scaling_float)
        self.scaling_tooltip.configure(message=str(self.scaling_optionemenu.get()) + "%")

    # Moves the scaling slider to the left
    def move_slider_left(self, event):
        if self.main_window.move_slider_left_enabled:
            value = self.scaling_optionemenu.get()
            if value != 97:
                value -= 3
                self.scaling_optionemenu.set(value)
                self.change_scaling_event(value)
                self.scaling_tooltip.configure(message=str(self.scaling_optionemenu.get()) + "%")

    # Moves the scaling slider to the right
    def move_slider_right(self, event):
        if self.main_window.move_slider_right_enabled:
            value = self.scaling_optionemenu.get()
            if value != 103:
                value += 3
                self.scaling_optionemenu.set(value)
                self.change_scaling_event(value)
                self.scaling_tooltip.configure(message=str(self.scaling_optionemenu.get()) + "%")


class MainMenu(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.intro_box = None
        self.log_in = None
        self.host_tooltip = None
        self.host_entry = None
        self.host = None
        self.introduction = None
        self.os = OsOperations
        self.sidebar = Sidebar()

    # create main entry
    def create_widgets(self, lang):
        translations = self.os.load_language(lang)
        self.introduction = customtkinter.CTkLabel(self, text=translations["introduction"],
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        self.host = customtkinter.CTkLabel(self, text=translations["host"])
        self.host_entry = CustomEntry(self, self, placeholder_text="myhost.example.edu")
        self.host_entry.grid(row=2, column=1, padx=(20, 0), pady=(20, 20))
        self.host_tooltip = CTkToolTip(self.host_entry, message=translations["host_tooltip"],
                                       bg_color="#1E90FF")
        self.log_in = customtkinter.CTkButton(self, border_width=2, text=translations["log_in"],
                                              text_color=("gray10", "#DCE4EE"), command=self.login_event_handler)
        self.log_in.configure(state="disabled")
        self.intro_box = customtkinter.CTkTextbox(self, height=245, width=400)
        self.intro_box.insert("0.0", translations["intro_box"])
        self.intro_box.configure(state="disabled", wrap="word", border_spacing=7)

    def create_grid(self):
        self.introduction.grid(row=0, column=1, columnspan=2, padx=(20, 0), pady=(20, 0))
        self.host.grid(row=2, column=0, columnspan=2, padx=(30, 0), pady=(20, 20))
        self.log_in.grid(row=3, column=1, padx=(20, 0), pady=(20, 20))
        self.intro_box.grid(row=1, column=1, padx=(20, 0), pady=(0, 0))

    def destroy_widgets(self):
        self.sidebar.language_menu.configure(state="disabled")
        self.introduction.destroy()
        self.host.destroy()
        self.host_entry.destroy()
        self.host_tooltip.destroy()
        self.log_in.destroy()
        self.intro_box.destory()


class AuthenticationScreen(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.back_tooltip = None
        self.back = None
        self.authentication = None
        self.username_tooltip = None
        self.username_entry = None
        self.username = None
        self.disclaimer = None
        self.uprb_image_grid = None
        self.uprb_image = None
        self.title_auth = None
        self.a_buttons_frame = None
        self.authentication_frame = None
        self.init_student = False
        self.main_window = MainWindow()
        self.os = OsOperations()

    # (Authentication Screen)
    def create_widgets(self, lang):
        translations = self.os.load_language(lang)
        self.authentication_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.authentication_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.a_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.a_buttons_frame.bind("<Button-1>", lambda event: self.focus_set())
        self.title_auth = customtkinter.CTkLabel(master=self.authentication_frame,
                                                 text=translations["title_auth"],
                                                 font=customtkinter.CTkFont(size=20, weight="bold"))
        self.uprb_image = self.main_window.images["uprb"]
        self.uprb_image_grid = customtkinter.CTkButton(self.authentication_frame, text="", image=self.uprb_image,
                                                       command=self.uprb_event, fg_color="transparent", hover=False)
        self.disclaimer = customtkinter.CTkLabel(master=self.authentication_frame, text=translations["disclaimer"])
        self.username = customtkinter.CTkLabel(master=self.authentication_frame, text=translations["username"])
        self.username_entry = CustomEntry(self.authentication_frame, self)
        self.username_tooltip = CTkToolTip(self.username_entry, message=translations["username_tooltip"],
                                           bg_color="#1E90FF")
        self.authentication = customtkinter.CTkButton(master=self.a_buttons_frame, border_width=2,
                                                      text=translations["authentication"],
                                                      text_color=("gray10", "#DCE4EE"),
                                                      command=self.student_event_handler)
        self.back = customtkinter.CTkButton(master=self.a_buttons_frame, fg_color="transparent", border_width=2,
                                            text=translations["back"], hover_color="#4E4F50",
                                            text_color=("gray10", "#DCE4EE"), command=self.go_back_event)
        self.back_tooltip = CTkToolTip(self.back, message=translations["back_tooltip"], bg_color="#A9A9A9", alpha=0.90)

    def create_grid(self, lang):
        self.authentication_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 100))
        self.authentication_frame.grid_columnconfigure(2, weight=1)
        self.a_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(0, 0), pady=(0, 40))
        self.a_buttons_frame.grid_columnconfigure(2, weight=1)
        self.title_auth.grid(row=0, column=0, padx=(20, 20), pady=10)
        self.uprb_image_grid.grid(row=1, column=0, padx=(0, 0), pady=10)
        self.disclaimer.grid(row=2, column=0, padx=(0, 0), pady=(30, 0))
        if lang == "English":
            self.username.grid(row=3, column=0, padx=(0, 125), pady=(0, 10))
            self.username_entry.grid(row=3, column=0, padx=(90, 0), pady=(0, 10))
        elif lang == "Español":
            self.username.grid(row=3, column=0, padx=(0, 140), pady=(0, 10))
            self.username_entry.grid(row=3, column=0, padx=(60, 0), pady=(0, 10))
        self.back.grid(row=4, column=0, padx=(0, 10), pady=(0, 0))
        self.authentication.grid(row=4, column=1, padx=(10, 0), pady=(0, 0))

    def destroy_widgets(self):
        self.authentication_frame.destroy()
        self.a_buttons_frame.destroy()
        self.title_auth.destroy()
        self.uprb_image.destroy()
        self.disclaimer.destroy()
        self.username.destroy()
        self.username_entry.destroy()
        self.username_tooltip.destroy()
        self.authentication.destroy()
        self.back.destroy()
        self.back_tooltip.destroy()


class StudentInformation(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.s_buttons_frame = None
        self.student_frame = None
        self.back_student_tooltip = None
        self.back_student = None
        self.system = None
        self.show_text = None
        self.code_tooltip = None
        self.code_entry = None
        self.code = None
        self.ssn_tooltip = None
        self.ssn_entry = None
        self.ssn = None
        self.lock_grid = None
        self.lock = None
        self.title_security = None
        self.init_student = False
        self.main_window = MainWindow()
        self.os = OsOperations()

    def create_widgets(self, lang):
        if not self.init_student:
            translations = self.os.load_language(lang)
            self.init_student = True
            self.student_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.student_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.s_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.s_buttons_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.title_security = customtkinter.CTkLabel(master=self.student_frame,
                                                         text=translations["title_security"],
                                                         font=customtkinter.CTkFont(size=20, weight="bold"))
            self.lock = self.main_window.images["lock"]
            self.lock_grid = customtkinter.CTkButton(self.student_frame, text="", image=self.lock,
                                                     command=self.lock_event, fg_color="transparent", hover=False)
            self.ssn = customtkinter.CTkLabel(master=self.student_frame, text=translations["ssn"])
            self.ssn_entry = CustomEntry(self.student_frame, self, placeholder_text="#########", show="*")
            self.ssn_tooltip = CTkToolTip(self.ssn_entry, message=translations["ssn_tooltip"], bg_color="#1E90FF")
            self.code = customtkinter.CTkLabel(master=self.student_frame, text=translations["code"])
            self.code_entry = CustomEntry(self.student_frame, self, placeholder_text="####", show="*")
            self.code_tooltip = CTkToolTip(self.code_entry, message=translations["code_tooltip"], bg_color="#1E90FF")
            self.show_text = customtkinter.CTkSwitch(master=self.student_frame, text=translations["show"],
                                                     command=self.show_event, onvalue="on", offvalue="off")
            self.bind("<space>", lambda event: self.spacebar_event())
            self.ssn_entry.bind("<Command-c>", lambda e: "break")
            self.ssn_entry.bind("<Control-c>", lambda e: "break")
            self.code_entry.bind("<Command-c>", lambda e: "break")
            self.code_entry.bind("<Control-c>", lambda e: "break")
            self.system = customtkinter.CTkButton(master=self.s_buttons_frame, border_width=2,
                                                  text=translations["system"],
                                                  text_color=("gray10", "#DCE4EE"), command=self.tuition_event_handler)
            self.back_student = customtkinter.CTkButton(master=self.s_buttons_frame, fg_color="transparent",
                                                        border_width=2, text=translations["back"], hover_color="#4E4F50",
                                                        text_color=("gray10", "#DCE4EE"), command=self.go_back_event)
            self.back_student_tooltip = CTkToolTip(self.back_student, message=translations["back_tooltip"],
                                                   bg_color="#A9A9A9", alpha=0.90)

    def create_grid(self, lang):
        self.student_frame.grid(row=0, column=1, columnspan=5, rowspan=5, padx=(0, 0), pady=(0, 100))
        self.student_frame.grid_columnconfigure(2, weight=1)
        self.s_buttons_frame.grid(row=3, column=1, columnspan=5, padx=(0, 0), pady=(0, 40))
        self.s_buttons_frame.grid_columnconfigure(2, weight=1)
        self.title_security.grid(row=0, column=1, padx=(20, 20), pady=(10, 20))
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
        self.show_text.grid(row=4, column=1, padx=(10, 0), pady=(0, 10))
        self.back_student.grid(row=5, column=0, padx=(0, 10), pady=(0, 0))
        self.system.grid(row=5, column=1, padx=(10, 0), pady=(0, 0))

    def destroy_widgets(self):
        self.student_frame.destroy()
        self.s_buttons_frame.destroy()
        self.title_security.destroy()
        self.lock.destroy()
        self.ssn.destroy()
        self.ssn_entry.destroy()
        self.ssn_tooltip.destroy()
        self.code.destroy()
        self.code_entry.destroy()
        self.code_tooltip.destroy()
        self.code_tooltip.destroy()
        self.show_text.destroy()
        self.system.destroy()
        self.back_student.destroy()
        self.back_student_tooltip.destroy()


class EnrollmentSystem(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.other_tab = None
        self.search_tab = None
        self.enroll_tab = None
        self.go_next_4CM = None
        self.go_next_683 = None
        self.go_next_409 = None
        self.go_next_1GP = None
        self.go_next_1VE = None
        self.menu_submit = None
        self.menu_semester_entry = None
        self.menu_semester = None
        self.menu_entry = None
        self.menu = None
        self.explanation_menu = None
        self.title_menu = None
        self.search_next_page_tooltip = None
        self.search_next_page = None
        self.show_all_tooltip = None
        self.show_all = None
        self.s_semester_entry = None
        self.s_semester = None
        self.s_classes_entry = None
        self.s_classes = None
        self.title_search = None
        self.search_scrollbar = None
        self.drop_tooltip = None
        self.drop = None
        self.register_tooltip = None
        self.register = None
        self.radio_var = None
        self.e_semester_entry = None
        self.e_semester = None
        self.e_section_entry = None
        self.e_section = None
        self.e_classes_entry = None
        self.e_class = None
        self.title_enroll = None
        self.t_buttons_frame = None
        self.tabview = None
        self.init_class = False

    def tabview(self):
        self.tabview = customtkinter.CTkTabview(self, corner_radius=10, command=self.switch_tab)
        self.t_buttons_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.t_buttons_frame.bind("<Button-1>", lambda event: self.focus_set())
        if not self.init_class:
            self.init_class = True
            self.enroll_tab = "Enroll/Matricular"
            self.search_tab = "Search/Buscar"
            self.other_tab = "Other/Otros"
            self.tabview.add(self.enroll_tab)
            self.tabview.add(self.search_tab)
            self.tabview.add(self.other_tab)

    # First Tab
    def create__enroll_widgets(self):
        self.title_enroll = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab),
                                                   text="Enroll Classes ",
                                                   font=customtkinter.CTkFont(size=20, weight="bold"))
        self.e_class = customtkinter.CTkLabel(master=self.tabview.tab(self.enroll_tab), text="Class")
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
    def widgets_search(self):
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
        self.search_next_page = customtkinter.CTkButton(master=self.search_scrollbar, fg_color="transparent",
                                                        border_width=2, text="Next Page",
                                                        text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                                        command=self.go_next_search_handler, width=85)
        self.search_next_page_tooltip = CTkToolTip(self.search_next_page, message="There's more sections\n"
                                                                                  "available",
                                                   bg_color="#A9A9A9", alpha=0.90)

    # Third Tab
    def widgets_other(self):
        self.title_menu = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
                                                 text="Option Menu ",
                                                 font=customtkinter.CTkFont(size=20, weight="bold"))
        self.explanation_menu = customtkinter.CTkLabel(master=self.tabview.tab(self.other_tab),
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
        self.menu_submit = customtkinter.CTkButton(master=self.tabview.tab(self.other_tab), border_width=2,
                                                   text="Submit", text_color=("gray10", "#DCE4EE"),
                                                   command=self.option_menu_event_handler, width=141)
        self.go_next_1VE = customtkinter.CTkButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                                   border_width=2, text="Next Page",
                                                   text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                                   command=self.go_next_page_handler, width=100)
        self.go_next_1GP = customtkinter.CTkButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                                   border_width=2, text="Next Page",
                                                   text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                                   command=self.go_next_page_handler, width=100)
        self.go_next_409 = customtkinter.CTkButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                                   border_width=2, text="Next Page",
                                                   text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                                   command=self.go_next_page_handler, width=100)
        self.go_next_683 = customtkinter.CTkButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                                   border_width=2, text="Next Page", hover_color="#4E4F50",
                                                   text_color=("gray10", "#DCE4EE"),
                                                   command=self.go_next_page_handler, width=100)
        self.go_next_4CM = customtkinter.CTkButton(master=self.tabview.tab(self.other_tab), fg_color="transparent",
                                                   border_width=2, text="Next Page",
                                                   text_color=("gray10", "#DCE4EE"), hover_color="#4E4F50",
                                                   command=self.go_next_page_handler, width=100)

    def hide_widgets(self):
        self.tabview.grid_forget()
        self.t_buttons_frame.grid_forget()


class MultipleEnrollmentSystem(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.auto_frame = None
        self.save_frame = None
        self.m_button_frame = None
        self.multiple_frame = None
        self.m_register_menu = None
        self.m_semester_entry = None
        self.m_section_entry = None
        self.m_classes_entry = None
        self.m_num_class = None
        self.auto_enroll_tooltip = None
        self.auto_enroll = None
        self.save_data_tooltip = None
        self.save_data = None
        self.submit_multiple = None
        self.back_multiple_tooltip = None
        self.back_multiple = None
        self.m_remove_tooltip = None
        self.m_remove = None
        self.m_add_tooltip = None
        self.m_add = None
        self.m_choice = None
        self.m_semester = None
        self.m_section = None
        self.m_class = None
        self.title_multiple = None
        self.init_multiple = None

    # Multiple Classes Enrollment
    def widgets_multiple(self):
        if not self.init_multiple:
            self.init_multiple = True
            self.multiple_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.multiple_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.m_button_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.m_button_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.save_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.save_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.auto_frame = customtkinter.CTkFrame(self, corner_radius=10)
            self.auto_frame.bind("<Button-1>", lambda event: self.focus_set())
            self.title_multiple = customtkinter.CTkLabel(master=self.multiple_frame,
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
            self.m_add = customtkinter.CTkButton(master=self.m_button_frame, border_width=2, text="+",
                                                 text_color=("gray10", "#DCE4EE"), command=self.add_event, height=40,
                                                 width=50, hover=True, fg_color="blue")
            self.m_add_tooltip = CTkToolTip(self.m_add, message="Add more classes", bg_color="blue")
            self.m_remove = customtkinter.CTkButton(master=self.m_button_frame, border_width=2, text="-",
                                                    text_color=("gray10", "#DCE4EE"), command=self.remove_event,
                                                    height=40, width=50, fg_color="red", hover=True,
                                                    hover_color="darkred", state="disabled")
            self.m_remove_tooltip = CTkToolTip(self.m_remove, message="Remove classes", bg_color="red")
            self.back_multiple = customtkinter.CTkButton(master=self.m_button_frame, fg_color="transparent",
                                                         border_width=2, text="Back", height=40, width=70,
                                                         hover_color="#4E4F50", text_color=("gray10", "#DCE4EE"),
                                                         command=self.go_back_event2)
            self.back_multiple_tooltip = CTkToolTip(self.back_multiple, alpha=0.90,
                                                    message="Go back to the previous \nscreen", bg_color="#A9A9A9")
            self.submit_multiple = customtkinter.CTkButton(master=self.m_button_frame, border_width=2,
                                                           text="Submit", text_color=("gray10", "#DCE4EE"),
                                                           command=self.submit_multiple_event_handler, height=40,
                                                           width=70)
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

    def hide_widgets(self):
        self.multiple_frame.grid_forget()
        self.m_button_frame.grid_forget()
        self.auto_frame.grid_forget()
        self.save_frame.grid_forget()

    def upload_saved_class_data(self):
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
        

class TopLevelWindows(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.disableIdle = None
        self.fix = None
        self.fixText = None
        self.disableIdleText = None
        self.filesText = None
        self.files = None
        self.termsTable = None
        self.termsText = None
        self.curriculum = None
        self.curriculumText = None
        self.class_list = None
        self.search_box = None
        self.searchboxText = None
        self.help_notice = None
        self.help_title = None
        self.help_scrollable_frame = None
        self.help = None
        self.faq = None
        self.qaTable = None
        self.faqText = None
        self.notasoLink = None
        self.notaso = None
        self.website_link = None
        self.website = None
        self.checkUpdate = None
        self.checkUpdateText = None
        self.feedbackSend = None
        self.feedbackText = None
        self.status_title = None
        self.status = None
        self.version = None
        self.status_scrollable_frame = None
        self.help_minimized = None
        self.status_minimized = None
        self.information = None
        self.success = None
        self.error = None
        self.os = OsOperations()
        self.main_window = MainWindow()
        self.network = Network()
        self.sidebar = Sidebar()
        self.db = DatabaseOperations("database.db")

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
        my_image = self.main_window.images["error"]
        image = customtkinter.CTkLabel(self.error, text="", image=my_image)
        image.pack(padx=10, pady=20)
        error_msg = customtkinter.CTkLabel(self.error, text=error_msg_text,
                                           font=customtkinter.CTkFont(size=15, weight="bold"))
        error_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)
        self.error.bind("<Escape>", lambda event: self.error.destroy())

    # success window pop up message
    def show_success_message(self, width, height, success_msg_text, lang):
        if self.success and self.success.winfo_exists():
            self.success.lift()
            return
        translations = self.os.load_language(lang)
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
        self.success.title(translations["success_title"])
        self.success.attributes("-topmost", True)
        self.success.resizable(False, False)
        self.success.after(256, lambda: self.success.iconbitmap("images/tera-term.ico"))
        my_image = self.main_window.images["success"]
        image = customtkinter.CTkLabel(self.success, text="", image=my_image)
        image.pack(padx=10, pady=10)
        success_msg = customtkinter.CTkLabel(self.success, text=success_msg_text,
                                             font=customtkinter.CTkFont(size=15, weight="bold"))
        success_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)
        self.success.after(3500, lambda: self.success.destroy())
        self.success.bind("<Escape>", lambda event: self.success.destroy())

    # important information window pop up message
    def show_information_message(self, width, height, success_msg_text, lang):
        if self.information and self.information.winfo_exists():
            self.information.lift()
            return
        translations = self.os.load_language(lang)
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
        self.information.title(translations["information_title"])
        self.information.resizable(False, False)
        self.information.after(256, lambda: self.information.iconbitmap("images/tera-term.ico"))
        my_image = self.main_window.images["information"]
        image = customtkinter.CTkLabel(self.information, text="", image=my_image)
        image.pack(padx=10, pady=10)
        information_msg = customtkinter.CTkLabel(self.information, text=success_msg_text,
                                                 font=customtkinter.CTkFont(size=15, weight="bold"))
        information_msg.pack(side="top", fill="both", expand=True, padx=10, pady=20)
        self.information.bind("<Escape>", lambda event: self.information.destroy())

    def status_widgets(self, lang):
        translations = self.os.load_language(lang)
        self.status = SmoothFadeToplevel()
        self.status_scrollable_frame = customtkinter.CTkScrollableFrame(self.status, width=475, height=280,
                                                                        fg_color=("#e6e6e6", "#222222"))
        self.status_title = customtkinter.CTkLabel(self.status_scrollable_frame, text=translations["app_version"])
        self.version = customtkinter.CTkLabel(self.status_scrollable_frame, text=translations["app_version"])
        self.feedbackText = customtkinter.CTkTextbox(self.status_scrollable_frame, wrap="word", border_spacing=8,
                                                     width=300, height=170, fg_color=("#ffffff", "#111111"))
        self.feedbackSend = customtkinter.CTkButton(self.status_scrollable_frame, border_width=2,
                                                    text=translations["feedback"], text_color=("gray10", "#DCE4EE"),
                                                    command=self.start_feedback_thread)
        self.checkUpdateText = customtkinter.CTkLabel(self.status_scrollable_frame, text=translations["update_title"])
        self.checkUpdate = customtkinter.CTkButton(self.status_scrollable_frame, border_width=2,
                                                   image=self.main_window.images["update"], text=translations["update"],
                                                   anchor="w", text_color=("gray10", "#DCE4EE"),
                                                   command=self.network.update_app(lang))
        self.website = customtkinter.CTkLabel(self.status_scrollable_frame, text="\n\nTera Term UI's Website:")
        self.website_link = customtkinter.CTkButton(self.status_scrollable_frame, border_width=2,
                                                    image=self.main_window.images["link"], text=translations["link"],
                                                    anchor="w", text_color=("gray10", "#DCE4EE"),
                                                    command=self.network.open_github_event)
        self.notaso = customtkinter.CTkLabel(self.status_scrollable_frame, text=translations["notaso_title"])
        self.notasoLink = customtkinter.CTkButton(self.status_scrollable_frame, border_width=2,
                                                  image=self.main_window.images["link"],
                                                  text=translations["notaso_link"], anchor="w",
                                                  text_color=("gray10", "#DCE4EE"),
                                                  command=self.network.open_notaso_event)
        self.faqText = customtkinter.CTkLabel(self.status_scrollable_frame, text=translations["faq"],
                                              font=customtkinter.CTkFont(size=15, weight="bold"))
        self.qaTable = [[translations["q"], translations["a"]],
                        [translations["q1"], translations["a1"]],
                        [translations["q2"], translations["a2"]]]
        self.faq = ctktable.CTkTable(self.status_scrollable_frame, row=3, column=2, values=self.qaTable)

    def status_pack(self):
        self.status_scrollable_frame.pack()
        self.status_title.pack()
        self.version.pack()
        self.feedbackText.pack(pady=10)
        self.feedbackSend.pack()
        self.checkUpdateText.pack(pady=5)
        self.checkUpdate.pack()
        self.website.pack(pady=5)
        self.website_link.pack()
        self.notaso.pack(pady=5)
        self.notasoLink.pack()
        self.faqText.pack()
        self.faq.pack(expand=True, fill="both", padx=20, pady=20)

    def help_widgets(self, lang):
        translations = self.os.load_language(lang)
        bg_color = "#0e95eb"
        fg_color = "#333333"
        listbox_font = ("Arial", 11)
        self.help = SmoothFadeToplevel()
        self.help_scrollable_frame = customtkinter.CTkScrollableFrame(self.help, width=475, height=280,
                                                                      fg_color=("#e6e6e6", "#222222"))
        self.help_title = customtkinter.CTkLabel(self.help_scrollable_frame, text=translations["help_button"],
                                                 font=customtkinter.CTkFont(size=20, weight="bold"))
        self.help_notice = customtkinter.CTkLabel(self.help_scrollable_frame, text=translations["notice"],
                                                  font=customtkinter.CTkFont(weight="bold", underline=True))
        self.searchboxText = customtkinter.CTkLabel(self.help_scrollable_frame, text=translations["searchbox_title"])
        self.search_box = CustomEntry(self.help_scrollable_frame, self, placeholder_text=translations["searchbox"])
        self.class_list = tk.Listbox(self.help_scrollable_frame, width=35, bg=bg_color, fg=fg_color, font=listbox_font)
        self.curriculumText = customtkinter.CTkLabel(self.help_scrollable_frame, text=translations["curriculums_title"])
        self.curriculum = customtkinter.CTkOptionMenu(self.help_scrollable_frame,
                                                      values=[translations["dep"], translations["acc"],
                                                              translations["finance"], translations["Management"],
                                                              translations["mark"], translations["g_biology"],
                                                              translations["h_biology"], translations["c_science"],
                                                              translations["it"], translations["s_science"],
                                                              translations["physical"], translations["elec"],
                                                              translations["equip"], translations["peda"],
                                                              translations["che"], translations["nur"],
                                                              translations["office"], translations["engi"]],
                                                      command=self.network.curriculums, height=30, width=150)
        self.termsText = customtkinter.CTkLabel(self.help_scrollable_frame, text=translations["terms_title"],
                                                font=customtkinter.CTkFont(weight="bold", size=15))
        terms = [[translations["terms_year"], translations["terms_term"]],
                 ["2019", "B91, B92, B93"],
                 ["2020", "C01, C02, C03"],
                 ["2021", "C11, C12, C13"],
                 ["2022", "C21, C22, C23"],
                 ["2023", "C31, C32, C33"],
                 [translations["semester"], translations["seasons"]]]
        self.termsTable = ctktable.CTkTable(self.help_scrollable_frame, column=2, row=7, values=terms)
        self.files = customtkinter.CTkButton(self.help_scrollable_frame, border_width=2,
                                             image=self.main_window.images["folder"],
                                             text=translations["files_button"], anchor="w",
                                             text_color=("gray10", "#DCE4EE"), command=self.db.set_teraterm_location)
        self.filesText = customtkinter.CTkLabel(self.help_scrollable_frame, text=translations["files_title"])
        self.disableIdleText = customtkinter.CTkLabel(self.help_scrollable_frame, text=translations["idle_title"])
        self.disableIdle = customtkinter.CTkSwitch(self.help_scrollable_frame, text="Disable Anti-Idle", onvalue="on",
                                                   offvalue="off", command=self.disable_enable_idle)
        self.fixText = customtkinter.CTkLabel(self.help_scrollable_frame, text=translations["fix_title"])
        self.fix = customtkinter.CTkButton(self.help_scrollable_frame, border_width=2,
                                           image=self.main_window.images["fix"], text=translations["fix_button"],
                                           anchor="w", text_color=("gray10", "#DCE4EE"),
                                           command=self.fix_execution_event_handler)

    def help_pack(self):
        self.help_scrollable_frame.pack()
        self.help_title.pack()
        self.help_notice.pack()
        self.searchboxText.pack()
        self.search_box.pack(pady=10)
        self.class_list.pack()
        self.curriculumText.pack()
        self.curriculum.pack(pady=5)
        self.termsText.pack()
        self.termsTable.pack(expand=True, fill="both", padx=20, pady=20)
        self.filesText.pack()
        self.files.pack(pady=5)
        self.disableIdleText.pack()
        self.disableIdle.pack()
        self.fixText.pack()
        self.fix.pack(pady=5)

    # Set focus on the UI application window
    def set_focus_to_tkinter(self):
        window_handle = win32gui.FindWindow(None, "Tera Term UI")
        win32gui.SetForegroundWindow(window_handle)
        self.focus_force()
        self.lift()
        self.attributes("-topmost", 1)
        self.after_idle(self.attributes, "-topmost", 0)

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

    def preparing(self):
        self.focus_set()
        self.destroy_windows()
        self.hide_sidebar_windows()
        self.unbind("<Return>")


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
