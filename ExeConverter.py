import subprocess
import shutil
import os

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
    r'--windows-icon-from-ico=C:\Users\arman\PycharmProjects\TeraTermUI\images\tera-term.ico'
)
output_directory = r"C:\Users\arman\OneDrive\Documentos\TeraTermUI_v0.9.0"
upx_command = r"upx --best " + output_directory + r"\TeraTermUI.dist\TeraTermUI.exe"
inno_directory = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
versions = ['installer', 'portable']

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

        with open(project_directory, 'w', encoding='utf-8') as file:
            file.write(data)
    except Exception as e:
        print(f"Error modifying script: {e}")

    try:
        subprocess.run(nuitka_command, shell=True, check=True)
    except Exception as e:
        print(f"Failed to create executable with Nuitka: {e}")

    try:
        subprocess.run(upx_command, shell=True, check=True)
    except Exception as e:
        print(f"Failed to compress executable with UPX: {e}")
    if script == "installer":
        try:
            os.rename(output_directory + r"\TeraTermUI.dist",
                      output_directory + r"\TeraTermUI_installer")
        except Exception as e:
            print(f"Error renaming folder: {e}")

        try:
            subprocess.run([inno_directory, output_directory + r"\InstallerScript.iss"], check=True)
        except Exception as e:
            print(f"Error compiling Inno Setup script: {e}")

        try:
            shutil.move(output_directory + r"\output\TeraTermUI_64-bit_Installer-v0.9.0.exe", output_directory)
            shutil.rmtree(output_directory + r"\output")
        except Exception as e:
            print(f"Error moving or removing folder: {e}")

    elif script == "portable":
        try:
            os.rename(output_directory + r"\TeraTermUI.dist", output_directory + r"\TeraTermUI")
            shutil.make_archive(output_directory + r"\TeraTermUI-v0.9.0", 'zip', output_directory, "TeraTermUI")
        except Exception as e:
            print(f"Error creating zip file: {e}")

print("Both versions (installer and portable) have been created successfully.")




