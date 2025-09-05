import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
import tkinter as tk
from typing import Dict, Optional, Callable


class DownloadPanel:
    """下载任务管理面板 """
    
    def __init__(self, parent: tk.Widget, on_add_download_callback: Optional[Callable[[], None]] = None) -> None:
        self.parent: tk.Widget = parent
        self.on_add_download_callback: Optional[Callable[[], None]] = on_add_download_callback
        
        # 变量
        self.url_var: ttk.StringVar = ttk.StringVar()
        
        self.create_widgets()
    
    def create_widgets(self) -> None:
        """创建界面组件"""
        # 主框架
        self.frame = ttk.LabelFrame(
            self.parent, 
            text="添加下载任务", 
            bootstyle="primary",
            padding="10"
        )
        self.frame.pack(fill=X, pady=(0, 10))
        
        # URL输入区域
        self.create_url_section()
        
        # 按钮区域
        self.create_button_section()
    
    def create_url_section(self) -> None:
        """创建URL输入区域"""
        # URL标签
        url_label = ttk.Label(
            self.frame, 
            text="下载链接:", 
            bootstyle="primary"
        )
        url_label.pack(anchor=W, pady=(0, 5))
        
        # URL输入框
        self.url_entry = ttk.Entry(
            self.frame, 
            textvariable=self.url_var,
            bootstyle="primary",
            font=("Consolas", 10)
        )
        self.url_entry.pack(fill=X, pady=(0, 10))
        
        # 绑定回车键
        self.url_entry.bind('<Return>', lambda e: self.add_download())
    
    
    def create_button_section(self) -> None:
        """创建按钮区域"""
        # 按钮框架
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        
        # 添加下载按钮
        add_btn = ttk.Button(
            btn_frame, 
            text="添加下载", 
            command=self.add_download,
            bootstyle="success",
            width=15
        )
        add_btn.pack(side=LEFT)
    
    
    def add_download(self) -> None:
        """添加下载按钮回调"""
        if self.on_add_download_callback:
            self.on_add_download_callback()
    
    
    def get_download_info(self) -> Dict[str, str]:
        """获取下载信息"""
        return {
            'url': self.url_var.get().strip()
        }
    
    def clear_url(self) -> None:
        """清空URL输入框"""
        self.url_var.set("")
        self.url_entry.focus()
    
