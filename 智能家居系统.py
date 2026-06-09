import sys
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, 
                             QListWidgetItem, QTabWidget, QGroupBox, QSlider,
                             QSpinBox, QDoubleSpinBox, QCheckBox, QLineEdit,
                             QTextEdit, QComboBox, QDateTimeEdit, QProgressBar,
                             QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QTimer, QDateTime, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QPainter, QPalette, QIcon, QPixmap
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
import requests


# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SmartHomeToolkit")


# 设备类型枚举
class DeviceType(Enum):
    LIGHT = "light"
    THERMOSTAT = "thermostat"
    DOOR_LOCK = "door_lock"
    CAMERA = "camera"
    SENSOR = "sensor"
    SWITCH = "switch"
    BLINDS = "blinds"
    SPEAKER = "speaker"


# 设备状态基类
@dataclass
class DeviceState:
    device_id: str
    timestamp: datetime
    online: bool = True


# 具体设备状态类
@dataclass
class LightState(DeviceState):
    brightness: int = 100
    color_temp: int = 4000
    color: str = "#FFFFFF"
    is_on: bool = False


@dataclass
class ThermostatState(DeviceState):
    temperature: float = 22.0
    target_temperature: float = 22.0
    mode: str = "heat"  # heat, cool, auto, off
    fan_on: bool = False


@dataclass
class DoorLockState(DeviceState):
    is_locked: bool = True
    battery_level: int = 100


# 设备基类
class SmartDevice:
    def __init__(self, device_id: str, name: str, device_type: DeviceType, room: str = "Unknown"):
        self.device_id = device_id
        self.name = name
        self.type = device_type
        self.room = room
        self.state = None
        self.callbacks = []
    
    def update_state(self, new_state: DeviceState):
        old_state = self.state
        self.state = new_state
        self._notify_callbacks(old_state, new_state)
    
    def add_state_change_callback(self, callback: Callable):
        self.callbacks.append(callback)
    
    def _notify_callbacks(self, old_state, new_state):
        for callback in self.callbacks:
            try:
                callback(self, old_state, new_state)
            except Exception as e:
                logger.error(f"Error in device callback: {e}")


# 设备管理器
class DeviceManager:
    def __init__(self):
        self.devices: Dict[str, SmartDevice] = {}
        self.rooms: Dict[str, List[SmartDevice]] = {}
    
    def add_device(self, device: SmartDevice):
        self.devices[device.device_id] = device
        
        if device.room not in self.rooms:
            self.rooms[device.room] = []
        self.rooms[device.room].append(device)
        
        logger.info(f"Added device: {device.name} ({device.type.value}) to room: {device.room}")
    
    def remove_device(self, device_id: str):
        if device_id in self.devices:
            device = self.devices[device_id]
            if device.room in self.rooms and device in self.rooms[device.room]:
                self.rooms[device.room].remove(device)
            del self.devices[device_id]
            logger.info(f"Removed device: {device_id}")
    
    def get_device(self, device_id: str) -> Optional[SmartDevice]:
        return self.devices.get(device_id)
    
    def get_devices_by_room(self, room: str) -> List[SmartDevice]:
        return self.rooms.get(room, [])
    
    def get_devices_by_type(self, device_type: DeviceType) -> List[SmartDevice]:
        return [device for device in self.devices.values() if device.type == device_type]
    
    def get_all_devices(self) -> List[SmartDevice]:
        return list(self.devices.values())


# 自动化规则条件
@dataclass
class Condition:
    device_id: str
    property_name: str
    operator: str  # ==, !=, >, <, >=, <=
    value: Any
    
    def evaluate(self, device_manager: DeviceManager) -> bool:
        device = device_manager.get_device(self.device_id)
        if not device or not device.state:
            return False
        
        current_value = getattr(device.state, self.property_name, None)
        if current_value is None:
            return False
        
        try:
            if self.operator == "==":
                return current_value == self.value
            elif self.operator == "!=":
                return current_value != self.value
            elif self.operator == ">":
                return current_value > self.value
            elif self.operator == "<":
                return current_value < self.value
            elif self.operator == ">=":
                return current_value >= self.value
            elif self.operator == "<=":
                return current_value <= self.value
            else:
                return False
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False


# 自动化规则动作
@dataclass
class Action:
    device_id: str
    command: str
    parameters: Dict[str, Any]
    
    def execute(self, device_manager: DeviceManager):
        device = device_manager.get_device(self.device_id)
        if not device:
            logger.error(f"Device {self.device_id} not found for action")
            return
        
        # 在实际实现中，这里会调用设备的实际控制方法
        logger.info(f"Executing action: {self.command} on {device.name} with params {self.parameters}")
        
        # 模拟设备状态更新
        if hasattr(device.state, self.command):
            # 这里简化处理，实际应该通过设备控制协议执行
            setattr(device.state, self.command, self.parameters.get('value'))
            
            # 更新时间戳
            device.state.timestamp = datetime.now()
            
            # 通知状态变化
            device._notify_callbacks(device.state, device.state)


# 自动化规则
class AutomationRule:
    def __init__(self, rule_id: str, name: str, enabled: bool = True):
        self.rule_id = rule_id
        self.name = name
        self.enabled = enabled
        self.conditions: List[Condition] = []
        self.actions: List[Action] = []
        self.trigger_count = 0
        self.last_triggered = None
    
    def add_condition(self, condition: Condition):
        self.conditions.append(condition)
    
    def add_action(self, action: Action):
        self.actions.append(action)
    
    def evaluate(self, device_manager: DeviceManager) -> bool:
        if not self.enabled:
            return False
        
        # 所有条件都必须满足
        for condition in self.conditions:
            if not condition.evaluate(device_manager):
                return False
        
        return True
    
    def execute(self, device_manager: DeviceManager):
        if not self.enabled:
            return
        
        self.trigger_count += 1
        self.last_triggered = datetime.now()
        
        for action in self.actions:
            action.execute(device_manager)
        
        logger.info(f"Automation rule '{self.name}' triggered")


# 场景
class Scene:
    def __init__(self, scene_id: str, name: str):
        self.scene_id = scene_id
        self.name = name
        self.actions: List[Action] = []
    
    def add_action(self, action: Action):
        self.actions.append(action)
    
    def activate(self, device_manager: DeviceManager):
        for action in self.actions:
            action.execute(device_manager)
        
        logger.info(f"Scene '{self.name}' activated")


# 数据记录器
class DataLogger:
    def __init__(self, db_path: str = "smart_home.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建设备状态记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                property_name TEXT NOT NULL,
                property_value TEXT NOT NULL
            )
        ''')
        
        # 创建设备事件记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT NOT NULL
            )
        ''')
        
        # 创建自动化规则触发记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS automation_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_device_state(self, device_id: str, property_name: str, property_value: Any):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO device_states (device_id, timestamp, property_name, property_value)
            VALUES (?, ?, ?, ?)
        ''', (device_id, datetime.now(), property_name, str(property_value)))
        
        conn.commit()
        conn.close()
    
    def log_device_event(self, device_id: str, event_type: str, event_data: Dict[str, Any]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO device_events (device_id, timestamp, event_type, event_data)
            VALUES (?, ?, ?, ?)
        ''', (device_id, datetime.now(), event_type, json.dumps(event_data)))
        
        conn.commit()
        conn.close()
    
    def log_automation_trigger(self, rule_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO automation_triggers (rule_id, timestamp)
            VALUES (?, ?)
        ''', (rule_id, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def get_device_history(self, device_id: str, property_name: str, 
                          start_time: datetime, end_time: datetime) -> List[tuple]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, property_value 
            FROM device_states 
            WHERE device_id = ? AND property_name = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        ''', (device_id, property_name, start_time, end_time))
        
        results = cursor.fetchall()
        conn.close()
        
        return results


# 智能家居核心系统
class SmartHomeSystem:
    def __init__(self):
        self.device_manager = DeviceManager()
        self.automation_rules: Dict[str, AutomationRule] = {}
        self.scenes: Dict[str, Scene] = {}
        self.data_logger = DataLogger()
        self.evaluation_timer = QTimer()
        self.evaluation_timer.timeout.connect(self.evaluate_automation_rules)
        self.evaluation_timer.start(5000)  # 每5秒检查一次自动化规则
    
    def add_automation_rule(self, rule: AutomationRule):
        self.automation_rules[rule.rule_id] = rule
    
    def remove_automation_rule(self, rule_id: str):
        if rule_id in self.automation_rules:
            del self.automation_rules[rule_id]
    
    def add_scene(self, scene: Scene):
        self.scenes[scene.scene_id] = scene
    
    def remove_scene(self, scene_id: str):
        if scene_id in self.scenes:
            del self.scenes[scene_id]
    
    def evaluate_automation_rules(self):
        for rule in self.automation_rules.values():
            if rule.evaluate(self.device_manager):
                rule.execute(self.device_manager)
                self.data_logger.log_automation_trigger(rule.rule_id)
    
    def activate_scene(self, scene_id: str):
        if scene_id in self.scenes:
            self.scenes[scene_id].activate(self.device_manager)


# 设备控制面板基类
class DeviceControlPanel(QWidget):
    def __init__(self, device: SmartDevice, parent=None):
        super().__init__(parent)
        self.device = device
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # 设备名称和状态
        self.name_label = QLabel(device.name)
        self.name_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.layout.addWidget(self.name_label)
        
        self.status_label = QLabel("离线")
        self.layout.addWidget(self.status_label)
        
        # 设备特定的控制部件
        self.setup_ui()
        
        # 监听设备状态变化
        self.device.add_state_change_callback(self.on_device_state_changed)
        self.on_device_state_changed(self.device, None, self.device.state)
    
    def setup_ui(self):
        # 子类重写此方法以添加特定设备的控制界面
        pass
    
    def on_device_state_changed(self, device, old_state, new_state):
        if new_state:
            status_text = "在线" if new_state.online else "离线"
            self.status_label.setText(status_text)
            
            if not new_state.online:
                self.status_label.setStyleSheet("color: red;")
            else:
                self.status_label.setStyleSheet("color: green;")
        
        self.update_ui()
    
    def update_ui(self):
        # 子类重写此方法以更新UI反映设备状态
        pass


# 灯光控制面板
class LightControlPanel(DeviceControlPanel):
    def setup_ui(self):
        # 开关按钮
        self.power_button = QPushButton("打开")
        self.power_button.clicked.connect(self.toggle_power)
        self.layout.addWidget(self.power_button)
        
        # 亮度滑块
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("亮度:"))
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.valueChanged.connect(self.set_brightness)
        brightness_layout.addWidget(self.brightness_slider)
        self.brightness_label = QLabel("100%")
        brightness_layout.addWidget(self.brightness_label)
        self.layout.addLayout(brightness_layout)
        
        # 色温控制
        color_temp_layout = QHBoxLayout()
        color_temp_layout.addWidget(QLabel("色温:"))
        self.color_temp_slider = QSlider(Qt.Horizontal)
        self.color_temp_slider.setRange(2700, 6500)
        self.color_temp_slider.valueChanged.connect(self.set_color_temp)
        color_temp_layout.addWidget(self.color_temp_slider)
        self.color_temp_label = QLabel("4000K")
        color_temp_layout.addWidget(self.color_temp_label)
        self.layout.addLayout(color_temp_layout)
    
    def update_ui(self):
        if self.device.state:
            state = self.device.state
            
            # 更新开关按钮
            if state.is_on:
                self.power_button.setText("关闭")
            else:
                self.power_button.setText("打开")
            
            # 更新亮度
            self.brightness_slider.setValue(state.brightness)
            self.brightness_label.setText(f"{state.brightness}%")
            
            # 更新色温
            self.color_temp_slider.setValue(state.color_temp)
            self.color_temp_label.setText(f"{state.color_temp}K")
    
    def toggle_power(self):
        if self.device.state:
            new_state = LightState(
                device_id=self.device.device_id,
                timestamp=datetime.now(),
                is_on=not self.device.state.is_on,
                brightness=self.device.state.brightness,
                color_temp=self.device.state.color_temp,
                color=self.device.state.color
            )
            self.device.update_state(new_state)
    
    def set_brightness(self, value):
        if self.device.state and self.device.state.is_on:
            new_state = LightState(
                device_id=self.device.device_id,
                timestamp=datetime.now(),
                is_on=self.device.state.is_on,
                brightness=value,
                color_temp=self.device.state.color_temp,
                color=self.device.state.color
            )
            self.device.update_state(new_state)
    
    def set_color_temp(self, value):
        if self.device.state and self.device.state.is_on:
            new_state = LightState(
                device_id=self.device.device_id,
                timestamp=datetime.now(),
                is_on=self.device.state.is_on,
                brightness=self.device.state.brightness,
                color_temp=value,
                color=self.device.state.color
            )
            self.device.update_state(new_state)


# 恒温器控制面板
class ThermostatControlPanel(DeviceControlPanel):
    def setup_ui(self):
        # 当前温度显示
        self.temp_label = QLabel("当前温度: --°C")
        self.temp_label.setFont(QFont("Arial", 16))
        self.layout.addWidget(self.temp_label)
        
        # 目标温度控制
        target_temp_layout = QHBoxLayout()
        target_temp_layout.addWidget(QLabel("目标温度:"))
        self.target_temp_spinbox = QDoubleSpinBox()
        self.target_temp_spinbox.setRange(10, 30)
        self.target_temp_spinbox.setSingleStep(0.5)
        self.target_temp_spinbox.valueChanged.connect(self.set_target_temperature)
        target_temp_layout.addWidget(self.target_temp_spinbox)
        target_temp_layout.addWidget(QLabel("°C"))
        self.layout.addLayout(target_temp_layout)
        
        # 模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["制热", "制冷", "自动", "关闭"])
        self.mode_combo.currentTextChanged.connect(self.set_mode)
        mode_layout.addWidget(self.mode_combo)
        self.layout.addLayout(mode_layout)
        
        # 风扇控制
        self.fan_checkbox = QCheckBox("开启风扇")
        self.fan_checkbox.stateChanged.connect(self.set_fan)
        self.layout.addWidget(self.fan_checkbox)
    
    def update_ui(self):
        if self.device.state:
            state = self.device.state
            
            # 更新温度显示
            self.temp_label.setText(f"当前温度: {state.temperature}°C")
            
            # 更新目标温度
            self.target_temp_spinbox.setValue(state.target_temperature)
            
            # 更新模式
            mode_map = {"heat": "制热", "cool": "制冷", "auto": "自动", "off": "关闭"}
            self.mode_combo.setCurrentText(mode_map.get(state.mode, "关闭"))
            
            # 更新风扇状态
            self.fan_checkbox.setChecked(state.fan_on)
    
    def set_target_temperature(self, value):
        if self.device.state:
            new_state = ThermostatState(
                device_id=self.device.device_id,
                timestamp=datetime.now(),
                temperature=self.device.state.temperature,
                target_temperature=value,
                mode=self.device.state.mode,
                fan_on=self.device.state.fan_on
            )
            self.device.update_state(new_state)
    
    def set_mode(self, mode_text):
        if self.device.state:
            mode_map = {"制热": "heat", "制冷": "cool", "自动": "auto", "关闭": "off"}
            new_mode = mode_map.get(mode_text, "off")
            
            new_state = ThermostatState(
                device_id=self.device.device_id,
                timestamp=datetime.now(),
                temperature=self.device.state.temperature,
                target_temperature=self.device.state.target_temperature,
                mode=new_mode,
                fan_on=self.device.state.fan_on
            )
            self.device.update_state(new_state)
    
    def set_fan(self, state):
        if self.device.state:
            new_state = ThermostatState(
                device_id=self.device.device_id,
                timestamp=datetime.now(),
                temperature=self.device.state.temperature,
                target_temperature=self.device.state.target_temperature,
                mode=self.device.state.mode,
                fan_on=state == Qt.Checked
            )
            self.device.update_state(new_state)


# 主界面
class SmartHomeMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.smart_home_system = SmartHomeSystem()
        self.init_ui()
        self.setup_demo_data()
    
    def init_ui(self):
        self.setWindowTitle("智能家居控制系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧设备列表
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(300)
        
        # 房间选择
        room_layout = QHBoxLayout()
        room_layout.addWidget(QLabel("房间:"))
        self.room_combo = QComboBox()
        self.room_combo.currentTextChanged.connect(self.on_room_changed)
        room_layout.addWidget(self.room_combo)
        left_layout.addLayout(room_layout)
        
        # 设备列表
        self.device_list = QListWidget()
        self.device_list.currentItemChanged.connect(self.on_device_selected)
        left_layout.addWidget(self.device_list)
        
        # 右侧控制面板
        self.control_panel = QTabWidget()
        
        # 添加设备控制选项卡
        self.device_tab = QWidget()
        self.device_tab_layout = QVBoxLayout()
        self.device_tab.setLayout(self.device_tab_layout)
        self.control_panel.addTab(self.device_tab, "设备控制")
        
        # 添加场景控制选项卡
        self.scene_tab = QWidget()
        self.scene_tab_layout = QVBoxLayout()
        self.scene_tab.setLayout(self.scene_tab_layout)
        self.control_panel.addTab(self.scene_tab, "场景")
        
        # 添加自动化规则选项卡
        self.automation_tab = QWidget()
        self.automation_tab_layout = QVBoxLayout()
        self.automation_tab.setLayout(self.automation_tab_layout)
        self.control_panel.addTab(self.automation_tab, "自动化")
        
        # 添加数据分析选项卡
        self.analytics_tab = QWidget()
        self.analytics_tab_layout = QVBoxLayout()
        self.analytics_tab.setLayout(self.analytics_tab_layout)
        self.control_panel.addTab(self.analytics_tab, "数据分析")
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.control_panel)
        splitter.setSizes([300, 900])
        
        main_layout.addWidget(splitter)
        
        # 初始化各个选项卡
        self.setup_scene_tab()
        self.setup_automation_tab()
        self.setup_analytics_tab()
    
    def setup_demo_data(self):
        # 添加示例设备
        light1 = SmartDevice("light_1", "客厅主灯", DeviceType.LIGHT, "客厅")
        light1.update_state(LightState("light_1", datetime.now(), is_on=False))
        self.smart_home_system.device_manager.add_device(light1)
        
        light2 = SmartDevice("light_2", "卧室灯", DeviceType.LIGHT, "卧室")
        light2.update_state(LightState("light_2", datetime.now(), is_on=True, brightness=80))
        self.smart_home_system.device_manager.add_device(light2)
        
        thermostat = SmartDevice("thermostat_1", "客厅恒温器", DeviceType.THERMOSTAT, "客厅")
        thermostat.update_state(ThermostatState("thermostat_1", datetime.now(), 
                                               temperature=22.5, target_temperature=23.0))
        self.smart_home_system.device_manager.add_device(thermostat)
        
        # 添加房间到下拉列表
        rooms = list(self.smart_home_system.device_manager.rooms.keys())
        self.room_combo.addItems(rooms)
        
        # 添加示例场景
        evening_scene = Scene("scene_1", "晚间模式")
        evening_scene.add_action(Action("light_1", "is_on", {"value": True}))
        evening_scene.add_action(Action("light_1", "brightness", {"value": 30}))
        evening_scene.add_action(Action("thermostat_1", "target_temperature", {"value": 20.0}))
        self.smart_home_system.add_scene(evening_scene)
        
        # 添加示例自动化规则
        away_rule = AutomationRule("rule_1", "离家模式")
        away_rule.add_condition(Condition("light_1", "is_on", "==", True))
        away_rule.add_action(Action("light_1", "is_on", {"value": False}))
        away_rule.add_action(Action("thermostat_1", "target_temperature", {"value": 18.0}))
        self.smart_home_system.add_automation_rule(away_rule)
        
        # 更新设备列表
        self.update_device_list()
    
    def update_device_list(self):
        self.device_list.clear()
        
        current_room = self.room_combo.currentText()
        if current_room:
            devices = self.smart_home_system.device_manager.get_devices_by_room(current_room)
            for device in devices:
                item = QListWidgetItem(device.name)
                item.setData(Qt.UserRole, device.device_id)
                self.device_list.addItem(item)
    
    def on_room_changed(self, room_name):
        self.update_device_list()
    
    def on_device_selected(self, current, previous):
        if not current:
            return
        
        # 清除之前的控制面板
        for i in reversed(range(self.device_tab_layout.count())):
            widget = self.device_tab_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # 获取选中的设备
        device_id = current.data(Qt.UserRole)
        device = self.smart_home_system.device_manager.get_device(device_id)
        
        if device:
            # 根据设备类型创建相应的控制面板
            if device.type == DeviceType.LIGHT:
                control_panel = LightControlPanel(device)
            elif device.type == DeviceType.THERMOSTAT:
                control_panel = ThermostatControlPanel(device)
            else:
                control_panel = DeviceControlPanel(device)
            
            self.device_tab_layout.addWidget(control_panel)
    
    def setup_scene_tab(self):
        # 场景列表
        scene_group = QGroupBox("场景")
        scene_layout = QVBoxLayout()
        scene_group.setLayout(scene_layout)
        
        self.scene_list = QListWidget()
        scene_layout.addWidget(self.scene_list)
        
        # 更新场景列表
        for scene in self.smart_home_system.scenes.values():
            self.scene_list.addItem(scene.name)
        
        # 激活场景按钮
        activate_button = QPushButton("激活选中场景")
        activate_button.clicked.connect(self.activate_selected_scene)
        scene_layout.addWidget(activate_button)
        
        self.scene_tab_layout.addWidget(scene_group)
    
    def setup_automation_tab(self):
        # 自动化规则列表
        automation_group = QGroupBox("自动化规则")
        automation_layout = QVBoxLayout()
        automation_group.setLayout(automation_layout)
        
        self.automation_table = QTableWidget()
        self.automation_table.setColumnCount(4)
        self.automation_table.setHorizontalHeaderLabels(["规则名称", "状态", "触发次数", "最后触发"])
        self.automation_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        automation_layout.addWidget(self.automation_table)
        
        # 更新自动化规则表格
        self.update_automation_table()
        
        # 控制按钮
        button_layout = QHBoxLayout()
        enable_button = QPushButton("启用选中规则")
        enable_button.clicked.connect(self.enable_selected_rule)
        button_layout.addWidget(enable_button)
        
        disable_button = QPushButton("禁用选中规则")
        disable_button.clicked.connect(self.disable_selected_rule)
        button_layout.addWidget(disable_button)
        
        automation_layout.addLayout(button_layout)
        
        self.automation_tab_layout.addWidget(automation_group)
    
    def setup_analytics_tab(self):
        # 数据分析界面
        analytics_group = QGroupBox("设备数据分析")
        analytics_layout = QVBoxLayout()
        analytics_group.setLayout(analytics_layout)
        
        # 设备选择
        device_select_layout = QHBoxLayout()
        device_select_layout.addWidget(QLabel("选择设备:"))
        self.analytics_device_combo = QComboBox()
        device_select_layout.addWidget(self.analytics_device_combo)
        
        # 属性选择
        device_select_layout.addWidget(QLabel("属性:"))
        self.analytics_property_combo = QComboBox()
        device_select_layout.addWidget(self.analytics_property_combo)
        
        # 时间范围选择
        device_select_layout.addWidget(QLabel("时间范围:"))
        self.analytics_time_combo = QComboBox()
        self.analytics_time_combo.addItems(["最近1小时", "最近24小时", "最近7天", "最近30天"])
        device_select_layout.addWidget(self.analytics_time_combo)
        
        analytics_layout.addLayout(device_select_layout)
        
        # 更新设备列表
        self.update_analytics_device_list()
        
        # 图表视图
        self.analytics_chart_view = QChartView()
        self.analytics_chart_view.setRenderHint(QPainter.Antialiasing)
        analytics_layout.addWidget(self.analytics_chart_view)
        
        # 生成图表按钮
        generate_button = QPushButton("生成图表")
        generate_button.clicked.connect(self.generate_analytics_chart)
        analytics_layout.addWidget(generate_button)
        
        self.automation_tab_layout.addWidget(analytics_group)
    
    def update_analytics_device_list(self):
        self.analytics_device_combo.clear()
        devices = self.smart_home_system.device_manager.get_all_devices()
        for device in devices:
            self.analytics_device_combo.addItem(device.name, device.device_id)
        
        # 默认选择第一个设备
        if devices:
            self.on_analytics_device_changed(0)
    
    def on_analytics_device_changed(self, index):
        device_id = self.analytics_device_combo.currentData()
        device = self.smart_home_system.device_manager.get_device(device_id)
        
        if device and device.state:
            self.analytics_property_combo.clear()
            # 获取设备状态的所有属性
            properties = [attr for attr in dir(device.state) 
                         if not attr.startswith('_') and not callable(getattr(device.state, attr))]
            self.analytics_property_combo.addItems(properties)
    
    def generate_analytics_chart(self):
        device_id = self.analytics_device_combo.currentData()
        property_name = self.analytics_property_combo.currentText()
        time_range = self.analytics_time_combo.currentText()
        
        # 计算时间范围
        end_time = datetime.now()
        if time_range == "最近1小时":
            start_time = end_time - timedelta(hours=1)
        elif time_range == "最近24小时":
            start_time = end_time - timedelta(days=1)
        elif time_range == "最近7天":
            start_time = end_time - timedelta(days=7)
        else:  # 最近30天
            start_time = end_time - timedelta(days=30)
        
        # 获取历史数据
        history = self.smart_home_system.data_logger.get_device_history(
            device_id, property_name, start_time, end_time
        )
        
        if not history:
            QMessageBox.information(self, "无数据", "选定时间段内没有数据")
            return
        
        # 创建图表
        chart = QChart()
        chart.setTitle(f"{self.analytics_device_combo.currentText()} - {property_name}")
        
        # 创建序列
        series = QLineSeries()
        
        for timestamp_str, value_str in history:
            timestamp = datetime.fromisoformat(timestamp_str)
            value = float(value_str) if value_str.replace('.', '').isdigit() else 0
            
            # 将时间戳转换为毫秒
            ms_timestamp = timestamp.timestamp() * 1000
            series.append(ms_timestamp, value)
        
        chart.addSeries(series)
        
        # 创建坐标轴
        axis_x = QDateTimeAxis()
        axis_x.setFormat("MM-dd hh:mm")
        axis_x.setTitleText("时间")
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setTitleText(property_name)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
        
        # 设置图表视图
        self.analytics_chart_view.setChart(chart)
    
    def activate_selected_scene(self):
        current_row = self.scene_list.currentRow()
        if current_row >= 0:
            scene_id = list(self.smart_home_system.scenes.keys())[current_row]
            self.smart_home_system.activate_scene(scene_id)
            QMessageBox.information(self, "场景激活", "场景已激活")
    
    def update_automation_table(self):
        self.automation_table.setRowCount(len(self.smart_home_system.automation_rules))
        
        for row, rule in enumerate(self.smart_home_system.automation_rules.values()):
            self.automation_table.setItem(row, 0, QTableWidgetItem(rule.name))
            
            status_item = QTableWidgetItem("启用" if rule.enabled else "禁用")
            status_item.setData(Qt.UserRole, rule.rule_id)
            self.automation_table.setItem(row, 1, status_item)
            
            self.automation_table.setItem(row, 2, QTableWidgetItem(str(rule.trigger_count)))
            
            last_triggered = rule.last_triggered.strftime("%Y-%m-%d %H:%M") if rule.last_triggered else "从未"
            self.automation_table.setItem(row, 3, QTableWidgetItem(last_triggered))
    
    def enable_selected_rule(self):
        current_row = self.automation_table.currentRow()
        if current_row >= 0:
            rule_id = self.automation_table.item(current_row, 1).data(Qt.UserRole)
            rule = self.smart_home_system.automation_rules.get(rule_id)
            if rule:
                rule.enabled = True
                self.update_automation_table()
    
    def disable_selected_rule(self):
        current_row = self.automation_table.currentRow()
        if current_row >= 0:
            rule_id = self.automation_table.item(current_row, 1).data(Qt.UserRole)
            rule = self.smart_home_system.automation_rules.get(rule_id)
            if rule:
                rule.enabled = False
                self.update_automation_table()


# 应用启动
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = SmartHomeMainWindow()
    window.show()
    
    sys.exit(app.exec_())