import sys
import json
import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import numpy as np
from PyQt5.QtCore import (Qt, QDate, QDateTime, QTimer, QSize, 
                         QPoint, QPropertyAnimation, QEasingCurve)
from PyQt5.QtGui import (QIcon, QPixmap, QColor, QFont, QPainter, 
                        QPen, QBrush, QLinearGradient)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QLabel, QPushButton,
                            QLineEdit, QTextEdit, QComboBox, QDateEdit, QStackedWidget,
                            QSpinBox, QDoubleSpinBox, QCheckBox, QRadioButton,
                            QGroupBox, QFrame, QScrollArea, QTabWidget,
                            QListWidget, QListWidgetItem, QTreeWidget,
                            QTreeWidgetItem, QTableWidget, QTableWidgetItem,
                            QHeaderView, QSplitter, QProgressBar, QSlider,
                            QMessageBox, QDialog, QDialogButtonBox,
                            QToolButton, QMenu, QAction, QStyleFactory,
                            QStyledItemDelegate, QStyleOptionViewItem)


class ServiceType(Enum):
    """家政服务类型枚举"""
    CLEANING = "清洁服务"
    COOKING = "烹饪服务"
    BABYSITTING = "保姆服务"
    ELDERLY_CARE = "老人照护"
    PET_CARE = "宠物照看"
    REPAIR = "维修服务"
    OTHER = "其他服务"


class ServiceStatus(Enum):
    """服务状态枚举"""
    PENDING = "待处理"
    CONFIRMED = "已确认"
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"
    CANCELLED = "已取消"


class Rating(Enum):
    """评分枚举"""
    ONE_STAR = 1
    TWO_STARS = 2
    THREE_STARS = 3
    FOUR_STARS = 4
    FIVE_STARS = 5


class FadeButton(QPushButton):
    """带渐入渐出动画效果的按钮"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._animation = QPropertyAnimation(self, b"opacity")
        self._animation.setDuration(300)
        self._opacity = 1.0
        
    def getOpacity(self):
        return self._opacity
        
    def setOpacity(self, opacity):
        self._opacity = opacity
        self.update()
        
    opacity = property(getOpacity, setOpacity)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(self._opacity)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())
        
    def enterEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self.opacity)
        self._animation.setEndValue(0.7)
        self._animation.start()
        
    def leaveEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self.opacity)
        self._animation.setEndValue(1.0)
        self._animation.start()


class ServiceCard(QFrame):
    """服务信息卡片组件"""
    def __init__(self, service_data, parent=None):
        super().__init__(parent)
        self.service_data = service_data
        self.setup_ui()
        
    def setup_ui(self):
        self.setObjectName("serviceCard")
        self.setStyleSheet("""
            #serviceCard {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                border: 1px solid #e0e0e0;
            }
            #serviceCard:hover {
                border: 1px solid #bbdefb;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # 服务类型和状态
        header_layout = QHBoxLayout()
        self.type_label = QLabel(self.service_data.get('type', '未知服务'))
        self.type_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #1976d2;")
        
        self.status_label = QLabel(self.service_data.get('status', '未知状态'))
        status_color = self.get_status_color(self.service_data.get('status'))
        self.status_label.setStyleSheet(f"background-color: {status_color}; color: white; padding: 2px 8px; border-radius: 10px;")
        
        header_layout.addWidget(self.type_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        layout.addLayout(header_layout)
        
        # 服务详情
        self.details_label = QLabel(f"时间: {self.service_data.get('time', '未指定')}\n"
                                   f"地址: {self.service_data.get('address', '未指定')}\n"
                                   f"服务人员: {self.service_data.get('worker', '未分配')}")
        layout.addWidget(self.details_label)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.details_btn = FadeButton("查看详情")
        self.details_btn.setStyleSheet("background-color: #e3f2fd; color: #1976d2;")
        
        self.cancel_btn = FadeButton("取消服务")
        self.cancel_btn.setStyleSheet("background-color: #ffebee; color: #d32f2f;")
        
        button_layout.addWidget(self.details_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
    def get_status_color(self, status):
        colors = {
            "待处理": "#ff9800",
            "已确认": "#2196f3",
            "进行中": "#4caf50",
            "已完成": "#9e9e9e",
            "已取消": "#f44336"
        }
        return colors.get(status, "#9e9e9e")


class CalendarWidget(QWidget):
    """自定义日历组件，支持标记有服务的日期"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.marked_dates = set()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 导航栏
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(30, 30)
        
        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignCenter)
        self.month_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(30, 30)
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.month_label)
        nav_layout.addWidget(self.next_btn)
        layout.addLayout(nav_layout)
        
        # 日历网格
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(5)
        
        # 添加星期几的标签
        days = ["日", "一", "二", "三", "四", "五", "六"]
        for i, day in enumerate(days):
            label = QLabel(day)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-weight: bold;")
            self.grid_layout.addWidget(label, 0, i)
            
        layout.addLayout(self.grid_layout)
        self.setLayout(layout)
        
        # 连接信号
        self.prev_btn.clicked.connect(self.previous_month)
        self.next_btn.clicked.connect(self.next_month)
        
        # 初始化当前日期
        self.current_date = QDate.currentDate()
        self.update_calendar()
        
    def update_calendar(self):
        # 更新月份标签
        self.month_label.setText(self.current_date.toString("yyyy年 MM月"))
        
        # 清除现有的日期按钮
        for i in reversed(range(1, self.grid_layout.rowCount())):
            for j in range(self.grid_layout.columnCount()):
                item = self.grid_layout.itemAtPosition(i, j)
                if item and item.widget():
                    item.widget().deleteLater()
                    
        # 计算月份的第一天和最后一天
        first_day = QDate(self.current_date.year(), self.current_date.month(), 1)
        last_day = first_day.addMonths(1).addDays(-1)
        
        # 计算第一天是星期几
        start_day = first_day.dayOfWeek() % 7  # Qt中周日是7，我们调整为0
        
        # 填充日历
        row, col = 1, start_day
        for day in range(1, last_day.day() + 1):
            date = QDate(self.current_date.year(), self.current_date.month(), day)
            btn = QPushButton(str(day))
            btn.setFixedSize(40, 40)
            
            # 标记有服务的日期
            if date in self.marked_dates:
                btn.setStyleSheet("background-color: #bbdefb; border-radius: 20px;")
            elif date == QDate.currentDate():
                btn.setStyleSheet("background-color: #ffcdd2; border-radius: 20px;")
            else:
                btn.setStyleSheet("border-radius: 20px;")
                
            self.grid_layout.addWidget(btn, row, col)
            
            col += 1
            if col > 6:
                col = 0
                row += 1
                
    def previous_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.update_calendar()
        
    def next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.update_calendar()
        
    def mark_date(self, date):
        """标记一个日期"""
        self.marked_dates.add(date)
        self.update_calendar()
        
    def unmark_date(self, date):
        """取消标记一个日期"""
        if date in self.marked_dates:
            self.marked_dates.remove(date)
            self.update_calendar()


class RatingWidget(QWidget):
    """评分组件"""
    def __init__(self, max_stars=5, parent=None):
        super().__init__(parent)
        self.max_stars = max_stars
        self.current_rating = 0
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(2)
        
        self.star_buttons = []
        for i in range(self.max_stars):
            btn = QToolButton()
            btn.setIcon(self.star_icon(False))
            btn.setIconSize(QSize(24, 24))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i+1: self.set_rating(idx))
            layout.addWidget(btn)
            self.star_buttons.append(btn)
            
        layout.addStretch()
        
    def star_icon(self, filled):
        """生成星星图标"""
        color = "#ffc107" if filled else "#e0e0e0"
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(color)))
        painter.setBrush(QBrush(QColor(color)))
        
        # 绘制五角星
        points = []
        for i in range(5):
            # 外点
            angle = 90 + i * 72
            x_out = 12 + 10 * np.cos(np.radians(angle))
            y_out = 12 - 10 * np.sin(np.radians(angle))
            points.append(QPoint(int(round(x_out)), int(round(y_out))))
            
            # 内点
            angle_in = angle + 36
            x_in = 12 + 4 * np.cos(np.radians(angle_in))
            y_in = 12 - 4 * np.sin(np.radians(angle_in))
            points.append(QPoint(int(round(x_in)), int(round(y_in))))
            
        painter.drawPolygon(points)
        painter.end()
        
        return QIcon(pixmap)
    
    def set_rating(self, rating):
        """设置评分"""
        self.current_rating = rating
        for i, btn in enumerate(self.star_buttons):
            btn.setIcon(self.star_icon(i < rating))
            
    def get_rating(self):
        """获取当前评分"""
        return self.current_rating


class ServiceBookingDialog(QDialog):
    """服务预订对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("预订家政服务")
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 服务类型选择
        type_group = QGroupBox("服务类型")
        type_layout = QVBoxLayout()
        self.type_combo = QComboBox()
        for service in ServiceType:
            self.type_combo.addItem(service.value, service)
        type_layout.addWidget(self.type_combo)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 日期和时间选择
        datetime_group = QGroupBox("服务时间")
        datetime_layout = QGridLayout()
        
        datetime_layout.addWidget(QLabel("日期:"), 0, 0)
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate().addDays(1))
        self.date_edit.setCalendarPopup(True)
        datetime_layout.addWidget(self.date_edit, 0, 1)
        
        datetime_layout.addWidget(QLabel("时间:"), 1, 0)
        self.time_combo = QComboBox()
        for hour in range(8, 19):
            self.time_combo.addItem(f"{hour}:00")
            self.time_combo.addItem(f"{hour}:30")
        datetime_layout.addWidget(self.time_combo, 1, 1)
        
        datetime_group.setLayout(datetime_layout)
        layout.addWidget(datetime_group)
        
        # 服务详情
        details_group = QGroupBox("服务详情")
        details_layout = QVBoxLayout()
        
        details_layout.addWidget(QLabel("地址:"))
        self.address_edit = QLineEdit()
        details_layout.addWidget(self.address_edit)
        
        details_layout.addWidget(QLabel("备注:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        details_layout.addWidget(self.notes_edit)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def get_booking_data(self):
        """获取预订数据"""
        return {
            "type": self.type_combo.currentData(),
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "time": self.time_combo.currentText(),
            "address": self.address_edit.text(),
            "notes": self.notes_edit.toPlainText()
        }


class HouseholdServiceSystem(QMainWindow):
    """家政系统主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级家政服务系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 初始化数据
        self.services = []
        self.load_sample_data()
        
        # 设置UI
        self.setup_ui()
        
    def setup_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧导航
        left_nav = self.create_left_navigation()
        main_layout.addWidget(left_nav, 1)
        
        # 右侧内容区域
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        
        # 顶部工具栏
        top_toolbar = self.create_top_toolbar()
        right_layout.addWidget(top_toolbar)
        
        # 内容区域
        self.content_stack = QStackedWidget()
        
        # 添加不同的页面
        self.dashboard_page = self.create_dashboard_page()
        self.services_page = self.create_services_page()
        self.calendar_page = self.create_calendar_page()
        self.workers_page = self.create_workers_page()
        
        self.content_stack.addWidget(self.dashboard_page)
        self.content_stack.addWidget(self.services_page)
        self.content_stack.addWidget(self.calendar_page)
        self.content_stack.addWidget(self.workers_page)
        
        right_layout.addWidget(self.content_stack, 1)
        
        main_layout.addWidget(right_content, 4)
        
    def create_left_navigation(self):
        nav_widget = QWidget()
        nav_widget.setObjectName("leftNav")
        nav_widget.setStyleSheet("""
            #leftNav {
                background-color: #263238;
                color: white;
            }
            QPushButton {
                text-align: left;
                padding: 10px;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #37474f;
            }
            QPushButton:checked {
                background-color: #1976d2;
            }
        """)
        
        layout = QVBoxLayout(nav_widget)
        
        # 品牌标志
        brand_label = QLabel("家政服务系统")
        brand_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 20px; color: #bbdefb;")
        brand_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(brand_label)
        
        # 导航按钮
        self.nav_buttons = []
        
        nav_items = [
            ("仪表盘", "dashboard"),
            ("服务管理", "services"),
            ("日历视图", "calendar"),
            ("服务人员", "workers"),
            ("客户管理", "clients"),
            ("财务管理", "finance"),
            ("设置", "settings")
        ]
        
        for text, icon_name in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=len(self.nav_buttons): self.switch_page(idx))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)
            
        # 默认选中第一个
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)
            
        layout.addStretch()
        
        return nav_widget
        
    def create_top_toolbar(self):
        toolbar = QWidget()
        toolbar.setFixedHeight(60)
        toolbar.setObjectName("topToolbar")
        toolbar.setStyleSheet("""
            #topToolbar {
                background-color: white;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        
        layout = QHBoxLayout(toolbar)
        
        # 标题
        self.title_label = QLabel("仪表盘")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # 搜索框
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("搜索...")
        search_edit.setFixedWidth(200)
        layout.addWidget(search_edit)
        
        # 通知按钮
        notify_btn = QToolButton()
        notify_btn.setIcon(QIcon.fromTheme("notifications"))
        layout.addWidget(notify_btn)
        
        # 用户菜单
        user_btn = QToolButton()
        user_btn.setText("管理员")
        user_btn.setPopupMode(QToolButton.InstantPopup)
        
        user_menu = QMenu()
        user_menu.addAction("个人信息")
        user_menu.addAction("设置")
        user_menu.addSeparator()
        user_menu.addAction("退出")
        user_btn.setMenu(user_menu)
        
        layout.addWidget(user_btn)
        
        return toolbar
        
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # 统计卡片
        stats_layout = QHBoxLayout()
        
        stats_data = [
            {"title": "今日订单", "value": "12", "color": "#2196f3"},
            {"title": "进行中服务", "value": "8", "color": "#4caf50"},
            {"title": "待确认订单", "value": "3", "color": "#ff9800"},
            {"title": "月收入", "value": "¥8,560", "color": "#9c27b0"}
        ]
        
        for stat in stats_data:
            card = QFrame()
            card.setFixedHeight(100)
            card.setStyleSheet(f"""
                background-color: {stat['color']};
                color: white;
                border-radius: 8px;
                padding: 15px;
            """)
            
            card_layout = QVBoxLayout(card)
            title = QLabel(stat['title'])
            title.setStyleSheet("font-size: 14px;")
            value = QLabel(stat['value'])
            value.setStyleSheet("font-size: 24px; font-weight: bold;")
            
            card_layout.addWidget(title)
            card_layout.addWidget(value)
            card_layout.addStretch()
            
            stats_layout.addWidget(card)
            
        layout.addLayout(stats_layout)
        
        # 最近服务
        recent_group = QGroupBox("最近服务")
        recent_layout = QVBoxLayout()
        
        for service in self.services[:5]:
            card = ServiceCard(service)
            recent_layout.addWidget(card)
            
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        
        return page
        
    def create_services_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # 操作栏
        action_bar = QHBoxLayout()
        
        add_btn = QPushButton("新建服务")
        add_btn.setStyleSheet("background-color: #4caf50; color: white;")
        add_btn.clicked.connect(self.add_new_service)
        
        filter_combo = QComboBox()
        filter_combo.addItems(["全部状态", "待处理", "已确认", "进行中", "已完成", "已取消"])
        
        action_bar.addWidget(add_btn)
        action_bar.addStretch()
        action_bar.addWidget(QLabel("筛选:"))
        action_bar.addWidget(filter_combo)
        
        layout.addLayout(action_bar)
        
        # 服务列表
        self.services_list = QListWidget()
        for service in self.services:
            item = QListWidgetItem()
            widget = ServiceCard(service)
            item.setSizeHint(widget.sizeHint())
            self.services_list.addItem(item)
            self.services_list.setItemWidget(item, widget)
            
        layout.addWidget(self.services_list)
        
        return page
        
    def create_calendar_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        self.calendar = CalendarWidget()
        layout.addWidget(self.calendar)
        
        # 标记一些示例日期
        today = QDate.currentDate()
        self.calendar.mark_date(today.addDays(2))
        self.calendar.mark_date(today.addDays(5))
        self.calendar.mark_date(today.addDays(7))
        
        return page
        
    def create_workers_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # 服务人员表格
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["姓名", "服务类型", "评分", "状态", "操作"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 示例数据
        workers = [
            {"name": "张三", "type": "清洁服务", "rating": 4.8, "status": "空闲"},
            {"name": "李四", "type": "烹饪服务", "rating": 4.9, "status": "忙碌"},
            {"name": "王五", "type": "保姆服务", "rating": 4.7, "status": "空闲"},
            {"name": "赵六", "type": "老人照护", "rating": 4.6, "status": "忙碌"},
        ]
        
        table.setRowCount(len(workers))
        for i, worker in enumerate(workers):
            table.setItem(i, 0, QTableWidgetItem(worker['name']))
            table.setItem(i, 1, QTableWidgetItem(worker['type']))
            
            # 评分单元格使用自定义组件
            rating_widget = RatingWidget()
            rating_widget.set_rating(int(worker['rating']))
            table.setCellWidget(i, 2, rating_widget)
            
            table.setItem(i, 3, QTableWidgetItem(worker['status']))
            
            # 操作按钮
            action_btn = QPushButton("查看详情")
            action_btn.setStyleSheet("background-color: #bbdefb;")
            table.setCellWidget(i, 4, action_btn)
            
        layout.addWidget(table)
        
        return page
        
    def switch_page(self, index):
        """切换页面"""
        for btn in self.nav_buttons:
            btn.setChecked(False)
        self.nav_buttons[index].setChecked(True)
        self.content_stack.setCurrentIndex(index)
        
        # 更新标题
        titles = ["仪表盘", "服务管理", "日历视图", "服务人员", "客户管理", "财务管理", "设置"]
        if index < len(titles):
            self.title_label.setText(titles[index])
            
    def add_new_service(self):
        """添加新服务"""
        dialog = ServiceBookingDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_booking_data()
            # 这里应该将数据保存到数据库
            QMessageBox.information(self, "成功", "服务已成功预订！")
            
    def load_sample_data(self):
        """加载示例数据"""
        self.services = [
            {
                "type": "清洁服务",
                "status": "待处理",
                "time": "2023-07-15 10:00",
                "address": "北京市海淀区中关村大街1号",
                "worker": "张三"
            },
            {
                "type": "烹饪服务",
                "status": "进行中",
                "time": "2023-07-14 18:30",
                "address": "北京市朝阳区建国门外大街2号",
                "worker": "李四"
            },
            {
                "type": "保姆服务",
                "status": "已完成",
                "time": "2023-07-13 09:00",
                "address": "北京市西城区西长安街3号",
                "worker": "王五"
            },
            {
                "type": "老人照护",
                "status": "已确认",
                "time": "2023-07-16 14:00",
                "address": "北京市东城区东长安街4号",
                "worker": "赵六"
            },
            {
                "type": "宠物照看",
                "status": "已取消",
                "time": "2023-07-12 16:00",
                "address": "北京市丰台区丰台路5号",
                "worker": "钱七"
            }
        ]


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # 创建并显示主窗口
    window = HouseholdServiceSystem()
    window.show()
    
    sys.exit(app.exec_())