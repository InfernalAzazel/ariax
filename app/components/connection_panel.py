import ttkbootstrap as ttk
from ttkbootstrap.constants import *


class ConnectionPanel:
    """Aria2连接配置面板"""
    
    def __init__(self, parent: ttk.Window, on_connect_callback=None, on_service_callback=None):
        self.parent = parent
        self.on_connect_callback = on_connect_callback
        self.on_service_callback = on_service_callback
        
        # 配置变量（从配置文件读取）
        self.config = self.load_config()
        
        # 状态变量
        self.connected = False
        self.service_running = False
        
        self.create_widgets()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        self.frame = ttk.LabelFrame(
            self.parent, 
            text="Aria2 连接配置", 
            bootstyle="info",
            padding="10"
        )
        self.frame.pack(fill=X, pady=(0, 10))
        
        # 连接配置行
        self.create_connection_row()
        
        # 服务控制行
        self.create_service_control_row()
        
        # 设置初始按钮状态
        self.update_service_status(self.service_running, "检查中...", "warning")
        
        # 更新配置信息显示
        self.update_config_info()
    
    def create_connection_row(self):
        """创建连接状态显示行"""
        # 连接状态框架
        conn_frame = ttk.Frame(self.frame)
        conn_frame.pack(fill=X, pady=(0, 10))
        
        # 连接状态标签
        ttk.Label(conn_frame, text="连接状态:", bootstyle="info").pack(side=LEFT, padx=(0, 10))
        self.status_label = ttk.Label(
            conn_frame, 
            text="未连接", 
            bootstyle="danger"
        )
        self.status_label.pack(side=LEFT, padx=(0, 10))
        
        # 自动连接按钮
        self.auto_connect_btn = ttk.Button(
            conn_frame,
            text="自动连接",
            command=self.connect,
            bootstyle="success",
            width=10
        )
        self.auto_connect_btn.pack(side=LEFT, padx=(0, 10))
        
        # 配置信息显示
        self.config_info_label = ttk.Label(
            conn_frame,
            text="配置: localhost:6800",
            bootstyle="secondary",
            font=("Arial", 9)
        )
        self.config_info_label.pack(side=LEFT, padx=(20, 0))
    
    def load_config(self):
        """加载配置文件"""
        try:
            from lib.path_manager import path_manager
            import json
            import os
            
            config_path = path_manager.get_config_path()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 返回默认配置
                return path_manager.create_default_config()
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            from lib.path_manager import path_manager
            return path_manager.create_default_config()
    
    def update_config_info(self):
        """更新配置信息显示"""
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 6800)
        secret = self.config.get("secret", "")
        secret_display = " (有密钥)" if secret else " (无密钥)"
        self.config_info_label.config(text=f"配置: {host}:{port}{secret_display}")
    
    def create_service_control_row(self):
        """创建服务控制行"""
        # 服务控制框架
        service_frame = ttk.Frame(self.frame)
        service_frame.pack(fill=X)
        
        # 服务状态标签
        ttk.Label(service_frame, text="服务状态:", bootstyle="info").pack(side=LEFT, padx=(0, 5))
        
        self.service_status_label = ttk.Label(
            service_frame, 
            text="检查中...", 
            bootstyle="warning"
        )
        self.service_status_label.pack(side=LEFT, padx=(0, 15))
        
        # 简化的服务控制按钮
        self.start_service_btn = ttk.Button(
            service_frame, 
            text="启动", 
            command=self.start_service,
            bootstyle="success",
            width=8
        )
        self.start_service_btn.pack(side=LEFT, padx=(0, 5))
        
        self.stop_service_btn = ttk.Button(
            service_frame, 
            text="停止", 
            command=self.stop_service,
            bootstyle="danger",
            width=8
        )
        self.stop_service_btn.pack(side=LEFT)
    
    def connect(self):
        """连接按钮回调"""
        if self.on_connect_callback:
            self.on_connect_callback()
    
    def start_service(self):
        """启动服务按钮回调"""
        if self.on_service_callback:
            self.on_service_callback("start")
    
    def stop_service(self):
        """停止服务按钮回调"""
        if self.on_service_callback:
            self.on_service_callback("stop")
    
    
    def get_connection_config(self):
        """获取连接配置"""
        return {
            'host': self.config.get('host', 'localhost'),
            'port': self.config.get('port', 6800),
            'secret': self.config.get('secret', '')
        }
    
    def update_connection_status(self, connected, message=""):
        """更新连接状态"""
        self.connected = connected
        if connected:
            self.status_label.config(text="已连接", bootstyle="success")
            self.auto_connect_btn.config(text="重新连接")
        else:
            self.status_label.config(text="未连接", bootstyle="danger")
            self.auto_connect_btn.config(text="自动连接")
        
        if message:
            self.status_label.config(text=message)
    
    def update_service_status(self, running: bool, status_text: str = "", color: str = "warning"):
        """更新服务状态"""
        self.service_running = running
        
        # 根据颜色设置bootstyle
        if color == "green":
            bootstyle = "success"
        elif color == "red":
            bootstyle = "danger"
        else:
            bootstyle = "warning"
        
        self.service_status_label.config(text=status_text, bootstyle=bootstyle)
        
        # 更新按钮状态
        if running:
            self.start_service_btn.config(state="disabled")
            self.stop_service_btn.config(state="normal")
        else:
            self.start_service_btn.config(state="normal")
            self.stop_service_btn.config(state="disabled")
        
        # 强制更新界面
        self.parent.update_idletasks()
