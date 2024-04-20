import tkinter as tk

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
        self.after(10, self._create_widgets)  # create widgets with slight delay, to avoid white flickering of background
        self.resizable(False, False)
        self.transient(master)
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
        self._label.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="ew")

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
        if self.is_mouse_over_widget() and not event.widget == self._text_label \
                and not event.widget == self._image_label:
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
        super().destroy()


class CustomEntry(CTkEntry):
    __slots__ = ("master", "teraterm_ui_instance", "lang")

    def __init__(self, master, teraterm_ui_instance, lang=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        initial_state = self.get()
        self._undo_stack = deque([initial_state], maxlen=25)
        self._redo_stack = deque(maxlen=25)
        self.lang = lang
        self.is_listbox_entry = False
        self.select = False

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
            max_paste_length = 1000  # Set a limit for the max paste length
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
