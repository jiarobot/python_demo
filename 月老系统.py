import sys
import sqlite3
import random
import json
import math
import os
from PyQt5.QtCore import QDate
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTextEdit, QListWidget, QTableWidget, QTableWidgetItem,
                             QTabWidget, QSplitter, QMessageBox, QProgressBar,
                             QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QGroupBox, QFormLayout, QCalendarWidget, QHeaderView,
                             QDialog, QDialogButtonBox, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon

# ==================== 数据库管理类 ====================
class DatabaseManager:
    def __init__(self, db_name="yuelao_system.db"):
        self.db_name = db_name
        self.init_database()
    
    def get_user_by_id(self, user_id):
        """根据ID获取用户信息"""
        query = "SELECT * FROM users WHERE id = ?"
        result = self.execute_query(query, (user_id,))
        if result:
            columns = [col[0] for col in self.execute_query("PRAGMA table_info(users)")]
            return dict(zip(columns, result[0]))
        return None
    
    def update_last_login(self, user_id):
        """更新用户最后登录时间"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.execute_update("UPDATE users SET last_login = ? WHERE id = ?", (current_time, user_id))

    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                height REAL,
                weight REAL,
                education TEXT,
                occupation TEXT,
                income INTEGER,
                hobbies TEXT,
                personality TEXT,
                location TEXT,
                bio TEXT,
                preferences TEXT,
                registration_date TEXT,
                last_login TEXT,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # 匹配记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER,
                user2_id INTEGER,
                match_score REAL,
                match_date TEXT,
                status TEXT,
                FOREIGN KEY (user1_id) REFERENCES users (id),
                FOREIGN KEY (user2_id) REFERENCES users (id)
            )
        ''')
        
        # 聊天记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER,
                user2_id INTEGER,
                message TEXT,
                sender_id INTEGER,
                timestamp TEXT,
                FOREIGN KEY (user1_id) REFERENCES users (id),
                FOREIGN KEY (user2_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=()):
        """执行查询并返回结果"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.close()
        return result
    
    def execute_update(self, query, params=()):
        """执行更新操作"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()

# ==================== 登录对话框 ====================
class LoginDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_id = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("用户登录")
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout()
        
        # 用户选择
        layout.addWidget(QLabel("选择用户:"))
        self.user_combo = QComboBox()
        self.load_users()
        layout.addWidget(self.user_combo)
        
        # 或创建新用户
        layout.addWidget(QLabel("或创建新用户:"))
        new_user_btn = QPushButton("创建新用户")
        new_user_btn.clicked.connect(self.create_new_user)
        layout.addWidget(new_user_btn)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_login)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_users(self):
        """加载用户列表"""
        users = self.db_manager.execute_query("SELECT id, name FROM users WHERE status = 'active'")
        self.user_combo.clear()
        for user_id, name in users:
            self.user_combo.addItem(f"{name} (ID: {user_id})", user_id)
    
    def create_new_user(self):
        """创建新用户"""
        name, ok = QInputDialog.getText(self, "创建用户", "请输入用户名:")
        if ok and name:
            # 简单创建用户，实际应用中需要更多信息
            age = 25
            gender = "男"
            registration_date = datetime.now().strftime("%Y-%m-%d")
            
            self.db_manager.execute_update(
                "INSERT INTO users (name, age, gender, registration_date) VALUES (?, ?, ?, ?)",
                (name, age, gender, registration_date)
            )
            
            # 获取新用户ID
            result = self.db_manager.execute_query("SELECT id FROM users WHERE name = ? ORDER BY id DESC LIMIT 1", (name,))
            if result:
                self.user_id = result[0][0]
                self.accept()
            
            self.load_users()  # 刷新用户列表
    
    def accept_login(self):
        """接受登录"""
        if self.user_combo.count() > 0:
            self.user_id = self.user_combo.currentData()
            # 更新最后登录时间
            self.db_manager.update_last_login(self.user_id)
            self.accept()
        else:
            QMessageBox.warning(self, "警告", "没有可用的用户，请先创建用户")

# ==================== 匹配算法类 ====================
class MatchAlgorithm:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def calculate_compatibility(self, user1, user2):
        """计算两个用户的兼容性分数（0-100）"""
        score = 0
        max_score = 100
        
        # 年龄兼容性 (权重: 20%)
        age_diff = abs(user1['age'] - user2['age'])
        if age_diff <= 5:
            age_score = 20
        elif age_diff <= 10:
            age_score = 15
        elif age_diff <= 15:
            age_score = 10
        else:
            age_score = 5
        score += age_score
        
        # 兴趣爱好匹配 (权重: 30%)
        hobbies1 = set(user1['hobbies'].split(',')) if user1.get('hobbies') else set()
        hobbies2 = set(user2['hobbies'].split(',')) if user2.get('hobbies') else set()
        if hobbies1 and hobbies2:
            common_hobbies = hobbies1.intersection(hobbies2)
            hobby_score = min(30, len(common_hobbies) * 5)
            score += hobby_score
        else:
            score += 15  # 默认分数
        
        # 教育背景匹配 (权重: 15%)
        if user1.get('education') and user2.get('education'):
            edu_levels = {"高中": 1, "大专": 2, "本科": 3, "硕士": 4, "博士": 5}
            edu1 = edu_levels.get(user1['education'], 0)
            edu2 = edu_levels.get(user2['education'], 0)
            edu_diff = abs(edu1 - edu2)
            edu_score = max(0, 15 - edu_diff * 3)
            score += edu_score
        else:
            score += 7  # 默认分数
        
        # 收入匹配 (权重: 15%)
        if user1.get('income') and user2.get('income'):
            income1 = user1['income'] or 0
            income2 = user2['income'] or 0
            if max(income1, income2) > 0:
                income_ratio = min(income1, income2) / max(income1, income2)
                income_score = income_ratio * 15
                score += income_score
            else:
                score += 7
        else:
            score += 7  # 默认分数
        
        # 地理位置匹配 (权重: 10%)
        if user1.get('location') and user2.get('location'):
            if user1['location'] == user2['location']:
                location_score = 10
            else:
                # 简单实现：同省得5分，不同省得2分
                loc1_parts = user1['location'].split('-')
                loc2_parts = user2['location'].split('-')
                if loc1_parts and loc2_parts and loc1_parts[0] == loc2_parts[0]:
                    location_score = 5
                else:
                    location_score = 2
            score += location_score
        else:
            score += 5  # 默认分数
        
        # 性格匹配 (权重: 10%)
        if user1.get('personality') and user2.get('personality'):
            # 简单实现：相同性格得10分，相似得7分，不同得3分
            personalities = ["内向", "外向", "理性", "感性", "稳重", "活泼"]
            p1 = user1['personality']
            p2 = user2['personality']
            if p1 == p2:
                personality_score = 10
            elif (p1 in ["内向", "外向"] and p2 in ["内向", "外向"]) or \
                 (p1 in ["理性", "感性"] and p2 in ["理性", "感性"]) or \
                 (p1 in ["稳重", "活泼"] and p2 in ["稳重", "活泼"]):
                personality_score = 7
            else:
                personality_score = 3
            score += personality_score
        else:
            score += 5  # 默认分数
        
        return min(score, max_score)
    
    def find_matches(self, user_id, limit=10):
        """为用户查找匹配对象"""
        # 获取当前用户信息
        user_query = "SELECT * FROM users WHERE id = ?"
        user_data = self.db_manager.execute_query(user_query, (user_id,))
        if not user_data:
            return []
        
        # 获取列名
        columns = [col[0] for col in self.db_manager.execute_query("PRAGMA table_info(users)")]
        user = dict(zip(columns, user_data[0]))
        
        # 获取所有其他活跃用户
        other_users_query = "SELECT * FROM users WHERE id != ? AND status = 'active'"
        other_users = self.db_manager.execute_query(other_users_query, (user_id,))
        
        matches = []
        for other_user in other_users:
            other_user_dict = dict(zip(columns, other_user))
            
            # 检查是否已有匹配记录
            existing_match = self.db_manager.execute_query(
                "SELECT * FROM matches WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)",
                (user_id, other_user_dict['id'], other_user_dict['id'], user_id)
            )
            
            if not existing_match:
                score = self.calculate_compatibility(user, other_user_dict)
                matches.append({
                    'user_id': other_user_dict['id'],
                    'name': other_user_dict['name'],
                    'age': other_user_dict['age'],
                    'gender': other_user_dict['gender'],
                    'score': score,
                    'bio': other_user_dict.get('bio', ''),
                    'occupation': other_user_dict.get('occupation', ''),
                    'location': other_user_dict.get('location', '')
                })
        
        # 按匹配分数排序并返回前limit个结果
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:limit]

    def record_match(self, user1_id, user2_id, score):
        """记录匹配结果"""
        match_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = """
            INSERT INTO matches (user1_id, user2_id, match_score, match_date, status)
            VALUES (?, ?, ?, ?, ?)
        """
        self.db_manager.execute_update(query, (user1_id, user2_id, score, match_date, 'pending'))

# ==================== 聊天管理器 ====================
class ChatManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def send_message(self, sender_id, receiver_id, message):
        """发送消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = """
            INSERT INTO chats (user1_id, user2_id, message, sender_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """
        # 确保user1_id是较小的ID，user2_id是较大的ID，以便统一存储
        user1_id = min(sender_id, receiver_id)
        user2_id = max(sender_id, receiver_id)
        
        self.db_manager.execute_update(query, (user1_id, user2_id, message, sender_id, timestamp))
    
    def get_chat_history(self, user1_id, user2_id):
        """获取两个用户之间的聊天记录"""
        # 确保user1_id是较小的ID，user2_id是较大的ID
        user1_id_sorted = min(user1_id, user2_id)
        user2_id_sorted = max(user1_id, user2_id)
        
        query = """
            SELECT * FROM chats 
            WHERE user1_id = ? AND user2_id = ?
            ORDER BY timestamp ASC
        """
        return self.db_manager.execute_query(query, (user1_id_sorted, user2_id_sorted))

# ==================== 数据分析类 ====================
class DataAnalyzer:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_user_stats(self):
        """获取用户统计信息"""
        total_users = self.db_manager.execute_query("SELECT COUNT(*) FROM users")[0][0]
        active_users = self.db_manager.execute_query("SELECT COUNT(*) FROM users WHERE status = 'active'")[0][0]
        male_users = self.db_manager.execute_query("SELECT COUNT(*) FROM users WHERE gender = '男'")[0][0]
        female_users = self.db_manager.execute_query("SELECT COUNT(*) FROM users WHERE gender = '女'")[0][0]
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'male_users': male_users,
            'female_users': female_users
        }
    
    def get_match_stats(self):
        """获取匹配统计信息"""
        total_matches = self.db_manager.execute_query("SELECT COUNT(*) FROM matches")[0][0]
        successful_matches = self.db_manager.execute_query("SELECT COUNT(*) FROM matches WHERE status = 'successful'")[0][0]
        avg_match_score = self.db_manager.execute_query("SELECT AVG(match_score) FROM matches")[0][0] or 0
        
        return {
            'total_matches': total_matches,
            'successful_matches': successful_matches,
            'avg_match_score': round(avg_match_score, 2)
        }
    
    def get_age_distribution(self):
        """获取年龄分布"""
        age_groups = {
            '18-25': 0,
            '26-35': 0,
            '36-45': 0,
            '46+': 0
        }
        
        users = self.db_manager.execute_query("SELECT age FROM users WHERE status = 'active'")
        for user in users:
            age = user[0]
            if 18 <= age <= 25:
                age_groups['18-25'] += 1
            elif 26 <= age <= 35:
                age_groups['26-35'] += 1
            elif 36 <= age <= 45:
                age_groups['36-45'] += 1
            elif age > 45:
                age_groups['46+'] += 1
        
        return age_groups

# ==================== 用户界面组件 ====================
class UserCardWidget(QWidget):
    """用户卡片组件"""
    def __init__(self, user_info, parent=None):
        super().__init__(parent)
        self.user_info = user_info
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 用户基本信息
        name = self.user_info.get('name', '未知用户')
        age = self.user_info.get('age', '未知')
        gender = self.user_info.get('gender', '未知')
        
        name_label = QLabel(f"姓名: {name}")
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        age_gender_label = QLabel(f"年龄: {age} | 性别: {gender}")
        
        layout.addWidget(name_label)
        layout.addWidget(age_gender_label)
        
        # 匹配分数
        if 'score' in self.user_info:
            score_label = QLabel(f"匹配度: {self.user_info['score']}%")
            score_label.setStyleSheet("color: green; font-weight: bold;")
            layout.addWidget(score_label)
        
        # 其他信息
        if self.user_info.get('occupation'):
            occupation_label = QLabel(f"职业: {self.user_info['occupation']}")
            layout.addWidget(occupation_label)
        
        if self.user_info.get('location'):
            location_label = QLabel(f"地点: {self.user_info['location']}")
            layout.addWidget(location_label)
        
        if self.user_info.get('bio'):
            bio_label = QLabel(f"简介: {self.user_info['bio']}")
            bio_label.setWordWrap(True)
            layout.addWidget(bio_label)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
                background-color: #f9f9f9;
            }
        """)

class MatchFinderWidget(QWidget):
    """匹配查找组件"""
    matchFound = pyqtSignal(dict)  # 匹配找到信号
    
    def __init__(self, db_manager, current_user_id, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user_id = current_user_id
        self.match_algorithm = MatchAlgorithm(db_manager)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("智能匹配推荐")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title_label)
        
        # 查找按钮
        find_button = QPushButton("查找匹配")
        find_button.clicked.connect(self.find_matches)
        layout.addWidget(find_button)
        
        # 匹配结果区域
        self.matches_layout = QVBoxLayout()
        matches_widget = QWidget()
        matches_widget.setLayout(self.matches_layout)
        
        layout.addWidget(matches_widget)
        self.setLayout(layout)
    
    def find_matches(self):
        """查找匹配"""
        # 清空现有结果
        for i in reversed(range(self.matches_layout.count())):
            widget = self.matches_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # 查找匹配
        matches = self.match_algorithm.find_matches(self.current_user_id)
        
        if not matches:
            no_match_label = QLabel("暂无匹配结果")
            self.matches_layout.addWidget(no_match_label)
            return
        
        for match in matches:
            match_card = UserCardWidget(match)
            self.matches_layout.addWidget(match_card)
            
            # 添加联系按钮
            contact_button = QPushButton("联系TA")
            contact_button.clicked.connect(lambda checked, m=match: self.contact_user(m))
            self.matches_layout.addWidget(contact_button)
    
    def contact_user(self, user_info):
        """联系用户"""
        # 记录匹配
        self.match_algorithm.record_match(self.current_user_id, user_info['user_id'], user_info['score'])
        self.matchFound.emit(user_info)

class ExportDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("导出数据")
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("选择导出内容:"))
        
        self.users_check = QCheckBox("用户数据")
        self.users_check.setChecked(True)
        layout.addWidget(self.users_check)
        
        self.matches_check = QCheckBox("匹配数据")
        self.matches_check.setChecked(True)
        layout.addWidget(self.matches_check)
        
        self.chats_check = QCheckBox("聊天记录")
        layout.addWidget(self.chats_check)
        
        export_button = QPushButton("导出数据")
        export_button.clicked.connect(self.export_data)
        layout.addWidget(export_button)
        
        self.setLayout(layout)
    
    def export_data(self):
        """导出数据到JSON文件"""
        data = {}
        
        if self.users_check.isChecked():
            users = self.db_manager.execute_query("SELECT * FROM users")
            columns = [col[0] for col in self.db_manager.execute_query("PRAGMA table_info(users)")]
            data['users'] = [dict(zip(columns, user)) for user in users]
        
        if self.matches_check.isChecked():
            matches = self.db_manager.execute_query("SELECT * FROM matches")
            columns = [col[0] for col in self.db_manager.execute_query("PRAGMA table_info(matches)")]
            data['matches'] = [dict(zip(columns, match)) for match in matches]
        
        if self.chats_check.isChecked():
            chats = self.db_manager.execute_query("SELECT * FROM chats")
            columns = [col[0] for col in self.db_manager.execute_query("PRAGMA table_info(chats)")]
            data['chats'] = [dict(zip(columns, chat)) for chat in chats]
        
        # 保存到文件
        filename = f"yuelao_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        QMessageBox.information(self, "导出成功", f"数据已导出到 {filename}")

class ChatWidget(QWidget):
    """聊天组件"""
    def __init__(self, db_manager, current_user_id, target_user_id, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user_id = current_user_id
        self.target_user_id = target_user_id
        self.chat_manager = ChatManager(db_manager)
        self.init_ui()
        self.load_chat_history()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 聊天记录显示区域
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)
        
        # 消息输入区域
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("输入消息...")
        self.message_input.returnPressed.connect(self.send_message)
        
        send_button = QPushButton("发送")
        send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_button)
        
        layout.addLayout(input_layout)
        self.setLayout(layout)
    
    def load_chat_history(self):
        """加载聊天记录"""
        self.chat_display.clear()
        history = self.chat_manager.get_chat_history(self.current_user_id, self.target_user_id)
        
        for message in history:
            # 解析消息记录
            msg_id, user1_id, user2_id, msg_text, sender_id, timestamp = message
            
            # 格式化显示
            try:
                time_str = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
            except:
                time_str = timestamp
            
            if sender_id == self.current_user_id:
                self.chat_display.append(f"[{time_str}] 我: {msg_text}")
            else:
                # 获取对方姓名
                user_info = self.db_manager.execute_query("SELECT name FROM users WHERE id = ?", (sender_id,))
                if user_info:
                    name = user_info[0][0]
                    self.chat_display.append(f"[{time_str}] {name}: {msg_text}")
        
        # 滚动到底部
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
    
    def send_message(self):
        """发送消息"""
        message = self.message_input.text().strip()
        if message:
            self.chat_manager.send_message(self.current_user_id, self.target_user_id, message)
            self.message_input.clear()
            self.load_chat_history()

class AnalyticsWidget(QWidget):
    """数据分析组件"""
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.data_analyzer = DataAnalyzer(db_manager)
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("系统数据分析")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title_label)
        
        # 数据统计区域
        stats_group = QGroupBox("基本统计")
        stats_layout = QFormLayout()
        
        self.user_stats_labels = {}
        stats_fields = [
            ("总用户数", "total_users"),
            ("活跃用户", "active_users"),
            ("男性用户", "male_users"),
            ("女性用户", "female_users")
        ]
        
        for label, key in stats_fields:
            value_label = QLabel("0")
            self.user_stats_labels[key] = value_label
            stats_layout.addRow(f"{label}:", value_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 匹配统计
        match_stats_group = QGroupBox("匹配统计")
        match_stats_layout = QFormLayout()
        
        self.match_stats_labels = {}
        match_fields = [
            ("总匹配数", "total_matches"),
            ("成功匹配", "successful_matches"),
            ("平均匹配度", "avg_match_score")
        ]
        
        for label, key in match_fields:
            value_label = QLabel("0")
            self.match_stats_labels[key] = value_label
            match_stats_layout.addRow(f"{label}:", value_label)
        
        match_stats_group.setLayout(match_stats_layout)
        layout.addWidget(match_stats_group)
        
        # 刷新按钮
        refresh_button = QPushButton("刷新数据")
        refresh_button.clicked.connect(self.load_data)
        layout.addWidget(refresh_button)
        
        self.setLayout(layout)
    
    def load_data(self):
        """加载数据"""
        # 用户统计
        user_stats = self.data_analyzer.get_user_stats()
        for key, label in self.user_stats_labels.items():
            label.setText(str(user_stats.get(key, 0)))
        
        # 匹配统计
        match_stats = self.data_analyzer.get_match_stats()
        for key, label in self.match_stats_labels.items():
            label.setText(str(match_stats.get(key, 0)))

# ==================== 用户信息编辑对话框 ====================
class UserEditDialog(QDialog):
    def __init__(self, user_info, db_manager, parent=None):
        super().__init__(parent)
        self.user_info = user_info
        self.db_manager = db_manager
        self.init_ui()
        self.load_user_data()
    
    def init_ui(self):
        self.setWindowTitle("编辑用户信息")
        self.setFixedSize(400, 500)
        
        layout = QVBoxLayout()
        
        # 基本信息表单
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        form_layout.addRow("姓名:", self.name_edit)
        
        self.age_spin = QSpinBox()
        self.age_spin.setRange(18, 100)
        form_layout.addRow("年龄:", self.age_spin)
        
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["男", "女"])
        form_layout.addRow("性别:", self.gender_combo)
        
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(100, 250)
        self.height_spin.setSuffix(" cm")
        form_layout.addRow("身高:", self.height_spin)
        
        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(30, 150)
        self.weight_spin.setSuffix(" kg")
        form_layout.addRow("体重:", self.weight_spin)
        
        self.education_combo = QComboBox()
        self.education_combo.addItems(["高中", "大专", "本科", "硕士", "博士"])
        form_layout.addRow("教育程度:", self.education_combo)
        
        self.occupation_edit = QLineEdit()
        form_layout.addRow("职业:", self.occupation_edit)
        
        self.income_spin = QSpinBox()
        self.income_spin.setRange(0, 100000)
        self.income_spin.setSuffix(" 元/月")
        form_layout.addRow("收入:", self.income_spin)
        
        self.hobbies_edit = QLineEdit()
        self.hobbies_edit.setPlaceholderText("多个爱好用逗号分隔")
        form_layout.addRow("兴趣爱好:", self.hobbies_edit)
        
        self.personality_combo = QComboBox()
        self.personality_combo.addItems(["内向", "外向", "理性", "感性", "稳重", "活泼"])
        form_layout.addRow("性格:", self.personality_combo)
        
        self.location_edit = QLineEdit()
        form_layout.addRow("所在地:", self.location_edit)
        
        self.bio_edit = QTextEdit()
        self.bio_edit.setMaximumHeight(80)
        form_layout.addRow("个人简介:", self.bio_edit)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_user_data)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_user_data(self):
        """加载用户数据到表单"""
        if self.user_info:
            self.name_edit.setText(self.user_info.get('name', ''))
            self.age_spin.setValue(self.user_info.get('age', 25))
            self.gender_combo.setCurrentText(self.user_info.get('gender', '男'))
            self.height_spin.setValue(self.user_info.get('height', 170))
            self.weight_spin.setValue(self.user_info.get('weight', 60))
            self.education_combo.setCurrentText(self.user_info.get('education', '本科'))
            self.occupation_edit.setText(self.user_info.get('occupation', ''))
            self.income_spin.setValue(self.user_info.get('income', 0))
            self.hobbies_edit.setText(self.user_info.get('hobbies', ''))
            self.personality_combo.setCurrentText(self.user_info.get('personality', '理性'))
            self.location_edit.setText(self.user_info.get('location', ''))
            self.bio_edit.setText(self.user_info.get('bio', ''))
    
    def save_user_data(self):
        """保存用户数据"""
        # 更新用户信息
        self.db_manager.execute_update('''
            UPDATE users SET 
            name=?, age=?, gender=?, height=?, weight=?, education=?, occupation=?,
            income=?, hobbies=?, personality=?, location=?, bio=?
            WHERE id=?
        ''', (
            self.name_edit.text(), self.age_spin.value(), self.gender_combo.currentText(),
            self.height_spin.value(), self.weight_spin.value(), self.education_combo.currentText(),
            self.occupation_edit.text(), self.income_spin.value(), self.hobbies_edit.text(),
            self.personality_combo.currentText(), self.location_edit.text(), self.bio_edit.toPlainText(),
            self.user_info['id']
        ))
        
        QMessageBox.information(self, "成功", "用户信息已更新!")
        self.accept()

# ==================== 主窗口 ====================
class YueLaoSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.current_user_id = None
        
        # 显示登录对话框
        self.show_login_dialog()
        
        if self.current_user_id:
            self.init_ui()
    
    def show_login_dialog(self):
        """显示登录对话框"""
        login_dialog = LoginDialog(self.db_manager, self)
        if login_dialog.exec_() == QDialog.Accepted:
            self.current_user_id = login_dialog.user_id
        else:
            # 用户取消登录，退出程序
            sys.exit(0)
    
    def init_sample_data(self):
        """初始化示例数据"""
        # 检查是否已有用户数据
        existing_users = self.db_manager.execute_query("SELECT COUNT(*) FROM users")
        if existing_users[0][0] > 0:
            return
        
        # 添加示例用户
        sample_users = [
            ("张三", 28, "男", 175, 70, "本科", "工程师", 15000, "阅读,编程,旅行", "理性", "北京-朝阳", "喜欢安静的生活", "温柔,体贴", "2023-01-01"),
            ("李四", 26, "女", 165, 50, "硕士", "教师", 12000, "音乐,电影,烹饪", "感性", "北京-海淀", "热爱生活", "成熟,稳重", "2023-01-02"),
            ("王五", 30, "男", 180, 75, "博士", "医生", 20000, "运动,旅游,摄影", "外向", "上海-浦东", "积极向上", "活泼,开朗", "2023-01-03"),
            ("赵六", 25, "女", 160, 48, "本科", "设计师", 10000, "绘画,音乐,美食", "内向", "上海-徐汇", "文艺青年", "细心,体贴", "2023-01-04"),
        ]
        
        for user in sample_users:
            self.db_manager.execute_update(
                "INSERT INTO users (name, age, gender, height, weight, education, occupation, income, hobbies, personality, location, bio, preferences, registration_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                user
            )
    
    def init_ui(self):
        self.setWindowTitle("月老系统 - 高级匹配工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 初始化示例数据
        self.init_sample_data()
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧导航栏
        left_nav = self.create_left_nav()
        main_layout.addWidget(left_nav)
        
        # 创建右侧内容区域
        self.content_area = QTabWidget()
        self.content_area.setTabsClosable(True)
        self.content_area.tabCloseRequested.connect(self.close_tab)
        main_layout.addWidget(self.content_area)
        
        # 设置布局比例
        main_layout.setStretchFactor(left_nav, 1)
        main_layout.setStretchFactor(self.content_area, 4)
    
    def close_tab(self, index):
        """关闭标签页"""
        self.content_area.removeTab(index)
    
    def create_left_nav(self):
        """创建左侧导航栏"""
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        
        # 用户信息区域
        user_info = self.get_current_user_info()
        user_card = UserCardWidget(user_info)
        nav_layout.addWidget(user_card)
        
        export_btn = QPushButton("导出数据")
        export_btn.clicked.connect(self.export_data)
        nav_layout.addWidget(export_btn)
        # 编辑个人信息按钮
        edit_profile_btn = QPushButton("编辑个人信息")
        edit_profile_btn.clicked.connect(self.edit_user_profile)
        nav_layout.addWidget(edit_profile_btn)
        
        # 导航按钮
        nav_buttons = [
            ("匹配推荐", self.show_match_finder),
            ("聊天记录", self.show_chat_history),
            ("数据分析", self.show_analytics),
            ("系统设置", self.show_settings)
        ]
        
        for text, slot in nav_buttons:
            button = QPushButton(text)
            button.clicked.connect(slot)
            nav_layout.addWidget(button)
        
        # 退出按钮
        logout_btn = QPushButton("退出登录")
        logout_btn.clicked.connect(self.logout)
        nav_layout.addWidget(logout_btn)
        
        nav_layout.addStretch()
        return nav_widget
    
    def export_data(self):
        """导出数据"""
        dialog = ExportDialog(self.db_manager, self)
        dialog.exec_()
        
    def edit_user_profile(self):
        """编辑用户个人信息"""
        user_info = self.get_current_user_info()
        if user_info:
            dialog = UserEditDialog(user_info, self.db_manager, self)
            if dialog.exec_() == QDialog.Accepted:
                # 刷新界面
                self.update_ui()
    
    def update_ui(self):
        """更新UI"""
        # 重新创建左侧导航栏
        for i in reversed(range(self.centralWidget().layout().count())):
            widget = self.centralWidget().layout().itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # 重新创建布局
        main_layout = self.centralWidget().layout()
        left_nav = self.create_left_nav()
        main_layout.addWidget(left_nav)
        main_layout.addWidget(self.content_area)
    
    def logout(self):
        """退出登录"""
        reply = QMessageBox.question(self, "确认退出", "确定要退出登录吗?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()
            # 重新启动登录流程
            self.current_user_id = None
            self.show_login_dialog()
            if self.current_user_id:
                self.update_ui()
    
    def get_current_user_info(self):
        """获取当前用户信息"""
        if not self.current_user_id:
            return {}
            
        user_data = self.db_manager.execute_query("SELECT * FROM users WHERE id = ?", (self.current_user_id,))
        if user_data:
            columns = [col[0] for col in self.db_manager.execute_query("PRAGMA table_info(users)")]
            return dict(zip(columns, user_data[0]))
        return {}
    
    def show_match_finder(self):
        """显示匹配查找界面"""
        # 移除现有同名标签页
        for i in range(self.content_area.count()):
            if self.content_area.tabText(i) == "匹配推荐":
                self.content_area.removeTab(i)
                break
        
        match_finder = MatchFinderWidget(self.db_manager, self.current_user_id)
        match_finder.matchFound.connect(self.start_chat)
        self.content_area.addTab(match_finder, "匹配推荐")
        self.content_area.setCurrentWidget(match_finder)
    
    def show_chat_history(self):
        """显示聊天记录界面"""
        # 移除现有同名标签页
        for i in range(self.content_area.count()):
            if self.content_area.tabText(i) == "聊天记录":
                self.content_area.removeTab(i)
                break
        
        chat_history_widget = QWidget()
        layout = QVBoxLayout(chat_history_widget)
        
        # 获取当前用户的聊天伙伴
        partners_query = """
            SELECT DISTINCT 
                CASE WHEN user1_id = ? THEN user2_id ELSE user1_id END as partner_id
            FROM chats 
            WHERE user1_id = ? OR user2_id = ?
        """
        partners = self.db_manager.execute_query(partners_query, (self.current_user_id, self.current_user_id, self.current_user_id))
        
        if partners:
            # 创建伙伴列表
            partners_list = QListWidget()
            self.partners_dict = {}  # 存储伙伴ID和姓名的映射
            
            for partner in partners:
                partner_id = partner[0]
                partner_info = self.db_manager.execute_query("SELECT name FROM users WHERE id = ?", (partner_id,))
                if partner_info:
                    name = partner_info[0][0]
                    item_text = f"{name} (ID: {partner_id})"
                    partners_list.addItem(item_text)
                    self.partners_dict[item_text] = partner_id
            
            # 创建聊天区域
            self.chat_area = QTextEdit()
            self.chat_area.setReadOnly(True)
            
            # 连接列表选择事件
            partners_list.currentTextChanged.connect(self.load_chat_for_partner)
            
            # 布局
            splitter = QSplitter(Qt.Horizontal)
            splitter.addWidget(partners_list)
            splitter.addWidget(self.chat_area)
            splitter.setSizes([200, 600])
            
            layout.addWidget(splitter)
        else:
            layout.addWidget(QLabel("暂无聊天记录"))
        
        self.content_area.addTab(chat_history_widget, "聊天记录")
        self.content_area.setCurrentWidget(chat_history_widget)
    
    def load_chat_for_partner(self, partner_text):
        """加载与指定伙伴的聊天记录"""
        if not partner_text or partner_text not in self.partners_dict:
            return
            
        partner_id = self.partners_dict[partner_text]
        self.chat_area.clear()
        chat_history = ChatManager(self.db_manager).get_chat_history(self.current_user_id, partner_id)
        
        for message in chat_history:
            msg_id, user1_id, user2_id, msg_text, sender_id, timestamp = message
            
            # 格式化显示
            try:
                time_str = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
            except:
                time_str = timestamp
                
            if sender_id == self.current_user_id:
                self.chat_area.append(f"[{time_str}] 我: {msg_text}")
            else:
                partner_info = self.db_manager.execute_query("SELECT name FROM users WHERE id = ?", (partner_id,))
                if partner_info:
                    name = partner_info[0][0]
                    self.chat_area.append(f"[{time_str}] {name}: {msg_text}")
    
    def show_analytics(self):
        """显示数据分析界面"""
        # 移除现有同名标签页
        for i in range(self.content_area.count()):
            if self.content_area.tabText(i) == "数据分析":
                self.content_area.removeTab(i)
                break
        
        analytics_widget = AnalyticsWidget(self.db_manager)
        self.content_area.addTab(analytics_widget, "数据分析")
        self.content_area.setCurrentWidget(analytics_widget)
    
    def show_settings(self):
        """显示系统设置界面"""
        # 移除现有同名标签页
        for i in range(self.content_area.count()):
            if self.content_area.tabText(i) == "系统设置":
                self.content_area.removeTab(i)
                break
        
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        
        # 设置标题
        title_label = QLabel("系统设置")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title_label)
        
        # 添加一些设置选项
        settings_form = QFormLayout()
        
        # 匹配偏好设置
        age_range_spin = QSpinBox()
        age_range_spin.setRange(1, 30)
        age_range_spin.setValue(10)
        settings_form.addRow("可接受年龄差:", age_range_spin)
        
        # 地理位置偏好
        location_pref = QComboBox()
        location_pref.addItems(["同城优先", "同省优先", "全国范围"])
        settings_form.addRow("地理位置偏好:", location_pref)
        
        # 教育背景偏好
        edu_pref = QComboBox()
        edu_pref.addItems(["不限", "相近学历", "同等或更高学历"])
        settings_form.addRow("教育背景偏好:", edu_pref)
        
        layout.addLayout(settings_form)
        
        # 保存设置按钮
        save_button = QPushButton("保存设置")
        save_button.clicked.connect(lambda: QMessageBox.information(self, "提示", "设置已保存!"))
        layout.addWidget(save_button)
        
        layout.addStretch()
        
        self.content_area.addTab(settings_widget, "系统设置")
        self.content_area.setCurrentWidget(settings_widget)
    
    def start_chat(self, user_info):
        """开始与指定用户聊天"""
        # 创建聊天标签页
        tab_name = f"与{user_info['name']}聊天"
        
        # 检查是否已存在该聊天标签页
        for i in range(self.content_area.count()):
            if self.content_area.tabText(i) == tab_name:
                self.content_area.setCurrentIndex(i)
                return
        
        # 创建新的聊天标签页
        chat_widget = ChatWidget(self.db_manager, self.current_user_id, user_info['user_id'])
        self.content_area.addTab(chat_widget, tab_name)
        self.content_area.setCurrentWidget(chat_widget)

# ==================== 主程序入口 ====================
def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 设置调色板
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, Qt.black)
    app.setPalette(palette)
    
    # 创建并显示主窗口
    window = YueLaoSystem()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()