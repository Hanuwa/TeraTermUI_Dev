import sys
import time
from typing import Union, Tuple, Callable, Optional

from .core_rendering import CTkCanvas
from .theme import ThemeManager
from .core_rendering import DrawEngine
from .core_widget_classes import CTkBaseClass


class CTkScrollbar(CTkBaseClass):
    """
    Scrollbar with rounded corners, configurable spacing.
    Connect to scrollable widget by passing .set() method and set command attribute.
    For detailed information check out the documentation.
    """
    __slots__ = ("master", "width", "height", "corner_radius", "border_spacing", "minimum_pixel_length", "bg_color",
                 "fg_color", "button_color", "button_hover_color", "hover", "command", "orientation")

    def __init__(self,
                 master: any,
                 width: Optional[Union[int, str]] = None,
                 height: Optional[Union[int, str]] = None,
                 corner_radius: Optional[int] = None,
                 border_spacing: Optional[int] = None,
                 minimum_pixel_length: int = 20,

                 bg_color: Union[str, Tuple[str, str]] = "transparent",
                 fg_color: Optional[Union[str, Tuple[str, str]]] = None,
                 button_color: Optional[Union[str, Tuple[str, str]]] = None,
                 button_hover_color: Optional[Union[str, Tuple[str, str]]] = None,

                 hover: bool = True,
                 command: Union[Callable, None] = None,
                 orientation: str = "vertical",
                 **kwargs):

        # set default dimensions according to orientation
        if width is None:
            if orientation.lower() == "vertical":
                width = 16
            else:
                width = 200
        if height is None:
            if orientation.lower() == "horizontal":
                height = 16
            else:
                height = 200

        # transfer basic functionality (_bg_color, size, __appearance_mode, scaling) to CTkBaseClass
        super().__init__(master=master, bg_color=bg_color, width=width, height=height, **kwargs)

        # color
        self._fg_color = ThemeManager.theme["CTkScrollbar"]["fg_color"] if fg_color is None else self._check_color_type(
            fg_color, transparency=True)
        self._button_color = ThemeManager.theme["CTkScrollbar"][
            "button_color"] if button_color is None else self._check_color_type(button_color)
        self._button_hover_color = ThemeManager.theme["CTkScrollbar"][
            "button_hover_color"] if button_hover_color is None else self._check_color_type(button_hover_color)

        # shape
        self._corner_radius = ThemeManager.theme["CTkScrollbar"][
            "corner_radius"] if corner_radius is None else corner_radius
        self._border_spacing = ThemeManager.theme["CTkScrollbar"][
            "border_spacing"] if border_spacing is None else border_spacing

        self._hover = hover
        self._hover_state: bool = False
        self._needs_redraw = True
        self._command = command
        self._orientation = orientation
        self._start_value: float = 0  # 0 to 1
        self._end_value: float = 1  # 0 to 1
        self._minimum_pixel_length = minimum_pixel_length
        self._last_refresh_time = time.time()
        self._motion_center_offset = 0
        self._last_motion_time = 0
        self._last_event_position = 0
        self._motion_refresh_rate =  0.0267

        self._canvas = CTkCanvas(master=self,
                                 highlightthickness=0,
                                 width=self._apply_widget_scaling(self._current_width),
                                 height=self._apply_widget_scaling(self._current_height), cursor="hand2")
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._draw_engine = DrawEngine(self._canvas)

        self._create_bindings()
        self._draw()

    def _create_bindings(self, sequence: Optional[str] = None):
        """ set necessary bindings for functionality of widget, will overwrite other bindings """
        if sequence is None:
            self._canvas.tag_bind("border_parts", "<Button-1>", self._clicked)
            self._canvas.tag_bind("scrollbar_parts", "<Button-1>", self._clicked_scrollbar)
        if sequence is None or sequence == "<ButtonRelease-1>":
            self._canvas.bind("<ButtonRelease-1>", self._on_release)
        if sequence is None or sequence == "<Enter>":
            self._canvas.bind("<Enter>", self._on_enter)
        if sequence is None or sequence == "<Leave>":
            self._canvas.bind("<Leave>", self._on_leave)
        if sequence is None or sequence == "<B1-Motion>":
            self._canvas.bind("<B1-Motion>", self._on_motion)
        if sequence is None or sequence == "<MouseWheel>":
            self._canvas.bind("<MouseWheel>", self._mouse_scroll_event)

    def _set_scaling(self, *args, **kwargs):
        super()._set_scaling(*args, **kwargs)

        self._canvas.configure(width=self._apply_widget_scaling(self._desired_width),
                               height=self._apply_widget_scaling(self._desired_height))
        self._draw(no_color_updates=True)

    def _set_dimensions(self, width=None, height=None):
        super()._set_dimensions(width, height)

        self._canvas.configure(width=self._apply_widget_scaling(self._desired_width),
                               height=self._apply_widget_scaling(self._desired_height))
        self._draw(no_color_updates=True)

    def _get_scrollbar_values_for_minimum_pixel_size(self):
        # correct scrollbar float values if scrollbar is too small
        if self._orientation == "vertical":
            scrollbar_pixel_length = (self._end_value - self._start_value) * self._current_height
            if scrollbar_pixel_length < self._minimum_pixel_length and -scrollbar_pixel_length + self._current_height != 0:
                # calculate how much to increase the float interval values so that the scrollbar width is self.minimum_pixel_length
                interval_extend_factor = (-scrollbar_pixel_length + self._minimum_pixel_length) / (
                            -scrollbar_pixel_length + self._current_height)
                corrected_end_value = self._end_value + (1 - self._end_value) * interval_extend_factor
                corrected_start_value = self._start_value - self._start_value * interval_extend_factor
                return corrected_start_value, corrected_end_value
            else:
                return self._start_value, self._end_value

        else:
            scrollbar_pixel_length = (self._end_value - self._start_value) * self._current_width
            if scrollbar_pixel_length < self._minimum_pixel_length and -scrollbar_pixel_length + self._current_width != 0:
                # calculate how much to increase the float interval values so that the scrollbar width is self.minimum_pixel_length
                interval_extend_factor = (-scrollbar_pixel_length + self._minimum_pixel_length) / (
                            -scrollbar_pixel_length + self._current_width)
                corrected_end_value = self._end_value + (1 - self._end_value) * interval_extend_factor
                corrected_start_value = self._start_value - self._start_value * interval_extend_factor
                return corrected_start_value, corrected_end_value
            else:
                return self._start_value, self._end_value

    def _draw(self, no_color_updates=False):
        if getattr(self, '_needs_redraw', True):
            super()._draw(no_color_updates)

        corrected_start_value, corrected_end_value = self._get_scrollbar_values_for_minimum_pixel_size()
        requires_recoloring = self._draw_engine.draw_rounded_scrollbar(
            self._apply_widget_scaling(self._current_width),
            self._apply_widget_scaling(self._current_height),
            self._apply_widget_scaling(self._corner_radius),
            self._apply_widget_scaling(self._border_spacing),
            corrected_start_value,
            corrected_end_value,
            self._orientation
        )

        if not no_color_updates or requires_recoloring:
            scrollbar_color = self._button_hover_color if self._hover_state else self._button_color
            border_color = self._bg_color if self._fg_color == "transparent" else self._fg_color
            applied_scrollbar_color = self._apply_appearance_mode(scrollbar_color)
            applied_border_color = self._apply_appearance_mode(border_color)

            self._canvas.itemconfig("scrollbar_parts", fill=applied_scrollbar_color, outline=applied_scrollbar_color)
            self._canvas.itemconfig("border_parts", fill=applied_border_color, outline=applied_border_color)
            self._canvas.configure(bg=applied_border_color)

        self._needs_redraw = False
        self._canvas.update_idletasks()

    def configure(self, require_redraw=False, **kwargs):
        if "fg_color" in kwargs:
            self._fg_color = self._check_color_type(kwargs.pop("fg_color"), transparency=True)
            require_redraw = True

        if "button_color" in kwargs:
            self._button_color = self._check_color_type(kwargs.pop("button_color"))
            require_redraw = True

        if "button_hover_color" in kwargs:
            self._button_hover_color = self._check_color_type(kwargs.pop("button_hover_color"))
            require_redraw = True

        if "hover" in kwargs:
            self._hover = kwargs.pop("hover")

        if "command" in kwargs:
            self._command = kwargs.pop("command")

        if "corner_radius" in kwargs:
            self._corner_radius = kwargs.pop("corner_radius")
            require_redraw = True

        if "border_spacing" in kwargs:
            self._border_spacing = kwargs.pop("border_spacing")
            require_redraw = True

        super().configure(require_redraw=require_redraw, **kwargs)

    def cget(self, attribute_name: str) -> any:
        if attribute_name == "corner_radius":
            return self._corner_radius
        elif attribute_name == "border_spacing":
            return self._border_spacing
        elif attribute_name == "minimum_pixel_length":
            return self._minimum_pixel_length

        elif attribute_name == "fg_color":
            return self._fg_color
        elif attribute_name == "scrollbar_color":
            return self._button_color
        elif attribute_name == "scrollbar_hover_color":
            return self._button_hover_color

        elif attribute_name == "hover":
            return self._hover
        elif attribute_name == "command":
            return self._command
        elif attribute_name == "orientation":
            return self._orientation

        else:
            return super().cget(attribute_name)

    def _on_enter(self, event=0):
        if self._hover is True:
            self._hover_state = True
            self._canvas.itemconfig("scrollbar_parts",
                                    outline=self._apply_appearance_mode(self._button_hover_color),
                                    fill=self._apply_appearance_mode(self._button_hover_color))

    def _on_leave(self, event=0):
        self._hover_state = False
        self._canvas.itemconfig("scrollbar_parts",
                                outline=self._apply_appearance_mode(self._button_color),
                                fill=self._apply_appearance_mode(self._button_color))

    def _on_release(self, event):
        self.update_idletasks()

    def _clicked(self, event):
        if self.master.focus_get():
            self.master.focus_set()

        self._motion_center_offset = 0
        self._on_motion(event)

    def _clicked_scrollbar(self, event):
        if self.master.focus_get():
            self.master.focus_set()
            
        if self._orientation == "vertical":
            value = self._reverse_widget_scaling(
                ((event.y - self._border_spacing) / (self._current_height - 2 * self._border_spacing)))
        else:
            value = self._reverse_widget_scaling(
                ((event.x - self._border_spacing) / (self._current_width - 2 * self._border_spacing)))
        center = self._start_value + ((self._end_value - self._start_value) * 0.5)
        self._motion_center_offset = center - value

    def _adjust_refresh_rate(self, speed):
        # Define the speed and refresh rate ranges
        min_speed = 350  # Minimum speed
        mid_speed = 850  # Mid speed
        max_speed = 1250  # Maximum speed
        min_rate = 0.0167  # Refresh rate for minimum speed
        mid_rate = 0.02  # Refresh rate for mid speed
        max_rate = 0.025  # Refresh rate for maximum speed

        # Calculate the slopes for each segment
        slope1 = (mid_rate - min_rate) / (mid_speed - min_speed)
        slope2 = (max_rate - mid_rate) / (max_speed - mid_speed)

        # Linear interpolation of refresh rate based on speed
        if speed <= min_speed:
            self._motion_refresh_rate = min_rate
        elif min_speed < speed <= mid_speed:
            # Interpolate between min_rate and mid_rate
            self._motion_refresh_rate = min_rate + slope1 * (speed - min_speed)
        elif mid_speed < speed < max_speed:
            # Interpolate between mid_rate and max_rate
            self._motion_refresh_rate = mid_rate + slope2 * (speed - mid_speed)
        else:  # speed >= max_speed
            self._motion_refresh_rate = max_rate

    def _on_motion(self, event):
        current_time = time.time()
        current_position = event.y if self._orientation == "vertical" else event.x

        time_diff = max(current_time - self._last_motion_time, 1e-6)  # Prevent division by zero
        position_diff = abs(current_position - self._last_event_position)
        speed = position_diff / time_diff

        if time_diff > self._motion_refresh_rate:
            self._adjust_refresh_rate(speed)
            self._last_motion_time = current_time
            self._last_event_position = current_position

            scrollbar_length = self._end_value - self._start_value
            relative_pos = (current_position - self._border_spacing) / (
                    self._current_height - 2 * self._border_spacing) \
                if self._orientation == "vertical" else (current_position - self._border_spacing) / (
                    self._current_width - 2 * self._border_spacing)
            new_value = self._reverse_widget_scaling(relative_pos) + self._motion_center_offset
            new_value = max(scrollbar_length / 2, min(new_value, 1 - scrollbar_length / 2))

            self._start_value = new_value - (scrollbar_length / 2)
            self._end_value = new_value + (scrollbar_length / 2)
            self._needs_redraw = True

            if self._command is not None:
                self._command('moveto', self._start_value)

    def _mouse_scroll_event(self, event=None):
        if self._command is not None:
            if sys.platform.startswith("win"):
                self._command('scroll', -int(event.delta / 40), 'units')
            else:
                self._command('scroll', -event.delta, 'units')

    def set(self, start_value: float, end_value: float):
        self._start_value = float(start_value)
        self._end_value = float(end_value)
        self._draw()

    def get(self):
        return self._start_value, self._end_value

    def bind(self, sequence=None, command=None, add=True):
        """ called on the tkinter.Canvas """
        if not (add == "+" or add is True):
            raise ValueError("'add' argument can only be '+' or True to preserve internal callbacks")
        self._canvas.bind(sequence, command, add=True)

    def unbind(self, sequence=None, funcid=None):
        """ called on the tkinter.Canvas, restores internal callbacks """
        if funcid is not None:
            raise ValueError("'funcid' argument can only be None, because there is a bug in" +
                             " tkinter and its not clear whether the internal callbacks will be unbinded or not")
        self._canvas.unbind(sequence, None)  # unbind all callbacks for sequence
        self._create_bindings(sequence=sequence)  # restore internal callbacks for sequence

    def focus(self):
        return self._canvas.focus()

    def focus_set(self):
        return self._canvas.focus_set()

    def focus_force(self):
        return self._canvas.focus_force()
