import argparse
import hashlib
import re
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from colorama import init, Fore, Style
from datetime import datetime, UTC

def parse_arguments():
    parser = argparse.ArgumentParser(description="TeraTermUI Exe Converter")
    parser.add_argument("--updater-version", type=str, default="1.0.2",
                        help="Specify the version number for updater.exe (default: 1.0.2)")
    parser.add_argument("--db-version", type=str, default="1.0.0",
                        help="Specify the version number for the database (default: 1.0.0)")
    parser.add_argument("--output-dir", type=str,
                        help="Specify custom output directory path (default: C:/Users/username/TeraTermUI_Builds)")
    parser.add_argument("--lto", choices=["auto", "yes", "no"], default="yes",
                        help="Set LTO (Link-Time Optimization) value")
    parser.add_argument("--report", action="store_true", help="Generate Nuitka compilation report")

    args = parser.parse_args()
    if args.output_dir:
        args.output_dir = os.path.normpath(args.output_dir).replace("\\", "/")
        if not os.path.isabs(args.output_dir):
            args.output_dir = os.path.abspath(args.output_dir).replace("\\", "/")

    return args

def extract_second_date_from_file(filepath):
    with open(filepath, "r") as file:
        for line in file:
            dates = re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", line)
            if len(dates) >= 2:
                return dates[1]

        return None

def check_and_restore_backup():
    main_file_path = os.path.join(project_directory, "TeraTermUI.py")
    if os.path.exists(main_file_path) and os.path.getsize(main_file_path) > 0:
        main_file_empty = False
    else:
        main_file_empty = True
    if os.path.exists(program_backup):
        if main_file_empty:
            shutil.copy2(program_backup, main_file_path)
            print(Fore.YELLOW + "\nMain file is empty. Restoration from backup completed" + Style.RESET_ALL)
            os.remove(program_backup)
        else:
            program_backup_date = extract_second_date_from_file(program_backup)
            tera_term_ui_date = extract_second_date_from_file(main_file_path)
            if program_backup_date != tera_term_ui_date:
                print(Fore.YELLOW + "\nDate mismatch detected between the main file and the backup one. "
                                    "\nRestoration from backup skipped. Delete backup file if no longer needed"
                      + Style.RESET_ALL)
            else:
                shutil.copy2(program_backup, main_file_path)
                print(
                    Fore.YELLOW + "\nPrevious session was interrupted. Restoration from backup completed" +
                    Style.RESET_ALL)
                os.remove(program_backup)

def attach_manifest(executable_path, manifest_path):
    try:
        sha1_hash = hashlib.sha1()
        with open(executable_path, "rb") as file:
            for byte_block in iter(lambda: file.read(8192), b""):
                sha1_hash.update(byte_block)
        sha1_checksum = sha1_hash.hexdigest()

        executable_name = os.path.basename(executable_path)
        with open(manifest_path, "r") as file:
            manifest_content = file.read()
        updated_manifest_content = re.sub(
            fr'<file name="{re.escape(executable_name)}" hashalg="SHA1" hash=".*?"/>',
            f'<file name="{executable_name}" hashalg="SHA1" hash="{sha1_checksum}"/>',
            manifest_content)
        with open(manifest_path, "w") as file:
            file.write(updated_manifest_content)

        subprocess.run(f"mt.exe -manifest {manifest_path} -outputresource:{executable_path};1", check=True)
        print(Fore.GREEN + "\nSuccessfully attached manifest\n" + Style.RESET_ALL)
    except KeyboardInterrupt as e:
        shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to attach manifest: {e}\n" + Style.RESET_ALL)
        sys.exit(1)
    except Exception as e:
        shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to attach manifest: {e}\n" + Style.RESET_ALL)

def generate_checksum(version_filename, executable_filename):
    try:
        sha256_hash = hashlib.sha256()
        with open(executable_filename, "rb") as file:
            for byte_block in iter(lambda: file.read(8192), b""):
                sha256_hash.update(byte_block)
        sha256_checksum = sha256_hash.hexdigest()

        if version_filename:
            try:
                with open(version_filename, "r") as file:
                    lines = file.readlines()
            except FileNotFoundError:
                lines = []

            checksum_line = f"SHA-256 Checksum: {sha256_checksum}\n"
            checksum_updated = False

            with open(version_filename, "w") as file:
                for line in lines:
                    if line.startswith("SHA-256 Checksum:"):
                        file.write(checksum_line)
                        checksum_updated = True
                    else:
                        file.write(line)

                if not checksum_updated:
                    file.write("\n" + checksum_line)
        print(Fore.GREEN + "Successfully generated SHA-256 checksum\n" + Style.RESET_ALL)
        return sha256_checksum
    except KeyboardInterrupt as e:
        shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to generate SHA-256 checksum: {e}\n" + Style.RESET_ALL)
        sys.exit(1)
    except Exception as e:
        shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to generate SHA-256 checksum {e}\n" + Style.RESET_ALL)

def update_updater_hash_value(main_file_path, new_hash):
    try:
        with open(main_file_path, "r", encoding="utf-8") as file:
            content = file.read()
        updated_content = re.sub(r'self\.updater_hash\s*=\s*".*?"',
                                 f'self.updater_hash = "{new_hash}"',
                                 content)
        with open(main_file_path, "w", encoding="utf-8") as file:
            file.write(updated_content)
    except Exception as e:
        print(Fore.RED + f"Error updating updater_hash: {e}\n" + Style.RESET_ALL)

def freeze_requirements(project_directory):
    scripts_directory = os.path.join(project_directory, ".venv", "Scripts")
    requirements_path = os.path.join(scripts_directory, "requirements.txt")
    clear_comtypes_cache_path = os.path.join(scripts_directory, "clear_comtypes_cache.exe")
    original_dir = os.getcwd()
    try:
        os.chdir(scripts_directory)
        subprocess.run(f'pip freeze > "{requirements_path}"', shell=True, check=True)
        process = subprocess.Popen([clear_comtypes_cache_path], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        process.communicate(input='y\n')
        if process.returncode != 0:
            print(Fore.RED + "Failed to clear comtypes cache" + Style.RESET_ALL)
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f"Failed to create requirements.txt: {e}" + Style.RESET_ALL)
    finally:
        os.chdir(original_dir)

def validate_version(ver):
    pattern = r"^[vV]?([0-9]{1,3}\.[0-9]{1,3}(\.[0-9]{1,3})?|[0-9]{1,3})$"
    return bool(re.match(pattern, ver, re.IGNORECASE))

init()
username = os.getlogin()
project_directory = str(os.path.dirname(os.path.abspath(__file__)).replace("\\", "/"))
inno_directory = "C:/Program Files (x86)/Inno Setup 6/ISCC.exe"
current_year = datetime.now().year
app_folder = "TeraTermUI"
while True:
    args = parse_arguments()
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
freeze_requirements(project_directory)
user_input = user_input.lower()
if user_input.startswith("v"):
    update = user_input
    update_without_v = user_input[1:]
else:
    update_without_v = user_input
    update = "v" + update_without_v
versions = ["installer", "portable"]
updater_version = args.updater_version
db_version = args.db_version
if args.output_dir:
    output_directory = os.path.join(args.output_dir, "TeraTermUI_" + update).replace("\\", "/")
else:
    output_directory = os.path.join("C:/Users/" + username + "/TeraTermUI_Builds",
                                    "TeraTermUI_" + update).replace("\\", "/")
program_backup = project_directory + "/TeraTermUI.BAK.py"
check_and_restore_backup()
shutil.copy2(project_directory + "/TeraTermUI.py", program_backup)
current_date = datetime.now().strftime("%m/%d/%Y")
version_file_path = os.path.join(project_directory, "VERSION.txt")
with open(version_file_path, "r") as file:
    version_file_content = file.read()
version_file_content = re.sub(r"(?<=Version Number: ).*", update, version_file_content)
version_file_content = re.sub(r"(?<=Release Date: ).*", current_date, version_file_content)
with open(version_file_path, "w") as file:
    file.write(version_file_content)
license_file_path = os.path.join(project_directory, "LICENSE.txt")
with open(license_file_path, "r") as file:
    license_content = file.read()
updated_license_content = re.sub(r"Copyright \(c\) \d{4}", f"Copyright (c) {current_year}", license_content)
with open(license_file_path, "w") as file:
    file.write(updated_license_content)
try:
    with sqlite3.connect(project_directory + "/database.db") as connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM user_config")
        cursor.execute("DELETE FROM user_data")
        cursor.execute("DELETE FROM saved_classes")
        if os.path.exists(project_directory + "/masterkey.json"):
            os.remove(project_directory + "/masterkey.json")
        utc_now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT value FROM metadata WHERE key = ?", ("version",))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO metadata (key, value, date) VALUES (?, ?, ?)",
                           ("version", db_version, utc_now_str))
        elif row[0] != db_version:
            cursor.execute("UPDATE metadata SET value = ?, date = ? WHERE key = ?",
                           (db_version, utc_now_str, "version"))
    dist_db_path = os.path.join(project_directory, "dist", "database.db")
    shutil.copy2(os.path.join(project_directory, "database.db"), dist_db_path)
except KeyboardInterrupt as e:
    shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + f"Failed to deal with database: {e}\n" + Style.RESET_ALL)
    sys.exit(1)
except Exception as e:
    shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + f"Failed to deal with database: {e}\n" + Style.RESET_ALL)
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
            elif line.startswith("OutputBaseFilename="):
                line = 'OutputBaseFilename="TeraTermUI_x64_Installer-' + update + '"\n'
            file.write(line)
    print(Fore.GREEN + "\nSuccessfully created distribution directory\n" + Style.RESET_ALL)
except PermissionError as e:
    print(Fore.RED + f"Error: cannot access because it is being used by another process: {e}\n" + Style.RESET_ALL)
    sys.exit(1)
except KeyboardInterrupt as e:
    shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + f"Error modifying creating distribution directory: {e}\n" + Style.RESET_ALL)
    sys.exit(1)
except Exception as e:
    shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + f"Error modifying creating distribution directory: {e}\n" + Style.RESET_ALL)

nuitka_command = (
    'cd /d "' + project_directory + '/.venv/Scripts" & python -m nuitka --standalone '
    '--deployment "' + project_directory + '/TeraTermUI.py" --windows-console-mode=disable '
    '--enable-plugin=tk-inter --include-data-dir="' + project_directory + '/.venv/Lib/site-packages'
    '/customtkinter=customtkinter" --include-data-dir="' + project_directory + '/.venv/Lib/site-packages'
    '/CTkMessageBox=CTkMessageBox" --include-package=CTkToolTip --include-package=CTkTable '
    '--include-data-dir="' + project_directory + '/images=images" '
    '--include-data-dir="' + project_directory + '/slideshow=slideshow" '                                           
    '--include-data-dir="' + project_directory + '/sounds=sounds" '
    '--include-data-dir="' + project_directory + '/translations=translations" '
    '--include-data-file="' + project_directory + '/database.db=database.db" '
    '--include-data-file="' + project_directory + '/Tesseract-OCR.7z=Tesseract-OCR.7z" '
    '--include-data-file="' + project_directory + '/feedback.zip=feedback.zip" '
    '--include-data-file="' + project_directory + '/VERSION.txt=VERSION.txt" '
    '--include-data-file="' + project_directory + '/LICENSE.txt=LICENSE.txt" '
    '--include-data-file="' + project_directory + r'/updater.exe=updater.exe" '
    '--output-dir="' + output_directory + '" --python-flag=no_asserts --lto="' + args.lto + '" '
    '--windows-icon-from-ico="' + project_directory + '/images/tera-term.ico" '
    '--nofollow-import-to=unittest --python-flag=no_docstrings --product-name="Tera Term UI" '
    '--company-name="Armando Del Valle Tejada" --file-description="TeraTermUI" '  
    '--file-version="' + update_without_v + '" --product-version="' + update_without_v + '" '
    '--copyright="Copyright (c) ' + str(current_year) + ' Armando Del Valle Tejada" '
)
if args.report:
    nuitka_command += f' --report="{output_directory}/compilation_report.html"'
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
                    r'cd /d "' + project_directory + r'/.venv/Scripts" & python -m nuitka "' + updater_py_path +
                    r'" --onefile --deployment --enable-plugin=tk-inter --python-flag=no_asserts ' +
                    r'--nofollow-import-to=unittest --python-flag=no_docstrings --python-flag=no_site ' +
                    r'--output-dir="' + project_directory + r'" ' + '--product-name="Tera Term UI Updater" ' +
                    r'--company-name="Armando Del Valle Tejada" ' + '--file-description="TeraTermUI Updater" ' +
                    r'--copyright="Copyright (c) 2024 Armando Del Valle Tejada" --file-version="' + updater_version + '" ' +
                    r'--product-version="' + updater_version + '" --windows-console-mode=disable --lto="yes" '
            )
            subprocess.run(nuitka_updater_command, shell=True, check=True)
            print(Fore.GREEN + "\nSuccessfully compiled updater.py\n" + Style.RESET_ALL)
            manifest_path = os.path.join(project_directory, "updater.manifest")
            attach_manifest(updater_exe_path, manifest_path)
            updater_checksum = generate_checksum(None, updater_exe_path)
            update_updater_hash_value(os.path.join(project_directory, "TeraTermUI.py"), updater_checksum)
            shutil.copy2(updater_exe_path, updater_dist_path)
            shutil.copy2(updater_exe_path, output_directory)
            for folder in ["updater.build", "updater.onefile-build", "updater.dist"]:
                folder_path = os.path.join(project_directory, folder)
                if os.path.exists(folder_path):
                    dest_path = os.path.join(output_directory, folder)
                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)
                    shutil.move(folder_path, dest_path)
except Exception as e:
    print(Fore.RED + f"An error occurred: {e}\n" + Style.RESET_ALL)
    sys.exit(1)
try:
    with open(project_directory + "/TeraTermUI.py", "r", encoding="utf-8") as file:
        data = file.read()
    if 'self.mode = "Portable"' in data:
        versions = ["installer", "portable"]
    else:
        versions = ["portable", "installer"]
    data = re.sub(r'self.USER_APP_VERSION = ".*?"', f'self.USER_APP_VERSION = "{update_without_v}"', data)
    data = re.sub(r"^(# DATE - Started .*?, Current Build )v[\d.]+( - .+)$",
                  r"\1" + update + r"\2", data, flags=re.MULTILINE)
    with open(project_directory + "/TeraTermUI.py", "w", encoding="utf-8") as file:
        file.write(data)
    shutil.copy2(project_directory + "/TeraTermUI.py", program_backup)
except KeyboardInterrupt as e:
    shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + f"Failed to decide what version to make (Installer or Portable): {e}\n" + Style.RESET_ALL)
    sys.exit(1)
except Exception as e:
    shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
    os.remove(program_backup)
    print(Fore.RED + f"Failed to decide what version to make (Installer or Portable): {e}\n" + Style.RESET_ALL)

installer_checksum = None
portable_checksum = None
for version in versions:
    script = None
    try:
        with open(project_directory + "/TeraTermUI.py", "r", encoding="utf-8") as file:
            data = file.read()
        if version == "installer":
            script = "installer"
            data = data.replace('self.mode = "Portable"',
                                'self.mode = "Installation"')
            data = data.replace('if not os.path.isfile(db_path) or not os.access(db_path, os.R_OK):',
                                'if not os.path.exists(self.db_path):')
            data = data.replace('self.connection_db = sqlite3.connect(db_path, check_same_thread=False)',
                                'self.connection_db = sqlite3.connect(self.db_path, check_same_thread=False)')
            data = data.replace('closing(sqlite3.connect(TeraTermUI.get_absolute_path("database.db"))) as connection',
                                'closing(sqlite3.connect(self.db_path)) as connection')
            data = data.replace('with AESZipFile(self.SERVICE_ACCOUNT_FILE) as archive:',
                                'with AESZipFile(self.ath) as archive:')
            data = data.replace('mode = "Portable"',
                                'mode = "Installation"')
            print(Fore.GREEN + "Successfully started installer version\n" + Style.RESET_ALL)
        else:
            script = "portable"
            data = data.replace('self.mode = "Installation"',
                                'self.mode = "Portable"')
            data = data.replace('if not os.path.exists(self.db_path):',
                                'if not os.path.isfile(db_path) or not os.access(db_path, os.R_OK):')
            data = data.replace('self.connection_db = sqlite3.connect(self.db_path, check_same_thread=False)',
                                'self.connection_db = sqlite3.connect(db_path, check_same_thread=False)')
            data = data.replace('closing(sqlite3.connect(self.db_path)) as connection',
                                'closing(sqlite3.connect(TeraTermUI.get_absolute_path("database.db"))) as connection')
            data = data.replace('with AESZipFile(self.ath) as archive:',
                                'with AESZipFile(self.SERVICE_ACCOUNT_FILE) as archive:')
            data = data.replace('mode = "Installation"',
                                'mode = "Portable"')
            print(Fore.GREEN + "Successfully started portable version\n" + Style.RESET_ALL)
        with open(project_directory + "/TeraTermUI.py", "w", encoding="utf-8") as file:
            file.write(data)
    except KeyboardInterrupt as e:
        shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Error modifying script: {e}\n" + Style.RESET_ALL)
        sys.exit(1)
    except Exception as e:
        shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Error modifying script: {e}\n" + Style.RESET_ALL)
    try:
        subprocess.run(nuitka_command, shell=True, check=True)
        print(Fore.GREEN + "\nSuccessfully completed nuitka script\n" + Style.RESET_ALL)
        executable_path = os.path.join(output_directory, "TeraTermUI.dist", "TeraTermUI.exe")
        version_path = os.path.join(output_directory, "TeraTermUI.dist", "VERSION.txt")
        manifest_path = os.path.join(project_directory, "TeraTermUI.manifest")
        attach_manifest(executable_path, manifest_path)
        generate_checksum(version_path, executable_path)
    except KeyboardInterrupt as e:
        shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to create executable with Nuitka: {e}\n" + Style.RESET_ALL)
        sys.exit(1)
    except Exception as e:
        shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
        os.remove(program_backup)
        print(Fore.RED + f"Failed to create executable with Nuitka: {e}\n" + Style.RESET_ALL)

    if script == "installer":
        retries = 5
        delay = 1
        for i in range(retries):
            try:
                os.rename(output_directory + "/TeraTermUI.dist", output_directory + "/TeraTermUI_installer")
                break
            except OSError as e:
                if i < retries - 1:
                    time.sleep(delay)
                else:
                    shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
                    os.remove(program_backup)
                    print(Fore.RED + f"Error renaming folder: {e}\n" + Style.RESET_ALL)
            except KeyboardInterrupt as e:
                shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
                os.remove(program_backup)
                print(Fore.RED + f"Error renaming folder: {e}\n" + Style.RESET_ALL)
                sys.exit(1)
            except Exception as e:
                shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
                os.remove(program_backup)
                print(Fore.RED + f"Error renaming folder: {e}\n" + Style.RESET_ALL)
        try:
            jaraco_folder = os.path.join(output_directory, "TeraTermUI_installer", "jaraco")
            if os.path.exists(jaraco_folder) and os.path.isdir(jaraco_folder):
                shutil.rmtree(jaraco_folder)
            os.remove(os.path.join(output_directory, "TeraTermUI_installer", "database.db"))
            os.remove(os.path.join(output_directory, "TeraTermUI_installer", "feedback.zip"))
            os.remove(os.path.join(output_directory, "TeraTermUI_installer", "updater.exe"))
        except KeyboardInterrupt as e:
            shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error removing files: {e}\n" + Style.RESET_ALL)
            sys.exit(1)
        except Exception as e:
            shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error removing files: {e}\n" + Style.RESET_ALL)
        try:
            subprocess.run([inno_directory, output_directory + "/InstallerScript.iss"], check=True)
            print(Fore.GREEN + "\nSuccessfully compiled installer script\n" + Style.RESET_ALL)
        except KeyboardInterrupt as e:
            shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error compiling Inno Setup script: {e}\n" + Style.RESET_ALL)
            sys.exit(1)
        except Exception as e:
            shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error compiling Inno Setup script: {e}\n" + Style.RESET_ALL)
        try:
            installer_executable_path = output_directory + "/TeraTermUI_x64_Installer-" + update + ".exe"
            shutil.move(output_directory + "/output/TeraTermUI_x64_Installer-" + update + ".exe", output_directory)
            shutil.rmtree(output_directory + "/output")
            installer_checksum = generate_checksum(None, installer_executable_path)
            print(Fore.GREEN + "Successfully completed installer version\n" + Style.RESET_ALL)
        except KeyboardInterrupt as e:
            shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error moving or removing folder: {e}\n" + Style.RESET_ALL)
            sys.exit(1)
        except Exception as e:
            shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
            os.remove(program_backup)
            print(Fore.RED + f"Error moving or removing folder: {e}\n" + Style.RESET_ALL)

    elif script == "portable":
        retries = 5
        delay = 1
        for i in range(retries):
            try:
                os.rename(output_directory + "/TeraTermUI.dist", output_directory + "/TeraTermUI")
                jaraco_folder = os.path.join(output_directory, "TeraTermUI", "jaraco")
                if os.path.exists(jaraco_folder) and os.path.isdir(jaraco_folder):
                    shutil.rmtree(jaraco_folder)
                zip_file_path = output_directory + f"/{app_folder}_x64-" + update + ""
                shutil.make_archive(zip_file_path, "zip", output_directory, app_folder)
                version_path = os.path.join(output_directory, app_folder, "VERSION.txt")
                destination_path = os.path.join(project_directory, "VERSION.txt")
                shutil.copy(version_path, destination_path)
                portable_checksum = generate_checksum(version_path, zip_file_path + ".zip")
                print(Fore.GREEN + "Successfully completed portable version\n" + Style.RESET_ALL)
                break
            except OSError as e:
                if i < retries - 1:
                    time.sleep(delay)
                else:
                    shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
                    os.remove(program_backup)
                    print(Fore.RED + f"Error during operation: {e}\n" + Style.RESET_ALL)
            except KeyboardInterrupt as e:
                shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
                os.remove(program_backup)
                print(Fore.RED + f"Operation interrupted: {e}\n" + Style.RESET_ALL)
                sys.exit(1)
            except Exception as e:
                shutil.copy2(program_backup, project_directory + "/TeraTermUI.py")
                os.remove(program_backup)
                print(Fore.RED + f"Unexpected error: {e}\n" + Style.RESET_ALL)
                sys.exit(1)
print(Fore.BLUE + "Checksum results:\n" + Style.RESET_ALL)
if portable_checksum:
    print(Fore.BLUE + f"Portable (ZIP) Checksum: {portable_checksum}\n" + Style.RESET_ALL)
if installer_checksum:
    print(Fore.BLUE+ f"Installer (EXE) Checksum: {installer_checksum}\n" + Style.RESET_ALL)
print(Fore.GREEN + "Both versions (installer and portable) have been created successfully.\n" + Style.RESET_ALL)
os.remove(program_backup)
sys.exit(0)
