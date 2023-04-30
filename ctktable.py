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
        self.fg_color = self._apply_appearance_mode(customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"])
        self.fg_color2 = self._apply_appearance_mode(customtkinter.ThemeManager.theme["CTkFrame"]["top_fg_color"])
        self._text_color = self._apply_appearance_mode(customtkinter.ThemeManager.theme["CTkLabel"]["text_color"])

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

    def edit_rows(self, row, **kwargs):
        """ edit all parameters of a single row """
        for i in range(self.columns):
            self.frame[row, i].configure(**kwargs)

    def edit_columns(self, column, **kwargs):
        """ edit all parameters of a single column """
        for i in range(self.rows):
            self.frame[i, column].configure(**kwargs)

    def insert(self, row, column, value, **kwargs):
        """ insert value in the [row, colum] """
        self.frame[row, column].configure(text=value, **kwargs)