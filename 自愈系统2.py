import sys
import os
import psutil
import time
import threading
import logging
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QTextEdit, QTabWidget, 
                             QProgressBar, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QGroupBox, QSpinBox, QDoubleSpinBox, 
                             QCheckBox, QMessageBox, QSplitter, QSystemTrayIcon, 
                             QMenu, QAction, QStyle, QComboBox, QLineEdit, QInputDialog)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread, QSettings
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
import json
import subprocess
import socket
import requests
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import deque
import platform
import hashlib

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("self_healing_system.log"),
        logging.StreamHandler()
    ]
)

class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self, db_path="self_healing_system.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建系统状态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                temperature REAL,
                network_latency REAL,
                process_count INTEGER
            )
        ''')
        
        # 创建异常记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metric TEXT,
                value REAL,
                threshold REAL,
                severity TEXT,
                resolved BOOLEAN DEFAULT 0,
                resolved_at DATETIME
            )
        ''')
        
        # 创建自愈动作记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS healing_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                anomaly_type TEXT,
                action_description TEXT,
                result TEXT,
                success BOOLEAN
            )
        ''')
        
        # 创建通知记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                type TEXT,
                title TEXT,
                message TEXT,
                sent BOOLEAN DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_system_stats(self, stats):
        """保存系统状态数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO system_stats 
            (cpu_percent, memory_percent, disk_percent, temperature, network_latency, process_count)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            stats['cpu_percent'],
            stats['memory_percent'],
            stats['disk_percent'],
            stats['temperature'],
            stats['network_latency'],
            stats['process_count']
        ))
        
        conn.commit()
        conn.close()
    
    def save_anomaly(self, anomaly_data):
        """保存异常记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for anomaly_id, data in anomaly_data.items():
            cursor.execute('''
                INSERT INTO anomalies (metric, value, threshold, severity)
                VALUES (?, ?, ?, ?)
            ''', (data['metric'], data['value'], data['threshold'], data['severity']))
        
        conn.commit()
        conn.close()
    
    def save_healing_action(self, action_data):
        """保存自愈动作记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO healing_actions (anomaly_type, action_description, result, success)
            VALUES (?, ?, ?, ?)
        ''', (
            action_data['anomaly_type'],
            action_data['action_description'],
            action_data['result'],
            action_data['success']
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_stats(self, hours=24):
        """获取最近指定小时内的系统状态数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        cursor.execute('''
            SELECT timestamp, cpu_percent, memory_percent, disk_percent, temperature, network_latency
            FROM system_stats 
            WHERE timestamp > ?
            ORDER BY timestamp
        ''', (cutoff_time,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results

class NotificationManager:
    """通知管理器"""
    
    def __init__(self):
        self.settings = QSettings("SelfHealingSystem", "Notifications")
        self.email_enabled = self.settings.value("email_enabled", False, type=bool)
        self.smtp_server = self.settings.value("smtp_server", "")
        self.smtp_port = self.settings.value("smtp_port", 587, type=int)
        self.email_from = self.settings.value("email_from", "")
        self.email_to = self.settings.value("email_to", "")
        self.email_username = self.settings.value("email_username", "")
        self.email_password = self.settings.value("email_password", "")
    
    def send_email_notification(self, subject, message):
        """发送邮件通知"""
        if not self.email_enabled:
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_username, self.email_password)
            text = msg.as_string()
            server.sendmail(self.email_from, self.email_to, text)
            server.quit()
            
            logging.info(f"邮件通知已发送: {subject}")
            return True
        except Exception as e:
            logging.error(f"发送邮件通知失败: {e}")
            return False
    
    def send_desktop_notification(self, title, message, duration=5000):
        """发送桌面通知"""
        try:
            # 这里可以使用系统通知API，这里简化处理
            logging.info(f"桌面通知: {title} - {message}")
            return True
        except Exception as e:
            logging.error(f"发送桌面通知失败: {e}")
            return False
    
    def save_settings(self, settings):
        """保存通知设置"""
        self.email_enabled = settings.get('email_enabled', False)
        self.smtp_server = settings.get('smtp_server', '')
        self.smtp_port = settings.get('smtp_port', 587)
        self.email_from = settings.get('email_from', '')
        self.email_to = settings.get('email_to', '')
        self.email_username = settings.get('email_username', '')
        self.email_password = settings.get('email_password', '')
        
        # 保存到QSettings
        self.settings.setValue("email_enabled", self.email_enabled)
        self.settings.setValue("smtp_server", self.smtp_server)
        self.settings.setValue("smtp_port", self.smtp_port)
        self.settings.setValue("email_from", self.email_from)
        self.settings.setValue("email_to", self.email_to)
        self.settings.setValue("email_username", self.email_username)
        self.settings.setValue("email_password", self.email_password)

class SystemMonitor(QThread):
    """系统监控线程"""
    system_stats_updated = pyqtSignal(dict)
    anomaly_detected = pyqtSignal(dict)
    service_status_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.monitoring_interval = 2  # 监控间隔(秒)
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0,
            'temperature': 80.0,  # 摄氏度
            'network_latency': 100.0,  # 毫秒
            'disk_io_percent': 80.0,  # 磁盘IO使用率
            'network_bandwidth': 90.0  # 网络带宽使用率
        }
        self.history = deque(maxlen=100)  # 存储历史数据
        self.monitored_services = ['nginx', 'mysql', 'apache2', 'postgresql']
        self.db_manager = DatabaseManager()
        
    def run(self):
        """主监控循环"""
        while self.running:
            try:
                stats = self.collect_system_stats()
                self.history.append(stats)
                self.system_stats_updated.emit(stats)
                
                # 保存到数据库
                self.db_manager.save_system_stats(stats)
                
                # 检测异常
                anomalies = self.detect_anomalies(stats)
                if anomalies:
                    self.anomaly_detected.emit(anomalies)
                    # 保存异常记录
                    self.db_manager.save_anomaly(anomalies)
                
                # 检查服务状态
                service_status = self.check_services_status()
                self.service_status_updated.emit(service_status)
                
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logging.error(f"监控错误: {e}")
    
    def collect_system_stats(self):
        """收集系统统计信息"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 磁盘使用率
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # 温度信息（如果可用）
        try:
            temperatures = psutil.sensors_temperatures()
            if 'coretemp' in temperatures:
                core_temp = max([temp.current for temp in temperatures['coretemp']])
            else:
                core_temp = 0
        except:
            core_temp = 0
        
        # 网络延迟
        network_latency = self.measure_network_latency()
        
        # 进程数量
        process_count = len(psutil.pids())
        
        # 系统启动时间
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        # 磁盘IO统计
        disk_io = psutil.disk_io_counters()
        disk_io_percent = 0
        if disk_io:
            # 计算磁盘IO使用率（简化计算）
            disk_io_percent = min(100, (disk_io.read_bytes + disk_io.write_bytes) / (1024 * 1024 * 1024))
        
        # 网络带宽使用率
        network_io = psutil.net_io_counters()
        network_bandwidth = 0
        if network_io:
            # 计算网络带宽使用率（简化计算）
            network_bandwidth = min(100, (network_io.bytes_sent + network_io.bytes_recv) / (1024 * 1024))
        
        return {
            'timestamp': datetime.now(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'disk_percent': disk_percent,
            'temperature': core_temp,
            'network_latency': network_latency,
            'process_count': process_count,
            'uptime': str(uptime).split('.')[0],  # 去掉微秒部分
            'disk_io_percent': disk_io_percent,
            'network_bandwidth': network_bandwidth
        }
    
    def measure_network_latency(self, host="8.8.8.8", port=53, timeout=3):
        """测量网络延迟"""
        try:
            start = time.time()
            socket.create_connection((host, port), timeout=timeout)
            end = time.time()
            return (end - start) * 1000  # 转换为毫秒
        except:
            return float('inf')  # 连接失败
    
    def check_services_status(self):
        """检查服务状态"""
        service_status = {}
        
        for service in self.monitored_services:
            try:
                # 根据操作系统使用不同的命令检查服务状态
                if platform.system() == "Windows":
                    cmd = f"sc query {service}"
                else:
                    cmd = f"systemctl is-active {service}"
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                service_status[service] = result.returncode == 0
            except Exception as e:
                service_status[service] = False
                logging.error(f"检查服务状态失败 {service}: {e}")
        
        return service_status
    
    def detect_anomalies(self, stats):
        """检测系统异常"""
        anomalies = {}
        
        if stats['cpu_percent'] > self.thresholds['cpu_percent']:
            anomalies['cpu'] = {
                'metric': 'CPU使用率',
                'value': stats['cpu_percent'],
                'threshold': self.thresholds['cpu_percent'],
                'severity': 'high' if stats['cpu_percent'] > 90 else 'medium',
                'timestamp': stats['timestamp']
            }
        
        if stats['memory_percent'] > self.thresholds['memory_percent']:
            anomalies['memory'] = {
                'metric': '内存使用率',
                'value': stats['memory_percent'],
                'threshold': self.thresholds['memory_percent'],
                'severity': 'high' if stats['memory_percent'] > 95 else 'medium',
                'timestamp': stats['timestamp']
            }
        
        if stats['disk_percent'] > self.thresholds['disk_percent']:
            anomalies['disk'] = {
                'metric': '磁盘使用率',
                'value': stats['disk_percent'],
                'threshold': self.thresholds['disk_percent'],
                'severity': 'high' if stats['disk_percent'] > 95 else 'medium',
                'timestamp': stats['timestamp']
            }
        
        if stats['temperature'] > self.thresholds['temperature'] and stats['temperature'] > 0:
            anomalies['temperature'] = {
                'metric': '温度',
                'value': stats['temperature'],
                'threshold': self.thresholds['temperature'],
                'severity': 'high' if stats['temperature'] > 90 else 'medium',
                'timestamp': stats['timestamp']
            }
        
        if stats['network_latency'] > self.thresholds['network_latency']:
            anomalies['network'] = {
                'metric': '网络延迟',
                'value': stats['network_latency'],
                'threshold': self.thresholds['network_latency'],
                'severity': 'high' if stats['network_latency'] > 500 else 'medium',
                'timestamp': stats['timestamp']
            }
        
        if stats['disk_io_percent'] > self.thresholds['disk_io_percent']:
            anomalies['disk_io'] = {
                'metric': '磁盘IO使用率',
                'value': stats['disk_io_percent'],
                'threshold': self.thresholds['disk_io_percent'],
                'severity': 'high' if stats['disk_io_percent'] > 90 else 'medium',
                'timestamp': stats['timestamp']
            }
        
        if stats['network_bandwidth'] > self.thresholds['network_bandwidth']:
            anomalies['network_bandwidth'] = {
                'metric': '网络带宽使用率',
                'value': stats['network_bandwidth'],
                'threshold': self.thresholds['network_bandwidth'],
                'severity': 'high' if stats['network_bandwidth'] > 95 else 'medium',
                'timestamp': stats['timestamp']
            }
        
        return anomalies if anomalies else None
    
    def add_monitored_service(self, service_name):
        """添加监控的服务"""
        if service_name not in self.monitored_services:
            self.monitored_services.append(service_name)
    
    def remove_monitored_service(self, service_name):
        """移除监控的服务"""
        if service_name in self.monitored_services:
            self.monitored_services.remove(service_name)
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False

class SelfHealingEngine:
    """自愈引擎"""
    
    def __init__(self):
        self.healing_actions = {
            'high_cpu': self.handle_high_cpu,
            'high_memory': self.handle_high_memory,
            'high_disk': self.handle_high_disk,
            'high_temperature': self.handle_high_temperature,
            'high_network_latency': self.handle_high_network_latency,
            'high_disk_io': self.handle_high_disk_io,
            'high_network_bandwidth': self.handle_high_network_bandwidth,
            'service_down': self.handle_service_down
        }
        self.db_manager = DatabaseManager()
        self.notification_manager = NotificationManager()
    
    def execute_healing_action(self, anomaly_type, anomaly_data):
        """执行自愈动作"""
        action_func = self.healing_actions.get(anomaly_type)
        if action_func:
            try:
                result = action_func(anomaly_data)
                
                # 记录自愈动作
                self.db_manager.save_healing_action({
                    'anomaly_type': anomaly_type,
                    'action_description': f"处理{anomaly_data.get('metric', '未知')}异常",
                    'result': result,
                    'success': '失败' not in result
                })
                
                # 发送通知
                if '失败' not in result:
                    self.notification_manager.send_email_notification(
                        "自愈系统 - 异常已处理",
                        f"系统已自动处理异常: {anomaly_data.get('metric', '未知')}\n处理结果: {result}"
                    )
                
                return result
            except Exception as e:
                error_msg = f"自愈动作执行失败: {e}"
                self.db_manager.save_healing_action({
                    'anomaly_type': anomaly_type,
                    'action_description': f"处理{anomaly_data.get('metric', '未知')}异常",
                    'result': error_msg,
                    'success': False
                })
                return error_msg
        else:
            return f"未知异常类型: {anomaly_type}"
    
    def handle_high_cpu(self, anomaly_data):
        """处理高CPU使用率"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # 按CPU使用率排序
            processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
            
            if processes and processes[0]['cpu_percent'] > 50:
                pid = processes[0]['pid']
                name = processes[0]['name']
                psutil.Process(pid).terminate()
                return f"已终止高CPU进程: {name} (PID: {pid})"
            else:
                return "未找到明显的高CPU进程，建议检查系统负载"
        except Exception as e:
            return f"处理高CPU失败: {e}"
    
    def handle_high_memory(self, anomaly_data):
        """处理高内存使用率"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    processes.append((proc.info['pid'], proc.info['name'], 
                                     proc.info['memory_info'].rss))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # 按内存使用量排序
            processes.sort(key=lambda x: x[2], reverse=True)
            
            if processes and processes[0][2] > 100 * 1024 * 1024:  # 超过100MB
                pid = processes[0][0]
                name = processes[0][1]
                psutil.Process(pid).terminate()
                return f"已终止高内存进程: {name} (PID: {pid})"
            else:
                return "未找到明显的高内存进程，建议检查内存泄漏"
        except Exception as e:
            return f"处理高内存失败: {e}"
    
    def handle_high_disk(self, anomaly_data):
        """处理高磁盘使用率"""
        # 建议清理临时文件
        commands = []
        
        if platform.system() == "Windows":
            commands = [
                "del /q /f %temp%\\*",  # 清理临时文件
                "for /d %x in (%temp%\\*) do @rd /s /q \"%x\"",  # 清理临时目录
            ]
        else:
            commands = [
                "sudo rm -rf /tmp/*",  # 清理/tmp目录
                "sudo journalctl --vacuum-time=7d",  # 清理7天前的日志
            ]
        
        results = []
        for cmd in commands:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    results.append(f"执行成功: {cmd}")
                else:
                    results.append(f"执行失败: {cmd} - {result.stderr}")
            except Exception as e:
                results.append(f"执行异常: {cmd} - {e}")
        
        return "; ".join(results) if results else "未执行磁盘清理操作"
    
    def handle_high_temperature(self, anomaly_data):
        """处理高温"""
        # 尝试降低系统负载
        try:
            if platform.system() == "Linux":
                # 设置CPU频率限制（如果可用）
                subprocess.run("echo powersave | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor", 
                              shell=True, capture_output=True)
                return "已尝试降低CPU频率以控制温度"
            else:
                return "无法直接控制温度，建议检查散热系统"
        except:
            return "无法直接控制温度，建议检查散热系统"
    
    def handle_high_network_latency(self, anomaly_data):
        """处理高网络延迟"""
        # 尝试刷新DNS缓存和网络接口
        commands = []
        
        if platform.system() == "Windows":
            commands = [
                "ipconfig /flushdns",  # 刷新DNS缓存
                "netsh int ip reset",  # 重置IP
            ]
        else:
            commands = [
                "sudo systemctl restart NetworkManager",  # 重启网络管理器
                "sudo systemd-resolve --flush-caches",  # 刷新DNS缓存
            ]
        
        results = []
        for cmd in commands:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    results.append(f"执行成功: {cmd}")
                else:
                    results.append(f"执行失败: {cmd} - {result.stderr}")
            except Exception as e:
                results.append(f"执行异常: {cmd} - {e}")
        
        return "; ".join(results) if results else "未执行网络修复操作"
    
    def handle_high_disk_io(self, anomaly_data):
        """处理高磁盘IO"""
        try:
            # 尝试找出高IO进程
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'io_counters']):
                try:
                    io_counters = proc.info['io_counters']
                    if io_counters:
                        total_io = io_counters.read_bytes + io_counters.write_bytes
                        processes.append((proc.info['pid'], proc.info['name'], total_io))
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                    pass
            
            # 按IO使用量排序
            processes.sort(key=lambda x: x[2], reverse=True)
            
            if processes and processes[0][2] > 100 * 1024 * 1024:  # 超过100MB
                pid = processes[0][0]
                name = processes[0][1]
                psutil.Process(pid).terminate()
                return f"已终止高IO进程: {name} (PID: {pid})"
            else:
                return "未找到明显的高IO进程，建议检查磁盘使用情况"
        except Exception as e:
            return f"处理高磁盘IO失败: {e}"
    
    def handle_high_network_bandwidth(self, anomaly_data):
        """处理高网络带宽使用率"""
        try:
            # 尝试找出高网络使用进程
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    connections = proc.info['connections']
                    if connections:
                        network_usage = len(connections)
                        processes.append((proc.info['pid'], proc.info['name'], network_usage))
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                    pass
            
            # 按网络连接数排序
            processes.sort(key=lambda x: x[2], reverse=True)
            
            if processes and processes[0][2] > 100:  # 超过100个连接
                pid = processes[0][0]
                name = processes[0][1]
                psutil.Process(pid).terminate()
                return f"已终止高网络使用进程: {name} (PID: {pid})"
            else:
                return "未找到明显的高网络使用进程，建议检查网络流量"
        except Exception as e:
            return f"处理高网络带宽失败: {e}"
    
    def handle_service_down(self, anomaly_data):
        """处理服务宕机"""
        service_name = anomaly_data.get('service_name', '')
        if not service_name:
            return "未指定服务名称"
        
        try:
            if platform.system() == "Windows":
                cmd = f"net start {service_name}"
            else:
                cmd = f"sudo systemctl start {service_name}"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"服务 {service_name} 已成功启动"
            else:
                return f"启动服务 {service_name} 失败: {result.stderr}"
        except Exception as e:
            return f"处理服务宕机失败: {e}"

class DashboardWidget(QWidget):
    """仪表板部件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 系统状态概览
        status_group = QGroupBox("系统状态概览")
        status_layout = QVBoxLayout()
        
        self.status_labels = {}
        metrics = [
            ('cpu', 'CPU使用率'),
            ('memory', '内存使用率'), 
            ('disk', '磁盘使用率'),
            ('temperature', '温度'),
            ('network', '网络延迟'),
            ('disk_io', '磁盘IO'),
            ('network_bandwidth', '网络带宽'),
            ('processes', '进程数量'),
            ('uptime', '运行时间')
        ]
        
        for metric, name in metrics:
            hbox = QHBoxLayout()
            label = QLabel(f"{name}:")
            value_label = QLabel("--")
            self.status_labels[metric] = value_label
            
            hbox.addWidget(label)
            hbox.addWidget(value_label)
            hbox.addStretch()
            status_layout.addLayout(hbox)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 进度条显示
        self.progress_bars = {}
        progress_metrics = ['cpu', 'memory', 'disk', 'disk_io', 'network_bandwidth']
        
        for metric in progress_metrics:
            hbox = QHBoxLayout()
            label = QLabel(f"{metrics[progress_metrics.index(metric)][1]}:")
            progress_bar = QProgressBar()
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(100)
            self.progress_bars[metric] = progress_bar
            
            hbox.addWidget(label)
            hbox.addWidget(progress_bar)
            layout.addLayout(hbox)
        
        # 服务状态
        services_group = QGroupBox("服务状态")
        services_layout = QVBoxLayout()
        
        self.service_labels = {}
        services = ['nginx', 'mysql', 'apache2', 'postgresql']
        
        for service in services:
            hbox = QHBoxLayout()
            label = QLabel(f"{service}:")
            status_label = QLabel("未知")
            status_label.setStyleSheet("color: gray")
            self.service_labels[service] = status_label
            
            hbox.addWidget(label)
            hbox.addWidget(status_label)
            hbox.addStretch()
            services_layout.addLayout(hbox)
        
        services_group.setLayout(services_layout)
        layout.addWidget(services_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def update_stats(self, stats):
        """更新统计信息显示"""
        # 更新标签
        self.status_labels['cpu'].setText(f"{stats['cpu_percent']:.1f}%")
        self.status_labels['memory'].setText(f"{stats['memory_percent']:.1f}%")
        self.status_labels['disk'].setText(f"{stats['disk_percent']:.1f}%")
        self.status_labels['temperature'].setText(f"{stats['temperature']:.1f}°C")
        self.status_labels['network'].setText(f"{stats['network_latency']:.1f}ms")
        self.status_labels['disk_io'].setText(f"{stats['disk_io_percent']:.1f}%")  # 修正键名
        self.status_labels['network_bandwidth'].setText(f"{stats['network_bandwidth']:.1f}%")  # 修正键名
        self.status_labels['processes'].setText(f"{stats['process_count']}")
        self.status_labels['uptime'].setText(stats['uptime'])
        
        # 更新进度条
        self.progress_bars['cpu'].setValue(int(stats['cpu_percent']))
        self.progress_bars['memory'].setValue(int(stats['memory_percent']))
        self.progress_bars['disk'].setValue(int(stats['disk_percent']))
        self.progress_bars['disk_io'].setValue(int(stats['disk_io_percent']))  # 修正键名
        self.progress_bars['network_bandwidth'].setValue(int(stats['network_bandwidth']))  # 修正键名
        
        # 根据阈值设置颜色
        for metric, bar in self.progress_bars.items():
            # 修正获取值的方式
            if metric in ['cpu', 'memory', 'disk']:
                value = stats[f"{metric}_percent"]
            elif metric == 'disk_io':
                value = stats['disk_io_percent']
            elif metric == 'network_bandwidth':
                value = stats['network_bandwidth']
            else:
                value = stats[metric] if metric in stats else 0
                
            if value > 90:
                bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
            elif value > 80:
                bar.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
            else:
                bar.setStyleSheet("QProgressBar::chunk { background-color: green; }")
    
    def update_service_status(self, service_status):
        """更新服务状态显示"""
        for service, status in service_status.items():
            if service in self.service_labels:
                if status:
                    self.service_labels[service].setText("运行中")
                    self.service_labels[service].setStyleSheet("color: green")
                else:
                    self.service_labels[service].setText("已停止")
                    self.service_labels[service].setStyleSheet("color: red")

class AnomaliesWidget(QWidget):
    """异常检测部件"""
    
    def __init__(self, healing_engine):
        super().__init__()
        self.anomalies = {}
        self.healing_engine = healing_engine
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 异常表格
        self.anomaly_table = QTableWidget(0, 6)
        self.anomaly_table.setHorizontalHeaderLabels([
            "时间", "指标", "当前值", "阈值", "严重程度", "状态"
        ])
        self.anomaly_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(QLabel("检测到的异常:"))
        layout.addWidget(self.anomaly_table)
        
        # 自愈动作按钮
        button_layout = QHBoxLayout()
        self.heal_button = QPushButton("执行自愈动作")
        self.heal_button.clicked.connect(self.execute_healing)
        
        self.clear_button = QPushButton("清空异常列表")
        self.clear_button.clicked.connect(self.clear_anomalies)
        
        button_layout.addWidget(self.heal_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def add_anomaly(self, anomalies):
        """添加异常到表格"""
        self.anomalies.update(anomalies)
        self.update_table()
    
    def update_table(self):
        """更新异常表格"""
        self.anomaly_table.setRowCount(len(self.anomalies))
        
        for row, (anomaly_id, anomaly_data) in enumerate(self.anomalies.items()):
            self.anomaly_table.setItem(row, 0, QTableWidgetItem(
                anomaly_data.get('timestamp', datetime.now()).strftime("%H:%M:%S")
            ))
            self.anomaly_table.setItem(row, 1, QTableWidgetItem(
                anomaly_data.get('metric', '未知')
            ))
            self.anomaly_table.setItem(row, 2, QTableWidgetItem(
                f"{anomaly_data.get('value', 0):.1f}"
            ))
            self.anomaly_table.setItem(row, 3, QTableWidgetItem(
                f"{anomaly_data.get('threshold', 0):.1f}"
            ))
            
            severity_item = QTableWidgetItem(anomaly_data.get('severity', '未知'))
            severity = anomaly_data.get('severity', '')
            if severity == 'high':
                severity_item.setBackground(QColor(255, 100, 100))  # 红色
            elif severity == 'medium':
                severity_item.setBackground(QColor(255, 200, 100))  # 橙色
            
            self.anomaly_table.setItem(row, 4, severity_item)
            
            status_item = QTableWidgetItem("未处理")
            status_item.setBackground(QColor(255, 255, 100))  # 黄色
            self.anomaly_table.setItem(row, 5, status_item)
    
    def execute_healing(self):
        """执行自愈动作"""
        if not self.anomalies:
            QMessageBox.information(self, "信息", "当前没有检测到异常")
            return
        
        # 执行自愈动作
        results = []
        for anomaly_id, anomaly_data in self.anomalies.items():
            result = self.healing_engine.execute_healing_action(anomaly_id, anomaly_data)
            results.append(f"{anomaly_data['metric']}: {result}")
            
            # 更新表格状态
            for row in range(self.anomaly_table.rowCount()):
                if self.anomaly_table.item(row, 1).text() == anomaly_data['metric']:
                    status_item = QTableWidgetItem("已处理")
                    status_item.setBackground(QColor(100, 255, 100))  # 绿色
                    self.anomaly_table.setItem(row, 5, status_item)
                    break
        
        # 显示结果
        QMessageBox.information(self, "自愈动作结果", "\n".join(results))
    
    def clear_anomalies(self):
        """清空异常列表"""
        self.anomalies.clear()
        self.anomaly_table.setRowCount(0)

class LogWidget(QWidget):
    """日志部件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))
        
        layout.addWidget(QLabel("系统日志:"))
        layout.addWidget(self.log_text)
        
        # 日志控制按钮
        button_layout = QHBoxLayout()
        self.clear_button = QPushButton("清空日志")
        self.clear_button.clicked.connect(self.log_text.clear)
        
        self.save_button = QPushButton("保存日志")
        self.save_button.clicked.connect(self.save_logs)
        
        self.export_button = QPushButton("导出数据")
        self.export_button.clicked.connect(self.export_data)
        
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.export_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def add_log(self, message, level="INFO"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 根据日志级别设置颜色
        if level == "ERROR":
            color = "red"
        elif level == "WARNING":
            color = "orange"
        else:
            color = "black"
        
        log_entry = f'<font color="{color}">[{timestamp}] {level}: {message}</font>'
        self.log_text.append(log_entry)
        
        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def save_logs(self):
        """保存日志到文件"""
        try:
            with open("self_healing_log.txt", "w") as f:
                f.write(self.log_text.toPlainText())
            QMessageBox.information(self, "成功", "日志已保存到 self_healing_log.txt")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存日志失败: {e}")
    
    def export_data(self):
        """导出监控数据"""
        try:
            db_manager = DatabaseManager()
            stats = db_manager.get_recent_stats(24)  # 获取最近24小时数据
            
            with open("system_stats_export.csv", "w") as f:
                f.write("时间,CPU使用率,内存使用率,磁盘使用率,温度,网络延迟\n")
                for row in stats:
                    f.write(f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]}\n")
            
            QMessageBox.information(self, "成功", "数据已导出到 system_stats_export.csv")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出数据失败: {e}")

class SettingsWidget(QWidget):
    """设置部件"""
    
    def __init__(self, monitor, notification_manager):
        super().__init__()
        self.monitor = monitor
        self.notification_manager = notification_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 监控间隔设置
        interval_group = QGroupBox("监控设置")
        interval_layout = QVBoxLayout()
        
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("监控间隔(秒):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(self.monitor.monitoring_interval)
        self.interval_spin.valueChanged.connect(self.update_interval)
        hbox.addWidget(self.interval_spin)
        hbox.addStretch()
        interval_layout.addLayout(hbox)
        
        interval_group.setLayout(interval_layout)
        layout.addWidget(interval_group)
        
        # 阈值设置
        thresholds_group = QGroupBox("异常阈值设置")
        thresholds_layout = QVBoxLayout()
        
        self.threshold_controls = {}
        thresholds = [
            ('cpu_percent', 'CPU使用率阈值(%)', 80.0),
            ('memory_percent', '内存使用率阈值(%)', 85.0),
            ('disk_percent', '磁盘使用率阈值(%)', 90.0),
            ('temperature', '温度阈值(°C)', 80.0),
            ('network_latency', '网络延迟阈值(ms)', 100.0),
            ('disk_io_percent', '磁盘IO阈值(%)', 80.0),
            ('network_bandwidth', '网络带宽阈值(%)', 90.0)
        ]
        
        for key, label, default in thresholds:
            hbox = QHBoxLayout()
            hbox.addWidget(QLabel(label))
            spinbox = QDoubleSpinBox()
            spinbox.setRange(0, 1000)
            spinbox.setValue(self.monitor.thresholds.get(key, default))
            spinbox.valueChanged.connect(lambda value, k=key: self.update_threshold(k, value))
            hbox.addWidget(spinbox)
            hbox.addStretch()
            thresholds_layout.addLayout(hbox)
            self.threshold_controls[key] = spinbox
        
        thresholds_group.setLayout(thresholds_layout)
        layout.addWidget(thresholds_group)
        
        # 服务监控设置
        services_group = QGroupBox("服务监控设置")
        services_layout = QVBoxLayout()
        
        hbox = QHBoxLayout()
        self.service_combo = QComboBox()
        self.service_combo.setEditable(True)
        self.service_combo.addItems(['nginx', 'mysql', 'apache2', 'postgresql', 'redis'])
        
        self.add_service_button = QPushButton("添加服务")
        self.add_service_button.clicked.connect(self.add_service)
        
        self.remove_service_button = QPushButton("移除服务")
        self.remove_service_button.clicked.connect(self.remove_service)
        
        hbox.addWidget(QLabel("监控服务:"))
        hbox.addWidget(self.service_combo)
        hbox.addWidget(self.add_service_button)
        hbox.addWidget(self.remove_service_button)
        hbox.addStretch()
        
        services_layout.addLayout(hbox)
        services_group.setLayout(services_layout)
        layout.addWidget(services_group)
        
        # 通知设置
        notifications_group = QGroupBox("通知设置")
        notifications_layout = QVBoxLayout()
        
        self.email_checkbox = QCheckBox("启用邮件通知")
        self.email_checkbox.setChecked(self.notification_manager.email_enabled)
        self.email_checkbox.stateChanged.connect(self.toggle_email_notifications)
        notifications_layout.addWidget(self.email_checkbox)
        
        # 邮件设置
        email_settings_layout = QVBoxLayout()
        
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("SMTP服务器:"))
        self.smtp_server_edit = QLineEdit(self.notification_manager.smtp_server)
        hbox.addWidget(self.smtp_server_edit)
        notifications_layout.addLayout(hbox)
        
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("SMTP端口:"))
        self.smtp_port_edit = QLineEdit(str(self.notification_manager.smtp_port))
        hbox.addWidget(self.smtp_port_edit)
        notifications_layout.addLayout(hbox)
        
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("发件人邮箱:"))
        self.email_from_edit = QLineEdit(self.notification_manager.email_from)
        hbox.addWidget(self.email_from_edit)
        notifications_layout.addLayout(hbox)
        
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("收件人邮箱:"))
        self.email_to_edit = QLineEdit(self.notification_manager.email_to)
        hbox.addWidget(self.email_to_edit)
        notifications_layout.addLayout(hbox)
        
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("邮箱用户名:"))
        self.email_username_edit = QLineEdit(self.notification_manager.email_username)
        hbox.addWidget(self.email_username_edit)
        notifications_layout.addLayout(hbox)
        
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("邮箱密码:"))
        self.email_password_edit = QLineEdit(self.notification_manager.email_password)
        self.email_password_edit.setEchoMode(QLineEdit.Password)
        hbox.addWidget(self.email_password_edit)
        notifications_layout.addLayout(hbox)
        
        self.save_email_button = QPushButton("保存邮件设置")
        self.save_email_button.clicked.connect(self.save_email_settings)
        notifications_layout.addWidget(self.save_email_button)
        
        self.test_email_button = QPushButton("测试邮件发送")
        self.test_email_button.clicked.connect(self.test_email)
        notifications_layout.addWidget(self.test_email_button)
        
        notifications_group.setLayout(notifications_layout)
        layout.addWidget(notifications_group)
        
        # 自愈设置
        healing_group = QGroupBox("自愈设置")
        healing_layout = QVBoxLayout()
        
        self.auto_heal_checkbox = QCheckBox("自动执行自愈动作")
        healing_layout.addWidget(self.auto_heal_checkbox)
        
        healing_group.setLayout(healing_layout)
        layout.addWidget(healing_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def update_interval(self, value):
        """更新监控间隔"""
        self.monitor.monitoring_interval = value
    
    def update_threshold(self, key, value):
        """更新阈值"""
        self.monitor.thresholds[key] = value
    
    def add_service(self):
        """添加监控服务"""
        service_name = self.service_combo.currentText().strip()
        if service_name and service_name not in self.monitor.monitored_services:
            self.monitor.add_monitored_service(service_name)
            QMessageBox.information(self, "成功", f"已添加服务: {service_name}")
    
    def remove_service(self):
        """移除监控服务"""
        service_name = self.service_combo.currentText().strip()
        if service_name in self.monitor.monitored_services:
            self.monitor.remove_monitored_service(service_name)
            QMessageBox.information(self, "成功", f"已移除服务: {service_name}")
    
    def toggle_email_notifications(self, state):
        """切换邮件通知状态"""
        self.notification_manager.email_enabled = (state == Qt.Checked)
    
    def save_email_settings(self):
        """保存邮件设置"""
        settings = {
            'email_enabled': self.email_checkbox.isChecked(),
            'smtp_server': self.smtp_server_edit.text(),
            'smtp_port': int(self.smtp_port_edit.text()),
            'email_from': self.email_from_edit.text(),
            'email_to': self.email_to_edit.text(),
            'email_username': self.email_username_edit.text(),
            'email_password': self.email_password_edit.text()
        }
        
        self.notification_manager.save_settings(settings)
        QMessageBox.information(self, "成功", "邮件设置已保存")
    
    def test_email(self):
        """测试邮件发送"""
        if self.notification_manager.send_email_notification(
            "自愈系统测试邮件", 
            "这是一封测试邮件，用于验证自愈系统的邮件通知功能。"
        ):
            QMessageBox.information(self, "成功", "测试邮件发送成功")
        else:
            QMessageBox.warning(self, "失败", "测试邮件发送失败，请检查邮件设置")

class SelfHealingSystem(QMainWindow):
    """自愈系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.monitor = SystemMonitor()
        self.healing_engine = SelfHealingEngine()
        self.notification_manager = NotificationManager()
        self.init_ui()
        self.setup_connections()
        self.setup_tray_icon()
        
        # 启动监控
        self.monitor.start()
        
        # 记录启动日志
        self.log_widget.add_log("自愈系统已启动", "INFO")
    
    def init_ui(self):
        self.setWindowTitle("高级自愈系统工具库")
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 仪表板标签页
        self.dashboard_widget = DashboardWidget()
        self.tabs.addTab(self.dashboard_widget, "仪表板")
        
        # 异常检测标签页
        self.anomalies_widget = AnomaliesWidget(self.healing_engine)
        self.tabs.addTab(self.anomalies_widget, "异常检测")
        
        # 日志标签页
        self.log_widget = LogWidget()
        self.tabs.addTab(self.log_widget, "日志")
        
        # 设置标签页
        self.settings_widget = SettingsWidget(self.monitor, self.notification_manager)
        self.tabs.addTab(self.settings_widget, "设置")
        
        layout.addWidget(self.tabs)
        
        # 状态栏
        self.status_label = QLabel("系统就绪")
        self.statusBar().addWidget(self.status_label)
    
    def setup_connections(self):
        """设置信号连接"""
        self.monitor.system_stats_updated.connect(self.update_dashboard)
        self.monitor.anomaly_detected.connect(self.handle_anomaly)
        self.monitor.service_status_updated.connect(self.update_service_status)
    
    def setup_tray_icon(self):
        """设置系统托盘图标"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        tray_menu = QMenu(self)
        
        show_action = QAction("显示", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def tray_icon_activated(self, reason):
        """托盘图标激活处理"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()
    
    def update_dashboard(self, stats):
        """更新仪表板"""
        self.dashboard_widget.update_stats(stats)
        
        # 更新状态栏
        status_text = f"CPU: {stats['cpu_percent']:.1f}% | 内存: {stats['memory_percent']:.1f}% | 磁盘: {stats['disk_percent']:.1f}%"
        self.status_label.setText(status_text)
    
    def update_service_status(self, service_status):
        """更新服务状态"""
        self.dashboard_widget.update_service_status(service_status)
        
        # 检查是否有服务停止并发送通知
        for service, status in service_status.items():
            if not status:
                self.log_widget.add_log(f"服务 {service} 已停止", "WARNING")
                
                # 如果启用了自动自愈，尝试重启服务
                if self.settings_widget.auto_heal_checkbox.isChecked():
                    result = self.healing_engine.execute_healing_action(
                        'service_down', 
                        {'service_name': service}
                    )
                    self.log_widget.add_log(f"尝试重启服务 {service}: {result}", "INFO")
    
    def handle_anomaly(self, anomalies):
        """处理检测到的异常"""
        self.anomalies_widget.add_anomaly(anomalies)
        
        # 记录异常到日志
        for anomaly_id, anomaly_data in anomalies.items():
            self.log_widget.add_log(
                f"检测到异常: {anomaly_data['metric']} = {anomaly_data['value']:.1f} "
                f"(阈值: {anomaly_data['threshold']:.1f}, 严重程度: {anomaly_data['severity']})", 
                "WARNING"
            )
            
            # 发送通知
            self.notification_manager.send_email_notification(
                "自愈系统 - 检测到异常",
                f"检测到系统异常:\n指标: {anomaly_data['metric']}\n"
                f"当前值: {anomaly_data['value']:.1f}\n"
                f"阈值: {anomaly_data['threshold']:.1f}\n"
                f"严重程度: {anomaly_data['severity']}\n"
                f"时间: {anomaly_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        # 如果启用了自动自愈，执行自愈动作
        if self.settings_widget.auto_heal_checkbox.isChecked():
            self.execute_auto_healing(anomalies)
    
    def execute_auto_healing(self, anomalies):
        """执行自动自愈"""
        for anomaly_id, anomaly_data in anomalies.items():
            result = self.healing_engine.execute_healing_action(anomaly_id, anomaly_data)
            self.log_widget.add_log(f"自动自愈执行结果: {result}", "INFO")
            
            # 显示通知
            self.tray_icon.showMessage(
                "自愈系统",
                f"已自动处理异常: {anomaly_data['metric']}",
                QSystemTrayIcon.Information,
                3000
            )
    
    def closeEvent(self, event):
        """关闭事件处理"""
        reply = QMessageBox.question(
            self, "确认退出",
            "确定要退出自愈系统吗？系统监控将停止。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 停止监控线程
            self.monitor.stop_monitoring()
            self.monitor.wait(3000)  # 等待线程结束，最多3秒
            
            # 记录退出日志
            self.log_widget.add_log("自愈系统已关闭", "INFO")
            
            event.accept()
        else:
            event.ignore()
    
    def quit_application(self):
        """退出应用程序"""
        self.close()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("高级自愈系统工具库")
    app.setApplicationVersion("2.0")
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = SelfHealingSystem()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()