import sys
import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable

import cv2
import numpy as np
from PIL import Image, ImageGrab
import pyautogui
import pytesseract
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                             QTabWidget, QGroupBox, QSpinBox, QComboBox, 
                             QCheckBox, QProgressBar, QMessageBox, QSystemTrayIcon,
                             QMenu, QAction, QStyle, qApp)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt, QSettings
from PyQt5.QtGui import QIcon, QPixmap, QFont, QPalette, QColor

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("onmyoji_assistant.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("OnmyojiAssistant")

class ImageRecognitionThread(QThread):
    """图像识别线程"""
    recognition_result = pyqtSignal(str, dict)
    
    def __init__(self, template_path, confidence=0.8):
        super().__init__()
        self.template_path = template_path
        self.confidence = confidence
        self.is_running = True
        
    def run(self):
        """运行图像识别"""
        while self.is_running:
            # 截取屏幕
            screenshot = ImageGrab.grab()
            screenshot_np = np.array(screenshot)
            screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
            
            # 加载模板图像
            template = cv2.imread(self.template_path)
            if template is None:
                logger.error(f"无法加载模板图像: {self.template_path}")
                break
                
            # 模板匹配
            result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= self.confidence:
                # 找到匹配
                h, w = template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                
                self.recognition_result.emit(self.template_path, {
                    'confidence': max_val,
                    'position': (center_x, center_y),
                    'size': (w, h)
                })
                
            time.sleep(0.5)  # 降低CPU使用率
            
    def stop(self):
        """停止线程"""
        self.is_running = False

class AutomationThread(QThread):
    """自动化任务线程"""
    progress_update = pyqtSignal(int, str)
    task_completed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, task_type, parameters):
        super().__init__()
        self.task_type = task_type
        self.parameters = parameters
        self.is_running = True
        
    def run(self):
        """执行自动化任务"""
        try:
            if self.task_type == "auto_battle":
                self.auto_battle()
            elif self.task_type == "soul_enhance":
                self.soul_enhance()
            elif self.task_type == "shikigami_upgrade":
                self.shikigami_upgrade()
            elif self.task_type == "explore":
                self.explore()
            else:
                self.error_occurred.emit(f"未知任务类型: {self.task_type}")
        except Exception as e:
            self.error_occurred.emit(f"任务执行错误: {str(e)}")
            
    def auto_battle(self):
        """自动刷图"""
        max_rounds = self.parameters.get('max_rounds', 10)
        battle_type = self.parameters.get('battle_type', 'explore')
        
        for round_num in range(1, max_rounds + 1):
            if not self.is_running:
                break
                
            self.progress_update.emit(
                int(round_num / max_rounds * 100),
                f"正在进行第 {round_num}/{max_rounds} 场战斗"
            )
            
            # 模拟战斗流程
            self.click_position(800, 600)  # 点击开始战斗
            time.sleep(2)
            
            # 等待战斗结束
            battle_time = self.parameters.get('battle_time', 30)
            time.sleep(battle_time)
            
            # 点击结束
            self.click_position(800, 600)
            time.sleep(2)
            
        self.task_completed.emit(f"自动刷图完成，共进行了 {max_rounds} 场战斗")
        
    def soul_enhance(self):
        """御魂强化"""
        max_attempts = self.parameters.get('max_attempts', 50)
        target_level = self.parameters.get('target_level', 15)
        
        for attempt in range(1, max_attempts + 1):
            if not self.is_running:
                break
                
            self.progress_update.emit(
                int(attempt / max_attempts * 100),
                f"御魂强化尝试 {attempt}/{max_attempts}"
            )
            
            # 模拟御魂强化流程
            self.click_position(700, 500)  # 选择御魂
            time.sleep(1)
            self.click_position(900, 700)  # 点击强化
            time.sleep(3)
            self.click_position(800, 600)  # 确认强化
            time.sleep(2)
            
        self.task_completed.emit(f"御魂强化完成，共尝试 {max_attempts} 次")
        
    def shikigami_upgrade(self):
        """式神培养"""
        max_shikigami = self.parameters.get('max_shikigami', 10)
        upgrade_type = self.parameters.get('upgrade_type', 'level')
        
        for i in range(1, max_shikigami + 1):
            if not self.is_running:
                break
                
            self.progress_update.emit(
                int(i / max_shikigami * 100),
                f"正在培养第 {i}/{max_shikigami} 个式神"
            )
            
            # 模拟式神培养流程
            self.click_position(600, 400)  # 选择式神
            time.sleep(1)
            self.click_position(800, 600)  # 点击培养
            time.sleep(2)
            self.click_position(700, 500)  # 选择材料
            time.sleep(1)
            self.click_position(900, 700)  # 确认培养
            time.sleep(3)
            
        self.task_completed.emit(f"式神培养完成，共培养 {max_shikigami} 个式神")
        
    def explore(self):
        """探索副本"""
        max_explores = self.parameters.get('max_explores', 20)
        chapter = self.parameters.get('chapter', 28)
        
        for i in range(1, max_explores + 1):
            if not self.is_running:
                break
                
            self.progress_update.emit(
                int(i / max_explores * 100),
                f"探索第 {i}/{max_explores} 次，章节 {chapter}"
            )
            
            # 模拟探索流程
            self.click_position(800, 400)  # 点击探索
            time.sleep(1)
            self.click_position(600, 500)  # 选择章节
            time.sleep(1)
            self.click_position(700, 600)  # 开始探索
            time.sleep(30)  # 探索时间
            
        self.task_completed.emit(f"探索完成，共探索 {max_explores} 次")
        
    def click_position(self, x, y):
        """模拟点击指定位置"""
        pyautogui.click(x, y)
        time.sleep(0.5)
        
    def stop(self):
        """停止任务"""
        self.is_running = False

class OnmyojiAssistant(QMainWindow):
    """阴阳师辅助系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.automation_thread = None
        self.recognition_threads = []
        self.settings = QSettings("OnmyojiAssistant", "Config")
        self.init_ui()
        self.init_tray_icon()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("阴阳师辅助系统 v2.0")
        self.setGeometry(100, 100, 900, 700)
        self.setMinimumSize(800, 600)
        
        # 设置应用图标
        self.setWindowIcon(QIcon(self.style().standardPixmap(QStyle.SP_ComputerIcon)))
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # 自动战斗标签页
        auto_battle_tab = self.create_auto_battle_tab()
        tab_widget.addTab(auto_battle_tab, "自动战斗")
        
        # 御魂强化标签页
        soul_enhance_tab = self.create_soul_enhance_tab()
        tab_widget.addTab(soul_enhance_tab, "御魂强化")
        
        # 式神培养标签页
        shikigami_tab = self.create_shikigami_tab()
        tab_widget.addTab(shikigami_tab, "式神培养")
        
        # 探索副本标签页
        explore_tab = self.create_explore_tab()
        tab_widget.addTab(explore_tab, "探索副本")
        
        # 设置标签页
        settings_tab = self.create_settings_tab()
        tab_widget.addTab(settings_tab, "设置")
        
        # 日志区域
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        self.statusBar().addWidget(self.status_label)
        
        # 加载保存的设置
        self.load_settings()
        
    def create_auto_battle_tab(self):
        """创建自动战斗标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 战斗类型选择
        type_group = QGroupBox("战斗类型")
        type_layout = QHBoxLayout()
        self.battle_type_combo = QComboBox()
        self.battle_type_combo.addItems(["探索副本", "御魂副本", "觉醒副本", "妖气封印"])
        type_layout.addWidget(QLabel("战斗类型:"))
        type_layout.addWidget(self.battle_type_combo)
        type_layout.addStretch()
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 战斗设置
        settings_group = QGroupBox("战斗设置")
        settings_layout = QVBoxLayout()
        
        rounds_layout = QHBoxLayout()
        self.rounds_spin = QSpinBox()
        self.rounds_spin.setRange(1, 999)
        self.rounds_spin.setValue(10)
        rounds_layout.addWidget(QLabel("战斗场次:"))
        rounds_layout.addWidget(self.rounds_spin)
        rounds_layout.addStretch()
        
        time_layout = QHBoxLayout()
        self.battle_time_spin = QSpinBox()
        self.battle_time_spin.setRange(10, 300)
        self.battle_time_spin.setValue(30)
        self.battle_time_spin.setSuffix(" 秒")
        time_layout.addWidget(QLabel("每场战斗时间:"))
        time_layout.addWidget(self.battle_time_spin)
        time_layout.addStretch()
        
        settings_layout.addLayout(rounds_layout)
        settings_layout.addLayout(time_layout)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 功能按钮
        button_layout = QHBoxLayout()
        self.start_battle_btn = QPushButton("开始自动战斗")
        self.start_battle_btn.clicked.connect(self.start_auto_battle)
        self.stop_battle_btn = QPushButton("停止战斗")
        self.stop_battle_btn.clicked.connect(self.stop_automation)
        self.stop_battle_btn.setEnabled(False)
        
        button_layout.addWidget(self.start_battle_btn)
        button_layout.addWidget(self.stop_battle_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return tab
        
    def create_soul_enhance_tab(self):
        """创建御魂强化标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 强化设置
        enhance_group = QGroupBox("御魂强化设置")
        enhance_layout = QVBoxLayout()
        
        attempts_layout = QHBoxLayout()
        self.enhance_attempts_spin = QSpinBox()
        self.enhance_attempts_spin.setRange(1, 999)
        self.enhance_attempts_spin.setValue(50)
        attempts_layout.addWidget(QLabel("强化尝试次数:"))
        attempts_layout.addWidget(self.enhance_attempts_spin)
        attempts_layout.addStretch()
        
        level_layout = QHBoxLayout()
        self.target_level_spin = QSpinBox()
        self.target_level_spin.setRange(1, 15)
        self.target_level_spin.setValue(15)
        level_layout.addWidget(QLabel("目标等级:"))
        level_layout.addWidget(self.target_level_spin)
        level_layout.addStretch()
        
        enhance_layout.addLayout(attempts_layout)
        enhance_layout.addLayout(level_layout)
        enhance_group.setLayout(enhance_layout)
        layout.addWidget(enhance_group)
        
        # 功能按钮
        button_layout = QHBoxLayout()
        self.start_enhance_btn = QPushButton("开始御魂强化")
        self.start_enhance_btn.clicked.connect(self.start_soul_enhance)
        self.stop_enhance_btn = QPushButton("停止强化")
        self.stop_enhance_btn.clicked.connect(self.stop_automation)
        self.stop_enhance_btn.setEnabled(False)
        
        button_layout.addWidget(self.start_enhance_btn)
        button_layout.addWidget(self.stop_enhance_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return tab
        
    def create_shikigami_tab(self):
        """创建式神培养标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 培养设置
        upgrade_group = QGroupBox("式神培养设置")
        upgrade_layout = QVBoxLayout()
        
        type_layout = QHBoxLayout()
        self.upgrade_type_combo = QComboBox()
        self.upgrade_type_combo.addItems(["等级提升", "技能升级", "觉醒"])
        type_layout.addWidget(QLabel("培养类型:"))
        type_layout.addWidget(self.upgrade_type_combo)
        type_layout.addStretch()
        
        count_layout = QHBoxLayout()
        self.shikigami_count_spin = QSpinBox()
        self.shikigami_count_spin.setRange(1, 50)
        self.shikigami_count_spin.setValue(10)
        count_layout.addWidget(QLabel("培养式神数量:"))
        count_layout.addWidget(self.shikigami_count_spin)
        count_layout.addStretch()
        
        upgrade_layout.addLayout(type_layout)
        upgrade_layout.addLayout(count_layout)
        upgrade_group.setLayout(upgrade_layout)
        layout.addWidget(upgrade_group)
        
        # 功能按钮
        button_layout = QHBoxLayout()
        self.start_upgrade_btn = QPushButton("开始式神培养")
        self.start_upgrade_btn.clicked.connect(self.start_shikigami_upgrade)
        self.stop_upgrade_btn = QPushButton("停止培养")
        self.stop_upgrade_btn.clicked.connect(self.stop_automation)
        self.stop_upgrade_btn.setEnabled(False)
        
        button_layout.addWidget(self.start_upgrade_btn)
        button_layout.addWidget(self.stop_upgrade_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return tab
        
    def create_explore_tab(self):
        """创建探索副本标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 探索设置
        explore_group = QGroupBox("探索设置")
        explore_layout = QVBoxLayout()
        
        chapter_layout = QHBoxLayout()
        self.chapter_spin = QSpinBox()
        self.chapter_spin.setRange(1, 28)
        self.chapter_spin.setValue(28)
        chapter_layout.addWidget(QLabel("章节:"))
        chapter_layout.addWidget(self.chapter_spin)
        chapter_layout.addStretch()
        
        count_layout = QHBoxLayout()
        self.explore_count_spin = QSpinBox()
        self.explore_count_spin.setRange(1, 999)
        self.explore_count_spin.setValue(20)
        count_layout.addWidget(QLabel("探索次数:"))
        count_layout.addWidget(self.explore_count_spin)
        count_layout.addStretch()
        
        explore_layout.addLayout(chapter_layout)
        explore_layout.addLayout(count_layout)
        explore_group.setLayout(explore_layout)
        layout.addWidget(explore_group)
        
        # 功能按钮
        button_layout = QHBoxLayout()
        self.start_explore_btn = QPushButton("开始探索")
        self.start_explore_btn.clicked.connect(self.start_explore)
        self.stop_explore_btn = QPushButton("停止探索")
        self.stop_explore_btn.clicked.connect(self.stop_automation)
        self.stop_explore_btn.setEnabled(False)
        
        button_layout.addWidget(self.start_explore_btn)
        button_layout.addWidget(self.stop_explore_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return tab
        
    def create_settings_tab(self):
        """创建设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 通用设置
        general_group = QGroupBox("通用设置")
        general_layout = QVBoxLayout()
        
        self.auto_start_check = QCheckBox("启动时最小化到系统托盘")
        self.auto_save_check = QCheckBox("自动保存设置")
        self.auto_save_check.setChecked(True)
        
        general_layout.addWidget(self.auto_start_check)
        general_layout.addWidget(self.auto_save_check)
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # 图像识别设置
        recognition_group = QGroupBox("图像识别设置")
        recognition_layout = QVBoxLayout()
        
        confidence_layout = QHBoxLayout()
        self.confidence_spin = QSpinBox()
        self.confidence_spin.setRange(50, 100)
        self.confidence_spin.setValue(80)
        self.confidence_spin.setSuffix(" %")
        confidence_layout.addWidget(QLabel("识别置信度:"))
        confidence_layout.addWidget(self.confidence_spin)
        confidence_layout.addStretch()
        
        recognition_layout.addLayout(confidence_layout)
        recognition_group.setLayout(recognition_layout)
        layout.addWidget(recognition_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.save_settings_btn = QPushButton("保存设置")
        self.save_settings_btn.clicked.connect(self.save_settings)
        self.load_settings_btn = QPushButton("加载设置")
        self.load_settings_btn.clicked.connect(self.load_settings)
        
        button_layout.addWidget(self.save_settings_btn)
        button_layout.addWidget(self.load_settings_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return tab
        
    def init_tray_icon(self):
        """初始化系统托盘图标"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(None, "系统托盘", "本系统不支持系统托盘功能")
            return
            
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示主窗口")
        show_action.triggered.connect(self.show)
        
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(qApp.quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        
    def tray_icon_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()
            
    def closeEvent(self, event):
        """关闭事件处理"""
        if self.auto_save_check.isChecked():
            self.save_settings()
            
        if self.tray_icon.isVisible():
            QMessageBox.information(self, "系统托盘", 
                                   "程序将继续在系统托盘中运行。要完全退出程序，请选择托盘菜单中的退出选项。")
            self.hide()
            event.ignore()
        else:
            event.accept()
            
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
    def update_progress(self, value, message):
        """更新进度条和状态"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        
    def start_auto_battle(self):
        """开始自动战斗"""
        parameters = {
            'max_rounds': self.rounds_spin.value(),
            'battle_type': self.battle_type_combo.currentText(),
            'battle_time': self.battle_time_spin.value()
        }
        self.start_automation("auto_battle", parameters)
        
    def start_soul_enhance(self):
        """开始御魂强化"""
        parameters = {
            'max_attempts': self.enhance_attempts_spin.value(),
            'target_level': self.target_level_spin.value()
        }
        self.start_automation("soul_enhance", parameters)
        
    def start_shikigami_upgrade(self):
        """开始式神培养"""
        parameters = {
            'max_shikigami': self.shikigami_count_spin.value(),
            'upgrade_type': self.upgrade_type_combo.currentText()
        }
        self.start_automation("shikigami_upgrade", parameters)
        
    def start_explore(self):
        """开始探索副本"""
        parameters = {
            'max_explores': self.explore_count_spin.value(),
            'chapter': self.chapter_spin.value()
        }
        self.start_automation("explore", parameters)
        
    def start_automation(self, task_type, parameters):
        """开始自动化任务"""
        if self.automation_thread and self.automation_thread.isRunning():
            QMessageBox.warning(self, "任务运行中", "当前已有任务正在运行，请先停止当前任务")
            return
            
        # 禁用开始按钮，启用停止按钮
        self.set_automation_buttons(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动自动化线程
        self.automation_thread = AutomationThread(task_type, parameters)
        self.automation_thread.progress_update.connect(self.update_progress)
        self.automation_thread.task_completed.connect(self.on_task_completed)
        self.automation_thread.error_occurred.connect(self.on_task_error)
        self.automation_thread.start()
        
        self.log_message(f"开始{task_type}任务")
        
    def stop_automation(self):
        """停止自动化任务"""
        if self.automation_thread and self.automation_thread.isRunning():
            self.automation_thread.stop()
            self.automation_thread.wait(5000)  # 等待5秒
            
            if self.automation_thread.isRunning():
                self.automation_thread.terminate()
                
            self.set_automation_buttons(True)
            self.progress_bar.setVisible(False)
            self.status_label.setText("任务已停止")
            self.log_message("任务已手动停止")
            
    def set_automation_buttons(self, enabled):
        """设置自动化按钮状态"""
        self.start_battle_btn.setEnabled(enabled)
        self.start_enhance_btn.setEnabled(enabled)
        self.start_upgrade_btn.setEnabled(enabled)
        self.start_explore_btn.setEnabled(enabled)
        
        self.stop_battle_btn.setEnabled(not enabled)
        self.stop_enhance_btn.setEnabled(not enabled)
        self.stop_upgrade_btn.setEnabled(not enabled)
        self.stop_explore_btn.setEnabled(not enabled)
        
    def on_task_completed(self, message):
        """任务完成回调"""
        self.set_automation_buttons(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("任务完成")
        self.log_message(message)
        QMessageBox.information(self, "任务完成", message)
        
    def on_task_error(self, error_message):
        """任务错误回调"""
        self.set_automation_buttons(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("任务出错")
        self.log_message(f"错误: {error_message}")
        QMessageBox.critical(self, "任务错误", error_message)
        
    def save_settings(self):
        """保存设置"""
        self.settings.setValue("auto_start", self.auto_start_check.isChecked())
        self.settings.setValue("auto_save", self.auto_save_check.isChecked())
        self.settings.setValue("confidence", self.confidence_spin.value())
        
        # 保存战斗设置
        self.settings.setValue("battle_type", self.battle_type_combo.currentIndex())
        self.settings.setValue("rounds", self.rounds_spin.value())
        self.settings.setValue("battle_time", self.battle_time_spin.value())
        
        # 保存御魂强化设置
        self.settings.setValue("enhance_attempts", self.enhance_attempts_spin.value())
        self.settings.setValue("target_level", self.target_level_spin.value())
        
        # 保存式神培养设置
        self.settings.setValue("upgrade_type", self.upgrade_type_combo.currentIndex())
        self.settings.setValue("shikigami_count", self.shikigami_count_spin.value())
        
        # 保存探索设置
        self.settings.setValue("chapter", self.chapter_spin.value())
        self.settings.setValue("explore_count", self.explore_count_spin.value())
        
        self.log_message("设置已保存")
        
    def load_settings(self):
        """加载设置"""
        self.auto_start_check.setChecked(self.settings.value("auto_start", False, type=bool))
        self.auto_save_check.setChecked(self.settings.value("auto_save", True, type=bool))
        self.confidence_spin.setValue(self.settings.value("confidence", 80, type=int))
        
        # 加载战斗设置
        self.battle_type_combo.setCurrentIndex(self.settings.value("battle_type", 0, type=int))
        self.rounds_spin.setValue(self.settings.value("rounds", 10, type=int))
        self.battle_time_spin.setValue(self.settings.value("battle_time", 30, type=int))
        
        # 加载御魂强化设置
        self.enhance_attempts_spin.setValue(self.settings.value("enhance_attempts", 50, type=int))
        self.target_level_spin.setValue(self.settings.value("target_level", 15, type=int))
        
        # 加载式神培养设置
        self.upgrade_type_combo.setCurrentIndex(self.settings.value("upgrade_type", 0, type=int))
        self.shikigami_count_spin.setValue(self.settings.value("shikigami_count", 10, type=int))
        
        # 加载探索设置
        self.chapter_spin.setValue(self.settings.value("chapter", 28, type=int))
        self.explore_count_spin.setValue(self.settings.value("explore_count", 20, type=int))
        
        self.log_message("设置已加载")

def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("阴阳师辅助系统")
    app.setApplicationVersion("2.0")
    app.setQuitOnLastWindowClosed(False)
    
    # 设置样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = OnmyojiAssistant()
    window.show()
    
    # 如果设置为启动时最小化到托盘
    if window.auto_start_check.isChecked():
        window.hide()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()