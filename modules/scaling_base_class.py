from typing import Union, Tuple
import copy
import re
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from .scaling_tracker import ScalingTracker
from ..font import CTkFont


class CTkScalingBaseClass:
    """
    Super-class that manages the scaling values and callbacks.
    Works for widgets and windows, type must be set in init method with
    scaling_type attribute. Methods:

    - _set_scaling() abstractmethod, gets called when scaling changes, must be overridden
    - destroy() must be called when sub-class is destroyed
    - _apply_widget_scaling()
    - _reverse_widget_scaling()
    - _apply_window_scaling()
    - _reverse_window_scaling()
    - _apply_font_scaling()
    - _apply_argument_scaling()
    - _apply_geometry_scaling()
    - _reverse_geometry_scaling()
    - _parse_geometry_string()

    """

    def __init__(self, scaling_type: Literal["widget", "window"] = "widget"):
        self.__scaling_type = scaling_type

        if self.__scaling_type == "widget":
            ScalingTracker.add_widget(self._set_scaling, self)  # add callback for automatic scaling changes
            self.__widget_scaling = ScalingTracker.get_widget_scaling(self)
        elif self.__scaling_type == "window":
            ScalingTracker.activate_high_dpi_awareness()  # make process DPI aware
            ScalingTracker.add_window(self._set_scaling, self)  # add callback for automatic scaling changes
            self.__window_scaling = ScalingTracker.get_window_scaling(self)

    def destroy(self):
        if self.__scaling_type == "widget":
            ScalingTracker.remove_widget(self._set_scaling, self)
        elif self.__scaling_type == "window":
            ScalingTracker.remove_window(self._set_scaling, self)

    def _set_scaling(self, new_widget_scaling, new_window_scaling):
        """ can be overridden, but super method must be called at the beginning """
        self.__widget_scaling = new_widget_scaling
        self.__window_scaling = new_window_scaling

    def _get_widget_scaling(self) -> float:
        return self.__widget_scaling

    def _get_window_scaling(self) -> float:
        return self.__window_scaling

    def _apply_widget_scaling(self, value: Union[int, float]) -> Union[float]:
        assert self.__scaling_type == "widget"
        return value * self.__widget_scaling

    def _reverse_widget_scaling(self, value: Union[int, float]) -> Union[float]:
        assert self.__scaling_type == "widget"
        return value / self.__widget_scaling

    def _apply_window_scaling(self, value: Union[int, float]) -> int:
        assert self.__scaling_type == "window"
        return int(value * self.__window_scaling)

    def _reverse_window_scaling(self, scaled_value: Union[int, float]) -> int:
        assert self.__scaling_type == "window"
        return int(scaled_value / self.__window_scaling)

    def _apply_font_scaling(self, font: Union[Tuple, CTkFont]) -> tuple:
        """ Takes CTkFont object and returns tuple font with scaled size, has to be called again for every change of font object """
        assert self.__scaling_type == "widget"

        if type(font) == tuple:
            if len(font) == 1:
                return font
            elif len(font) == 2:
                return font[0], -abs(round(font[1] * self.__widget_scaling))
            elif 3 <= len(font) <= 6:
                return font[0], -abs(round(font[1] * self.__widget_scaling)), font[2:]
            else:
                raise ValueError(f"Can not scale font {font}. font needs to be tuple of len 1, 2 or 3")

        elif isinstance(font, CTkFont):
            return font.create_scaled_tuple(self.__widget_scaling)
        else:
            raise ValueError(f"Can not scale font '{font}' of type {type(font)}. font needs to be tuple or instance of CTkFont")

    def _apply_argument_scaling(self, kwargs: dict) -> dict:
        assert self.__scaling_type == "widget"
        scaled_kwargs = kwargs.copy()
        scalable_keys = ['pady', 'padx', 'x', 'y']
        for key in scalable_keys:
            if key in scaled_kwargs:
                value = scaled_kwargs[key]
                if isinstance(value, (int, float)):
                    scaled_kwargs[key] = self._apply_widget_scaling(value)
                elif isinstance(value, tuple):
                    scaled_kwargs[key] = tuple(self._apply_widget_scaling(v) for v in value)

        return scaled_kwargs

    @staticmethod
    def _parse_geometry_string(geometry_string: str) -> tuple:
        dimensions, *position = geometry_string.split('+')
        width, height = map(int, dimensions.split('x')) if 'x' in dimensions else (None, None)
        x, y = map(int, position) if position else (None, None)
        return width, height, x, y

    def _scale_geometry(self, geometry_string: str, scale: bool) -> str:
        width, height, x, y = self._parse_geometry_string(geometry_string)
        scaling_factor = self.__window_scaling if scale else 1 / self.__window_scaling

        scaled_width = round(width * scaling_factor) if width is not None else None
        scaled_height = round(height * scaling_factor) if height is not None else None

        geometry_parts = []
        if scaled_width is not None and scaled_height is not None:
            geometry_parts.append(f"{scaled_width}x{scaled_height}")
        if x is not None and y is not None:
            geometry_parts.append(f"+{x}+{y}")

        return "".join(geometry_parts)

    def _apply_geometry_scaling(self, geometry_string: str) -> str:
        return self._scale_geometry(geometry_string, True)

    def _reverse_geometry_scaling(self, scaled_geometry_string: str) -> str:
        return self._scale_geometry(scaled_geometry_string, False)
