import os
import shutil
import subprocess
import sys
import tempfile
import time
import tkinter as tk
import urllib.request
import zipfile
from tkinter import ttk


class UpdateGUI:
    def __init__(self, root, app_directory):
        self.root = root
        self.root.title("Tera Term UI Updater")
        self.root.configure(bg="gray")
        self.app_directory = app_directory
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.cancel_download(self.app_directory))
        style = ttk.Style(root)
        style.theme_use("default")
        style.configure("Custom.Horizontal.TProgressbar", troughcolor="white",
                        background="blue", bordercolor="black", borderwidth=1,
                        lightcolor="blue", darkcolor="blue")
        frame = ttk.Frame(root, style="TFrame", padding=(10, 10, 10, 10))
        frame.pack(pady=20, padx=10, fill="x", expand=True)
        self.progress = ttk.Progressbar(frame, style="Custom.Horizontal.TProgressbar",
                                        orient="horizontal", length=300, mode="determinate")
        self.progress.pack(fill="x", expand=True)
        label_font = ("Roboto", 12, "bold")
        self.label = ttk.Label(frame, text="Starting update...", font=label_font)
        self.label.pack(pady=10)
        self.cancel_button = ttk.Button(frame, text="Cancel", command=lambda: self.cancel_download(self.app_directory))
        self.cancel_button.pack(pady=(10, 0))
        self.cancel_requested = False

    def update_progress(self, value, text):
        self.progress["value"] = value
        self.label.config(text=text)
        self.root.update()

    def cancel_download(self, app_directory):
        self.cancel_requested = True
        self.update_progress(0, "Download cancelled...exiting")
        gui.root.after(1500, lambda: (gui.root.destroy(), restart_application(app_directory)))

    def disable_close(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def enable_close(self):
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def on_close(self):
        pass


def download_update(gui, mode, version):
    base_url = "https://github.com/Hanuwa/TeraTermUI/releases/latest"
    file_name = f"TeraTermUI-v{version}.zip" if mode == "Portable" else f"TeraTermUI_64-bit_Installer-v{version}.exe"
    download_url = f"{base_url}/download/{file_name}"
    temp_folder = os.path.join(tempfile.gettempdir(), "TeraTermUI")
    os.makedirs(temp_folder, exist_ok=True)
    file_path = os.path.join(temp_folder, file_name)
    try:
        with urllib.request.urlopen(download_url) as response:
            total_length = response.getheader("content-length")
            total_length = int(total_length) if total_length else None
            with open(file_path, "wb") as file:
                if total_length is None:
                    file.write(response.read())
                else:
                    downloaded = 0
                    last_updated_percentage = 0
                    while True:
                        data = response.read(4096)
                        if not data:
                            break
                        file.write(data)
                        downloaded += len(data)
                        current_percentage = (downloaded / total_length) * 100
                        scaled_percentage = current_percentage * 0.25
                        if scaled_percentage - last_updated_percentage >= 0.25:
                            gui.update_progress(scaled_percentage, f"Downloading Update: {int(scaled_percentage * 4)}%")
                            last_updated_percentage = scaled_percentage

        gui.update_progress(25, "Download Completed!")
        time.sleep(1)
        return file_path

    except Exception as e:
        gui.update_progress(0, f"Download failed: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return None


def has_write_permission(directory):
    try:
        testfile = tempfile.TemporaryFile(dir=directory)
        testfile.close()
        return True
    except (OSError, IOError):
        return False


def install_extract_update(gui, mode, update_db, version, downloaded_file, app_directory):
    download_dir = os.path.dirname(downloaded_file)
    temp_extract_folder = os.path.join(download_dir, f"TeraTermUI_{version}_Extraction")
    backup_folder = os.path.join(download_dir, f"TeraTermUI_{version}_Backup")
    gui.disable_close()
    gui.cancel_button.pack_forget()
    try:
        if mode == "Portable":
            if not has_write_permission(app_directory):
                raise PermissionError(f"Insufficient permissions to write to directory: {app_directory}")
            os.makedirs(temp_extract_folder, exist_ok=True)
            shutil.copytree(app_directory, backup_folder, dirs_exist_ok=True)
            with zipfile.ZipFile(downloaded_file, "r") as zip_ref:
                total_files = len(zip_ref.infolist())
                gui.update_progress(25, "Extracting update package...")
                time.sleep(1)
                processed_files = 0
                for file in zip_ref.infolist():
                    zip_ref.extract(file, temp_extract_folder)
                    processed_files += 1
                    if processed_files % 10 == 0 or processed_files == total_files:
                        gui.update_progress(25 + (processed_files / total_files) * 35,
                                            f"Extracting file {processed_files} of {total_files}...")

            gui.update_progress(60, "Adding updated files...")
            time.sleep(1)
            inner_folder = os.path.join(temp_extract_folder, "TeraTermUI")
            total_files_to_move = sum(len(files) for _, _, files in os.walk(inner_folder))
            processed_files = 0
            for root, dirs, files in os.walk(inner_folder):
                for file in files:
                    if file == "database.db" and not update_db:
                        continue
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, inner_folder)
                    dest_file = os.path.join(app_directory, rel_path)
                    if not os.path.exists(os.path.dirname(dest_file)):
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.move(src_file, dest_file)
                    processed_files += 1
                    if processed_files % 10 == 0 or processed_files == total_files_to_move:
                        percentage = 60 + (processed_files / total_files_to_move) * 30
                        gui.update_progress(percentage, f"Moving file {processed_files} of {total_files_to_move}...")

            gui.update_progress(90, "Finalizing update...")
            time.sleep(2.5)
            if os.path.exists(temp_extract_folder):
                shutil.rmtree(temp_extract_folder)
            if os.path.exists(backup_folder):
                shutil.rmtree(backup_folder)

            gui.update_progress(100, "Update completed!")

        if mode == "Installation":
            gui.update_progress(75, "Starting installer...")
            process = subprocess.Popen([downloaded_file, "/VERYSILENT"])
            time.sleep(1)
            gui.root.after(1000, lambda: check_installation_status(
                gui, process, version, downloaded_file, app_directory))

    except Exception as e:
        error_message = f"Update failed: {str(e)}"
        gui.update_progress(0, error_message)
        if os.path.exists(backup_folder) and "Insufficient permissions" not in error_message:
            shutil.rmtree(app_directory)
            shutil.copytree(backup_folder, app_directory)
        if os.path.exists(temp_extract_folder):
            shutil.rmtree(temp_extract_folder)
        if os.path.exists(backup_folder):
            shutil.rmtree(backup_folder)
        gui.cancel_button.config(text="Copy Error", command=lambda: copy_to_clipboard(gui, error_message))
        gui.cancel_button.pack(pady=(10, 0))
        return False

    finally:
        if mode == "Portable":
            gui.enable_close()

    return True


def check_installation_status(gui, process, version, downloaded_file, app_directory):
    if process.poll() is None:
        gui.update_progress(75, "Installer is running...")
        gui.root.after(1000, lambda: check_installation_status(
            gui, process, version, downloaded_file, app_directory))
    else:
        finalize_update(gui, version, downloaded_file, app_directory)


def check_update_success(app_directory, version):
    version_file_path = os.path.join(app_directory, "VERSION.txt")
    with open(version_file_path, "r") as file:
        for line in file:
            if line.startswith("Version Number: v"):
                current_version = line.strip().split("v")[-1]
                return current_version == version


def finalize_update(gui, version, downloaded_file, app_directory):
    download_dir = os.path.dirname(downloaded_file)
    update_success = check_update_success(app_directory, version)
    if update_success:
        gui.update_progress(90, "Finalizing update...")
        time.sleep(1)
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)
        gui.update_progress(100, "Update completed!")
    else:
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)
        gui.update_progress(0, "Update failed or canceled by the user")
        gui.enable_close()
    gui.root.after(1500, lambda: (gui.root.destroy(), restart_application(app_directory)))


def copy_to_clipboard(gui, text):
    gui.clipboard_clear()
    gui.clipboard_append(text)


def restart_application(app_directory):
    executable_path = os.path.join(app_directory, "TeraTermUI.exe")
    if os.path.exists(executable_path):
        subprocess.Popen(executable_path)
    sys.exit(0)


def start_update(gui):
    mode = sys.argv[1]
    version = sys.argv[2]
    update_db = sys.argv[3]
    app_directory = sys.argv[4]

    downloaded_file = download_update(gui, mode, version)
    if downloaded_file:
        update_success = install_extract_update(gui, mode, update_db, version, downloaded_file, app_directory)
        if update_success and mode == "Portable":
            gui.root.after(250, lambda: (gui.root.destroy(), restart_application(app_directory)))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(0)

    root = tk.Tk()
    width, height = 425, 225
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = int((screen_width / 2) - (width / 2))
    y = int((screen_height / 2) - (height / 2))
    root.geometry(f"{width}x{height}+{x}+{y}")
    app_directory = sys.argv[4]
    gui = UpdateGUI(root, app_directory)
    root.after(500, lambda: start_update(gui))
    root.mainloop()
