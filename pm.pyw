import tkinter as tk  # 导入tkinter，用于创建图形界面
import time  # 导入time，用于获取当前时间
import pickle  # 导入pickle，用于序列化/反序列化数据（保存和加载计划）
from datetime import datetime  # 导入datetime，用于处理日期和时间
from plyer import notification  # 导入plyer，用于发送系统通知（Windows右下角弹窗）

DATA_FILE = "scheduler.dat"  # 定义存储计划数据的文件名

class FloatingWindow:
    """浮动窗口类 - 在屏幕右上角显示一个半透明的悬浮窗"""
    
    def __init__(self):
        """初始化窗口，设置所有属性和组件"""
        self.root = tk.Tk()  # 创建tkinter主窗口
        
        # ============ 窗口尺寸设置 ============
        # 面积约为原版的60%（宽高各乘以√0.6 ≈ 0.775）
        self.width = 310   # 窗口宽度（原400 * 0.775）
        self.height = 194  # 窗口高度（原250 * 0.775）
        
        # ============ 窗口样式设置 ============
        self.root.overrideredirect(True)  # 移除窗口标题栏、边框，创建无边框窗口
        self.root.attributes("-topmost", True)  # 窗口置顶，始终显示在最前面
        
        # ============ 透明度设置 ============
        self.normal_alpha = 0.85  # 正常模式透明度（85%不透明）
        self.idle_alpha = 0.3     # 空闲模式透明度（30%不透明，鼠标移出时）
        self.hidden_alpha = 0.0   # 隐身模式透明度（完全透明）
        self.root.attributes("-alpha", self.normal_alpha)  # 应用正常透明度
        
        # ============ 窗口位置设置 ============
        screen_width = self.root.winfo_screenwidth()   # 获取屏幕宽度
        screen_height = self.root.winfo_screenheight() # 获取屏幕高度
        x = screen_width - self.width - 50  # 计算X坐标：屏幕右边缘 - 窗口宽度 - 50px边距
        y = screen_height - self.height - 100  # 计算Y坐标：屏幕底部 - 窗口高度 - 100px边距
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")  # 设置窗口位置
        
        # ============ 数据存储 ============
        self.root.configure(bg="#1e3a8a")  # 设置背景色为深蓝色
        self.schedule_data = [[], [], [], [], [], [], []]  # 7个列表，分别存储周一到周日的计划
        self.task_queue = []  # 当前任务队列（今天的计划，按时间排序）
        self.last_popped_task = None  # 记录最后一个完成的任务（用于调试）
        self.carousel_index = 0  # 轮播当前索引（显示哪个任务）
        self.is_hidden = False  # 窗口是否处于隐身模式（完全透明）
        self.drag_data = {"x": 0, "y": 0}  # 拖拽数据，记录鼠标按下时的位置
        
        # ============ 计时器管理 ============
        self._last_popup_time = 0  # 上次发送通知的时间，用于防止通知刷屏
        self.display_list = []  # 当前显示的轮播列表（缓存）
        self.carousel_running = False  # 轮播是否正在运行
        self.carousel_after_id = None  # 轮播的定时器ID，用于取消
        self.check_after_id = None  # 任务检查的定时器ID，用于取消
        self.refreshing = False  # 是否正在刷新中（防止重复刷新）

        # ============ 初始化界面 ============
        self.add_content()  # 添加所有UI组件
        self.setup_dragging()  # 设置窗口拖拽功能
        self.setup_alpha_switch()  # 设置鼠标悬停透明度切换
        
        # ============ 加载数据并启动 ============
        self.load_schedule()  # 从文件加载计划数据
        self.update_time()  # 启动时间更新
        self.start_check_task_status()  # 启动任务检查

    def load_schedule(self):
        """从文件加载计划数据，并重置今天的任务队列"""
        try:
            with open(DATA_FILE, "rb") as f:  # 以二进制读取模式打开
                self.schedule_data = pickle.load(f)  # 反序列化加载数据
        except Exception:  # 如果文件损坏或格式错误
            self.schedule_data = [[], [], [], [], [], [], []]  # 重置为空数据
        
        self.reset_today_queue()  # 重置今天的任务队列
        self.reset_carousel()  # 重置轮播状态

    def reset_carousel(self):
        """重置轮播状态 - 停止轮播，清除缓存"""
        # 取消正在运行的轮播定时器
        if self.carousel_after_id:
            self.root.after_cancel(self.carousel_after_id)  # 取消定时器
            self.carousel_after_id = None  # 清空ID
        
        self.carousel_running = False  # 标记轮播已停止
        self.carousel_index = 0  # 重置索引到0
        self.display_list = []  # 清空显示列表缓存

    def reset_today_queue(self):
        """重置今天的任务队列 - 从schedule_data中提取今天的计划并排序"""
        now = datetime.now()  # 获取当前时间
        current_weekday = now.weekday()  # 获取今天是星期几（0=周一, 6=周日）
        today_plans = self.schedule_data[current_weekday]  # 获取今天的计划列表
        self.task_queue = sorted(today_plans, key=lambda x: x[0])  # 按时间排序（x[0]是时间）
        self.last_popped_task = None  # 清空上一个完成的任务

    def add_content(self):
        """添加所有UI组件到窗口"""
        
        # ===== 左上角标题 =====
        self.title_label = tk.Label(
            self.root,  # 父容器
            text="Plan Manager",  # 显示文字
            fg="#93c5fd",  # 前景色（浅蓝色）
            bg="#1e3a8a",  # 背景色（深蓝色）
            font=("Microsoft YaHei", 8)  # 字体和大小
        )
        self.title_label.place(x=12, y=8)  # 放置在左上角
        
        # ===== 休眠按钮（🌙） =====
        self.sleep_btn = tk.Label(
            self.root,
            text="🌙",  # 月亮图标
            bg="#1e3a8a",
            fg="white",
            font=("Arial", 11),
            cursor="hand2"  # 鼠标悬停时变为手型
        )
        self.sleep_btn.place(x=self.width-32, y=6, width=22, height=22)  # 放在右上角
        self.sleep_btn.bind("<Button-1>", self.go_to_sleep)  # 点击时调用go_to_sleep
        
        # ===== 刷新按钮（🔄） =====
        self.refresh_btn = tk.Label(
            self.root,
            text="🔄",  # 刷新图标
            bg="#1e3a8a",
            fg="white",
            font=("Arial", 10),
            cursor="hand2"
        )
        self.refresh_btn.place(x=self.width-58, y=7, width=20, height=20)  # 放在休眠按钮左边
        self.refresh_btn.bind("<Button-1>", self.refresh_schedule)  # 点击时刷新
        
        # ===== 时间显示 =====
        self.time_label = tk.Label(
            self.root,
            text="",  # 初始为空，由update_time更新
            fg="white",
            bg="#1e3a8a",
            font=("Consolas", 18, "bold")  # 等宽字体，粗体
        )
        self.time_label.place(relx=0.5, rely=0.20, anchor="center")  # 居中，位于窗口20%高度
        
        # ===== 日期显示 =====
        self.date_label = tk.Label(
            self.root,
            text="",
            fg="#bfdbfe",  # 浅蓝色
            bg="#1e3a8a",
            font=("Microsoft YaHei", 9)
        )
        self.date_label.place(relx=0.5, rely=0.38, anchor="center")  # 居中，位于窗口38%高度
        
        # ===== 任务显示区域 =====
        self.task_label = tk.Label(
            self.root,
            text="",
            bg="#1e3a8a",
            font=("Microsoft YaHei", 12, "bold"),
            justify="center"  # 文字居中
        )
        self.task_label.place(relx=0.5, rely=0.65, anchor="center")  # 居中，位于窗口65%高度
        self.task_label.config(wraplength=290)  # 文字宽度超过290px时自动换行

    def refresh_schedule(self, event=None):
        """刷新按钮点击处理 - 重新加载计划"""
        if self.refreshing:  # 如果正在刷新，直接返回防止重复
            return
        
        self.refreshing = True  # 标记开始刷新
        
        # ===== 取消所有正在运行的定时器 =====
        if self.carousel_after_id:
            self.root.after_cancel(self.carousel_after_id)  # 取消轮播
            self.carousel_after_id = None
        if self.check_after_id:
            self.root.after_cancel(self.check_after_id)  # 取消任务检查
            self.check_after_id = None
        
        # ===== 重置状态 =====
        self.reset_carousel()  # 重置轮播
        self.carousel_running = False
        
        # ===== 重新加载数据 =====
        self.load_schedule()  # 从文件加载新计划
        
        # ===== 立即显示第一个任务 =====
        self.update_display_after_refresh()
        
        # ===== 如果窗口在隐身模式，唤醒 =====
        if self.is_hidden:
            self.wake_up()
        
        # ===== 发送通知 =====
        self.show_toast("Schedule Refreshed", "Latest schedule loaded")
        
        # ===== 延迟重启任务检查 =====
        # 延迟3秒后重启，避免刷新后立即触发任务切换
        self.root.after(3000, self.restart_after_refresh)

    def update_display_after_refresh(self):
        """刷新后立即更新显示（不触发任何切换逻辑）"""
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")  # 格式化为"HH:MM"
        
        # 如果任务队列为空，显示"已完成"
        if not self.task_queue:
            self.task_label.config(text="Today's plan completed", fg="#c4b5fd")
            self.refreshing = False
            return
        
        # 获取第一个任务
        t1, p1 = self.task_queue[0]
        is_task1_started = t1 <= current_time_str  # 检查任务是否已开始
        
        # 如果任务还没开始，显示"即将进行"
        if not is_task1_started:
            self.task_label.config(text=f"Upcoming: {t1} {p1}", fg="#93c5fd")
            self.refreshing = False
            return
        
        # 任务已开始，显示第一个任务（紫色）
        self.update_display_list()  # 生成显示列表
        if self.display_list:
            self.task_label.config(text=self.display_list[0], fg="#c4b5fd")
            self.carousel_index = 0  # 重置索引

    def restart_after_refresh(self):
        """刷新完成后重启任务检查"""
        self.refreshing = False  # 标记刷新结束
        self.carousel_running = False  # 重置轮播状态
        self.start_check_task_status()  # 重新开始任务检查

    def go_to_sleep(self, event=None):
        """点击🌙进入隐身模式 - 窗口完全透明"""
        self.root.attributes("-alpha", self.hidden_alpha)  # 设置透明度为0
        self.is_hidden = True  # 标记为隐身
        self.sleep_btn.config(fg="#64748b", text="🌙")  # 按钮颜色变灰

    def wake_up(self):
        """唤醒窗口 - 从隐身模式恢复"""
        if self.is_hidden:  # 如果当前是隐身状态
            self.root.attributes("-alpha", self.normal_alpha)  # 恢复透明度
            self.is_hidden = False  # 取消隐身标记
            self.sleep_btn.config(fg="white", text="🌙")  # 按钮恢复白色

    def show_toast(self, title, body):
        """发送系统通知（Windows右下角弹窗）"""
        try:
            notification.notify(
                title=title,  # 通知标题
                message=body,  # 通知内容
                app_name='Plan Manager',  # 应用名称
                timeout=5  # 显示时长（秒）
            )
        except Exception:  # 如果发送失败，静默忽略
            pass

    def update_time(self):
        """每秒更新一次时间和日期显示"""
        current_time = time.strftime("%H:%M:%S")  # 格式化为"HH:MM:SS"
        self.time_label.config(text=current_time)  # 更新时间显示
        
        # ===== 更新日期 =====
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")  # 格式化为"YYYY-MM-DD"
        weekday_str = weekdays[now.weekday()]  # 获取星期几的英文名
        self.date_label.config(text=f"{date_str} {weekday_str}")  # 更新日期显示
        
        # 每秒调用一次自己，实现持续更新
        self.root.after(1000, self.update_time)

    def start_check_task_status(self):
        """启动任务状态检查循环"""
        if self.check_after_id:  # 如果有旧的定时器，取消
            self.root.after_cancel(self.check_after_id)
        self.check_task_status()  # 开始第一次检查

    def check_task_status(self):
        """检查任务状态（每秒执行一次）"""
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")  # 当前时间（HH:MM格式）
        
        # ===== 如果正在刷新，跳过检查 =====
        if self.refreshing:
            self.check_after_id = self.root.after(1000, self.check_task_status)
            return
        
        # ===== 如果任务队列为空，显示"已完成" =====
        if not self.task_queue:
            self.task_label.config(text="Today's plan completed", fg="#c4b5fd")
            self.carousel_running = False
            self.check_after_id = self.root.after(1000, self.check_task_status)
            return

        # ===== 检查是否有任务需要结束 =====
        # 规则：如果队列中至少有2个任务，且第二个任务已经到时间
        # 说明第一个任务应该结束了
        task_switched = False  # 标记是否有任务切换
        while len(self.task_queue) >= 2 and self.task_queue[1][0] <= current_time_str:
            # 弹出第一个任务（它已经结束了）
            ended_task = self.task_queue.pop(0)
            self.last_popped_task = ended_task
            task_switched = True
            
            # 如果队列还有任务，发送切换通知
            if self.task_queue:
                current_plan = self.task_queue[0]  # 新的第一个任务
                title = "Task Switch Notification"
                body = f"{ended_task[0]} {ended_task[1]} ended\nNow starting: {current_plan[0]} {current_plan[1]}"
                
                self.wake_up()  # 如果窗口在隐身模式，唤醒
                
                # 防止通知刷屏：至少间隔2秒
                if time.time() - self._last_popup_time > 2:
                    self.show_toast(title, body)
                    self._last_popup_time = time.time()
            
            # 如果队列为空，退出循环
            if not self.task_queue:
                break

        # ===== 如果任务切换了，重置轮播 =====
        if task_switched:
            self.reset_carousel()  # 停止当前轮播
            self.update_display_list()  # 更新显示列表
            self.carousel_index = 0
            # 立即显示第一个任务（紫色高亮）
            if self.display_list:
                self.task_label.config(text=self.display_list[0], fg="#c4b5fd")
        
        # ===== 如果队列为空，显示"已完成" =====
        if not self.task_queue:
            self.task_label.config(text="Today's plan completed", fg="#c4b5fd")
            self.carousel_running = False
            self.check_after_id = self.root.after(1000, self.check_task_status)
            return

        # ===== 检查第一个任务是否已开始 =====
        t1, p1 = self.task_queue[0]
        is_task1_started = t1 <= current_time_str

        # 如果任务还没开始，显示"即将进行"
        if not is_task1_started:
            self.task_label.config(text=f"Upcoming: {t1} {p1}", fg="#93c5fd")
            self.carousel_running = False
            self.check_after_id = self.root.after(1000, self.check_task_status)
            return

        # ===== 更新显示列表 =====
        if not self.display_list or task_switched:
            self.update_display_list()
            self.carousel_index = 0
        
        # ===== 如果轮播未开始，启动它 =====
        if not self.carousel_running and self.display_list:
            self.carousel_running = True
            # 延迟1秒后启动轮播，让用户先看到第一个任务
            self.carousel_after_id = self.root.after(1000, self.start_carousel)
        
        # ===== 继续下一次检查（1秒后） =====
        self.check_after_id = self.root.after(1000, self.check_task_status)

    def update_display_list(self):
        """生成轮播显示列表 - 包含当前任务和接下来的两个任务"""
        self.display_list = []  # 清空列表
        if not self.task_queue:  # 如果没有任务，直接返回
            return
        
        # 添加第一个任务（当前任务）
        t1, p1 = self.task_queue[0]
        self.display_list.append(f"{t1} {p1}")  # 格式："时间 任务名"
        
        # 添加第二个任务（如果有）
        if len(self.task_queue) >= 2:
            t2, p2 = self.task_queue[1]
            self.display_list.append(f"{t2} {p2}")
        
        # 添加第三个任务（如果有）
        if len(self.task_queue) >= 3:
            t3, p3 = self.task_queue[2]
            self.display_list.append(f"{t3} {p3}")

    def start_carousel(self):
        """启动轮播 - 每2.5秒切换一次显示"""
        # 如果轮播已停止、没有显示内容、或正在刷新，停止轮播
        if not self.carousel_running or not self.display_list or self.refreshing:
            self.carousel_running = False
            return
        
        # 切换到下一个任务（循环索引）
        self.carousel_index = (self.carousel_index + 1) % len(self.display_list)
        current_text = self.display_list[self.carousel_index]
        
        # 根据索引设置颜色：第一个任务用紫色，其他用浅蓝色
        if self.carousel_index == 0:
            self.task_label.config(text=current_text, fg="#c4b5fd")  # 紫色
        else:
            self.task_label.config(text=current_text, fg="#bfdbfe")  # 浅蓝色
        
        # 2.5秒后再次调用自己，实现循环轮播
        self.carousel_after_id = self.root.after(2500, self.start_carousel)

    def setup_dragging(self):
        """设置窗口拖拽功能 - 用户可以通过拖拽窗口移动位置"""
        
        def start_move(event):
            """鼠标按下时，记录当前鼠标位置"""
            self.drag_data["x"] = event.x  # 记录鼠标在窗口内的X坐标
            self.drag_data["y"] = event.y  # 记录鼠标在窗口内的Y坐标

        def on_move(event):
            """鼠标拖拽时，移动窗口"""
            # 计算鼠标移动的距离
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            
            # 计算窗口新位置
            new_x = self.root.winfo_x() + dx
            new_y = self.root.winfo_y() + dy
            
            # 限制窗口不超出屏幕边界
            new_x = max(-self.width + 10, min(new_x, self.root.winfo_screenwidth() - 10))
            new_y = max(-self.height + 10, min(new_y, self.root.winfo_screenheight() - 10))
            
            # 移动窗口到新位置
            self.root.geometry(f"+{new_x}+{new_y}")

        # 绑定鼠标事件
        self.root.bind("<ButtonPress-1>", start_move)  # 鼠标左键按下
        self.root.bind("<B1-Motion>", on_move)  # 鼠标左键拖拽

    def setup_alpha_switch(self):
        """设置鼠标悬停透明度切换 - 悬停时变亮，移出时变暗"""
        self.root.bind("<Enter>", self.on_mouse_enter)  # 鼠标进入窗口
        self.root.bind("<Leave>", self.on_mouse_leave)  # 鼠标离开窗口

    def on_mouse_enter(self, event):
        """鼠标进入窗口时，恢复完全不透明"""
        if not self.is_hidden:  # 如果不在隐身模式
            self.root.attributes("-alpha", self.normal_alpha)  # 设置为正常透明度

    def on_mouse_leave(self, event):
        """鼠标离开窗口时，变为半透明"""
        if not self.is_hidden:  # 如果不在隐身模式
            self.root.attributes("-alpha", self.idle_alpha)  # 设置为空闲透明度

    def run(self):
        """启动主循环 - 显示窗口并开始事件处理"""
        self.root.mainloop()  # tkinter的主事件循环

# ===== 程序入口 =====
if __name__ == "__main__":
    app = FloatingWindow()  # 创建窗口实例
    app.run()  # 启动程序
