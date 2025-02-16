from typing import Union, Tuple, Optional
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
        self._is_widget_scaling = scaling_type == "widget"
        self._is_window_scaling = scaling_type == "window"

        if self._is_widget_scaling:
            ScalingTracker.add_widget(self._set_scaling, self)
            self.__widget_scaling = ScalingTracker.get_widget_scaling(self)
        elif self._is_window_scaling:
            ScalingTracker.activate_high_dpi_awareness()
            ScalingTracker.add_window(self._set_scaling, self)
            self.__window_scaling = ScalingTracker.get_window_scaling(self)
        else:
            raise ValueError(f"Invalid scaling_type: {scaling_type}")

    def destroy(self):
        if self._is_widget_scaling:
            ScalingTracker.remove_widget(self._set_scaling, self)
        elif self._is_window_scaling:
            ScalingTracker.remove_window(self._set_scaling, self)

    def _set_scaling(self, new_widget_scaling, new_window_scaling):
        """Can be overridden; super method must be called at the beginning."""
        if self._is_widget_scaling:
            self.__widget_scaling = new_widget_scaling
        elif self._is_window_scaling:
            self.__window_scaling = new_window_scaling

    def _get_widget_scaling(self) -> float:
        return self.__widget_scaling

    def _get_window_scaling(self) -> float:
        return self.__window_scaling

    def _apply_widget_scaling(self, value: Union[int, float]) -> int:
        scaling = self.__widget_scaling
        return int(value * scaling + 0.5)

    def _reverse_widget_scaling(self, value: Union[int, float]) -> float:
        scaling = self.__widget_scaling
        return value / scaling

    def _apply_window_scaling(self, value: Union[int, float]) -> int:
        scaling = self.__window_scaling
        return int(value * scaling + 0.5)

    def _reverse_window_scaling(self, scaled_value: Union[int, float]) -> float:
        scaling = self.__window_scaling
        return scaled_value / scaling

    def _apply_font_scaling(self, font: Union[Tuple, CTkFont]) -> tuple:
        """Takes CTkFont object and returns tuple font with scaled size."""
        scaling = self.__widget_scaling

        if isinstance(font, CTkFont):
            return font.create_scaled_tuple(scaling)
        elif isinstance(font, tuple):
            font_length = len(font)
            if font_length == 1:
                return font
            elif font_length >= 2:
                font_name = font[0]
                font_size = -abs(int(font[1] * scaling + 0.5))
                other_args = font[2:] if font_length > 2 else ()
                return (font_name, font_size) + other_args
            else:
                raise ValueError(f"Cannot scale font {font}. Font tuple length must be at least 1.")
        else:
            raise ValueError(f"Cannot scale font '{font}' of type {type(font)}.")

    def _apply_argument_scaling(self, kwargs: dict) -> dict:
        scaling = self.__widget_scaling
        scaled_kwargs = kwargs.copy()
        scalable_keys = ('pady', 'padx', 'x', 'y')

        for key in scalable_keys:
            value = scaled_kwargs.get(key)
            if value is not None:
                if isinstance(value, (int, float)):
                    scaled_kwargs[key] = int(value * scaling + 0.5)
                elif isinstance(value, tuple):
                    scaled_kwargs[key] = tuple(int(v * scaling + 0.5) for v in value)

        return scaled_kwargs

    @staticmethod
    def _parse_geometry_string(geometry_string: str) -> tuple:
        #                 index:   1                   2           3          4             5       6
        # regex group structure: ('<width>x<height>', '<width>', '<height>', '+-<x>+-<y>', '-<x>', '-<y>')
        result = re.search(r"((\d+)x(\d+)){0,1}(\+{0,1}([+-]{0,1}\d+)\+{0,1}([+-]{0,1}\d+)){0,1}", geometry_string)

        width = int(result.group(2)) if result.group(2) is not None else None
        height = int(result.group(3)) if result.group(3) is not None else None
        x = int(result.group(5)) if result.group(5) is not None else None
        y = int(result.group(6)) if result.group(6) is not None else None

        return width, height, x, y

    def _apply_geometry_scaling(self, geometry_string: str) -> str:
        """Applies window scaling to the given geometry string."""
        assert self._is_window_scaling

        width, height, x, y = self._parse_geometry_string(geometry_string)

        if width is not None and height is not None:
            scaled_width = round(width * self.__window_scaling)
            scaled_height = round(height * self.__window_scaling)
        else:
            scaled_width, scaled_height = None, None

        if x is not None and y is not None:
            scaled_x = round(x * self.__window_scaling)
            scaled_y = round(y * self.__window_scaling)
        else:
            scaled_x, scaled_y = None, None

        # Construct the final geometry string
        geometry_parts = []
        if scaled_width is not None and scaled_height is not None:
            geometry_parts.append(f"{scaled_width}x{scaled_height}")
        if scaled_x is not None and scaled_y is not None:
            geometry_parts.append(f"+{scaled_x}+{scaled_y}")

        return "".join(geometry_parts)

    def _reverse_geometry_scaling(self, scaled_geometry_string: str) -> str:
        """Reverses scaling of window geometry."""
        assert self._is_window_scaling

        width, height, x, y = self._parse_geometry_string(scaled_geometry_string)

        if width is not None and height is not None:
            original_width = round(width / self.__window_scaling)
            original_height = round(height / self.__window_scaling)
        else:
            original_width, original_height = None, None

        if x is not None and y is not None:
            original_x = round(x / self.__window_scaling)
            original_y = round(y / self.__window_scaling)
        else:
            original_x, original_y = None, None

        geometry_parts = []
        if original_width is not None and original_height is not None:
            geometry_parts.append(f"{original_width}x{original_height}")
        if original_x is not None and original_y is not None:
            geometry_parts.append(f"+{original_x}+{original_y}")

        return "".join(geometry_parts)


