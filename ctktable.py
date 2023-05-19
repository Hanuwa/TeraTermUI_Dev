import customtkinter


class CTkTable(customtkinter.CTkFrame):
    """ CTkTable Widget (Lite Version)"""

    def __init__(
            self,
            master: any = None,
            row: int = 5,
            column: int = 5,
            padx: int = 1,
            pady: int = 0,
            values: list = None):

        super().__init__(master, fg_color="transparent")

        self.master = master
        self.rows = row
        self.columns = column
        self.padx = padx
        self.pady = pady
        self.values = values
        self.fg_color = customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"]
        self.fg_color2 = customtkinter.ThemeManager.theme["CTkFrame"]["top_fg_color"]
        self._text_color = customtkinter.ThemeManager.theme["CTkLabel"]["text_color"]

        self.frame = {}
        self.draw_table()

    def draw_table(self):
        for i in range(self.rows):
            for j in range(self.columns):

                if i % 2 == 0:
                    fg = self.fg_color
                    text_color = self._text_color
                else:
                    fg = self.fg_color2
                    text_color = self._text_color

                if i == 0 and j == 0:
                    corners = ["", fg, fg, fg]
                elif i == self.rows - 1 and j == self.columns - 1:
                    corners = [fg, fg, "", fg]
                elif i == self.rows - 1 and j == 0:
                    corners = [fg, fg, fg, ""]
                elif i == 0 and j == self.columns - 1:
                    corners = [fg, "", fg, fg]
                else:
                    corners = [fg, fg, fg, fg]

                if self.values:
                    value = self.values[i][j]
                else:
                    value = " "

                self.frame[i, j] = customtkinter.CTkButton(self, background_corner_colors=corners, corner_radius=20,
                                                           fg_color=fg, hover=False, text=value, text_color=text_color)
                self.frame[i, j].grid(column=j, row=i, padx=self.padx, pady=self.pady, sticky="nsew")

                self.rowconfigure(i, weight=1)
                self.columnconfigure(j, weight=1)

    def edit_row(self, row, **kwargs):
        """ edit all parameters of a single row """
        for i in range(self.columns):
            self.frame[row, i].configure(**kwargs)

    def edit_column(self, column, **kwargs):
        """ edit all parameters of a single column """
        for i in range(self.rows):
            self.frame[i, column].configure(**kwargs)

    def update_values(self, values, **kwargs):
        """ update all values at once """
        for i in self.frame.values():
            i.destroy()
        self.frame = {}
        self.values = values
        self.draw_table(**kwargs)

    def add_row(self, values, index=None):
        """ add a new row """
        for i in self.frame.values():
            i.destroy()
        self.frame = {}
        if index is None:
            index = len(self.values)
        self.values.insert(index, values)
        self.rows = len(self.values)
        self.columns = len(self.values[0])
        self.draw_table()

    def add_column(self, values, index=None):
        """ add a new column """
        for i in self.frame.values():
            i.destroy()
        self.frame = {}
        if index is None:
            index = len(self.values[0])
        x = 0
        for i in self.values:
            i.insert(index, values[x])
            x += 1
        self.rows = len(self.values)
        self.columns = len(self.values[0])
        self.draw_table()

    def delete_row(self, index=None):
        """ delete a particular row """
        if index is None or index > len(self.values):
            index = len(self.values) - 1
        self.values.pop(index)
        for i in self.frame.values():
            i.destroy()
        self.rows = len(self.values)
        self.frame = {}
        self.draw_table()

    def delete_column(self, index=None):
        """ delete a particular column """
        if index is None or index > len(self.values[0]):
            index = len(self.values) - 1
        for i in self.values:
            i.pop(index)
        for i in self.frame.values():
            i.destroy()
        self.columns = len(self.values[0])
        self.frame = {}
        self.draw_table()

    def insert(self, row, column, value, **kwargs):
        """ insert value in a specific block [row, column] """
        self.frame[row, column].configure(text=value, **kwargs)

    def delete(self, row, column, **kwargs):
        """ delete a value from a specific block [row, column] """
        self.frame[row, column].configure(text="", **kwargs)

    def get(self):
        return self.values

    def configure(self, **kwargs):
        """ configure table widget attributes"""

        if "colors" in kwargs:
            self.colors = kwargs.pop("colors")
            self.fg_color = self.colors[0]
            self.fg_color2 = self.colors[1]
        if "header_color" in kwargs:
            self.header_color = kwargs.pop("header_color")
        if "rows" in kwargs:
            self.rows = kwargs.pop("rows")
        if "columns" in kwargs:
            self.columns = kwargs.pop("columns")
        if "values" in kwargs:
            self.values = values
        if "padx" in kwargs:
            self.padx = kwargs.pop("padx")
        if "padx" in kwargs:
            self.pady = kwargs.pop("pady")

        self.update_values(self.values, **kwargs)
