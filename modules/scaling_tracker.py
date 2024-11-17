import tkinter
import sys
from weakref import WeakKeyDictionary
from typing import Callable


class ScalingTracker:
    deactivate_automatic_dpi_awareness = False

    # Contains window objects as keys with list of widget callbacks as elements
    window_widgets_dict = WeakKeyDictionary()
    # Contains window objects as keys and corresponding scaling factors
    window_dpi_scaling_dict = WeakKeyDictionary()
    # Cache for storing window roots of widgets
    window_root_cache = WeakKeyDictionary()
    # Cache for storing calculated scaling values
    scaling_cache = WeakKeyDictionary()

    widget_scaling = 1.0  # User-defined scaling factor for widgets
    window_scaling = 1.0  # User-defined scaling factor for windows

    update_loop_running = False
    update_loop_interval = 500  # ms
    loop_pause_after_new_scaling = 1500  # ms

    @classmethod
    def get_widget_scaling(cls, widget) -> float:
        scaling = cls.scaling_cache.get(widget)
        if scaling is None:
            window_root = cls.get_window_root_of_widget(widget)
            window_scaling = cls.window_dpi_scaling_dict.get(window_root, 1.0)
            scaling = window_scaling * cls.widget_scaling
            cls.scaling_cache[widget] = scaling
        return scaling

    @classmethod
    def get_window_scaling(cls, window) -> float:
        scaling = cls.scaling_cache.get(window)
        if scaling is None:
            window_root = cls.get_window_root_of_widget(window)
            window_scaling = cls.window_dpi_scaling_dict.get(window_root, 1.0)
            scaling = window_scaling * cls.window_scaling
            cls.scaling_cache[window] = scaling
        return scaling

    @classmethod
    def set_widget_scaling(cls, widget_scaling_factor: float):
        cls.widget_scaling = max(widget_scaling_factor, 0.4)
        cls.scaling_cache.clear()
        cls.update_scaling_callbacks_all()

    @classmethod
    def set_window_scaling(cls, window_scaling_factor: float):
        cls.window_scaling = max(window_scaling_factor, 0.4)
        cls.scaling_cache.clear()
        cls.update_scaling_callbacks_all()

    @classmethod
    def get_window_root_of_widget(cls, widget):
        window_root = cls.window_root_cache.get(widget)
        if window_root is None:
            current_widget = widget
            while not isinstance(current_widget, (tkinter.Tk, tkinter.Toplevel)):
                current_widget = current_widget.master
                if current_widget is None:
                    break
            cls.window_root_cache[widget] = current_widget
            window_root = current_widget
        return window_root

    @classmethod
    def update_scaling_callbacks_all(cls):
        deactivate_dpi_awareness = cls.deactivate_automatic_dpi_awareness
        widget_scaling = cls.widget_scaling
        window_scaling = cls.window_scaling

        for window, callback_list in list(cls.window_widgets_dict.items()):
            window_scaling_factor = cls.window_dpi_scaling_dict.get(window, 1.0)
            total_widget_scaling = window_scaling_factor * widget_scaling if not deactivate_dpi_awareness else widget_scaling
            total_window_scaling = window_scaling_factor * window_scaling if not deactivate_dpi_awareness else window_scaling

            new_callback_list = []
            for callback in callback_list:
                widget = getattr(callback, '__self__', None)
                if widget and widget.winfo_exists():
                    try:
                        callback(total_widget_scaling, total_window_scaling)
                        new_callback_list.append(callback)
                    except tkinter.TclError:
                        pass  # Widget might have been destroyed
            cls.window_widgets_dict[window] = new_callback_list

    @classmethod
    def update_scaling_callbacks_for_window(cls, window):
        deactivate_dpi_awareness = cls.deactivate_automatic_dpi_awareness
        widget_scaling = cls.widget_scaling
        window_scaling = cls.window_scaling

        callback_list = cls.window_widgets_dict.get(window, [])
        window_scaling_factor = cls.window_dpi_scaling_dict.get(window, 1.0)
        total_widget_scaling = window_scaling_factor * widget_scaling if not deactivate_dpi_awareness else widget_scaling
        total_window_scaling = window_scaling_factor * window_scaling if not deactivate_dpi_awareness else window_scaling

        for callback in callback_list:
            try:
                callback(total_widget_scaling, total_window_scaling)
            except tkinter.TclError:
                pass  # Widget might have been destroyed

    @classmethod
    def add_widget(cls, widget_callback: Callable, widget):
        window_root = cls.get_window_root_of_widget(widget)
        if window_root is None:
            return  # Cannot find window root; skip adding

        callback_list = cls.window_widgets_dict.setdefault(window_root, [])
        callback_list.append(widget_callback)

        if window_root not in cls.window_dpi_scaling_dict:
            cls.window_dpi_scaling_dict[window_root] = cls.get_window_dpi_scaling(window_root)

        if not cls.update_loop_running:
            window_root.after(100, cls.check_dpi_scaling)
            cls.update_loop_running = True

    @classmethod
    def remove_widget(cls, widget_callback: Callable, widget):
        window_root = cls.get_window_root_of_widget(widget)
        if window_root is None:
            return  # Cannot find window root; nothing to remove

        callback_list = cls.window_widgets_dict.get(window_root)
        if callback_list and widget_callback in callback_list:
            callback_list.remove(widget_callback)
            if not callback_list:
                del cls.window_widgets_dict[window_root]
                cls.window_dpi_scaling_dict.pop(window_root, None)

    @classmethod
    def remove_window(cls, window_callback: Callable, window):
        callback_list = cls.window_widgets_dict.get(window)
        if callback_list and window_callback in callback_list:
            callback_list.remove(window_callback)
            if not callback_list:
                del cls.window_widgets_dict[window]
                cls.window_dpi_scaling_dict.pop(window, None)

    @classmethod
    def add_window(cls, window_callback: Callable, window):
        callback_list = cls.window_widgets_dict.setdefault(window, [])
        callback_list.append(window_callback)

        if window not in cls.window_dpi_scaling_dict:
            cls.window_dpi_scaling_dict[window] = cls.get_window_dpi_scaling(window)

    @classmethod
    def activate_high_dpi_awareness(cls):
        """Make process DPI aware; custom elements will get scaled automatically."""
        if not cls.deactivate_automatic_dpi_awareness:
            if sys.platform == "darwin":
                pass  # High DPI scaling works automatically on macOS
            elif sys.platform.startswith("win"):
                import ctypes
                try:
                    # Windows 10 Anniversary Update and later
                    DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
                    ctypes.windll.user32.SetProcessDpiAwarenessContext(
                        ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2))
                except AttributeError:
                    # Fallback for older Windows versions
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
            # For Linux and other platforms, DPI awareness may not be applicable

    @classmethod
    def get_window_dpi_scaling(cls, window) -> float:
        if cls.deactivate_automatic_dpi_awareness:
            return 1.0

        if sys.platform == "darwin":
            return 1.0  # Scaling works automatically on macOS

        elif sys.platform.startswith("win"):
            try:
                from ctypes import windll, pointer, wintypes

                DPI100pc = 96  # DPI 96 is 100% scaling
                DPI_type = 0  # MDT_EFFECTIVE_DPI = 0
                window_hwnd = wintypes.HWND(window.winfo_id())
                monitor_handle = windll.user32.MonitorFromWindow(
                    window_hwnd, wintypes.DWORD(2))  # MONITOR_DEFAULTTONEAREST = 2
                x_dpi = wintypes.UINT()
                y_dpi = wintypes.UINT()
                windll.shcore.GetDpiForMonitor(
                    monitor_handle, DPI_type, pointer(x_dpi), pointer(y_dpi))
                return (x_dpi.value + y_dpi.value) / (2 * DPI100pc)
            except Exception:
                return 1.0  # Default scaling if DPI retrieval fails
        else:
            return 1.0  # DPI awareness on Linux not implemented

    @classmethod
    def check_dpi_scaling(cls):
        new_scaling_detected = False

        # Avoid modifying the dictionary during iteration
        window_items = list(cls.window_widgets_dict.items())
        for window, _ in window_items:
            if window.winfo_exists() and window.state() != "iconic":
                current_dpi_scaling_value = cls.get_window_dpi_scaling(window)
                previous_scaling = cls.window_dpi_scaling_dict.get(window, 1.0)
                if current_dpi_scaling_value != previous_scaling:
                    cls.window_dpi_scaling_dict[window] = current_dpi_scaling_value
                    cls.scaling_cache.clear()  # Clear cache when scaling changes
                    cls.update_scaling_callbacks_for_window(window)
                    new_scaling_detected = True

        # Schedule the next check
        if new_scaling_detected:
            interval = cls.loop_pause_after_new_scaling
        else:
            interval = cls.update_loop_interval

        # Use any existing window to schedule the next call
        for window in cls.window_widgets_dict.keys():
            if window.winfo_exists():
                window.after(interval, cls.check_dpi_scaling)
                return

        cls.update_loop_running = False  # No windows left; stop the loop
