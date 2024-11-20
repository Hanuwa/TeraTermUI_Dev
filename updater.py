import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from filelock import FileLock, Timeout
from tkinter import messagebox, ttk

try:
    import psutil
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

MAX_RETRIES = 5
RETRY_DELAY = 0.2
CHUNK_SIZE = 8192
UI_UPDATE_DELAY = 100

temp_dir = os.path.join(tempfile.gettempdir(), "TeraTermUI")
os.makedirs(temp_dir, exist_ok=True)

try:
    log_path = os.path.join(temp_dir, "updater.log")
    logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    logging.info(f"Logging initialized. Log file located at: {log_path}")
except Exception as e:
    print(f"Failed to initialize logging: {e}")
    sys.exit(1)

LOCK_FILE = os.path.join(temp_dir, "TeraTermUI_Updater.lock")
LOCK = FileLock(LOCK_FILE, timeout=1)


class UpdateGUI:
    def __init__(self, root, app_directory):
        self.root = root
        self.root.title("Tera Term UI Updater")
        self.app_directory = app_directory
        self.cancel_requested = False
        self.pause_requested = False
        self.temp_folders = set()
        self.downloaded_file = None
        self.backup_folder = None
        self.temp_extract_folder = None
        self.current_stage = "initializing"
        self.last_status_message = "Starting update..."

        try:
            self._configure_styles()
            self._create_ui_elements()
        except Exception as e:
            logging.error(f"Failed to initialize UI: {e}")
            messagebox.showerror("Error", "Failed to initialize the updater interface")
            self.root.destroy()
            sys.exit(1)

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#2E2E2E")
        style.configure("TLabel", background="#2E2E2E", foreground="white", font=("Arial", 14))
        style.configure("Custom.TButton", background="#4E4E4E", foreground="white",
                        borderwidth=0, padding=(20, 10), font=("Arial", 12))
        style.map("Custom.TButton", background=[("active", "#3E3E3E"), ("pressed", "#2E2E2E")],
                  foreground=[("active", "white"), ("pressed", "#CCCCCC")])
        style.configure("Custom.Horizontal.TProgressbar", troughcolor="#3E3E3E", bordercolor="#3E3E3E",
                        background="#1E90FF", lightcolor="#1E90FF", darkcolor="#1E90FF", thickness=25)

    def _create_ui_elements(self):
        frame = ttk.Frame(self.root, padding=(30, 45, 30, 15))
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(frame, style="Custom.Horizontal.TProgressbar", orient="horizontal", length=500,
                                        mode="determinate")
        self.progress.pack(pady=(20, 20))

        label_frame = ttk.Frame(frame)
        label_frame.pack(fill="x", pady=(10, 10))
        label_frame.grid_columnconfigure(0, weight=1)

        self.label = tk.Label(label_frame, text=self.last_status_message, wraplength=460, justify="center",
                              background="#2E2E2E", foreground="white", font=("Arial", 14), anchor="center")
        self.label.pack(fill="x", pady=10)

        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=(15, 25))

        self.pause_button = ttk.Button(button_frame, text="⏸️ Pause", command=self.toggle_pause, style="Custom.TButton")
        self.pause_button.pack(side="left", padx=10)
        self._add_button_bindings(self.pause_button)

        self.cancel_button = ttk.Button(button_frame, text="❌ Cancel", command=self.cancel_download,
                                        style="Custom.TButton")
        self.cancel_button.pack(side="left", padx=10)
        self._add_button_bindings(self.cancel_button)

        self.root.protocol("WM_DELETE_WINDOW", self.cancel_download)
        self.root.bind("<Alt-F4>", lambda e: self.cancel_download())
        self.root.bind("<Configure>", self.on_window_resize)

    def _add_button_bindings(self, button):
        button.bind("<Enter>", self.on_enter)
        button.bind("<Leave>", self.on_leave)

    def on_window_resize(self, event):
        if event.widget == self.root:
            new_wrap_length = event.width - 80
            self.label.configure(wraplength=new_wrap_length)

    def update_progress(self, value, text):
        if not self.pause_requested or self.cancel_requested:
            self.last_status_message = text

        self.progress["value"] = value
        display_text = "Update paused..." if self.pause_requested and not self.cancel_requested else text

        words = display_text.split()
        wrapped_text = " ".join(words)
        self.label.configure(text=wrapped_text)
        self.root.update_idletasks()

    def cancel_download(self):
        if self.cancel_requested:
            logging.info("Cancel already in progress, ignoring repeated request")
            return

        logging.info(f"Cancel requested during {self.current_stage} stage")
        self.cancel_requested = True
        self.pause_requested = False
        self.update_progress(0, "Cancelling update, please wait...")
        self.pause_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")

        def cleanup_task():
            cleanup_success = True
            error_messages = []
            try:
                if self.current_stage == "downloading":
                    if self.downloaded_file and os.path.exists(self.downloaded_file):
                        try:
                            os.remove(self.downloaded_file)
                            logging.info(f"Removed downloaded file: {self.downloaded_file}")
                        except Exception as e:
                            error_msg = f"Failed to remove downloaded file: {e}"
                            logging.error(error_msg)
                            error_messages.append(error_msg)
                            cleanup_success = False

                elif self.current_stage in ["extracting", "updating"]:
                    if self.backup_folder and os.path.exists(self.backup_folder):
                        try:
                            if os.path.exists(self.app_directory):
                                logging.info("Removing current application files for restoration")
                                for root, dirs, files in os.walk(self.app_directory):
                                    for file in files:
                                        try:
                                            os.remove(os.path.join(root, file))
                                        except Exception as e:
                                            logging.warning(f"Failed to remove file {file}: {e}")
                                    for dir in dirs:
                                        try:
                                            shutil.rmtree(os.path.join(root, dir))
                                        except Exception as e:
                                            logging.warning(f"Failed to remove directory {dir}: {e}")

                            logging.info("Restoring from backup")
                            shutil.copytree(self.backup_folder, self.app_directory, dirs_exist_ok=True)
                            logging.info(f"Restored from backup: {self.backup_folder}")
                        except Exception as e:
                            error_msg = f"Failed to restore from backup: {e}"
                            logging.error(error_msg)
                            error_messages.append(error_msg)
                            cleanup_success = False

                for folder in self.temp_folders:
                    if os.path.exists(folder):
                        try:
                            retries = 3
                            for attempt in range(retries):
                                try:
                                    shutil.rmtree(folder)
                                    logging.info(f"Removed temporary folder: {folder}")
                                    break
                                except Exception as e:
                                    if attempt == retries - 1:
                                        error_msg = f"Failed to remove temporary folder {folder}: {e}"
                                        logging.error(error_msg)
                                        error_messages.append(error_msg)
                                        cleanup_success = False
                                    else:
                                        time.sleep(0.5)
                        except Exception as e:
                            error_msg = f"Error during folder cleanup {folder}: {e}"
                            logging.error(error_msg)
                            error_messages.append(error_msg)
                            cleanup_success = False

                updater_dir = os.path.dirname(self.temp_extract_folder) if self.temp_extract_folder else None
                if updater_dir and os.path.exists(updater_dir):
                    try:
                        success, error = retry_remove_directory(updater_dir)
                        if success:
                            logging.info(f"Successfully removed updater directory: {updater_dir}")
                        else:
                            error_msg = f"Failed to remove updater directory: {error}"
                            logging.error(error_msg)
                            error_messages.append(error_msg)
                            cleanup_success = False
                    except Exception as e:
                        error_msg = f"Error cleaning up updater directory: {e}"
                        logging.error(error_msg)
                        error_messages.append(error_msg)
                        cleanup_success = False

                try:
                    LOCK.release()
                    logging.info("Released file lock")
                except Exception as e:
                    logging.warning(f"Error releasing file lock: {e}")

                logging.info(f"Update cancelled during {self.current_stage} stage. Cleanup completed")

                self.root.after(0, lambda: self.finish_cancellation(error_messages if not cleanup_success else None))

            except Exception as e:
                logging.error(f"Error during cancellation cleanup: {e}")
                self.root.after(0, lambda: self.finish_cancellation([str(e)]))

        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()

    def finish_cancellation(self, error_messages=None):
        try:
            if error_messages:
                self.update_progress(0, "Cleanup completed with errors")
                detailed_message = "The following errors occurred during cleanup:\n\n" + \
                                   "\n".join(f"- {msg}" for msg in error_messages) + \
                                   "\n\nCheck the logs for details"
                messagebox.showerror("Cleanup Errors", detailed_message)
                gui.set_failure_state()
            else:
                self.update_progress(0, "Update cancelled successfully")
                messagebox.showinfo(
                    "Update Cancelled",
                    "Update has been cancelled and all changes have been reverted successfully")
                gui.set_failure_state()

            self.root.after(500, lambda: self.cleanup_and_restart())

        except Exception as e:
            logging.error(f"Error during cancellation finalization: {e}")
            self.root.destroy()
            restart_application(self.app_directory)

    def cleanup_and_restart(self):
        try:
            self.root.destroy()
            restart_application(self.app_directory)
        except Exception as e:
            logging.error(f"Error during final cleanup and restart: {e}")
            sys.exit(1)

    def set_failure_state(self):
        self.cancel_button.configure(command=self.exit_updater)
        self.root.protocol("WM_DELETE_WINDOW", self.exit_updater)
        self.root.unbind("<Alt-F4>")
        self.root.bind("<Alt-F4>", lambda e: self.exit_updater())
        self.pause_button.configure(state="disabled")
        logging.info("Updater GUI has been set to failure state. Buttons reconfigured to exit")

    def exit_updater(self):
        logging.info("Exiting updater application")
        self.root.destroy()
        sys.exit(0)

    def on_enter(self, e):
        if e.widget["state"] != "disabled":
            e.widget.configure(cursor="hand2")

    def on_leave(self, e):
        if e.widget["state"] != "disabled":
            e.widget.configure(cursor="")

    def toggle_pause(self):
        if self.cancel_requested:
            return

        self.pause_requested = not self.pause_requested
        if self.pause_requested:
            self.last_status_message = self.label.cget("text")
            self.pause_button.configure(text="▶️ Resume")
            self.update_progress(self.progress["value"], "Update paused...")
        else:
            self.pause_button.configure(text="⏸️ Pause")
            self.update_progress(self.progress["value"], "Resuming update...")
            self.root.after(1000, lambda: self.update_progress(self.progress["value"], self.last_status_message))

def parse_arguments():
    parser = argparse.ArgumentParser(description="Tera Term UI Updater")
    parser.add_argument("mode", choices=["Portable", "Installation"], help="Update mode")
    parser.add_argument("version", help="Version number to update to")
    parser.add_argument("update_db", type=lambda x: x.lower() == "true", help="Whether to update the database")
    parser.add_argument("app_directory", help="Application directory path")

    try:
        args = parser.parse_args()
        if not os.path.exists(args.app_directory):
            parser.error(f"Application directory does not exist: {args.app_directory}")
        if not re.match(r"^\d+\.\d+\.\d+$", args.version):
            parser.error(f"Invalid version format: {args.version}. Expected format: X.Y.Z")
        return args
    except Exception as e:
        logging.error(f"Argument parsing failed: {e}")
        sys.exit(1)

def retry_remove_directory(directory, max_attempts=MAX_RETRIES, delay=RETRY_DELAY):
    for attempt in range(max_attempts):
        try:
            if os.path.exists(directory):
                if not os.listdir(directory):
                    os.rmdir(directory)
                    logging.info(f"Removed empty directory on attempt {attempt + 1}: {directory}")
                    return True, None
                else:
                    for root, dirs, files in os.walk(directory, topdown=False):
                        for name in files:
                            try:
                                os.remove(os.path.join(root, name))
                            except Exception as e:
                                logging.warning(f"Failed to remove file {name}: {e}")
                        for name in dirs:
                            try:
                                os.rmdir(os.path.join(root, name))
                            except Exception as e:
                                logging.warning(f"Failed to remove directory {name}: {e}")
            else:
                return True, None
        except Exception as e:
            if attempt == max_attempts - 1:
                return False, str(e)
            time.sleep(delay * (attempt + 1))
    return False, "Max attempts reached"

def has_write_permission(directory):
    if not os.path.exists(directory):
        logging.error(f"Directory does not exist: {directory}")
        return False

    test_file = os.path.join(directory, ".write_test")
    test_dir = os.path.join(directory, ".write_test_dir")

    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.rename(test_file, test_file + "_renamed")
        os.remove(test_file + "_renamed")
        os.makedirs(test_dir, exist_ok=True)
        os.rmdir(test_dir)
        logging.info(f"Write permission check passed for directory: {directory}")
        return True
    except Exception as e:
        logging.warning(f"No write permission for directory: {directory}. Error: {e}")
        return False

def is_application_running(app_name):
    try:
        for proc in psutil.process_iter(["name", "exe", "cmdline"]):
            try:
                if proc.info["name"].lower() == app_name.lower():
                    return True
                if proc.info["exe"] and os.path.basename(proc.info["exe"]).lower() == app_name.lower():
                    return True
                if proc.info["cmdline"] and any(app_name.lower() in cmd.lower() for cmd in proc.info["cmdline"]):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False
    except Exception as e:
        logging.error(f"Error checking if application is running: {e}")
        return False

def has_enough_disk_space(required_space, directory):
    try:
        required_space = int(required_space * 1.1)
        total, used, free = shutil.disk_usage(directory)
        logging.info(f"Disk space check - Directory: {directory}")
        logging.info(
            f"Total: {total / 1024 / 1024:.2f}MB, Used: {used / 1024 / 1024:.2f}MB, Free: {free / 1024 / 1024:.2f}MB")
        logging.info(f"Required (with margin): {required_space / 1024 / 1024:.2f}MB")

        return free >= required_space
    except Exception as e:
        logging.error(f"Disk space check failed: {e}")
        return False

def start_update(gui, args):
    def update_task():
        try:
            if not has_write_permission(args.app_directory):
                raise PermissionError("Insufficient permissions to write to the application directory")

            try:
                LOCK.acquire(timeout=5)
            except Timeout:
                gui.update_progress(0, "Another update is in progress")
                logging.error("Another update is in progress (lock acquisition failed)")
                gui.set_failure_state()
                return

            if is_application_running("TeraTermUI.exe"):
                LOCK.release()
                gui.update_progress(0, "Please close TeraTermUI before updating")
                logging.warning("Application is running. Update cancelled")
                messagebox.showerror(
                    "Application Running",
                    "Please close TeraTermUI before updating.\n\nThe update will now exit")
                gui.set_failure_state()
                return

            gui.update_progress(5, "Fetching release information...")
            checksum_info = fetch_checksums_and_urls(args.version)
            if not checksum_info:
                LOCK.release()
                gui.update_progress(0, "Failed to fetch release information")
                logging.error("Failed to fetch release information")
                messagebox.showerror(
                    "Update Failed",
                    "Failed to fetch release information.\nPlease check your internet connection and try again")
                gui.set_failure_state()
                return

            gui.update_progress(10, "Starting download...")
            downloaded_file = download_update(gui, args.mode, checksum_info)

            if downloaded_file:
                gui.downloaded_file = downloaded_file
                update_success = install_extract_update(gui, args.mode, args.update_db, args.version,
                                                        downloaded_file, args.app_directory)

                if args.mode == "Portable":
                    if not update_success:
                        if gui.cancel_requested:
                            logging.info("Update failed because it was cancelled by user")
                        else:
                            messagebox.showerror(
                                "Update Failed",
                                "The update failed. Please check the logs for more information")
                            gui.set_failure_state()
                    else:
                        gui.root.after(250,lambda: (gui.root.destroy(), restart_application(args.app_directory)))

            try:
                LOCK.release()
            except:
                pass

        except Exception as e:
            try:
                LOCK.release()
            except:
                pass

            error_msg = str(e)
            logging.error(f"Update failed: {error_msg}")
            gui.update_progress(0, f"Update failed: {error_msg}")

            if "network" in error_msg.lower():
                messagebox.showerror(
                    "Network Error",
                    "Failed to connect to the update server.\nPlease check your internet connection and try again")
            elif "permission" in error_msg.lower():
                messagebox.showerror(
                    "Permission Error",
                    "Insufficient permissions to perform the update.\nPlease run the updater with administrative privileges")
            else:
                messagebox.showerror(
                    "Update Failed",
                    f"The update failed:\n\n{error_msg}\n\nPlease check the logs for more information")

            gui.set_failure_state()

    update_thread = threading.Thread(target=update_task, daemon=True)
    update_thread.start()

def verify_checksum(file_path, expected_checksum):
    logging.info(f"Verifying checksum for file: {file_path}")

    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return False

    try:
        sha256_hash = hashlib.sha256()
        total_size = os.path.getsize(file_path)
        processed_size = 0

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                sha256_hash.update(chunk)
                processed_size += len(chunk)
                progress = (processed_size / total_size) * 100
                if progress % 10 == 0:
                    logging.info(f"Checksum verification progress: {progress:.1f}%")

        calculated_checksum = sha256_hash.hexdigest()
        if calculated_checksum == expected_checksum:
            logging.info("Checksum verification passed")
            return True
        else:
            logging.error(
                f"Checksum verification failed. Expected: {expected_checksum}, Calculated: {calculated_checksum}")
            return False
    except Exception as e:
        logging.error(f"Checksum verification failed with error: {e}")
        return False

def fetch_checksums_and_urls(version):
    logging.info(f"Fetching checksums and URLs for version: {version}")
    repo_api_url = f"https://api.github.com/repos/Hanuwa/TeraTermUI/releases/tags/v{version}"

    try:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TeraTermUI-Updater"
        }
        request = urllib.request.Request(repo_api_url, headers=headers)

        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                logging.error(f"GitHub API returned status code: {response.status}")
                return None

            release_info = json.loads(response.read().decode())

            if not release_info:
                logging.error("Empty response from GitHub API")
                return None

            description = release_info.get("body", "")
            assets = release_info.get("assets", [])

            if not description or not assets:
                logging.error("Missing required release information")
                return None

            result = {
                "portable": {"checksum": None, "url": None},
                "installer": {"checksum": None, "url": None}
            }

            patterns = {
                "portable": r"1\.\s*Portable Version \(Zip File\)\s*-\s*\*\*Checksum\*\*\s*:\s*```([a-fA-F0-9]{64})```",
                "installer": r"2\.\s*Installation File \(64-Bit\)\s*-\s*\*\*Checksum\*\*\s*:\s*```([a-fA-F0-9]{64})```"
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, description)
                if match:
                    result[key]["checksum"] = match.group(1)
                    logging.info(f"Found {key} checksum: {result[key]['checksum']}")
                else:
                    logging.error(f"{key.capitalize()} checksum not found")

            for asset in assets:
                asset_name = asset.get("name", "")
                if not asset_name:
                    continue

                if asset_name == f"TeraTermUI-v{version}.zip":
                    result["portable"]["url"] = asset.get("browser_download_url")
                    logging.info(f"Found portable download URL: {result['portable']['url']}")
                elif asset_name == f"TeraTermUI_64-bit_Installer-v{version}.exe":
                    result["installer"]["url"] = asset.get("browser_download_url")
                    logging.info(f"Found installer download URL: {result['installer']['url']}")

            for key in ["portable", "installer"]:
                if not result[key]["checksum"] or not result[key]["url"]:
                    logging.error(f"Missing {key} information")
                    return None

            return result

    except urllib.error.HTTPError as e:
        logging.error(f"HTTP error occurred: {e.code} - {e.reason}")
        return None
    except urllib.error.URLError as e:
        logging.error(f"URL error occurred: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching release info: {e}")
        return None

def download_update(gui, mode, checksum_info):
    gui.current_stage = "downloading"
    logging.info(f"Starting download for mode: {mode}")

    if mode not in ["Portable", "Installation"]:
        gui.update_progress(0, "Invalid update mode specified")
        logging.error(f"Invalid mode: {mode}")
        return None

    mode_key = "portable" if mode == "Portable" else "installer"
    expected_checksum = checksum_info[mode_key]["checksum"]
    download_url = checksum_info[mode_key]["url"]

    if not expected_checksum or not download_url:
        gui.update_progress(0, f"Missing download information for {mode} version")
        logging.error(f"Missing download information for {mode} version")
        return None

    temp_folder = os.path.join(tempfile.gettempdir(), "TeraTermUI_Updater")
    os.makedirs(temp_folder, exist_ok=True)
    file_name = os.path.basename(download_url)
    file_path = os.path.join(temp_folder, file_name)

    try:
        headers = {"User-Agent": "TeraTermUI-Updater"}
        request = urllib.request.Request(download_url, headers=headers)

        with urllib.request.urlopen(request, timeout=30) as response:
            total_length = response.getheader("content-length")
            if total_length is None:
                gui.update_progress(0, "Unable to determine file size")
                logging.error("Content-Length header missing")
                return None

            total_length = int(total_length)
            required_space = total_length * 2

            if not has_enough_disk_space(required_space, temp_folder):
                gui.update_progress(0, "Insufficient disk space for download")
                logging.error(f"Insufficient disk space. Required: {required_space / 1024 / 1024:.2f}MB")
                return None

            with open(file_path, "wb") as file:
                downloaded = 0
                last_update_time = time.time()
                downloaded_since_last_update = 0
                last_progress_update = 0

                while not gui.cancel_requested:
                    if gui.pause_requested:
                        time.sleep(0.1)
                        last_update_time = time.time()
                        continue

                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    file.write(chunk)
                    downloaded += len(chunk)
                    downloaded_since_last_update += len(chunk)

                    current_time = time.time()
                    time_delta = current_time - last_update_time

                    if time_delta >= 0.1:
                        current_percentage = (downloaded / total_length) * 100

                        if abs(current_percentage - last_progress_update) >= 1:
                            speed = downloaded_since_last_update / time_delta
                            speed_text = f"{speed / 1024 / 1024:.1f} MB/s"
                            remaining_bytes = total_length - downloaded

                            if speed > 0:
                                remaining_seconds = remaining_bytes / speed
                                if remaining_seconds < 60:
                                    time_text = f"{remaining_seconds:.0f}s remaining"
                                else:
                                    time_text = f"{remaining_seconds / 60:.1f}m remaining"
                            else:
                                time_text = "calculating..."

                            progress_text = (f"Downloading Update: {int(current_percentage)}% "
                                             f"({speed_text}, {time_text})")
                            gui.update_progress(current_percentage * 0.5, progress_text)

                            last_progress_update = current_percentage
                            last_update_time = current_time
                            downloaded_since_last_update = 0

                            if int(current_percentage) % 10 == 0:
                                logging.info(f"Download progress: {int(current_percentage)}% ({speed_text})")

        if gui.cancel_requested:
            if os.path.exists(file_path):
                os.remove(file_path)
            logging.info("Download cancelled by user")
            return None

        if downloaded != total_length:
            raise ValueError(f"Download incomplete. Expected {total_length} bytes, got {downloaded} bytes")

        logging.info(f"Download completed: {file_path}")

        gui.update_progress(50, "Verifying download...")
        if not verify_checksum(file_path, expected_checksum):
            raise ValueError("Checksum verification failed")

        gui.update_progress(50, "Download completed and verified!")
        return file_path

    except urllib.error.HTTPError as e:
        error_msg = f"HTTP error occurred: {e.code} - {e.reason}"
        logging.error(error_msg)
        gui.update_progress(0, error_msg)
    except urllib.error.URLError as e:
        error_msg = f"Network error: {e.reason}"
        logging.error(error_msg)
        gui.update_progress(0, error_msg)
    except Exception as e:
        error_msg = f"Download failed: {str(e)}"
        logging.error(error_msg)
        gui.update_progress(0, error_msg)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logging.info(f"Removed incomplete downloaded file: {file_path}")
        except Exception as cleanup_error:
            logging.error(f"Failed to remove incomplete file: {cleanup_error}")

    return None


def install_extract_update(gui, mode, update_db, version, downloaded_file, app_directory):
    if gui.cancel_requested:
        logging.info("Update cancelled by user during installation")
        return False

    logging.info(f"Starting installation/extraction for mode: {mode}")
    download_dir = os.path.join(tempfile.gettempdir(), "TeraTermUI_Updater")
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    gui.temp_extract_folder = os.path.join(download_dir, f"TeraTermUI_{version}_Extraction_{timestamp}")
    backup_folder = os.path.join(tempfile.gettempdir(), f"TeraTermUI_Backup_{timestamp}")

    gui.temp_folders.update({download_dir, gui.temp_extract_folder, backup_folder})
    gui.backup_folder = backup_folder

    try:
        if mode == "Portable":
            os.makedirs(gui.temp_extract_folder, exist_ok=True)
            logging.info(f"Created temporary extraction folder: {gui.temp_extract_folder}")

            try:
                gui.current_stage = "extracting"
                gui.update_progress(50, "Preparing extraction...")

                with zipfile.ZipFile(downloaded_file, "r") as zip_ref:
                    namelist = zip_ref.namelist()
                    if not namelist:
                        logging.error("Zip file is empty")
                        return False

                    strip_prefix = ""
                    if namelist[0].startswith("TeraTermUI/"):
                        strip_prefix = "TeraTermUI/"

                    total_size = sum(file.file_size for file in zip_ref.filelist)
                    extracted_size = 0
                    for file in zip_ref.infolist():
                        if gui.cancel_requested:
                            logging.info("Update cancelled during extraction")
                            return False

                        while gui.pause_requested and not gui.cancel_requested:
                            time.sleep(0.1)
                            continue

                        if strip_prefix and file.filename.startswith(strip_prefix):
                            extract_name = file.filename[len(strip_prefix):]
                        else:
                            extract_name = file.filename

                        if extract_name:
                            zip_ref.extract(file, gui.temp_extract_folder)
                            if strip_prefix:
                                src = os.path.join(gui.temp_extract_folder, file.filename)
                                dst = os.path.join(gui.temp_extract_folder, extract_name)
                                os.makedirs(os.path.dirname(dst), exist_ok=True)
                                if os.path.exists(src):
                                    shutil.move(src, dst)

                            extracted_size += file.file_size
                            progress = (extracted_size / total_size) * 100
                            current_progress = 50 + (progress * 0.25)
                            gui.update_progress(current_progress, f"Extracting files: {int(progress)}%")

                    nested_dir = os.path.join(gui.temp_extract_folder, "TeraTermUI")
                    if os.path.exists(nested_dir) and not os.listdir(nested_dir):
                        os.rmdir(nested_dir)
                        logging.info(f"Removed empty nested directory: {nested_dir}")

                logging.info(f"Extraction completed successfully. Files extracted to: {gui.temp_extract_folder}")
                logging.info(f"Total files extracted: {len(namelist)}")
                logging.info(f"Total size extracted: {total_size / 1024 / 1024:.2f} MB")

            except Exception as e:
                logging.error(f"Extraction failed: {e}")
                return False

            if gui.cancel_requested:
                return False

            logging.info("Starting backup creation")
            total_size = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, dn, filenames in os.walk(app_directory)
                for f in filenames)

            if not has_enough_disk_space(total_size * 2, os.path.dirname(backup_folder)):
                gui.update_progress(0, "Insufficient disk space for backup")
                logging.error("Insufficient disk space for backup")
                return False

            try:
                shutil.copytree(app_directory, backup_folder)
                logging.info(f"Backup created at: {backup_folder}")
            except Exception as e:
                logging.error(f"Backup creation failed: {e}")
                return False

            gui.current_stage = "updating"
            gui.update_progress(75, "Updating files...")

            try:
                removed_files = 0
                for root, _, files in os.walk(app_directory):
                    for file in files:
                        if gui.cancel_requested:
                            logging.info("Update cancelled during file removal")
                            return False

                        while gui.pause_requested and not gui.cancel_requested:
                            time.sleep(0.1)
                            continue

                        if file == "database.db" and not update_db:
                            logging.info(f"Skipping database file: {file}")
                            continue

                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                            removed_files += 1
                        except Exception as e:
                            logging.error(f"Failed to remove file {file_path}: {e}")
                            return False

                logging.info(f"Total files removed: {removed_files}")

                total_files = sum(len(files) for _, _, files in os.walk(gui.temp_extract_folder))
                processed_files = 0
                updated_files = 0

                for root, _, files in os.walk(gui.temp_extract_folder):
                    for file in files:
                        if gui.cancel_requested:
                            logging.info("Update cancelled during file copying")
                            return False

                        while gui.pause_requested and not gui.cancel_requested:
                            time.sleep(0.1)
                            continue

                        if file == "database.db" and not update_db:
                            logging.info(f"Skipping database file update: {file}")
                            continue

                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, gui.temp_extract_folder)
                        dest_file = os.path.join(app_directory, rel_path)

                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        shutil.copy2(src_file, dest_file)
                        updated_files += 1

                        processed_files += 1
                        progress = (processed_files / total_files) * 100
                        current_progress = 75 + (progress * 0.2)
                        gui.update_progress(current_progress, f"Updating files: {int(progress)}%")

                logging.info(f"Total files updated: {updated_files}")

            except Exception as update_error:
                logging.error(f"Error during file replacement: {update_error}")
                try:
                    restore_from_backup(app_directory, backup_folder)
                except Exception as rollback_error:
                    logging.error(f"Rollback failed: {rollback_error}")
                return False

            if not gui.cancel_requested:
                logging.info("Update completed, starting cleanup")
                gui.update_progress(95, "Finalizing update...")
                gui.current_stage = "completed"

                cleanup_success = cleanup_update_files(gui)
                if not cleanup_success:
                    logging.warning("Cleanup completed with some warnings")

                gui.update_progress(100, "Update completed successfully!")
                logging.info("Update completed successfully")
                return True

            return False

        elif mode == "Installation":
            return handle_installation_mode(gui, downloaded_file, version, app_directory)

    except Exception as e:
        logging.error(f"Update failed: {e}")
        gui.update_progress(0, f"Update failed: {str(e)}")
        return False

def check_installation_status(gui, process, version, downloaded_file, app_directory, mode):
    gui.pause_button.configure(state="disabled")
    gui.cancel_button.configure(state="disabled")
    try:
        if process.poll() is None:
            if gui.cancel_requested:
                try:
                    process.terminate()
                    logging.info("Installation cancelled by user")
                    gui.update_progress(0, "Installation cancelled")
                    messagebox.showinfo("Installation Cancelled", "Installation was cancelled by user")
                    gui.root.after(1000, gui.root.destroy)
                    return
                except Exception as e:
                    logging.error(f"Error terminating installer process: {e}")

            if not gui.pause_requested:
                current_time = time.time()
                if not hasattr(gui, "last_progress_update") or current_time - gui.last_progress_update >= 3:
                    gui.update_progress(80,
                        "Installing... Please follow the installer prompts. Do not close this window")
                    gui.last_progress_update = current_time

            gui.root.after(1000, lambda: check_installation_status(
                gui, process, version,downloaded_file, app_directory, mode))
            return

        exit_code = process.returncode
        if exit_code != 0:
            if exit_code in [1602, 1603]:
                logging.info(f"Installation cancelled by user (exit code: {exit_code})")
                gui.update_progress(0, "Installation cancelled")
                messagebox.showinfo(
                    "Installation Cancelled",
                    "Installation was cancelled by user")
            else:
                logging.error(f"Installer exited with code {exit_code}")
                gui.update_progress(0, "Installation failed")
                messagebox.showerror(
                    "Installation Failed",
                    f"The installer encountered an error (exit code: {exit_code}).\nPlease try again")

            gui.set_failure_state()
            cleanup_installer_files(downloaded_file)
            gui.root.after(1000, lambda: (gui.root.destroy(), restart_application(app_directory)))
            return

        logging.info("Installer process completed successfully")
        gui.root.after( 2000, lambda: verify_and_finalize_installation(
            gui, version, downloaded_file, app_directory))

    except Exception as e:
        logging.error(f"Error monitoring installation: {e}")
        gui.update_progress(0, "Installation monitoring failed")
        messagebox.showerror(
            "Error",
            f"Failed to monitor installation:\n\n{str(e)}")
        gui.set_failure_state()
        cleanup_installer_files(downloaded_file)
        gui.root.after(1000, lambda: (gui.root.destroy(), restart_application(app_directory)))

def cleanup_installer_files(downloaded_file):
    try:
        if downloaded_file and os.path.exists(downloaded_file):
            os.remove(downloaded_file)
            logging.info(f"Removed installer file: {downloaded_file}")

        parent_dir = os.path.dirname(downloaded_file)
        if os.path.exists(parent_dir) and not os.listdir(parent_dir):
            os.rmdir(parent_dir)
            logging.info(f"Removed empty parent directory: {parent_dir}")

    except Exception as e:
        logging.error(f"Error cleaning up installer files: {e}")

def handle_installation_mode(gui, downloaded_file, version, app_directory):
    try:
        gui.update_progress(60, "Preparing to start installer...")
        logging.info(f"Starting installer from: {downloaded_file}")

        gui.pause_button.configure(state="disabled")
        gui.cancel_button.configure(state="disabled")

        messagebox.showinfo("Installer",
                            "The installer will now start. Please note:\n\n"
                            "1. Administrative privileges may be required\n"
                            "2. Follow the installer prompts\n"
                            "3. Do not close this update window")

        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        process = subprocess.Popen(
            [downloaded_file],
            shell=True,
            startupinfo=startupinfo
        )

        gui.root.after(1000, lambda: check_installation_status(
            gui, process, version, downloaded_file, app_directory, "Installation"))

        return True

    except Exception as e:
        logging.error(f"Failed to start installer: {e}")
        gui.update_progress(0, f"Failed to start installer: {str(e)}")
        messagebox.showerror("Error", f"Failed to start installer: {str(e)}")
        gui.set_failure_state()
        return False

def cleanup_update_files(gui):
    success = True

    try:
        if gui.temp_extract_folder and os.path.exists(gui.temp_extract_folder):
            shutil.rmtree(gui.temp_extract_folder)
            logging.info(f"Removed temporary extraction folder: {gui.temp_extract_folder}")
        if gui.backup_folder and os.path.exists(gui.backup_folder):
            shutil.rmtree(gui.backup_folder)
            logging.info(f"Removed backup folder: {gui.backup_folder}")
        if gui.downloaded_file and os.path.exists(gui.downloaded_file):
            os.remove(gui.downloaded_file)
            logging.info(f"Removed downloaded file: {gui.downloaded_file}")

        for folder in gui.temp_folders:
            if os.path.exists(folder):
                shutil.rmtree(folder)
                logging.info(f"Removed temporary folder: {folder}")

        updater_dir = os.path.dirname(gui.temp_extract_folder) if gui.temp_extract_folder else None
        if updater_dir and os.path.exists(updater_dir):
            success, error = retry_remove_directory(updater_dir)
            if success:
                logging.info(f"Removed updater directory: {updater_dir}")
            else:
                logging.warning(f"Could not remove updater directory: {error}")
                success = False

    except Exception as e:
        logging.error(f"Error during cleanup: {e}")
        success = False

    return success

def restore_from_backup(app_directory, backup_folder):
    if not backup_folder or not os.path.exists(backup_folder):
        logging.error("Backup folder not found")
        raise ValueError("Backup folder not found")

    try:
        for root, dirs, files in os.walk(app_directory):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                shutil.rmtree(os.path.join(root, dir))

        shutil.copytree(backup_folder, app_directory, dirs_exist_ok=True)
        logging.info(f"Successfully restored from backup: {backup_folder}")

    except Exception as e:
        logging.error(f"Failed to restore from backup: {e}")
        raise

def check_update_success(app_directory, version):
    logging.info(f"Performing update verification for version {version}")

    required_files = ["TeraTermUI.exe", "VERSION.txt",]

    for item in required_files:
        path = os.path.join(app_directory, item)
        if not os.path.exists(path):
            logging.error(f"Required item not found: {item}")
            return False

    exe_path = os.path.join(app_directory, "TeraTermUI.exe")
    try:
        if not os.path.getsize(exe_path) > 0:
            logging.error("TeraTermUI.exe appears to be empty")
            return False
    except Exception as e:
        logging.error(f"Error checking executable: {e}")
        return False

    version_file_path = os.path.join(app_directory, "VERSION.txt")
    try:
        with open(version_file_path, "r", encoding="utf-8") as file:
            content = file.read()
            version_pattern = rf"Version Number: v{re.escape(version)}"
            if not re.search(version_pattern, content):
                logging.error(f"Version mismatch in VERSION.txt. Expected v{version}")
                return False
            logging.info(f"Version verification successful: v{version}")
    except Exception as e:
        logging.error(f"Error reading VERSION.txt: {e}")
        return False

    logging.info("Update verification completed successfully")
    return True

def verify_and_finalize_installation(gui, version, downloaded_file, app_directory):
    logging.info("Starting installation verification")
    gui.update_progress(90, "Verifying installation...")

    try:
        executable_path = os.path.join(app_directory, "TeraTermUI.exe")
        if not os.path.exists(executable_path):
            raise FileNotFoundError(f"Executable not found at: {executable_path}")

        if not check_update_success(app_directory, version):
            raise ValueError("Installation verification failed - version mismatch")

        cleanup_successful = cleanup_installer(downloaded_file)
        if not cleanup_successful:
            logging.warning("Could not clean up installer file completely")

        logging.info("Installation completed and verified successfully")
        gui.current_stage = "completed"
        gui.update_progress(100, "Installation completed successfully!")

        messagebox.showinfo(
            "Installation Complete",
            "Installation completed successfully!\n\nThe application will restart automatically")
        gui.root.after(1500, lambda: finalize_and_restart(gui, app_directory))

    except Exception as e:
        error_msg = f"Installation verification failed: {str(e)}"
        logging.error(error_msg)
        gui.update_progress(0, "Installation verification failed")
        messagebox.showerror("Installation Failed", error_msg)
        gui.set_failure_state()
        gui.root.after(1000, gui.root.destroy)

def cleanup_installer(installer_path):
    max_attempts = 3
    delay = 1.0

    for attempt in range(max_attempts):
        try:
            if os.path.exists(installer_path):
                os.remove(installer_path)
                logging.info(f"Installer file removed: {installer_path}")
                return True
        except Exception as e:
            logging.warning(f"Cleanup attempt {attempt + 1} failed: {e}")
            if attempt < max_attempts - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return False
    return True

def finalize_and_restart(gui, app_directory):
    try:
        try:
            LOCK.release()
        except:
            pass

        gui.root.destroy()
        restart_application(app_directory)

    except Exception as e:
        logging.error(f"Error during finalization: {e}")
        try:
            gui.root.destroy()
        except:
            pass
        sys.exit(1)

def restart_application(app_directory):
    executable_path = os.path.join(app_directory, "TeraTermUI.exe")

    if not os.path.exists(executable_path):
        error_msg = f"Executable not found at: {executable_path}"
        logging.error(error_msg)
        messagebox.showerror(
            "Error",
            f"{error_msg}\nPlease start the application manually")
        sys.exit(1)

    try:
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        subprocess.Popen([executable_path], shell=True, startupinfo=startupinfo)
        logging.info("Application restart initiated successfully")

    except Exception as e:
        error_msg = f"Failed to restart application: {str(e)}"
        logging.error(error_msg)
        messagebox.showerror(
            "Error",
            f"{error_msg}\nPlease start the application manually")

    finally:
        logging.info("Updater process completing")
        sys.exit(0)


if __name__ == "__main__":
    try:
        args = parse_arguments()
        app_directory = args.app_directory
        logging.info(f"Updater started with arguments: {args}")

        root = tk.Tk()

        try:
            icon_path = os.path.join(app_directory, "images", "updater.ico")
            if os.path.exists(icon_path):
                root.iconbitmap(icon_path)
                logging.info("Successfully set window icon")
            else:
                logging.warning(f"Icon file not found at: {icon_path}")
        except Exception as icon_error:
            logging.error(f"Failed to set window icon: {icon_error}")

        width, height = 600, 300
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        root.geometry(f"{width}x{height}+{x}+{y}")
        root.minsize(width, height)
        root.resizable(True, True)
        root.title("Tera Term UI Updater")
        gui = UpdateGUI(root, app_directory)

        root.after(500, start_update, gui, args)
        root.mainloop()
    except Exception as e:
        logging.critical(f"Unhandled exception in main: {e}")
        messagebox.showerror(
            "Critical Error",
            f"An unexpected error occurred:\n\n{str(e)}\n\nPlease check the logs for details")
        sys.exit(1)
        
