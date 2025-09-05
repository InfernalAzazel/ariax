import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.constants import *
import ttkbootstrap as ttk
from typing import Dict,Optional, Callable
import json
import os


class ConfigWindow:
    """Aria2配置窗口"""
    
    def __init__(self, parent: tk.Tk, config_path: Optional[str] = None, on_config_save: Optional[Callable] = None):
        self.parent = parent
        # 使用路径管理器获取标准配置文件路径
        if config_path is None:
            from lib.path_manager import path_manager
            self.config_path = path_manager.get_config_path()
        else:
            self.config_path = config_path
        self.on_config_save = on_config_save
        self.window: Optional[tk.Toplevel] = None
        
        # 配置变量
        self.config_vars: Dict[str, tk.StringVar] = {}
        
    def show(self) -> None:
        """显示配置窗口"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
            
        self.create_window()
        self.load_config()
        
    def create_window(self) -> None:
        """创建配置窗口"""
        self.window = ttk.Toplevel(self.parent)
        self.window.title("Aria2 配置")
        self.window.geometry("1200x800")
        self.window.resizable(True, True)
        
        # 居中显示
        self.center_window()
        
        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=BOTH, expand=True)
        
        # 创建滚动区域
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 创建配置项
        self.create_config_sections(scrollable_frame)
        
        # 创建按钮区域
        self.create_button_section(main_frame)
        
        # 打包滚动区域
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def center_window(self) -> None:
        """窗口居中显示"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
    def create_config_sections(self, parent: ttk.Frame) -> None:
        """创建配置区域"""
        from lib.path_manager import path_manager
        
        # 获取默认配置
        default_config = path_manager.create_default_config()
        
        # 定义配置项的分组和显示信息
        config_groups = {
            "连接配置": [
                ("host", "RPC主机", "Aria2 RPC服务器地址"),
                ("port", "RPC端口", "Aria2 RPC服务器端口"),
                ("secret", "RPC密钥", "Aria2 RPC密钥（可选）"),
            ],
            "下载配置": [
                ("download_dir", "下载目录", "默认下载目录"),
                ("max_connections", "最大连接数", "每个任务的最大连接数"),
                ("max_downloads", "最大下载数", "同时下载的最大任务数"),
            ],
            "代理配置": [
                ("all_proxy", "全局代理", "格式: http://proxy:port 或 socks5://proxy:port"),
            ],
            "日志配置": [
                ("log_level", "日志级别", "日志级别: debug, info, notice, warn, error"),
            ]
        }
        
        # 动态创建配置区域
        for group_name, items in config_groups.items():
            section_items = []
            for key, label, help_text in items:
                if key in default_config:
                    default_value = str(default_config[key])
                    section_items.append((key, label, default_value, help_text))
            
            if section_items:  # 只有当组内有有效配置项时才创建
                self.create_section(parent, group_name, section_items)
        
    def create_section(self, parent: ttk.Frame, title: str, items: list) -> None:
        """创建配置区域"""
        # 区域框架
        section_frame = ttk.LabelFrame(parent, text=title, bootstyle="info", padding="10")
        section_frame.pack(fill=X, pady=(0, 15))
        
        for key, label, default, help_text in items:
            # 配置项框架
            item_frame = ttk.Frame(section_frame)
            item_frame.pack(fill=X, pady=(0, 8))
            
            # 标签
            ttk.Label(item_frame, text=f"{label}:", width=15, anchor=W).pack(side=LEFT, padx=(0, 10))
            
            # 输入框
            var = ttk.StringVar(value=default)
            self.config_vars[key] = var
            
            # 文本输入框
            entry = ttk.Entry(
                item_frame, 
                textvariable=var,
                bootstyle="primary",
                width=30
            )
            entry.pack(side=LEFT, padx=(0, 10))
            
            # 帮助文本
            help_label = ttk.Label(
                item_frame, 
                text=help_text, 
                bootstyle="secondary",
                font=("Arial", 8)
            )
            help_label.pack(side=LEFT)
            
    def create_button_section(self, parent: ttk.Frame) -> None:
        """创建按钮区域"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=X, pady=(20, 0))
        
        # 保存按钮
        save_btn = ttk.Button(
            button_frame,
            text="保存配置",
            command=self.save_config,
            bootstyle="success",
            width=15
        )
        save_btn.pack(side=LEFT, padx=(0, 10))
        
        # 重置按钮
        reset_btn = ttk.Button(
            button_frame,
            text="重置默认",
            command=self.reset_config,
            bootstyle="warning",
            width=15
        )
        reset_btn.pack(side=LEFT, padx=(0, 10))
        
        # 取消按钮
        cancel_btn = ttk.Button(
            button_frame,
            text="取消",
            command=self.on_close,
            bootstyle="secondary",
            width=15
        )
        cancel_btn.pack(side=LEFT)
        
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # 更新配置变量
                for key, var in self.config_vars.items():
                    if key in config:
                        value = str(config[key])
                        var.set(value)
        except Exception as e:
            messagebox.showerror("错误", f"加载配置文件失败: {e}")
            
    def save_config(self) -> None:
        """保存配置文件"""
        try:
            # 使用path_manager的默认配置作为基础
            from lib.path_manager import path_manager
            config = path_manager.create_default_config()
            
            # 只更新在配置窗口中定义的配置项
            for key, var in self.config_vars.items():
                if key in config:  # 只保存path_manager中定义的配置项
                    value = var.get().strip()
                    
                    # 处理数字值
                    if key in ["port", "max_connections", "max_downloads"]:
                        try:
                            config[key] = int(value) if value else 0
                        except ValueError:
                            config[key] = 0
                    else:
                        config[key] = value
                    
            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
            messagebox.showinfo("成功", "配置已保存")
            
            # 通知回调
            if self.on_config_save:
                self.on_config_save(config)
                
        except Exception as e:
            messagebox.showerror("错误", f"保存配置文件失败: {e}")
            
    def reset_config(self) -> None:
        """重置为默认配置"""
        # 使用aria2.py中的默认配置
        from lib.path_manager import path_manager
        default_config = path_manager.create_default_config()
        
        # 更新配置变量
        for key, var in self.config_vars.items():
            if key in default_config:
                value = default_config[key]
                if isinstance(value, bool):
                    var.set("1" if value else "0")
                else:
                    var.set(str(value))
                    
    def on_close(self) -> None:
        """关闭窗口"""
        if self.window:
            self.window.destroy()
            self.window = None
