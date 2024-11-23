from __future__ import annotations
import sys
import math
import tkinter
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core_rendering import CTkCanvas


class DrawEngine:
    """
    This is the core of the CustomTkinter library where all the drawing on the tkinter.Canvas happens.
    A year of experimenting and trying out different drawing methods have led to the current state of this
    class, and I don't think there's much I can do to make the rendering look better than this with the
    limited capabilities the tkinter.Canvas offers.

    Functions:
     - draw_rounded_rect_with_border()
     - draw_rounded_rect_with_border_vertical_split()
     - draw_rounded_progress_bar_with_border()
     - draw_rounded_slider_with_border_and_button()
     - draw_rounded_scrollbar()
     - draw_checkmark()
     - draw_dropdown_arrow()

    """

    preferred_drawing_method: str = None  # 'polygon_shapes', 'font_shapes', 'circle_shapes'

    def __init__(self, canvas: CTkCanvas):
        self._canvas = canvas
        self._items = {}
        self._round_width_to_even_numbers: bool = True
        self._round_height_to_even_numbers: bool = True
        self._last_rounded_rect_settings = None
        self._last_background_corners = None
        self._last_dropdown_arrow =  None
        self._last_progress_bar_settings = None
        self._last_slider_settings = None
        self._last_scrollbar_settings = None

    def set_round_to_even_numbers(self, round_width_to_even_numbers: bool = True, round_height_to_even_numbers: bool = True):
        self._round_width_to_even_numbers: bool = round_width_to_even_numbers
        self._round_height_to_even_numbers: bool = round_height_to_even_numbers

    def __calc_optimal_corner_radius(self, user_corner_radius: Union[float, int]) -> Union[float, int]:
        # Optimize corner_radius based on the preferred drawing method
        if self.preferred_drawing_method == "polygon_shapes":
            return user_corner_radius if sys.platform == "darwin" else round(user_corner_radius)
        elif self.preferred_drawing_method == "font_shapes":
            return round(user_corner_radius)
        elif self.preferred_drawing_method == "circle_shapes":
            user_corner_radius = 0.5 * round(user_corner_radius / 0.5)
            return user_corner_radius + 0.5 if user_corner_radius % 1 == 0 else user_corner_radius
        else:
            return round(user_corner_radius)

    def draw_background_corners(self, width: Union[float, int], height: Union[float, int], ):
        current_settings = (width, height)
        if self._last_background_corners == current_settings:
            return False

        if self._round_width_to_even_numbers:
            width = math.floor(width / 2) * 2  # round (floor) _current_width and _current_height and restrict them to even values only
        if self._round_height_to_even_numbers:
            height = math.floor(height / 2) * 2

        requires_recoloring = False

        # Initialize items if they haven't been created yet
        if not self._items.get("background_corner_top_left"):
            self._items["background_corner_top_left"] = self._canvas.create_rectangle(
                (0, 0, 0, 0), tags=("background_parts", "background_corner_top_left"), width=0)
            requires_recoloring = True

        if not self._items.get("background_corner_top_right"):
            self._items["background_corner_top_right"] = self._canvas.create_rectangle(
                (0, 0, 0, 0), tags=("background_parts", "background_corner_top_right"), width=0)
            requires_recoloring = True

        if not self._items.get("background_corner_bottom_right"):
            self._items["background_corner_bottom_right"] = self._canvas.create_rectangle(
                (0, 0, 0, 0), tags=("background_parts", "background_corner_bottom_right"), width=0)
            requires_recoloring = True

        if not self._items.get("background_corner_bottom_left"):
            self._items["background_corner_bottom_left"] = self._canvas.create_rectangle(
                (0, 0, 0, 0), tags=("background_parts", "background_corner_bottom_left"), width=0)
            requires_recoloring = True

        mid_width, mid_height = round(width / 2), round(height / 2)
        self._canvas.coords(self._items["background_corner_top_left"], (0, 0, mid_width, mid_height))
        self._canvas.coords(self._items["background_corner_top_right"], (mid_width, 0, width, mid_height))
        self._canvas.coords(self._items["background_corner_bottom_right"], (mid_width, mid_height, width, height))
        self._canvas.coords(self._items["background_corner_bottom_left"], (0, mid_height, mid_width, height))

        self._last_background_corners = current_settings

        if requires_recoloring:  # new parts were added -> manage z-order
            self._canvas.tag_lower("background_parts")

        return requires_recoloring

    def draw_rounded_rect_with_border(self, width: Union[float, int], height: Union[float, int], corner_radius: Union[float, int],
                                      border_width: Union[float, int], overwrite_preferred_drawing_method: str = None) -> bool:
        """ Draws a rounded rectangle with a corner_radius and border_width on the canvas. The border elements have a 'border_parts' tag,
            the main foreground elements have an 'inner_parts' tag to color the elements accordingly.

            returns bool if recoloring is necessary """

        current_settings = (width, height, corner_radius, border_width, overwrite_preferred_drawing_method)
        if self._last_rounded_rect_settings == current_settings:
            return False

        # Round dimensions if required
        width = math.floor(width / 2) * 2 if self._round_width_to_even_numbers else width
        height = math.floor(height / 2) * 2 if self._round_height_to_even_numbers else height
        corner_radius = min(round(corner_radius), width / 2, height / 2)
        border_width = round(border_width)
        corner_radius = self.__calc_optimal_corner_radius(corner_radius)

        inner_corner_radius = max(corner_radius - border_width, 0)

        preferred_drawing_method = overwrite_preferred_drawing_method or self.preferred_drawing_method
        drawing_methods = {
            "polygon_shapes": self.__draw_rounded_rect_with_border_polygon_shapes,
            "font_shapes": self.__draw_rounded_rect_with_border_font_shapes,
            "circle_shapes": self.__draw_rounded_rect_with_border_circle_shapes,
        }

        draw_method = drawing_methods.get(preferred_drawing_method)
        if draw_method:
            result = draw_method(width, height, corner_radius, border_width, inner_corner_radius)
            self._last_rounded_rect_settings = current_settings
            return result
        else:
            raise ValueError(f"Unsupported drawing method: {preferred_drawing_method}")

    def __draw_rounded_rect_with_border_polygon_shapes(self, width: int, height: int, corner_radius: int,
                                                       border_width: int, inner_corner_radius: int) -> bool:
        requires_recoloring = False

        # Create or update border parts
        if border_width > 0:
            if "border_line_1" not in self._items:
                self._items["border_line_1"] = self._canvas.create_polygon(
                    (0, 0, 0, 0), tags=("border_parts"), width=corner_radius * 2, joinstyle=tkinter.ROUND)
                requires_recoloring = True
            else:
                self._canvas.itemconfig(self._items["border_line_1"], state='normal')

            self._canvas.coords(self._items["border_line_1"],
                                (corner_radius,
                                 corner_radius,
                                 width - corner_radius,
                                 corner_radius,
                                 width - corner_radius,
                                 height - corner_radius,
                                 corner_radius,
                                 height - corner_radius))
            self._canvas.itemconfig(self._items["border_line_1"], width=corner_radius * 2)

        else:
            if "border_line_1" in self._items:
                self._canvas.itemconfig(self._items["border_line_1"], state='hidden')

        # Create or update inner parts
        if "inner_line_1" not in self._items:
            self._items["inner_line_1"] = self._canvas.create_polygon(
                (0, 0, 0, 0), tags=("inner_parts"), width=inner_corner_radius * 2, joinstyle=tkinter.ROUND)
            requires_recoloring = True
        else:
            self._canvas.itemconfig(self._items["inner_line_1"], state='normal')

        if corner_radius <= border_width:
            bottom_right_shift = -1  # weird canvas rendering inaccuracy that has to be corrected in some cases
        else:
            bottom_right_shift = 0

        self._canvas.coords(self._items["inner_line_1"],
                            border_width + inner_corner_radius,
                            border_width + inner_corner_radius,
                            width - (border_width + inner_corner_radius) + bottom_right_shift,
                            border_width + inner_corner_radius,
                            width - (border_width + inner_corner_radius) + bottom_right_shift,
                            height - (border_width + inner_corner_radius) + bottom_right_shift,
                            border_width + inner_corner_radius,
                            height - (border_width + inner_corner_radius) + bottom_right_shift)
        self._canvas.itemconfig(self._items["inner_line_1"], width=inner_corner_radius * 2)

        if requires_recoloring:
            # Manage z-order
            self._canvas.tag_lower("inner_parts")
            self._canvas.tag_lower("border_parts")
            self._canvas.tag_lower("background_parts")

        return requires_recoloring

    def __draw_rounded_rect_with_border_font_shapes(self, width: int, height: int, corner_radius: int,
                                                    border_width: int, inner_corner_radius: int,
                                                    exclude_parts: tuple = ()) -> bool:
        requires_recoloring = False

        def create_or_update_item(key, create_func, coords, tags, **kwargs):
            if key not in self._items:
                self._items[key] = create_func(*coords, tags=tags, **kwargs)
                nonlocal requires_recoloring
                requires_recoloring = True
            else:
                self._canvas.itemconfig(self._items[key], state='normal')
                self._canvas.coords(self._items[key], *coords)

        # Border Parts
        if border_width > 0:
            if corner_radius > 0:
                # Border corner parts
                for i in range(1, 5):
                    key_a = f"border_oval_{i}_a"
                    key_b = f"border_oval_{i}_b"
                    if key_a in exclude_parts:
                        continue
                    tags = ("border_corner_part", "border_parts")
                    create_or_update_item(
                        key_a, self._canvas.create_aa_circle,
                        (0, 0, 0), tags, anchor=tkinter.CENTER
                    )
                    create_or_update_item(
                        key_b, self._canvas.create_aa_circle,
                        (0, 0, 0), tags, anchor=tkinter.CENTER, angle=180
                    )
                # Set positions of border corner parts
                self._canvas.coords(self._items["border_oval_1_a"], corner_radius, corner_radius, corner_radius)
                self._canvas.coords(self._items["border_oval_1_b"], corner_radius, corner_radius, corner_radius)
                self._canvas.coords(self._items["border_oval_2_a"], width - corner_radius, corner_radius, corner_radius)
                self._canvas.coords(self._items["border_oval_2_b"], width - corner_radius, corner_radius, corner_radius)
                self._canvas.coords(self._items["border_oval_3_a"], width - corner_radius, height - corner_radius,
                                    corner_radius)
                self._canvas.coords(self._items["border_oval_3_b"], width - corner_radius, height - corner_radius,
                                    corner_radius)
                self._canvas.coords(self._items["border_oval_4_a"], corner_radius, height - corner_radius,
                                    corner_radius)
                self._canvas.coords(self._items["border_oval_4_b"], corner_radius, height - corner_radius,
                                    corner_radius)
            else:
                # Hide border corner parts
                for i in range(1, 5):
                    for key in (f"border_oval_{i}_a", f"border_oval_{i}_b"):
                        if key in self._items:
                            self._canvas.itemconfig(self._items[key], state='hidden')

            # Border rectangle parts
            for i in range(1, 3):
                key = f"border_rectangle_{i}"
                tags = ("border_rectangle_part", "border_parts")
                create_or_update_item(
                    key, self._canvas.create_rectangle,
                    (0, 0, 0, 0), tags, width=0
                )
            # Set positions of border rectangle parts
            self._canvas.coords(self._items["border_rectangle_1"], (0, corner_radius, width, height - corner_radius))
            self._canvas.coords(self._items["border_rectangle_2"], (corner_radius, 0, width - corner_radius, height))
        else:
            # Hide border parts
            for key in [f"border_rectangle_{i}" for i in range(1, 3)] + \
                       [f"border_oval_{i}_{suffix}" for i in range(1, 5) for suffix in ('a', 'b')]:
                if key in self._items:
                    self._canvas.itemconfig(self._items[key], state='hidden')

        # Inner Parts
        if inner_corner_radius > 0:
            # Inner corner parts
            for i in range(1, 5):
                key_a = f"inner_oval_{i}_a"
                key_b = f"inner_oval_{i}_b"
                if key_a in exclude_parts:
                    continue
                tags = ("inner_corner_part", "inner_parts")
                create_or_update_item(
                    key_a, self._canvas.create_aa_circle,
                    (0, 0, 0), tags, anchor=tkinter.CENTER
                )
                create_or_update_item(
                    key_b, self._canvas.create_aa_circle,
                    (0, 0, 0), tags, anchor=tkinter.CENTER, angle=180
                )
            # Set positions of inner corner parts
            self._canvas.coords(self._items["inner_oval_1_a"],
                                border_width + inner_corner_radius, border_width + inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_1_b"],
                                border_width + inner_corner_radius, border_width + inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_2_a"],
                                width - border_width - inner_corner_radius, border_width + inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_2_b"],
                                width - border_width - inner_corner_radius, border_width + inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_3_a"],
                                width - border_width - inner_corner_radius, height - border_width - inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_3_b"],
                                width - border_width - inner_corner_radius, height - border_width - inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_4_a"],
                                border_width + inner_corner_radius, height - border_width - inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_4_b"],
                                border_width + inner_corner_radius, height - border_width - inner_corner_radius,
                                inner_corner_radius)
        else:
            # Hide inner corner parts
            for i in range(1, 5):
                for key in (f"inner_oval_{i}_a", f"inner_oval_{i}_b"):
                    if key in self._items:
                        self._canvas.itemconfig(self._items[key], state='hidden')

        # Inner rectangle parts
        for i in range(1, 3):
            key = f"inner_rectangle_{i}"
            tags = ("inner_rectangle_part", "inner_parts")
            create_or_update_item(
                key, self._canvas.create_rectangle,
                (0, 0, 0, 0), tags, width=0
            )
        # Set positions of inner rectangle parts
        self._canvas.coords(self._items["inner_rectangle_1"], (
            border_width + inner_corner_radius, border_width,
            width - border_width - inner_corner_radius, height - border_width
        ))

        needs_inner_rectangle_2 = inner_corner_radius * 2 < height - (border_width * 2)
        if needs_inner_rectangle_2:
            self._canvas.coords(self._items["inner_rectangle_2"], (
                border_width, border_width + inner_corner_radius,
                width - border_width, height - inner_corner_radius - border_width
            ))
        else:
            if "inner_rectangle_2" in self._items:
                self._canvas.itemconfig(self._items["inner_rectangle_2"], state='hidden')

        if requires_recoloring:
            # Manage z-order
            self._canvas.tag_lower("inner_parts")
            self._canvas.tag_lower("border_parts")
            self._canvas.tag_lower("background_parts")

        return requires_recoloring

    def __draw_rounded_rect_with_border_circle_shapes(self, width: int, height: int, corner_radius: int,
                                                      border_width: int, inner_corner_radius: int) -> bool:
        requires_recoloring = False

        # Border parts
        if border_width > 0:
            if corner_radius > 0:
                # Create or update border corner parts
                for i in range(1, 5):
                    key = f"border_oval_{i}"
                    if key not in self._items:
                        self._items[key] = self._canvas.create_oval(
                            0, 0, 0, 0, tags=("border_corner_part", "border_parts"), width=0)
                        requires_recoloring = True
                    else:
                        self._canvas.itemconfig(self._items[key], state='normal')

                # Set positions of border corner parts
                self._canvas.coords(self._items["border_oval_1"], 0, 0, corner_radius * 2 - 1, corner_radius * 2 - 1)
                self._canvas.coords(self._items["border_oval_2"], width - corner_radius * 2, 0, width - 1,
                                    corner_radius * 2 - 1)
                self._canvas.coords(self._items["border_oval_3"], 0, height - corner_radius * 2, corner_radius * 2 - 1,
                                    height - 1)
                self._canvas.coords(self._items["border_oval_4"], width - corner_radius * 2, height - corner_radius * 2,
                                    width - 1, height - 1)
            else:
                # Hide border corner parts
                for i in range(1, 5):
                    key = f"border_oval_{i}"
                    if key in self._items:
                        self._canvas.itemconfig(self._items[key], state='hidden')

            # Create or update border rectangle parts
            for i in range(1, 3):
                key = f"border_rectangle_{i}"
                if key not in self._items:
                    self._items[key] = self._canvas.create_rectangle(
                        0, 0, 0, 0, tags=("border_rectangle_part", "border_parts"), width=0)
                    requires_recoloring = True
                else:
                    self._canvas.itemconfig(self._items[key], state='normal')

            # Set positions of border rectangle parts
            self._canvas.coords(self._items["border_rectangle_1"], 0, corner_radius, width, height - corner_radius)
            self._canvas.coords(self._items["border_rectangle_2"], corner_radius, 0, width - corner_radius, height)
        else:
            # Hide border parts
            for key in ["border_rectangle_1", "border_rectangle_2"]:
                if key in self._items:
                    self._canvas.itemconfig(self._items[key], state='hidden')
            for i in range(1, 5):
                key = f"border_oval_{i}"
                if key in self._items:
                    self._canvas.itemconfig(self._items[key], state='hidden')

        # Inner parts
        if inner_corner_radius > 0:
            # Create or update inner corner parts
            for i in range(1, 5):
                key = f"inner_oval_{i}"
                if key not in self._items:
                    self._items[key] = self._canvas.create_oval(
                        0, 0, 0, 0, tags=("inner_corner_part", "inner_parts"), width=0)
                    requires_recoloring = True
                else:
                    self._canvas.itemconfig(self._items[key], state='normal')

            # Set positions of inner corner parts
            self._canvas.coords(self._items["inner_oval_1"], border_width, border_width,
                                border_width + inner_corner_radius * 2 - 1, border_width + inner_corner_radius * 2 - 1)
            self._canvas.coords(self._items["inner_oval_2"], width - border_width - inner_corner_radius * 2,
                                border_width, width - border_width - 1, border_width + inner_corner_radius * 2 - 1)
            self._canvas.coords(self._items["inner_oval_3"], border_width,
                                height - border_width - inner_corner_radius * 2,
                                border_width + inner_corner_radius * 2 - 1, height - border_width - 1)
            self._canvas.coords(self._items["inner_oval_4"], width - border_width - inner_corner_radius * 2,
                                height - border_width - inner_corner_radius * 2, width - border_width - 1,
                                height - border_width - 1)
        else:
            # Hide inner corner parts
            for i in range(1, 5):
                key = f"inner_oval_{i}"
                if key in self._items:
                    self._canvas.itemconfig(self._items[key], state='hidden')

        # Inner rectangle parts
        for i in range(1, 3):
            key = f"inner_rectangle_{i}"
            if key not in self._items:
                self._items[key] = self._canvas.create_rectangle(
                    0, 0, 0, 0, tags=("inner_rectangle_part", "inner_parts"), width=0)
                requires_recoloring = True
            else:
                self._canvas.itemconfig(self._items[key], state='normal')

        # Set positions of inner rectangle parts
        self._canvas.coords(self._items["inner_rectangle_1"], border_width + inner_corner_radius,
                            border_width, width - border_width - inner_corner_radius, height - border_width)
        self._canvas.coords(self._items["inner_rectangle_2"], border_width,
                            border_width + inner_corner_radius, width - border_width,
                            height - inner_corner_radius - border_width)

        if requires_recoloring:
            # Manage z-order
            self._canvas.tag_lower("inner_parts")
            self._canvas.tag_lower("border_parts")
            self._canvas.tag_lower("background_parts")

        return requires_recoloring

    def draw_rounded_rect_with_border_vertical_split(self, width: Union[float, int], height: Union[float, int], corner_radius: Union[float, int],
                                                     border_width: Union[float, int], left_section_width: Union[float, int]) -> bool:
        """ Draws a rounded rectangle with a corner_radius and border_width on the canvas which is split at left_section_width.
            The border elements have the tags 'border_parts_left', 'border_parts_lright',
            the main foreground elements have an 'inner_parts_left' and inner_parts_right' tag,
            to color the elements accordingly.

            returns bool if recoloring is necessary """

        left_section_width = round(left_section_width)
        if self._round_width_to_even_numbers:
            width = math.floor(
                width / 2) * 2  # round (floor) _current_width and _current_height and restrict them to even values only
        if self._round_height_to_even_numbers:
            height = math.floor(height / 2) * 2
        corner_radius = round(corner_radius)

        if corner_radius > width / 2 or corner_radius > height / 2:  # restrict corner_radius if it's too large
            corner_radius = min(width / 2, height / 2)

        border_width = round(border_width)
        corner_radius = self.__calc_optimal_corner_radius(corner_radius)  # optimize corner_radius for different drawing methods (different rounding)

        if corner_radius >= border_width:
            inner_corner_radius = corner_radius - border_width
        else:
            inner_corner_radius = 0

        if left_section_width > width - corner_radius * 2:
            left_section_width = width - corner_radius * 2
        elif left_section_width < corner_radius * 2:
            left_section_width = corner_radius * 2

        if self.preferred_drawing_method == "polygon_shapes" or self.preferred_drawing_method == "circle_shapes":
            return self.__draw_rounded_rect_with_border_vertical_split_polygon_shapes(width, height, corner_radius,
                                                                                      border_width, inner_corner_radius,
                                                                                      left_section_width)
        elif self.preferred_drawing_method == "font_shapes":
            return self.__draw_rounded_rect_with_border_vertical_split_font_shapes(width, height, corner_radius,
                                                                                   border_width, inner_corner_radius,
                                                                                   left_section_width, ())

    def __draw_rounded_rect_with_border_vertical_split_polygon_shapes(self, width: int, height: int, corner_radius: int,
                                                                      border_width: int, inner_corner_radius: int,
                                                                      left_section_width: int) -> bool:
        requires_recoloring = False

        # Border parts
        if border_width > 0:
            # Left border parts
            if "border_line_left_1" not in self._items:
                self._items["border_line_left_1"] = self._canvas.create_polygon(
                    (0, 0, 0, 0), tags=("border_parts_left", "border_parts"), width=corner_radius * 2,
                    joinstyle=tkinter.ROUND)
                requires_recoloring = True
            else:
                self._canvas.itemconfig(self._items["border_line_left_1"], state='normal')

            self._canvas.coords(self._items["border_line_left_1"],
                                corner_radius,
                                corner_radius,
                                left_section_width - corner_radius,
                                corner_radius,
                                left_section_width - corner_radius,
                                height - corner_radius,
                                corner_radius,
                                height - corner_radius)
            self._canvas.itemconfig(self._items["border_line_left_1"], width=corner_radius * 2)

            # Right border parts
            if "border_line_right_1" not in self._items:
                self._items["border_line_right_1"] = self._canvas.create_polygon(
                    (0, 0, 0, 0), tags=("border_parts_right", "border_parts", "right_parts"), width=corner_radius * 2,
                    joinstyle=tkinter.ROUND)
                requires_recoloring = True
            else:
                self._canvas.itemconfig(self._items["border_line_right_1"], state='normal')

            self._canvas.coords(self._items["border_line_right_1"],
                                left_section_width + corner_radius,
                                corner_radius,
                                width - corner_radius,
                                corner_radius,
                                width - corner_radius,
                                height - corner_radius,
                                left_section_width + corner_radius,
                                height - corner_radius)
            self._canvas.itemconfig(self._items["border_line_right_1"], width=corner_radius * 2)

        else:
            # Hide border parts
            for key in ["border_line_left_1", "border_line_right_1"]:
                if key in self._items:
                    self._canvas.itemconfig(self._items[key], state='hidden')

        # Inner parts
        # Left inner parts
        if "inner_line_left_1" not in self._items:
            self._items["inner_line_left_1"] = self._canvas.create_polygon(
                (0, 0, 0, 0), tags=("inner_parts_left", "inner_parts"), width=inner_corner_radius * 2,
                joinstyle=tkinter.ROUND)
            requires_recoloring = True
        else:
            self._canvas.itemconfig(self._items["inner_line_left_1"], state='normal')

        self._canvas.coords(self._items["inner_line_left_1"],
                            corner_radius,
                            corner_radius,
                            left_section_width - inner_corner_radius,
                            corner_radius,
                            left_section_width - inner_corner_radius,
                            height - corner_radius,
                            corner_radius,
                            height - corner_radius)
        self._canvas.itemconfig(self._items["inner_line_left_1"], width=inner_corner_radius * 2)

        # Right inner parts
        if "inner_line_right_1" not in self._items:
            self._items["inner_line_right_1"] = self._canvas.create_polygon(
                (0, 0, 0, 0), tags=("inner_parts_right", "inner_parts", "right_parts"), width=inner_corner_radius * 2,
                joinstyle=tkinter.ROUND)
            requires_recoloring = True
        else:
            self._canvas.itemconfig(self._items["inner_line_right_1"], state='normal')

        self._canvas.coords(self._items["inner_line_right_1"],
                            left_section_width + inner_corner_radius,
                            corner_radius,
                            width - corner_radius,
                            corner_radius,
                            width - corner_radius,
                            height - corner_radius,
                            left_section_width + inner_corner_radius,
                            height - corner_radius)
        self._canvas.itemconfig(self._items["inner_line_right_1"], width=inner_corner_radius * 2)

        if requires_recoloring:
            # Manage z-order
            self._canvas.tag_lower("inner_parts")
            self._canvas.tag_lower("border_parts")
            self._canvas.tag_lower("background_parts")

        return requires_recoloring

    def __draw_rounded_rect_with_border_vertical_split_font_shapes(self, width: int, height: int, corner_radius: int,
                                                                   border_width: int, inner_corner_radius: int,
                                                                   left_section_width: int,
                                                                   exclude_parts: tuple) -> bool:
        requires_recoloring = False

        # Border parts
        if border_width > 0:
            if corner_radius > 0:
                # Border corner parts
                # Left side
                for i in [1, 4]:
                    key_a = f"border_oval_{i}_a_left"
                    key_b = f"border_oval_{i}_b_left"
                    if key_a not in self._items:
                        self._items[key_a] = self._canvas.create_aa_circle(
                            0, 0, 0, tags=("border_corner_part", "border_parts_left", "border_parts"),
                            anchor=tkinter.CENTER)
                        self._items[key_b] = self._canvas.create_aa_circle(
                            0, 0, 0, tags=("border_corner_part", "border_parts_left", "border_parts"),
                            anchor=tkinter.CENTER, angle=180)
                        requires_recoloring = True
                    else:
                        self._canvas.itemconfig(self._items[key_a], state='normal')
                        self._canvas.itemconfig(self._items[key_b], state='normal')

                # Right side
                for i in [2, 3]:
                    key_a = f"border_oval_{i}_a_right"
                    key_b = f"border_oval_{i}_b_right"
                    if key_a not in self._items:
                        self._items[key_a] = self._canvas.create_aa_circle(
                            0, 0, 0,
                            tags=("border_corner_part", "border_parts_right", "border_parts", "right_parts"),
                            anchor=tkinter.CENTER)
                        self._items[key_b] = self._canvas.create_aa_circle(
                            0, 0, 0,
                            tags=("border_corner_part", "border_parts_right", "border_parts", "right_parts"),
                            anchor=tkinter.CENTER, angle=180)
                        requires_recoloring = True
                    else:
                        self._canvas.itemconfig(self._items[key_a], state='normal')
                        self._canvas.itemconfig(self._items[key_b], state='normal')

                # Set positions of border corner parts
                self._canvas.coords(self._items["border_oval_1_a_left"], corner_radius, corner_radius, corner_radius)
                self._canvas.coords(self._items["border_oval_1_b_left"], corner_radius, corner_radius, corner_radius)
                self._canvas.coords(self._items["border_oval_2_a_right"], width - corner_radius, corner_radius,
                                    corner_radius)
                self._canvas.coords(self._items["border_oval_2_b_right"], width - corner_radius, corner_radius,
                                    corner_radius)
                self._canvas.coords(self._items["border_oval_3_a_right"], width - corner_radius, height - corner_radius,
                                    corner_radius)
                self._canvas.coords(self._items["border_oval_3_b_right"], width - corner_radius, height - corner_radius,
                                    corner_radius)
                self._canvas.coords(self._items["border_oval_4_a_left"], corner_radius, height - corner_radius,
                                    corner_radius)
                self._canvas.coords(self._items["border_oval_4_b_left"], corner_radius, height - corner_radius,
                                    corner_radius)
            else:
                # Hide border corner parts
                for i in [1, 4]:
                    key_a = f"border_oval_{i}_a_left"
                    key_b = f"border_oval_{i}_b_left"
                    if key_a in self._items:
                        self._canvas.itemconfig(self._items[key_a], state='hidden')
                        self._canvas.itemconfig(self._items[key_b], state='hidden')
                for i in [2, 3]:
                    key_a = f"border_oval_{i}_a_right"
                    key_b = f"border_oval_{i}_b_right"
                    if key_a in self._items:
                        self._canvas.itemconfig(self._items[key_a], state='hidden')
                        self._canvas.itemconfig(self._items[key_b], state='hidden')

            # Border rectangle parts
            for side in ["left", "right"]:
                key1 = f"border_rectangle_1_{side}"
                key2 = f"border_rectangle_2_{side}"
                tags = (f"border_rectangle_part", f"border_parts_{side}", "border_parts")
                if side == "right":
                    tags += ("right_parts",)

                if key1 not in self._items:
                    self._items[key1] = self._canvas.create_rectangle(
                        0, 0, 0, 0, tags=tags, width=0)
                    requires_recoloring = True
                else:
                    self._canvas.itemconfig(self._items[key1], state='normal')

                if key2 not in self._items:
                    self._items[key2] = self._canvas.create_rectangle(
                        0, 0, 0, 0, tags=tags, width=0)
                    requires_recoloring = True
                else:
                    self._canvas.itemconfig(self._items[key2], state='normal')

            # Set positions of border rectangle parts
            self._canvas.coords(self._items["border_rectangle_1_left"], 0, corner_radius, left_section_width,
                                height - corner_radius)
            self._canvas.coords(self._items["border_rectangle_2_left"], corner_radius, 0, left_section_width, height)
            self._canvas.coords(self._items["border_rectangle_1_right"], left_section_width, corner_radius, width,
                                height - corner_radius)
            self._canvas.coords(self._items["border_rectangle_2_right"], left_section_width, 0, width - corner_radius,
                                height)
        else:
            # Hide border parts
            for side in ["left", "right"]:
                for key in [f"border_rectangle_1_{side}", f"border_rectangle_2_{side}"]:
                    if key in self._items:
                        self._canvas.itemconfig(self._items[key], state='hidden')
                for i in [1, 4]:
                    key_a = f"border_oval_{i}_a_left"
                    key_b = f"border_oval_{i}_b_left"
                    if key_a in self._items:
                        self._canvas.itemconfig(self._items[key_a], state='hidden')
                        self._canvas.itemconfig(self._items[key_b], state='hidden')
                for i in [2, 3]:
                    key_a = f"border_oval_{i}_a_right"
                    key_b = f"border_oval_{i}_b_right"
                    if key_a in self._items:
                        self._canvas.itemconfig(self._items[key_a], state='hidden')
                        self._canvas.itemconfig(self._items[key_b], state='hidden')

        # Inner parts
        if inner_corner_radius > 0:
            # Inner corner parts
            # Left side
            for i in [1, 4]:
                key_a = f"inner_oval_{i}_a_left"
                key_b = f"inner_oval_{i}_b_left"
                if key_a not in self._items:
                    self._items[key_a] = self._canvas.create_aa_circle(
                        0, 0, 0, tags=("inner_corner_part", "inner_parts_left", "inner_parts"), anchor=tkinter.CENTER)
                    self._items[key_b] = self._canvas.create_aa_circle(
                        0, 0, 0, tags=("inner_corner_part", "inner_parts_left", "inner_parts"),
                        anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True
                else:
                    self._canvas.itemconfig(self._items[key_a], state='normal')
                    self._canvas.itemconfig(self._items[key_b], state='normal')

            # Right side
            for i in [2, 3]:
                key_a = f"inner_oval_{i}_a_right"
                key_b = f"inner_oval_{i}_b_right"
                if key_a not in self._items:
                    self._items[key_a] = self._canvas.create_aa_circle(
                        0, 0, 0,
                        tags=("inner_corner_part", "inner_parts_right", "inner_parts", "right_parts"),
                        anchor=tkinter.CENTER)
                    self._items[key_b] = self._canvas.create_aa_circle(
                        0, 0, 0,
                        tags=("inner_corner_part", "inner_parts_right", "inner_parts", "right_parts"),
                        anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True
                else:
                    self._canvas.itemconfig(self._items[key_a], state='normal')
                    self._canvas.itemconfig(self._items[key_b], state='normal')

            # Set positions of inner corner parts
            self._canvas.coords(self._items["inner_oval_1_a_left"],
                                border_width + inner_corner_radius, border_width + inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_1_b_left"],
                                border_width + inner_corner_radius, border_width + inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_2_a_right"],
                                width - border_width - inner_corner_radius, border_width + inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_2_b_right"],
                                width - border_width - inner_corner_radius, border_width + inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_3_a_right"],
                                width - border_width - inner_corner_radius, height - border_width - inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_3_b_right"],
                                width - border_width - inner_corner_radius, height - border_width - inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_4_a_left"],
                                border_width + inner_corner_radius, height - border_width - inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["inner_oval_4_b_left"],
                                border_width + inner_corner_radius, height - border_width - inner_corner_radius,
                                inner_corner_radius)
        else:
            # Hide inner corner parts
            for i in [1, 4]:
                key_a = f"inner_oval_{i}_a_left"
                key_b = f"inner_oval_{i}_b_left"
                if key_a in self._items:
                    self._canvas.itemconfig(self._items[key_a], state='hidden')
                    self._canvas.itemconfig(self._items[key_b], state='hidden')
            for i in [2, 3]:
                key_a = f"inner_oval_{i}_a_right"
                key_b = f"inner_oval_{i}_b_right"
                if key_a in self._items:
                    self._canvas.itemconfig(self._items[key_a], state='hidden')
                    self._canvas.itemconfig(self._items[key_b], state='hidden')

        # Inner rectangle parts
        for side in ["left", "right"]:
            key1 = f"inner_rectangle_1_{side}"
            key2 = f"inner_rectangle_2_{side}"
            tags = (f"inner_rectangle_part", f"inner_parts_{side}", "inner_parts")
            if side == "right":
                tags += ("right_parts",)

            if key1 not in self._items:
                self._items[key1] = self._canvas.create_rectangle(
                    0, 0, 0, 0, tags=tags, width=0)
                requires_recoloring = True
            else:
                self._canvas.itemconfig(self._items[key1], state='normal')

            needs_inner_rectangle_2 = inner_corner_radius * 2 < height - (border_width * 2)
            if needs_inner_rectangle_2:
                if key2 not in self._items:
                    self._items[key2] = self._canvas.create_rectangle(
                        0, 0, 0, 0, tags=tags, width=0)
                    requires_recoloring = True
                else:
                    self._canvas.itemconfig(self._items[key2], state='normal')
            else:
                if key2 in self._items:
                    self._canvas.itemconfig(self._items[key2], state='hidden')

        # Set positions of inner rectangle parts
        self._canvas.coords(self._items["inner_rectangle_1_left"],
                            border_width + inner_corner_radius, border_width,
                            left_section_width, height - border_width)
        self._canvas.coords(self._items["inner_rectangle_1_right"],
                            left_section_width, border_width,
                            width - border_width - inner_corner_radius, height - border_width)

        if inner_corner_radius * 2 < height - (border_width * 2):
            self._canvas.coords(self._items["inner_rectangle_2_left"],
                                border_width, border_width + inner_corner_radius,
                                left_section_width, height - inner_corner_radius - border_width)
            self._canvas.coords(self._items["inner_rectangle_2_right"],
                                left_section_width, border_width + inner_corner_radius,
                                width - border_width, height - inner_corner_radius - border_width)

        if requires_recoloring:
            # Manage z-order
            self._canvas.tag_lower("inner_parts")
            self._canvas.tag_lower("border_parts")
            self._canvas.tag_lower("background_parts")

        return requires_recoloring

    def draw_rounded_progress_bar_with_border(self, width: Union[float, int], height: Union[float, int], corner_radius: Union[float, int],
                                              border_width: Union[float, int], progress_value_1: float, progress_value_2: float, orientation: str) -> bool:
        """ Draws a rounded bar on the canvas, and onntop sits a progress bar from value 1 to value 2 (range 0-1, left to right, bottom to top).
            The border elements get the 'border_parts' tag", the main elements get the 'inner_parts' tag and
            the progress elements get the 'progress_parts' tag. The 'orientation' argument defines from which direction the progress starts (n, w, s, e).

            returns bool if recoloring is necessary """

        current_settings = (width, height, corner_radius, border_width, progress_value_1, progress_value_2, orientation)
        if self._last_progress_bar_settings == current_settings:
            return False

        if self._round_width_to_even_numbers:
            width = math.floor(
                width / 2) * 2  # round _current_width and _current_height and restrict them to even values only
        if self._round_height_to_even_numbers:
            height = math.floor(height / 2) * 2

        if corner_radius > width / 2 or corner_radius > height / 2:  # restrict corner_radius if it's too large
            corner_radius = min(width / 2, height / 2)

        border_width = round(border_width)
        corner_radius = self.__calc_optimal_corner_radius(
            corner_radius)  # optimize corner_radius for different drawing methods (different rounding)

        if corner_radius >= border_width:
            inner_corner_radius = corner_radius - border_width
        else:
            inner_corner_radius = 0

        self._last_progress_bar_settings = current_settings

        if self.preferred_drawing_method == "polygon_shapes" or self.preferred_drawing_method == "circle_shapes":
            return self.__draw_rounded_progress_bar_with_border_polygon_shapes(width, height, corner_radius,
                                                                               border_width, inner_corner_radius,
                                                                               progress_value_1, progress_value_2,
                                                                               orientation)
        elif self.preferred_drawing_method == "font_shapes":
            return self.__draw_rounded_progress_bar_with_border_font_shapes(width, height, corner_radius, border_width,
                                                                            inner_corner_radius,
                                                                            progress_value_1, progress_value_2,
                                                                            orientation)

    def __draw_rounded_progress_bar_with_border_polygon_shapes(self, width: int, height: int, corner_radius: int, border_width: int, inner_corner_radius: int,
                                                               progress_value_1: float, progress_value_2: float, orientation: str) -> bool:

        requires_recoloring = self.__draw_rounded_rect_with_border_polygon_shapes(width, height, corner_radius,
                                                                                  border_width, inner_corner_radius)

        # Create or update progress parts
        if "progress_line_1" not in self._items:
            self._items["progress_line_1"] = self._canvas.create_polygon(
                (0, 0, 0, 0), tags=("progress_parts"), width=inner_corner_radius * 2, joinstyle=tkinter.ROUND)
            self._canvas.tag_raise("progress_parts", "inner_parts")
            requires_recoloring = True
        else:
            self._canvas.itemconfig(self._items["progress_line_1"], state='normal')

        if corner_radius <= border_width:
            bottom_right_shift = 0  # weird canvas rendering inaccuracy that has to be corrected in some cases
        else:
            bottom_right_shift = 0

        if orientation == "w":
            self._canvas.coords(self._items["progress_line_1"],
                                border_width + inner_corner_radius + (
                                            width - 2 * border_width - 2 * inner_corner_radius) * progress_value_1,
                                border_width + inner_corner_radius,
                                border_width + inner_corner_radius + (
                                            width - 2 * border_width - 2 * inner_corner_radius) * progress_value_2,
                                border_width + inner_corner_radius,
                                border_width + inner_corner_radius + (
                                            width - 2 * border_width - 2 * inner_corner_radius) * progress_value_2,
                                height - (border_width + inner_corner_radius) + bottom_right_shift,
                                border_width + inner_corner_radius + (
                                            width - 2 * border_width - 2 * inner_corner_radius) * progress_value_1,
                                height - (border_width + inner_corner_radius) + bottom_right_shift)
        elif orientation == "s":
            self._canvas.coords(self._items["progress_line_1"],
                                border_width + inner_corner_radius,
                                border_width + inner_corner_radius + (
                                            height - 2 * border_width - 2 * inner_corner_radius) * (
                                            1 - progress_value_2),
                                width - (border_width + inner_corner_radius),
                                border_width + inner_corner_radius + (
                                            height - 2 * border_width - 2 * inner_corner_radius) * (
                                            1 - progress_value_2),
                                width - (border_width + inner_corner_radius),
                                border_width + inner_corner_radius + (
                                            height - 2 * border_width - 2 * inner_corner_radius) * (
                                            1 - progress_value_1),
                                border_width + inner_corner_radius,
                                border_width + inner_corner_radius + (
                                            height - 2 * border_width - 2 * inner_corner_radius) * (
                                            1 - progress_value_1))

        self._canvas.itemconfig(self._items["progress_line_1"], width=inner_corner_radius * 2)

        return requires_recoloring

    def __draw_rounded_progress_bar_with_border_font_shapes(self, width: int, height: int, corner_radius: int, border_width: int, inner_corner_radius: int,
                                                            progress_value_1: float, progress_value_2: float, orientation: str) -> bool:
        requires_recoloring = False

        # Draw the base rounded rectangle
        requires_recoloring |= self.__draw_rounded_rect_with_border_font_shapes(
            width, height, corner_radius, border_width, inner_corner_radius, ())

        # Progress parts
        if inner_corner_radius > 0:
            # Create or update progress corner parts
            for i in range(1, 5):
                key_a = f"progress_oval_{i}_a"
                key_b = f"progress_oval_{i}_b"
                if key_a not in self._items:
                    self._items[key_a] = self._canvas.create_aa_circle(
                        0, 0, 0, tags=("progress_corner_part", "progress_parts"), anchor=tkinter.CENTER)
                    self._items[key_b] = self._canvas.create_aa_circle(
                        0, 0, 0, tags=("progress_corner_part", "progress_parts"), anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True
                else:
                    self._canvas.itemconfig(self._items[key_a], state='normal')
                    self._canvas.itemconfig(self._items[key_b], state='normal')

        # Create or update progress rectangle parts
        if "progress_rectangle_1" not in self._items:
            self._items["progress_rectangle_1"] = self._canvas.create_rectangle(
                0, 0, 0, 0, tags=("progress_rectangle_part", "progress_parts"), width=0)
            requires_recoloring = True
        else:
            self._canvas.itemconfig(self._items["progress_rectangle_1"], state='normal')

        needs_progress_rectangle_2 = inner_corner_radius * 2 < height - (border_width * 2)
        if needs_progress_rectangle_2:
            if "progress_rectangle_2" not in self._items:
                self._items["progress_rectangle_2"] = self._canvas.create_rectangle(
                    0, 0, 0, 0, tags=("progress_rectangle_part", "progress_parts"), width=0)
                requires_recoloring = True
            else:
                self._canvas.itemconfig(self._items["progress_rectangle_2"], state='normal')
        else:
            if "progress_rectangle_2" in self._items:
                self._canvas.itemconfig(self._items["progress_rectangle_2"], state='hidden')

        # Set positions of progress parts based on orientation
        if orientation == "w":
            # Horizontal orientation from the left
            x1 = border_width + inner_corner_radius + (
                        width - 2 * border_width - 2 * inner_corner_radius) * progress_value_1
            x2 = border_width + inner_corner_radius + (
                        width - 2 * border_width - 2 * inner_corner_radius) * progress_value_2

            # Update corner parts
            self._canvas.coords(self._items["progress_oval_1_a"], x1, border_width + inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_1_b"], x1, border_width + inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_2_a"], x2, border_width + inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_2_b"], x2, border_width + inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_3_a"], x2, height - border_width - inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_3_b"], x2, height - border_width - inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_4_a"], x1, height - border_width - inner_corner_radius,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_4_b"], x1, height - border_width - inner_corner_radius,
                                inner_corner_radius)

            # Update rectangle parts
            self._canvas.coords(self._items["progress_rectangle_1"], x1, border_width,
                                x2, height - border_width)
            if inner_corner_radius * 2 < height - (border_width * 2):
                self._canvas.coords(self._items["progress_rectangle_2"],
                                    x1 + inner_corner_radius, border_width + inner_corner_radius,
                                    x2 - inner_corner_radius, height - inner_corner_radius - border_width)

        elif orientation == "s":
            # Vertical orientation from the bottom
            y1 = border_width + inner_corner_radius + (height - 2 * border_width - 2 * inner_corner_radius) * (
                        1 - progress_value_2)
            y2 = border_width + inner_corner_radius + (height - 2 * border_width - 2 * inner_corner_radius) * (
                        1 - progress_value_1)

            # Update corner parts
            self._canvas.coords(self._items["progress_oval_1_a"], border_width + inner_corner_radius, y1,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_1_b"], border_width + inner_corner_radius, y1,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_2_a"], width - border_width - inner_corner_radius, y1,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_2_b"], width - border_width - inner_corner_radius, y1,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_3_a"], width - border_width - inner_corner_radius, y2,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_3_b"], width - border_width - inner_corner_radius, y2,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_4_a"], border_width + inner_corner_radius, y2,
                                inner_corner_radius)
            self._canvas.coords(self._items["progress_oval_4_b"], border_width + inner_corner_radius, y2,
                                inner_corner_radius)

            # Update rectangle parts
            self._canvas.coords(self._items["progress_rectangle_1"], border_width,
                                y1, width - border_width, y2)
            if inner_corner_radius * 2 < width - (border_width * 2):
                self._canvas.coords(self._items["progress_rectangle_2"],
                                    border_width + inner_corner_radius, y1 + inner_corner_radius,
                                    width - inner_corner_radius - border_width, y2 - inner_corner_radius)

        if requires_recoloring:
            # Manage z-order
            self._canvas.tag_raise("progress_parts", "inner_parts")

        return requires_recoloring

    def draw_rounded_slider_with_border_and_button(self, width: Union[float, int], height: Union[float, int], corner_radius: Union[float, int],
                                                   border_width: Union[float, int], button_length: Union[float, int], button_corner_radius: Union[float, int],
                                                   slider_value: float, orientation: str) -> bool:

        current_settings = (width, height, corner_radius, border_width, button_length,
                            button_corner_radius, slider_value, orientation)
        if self._last_slider_settings == current_settings:
            return False

        if self._round_width_to_even_numbers:
            width = math.floor(
                width / 2) * 2  # round _current_width and _current_height and restrict them to even values only
        if self._round_height_to_even_numbers:
            height = math.floor(height / 2) * 2

        if corner_radius > width / 2 or corner_radius > height / 2:  # restrict corner_radius if it's too large
            corner_radius = min(width / 2, height / 2)

        if button_corner_radius > width / 2 or button_corner_radius > height / 2:  # restrict button_corner_radius if it's too large
            button_corner_radius = min(width / 2, height / 2)

        button_length = round(button_length)
        border_width = round(border_width)
        button_corner_radius = round(button_corner_radius)
        corner_radius = self.__calc_optimal_corner_radius(
            corner_radius)  # optimize corner_radius for different drawing methods (different rounding)

        if corner_radius >= border_width:
            inner_corner_radius = corner_radius - border_width
        else:
            inner_corner_radius = 0

        self._last_slider_settings = current_settings

        if self.preferred_drawing_method == "polygon_shapes" or self.preferred_drawing_method == "circle_shapes":
            return self.__draw_rounded_slider_with_border_and_button_polygon_shapes(width, height, corner_radius,
                                                                                    border_width, inner_corner_radius,
                                                                                    button_length, button_corner_radius,
                                                                                    slider_value, orientation)
        elif self.preferred_drawing_method == "font_shapes":
            return self.__draw_rounded_slider_with_border_and_button_font_shapes(width, height, corner_radius,
                                                                                 border_width, inner_corner_radius,
                                                                                 button_length, button_corner_radius,
                                                                                 slider_value, orientation)

    def __draw_rounded_slider_with_border_and_button_polygon_shapes(self, width: int, height: int, corner_radius: int, border_width: int, inner_corner_radius: int,
                                                                    button_length: int, button_corner_radius: int, slider_value: float, orientation: str) -> bool:

        # Draw normal progress bar
        requires_recoloring = self.__draw_rounded_progress_bar_with_border_polygon_shapes(width, height, corner_radius,
                                                                                          border_width,
                                                                                          inner_corner_radius,
                                                                                          0, slider_value, orientation)

        # Create or update slider button part
        if "slider_line_1" not in self._items:
            self._items["slider_line_1"] = self._canvas.create_polygon(
                (0, 0, 0, 0), tags=("slider_parts"), width=button_corner_radius * 2, joinstyle=tkinter.ROUND)
            self._canvas.tag_raise("slider_parts")
            requires_recoloring = True
        else:
            self._canvas.itemconfig(self._items["slider_line_1"], state='normal')

        if orientation == "w":
            slider_x_position = corner_radius + (button_length / 2) + (
                        width - 2 * corner_radius - button_length) * slider_value
            self._canvas.coords(self._items["slider_line_1"],
                                slider_x_position - (button_length / 2), button_corner_radius,
                                slider_x_position + (button_length / 2), button_corner_radius,
                                slider_x_position + (button_length / 2), height - button_corner_radius,
                                slider_x_position - (button_length / 2), height - button_corner_radius)
            self._canvas.itemconfig(self._items["slider_line_1"], width=button_corner_radius * 2)
        elif orientation == "s":
            slider_y_position = corner_radius + (button_length / 2) + (height - 2 * corner_radius - button_length) * (
                        1 - slider_value)
            self._canvas.coords(self._items["slider_line_1"],
                                button_corner_radius, slider_y_position - (button_length / 2),
                                button_corner_radius, slider_y_position + (button_length / 2),
                                width - button_corner_radius, slider_y_position + (button_length / 2),
                                width - button_corner_radius, slider_y_position - (button_length / 2))
            self._canvas.itemconfig(self._items["slider_line_1"], width=button_corner_radius * 2)

        return requires_recoloring

    def __draw_rounded_slider_with_border_and_button_font_shapes(self, width: int, height: int, corner_radius: int, border_width: int, inner_corner_radius: int,
                                                                 button_length: int, button_corner_radius: int, slider_value: float, orientation: str) -> bool:
        requires_recoloring = False

        # Draw the progress bar
        requires_recoloring |= self.__draw_rounded_progress_bar_with_border_font_shapes(
            width, height, corner_radius, border_width, inner_corner_radius, 0, slider_value, orientation)

        # Slider button parts
        if button_corner_radius > 0:
            # Create or update slider corner parts
            for i in range(1, 5):
                key_a = f"slider_oval_{i}_a"
                key_b = f"slider_oval_{i}_b"
                if key_a not in self._items:
                    self._items[key_a] = self._canvas.create_aa_circle(
                        0, 0, 0, tags=("slider_corner_part", "slider_parts"), anchor=tkinter.CENTER)
                    self._items[key_b] = self._canvas.create_aa_circle(
                        0, 0, 0, tags=("slider_corner_part", "slider_parts"), anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True
                else:
                    self._canvas.itemconfig(self._items[key_a], state='normal')
                    self._canvas.itemconfig(self._items[key_b], state='normal')

        # Create or update slider rectangle parts
        if "slider_rectangle_1" not in self._items:
            self._items["slider_rectangle_1"] = self._canvas.create_rectangle(
                0, 0, 0, 0, tags=("slider_rectangle_part", "slider_parts"), width=0)
            requires_recoloring = True
        else:
            self._canvas.itemconfig(self._items["slider_rectangle_1"], state='normal')

        needs_slider_rectangle_2 = button_corner_radius * 2 < height
        if needs_slider_rectangle_2:
            if "slider_rectangle_2" not in self._items:
                self._items["slider_rectangle_2"] = self._canvas.create_rectangle(
                    0, 0, 0, 0, tags=("slider_rectangle_part", "slider_parts"), width=0)
                requires_recoloring = True
            else:
                self._canvas.itemconfig(self._items["slider_rectangle_2"], state='normal')
        else:
            if "slider_rectangle_2" in self._items:
                self._canvas.itemconfig(self._items["slider_rectangle_2"], state='hidden')

        # Set positions based on orientation
        if orientation == "w":
            slider_x_position = corner_radius + (button_length / 2) + (
                        width - 2 * corner_radius - button_length) * slider_value

            # Update corner parts
            self._canvas.coords(self._items["slider_oval_1_a"],
                                slider_x_position - (button_length / 2), button_corner_radius, button_corner_radius)
            self._canvas.coords(self._items["slider_oval_1_b"],
                                slider_x_position - (button_length / 2), button_corner_radius, button_corner_radius)
            self._canvas.coords(self._items["slider_oval_2_a"],
                                slider_x_position + (button_length / 2), button_corner_radius, button_corner_radius)
            self._canvas.coords(self._items["slider_oval_2_b"],
                                slider_x_position + (button_length / 2), button_corner_radius, button_corner_radius)
            self._canvas.coords(self._items["slider_oval_3_a"],
                                slider_x_position + (button_length / 2), height - button_corner_radius,
                                button_corner_radius)
            self._canvas.coords(self._items["slider_oval_3_b"],
                                slider_x_position + (button_length / 2), height - button_corner_radius,
                                button_corner_radius)
            self._canvas.coords(self._items["slider_oval_4_a"],
                                slider_x_position - (button_length / 2), height - button_corner_radius,
                                button_corner_radius)
            self._canvas.coords(self._items["slider_oval_4_b"],
                                slider_x_position - (button_length / 2), height - button_corner_radius,
                                button_corner_radius)

            # Update rectangle parts
            self._canvas.coords(self._items["slider_rectangle_1"],
                                slider_x_position - (button_length / 2), 0,
                                slider_x_position + (button_length / 2), height)
            if button_corner_radius * 2 < height:
                self._canvas.coords(self._items["slider_rectangle_2"],
                                    slider_x_position - (button_length / 2) - button_corner_radius,
                                    button_corner_radius,
                                    slider_x_position + (button_length / 2) + button_corner_radius,
                                    height - button_corner_radius)

        elif orientation == "s":
            slider_y_position = corner_radius + (button_length / 2) + (height - 2 * corner_radius - button_length) * (
                        1 - slider_value)

            # Update corner parts
            self._canvas.coords(self._items["slider_oval_1_a"],
                                button_corner_radius, slider_y_position - (button_length / 2), button_corner_radius)
            self._canvas.coords(self._items["slider_oval_1_b"],
                                button_corner_radius, slider_y_position - (button_length / 2), button_corner_radius)
            self._canvas.coords(self._items["slider_oval_2_a"],
                                button_corner_radius, slider_y_position + (button_length / 2), button_corner_radius)
            self._canvas.coords(self._items["slider_oval_2_b"],
                                button_corner_radius, slider_y_position + (button_length / 2), button_corner_radius)
            self._canvas.coords(self._items["slider_oval_3_a"],
                                width - button_corner_radius, slider_y_position + (button_length / 2),
                                button_corner_radius)
            self._canvas.coords(self._items["slider_oval_3_b"],
                                width - button_corner_radius, slider_y_position + (button_length / 2),
                                button_corner_radius)
            self._canvas.coords(self._items["slider_oval_4_a"],
                                width - button_corner_radius, slider_y_position - (button_length / 2),
                                button_corner_radius)
            self._canvas.coords(self._items["slider_oval_4_b"],
                                width - button_corner_radius, slider_y_position - (button_length / 2),
                                button_corner_radius)

            # Update rectangle parts
            self._canvas.coords(self._items["slider_rectangle_1"],
                                0, slider_y_position - (button_length / 2),
                                width, slider_y_position + (button_length / 2))
            if button_corner_radius * 2 < width:
                self._canvas.coords(self._items["slider_rectangle_2"],
                                    button_corner_radius,
                                    slider_y_position - (button_length / 2) - button_corner_radius,
                                    width - button_corner_radius,
                                    slider_y_position + (button_length / 2) + button_corner_radius)

        if requires_recoloring:
            # Manage z-order
            self._canvas.tag_raise("slider_parts")

        return requires_recoloring

    def draw_rounded_scrollbar(self, width: Union[float, int], height: Union[float, int], corner_radius: Union[float, int],
                               border_spacing: Union[float, int], start_value: float, end_value: float, orientation: str) -> bool:

        current_settings = (width, height, corner_radius, border_spacing, start_value, end_value, orientation)
        if self._last_scrollbar_settings == current_settings:
            return False

        if self._round_width_to_even_numbers:
            width = math.floor(
                width / 2) * 2  # round _current_width and _current_height and restrict them to even values only
        if self._round_height_to_even_numbers:
            height = math.floor(height / 2) * 2

        if corner_radius > width / 2 or corner_radius > height / 2:  # restrict corner_radius if it's too large
            corner_radius = min(width / 2, height / 2)

        border_spacing = round(border_spacing)
        corner_radius = self.__calc_optimal_corner_radius(
            corner_radius)  # optimize corner_radius for different drawing methods (different rounding)

        if corner_radius >= border_spacing:
            inner_corner_radius = corner_radius - border_spacing
        else:
            inner_corner_radius = 0

        self._last_scrollbar_settings = current_settings

        if self.preferred_drawing_method == "polygon_shapes" or self.preferred_drawing_method == "circle_shapes":
            return self.__draw_rounded_scrollbar_polygon_shapes(width, height, corner_radius, inner_corner_radius,
                                                                start_value, end_value, orientation)
        elif self.preferred_drawing_method == "font_shapes":
            return self.__draw_rounded_scrollbar_font_shapes(width, height, corner_radius, inner_corner_radius,
                                                             start_value, end_value, orientation)

    def __draw_rounded_scrollbar_polygon_shapes(self, width: int, height: int, corner_radius: int, inner_corner_radius: int,
                                                start_value: float, end_value: float, orientation: str) -> bool:
        requires_recoloring = False

        # Create or update border rectangle
        if "border_rectangle_1" not in self._items:
            self._items["border_rectangle_1"] = self._canvas.create_rectangle(
                0, 0, width, height, tags=("border_parts"), width=0)
            requires_recoloring = True
        else:
            self._canvas.itemconfig(self._items["border_rectangle_1"], state='normal')
            self._canvas.coords(self._items["border_rectangle_1"], 0, 0, width, height)

        # Create or update scrollbar parts
        if "scrollbar_polygon_1" not in self._items:
            self._items["scrollbar_polygon_1"] = self._canvas.create_polygon(
                (0, 0, 0, 0), tags=("scrollbar_parts"), width=inner_corner_radius * 2, joinstyle=tkinter.ROUND)
            self._canvas.tag_raise("scrollbar_parts", "border_parts")
            requires_recoloring = True
        else:
            self._canvas.itemconfig(self._items["scrollbar_polygon_1"], state='normal')

        if orientation == "vertical":
            self._canvas.coords(self._items["scrollbar_polygon_1"],
                                corner_radius, corner_radius + (height - 2 * corner_radius) * start_value,
                                width - corner_radius, corner_radius + (height - 2 * corner_radius) * start_value,
                                width - corner_radius, corner_radius + (height - 2 * corner_radius) * end_value,
                                corner_radius, corner_radius + (height - 2 * corner_radius) * end_value)
        elif orientation == "horizontal":
            self._canvas.coords(self._items["scrollbar_polygon_1"],
                                corner_radius + (width - 2 * corner_radius) * start_value, corner_radius,
                                corner_radius + (width - 2 * corner_radius) * end_value, corner_radius,
                                corner_radius + (width - 2 * corner_radius) * end_value, height - corner_radius,
                                corner_radius + (width - 2 * corner_radius) * start_value, height - corner_radius)

        self._canvas.itemconfig(self._items["scrollbar_polygon_1"], width=inner_corner_radius * 2)

        return requires_recoloring

    def __draw_rounded_scrollbar_font_shapes(self, width: int, height: int, corner_radius: int,
                                             inner_corner_radius: int,
                                             start_value: float, end_value: float, orientation: str) -> bool:
        requires_recoloring = False

        # Create or update border rectangle
        if "border_rectangle_1" not in self._items:
            self._items["border_rectangle_1"] = self._canvas.create_rectangle(
                0, 0, width, height, tags=("border_parts"), width=0)
            requires_recoloring = True
        else:
            self._canvas.itemconfig(self._items["border_rectangle_1"], state='normal')
            self._canvas.coords(self._items["border_rectangle_1"], 0, 0, width, height)

        # Scrollbar parts
        if inner_corner_radius > 0:
            # Create or update scrollbar corner parts
            for i in range(1, 5):
                key_a = f"scrollbar_oval_{i}_a"
                key_b = f"scrollbar_oval_{i}_b"
                if key_a not in self._items:
                    self._items[key_a] = self._canvas.create_aa_circle(
                        0, 0, 0, tags=("scrollbar_corner_part", "scrollbar_parts"), anchor=tkinter.CENTER)
                    self._items[key_b] = self._canvas.create_aa_circle(
                        0, 0, 0, tags=("scrollbar_corner_part", "scrollbar_parts"), anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True
                else:
                    self._canvas.itemconfig(self._items[key_a], state='normal')
                    self._canvas.itemconfig(self._items[key_b], state='normal')
        else:
            # Hide scrollbar corner parts
            for i in range(1, 5):
                key_a = f"scrollbar_oval_{i}_a"
                key_b = f"scrollbar_oval_{i}_b"
                if key_a in self._items:
                    self._canvas.itemconfig(self._items[key_a], state='hidden')
                    self._canvas.itemconfig(self._items[key_b], state='hidden')

        # Create or update scrollbar rectangle parts
        if "scrollbar_rectangle_1" not in self._items:
            self._items["scrollbar_rectangle_1"] = self._canvas.create_rectangle(
                0, 0, 0, 0, tags=("scrollbar_rectangle_part", "scrollbar_parts"), width=0)
            requires_recoloring = True
        else:
            self._canvas.itemconfig(self._items["scrollbar_rectangle_1"], state='normal')

        needs_scrollbar_rectangle_2 = (height if orientation == "vertical" else width) > 2 * corner_radius
        if needs_scrollbar_rectangle_2:
            if "scrollbar_rectangle_2" not in self._items:
                self._items["scrollbar_rectangle_2"] = self._canvas.create_rectangle(
                    0, 0, 0, 0, tags=("scrollbar_rectangle_part", "scrollbar_parts"), width=0)
                requires_recoloring = True
            else:
                self._canvas.itemconfig(self._items["scrollbar_rectangle_2"], state='normal')
        else:
            if "scrollbar_rectangle_2" in self._items:
                self._canvas.itemconfig(self._items["scrollbar_rectangle_2"], state='hidden')

        # Set positions based on orientation
        if orientation == "vertical":
            y1 = corner_radius + (height - 2 * corner_radius) * start_value
            y2 = corner_radius + (height - 2 * corner_radius) * end_value

            # Update rectangle parts
            self._canvas.coords(self._items["scrollbar_rectangle_1"],
                                corner_radius - inner_corner_radius, y1,
                                width - (corner_radius - inner_corner_radius), y2)

            if inner_corner_radius > 0:
                self._canvas.coords(self._items["scrollbar_rectangle_2"],
                                    corner_radius, y1 - inner_corner_radius,
                                    width - corner_radius, y2 + inner_corner_radius)

                # Update corner parts
                self._canvas.coords(self._items["scrollbar_oval_1_a"], corner_radius, y1, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_1_b"], corner_radius, y1, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_2_a"], width - corner_radius, y1, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_2_b"], width - corner_radius, y1, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_3_a"], width - corner_radius, y2, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_3_b"], width - corner_radius, y2, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_4_a"], corner_radius, y2, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_4_b"], corner_radius, y2, inner_corner_radius)

        elif orientation == "horizontal":
            x1 = corner_radius + (width - 2 * corner_radius) * start_value
            x2 = corner_radius + (width - 2 * corner_radius) * end_value

            # Update rectangle parts
            self._canvas.coords(self._items["scrollbar_rectangle_1"],
                                x1, corner_radius - inner_corner_radius,
                                x2, height - (corner_radius - inner_corner_radius))

            if inner_corner_radius > 0:
                self._canvas.coords(self._items["scrollbar_rectangle_2"],
                                    x1 - inner_corner_radius, corner_radius,
                                    x2 + inner_corner_radius, height - corner_radius)

                # Update corner parts
                self._canvas.coords(self._items["scrollbar_oval_1_a"], x1, corner_radius, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_1_b"], x1, corner_radius, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_2_a"], x2, corner_radius, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_2_b"], x2, corner_radius, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_3_a"], x2, height - corner_radius, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_3_b"], x2, height - corner_radius, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_4_a"], x1, height - corner_radius, inner_corner_radius)
                self._canvas.coords(self._items["scrollbar_oval_4_b"], x1, height - corner_radius, inner_corner_radius)

        if requires_recoloring:
            # Manage z-order
            self._canvas.tag_raise("scrollbar_parts", "border_parts")

        return requires_recoloring

    def draw_checkmark(self, width: Union[float, int], height: Union[float, int], size: Union[int, float]) -> bool:
        """ Draws a rounded rectangle with a corner_radius and border_width on the canvas. The border elements have a 'border_parts' tag,
            the main foreground elements have an 'inner_parts' tag to color the elements accordingly.

            returns bool if recoloring is necessary """

        size = round(size)
        requires_recoloring = False
        x, y, radius = width / 2, height / 2, size / 2.8

        if self.preferred_drawing_method in ("polygon_shapes", "circle_shapes"):
            if not self._canvas.find_withtag("checkmark"):
                self._canvas.create_line(0, 0, 0, 0,
                    tags=("checkmark", "create_line"),
                    width=round(height / 8),
                    joinstyle=tkinter.MITER,
                    capstyle=tkinter.ROUND)
                requires_recoloring = True
            self._canvas.coords(
                "checkmark",
                x + radius, y - radius,
                x - radius / 4, y + radius * 0.8,
                x - radius, y + radius / 6)

        elif self.preferred_drawing_method == "font_shapes":
            if not self._canvas.find_withtag("checkmark"):
                self._canvas.create_text(0, 0, text="Z",
                    font=("CustomTkinter_shapes_font", -size),
                    tags=("checkmark", "create_text"),
                    anchor=tkinter.CENTER)
                requires_recoloring = True
            self._canvas.coords("checkmark", round(width / 2), round(height / 2))

        self._canvas.tag_raise("checkmark")

        return requires_recoloring

    def draw_dropdown_arrow(self, x_position: Union[int, float], y_position: Union[int, float], size: Union[int, float]) -> bool:
        """ Draws a dropdown bottom facing arrow at (x_position, y_position) in a given size

            returns bool if recoloring is necessary """

        current_settings = (round(x_position), round(y_position), round(size))
        if self._last_dropdown_arrow == current_settings:
            return False

        x, y, size = current_settings
        requires_recoloring = False

        if "dropdown_arrow" not in self._items:
            if self.preferred_drawing_method in ("polygon_shapes", "circle_shapes"):
                self._items["dropdown_arrow"] = self._canvas.create_line(
                    0, 0, 0, 0, tags="dropdown_arrow", width=round(size / 3), joinstyle=tkinter.ROUND,
                    capstyle=tkinter.ROUND
                )
            elif self.preferred_drawing_method == "font_shapes":
                self._items["dropdown_arrow"] = self._canvas.create_text(
                    0, 0, text="Y", font=("CustomTkinter_shapes_font", -size), tags="dropdown_arrow",
                    anchor=tkinter.CENTER
                )
            self._canvas.tag_raise("dropdown_arrow")
            requires_recoloring = True

        if self.preferred_drawing_method in ("polygon_shapes", "circle_shapes"):
            half_size = size / 2
            coords = [
                x - half_size, y - size / 5,
                x, y + size / 5,
                x + half_size, y - size / 5
            ]
            self._canvas.coords(self._items["dropdown_arrow"], *coords)
            self._canvas.itemconfig(self._items["dropdown_arrow"], width=round(size / 3))
        else:
            self._canvas.coords(self._items["dropdown_arrow"], x, y)
            self._canvas.itemconfigure(self._items["dropdown_arrow"], font=("CustomTkinter_shapes_font", -size))

        self._last_dropdown_arrow = current_settings

        return requires_recoloring
