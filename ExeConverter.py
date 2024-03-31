import datetime
import re
import os
import signal
import shutil
import sqlite3
import subprocess
import sys
from colorama import init, Fore, Style


def extract_second_date_from_file(filepath):
    with open(filepath, "r") as f:
        for line in f:
            dates = re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", line)
            if len(dates) >= 2:
                return dates[1]
        return None


def extract_version_main_file(filepath):
    with open(filepath, "r") as f:
        for line in f:
            if "v" in line:
                positions = [pos for pos, char in enumerate(line) if char == "v"]
                for pos in positions:
                    if line[pos+1].isdigit():
                        start_pos = pos + 1
                        end_pos = line[start_pos:].find(" ")
                        return line[start_pos:start_pos+end_pos]
        return None


def check_and_restore_backup():
    if os.path.exists(program_backup):
        program_backup_date = extract_second_date_from_file(program_backup)
        tera_term_ui_date = extract_second_date_from_file(project_directory + r"\TeraTermUI.py")
        tera_term_ui_version = extract_version_main_file(project_directory + r"\TeraTermUI.py")
        if program_backup_date != tera_term_ui_date:
            print(Fore.YELLOW + "\nDate mismatch detected between the main file and the backup one. "
                                "\nRestoration from backup skipped. Delete backup file if no longer needed"
                  + Style.RESET_ALL)
        elif tera_term_ui_version != update_without_v:
            print(Fore.YELLOW + "\nVersion mismatch detected between the main file and the backup one. "
                                "\nRestoration from backup skipped. Delete backup file if no longer needed"
                  + Style.RESET_ALL)
        else:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            print(
                Fore.YELLOW + "\nPrevious session was interrupted. Restoration from backup completed." +
                Style.RESET_ALL)
            os.remove(program_backup)


def attach_manifest(executable_path, manifest_path):
    try:
        subprocess.run(f"mt.exe -manifest {manifest_path} -outputresource:{executable_path};1",  check=True)
    except KeyboardInterrupt as e:
        shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to attach manifest: {e}\n" + Style.RESET_ALL)
        sys.exit(1)
    except Exception as e:
        shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to attach manifest: {e}\n" + Style.RESET_ALL)


def terminate_process(signum, frame):
    shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + "Script execution was externally terminated.\n" + Style.RESET_ALL)
    sys.exit(-1)


def validate_version(ver_str: str) -> bool:
    pattern = r"^[vV]?([0-9]{1,3}\.[0-9]{1,3}(\.[0-9]{1,3})?|[0-9]{1,3})$"
    return bool(re.match(pattern, ver_str, re.IGNORECASE))


init()
username = os.getlogin()
project_directory = r"C:\Users\\" + username + r"\PycharmProjects\TeraTermUI"
inno_directory = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
app_folder = "TeraTermUI"
while True:
    user_input = input(Fore.BLUE + "Please enter the update version number"
                       " (e.g., v1.0.0 or 1.0.0): " + Style.RESET_ALL).replace(" ", "").strip()
    if validate_version(user_input):
        user_input_segments = user_input.lower().replace("v", "").split(".")
        if len(user_input_segments) == 2:
            user_input = f"{user_input_segments[0]}.{user_input_segments[1]}"
        elif len(user_input_segments) == 3:
            user_input = f"{user_input_segments[0]}.{user_input_segments[1]}.{user_input_segments[2]}"
        elif len(user_input) == 3 and user_input.isdigit():
            user_input = f"{user_input[0]}.{user_input[1]}.{user_input[2]}"
        elif len(user_input) == 2 and user_input.isdigit():
            user_input = f"{user_input[0]}.{user_input[1]}"
        break
    print(Fore.RED + "\nInvalid format. Please provide an update version number"
          " in the format x.x.x or vx.x.x (e.g., v1.0.0 or 1.0.0): \n" + Style.RESET_ALL)
user_input = user_input.lower()
if user_input.startswith("v"):
    update = user_input
    update_without_v = user_input[1:]
else:
    update_without_v = user_input
    update = "v" + update_without_v
versions = ["installer", "portable"]
output_directory = os.path.join(r"C:\Users\\" + username + r"\OneDrive\Documentos", "TeraTermUI_" + update)

program_backup = project_directory + r"\TeraTermUI.BAK.py"
check_and_restore_backup()
shutil.copy2(project_directory + r"\TeraTermUI.py", program_backup)
signal.signal(signal.SIGTERM, terminate_process)
signal.signal(signal.SIGINT, terminate_process)

current_date = datetime.datetime.now().strftime("%m/%d/%Y")
version_file_path = os.path.join(project_directory, "VERSION.txt")
with open(version_file_path, "r") as file:
    version_file_content = file.read()
version_file_content = re.sub(r"(?<=Version Number: ).*", update, version_file_content)
version_file_content = re.sub(r"(?<=Release Date: ).*", current_date, version_file_content)
with open(version_file_path, "w") as file:
    file.write(version_file_content)

try:
    if os.path.exists(output_directory):
        shutil.rmtree(output_directory)
    os.makedirs(output_directory, exist_ok=True)
    for filename in os.listdir(os.path.join(project_directory, "dist")):
        src = os.path.join(project_directory, "dist", filename)
        dst = os.path.join(output_directory, filename)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
    inno_file_path = os.path.join(output_directory, "InstallerScript.iss")
    with open(inno_file_path, "r") as file:
        lines = file.readlines()
    with open(inno_file_path, "w") as file:
        for line in lines:
            if line.startswith("#define MyAppVersion"):
                line = '#define MyAppVersion "' + update_without_v + '"\n'
            elif line.startswith("#define MyAppPath"):
                line = '#define MyAppPath "' + output_directory + '"\n'
            elif line.startswith("OutputBaseFilename="):
                line = 'OutputBaseFilename="TeraTermUI_64-bit_Installer-' + update + '"\n'
            file.write(line)
    print(Fore.GREEN + "\nSuccessfully created distribution directory\n" + Style.RESET_ALL)
except KeyboardInterrupt as e:
    shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + f"Error modifying creating distribution directory: {e}\n" + Style.RESET_ALL)
    sys.exit(1)
except Exception as e:
    shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + f"Error modifying creating distribution directory: {e}\n" + Style.RESET_ALL)

nuitka_command = (
    r'cd /d "' + project_directory + r'\.venv\Scripts" & python -m nuitka --standalone '
    r'--deployment "' + project_directory + r'\TeraTermUI.py" --disable-console '
    r'--enable-plugin=tk-inter --include-data-dir="' + project_directory + r'\.venv\Lib\site-packages'
    r'\customtkinter=customtkinter" --include-data-dir="' + project_directory + r'\.venv\Lib\site-packages'
    r'\CTkMessageBox=CTkMessageBox" --include-package=CTkToolTip --include-package=CTkTable '
    r'--include-data-dir="' + project_directory + r'\images=images" '
    r'--include-data-dir="' + project_directory + r'\slideshow=slideshow" '                                           
    r'--include-data-dir="' + project_directory + r'\sounds=sounds" '
    r'--include-data-dir="' + project_directory + r'\translations=translations" '
    r'--include-data-file="' + project_directory + r'\database.db=database.db" '
    r'--include-data-file="' + project_directory + r'\Tesseract-OCR.7z=Tesseract-OCR.7z" '
    r'--include-data-file="' + project_directory + r'\feedback.zip=feedback.zip" '
    r'--include-data-file="' + project_directory + r'\VERSION.txt=VERSION.txt" '
    r'--include-data-file="' + project_directory + r'\LICENSE.txt=LICENSE.txt" '   
    r'--include-data-file="' + project_directory + r'\updater.exe=updater.exe" '                                                
    r'--output-dir="' + output_directory + r'" --python-flag=no_asserts '
    r'--windows-icon-from-ico="' + project_directory + r'\images\tera-term.ico" '
    r'--nofollow-import-to=unittest --python-flag=no_docstrings --product-name="Tera Term UI" '
    r'--company-name="Armando Del Valle Tejada" --file-description="TeraTermUI" '  
    r'--file-version="' + update_without_v + r'" --product-version="' + update_without_v + r'" '
    r'--copyright="Copyright © 2024 Armando Del Valle Tejada" '
)
try:
    updater_exe_path = os.path.join(project_directory, "updater.exe")
    updater_dist_path = os.path.join(project_directory, "dist", "updater.exe")
    if not os.path.isfile(updater_exe_path) or not os.path.isfile(updater_dist_path):
        if os.path.isfile(updater_exe_path):
            shutil.copy2(updater_exe_path, updater_dist_path)
            shutil.copy2(updater_exe_path, output_directory)
            print(Fore.GREEN + "Copied updater.exe to 'dist' directory\n" + Style.RESET_ALL)
        elif os.path.isfile(updater_dist_path):
            shutil.copy2(updater_dist_path, updater_exe_path)
            print(Fore.GREEN + "Copied updater.exe to project directory\n" + Style.RESET_ALL)
        else:
            updater_py_path = os.path.join(project_directory, "updater.py")
            if not os.path.isfile(updater_py_path):
                print(Fore.RED + "updater.py does not exist. Exiting the script" + Style.RESET_ALL)
                sys.exit(1)
            nuitka_updater_command = (
                    r'cd /d "' + project_directory + r'\.venv\Scripts" & python -m nuitka "' + updater_py_path +
                    r'" --onefile --deployment --enable-plugin=tk-inter --disable-console --python-flag=no_asserts ' +
                    r'--nofollow-import-to=unittest --python-flag=no_docstrings --python-flag=no_site ' +
                    r'--output-dir="' + project_directory + r'" ' + '--product-name="Tera Term UI Updater" ' +
                    r'--company-name="Armando Del Valle Tejada" ' + '--file-description="TeraTermUI Updater" ' +
                    r'--copyright="Copyright © 2024 Armando Del Valle Tejada" --file-version="1.0.0" '
                    r'--product-version="1.0.0" '
            )
            subprocess.run(nuitka_updater_command, shell=True, check=True)
            manifest_path = os.path.join(project_directory, "TeraTermUI.manifest")
            attach_manifest(updater_exe_path, manifest_path)
            shutil.copy2(updater_exe_path, updater_dist_path)
            shutil.copy2(updater_exe_path, output_directory)
            for folder in ["updater.build", "updater.onefile-build", "updater.dist"]:
                folder_path = os.path.join(project_directory, folder)
                if os.path.exists(folder_path):
                    shutil.rmtree(folder_path)
            print(Fore.GREEN + "\nSuccessfully compiled updater.py\n" + Style.RESET_ALL)
except Exception as e:
    print(Fore.RED + f"An error occurred: {e}\n" + Style.RESET_ALL)
    sys.exit(1)
try:
    connection = sqlite3.connect(r"C:\Users" + "\\" + username + r"\PycharmProjects\TeraTermUI\database.db")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM user_data")
    cursor.execute("DELETE FROM save_classes")
    connection.commit()
except KeyboardInterrupt as e:
    shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + f"Failed to reset database: {e}\n" + Style.RESET_ALL)
    sys.exit(1)
except Exception as e:
    shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + f"Failed to reset database: {e}\n" + Style.RESET_ALL)
try:
    with open(project_directory+r"\TeraTermUI.py", "r", encoding="utf-8") as file:
        data = file.read()
    if 'self.mode = "Portable"' in data:
        versions = ["installer", "portable"]
    else:
        versions = ['portable', 'installer']
    data = re.sub(r'self.USER_APP_VERSION = ".*?"', f'self.USER_APP_VERSION = "{update_without_v}"', data)
    with open(project_directory+r"\TeraTermUI.py", "w", encoding="utf-8") as file:
        file.write(data)
except KeyboardInterrupt as e:
    shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + f"Failed to decide what version to make (Installer or Portable): {e}\n" + Style.RESET_ALL)
    sys.exit(1)
except Exception as e:
    shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + f"Failed to decide what version to make (Installer or Portable): {e}\n" + Style.RESET_ALL)

for version in versions:
    script = None
    try:
        with open(project_directory+r"\TeraTermUI.py", "r", encoding="utf-8") as file:
            data = file.read()
        if version == "installer":
            script = "installer"
            data = data.replace('self.mode = "Portable"',
                                'self.mode = "Installation"')
            data = data.replace('if not os.path.isfile(db_path) or not os.access(db_path, os.R_OK):',
                                'if not os.path.exists(self.db_path):')
            data = data.replace('self.connection = sqlite3.connect(db_path, check_same_thread=False)',
                                'self.connection = sqlite3.connect(self.db_path, check_same_thread=False)')
            data = data.replace('closing(sqlite3.connect(TeraTermUI.get_absolute_path("database.db"))) as connection',
                                'closing(sqlite3.connect(self.db_path)) as connection')
            data = data.replace('with open(self.SERVICE_ACCOUNT_FILE, "rb"):',
                                'with open(self.ath, "rb"):')
            data = data.replace('archive = pyzipper.AESZipFile(self.SERVICE_ACCOUNT_FILE)',
                                'archive = pyzipper.AESZipFile(self.ath)')
            data = data.replace('with open(TeraTermUI.get_absolute_path("logs.txt"), "a")',
                                'with open(self.logs, "a")')
            print(Fore.GREEN + "Successfully started installer version\n" + Style.RESET_ALL)
        else:
            script = "portable"
            data = data.replace('self.mode = "Installation"',
                                'self.mode = "Portable"')
            data = data.replace('if not os.path.exists(self.db_path):',
                                'if not os.path.isfile(db_path) or not os.access(db_path, os.R_OK):')
            data = data.replace('self.connection = sqlite3.connect(self.db_path, check_same_thread=False)',
                                'self.connection = sqlite3.connect(db_path, check_same_thread=False)')
            data = data.replace('closing(sqlite3.connect(self.db_path)) as connection',
                                'closing(sqlite3.connect(TeraTermUI.get_absolute_path("database.db"))) as connection')
            data = data.replace('with open(self.ath, "rb"):',
                                'with open(self.SERVICE_ACCOUNT_FILE, "rb"):')
            data = data.replace('archive = pyzipper.AESZipFile(self.ath)',
                                'archive = pyzipper.AESZipFile(self.SERVICE_ACCOUNT_FILE)')
            data = data.replace('with open(self.logs, "a")',
                                'with open(TeraTermUI.get_absolute_path("logs.txt"), "a")')
            print(Fore.GREEN + "Successfully started portable version\n" + Style.RESET_ALL)
        with open(project_directory+r"\TeraTermUI.py", "w", encoding="utf-8") as file:
            file.write(data)
    except KeyboardInterrupt as e:
        shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Error modifying script: {e}\n" + Style.RESET_ALL)
        sys.exit(1)
    except Exception as e:
        shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Error modifying script: {e}\n" + Style.RESET_ALL)
    try:
        subprocess.run(nuitka_command, shell=True, check=True)
        print(Fore.GREEN + "\nSuccessfully completed nuitka script\n" + Style.RESET_ALL)
        executable_path = os.path.join(output_directory, "TeraTermUI.dist", "TeraTermUI.exe")
        manifest_path = os.path.join(project_directory, "TeraTermUI.manifest")
        attach_manifest(executable_path, manifest_path)
    except KeyboardInterrupt as e:
        shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to create executable with Nuitka: {e}\n" + Style.RESET_ALL)
        sys.exit(1)
    except Exception as e:
        shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to create executable with Nuitka: {e}\n" + Style.RESET_ALL)

    if script == "installer":
        try:
            os.rename(output_directory + r"\TeraTermUI.dist",
                      output_directory + r"\TeraTermUI_installer")
            print(Fore.GREEN + "\nSuccessfully created TeraTermUI installer folder\n" + Style.RESET_ALL)
        except KeyboardInterrupt as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error renaming folder: {e}\n" + Style.RESET_ALL)
            sys.exit(1)
        except Exception as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error renaming folder: {e}\n" + Style.RESET_ALL)
        try:
            os.remove(os.path.join(output_directory, "TeraTermUI_installer", "database.db"))
            os.remove(os.path.join(output_directory, "TeraTermUI_installer", "feedback.zip"))
            os.remove(os.path.join(output_directory, "TeraTermUI_installer", "updater.exe"))
        except KeyboardInterrupt as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error removing files: {e}\n" + Style.RESET_ALL)
            sys.exit(1)
        except Exception as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error removing files: {e}\n" + Style.RESET_ALL)
        try:
            subprocess.run([inno_directory, output_directory + r"\InstallerScript.iss"], check=True)
            print(Fore.GREEN + "Successfully compiled TeraTermUI installer\n" + Style.RESET_ALL)
        except KeyboardInterrupt as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error compiling Inno Setup script: {e}\n" + Style.RESET_ALL)
            sys.exit(1)
        except Exception as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error compiling Inno Setup script: {e}\n" + Style.RESET_ALL)
        try:
            shutil.move(output_directory + r"\output\TeraTermUI_64-bit_Installer-"+update+".exe", output_directory)
            shutil.rmtree(output_directory + r"\output")
            print(Fore.GREEN + "Successfully completed installer version\n" + Style.RESET_ALL)
        except KeyboardInterrupt as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error moving or removing folder: {e}\n" + Style.RESET_ALL)
            sys.exit(1)
        except Exception as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error moving or removing folder: {e}\n" + Style.RESET_ALL)

    elif script == "portable":
        try:
            os.rename(output_directory + r"\TeraTermUI.dist", output_directory + r"\TeraTermUI")
            zip_file_path = output_directory + fr"\{app_folder}-"+update+""
            shutil.make_archive(zip_file_path, "zip", output_directory, app_folder)
            print(Fore.GREEN + "\nSuccessfully completed portable version\n" + Style.RESET_ALL)
        except KeyboardInterrupt as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error creating zip file: {e}\n" + Style.RESET_ALL)
            sys.exit(1)
        except Exception as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error creating zip file: {e}\n" + Style.RESET_ALL)

print(Fore.GREEN + "Both versions (installer and portable) have been created successfully.\n"
      + Style.RESET_ALL)
os.remove(program_backup)
sys.exit(0)
