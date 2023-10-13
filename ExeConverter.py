import re
import os
import signal
import shutil
import sqlite3
import subprocess
import sys
from colorama import init, Fore, Style


def extract_second_date_from_file(filepath):
    with open(filepath, 'r') as f:
        for line in f:
            # Find all date patterns in the line
            dates = re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}', line)

            # Check if at least two dates are found
            if len(dates) >= 2:
                return dates[1]
        return None


def extract_version_main_file(filepath):
    with open(filepath, 'r') as f:
        for line in f:
            # Check if the line contains the word "v" followed by a numeric character
            if 'v' in line:
                positions = [pos for pos, char in enumerate(line) if char == 'v']
                for pos in positions:
                    if line[pos+1].isdigit():
                        start_pos = pos + 1
                        end_pos = line[start_pos:].find(' ')
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
# Prompt user for version input until a valid format is received
while True:
    user_input = input(Fore.BLUE + "Please enter the update version number"
                       " (e.g., v1.0.0 or 1.0.0): " + Style.RESET_ALL).replace(" ", "").strip()
    if validate_version(user_input):
        user_input_segments = user_input.lower().replace('v', '').split('.')
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
if user_input.startswith('v'):
    update = user_input
    update_without_v = user_input[1:]
else:
    update_without_v = user_input
    update = "v" + update_without_v
versions = ['installer', 'portable']
output_directory = os.path.join(r"C:/Users/" + username + "/OneDrive/Documentos", "TeraTermUI_" + update)
upx_command = r"upx --best " + output_directory + r"\TeraTermUI.dist\TeraTermUI.exe"

# If process gets abruptly interrupted, load backup file
program_backup = project_directory + r"\TeraTermUI.BAK.py"
check_and_restore_backup()
shutil.copy2(project_directory + r"\TeraTermUI.py", program_backup)
signal.signal(signal.SIGTERM, terminate_process)
signal.signal(signal.SIGINT, terminate_process)

try:
    if os.path.exists(output_directory):
        shutil.rmtree(output_directory)
    os.makedirs(output_directory, exist_ok=True)
    for filename in os.listdir(project_directory+"\dist"):
        src = os.path.join(project_directory+"\dist", filename)
        dst = os.path.join(output_directory, filename)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
    # Open the inno script to overwrite it
    file_path = os.path.join(output_directory, "InstallerScript.iss")
    with open(file_path, "r") as file:
        lines = file.readlines()
    with open(file_path, "w") as file:
        for line in lines:
            if line.startswith("#define MyAppVersion"):
                line = '#define MyAppVersion "' + update_without_v + '"\n'
            elif line.startswith("#define MyAppPath"):
                line = '#define MyAppPath "' + output_directory + '"\n'
            elif line.startswith("OutputBaseFilename="):
                line = 'OutputBaseFilename="TeraTermUI_64-bit_Installer-' + update + '"\n'
            # Write the line back to the file
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
    sys.exit(1)

nuitka_command = (
    r'cd /d "'+project_directory+r'\venv\Scripts" & python -m nuitka --standalone '
    r'--experimental=treefree "'+project_directory+r'\TeraTermUI.py" '
    r'--enable-plugin=tk-inter --include-data-dir="'+project_directory+r'\venv\Lib\site-packages'
    r'\customtkinter=customtkinter" --include-data-dir="'+project_directory+r'\venv\Lib\site-packages'
    r'\CTkMessageBox=CTkMessageBox" --include-package=CTkToolTip '
    r'--include-data-dir="'+project_directory+r'\images=images" '
    r'--include-data-dir="'+project_directory+r'\slideshow=slideshow" '                                           
    r'--include-data-dir="'+project_directory+r'\sounds=sounds" '
    r'--include-data-file="'+project_directory+r'\database.db=database.db" '
    r'--include-data-file="'+project_directory+r'\Tesseract-OCR.7z=Tesseract-OCR.7z" '
    r'--include-data-file="'+project_directory+r'\feedback.zip=feedback.zip" '
    r'--include-data-file="'+project_directory+r'\VERSION.txt=VERSION.txt" '
    r'--include-data-file="'+project_directory+r'\LICENSE.txt=LICENSE.txt" '
    r'--include-data-file="'+project_directory+r'\english.json=english.json" '     
    r'--include-data-file="'+project_directory+r'\spanish.json=spanish.json" '                                                
    r'--output-dir="'+output_directory+r'" --disable-console '
    r'--windows-icon-from-ico="'+project_directory+r'\images\tera-term.ico" '
    r'--lto=yes --nofollow-import-to=unittest --nofollow-import-to=reportlab.graphics.testshapes'
)

try:
    # Execute the DELETE SQL command
    connection = sqlite3.connect(r"C:\Users" + "\\" + username + r"\PycharmProjects\TeraTermUI\database.db")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM user_data")
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
    sys.exit(1)
try:
    # Check current state of the script to decide the order of versions
    with open(project_directory+r"\TeraTermUI.py", 'r', encoding='utf-8') as file:
        data = file.read()
    if 'if not os.path.isfile(db_path):' in data:
        versions = ['installer', 'portable']
    else:
        versions = ['portable', 'installer']
    data = re.sub(r'self.USER_APP_VERSION = ".*?"', f'self.USER_APP_VERSION = "{update_without_v}"', data)
    with open(project_directory+r"\TeraTermUI.py", 'w', encoding='utf-8') as file:
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
    sys.exit(1)

for version in versions:
    script = None
    try:
        with open(project_directory+r"\TeraTermUI.py", 'r', encoding='utf-8') as file:
            data = file.read()
        # Replace old text with new text for portable and installer versions
        if version == 'installer':
            script = "installer"
            data = data.replace('if not os.path.isfile(db_path):',
                                'if not os.path.exists(self.db_path):')
            data = data.replace('self.connection = sqlite3.connect(db_path, check_same_thread=False)',
                                'self.connection = sqlite3.connect(self.db_path, check_same_thread=False)')
            data = data.replace('closing(sqlite3.connect("database.db")) as connection',
                                'closing(sqlite3.connect(self.db_path)) as connection')
            data = data.replace('with open(self.SERVICE_ACCOUNT_FILE, "rb"):',
                                'with open(self.ath, "rb"):')
            data = data.replace('archive = pyzipper.AESZipFile(self.SERVICE_ACCOUNT_FILE)',
                                'archive = pyzipper.AESZipFile(self.ath)')
            data = data.replace('FileLock(lock_file, timeout=10)',
                                'FileLock(lock_file_appdata, timeout=10)')
            print(Fore.GREEN + "Successfully started installer version\n" + Style.RESET_ALL)
        else:
            script = "portable"
            data = data.replace('if not os.path.exists(self.db_path):',
                                'if not os.path.isfile(db_path):')
            data = data.replace('self.connection = sqlite3.connect(self.db_path, check_same_thread=False)',
                                'self.connection = sqlite3.connect(db_path, check_same_thread=False)')
            data = data.replace('closing(sqlite3.connect(self.db_path)) as connection',
                                'closing(sqlite3.connect("database.db")) as connection')
            data = data.replace('with open(self.ath, "rb"):',
                                'with open(self.SERVICE_ACCOUNT_FILE, "rb"):')
            data = data.replace('archive = pyzipper.AESZipFile(self.ath)',
                                'archive = pyzipper.AESZipFile(self.SERVICE_ACCOUNT_FILE)')
            data = data.replace('FileLock(lock_file_appdata, timeout=10)',
                                'FileLock(lock_file, timeout=10)')
            print(Fore.GREEN + "Successfully started portable version\n" + Style.RESET_ALL)

        with open(project_directory+r"\TeraTermUI.py", 'w', encoding='utf-8') as file:
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
        sys.exit(1)

    try:
        subprocess.run(nuitka_command, shell=True, check=True)
        print(Fore.GREEN + "Successfully completed nuitka script\n" + Style.RESET_ALL)
    except KeyboardInterrupt as e:
        shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to create executable with Nuitka: {e}\n" + Style.RESET_ALL)
        sys.exit(1)
    except Exception as e:
        shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to create executable with Nuitka: {e}\n" + Style.RESET_ALL)
        sys.exit(1)

    try:
        subprocess.run(upx_command, shell=True, check=True)
        print(Fore.GREEN + "Successfully completed UPX script\n" + Style.RESET_ALL)
    except KeyboardInterrupt as e:
        shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to compress executable with UPX: {e}\n" + Style.RESET_ALL)
        sys.exit(1)
    except Exception as e:
        shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to compress executable with UPX: {e}\n" + Style.RESET_ALL)
        sys.exit(1)

    if script == "installer":
        try:
            os.rename(output_directory + r"\TeraTermUI.dist",
                      output_directory + r"\TeraTermUI_installer")
            print(Fore.GREEN + "Successfully created TeraTermUI installer folder\n" + Style.RESET_ALL)
        except KeyboardInterrupt as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error renaming folder: {e}\n" + Style.RESET_ALL)
            sys.exit(1)
        except Exception as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error renaming folder: {e}\n" + Style.RESET_ALL)
            sys.exit(1)

        try:
            os.remove(os.path.join(output_directory, "TeraTermUI_installer", "database.db"))
            os.remove(os.path.join(output_directory, "TeraTermUI_installer", "feedback.zip"))
        except KeyboardInterrupt as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error removing files: {e}\n" + Style.RESET_ALL)
            sys.exit(1)
        except Exception as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error removing files: {e}\n" + Style.RESET_ALL)
            sys.exit(1)

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
            sys.exit(1)

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
            sys.exit(1)

    elif script == "portable":
        try:
            os.rename(output_directory + r"\TeraTermUI.dist", output_directory + r"\TeraTermUI")
            zip_file_path = output_directory + fr"\{app_folder}-"+update+""
            shutil.make_archive(zip_file_path, 'zip', output_directory, app_folder)
            print(Fore.GREEN + "Successfully completed portable version\n" + Style.RESET_ALL)
        except KeyboardInterrupt as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error creating zip file: {e}\n" + Style.RESET_ALL)
            sys.exit(1)
        except Exception as e:
            shutil.copy2(program_backup, project_directory + r"\TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error creating zip file: {e}\n" + Style.RESET_ALL)
            sys.exit(1)

print(Fore.GREEN + "Both versions (installer and portable) have been created successfully.\n"
      + Style.RESET_ALL)
os.remove(program_backup)
sys.exit(0)
