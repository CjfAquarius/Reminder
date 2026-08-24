import tkinter as tk
import time
import pickle
from datetime import datetime
from plyer import notification
import urllib.request
import urllib.error
import json
import os
import sys
import subprocess
import tempfile
import threading
from tkinter import messagebox, ttk

DATA_FILE = "scheduler.dat"
VERSION_FILE = "version.txt"  # Version information file
# Update related constants
REPO_OWNER = "CjfAquarius"
REPO_NAME = "Reminder"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
EXE_NAME = "setup.exe"

# GitHub acceleration site list (sorted by priority)
ACCELERATORS = [
    "https://ghproxy.net",
    "https://github.moeyy.xyz",
    "https://gh.llkk.cc",
    "https://gh.con.sh",
    "https://github.dog",
]

class FloatingWindow:
    def __init__(self):
        self.root = tk.Tk()
        
        # ============ Window Size Settings ============
        self.width = 310
        self.height = 194
        
        # ============ Window Style Settings ============
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # ============ Transparency Settings ============
        self.normal_alpha = 0.85
        self.idle_alpha = 0.3
        self.hidden_alpha = 0.0
        self.root.attributes("-alpha", self.normal_alpha)
        
        # ============ Window Position Settings ============
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - self.width - 50
        y = screen_height - self.height - 100
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        
        # ============ Data Storage ============
        self.root.configure(bg="#1e3a8a")
        self.schedule_data = [[], [], [], [], [], [], []]
        self.task_queue = []
        self.last_popped_task = None
        self.carousel_index = 0
        self.is_hidden = False
        self.drag_data = {"x": 0, "y": 0}
        
        # ============ Timer Management ============
        self._last_popup_time = 0
        self.display_list = []
        self.carousel_running = False
        self.carousel_after_id = None
        self.check_after_id = None
        self.refreshing = False
        
        # ============ Update Related ============
        self.update_in_progress = False
        self.current_version = self._read_version()  # Read version from version.txt

        # ============ Initialize Interface ============
        self.add_content()
        self.setup_dragging()
        self.setup_alpha_switch()
        
        # ============ Load Data and Start ============
        self.load_schedule()
        self.update_time()
        self.start_check_task_status()

    def _read_version(self):
        """Read version number from version.txt, return default version if file doesn't exist"""
        try:
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                    version = f.read().strip()
                    if version:
                        return version
        except Exception:
            pass
        return "1.0.0"  # Default version

    def _get_accelerated_url(self, original_url):
        """Convert GitHub download link to acceleration site link"""
        for accelerator in ACCELERATORS:
            # Try different acceleration site formats
            # Format 1: https://acceleration-site/https://github.com/...
            url1 = f"{accelerator}/{original_url}"
            # Format 2: https://acceleration-site/github.com/... (some sites don't need https:// prefix)
            if original_url.startswith("https://"):
                url2 = f"{accelerator}/{original_url[8:]}"
            else:
                url2 = f"{accelerator}/{original_url}"
            
            # Return the first available acceleration site (simply returns here, will attempt connection in actual use)
            # Prefer format 1
            return url1
        
        return original_url  # Use original link if no acceleration site is available

    def _download_with_accelerator(self, download_url, exe_path, timeout=60):
        """Download file using acceleration site, try next site if failed"""
        # Get the filename part of the original URL
        file_name = download_url.split('/')[-1]
        
        # Build acceleration site URL list
        accelerated_urls = []
        for accelerator in ACCELERATORS:
            # Try different formats
            accelerated_urls.append(f"{accelerator}/{download_url}")
            if download_url.startswith("https://"):
                accelerated_urls.append(f"{accelerator}/{download_url[8:]}")
        
        # Try each acceleration site in order
        for url in accelerated_urls:
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                    }
                )
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    # Check response status
                    if response.status == 200:
                        with open(exe_path, 'wb') as f:
                            f.write(response.read())
                        return True, url  # Download successful
            except Exception as e:
                # Current acceleration site failed, try next one
                continue
        
        # All acceleration sites failed, try downloading from original URL directly
        try:
            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    with open(exe_path, 'wb') as f:
                        f.write(response.read())
                    return True, download_url
        except Exception:
            pass
        
        return False, None

    def load_schedule(self):
        """Load schedule data from file and reset today's task queue"""
        try:
            with open(DATA_FILE, "rb") as f:
                self.schedule_data = pickle.load(f)
        except Exception:
            self.schedule_data = [[], [], [], [], [], [], []]
        
        self.reset_today_queue()
        self.reset_carousel()

    def reset_carousel(self):
        """Reset carousel state"""
        if self.carousel_after_id:
            self.root.after_cancel(self.carousel_after_id)
            self.carousel_after_id = None
        
        self.carousel_running = False
        self.carousel_index = 0
        self.display_list = []

    def reset_today_queue(self):
        """Reset today's task queue"""
        now = datetime.now()
        current_weekday = now.weekday()
        today_plans = self.schedule_data[current_weekday]
        self.task_queue = sorted(today_plans, key=lambda x: x[0])
        self.last_popped_task = None

    def add_content(self):
        """Add all UI components to the window"""
        # ===== Top-left Title =====
        self.title_label = tk.Label(
            self.root,
            text="Plan Manager",
            fg="#93c5fd",
            bg="#1e3a8a",
            font=("Microsoft YaHei", 8)
        )
        self.title_label.place(x=12, y=8)
        
        # ===== Sleep Button (🌙) =====
        self.sleep_btn = tk.Label(
            self.root,
            text="🌙",
            bg="#1e3a8a",
            fg="white",
            font=("Arial", 11),
            cursor="hand2"
        )
        self.sleep_btn.place(x=self.width-32, y=6, width=22, height=22)
        self.sleep_btn.bind("<Button-1>", self.go_to_sleep)
        
        # ===== Refresh Button (🔄) =====
        self.refresh_btn = tk.Label(
            self.root,
            text="🔄",
            bg="#1e3a8a",
            fg="white",
            font=("Arial", 11),
            cursor="hand2"
        )
        self.refresh_btn.place(x=self.width-58, y=7, width=20, height=20)
        self.refresh_btn.bind("<Button-1>", self.refresh_schedule)
        
        # ===== Update Button (🆕) =====
        self.update_btn = tk.Label(
            self.root,
            text="🆕",
            bg="#1e3a8a",
            fg="white",
            font=("Arial", 11),
            cursor="hand2"
        )
        self.update_btn.place(x=self.width-84, y=7, width=20, height=20)
        self.update_btn.bind("<Button-1>", self.check_for_updates)
        
        # ===== Time Display =====
        self.time_label = tk.Label(
            self.root,
            text="",
            fg="white",
            bg="#1e3a8a",
            font=("Consolas", 18, "bold")
        )
        self.time_label.place(relx=0.5, rely=0.20, anchor="center")
        
        # ===== Date Display =====
        self.date_label = tk.Label(
            self.root,
            text="",
            fg="#bfdbfe",
            bg="#1e3a8a",
            font=("Microsoft YaHei", 9)
        )
        self.date_label.place(relx=0.5, rely=0.38, anchor="center")
        
        # ===== Task Display Area =====
        self.task_label = tk.Label(
            self.root,
            text="",
            bg="#1e3a8a",
            font=("Microsoft YaHei", 12, "bold"),
            justify="center"
        )
        self.task_label.place(relx=0.5, rely=0.65, anchor="center")
        self.task_label.config(wraplength=290)

    def refresh_schedule(self, event=None):
        """Handle refresh button click"""
        if self.refreshing:
            return
        
        self.refreshing = True
        
        if self.carousel_after_id:
            self.root.after_cancel(self.carousel_after_id)
            self.carousel_after_id = None
        if self.check_after_id:
            self.root.after_cancel(self.check_after_id)
            self.check_after_id = None
        
        self.reset_carousel()
        self.carousel_running = False
        self.load_schedule()
        self.update_display_after_refresh()
        
        if self.is_hidden:
            self.wake_up()
        
        self.show_toast("Schedule Refreshed", "Latest schedule loaded")
        self.root.after(3000, self.restart_after_refresh)

    def update_display_after_refresh(self):
        """Update display immediately after refresh"""
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        if not self.task_queue:
            self.task_label.config(text="Today's plan completed", fg="#c4b5fd")
            self.refreshing = False
            return
        
        t1, p1 = self.task_queue[0]
        is_task1_started = t1 <= current_time_str
        
        if not is_task1_started:
            self.task_label.config(text=f"Upcoming: {t1} {p1}", fg="#93c5fd")
            self.refreshing = False
            return
        
        self.update_display_list()
        if self.display_list:
            self.task_label.config(text=self.display_list[0], fg="#c4b5fd")
            self.carousel_index = 0

    def restart_after_refresh(self):
        """Restart task checking after refresh completes"""
        self.refreshing = False
        self.carousel_running = False
        self.start_check_task_status()

    def go_to_sleep(self, event=None):
        """Enter stealth mode"""
        self.root.attributes("-alpha", self.hidden_alpha)
        self.is_hidden = True
        self.sleep_btn.config(fg="#64748b", text="🌙")

    def wake_up(self):
        """Wake up the window"""
        if self.is_hidden:
            self.root.attributes("-alpha", self.normal_alpha)
            self.is_hidden = False
            self.sleep_btn.config(fg="white", text="🌙")

    def show_toast(self, title, body):
        """Send system notification"""
        try:
            notification.notify(
                title=title,
                message=body,
                app_name='Plan Manager',
                timeout=5
            )
        except Exception:
            pass

    def update_time(self):
        """Update time and date every second"""
        current_time = time.strftime("%H:%M:%S")
        self.time_label.config(text=current_time)
        
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        weekday_str = weekdays[now.weekday()]
        self.date_label.config(text=f"{date_str} {weekday_str}")
        
        self.root.after(1000, self.update_time)

    def start_check_task_status(self):
        """Start task status check loop"""
        if self.check_after_id:
            self.root.after_cancel(self.check_after_id)
        self.check_task_status()

    def check_task_status(self):
        """Check task status (executed every second)"""
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        if self.refreshing:
            self.check_after_id = self.root.after(1000, self.check_task_status)
            return
        
        if not self.task_queue:
            self.task_label.config(text="Today's plan completed", fg="#c4b5fd")
            self.carousel_running = False
            self.check_after_id = self.root.after(1000, self.check_task_status)
            return

        task_switched = False
        while len(self.task_queue) >= 2 and self.task_queue[1][0] <= current_time_str:
            ended_task = self.task_queue.pop(0)
            self.last_popped_task = ended_task
            task_switched = True
            
            if self.task_queue:
                current_plan = self.task_queue[0]
                title = "Task Switch Notification"
                body = f"{ended_task[0]} {ended_task[1]} ended\nNow starting: {current_plan[0]} {current_plan[1]}"
                
                self.wake_up()
                if time.time() - self._last_popup_time > 2:
                    self.show_toast(title, body)
                    self._last_popup_time = time.time()
            
            if not self.task_queue:
                break

        if task_switched:
            self.reset_carousel()
            self.update_display_list()
            self.carousel_index = 0
            if self.display_list:
                self.task_label.config(text=self.display_list[0], fg="#c4b5fd")
        
        if not self.task_queue:
            self.task_label.config(text="Today's plan completed", fg="#c4b5fd")
            self.carousel_running = False
            self.check_after_id = self.root.after(1000, self.check_task_status)
            return

        t1, p1 = self.task_queue[0]
        is_task1_started = t1 <= current_time_str

        if not is_task1_started:
            self.task_label.config(text=f"Upcoming: {t1} {p1}", fg="#93c5fd")
            self.carousel_running = False
            self.check_after_id = self.root.after(1000, self.check_task_status)
            return

        if not self.display_list or task_switched:
            self.update_display_list()
            self.carousel_index = 0
        
        if not self.carousel_running and self.display_list:
            self.carousel_running = True
            self.carousel_after_id = self.root.after(1000, self.start_carousel)
        
        self.check_after_id = self.root.after(1000, self.check_task_status)

    def update_display_list(self):
        """Generate carousel display list"""
        self.display_list = []
        if not self.task_queue:
            return
        
        t1, p1 = self.task_queue[0]
        self.display_list.append(f"{t1} {p1}")
        
        if len(self.task_queue) >= 2:
            t2, p2 = self.task_queue[1]
            self.display_list.append(f"{t2} {p2}")
        
        if len(self.task_queue) >= 3:
            t3, p3 = self.task_queue[2]
            self.display_list.append(f"{t3} {p3}")

    def start_carousel(self):
        """Start carousel"""
        if not self.carousel_running or not self.display_list or self.refreshing:
            self.carousel_running = False
            return
        
        self.carousel_index = (self.carousel_index + 1) % len(self.display_list)
        current_text = self.display_list[self.carousel_index]
        
        if self.carousel_index == 0:
            self.task_label.config(text=current_text, fg="#c4b5fd")
        else:
            self.task_label.config(text=current_text, fg="#bfdbfe")
        
        self.carousel_after_id = self.root.after(2500, self.start_carousel)

    def setup_dragging(self):
        """Set up window dragging functionality"""
        def start_move(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        def on_move(event):
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            
            new_x = self.root.winfo_x() + dx
            new_y = self.root.winfo_y() + dy
            
            new_x = max(-self.width + 10, min(new_x, self.root.winfo_screenwidth() - 10))
            new_y = max(-self.height + 10, min(new_y, self.root.winfo_screenheight() - 10))
            
            self.root.geometry(f"+{new_x}+{new_y}")

        self.root.bind("<ButtonPress-1>", start_move)
        self.root.bind("<B1-Motion>", on_move)

    def setup_alpha_switch(self):
        """Set up mouse hover transparency switch"""
        self.root.bind("<Enter>", self.on_mouse_enter)
        self.root.bind("<Leave>", self.on_mouse_leave)

    def on_mouse_enter(self, event):
        """Mouse enters window"""
        if not self.is_hidden:
            self.root.attributes("-alpha", self.normal_alpha)

    def on_mouse_leave(self, event):
        """Mouse leaves window"""
        if not self.is_hidden:
            self.root.attributes("-alpha", self.idle_alpha)

    # ============ Update Related Methods ============
    def check_for_updates(self, event=None):
        """Check GitHub Releases for updates"""
        if self.update_in_progress:
            return
        
        threading.Thread(target=self._check_updates_thread, daemon=True).start()

    def _check_updates_thread(self):
        """Background thread to check for updates"""
        try:
            self.root.after(0, lambda: self.update_btn.config(text="⏳"))
            
            req = urllib.request.Request(
                GITHUB_API_URL,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                data = json.loads(response.read().decode('utf-8'))
            
            latest_tag = data.get("tag_name", "").lstrip("v")
            if not latest_tag:
                raise Exception("Unable to get version number")
            
            latest_major_minor = ".".join(latest_tag.split(".")[:2])
            current_major_minor = ".".join(self.current_version.split(".")[:2])
            
            download_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/{data.get('tag_name', '')}/{EXE_NAME}"
            
            if latest_major_minor <= current_major_minor:
                self.root.after(0, lambda: self._show_update_result("Already Latest", f"Current version v{self.current_version} is already up to date"))
                return
            
            self.root.after(0, lambda: self._prompt_update(latest_tag, download_url))
            
        except urllib.error.URLError as e:
            self.root.after(0, lambda: self._show_update_result("Network Error", f"Connection failed: {str(e)}"))
        except json.JSONDecodeError as e:
            self.root.after(0, lambda: self._show_update_result("Data Error", f"Failed to parse response: {str(e)}"))
        except Exception as e:
            self.root.after(0, lambda: self._show_update_result("Error", f"Failed to check for updates: {str(e)}"))

    def _prompt_update(self, version, download_url):
        """Ask user whether to download the update"""
        result = messagebox.askyesno(
            "New Version Found",
            f"New version v{version} found\n\nCurrent version: v{self.current_version}\n\nDo you want to download and install the update?",
            icon=messagebox.QUESTION
        )
        if result:
            threading.Thread(target=self._download_and_run, args=(download_url,), daemon=True).start()
        else:
            self.root.after(0, lambda: self.update_btn.config(text="🆕"))

    def _download_and_run(self, download_url):
        """Download setup.exe and run it (using acceleration sites)"""
        if self.update_in_progress:
            return
        
        self.update_in_progress = True
        
        try:
            self.root.after(0, lambda: self.update_btn.config(text="⬇️"))
            
            temp_dir = tempfile.mkdtemp()
            exe_path = os.path.join(temp_dir, EXE_NAME)
            
            # Download using acceleration sites
            self.root.after(0, lambda: self._update_status_label("Downloading using acceleration sites..."))
            success, used_url = self._download_with_accelerator(download_url, exe_path, timeout=120)
            
            if not success:
                raise Exception("All download sources failed, please check your network connection")
            
            if not os.path.exists(exe_path) or os.path.getsize(exe_path) == 0:
                raise Exception("Downloaded file is invalid or empty")
            
            self.root.after(0, lambda: self.update_btn.config(text="✅"))
            self.root.after(0, lambda: self._launch_and_exit(exe_path))
            
        except Exception as e:
            self.update_in_progress = False
            self.root.after(0, lambda: messagebox.showerror("Update Failed", f"Download failed: {str(e)}"))
            self.root.after(0, lambda: self.update_btn.config(text="🆕"))

    def _update_status_label(self, message):
        """Update status display (for showing download progress)"""
        # Can update task_label here to show download status
        self.task_label.config(text=message, fg="#93c5fd")

    def _launch_and_exit(self, installer_path):
        """Launch the installer and exit immediately"""
        try:
            os.startfile(installer_path)
            self._exit_app()
        except Exception as e:
            messagebox.showerror("Launch Failed", f"Unable to launch installer: {str(e)}")
            self.update_in_progress = False
            self.update_btn.config(text="🆕")

    def _exit_app(self):
        """Exit the application"""
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def _show_update_result(self, title, message):
        """Show update check result"""
        self.update_btn.config(text="🆕")
        if "Failed" in title or "Error" in title:
            self.update_btn.config(text="❌")
            messagebox.showwarning(title, message)
        else:
            self.update_btn.config(text="✅")
            messagebox.showinfo(title, message)
        self.root.after(2000, lambda: self.update_btn.config(text="🆕"))

    def run(self):
        """Start the main loop"""
        self.root.mainloop()

if __name__ == "__main__":
    app = FloatingWindow()
    app.run()
