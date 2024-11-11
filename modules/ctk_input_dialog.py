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


class CustomEntry(CTkEntry):
    __slots__ = ("master", "teraterm_ui_instance", "lang", "max_length")

    def __init__(self, master, teraterm_ui_instance, lang=None, max_length=250, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        initial_state = self.get()
        self.root = self.winfo_toplevel()
        self._undo_stack = deque([initial_state], maxlen=100)
        self._redo_stack = deque(maxlen=100)
        self.max_length = max_length
        self.lang = lang
        self.is_listbox_entry = False
        self.select = False
        self.border_color = None

        self.teraterm_ui = teraterm_ui_instance
        self.focus_out_bind_id = self.root.bind("<FocusOut>", self._on_window_focus_out, add="+")
        self.bind("<FocusIn>", self.disable_slider_keys)
        self.bind("<FocusOut>", self.enable_slider_keys)

        self.bind("<Control-z>", self.undo)
        self.bind("<Control-Z>", self.undo)
        self.bind("<Control-y>", self.redo)
        self.bind("<Control-Y>", self.redo)

        self.bind("<Control-v>", self.custom_paste)
        self.bind("<Control-V>", self.custom_paste)

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

    def _on_window_focus_out(self, event=None):
        if self.get() == "" or self.get().isspace():
            self._activate_placeholder()

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
            # Get states and find position of change
            current_text = self._undo_stack[-1]
            last_text = self._undo_stack.pop()
            self._redo_stack.append(last_text)
            previous_state = self._undo_stack[-1]

            change_position = 0
            min_len = min(len(current_text), len(previous_state))
            for i in range(min_len):
                if current_text[i] != previous_state[i]:
                    change_position = i
                    break
                change_position = i + 1

            if change_position == min_len:
                change_position = min_len

            # Apply changes and update cursor
            self.delete(0, "end")
            self.insert(0, previous_state, enforce_length_check=False)
            self.icursor(change_position)

            if self.cget("border_color") in ["#c30101", "#228B22"]:
                default_color = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"]
                self.configure(border_color=default_color)

            # Update view position
            if len(previous_state) > 0:
                visible_ratio = change_position / len(previous_state)
                self.xview_moveto(max(0.0, min(1.0, visible_ratio - 0.1)))

            if self.is_listbox_entry:
                self.update_listbox()

    def redo(self, event=None):
        if self._redo_stack:
            # Get states and find position of change
            current_text = self.get()
            state_to_redo = self._redo_stack.pop()
            self._undo_stack.append(state_to_redo)

            change_position = 0
            min_len = min(len(current_text), len(state_to_redo))
            for i in range(min_len):
                if current_text[i] != state_to_redo[i]:
                    change_position = i
                    break
                change_position = i + 1

            if change_position == min_len:
                change_position = min_len

            # Apply changes and calculate cursor position
            self.delete(0, "end")
            self.insert(0, state_to_redo, enforce_length_check=False)

            new_cursor_position = (change_position + (len(state_to_redo) - len(current_text))
                                 if len(state_to_redo) > len(current_text)
                                 else change_position)
            self.icursor(new_cursor_position)

            if self.cget("border_color") in ["#c30101", "#228B22"]:
                default_color = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"]
                self.configure(border_color=default_color)

            # Calculate view position based on entry width
            entry_width = self.winfo_width()
            visible_chars = entry_width // 8  # Approximate character width of 8 pixels

            if len(state_to_redo) > visible_chars:
                chars_before_cursor = visible_chars // 2
                start_pos = max(0, new_cursor_position - chars_before_cursor)
                if start_pos + visible_chars > len(state_to_redo):
                    start_pos = max(0, len(state_to_redo) - visible_chars)
                self.xview_moveto(start_pos / len(state_to_redo))
            else:
                self.xview_moveto(0)

            if self.is_listbox_entry:
                self.update_listbox()

    def custom_middle_mouse(self, event=None):
        if self.select_present():
            char_index = self.index("@%d" % event.x)
            self.icursor(char_index)
            self.select_clear()
            return "break"

    def find_active_tooltips(self, widget):
        if isinstance(widget, tk.Toplevel) and hasattr(widget, "is_ctktooltip"):
            widget.on_focus_out(event=None)
        for child in widget.winfo_children():
            self.find_active_tooltips(child)

    def show_menu(self, event):
        if self.cget("state") == "disabled":
            return

        self.focus_set()
        root = self.winfo_toplevel()
        self.find_active_tooltips(root)
        self.icursor(tk.END)
        self.select = True

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
            self._redo_stack.clear()

            if self.is_listbox_entry:
                self.update_listbox()
        except tk.TclError:
            print("No text selected to cut")

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
            print("No text selected to copy")

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
                print("Pasted content truncated to maximum length")

            current_text = self.get()
            # Save the current state to undo stack
            if len(self._undo_stack) == 0 or (len(self._undo_stack) > 0 and current_text != self._undo_stack[-1]):
                self._undo_stack.append(current_text)

            insert_index = self.index(tk.INSERT)
            try:
                start_index = self.index(tk.SEL_FIRST)
                end_index = self.index(tk.SEL_LAST)
                self.delete(start_index, end_index)
                insert_index = start_index
            except tk.TclError:
                pass  # Nothing selected, which is fine

            space_left = self.max_length - len(current_text)
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
                print("Input limited to the maximum allowed length")
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
        self.root.unbind("<FocusOut>", self.focus_out_bind_id)
        self.focus_out_bind_id = None
        self.max_length = None
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
