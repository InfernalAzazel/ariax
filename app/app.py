import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
import threading
import time
import os
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from components.connection_panel import ConnectionPanel
from components.download_panel import DownloadPanel
from components.task_list import TaskList
from components.config_window import ConfigWindow
from components.log_window import LogWindow
from lib.aria2 import Aria2


class Aria2GUI:
    """Aria2 GUI主应用程序"""
    
    def __init__(self) -> None:
        # 创建主窗口
        self.root: ttk.Window = ttk.Window()
        self.root.title("Aria2 GUI 下载器")
        # 居中显示主窗口
        self.center_window(self.root, 1600, 1500)
        
        # 创建菜单栏
        self.create_menu()
        
        # 设置窗口图标（如果有的话）
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 创建Aria2服务管理器
        self.aria2_service: Aria2 = Aria2()
        self.aria2_service.set_callbacks(
            on_status_change=self.on_service_status_change,
            on_connection_change=self.on_connection_change
        )
        
        # 创建界面组件
        self.connection_panel: ConnectionPanel
        self.download_panel: DownloadPanel
        self.task_list: TaskList
        self.status_bar: ttk.Label
        
        # 创建界面
        self.create_widgets()
        
        # 初始化
        self.initialize()
    
    def center_window(self, window: ttk.Window, width: int, height: int, parent: Optional[ttk.Window] = None) -> None:
        """将窗口居中显示"""
        if parent:
            # 相对于父窗口居中
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            
            x = parent_x + (parent_width - width) // 2
            y = parent_y + (parent_height - height) // 2
        else:
            # 相对于屏幕居中
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
        
        # 确保窗口不会超出屏幕边界
        x = max(0, x)
        y = max(0, y)
        
        window.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self) -> None:
        """创建GUI组件"""
        # 创建主框架
        main_frame: ttk.Frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=BOTH, expand=True)
        
        # 创建连接配置面板
        self.connection_panel = ConnectionPanel(
            main_frame,
            on_connect_callback=self.connect_aria2,
            on_service_callback=self.handle_service_action
        )
        
        # 创建下载面板
        self.download_panel = DownloadPanel(
            main_frame,
            on_add_download_callback=self.add_download
        )
        
        # 创建任务列表
        self.task_list = TaskList(
            main_frame,
            on_pause_callback=self.pause_selected,
            on_resume_callback=self.resume_selected,
            on_remove_callback=self.remove_selected,
            on_refresh_callback=self.refresh_tasks,
            on_open_folder_callback=self.open_task_folder
        )
        
        # 初始化配置和日志窗口
        self.config_window = ConfigWindow(
            self.root, 
            on_config_save=self.on_config_save
        )
        self.log_window = LogWindow(self.root)
        
        # 创建状态栏
        self.status_bar = ttk.Label(
            main_frame, 
            text="就绪", 
            bootstyle="info",
            relief="sunken",
            anchor="w"
        )
        self.status_bar.pack(fill=X, pady=(10, 0))
        
        # 刷新时间标签
        self.refresh_time_label = ttk.Label(
            main_frame,
            text="",
            bootstyle="secondary",
            font=("Arial", 8)
        )
        self.refresh_time_label.pack(anchor="e", pady=(2, 0))
    
    def initialize(self) -> None:
        """初始化应用程序"""
        # 初始检查服务状态
        self.update_service_status()
        
        # 自动尝试连接
        self.auto_connect()
        
        # 开始自动刷新任务列表
        self.start_auto_refresh()
        
        # 开始定期检查服务状态
        self.start_service_status_check()
    
    def auto_connect(self) -> None:
        """自动连接（在后台线程中执行）"""
        def connect_thread():
            import time
            time.sleep(1)  # 等待界面完全加载
            
            # 检查服务状态
            if not self.aria2_service.is_running():
                print("服务未运行，尝试自动启动...")
                if self.start_aria2c():
                    time.sleep(3)  # 等待服务启动
                else:
                    print("自动启动服务失败")
                    return
            
            # 尝试连接
            config = self.connection_panel.get_connection_config()
            if self.aria2_service.connect(config['host'], config['port'], config['secret']):
                self.root.after(0, lambda: self.status_bar.config(text="已自动连接到Aria2服务器"))
            else:
                self.root.after(0, lambda: self.status_bar.config(text="自动连接失败，请点击'自动连接'按钮"))
        
        # 在后台线程中执行自动连接
        import threading
        connect_thread_obj = threading.Thread(target=connect_thread, daemon=True)
        connect_thread_obj.start()
        
    def create_menu(self) -> None:
        """创建菜单栏"""
        menubar = ttk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = ttk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="配置", command=self.show_config_window)
        file_menu.add_command(label="日志", command=self.show_log_window)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 工具菜单
        tools_menu = ttk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="刷新任务", command=self.refresh_tasks)
        tools_menu.add_command(label="清空任务", command=self.clear_tasks)
        
        # 帮助菜单
        help_menu = ttk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
        
    def show_config_window(self) -> None:
        """显示配置窗口"""
        self.config_window.show()
        
    def show_log_window(self) -> None:
        """显示日志窗口"""
        self.log_window.show()
        
    def show_about(self) -> None:
        """显示关于对话框"""
        Messagebox.show_info(
            "关于 Aria2 GUI",
            "Aria2 GUI 下载管理器\n\n"
            "基于 aria2p 和 ttkbootstrap 构建\n"
            "支持多线程下载、代理配置、任务管理等功能",
            parent=self.root
        )
        
    def clear_tasks(self) -> None:
        """清空任务列表"""
        if Messagebox.show_question(
            "确认清空",
            "确定要清空所有任务吗？",
            parent=self.root
        ) == "是":
            self.task_list.clear_tasks()
    
    def on_config_save(self, config: Dict[str, Any]) -> None:
        """配置保存回调"""
        # 重新加载连接面板的配置
        self.connection_panel.config = config
        self.connection_panel.update_config_info()
        
        # 如果代理配置发生变化，重新设置代理
        if 'all_proxy' in config and config['all_proxy']:
            if self.aria2_service.connected:
                self.aria2_service.set_proxy(config['all_proxy'])
        
        # 显示保存成功消息
        Messagebox.show_info("配置已保存", "配置已保存，部分设置需要重启服务后生效", parent=self.root)
    
    def on_service_status_change(self, running: bool, status_text: str, color: str) -> None:
        """服务状态变化回调"""
        self.connection_panel.update_service_status(running, status_text, color)
    
    def on_connection_change(self, connected: bool, message: str) -> None:
        """连接状态变化回调"""
        self.connection_panel.update_connection_status(connected, message)
        self.status_bar.config(text=message)
    
    def update_service_status(self) -> None:
        """更新服务状态"""
        running = self.aria2_service.is_running()
        status_text = "运行中" if running else "未运行"
        color = "green" if running else "red"
        
        # 直接调用状态更新方法
        self.on_service_status_change(running, status_text, color)
    
    def connect_aria2(self) -> None:
        """自动连接到aria2"""
        # 首先尝试启动服务
        if not self.aria2_service.is_running():
            print("服务未运行，正在启动...")
            if not self.start_aria2c():
                print("启动服务失败")
                return
        
        # 等待服务启动
        import time
        time.sleep(2)
        
        # 尝试连接
        config: Dict[str, Any] = self.connection_panel.get_connection_config()
        if self.aria2_service.connect(config['host'], config['port'], config['secret']):
            print("自动连接成功")
            self.status_bar.config(text="已自动连接到Aria2服务器")
        else:
            print("自动连接失败")
            self.status_bar.config(text="自动连接失败，请检查配置")
    
    def handle_service_action(self, action: str) -> None:
        """处理服务操作"""
        if action == "start":
            self.start_aria2c()
        elif action == "stop":
            self.stop_aria2c()
        elif action == "config":
            self.open_config_dialog()
        elif action == "logs":
            self.view_service_logs()
        elif action == "status":
            self.view_service_status()
    
    def start_aria2c(self) -> bool:
        """启动aria2c服务"""
        if self.aria2_service.start_service():
            # 等待服务启动
            time.sleep(1)
            # 立即更新服务状态
            self.update_service_status()
            return True
        else:
            Messagebox.show_error("失败", "Aria2c服务启动失败，请检查aria2c是否已安装", self.root)
            # 即使启动失败也要更新状态
            self.update_service_status()
            return False
    
    def stop_aria2c(self) -> None:
        """停止aria2c服务"""
        if self.aria2_service.stop_service():
            # 等待服务停止
            time.sleep(1)
            # 立即更新服务状态
            self.update_service_status()
        else:
            Messagebox.show_error("错误", "停止aria2c服务失败", self.root)
            # 即使停止失败也要更新状态
            self.update_service_status()

    
    def open_config_dialog(self) -> None:
        """打开配置对话框"""
        try:
            # 导入配置GUI
           
            
            # 创建配置窗口
            config_window: ttk.Toplevel = ttk.Toplevel(self.root)
            config_window.title("Aria2 配置管理")

            config_window.transient(self.root)
            config_window.grab_set()
            
            # 配置窗口相对于主窗口居中
            self.center_window(config_window, 800, 900, parent=self.root)
            
            # 创建配置GUI
            
        except Exception as e:
            Messagebox.show_error("错误", f"打开配置对话框失败: {e}", self.root)
    
    def view_service_logs(self) -> None:
        """查看服务日志"""
        try:
            # 创建日志查看窗口
            logs_window: ttk.Toplevel = ttk.Toplevel(self.root)
            logs_window.title("Aria2c 服务日志")
            logs_window.geometry("800x600")
            logs_window.transient(self.root)
            logs_window.grab_set()
            
            # 日志窗口相对于主窗口居中
            self.center_window(logs_window, 800, 600, parent=self.root)
            
            # 创建日志显示区域
            main_frame: ttk.Frame = ttk.Frame(logs_window, padding="10")
            main_frame.pack(fill=BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(
                main_frame, 
                text="Aria2c 服务日志", 
                bootstyle="primary",
                font=("", 14, "bold")
            )
            title_label.pack(anchor=W, pady=(0, 10))
            
            # 日志文本框
            from tkinter import scrolledtext
            self.logs_text = scrolledtext.ScrolledText(
                main_frame, 
                height=25,
                font=("Consolas", 10),
                wrap="word"
            )
            self.logs_text.pack(fill=BOTH, expand=True, pady=(0, 10))
            
            # 按钮区域
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(fill=X)
            
            # 刷新按钮
            refresh_btn = ttk.Button(
                btn_frame, 
                text="刷新", 
                command=self.refresh_logs,
                bootstyle="success",
                width=10
            )
            refresh_btn.pack(side=LEFT, padx=(0, 10))
            
            # 关闭按钮
            close_btn = ttk.Button(
                btn_frame, 
                text="关闭", 
                command=logs_window.destroy,
                bootstyle="secondary",
                width=10
            )
            close_btn.pack(side=RIGHT)
            
            # 初始加载日志
            self.refresh_logs()
            
        except Exception as e:
            Messagebox.show_error("错误", f"打开日志窗口失败: {e}", self.root)
    
    def refresh_logs(self) -> None:
        """刷新日志内容"""
        try:
            logs = self.aria2_service.get_logs(100)  # 获取最近100行日志
            
            # 清空文本框
            self.logs_text.delete("1.0", END)
            
            # 插入日志内容
            for log_line in logs:
                self.logs_text.insert(END, log_line + "\n")
            
            # 滚动到底部
            self.logs_text.see(END)
            
        except Exception as e:
            self.logs_text.delete("1.0", END)
            self.logs_text.insert(END, f"获取日志失败: {e}")
    
    def view_service_status(self) -> None:
        """查看服务状态"""
        try:
            status = self.aria2_service.get_status()
            
            # 创建状态显示窗口
            status_window: ttk.Toplevel = ttk.Toplevel(self.root)
            status_window.title("Aria2c 服务状态")
            status_window.geometry("600x500")
            status_window.transient(self.root)
            status_window.grab_set()
            
            # 状态窗口相对于主窗口居中
            self.center_window(status_window, 600, 500, parent=self.root)
            
            # 创建状态显示区域
            main_frame: ttk.Frame = ttk.Frame(status_window, padding="15")
            main_frame.pack(fill=BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(
                main_frame, 
                text="Aria2c 服务状态", 
                bootstyle="primary",
                font=("", 16, "bold")
            )
            title_label.pack(anchor=W, pady=(0, 20))
            
            # 状态信息框架
            status_frame = ttk.LabelFrame(main_frame, text="服务状态", bootstyle="info", padding="10")
            status_frame.pack(fill=X, pady=(0, 15))
            
            # 运行状态
            running_text = "运行中" if status['running'] else "未运行"
            running_color = "success" if status['running'] else "danger"
            
            ttk.Label(status_frame, text="运行状态:", bootstyle="info").grid(row=0, column=0, sticky=W, pady=2)
            ttk.Label(status_frame, text=running_text, bootstyle=running_color).grid(row=0, column=1, sticky=W, padx=(10, 0), pady=2)
            
            # 配置文件
            ttk.Label(status_frame, text="配置文件:", bootstyle="info").grid(row=1, column=0, sticky=W, pady=2)
            ttk.Label(status_frame, text=status['config_file'], bootstyle="secondary").grid(row=1, column=1, sticky=W, padx=(10, 0), pady=2)
            
            # PID文件
            ttk.Label(status_frame, text="PID文件:", bootstyle="info").grid(row=2, column=0, sticky=W, pady=2)
            ttk.Label(status_frame, text=status['pid_file'], bootstyle="secondary").grid(row=2, column=1, sticky=W, padx=(10, 0), pady=2)
            
            # 日志文件
            ttk.Label(status_frame, text="日志文件:", bootstyle="info").grid(row=3, column=0, sticky=W, pady=2)
            ttk.Label(status_frame, text=status['log_file'], bootstyle="secondary").grid(row=3, column=1, sticky=W, padx=(10, 0), pady=2)
            
            # 如果服务正在运行，显示进程信息
            if status['running'] and 'pid' in status:
                ttk.Label(status_frame, text="进程ID:", bootstyle="info").grid(row=4, column=0, sticky=W, pady=2)
                ttk.Label(status_frame, text=str(status['pid']), bootstyle="success").grid(row=4, column=1, sticky=W, padx=(10, 0), pady=2)
                
                if 'start_time' in status:
                    import time
                    start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status['start_time']))
                    ttk.Label(status_frame, text="启动时间:", bootstyle="info").grid(row=5, column=0, sticky=W, pady=2)
                    ttk.Label(status_frame, text=start_time, bootstyle="success").grid(row=5, column=1, sticky=W, padx=(10, 0), pady=2)
            
            # 配置信息框架
            config_frame = ttk.LabelFrame(main_frame, text="当前配置", bootstyle="info", padding="10")
            config_frame.pack(fill=X, pady=(0, 15))
            
            config = status['config']
            row = 0
            
            # 显示主要配置项
            config_items = [
                ("主机", config.get('host', 'localhost')),
                ("端口", str(config.get('port', 6800))),
                ("密钥", "已设置" if config.get('secret') else "未设置"),
                ("下载目录", config.get('download_dir', '~/Downloads')),
                ("最大连接数", str(config.get('max_connections', 16))),
                ("最大下载数", str(config.get('max_downloads', 5))),
                ("日志级别", config.get('log_level', 'info'))
            ]
            
            for label, value in config_items:
                ttk.Label(config_frame, text=f"{label}:", bootstyle="info").grid(row=row, column=0, sticky=W, pady=2)
                ttk.Label(config_frame, text=value, bootstyle="secondary").grid(row=row, column=1, sticky=W, padx=(10, 0), pady=2)
                row += 1
            
            # 按钮区域
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(fill=X, pady=(10, 0))
            
            # 刷新按钮
            refresh_btn = ttk.Button(
                btn_frame, 
                text="刷新", 
                command=lambda: self.refresh_service_status(status_window),
                bootstyle="success",
                width=10
            )
            refresh_btn.pack(side=LEFT, padx=(0, 10))
            
            # 关闭按钮
            close_btn = ttk.Button(
                btn_frame, 
                text="关闭", 
                command=status_window.destroy,
                bootstyle="secondary",
                width=10
            )
            close_btn.pack(side=RIGHT)
            
        except Exception as e:
            Messagebox.show_error("错误", f"获取服务状态失败: {e}", self.root)
    
    def refresh_service_status(self, status_window) -> None:
        """刷新服务状态"""
        status_window.destroy()
        self.view_service_status()
    
    def add_download(self) -> None:
        """添加下载任务"""
        if not self.aria2_service.connected:
            Messagebox.show_error("错误", "请先连接到Aria2服务器", self.root)
            return
        
        download_info: Dict[str, Any] = self.download_panel.get_download_info()
        url: str = download_info['url']
        
        if not url:
            Messagebox.show_error("错误", "请输入下载链接", self.root)
            return
        
        # 验证URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("无效的URL")
        except:
            Messagebox.show_error("错误", "请输入有效的下载链接", self.root)
            return
        
        # 从配置文件获取下载路径
        config = self.aria2_service.load_config()
        path = config.get('download_dir', '~/Downloads')
        
        # 创建保存目录
        if path:
            os.makedirs(path, exist_ok=True)
        
        # 添加下载任务
        gid: Optional[str] = self.aria2_service.add_download(url, path)
        if gid:
            self.download_panel.clear_url()
            self.status_bar.config(text=f"已添加下载任务: {gid}")
            self.refresh_tasks()
            Messagebox.show_info("成功", "下载任务已添加", self.root)
        else:
            Messagebox.show_error("错误", "添加下载任务失败", self.root)
    
    
    def refresh_tasks(self) -> None:
        """刷新任务列表"""
        if not self.aria2_service.connected:
            return
        
        try:
            downloads: List[Dict[str, Any]] = self.aria2_service.get_downloads()
            
            # 获取当前任务列表中的GID
            current_gids = set(self.task_list.get_selected_gids())
            new_gids = set(download['gid'] for download in downloads)
            
            # 删除不存在的任务
            for item in self.task_list.task_tree.get_children():
                tags = self.task_list.task_tree.item(item, "tags")
                if tags and tags[0] not in new_gids:
                    self.task_list.task_tree.delete(item)
            
            # 更新或添加任务
            for download in downloads:
                gid = download['gid']
                # 查找是否已存在
                existing_item = None
                for item in self.task_list.task_tree.get_children():
                    tags = self.task_list.task_tree.item(item, "tags")
                    if tags and tags[0] == gid:
                        existing_item = item
                        break
                
                if existing_item:
                    # 更新现有任务
                    self.task_list.update_task(gid, download)
                else:
                    # 添加新任务
                    self.task_list.add_task(download)
            
            # 更新刷新时间显示
            import time
            current_time = time.strftime("%H:%M:%S")
            self.refresh_time_label.config(text=f"最后刷新: {current_time} | 任务数: {len(downloads)}")
        
        except Exception as e:
            print(f"刷新任务失败: {e}")
            self.refresh_time_label.config(text=f"刷新失败: {e}")
    
    def pause_selected(self) -> None:
        """暂停选中的任务"""
        if not self.aria2_service.connected:
            Messagebox.show_error("错误", "请先连接到Aria2服务器", self.root)
            return
        
        gids: List[str] = self.task_list.get_selected_gids()
        if not gids:
            Messagebox.show_warning("警告", "请先选择要操作的任务", self.root)
            return
        
        if self.aria2_service.pause_downloads(gids):
            self.status_bar.config(text=f"已暂停 {len(gids)} 个任务")
            self.refresh_tasks()
        else:
            Messagebox.show_error("错误", "暂停任务失败", self.root)
    
    def resume_selected(self) -> None:
        """继续选中的任务"""
        if not self.aria2_service.connected:
            Messagebox.show_error("错误", "请先连接到Aria2服务器", self.root)
            return
        
        gids: List[str] = self.task_list.get_selected_gids()
        if not gids:
            Messagebox.show_warning("警告", "请先选择要操作的任务", self.root)
            return
        
        if self.aria2_service.resume_downloads(gids):
            self.status_bar.config(text=f"已继续 {len(gids)} 个任务")
            self.refresh_tasks()
        else:
            Messagebox.show_error("错误", "继续任务失败", self.root)
    
    def remove_selected(self) -> None:
        """删除选中的任务"""
        if not self.aria2_service.connected:
            Messagebox.show_error("错误", "请先连接到Aria2服务器", self.root)
            return
        
        gids: List[str] = self.task_list.get_selected_gids()
        if not gids:
            Messagebox.show_warning("警告", "请先选择要操作的任务", self.root)
            return
        
        if Messagebox.yesno("确认", f"确定要删除选中的 {len(gids)} 个任务吗？", self.root):
            if self.aria2_service.remove_downloads(gids):
                self.status_bar.config(text=f"已删除 {len(gids)} 个任务")
                self.refresh_tasks()
            else:
                Messagebox.show_error("错误", "删除任务失败", self.root)
    
    def open_task_folder(self, gid: str) -> None:
        """打开任务文件夹"""
        try:
            # 获取任务信息
            downloads = self.aria2_service.get_downloads()
            task_info = None
            for download in downloads:
                if download.get('gid') == gid:
                    task_info = download
                    break
            
            if not task_info:
                Messagebox.show_error("错误", "找不到任务信息", self.root)
                return
            
            # 获取文件路径
            filename = task_info.get('filename', '')
            if not filename or filename == '未知文件':
                Messagebox.show_error("错误", "无法获取文件路径", self.root)
                return
            
            # 构建完整路径
            import os
            from pathlib import Path
            
            # 从aria2配置获取下载目录
            config = self.aria2_service.load_config()
            download_dir = os.path.expanduser(config.get('download_dir', '~/Downloads'))
            file_path = os.path.join(download_dir, filename)
            
            # 打开文件夹
            if os.path.exists(file_path):
                folder_path = os.path.dirname(file_path)
                if os.name == 'nt':  # Windows
                    os.startfile(folder_path)
                elif os.name == 'posix':  # macOS and Linux
                    os.system(f'xdg-open "{folder_path}"')
                else:
                    Messagebox.show_info("提示", f"文件夹路径: {folder_path}", self.root)
            else:
                Messagebox.show_error("错误", f"文件不存在: {file_path}", self.root)
                
        except Exception as e:
            Messagebox.show_error("错误", f"打开文件夹失败: {e}", self.root)
    
    
    def start_auto_refresh(self) -> None:
        """开始自动刷新任务列表"""
        def refresh_loop() -> None:
            while True:
                if self.aria2_service.connected:
                    self.root.after(0, self.refresh_tasks)
                time.sleep(1)  # 每1秒刷新一次，提高刷新频率
        
        refresh_thread: threading.Thread = threading.Thread(target=refresh_loop, daemon=True)
        refresh_thread.start()
    
    def start_service_status_check(self) -> None:
        """开始定期检查服务状态"""
        def status_check_loop() -> None:
            while True:
                # 在后台线程中检查状态，然后在主线程中更新UI
                self.root.after(0, self.update_service_status)
                time.sleep(3)  # 每3秒检查一次服务状态
        
        status_thread: threading.Thread = threading.Thread(target=status_check_loop, daemon=True)
        status_thread.start()
    
    def run(self) -> None:
        """运行应用程序"""
        self.root.mainloop()


def main() -> None:
    app = Aria2GUI()
    app.run()


if __name__ == "__main__":
    main()
