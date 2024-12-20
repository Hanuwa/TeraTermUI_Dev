import tkinter
import sys
from weakref import WeakKeyDictionary
from typing import Callable
from functools import lru_cache


class ScalingTracker:
    deactivate_automatic_dpi_awareness = False

    # Contains window objects as keys with list of widget callbacks as elements
    window_widgets_dict = WeakKeyDictionary()
    # Contains window objects as keys and corresponding scaling factors
    window_dpi_scaling_dict = WeakKeyDictionary()
    # Cache for storing window roots of widgets
    window_root_cache = WeakKeyDictionary()

    widget_scaling = 1.0  # User-defined scaling factor for widgets
    window_scaling = 1.0  # User-defined scaling factor for windows

    update_loop_running = False
    update_loop_interval = 500  # ms
    loop_pause_after_new_scaling = 1500  # ms

    # Class constants
    WINDOW_TYPES = (tkinter.Tk, tkinter.Toplevel)
    DPI_100_PERCENT = 96  # DPI 96 is 100% scaling
    DPI_TYPE_EFFECTIVE = 0  # MDT_EFFECTIVE_DPI = 0
    MONITOR_DEFAULT_NEAREST = 2

    @classmethod
    @lru_cache(maxsize=128)
    def get_widget_scaling(cls, widget) -> float:
        """Get the scaling factor for a widget with built-in caching."""
        window_root = cls.get_window_root_of_widget(widget)
        window_scaling = cls.window_dpi_scaling_dict.get(window_root, 1.0)
        return window_scaling * cls.widget_scaling

    @classmethod
    @lru_cache(maxsize=128)
    def get_window_scaling(cls, window) -> float:
        """Get the scaling factor for a window with built-in caching."""
        window_root = cls.get_window_root_of_widget(window)
        window_scaling = cls.window_dpi_scaling_dict.get(window_root, 1.0)
        return window_scaling * cls.window_scaling

    @classmethod
    def set_widget_scaling(cls, widget_scaling_factor: float):
        """Set the widget scaling factor and update all callbacks."""
        cls.widget_scaling = max(widget_scaling_factor, 0.4)
        cls.get_widget_scaling.cache_clear()
        cls.get_window_scaling.cache_clear()
        cls.update_scaling_callbacks_all()

    @classmethod
    def set_window_scaling(cls, window_scaling_factor: float):
        """Set the window scaling factor and update all callbacks."""
        cls.window_scaling = max(window_scaling_factor, 0.4)
        cls.get_widget_scaling.cache_clear()
        cls.get_window_scaling.cache_clear()
        cls.update_scaling_callbacks_all()

    @classmethod
    def get_window_root_of_widget(cls, widget):
        """Get the root window of a widget with optimized lookup."""
        try:
            return cls.window_root_cache[widget]
        except KeyError:
            current_widget = widget
            try:
                while not isinstance(current_widget, cls.WINDOW_TYPES):
                    current_widget = current_widget.master
            except AttributeError:
                current_widget = None
            cls.window_root_cache[widget] = current_widget
            return current_widget

    @classmethod
    def update_scaling_callbacks_all(cls):
        """Update all scaling callbacks with optimized performance."""
        if not cls.window_widgets_dict:
            return

        deactivate_dpi_awareness = cls.deactivate_automatic_dpi_awareness
        base_widget_scaling = cls.widget_scaling
        base_window_scaling = cls.window_scaling

        def calculate_scaling(window_scaling_factor):
            if deactivate_dpi_awareness:
                return base_widget_scaling, base_window_scaling
            return (window_scaling_factor * base_widget_scaling,
                    window_scaling_factor * base_window_scaling)

        for window, callback_list in list(cls.window_widgets_dict.items()):
            window_scaling_factor = cls.window_dpi_scaling_dict.get(window, 1.0)
            total_widget_scaling, total_window_scaling = calculate_scaling(window_scaling_factor)

            valid_callbacks = []
            for callback in callback_list:
                widget = getattr(callback, '__self__', None)
                if widget and widget.winfo_exists():
                    try:
                        callback(total_widget_scaling, total_window_scaling)
                        valid_callbacks.append(callback)
                    except tkinter.TclError:
                        continue
            cls.window_widgets_dict[window] = valid_callbacks

    @classmethod
    def update_scaling_callbacks_for_window(cls, window):
        """Update scaling callbacks for a specific window."""
        callback_list = cls.window_widgets_dict.get(window, [])
        if not callback_list:
            return

        deactivate_dpi_awareness = cls.deactivate_automatic_dpi_awareness
        window_scaling_factor = cls.window_dpi_scaling_dict.get(window, 1.0)

        if deactivate_dpi_awareness:
            total_widget_scaling = cls.widget_scaling
            total_window_scaling = cls.window_scaling
        else:
            total_widget_scaling = window_scaling_factor * cls.widget_scaling
            total_window_scaling = window_scaling_factor * cls.window_scaling

        for callback in callback_list:
            try:
                callback(total_widget_scaling, total_window_scaling)
            except tkinter.TclError:
                pass

    @classmethod
    def add_widget(cls, widget_callback: Callable, widget):
        """Add a widget callback with optimized window root lookup."""
        window_root = cls.get_window_root_of_widget(widget)
        if window_root is None:
            return

        callback_list = cls.window_widgets_dict.setdefault(window_root, [])
        if widget_callback not in callback_list:
            callback_list.append(widget_callback)

        if window_root not in cls.window_dpi_scaling_dict:
            cls.window_dpi_scaling_dict[window_root] = cls.get_window_dpi_scaling(window_root)

        if not cls.update_loop_running:
            window_root.after(100, cls.check_dpi_scaling)
            cls.update_loop_running = True

    @classmethod
    def remove_widget(cls, widget_callback: Callable, widget):
        """Remove a widget callback with optimized lookup."""
        window_root = cls.get_window_root_of_widget(widget)
        if window_root is None:
            return

        callback_list = cls.window_widgets_dict.get(window_root)
        if callback_list and widget_callback in callback_list:
            callback_list.remove(widget_callback)
            if not callback_list:
                cls.window_widgets_dict.pop(window_root, None)
                cls.window_dpi_scaling_dict.pop(window_root, None)

    @classmethod
    def add_window(cls, window_callback: Callable, window):
        """Add a window callback with duplicate check."""
        callback_list = cls.window_widgets_dict.setdefault(window, [])
        if window_callback not in callback_list:
            callback_list.append(window_callback)

        if window not in cls.window_dpi_scaling_dict:
            cls.window_dpi_scaling_dict[window] = cls.get_window_dpi_scaling(window)

    @classmethod
    def remove_window(cls, window_callback: Callable, window):
        """Remove a window callback with optimized cleanup."""
        callback_list = cls.window_widgets_dict.get(window)
        if callback_list and window_callback in callback_list:
            callback_list.remove(window_callback)
            if not callback_list:
                cls.window_widgets_dict.pop(window, None)
                cls.window_dpi_scaling_dict.pop(window, None)

    @classmethod
    def activate_high_dpi_awareness(cls):
        """Activate high DPI awareness with platform-specific optimizations."""
        if not cls.deactivate_automatic_dpi_awareness:
            if sys.platform.startswith("win"):
                import ctypes
                try:
                    # Windows 10 Anniversary Update and later
                    DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
                    ctypes.windll.user32.SetProcessDpiAwarenessContext(
                        ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2))
                except AttributeError:
                    # Fallback for older Windows versions
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)

    @classmethod
    def get_window_dpi_scaling(cls, window) -> float:
        """Get window DPI scaling with platform-specific optimizations."""
        if cls.deactivate_automatic_dpi_awareness:
            return 1.0

        if sys.platform.startswith("win"):
            try:
                from ctypes import windll, pointer, wintypes

                window_hwnd = wintypes.HWND(window.winfo_id())
                monitor_handle = windll.user32.MonitorFromWindow(
                    window_hwnd, wintypes.DWORD(cls.MONITOR_DEFAULT_NEAREST))
                x_dpi = wintypes.UINT()
                y_dpi = wintypes.UINT()
                windll.shcore.GetDpiForMonitor(
                    monitor_handle, cls.DPI_TYPE_EFFECTIVE,
                    pointer(x_dpi), pointer(y_dpi))
                return (x_dpi.value + y_dpi.value) / (2 * cls.DPI_100_PERCENT)
            except Exception:
                return 1.0
        return 1.0

    @classmethod
    def check_dpi_scaling(cls):
        """Check DPI scaling with optimized window handling."""
        if not cls.window_widgets_dict:
            cls.update_loop_running = False
            return

        new_scaling_detected = False
        for window in list(cls.window_widgets_dict):
            if not window.winfo_exists() or window.state() == "iconic":
                continue

            current_dpi_scaling = cls.get_window_dpi_scaling(window)
            if current_dpi_scaling != cls.window_dpi_scaling_dict.get(window, 1.0):
                cls.window_dpi_scaling_dict[window] = current_dpi_scaling
                cls.get_widget_scaling.cache_clear()
                cls.get_window_scaling.cache_clear()
                cls.update_scaling_callbacks_for_window(window)
                new_scaling_detected = True

        # Schedule next check on first available window
        interval = (cls.loop_pause_after_new_scaling if new_scaling_detected
                    else cls.update_loop_interval)

        for window in cls.window_widgets_dict:
            if window.winfo_exists():
                window.after(interval, cls.check_dpi_scaling)
                cls.update_loop_running = True
                return

        cls.update_loop_running = False
        
