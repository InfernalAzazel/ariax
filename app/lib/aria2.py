import os
import time
import subprocess
import psutil
import json
from typing import Dict, Optional, Callable, List
from pathlib import Path
from aria2p import API, Client, Download
from .path_manager import path_manager


class Aria2:
    """Aria2服务管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        # 使用路径管理器获取标准路径
        self.config_path = Path(path_manager.get_config_path())
        self.pid_path = Path(path_manager.get_pid_path())
        self.log_path = Path(path_manager.get_log_path())
        
        # 如果提供了自定义配置文件路径，则使用它
        if config_file:
            self.config_path = Path(config_file)
        
        # 状态
        self.connected = False
        self.api = None
        
        # 回调函数
        self.on_status_change: Optional[Callable] = None
        self.on_connection_change: Optional[Callable] = None
        
        # 默认配置
        # 使用路径管理器创建默认配置
        self.default_config = path_manager.create_default_config()
    
    def set_callbacks(self, on_status_change: Optional[Callable] = None, on_connection_change: Optional[Callable] = None) -> None:
        """设置回调函数"""
        self.on_status_change = on_status_change
        self.on_connection_change = on_connection_change
    
    def load_config(self) -> Dict:
        """加载配置文件"""
        if not self.config_path.exists():
            self.save_config(self.default_config)
            return self.default_config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return self.default_config
    
    def save_config(self, config: Dict) -> None:
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def _build_command(self, config: Dict) -> List[str]:
        """构建aria2c启动命令"""
        cmd = ["aria2c", "--enable-rpc=true", "--rpc-listen-all=true", "--rpc-allow-origin-all=true"]
        
        # 基本配置
        cmd.extend([
            f"--rpc-listen-port={config.get('port', 6800)}",
            f"--dir={config.get('download_dir', path_manager.get_downloads_path())}",
            f"--max-connection-per-server={config.get('max_connections', 16)}",
            f"--max-concurrent-downloads={config.get('max_downloads', 5)}",
            f"--split={config.get('max_connections', 16)}",
            "--min-split-size=1M",
            "--continue=true",
            "--max-tries=5",
            "--retry-wait=3",
            "--disk-cache=32M",
            "--file-allocation=falloc",
            f"--log={config.get('log_path', path_manager.get_log_path())}",
            f"--log-level={config.get('log_level', 'info')}",
            "--daemon=true"
        ])
        
        # 可选配置
        if config.get("secret"):
            cmd.append(f"--rpc-secret={config['secret']}")
        
        # 代理配置
        if config.get("all_proxy"):
            proxy = config["all_proxy"]
            # 直接使用完整的代理URL
            cmd.append(f"--all-proxy={proxy}")
        
        return cmd
    
    def is_running(self) -> bool:
        """检查aria2c服务是否运行"""
        try:
            # 检查进程
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    if proc.info['name'] == 'aria2c' and proc.info['cmdline']:
                        if '--enable-rpc' in ' '.join(proc.info['cmdline']):
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return False
        except Exception:
            return False
    
    def start_service(self) -> bool:
        """启动aria2c服务"""
        if self.is_running():
            return True
        
        try:
            config = self.load_config()
            cmd = self._build_command(config)
            
            # 创建日志目录
            Path(path_manager.get_log_path()).parent.mkdir(parents=True, exist_ok=True)
            
            # 启动进程（后台运行）
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            # 等待aria2c进程启动
            time.sleep(2)
            
            # 检查服务是否启动成功
            return self.is_running()
                
        except FileNotFoundError:
            print("错误: 未找到aria2c命令")
            return False
        except Exception as e:
            print(f"启动失败: {e}")
            return False
    
    def stop_service(self) -> bool:
        """停止aria2c服务"""
        if not self.is_running():
            return True
        
        try:
            # 通过进程名停止
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    if proc.info['name'] == 'aria2c' and proc.info['cmdline']:
                        if '--enable-rpc' in ' '.join(proc.info['cmdline']):
                            proc.terminate()
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return False
        except Exception:
            return False
    
    def get_status(self) -> Dict:
        """获取服务状态"""
        config = self.load_config()
        running = self.is_running()
        
        status = {
            "running": running,
            "config_file": str(self.config_path),
            "log_file": path_manager.get_log_path(),
            "config": config
        }
        
        # 获取运行中的进程信息
        if running:
            try:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                    try:
                        if proc.info['name'] == 'aria2c' and proc.info['cmdline']:
                            if '--enable-rpc' in ' '.join(proc.info['cmdline']):
                                status["pid"] = proc.info['pid']
                                status["start_time"] = proc.info['create_time']
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception:
                pass
        
        return status
    
    def get_logs(self, lines: int = 50) -> List[str]:
        """获取日志"""
        log_path = Path(path_manager.get_log_path())
        if not log_path.exists():
            return ["日志文件不存在"]
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                return [line.rstrip() for line in f.readlines()[-lines:]]
        except Exception:
            return ["读取日志失败"]
    
    def connect(self, host: Optional[str] = None, port: Optional[int] = None, secret: Optional[str] = None) -> bool:
        """连接到aria2服务"""
        try:
            config = self.load_config()
            host = host or config.get('host', 'localhost')
            port = port or config.get('port', 6800)
            secret = secret or config.get('secret', '')
            
            # 创建客户端和API - 使用默认参数
            if secret:
                client = Client(host=host, port=port, secret=secret)
            else:
                client = Client()  # 使用默认参数
            self.api = API(client)
            
            # 测试连接 - 使用get_stats方法
            self.api.get_stats()
            self.connected = True
            
            if self.on_connection_change:
                self.on_connection_change(True, "已连接")
            return True
            
        except Exception as e:
            self.connected = False
            if self.on_connection_change:
                self.on_connection_change(False, f"连接失败: {e}")
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        self.connected = False
        self.api = None
        if self.on_connection_change:
            self.on_connection_change(False, "已断开")
    
    def add_download(self, url: str, download_dir: Optional[str] = None, **options) -> Optional[str]:
        """添加下载任务"""
        if not self.connected or not self.api:
            return None
        
        try:
            # 验证URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return None
            
            # 设置选项
            download_options = {"max-connection-per-server": "16", "split": "16"}
            if download_dir:
                download_options["dir"] = download_dir
            download_options.update(options)
            
            # 添加下载
            download = self.api.add_uris([url], options=download_options)
            return download.gid
            
        except Exception:
            return None
    
    def add_batch_downloads(self, urls: List[str], download_dir: Optional[str] = None, **options) -> List[str]:
        """批量添加下载任务"""
        if not self.connected or not self.api:
            return []
        
        return [gid for url in urls if (gid := self.add_download(url, download_dir, **options))]
    
    def get_downloads(self) -> List[Dict]:
        """获取所有下载任务"""
        if not self.connected or not self.api:
            return []
        
        try:
            downloads = []
            
            # 获取所有任务
            all_tasks = self.api.get_downloads()
            
            # 按状态分类并格式化
            for download in all_tasks:
                status = download.status
                if status == "active":
                    label = "下载中"
                elif status == "waiting":
                    label = "等待中"
                elif status == "paused":
                    label = "已暂停"
                elif status == "complete":
                    label = "已完成"
                elif status == "error":
                    label = "错误"
                elif status == "removed":
                    label = "已删除"
                else:
                    label = status
                
                downloads.append(self._format_download_info(download, label))
            
            return downloads
            
        except Exception as e:
            print(f"获取下载任务失败: {e}")
            return []
    
    def _format_download_info(self, download: Download, status: str) -> Dict:
        """格式化下载信息"""
        try:
            # 获取URL和文件名
            url = "未知"
            filename = "未知文件"
            
            if download.files and download.files[0]:
                file_info = download.files[0]
                
                # 首先获取URL
                if hasattr(file_info, 'uris') and file_info.uris:
                    uri_info = file_info.uris[0]
                    if isinstance(uri_info, dict):
                        url = uri_info.get('uri', '未知')
                    else:
                        url = getattr(uri_info, 'uri', '未知')
                
                # 然后获取文件名
                if hasattr(file_info, 'path') and file_info.path and str(file_info.path) != '.' and len(str(file_info.path)) > 1:
                    filename = os.path.basename(str(file_info.path))
                elif url and url != '未知':
                    # 从URL中提取文件名
                    filename = self._extract_filename_from_url(url)
                else:
                    # 如果都没有，尝试从download对象获取更多信息
                    if hasattr(download, 'name') and download.name:
                        filename = download.name
                    elif hasattr(download, 'gid'):
                        filename = f"下载_{download.gid[:8]}"
            
            # 获取文件大小和进度
            total_length = download.total_length or 0
            completed_length = download.completed_length or 0
            
            if total_length > 0:
                # 显示已下载/总大小
                completed_str = self._format_size(completed_length)
                total_str = self._format_size(total_length)
                size_str = f"{completed_str}/{total_str}"
                progress = f"{int(completed_length * 100 / total_length)}%"
            else:
                size_str = "未知"
                progress = "0%"
            
            # 获取下载速度
            download_speed = download.download_speed or 0
            speed_str = self._format_speed(download_speed)
            
            # 计算剩余时间
            if download_speed > 0 and total_length > completed_length:
                remaining_bytes = total_length - completed_length
                remaining_time = remaining_bytes // download_speed
                time_str = self._format_time(remaining_time)
            else:
                time_str = "未知"
            
            
            return {
                "gid": download.gid,
                "status": status,
                "filename": filename,
                "url": url,
                "size": size_str,
                "progress": progress,
                "speed": speed_str,
                "time": time_str
            }
            
        except Exception as e:
            print(f"格式化下载信息时出错: {e}")
            return {
                "gid": download.gid,
                "status": status,
                "filename": "未知文件",
                "url": "未知",
                "size": "未知",
                "progress": "0%",
                "speed": "0 B/s",
                "time": "未知"
            }
    
    def pause_downloads(self, gids: List[str]) -> bool:
        """暂停下载任务"""
        if not self.connected or not self.api:
            return False
        
        try:
            # 获取所有任务
            all_tasks = self.api.get_downloads()
            
            # 找到对应的任务
            tasks_to_pause = []
            for gid in gids:
                for task in all_tasks:
                    if task.gid == gid:
                        tasks_to_pause.append(task)
                        break
            
            # 暂停任务
            if tasks_to_pause:
                self.api.pause(tasks_to_pause)
                return True
            return False
        except Exception as e:
            print(f"暂停任务失败: {e}")
            return False
    
    def resume_downloads(self, gids: List[str]) -> bool:
        """继续下载任务"""
        if not self.connected or not self.api:
            return False
        
        try:
            # 获取所有任务
            all_tasks = self.api.get_downloads()
            
            # 找到对应的任务
            tasks_to_resume = []
            for gid in gids:
                for task in all_tasks:
                    if task.gid == gid:
                        tasks_to_resume.append(task)
                        break
            
            # 恢复任务
            if tasks_to_resume:
                self.api.resume(tasks_to_resume)
                return True
            return False
        except Exception as e:
            print(f"恢复任务失败: {e}")
            return False
    
    def remove_downloads(self, gids: List[str]) -> bool:
        """删除下载任务"""
        if not self.connected or not self.api:
            return False
        
        try:
            # 获取所有任务
            all_tasks = self.api.get_downloads()
            
            # 找到对应的任务
            tasks_to_remove = []
            for gid in gids:
                for task in all_tasks:
                    if task.gid == gid:
                        tasks_to_remove.append(task)
                        break
            
            # 删除任务
            if tasks_to_remove:
                # 尝试删除任务，如果失败则强制删除
                try:
                    self.api.remove(tasks_to_remove)
                except Exception as e:
                    print(f"正常删除失败，尝试强制删除: {e}")
                    # 强制删除，不删除文件
                    self.api.remove(tasks_to_remove, files=False)
                return True
            return False
        except Exception as e:
            print(f"删除任务失败: {e}")
            # 如果还是失败，尝试使用GID直接删除
            try:
                for gid in gids:
                    self.api.remove([gid], files=False)
                return True
            except Exception as e2:
                print(f"强制删除也失败: {e2}")
                return False
    
    def _extract_filename_from_url(self, url: str) -> str:
        """从URL中提取文件名"""
        if not url:
            return "未知文件"
        
        try:
            from urllib.parse import urlparse, unquote, parse_qs
            
            # 解析URL
            parsed = urlparse(url)
            
            # 首先检查Content-Disposition头中的filename
            if parsed.query:
                query_params = parse_qs(parsed.query)
                # 检查各种可能的disposition参数
                for param_name in ['response-content-disposition', 'rcd', 'content-disposition']:
                    if param_name in query_params:
                        disposition = query_params[param_name][0]
                        if 'filename=' in disposition:
                            # 提取filename=后面的值
                            filename_part = disposition.split('filename=')[1]
                            # 去掉引号和分号
                            filename = filename_part.strip('"\' ;')
                            filename = unquote(filename)
                            if filename:
                                return filename
            
            # 从路径中提取文件名
            path = parsed.path
            if path and path != '/':
                filename = os.path.basename(path)
                if filename:
                    # URL解码
                    filename = unquote(filename)
                    return filename
            
            # 如果路径中没有文件名，尝试从查询参数中获取
            if parsed.query:
                # 查找常见的文件名参数
                for param in ['filename', 'name', 'file']:
                    if param in parsed.query:
                        # 简单的参数解析
                        for part in parsed.query.split('&'):
                            if part.startswith(f'{param}='):
                                filename = part.split('=', 1)[1]
                                filename = unquote(filename)
                                if filename and filename != 'download':  # 避免返回无意义的参数值
                                    return filename
            
            # 如果都没有，返回URL的最后一部分
            return os.path.basename(parsed.path) or "下载文件"
            
        except Exception as e:
            print(f"URL解析错误: {e}")
            return "未知文件"
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _format_speed(self, speed_bytes: int) -> str:
        """格式化下载速度"""
        return f"{self._format_size(speed_bytes)}/s" if speed_bytes > 0 else "0 B/s"
    
    def _format_time(self, seconds: int) -> str:
        """格式化时间"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分{seconds % 60}秒"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}小时{minutes}分钟"
