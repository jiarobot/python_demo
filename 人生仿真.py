import sys
import json
import random
import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from PyQt5.QtWidgets import (QApplication, QListWidgetItem, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QPushButton, QLabel, 
                             QListWidget, QTextEdit, QLineEdit, QSpinBox,
                             QDoubleSpinBox, QComboBox, QGroupBox, QFormLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QSplitter, QProgressBar, QTreeWidget,
                             QTreeWidgetItem, QCheckBox, QDateEdit, QTimeEdit)
from PyQt5.QtCore import QTimer, QDateTime, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor


# ==================== 枚举定义 ====================
class Gender(Enum):
    MALE = "男"
    FEMALE = "女"

class EducationLevel(Enum):
    PRIMARY = "小学"
    JUNIOR = "初中"
    SENIOR = "高中"
    COLLEGE = "大学"
    MASTER = "硕士"
    DOCTOR = "博士"

class HealthStatus(Enum):
    EXCELLENT = "优秀"
    GOOD = "良好"
    FAIR = "一般"
    POOR = "较差"
    CRITICAL = "危重"

class RelationshipType(Enum):
    FAMILY = "家人"
    FRIEND = "朋友"
    COLLEAGUE = "同事"
    PARTNER = "伴侣"
    ACQUAINTANCE = "熟人"


# ==================== 基础类定义 ====================
class Person:
    """人物类"""
    def __init__(self, name: str, age: int, gender: Gender):
        self.id = random.randint(1000, 9999)
        self.name = name
        self.age = age
        self.gender = gender
        self.birth_date = QDateTime.currentDateTime().addYears(-age)
        self.health = HealthStatus.GOOD
        self.education = EducationLevel.PRIMARY
        self.occupation = ""
        self.income = 0
        self.savings = 0
        self.happiness = 75
        self.stress = 25
        self.skills = {}
        self.relationships = {}
        self.location = "家"
        self.created_at = QDateTime.currentDateTime()
        
    def to_dict(self) -> Dict[str, Any]:
        """将人物对象转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender.value,
            "birth_date": self.birth_date.toString("yyyy-MM-dd"),
            "health": self.health.value,
            "education": self.education.value,
            "occupation": self.occupation,
            "income": self.income,
            "savings": self.savings,
            "happiness": self.happiness,
            "stress": self.stress,
            "skills": self.skills,
            "relationships": {k: v.to_dict() for k, v in self.relationships.items()},
            "location": self.location,
            "created_at": self.created_at.toString("yyyy-MM-dd hh:mm:ss")
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Person':
        """从字典创建人物对象"""
        person = cls(data["name"], data["age"], Gender(data["gender"]))
        person.id = data["id"]
        person.birth_date = QDateTime.fromString(data["birth_date"], "yyyy-MM-dd")
        person.health = HealthStatus(data["health"])
        person.education = EducationLevel(data["education"])
        person.occupation = data["occupation"]
        person.income = data["income"]
        person.savings = data["savings"]
        person.happiness = data["happiness"]
        person.stress = data["stress"]
        person.skills = data["skills"]
        person.location = data["location"]
        person.created_at = QDateTime.fromString(data["created_at"], "yyyy-MM-dd hh:mm:ss")
        return person


class Relationship:
    """人际关系类"""
    def __init__(self, person_id: int, relationship_type: RelationshipType, closeness: int = 50):
        self.person_id = person_id
        self.type = relationship_type
        self.closeness = closeness  # 0-100，表示关系亲密程度
        self.last_interaction = QDateTime.currentDateTime()
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "person_id": self.person_id,
            "type": self.type.value,
            "closeness": self.closeness,
            "last_interaction": self.last_interaction.toString("yyyy-MM-dd hh:mm:ss")
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        relationship = cls(data["person_id"], RelationshipType(data["type"]), data["closeness"])
        relationship.last_interaction = QDateTime.fromString(data["last_interaction"], "yyyy-MM-dd hh:mm:ss")
        return relationship


class Event:
    """事件类"""
    def __init__(self, title: str, description: str, participants: List[int], 
                 start_time: QDateTime, duration_hours: int = 1):
        self.id = random.randint(10000, 99999)
        self.title = title
        self.description = description
        self.participants = participants
        self.start_time = start_time
        self.duration_hours = duration_hours
        self.end_time = start_time.addSecs(duration_hours * 3600)
        self.is_completed = False
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "participants": self.participants,
            "start_time": self.start_time.toString("yyyy-MM-dd hh:mm:ss"),
            "duration_hours": self.duration_hours,
            "is_completed": self.is_completed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        event = cls(
            data["title"], 
            data["description"], 
            data["participants"],
            QDateTime.fromString(data["start_time"], "yyyy-MM-dd hh:mm:ss"),
            data["duration_hours"]
        )
        event.id = data["id"]
        event.is_completed = data["is_completed"]
        return event


# ==================== 系统管理类 ====================
class PersonManager:
    """人物管理器"""
    def __init__(self):
        self.people = {}  # id -> Person
        self.next_person_id = 1000
        
    def add_person(self, person: Person) -> int:
        """添加人物"""
        if person.id in self.people:
            person.id = self.next_person_id
            self.next_person_id += 1
        
        self.people[person.id] = person
        return person.id
    
    def remove_person(self, person_id: int) -> bool:
        """移除人物"""
        if person_id in self.people:
            # 从其他人物的关系中移除该人物
            for person in self.people.values():
                if person_id in person.relationships:
                    del person.relationships[person_id]
            
            del self.people[person_id]
            return True
        return False
    
    def get_person(self, person_id: int) -> Optional[Person]:
        """获取人物"""
        return self.people.get(person_id)
    
    def get_all_people(self) -> List[Person]:
        """获取所有人物"""
        return list(self.people.values())
    
    def add_relationship(self, person1_id: int, person2_id: int, 
                        relationship_type: RelationshipType) -> bool:
        """添加关系"""
        if person1_id not in self.people or person2_id not in self.people:
            return False
        
        person1 = self.people[person1_id]
        person2 = self.people[person2_id]
        
        person1.relationships[person2_id] = Relationship(person2_id, relationship_type)
        person2.relationships[person1_id] = Relationship(person1_id, relationship_type)
        
        return True
    
    def save_to_file(self, filename: str) -> bool:
        """保存到文件"""
        try:
            data = {
                "people": {str(k): v.to_dict() for k, v in self.people.items()},
                "next_person_id": self.next_person_id
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            return False
    
    def load_from_file(self, filename: str) -> bool:
        """从文件加载"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.people = {}
            for k, v in data["people"].items():
                person = Person.from_dict(v)
                self.people[person.id] = person
            
            # 重建关系对象
            for person in self.people.values():
                for rel_data in person.relationships.values():
                    relationship = Relationship.from_dict(rel_data)
                    person.relationships[relationship.person_id] = relationship
            
            self.next_person_id = data.get("next_person_id", 1000)
            return True
        except Exception as e:
            print(f"加载失败: {e}")
            return False


class TimeSystem:
    """时间系统"""
    def __init__(self):
        self.current_time = QDateTime.currentDateTime()
        self.time_scale = 1  # 时间流速倍数
        self.is_paused = False
        self.day_counter = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)  # 每秒触发一次
        
    def tick(self):
        """时间推进"""
        if not self.is_paused:
            self.current_time = self.current_time.addSecs(3600 * self.time_scale)
            self.day_counter += self.time_scale / 24
            
    def set_time_scale(self, scale: float):
        """设置时间流速"""
        self.time_scale = max(0.1, min(scale, 100))  # 限制在0.1-100倍之间
    
    def pause(self):
        """暂停时间"""
        self.is_paused = True
    
    def resume(self):
        """恢复时间"""
        self.is_paused = False
    
    def get_formatted_time(self) -> str:
        """获取格式化时间"""
        return self.current_time.toString("yyyy年MM月dd日 hh:mm:ss")


class EventManager:
    """事件管理器"""
    def __init__(self, person_manager: PersonManager, time_system: TimeSystem):
        self.person_manager = person_manager
        self.time_system = time_system
        self.events = {}  # id -> Event
        self.completed_events = []
        
    def add_event(self, event: Event) -> int:
        """添加事件"""
        self.events[event.id] = event
        return event.id
    
    def remove_event(self, event_id: int) -> bool:
        """移除事件"""
        if event_id in self.events:
            del self.events[event_id]
            return True
        return False
    
    def get_upcoming_events(self, hours: int = 24) -> List[Event]:
        """获取即将发生的事件"""
        now = self.time_system.current_time
        future = now.addSecs(hours * 3600)
        
        upcoming = []
        for event in self.events.values():
            if not event.is_completed and event.start_time >= now and event.start_time <= future:
                upcoming.append(event)
        
        return sorted(upcoming, key=lambda e: e.start_time)
    
    def check_event_completion(self):
        """检查事件完成状态"""
        now = self.time_system.current_time
        completed = []
        
        for event_id, event in self.events.items():
            if not event.is_completed and now >= event.end_time:
                event.is_completed = True
                completed.append(event)
                self.completed_events.append(event)
        
        # 从当前事件列表中移除已完成事件
        for event in completed:
            del self.events[event.id]
        
        return completed


class EconomySystem:
    """经济系统"""
    def __init__(self, person_manager: PersonManager):
        self.person_manager = person_manager
        self.inflation_rate = 0.02  # 年通货膨胀率
        self.market_fluctuation = 0.05  # 市场波动率
        
    def process_daily_economy(self):
        """处理日常经济"""
        for person in self.person_manager.get_all_people():
            # 收入处理（假设有工作的人每天获得收入）
            if person.occupation:
                daily_income = person.income / 30  # 按月收入计算日收入
                person.savings += daily_income * (1 + random.uniform(-0.1, 0.1))  # 加入随机波动
            
            # 日常开销（基于收入水平）
            daily_expense = person.income / 100  # 假设日开销为月收入的1/100
            person.savings -= daily_expense * (1 + random.uniform(-0.2, 0.2))
            
            # 确保储蓄不为负（简化处理）
            person.savings = max(0, person.savings)


# ==================== 界面组件 ====================
class PersonEditor(QWidget):
    """人物编辑器"""
    def __init__(self, person_manager: PersonManager):
        super().__init__()
        self.person_manager = person_manager
        self.current_person = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 基本信息组
        info_group = QGroupBox("基本信息")
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.age_spin = QSpinBox()
        self.age_spin.setRange(0, 150)
        self.gender_combo = QComboBox()
        self.gender_combo.addItems([g.value for g in Gender])
        
        form_layout.addRow("姓名:", self.name_edit)
        form_layout.addRow("年龄:", self.age_spin)
        form_layout.addRow("性别:", self.gender_combo)
        
        info_group.setLayout(form_layout)
        layout.addWidget(info_group)
        
        # 状态组
        status_group = QGroupBox("状态信息")
        status_layout = QFormLayout()
        
        self.health_combo = QComboBox()
        self.health_combo.addItems([h.value for h in HealthStatus])
        self.education_combo = QComboBox()
        self.education_combo.addItems([e.value for e in EducationLevel])
        self.occupation_edit = QLineEdit()
        self.income_spin = QDoubleSpinBox()
        self.income_spin.setRange(0, 1000000)
        self.income_spin.setSuffix(" 元/月")
        self.savings_spin = QDoubleSpinBox()
        self.savings_spin.setRange(0, 10000000)
        self.savings_spin.setSuffix(" 元")
        
        status_layout.addRow("健康状况:", self.health_combo)
        status_layout.addRow("教育程度:", self.education_combo)
        status_layout.addRow("职业:", self.occupation_edit)
        status_layout.addRow("收入:", self.income_spin)
        status_layout.addRow("储蓄:", self.savings_spin)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 情绪状态
        emotion_group = QGroupBox("情绪状态")
        emotion_layout = QVBoxLayout()
        
        happiness_layout = QHBoxLayout()
        happiness_layout.addWidget(QLabel("幸福度:"))
        self.happiness_bar = QProgressBar()
        self.happiness_bar.setRange(0, 100)
        happiness_layout.addWidget(self.happiness_bar)
        emotion_layout.addLayout(happiness_layout)
        
        stress_layout = QHBoxLayout()
        stress_layout.addWidget(QLabel("压力值:"))
        self.stress_bar = QProgressBar()
        self.stress_bar.setRange(0, 100)
        stress_layout.addWidget(self.stress_bar)
        emotion_layout.addLayout(stress_layout)
        
        emotion_group.setLayout(emotion_layout)
        layout.addWidget(emotion_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.new_btn = QPushButton("新建")
        self.delete_btn = QPushButton("删除")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.new_btn)
        button_layout.addWidget(self.delete_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 连接信号
        self.save_btn.clicked.connect(self.save_person)
        self.new_btn.clicked.connect(self.new_person)
        self.delete_btn.clicked.connect(self.delete_person)
        
    def load_person(self, person: Person):
        """加载人物数据到编辑器"""
        self.current_person = person
        
        self.name_edit.setText(person.name)
        self.age_spin.setValue(person.age)
        self.gender_combo.setCurrentText(person.gender.value)
        self.health_combo.setCurrentText(person.health.value)
        self.education_combo.setCurrentText(person.education.value)
        self.occupation_edit.setText(person.occupation)
        self.income_spin.setValue(person.income)
        self.savings_spin.setValue(person.savings)
        
        self.happiness_bar.setValue(person.happiness)
        self.stress_bar.setValue(person.stress)
        
    def save_person(self):
        """保存人物数据"""
        if not self.current_person:
            return
            
        self.current_person.name = self.name_edit.text()
        self.current_person.age = self.age_spin.value()
        self.current_person.gender = Gender(self.gender_combo.currentText())
        self.current_person.health = HealthStatus(self.health_combo.currentText())
        self.current_person.education = EducationLevel(self.education_combo.currentText())
        self.current_person.occupation = self.occupation_edit.text()
        self.current_person.income = self.income_spin.value()
        self.current_person.savings = self.savings_spin.value()
        
        QMessageBox.information(self, "成功", f"已保存 {self.current_person.name} 的信息")
        
    def new_person(self):
        """创建新人物"""
        person = Person("新人物", 20, Gender.MALE)
        self.person_manager.add_person(person)
        self.load_person(person)
        
    def delete_person(self):
        """删除当前人物"""
        if not self.current_person:
            return
            
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除 {self.current_person.name} 吗？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.person_manager.remove_person(self.current_person.id)
            self.current_person = None
            self.clear_editor()
            
    def clear_editor(self):
        """清空编辑器"""
        self.name_edit.clear()
        self.age_spin.setValue(20)
        self.gender_combo.setCurrentIndex(0)
        self.health_combo.setCurrentIndex(0)
        self.education_combo.setCurrentIndex(0)
        self.occupation_edit.clear()
        self.income_spin.setValue(0)
        self.savings_spin.setValue(0)
        self.happiness_bar.setValue(75)
        self.stress_bar.setValue(25)


class EventPlanner(QWidget):
    """事件计划器"""
    def __init__(self, event_manager: EventManager, person_manager: PersonManager):
        super().__init__()
        self.event_manager = event_manager
        self.person_manager = person_manager
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 事件创建表单
        form_group = QGroupBox("创建新事件")
        form_layout = QFormLayout()
        
        self.event_title = QLineEdit()
        self.event_description = QTextEdit()
        self.event_description.setMaximumHeight(100)
        self.event_date = QDateEdit()
        self.event_date.setDate(QDateTime.currentDateTime().date())
        self.event_time = QTimeEdit()
        self.event_time.setTime(QDateTime.currentDateTime().time())
        self.event_duration = QSpinBox()
        self.event_duration.setRange(1, 24)
        self.event_duration.setSuffix(" 小时")
        
        self.participants_list = QListWidget()
        self.update_participants_list()
        
        form_layout.addRow("事件标题:", self.event_title)
        form_layout.addRow("事件描述:", self.event_description)
        form_layout.addRow("日期:", self.event_date)
        form_layout.addRow("时间:", self.event_time)
        form_layout.addRow("持续时间:", self.event_duration)
        form_layout.addRow("参与者:", self.participants_list)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.create_btn = QPushButton("创建事件")
        self.clear_btn = QPushButton("清空表单")
        
        button_layout.addWidget(self.create_btn)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # 即将发生的事件
        upcoming_group = QGroupBox("即将发生的事件 (24小时内)")
        upcoming_layout = QVBoxLayout()
        
        self.upcoming_events = QListWidget()
        upcoming_layout.addWidget(self.upcoming_events)
        
        upcoming_group.setLayout(upcoming_layout)
        layout.addWidget(upcoming_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.create_btn.clicked.connect(self.create_event)
        self.clear_btn.clicked.connect(self.clear_form)
        
        # 定时更新事件列表
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_upcoming_events)
        self.update_timer.start(5000)  # 每5秒更新一次
        
        self.update_upcoming_events()
        
    def update_participants_list(self):
        """更新参与者列表"""
        self.participants_list.clear()
        for person in self.person_manager.get_all_people():
            item = QListWidgetItem(f"{person.name} (ID: {person.id})")
            item.setData(Qt.UserRole, person.id)
            self.participants_list.addItem(item)
            
    def create_event(self):
        """创建新事件"""
        title = self.event_title.text().strip()
        if not title:
            QMessageBox.warning(self, "错误", "请输入事件标题")
            return
            
        selected_items = self.participants_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "错误", "请选择至少一个参与者")
            return
            
        participants = [item.data(Qt.UserRole) for item in selected_items]
        
        start_time = QDateTime(self.event_date.date(), self.event_time.time())
        duration = self.event_duration.value()
        
        event = Event(title, self.event_description.toPlainText(), 
                     participants, start_time, duration)
        
        self.event_manager.add_event(event)
        QMessageBox.information(self, "成功", f"已创建事件: {title}")
        self.clear_form()
        self.update_upcoming_events()
        
    def clear_form(self):
        """清空表单"""
        self.event_title.clear()
        self.event_description.clear()
        self.event_date.setDate(QDateTime.currentDateTime().date())
        self.event_time.setTime(QDateTime.currentDateTime().time())
        self.event_duration.setValue(1)
        self.participants_list.clearSelection()
        
    def update_upcoming_events(self):
        """更新即将发生的事件列表"""
        self.upcoming_events.clear()
        upcoming = self.event_manager.get_upcoming_events(24)
        
        for event in upcoming:
            participants_names = []
            for pid in event.participants:
                person = self.person_manager.get_person(pid)
                if person:
                    participants_names.append(person.name)
            
            item_text = f"{event.start_time.toString('MM/dd hh:mm')} - {event.title} ({', '.join(participants_names)})"
            item = QListWidgetItem(item_text)
            self.upcoming_events.addItem(item)


class Dashboard(QWidget):
    """系统仪表板"""
    def __init__(self, person_manager: PersonManager, time_system: TimeSystem, 
                 event_manager: EventManager, economy_system: EconomySystem):
        super().__init__()
        self.person_manager = person_manager
        self.time_system = time_system
        self.event_manager = event_manager
        self.economy_system = economy_system
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 时间控制
        time_group = QGroupBox("时间控制")
        time_layout = QHBoxLayout()
        
        self.time_label = QLabel(self.time_system.get_formatted_time())
        self.time_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        self.pause_btn = QPushButton("暂停")
        self.resume_btn = QPushButton("继续")
        self.speed_slider = QSpinBox()
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(int(self.time_system.time_scale))
        self.speed_slider.setSuffix("x")
        
        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.pause_btn)
        time_layout.addWidget(self.resume_btn)
        time_layout.addWidget(QLabel("时间流速:"))
        time_layout.addWidget(self.speed_slider)
        
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)
        
        # 统计信息
        stats_group = QGroupBox("系统统计")
        stats_layout = QHBoxLayout()
        
        self.people_count = QLabel("0")
        self.people_count.setFont(QFont("Arial", 18, QFont.Bold))
        
        self.events_count = QLabel("0")
        self.events_count.setFont(QFont("Arial", 18, QFont.Bold))
        
        self.avg_happiness = QProgressBar()
        self.avg_happiness.setRange(0, 100)
        
        stats_layout.addWidget(QLabel("总人口:"))
        stats_layout.addWidget(self.people_count)
        stats_layout.addWidget(QLabel("活跃事件:"))
        stats_layout.addWidget(self.events_count)
        stats_layout.addWidget(QLabel("平均幸福度:"))
        stats_layout.addWidget(self.avg_happiness)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 系统日志
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.pause_btn.clicked.connect(self.time_system.pause)
        self.resume_btn.clicked.connect(self.time_system.resume)
        self.speed_slider.valueChanged.connect(self.time_system.set_time_scale)
        
        # 定时更新
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_dashboard)
        self.update_timer.start(1000)  # 每秒更新一次
        
        self.update_dashboard()
        
    def update_dashboard(self):
        """更新仪表板数据"""
        # 更新时间
        self.time_label.setText(self.time_system.get_formatted_time())
        
        # 更新统计
        people = self.person_manager.get_all_people()
        self.people_count.setText(str(len(people)))
        
        events = len(self.event_manager.events)
        self.events_count.setText(str(events))
        
        # 计算平均幸福度
        if people:
            avg_happiness = sum(p.happiness for p in people) / len(people)
            self.avg_happiness.setValue(int(avg_happiness))
        else:
            self.avg_happiness.setValue(0)
        
        # 检查并记录已完成事件
        completed_events = self.event_manager.check_event_completion()
        for event in completed_events:
            self.log_text.append(f"[{self.time_system.get_formatted_time()}] 事件完成: {event.title}")
            
    def add_log(self, message: str):
        """添加日志消息"""
        timestamp = self.time_system.get_formatted_time()
        self.log_text.append(f"[{timestamp}] {message}")


# ==================== 主窗口 ====================
class LifeSimulationSystem(QMainWindow):
    """人生高仿真系统主窗口"""
    def __init__(self):
        super().__init__()
        
        # 初始化系统组件
        self.person_manager = PersonManager()
        self.time_system = TimeSystem()
        self.event_manager = EventManager(self.person_manager, self.time_system)
        self.economy_system = EconomySystem(self.person_manager)
        
        # 创建示例数据
        self.create_sample_data()
        
        # 设置UI
        self.init_ui()
        self.setWindowTitle("人生高仿真系统")
        self.setGeometry(100, 100, 1200, 800)
        
    def create_sample_data(self):
        """创建示例数据"""
        # 创建示例人物
        person1 = Person("张三", 25, Gender.MALE)
        person1.occupation = "软件工程师"
        person1.income = 15000
        person1.savings = 50000
        person1.education = EducationLevel.COLLEGE
        self.person_manager.add_person(person1)
        
        person2 = Person("李四", 28, Gender.FEMALE)
        person2.occupation = "医生"
        person2.income = 20000
        person2.savings = 80000
        person2.education = EducationLevel.MASTER
        self.person_manager.add_person(person2)
        
        person3 = Person("王五", 22, Gender.MALE)
        person3.occupation = "学生"
        person3.income = 2000
        person3.savings = 5000
        person3.education = EducationLevel.SENIOR
        self.person_manager.add_person(person3)
        
        # 创建关系
        self.person_manager.add_relationship(person1.id, person2.id, RelationshipType.FRIEND)
        self.person_manager.add_relationship(person1.id, person3.id, RelationshipType.FAMILY)
        
        # 创建示例事件
        event_time = QDateTime.currentDateTime().addSecs(3600)  # 1小时后
        event = Event("团队会议", "每周团队例会", [person1.id, person2.id], event_time, 2)
        self.event_manager.add_event(event)
        
    def init_ui(self):
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧面板 - 人物列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.people_list = QListWidget()
        self.update_people_list()
        
        left_layout.addWidget(QLabel("人物列表"))
        left_layout.addWidget(self.people_list)
        
        splitter.addWidget(left_panel)
        
        # 右侧面板 - 标签页
        right_panel = QTabWidget()
        
        # 仪表板标签页
        self.dashboard = Dashboard(self.person_manager, self.time_system, 
                                  self.event_manager, self.economy_system)
        right_panel.addTab(self.dashboard, "仪表板")
        
        # 人物编辑器标签页
        self.person_editor = PersonEditor(self.person_manager)
        right_panel.addTab(self.person_editor, "人物编辑")
        
        # 事件计划器标签页
        self.event_planner = EventPlanner(self.event_manager, self.person_manager)
        right_panel.addTab(self.event_planner, "事件计划")
        
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setSizes([200, 1000])
        
        main_layout.addWidget(splitter)
        
        # 连接信号
        self.people_list.currentRowChanged.connect(self.on_person_selected)
        
        # 创建菜单栏
        self.create_menu_bar()
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        save_action = file_menu.addAction('保存系统')
        save_action.triggered.connect(self.save_system)
        
        load_action = file_menu.addAction('加载系统')
        load_action.triggered.connect(self.load_system)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('退出')
        exit_action.triggered.connect(self.close)
        
        # 工具菜单
        tool_menu = menubar.addMenu('工具')
        
        add_sample_action = tool_menu.addAction('添加示例数据')
        add_sample_action.triggered.connect(self.create_sample_data)
        
        process_day_action = tool_menu.addAction('模拟一天')
        process_day_action.triggered.connect(self.simulate_one_day)
        
    def update_people_list(self):
        """更新人物列表"""
        self.people_list.clear()
        for person in self.person_manager.get_all_people():
            item_text = f"{person.name} ({person.age}岁, {person.occupation})"
            self.people_list.addItem(item_text)
            
    def on_person_selected(self, index):
        """当选择人物时"""
        if index >= 0:
            person = self.person_manager.get_all_people()[index]
            self.person_editor.load_person(person)
            
    def save_system(self):
        """保存系统状态"""
        filename = "life_simulation_save.json"
        if self.person_manager.save_to_file(filename):
            QMessageBox.information(self, "成功", f"系统已保存到 {filename}")
        else:
            QMessageBox.warning(self, "错误", "保存系统失败")
            
    def load_system(self):
        """加载系统状态"""
        filename = "life_simulation_save.json"
        if self.person_manager.load_from_file(filename):
            self.update_people_list()
            QMessageBox.information(self, "成功", f"已从 {filename} 加载系统")
        else:
            QMessageBox.warning(self, "错误", "加载系统失败")
            
    def simulate_one_day(self):
        """模拟一天"""
        # 处理经济系统
        self.economy_system.process_daily_economy()
        
        # 更新人物状态（简化处理）
        for person in self.person_manager.get_all_people():
            # 随机变化幸福度和压力
            person.happiness += random.randint(-5, 5)
            person.happiness = max(0, min(100, person.happiness))
            
            person.stress += random.randint(-5, 5)
            person.stress = max(0, min(100, person.stress))
            
            # 年龄增长（每年一次）
            if self.time_system.day_counter >= 365:
                person.age += 1
                self.time_system.day_counter = 0
        
        self.dashboard.add_log("模拟了一天的时间流逝")
        self.update_people_list()


# ==================== 应用程序入口 ====================
def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = LifeSimulationSystem()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()