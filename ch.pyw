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
        self.width = 400
        self.height = 250
        
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
        self.schedule_data = [[], [], [], [], [], [], []] # 0~6
        self.task_queue = []
        self.last_popped_task = None
        self.carousel_index = 0
        self.is_hidden = False
        self.drag_data = {"x": 0, "y": 0} # 修复：正确初始化字典

        self.add_content()
        self.setup_dragging()
        self.setup_alpha_switch()
        
        self.load_schedule()
        self.update_time()
        self.check_task_status()

    def load_schedule(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "rb") as f:
                    self.schedule_data = pickle.load(f)
            except Exception:
                self.schedule_data = [[], [], [], [], [], [], []]
        else:
            self.schedule_data = [[], [], [], [], [], [], []]
        
        self.reset_today_queue()

    def reset_today_queue(self):
        now = datetime.now()
        current_weekday = now.weekday() # 0=周一, 6=周日
        today_plans = self.schedule_data[current_weekday]
        self.task_queue = sorted(today_plans, key=lambda x: x[0])
        self.last_popped_task = None

    def add_content(self):
        # 左上角标题
        self.title_label = tk.Label(self.root, text="计划管理器", fg="#93c5fd", bg="#1e3a8a", 
                                    font=("Microsoft YaHei", 9))
        self.title_label.place(x=15, y=10)
        
        # 🌙 休眠按钮
        self.sleep_btn = tk.Label(self.root, text="🌙", bg="#1e3a8a", fg="white", 
                                  font=("Arial", 14), cursor="hand2")
        self.sleep_btn.place(x=self.width-35, y=8, width=25, height=25)
        self.sleep_btn.bind("<Button-1>", self.go_to_sleep)

        # 时间
        self.time_label = tk.Label(self.root, text="", fg="white", bg="#1e3a8a", 
                                   font=("Consolas", 22, "bold"))
        self.time_label.place(relx=0.5, rely=0.25, anchor="center")
        
        # 日期
        self.date_label = tk.Label(self.root, text="", fg="#bfdbfe", bg="#1e3a8a", 
                                   font=("Microsoft YaHei", 11))
        self.date_label.place(relx=0.5, rely=0.40, anchor="center")
        
        # 任务展示区
        self.task_label = tk.Label(self.root, text="", bg="#1e3a8a", 
                                   font=("Microsoft YaHei", 16, "bold"), justify="center")
        self.task_label.place(relx=0.5, rely=0.65, anchor="center")
        self.task_label.config(wraplength=380)

    def go_to_sleep(self, event=None):
        """点击 🌙 进入隐身模式"""
        self.root.attributes("-alpha", self.hidden_alpha)
        self.is_hidden = True
        self.sleep_btn.config(fg="#64748b", text="🌙")

    def wake_up(self):
        """被任务切换触发唤醒"""
        if self.is_hidden:
            self.root.attributes("-alpha", self.normal_alpha)
            self.is_hidden = False
            self.sleep_btn.config(fg="white", text="🌙")

    def show_toast(self, title, body):
        try:
            notification.notify(
                title=title,
                message=body,
                app_name='计划管理器',
                timeout=5
            )
        except Exception:
            pass

    def update_time(self):
        current_time = time.strftime("%H:%M:%S")
        self.time_label.config(text=current_time)
        
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        weekday_str = weekdays[now.weekday()]
        self.date_label.config(text=f"{date_str} {weekday_str}")
        
        self.root.after(1000, self.update_time)

    def check_task_status(self):
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        if not self.task_queue:
            self.task_label.config(text="今日计划已完成", fg="#c4b5fd")
            self.root.after(1000, self.check_task_status)
            return

        popped = False
        while len(self.task_queue) >= 2 and self.task_queue[1][0] <= current_time_str:
            popped_task = self.task_queue.pop(0)
            popped = True
        
        if popped and self.task_queue:
            current_plan = self.task_queue[0]
            title = "任务切换通知"
            body = f"{popped_task[0]} {popped_task[1]} 已结束\n现在开始：{current_plan[0]} {current_plan[1]}"
            
            self.wake_up()
            
            if hasattr(self, '_last_popup_time'):
                if time.time() - self._last_popup_time > 2:
                    self.show_toast(title, body)
                    self._last_popup_time = time.time()
            else:
                self.show_toast(title, body)
                self._last_popup_time = time.time()

        if not self.task_queue:
            self.task_label.config(text="今日计划已完成", fg="#c4b5fd")
            self.root.after(1000, self.check_task_status)
            return

        t1, p1 = self.task_queue[0]
        is_task1_started = t1 <= current_time_str

        if not is_task1_started:
            self.task_label.config(text=f"即将进行：{t1} {p1}", fg="#93c5fd")
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
        # 修复：移除错误的 self.drag_data 重新赋值逻辑
        def start_move(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        def on_move(event):
            # 修复：这里的 y 用正确的 self.drag_data["y"]，而不是 "dy"
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
