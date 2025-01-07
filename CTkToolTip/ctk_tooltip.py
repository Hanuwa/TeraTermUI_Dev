"""
CTkToolTip Widget
version: 0.8
"""
import os
import time
import sys
import logging
import win32gui
import win32process
import customtkinter
from tkinter import Toplevel, Frame


class CTkToolTip(Toplevel):
    """
    Creates a ToolTip (pop-up) widget for customtkinter.
    """
    __slots__ = ("widget", "message", "delay", "follow", "x_offset", "y_offset", "bg_color", "corner_radius",
                 "border_width", "border_color", "alpha", "padding", "visibility", "disable")

    def __init__(
            self,
            widget: any = None,
            message: str = None,
            delay: float = 0.1,
            follow: bool = True,
            x_offset: int = +20,
            y_offset: int = +10,
            bg_color: str = None,
            corner_radius: int = 10,
            border_width: int = 0,
            border_color: str = None,
            alpha: float = 0.95,
            padding: tuple = (10, 2),
            visibility: bool = True,
            **message_kwargs):

        super().__init__()

        self.widget = widget
        self.title("TTUI Tooltip")

        self.withdraw()

        # Disable ToolTip's title bar
        self.overrideredirect(True)

        if sys.platform.startswith("win"):
            self.transparent_color = self.widget._apply_appearance_mode(
                customtkinter.ThemeManager.theme["CTkToplevel"]["fg_color"])
            self.attributes("-transparentcolor", self.transparent_color)
            self.transient()
        elif sys.platform.startswith("darwin"):
            self.transparent_color = 'systemTransparent'
            self.attributes("-transparent", True)
            self.transient(self.master)
        else:
            self.transparent_color = '#000001'
            corner_radius = 0
            self.transient()

        self.resizable(width=True, height=True)

        # Make the background transparent
        self.config(background=self.transparent_color)

        # StringVar instance for msg string
        self.messageVar = customtkinter.StringVar()
        self.message = message
        self.messageVar.set(self.message)

        self.delay = delay
        self.follow = follow
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.corner_radius = corner_radius
        self.alpha = alpha
        self.border_width = border_width
        self.padding = padding
        self.bg_color = customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"] if bg_color is None else bg_color
        self.border_color = border_color
        self.is_ctktooltip = True
        self.visibility = visibility  # Initialize visibility
        self.disable = not visibility  # Initialize disable attribute

        # visibility status of the ToolTip inside|outside|visible
        self.status = "outside"
        self.last_moved = 0
        self.attributes('-alpha', self.alpha)

        if sys.platform.startswith("win"):
            if self.widget._apply_appearance_mode(self.bg_color) == self.transparent_color:
                self.transparent_color = "#000001"
                self.config(background=self.transparent_color)
                self.attributes("-transparentcolor", self.transparent_color)

        # Add the message widget inside the tooltip
        self.transparent_frame = Frame(self, bg=self.transparent_color)
        self.transparent_frame.pack(padx=0, pady=0, fill="both", expand=True)

        self.frame = customtkinter.CTkFrame(self.transparent_frame, bg_color=self.transparent_color,
                                            corner_radius=self.corner_radius,
                                            border_width=self.border_width, fg_color=self.bg_color,
                                            border_color=self.border_color)
        self.frame.pack(padx=17, pady=17, fill="both", expand=True)

        self.message_label = customtkinter.CTkLabel(self.frame, textvariable=self.messageVar, **message_kwargs)
        self.message_label.pack(fill="both", padx=self.padding[0] + self.border_width,
                                pady=self.padding[1] + self.border_width, expand=True)

        if self.widget.winfo_name() != "tk":
            if self.frame.cget("fg_color") == self.widget.cget("bg_color"):
                if not bg_color:
                    self._top_fg_color = self.frame._apply_appearance_mode(
                        customtkinter.ThemeManager.theme["CTkFrame"]["top_fg_color"])
                    if self._top_fg_color != self.transparent_color:
                        self.frame.configure(fg_color=self._top_fg_color)

        # Add bindings to the widget without overriding the existing ones
        self.widget.bind("<Enter>", self.on_enter, add="+")
        self.widget.bind("<Leave>", self.on_leave, add="+")
        self.widget.bind("<Motion>", self.on_enter, add="+")
        self.widget.bind("<B1-Motion>", self.on_enter, add="+")
        self.widget.bind("<Destroy>", lambda _: self.hide(), add="+")
        self.main_win = widget.winfo_toplevel()
        self.main_win.bind("<FocusOut>", self.on_focus_out, add="+")

    def show(self) -> None:
        """
        Enable the widget.
        """
        self.visibility = True
        self.disable = False

    @staticmethod
    def find_context_menu():
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

    def on_enter(self, event) -> None:
        """
        Processes motion within the widget including entering and moving.
        """
        context_menu = self.find_context_menu()
        if self.disable or context_menu:
            return

        self.last_moved = time.time()
        if hasattr(self.widget, "is_pressed") and self.widget.is_pressed:
            self.widget._on_enter(event)
            self.widget.configure(cursor="hand2")

        # Set the status as inside for the very first time
        if self.status == "outside":
            self.status = "inside"

        # If the follow flag is not set, motion within the widget will make the ToolTip disappear
        if not self.follow:
            self.status = "inside"
            self.withdraw()

        if not self._is_mouse_inside_widget() and hasattr(self.widget, "is_pressed") and self.widget.is_pressed:
            self.status = "outside"
            self.withdraw()
            self.widget._on_leave(event)
            self.widget.configure(cursor="")

        # Calculate available space on the right side of the widget relative to the screen
        root_width = self.winfo_screenwidth()
        widget_x = event.x_root
        space_on_right = root_width - widget_x

        # Calculate the width of the tooltip's text based on the length of the message string
        text_width = self.message_label.winfo_reqwidth()

        # Calculate the offset based on available space and text width to avoid going off-screen on the right side
        offset_x = self.x_offset
        if space_on_right < text_width + 20:  # Adjust the threshold as needed
            offset_x = -text_width - 20  # Negative offset when space is limited on the right side

        self.geometry(f"+{event.x_root + offset_x - 17}+{event.y_root + self.y_offset - 17}")
        self.after(int(self.delay * 1000), self._show)

    def on_leave(self, event=None) -> None:
        """
        Hides the ToolTip temporarily.
        """
        main_win_status = self.widget.winfo_toplevel().attributes("-disabled") == 1
        if self.disable:
            return

        if not self._is_mouse_inside_widget() or not self.widget.winfo_ismapped() or main_win_status:
            self.status = "outside"
            self.withdraw()
            if hasattr(self.widget, "_on_leave"):
                self.widget._on_leave()


    def on_focus_out(self, event) -> None:
        """
        Hides the ToolTip when the main window loses focus.
        """
        if self.disable or not self.winfo_exists():
            return
        self.status = "outside"
        self.withdraw()

    def monitor_tooltip(self):
        """
        Continuously monitors the tooltip's state and mouse position to ensure proper behavior.
        """
        main_win_status = self.widget.winfo_toplevel().attributes("-disabled") == 1
        if self.status == "outside" or self.disable:
            return

        if not self._is_mouse_inside_widget() or not self.widget.winfo_ismapped() or main_win_status:
            self.status = "outside"
            self.withdraw()
            if hasattr(self.widget, "_on_leave"):
                self.widget._on_leave()

        self.after(25, self.monitor_tooltip)

    def _show(self) -> None:
        """
        Displays the ToolTip.
        """
        if not self.widget.winfo_exists():
            self.hide()
            self.destroy()

        if self.status == "inside" and time.time() - self.last_moved >= self.delay:
            # Check if the mouse is still within the widget's boundaries
            if self._is_mouse_inside_widget():
                self.monitor_tooltip()
                self.status = "visible"
                self.deiconify()
            else:
                self.on_leave()

    def _is_mouse_inside_widget(self) -> bool:
        """
        Checks if the mouse is inside the widget's area.
        """
        x, y = self.widget.winfo_pointerxy()
        widget_coords = (self.widget.winfo_rootx(), self.widget.winfo_rooty(),
                         self.widget.winfo_rootx() + self.widget.winfo_width(),
                         self.widget.winfo_rooty() + self.widget.winfo_height())

        return widget_coords[0] < x < widget_coords[2] and widget_coords[1] < y < widget_coords[3]


    def hide(self) -> None:
        """
        Disable the widget from appearing.
        """
        if not self.winfo_exists():
            return
        self.withdraw()
        self.disable = True

    def is_disabled(self) -> bool:
        """
        Return the window state.
        """
        return self.disable

    def get(self) -> str:
        """
        Returns the text on the tooltip.
        """
        return self.messageVar.get()

    def configure(self, message: str = None, delay: float = None, bg_color: str = None, visibility: bool = None, **kwargs) -> None:
        """
        Set new message or configure the label parameters.
        """
        if delay:
            self.delay = delay
        if bg_color:
            self.frame.configure(fg_color=bg_color)
        if visibility is not None:
            self.visibility = visibility
            if self.visibility:
                self.show()
            else:
                self.hide()

        self.messageVar.set(message)
        self.message_label.configure(**kwargs)

    def cget(self, option: str):
        """
        Get the value of the given configuration option.
        """
        options = {
            "message": self.messageVar.get(),
            "delay": self.delay,
            "bg_color": self.frame.cget("fg_color"),
            "visibility": self.visibility,
        }
        return options.get(option, None)

    def destroy(self) -> None:
        if self.widget is not None and self.widget.winfo_exists():
            self.widget.unbind("<Enter>")
            self.widget.unbind("<Leave>")
            self.widget.unbind("<Motion>")
            self.widget.unbind("<B1-Motion>")
            self.widget.unbind("<Destroy>")
        if self.message_label is not None:
            self.message_label.destroy()
            self.message_label = None
        if self.frame is not None:
            self.frame.destroy()
            self.frame = None
        if self.transparent_frame is not None:
            self.transparent_frame.destroy()
            self.transparent_frame = None
        super().destroy()
