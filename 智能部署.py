import sys
import os
import json
import yaml
import paramiko
import docker
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QTextEdit, QPushButton, 
                             QLabel, QLineEdit, QComboBox, QListWidget, 
                             QListWidgetItem, QTreeWidget, QTreeWidgetItem,
                             QProgressBar, QMessageBox, QFileDialog, QSplitter,
                             QGroupBox, QCheckBox, QSpinBox, QDoubleSpinBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QToolBar, QAction, QStatusBar, QMenu, QSystemTrayIcon)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings, QSize
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QTextCursor


class DeployLogger:
    """部署日志管理器"""
    
    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.setup_logging()
    
    def setup_logging(self):
        """配置日志系统"""
        log_file = self.log_dir / f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("DeploySystem")
    
    def log(self, message, level="info"):
        """记录日志"""
        if level == "info":
            self.logger.info(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        elif level == "debug":
            self.logger.debug(message)


class SSHManager:
    """SSH连接管理器"""
    
    def __init__(self):
        self.connections = {}
        self.logger = DeployLogger().logger
    
    def connect(self, hostname, username, password=None, key_file=None, port=22):
        """建立SSH连接"""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if key_file:
                client.connect(hostname, port=port, username=username, key_filename=key_file)
            else:
                client.connect(hostname, port=port, username=username, password=password)
            
            self.connections[hostname] = client
            self.logger.info(f"成功连接到 {hostname}")
            return True
        except Exception as e:
            self.logger.error(f"连接 {hostname} 失败: {str(e)}")
            return False
    
    def execute_command(self, hostname, command, timeout=30):
        """在远程主机上执行命令"""
        if hostname not in self.connections:
            self.logger.error(f"未找到 {hostname} 的连接")
            return False, ""
        
        try:
            stdin, stdout, stderr = self.connections[hostname].exec_command(command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            output = stdout.read().decode()
            error = stderr.read().decode()
            
            self.logger.info(f"在 {hostname} 上执行命令: {command}")
            if output:
                self.logger.info(f"输出: {output}")
            if error:
                self.logger.warning(f"错误: {error}")
            
            return exit_code == 0, output + error
        except Exception as e:
            self.logger.error(f"在 {hostname} 上执行命令失败: {str(e)}")
            return False, str(e)
    
    def upload_file(self, hostname, local_path, remote_path):
        """上传文件到远程主机"""
        if hostname not in self.connections:
            self.logger.error(f"未找到 {hostname} 的连接")
            return False
        
        try:
            sftp = self.connections[hostname].open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            self.logger.info(f"成功上传 {local_path} 到 {hostname}:{remote_path}")
            return True
        except Exception as e:
            self.logger.error(f"上传文件失败: {str(e)}")
            return False
    
    def disconnect(self, hostname):
        """断开SSH连接"""
        if hostname in self.connections:
            self.connections[hostname].close()
            del self.connections[hostname]
            self.logger.info(f"已断开与 {hostname} 的连接")


class DockerManager:
    """Docker容器管理器"""
    
    def __init__(self):
        self.client = None
        self.logger = DeployLogger().logger
        self.connect()
    
    def connect(self):
        """连接到Docker守护进程"""
        try:
            self.client = docker.from_env()
            self.logger.info("成功连接到Docker守护进程")
            return True
        except Exception as e:
            self.logger.error(f"连接Docker失败: {str(e)}")
            return False
    
    def list_containers(self, all_containers=False):
        """列出所有容器"""
        try:
            containers = self.client.containers.list(all=all_containers)
            return [{"id": c.id, "name": c.name, "status": c.status, "image": c.image.tags} for c in containers]
        except Exception as e:
            self.logger.error(f"获取容器列表失败: {str(e)}")
            return []
    
    def start_container(self, container_id):
        """启动容器"""
        try:
            container = self.client.containers.get(container_id)
            container.start()
            self.logger.info(f"已启动容器: {container.name}")
            return True
        except Exception as e:
            self.logger.error(f"启动容器失败: {str(e)}")
            return False
    
    def stop_container(self, container_id):
        """停止容器"""
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            self.logger.info(f"已停止容器: {container.name}")
            return True
        except Exception as e:
            self.logger.error(f"停止容器失败: {str(e)}")
            return False
    
    def pull_image(self, image_name):
        """拉取Docker镜像"""
        try:
            self.logger.info(f"开始拉取镜像: {image_name}")
            image = self.client.images.pull(image_name)
            self.logger.info(f"成功拉取镜像: {image_name}")
            return True
        except Exception as e:
            self.logger.error(f"拉取镜像失败: {str(e)}")
            return False


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file="deploy_config.json"):
        self.config_file = Path(config_file)
        # 先初始化 logger
        self.logger = DeployLogger().logger
        # 然后加载配置
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 创建默认配置
            default_config = {
                "servers": [],
                "deploy_templates": {},
                "settings": {
                    "log_retention_days": 30,
                    "auto_save_interval": 300,
                    "default_timeout": 30
                }
            }
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config=None):
        """保存配置文件"""
        if config is None:
            config = self.config
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        self.logger.info("配置文件已保存")
    
    def get_server_config(self, server_name):
        """获取服务器配置"""
        for server in self.config.get("servers", []):
            if server["name"] == server_name:
                return server
        return None
    
    def add_server(self, server_config):
        """添加服务器配置"""
        self.config["servers"].append(server_config)
        self.save_config()
    
    def update_server(self, server_name, new_config):
        """更新服务器配置"""
        for i, server in enumerate(self.config.get("servers", [])):
            if server["name"] == server_name:
                self.config["servers"][i] = new_config
                self.save_config()
                return True
        return False


class DeploymentWorker(QThread):
    """部署工作线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(int, str)
    deployment_finished = pyqtSignal(bool, str)
    log_message = pyqtSignal(str, str)  # message, level
    
    def __init__(self, deployment_config):
        super().__init__()
        self.deployment_config = deployment_config
        self.is_running = True
        self.ssh_manager = SSHManager()
        self.docker_manager = DockerManager()
        self.logger = DeployLogger().logger
    
    def run(self):
        """执行部署任务"""
        try:
            self.log_message.emit("开始部署任务", "info")
            
            # 步骤1: 连接到目标服务器
            self.progress_updated.emit(10, "连接到目标服务器")
            server_config = self.deployment_config["server"]
            if not self.ssh_manager.connect(
                server_config["hostname"],
                server_config["username"],
                server_config.get("password"),
                server_config.get("key_file")
            ):
                self.deployment_finished.emit(False, "连接服务器失败")
                return
            
            # 步骤2: 上传部署文件
            self.progress_updated.emit(30, "上传部署文件")
            for file_mapping in self.deployment_config.get("file_transfers", []):
                local_path = file_mapping["local"]
                remote_path = file_mapping["remote"]
                if not self.ssh_manager.upload_file(server_config["hostname"], local_path, remote_path):
                    self.deployment_finished.emit(False, f"上传文件失败: {local_path}")
                    return
            
            # 步骤3: 执行部署命令
            self.progress_updated.emit(60, "执行部署命令")
            for command in self.deployment_config.get("commands", []):
                success, output = self.ssh_manager.execute_command(server_config["hostname"], command)
                if not success:
                    self.deployment_finished.emit(False, f"执行命令失败: {command}")
                    return
            
            # 步骤4: 启动/重启服务
            self.progress_updated.emit(80, "启动服务")
            if self.deployment_config.get("docker_deploy", False):
                # Docker部署
                container_id = self.deployment_config.get("container_id")
                if container_id:
                    self.docker_manager.stop_container(container_id)
                    self.docker_manager.start_container(container_id)
            
            # 步骤5: 验证部署
            self.progress_updated.emit(90, "验证部署")
            if self.deployment_config.get("validation_command"):
                success, output = self.ssh_manager.execute_command(
                    server_config["hostname"], 
                    self.deployment_config["validation_command"]
                )
                if not success:
                    self.deployment_finished.emit(False, "部署验证失败")
                    return
            
            self.progress_updated.emit(100, "部署完成")
            self.deployment_finished.emit(True, "部署成功完成")
            
        except Exception as e:
            self.log_message.emit(f"部署过程中发生错误: {str(e)}", "error")
            self.deployment_finished.emit(False, f"部署失败: {str(e)}")
        finally:
            # 清理连接
            if "server" in self.deployment_config:
                self.ssh_manager.disconnect(self.deployment_config["server"]["hostname"])
    
    def stop(self):
        """停止部署任务"""
        self.is_running = False


class DeploymentHistory:
    """部署历史管理器"""
    
    def __init__(self, history_file="deployment_history.json"):
        self.history_file = Path(history_file)
        self.history = self.load_history()
    
    def load_history(self):
        """加载部署历史"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {"deployments": []}
    
    def save_history(self):
        """保存部署历史"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=4, ensure_ascii=False)
    
    def add_deployment(self, deployment_info):
        """添加部署记录"""
        deployment_info["timestamp"] = datetime.now().isoformat()
        self.history["deployments"].append(deployment_info)
        self.save_history()
    
    def get_recent_deployments(self, limit=10):
        """获取最近的部署记录"""
        deployments = self.history.get("deployments", [])
        return deployments[-limit:] if deployments else []


class LogViewer(QWidget):
    """日志查看器组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新")
        self.clear_btn = QPushButton("清空")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["所有", "信息", "警告", "错误", "调试"])
        
        toolbar.addWidget(QLabel("筛选:"))
        toolbar.addWidget(self.filter_combo)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.clear_btn)
        toolbar.addStretch()
        
        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        font = QFont("Courier New", 10)
        self.log_text.setFont(font)
        
        layout.addLayout(toolbar)
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)
        
        # 连接信号
        self.refresh_btn.clicked.connect(self.refresh_logs)
        self.clear_btn.clicked.connect(self.clear_logs)
        self.filter_combo.currentTextChanged.connect(self.filter_logs)
    
    def append_log(self, message, level="info"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 根据日志级别设置颜色
        if level == "error":
            color = "red"
        elif level == "warning":
            color = "orange"
        elif level == "debug":
            color = "gray"
        else:
            color = "black"
        
        log_entry = f'<span style="color: {color}">[{timestamp}] {message}</span><br>'
        
        # 移动到文本末尾并插入
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(log_entry)
        
        # 自动滚动到底部
        self.log_text.ensureCursorVisible()
    
    def refresh_logs(self):
        """刷新日志显示"""
        # 这里可以添加从文件加载日志的功能
        pass
    
    def clear_logs(self):
        """清空日志显示"""
        self.log_text.clear()
    
    def filter_logs(self, level_filter):
        """根据级别筛选日志"""
        # 这里可以实现日志筛选功能
        pass


class ServerManager(QWidget):
    """服务器管理器组件"""
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.init_ui()
        self.load_servers()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("添加服务器")
        self.edit_btn = QPushButton("编辑服务器")
        self.delete_btn = QPushButton("删除服务器")
        self.test_btn = QPushButton("测试连接")
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addWidget(self.test_btn)
        toolbar.addStretch()
        
        # 服务器列表
        self.server_table = QTableWidget()
        self.server_table.setColumnCount(5)
        self.server_table.setHorizontalHeaderLabels(["名称", "主机名", "用户名", "端口", "状态"])
        self.server_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addLayout(toolbar)
        layout.addWidget(self.server_table)
        
        self.setLayout(layout)
        
        # 连接信号
        self.add_btn.clicked.connect(self.add_server)
        self.edit_btn.clicked.connect(self.edit_server)
        self.delete_btn.clicked.connect(self.delete_server)
        self.test_btn.clicked.connect(self.test_connection)
    
    def load_servers(self):
        """加载服务器列表"""
        servers = self.config_manager.config.get("servers", [])
        self.server_table.setRowCount(len(servers))
        
        for i, server in enumerate(servers):
            self.server_table.setItem(i, 0, QTableWidgetItem(server.get("name", "")))
            self.server_table.setItem(i, 1, QTableWidgetItem(server.get("hostname", "")))
            self.server_table.setItem(i, 2, QTableWidgetItem(server.get("username", "")))
            self.server_table.setItem(i, 3, QTableWidgetItem(str(server.get("port", 22))))
            
            # 测试连接状态
            status_item = QTableWidgetItem("未知")
            self.server_table.setItem(i, 4, status_item)
    
    def add_server(self):
        """添加服务器"""
        dialog = ServerDialog(self)
        if dialog.exec_() == ServerDialog.Accepted:
            server_config = dialog.get_server_config()
            self.config_manager.add_server(server_config)
            self.load_servers()
    
    def edit_server(self):
        """编辑服务器"""
        current_row = self.server_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择一个服务器")
            return
        
        server_name = self.server_table.item(current_row, 0).text()
        server_config = self.config_manager.get_server_config(server_name)
        
        if server_config:
            dialog = ServerDialog(self, server_config)
            if dialog.exec_() == ServerDialog.Accepted:
                new_config = dialog.get_server_config()
                self.config_manager.update_server(server_name, new_config)
                self.load_servers()
    
    def delete_server(self):
        """删除服务器"""
        current_row = self.server_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择一个服务器")
            return
        
        server_name = self.server_table.item(current_row, 0).text()
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除服务器 '{server_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            servers = self.config_manager.config.get("servers", [])
            self.config_manager.config["servers"] = [s for s in servers if s["name"] != server_name]
            self.config_manager.save_config()
            self.load_servers()
    
    def test_connection(self):
        """测试服务器连接"""
        current_row = self.server_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择一个服务器")
            return
        
        server_name = self.server_table.item(current_row, 0).text()
        server_config = self.config_manager.get_server_config(server_name)
        
        if server_config:
            ssh_manager = SSHManager()
            success = ssh_manager.connect(
                server_config["hostname"],
                server_config["username"],
                server_config.get("password"),
                server_config.get("key_file"),
                server_config.get("port", 22)
            )
            
            status_item = self.server_table.item(current_row, 4)
            if success:
                status_item.setText("连接成功")
                status_item.setForeground(QColor("green"))
                ssh_manager.disconnect(server_config["hostname"])
            else:
                status_item.setText("连接失败")
                status_item.setForeground(QColor("red"))


class ServerDialog(QWidget):
    """服务器配置对话框"""
    
    def __init__(self, parent=None, server_config=None):
        super().__init__(parent)
        self.server_config = server_config or {}
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 服务器基本信息
        info_group = QGroupBox("服务器信息")
        info_layout = QVBoxLayout()
        
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("名称:"))
        self.name_edit = QLineEdit(self.server_config.get("name", ""))
        form_layout.addWidget(self.name_edit)
        info_layout.addLayout(form_layout)
        
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("主机名:"))
        self.hostname_edit = QLineEdit(self.server_config.get("hostname", ""))
        form_layout.addWidget(self.hostname_edit)
        info_layout.addLayout(form_layout)
        
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("端口:"))
        self.port_edit = QLineEdit(str(self.server_config.get("port", 22)))
        form_layout.addWidget(self.port_edit)
        info_layout.addLayout(form_layout)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 认证信息
        auth_group = QGroupBox("认证信息")
        auth_layout = QVBoxLayout()
        
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("用户名:"))
        self.username_edit = QLineEdit(self.server_config.get("username", ""))
        form_layout.addWidget(self.username_edit)
        auth_layout.addLayout(form_layout)
        
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("密码:"))
        self.password_edit = QLineEdit(self.server_config.get("password", ""))
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.password_edit)
        auth_layout.addLayout(form_layout)
        
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("密钥文件:"))
        self.key_file_edit = QLineEdit(self.server_config.get("key_file", ""))
        self.browse_key_btn = QPushButton("浏览")
        form_layout.addWidget(self.key_file_edit)
        form_layout.addWidget(self.browse_key_btn)
        auth_layout.addLayout(form_layout)
        
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 连接信号
        self.browse_key_btn.clicked.connect(self.browse_key_file)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    
    def browse_key_file(self):
        """浏览密钥文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择SSH密钥文件", "", "All Files (*)"
        )
        if file_path:
            self.key_file_edit.setText(file_path)
    
    def get_server_config(self):
        """获取服务器配置"""
        return {
            "name": self.name_edit.text(),
            "hostname": self.hostname_edit.text(),
            "port": int(self.port_edit.text()) if self.port_edit.text() else 22,
            "username": self.username_edit.text(),
            "password": self.password_edit.text(),
            "key_file": self.key_file_edit.text() if self.key_file_edit.text() else None
        }
    
    def accept(self):
        """接受配置"""
        if not all([self.name_edit.text(), self.hostname_edit.text(), self.username_edit.text()]):
            QMessageBox.warning(self, "警告", "请填写所有必填字段")
            return
        
        self.close()
    
    def reject(self):
        """取消配置"""
        self.close()
    
    def exec_(self):
        """执行对话框"""
        self.show()
        return self.Accepted if self.ok_btn.clicked else self.Rejected


class DeploymentWizard(QWidget):
    """部署向导组件"""
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.deployment_worker = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 部署配置区域
        config_group = QGroupBox("部署配置")
        config_layout = QVBoxLayout()
        
        # 服务器选择
        server_layout = QHBoxLayout()
        server_layout.addWidget(QLabel("目标服务器:"))
        self.server_combo = QComboBox()
        self.load_servers()
        server_layout.addWidget(self.server_combo)
        config_layout.addLayout(server_layout)
        
        # 部署模板选择
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("部署模板:"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(["自定义部署", "Web应用部署", "Docker部署"])
        template_layout.addWidget(self.template_combo)
        config_layout.addLayout(template_layout)
        
        # 文件传输配置
        file_group = QGroupBox("文件传输")
        file_layout = QVBoxLayout()
        
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(2)
        self.file_table.setHorizontalHeaderLabels(["本地路径", "远程路径"])
        file_layout.addWidget(self.file_table)
        
        file_btn_layout = QHBoxLayout()
        self.add_file_btn = QPushButton("添加文件")
        self.remove_file_btn = QPushButton("删除文件")
        file_btn_layout.addWidget(self.add_file_btn)
        file_btn_layout.addWidget(self.remove_file_btn)
        file_btn_layout.addStretch()
        file_layout.addLayout(file_btn_layout)
        
        file_group.setLayout(file_layout)
        config_layout.addWidget(file_group)
        
        # 命令配置
        command_group = QGroupBox("部署命令")
        command_layout = QVBoxLayout()
        
        self.command_edit = QTextEdit()
        self.command_edit.setPlaceholderText("每行一个命令")
        command_layout.addWidget(self.command_edit)
        
        command_group.setLayout(command_layout)
        config_layout.addWidget(command_group)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("准备部署")
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.deploy_btn = QPushButton("开始部署")
        self.stop_btn = QPushButton("停止部署")
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.deploy_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 连接信号
        self.deploy_btn.clicked.connect(self.start_deployment)
        self.stop_btn.clicked.connect(self.stop_deployment)
        self.add_file_btn.clicked.connect(self.add_file_mapping)
        self.remove_file_btn.clicked.connect(self.remove_file_mapping)
    
    def load_servers(self):
        """加载服务器列表"""
        servers = self.config_manager.config.get("servers", [])
        self.server_combo.clear()
        for server in servers:
            self.server_combo.addItem(server["name"], server)
    
    def add_file_mapping(self):
        """添加文件映射"""
        row_count = self.file_table.rowCount()
        self.file_table.insertRow(row_count)
    
    def remove_file_mapping(self):
        """删除文件映射"""
        current_row = self.file_table.currentRow()
        if current_row >= 0:
            self.file_table.removeRow(current_row)
    
    def get_deployment_config(self):
        """获取部署配置"""
        server_name = self.server_combo.currentText()
        server_config = self.config_manager.get_server_config(server_name)
        
        # 获取文件传输配置
        file_transfers = []
        for row in range(self.file_table.rowCount()):
            local_item = self.file_table.item(row, 0)
            remote_item = self.file_table.item(row, 1)
            if local_item and remote_item:
                file_transfers.append({
                    "local": local_item.text(),
                    "remote": remote_item.text()
                })
        
        # 获取命令配置
        commands = [cmd.strip() for cmd in self.command_edit.toPlainText().split('\n') if cmd.strip()]
        
        return {
            "server": server_config,
            "file_transfers": file_transfers,
            "commands": commands,
            "template": self.template_combo.currentText()
        }
    
    def start_deployment(self):
        """开始部署"""
        deployment_config = self.get_deployment_config()
        
        if not deployment_config["server"]:
            QMessageBox.warning(self, "警告", "请选择目标服务器")
            return
        
        self.deploy_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 创建部署工作线程
        self.deployment_worker = DeploymentWorker(deployment_config)
        self.deployment_worker.progress_updated.connect(self.update_progress)
        self.deployment_worker.deployment_finished.connect(self.deployment_finished)
        self.deployment_worker.log_message.connect(self.log_message)
        self.deployment_worker.start()
    
    def stop_deployment(self):
        """停止部署"""
        if self.deployment_worker:
            self.deployment_worker.stop()
            self.deployment_worker.wait()
        
        self.deploy_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("部署已停止")
    
    def update_progress(self, value, message):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
    
    def deployment_finished(self, success, message):
        """部署完成"""
        self.deploy_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)
    
    def log_message(self, message, level):
        """记录日志消息"""
        # 这里可以将日志发送到主界面的日志查看器
        print(f"[{level}] {message}")


class SmartDeploySystem(QMainWindow):
    """智能部署系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.deployment_history = DeploymentHistory()
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        self.setWindowTitle("智能部署系统 - 高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 服务器管理标签页
        self.server_manager = ServerManager(self.config_manager)
        self.tab_widget.addTab(self.server_manager, "服务器管理")
        
        # 部署向导标签页
        self.deployment_wizard = DeploymentWizard(self.config_manager)
        self.tab_widget.addTab(self.deployment_wizard, "部署向导")
        
        # 部署历史标签页
        self.history_widget = self.create_history_tab()
        self.tab_widget.addTab(self.history_widget, "部署历史")
        
        # 日志查看器标签页
        self.log_viewer = LogViewer()
        self.tab_widget.addTab(self.log_viewer, "系统日志")
        
        main_layout.addWidget(self.tab_widget)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_tool_bar()
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建部署", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)
        
        open_action = QAction("打开配置", self)
        open_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_action)
        
        save_action = QAction("保存配置", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        settings_action = QAction("设置", self)
        tools_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_tool_bar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        deploy_action = QAction("开始部署", self)
        deploy_action.triggered.connect(self.start_deployment)
        toolbar.addAction(deploy_action)
        
        toolbar.addSeparator()
        
        refresh_action = QAction("刷新", self)
        toolbar.addAction(refresh_action)
    
    def create_history_tab(self):
        """创建部署历史标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "时间", "服务器", "模板", "状态", "详情"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.history_table)
        widget.setLayout(layout)
        
        # 加载历史记录
        self.load_deployment_history()
        
        return widget
    
    def load_deployment_history(self):
        """加载部署历史"""
        deployments = self.deployment_history.get_recent_deployments(20)
        self.history_table.setRowCount(len(deployments))
        
        for i, deployment in enumerate(deployments):
            self.history_table.setItem(i, 0, QTableWidgetItem(
                deployment.get("timestamp", "").replace("T", " ").split(".")[0]
            ))
            self.history_table.setItem(i, 1, QTableWidgetItem(
                deployment.get("server", {}).get("name", "")
            ))
            self.history_table.setItem(i, 2, QTableWidgetItem(
                deployment.get("template", "")
            ))
            
            status_item = QTableWidgetItem(
                "成功" if deployment.get("success") else "失败"
            )
            status_item.setForeground(
                QColor("green") if deployment.get("success") else QColor("red")
            )
            self.history_table.setItem(i, 3, status_item)
            
            self.history_table.setItem(i, 4, QTableWidgetItem(
                deployment.get("message", "")
            ))
    
    def start_deployment(self):
        """开始部署"""
        # 切换到部署向导标签页
        self.tab_widget.setCurrentIndex(1)
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, 
            "关于智能部署系统",
            "智能部署系统 - 高级工具库\n\n"
            "版本: 1.0.0\n"
            "作者: AI Assistant\n"
            "描述: 基于PyQt的智能部署系统，提供强大的部署工具库"
        )
    
    def load_settings(self):
        """加载应用程序设置"""
        settings = QSettings("SmartDeploy", "DeploySystem")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def closeEvent(self, event):
        """关闭应用程序事件"""
        # 保存设置
        settings = QSettings("SmartDeploy", "DeploySystem")
        settings.setValue("geometry", self.saveGeometry())
        
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("智能部署系统")
    app.setApplicationVersion("1.0.0")
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = SmartDeploySystem()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()