import sys
import os
import pathlib
import json
from typing import List, Union

class ThemeManager:
    theme: dict = {}  # contains all the theme data
    _built_in_themes: List[str] = ["blue", "green", "dark-blue", "sweetkind"]
    _currently_loaded_theme: Union[str, None] = None

    @classmethod
    def load_theme(cls, theme_name_or_path: str):
        script_directory = os.path.dirname(os.path.abspath(__file__))

        # Distinguish between built-in themes and custom themes
        if theme_name_or_path in cls._built_in_themes:
            customtkinter_path = pathlib.Path(script_directory).parent.parent.parent
            theme_path = os.path.join(customtkinter_path, "assets", "themes", f"{theme_name_or_path}.json")
        else:
            theme_path = theme_name_or_path

        with open(theme_path, "r") as f:
            cls.theme = json.load(f)

        cls._currently_loaded_theme = theme_name_or_path

        # Apply platform-specific overrides
        for key in list(cls.theme.keys()):
            if isinstance(cls.theme[key], dict) and \
               "macOS" in cls.theme[key] and \
               "Windows" in cls.theme[key] and \
               "Linux" in cls.theme[key]:
                if sys.platform == "darwin":
                    cls.theme[key] = cls.theme[key]["macOS"]
                elif sys.platform.startswith("win"):
                    cls.theme[key] = cls.theme[key]["Windows"]
                else:
                    cls.theme[key] = cls.theme[key]["Linux"]

        # Handle naming inconsistencies
        if "CTkCheckbox" in cls.theme:
            cls.theme["CTkCheckBox"] = cls.theme.pop("CTkCheckbox")
        if "CTkRadiobutton" in cls.theme:
            cls.theme["CTkRadioButton"] = cls.theme.pop("CTkRadiobutton")

    @classmethod
    def save_theme(cls):
        if cls._currently_loaded_theme is not None:
            # Prevent modification of built-in themes
            if cls._currently_loaded_theme not in cls._built_in_themes:
                with open(cls._currently_loaded_theme, "w") as f:
                    json.dump(cls.theme, f, indent=2)
            else:
                raise ValueError(f"cannot modify builtin theme '{cls._currently_loaded_theme}'")
        else:
            raise ValueError("cannot save theme, no theme is loaded")
