import sys
import os
import json
import requests
import sqlite3
from datetime import datetime
from urllib.parse import urlparse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QLineEdit, 
                             QLabel, QTableWidget, QTableWidgetItem, QTabWidget,
                             QGroupBox, QProgressBar, QMessageBox, QFileDialog,
                             QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView,
                             QComboBox, QSpinBox, QCheckBox, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor
import threading
import time
from bs4 import BeautifulSoup
import hashlib
import zipfile
import shutil


# 数据库管理类
class DatabaseManager:
    def __init__(self, db_path="website_manager.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建网站表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS websites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                status TEXT,
                last_checked TEXT,
                created_at TEXT
            )
        ''')
        
        # 创建备份表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_id INTEGER,
                backup_path TEXT,
                backup_date TEXT,
                file_count INTEGER,
                FOREIGN KEY (website_id) REFERENCES websites (id)
            )
        ''')
        
        # 创建监控日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_id INTEGER,
                check_time TEXT,
                response_time REAL,
                status_code INTEGER,
                content_hash TEXT,
                FOREIGN KEY (website_id) REFERENCES websites (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_website(self, name, url):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO websites (name, url, created_at) VALUES (?, ?, ?)",
            (name, url, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    def get_websites(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM websites")
        websites = cursor.fetchall()
        conn.close()
        return websites
    
    def delete_website(self, website_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM websites WHERE id = ?", (website_id,))
        conn.commit()
        conn.close()


# 网站监控线程
class WebsiteMonitorThread(QThread):
    update_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal()
    
    def __init__(self, websites, check_content=False):
        super().__init__()
        self.websites = websites
        self.check_content = check_content
        self.is_running = True
    
    def run(self):
        for website in self.websites:
            if not self.is_running:
                break
                
            result = self.check_website(website)
            self.update_signal.emit(result)
        
        self.finished_signal.emit()
    
    def check_website(self, website):
        try:
            start_time = time.time()
            response = requests.get(website[2], timeout=10)  # website[2] is URL
            response_time = time.time() - start_time
            
            content_hash = ""
            if self.check_content:
                content_hash = hashlib.md5(response.content).hexdigest()
            
            return {
                'id': website[0],
                'name': website[1],
                'url': website[2],
                'status_code': response.status_code,
                'response_time': round(response_time, 2),
                'content_hash': content_hash,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'id': website[0],
                'name': website[1],
                'url': website[2],
                'status_code': 0,
                'response_time': 0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def stop(self):
        self.is_running = False


# 备份管理类
class BackupManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def create_backup(self, website_id, source_path, backup_dir):
        try:
            website_name = self.get_website_name(website_id)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{website_name}_{timestamp}.zip"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # 创建备份
            file_count = self.zip_directory(source_path, backup_path)
            
            # 记录到数据库
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO backups (website_id, backup_path, backup_date, file_count) VALUES (?, ?, ?, ?)",
                (website_id, backup_path, datetime.now().isoformat(), file_count)
            )
            conn.commit()
            conn.close()
            
            return True, f"备份成功: {backup_filename}", backup_path
        except Exception as e:
            return False, f"备份失败: {str(e)}", ""
    
    def zip_directory(self, source_path, backup_path):
        file_count = 0
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_path)
                    zipf.write(file_path, arcname)
                    file_count += 1
        return file_count
    
    def get_website_name(self, website_id):
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM websites WHERE id = ?", (website_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "Unknown"


# SEO分析工具类
class SEOAnalyzer:
    def __init__(self):
        pass
    
    def analyze_url(self, url):
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取SEO相关信息
            title = soup.find('title')
            title_text = title.text if title else "无标题"
            
            meta_description = soup.find('meta', attrs={'name': 'description'})
            description = meta_description['content'] if meta_description else "无描述"
            
            h1_tags = soup.find_all('h1')
            h1_count = len(h1_tags)
            h1_texts = [h1.text for h1 in h1_tags]
            
            # 计算页面大小
            page_size = len(response.content)
            
            # 检查图片ALT属性
            images = soup.find_all('img')
            images_without_alt = [img for img in images if not img.get('alt')]
            
            return {
                'title': title_text,
                'description': description,
                'h1_count': h1_count,
                'h1_texts': h1_texts,
                'page_size': page_size,
                'images_count': len(images),
                'images_without_alt': len(images_without_alt),
                'status_code': response.status_code
            }
        except Exception as e:
            return {'error': str(e)}


# 主界面类
class WebsiteManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.backup_manager = BackupManager(self.db_manager)
        self.seo_analyzer = SEOAnalyzer()
        self.monitor_thread = None
        self.settings = QSettings("WebsiteManager", "WebsiteManager")
        
        self.init_ui()
        self.load_settings()
        self.refresh_website_list()
    
    def init_ui(self):
        self.setWindowTitle("网站管理系统高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 创建各个功能标签页
        self.setup_dashboard_tab()
        self.setup_monitoring_tab()
        self.setup_backup_tab()
        self.setup_seo_tab()
        self.setup_settings_tab()
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def setup_dashboard_tab(self):
        dashboard_tab = QWidget()
        layout = QVBoxLayout(dashboard_tab)
        
        # 网站列表
        website_group = QGroupBox("网站列表")
        website_layout = QVBoxLayout(website_group)
        
        # 添加网站表单
        form_layout = QHBoxLayout()
        self.website_name_input = QLineEdit()
        self.website_name_input.setPlaceholderText("网站名称")
        self.website_url_input = QLineEdit()
        self.website_url_input.setPlaceholderText("网站URL")
        add_button = QPushButton("添加网站")
        add_button.clicked.connect(self.add_website)
        
        form_layout.addWidget(QLabel("名称:"))
        form_layout.addWidget(self.website_name_input)
        form_layout.addWidget(QLabel("URL:"))
        form_layout.addWidget(self.website_url_input)
        form_layout.addWidget(add_button)
        website_layout.addLayout(form_layout)
        
        # 网站表格
        self.website_table = QTableWidget()
        self.website_table.setColumnCount(5)
        self.website_table.setHorizontalHeaderLabels(["ID", "名称", "URL", "状态", "操作"])
        self.website_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        website_layout.addWidget(self.website_table)
        
        layout.addWidget(website_group)
        self.tabs.addTab(dashboard_tab, "仪表板")
    
    def setup_monitoring_tab(self):
        monitoring_tab = QWidget()
        layout = QVBoxLayout(monitoring_tab)
        
        # 监控控制
        control_group = QGroupBox("监控控制")
        control_layout = QHBoxLayout(control_group)
        
        self.start_monitor_btn = QPushButton("开始监控")
        self.start_monitor_btn.clicked.connect(self.start_monitoring)
        self.stop_monitor_btn = QPushButton("停止监控")
        self.stop_monitor_btn.clicked.connect(self.stop_monitoring)
        self.stop_monitor_btn.setEnabled(False)
        
        self.monitor_interval = QSpinBox()
        self.monitor_interval.setRange(1, 60)
        self.monitor_interval.setValue(5)
        self.monitor_interval.setSuffix(" 分钟")
        
        self.check_content_cb = QCheckBox("检查内容变化")
        
        control_layout.addWidget(QLabel("监控间隔:"))
        control_layout.addWidget(self.monitor_interval)
        control_layout.addWidget(self.check_content_cb)
        control_layout.addWidget(self.start_monitor_btn)
        control_layout.addWidget(self.stop_monitor_btn)
        control_layout.addStretch()
        
        layout.addWidget(control_group)
        
        # 监控结果
        result_group = QGroupBox("监控结果")
        result_layout = QVBoxLayout(result_group)
        
        self.monitor_table = QTableWidget()
        self.monitor_table.setColumnCount(6)
        self.monitor_table.setHorizontalHeaderLabels(["网站", "URL", "状态码", "响应时间", "内容哈希", "时间"])
        self.monitor_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        result_layout.addWidget(self.monitor_table)
        
        layout.addWidget(result_group)
        self.tabs.addTab(monitoring_tab, "网站监控")
    
    def setup_backup_tab(self):
        backup_tab = QWidget()
        layout = QVBoxLayout(backup_tab)
        
        # 备份控制
        backup_control_group = QGroupBox("备份控制")
        backup_control_layout = QHBoxLayout(backup_control_group)
        
        self.website_combo = QComboBox()
        self.source_path_input = QLineEdit()
        self.source_path_input.setPlaceholderText("源路径")
        self.browse_source_btn = QPushButton("浏览")
        self.browse_source_btn.clicked.connect(self.browse_source_path)
        
        self.backup_dir_input = QLineEdit()
        self.backup_dir_input.setPlaceholderText("备份目录")
        self.browse_backup_btn = QPushButton("浏览")
        self.browse_backup_btn.clicked.connect(self.browse_backup_dir)
        
        self.create_backup_btn = QPushButton("创建备份")
        self.create_backup_btn.clicked.connect(self.create_backup)
        
        backup_control_layout.addWidget(QLabel("网站:"))
        backup_control_layout.addWidget(self.website_combo)
        backup_control_layout.addWidget(QLabel("源路径:"))
        backup_control_layout.addWidget(self.source_path_input)
        backup_control_layout.addWidget(self.browse_source_btn)
        backup_control_layout.addWidget(QLabel("备份目录:"))
        backup_control_layout.addWidget(self.backup_dir_input)
        backup_control_layout.addWidget(self.browse_backup_btn)
        backup_control_layout.addWidget(self.create_backup_btn)
        
        layout.addWidget(backup_control_group)
        
        # 备份列表
        backup_list_group = QGroupBox("备份列表")
        backup_list_layout = QVBoxLayout(backup_list_group)
        
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(5)
        self.backup_table.setHorizontalHeaderLabels(["ID", "网站", "备份路径", "备份时间", "文件数量"])
        self.backup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        backup_list_layout.addWidget(self.backup_table)
        
        layout.addWidget(backup_list_group)
        self.tabs.addTab(backup_tab, "备份管理")
    
    def setup_seo_tab(self):
        seo_tab = QWidget()
        layout = QVBoxLayout(seo_tab)
        
        # SEO分析控制
        seo_control_group = QGroupBox("SEO分析")
        seo_control_layout = QHBoxLayout(seo_control_group)
        
        self.seo_url_input = QLineEdit()
        self.seo_url_input.setPlaceholderText("输入要分析的URL")
        self.analyze_seo_btn = QPushButton("分析")
        self.analyze_seo_btn.clicked.connect(self.analyze_seo)
        
        seo_control_layout.addWidget(QLabel("URL:"))
        seo_control_layout.addWidget(self.seo_url_input)
        seo_control_layout.addWidget(self.analyze_seo_btn)
        seo_control_layout.addStretch()
        
        layout.addWidget(seo_control_group)
        
        # SEO分析结果
        seo_result_group = QGroupBox("分析结果")
        seo_result_layout = QVBoxLayout(seo_result_group)
        
        self.seo_result_text = QTextEdit()
        self.seo_result_text.setReadOnly(True)
        seo_result_layout.addWidget(self.seo_result_text)
        
        layout.addWidget(seo_result_group)
        self.tabs.addTab(seo_tab, "SEO分析")
    
    def setup_settings_tab(self):
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        
        # 主题设置
        theme_group = QGroupBox("主题设置")
        theme_layout = QHBoxLayout(theme_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色", "深色"])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        
        theme_layout.addWidget(QLabel("主题:"))
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        layout.addWidget(theme_group)
        
        # 数据库操作
        db_group = QGroupBox("数据库操作")
        db_layout = QHBoxLayout(db_group)
        
        self.export_db_btn = QPushButton("导出数据库")
        self.export_db_btn.clicked.connect(self.export_database)
        
        self.import_db_btn = QPushButton("导入数据库")
        self.import_db_btn.clicked.connect(self.import_database)
        
        db_layout.addWidget(self.export_db_btn)
        db_layout.addWidget(self.import_db_btn)
        db_layout.addStretch()
        
        layout.addWidget(db_group)
        
        layout.addStretch()
        self.tabs.addTab(settings_tab, "设置")
    
    def add_website(self):
        name = self.website_name_input.text().strip()
        url = self.website_url_input.text().strip()
        
        if not name or not url:
            QMessageBox.warning(self, "警告", "请填写网站名称和URL")
            return
        
        # 验证URL格式
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("无效的URL")
        except:
            QMessageBox.warning(self, "警告", "请输入有效的URL")
            return
        
        self.db_manager.add_website(name, url)
        self.website_name_input.clear()
        self.website_url_input.clear()
        self.refresh_website_list()
        QMessageBox.information(self, "成功", "网站添加成功")
    
    def refresh_website_list(self):
        websites = self.db_manager.get_websites()
        self.website_table.setRowCount(len(websites))
        
        for row, website in enumerate(websites):
            self.website_table.setItem(row, 0, QTableWidgetItem(str(website[0])))
            self.website_table.setItem(row, 1, QTableWidgetItem(website[1]))
            self.website_table.setItem(row, 2, QTableWidgetItem(website[2]))
            self.website_table.setItem(row, 3, QTableWidgetItem(website[3] or "未检查"))
            
            # 添加删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda checked, id=website[0]: self.delete_website(id))
            self.website_table.setCellWidget(row, 4, delete_btn)
        
        # 刷新备份标签页中的网站下拉框
        self.website_combo.clear()
        for website in websites:
            self.website_combo.addItem(website[1], website[0])
    
    def delete_website(self, website_id):
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个网站吗？", 
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db_manager.delete_website(website_id)
            self.refresh_website_list()
            QMessageBox.information(self, "成功", "网站删除成功")
    
    def start_monitoring(self):
        websites = self.db_manager.get_websites()
        if not websites:
            QMessageBox.warning(self, "警告", "没有可监控的网站")
            return
        
        self.monitor_thread = WebsiteMonitorThread(
            websites, 
            self.check_content_cb.isChecked()
        )
        self.monitor_thread.update_signal.connect(self.update_monitor_result)
        self.monitor_thread.finished_signal.connect(self.monitor_finished)
        
        self.start_monitor_btn.setEnabled(False)
        self.stop_monitor_btn.setEnabled(True)
        
        self.monitor_thread.start()
        
        # 设置定时器定期执行监控
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.start_monitoring)
        interval_minutes = self.monitor_interval.value()
        self.monitor_timer.start(interval_minutes * 60 * 1000)  # 转换为毫秒
        
        self.statusBar().showMessage(f"监控已启动，间隔: {interval_minutes}分钟")
    
    def stop_monitoring(self):
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        
        if hasattr(self, 'monitor_timer'):
            self.monitor_timer.stop()
        
        self.start_monitor_btn.setEnabled(True)
        self.stop_monitor_btn.setEnabled(False)
        self.statusBar().showMessage("监控已停止")
    
    def update_monitor_result(self, result):
        # 在监控表格中显示结果
        row = self.monitor_table.rowCount()
        self.monitor_table.insertRow(row)
        
        self.monitor_table.setItem(row, 0, QTableWidgetItem(result['name']))
        self.monitor_table.setItem(row, 1, QTableWidgetItem(result['url']))
        
        status_item = QTableWidgetItem(str(result.get('status_code', 'N/A')))
        if result.get('status_code', 0) == 200:
            status_item.setBackground(Qt.green)
        else:
            status_item.setBackground(Qt.red)
        self.monitor_table.setItem(row, 2, status_item)
        
        self.monitor_table.setItem(row, 3, QTableWidgetItem(str(result.get('response_time', 'N/A'))))
        self.monitor_table.setItem(row, 4, QTableWidgetItem(result.get('content_hash', 'N/A')[:8] + '...'))
        self.monitor_table.setItem(row, 5, QTableWidgetItem(result.get('timestamp', 'N/A')))
        
        # 自动滚动到最后一行
        self.monitor_table.scrollToBottom()
    
    def monitor_finished(self):
        self.statusBar().showMessage("监控周期完成")
    
    def browse_source_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择源目录")
        if path:
            self.source_path_input.setText(path)
    
    def browse_backup_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择备份目录")
        if path:
            self.backup_dir_input.setText(path)
    
    def create_backup(self):
        if self.website_combo.currentIndex() == -1:
            QMessageBox.warning(self, "警告", "请先选择一个网站")
            return
        
        website_id = self.website_combo.currentData()
        source_path = self.source_path_input.text().strip()
        backup_dir = self.backup_dir_input.text().strip()
        
        if not source_path or not backup_dir:
            QMessageBox.warning(self, "警告", "请填写源路径和备份目录")
            return
        
        if not os.path.exists(source_path):
            QMessageBox.warning(self, "警告", "源路径不存在")
            return
        
        if not os.path.exists(backup_dir):
            try:
                os.makedirs(backup_dir)
            except:
                QMessageBox.warning(self, "警告", "无法创建备份目录")
                return
        
        success, message, backup_path = self.backup_manager.create_backup(
            website_id, source_path, backup_dir
        )
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.refresh_backup_list()
        else:
            QMessageBox.warning(self, "失败", message)
    
    def refresh_backup_list(self):
        # 实现备份列表刷新
        pass
    
    def analyze_seo(self):
        url = self.seo_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入要分析的URL")
            return
        
        # 添加http://前缀如果缺失
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        self.statusBar().showMessage("正在分析SEO...")
        
        # 在单独的线程中执行SEO分析
        threading.Thread(target=self._analyze_seo_thread, args=(url,), daemon=True).start()
    
    def _analyze_seo_thread(self, url):
        result = self.seo_analyzer.analyze_url(url)
        
        # 使用信号或直接在主线程中更新UI
        self._update_seo_result(result)
    
    def _update_seo_result(self, result):
        if 'error' in result:
            self.seo_result_text.setText(f"分析失败: {result['error']}")
            self.statusBar().showMessage("SEO分析失败")
        else:
            result_text = f"""
SEO分析结果 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
============================================

页面标题: {result.get('title', 'N/A')}
页面描述: {result.get('description', 'N/A')}
H1标签数量: {result.get('h1_count', 0)}
页面大小: {result.get('page_size', 0)} 字节
图片数量: {result.get('images_count', 0)}
缺少ALT属性的图片: {result.get('images_without_alt', 0)}
状态码: {result.get('status_code', 'N/A')}

H1标签内容:
"""
            for i, h1 in enumerate(result.get('h1_texts', [])):
                result_text += f"  {i+1}. {h1}\n"
            
            self.seo_result_text.setText(result_text)
            self.statusBar().showMessage("SEO分析完成")
    
    def change_theme(self, theme):
        if theme == "深色":
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
        
        self.settings.setValue("theme", theme)
    
    def apply_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.setPalette(palette)
    
    def apply_light_theme(self):
        QApplication.setPalette(QApplication.style().standardPalette())
    
    def export_database(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据库", "website_manager_backup.db", "数据库文件 (*.db)"
        )
        if file_path:
            try:
                shutil.copy2(self.db_manager.db_path, file_path)
                QMessageBox.information(self, "成功", "数据库导出成功")
            except Exception as e:
                QMessageBox.warning(self, "失败", f"数据库导出失败: {str(e)}")
    
    def import_database(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入数据库", "", "数据库文件 (*.db)"
        )
        if file_path:
            try:
                # 备份当前数据库
                backup_path = f"{self.db_manager.db_path}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2(self.db_manager.db_path, backup_path)
                
                # 导入新数据库
                shutil.copy2(file_path, self.db_manager.db_path)
                
                # 刷新界面
                self.db_manager = DatabaseManager()
                self.backup_manager = BackupManager(self.db_manager)
                self.refresh_website_list()
                
                QMessageBox.information(self, "成功", "数据库导入成功")
            except Exception as e:
                QMessageBox.warning(self, "失败", f"数据库导入失败: {str(e)}")
    
    def load_settings(self):
        theme = self.settings.value("theme", "浅色")
        self.theme_combo.setCurrentText(theme)
        self.change_theme(theme)
    
    def closeEvent(self, event):
        self.stop_monitoring()
        self.settings.sync()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("网站管理系统")
    
    window = WebsiteManager()
    window.show()
    
    sys.exit(app.exec_())