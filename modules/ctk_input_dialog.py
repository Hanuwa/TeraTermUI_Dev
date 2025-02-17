import tkinter as tk
import os
import logging
import pyperclip
import win32gui
import weakref

from typing import Union, Tuple, Optional

from .widgets import CTkLabel
from .widgets import CTkEntry
from .widgets import CTkButton
from .widgets.theme import ThemeManager
from .ctk_toplevel import CTkToplevel
from .widgets.font import CTkFont
from collections import deque


class CTkInputDialog(CTkToplevel):
    """
    Dialog with extra window, message, entry widget, cancel and ok button.
    For detailed information check out the documentation.
    """

    def __init__(self,
                 master: any = None,
                 fg_color: Optional[Union[str, Tuple[str, str]]] = None,
                 text_color: Optional[Union[str, Tuple[str, str]]] = None,
                 button_fg_color: Optional[Union[str, Tuple[str, str]]] = None,
                 button_hover_color: Optional[Union[str, Tuple[str, str]]] = None,
                 button_text_color: Optional[Union[str, Tuple[str, str]]] = None,
                 entry_fg_color: Optional[Union[str, Tuple[str, str]]] = None,
                 entry_border_color: Optional[Union[str, Tuple[str, str]]] = None,
                 entry_text_color: Optional[Union[str, Tuple[str, str]]] = None,
                 lang: str = 'English',
                 ok_text: str = 'Ok',
                 cancel_text: str = 'Cancel',
                 title: str = "CTkDialog",
                 font: Optional[Union[tuple, CTkFont]] = None,
                 text: str = "CTkDialog"):

        super().__init__(fg_color=fg_color)

        self._fg_color = ThemeManager.theme["CTkToplevel"]["fg_color"] if fg_color is None else self._check_color_type(fg_color)
        self._text_color = ThemeManager.theme["CTkLabel"]["text_color"] if text_color is None else self._check_color_type(button_hover_color)
        self._button_fg_color = ThemeManager.theme["CTkButton"]["fg_color"] if button_fg_color is None else self._check_color_type(button_fg_color)
        self._button_hover_color = ThemeManager.theme["CTkButton"]["hover_color"] if button_hover_color is None else self._check_color_type(button_hover_color)
        self._button_text_color = ThemeManager.theme["CTkButton"]["text_color"] if button_text_color is None else self._check_color_type(button_text_color)
        self._entry_fg_color = ThemeManager.theme["CTkEntry"]["fg_color"] if entry_fg_color is None else self._check_color_type(entry_fg_color)
        self._entry_border_color = ThemeManager.theme["CTkEntry"]["border_color"] if entry_border_color is None else self._check_color_type(entry_border_color)
        self._entry_text_color = ThemeManager.theme["CTkEntry"]["text_color"] if entry_text_color is None else self._check_color_type(entry_text_color)

        self._user_input: Union[str, None] = None
        self._running: bool = False
        self._title = title
        self._text = text
        self._font = font
        self._lang = lang
        self._ok_text = ok_text
        self._cancel_text = cancel_text

        self.title(self._title)
        self.lift()  # lift window on top
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._create_widgets()
        self.resizable(False, False)
        self.transient(master)
        self.geometry("325x165")
        self.grab_set()  # make other windows not clickable

    def _create_widgets(self):
        self.grid_columnconfigure((0, 1), weight=1)
        self.rowconfigure(0, weight=1)

        self._label = CTkLabel(master=self,
                               width=300,
                               wraplength=300,
                               fg_color="transparent",
                               text_color=self._text_color,
                               text=self._text,
                               font=self._font)
        self._label.grid(row=0, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="ew")

        self._entry = CustomEntry(self, self,
                                  lang=self._lang,
                                  width=230,
                                  fg_color=self._entry_fg_color,
                                  border_color=self._entry_border_color,
                                  text_color=self._entry_text_color,
                                  font=self._font)
        self._entry.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")

        self._ok_button = CustomButton(master=self,
                                       width=100,
                                       border_width=0,
                                       fg_color=self._button_fg_color,
                                       hover_color=self._button_hover_color,
                                       text_color=self._button_text_color,
                                       text=self._ok_text,
                                       font=self._font,
                                       command=self._ok_event)
        self._ok_button.grid(row=2, column=0, columnspan=1, padx=(20, 10), pady=(0, 20), sticky="ew")

        self._cancel_button = CustomButton(master=self,
                                            width=100,
                                            border_width=0,
                                            fg_color=self._button_fg_color,
                                            hover_color=self._button_hover_color,
                                            text_color=self._button_text_color,
                                            text=self._cancel_text,
                                            font=self._font,
                                            command=self._cancel_event)
        self._cancel_button.grid(row=2, column=1, columnspan=1, padx=(10, 20), pady=(0, 20), sticky="ew")

        self.after(150, lambda: self._entry.focus())  # set focus to entry with slight delay, otherwise it won't work
        self._entry.bind("<Return>", self._ok_event)

    def _ok_event(self, event=None):
        self._user_input = self._entry.get()
        self.grab_release()
        self.destroy()

    def _on_closing(self):
        self.grab_release()
        self.destroy()

    def _cancel_event(self):
        self.grab_release()
        self.destroy()

    def get_input(self):
        self.master.wait_window(self)
        return self._user_input


class CustomButton(CTkButton):
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
        bindings = [("<ButtonPress-1>", self.on_button_down), ("<ButtonRelease-1>", self.on_button_up)]
        if not (self.image and not self.text):
            bindings.extend([("<Enter>", self.on_enter), ("<Motion>", self.on_enter), ("<Leave>", self.on_leave),
                             ("<B1-Motion>", self.on_motion)])
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


class CustomEntry(CTkEntry):
    __slots__ = ("master", "teraterm_ui", "lang", "max_length", "is_listbox_entry", "selected_text", "border_color",
                 "focus_out_bind_id", "context_menu", "bindings", "_undo_stack", "_redo_stack")

    def __init__(self, master, teraterm_ui_instance, lang=None, max_length=250, *args, **kwargs):
        if "cursor" not in CTkEntry._valid_tk_entry_attributes:
            CTkEntry._valid_tk_entry_attributes.add("cursor")
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
        self.setup_context_menu()

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
        context_menu = self.find_context_menu()
        if context_menu:
            return "break"
        if self.select_present():
            char_index = self.index("@%d" % event.x)
            self.icursor(char_index)
            self.select_clear()
            return "break"

    def setup_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0, font=("Arial", 10),
                                    relief="flat", background="gray40", fg="snow")
        menu_items = [("Cut", lambda: self.cut()), ("Copy", lambda: self.copy()), ("Paste", lambda: self.paste()),
                      ("Select All", lambda: self.select_all()), ("Undo", lambda: self.undo()),
                      ("Redo", lambda: self.redo())]
        for label, command in menu_items:
            self.context_menu.add_command(label=label, command=command)

    def show_menu(self, event):
        if self.cget("state") == "disabled":
            return

        self.focus_set()
        self.selected_text = True

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
                               disabledforeground=self._apply_appearance_mode(self._placeholder_text_color),
                               show="")
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
