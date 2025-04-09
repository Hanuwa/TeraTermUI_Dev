import ctypes
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
import winreg

PYTHON_REQUIRED = (3, 12, 10)
MSVC_URL = "https://aka.ms/vs/17/release/vs_BuildTools.exe"
INNO_SETUP_URL = "https://jrsoftware.org/download.php/is.exe"

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(ROOT_DIR, ".venv")
VENV_SCRIPTS_DIR = os.path.join(VENV_DIR, "Scripts")
VENV_PYTHON = os.path.join(VENV_SCRIPTS_DIR, "python.exe")
VENV_PIP = os.path.join(VENV_SCRIPTS_DIR, "pip.exe")
VENV_LIB_DIR = os.path.join(VENV_DIR, "Lib", "site-packages")
CTK_PACKAGE_PATH = os.path.join(VENV_LIB_DIR, "customtkinter")
TESSERACT_DIR = os.path.join(ROOT_DIR, "Tesseract-OCR")
TESSERACT_INSTALLER = os.path.join(TESSERACT_DIR, "tesseract_setup.exe")
DIST_FOLDER = os.path.join(ROOT_DIR, "dist")
REQUIREMENTS_FILE = os.path.join(ROOT_DIR, "requirements.txt")
FILES_TO_COPY = ["database.db", "feedback.zip", "updater.exe"]

CTK_FOLDERS = {
    "windows": ["ctk_input_dialog.py", "ctk_tk.py", "ctk_toplevel.py"],
    "widgets": [
        "ctk_button.py", "ctk_checkbox.py", "ctk_combobox.py", "ctk_frame.py", "ctk_optionmenu.py",
        "ctk_progressbar.py", "ctk_radiobutton.py", "ctk_scrollable_frame.py", "ctk_scrollbar.py",
        "ctk_switch.py", "ctk_tabview.py", "ctk_textbox.py"
    ],
    "appearance_mode": ["appearance_mode_tracker.py"],
    "core_rendering": ["ctk_canvas.py", "draw_engine.py"],
    "core_widget_classes": ["ctk_base_class.py", "dropdown_menu.py"],
    "font": ["ctk_font.py"],
    "image": ["ctk_image.py"],
    "scaling": ["scaling_base_class.py", "scaling_tracker.py"],
    "theme": ["theme_manager.py"]
}

def find_python_312():
    try:
        output = subprocess.check_output(["py", "-3.12", "-c", "import sys; print(sys.executable)"], text=True).strip()
        return output if os.path.exists(output) else None
    except subprocess.CalledProcessError:
        return None

def is_admin():
    return ctypes.windll.shell32.IsUserAnAdmin()

def force_admin():
    if not is_admin():
        python_required_str = ".".join(map(str, PYTHON_REQUIRED))
        python_exe = find_python_312()
        if not python_exe:
            print(f"[ERROR] Python {python_required_str} not found")
            input("Press Enter to exit...")
            sys.exit(1)
        print(f"[INFO] Restarting as admin using {python_exe} (Python {python_required_str})...")
        time.sleep(2)
        script_path = os.path.abspath(__file__)
        cmd = f'powershell -Command "Start-Process \'{python_exe}\' -ArgumentList \'{script_path}\' -Verb RunAs"'
        subprocess.run(cmd, shell=True)
        sys.exit(0)

def check_python_version():
    major, minor, patch = sys.version_info[:3]
    if (major, minor) == (3, 12) and patch >= 10:
        print(f"[OK] Python {major}.{minor}.{patch} is compatible")
    else:
        print(f"[ERROR] Python 3.12 with patch version 10 or higher is required; found {major}.{minor}.{patch}")
        input("Press Enter to exit...")
        sys.exit(1)

def create_virtualenv():
    if os.path.exists(VENV_DIR):
        print("[INFO] Virtual environment (.venv) already exists. Exiting setup")
        input("Press Enter to exit...")
        sys.exit(0)
    print("[INFO] Creating virtual environment (.venv)...")
    subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
    print("[OK] Virtual environment is set up")

def update_pip():
    print("[INFO] Upgrading pip...")
    subprocess.run([VENV_PYTHON, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    print("[OK] Pip upgraded")

def install_dependencies():
    update_pip()
    shutil.move(REQUIREMENTS_FILE, os.path.join(VENV_SCRIPTS_DIR, "requirements.txt"))
    subprocess.run([VENV_PIP, "install", "-r", os.path.join(VENV_SCRIPTS_DIR, "requirements.txt")], check=True)

def move_ctk_files():
    if not os.path.exists(CTK_PACKAGE_PATH):
        print(f"[ERROR] CustomTkinter package not found at {CTK_PACKAGE_PATH}")
        return
    print("[INFO] Moving CustomTkinter modules...")
    for folder, files in CTK_FOLDERS.items():
        target_folder = os.path.join(CTK_PACKAGE_PATH, folder)
        os.makedirs(target_folder, exist_ok=True)
        for file in files:
            src = os.path.join("modules", file)
            dst = os.path.join(target_folder, file)
            if os.path.exists(src):
                shutil.move(src, dst)
                print(f"[OK] Moved {file} to {folder}")
            else:
                print(f"[WARNING] {file} not found in modules")
    if os.path.exists("modules"):
        shutil.rmtree("modules")

def install_inno_setup():
    reg_paths = [
        r"SOFTWARE\Jordan Russell\Inno Setup 6",
        r"SOFTWARE\WOW6432Node\Jordan Russell\Inno Setup 6"
    ]
    inno_installed = False
    for path in reg_paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
            install_loc, _ = winreg.QueryValueEx(key, "InstallLocation")
            winreg.CloseKey(key)
            if install_loc and os.path.exists(os.path.join(install_loc, "ISCC.exe")):
                inno_installed = True
                break
        except FileNotFoundError:
            continue
    inno_exe = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if inno_installed or os.path.exists(inno_exe):
        print("[OK] Inno Setup is already installed")
    else:
        print("[INFO] Installing Inno Setup...")
        inno_installer = os.path.join(ROOT_DIR, "inno_setup.exe")
        urllib.request.urlretrieve(INNO_SETUP_URL, inno_installer)
        subprocess.run([inno_installer, "/VERYSILENT", "/NORESTART"], check=True)
        os.remove(inno_installer)
        if os.path.exists(inno_exe):
            print(f"[OK] Inno Setup installed successfully at {inno_exe}")
        else:
            print("[WARNING] Inno Setup installation could not be fully verified")

def ensure_msvc_in_path(new_path):
    key = winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        0, winreg.KEY_ALL_ACCESS)
    try:
        current_path, _ = winreg.QueryValueEx(key, "Path")
        if new_path.lower() not in current_path.lower():
            new_path_value = f"{current_path};{new_path}"
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path_value)
            print(f"[OK] Added {new_path} to system PATH")
    finally:
        winreg.CloseKey(key)

def detect_msvc():
    vswhere_path = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    if os.path.exists(vswhere_path):
        try:
            output = subprocess.check_output([
                vswhere_path,
                "-latest",
                "-products", "*",
                "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property", "installationPath"
            ], text=True).strip()
            if output:
                msvc_dir = os.path.join(output, "VC", "Tools", "MSVC")
                if os.path.exists(msvc_dir):
                    for version in sorted(os.listdir(msvc_dir), reverse=True):
                        candidate = os.path.join(msvc_dir, version, "bin", "Hostx64", "x64", "cl.exe")
                        if os.path.exists(candidate):
                            return candidate
        except subprocess.CalledProcessError:
            pass

    try:
        output = subprocess.check_output(["where", "cl.exe"], text=True).strip().splitlines()
        if output:
            return output[0]
    except subprocess.CalledProcessError:
        pass

    defaults = [
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Tools\MSVC",
        r"C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC",
        r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC"
    ]
    for base in defaults:
        if os.path.exists(base):
            for root, _, files in os.walk(base):
                if "cl.exe" in files:
                    return os.path.join(root, "cl.exe")
    return None

def install_msvc():
    os_version = platform.version()
    print(f"[INFO] Detected Windows Version: {os_version}")
    if "10" in os_version:
        sdk_version = "10.0.20348.0"
        sdk_component = "Microsoft.VisualStudio.Component.Windows10SDK.20348"
    elif "11" in os_version:
        sdk_version = "10.0.26100.0"
        sdk_component = "Microsoft.VisualStudio.Component.Windows11SDK.26100"
    else:
        raise ValueError(f"Unsupported OS version: {os_version}")
    sdk_path = fr"C:\Program Files (x86)\Windows Kits\10\bin\{sdk_version}\x64"
    cl_path = detect_msvc()
    if cl_path:
        print(f"[OK] MSVC Compiler is already installed")
        ensure_msvc_in_path(sdk_path)
        return
    
    print("[INFO] Installing MSVC Compiler... (this might take a while)")
    installer_filename = "vs_build_tools.exe"
    urllib.request.urlretrieve(MSVC_URL, installer_filename)

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.run(
        [installer_filename, "--quiet", "--wait", "--norestart", 
        "--add", "Microsoft.VisualStudio.Workload.VCTools",  
        "--add", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
        "--add", sdk_component],
        check=True, startupinfo=startupinfo
    )
    os.remove(installer_filename)
    cl_path = detect_msvc()
    if cl_path:
        print(f"[OK] MSVC Compiler installed at: {cl_path}")
        ensure_msvc_in_path(sdk_path)
    else:
        print("[ERROR] MSVC Compiler installation failed to detect cl.exe.")

def copy_dist_files():
    if not os.path.exists(DIST_FOLDER):
        print(f"[ERROR] 'dist' folder not found at '{DIST_FOLDER}'")
        return
    print("[INFO] Copying files from 'dist' to root...")
    for file in FILES_TO_COPY:
        src = os.path.join(DIST_FOLDER, file)
        dst = os.path.join(ROOT_DIR, file)
        if os.path.exists(src):
            shutil.copy(src, dst)
            print(f"[OK] Copied '{file}' to root")
        else:
            print(f"[WARNING] '{file}' not found in 'dist'. Skipping")
    for extra in ["PIP_Commands.txt", "README.md"]:
        extra_path = os.path.join(ROOT_DIR, extra)
        if os.path.exists(extra_path):
            os.remove(extra_path)
    license_path = os.path.join(ROOT_DIR, "LICENSE")
    if os.path.exists(license_path):
        new_license_path = os.path.join(ROOT_DIR, "LICENSE.txt")
        os.rename(license_path, new_license_path)

def main():
    print("|-----------------------------------------------------|")
    print("|       TeraTermUI Development Environment Setup      |")
    print("|            Automated Setup Script                   |")
    print("|-----------------------------------------------------|\n")
    input("Press Enter to begin...")
    force_admin()
    check_python_version()
    create_virtualenv()
    install_dependencies()
    move_ctk_files()
    copy_dist_files()
    install_inno_setup()
    install_msvc()
    print("\n[SETUP COMPLETE] Your Dev environment is ready to use!")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
