import tkinter
from typing import Callable
import weakref
import threading

try:
    import darkdetect
except ImportError:
    darkdetect = None

class AppearanceModeTracker:

    callback_list = []
    app_list = weakref.WeakSet()
    update_loop_running = False
    update_loop_interval = 500  # Increased from 50 milliseconds to 500 milliseconds

    appearance_mode_set_by = "system"
    appearance_mode = 0  # Light (standard)

    _lock = threading.Lock()  # Threading lock for thread safety

    @classmethod
    def init_appearance_mode(cls):
        with cls._lock:
            if cls.appearance_mode_set_by == "system":
                new_appearance_mode = cls.detect_appearance_mode()

                if new_appearance_mode != cls.appearance_mode:
                    cls.appearance_mode = new_appearance_mode

        cls.update_callbacks()  # Call without holding the lock

    @classmethod
    def add(cls, callback: Callable, widget=None):
        with cls._lock:
            if hasattr(callback, '__self__') and callback.__self__:
                cls.callback_list.append(weakref.WeakMethod(callback))
            else:
                cls.callback_list.append(weakref.ref(callback))

            should_start_update = not cls.update_loop_running

            if widget is not None:
                app = cls.get_tk_root_of_widget(widget)
                if app is not None:
                    cls.app_list.add(app)

            if should_start_update and cls.app_list:
                cls.update_loop_running = True
                app_to_use = next(iter(cls.app_list))
            else:
                app_to_use = None

        # Schedule the update outside the lock
        if app_to_use is not None:
            try:
                app_to_use.after(cls.update_loop_interval, cls.update)
            except Exception as e:
                print(f"Error scheduling update: {e}")

    @classmethod
    def remove(cls, callback: Callable):
        with cls._lock:
            for ref in cls.callback_list:
                if ref() is callback:
                    cls.callback_list.remove(ref)
                    break

    @staticmethod
    def detect_appearance_mode() -> int:
        if darkdetect:
            try:
                if darkdetect.theme() == "Dark":
                    return 1  # Dark
                else:
                    return 0  # Light
            except Exception:
                return 0  # Default to Light in case of error
        else:
            return 0  # Light

    @classmethod
    def get_tk_root_of_widget(cls, widget):
        current_widget = widget

        while not isinstance(current_widget, tkinter.Tk):
            if current_widget.master is None:
                # Widget has no master, likely destroyed
                return None
            current_widget = current_widget.master

        return current_widget

    @classmethod
    def update_callbacks(cls):
        with cls._lock:
            mode_string = "Light" if cls.appearance_mode == 0 else "Dark"
            callbacks = cls.callback_list[:]

        # Call callbacks outside the lock
        for ref in callbacks:
            callback = ref()
            if callback:
                try:
                    callback(mode_string)
                except Exception as e:
                    print(f"Error in callback {callback}: {e}")
            else:
                # Remove dead references
                with cls._lock:
                    if ref in cls.callback_list:
                        cls.callback_list.remove(ref)

    @classmethod
    def update(cls):
        # Acquire lock to read and update shared state
        with cls._lock:
            if cls.appearance_mode_set_by == "system":
                new_appearance_mode = cls.detect_appearance_mode()
                if new_appearance_mode != cls.appearance_mode:
                    cls.appearance_mode = new_appearance_mode
                    need_to_update_callbacks = True
                else:
                    need_to_update_callbacks = False
            else:
                need_to_update_callbacks = False

            # Clean up destroyed apps
            cls.app_list = weakref.WeakSet([app for app in cls.app_list if app.winfo_exists()])

            if not cls.app_list:
                cls.update_loop_running = False
                return  # No apps to schedule, exit

            app = next(iter(cls.app_list))

        # Call update_callbacks outside the lock
        if need_to_update_callbacks:
            cls.update_callbacks()

        # Schedule the next update outside the lock
        try:
            app.after(cls.update_loop_interval, cls.update)
        except Exception as e:
            print(f"Error scheduling update: {e}")

    @classmethod
    def get_mode(cls) -> int:
        with cls._lock:
            return cls.appearance_mode

    @classmethod
    def set_appearance_mode(cls, mode_string: str):
        with cls._lock:
            previous_mode = cls.appearance_mode
            if mode_string.lower() == "dark":
                cls.appearance_mode_set_by = "user"
                cls.appearance_mode = 1

            elif mode_string.lower() == "light":
                cls.appearance_mode_set_by = "user"
                cls.appearance_mode = 0

            elif mode_string.lower() == "system":
                cls.appearance_mode_set_by = "system"
                cls.appearance_mode = cls.detect_appearance_mode()

            else:
                raise ValueError("Invalid appearance mode. Choose 'Light', 'Dark', or 'System'.")

            need_to_update_callbacks = (cls.appearance_mode != previous_mode)

        if need_to_update_callbacks:
            cls.update_callbacks()  # Call outside the lock
