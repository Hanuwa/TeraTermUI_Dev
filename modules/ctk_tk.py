import tkinter
import sys
import os
import platform
import ctypes
import weakref
from typing import Union, Tuple, Optional
from packaging import version

from .widgets.theme import ThemeManager
from .widgets.scaling import CTkScalingBaseClass
from .widgets.appearance_mode import CTkAppearanceModeBaseClass

from customtkinter.windows.widgets.utility.utility_functions import pop_from_dict_by_set, check_kwargs_empty

CTK_PARENT_CLASS = tkinter.Tk


class CTk(CTK_PARENT_CLASS, CTkAppearanceModeBaseClass, CTkScalingBaseClass):
    """
    Main app window with dark titlebar on Windows and macOS.
    For detailed information check out the documentation.
    """

    _valid_tk_constructor_arguments = frozenset({"screenName", "baseName", "className", "useTk", "sync", "use"})

    _valid_tk_configure_arguments = frozenset({'bd', 'borderwidth', 'class', 'menu', 'relief', 'screen',
                                               'use', 'container', 'cursor', 'height', 'highlightthickness',
                                               'padx', 'pady', 'takefocus', 'visual', 'width'})

    _deactivate_macos_window_header_manipulation: bool = False
    _deactivate_windows_window_header_manipulation: bool = False

    def __init__(self,
                 fg_color: Optional[Union[str, Tuple[str, str]]] = None,
                 **kwargs):

        valid_args = pop_from_dict_by_set(kwargs, self._valid_tk_constructor_arguments)
        self._enable_macos_dark_title_bar()

        # call init methods of super classes
        CTK_PARENT_CLASS.__init__(self, **valid_args)
        CTkAppearanceModeBaseClass.__init__(self)
        CTkScalingBaseClass.__init__(self, scaling_type="window")
        check_kwargs_empty(kwargs, raise_error=True)

        self._current_width = 600  # initial window size, independent of scaling
        self._current_height = 500
        self._min_width: int = 0
        self._min_height: int = 0
        self._max_width: int = 1_000_000
        self._max_height: int = 1_000_000
        self._last_resizable_args: Union[Tuple[list, dict], None] = None  # (args, kwargs)

        self._fg_color = ThemeManager.theme["CTk"]["fg_color"] if fg_color is None else self._check_color_type(fg_color)

        # set bg of tkinter.Tk
        super().configure(bg=self._apply_appearance_mode(self._fg_color))

        # set title
        self.title("CTk")

        self._is_windows = sys.platform.startswith("win")
        self._is_macos = sys.platform == "darwin"
        self._resize_after_id = None

        # indicator variables
        self._iconbitmap_method_called = False  # indicates if wm_iconbitmap method got called
        self._state_before_windows_set_titlebar_color = None
        self._window_exists = False  # indicates if the window is already shown through update() or mainloop() after init
        self._withdraw_called_before_window_exists = False  # indicates if withdraw() was called before window is first shown through update() or mainloop()
        self._iconify_called_before_window_exists = False  # indicates if iconify() was called before window is first shown through update() or mainloop()
        self._block_update_dimensions_event = False

        # save focus before calling withdraw
        self.focused_widget_before_widthdraw = None

        # set CustomTkinter titlebar icon (Windows only)
        if self._is_windows:
            self.after(200, self._windows_set_titlebar_icon)

        # set titlebar color (Windows only)
        if self._is_windows:
            self._windows_set_titlebar_color(self._get_appearance_mode())

        self.bind('<Configure>', self._update_dimensions_event)
        self.bind('<FocusIn>', self._focus_in_event)

    def destroy(self):
        self._disable_macos_dark_title_bar()

        if self._resize_after_id:
            try:
                self.after_cancel(self._resize_after_id)
            except ValueError:
                pass
            self._resize_after_id = None

        self.unbind('<Configure>')
        self.unbind('<FocusIn>')

        # call destroy methods of super classes
        super().destroy()
        CTkAppearanceModeBaseClass.destroy(self)
        CTkScalingBaseClass.destroy(self)

    def _focus_in_event(self, event):
        # sometimes window looses jumps back on macOS if window is selected from Mission Control, so has to be lifted again
        if self._is_macos:
            self.lift()

    def _update_dimensions_event(self, event=None):
        if not self._block_update_dimensions_event:
            if self._resize_after_id is not None:
                self.after_cancel(self._resize_after_id)
                self._resize_after_id = None
            self._resize_after_id = self.after(100, self._perform_dimension_update)

    def _perform_dimension_update(self):
        detected_width = super().winfo_width()
        detected_height = super().winfo_height()
        new_width = self._reverse_window_scaling(detected_width)
        new_height = self._reverse_window_scaling(detected_height)
        if self._current_width != new_width or self._current_height != new_height:
            self._current_width = new_width
            self._current_height = new_height

    def _set_scaling(self, new_widget_scaling, new_window_scaling):
        super()._set_scaling(new_widget_scaling, new_window_scaling)

        # Force new dimensions on window by using min, max, and geometry. Without min, max it won't work.
        super().minsize(self._apply_window_scaling(self._current_width), self._apply_window_scaling(self._current_height))
        super().maxsize(self._apply_window_scaling(self._current_width), self._apply_window_scaling(self._current_height))

        super().geometry(f"{self._apply_window_scaling(self._current_width)}x{self._apply_window_scaling(self._current_height)}")

        # set new scaled min and max with delay (delay prevents weird bug where window dimensions snap to unscaled dimensions when mouse releases window)
        self.after(1000, self._set_scaled_min_max)  # Why 1000ms delay? Experience! (Everything tested on Windows 11)

    def block_update_dimensions_event(self):
        self._block_update_dimensions_event = False

    def unblock_update_dimensions_event(self):
        self._block_update_dimensions_event = False

    def _set_scaled_min_max(self):
        if self._min_width is not None or self._min_height is not None:
            super().minsize(self._apply_window_scaling(self._min_width), self._apply_window_scaling(self._min_height))
        if self._max_width is not None or self._max_height is not None:
            super().maxsize(self._apply_window_scaling(self._max_width), self._apply_window_scaling(self._max_height))

    def withdraw(self):
        if self._window_exists is False:
            self._withdraw_called_before_window_exists = True
        super().withdraw()

    def iconify(self):
        if self._window_exists is False:
            self._iconify_called_before_window_exists = True
        super().iconify()

    def update(self):
        if not self._window_exists and self._is_windows:
            if not (self._withdraw_called_before_window_exists or
                    self._iconify_called_before_window_exists):
                self.deiconify()
            self._window_exists = True
        super().update()

    def mainloop(self, *args, **kwargs):
        if not self._window_exists:
            if self._is_windows:
                self._windows_set_titlebar_color(self._get_appearance_mode())
                if not (self._withdraw_called_before_window_exists or
                        self._iconify_called_before_window_exists):
                    self.deiconify()
            self._window_exists = True
        super().mainloop(*args, **kwargs)

    def resizable(self, width: bool = None, height: bool = None):
        current_resizable_values = super().resizable(width, height)
        self._last_resizable_args = ([], {"width": width, "height": height})

        if self._is_windows:
            self._windows_set_titlebar_color(self._get_appearance_mode())

        return current_resizable_values

    def minsize(self, width: int = None, height: int = None):
        self._min_width = width
        self._min_height = height
        if self._current_width < width:
            self._current_width = width
        if self._current_height < height:
            self._current_height = height
        super().minsize(self._apply_window_scaling(self._min_width), self._apply_window_scaling(self._min_height))

    def maxsize(self, width: int = None, height: int = None):
        self._max_width = width
        self._max_height = height
        if self._current_width > width:
            self._current_width = width
        if self._current_height > height:
            self._current_height = height
        super().maxsize(self._apply_window_scaling(self._max_width), self._apply_window_scaling(self._max_height))

    def geometry(self, geometry_string: str = None):
        if geometry_string is not None:
            super().geometry(self._apply_geometry_scaling(geometry_string))

            # update width and height attributes
            width, height, x, y = self._parse_geometry_string(geometry_string)
            if width is not None and height is not None:
                self._current_width = max(self._min_width, min(width, self._max_width))  # bound value between min and max
                self._current_height = max(self._min_height, min(height, self._max_height))
        else:
            return self._reverse_geometry_scaling(super().geometry())

    def configure(self, **kwargs):
        if "fg_color" in kwargs:
            self._fg_color = self._check_color_type(kwargs.pop("fg_color"))
            super().configure(bg=self._apply_appearance_mode(self._fg_color))
            for child in self.winfo_children():
                if isinstance(child, CTkBaseWidget):
                    child.configure(bg_color=self._fg_color)

        super().configure(**pop_from_dict_by_set(kwargs, self._valid_tk_configure_arguments))
        check_kwargs_empty(kwargs)

    def cget(self, attribute_name: str) -> any:
        if attribute_name == "fg_color":
            return self._fg_color
        else:
            return super().cget(attribute_name)

    def wm_iconbitmap(self, bitmap=None, default=None):
        self._iconbitmap_method_called = True
        super().wm_iconbitmap(bitmap, default)

    def iconbitmap(self, bitmap=None, default=None):
        self._iconbitmap_method_called = True
        super().wm_iconbitmap(bitmap, default)

    def _windows_set_titlebar_icon(self):
        try:
            # if not the user already called iconbitmap method, set icon
            if not self._iconbitmap_method_called:
                customtkinter_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                self.iconbitmap(os.path.join(customtkinter_directory, "assets", "icons", "CustomTkinter_icon_Windows.ico"))
        except Exception:
            pass

    @classmethod
    def _enable_macos_dark_title_bar(cls):
        if sys.platform == "darwin" and not cls._deactivate_macos_window_header_manipulation:  # macOS
            if version.parse(platform.python_version()) < version.parse("3.10"):
                if version.parse(tkinter.Tcl().call("info", "patchlevel")) >= version.parse("8.6.9"):  # Tcl/Tk >= 8.6.9
                    os.system("defaults write -g NSRequiresAquaSystemAppearance -bool No")
                    # This command allows dark-mode for all programs

    @classmethod
    def _disable_macos_dark_title_bar(cls):
        if sys.platform == "darwin" and not cls._deactivate_macos_window_header_manipulation:  # macOS
            if version.parse(platform.python_version()) < version.parse("3.10"):
                if version.parse(tkinter.Tcl().call("info", "patchlevel")) >= version.parse("8.6.9"):  # Tcl/Tk >= 8.6.9
                    os.system("defaults delete -g NSRequiresAquaSystemAppearance")
                    # This command reverts the dark-mode setting for all programs.

    def _windows_set_titlebar_color(self, color_mode: str):
        """
        Set the titlebar color of the window to light or dark theme on Microsoft Windows.

        Credits for this function:
        https://stackoverflow.com/questions/23836000/can-i-change-the-title-bar-in-tkinter/70724666#70724666

        MORE INFO:
        https://docs.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute
        """

        if not self._is_windows or self._deactivate_windows_window_header_manipulation:
            return

        if self._window_exists:
            self._state_before_windows_set_titlebar_color = self.state()
            if self._state_before_windows_set_titlebar_color not in ("iconic", "withdrawn"):
                self.focused_widget_before_widthdraw = weakref.proxy(self.focus_get()) if self.focus_get() else None
                super().withdraw()
        else:
            self.focused_widget_before_widthdraw = weakref.proxy(self.focus_get()) if self.focus_get() else None
            super().withdraw()
            super().update()

        value = 1 if color_mode.lower() == "dark" else 0 if color_mode.lower() == "light" else None
        if value is None:
            return

        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            try:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 20,  # DWMWA_USE_IMMERSIVE_DARK_MODE
                    ctypes.byref(ctypes.c_int(value)),
                    ctypes.sizeof(ctypes.c_int(value))
                )
            except Exception:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 19,  # DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1
                    ctypes.byref(ctypes.c_int(value)),
                    ctypes.sizeof(ctypes.c_int(value))
                )
        except Exception:
            pass

        if self._window_exists:
            state = self._state_before_windows_set_titlebar_color
            if state == "normal":
                self.deiconify()
            elif state == "iconic":
                self.iconify()
            elif state == "zoomed":
                self.state("zoomed")
            else:
                self.state(state)

        if self.focused_widget_before_widthdraw:
            self.after(1,
                       lambda: self.focused_widget_before_widthdraw.focus() if self.focused_widget_before_widthdraw else None)
            self.focused_widget_before_widthdraw = None

    def _set_appearance_mode(self, mode_string: str):
        CTkAppearanceModeBaseClass._set_appearance_mode(self, mode_string)
        if self._is_windows:
            self._windows_set_titlebar_color(mode_string)
        elif self._is_macos:
            self._enable_macos_dark_title_bar()
        self.configure(bg=self._apply_appearance_mode(self._fg_color))
