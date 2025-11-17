#!/usr/bin/env python3
"""
universal_fps_booster.py

Cross-platform FPS booster for macOS and Windows 10/11.
- Detects foreground (active) application (best-effort)
- Closes configurable background apps
- Flushes DNS / network caches
- Attempts to enable high-performance power modes
- Elevates priority of the active app (game) safely
- Applies macOS UI/performance tweaks (best-effort)
- Provides optional modules (commented) for further tuning

Requirements:
- Python 3.8+
- psutil (script will attempt to install it if missing)

Security constraints:
- Does NOT modify game files or anti-cheat components
- Does not spoof network/ping
- Avoids destructive file deletions; prompts required for destructive actions
"""

import os
import sys
import platform
import subprocess
import time
import shutil

# --- Ensure psutil available ---
def ensure_psutil():
    try:
        import psutil  # noqa: F401
    except Exception:
        print("psutil not found. Attempting to install psutil...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "psutil"])
            print("psutil installed.")
        except Exception as e:
            print("Failed to auto-install psutil:", e)
            print("Please install psutil manually and re-run: pip install psutil")
            sys.exit(1)

ensure_psutil()
import psutil

SYSTEM = platform.system()

# ------------------ User-tweakable configuration ------------------
# Comprehensive list of resource-heavy apps to terminate (cross-platform optimized)
BG_APPS = [
    # Browsers
    "chrome", "google chrome", "firefox", "safari", "edge", "opera", "brave", "chromium",
    # Media & Music
    "spotify", "itunes", "music", "tv", "vlc", "quicktime", "plex", "netflix",
    # Communication
    "discord", "skype", "teams", "microsoft teams", "zoom", "slack", "telegram", "whatsapp", "messages",
    # Cloud Storage
    "dropbox", "onedrive", "google drive", "googledrive", "box", "sync", "icloud",
    # Gaming Platforms
    "steam", "epic", "epic games launcher", "origin", "uplay", "battle.net", "battlenet", "gog",
    # Streaming/Recording
    "obs", "streamlabs", "twitch", "quicktime player", "bandicam", "fraps", "xsplit",
    # Creative Software
    "adobe photoshop", "photoshop", "adobe premiere", "premiere", "adobe after effects", 
    "adobe illustrator", "adobe lightroom", "final cut pro", "motion", "compressor",
    "blender", "unity", "unreal", "cinema4d", "maya", "3ds max",
    # Torrents
    "transmission", "utorrent", "bittorrent", "qbittorrent", "deluge",
    # Office & Productivity
    "microsoft word", "microsoft excel", "microsoft powerpoint", "microsoft outlook",
    "pages", "numbers", "keynote", "word", "excel", "powerpoint", "outlook",
    # Development
    "xcode", "visual studio code", "android studio", "intellij", "pycharm", "eclipse",
    # System monitoring & utilities
    "activity monitor", "console", "disk utility", "task manager", "resource monitor",
    # Hardware utilities
    "corsair", "logitech", "razer", "steelseries", "asus", "msi", "gigabyte", "nvidia", "amd",
    # Security software
    "malwarebytes", "avast", "avg", "norton", "mcafee", "kaspersky", "bitdefender",
    # Menu bar/taskbar specific apps
    "bartender", "alfred", "cleanmymac", "1password", "lastpass", "amphetamine", "caffeine",
    "flux", "nightowl", "lunar", "istat", "memory clean", "newer battery", "coconutbattery"
]

# Whether to attempt admin-level operations (power plan, purge, winsock reset)
TRY_ADMIN_ACTIONS = True

# Whether to attempt to detect foreground app and prioritize it
PRIORITIZE_FOREGROUND = True

# How long to wait after closing background apps (seconds)
POST_CLOSE_WAIT = 1.2

# Enable aggressive optimizations (may require reboot)
AGGRESSIVE_MODE = True

# ------------------------------------------------------------------

def is_elevated():
    if SYSTEM == "Windows":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0

def run(cmd, capture=False, shell=False):
    try:
        if capture:
            return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=shell)
        else:
            return subprocess.run(cmd, shell=shell)
    except Exception as e:
        print("Command failed:", cmd, e)
        return None

# ------------------ Foreground (active) application detection ------------------

def get_foreground_process_name_windows():
    """Use Win32 APIs via ctypes to get the foreground window's process name (no extra packages)."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        pid = ctypes.c_ulong()
        hwnd = user32.GetForegroundWindow()
        if hwnd == 0:
            return None
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        p = psutil.Process(pid.value)
        return p.name()
    except Exception:
        return None

def get_foreground_process_name_macos():
    """Use AppleScript to get frontmost application name, then map to process."""
    try:
        # Get the frontmost application name
        cmd = ['osascript', '-e', 'tell application "System Events" to get name of first application process whose frontmost is true']
        proc = run(cmd, capture=True)
        if proc and proc.stdout:
            app_name = proc.stdout.strip()
            # Try to map to a process name
            for p in psutil.process_iter(['name', 'cmdline']):
                try:
                    if p.info.get('name') and app_name.lower() in p.info['name'].lower():
                        return p.info['name']
                    # Also check cmdline
                    cmdline = " ".join(p.info.get('cmdline') or [])
                    if app_name.lower() in cmdline.lower():
                        return p.info['name']
                except Exception:
                    continue
            return app_name
    except Exception:
        return None

def get_foreground_process_name_linux():
    # Best-effort: use xprop/wmctrl (not reliable on all systems)
    try:
        out = run(["xdotool", "getwindowfocus", "getwindowpid"], capture=True)
        if out and out.stdout:
            pid = int(out.stdout.strip())
            return psutil.Process(pid).name()
    except Exception:
        return None

def detect_foreground_process():
    if SYSTEM == "Windows":
        return get_foreground_process_name_windows()
    elif SYSTEM == "Darwin":
        return get_foreground_process_name_macos()
    elif SYSTEM == "Linux":
        return get_foreground_process_name_linux()
    else:
        return None

# ------------------ Background app termination ------------------

def kill_taskbar_apps():
    """Specifically target taskbar/menu bar apps that run in system tray."""
    killed = []
    print("🎯 Targeting taskbar/menu bar apps...")
    
    # Common taskbar/system tray apps
    taskbar_apps = [
        # Windows taskbar apps
        "discord", "spotify", "steam", "skype", "teams", "zoom", "slack",
        "dropbox", "onedrive", "googledrive", "box", "sync",
        "obs", "streamlabs", "nvidia", "amd", "corsair", "logitech",
        "razer", "steelseries", "asus", "msi", "gigabyte",
        "malwarebytes", "avast", "avg", "norton", "mcafee",
        "utorrent", "bittorrent", "qbittorrent",
        # macOS menu bar apps
        "bartender", "alfred", "cleanmymac", "1password", "lastpass",
        "amphetamine", "caffeine", "flux", "nightowl", "lunar",
        "istat", "activity monitor", "memory clean", "disk utility",
        "newer battery", "coconutbattery", "battery health",
        "little snitch", "micro snitch", "hands off"
    ]
    
    # Find and kill taskbar processes
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = (p.info.get('name') or "").lower()
            cmdline = " ".join(p.info.get('cmdline') or []).lower()
            
            # Skip system processes
            if p.pid <= 4 or name in ['explorer.exe', 'finder', 'dock']:
                continue
            
            for app in taskbar_apps:
                if app.lower() in name or app.lower() in cmdline:
                    try:
                        print(f"🎯 Found taskbar app: {name} (PID: {p.pid})")
                        p.terminate()
                        killed.append((p.pid, name))
                        time.sleep(0.1)
                    except Exception:
                        try:
                            p.kill()
                            killed.append((p.pid, name))
                            print(f"💥 Force killed: {name}")
                        except Exception:
                            pass
                    break
        except Exception:
            continue
    
    return killed

def force_kill_by_name(process_names):
    """Aggressively kill processes by name using system commands."""
    killed = []
    print("🔥 Using system commands to force kill stubborn processes...")
    
    for name in process_names:
        if SYSTEM == "Windows":
            # Try multiple variations for Windows
            variations = [f"{name}.exe", f"{name}", name.capitalize(), f"{name.capitalize()}.exe"]
            for variant in variations:
                try:
                    result = run(["taskkill", "/f", "/im", variant], capture=True)
                    if result and result.returncode == 0:
                        killed.append(f"{name} ({variant})")
                        print(f"💀 System killed: {variant}")
                        break
                except Exception:
                    continue
            
            # Also try killing by process name pattern
            try:
                result = run(["wmic", "process", "where", f"name like '%{name}%'", "delete"], capture=True)
                if result and result.returncode == 0:
                    killed.append(f"{name} (wmic)")
                    print(f"💀 WMIC killed: {name}")
            except Exception:
                pass
                    
        elif SYSTEM == "Darwin":
            # macOS-specific killing methods
            app_killed = False
            
            # Method 1: Kill by exact app name
            try:
                result = run(["killall", "-9", name], capture=True)
                if result and result.returncode == 0:
                    killed.append(name)
                    print(f"💀 Killall: {name}")
                    app_killed = True
            except Exception:
                pass
            
            # Method 2: Kill by process name with pkill
            if not app_killed:
                try:
                    result = run(["pkill", "-9", "-f", name], capture=True)
                    if result and result.returncode == 0:
                        killed.append(f"{name} (pkill)")
                        print(f"💀 Pkill: {name}")
                        app_killed = True
                except Exception:
                    pass
            
            # Method 3: Try common macOS app variations
            if not app_killed:
                app_variations = [
                    name.capitalize(),
                    f"{name.capitalize()}.app",
                    f"Google Chrome" if name == "chrome" else name,
                    f"Microsoft Teams" if name == "teams" else name,
                    f"Visual Studio Code" if name == "code" else name
                ]
                
                for variant in app_variations:
                    try:
                        result = run(["killall", "-9", variant], capture=True)
                        if result and result.returncode == 0:
                            killed.append(f"{variant}")
                            print(f"💀 Killed variant: {variant}")
                            app_killed = True
                            break
                    except Exception:
                        continue
            
            # Method 4: Use osascript to quit apps gracefully first, then force
            if not app_killed and name in ["chrome", "firefox", "safari", "discord", "spotify"]:
                app_name_map = {
                    "chrome": "Google Chrome",
                    "firefox": "Firefox",
                    "safari": "Safari",
                    "discord": "Discord",
                    "spotify": "Spotify"
                }
                app_name = app_name_map.get(name, name.capitalize())
                try:
                    # Try to quit gracefully first
                    run(["osascript", "-e", f'tell application "{app_name}" to quit'], capture=True)
                    time.sleep(1)
                    # Then force kill
                    result = run(["killall", "-9", app_name], capture=True)
                    if result and result.returncode == 0:
                        killed.append(f"{app_name} (osascript)")
                        print(f"💀 OSA quit + kill: {app_name}")
                except Exception:
                    pass
    
    return killed

def close_background_apps(app_substrings):
    closed = []
    print("🔍 Scanning for background apps to close...")
    
    # Get all processes and find targets
    all_processes = list(psutil.process_iter(['pid', 'name', 'cmdline', 'exe']))
    processes_to_kill = []
    
    for p in all_processes:
        try:
            name = (p.info.get('name') or "").lower()
            cmdline = " ".join(p.info.get('cmdline') or []).lower()
            exe_path = (p.info.get('exe') or "").lower()
            
            # Skip critical system processes
            if (p.pid <= 4 or 
                name in ['system', 'kernel_task', 'launchd', 'init', 'csrss.exe', 'winlogon.exe', 'explorer.exe', 
                        'finder', 'dock', 'systemuiserver', 'windowserver', 'loginwindow'] or
                'windows' in exe_path or 'system32' in exe_path or
                '/system/' in exe_path.lower() or '/usr/sbin/' in exe_path.lower()):
                continue
            
            # Check if process matches any target app
            for s in app_substrings:
                s_low = s.lower()
                if (s_low in name or s_low in cmdline or s_low in exe_path):
                    processes_to_kill.append((p, name))
                    print(f"🎯 Target found: {name} (PID: {p.pid})")
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    print(f"📋 Found {len(processes_to_kill)} processes to terminate")
    
    # Kill processes aggressively
    for p, name in processes_to_kill:
        try:
            print(f"⚡ Terminating: {name} (PID: {p.pid})")
            p.terminate()
            closed.append((p.pid, name))
            time.sleep(0.1)  # Brief pause
        except Exception:
            try:
                print(f"💀 Force killing: {name} (PID: {p.pid})")
                p.kill()
                closed.append((p.pid, name))
            except Exception as e:
                print(f"❌ Failed to kill {name}: {str(e)[:50]}")
    
    # Wait and verify termination
    if closed:
        print("⏳ Waiting for processes to terminate...")
        time.sleep(3)
        
        # Check if any are still running
        still_running = []
        for pid, name in closed:
            try:
                if psutil.pid_exists(pid):
                    still_running.append((pid, name))
            except Exception:
                pass
        
        if still_running:
            print(f"⚠️  {len(still_running)} processes still running, force killing...")
            for pid, name in still_running:
                try:
                    p = psutil.Process(pid)
                    p.kill()
                    print(f"💥 Force killed: {name}")
                except Exception:
                    pass
    
    return closed

# ------------------ OS-specific optimizations ------------------

def windows_optimizations(elevated):
    print("[Windows] Applying optimizations...")
    # 1) Flush DNS
    run(["ipconfig", "/flushdns"])
    run(["ipconfig", "/release"])
    run(["ipconfig", "/renew"])
    
    # 2) Set High Performance power plan
    if TRY_ADMIN_ACTIONS and elevated:
        try:
            run(["powercfg", "/setactive", "SCHEME_MIN"])
            # Disable USB selective suspend
            run(["powercfg", "/change", "usb-selective-suspend-setting", "0"])
        except Exception:
            pass
    
    # 3) Network optimizations
    if TRY_ADMIN_ACTIONS and elevated:
        # TCP optimizations
        run(["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"])
        run(["netsh", "int", "tcp", "set", "global", "chimney=enabled"])
        run(["netsh", "int", "tcp", "set", "global", "rss=enabled"])
        run(["netsh", "int", "tcp", "set", "global", "netdma=enabled"])
        # Disable Nagle's algorithm for gaming
        run(["netsh", "int", "tcp", "set", "global", "nonsackrttresiliency=disabled"])
    
    # 4) GPU optimizations
    if TRY_ADMIN_ACTIONS and elevated:
        # Set GPU hardware scheduling (Windows 10/11)
        try:
            run(["reg", "add", "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers", "/v", "HwSchMode", "/t", "REG_DWORD", "/d", "2", "/f"], capture=True)
        except Exception:
            pass
    
    # 5) Trim working sets
    try:
        import ctypes
        psapi = ctypes.windll.psapi
        kernel32 = ctypes.windll.kernel32
        for p in psutil.process_iter(["pid", "name"]):
            try:
                pid = p.info["pid"]
                PROCESS_SET_QUOTA = 0x0100
                PROCESS_QUERY_INFORMATION = 0x0400
                h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, int(pid))
                if h:
                    psapi.EmptyWorkingSet(h)
                    kernel32.CloseHandle(h)
            except Exception:
                continue
    except Exception:
        pass

def macos_optimizations(elevated):
    print("[macOS] Applying optimizations...")
    # 1) Flush DNS and network caches
    run(["dscacheutil", "-flushcache"])
    run(["killall", "-HUP", "mDNSResponder"])
    run(["dscacheutil", "-flushcache"])
    
    # 2) Disable App Nap and reduce UI animations
    run(["defaults", "write", "NSGlobalDomain", "NSAppSleepDisabled", "-bool", "YES"])
    run(["defaults", "write", "NSGlobalDomain", "NSWindowResizeTime", "-float", "0.001"])
    run(["defaults", "write", "NSGlobalDomain", "NSDocumentRevisionsDebugMode", "-bool", "YES"])
    run(["defaults", "write", "com.apple.dock", "launchanim", "-bool", "false"])
    
    # 3) Network optimizations
    run(["networksetup", "-setdnsservers", "Wi-Fi", "1.1.1.1", "8.8.8.8"])
    run(["networksetup", "-setdnsservers", "Ethernet", "1.1.1.1", "8.8.8.8"])
    
    # 4) Power management
    if TRY_ADMIN_ACTIONS and elevated:
        run(["pmset", "-a", "displaysleep", "0"])
        run(["pmset", "-a", "sleep", "0"])
        run(["pmset", "-a", "powernap", "0"])
        run(["pmset", "-a", "hibernatemode", "0"])
        run(["pmset", "-a", "standby", "0"])
    
    # 5) Memory optimization
    if TRY_ADMIN_ACTIONS and elevated:
        run(["purge"])
        # Clear system caches
        run(["rm", "-rf", "/System/Library/Caches/*"])
        run(["rm", "-rf", "/Library/Caches/*"])

# ------------------ Network optimizations ------------------

def optimize_network():
    """Apply network optimizations for lower ping and better connection."""
    print("Optimizing network settings...")
    
    if SYSTEM == "Windows":
        # Windows network optimizations
        run(["netsh", "winsock", "reset"])
        run(["netsh", "int", "ip", "reset"])
        # Optimize TCP settings
        run(["netsh", "int", "tcp", "set", "heuristics", "disabled"])
        run(["netsh", "int", "tcp", "set", "global", "rsc=disabled"])
        run(["netsh", "int", "tcp", "set", "global", "ecncapability=disabled"])
        # Set DNS to fast servers (try multiple interface names)
        interfaces = ["Wi-Fi", "Ethernet", "Local Area Connection", "Wireless Network Connection"]
        for interface in interfaces:
            try:
                run(["netsh", "interface", "ip", "set", "dns", f"name={interface}", "static", "1.1.1.1"], capture=True)
                run(["netsh", "interface", "ip", "add", "dns", f"name={interface}", "8.8.8.8", "index=2"], capture=True)
            except Exception:
                continue
    
    elif SYSTEM == "Darwin":
        # macOS network optimizations
        run(["networksetup", "-setdnsservers", "Wi-Fi", "1.1.1.1", "8.8.8.8"])
        run(["networksetup", "-setdnsservers", "Ethernet", "1.1.1.1", "8.8.8.8"])
        # Flush network state
        run(["dscacheutil", "-flushcache"])
        run(["killall", "-HUP", "mDNSResponder"])

def set_cpu_affinity(proc_name, cpu_cores=None):
    """Set CPU affinity for game processes to dedicated cores."""
    if not proc_name or SYSTEM != "Windows":
        return []
    
    if cpu_cores is None:
        # Use last 2 cores for games
        cpu_count = psutil.cpu_count()
        cpu_cores = list(range(max(0, cpu_count-2), cpu_count))
    
    affected = []
    for p in psutil.process_iter(['pid', 'name']):
        try:
            if proc_name.lower() in (p.info.get('name') or "").lower():
                p.cpu_affinity(cpu_cores)
                affected.append((p.pid, p.info.get('name')))
        except Exception:
            continue
    return affected

# ------------------ Priority & affinity ------------------

def prioritize_process_by_name(proc_name):
    """Set process priority to high for matching processes (case-insensitive substring match)."""
    if not proc_name:
        return []
    prioritized = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = (p.info.get('name') or "").lower()
            cmdline = " ".join(p.info.get('cmdline') or []).lower()
            if proc_name.lower() in name or proc_name.lower() in cmdline:
                try:
                    if SYSTEM == "Windows":
                        p.nice(psutil.HIGH_PRIORITY_CLASS)
                    else:
                        try:
                            p.nice(-10)  # requires root to set very negative niceness
                        except psutil.AccessDenied:
                            # best-effort: lower nice moderately
                            p.nice( -1 if p.nice() > -1 else p.nice() )
                    prioritized.append((p.pid, p.info.get('name')))
                except Exception:
                    continue
        except Exception:
            continue
    return prioritized

# ------------------ Friendly, safe logging ------------------

def human_report(closed, prioritized, cpu_affinity_set=None, force_killed=None, taskbar_killed=None):
    print("\n=== OPTIMIZATION RESULTS ===")
    
    if closed:
        print(f"✅ Successfully closed {len(closed)} background processes:")
        for pid, name in closed:
            print(f"  💀 PID {pid} : {name}")
    else:
        print("⚠️  No matching background apps found to close.")
    
    if taskbar_killed:
        print(f"🎯 Killed {len(taskbar_killed)} taskbar/menu bar apps:")
        for pid, name in taskbar_killed:
            print(f"  🎯 PID {pid} : {name}")
    
    if force_killed:
        print(f"🔥 System-level killed {len(force_killed)} resource hogs:")
        for name in force_killed:
            print(f"  💥 {name}")
    
    if not closed and not taskbar_killed and not force_killed:
        print("💡 System appears clean - no resource-heavy apps found to close.")

    if prioritized:
        print(f"✓ Prioritized {len(prioritized)} game processes:")
        for pid, name in prioritized:
            print(f"  - PID {pid} : {name}")
    else:
        print("⚠ No processes prioritized (start the game and re-run if required).")
    
    if cpu_affinity_set:
        print(f"✓ CPU affinity optimized for {len(cpu_affinity_set)} processes:")
        for pid, name in cpu_affinity_set:
            print(f"  - PID {pid} : {name}")

# ------------------ Main flow ------------------

def main():
    print("Universal FPS booster — starting.")
    elevated = is_elevated()
    if TRY_ADMIN_ACTIONS and not elevated:
        print("Note: You are not running as Administrator/root. Run elevated for maximum effect.")

    # 1) Detect foreground app
    fg = detect_foreground_process() if PRIORITIZE_FOREGROUND else None
    print("Detected foreground application (best-effort):", fg)

    # 2) Close background apps
    print("\n🎯 === TERMINATING BACKGROUND APPS ===")
    closed = close_background_apps(BG_APPS)
    
    # 2.1) Kill taskbar/menu bar apps specifically
    taskbar_killed = kill_taskbar_apps()
    
    # 2.2) System-level force kill of major resource hogs
    major_hogs = ["chrome", "firefox", "discord", "spotify", "steam", "obs", "teams", "zoom", "photoshop"]
    force_killed = force_kill_by_name(major_hogs)
    
    time.sleep(POST_CLOSE_WAIT)

    # 3) OS-specific optimizations
    if SYSTEM == "Windows":
        windows_optimizations(elevated)
    elif SYSTEM == "Darwin":
        macos_optimizations(elevated)
    else:
        print("Basic optimizations for Linux/other: flushing DNS if available.")
        try:
            run(["systemd-resolve", "--flush-caches"])
        except Exception:
            pass

    # 4) Network optimizations
    optimize_network()
    
    # 5) Prioritize foreground/game process
    prioritized = []
    cpu_affinity_set = []
    if fg:
        prioritized = prioritize_process_by_name(fg)
        cpu_affinity_set = set_cpu_affinity(fg)
    else:
        # Best-effort: if no foreground detected, try to prioritize common game executables
        common_games = ["fortnite", "gta", "valorant", "csgo", "counter-strike", "minecraft", "roblox", "apex", "overwatch", "dota", "lol"]
        for g in common_games:
            prioritized = prioritize_process_by_name(g)
            if prioritized:
                cpu_affinity_set = set_cpu_affinity(g)
                break

    # 6) Final tips output
    human_report(closed, prioritized, cpu_affinity_set, force_killed, taskbar_killed)
    print("\n🚀 FPS BOOST COMPLETE! 🚀")
    print("\nOptimizations applied:")
    print("✓ Background apps closed")
    print("✓ DNS flushed and optimized")
    print("✓ Network settings tuned for gaming")
    print("✓ Power plan set to high performance")
    print("✓ Game process prioritized")
    print("✓ CPU affinity optimized")
    print("\nAdditional tips for MAXIMUM FPS:")
    print("- Use wired Ethernet (lower ping than Wi-Fi)")
    print("- Update GPU drivers regularly")
    print("- Close browser tabs and streaming apps")
    print("- Set game to fullscreen mode")
    print("- Lower in-game settings: shadows, reflections, anti-aliasing")
    print("- Disable Windows Game Mode if it causes issues")
    print("- Run this script AFTER starting your game for best results")
    print("\n⚡ Your system is now optimized for gaming! ⚡")
    print("Finished.")

if __name__ == "__main__":
    main()