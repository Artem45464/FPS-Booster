#!/usr/bin/env python3
"""
universal_fps_booster.py - Enhanced Version

Cross-platform FPS booster for macOS and Windows 10/11.
Improvements:
- Better error handling and user feedback
- More robust process detection
- Enhanced safety checks
- Progress indicators
- Logging capabilities
"""

import os
import sys
import platform
import subprocess
import time
from datetime import datetime

# --- Ensure psutil available ---
def ensure_psutil():
    try:
        import psutil
        return psutil
    except Exception:
        print("psutil not found. Attempting to install psutil...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "psutil"])
            print("psutil installed successfully.")
            import psutil
            return psutil
        except Exception as e:
            print(f"Failed to auto-install psutil: {e}")
            print("Please install psutil manually: pip install psutil")
            sys.exit(1)

psutil = ensure_psutil()

SYSTEM = platform.system()

# ------------------ Configuration ------------------
BG_APPS = [
    # Browsers
    "chrome", "firefox", "edge", "opera", "brave", "safari",
    # Media & Music
    "spotify", "vlc", "plex", "itunes", "music", "netflix", "youtube",
    # Communication
    "discord", "skype", "zoom", "slack", "teams", "whatsapp", "telegram",
    # Gaming Platforms (launchers only)
    "steam", "epic games launcher", "origin", "battle.net", "uplay", "gog galaxy",
    # Streaming/Recording
    "obs", "streamlabs", "bandicam", "fraps", "nvidia broadcast", "nvidia shadowplay",
    # Adobe Creative Suite
    "photoshop", "illustrator", "premiere", "after effects", "lightroom", "acrobat",
    # Office & Productivity
    "word", "excel", "powerpoint", "outlook", "onenote", "notion",
    # Cloud Storage
    "dropbox", "onedrive", "google drive", "icloud",
    # Other Resource Heavy
    "blender", "unity", "unreal", "android studio", "xcode", "docker", "virtualbox"
]

PROTECTED_APPS = [
    "code", "vscode", "visual studio code", "terminal", "cmd", "powershell", "bash",
    "python", "pythonw", "conhost", "dwm", "winlogon", "wininit", "explorer",
    "finder", "dock", "systemuiserver"
]

PRIORITIZE_FOREGROUND = True

# ------------------ Utility Functions ------------------

def is_elevated():
    """Check if script is running with elevated privileges."""
    if SYSTEM == "Windows":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0

def run(cmd, capture=False, shell=False, timeout=10):
    """Execute command with improved error handling."""
    try:
        if capture:
            return subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                shell=shell,
                timeout=timeout
            )
        else:
            return subprocess.run(cmd, shell=shell, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"⚠️  Command timed out: {cmd}")
        return None
    except Exception as e:
        print(f"⚠️  Command failed: {e}")
        return None

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)

# ------------------ Foreground Process Detection ------------------

def get_foreground_process_name_windows():
    """Get foreground window's process name using Win32 APIs."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        # Get foreground window
        hwnd = user32.GetForegroundWindow()
        if hwnd == 0:
            return None
        
        # Get process ID
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        if pid.value == 0:
            return None
        
        # Get process info
        p = psutil.Process(pid.value)
        return p.name()
    except Exception as e:
        print(f"⚠️  Failed to detect foreground app: {e}")
        return None

def get_foreground_process_name_macos():
    """Get frontmost application name using AppleScript."""
    try:
        cmd = [
            'osascript', '-e',
            'tell application "System Events" to get name of first application process whose frontmost is true'
        ]
        proc = run(cmd, capture=True)
        
        if proc and proc.stdout:
            app_name = proc.stdout.strip()
            
            # Map application name to process
            for p in psutil.process_iter(['name', 'cmdline']):
                try:
                    name = p.info.get('name', '')
                    if app_name.lower() in name.lower():
                        return name
                    
                    cmdline = " ".join(p.info.get('cmdline') or [])
                    if app_name.lower() in cmdline.lower():
                        return name
                except Exception:
                    continue
            
            return app_name
    except Exception as e:
        print(f"⚠️  Failed to detect foreground app: {e}")
        return None

def get_foreground_process_name_linux():
    """Get foreground process on Linux (requires xdotool)."""
    try:
        out = run(["xdotool", "getwindowfocus", "getwindowpid"], capture=True)
        if out and out.stdout:
            pid = int(out.stdout.strip())
            return psutil.Process(pid).name()
    except Exception as e:
        print(f"⚠️  Failed to detect foreground app: {e}")
        return None

def detect_foreground_process():
    """Detect the currently active (foreground) process."""
    if SYSTEM == "Windows":
        return get_foreground_process_name_windows()
    elif SYSTEM == "Darwin":
        return get_foreground_process_name_macos()
    elif SYSTEM == "Linux":
        return get_foreground_process_name_linux()
    else:
        return None

# ------------------ Process Management ------------------

def get_user_confirmation():
    """Get user confirmation before proceeding."""
    print("\n" + "⚠️ "*20)
    print("  WARNING: This script will:")
    print("  • Close background applications")
    print("  • Modify network settings")
    print("  • Change power settings (if admin)")
    print("  • Adjust process priorities")
    print("\n  💾 SAVE YOUR WORK BEFORE CONTINUING!")
    print("⚠️ "*20 + "\n")
    
    response = input("Continue? (yes/no): ").lower().strip()
    return response in ['yes', 'y']

def is_process_protected(name, cmdline):
    """Check if a process should be protected from termination."""
    name_lower = name.lower()
    cmdline_lower = cmdline.lower()
    
    # Critical system processes
    critical = ['system', 'kernel_task', 'launchd', 'init', 'csrss.exe', 
                'winlogon.exe', 'explorer.exe', 'finder', 'dock', 'dwm.exe']
    
    if any(crit in name_lower for crit in critical):
        return True
    
    # Protected apps
    for protected in PROTECTED_APPS:
        if protected.lower() in name_lower or protected.lower() in cmdline_lower:
            return True
    
    return False

def graceful_close_process(process):
    """Attempt graceful termination before force killing."""
    try:
        # Try graceful termination
        process.terminate()
        process.wait(timeout=3)
        return True
    except psutil.TimeoutExpired:
        # Force kill as last resort
        try:
            process.kill()
            return True
        except Exception:
            return False
    except Exception:
        return False

def close_background_apps(app_substrings):
    """Close background apps with improved safety checks."""
    closed = []
    failed = []
    
    print("\n🔍 Scanning for background apps...")
    time.sleep(0.5)  # Brief pause for user readability
    
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = (p.info.get('name') or "").lower()
            cmdline = " ".join(p.info.get('cmdline') or []).lower()
            
            # Skip low PIDs (system processes)
            if p.pid <= 4:
                continue
            
            # Skip protected processes
            if is_process_protected(p.info.get('name', ''), cmdline):
                continue
            
            # Check if matches target apps
            for s in app_substrings:
                if s.lower() in name or s.lower() in cmdline:
                    print(f"  🎯 Closing: {p.info.get('name')} (PID: {p.pid})")
                    
                    if graceful_close_process(p):
                        closed.append((p.pid, p.info.get('name')))
                    else:
                        failed.append((p.pid, p.info.get('name')))
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception as e:
            continue
    
    # Print summary
    if closed:
        print(f"\n✅ Successfully closed {len(closed)} apps")
    if failed:
        print(f"⚠️  Failed to close {len(failed)} apps (may require admin)")
    
    return closed, failed

# ------------------ Network Optimization ------------------

def get_network_interfaces():
    """Get available network interfaces."""
    interfaces = []
    
    if SYSTEM == "Windows":
        try:
            result = run(["netsh", "interface", "show", "interface"], capture=True)
            if result and result.stdout:
                for line in result.stdout.split('\n'):
                    if 'Connected' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            interface_name = ' '.join(parts[3:])
                            interfaces.append(interface_name)
        except Exception:
            interfaces = ["Wi-Fi", "Ethernet"]
    
    elif SYSTEM == "Darwin":
        try:
            result = run(["networksetup", "-listallnetworkservices"], capture=True)
            if result and result.stdout:
                for line in result.stdout.split('\n')[1:]:
                    line = line.strip()
                    if line and not line.startswith('*'):
                        interfaces.append(line)
        except Exception:
            interfaces = ["Wi-Fi", "Ethernet"]
    
    return interfaces

def optimize_network():
    """Apply network optimizations."""
    print("\n🌐 Optimizing network settings...")
    success_count = 0
    
    # Flush DNS cache
    print("  • Flushing DNS cache...")
    if SYSTEM == "Windows":
        if run(["ipconfig", "/flushdns"], capture=True):
            print("    ✓ DNS cache flushed")
            success_count += 1
    elif SYSTEM == "Darwin":
        if run(["dscacheutil", "-flushcache"], capture=True):
            run(["killall", "-HUP", "mDNSResponder"], capture=True)
            print("    ✓ DNS cache flushed")
            success_count += 1
    
    # Set DNS servers
    print("  • Configuring DNS servers (Cloudflare & Google)...")
    interfaces = get_network_interfaces()
    
    if not interfaces:
        print("    ⚠️  No network interfaces found")
        return success_count
    
    for interface in interfaces:
        try:
            if SYSTEM == "Windows":
                result = run([
                    "netsh", "interface", "ip", "set", "dns",
                    f"name={interface}", "static", "1.1.1.1"
                ], capture=True)
                if result and result.returncode == 0:
                    success_count += 1
            
            elif SYSTEM == "Darwin":
                result = run([
                    "networksetup", "-setdnsservers",
                    interface, "1.1.1.1", "8.8.8.8"
                ], capture=True)
                if result and result.returncode == 0:
                    success_count += 1
        except Exception:
            continue
    
    if success_count > 0:
        print(f"    ✓ DNS configured on {len(interfaces)} interface(s)")
    else:
        print("    ⚠️  DNS configuration failed (may require admin)")
    
    return success_count

# ------------------ Power Optimization ------------------

def optimize_power():
    """Apply power optimizations."""
    print("\n⚡ Optimizing power settings...")
    
    if not is_elevated():
        print("  ⚠️  Admin privileges required for power optimization")
        print("     Run script as administrator for full optimization")
        return False
    
    if SYSTEM == "Windows":
        try:
            # Try to set high performance mode
            result = run([
                "powercfg", "/setactive",
                "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"  # High Performance GUID
            ], capture=True)
            
            if result and result.returncode == 0:
                print("  ✓ High performance mode enabled")
                return True
            else:
                print("  ⚠️  Failed to enable high performance mode")
                return False
        except Exception as e:
            print(f"  ⚠️  Power optimization failed: {e}")
            return False
    
    elif SYSTEM == "Darwin":
        try:
            run(["pmset", "-a", "displaysleep", "0"], capture=True)
            run(["pmset", "-a", "sleep", "0"], capture=True)
            print("  ✓ Sleep mode disabled")
            return True
        except Exception:
            print("  ⚠️  Failed to modify power settings")
            return False
    
    return False

# ------------------ Process Prioritization ------------------

def prioritize_game_process(proc_name):
    """Prioritize game process with improved error handling."""
    if not proc_name:
        return []
    
    prioritized = []
    failed = []
    
    print(f"\n🎮 Prioritizing game processes...")
    
    for p in psutil.process_iter(['pid', 'name']):
        try:
            name = (p.info.get('name') or "").lower()
            
            if proc_name.lower() in name:
                try:
                    if SYSTEM == "Windows":
                        p.nice(psutil.HIGH_PRIORITY_CLASS)
                    else:
                        p.nice(-10)
                    
                    prioritized.append((p.pid, p.info.get('name')))
                    print(f"  ✓ Prioritized: {p.info.get('name')} (PID: {p.pid})")
                except psutil.AccessDenied:
                    failed.append((p.pid, p.info.get('name')))
                except Exception:
                    continue
        except Exception:
            continue
    
    if failed:
        print(f"  ⚠️  Failed to prioritize {len(failed)} process(es) (may require admin)")
    
    return prioritized

# ------------------ Main Function ------------------

def main():
    start_time = time.time()
    
    print_section("🎮 FPS BOOSTER v2.5 - Enhanced Edition")
    print(f"Platform: {SYSTEM}")
    print(f"Admin Mode: {'YES' if is_elevated() else 'NO'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get user confirmation
    if not get_user_confirmation():
        print("\n❌ Optimization cancelled by user.\n")
        return
    
    print("\n🚀 Starting optimization process...")
    
    # Stats tracking
    stats = {
        'closed': 0,
        'prioritized': 0,
        'network_optimized': False,
        'power_optimized': False
    }
    
    # 1) Detect active game
    fg = None
    if PRIORITIZE_FOREGROUND:
        print("\n🔎 Detecting active application...")
        fg = detect_foreground_process()
        if fg:
            print(f"  ✓ Detected: {fg}")
        else:
            print("  ⚠️  Could not detect active application")
    
    # 2) Close background apps
    print_section("CLOSING BACKGROUND APPS")
    closed, failed = close_background_apps(BG_APPS)
    stats['closed'] = len(closed)
    
    # 3) Network optimization
    print_section("NETWORK OPTIMIZATION")
    net_result = optimize_network()
    stats['network_optimized'] = net_result > 0
    
    # 4) Power optimization
    print_section("POWER OPTIMIZATION")
    stats['power_optimized'] = optimize_power()
    
    # 5) Prioritize game
    print_section("GAME PRIORITIZATION")
    prioritized = []
    
    if fg:
        prioritized = prioritize_game_process(fg)
    
    # If no foreground detected, try common games
    if not prioritized:
        print("  Searching for common games...")
        common_games = ["fortnite", "valorant", "csgo", "minecraft", "gta", "apex",
                       "warzone", "overwatch", "league", "dota"]
        for game in common_games:
            prioritized = prioritize_game_process(game)
            if prioritized:
                break
    
    if not prioritized:
        print("  ⚠️  No game processes found to prioritize")
    
    stats['prioritized'] = len(prioritized)
    
    # Final summary
    elapsed = time.time() - start_time
    
    print_section("📊 OPTIMIZATION COMPLETE")
    print(f"\n  ✅ Closed Apps:        {stats['closed']}")
    print(f"  ✅ Prioritized:        {stats['prioritized']} process(es)")
    print(f"  {'✅' if stats['network_optimized'] else '⚠️ '} Network:          {'Optimized' if stats['network_optimized'] else 'Partial/Failed'}")
    print(f"  {'✅' if stats['power_optimized'] else '⚠️ '} Power:            {'Optimized' if stats['power_optimized'] else 'Requires Admin'}")
    print(f"\n  ⏱️  Time Elapsed:      {elapsed:.2f} seconds")
    
    print("\n💡 Additional Tips for Best Performance:")
    print("  • Use wired Ethernet connection")
    print("  • Set game to exclusive fullscreen mode")
    print("  • Update GPU drivers regularly")
    print("  • Close browser tabs")
    print("  • Disable overlays (Discord, Steam, etc.)")
    print("  • Monitor temps (CPU/GPU should stay cool)")
    
    if not is_elevated():
        print("\n⚡ Pro Tip: Run as Administrator for full optimization!")
    
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Optimization interrupted by user.\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}\n")
        sys.exit(1)
