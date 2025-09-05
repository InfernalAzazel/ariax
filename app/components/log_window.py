import tkinter as tk
from tkinter import ttk, scrolledtext
from tkinter.constants import *
import ttkbootstrap as ttk
from typing import Optional
import threading
import time
import os


class LogWindow:
    """日志查看窗口"""
    
    def __init__(self, parent: tk.Tk, log_path: Optional[str] = None):
        self.parent = parent
        # 使用路径管理器获取标准日志文件路径
        if log_path is None:
            from lib.path_manager import path_manager
            self.log_path = path_manager.get_log_path()
        else:
            self.log_path = log_path
        self.window: Optional[tk.Toplevel] = None
        self.text_widget: Optional[scrolledtext.ScrolledText] = None
        self.auto_refresh = True
        self.refresh_thread: Optional[threading.Thread] = None
        self.stop_refresh = False
        
    def show(self) -> None:
        """显示日志窗口"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
            
        self.create_window()
        self.start_auto_refresh()
        
    def create_window(self) -> None:
        """创建日志窗口"""
        self.window = ttk.Toplevel(self.parent)
        self.window.title("Aria2 日志")
        self.window.geometry("1200x600")
        self.window.resizable(True, True)
        
        # 居中显示
        self.center_window()
        
        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=BOTH, expand=True)
        
        # 创建工具栏
        self.create_toolbar(main_frame)
        
        # 创建日志显示区域
        self.create_log_area(main_frame)
        
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
        
    def create_toolbar(self, parent: ttk.Frame) -> None:
        """创建工具栏"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=X, pady=(0, 10))
        
        # 刷新按钮
        refresh_btn = ttk.Button(
            toolbar,
            text="刷新",
            command=self.refresh_log,
            bootstyle="primary",
            width=10
        )
        refresh_btn.pack(side=LEFT, padx=(0, 10))
        
        # 自动刷新开关
        self.auto_refresh_var = ttk.BooleanVar(value=True)
        auto_refresh_check = ttk.Checkbutton(
            toolbar,
            text="自动刷新",
            variable=self.auto_refresh_var,
            command=self.toggle_auto_refresh,
            bootstyle="success-round-toggle"
        )
        auto_refresh_check.pack(side=LEFT, padx=(0, 10))
        
        # 清空按钮
        clear_btn = ttk.Button(
            toolbar,
            text="清空",
            command=self.clear_log,
            bootstyle="warning",
            width=10
        )
        clear_btn.pack(side=LEFT, padx=(0, 10))
        
        # 保存按钮
        save_btn = ttk.Button(
            toolbar,
            text="保存日志",
            command=self.save_log,
            bootstyle="info",
            width=10
        )
        save_btn.pack(side=LEFT, padx=(0, 10))
        
        # 日志文件路径标签
        log_path_label = ttk.Label(
            toolbar,
            text=f"日志文件: {self.log_path}",
            bootstyle="secondary",
            font=("Arial", 9)
        )
        log_path_label.pack(side=LEFT, padx=(20, 0))
        
    def create_log_area(self, parent: ttk.Frame) -> None:
        """创建日志显示区域"""
        # 日志文本区域
        self.text_widget = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#404040",
            height=25
        )
        self.text_widget.pack(fill=BOTH, expand=True)
        
        # 配置文本标签颜色
        self.text_widget.tag_configure("error", foreground="#ff6b6b")
        self.text_widget.tag_configure("warning", foreground="#ffd93d")
        self.text_widget.tag_configure("info", foreground="#6bcf7f")
        self.text_widget.tag_configure("debug", foreground="#4dabf7")
        
        # 初始加载日志
        self.refresh_log()
        
    def refresh_log(self) -> None:
        """刷新日志内容"""
        try:
            if not os.path.exists(self.log_path):
                self.text_widget.delete(1.0, tk.END)
                self.text_widget.insert(tk.END, "日志文件不存在\n")
                return
                
            # 读取日志文件
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            # 只显示最后1000行
            if len(lines) > 1000:
                lines = lines[-1000:]
                
            # 清空并插入新内容
            self.text_widget.delete(1.0, tk.END)
            
            for line in lines:
                line = line.rstrip()
                if not line:
                    continue
                    
                # 根据日志级别设置颜色
                if "ERROR" in line or "error" in line:
                    self.text_widget.insert(tk.END, line + "\n", "error")
                elif "WARN" in line or "warning" in line:
                    self.text_widget.insert(tk.END, line + "\n", "warning")
                elif "INFO" in line or "info" in line:
                    self.text_widget.insert(tk.END, line + "\n", "info")
                elif "DEBUG" in line or "debug" in line:
                    self.text_widget.insert(tk.END, line + "\n", "debug")
                else:
                    self.text_widget.insert(tk.END, line + "\n")
                    
            # 滚动到底部
            self.text_widget.see(tk.END)
            
        except Exception as e:
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(tk.END, f"读取日志失败: {e}\n")
            
    def start_auto_refresh(self) -> None:
        """开始自动刷新"""
        if self.refresh_thread and self.refresh_thread.is_alive():
            return
            
        self.stop_refresh = False
        self.refresh_thread = threading.Thread(target=self._auto_refresh_loop, daemon=True)
        self.refresh_thread.start()
        
    def _auto_refresh_loop(self) -> None:
        """自动刷新循环"""
        while not self.stop_refresh:
            if self.auto_refresh and self.window and self.window.winfo_exists():
                self.window.after(0, self.refresh_log)
            time.sleep(2)  # 每2秒刷新一次
            
    def toggle_auto_refresh(self) -> None:
        """切换自动刷新"""
        self.auto_refresh = self.auto_refresh_var.get()
        
    def clear_log(self) -> None:
        """清空日志显示"""
        self.text_widget.delete(1.0, tk.END)
        
    def save_log(self) -> None:
        """保存日志到文件"""
        try:
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                title="保存日志",
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            
            if filename:
                content = self.text_widget.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                ttk.messagebox.showinfo("成功", f"日志已保存到: {filename}")
                
        except Exception as e:
            ttk.messagebox.showerror("错误", f"保存日志失败: {e}")
            
    def on_close(self) -> None:
        """关闭窗口"""
        self.stop_refresh = True
        if self.refresh_thread and self.refresh_thread.is_alive():
            self.refresh_thread.join(timeout=1)
            
        if self.window:
            self.window.destroy()
            self.window = None
