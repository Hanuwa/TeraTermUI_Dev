import tkinter
from typing import Callable
import darkdetect
import weakref

class AppearanceModeTracker:

    callback_list = []
    app_list = weakref.WeakSet()
    update_loop_running = False
    update_loop_interval = 50  # milliseconds

    appearance_mode_set_by = "system"
    appearance_mode = 0  # Light (standard)

    @classmethod
    def init_appearance_mode(cls):
        if cls.appearance_mode_set_by == "system":
            new_appearance_mode = cls.detect_appearance_mode()

            if new_appearance_mode != cls.appearance_mode:
                cls.appearance_mode = new_appearance_mode
                cls.update_callbacks()

    @classmethod
    def add(cls, callback: Callable, widget=None):
        if hasattr(callback, '__self__') and callback.__self__:
            cls.callback_list.append(weakref.WeakMethod(callback))
        else:
            cls.callback_list.append(weakref.ref(callback))

        if widget is not None:
            app = cls.get_tk_root_of_widget(widget)
            cls.app_list.add(app)

            if not cls.update_loop_running:
                app.after(cls.update_loop_interval, cls.update)
                cls.update_loop_running = True

    @classmethod
    def remove(cls, callback: Callable):
        for ref in cls.callback_list:
            if ref() is callback:
                cls.callback_list.remove(ref)
                break

    @staticmethod
    def detect_appearance_mode() -> int:
        try:
            if darkdetect.theme() == "Dark":
                return 1  # Dark
            else:
                return 0  # Light
        except NameError:
            return 0  # Light

    @classmethod
    def get_tk_root_of_widget(cls, widget):
        current_widget = widget

        while isinstance(current_widget, tkinter.Tk) is False:
            current_widget = current_widget.master

        return current_widget

    @classmethod
    def update_callbacks(cls):
        mode_string = "Light" if cls.appearance_mode == 0 else "Dark"
        for ref in cls.callback_list[:]:  # Iterate over a shallow copy to allow removal during iteration
            callback = ref()
            if callback:
                try:
                    callback(mode_string)
                except Exception:
                    continue
            else:
                cls.callback_list.remove(ref)

    @classmethod
    def update(cls):
        if cls.appearance_mode_set_by == "system":
            new_appearance_mode = cls.detect_appearance_mode()

            if new_appearance_mode != cls.appearance_mode:
                cls.appearance_mode = new_appearance_mode
                cls.update_callbacks()

        # find an existing tkinter.Tk object for the next call of .after()
        for app in cls.app_list:
            try:
                app.after(cls.update_loop_interval, cls.update)
                return
            except Exception:
                continue

        cls.update_loop_running = False

    @classmethod
    def get_mode(cls) -> int:
        return cls.appearance_mode

    @classmethod
    def set_appearance_mode(cls, mode_string: str):
        if mode_string.lower() == "dark":
            cls.appearance_mode_set_by = "user"
            new_appearance_mode = 1

            if new_appearance_mode != cls.appearance_mode:
                cls.appearance_mode = new_appearance_mode
                cls.update_callbacks()

        elif mode_string.lower() == "light":
            cls.appearance_mode_set_by = "user"
            new_appearance_mode = 0

            if new_appearance_mode != cls.appearance_mode:
                cls.appearance_mode = new_appearance_mode
                cls.update_callbacks()

        elif mode_string.lower() == "system":
            cls.appearance_mode_set_by = "system"
