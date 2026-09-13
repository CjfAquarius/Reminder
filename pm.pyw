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
VERSION_FILE = "version.txt"  # 版本信息文件
# 更新相关常量
REPO_OWNER = "CjfAquarius"
REPO_NAME = "Reminder"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
EXE_NAME = "setup.exe"

# GitHub 加速站列表（按优先级排序）
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
        
        # ============ 窗口尺寸设置 ============
        self.width = 310
        self.height = 194
        
        # ============ 窗口样式设置 ============
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # ============ 透明度设置 ============
        self.normal_alpha = 0.85
        self.idle_alpha = 0.5
        self.hidden_alpha = 0.0
        self.root.attributes("-alpha", self.normal_alpha)
        
        # ============ 窗口位置设置 ============
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - self.width - 50
        y = screen_height - self.height - 100
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        
        # ============ 数据存储 ============
        self.root.configure(bg="#1e3a8a")
        self.schedule_data = [[], [], [], [], [], [], []]
        self.task_queue = []
        self.last_popped_task = None
        self.carousel_index = 0
        self.is_hidden = False
        self.drag_data = {"x": 0, "y": 0}
        
        # ============ 计时器管理 ============
        self._last_popup_time = 0
        self.display_list = []
        self.carousel_running = False
        self.carousel_after_id = None
        self.check_after_id = None
        self.refreshing = False
        
        # ============ 更新相关 ============
        self.update_in_progress = False
        self.current_version = self._read_version()  # 从version.txt读取版本

        # ============ 初始化界面 ============
        self.add_content()
        self.setup_dragging()
        self.setup_alpha_switch()
        
        # ============ 加载数据并启动 ============
        self.load_schedule()
        self.update_time()
        self.start_check_task_status()

    def _read_version(self):
        """从version.txt读取版本号，如果文件不存在则返回默认版本"""
        try:
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                    version = f.read().strip()
                    if version:
                        return version
        except Exception:
            pass
        return "1.0.0"  # 默认版本

    def _get_accelerated_url(self, original_url):
        """将GitHub下载链接转换为加速站链接"""
        for accelerator in ACCELERATORS:
            # 尝试不同的加速站格式
            # 格式1: https://加速站/https://github.com/...
            url1 = f"{accelerator}/{original_url}"
            # 格式2: https://加速站/github.com/... (部分加速站不需要https://前缀)
            if original_url.startswith("https://"):
                url2 = f"{accelerator}/{original_url[8:]}"
            else:
                url2 = f"{accelerator}/{original_url}"
            
            # 返回第一个可用的加速站（这里简单返回，实际使用时会尝试连接）
            # 优先使用格式1
            return url1
        
        return original_url  # 如果没有加速站可用，使用原链接

    def _download_with_accelerator(self, download_url, exe_path, timeout=60):
        """使用加速站下载文件，如果失败则尝试下一个加速站"""
        # 获取原始URL的文件名部分
        file_name = download_url.split('/')[-1]
        
        # 构建加速站URL列表
        accelerated_urls = []
        for accelerator in ACCELERATORS:
            # 尝试不同的格式
            accelerated_urls.append(f"{accelerator}/{download_url}")
            if download_url.startswith("https://"):
                accelerated_urls.append(f"{accelerator}/{download_url[8:]}")
        
        # 依次尝试每个加速站
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
                    # 检查响应状态
                    if response.status == 200:
                        with open(exe_path, 'wb') as f:
                            f.write(response.read())
                        return True, url  # 下载成功
            except Exception as e:
                # 当前加速站失败，尝试下一个
                continue
        
        # 所有加速站都失败，尝试直接下载原始URL
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
        """从文件加载计划数据，并重置今天的任务队列"""
        try:
            with open(DATA_FILE, "rb") as f:
                self.schedule_data = pickle.load(f)
        except Exception:
            self.schedule_data = [[], [], [], [], [], [], []]
        
        self.reset_today_queue()
        self.reset_carousel()

    def reset_carousel(self):
        """重置轮播状态"""
        if self.carousel_after_id:
            self.root.after_cancel(self.carousel_after_id)
            self.carousel_after_id = None
        
        self.carousel_running = False
        self.carousel_index = 0
        self.display_list = []

    def reset_today_queue(self):
        """重置今天的任务队列"""
        now = datetime.now()
        current_weekday = now.weekday()
        today_plans = self.schedule_data[current_weekday]
        self.task_queue = sorted(today_plans, key=lambda x: x[0])
        self.last_popped_task = None

    def add_content(self):
        """添加所有UI组件到窗口"""
        # ===== 左上角标题 =====
        self.title_label = tk.Label(
            self.root,
            text="Plan Manager",
            fg="#93c5fd",
            bg="#1e3a8a",
            font=("Microsoft YaHei", 8)
        )
        self.title_label.place(x=12, y=8)
        
        # ===== 休眠按钮（🌙） =====
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
        
        # ===== 刷新按钮（🔄） =====
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
        
        # ===== 更新按钮（🆕） =====
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
        
        # ===== 时间显示 =====
        self.time_label = tk.Label(
            self.root,
            text="",
            fg="white",
            bg="#1e3a8a",
            font=("Consolas", 18, "bold")
        )
        self.time_label.place(relx=0.5, rely=0.20, anchor="center")
        
        # ===== 日期显示 =====
        self.date_label = tk.Label(
            self.root,
            text="",
            fg="#bfdbfe",
            bg="#1e3a8a",
            font=("Microsoft YaHei", 9)
        )
        self.date_label.place(relx=0.5, rely=0.38, anchor="center")
        
        # ===== 任务显示区域 =====
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
        """刷新按钮点击处理"""
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
        """刷新后立即更新显示"""
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
        """刷新完成后重启任务检查"""
        self.refreshing = False
        self.carousel_running = False
        self.start_check_task_status()

    def go_to_sleep(self, event=None):
        """进入隐身模式"""
        self.root.attributes("-alpha", self.hidden_alpha)
        self.is_hidden = True
        self.sleep_btn.config(fg="#64748b", text="🌙")

    def wake_up(self):
        """唤醒窗口"""
        if self.is_hidden:
            self.root.attributes("-alpha", self.normal_alpha)
            self.is_hidden = False
            self.sleep_btn.config(fg="white", text="🌙")

    def show_toast(self, title, body):
        """发送系统通知"""
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
        """每秒更新时间和日期"""
        current_time = time.strftime("%H:%M:%S")
        self.time_label.config(text=current_time)
        
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        weekday_str = weekdays[now.weekday()]
        self.date_label.config(text=f"{date_str} {weekday_str}")
        
        self.root.after(1000, self.update_time)

    def start_check_task_status(self):
        """启动任务状态检查循环"""
        if self.check_after_id:
            self.root.after_cancel(self.check_after_id)
        self.check_task_status()

    def check_task_status(self):
        """检查任务状态（每秒执行）"""
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
        """生成轮播显示列表"""
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
        """启动轮播"""
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
        """设置窗口拖拽功能"""
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
        """设置鼠标悬停透明度切换"""
        self.root.bind("<Enter>", self.on_mouse_enter)
        self.root.bind("<Leave>", self.on_mouse_leave)

    def on_mouse_enter(self, event):
        """鼠标进入窗口"""
        if not self.is_hidden:
            self.root.attributes("-alpha", self.normal_alpha)

    def on_mouse_leave(self, event):
        """鼠标离开窗口"""
        if not self.is_hidden:
            self.root.attributes("-alpha", self.idle_alpha)

    # ============ 更新相关方法 ============
    def check_for_updates(self, event=None):
        """检查GitHub Releases是否有更新"""
        if self.update_in_progress:
            return
        
        threading.Thread(target=self._check_updates_thread, daemon=True).start()

    def _check_updates_thread(self):
        """后台线程检查更新"""
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
                raise Exception("无法获取版本号")
            
            latest_major_minor = ".".join(latest_tag.split(".")[:2])
            current_major_minor = ".".join(self.current_version.split(".")[:2])
            
            download_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/{data.get('tag_name', '')}/{EXE_NAME}"
            
            if latest_major_minor <= current_major_minor:
                self.root.after(0, lambda: self._show_update_result("已是最新", f"当前版本 v{self.current_version} 已是最新"))
                return
            
            self.root.after(0, lambda: self._prompt_update(latest_tag, download_url))
            
        except urllib.error.URLError as e:
            self.root.after(0, lambda: self._show_update_result("网络错误", f"连接失败: {str(e)}"))
        except json.JSONDecodeError as e:
            self.root.after(0, lambda: self._show_update_result("数据错误", f"解析响应失败: {str(e)}"))
        except Exception as e:
            self.root.after(0, lambda: self._show_update_result("错误", f"检查更新失败: {str(e)}"))

    def _prompt_update(self, version, download_url):
        """询问用户是否下载更新"""
        result = messagebox.askyesno(
            "发现新版本",
            f"发现新版本 v{version}\n\n当前版本: v{self.current_version}\n\n是否下载并安装更新？",
            icon=messagebox.QUESTION
        )
        if result:
            threading.Thread(target=self._download_and_run, args=(download_url,), daemon=True).start()
        else:
            self.root.after(0, lambda: self.update_btn.config(text="🆕"))

    def _download_and_run(self, download_url):
        """下载setup.exe并运行（使用加速站）"""
        if self.update_in_progress:
            return
        
        self.update_in_progress = True
        
        try:
            self.root.after(0, lambda: self.update_btn.config(text="⬇️"))
            
            temp_dir = tempfile.mkdtemp()
            exe_path = os.path.join(temp_dir, EXE_NAME)
            
            # 使用加速站下载
            self.root.after(0, lambda: self._update_status_label("正在使用加速站下载..."))
            success, used_url = self._download_with_accelerator(download_url, exe_path, timeout=120)
            
            if not success:
                raise Exception("所有下载源均失败，请检查网络连接")
            
            if not os.path.exists(exe_path) or os.path.getsize(exe_path) == 0:
                raise Exception("下载的文件无效或为空")
            
            self.root.after(0, lambda: self.update_btn.config(text="✅"))
            self.root.after(0, lambda: self._launch_and_exit(exe_path))
            
        except Exception as e:
            self.update_in_progress = False
            self.root.after(0, lambda: messagebox.showerror("更新失败", f"下载失败: {str(e)}"))
            self.root.after(0, lambda: self.update_btn.config(text="🆕"))

    def _update_status_label(self, message):
        """更新状态显示（用于显示下载进度）"""
        # 可以在这里更新task_label显示下载状态
        self.task_label.config(text=message, fg="#93c5fd")

    def _launch_and_exit(self, installer_path):
        """启动安装程序并立即退出"""
        try:
            os.startfile(installer_path)
            self._exit_app()
        except Exception as e:
            messagebox.showerror("启动失败", f"无法启动安装程序: {str(e)}")
            self.update_in_progress = False
            self.update_btn.config(text="🆕")

    def _exit_app(self):
        """退出应用"""
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def _show_update_result(self, title, message):
        """显示更新检查结果"""
        self.update_btn.config(text="🆕")
        if "失败" in title or "错误" in title:
            self.update_btn.config(text="❌")
            messagebox.showwarning(title, message)
        else:
            self.update_btn.config(text="✅")
            messagebox.showinfo(title, message)
        self.root.after(2000, lambda: self.update_btn.config(text="🆕"))

    def run(self):
        """启动主循环"""
        self.root.mainloop()

if __name__ == "__main__":
    app = FloatingWindow()
    app.run()
