import ctypes
import json
import logging
import os
import re
import shutil
import socket
import sqlite3
import tempfile
import webbrowser
import aiohttp
import asyncio
import customtkinter
from datetime import datetime, timedelta
import psutil
import py7zr
import pytesseract
import pyzipper
import requests
from contextlib import closing
import uuid
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from pathlib import Path
import pygetwindow as gw
import tkinter as tk
import winsound
from CTkMessagebox import CTkMessagebox
from ctypes import wintypes
from tkinter import filedialog
from UserInterface import Sidebar
from UserInterface import MainWindow
from UserInterface import TopLevelWindows


class Network(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.disable_feedback = None
        self.GITHUB_REPO = "https://api.github.com/repos/Hanuwa/TeraTermUI"
        self.USER_APP_VERSION = "0.9.0"
        self.SERVICE_ACCOUNT_FILE = "feedback.zip"
        self.SPREADSHEET_ID = "1ffJLgp8p-goOlxC10OFEu0JefBgQDsgEo_suis4k0Pw"
        self.SPREADSHEET_BANNED_ID = "1JGDSyB-tE7gH5ozZ1MBlr9uMGcAWRgN7CyqK-QDQRxg"
        self.RANGE_NAME = "Sheet1!A:A"
        os.environ["Feedback"] = "F_QL^B#O_/r9|Rl0i=x),;!@en|V5qR%W(9;2^+f=lRPcw!+4"
        self.FEEDBACK = os.getenv("Feedback")
        self.db_operations = DatabaseOperations("database.db")
        self.credentials = None
        self.user_id = None
        self.connection_error = None
        self.os = OsOperations()
        self.top_level = TopLevelWindows()

    @staticmethod
    async def fetch(session, url):
        try:
            async with session.get(url, timeout=3.0) as response:
                if response.status != 200:
                    print(f"Non-200 response code: {response.status}")
                    return False
                return True
        except aiohttp.ClientConnectionError:
            print(f"Failed to connect to {url}")
            return False
        except aiohttp.ClientTimeout:
            print(f"Request to {url} timed out")
            return False
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False

    async def test_connection(self, lang):
        translation = self.os.load_language(lang)
        urls = ["http://www.google.com/", "http://www.bing.com/", "http://www.yahoo.com/"]
        async with aiohttp.ClientSession() as session:
            tasks = [Network.fetch(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
        connected = any(results)
        if not connected:
            self.after(0, self.top_level.show_error_message, 300, 215,
                       translation["Error! Not Connected to the internet"])
        return connected

    def check_server_status(self, lang):
        HOST = "uprbay.uprb.edu"
        PORT = 22
        timeout = 3
        translation = self.os.load_language(lang)
        try:
            with socket.create_connection((HOST, PORT), timeout=timeout):
                # the connection attempt succeeded
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            # the connection attempt failed
            self.after(0, self.top_level.show_error_message, 300, 215, translation["uprb_down"])
            return False

    def call_sheets_api(self, values, lang):
        if asyncio.run(self.test_connection(lang)):
            self.connection_error = False
            try:
                service = build("sheets", "v4", credentials=self.credentials)
            except:
                DISCOVERY_SERVICE_URL = "https://sheets.googleapis.com/$discovery/rest?version=v4"
                service = build("sheets", "v4", credentials=self.credentials, discoveryServiceUrl=DISCOVERY_SERVICE_URL)
            now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
            body = {
                "values": [[now, self.user_id, values[0][0]]]
            }

            try:
                result = service.spreadsheets().values().append(
                    spreadsheetId=self.SPREADSHEET_ID, range=self.RANGE_NAME,
                    valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                    body=body).execute()
                return result
            except HttpError as error:
                print(f"An error occurred: {error}")
                return None
        else:
            self.connection_error = True

    def is_user_banned(self, user_id, lang):
        if asyncio.run(self.test_connection(lang)):
            self.connection_error = False
            try:
                service = build("sheets", "v4", credentials=self.credentials)
            except:
                DISCOVERY_SERVICE_URL = "https://sheets.googleapis.com/$discovery/rest?version=v4"
                service = build("sheets", "v4", credentials=self.credentials, discoveryServiceUrl=DISCOVERY_SERVICE_URL)
            try:
                # Get all values in column A from the banned users spreadsheet
                result = service.spreadsheets().values().get(
                    spreadsheetId=self.SPREADSHEET_BANNED_ID, range=self.RANGE_NAME).execute()
                values = result.get("values", [])
                # Check if the user_id is in the values
                flat_values = [item for sublist in values for item in sublist]
                if user_id in flat_values:
                    return True
                else:
                    return False
            except HttpError as error:
                print(f"An error occurred: {error}")
                return False
        else:
            self.connection_error = True

    # Gets the latest release of the application on GitHub
    def get_latest_release(self, lang):
        if asyncio.run(self.test_connection(lang)):
            url = f"{self.GITHUB_REPO}/releases/latest"
            self.connection_error = False
            try:
                response = requests.get(url)

                if response.status_code != 200:
                    print(f"Error fetching release information: {response.status_code}")
                    return None

                release_data = response.json()
                latest_version = release_data.get("tag_name")

                if latest_version and latest_version.startswith("v"):
                    latest_version = latest_version[1:]

                return latest_version

            except requests.exceptions.RequestException as e:
                print(f"Request failed: {e}")
                return None
            except Exception as e:
                print(f"An error occurred while fetching the latest release: {e}")
                return None
        else:
            self.connection_error = True

    @staticmethod
    def compare_versions(latest_version, user_version):
        latest_version_parts = [int(part) for part in latest_version.split(".")]
        user_version_parts = [int(part) for part in user_version.split(".")]

        for latest, user in zip(latest_version_parts, user_version_parts):
            if latest > user:
                return False
            elif latest < user:
                return True
        return len(latest_version_parts) <= len(user_version_parts)

    def read_feedback_file(self):
        # Reads from the feedback.json file to connect to Google's Sheets Api for user feedback
        try:
            with open(self.SERVICE_ACCOUNT_FILE, "rb"):
                archive = pyzipper.AESZipFile(self.SERVICE_ACCOUNT_FILE)
                archive.setpassword(self.FEEDBACK.encode())
                file_contents = archive.read("feedback.json")
                credentials_dict = json.loads(file_contents.decode())
                self.credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
        except Exception as e:
            print(f"Failed to load credentials: {str(e)}")
            self.credentials = None
            self.disable_feedback = True

    # Asks the user if they want to update to the latest version of the application
    def update_app(self, lang):
        msg = None
        current_date = datetime.today().strftime("%Y-%m-%d")
        date = self.db_operations.fetch_data("SELECT date FROM user_data")
        welcome = self.db_operations.fetch_data("SELECT welcome FROM user_data")
        dates_list = [record[0] for record in date]
        if current_date not in dates_list:
            try:
                latest_version = self.get_latest_release(lang)
                if not Network.compare_versions(latest_version, self.USER_APP_VERSION) and welcome:
                    winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
                    if lang == "English":
                        msg = CTkMessagebox(master=self, title="Update",
                                            message="A newer version of the application is available,\n\n"
                                                    "would you like to update?",
                                            icon="question",
                                            option_1="Cancel", option_2="No", option_3="Yes",
                                            icon_size=(65, 65),
                                            button_color=("#c30101", "#145DA0", "#145DA0"),
                                            hover_color=("darkred", "darkblue", "darkblue"))
                    elif lang == "Español":
                        msg = CTkMessagebox(master=self, title="Actualización",
                                            message="Una nueva de versión de la aplicación esta disponible,\n\n "
                                                    "¿desea actualizar?",
                                            icon="question",
                                            option_1="Cancelar", option_2="No", option_3="Sí",
                                            icon_size=(65, 65),
                                            button_color=("#c30101", "#145DA0", "#145DA0"),
                                            hover_color=("darkred", "darkblue", "darkblue"))
                    response = msg.get()
                    if response[0] == "Yes" or response[0] == "Sí":
                        webbrowser.open("https://github.com/Hanuwa/TeraTermUI/releases/latest")
                    resultDate = self.db_operations.fetch_data("SELECT date FROM user_data")
                    if len(resultDate) == 0:
                        self.db_operations.fetch_data("INSERT INTO user_data (date) VALUES (?)", (current_date,))
                    elif len(resultDate) == 1:
                        self.db_operations.fetch_data("UPDATE user_data SET date=?", (current_date,))
                    self.db_operations.commit()
            except requests.exceptions.RequestException as err:
                print(f"Error occurred while fetching latest release information: {err}")
                print("Please check your internet connection and try again.")

    # opens GitHub page
    @staticmethod
    def open_github_event():
        webbrowser.open("https://github.com/Hanuwa/TeraTermUI")

    @staticmethod
    def open_notaso_event():
        webbrowser.open("https://notaso.com")

    # opens UPRB main page
    @staticmethod
    def open_uprb_event():
        webbrowser.open("https://www.uprb.edu")

    # opens a web page containing information about security information
    @staticmethod
    def open_lock_event():
        webbrowser.open("https://www.techtarget.com/searchsecurity/definition/Advanced-Encryption-Standard")

    # link to download tera term
    def download_teraterm(self, lang):
        msg = None
        winsound.PlaySound("sounds/notification.wav", winsound.SND_ASYNC)
        if lang == "English":
            msg = CTkMessagebox(master=self, title="Download",
                                message="Tera Term must be installed in your computer in order to use this application"
                                        " do you wish to download it?",
                                icon="question",
                                option_1="Cancel", option_2="No", option_3="Yes", icon_size=(65, 65),
                                button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
        elif lang == "Español":
            msg = CTkMessagebox(master=self, title="Download",
                                message="Tera Term tiene que estar instalado en su computadora para poder usar esta"
                                        " aplicación, ¿desea instalarlo?",
                                icon="question",
                                option_1="Cancelar", option_2="No", option_3="Sí", icon_size=(65, 65),
                                button_color=("#c30101", "#145DA0", "#145DA0"),
                                hover_color=("darkred", "darkblue", "darkblue"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            webbrowser.open("https://osdn.net/projects/ttssh2/releases/")

    @staticmethod
    def curriculums(choice):
        links = {
            "Departments": "https://www.uprb.edu/sample-page/decanato-de-asuntos-academicos/departamentos-academicos-2/",
            "Departamentos": "https://www.uprb.edu/sample-page/decanato-de-asuntos-academicos/departamentos"
                             "-academicos-2/",
            "Accounting": "https://drive.google.com/file/d/0BzdErxfu_JSCSDA0NHMyYVNhdXA3V1ZqX2c1aUlIT21Oc1RF/view"
                          "?resourcekey=0-S2WGur2snYQ0UVIHABbdKg",
            "Contabilidad": "https://drive.google.com/file/d/0BzdErxfu_JSCSDA0NHMyYVNhdXA3V1ZqX2c1aUlIT21Oc1RF/view"
                            "?resourcekey=0-S2WGur2snYQ0UVIHABbdKg",
            "Finance": "https://drive.google.com/file/d/0BzdErxfu_JSCR2gyNzJOeHA2c2EwTklRYmZYZ0Zfck9UT3E0/view"
                       "?resourcekey=0-jizC_JvFrbYxmb9ZScl8RA",
            "Finanzas": "https://drive.google.com/file/d/0BzdErxfu_JSCR2gyNzJOeHA2c2EwTklRYmZYZ0Zfck9UT3E0/view"
                        "?resourcekey=0-jizC_JvFrbYxmb9ZScl8RA",
            "Management": "https://drive.google.com/file/d/0BzdErxfu_JSCVllhTWJGMzRYd3JoemtObDkzX3I5MHNqU3V3/view"
                          "?resourcekey=0-368G697L5iz5EjZ_DCngHQ",
            "Gerencia": "https://drive.google.com/file/d/0BzdErxfu_JSCVllhTWJGMzRYd3JoemtObDkzX3I5MHNqU3V3/view"
                        "?resourcekey=0-368G697L5iz5EjZ_DCngHQ",
            "Marketing": "https://drive.google.com/file/d/0BzdErxfu_JSCa3BIWnZyQmlHa0hGcEVtSlV2d2gxN0dENVcw/view"
                         "?resourcekey=0-hve5FwLHcBdt0K6Je5hMSg",
            "Mercadeo": "https://drive.google.com/file/d/0BzdErxfu_JSCa3BIWnZyQmlHa0hGcEVtSlV2d2gxN0dENVcw/view"
                        "?resourcekey=0-hve5FwLHcBdt0K6Je5hMSg",
            "General Biology": "https://drive.google.com/file/d/11yfoYqXYPybDZmeEmgW8osgSCCmxzjQl/view",
            "Biología General": "https://drive.google.com/file/d/11yfoYqXYPybDZmeEmgW8osgSCCmxzjQl/view",
            "Biology-Human Focus": "https://drive.google.com/file/d/1z-aphTwLLwAY5-G3O7_SXG3ZvvRSN6p9/view",
            "Biología-Enfoque Humano": "https://drive.google.com/file/d/1z-aphTwLLwAY5-G3O7_SXG3ZvvRSN6p9/view",
            "Computer Science": "https://docs.uprb.edu/deptsici/CIENCIAS-DE-COMPUTADORAS-2016.pdf",
            "Ciencias de Computadoras": "https://docs.uprb.edu/deptsici/CIENCIAS-DE-COMPUTADORAS-2016.pdf",
            "Information Systems": "https://docs.uprb.edu/deptsici/SISTEMAS-INFORMACION-2016.pdf",
            "Sistemas de Información": "https://docs.uprb.edu/deptsici/SISTEMAS-INFORMACION-2016.pdf",
            "Social Sciences": "https://drive.google.com/file/d/1cZnD6EhBsu7u6U8IVZoeK0VHgQmYt3sf/view",
            "Ciencias Sociales": "https://drive.google.com/file/d/1cZnD6EhBsu7u6U8IVZoeK0VHgQmYt3sf/view",
            "Physical Education": "https://drive.google.com/file/d/0BzdErxfu_JSCQWFEWlpCSnRFMVFGQnZoTXRyZHJiMzBkc2dZ"
                                  "/view?resourcekey=0-zLsz0IP1Ajy853kM9I2PQg",
            "Educación Física": "https://drive.google.com/file/d/0BzdErxfu_JSCQWFEWlpCSnRFMVFGQnZoTXRyZHJiMzBkc2dZ/view"
                                "?resourcekey=0-zLsz0IP1Ajy853kM9I2PQg",
            "Electronics": "https://drive.google.com/file/d/1tfzaHKilu5iQccD2sBzD8O_6UlXtSREF/view",
            "Electrónica": "https://drive.google.com/file/d/1tfzaHKilu5iQccD2sBzD8O_6UlXtSREF/view",
            "Equipment Management": "https://drive.google.com/file/d/13ohtab5ns6qO2QIHouScKtrFHrM7X3zl/view",
            "Gerencia de Materiales": "https://drive.google.com/file/d/13ohtab5ns6qO2QIHouScKtrFHrM7X3zl/view",
            "Pedagogy": "https://www.upr.edu/bayamon/wp-content/uploads/sites/9/2015/06/Secuencia-curricular-aprobada"
                        "-en-mayo-de-2013.pdf",
            "Pedagogía": "https://www.upr.edu/bayamon/wp-content/uploads/sites/9/2015/06/Secuencia-curricular"
                         "-aprobada-en-mayo-de-2013.pdf",
            "Chemistry": "https://drive.google.com/file/d/0BzdErxfu_JSCNHJENWNaY1JmZjNSSU5mR2U5SnVOc1gxUTVJ/view"
                         "?resourcekey=0-CWkQQfEczPuV0Rx4KQnkBA",
            "Química": "https://drive.google.com/file/d/0BzdErxfu_JSCNHJENWNaY1JmZjNSSU5mR2U5SnVOc1gxUTVJ/view"
                       "?resourcekey=0-CWkQQfEczPuV0Rx4KQnkBA",
            "Nursing": "https://drive.google.com/file/d/0BzdErxfu_JSCaF9tMFc3Y0hnRGpsZ1dMTXFPRjRMUlVEQ1ZZ/view"
                       "?resourcekey=0-JQUivKyxJQlXP-2K008d_Q",
            "Enfermería": "https://drive.google.com/file/d/0BzdErxfu_JSCaF9tMFc3Y0hnRGpsZ1dMTXFPRjRMUlVEQ1ZZ/view"
                          "?resourcekey=0-JQUivKyxJQlXP-2K008d_Q",
            "Office Systems": "https://docs.uprb.edu/deptsofi/curriculo-BA-SOFI-agosto-2016.pdf",
            "Sistemas de Oficina": "https://docs.uprb.edu/deptsofi/curriculo-BA-SOFI-agosto-2016.pdf",
            "Information Engineering": "https://drive.google.com/file/d/1mYCHmCy3Mb2fDyp9EiFEtR0j4-rsDdlN/view",
            "Ingeniería de la Información": "https://drive.google.com/file/d/1mYCHmCy3Mb2fDyp9EiFEtR0j4-rsDdlN/view"}

        url = links.get(choice, None)
        if url:
            webbrowser.open(url)


class OsOperations:
    def __init__(self):
        self.network = Network()
        self.network.disable_feedback = None
        os.environ["Feedback"] = "F_QL^B#O_/r9|Rl0i=x),;!@en|V5qR%W(9;2^+f=lRPcw!+4"
        self.FEEDBACK = os.getenv("Feedback")
        self.user_id = None
        self.tesseract_unzipped = None
        self.original_font = None
        # path for tesseract application
        self.zip_path = os.path.join(os.path.dirname(__file__), "Tesseract-OCR.7z")
        self.app_temp_dir = Path(tempfile.gettempdir()) / "TeraTermUI"
        self.app_temp_dir.mkdir(parents=True, exist_ok=True)

    # checks if the specified window exists
    @staticmethod
    def window_exists(title):
        try:
            window = gw.getWindowsWithTitle(title)[0]
            return True
        except IndexError:
            return False

    # function that checks if Tera Term is running or not
    @staticmethod
    def checkIfProcessRunning(processName):
        for proc in psutil.process_iter():
            try:
                if processName.lower() in proc.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logging.error(f"Exception occurred: {e}")
                pass
        return False

    # checks whether the user has the requested file
    @staticmethod
    def is_file_in_directory(file_name, directory):
        # Join the directory path and file name
        full_path = os.path.join(directory, file_name)
        # Check if the file exists
        return os.path.isfile(full_path)

    # Edits the font that tera term uses to "Terminal" to mitigate the chance of the OCR mistaking words
    def edit_teraterm_config(self, file_path):
        if OsOperations.is_file_in_directory("ttermpro.exe", r"C:/Program Files (x86)/teraterm"):
            backup_path = self.app_temp_dir / "TERATERM.ini.bak"
            if not os.path.exists(backup_path):
                backup_path = os.path.join(self.app_temp_dir, os.path.basename(file_path) + ".bak")
                try:
                    shutil.copyfile(file_path, backup_path)
                except FileNotFoundError:
                    print("Tera Term Probably not installed\n"
                          "or installed in a different location from the default")
            try:
                with open(file_path, "r") as file:
                    lines = file.readlines()
            except FileNotFoundError:
                return
            try:
                with open(file_path, "w") as file:
                    for line in lines:
                        if line.startswith("VTFont="):
                            current_value = line.strip().split("=")[1]
                            font_name = current_value.split(",")[0]
                            self.original_font = current_value
                            updated_value = "Lucida Console" + current_value[len(font_name):]
                            line = f"VTFont={updated_value}\n"
                        file.write(line)
            # If something goes wrong, restore the backup
            except Exception as e:
                print(f"Error occurred: {e}")
                print("Restoring from backup...")
                shutil.copyfile(backup_path, file_path)

    # Restores the original font option the user had
    def restore_original_font(self, file_path):
        backup_path = self.app_temp_dir / "TERATERM.ini.bak"
        try:
            with open(file_path, "r") as file:
                lines = file.readlines()

            with open(file_path, "w") as file:
                for line in lines:
                    if line.startswith("VTFont="):
                        line = f"VTFont={self.original_font}\n"
                    file.write(line)

            with open(backup_path, "r") as backup_file:
                backup_lines = backup_file.readlines()

            backup_font = None
            backup_font_name = None
            for line in backup_lines:
                if line.startswith("VTFont="):
                    backup_font = line.strip().split("=")[1]
                    backup_font_name = backup_font.split(",")[0]
                    break
            if backup_font_name and self.original_font.split(",")[0]:
                if backup_font_name.lower() != self.original_font.split(",")[0].lower():
                    with open(file_path, "w") as file:
                        for line in lines:
                            if line.startswith("VTFont="):
                                line = f"VTFont={backup_font}\n"
                            file.write(line)
        # If something goes wrong, restore the backup
        except FileNotFoundError:
            print(f"Backup file at {backup_path} not found.")
        except Exception as e:
            print(f"Error occurred: {e}")
            print("Restoring from backup...")
            try:
                shutil.copyfile(backup_path, file_path)
            except FileNotFoundError:
                print(f"The backup file at {backup_path} was not found.")

    # Unzips Teserract OCR
    def unzip_tesseract(self):
        try:
            with py7zr.SevenZipFile(self.zip_path, mode="r") as z:
                z.extractall(self.app_temp_dir)
            tesseract_dir = Path(self.app_temp_dir) / "Tesseract-OCR"
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_dir / "tesseract.exe")
            # tessdata_dir_config = f"--tessdata-dir {tesseract_dir / 'tessdata'}"
            self.tesseract_unzipped = True
        except Exception as e:
            print(f"Error occurred during unzipping: {str(e)}")
            self.tesseract_unzipped = False

    # Generating user_id to ban user from sending feedback if needed
    # If the file doesn't already exist, generate a new UUID and write it to the file
    def generate_user_id(self):
        user_path = Path(self.app_temp_dir) / "user_id.zip"
        if not user_path.is_file():
            user_id = str(uuid.uuid4())
            # Create a new password-protected zip archive and add the text file to it
            with pyzipper.AESZipFile(user_path, "w", encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(self.FEEDBACK.encode())
                zf.writestr("user_id.txt", user_id)
        # Read the user_id from the text file in the password-protected zip archive
        try:
            with pyzipper.AESZipFile(user_path, "r") as zf:
                zf.setpassword(self.FEEDBACK.encode())
                with zf.open("user_id.txt") as f:
                    self.user_id = f.read().decode().strip()
        except Exception as e:
            print(f"Failed to read user_id: {str(e)}")
            self.network.disable_feedback = True

    # Cleanup any leftover files/directories if they exist in any directory under temp_dir
    def cleanup_tesseract(self):
        tesseract_dir_path = self.app_temp_dir / "Tesseract-OCR"
        if tesseract_dir_path.is_dir():
            shutil.rmtree(tesseract_dir_path)

    @staticmethod
    def load_language(lang):
        if lang == "English":
            with open("english.json", "r", encoding='utf-8') as f:
                translations = json.load(f)
            return translations
        elif lang == "Español":
            with open("spanish.json", "r", encoding='utf-8') as f:
                translations = json.load(f)
            return translations


class DatabaseOperations:
    def __init__(self, db_path):
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.os = OsOperations()
        self.main_window = MainWindow()
        self.sidebar = Sidebar()
        self.top_level = TopLevelWindows()

    def query(self, query):
        return self.cursor.execute(query)

    def fetch_data(self, query, *args):
        return self.cursor.execute(query, args).fetchone()

    def commit(self):
        return self.connection.commit()

    # saves class information for another session
    def save_classes(self, save, lang, add, classes, sections, semesters, menu):
        if save == "on":
            # Clear existing data from the table
            translation = self.os.load_language(lang)
            self.fetch_data("DELETE FROM save_classes")
            self.commit()
            is_empty = False
            is_invalid_format = False
            # Iterate over the added entries based on self.a_counter
            for index in range(add + 1):
                class_value = classes[index].get()
                section_value = sections[index].get()
                semester_value = semesters[index].get()
                register_value = menu[index].get()
                if not class_value or not section_value or not semester_value or register_value in ("Choose", "Escoge"):
                    is_empty = True
                elif (not re.fullmatch("^[A-Z]{4}[0-9]{4}$", class_value, flags=re.IGNORECASE) or
                      not re.fullmatch("^[A-Z]{2}1$", section_value, flags=re.IGNORECASE) or
                      not re.fullmatch("^[A-Z][0-9]{2}$", semester_value, flags=re.IGNORECASE)):
                    is_invalid_format = True
                else:
                    # Perform the insert operation
                    self.fetch_data("INSERT INTO save_classes (class, section, semester, action,"
                                    " 'check') VALUES (?, ?, ?, ?, ?)",
                                    (class_value, section_value, semester_value, register_value, "Yes"))
                    self.commit()
            if is_empty:
                self.top_level.show_error_message(330, 255, translation["failed_saved_lack_info"])
                save.deselect()

            if is_invalid_format:
                self.top_level.show_error_message(330, 255, translation["failed_saved_invalid_info"])
                save.deselect()
            else:
                self.query("SELECT COUNT(*) FROM save_classes")
                row_count = self.cursor.fetchone()[0]
                if row_count == 0:  # Check the counter after the loop
                    self.top_level.show_error_message(330, 255, translation["failed_saved_invalid_info"])
                    save.deselect()
                else:
                    self.top_level.show_error_message(350, 265, translation["saved_classes_success"])
        if save == "off":
            self.fetch_data("DELETE FROM save_classes")
            self.commit()

    # saves the information to the database when the app closes
    def save_user_data(self, lang, appearance, scaling, choice, host):
        field_values = {
            "welcome": "Checked",
            "host": "uprbay.uprb.edu",
            "language": lang,
            "appearance": appearance,
            "scaling": scaling,
            "exit": choice,
        }
        for field, value in field_values.items():
            if field == "host" and (host.get().replace(" ", "").lower() != "uprbay.uprb.edu" and
                                    host.get().replace(" ", "").lower() != "uprbayuprbedu"):
                continue
            result = self.cursor.execute(f"SELECT {field} FROM user_data").fetchone()
            if result is None:
                self.cursor.execute(f"INSERT INTO user_data ({field}) VALUES (?)", (value,))
            elif result[0] != value:
                self.cursor.execute(f"UPDATE user_data SET {field} = ? ", (value,))
        with closing(sqlite3.connect("database.db")) as connection:
            with closing(connection.cursor()) as self.cursor:
                self.commit()

    # Function that lets user select where their Tera Term application is located
    def set_teraterm_location(self, lang):
        translation = self.os.load_language(lang)
        filename = filedialog.askopenfilename(initialdir="C:/",
                                              title=translation["select_tera_term"],
                                              filetypes=(("Tera Term", "*ttermpro.exe"),))
        if re.search("ttermpro.exe", filename):
            self.main_window.teraterm_location = filename
            directory, filename = os.path.split(filename)
            self.main_window.teraterm_config_location = directory + "/TERATERM.ini"
            location = self.cursor.execute("SELECT location FROM user_data").fetchall()
            teraterm_config = self.cursor.execute("SELECT config FROM user_data").fetchall()
            if len(location) == 0:
                self.cursor.execute("INSERT INTO user_data (location) VALUES (?)",
                                    (self.main_window.teraterm_location,))
            elif len(location) == 1:
                self.cursor.execute("UPDATE user_data SET location=?",
                                    (self.main_window.teraterm_location,))
            if len(teraterm_config) == 0:
                self.cursor.execute("INSERT INTO user_data (config) VALUES (?)",
                                    (self.main_window.teraterm_config_location,))
            elif len(teraterm_config) == 1:
                self.cursor.execute("UPDATE user_data SET config=?", (self.main_window.teraterm_config_location,))
            self.cursor.connection.commit()
            self.top_level.show_success_message(350, 265, translation["tera_term_success"], lang)
            self.os.edit_teraterm_config(self.main_window.teraterm_config_location)
        self.sidebar.help.lift()

    # list of classes available for all departments in the university
    def search_classes(self, event, lang):
        translation = self.os.load_language(lang)
        self.sidebar.class_list.delete(0, tk.END)  # always clear the list box first
        search_term = self.sidebar.search_box.get().strip().lower()
        if search_term == "" or len(search_term) == 0:  # if the search term is empty, do not return any records
            return
        if search_term in ["all", "todo", "todos"]:
            query = "SELECT name, code FROM courses"
        else:
            query_conditions = [f"LOWER(name) LIKE '%{search_term}%'", f"LOWER(code) LIKE '%{search_term}%'"]
            query_conditions_str = " OR ".join(query_conditions)
            query = f"SELECT name, code FROM courses WHERE {query_conditions_str}"

        results = self.cursor.execute(query).fetchall()
        if not results:  # if there are no results, display a message
            self.sidebar.class_list.delete(0, tk.END)
            self.sidebar.class_list.insert(tk.END, translation["no_results"])
        else:
            for row in results:
                self.sidebar.class_list.insert(tk.END, row[0])

    # query for searching for either class code or name
    def show_class_code(self, event, lang):
        translation = self.os.load_language(lang)
        selection = self.sidebar.class_list.curselection()
        if len(selection) == 0:
            return
        selected_class = self.sidebar.class_list.get(self.sidebar.class_list.curselection())
        query = "SELECT code FROM courses WHERE name = ? OR code = ?"
        result = self.cursor.execute(query, (selected_class, selected_class)).fetchone()
        if result is None:
            self.sidebar.class_list.delete(0, tk.END)
            self.sidebar.class_list.insert(tk.END, translation["no_results"])
        else:
            self.sidebar.search_box.delete(0, tk.END)
            self.sidebar.search_box.insert(0, result[0])

    # Disables check_idle functionality
    def disable_enable_idle(self):
        if self.top_level.disableIdle.get() == "on":
            idle = self.cursor.execute("SELECT idle FROM user_data").fetchall()
            if len(idle) == 0:
                self.cursor.execute("INSERT INTO user_data (idle) VALUES (?)", ("Disabled",))
            elif len(idle) == 1:
                self.cursor.execute("UPDATE user_data SET idle=?", ("Disabled",))
            self.reset_activity_timer(None)
            self.stop_idle_thread()
        if self.top_level.disableIdle.get() == "off":
            idle = self.cursor.execute("SELECT idle FROM user_data").fetchall()
            if len(idle) == 0:
                self.cursor.execute("INSERT INTO user_data (idle) VALUES (?)", ("Enabled",))
            elif len(idle) == 1:
                self.cursor.execute("UPDATE user_data SET idle=?", ("Enabled",))
            if self.auto_enroll is not None:
                self.auto_enroll.configure(state="normal")
            if self.run_fix and self.os.checkIfProcessRunning("ttermpro"):
                self.hide_sidebar_windows()
                self.destroy_windows()
                ctypes.windll.user32.BlockInput(True)
                term_window = gw.getWindowsWithTitle("uprbay.uprb.edu - Tera Term VT")[0]
                if term_window.isMinimized:
                    term_window.restore()
                self.uprbay_window.wait("visible", timeout=30)
                self.uprb.UprbayTeraTermVt.type_keys("SRM")
                send_keys("{ENTER}")
                ctypes.windll.user32.BlockInput(False)
                self.reset_activity_timer(None)
                self.start_check_idle_thread()
                self.show_sidebar_windows()
        self.connection.commit()


DWMWA_EXTENDED_FRAME_BOUNDS = 9


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG)]


def get_window_rect(hwnd):
    rect = RECT()
    DwmGetWindowAttribute = ctypes.windll.dwmapi.DwmGetWindowAttribute
    DwmGetWindowAttribute.restype = wintypes.LONG
    DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.POINTER(RECT), wintypes.DWORD]
    DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect))
    return rect.left, rect.top, rect.right, rect.bottom
