import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
import tkinter as tk
from typing import Dict, List, Optional, Callable, Any


class TaskList:
    """下载任务列表组件"""
    
    def __init__(
        self, 
        parent: tk.Widget, 
        on_pause_callback: Optional[Callable[[], None]] = None, 
        on_resume_callback: Optional[Callable[[], None]] = None, 
        on_remove_callback: Optional[Callable[[], None]] = None, 
        on_refresh_callback: Optional[Callable[[], None]] = None, 
        on_open_folder_callback: Optional[Callable[[str], None]] = None
    ) -> None:

        self.parent: tk.Widget = parent
        self.on_pause_callback: Optional[Callable[[], None]] = on_pause_callback
        self.on_resume_callback: Optional[Callable[[], None]] = on_resume_callback
        self.on_remove_callback: Optional[Callable[[], None]] = on_remove_callback
        self.on_refresh_callback: Optional[Callable[[], None]] = on_refresh_callback
        self.on_open_folder_callback: Optional[Callable[[str], None]] = on_open_folder_callback
        
        self.create_widgets()
    
    def create_widgets(self) -> None:
        """创建界面组件"""
        # 主框架
        self.frame = ttk.LabelFrame(
            self.parent, 
            text="下载任务", 
            bootstyle="secondary",
            padding="10"
        )
        self.frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        # 创建Treeview框架
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview - 添加文件大小列
        columns = ("状态", "文件名", "大小", "进度", "速度")
        self.task_tree = ttk.Treeview(
            tree_frame, 
            columns=columns, 
            show="headings", 
            height=15,
        )
        
        # 配置颜色标签
        self.task_tree.tag_configure("downloading", background="#e8f5e8", foreground="#2d5a2d")  # 下载中 - 浅绿色
        self.task_tree.tag_configure("completed", background="#e8f5e8", foreground="#2d5a2d")   # 已完成 - 浅绿色
        self.task_tree.tag_configure("waiting", background="#fff3cd", foreground="#856404")     # 等待中 - 浅黄色
        self.task_tree.tag_configure("paused", background="#f8d7da", foreground="#721c24")      # 暂停 - 浅红色
        self.task_tree.tag_configure("unknown", background="#d1ecf1", foreground="#0c5460")     # 未知 - 浅蓝色
        
        # 选中标签 - 使用深色背景确保覆盖原有颜色
        self.task_tree.tag_configure("selected", background="#007bff", foreground="#ffffff")    # 选中 - 蓝色
        
        # 设置列标题和宽度
        self.task_tree.heading("状态", text="状态")
        self.task_tree.heading("文件名", text="文件名")
        self.task_tree.heading("大小", text="大小")
        self.task_tree.heading("进度", text="进度")
        self.task_tree.heading("速度", text="速度")
        
        self.task_tree.column("状态", width=80, anchor=CENTER)
        self.task_tree.column("文件名", width=300, anchor=W)
        self.task_tree.column("大小", width=120, anchor=E)
        self.task_tree.column("进度", width=100, anchor=CENTER)
        self.task_tree.column("速度", width=120, anchor=E)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(
            tree_frame, 
            orient=VERTICAL, 
            command=self.task_tree.yview,
            bootstyle="secondary"
        )
        self.task_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.task_tree.grid(row=0, column=0, sticky=(W, E, N, S))
        scrollbar.grid(row=0, column=1, sticky=(N, S))
        
        # 绑定双击事件
        self.task_tree.bind("<Double-1>", self.on_double_click)
        
        # 绑定虚拟事件来处理选中状态
        self.task_tree.bind("<<TreeviewSelect>>", self.on_selection_change)
        self.task_tree.bind("<FocusIn>", self.on_focus_in)
        self.task_tree.bind("<FocusOut>", self.on_focus_out)
        
        # 创建右键菜单
        self.create_context_menu()
    
    def create_context_menu(self) -> None:
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.parent, tearoff=0)
        self.context_menu.add_command(label="暂停", command=self.pause_selected)
        self.context_menu.add_command(label="继续", command=self.resume_selected)
        self.context_menu.add_command(label="删除", command=self.remove_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="打开文件夹", command=self.open_folder)
        
        # 绑定右键事件
        self.task_tree.bind("<Button-3>", self.show_context_menu)
        
        # 绑定其他事件来隐藏菜单
        self.task_tree.bind("<Button-1>", self.on_left_click)      # 左键点击
        self.task_tree.bind("<FocusOut>", self.hide_context_menu)  # 失去焦点
        self.parent.bind("<Button-1>", self.hide_context_menu)     # 点击父窗口
        self.task_tree.bind("<Escape>", self.hide_context_menu)    # ESC键
        self.context_menu.bind("<FocusOut>", self.hide_context_menu)  # 菜单失去焦点
    
    def show_context_menu(self, event: tk.Event) -> None:
        """显示右键菜单"""
        # 先隐藏之前的菜单
        self.hide_context_menu()
        
        # 获取点击位置的项目
        item = self.task_tree.identify_row(event.y)
        if item:
            # 选中该项目
            self.task_tree.selection_set(item)
            # 显示右键菜单
            self.context_menu.post(event.x_root, event.y_root)
    
    def on_left_click(self, event: tk.Event) -> None:
        """左键点击处理"""
        # 获取点击位置的项目
        item = self.task_tree.identify_row(event.y)
        if not item:
            # 点击空白区域，隐藏菜单
            self.hide_context_menu()
    
    def hide_context_menu(self, event: Optional[tk.Event] = None) -> None:
        """隐藏右键菜单"""
        try:
            self.context_menu.unpost()
        except:
            pass  # 忽略菜单未显示时的错误
    
    def on_selection_change(self, event: tk.Event) -> None:
        """选中事件处理 - 更新选中项颜色"""
        # 清除所有项目的选中标签
        for item in self.task_tree.get_children():
            tags = list(self.task_tree.item(item, "tags"))
            if "selected" in tags:
                tags.remove("selected")
            self.task_tree.item(item, tags=tags)
        
        # 为选中的项目添加选中标签
        selected_items = self.task_tree.selection()
        for item in selected_items:
            tags = list(self.task_tree.item(item, "tags"))
            if "selected" not in tags:
                tags.append("selected")
            self.task_tree.item(item, tags=tags)
    
    def on_focus_in(self, event: tk.Event) -> None:
        """获得焦点时处理选中项"""
        self.on_selection_change(event)
    
    def on_focus_out(self, event: tk.Event) -> None:
        """失去焦点时清除选中标签"""
        for item in self.task_tree.get_children():
            tags = list(self.task_tree.item(item, "tags"))
            if "selected" in tags:
                tags.remove("selected")
            self.task_tree.item(item, tags=tags)
    
    def on_double_click(self, event: tk.Event) -> None:
        """双击事件处理 - 打开文件夹"""
        item = self.task_tree.selection()[0] if self.task_tree.selection() else None
        if item:
            self.open_folder()
    
    def pause_selected(self) -> None:
        """暂停选中任务"""
        if self.on_pause_callback:
            self.on_pause_callback()
    
    def resume_selected(self) -> None:
        """继续选中任务"""
        if self.on_resume_callback:
            self.on_resume_callback()
    
    def remove_selected(self) -> None:
        """删除选中任务"""
        if self.on_remove_callback:
            self.on_remove_callback()
    
    def refresh_tasks(self) -> None:
        """刷新任务列表"""
        if self.on_refresh_callback:
            self.on_refresh_callback()
    
    def open_folder(self) -> None:
        """打开文件夹"""
        selected_items = self.task_tree.selection()
        if not selected_items:
            Messagebox.show_warning("警告", "请先选择要打开文件夹的任务", parent=self.parent)
            return
        
        # 获取选中任务的GID
        gids = self.get_selected_gids()
        if not gids:
            Messagebox.show_warning("警告", "无法获取任务信息", parent=self.parent)
            return
        
        # 只处理第一个选中的任务
        gid = gids[0]
        
        # 通过回调获取任务信息并打开文件夹
        if hasattr(self, 'on_open_folder_callback') and self.on_open_folder_callback:
            self.on_open_folder_callback(gid)
        else:
            Messagebox.show_info("提示", "打开文件夹功能需要任务信息", parent=self.parent)
    
    def get_selected_gids(self) -> List[str]:
        """获取选中任务的GID"""
        gids = []
        for item in self.task_tree.selection():
            tags = self.task_tree.item(item, "tags")
            if tags:
                gids.append(tags[0])
        return gids
    
    def clear_tasks(self) -> None:
        """清空任务列表"""
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
    
    def add_task(self, task_info: Dict[str, Any]) -> None:
        """添加任务到列表"""
        gid = task_info.get("gid", "")
        status = task_info.get("status", "未知")
        filename = task_info.get("filename", "未知文件")
        size_str = task_info.get("size", "未知")
        progress = task_info.get("progress", "0%")
        speed_str = task_info.get("speed", "0 B/s")
        
        # 根据状态设置标签颜色
        tags = [gid]
        if status == "下载中":
            tags.append("downloading")
        elif status == "已完成":
            tags.append("completed")
        elif status == "等待中":
            tags.append("waiting")
        elif status == "已暂停":
            tags.append("paused")
        else:
            tags.append("unknown")
        
        # 插入到树形控件 - 包含文件大小
        item = self.task_tree.insert("", END, values=(
            status, filename, size_str, progress, speed_str
        ), tags=tags)
        
        # 设置行颜色
        self.set_row_color(item, status)
    
    def set_row_color(self, item: str, status: str) -> None:
        """设置行颜色"""
        if status == "下载中":
            self.task_tree.set(item, "状态", "🔄 下载中")
        elif status == "已完成":
            self.task_tree.set(item, "状态", "✅ 已完成")
        elif status == "等待中":
            self.task_tree.set(item, "状态", "⏳ 等待中")
        elif status == "暂停":
            self.task_tree.set(item, "状态", "⏸️ 暂停")
        else:
            self.task_tree.set(item, "状态", "❓ 未知")
    
    def update_task(self, gid: str, task_info: Dict[str, Any]) -> None:
        """更新任务信息"""
        # 查找对应的任务项
        for item in self.task_tree.get_children():
            tags = self.task_tree.item(item, "tags")
            if tags and tags[0] == gid:
                # 更新任务信息 - 包含文件大小
                status = task_info.get("status", "未知")
                filename = task_info.get("filename", "未知文件")
                size_str = task_info.get("size", "未知")
                progress = task_info.get("progress", "0%")
                speed_str = task_info.get("speed", "0 B/s")
                
                self.task_tree.item(item, values=(
                    status, filename, size_str, progress, speed_str
                ))
                
                # 更新颜色标签
                current_tags = list(tags)
                # 移除旧的状态标签
                for tag in ["downloading", "completed", "waiting", "paused", "unknown"]:
                    if tag in current_tags:
                        current_tags.remove(tag)
                
                # 添加新的状态标签
                if status == "下载中":
                    current_tags.append("downloading")
                elif status == "已完成":
                    current_tags.append("completed")
                elif status == "等待中":
                    current_tags.append("waiting")
                elif status == "已暂停":
                    current_tags.append("paused")
                else:
                    current_tags.append("unknown")
                
                # 如果该项目当前被选中，添加选中标签
                if item in self.task_tree.selection():
                    if "selected" not in current_tags:
                        current_tags.append("selected")
                
                self.task_tree.item(item, tags=current_tags)
                
                # 更新行颜色
                self.set_row_color(item, status)
                break
    
    def get_task_count(self) -> int:
        """获取任务总数"""
        return len(self.task_tree.get_children())
    
    def get_downloading_count(self) -> int:
        """获取正在下载的任务数"""
        count = 0
        for item in self.task_tree.get_children():
            values = self.task_tree.item(item, "values")
            if values and "下载中" in values[0]:
                count += 1
        return count
