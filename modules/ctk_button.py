import tkinter
import sys
from typing import Union, Tuple, Callable, Optional, Any

from .core_rendering import CTkCanvas
from .theme import ThemeManager
from .core_rendering import DrawEngine
from .core_widget_classes import CTkBaseClass
from .font import CTkFont
from .image import CTkImage


class CTkButton(CTkBaseClass):
    """
    Button with rounded corners, border, hover effect, image support, click command and textvariable.
    For detailed information check out the documentation.
    """

    _BINDING_EVENTS = ("<Enter>", "<Leave>", "<Button-1>")
    _image_label_spacing: int = 6

    def __init__(self,
                 master: Any,
                 width: int = 140,
                 height: int = 28,
                 corner_radius: Optional[int] = None,
                 border_width: Optional[int] = None,
                 border_spacing: int = 2,

                 bg_color: Union[str, Tuple[str, str]] = "transparent",
                 fg_color: Optional[Union[str, Tuple[str, str]]] = None,
                 hover_color: Optional[Union[str, Tuple[str, str]]] = None,
                 border_color: Optional[Union[str, Tuple[str, str]]] = None,
                 text_color: Optional[Union[str, Tuple[str, str]]] = None,
                 text_color_disabled: Optional[Union[str, Tuple[str, str]]] = None,

                 background_corner_colors: Union[Tuple[Union[str, Tuple[str, str]]], None] = None,
                 round_width_to_even_numbers: bool = True,
                 round_height_to_even_numbers: bool = True,

                 text: str = "CTkButton",
                 font: Optional[Union[tuple, CTkFont]] = None,
                 textvariable: Union[tkinter.Variable, None] = None,
                 image: Union[CTkImage, "ImageTk.PhotoImage", None] = None,
                 state: str = "normal",
                 hover: bool = True,
                 command: Union[Callable[[], Any], None] = None,
                 compound: str = "left",
                 anchor: str = "center",
                 **kwargs):

        # transfer basic functionality (bg_color, size, appearance_mode, scaling) to CTkBaseClass
        super().__init__(master=master, bg_color=bg_color, width=width, height=height, **kwargs)

        # shape
        self._corner_radius: int = ThemeManager.theme["CTkButton"]["corner_radius"] if corner_radius is None else corner_radius
        self._corner_radius = min(self._corner_radius, round(self._current_height / 2))
        self._border_width: int = ThemeManager.theme["CTkButton"]["border_width"] if border_width is None else border_width
        self._border_spacing: int = border_spacing

        # color
        self._fg_color: Union[str, Tuple[str, str]] = ThemeManager.theme["CTkButton"]["fg_color"] if fg_color is None else self._check_color_type(fg_color, transparency=True)
        self._hover_color: Union[str, Tuple[str, str]] = ThemeManager.theme["CTkButton"]["hover_color"] if hover_color is None else self._check_color_type(hover_color)
        self._border_color: Union[str, Tuple[str, str]] = ThemeManager.theme["CTkButton"]["border_color"] if border_color is None else self._check_color_type(border_color)
        self._text_color: Union[str, Tuple[str, str]] = ThemeManager.theme["CTkButton"]["text_color"] if text_color is None else self._check_color_type(text_color)
        self._text_color_disabled: Union[str, Tuple[str, str]] = ThemeManager.theme["CTkButton"]["text_color_disabled"] if text_color_disabled is None else self._check_color_type(text_color_disabled)

        # rendering options
        self._background_corner_colors: Union[Tuple[Union[str, Tuple[str, str]]], None] = background_corner_colors  # rendering options for DrawEngine
        self._round_width_to_even_numbers: bool = round_width_to_even_numbers  # rendering options for DrawEngine
        self._round_height_to_even_numbers: bool = round_height_to_even_numbers  # rendering options for DrawEngine

        # text, font
        self._text = text
        self._text_label: Union[tkinter.Label, None] = None
        self._textvariable: tkinter.Variable = textvariable
        self._font: Union[tuple, CTkFont] = CTkFont() if font is None else self._check_font_type(font)
        if isinstance(self._font, CTkFont):
            self._font.add_size_configure_callback(self._update_font)

        # image
        self._image = self._check_image_type(image)
        self._image_label: Union[tkinter.Label, None] = None
        if isinstance(self._image, CTkImage):
            self._image.add_configure_callback(self._update_image)

        # other
        self._state: str = state
        self._hover: bool = hover
        self._command: Callable = command
        self._compound: str = compound
        self._anchor: str = anchor
        self._click_animation_running: bool = False

        # canvas and draw engine
        self._canvas = CTkCanvas(master=self,
                                 highlightthickness=0,
                                 width=self._apply_widget_scaling(self._desired_width),
                                 height=self._apply_widget_scaling(self._desired_height))
        self._canvas.grid(row=0, column=0, rowspan=5, columnspan=5, sticky="nsew")
        self._draw_engine = DrawEngine(self._canvas)
        self._draw_engine.set_round_to_even_numbers(self._round_width_to_even_numbers, self._round_height_to_even_numbers)  # rendering options

        # configure cursor and initial draw
        self._create_bindings()
        self._set_cursor()
        self._draw()

    def _create_bindings(self, sequence: Optional[str] = None):
        """ set necessary bindings for functionality of widget, will overwrite other bindings """

        if sequence is not None and sequence not in self._BINDING_EVENTS:
            return

        handlers = {"<Enter>": self._on_enter, "<Leave>": self._on_leave, "<Button-1>": self._clicked}
        widgets = [w for w in (self._canvas, self._text_label, self._image_label) if w is not None]

        if sequence:
            for widget in widgets:
                widget.bind(sequence, handlers[sequence])
        else:
            for event, handler in handlers.items():
                for widget in widgets:
                    widget.bind(event, handler)

    def _set_scaling(self, *args, **kwargs):
        super()._set_scaling(*args, **kwargs)

        self._create_grid()

        if self._text_label is not None:
            self._text_label.configure(font=self._apply_font_scaling(self._font))

        self._update_image()

        self._canvas.configure(width=self._apply_widget_scaling(self._desired_width),
                               height=self._apply_widget_scaling(self._desired_height))
        self._draw(no_color_updates=True)

    def _set_appearance_mode(self, mode_string):
        super()._set_appearance_mode(mode_string)
        self._update_image()

    def _set_dimensions(self, width: int = None, height: int = None):
        super()._set_dimensions(width, height)

        self._canvas.configure(width=self._apply_widget_scaling(self._desired_width),
                               height=self._apply_widget_scaling(self._desired_height))
        self._draw()

    def _update_font(self):
        """ pass font to tkinter widgets with applied font scaling and update grid with workaround """
        if self._text_label is not None:
            self._text_label.configure(font=self._apply_font_scaling(self._font))

            # Workaround to force grid to be resized when text changes size.
            # Otherwise grid will lag and only resizes if other mouse action occurs.
            self._canvas.grid_forget()
            self._canvas.grid(row=0, column=0, rowspan=5, columnspan=5, sticky="nsew")

    def _update_image(self):
        if not hasattr(self, '_image_label') or self._image_label is None or not hasattr(self, '_image'):
            return

        if isinstance(self._image, CTkImage):
            new_scaled_image = self._image.create_scaled_photo_image(
                self._get_widget_scaling(), self._get_appearance_mode())

            if hasattr(self._image_label, '_last_image'):
                del self._image_label._last_image

            self._image_label._last_image = new_scaled_image
            self._image_label.configure(image=new_scaled_image)
        else:
            self._image_label.configure(image=self._image)

    def destroy(self):
        if isinstance(self._font, CTkFont):
            self._font.remove_size_configure_callback(self._update_font)
        if hasattr(self, '_image') and isinstance(self._image, CTkImage):
            self._image.remove_configure_callback(self._update_image)
        if hasattr(self, '_image_label') and hasattr(self._image_label, '_last_image'):
            del self._image_label._last_image
        super().destroy()

    def _draw(self, no_color_updates=False):
        if not self._canvas.winfo_exists():
            return

        super()._draw(no_color_updates)

        # Cache all scaled dimensions at once
        scaled_dims = {
            "width": self._apply_widget_scaling(self._current_width),
            "height": self._apply_widget_scaling(self._current_height),
            "corner_radius": self._apply_widget_scaling(self._corner_radius),
            "border_width": self._apply_widget_scaling(self._border_width)
        }

        # Pre-calculate all needed colors once
        if not no_color_updates:
            appearance_colors = {
                "bg": self._apply_appearance_mode(self._bg_color),
                "fg": self._apply_appearance_mode(self._fg_color),
                "border": self._apply_appearance_mode(self._border_color),
                "text": self._apply_appearance_mode(self._text_color if self._state != tkinter.DISABLED
                                                    else self._text_color_disabled)
            }
            self._current_colors = appearance_colors  # Cache for enter/leave events
        else:
            appearance_colors = self._current_colors

        # Draw background corners (only if needed)
        if self._background_corner_colors is not None:
            self._draw_engine.draw_background_corners(scaled_dims["width"], scaled_dims["height"])
            corner_colors = {
                f"background_corner_{pos}": self._apply_appearance_mode(color)
                for pos, color in zip(
                    ["top_left", "top_right", "bottom_right", "bottom_left"],
                    self._background_corner_colors
                )
            }
            # Batch update corner colors
            for tag, color in corner_colors.items():
                self._canvas.itemconfig(tag, fill=color)
        else:
            self._canvas.delete("background_parts")

        # Draw button shape
        requires_recoloring = self._draw_engine.draw_rounded_rect_with_border(
            scaled_dims["width"],
            scaled_dims["height"],
            scaled_dims["corner_radius"],
            scaled_dims["border_width"]
        )

        # Batch update colors if needed
        if not no_color_updates or requires_recoloring:
            inner_color = appearance_colors["bg"] if self._fg_color == "transparent" else appearance_colors["fg"]
            updates = {
                "bg": appearance_colors["bg"],
                "border_parts": {"outline": appearance_colors["border"], "fill": appearance_colors["border"]},
                "inner_parts": {"outline": inner_color, "fill": inner_color}
            }

            self._canvas.configure(bg=updates["bg"])
            for part, colors in updates.items():
                if isinstance(colors, dict):
                    self._canvas.itemconfig(part, **colors)

            # Update both labels' colors at once if they exist
            label_colors = {"bg": inner_color}
            text_label_colors = {**label_colors, "fg": appearance_colors["text"]}

            if self._text_label is not None:
                self._text_label.configure(**text_label_colors)
            if self._image_label is not None:
                self._image_label.configure(**label_colors)

        # Handle text label - create only if needed
        grid_needs_update = False
        if self._text and self._text != "":
            if self._text_label is None:
                self._text_label = tkinter.Label(
                    master=self, text=self._text, font=self._apply_font_scaling(self._font),
                    textvariable=self._textvariable, padx=0, pady=0, borderwidth=0, **text_label_colors)
                for event in ("<Enter>", "<Leave>", "<Button-1>"):
                    self._text_label.bind(event,{"<Enter>": self._on_enter, "<Leave>": self._on_leave,
                                                 "<Button-1>": self._clicked}[event])
                grid_needs_update = True
        elif self._text_label is not None:
            self._text_label.destroy()
            self._text_label = None
            grid_needs_update = True

        # Handle image label - create only if needed
        if self._image is not None:
            if self._image_label is None:
                self._image_label = tkinter.Label(master=self, **label_colors)
                for event in ("<Enter>", "<Leave>", "<Button-1>"):
                    self._image_label.bind(event,
                                           {"<Enter>": self._on_enter,
                                            "<Leave>": self._on_leave,
                                            "<Button-1>": self._clicked}[event]
                                           )
                grid_needs_update = True

            # Update image only if it's a CTkImage or first time
            if isinstance(self._image, CTkImage):
                current_img = self._image.create_scaled_photo_image(
                    self._get_widget_scaling(),
                    self._get_appearance_mode()
                )
                if hasattr(self._image_label, '_last_image'):
                    if self._image_label._last_image != current_img:
                        self._image_label._last_image = current_img
                        self._image_label.configure(image=current_img)
                else:
                    self._image_label._last_image = current_img
                    self._image_label.configure(image=current_img)
            elif not hasattr(self._image_label, 'image'):
                self._image_label.configure(image=self._image)
        elif self._image_label is not None:
            self._image_label.destroy()
            self._image_label = None
            grid_needs_update = True

        # Update grid only if needed
        if grid_needs_update:
            self._create_grid()

    def _create_grid(self):
        """ configure grid system (5x5) """

        # Calculate padding weights
        n_weight = s_weight = e_weight = w_weight = 1000
        if self._anchor != "center":
            if "n" in self._anchor: n_weight, s_weight = 0, 1000
            if "s" in self._anchor: n_weight, s_weight = 1000, 0
            if "e" in self._anchor: e_weight, w_weight = 1000, 0
            if "w" in self._anchor: e_weight, w_weight = 0, 1000

        # Calculate minimal sizes once
        minsize_rows = self._apply_widget_scaling(max(self._border_width + 1, self._border_spacing))
        minsize_cols = self._apply_widget_scaling(
            max(self._corner_radius, self._border_width + 1, self._border_spacing))

        self.grid_rowconfigure(0, weight=n_weight, minsize=minsize_rows)
        self.grid_rowconfigure(4, weight=s_weight, minsize=minsize_rows)
        self.grid_columnconfigure(0, weight=e_weight, minsize=minsize_cols)
        self.grid_columnconfigure(4, weight=w_weight, minsize=minsize_cols)

        # Configure inner grid based on compound
        if self._compound in ("right", "left"):
            self.grid_rowconfigure(2, weight=1)
            spacing = self._apply_widget_scaling(
                self._image_label_spacing) if self._image_label and self._text_label else 0
            self.grid_columnconfigure(2, weight=0, minsize=spacing)
            self.grid_rowconfigure((1, 3), weight=0)
            self.grid_columnconfigure((1, 3), weight=1)
        else:
            self.grid_columnconfigure(2, weight=1)
            spacing = self._apply_widget_scaling(
                self._image_label_spacing) if self._image_label and self._text_label else 0
            self.grid_rowconfigure(2, weight=0, minsize=spacing)
            self.grid_columnconfigure((1, 3), weight=0)
            self.grid_rowconfigure((1, 3), weight=1)

        # Position widgets based on compound
        positions = {
            "right": [(self._image_label, 2, 3, "w"), (self._text_label, 2, 1, "e")],
            "left": [(self._image_label, 2, 1, "e"), (self._text_label, 2, 3, "w")],
            "top": [(self._image_label, 1, 2, "s"), (self._text_label, 3, 2, "n")],
            "bottom": [(self._image_label, 3, 2, "n"), (self._text_label, 1, 2, "s")]
        }

        if self._compound in positions:
            for widget, row, col, sticky in positions[self._compound]:
                if widget is not None:
                    widget.grid(row=row, column=col, sticky=sticky)

    def configure(self, require_redraw=False, **kwargs):
        if "corner_radius" in kwargs:
            self._corner_radius = kwargs.pop("corner_radius")
            self._create_grid()
            require_redraw = True

        if "border_width" in kwargs:
            self._border_width = kwargs.pop("border_width")
            self._create_grid()
            require_redraw = True

        if "border_spacing" in kwargs:
            self._border_spacing = kwargs.pop("border_spacing")
            self._create_grid()
            require_redraw = True

        if "fg_color" in kwargs:
            self._fg_color = self._check_color_type(kwargs.pop("fg_color"), transparency=True)
            require_redraw = True

        if "hover_color" in kwargs:
            self._hover_color = self._check_color_type(kwargs.pop("hover_color"))
            require_redraw = True

        if "border_color" in kwargs:
            self._border_color = self._check_color_type(kwargs.pop("border_color"))
            require_redraw = True

        if "text_color" in kwargs:
            self._text_color = self._check_color_type(kwargs.pop("text_color"))
            require_redraw = True

        if "text_color_disabled" in kwargs:
            self._text_color_disabled = self._check_color_type(kwargs.pop("text_color_disabled"))
            require_redraw = True

        if "background_corner_colors" in kwargs:
            self._background_corner_colors = kwargs.pop("background_corner_colors")
            require_redraw = True

        if "text" in kwargs:
            self._text = kwargs.pop("text")
            if self._text_label is None:
                require_redraw = True  # text_label will be created in .draw()
            else:
                self._text_label.configure(text=self._text)

        if "font" in kwargs:
            if isinstance(self._font, CTkFont):
                self._font.remove_size_configure_callback(self._update_font)
            self._font = self._check_font_type(kwargs.pop("font"))
            if isinstance(self._font, CTkFont):
                self._font.add_size_configure_callback(self._update_font)

            self._update_font()

        if "textvariable" in kwargs:
            self._textvariable = kwargs.pop("textvariable")
            if self._text_label is not None:
                self._text_label.configure(textvariable=self._textvariable)

        if "image" in kwargs:
            if hasattr(self, '_image') and isinstance(self._image, CTkImage):
                self._image.remove_configure_callback(self._update_image)

            if hasattr(self, '_image_label') and hasattr(self._image_label, '_last_image'):
                del self._image_label._last_image

            self._image = self._check_image_type(kwargs.pop("image"))

            if isinstance(self._image, CTkImage):
                self._image.add_configure_callback(self._update_image)

            if hasattr(self, '_image_label') and self._image_label is not None:
                if isinstance(self._image, CTkImage):
                    new_scaled_image = self._image.create_scaled_photo_image(
                        self._get_widget_scaling(), self._get_appearance_mode())
                    self._image_label._last_image = new_scaled_image
                    self._image_label.configure(image=new_scaled_image)
                else:
                    self._image_label.configure(image=self._image)
            require_redraw = True

        if "state" in kwargs:
            self._state = kwargs.pop("state")
            self._set_cursor()
            require_redraw = True

        if "hover" in kwargs:
            self._hover = kwargs.pop("hover")

        if "command" in kwargs:
            self._command = kwargs.pop("command")
            self._set_cursor()

        if "compound" in kwargs:
            self._compound = kwargs.pop("compound")
            require_redraw = True

        if "anchor" in kwargs:
            self._anchor = kwargs.pop("anchor")
            self._create_grid()
            require_redraw = True

        super().configure(require_redraw=require_redraw, **kwargs)

    def cget(self, attribute_name: str) -> any:
        if attribute_name == "corner_radius":
            return self._corner_radius
        elif attribute_name == "border_width":
            return self._border_width
        elif attribute_name == "border_spacing":
            return self._border_spacing

        elif attribute_name == "fg_color":
            return self._fg_color
        elif attribute_name == "hover_color":
            return self._hover_color
        elif attribute_name == "border_color":
            return self._border_color
        elif attribute_name == "text_color":
            return self._text_color
        elif attribute_name == "text_color_disabled":
            return self._text_color_disabled
        elif attribute_name == "background_corner_colors":
            return self._background_corner_colors

        elif attribute_name == "text":
            return self._text
        elif attribute_name == "font":
            return self._font
        elif attribute_name == "textvariable":
            return self._textvariable
        elif attribute_name == "image":
            return self._image
        elif attribute_name == "state":
            return self._state
        elif attribute_name == "hover":
            return self._hover
        elif attribute_name == "command":
            return self._command
        elif attribute_name == "compound":
            return self._compound
        elif attribute_name == "anchor":
            return self._anchor
        else:
            return super().cget(attribute_name)

    def _set_cursor(self):
        if self._cursor_manipulation_enabled:
            if self._state == tkinter.DISABLED:
                if sys.platform == "darwin" and self._command is not None:
                    self.configure(cursor="arrow")
                elif sys.platform.startswith("win") and self._command is not None:
                    self.configure(cursor="arrow")

            elif self._state == tkinter.NORMAL:
                if sys.platform == "darwin" and self._command is not None:
                    self.configure(cursor="pointinghand")
                elif sys.platform.startswith("win") and self._command is not None:
                    self.configure(cursor="hand2")

    def _on_enter(self, event=None):
        if not (self._hover and self._state == "normal"):
            return

        color = self._hover_color if self._hover_color is not None else self._fg_color
        appearance_color = self._apply_appearance_mode(color)

        self._canvas.itemconfig("inner_parts", outline=appearance_color, fill=appearance_color)
        for label in (self._text_label, self._image_label):
            if label is not None:
                label.configure(bg=appearance_color)

    def _on_leave(self, event=None):
        self._click_animation_running = False
        color = self._bg_color if self._fg_color == "transparent" else self._fg_color
        appearance_color = self._apply_appearance_mode(color)

        self._canvas.itemconfig("inner_parts", outline=appearance_color, fill=appearance_color)
        for label in (self._text_label, self._image_label):
            if label is not None:
                label.configure(bg=appearance_color)

    def _click_animation(self):
        if self._click_animation_running:
            self._on_enter()

    def _clicked(self, event=None):
        if self._state != tkinter.DISABLED:

            # click animation: change color with .on_leave() and back to normal after 100ms with click_animation()
            self._on_leave()
            self._click_animation_running = True
            self.after(100, self._click_animation)

            if self._command is not None:
                self._command()

    def invoke(self):
        """ calls command function if button is not disabled """
        if self._state != tkinter.DISABLED:
            if self._command is not None:
                return self._command()

    def bind(self, sequence: str = None, command: Callable = None, add: Union[str, bool] = True):
        """ called on the tkinter.Canvas """
        if not (add == "+" or add is True):
            raise ValueError("'add' argument can only be '+' or True to preserve internal callbacks")
        self._canvas.bind(sequence, command, add=True)

        if self._text_label is not None:
            self._text_label.bind(sequence, command, add=True)
        if self._image_label is not None:
            self._image_label.bind(sequence, command, add=True)

    def unbind(self, sequence: str = None, funcid: str = None):
        """ called on the tkinter.Label and tkinter.Canvas """
        if funcid is not None:
            raise ValueError("'funcid' argument can only be None, because there is a bug in" +
                             " tkinter and its not clear whether the internal callbacks will be unbinded or not")
        self._canvas.unbind(sequence, None)

        if self._text_label is not None:
            self._text_label.unbind(sequence, None)
        if self._image_label is not None:
            self._image_label.unbind(sequence, None)

        self._create_bindings(sequence=sequence)  # restore internal callbacks for sequence

    def focus(self):
        return self._text_label.focus()

    def focus_set(self):
        return self._text_label.focus_set()

    def focus_force(self):
        return self._text_label.focus_force()
