import tkinter
import sys
import threading
from weakref import WeakKeyDictionary
from typing import Callable, Dict, List, Optional


class ScalingTracker:
    deactivate_automatic_dpi_awareness = False

    # Contains window objects as keys with list of widget callbacks as elements
    window_widgets_dict: WeakKeyDictionary = WeakKeyDictionary()
    # Contains window objects as keys and corresponding scaling factors
    window_dpi_scaling_dict: WeakKeyDictionary = WeakKeyDictionary()
    # Cache for storing window roots of widgets
    window_root_cache: WeakKeyDictionary = WeakKeyDictionary()
    # Cache for storing calculated scaling values
    scaling_cache: WeakKeyDictionary = WeakKeyDictionary()

    widget_scaling = 1.0  # User values which multiply to detected window scaling factor
    window_scaling = 1.0

    update_loop_running = False
    update_loop_interval = 500  # ms
    loop_pause_after_new_scaling = 1500  # ms

    @classmethod
    def get_widget_scaling(cls, widget) -> float:
        if widget not in cls.scaling_cache:
            window_root = cls.get_window_root_of_widget(widget)
            scaling_factor = cls.window_dpi_scaling_dict.get(window_root, 1.0) * cls.widget_scaling
            cls.scaling_cache[widget] = scaling_factor
        return cls.scaling_cache[widget]

    @classmethod
    def get_window_scaling(cls, window) -> float:
        if window not in cls.scaling_cache:
            window_root = cls.get_window_root_of_widget(window)
            scaling_factor = cls.window_dpi_scaling_dict.get(window_root, 1.0) * cls.window_scaling
            cls.scaling_cache[window] = scaling_factor
        return cls.scaling_cache[window]

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
        if widget not in cls.window_root_cache:
            current_widget = widget
            while not isinstance(current_widget, (tkinter.Tk, tkinter.Toplevel)):
                current_widget = current_widget.master
            cls.window_root_cache[widget] = current_widget
        return cls.window_root_cache[widget]

    @classmethod
    def update_scaling_callbacks_all(cls):
        for window, callback_list in list(cls.window_widgets_dict.items()):
            new_callback_list = []
            for callback in callback_list:
                if callback is not None:
                    widget = getattr(callback, '__self__', None)
                    if widget and widget.winfo_exists() and widget.master is not None:
                        try:
                            if not cls.deactivate_automatic_dpi_awareness:
                                scaling_factor = cls.window_dpi_scaling_dict.get(window, 1.0)
                                callback(scaling_factor * cls.widget_scaling,
                                         scaling_factor * cls.window_scaling)
                            else:
                                callback(cls.widget_scaling, cls.window_scaling)
                            new_callback_list.append(callback)
                        except tkinter.TclError:
                            pass  # Widget might have been destroyed
            cls.window_widgets_dict[window] = new_callback_list

    @classmethod
    def update_scaling_callbacks_for_window(cls, window):
        for callback in cls.window_widgets_dict.get(window, []):
            if callback is not None:
                try:
                    if not cls.deactivate_automatic_dpi_awareness:
                        scaling_factor = cls.window_dpi_scaling_dict.get(window, 1.0)
                        callback(scaling_factor * cls.widget_scaling,
                                 scaling_factor * cls.window_scaling)
                    else:
                        callback(cls.widget_scaling, cls.window_scaling)
                except tkinter.TclError:
                    pass  # Widget might have been destroyed

    @classmethod
    def add_widget(cls, widget_callback: Callable, widget):
        window_root = cls.get_window_root_of_widget(widget)
        if window_root not in cls.window_widgets_dict:
            cls.window_widgets_dict[window_root] = [widget_callback]
        else:
            cls.window_widgets_dict[window_root].append(widget_callback)

        if window_root not in cls.window_dpi_scaling_dict:
            cls.window_dpi_scaling_dict[window_root] = cls.get_window_dpi_scaling(window_root)

        if not cls.update_loop_running:
            window_root.after(100, cls.check_dpi_scaling)
            cls.update_loop_running = True

    @classmethod
    def remove_widget(cls, widget_callback: Callable, widget):
        window_root = cls.get_window_root_of_widget(widget)
        try:
            cls.window_widgets_dict[window_root].remove(widget_callback)
            if not cls.window_widgets_dict[window_root]:
                del cls.window_widgets_dict[window_root]
                del cls.window_dpi_scaling_dict[window_root]
        except (ValueError, KeyError):
            pass

    @classmethod
    def remove_window(cls, window_callback: Callable, window):
        try:
            cls.window_widgets_dict[window].remove(window_callback)
            if not cls.window_widgets_dict[window]:
                del cls.window_widgets_dict[window]
                del cls.window_dpi_scaling_dict[window]
        except (ValueError, KeyError):
            pass

    @classmethod
    def add_window(cls, window_callback: Callable, window):
        if window not in cls.window_widgets_dict:
            cls.window_widgets_dict[window] = [window_callback]
        else:
            cls.window_widgets_dict[window].append(window_callback)

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
            elif sys.platform.startswith("linux"):
                # For GTK-based systems (might require additional configurations)
                pass  # DPI awareness on Linux not implemented
            else:
                pass  # Other platforms not specifically handled

    @classmethod
    def get_window_dpi_scaling(cls, window) -> float:
        if not cls.deactivate_automatic_dpi_awareness:
            if sys.platform == "darwin":
                return 1.0  # Scaling works automatically on macOS
            elif sys.platform.startswith("win"):
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
            else:
                return 1.0  # DPI awareness on Linux not implemented
        else:
            return 1.0

    @classmethod
    def check_dpi_scaling(cls):
        new_scaling_detected = False

        # Check for every window if scaling value changed
        for window in list(cls.window_widgets_dict):
            if window.winfo_exists() and window.state() != "iconic":
                current_dpi_scaling_value = cls.get_window_dpi_scaling(window)
                if current_dpi_scaling_value != cls.window_dpi_scaling_dict.get(window, 1.0):
                    cls.window_dpi_scaling_dict[window] = current_dpi_scaling_value

                    if sys.platform.startswith("win"):
                        window.attributes("-alpha", 0.15)

                    if hasattr(window, 'block_update_dimensions_event'):
                        window.block_update_dimensions_event()
                    cls.update_scaling_callbacks_for_window(window)
                    if hasattr(window, 'unblock_update_dimensions_event'):
                        window.unblock_update_dimensions_event()

                    if sys.platform.startswith("win"):
                        window.attributes("-alpha", 1.0)

                    new_scaling_detected = True

        # Clear scaling cache if new scaling was detected
        if new_scaling_detected:
            cls.scaling_cache.clear()

        # Schedule the next check
        for app in cls.window_widgets_dict.keys():
            try:
                if new_scaling_detected:
                    app.after(cls.loop_pause_after_new_scaling, cls.check_dpi_scaling)
                else:
                    app.after(cls.update_loop_interval, cls.check_dpi_scaling)
                return
            except Exception:
                continue

        cls.update_loop_running = False
