# CTkTable Widget by Akascape
# License: MIT
# Author: Akash Bora

import customtkinter
import copy


class CTkTable(customtkinter.CTkFrame):
    """ CTkTable Widget """

    __slots__ = ("master", "rows", "columns", "padx", "pady", "width", "height", "values", "colors", "orientation",
                "color_phase", "border_width", "text_color", "border_color", "font", "header_color", "corner_radius",
                "write", "command", "anchor", "hover_color", "hover", "justify", "wraplength", "data", "frame", 
                "corner_buttons", "cell_bindings", "phase", "corner", "orient", "fg_color", "fg_color2", "inside_frame")

    def __init__(
            self,
            master: any,
            row: int = None,
            column: int = None,
            padx: int = 1,
            pady: int = 0,
            width: int = 140,
            height: int = 28,
            values: list = None,
            colors: list = [None, None],
            orientation: str = "horizontal",
            color_phase: str = "horizontal",
            border_width: int = 0,
            text_color: str or tuple = None,
            border_color: str or tuple = None,
            font: tuple = None,
            header_color: str or tuple = None,
            corner_radius: int = 11,
            write: str = False,
            command=None,
            anchor: str = "c",
            hover_color: str or tuple = None,
            hover: bool = False,
            justify: str = "center",
            wraplength: int = 1000,
            **kwargs):

        super().__init__(master, fg_color="transparent")

        if values is None:
            values = [[None, None], [None, None]]

        self.master = master  # parent widget
        self.rows = row if row else len(values)  # number of default rows
        self.columns = column if column else len(values[0])  # number of default columns
        self.width = width
        self.height = height
        self.padx = padx  # internal padding between the rows/columns
        self.pady = pady
        self.command = command
        self.values = values  # the default values of the table
        self.colors = colors  # colors of the table if required
        self.header_color = header_color  # specify the topmost row color
        self.phase = color_phase
        self.corner = corner_radius
        self.write = write
        self.justify = justify

        if self.write:
            border_width = border_width = +1

        if hover_color is not None and hover is False:
            hover = True

        self.anchor = anchor
        self.wraplength = wraplength
        self.hover = hover
        self.border_width = border_width
        self.hover_color = customtkinter.ThemeManager.theme["CTkButton"][
            "hover_color"] if hover_color is None else hover_color
        self.orient = orientation
        self.border_color = customtkinter.ThemeManager.theme["CTkButton"][
            "border_color"] if border_color is None else border_color
        self.inside_frame = customtkinter.CTkFrame(self, border_width=0, fg_color="transparent")
        super().configure(border_color=self.border_color, border_width=self.border_width, corner_radius=self.corner)
        self.inside_frame.pack(expand=True, fill="both", padx=self.border_width, pady=self.border_width)

        self.text_color = customtkinter.ThemeManager.theme["CTkLabel"][
            "text_color"] if text_color is None else text_color
        self.font = font
        # if colors are None then use the default frame colors:
        self.data = {}
        self.fg_color = customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"] if not self.colors[0] else self.colors[
            0]
        self.fg_color2 = customtkinter.ThemeManager.theme["CTkFrame"]["top_fg_color"] if not self.colors[1] else \
            self.colors[1]

        if self.colors[0] is None and self.colors[1] is None:
            if self.fg_color == self.master.cget("fg_color"):
                self.fg_color = customtkinter.ThemeManager.theme["CTk"]["fg_color"]
            if self.fg_color2 == self.master.cget("fg_color"):
                self.fg_color2 = customtkinter.ThemeManager.theme["CTk"]["fg_color"]

        self.frame = {}
        self.corner_buttons = {}
        self.cell_bindings = {}
        self.draw_table(**kwargs)

    def draw_table(self, **kwargs):
        """ draw the table """

        for i in range(self.rows):
            self.inside_frame.grid_rowconfigure(i, weight=1)
        for j in range(self.columns):
            self.inside_frame.grid_columnconfigure(j, weight=1)

        row_colors = [self.fg_color if i % 2 == 0 else self.fg_color2 for i in range(self.rows)]
        column_colors = [self.fg_color if j % 2 == 0 else self.fg_color2 for j in range(self.columns)]

        for i in range(self.rows):
            for j in range(self.columns):
                fg = row_colors[i] if self.phase == "horizontal" else column_colors[j]

                if self.header_color and (
                        (self.orient == "horizontal" and i == 0) or (self.orient != "horizontal" and j == 0)):
                    fg = self.header_color

                corner_radius = self.corner
                if (self.border_width >= 5) and (self.corner >= 5):
                    tr = self.border_color
                else:
                    tr = ""
                if i == 0 and j == 0:
                    corners = [tr, fg, fg, fg]
                    hover_modify = self.hover

                elif i == self.rows - 1 and j == self.columns - 1:
                    corners = [fg, fg, tr, fg]
                    hover_modify = self.hover

                elif i == self.rows - 1 and j == 0:
                    corners = [fg, fg, fg, tr]
                    hover_modify = self.hover

                elif i == 0 and j == self.columns - 1:
                    corners = [fg, tr, fg, fg]
                    hover_modify = self.hover

                else:
                    corners = [fg, fg, fg, fg]
                    corner_radius = 0
                    hover_modify = False

                if i == 0:
                    pady = (0, self.pady)
                else:
                    pady = self.pady

                if j == 0:
                    padx = (0, self.padx)
                else:
                    padx = self.padx

                if i == self.rows - 1:
                    pady = (self.pady, 0)

                if j == self.columns - 1:
                    padx = (self.padx, 0)

                if self.values:
                    try:
                        if self.orient == "horizontal":
                            value = self.values[i][j]
                        else:
                            value = self.values[j][i]
                    except IndexError:
                        value = " "
                else:
                    value = " "

                if value == "":
                    value = " "

                args = copy.deepcopy(kwargs)
                args.setdefault("text_color", self.text_color)
                args.setdefault("height", self.height)
                args.setdefault("width", self.width)
                args["fg_color"] = fg  # Ensure fg_color is set correctly

                for key in ["corner_radius", "border_color", "border_width", "color_phase", "orientation", "write"]:
                    args.pop(key, None)

                if self.write:
                    for key in ["anchor", "hover_color", "hover"]:
                        args.pop(key, None)
                    args.setdefault("justify", self.justify)

                    self.frame[i, j] = customtkinter.CTkEntry(
                        self.inside_frame,
                        font=self.font,
                        corner_radius=0,
                        **args
                    )
                    if value is None:
                        value = " "
                    self.frame[i, j].insert(0, str(value))
                    self.frame[i, j].bind("<Key>", lambda e, row=i, column=j:
                                          self.after(100, lambda: self.manipulate_data(row, column)))
                    self.frame[i, j].grid(column=j, row=i, padx=padx, pady=pady, sticky="nsew")

                    if self.header_color:
                        if i == 0:
                            self.frame[i, j].configure(state="readonly")

                else:
                    args.setdefault("anchor", self.anchor)
                    args.setdefault("hover_color", self.hover_color)
                    args.setdefault("hover", self.hover)
                    if "justify" in args:
                        anchor = args["justify"]
                        if anchor == "center":
                            anchor = "c"
                        elif anchor == "left":
                            anchor = "w"
                        elif anchor == "right":
                            anchor = "e"
                        args.update({"anchor": anchor})
                        del args["justify"]
                    if value is None:
                        value = " "
                    self.frame[i, j] = customtkinter.CTkButton(
                        self.inside_frame,
                        background_corner_colors=corners,
                        font=self.font,
                        corner_radius=corner_radius,
                        text=value,
                        border_width=0,
                        command=(lambda row=i, col=j: self.command(
                            row, col)) if self.command else None,
                        **args
                    )
                    self.frame[i, j].grid(column=j, row=i, padx=padx, pady=pady, sticky="nsew")
                    if self.frame[i, j]._text_label is not None:
                        self.frame[i, j]._text_label.config(wraplength=self.wraplength)

                    if hover_modify:
                        self.dynamic_hover(self.frame[i, j], i, j)

                if (i, j) in self.cell_bindings:
                    for sequence, func in self.cell_bindings[(i, j)]:
                        self.frame[i, j].bind(sequence, func)

                self.rowconfigure(i, weight=1)
                self.columnconfigure(j, weight=1)
        self.update_idletasks()

    def dynamic_hover(self, frame, i, j):
        """ internal function to change corner cell colors """
        if not self.hover:
            return

        self.corner_buttons[i, j] = frame
        fg = frame.cget("fg_color")
        hv = frame.cget("hover_color")
        if (self.border_width >= 5) and (self.corner >= 5):
            tr = self.border_color
        else:
            tr = ""
        if i == 0 and j == 0:
            corners = [tr, fg, fg, fg]
            hover_corners = [tr, hv, hv, hv]
        elif i == self.rows - 1 and j == self.columns - 1:
            corners = [fg, fg, tr, fg]
            hover_corners = [hv, hv, tr, hv]
        elif i == self.rows - 1 and j == 0:
            corners = [fg, fg, fg, tr]
            hover_corners = [hv, hv, hv, tr]
        elif i == 0 and j == self.columns - 1:
            corners = [fg, tr, fg, fg]
            hover_corners = [hv, tr, hv, hv]
        else:
            return

        frame.configure(background_corner_colors=corners, fg_color=fg)
        frame.bind("<Enter>", lambda e, x=i, y=j, color=hover_corners, fg_color=hv: self.frame[x, y].configure(
            background_corner_colors=color, fg_color=fg_color))
        frame.bind("<Leave>", lambda e, x=i, y=j, color=corners, fg_color=fg: self.frame[x, y].configure(
            background_corner_colors=color, fg_color=fg_color))
    
    def unhover_cell(self, row, column):
        """ Remove the hover effect from a specified cell """
        if 0 <= row < self.rows and 0 <= column < self.columns:
            cell = self.frame.get((row, column))
            if cell:
                if self.header_color and (
                        (self.orient == "horizontal" and row == 0) or (self.orient != "horizontal" and column == 0)):
                    original_fg_color = self.header_color
                else:
                    original_fg_color = self.fg_color if row % 2 == 0 else self.fg_color2
                corners = [original_fg_color] * 4
                cell.configure(background_corner_colors=corners, fg_color=original_fg_color)
    
    def manipulate_data(self, row, column):
        """ entry callback """
        self.update_data()
        if self.command:
            self.command(self.get(row, column))

    def update_data(self):
        """ update the data when values are changed """
        for (i, j), widget in self.frame.items():
            if self.write:
                self.values[i][j] = widget.get()
            else:
                self.values[i][j] = widget.cget("text")

    def edit_row(self, row, value=None, **kwargs):
        """ edit all parameters of a single row """
        for i in range(self.columns):
            self.frame[row, i].configure(require_redraw=True, **kwargs)
            if value is not None:
                self.insert(row, i, value)
            if (row, i) in self.corner_buttons.keys():
                self.dynamic_hover(self.corner_buttons[row, i], row, i)
        self.update_data()

    def edit_column(self, column, value=None, **kwargs):
        """ edit all parameters of a single column """
        for i in range(self.rows):
            self.frame[i, column].configure(require_redraw=True, **kwargs)
            if value is not None:
                self.insert(i, column, value)
            if (i, column) in self.corner_buttons.keys():
                self.dynamic_hover(self.corner_buttons[i, column], i, column)
        self.update_data()

    def update_values(self, new_values):
        """
        Update the table with new values.
        Only cells whose values have changed are updated.
        """
        for row_index in range(min(len(new_values), self.rows)):
            for col_index in range(min(len(new_values[row_index]), self.columns)):
                new_value = str(new_values[row_index][col_index])
                cell = self.get_cell(row_index, col_index)
                if cell:
                    current_value = cell.get() if self.write else cell.cget('text')
                    if current_value != new_value:
                        if self.write:
                            cell.delete(0, customtkinter.END)
                            cell.insert(0, new_value)
                        else:
                            cell.configure(text=new_value)
        self.values = new_values
        self.update_idletasks()

    def refresh_table(self, new_values):
        """
        Update the table with new values.
        Adjust the number of rows and columns if necessary.
        """
        new_rows = len(new_values)
        new_columns = len(new_values[0]) if new_values else 0

        if new_rows != self.rows or new_columns != self.columns:
            for i in self.frame.values():
                i.destroy()
            self.frame = {}
            self.rows = new_rows
            self.columns = new_columns
            self.values = new_values
            self.draw_table()
        else:
            self.update_values(new_values)

    def add_row(self, values, index=None, **kwargs):
        """ add a new row """
        if index is None:
            index = len(self.values)
        self.values.insert(index, values)
        self.rows += 1
        for i in self.frame.values():
            i.destroy()
        self.frame = {}
        self.draw_table(**kwargs)
        self.update_data()

    def update_headers(self, new_headers):
        """
        Update the headers of the table with a list of new header values.
        Args:
            new_headers (list): A list of new header values.
        """
        if self.orient == "horizontal":
            # Update the headers in the first row
            for j in range(self.columns):
                self.frame[0, j].configure(text=new_headers[j])
        else:
            # Update the headers in the first column
            for i in range(self.rows):
                self.frame[i, 0].configure(text=new_headers[i])

    def update_text(self, row, column, new_text):
        """
        Update the text of a specific cell in the table.
        Args:
            row (int): The row index of the cell.
            column (int): The column index of the cell.
            new_text (str): The new text to set for the cell.
        """
        if 0 <= row < self.rows and 0 <= column < self.columns:
            # Check if the cell exists within the table boundaries
            cell = self.frame[row, column]
            if self.write:
                cell.delete(0, customtkinter.END)
                cell.insert(0, new_text)
            else:
                cell.configure(text=new_text)
            self.update_data()

    def add_column(self, values, index=None, **kwargs):
        """ add a new column """
        if index is None:
            index = len(self.values[0])
        for i, row in enumerate(self.values):
            row.insert(index, values[i])
        self.columns += 1
        for i in self.frame.values():
            i.destroy()
        self.frame = {}
        self.draw_table(**kwargs)
        self.update_data()

    def get_cell(self, row, column):
        """ Retrieve a specific cell widget from the table. """
        return self.frame.get((row, column))

    def get_all_cells(self):
        """
        Retrieve all cell widgets in the table.

        Returns:
            list: A list of all cell widgets.
        """
        return list(self.frame.values())

    def delete_row(self, index=None):
        """ delete a particular row """
        if len(self.values) == 1:
            return
        if index is None or index >= len(self.values):
            index = len(self.values) - 1
        self.values.pop(index)
        self.rows -= 1
        for i in self.frame.values():
            i.destroy()
        self.frame = {}
        self.draw_table()
        self.update_data()

    def delete_column(self, index=None):
        """ delete a particular column """
        if len(self.values[0]) == 1:
            return
        if index is None or index >= len(self.values[0]):
            index = len(self.values[0]) - 1
        for row in self.values:
            row.pop(index)
        self.columns -= 1
        for i in self.frame.values():
            i.destroy()
        self.frame = {}
        self.draw_table()
        self.update_data()

    def delete_rows(self, indices=[]):
        """ delete multiple rows """
        if not indices:
            return
        self.values = [v for i, v in enumerate(self.values) if i not in indices]
        self.rows -= len(set(indices))
        for i in self.frame.values():
            i.destroy()
        self.frame = {}
        self.draw_table()
        self.update_data()

    def delete_columns(self, indices=[]):
        """ delete multiple columns """
        if not indices:
            return
        for row in self.values:
            for index in sorted(indices, reverse=True):
                row.pop(index)
        self.columns -= len(set(indices))
        for i in self.frame.values():
            i.destroy()
        self.frame = {}
        self.draw_table()
        self.update_data()

    def get_row(self, row):
        """ get values of one row """
        return self.values[row]

    def get_column(self, column):
        """ get values of one column """
        return [row[column] for row in self.values]

    def select_row(self, row):
        """ select an entire row """
        self.edit_row(row, fg_color=self.hover_color)
        if self.orient != "horizontal":
            if self.header_color:
                self.edit_column(0, fg_color=self.header_color)
        else:
            if self.header_color:
                self.edit_row(0, fg_color=self.header_color)
        return self.get_row(row)

    def select_column(self, column):
        """ select an entire column """
        self.edit_column(column, fg_color=self.hover_color)
        if self.orient != "horizontal":
            if self.header_color:
                self.edit_column(0, fg_color=self.header_color)
        else:
            if self.header_color:
                self.edit_row(0, fg_color=self.header_color)
        return self.get_column(column)

    def deselect_row(self, row):
        """ deselect an entire row """
        self.edit_row(row, fg_color=self.fg_color if row % 2 == 0 else self.fg_color2)
        if self.orient != "horizontal":
            if self.header_color:
                self.edit_column(0, fg_color=self.header_color)
        else:
            if self.header_color:
                self.edit_row(0, fg_color=self.header_color)

    def deselect_column(self, column):
        """ deselect an entire column """
        for i in range(self.rows):
            fg_color = self.fg_color if i % 2 == 0 else self.fg_color2
            self.frame[i, column].configure(fg_color=fg_color)
        if self.orient != "horizontal":
            if self.header_color:
                self.edit_column(0, fg_color=self.header_color)
        else:
            if self.header_color:
                self.edit_row(0, fg_color=self.header_color)

    def select(self, row, column):
        """ select any cell """
        if row == 0 and column == 0:
            hover_corners = ["", self.hover_color, self.hover_color, self.hover_color]
        elif row == self.rows - 1 and column == self.columns - 1:
            hover_corners = [self.hover_color, self.hover_color, "", self.hover_color]
        elif row == self.rows - 1 and column == 0:
            hover_corners = [self.hover_color, self.hover_color, self.hover_color, ""]
        elif row == 0 and column == self.columns - 1:
            hover_corners = [self.hover_color, "", self.hover_color, self.hover_color]
        else:
            hover_corners = [self.hover_color, self.hover_color, self.hover_color, self.hover_color]
        self.frame[row, column].configure(background_corner_colors=hover_corners, fg_color=self.hover_color)

    def deselect(self, row, column):
        """ deselect any cell """
        fg_color = self.fg_color if row % 2 == 0 else self.fg_color2
        self.frame[row, column].configure(fg_color=fg_color)

    def insert(self, row, column, value, **kwargs):
        """ insert value in a specific block [row, column] """
        if self.write:
            self.frame[row, column].delete(0, customtkinter.END)
            self.frame[row, column].insert(0, value)
            self.frame[row, column].configure(**kwargs)
        else:
            self.frame[row, column].configure(require_redraw=True, text=value, **kwargs)
            if (row, column) in self.corner_buttons.keys():
                self.dynamic_hover(self.corner_buttons[row, column], row, column)
        self.values[row][column] = value
        self.update_data()

    def edit(self, row, column, **kwargs):
        """ change parameters of a cell without changing value """
        if self.write:
            self.frame[row, column].configure(**kwargs)
        else:
            self.frame[row, column].configure(require_redraw=True, **kwargs)
            if (row, column) in self.corner_buttons.keys():
                self.dynamic_hover(self.corner_buttons[row, column], row, column)

    def delete(self, row, column, **kwargs):
        """ delete a value from a specific block [row, column] """
        if self.write:
            self.frame[row, column].delete(0, customtkinter.END)
            self.frame[row, column].configure(**kwargs)
        else:
            self.frame[row, column].configure(require_redraw=True, text="", **kwargs)
        self.values[row][column] = ""
        self.update_data()

    def get(self, row=None, column=None):
        """ get the required cell """
        if row is not None and column is not None:
            return self.values[row][column]
        else:
            return self.values

    def get_selected_row(self):
        """ Return the index and data of the selected row """
        selected_row_index = None
        for i in range(self.rows):
            if self.frame[i, 0].cget("fg_color") == self.hover_color:
                selected_row_index = i
                break
        selected_row_data = self.get_row(selected_row_index) if selected_row_index is not None else None
        return {"row_index": selected_row_index, "values": selected_row_data}

    def get_selected_column(self):
        """ Return the index and data of the selected column """
        selected_column_index = None
        for i in range(self.columns):
            if self.frame[0, i].cget("fg_color") == self.hover_color:
                selected_column_index = i
                break
        selected_column_data = self.get_column(selected_column_index) if selected_column_index is not None else None
        return {"column_index": selected_column_index, "values": selected_column_data}

    def configure(self, **kwargs):
        """ configure table widget attributes"""

        if "colors" in kwargs:
            self.colors = kwargs.pop("colors")
            self.fg_color = self.colors[0]
            self.fg_color2 = self.colors[1]
        if "fg_color" in kwargs:
            self.colors = (kwargs["fg_color"], kwargs.pop("fg_color"))
            self.fg_color = self.colors[0]
            self.fg_color2 = self.colors[1]
        if "bg_color" in kwargs:
            super().configure(bg_color=kwargs["bg_color"])
            self.inside_frame.configure(fg_color=kwargs["bg_color"])
        if "header_color" in kwargs:
            self.header_color = kwargs.pop("header_color")
        if "rows" in kwargs:
            self.rows = kwargs.pop("rows")
        if "columns" in kwargs:
            self.columns = kwargs.pop("columns")
        if "values" in kwargs:
            self.values = kwargs.pop("values")
        if "padx" in kwargs:
            self.padx = kwargs.pop("padx")
        if "pady" in kwargs:
            self.pady = kwargs.pop("pady")
        if "wraplength" in kwargs:
            self.wraplength = kwargs.pop("wraplength")

        if "hover_color" in kwargs:
            self.hover_color = kwargs.pop("hover_color")
        if "text_color" in kwargs:
            self.text_color = kwargs.pop("text_color")
        if "border_width" in kwargs:
            self.border_width = kwargs.pop("border_width")
            super().configure(border_width=self.border_width)
            self.inside_frame.pack(expand=True, fill="both", padx=self.border_width, pady=self.border_width)
        if "border_color" in kwargs:
            self.border_color = kwargs.pop("border_color")
            super().configure(border_color=self.border_color)
        if "hover" in kwargs:
            self.hover = kwargs.pop("hover")
        if "anchor" in kwargs:
            self.anchor = kwargs.pop("anchor")
        if "corner_radius" in kwargs:
            self.corner = kwargs.pop("corner_radius")
            super().configure(corner_radius=self.corner)
        if "color_phase" in kwargs:
            self.phase = kwargs.pop("color_phase")
        if "justify" in kwargs:
            self.justify = kwargs.pop("justify")
        if "orientation" in kwargs:
            self.orient = kwargs.pop("orientation")
        if "write" in kwargs:
            self.write = kwargs.pop("write")
        if "width" in kwargs:
            self.width = kwargs.pop("width")
        if "height" in kwargs:
            self.height = kwargs.pop("height")

        self.update_values(self.values, **kwargs)

    def cget(self, param):
        if param == "width":
            return self.frame[0, 0].winfo_reqwidth()
        if param == "height":
            return self.frame[0, 0].winfo_reqheight()
        if param == "colors":
            return (self.fg_color, self.fg_color2)
        if param == "hover_color":
            return self.hover_color
        if param == "text_color":
            return self.text_color
        if param == "border_width":
            return self.border_width
        if param == "border_color":
            return self.border_color
        if param == "hover":
            return self.hover
        if param == "anchor":
            return self.anchor
        if param == "wraplength":
            return self.wraplength
        if param == "padx":
            return self.padx
        if param == "pady":
            return self.pady
        if param == "header_color":
            return self.header_color
        if param == "row":
            return self.rows
        if param == "column":
            return self.columns
        if param == "values":
            return self.values
        if param == "color_phase":
            return self.phase
        if param == "justify":
            return self.justify
        if param == "orientation":
            return self.orient
        if param == "write":
            return self.write

        return super().cget(param)

    def bind(self, sequence: str = None, command=None, add=True):
        """ Bind an event to the entire table """
        super().bind(sequence, command, add)
        self.inside_frame.bind(sequence, command, add)

    def unbind(self, sequence: str = None, funcid: str = None):
        """ Unbind an event from the entire table """
        super().unbind(sequence, funcid)
        self.inside_frame.unbind(sequence, funcid)

    def bind_cell(self, row, column, sequence, func):
        """ Bind an event to a specific cell """
        if (row, column) not in self.cell_bindings:
            self.cell_bindings[(row, column)] = []
        self.cell_bindings[(row, column)].append((sequence, func))
        cell = self.get_cell(row, column)
        if cell:
            cell.bind(sequence, func)

    def unbind_cell(self, row, column, sequence=None):
        """ Unbind an event from a specific cell """
        cell = self.get_cell(row, column)
        if cell and (row, column) in self.cell_bindings:
            if sequence:
                cell.unbind(sequence)
                self.cell_bindings[(row, column)] = [
                    (seq, func) for seq, func in self.cell_bindings[(row, column)] if seq != sequence]
            else:
                for seq, _ in self.cell_bindings[(row, column)]:
                    cell.unbind(seq)
                del self.cell_bindings[(row, column)]

    def destroy(self):
        for (row, column), cell in self.frame.items():
            if (row, column) in self.cell_bindings:
                for sequence, _ in self.cell_bindings[(row, column)]:
                    self.unbind_cell(row, column, sequence)
            if hasattr(cell, 'configure'):
                cell.configure(command=None)
            cell.destroy()
        self.frame.clear()
        self.cell_bindings.clear()
        if self.inside_frame:
            self.inside_frame.destroy()
            self.inside_frame = None
        self.data.clear()
        self.values = None
        super().destroy()
