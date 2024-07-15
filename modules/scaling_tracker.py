import tkinter
import sys
from weakref import WeakKeyDictionary, WeakMethod
from typing import Callable


class ScalingTracker:
    deactivate_automatic_dpi_awareness = False

    window_widgets_dict = WeakKeyDictionary()  # contains window objects as keys with list of widget callbacks as elements
    window_dpi_scaling_dict = WeakKeyDictionary()  # contains window objects as keys and corresponding scaling factors
    window_root_cache = WeakKeyDictionary()  # cache for storing window roots of widgets
    scaling_cache = WeakKeyDictionary()  # Cache for storing calculated scaling values

    widget_scaling = 1  # user values which multiply to detected window scaling factor
    window_scaling = 1

    update_loop_running = False
    update_loop_interval = 500  # ms
    loop_pause_after_new_scaling = 1000  # ms

    @classmethod
    def get_widget_scaling(cls, widget) -> float:
        if widget not in cls.scaling_cache:
            window_root = cls.get_window_root_of_widget(widget)
            cls.scaling_cache[widget] = cls.window_dpi_scaling_dict[window_root] * cls.widget_scaling
        return cls.scaling_cache[widget]

    @classmethod
    def get_window_scaling(cls, window) -> float:
        if window not in cls.scaling_cache:
            window_root = cls.get_window_root_of_widget(window)
            cls.scaling_cache[window] = cls.window_dpi_scaling_dict[window_root] * cls.window_scaling
        return cls.scaling_cache[window]

    @classmethod
    def set_widget_scaling(cls, widget_scaling_factor: float):
        cls.widget_scaling = max(widget_scaling_factor, 0.4)
        cls.update_scaling_callbacks_all()
        cls.scaling_cache.clear()

    @classmethod
    def set_window_scaling(cls, window_scaling_factor: float):
        cls.window_scaling = max(window_scaling_factor, 0.4)
        cls.update_scaling_callbacks_all()
        cls.scaling_cache.clear()

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
            for set_scaling_callback in callback_list:
                callback = set_scaling_callback()
                if callback is not None:
                    widget = callback.__self__
                    if widget.winfo_exists() and widget.master is not None:
                        try:
                            if not cls.deactivate_automatic_dpi_awareness:
                                callback(cls.window_dpi_scaling_dict[window] * cls.widget_scaling,
                                         cls.window_dpi_scaling_dict[window] * cls.window_scaling)
                            else:
                                callback(cls.widget_scaling, cls.window_scaling)
                            new_callback_list.append(set_scaling_callback)
                        except tkinter.TclError:
                            pass
            cls.window_widgets_dict[window] = new_callback_list

    @classmethod
    def update_scaling_callbacks_for_window(cls, window):
        for set_scaling_callback in cls.window_widgets_dict.get(window, []):
            callback = set_scaling_callback()
            if callback is not None:
                if not cls.deactivate_automatic_dpi_awareness:
                    callback(cls.window_dpi_scaling_dict[window] * cls.widget_scaling,
                             cls.window_dpi_scaling_dict[window] * cls.window_scaling)
                else:
                    callback(cls.widget_scaling, cls.window_scaling)

    @classmethod
    def add_widget(cls, widget_callback: Callable, widget):
        weak_widget_callback = WeakMethod(widget_callback)
        window_root = cls.get_window_root_of_widget(widget)

        if window_root not in cls.window_widgets_dict:
            cls.window_widgets_dict[window_root] = [weak_widget_callback]
        else:
            cls.window_widgets_dict[window_root].append(weak_widget_callback)

        if window_root not in cls.window_dpi_scaling_dict:
            cls.window_dpi_scaling_dict[window_root] = cls.get_window_dpi_scaling(window_root)

        if not cls.update_loop_running:
            window_root.after(100, cls.check_dpi_scaling)
            cls.update_loop_running = True

    @classmethod
    def remove_widget(cls, widget_callback, widget):
        window_root = cls.get_window_root_of_widget(widget)
        try:
            weak_widget_callback = WeakMethod(widget_callback)
            cls.window_widgets_dict[window_root].remove(weak_widget_callback)
        except ValueError:
            pass

    @classmethod
    def remove_window(cls, window_callback, window):
        try:
            weak_window_callback = WeakMethod(window_callback)
            cls.window_widgets_dict[window].remove(weak_window_callback)
        except ValueError:
            pass

    @classmethod
    def add_window(cls, window_callback, window):
        weak_window_callback = WeakMethod(window_callback)

        if window not in cls.window_widgets_dict:
            cls.window_widgets_dict[window] = [weak_window_callback]
        else:
            cls.window_widgets_dict[window].append(weak_window_callback)

        if window not in cls.window_dpi_scaling_dict:
            cls.window_dpi_scaling_dict[window] = cls.get_window_dpi_scaling(window)

    @classmethod
    def activate_high_dpi_awareness(cls):
        """ make process DPI aware, customtkinter elements will get scaled automatically,
            only gets activated when CTk object is created """

        if not cls.deactivate_automatic_dpi_awareness:
            if sys.platform == "darwin":
                pass  # high DPI scaling works automatically on macOS

            elif sys.platform.startswith("win"):
                import ctypes

                # Values for SetProcessDpiAwareness and SetProcessDpiAwarenessContext:
                # internal enum PROCESS_DPI_AWARENESS
                # {
                #     Process_DPI_Unaware = 0,
                #     Process_System_DPI_Aware = 1,
                #     Process_Per_Monitor_DPI_Aware = 2
                # }
                #
                # internal enum DPI_AWARENESS_CONTEXT
                # {
                #     DPI_AWARENESS_CONTEXT_UNAWARE = 16,
                #     DPI_AWARENESS_CONTEXT_SYSTEM_AWARE = 17,
                #     DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE = 18,
                #     DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = 34
                # }

                # ctypes.windll.user32.SetProcessDpiAwarenessContext(34)  # Non client area scaling at runtime (titlebar)
                # does not work with resizable(False, False), window starts growing on monitor with different scaling (weird tkinter bug...)
                # ctypes.windll.user32.EnableNonClientDpiScaling(hwnd) does not work for some reason (tested on Windows 11)

                # It's too bad, that these Windows API methods don't work properly with tkinter. But I tested days with multiple monitor setups,
                # and I don't think there is anything left to do. So this is the best option at the moment:

                ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Titlebar does not scale at runtime
            else:
                pass  # DPI awareness on Linux not implemented

    @classmethod
    def get_window_dpi_scaling(cls, window) -> float:
        if not cls.deactivate_automatic_dpi_awareness:
            if sys.platform == "darwin":
                return 1  # scaling works automatically on macOS

            elif sys.platform.startswith("win"):
                from ctypes import windll, pointer, wintypes

                DPI100pc = 96  # DPI 96 is 100% scaling
                DPI_type = 0  # MDT_EFFECTIVE_DPI = 0, MDT_ANGULAR_DPI = 1, MDT_RAW_DPI = 2
                window_hwnd = wintypes.HWND(window.winfo_id())
                monitor_handle = windll.user32.MonitorFromWindow(window_hwnd, wintypes.DWORD(2))  # MONITOR_DEFAULTTONEAREST = 2
                x_dpi, y_dpi = wintypes.UINT(), wintypes.UINT()
                windll.shcore.GetDpiForMonitor(monitor_handle, DPI_type, pointer(x_dpi), pointer(y_dpi))
                return (x_dpi.value + y_dpi.value) / (2 * DPI100pc)

            else:
                return 1  # DPI awareness on Linux not implemented
        else:
            return 1

    @classmethod
    def check_dpi_scaling(cls):
        new_scaling_detected = False

        # check for every window if scaling value changed
        for window in list(cls.window_widgets_dict):
            if window.winfo_exists() and not window.state() == "iconic":
                current_dpi_scaling_value = cls.get_window_dpi_scaling(window)
                if current_dpi_scaling_value != cls.window_dpi_scaling_dict[window]:
                    cls.window_dpi_scaling_dict[window] = current_dpi_scaling_value

                    if sys.platform.startswith("win"):
                        window.attributes("-alpha", 0.15)

                    if hasattr(window, 'block_update_dimensions_event'):
                        window.block_update_dimensions_event()
                    cls.update_scaling_callbacks_for_window(window)
                    if hasattr(window, 'unblock_update_dimensions_event'):
                        window.unblock_update_dimensions_event()

                    if sys.platform.startswith("win"):
                        window.attributes("-alpha", 1)

                    new_scaling_detected = True

        # find an existing tkinter object for the next call of .after()
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

