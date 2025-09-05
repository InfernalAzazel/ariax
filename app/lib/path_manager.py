import platform
from pathlib import Path
from typing import Dict, Any
import platformdirs



class PathManager:
    """跨平台路径管理器"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self._setup_paths()
    
    def _setup_paths(self):
        """设置跨平台路径"""
        # 使用系统标准函数获取路径
        self.app_data_dir = self._get_app_data_dir()
        self.downloads_dir = self._get_downloads_dir()
        self.config_dir = self._get_config_dir()
        
        # 确保目录存在
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_app_data_dir(self) -> Path:
        """获取应用数据目录"""
        return Path(platformdirs.user_data_dir("Aria2GUI", "Aria2GUI"))
    
    def _get_config_dir(self) -> Path:
        """获取配置目录"""
        return Path(platformdirs.user_config_dir("Aria2GUI", "Aria2GUI"))
    
    def _get_downloads_dir(self) -> Path:
        """获取下载目录"""
        return Path(platformdirs.user_downloads_dir())
    
    
    def get_config_path(self) -> str:
        """获取配置文件路径"""
        return str(self.config_dir / "aria2.conf")
    
    def get_pid_path(self) -> str:
        """获取PID文件路径"""
        pid_path = self.config_dir / "aria2.pid"
        # PID文件会在服务启动时自动创建，这里不需要预先创建
        return str(pid_path)
    
    def get_log_path(self) -> str:
        """获取日志文件路径"""
        log_path = self.config_dir / "aria2.log"
        # 确保日志文件存在
        if not log_path.exists():
            log_path.touch()
        return str(log_path)
    
    def get_downloads_path(self) -> str:
        """获取下载目录路径"""
        return str(self.downloads_dir)
    
    
    def create_default_config(self) -> Dict[str, Any]:
        """创建默认配置"""
        return {
            "host": "localhost",
            "port": 6800,
            "secret": "",
            "download_dir": self.get_downloads_path(),
            "max_connections": 16,
            "max_downloads": 10,
            "all_proxy": "",
            "log_level": "info"
        }
    


# 全局路径管理器实例
path_manager = PathManager()
