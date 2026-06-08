# ==========================================
# Copyright (c) 2026
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==========================================

import os
import subprocess
import platform
import sys

def enforce_limits_unix():
    """Unix-only limits using the resource module and setrlimit."""
    try:
        import resource
        # Limit memory to 256 MB
        max_memory = 268435456
        resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
        
        # Limit CPU time to 3 seconds
        resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
        
        # Limit file size to 5 MB
        max_file_size = 5242880
        resource.setrlimit(resource.RLIMIT_FSIZE, (max_file_size, max_file_size))
        
        # Run in a new session to allow killing the entire process group
        os.setsid()
    except ImportError:
        pass # Ignore if not on Unix

def run_sandboxed(script_path: str, timeout_sec: float = 3.0) -> dict:
    """
    Executes a given script in a sandboxed environment.
    Uses strict Bubblewrap and resource limits on Unix,
    and falls back to standard subprocess constraints on Windows.
    """
    print(f"[SANDBOX] Initiating sandboxed execution for {script_path}")
    
    is_windows = platform.system().lower() == "windows"
    
    if is_windows:
        # Cross-platform fallback: standard subprocess timeouts
        print("[SANDBOX] OS detected as Windows. Bypassing 'bwrap' and 'resource' modules. Using standard subprocess timeout.")
        cmd = [sys.executable, script_path]
        preexec = None
    else:
        # Unix/Linux strict sandboxing via bwrap
        print("[SANDBOX] OS detected as Unix. Enforcing Bubblewrap namespace isolation and kernel resource limits.")
        # Check if bwrap exists
        bwrap_path = subprocess.run(["which", "bwrap"], capture_output=True, text=True).stdout.strip()
        if bwrap_path:
            cmd = [
                "bwrap",
                "--ro-bind", "/usr", "/usr",
                "--ro-bind", "/lib", "/lib",
                "--ro-bind", "/lib64", "/lib64",
                "--symlink", "usr/lib64", "/lib64",
                "--proc", "/proc",
                "--dev", "/dev",
                "--tmpfs", "/tmp",
                "--tmpfs", "/home",
                "--bind", os.path.dirname(os.path.abspath(script_path)), "/app/sandbox",
                "--unshare-pid",
                "--unshare-net",
                "--new-session",
                "--",
                sys.executable, f"/app/sandbox/{os.path.basename(script_path)}"
            ]
        else:
            print("[SANDBOX WARNING] bwrap not found in PATH. Falling back to native subprocess.")
            cmd = [sys.executable, script_path]
            
        preexec = enforce_limits_unix

    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_sec,
            text=True,
            preexec_fn=preexec
        )
        print(f"[SANDBOX] Execution completed with exit code {process.returncode}")
        return {
            "success": process.returncode == 0,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "exit_code": process.returncode
        }
    except subprocess.TimeoutExpired as e:
        print("[SANDBOX CRITICAL] Execution exceeded hard CPU timeout limits.")
        # If running on unix, attempt to clean up process group
        if not is_windows and preexec is not None:
            try:
                import signal
                if hasattr(e, 'pid') and e.pid:
                    os.killpg(e.pid, signal.SIGKILL)
            except Exception:
                pass
                
        return {
            "success": False,
            "stdout": e.stdout.decode() if e.stdout else "",
            "stderr": e.stderr.decode() if e.stderr else "TimeoutError: Execution exceeded 3.0s limit",
            "exit_code": -1
        }
