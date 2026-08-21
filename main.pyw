import tkinter as tk
import time
import pickle
import os
from datetime import datetime
from plyer import notification

DATA_FILE = "scheduler.dat"

class FloatingWindow:
    def __init__(self):
        self.root = tk.Tk()
        # Area is about 60% of original (width and height multiplied by √0.6)
        self.width = 310   # 400 * 0.775
        self.height = 194  # 250 * 0.775
        
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        self.normal_alpha = 0.85
        self.idle_alpha = 0.3
        self.hidden_alpha = 0.0
        self.root.attributes("-alpha", self.normal_alpha)
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - self.width - 50
        y = screen_height - self.height - 100
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        
        self.root.configure(bg="#1e3a8a")
        self.schedule_data = [[], [], [], [], [], [], []]  # 0~6 (Mon~Sun)
        self.task_queue = []
        self.last_popped_task = None
        self.carousel_index = 0
        self.is_hidden = False
        self.drag_data = {"x": 0, "y": 0}

        self.add_content()
        self.setup_dragging()
        self.setup_alpha_switch()
        
        self.load_schedule()
        self.update_time()
        self.check_task_status()

    def load_schedule(self):
        """Load schedule and reset today's task queue"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "rb") as f:
                    self.schedule_data = pickle.load(f)
            except Exception:
                self.schedule_data = [[], [], [], [], [], [], []]
        else:
            self.schedule_data = [[], [], [], [], [], [], []]
        
        self.reset_today_queue()
        self.carousel_index = 0
        self.task_label.config(text="Refreshed ✓", fg="#34d399")
        self.root.after(1500, self.refresh_display)

    def refresh_display(self):
        self.check_task_status()

    def reset_today_queue(self):
        now = datetime.now()
        current_weekday = now.weekday()  # 0=Mon, 6=Sun
        today_plans = self.schedule_data[current_weekday]
        self.task_queue = sorted(today_plans, key=lambda x: x[0])
        self.last_popped_task = None

    def add_content(self):
        # Top-left title
        self.title_label = tk.Label(self.root, text="Plan Manager", fg="#93c5fd", bg="#1e3a8a", 
                                    font=("Microsoft YaHei", 8))
        self.title_label.place(x=12, y=8)
        
        # 🌙 Sleep button
        self.sleep_btn = tk.Label(self.root, text="🌙", bg="#1e3a8a", fg="white", 
                                  font=("Arial", 11), cursor="hand2")
        self.sleep_btn.place(x=self.width-32, y=6, width=22, height=22)
        self.sleep_btn.bind("<Button-1>", self.go_to_sleep)

        # 🔄 Refresh button
        self.refresh_btn = tk.Label(self.root, text="🔄", bg="#1e3a8a", fg="white", 
                                    font=("Arial", 10), cursor="hand2")
        self.refresh_btn.place(x=self.width-58, y=7, width=20, height=20)
        self.refresh_btn.bind("<Button-1>", self.refresh_schedule)

        # Time display
        self.time_label = tk.Label(self.root, text="", fg="white", bg="#1e3a8a", 
                                   font=("Consolas", 18, "bold"))
        self.time_label.place(relx=0.5, rely=0.20, anchor="center")
        
        # Date display
        self.date_label = tk.Label(self.root, text="", fg="#bfdbfe", bg="#1e3a8a", 
                                   font=("Microsoft YaHei", 9))
        self.date_label.place(relx=0.5, rely=0.38, anchor="center")
        
        # Task display area
        self.task_label = tk.Label(self.root, text="", bg="#1e3a8a", 
                                   font=("Microsoft YaHei", 12, "bold"), justify="center")
        self.task_label.place(relx=0.5, rely=0.65, anchor="center")
        self.task_label.config(wraplength=290)

    def refresh_schedule(self, event=None):
        """Refresh button click handler"""
        self.load_schedule()
        if self.is_hidden:
            self.wake_up()
        self.show_toast("Schedule Refreshed", "Latest schedule loaded")

    def go_to_sleep(self, event=None):
        """Click 🌙 to enter stealth mode"""
        self.root.attributes("-alpha", self.hidden_alpha)
        self.is_hidden = True
        self.sleep_btn.config(fg="#64748b", text="🌙")

    def wake_up(self):
        """Wake up when triggered by task switch"""
        if self.is_hidden:
            self.root.attributes("-alpha", self.normal_alpha)
            self.is_hidden = False
            self.sleep_btn.config(fg="white", text="🌙")

    def show_toast(self, title, body):
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
        current_time = time.strftime("%H:%M:%S")
        self.time_label.config(text=current_time)
        
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        weekday_str = weekdays[now.weekday()]
        self.date_label.config(text=f"{date_str} {weekday_str}")
        
        self.root.after(1000, self.update_time)

    def check_task_status(self):
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        if not self.task_queue:
            self.task_label.config(text="Today's plan completed", fg="#c4b5fd")
            self.root.after(1000, self.check_task_status)
            return

        popped = False
        popped_task = None
        while len(self.task_queue) >= 2 and self.task_queue[1][0] <= current_time_str:
            popped_task = self.task_queue.pop(0)
            popped = True
        
        if popped and self.task_queue:
            current_plan = self.task_queue[0]
            title = "Task Switch Notification"
            body = f"{popped_task[0]} {popped_task[1]} ended\nNow starting: {current_plan[0]} {current_plan[1]}"
            
            self.wake_up()
            
            if hasattr(self, '_last_popup_time'):
                if time.time() - self._last_popup_time > 2:
                    self.show_toast(title, body)
                    self._last_popup_time = time.time()
            else:
                self.show_toast(title, body)
                self._last_popup_time = time.time()

        if not self.task_queue:
            self.task_label.config(text="Today's plan completed", fg="#c4b5fd")
            self.root.after(1000, self.check_task_status)
            return

        t1, p1 = self.task_queue[0]
        is_task1_started = t1 <= current_time_str

        if not is_task1_started:
            self.task_label.config(text=f"Upcoming: {t1} {p1}", fg="#93c5fd")
            self.root.after(1000, self.check_task_status)
            return

        display_list = []
        display_list.append(f"{t1} {p1}")
        if len(self.task_queue) >= 2:
            t2, p2 = self.task_queue[1]
            display_list.append(f"{t2} {p2}")
        if len(self.task_queue) >= 3:
            t3, p3 = self.task_queue[2]
            display_list.append(f"{t3} {p3}")

        self.carousel_index = (self.carousel_index + 1) % len(display_list)
        current_text = display_list[self.carousel_index]
        
        if self.carousel_index == 0:
            self.task_label.config(text=current_text, fg="#c4b5fd")
        else:
            self.task_label.config(text=current_text, fg="#bfdbfe")

        self.root.after(2500, self.check_task_status)

    def setup_dragging(self):
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
        self.root.bind("<Enter>", self.on_mouse_enter)
        self.root.bind("<Leave>", self.on_mouse_leave)

    def on_mouse_enter(self, event):
        if not self.is_hidden:
            self.root.attributes("-alpha", self.normal_alpha)

    def on_mouse_leave(self, event):
        if not self.is_hidden:
            self.root.attributes("-alpha", self.idle_alpha)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = FloatingWindow()
    app.run()
