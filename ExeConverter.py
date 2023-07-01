import subprocess
import sqlite3
import shutil
import os
import sys
from colorama import init, Fore, Style

project_directory = r"C:\Users\arman\PycharmProjects\TeraTermUI\TeraTermUI.py"
nuitka_command = (
    r'cd /d C:\Users\arman\PycharmProjects\TeraTermUI\venv\Scripts & python -m nuitka --standalone '
    r'--experimental=treefree C:\Users\arman\PycharmProjects\TeraTermUI\TeraTermUI.py '
    r'--enable-plugin=tk-inter --include-data-dir=C:\Users\arman\PycharmProjects\TeraTermUI\venv\Lib\site-packages'
    r'\customtkinter=customtkinter --include-data-dir=C:\Users\arman\PycharmProjects\TeraTermUI\venv\Lib\site-packages'
    r'\CTkMessageBox=CTkMessageBox --include-package=CTkToolTip '
    r'--include-data-dir=C:\Users\arman\PycharmProjects\TeraTermUI\images=images '
    r'--include-data-dir=C:\Users\arman\PycharmProjects\TeraTermUI\sounds=sounds '
    r'--include-data-file=C:\Users\arman\PycharmProjects\TeraTermUI\database.db=database.db '
    r'--include-data-file=C:\Users\arman\PycharmProjects\TeraTermUI\Tesseract-OCR.7z=Tesseract-OCR.7z '
    r'--include-data-file=C:\Users\arman\PycharmProjects\TeraTermUI\feedback.zip=feedback.zip '
    r'--include-data-file=C:\Users\arman\PycharmProjects\TeraTermUI\VERSION.txt=VERSION.txt '
    r'--include-data-file=C:\Users\arman\PycharmProjects\TeraTermUI\LICENSE.txt=LICENSE.txt '
    r'--output-dir=C:\Users\arman\OneDrive\Documentos\TeraTermUI_v0.9.0 --disable-console '
    r'--windows-icon-from-ico=C:\Users\arman\PycharmProjects\TeraTermUI\images\tera-term.ico '
    r'--include-package=spellchecker '
    r'--include-data-dir=C:\Users\arman\PycharmProjects\TeraTermUI\venv\Lib\site-packages\spellchecker=spellchecker'
)
output_directory = r"C:\Users\arman\OneDrive\Documentos\TeraTermUI_v0.9.0"
app_folder = "TeraTermUI"
upx_command = r"upx --best " + output_directory + r"\TeraTermUI.dist\TeraTermUI.exe"
inno_directory = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
versions = ['installer', 'portable']
init()

connection = sqlite3.connect(r"C:\Users\arman\PycharmProjects\TeraTermUI\database.db")
cursor = connection.cursor()
# Execute the DELETE SQL command
cursor.execute("DELETE FROM user_data")
connection.commit()

for version in versions:
    script = None
    try:
        with open(project_directory, 'r', encoding='utf-8') as file:
            data = file.read()
        # Replace old text with new text for portable and installer versions
        if version == 'installer':
            script = "installer"
            data = data.replace('self.connection = sqlite3.connect("database.db")',
                                'self.connection = sqlite3.connect(self.db_path)')
            data = data.replace('closing(sqlite3.connect("database.db")) as connection',
                                'closing(sqlite3.connect(self.db_path)) as connection')
            data = data.replace('with open(self.SERVICE_ACCOUNT_FILE, "rb") as f',
                                'with open(self.ath, "rb") as f')
            data = data.replace('archive = pyzipper.AESZipFile(self.SERVICE_ACCOUNT_FILE)',
                                'archive = pyzipper.AESZipFile(self.ath)')
            data = data.replace('FileLock(lock_file, timeout=10)',
                                'FileLock(lock_file_appdata, timeout=10)')
            print(Fore.GREEN + "Successfully started installer version" + Style.RESET_ALL)
        else:
            script = "portable"
            data = data.replace('self.connection = sqlite3.connect(self.db_path)',
                                'self.connection = sqlite3.connect("database.db")')
            data = data.replace('closing(sqlite3.connect(self.db_path)) as connection',
                                'closing(sqlite3.connect("database.db")) as connection')
            data = data.replace('with open(self.ath, "rb") as f',
                                'with open(self.SERVICE_ACCOUNT_FILE, "rb") as f')
            data = data.replace('archive = pyzipper.AESZipFile(self.ath)',
                                'archive = pyzipper.AESZipFile(self.SERVICE_ACCOUNT_FILE)')
            data = data.replace('FileLock(lock_file_appdata, timeout=10)',
                                'FileLock(lock_file, timeout=10)')
            print(Fore.GREEN + "Successfully started portable version" + Style.RESET_ALL)

        with open(project_directory, 'w', encoding='utf-8') as file:
            file.write(data)
    except Exception as e:
        print(Fore.RED + f"Error modifying script: {e}" + Style.RESET_ALL)
        sys.exit(1)

    try:
        subprocess.run(nuitka_command, shell=True, check=True)
        print(Fore.GREEN + "Successfully completed nuitka script" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Failed to create executable with Nuitka: {e}" + Style.RESET_ALL)
        sys.exit(1)

    try:
        subprocess.run(upx_command, shell=True, check=True)
        print(Fore.GREEN + "Successfully completed UPX script" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Failed to compress executable with UPX: {e}" + Style.RESET_ALL)
        sys.exit(1)

    if script == "installer":
        try:
            os.rename(output_directory + r"\TeraTermUI.dist",
                      output_directory + r"\TeraTermUI_installer")
            print(Fore.GREEN + "Successfully created TeraTermUI installer folder" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"Error renaming folder: {e}" + Style.RESET_ALL)
            sys.exit(1)

        try:
            subprocess.run([inno_directory, output_directory + r"\InstallerScript.iss"], check=True)
            print(Fore.GREEN + "Successfully compiled TeraTermUI installer" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"Error compiling Inno Setup script: {e}" + Style.RESET_ALL)
            sys.exit(1)

        try:
            shutil.move(output_directory + r"\output\TeraTermUI_64-bit_Installer-v0.9.0.exe", output_directory)
            shutil.rmtree(output_directory + r"\output")
            print(Fore.GREEN + "Successfully completed installer version" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"Error moving or removing folder: {e}" + Style.RESET_ALL)
            sys.exit(1)

    elif script == "portable":
        try:
            os.rename(output_directory + r"\TeraTermUI.dist", output_directory + r"\TeraTermUI")
            zip_file_path = output_directory + fr"\{app_folder}-v0.9.0.zip"
            shutil.make_archive(zip_file_path, 'zip', output_directory, app_folder)
            print(Fore.GREEN + "Successfully completed portable version" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"Error creating zip file: {e}" + Style.RESET_ALL)
            sys.exit(1)

print(Fore.GREEN + "Both versions (installer and portable) have been created successfully."
      + Style.RESET_ALL)
sys.exit(0)
