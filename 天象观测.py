import sys
import math
import numpy as np
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QLineEdit, QTextEdit, QTabWidget, QGroupBox,
                             QDoubleSpinBox, QDateEdit, QTimeEdit, QCheckBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QProgressBar, QSplitter)
from PyQt5.QtCore import QPointF, Qt, QTimer, QDateTime, QDate, QTime
from PyQt5.QtGui import QFont, QPalette, QColor
import ephem  # 需要安装pyephem库: pip install pyephem


class CelestialCalculator:
    """天象计算器类"""
    
    def __init__(self):
        self.observer = ephem.Observer()
        self.observer.lat = '40.7128'  # 默认纽约纬度
        self.observer.lon = '-74.0060'  # 默认纽约经度
        self.observer.elevation = 10  # 海拔高度(米)
        
    def set_observer_location(self, lat, lon, elevation=10):
        """设置观测者位置"""
        self.observer.lat = str(lat)
        self.observer.lon = str(lon)
        self.observer.elevation = elevation
        
    def get_sun_position(self, date_time):
        """计算太阳位置"""
        self.observer.date = date_time
        sun = ephem.Sun(self.observer)
        sun.compute(self.observer)
        return {
            'altitude': math.degrees(sun.alt),
            'azimuth': math.degrees(sun.az),
            'ra': math.degrees(sun.ra),
            'dec': math.degrees(sun.dec)
        }
    
    def get_moon_position(self, date_time):
        """计算月亮位置"""
        self.observer.date = date_time
        moon = ephem.Moon(self.observer)
        moon.compute(self.observer)
        
        # 计算月亮照明百分比
        # 使用月相和三角函数近似计算照明百分比
        # phase: 0=新月, 90=上弦月, 180=满月, 270=下弦月
        phase_angle = math.radians(moon.phase)
        illuminated = (1 + math.cos(phase_angle)) / 2 * 100
        
        return {
            'altitude': math.degrees(moon.alt),
            'azimuth': math.degrees(moon.az),
            'ra': math.degrees(moon.ra),
            'dec': math.degrees(moon.dec),
            'phase': moon.phase,
            'illuminated': illuminated  # 照明百分比
        }
    
    def get_planet_position(self, planet_name, date_time):
        """计算行星位置"""
        self.observer.date = date_time
        planet_class = getattr(ephem, planet_name.capitalize())
        planet = planet_class(self.observer)
        planet.compute(self.observer)
        return {
            'altitude': math.degrees(planet.alt),
            'azimuth': math.degrees(planet.az),
            'ra': math.degrees(planet.ra),
            'dec': math.degrees(planet.dec)
        }
    
    def get_star_position(self, star_name, date_time):
        """计算恒星位置（简化版）"""
        # 这里可以扩展为包含更多恒星数据
        stars = {
            'Sirius': ('06:45:08.9', '-16:42:58'),  # 天狼星
            'Vega': ('18:36:56.3', '+38:47:01'),    # 织女星
            'Polaris': ('02:31:49.1', '+89:15:51')  # 北极星
        }
        
        if star_name in stars:
            ra, dec = stars[star_name]
            star = ephem.FixedBody()
            star._ra = ra
            star._dec = dec
            self.observer.date = date_time
            star.compute(self.observer)
            return {
                'altitude': math.degrees(star.alt),
                'azimuth': math.degrees(star.az),
                'ra': math.degrees(star.ra),
                'dec': math.degrees(star.dec)
            }
        return None
    
    def get_rise_set_times(self, celestial_body, date):
        """计算天体的升起和落下时间"""
        self.observer.date = date
        body_class = getattr(ephem, celestial_body.capitalize())
        body = body_class()
        
        try:
            rise_time = self.observer.next_rising(body)
            set_time = self.observer.next_setting(body)
            return {
                'rise': rise_time.datetime(),
                'set': set_time.datetime()
            }
        except:
            return None
    
    def get_julian_date(self, date_time):
        """计算儒略日"""
        return ephem.julian_date(date_time)


class StarMapWidget(QWidget):
    """星图显示部件"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 400)
        self.celestial_objects = []
        self.observer_alt = 0
        self.observer_az = 0
        
    def set_observer_view(self, alt, az):
        """设置观测者视角"""
        self.observer_alt = alt
        self.observer_az = az
        self.update()
        
    def add_celestial_object(self, name, alt, az, magnitude, obj_type):
        """添加天体到星图"""
        self.celestial_objects.append({
            'name': name,
            'alt': alt,
            'az': az,
            'magnitude': magnitude,
            'type': obj_type
        })
        self.update()
        
    def clear_objects(self):
        """清空星图上的天体"""
        self.celestial_objects = []
        self.update()
        
    def paintEvent(self, event):
        """绘制星图"""
        from PyQt5.QtGui import QPainter, QPen, QBrush, QFont
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景（夜空）
        painter.fillRect(self.rect(), QColor(10, 10, 30))
        
        # 绘制地平圈
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(center_x, center_y) * 0.9
        
        painter.setPen(QPen(QColor(100, 100, 150), 2))
        painter.drawEllipse(int(center_x - radius), int(center_y - radius), 
                           int(radius * 2), int(radius * 2))
        
        # 绘制方位标记
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.setPen(QPen(Qt.white, 1))
        
        directions = ['N', 'E', 'S', 'W']
        angles = [0, 90, 180, 270]
        
        for direction, angle in zip(directions, angles):
            rad_angle = math.radians(angle)
            x = center_x + radius * math.sin(rad_angle)
            y = center_y - radius * math.cos(rad_angle)
            painter.drawText(int(x - 10), int(y - 10), 20, 20, Qt.AlignCenter, direction)
        
        # 绘制天体
        for obj in self.celestial_objects:
            # 将高度角转换为在星图上的位置
            alt_rad = math.radians(obj['alt'])
            az_rad = math.radians(obj['az'])
            
            # 计算在星图上的坐标
            r = radius * (1 - alt_rad / (math.pi / 2))  # 高度角为0时在地平圈上，90度在中心
            x = center_x + r * math.sin(az_rad)
            y = center_y - r * math.cos(az_rad)
            
            # 根据天体类型和星等设置颜色和大小
            if obj['type'] == 'star':
                color = QColor(255, 255, 200)  # 星星的黄色
                size = max(2, 8 - obj['magnitude'])  # 星等越小（越亮），点越大
            elif obj['type'] == 'planet':
                color = QColor(200, 200, 255)  # 行星的蓝色
                size = 6
            elif obj['type'] == 'sun':
                color = QColor(255, 255, 0)  # 太阳的黄色
                size = 10
            elif obj['type'] == 'moon':
                color = QColor(200, 200, 200)  # 月亮的灰色
                size = 8
            else:
                color = Qt.white
                size = 4
                
            # 绘制天体
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color, 1))
            painter.drawEllipse(int(x - size/2), int(y - size/2), size, size)
            
            # 绘制天体名称
            if obj['magnitude'] < 3 or obj['type'] in ['sun', 'moon']:  # 只显示较亮的天体名称
                painter.drawText(x + size, y, obj['name'])


class CelestialToolkit(QMainWindow):
    """天象观测系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.calculator = CelestialCalculator()
        self.init_ui()
        self.update_display()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('高级天象观测系统')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 创建右侧显示区域
        display_area = self.create_display_area()
        main_layout.addWidget(display_area, 2)
        
        # 设置定时器，每10秒更新一次显示
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(10000)
        
    def create_control_panel(self):
        """创建控制面板"""
        panel = QWidget()
        panel.setMaximumWidth(400)
        layout = QVBoxLayout(panel)
        
        # 位置设置组
        location_group = QGroupBox("观测位置设置")
        location_layout = QVBoxLayout(location_group)
        
        # 纬度输入
        lat_layout = QHBoxLayout()
        lat_layout.addWidget(QLabel("纬度:"))
        self.lat_input = QLineEdit("40.7128")
        lat_layout.addWidget(self.lat_input)
        lat_layout.addWidget(QLabel("°"))
        location_layout.addLayout(lat_layout)
        
        # 经度输入
        lon_layout = QHBoxLayout()
        lon_layout.addWidget(QLabel("经度:"))
        self.lon_input = QLineEdit("-74.0060")
        lon_layout.addWidget(self.lon_input)
        lon_layout.addWidget(QLabel("°"))
        location_layout.addLayout(lon_layout)
        
        # 海拔输入
        elev_layout = QHBoxLayout()
        elev_layout.addWidget(QLabel("海拔:"))
        self.elev_input = QLineEdit("10")
        elev_layout.addWidget(self.elev_input)
        elev_layout.addWidget(QLabel("米"))
        location_layout.addLayout(elev_layout)
        
        # 更新位置按钮
        self.update_location_btn = QPushButton("更新位置")
        self.update_location_btn.clicked.connect(self.update_location)
        location_layout.addWidget(self.update_location_btn)
        
        layout.addWidget(location_group)
        
        # 时间设置组
        time_group = QGroupBox("观测时间设置")
        time_layout = QVBoxLayout(time_group)
        
        # 日期选择
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("日期:"))
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        date_layout.addWidget(self.date_input)
        time_layout.addLayout(date_layout)
        
        # 时间选择
        time_input_layout = QHBoxLayout()
        time_input_layout.addWidget(QLabel("时间:"))
        self.time_input = QTimeEdit()
        self.time_input.setTime(QTime.currentTime())
        time_input_layout.addWidget(self.time_input)
        time_layout.addLayout(time_input_layout)
        
        # 使用当前时间按钮
        self.use_current_time_btn = QPushButton("使用当前时间")
        self.use_current_time_btn.clicked.connect(self.use_current_time)
        time_layout.addWidget(self.use_current_time_btn)
        
        layout.addWidget(time_group)
        
        # 观测目标选择组
        target_group = QGroupBox("观测目标")
        target_layout = QVBoxLayout(target_group)
        
        self.target_combo = QComboBox()
        self.target_combo.addItems(["太阳", "月亮", "水星", "金星", "火星", 
                                   "木星", "土星", "天王星", "海王星", 
                                   "天狼星", "织女星", "北极星"])
        target_layout.addWidget(self.target_combo)
        
        self.add_to_starmap_btn = QPushButton("添加到星图")
        self.add_to_starmap_btn.clicked.connect(self.add_to_starmap)
        target_layout.addWidget(self.add_to_starmap_btn)
        
        self.clear_starmap_btn = QPushButton("清空星图")
        self.clear_starmap_btn.clicked.connect(self.clear_starmap)
        target_layout.addWidget(self.clear_starmap_btn)
        
        layout.addWidget(target_group)
        
        # 计算功能组
        calc_group = QGroupBox("计算功能")
        calc_layout = QVBoxLayout(calc_group)
        
        self.rise_set_btn = QPushButton("计算升起/落下时间")
        self.rise_set_btn.clicked.connect(self.calculate_rise_set)
        calc_layout.addWidget(self.rise_set_btn)
        
        self.julian_date_btn = QPushButton("计算儒略日")
        self.julian_date_btn.clicked.connect(self.calculate_julian_date)
        calc_layout.addWidget(self.julian_date_btn)
        
        layout.addWidget(calc_group)
        
        # 添加伸缩空间，使控件靠上对齐
        layout.addStretch(1)
        
        return panel
        
    def create_display_area(self):
        """创建显示区域"""
        display_widget = QWidget()
        layout = QVBoxLayout(display_widget)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 星图选项卡
        self.star_map = StarMapWidget()
        self.tabs.addTab(self.star_map, "星图")
        
        # 位置信息选项卡
        self.position_info = QTextEdit()
        self.position_info.setReadOnly(True)
        self.tabs.addTab(self.position_info, "位置信息")
        
        # 升起/落下时间选项卡
        self.rise_set_info = QTextEdit()
        self.rise_set_info.setReadOnly(True)
        self.tabs.addTab(self.rise_set_info, "升起/落下时间")
        
        # 天体数据表选项卡
        self.celestial_table = QTableWidget()
        self.celestial_table.setColumnCount(5)
        self.celestial_table.setHorizontalHeaderLabels(["天体", "赤经", "赤纬", "高度", "方位"])
        self.celestial_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabs.addTab(self.celestial_table, "天体数据表")
        
        layout.addWidget(self.tabs)
        
        return display_widget
        
    def update_location(self):
        """更新观测位置"""
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            elev = float(self.elev_input.text())
            self.calculator.set_observer_location(lat, lon, elev)
            self.update_display()
            QMessageBox.information(self, "成功", "位置已更新")
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的经纬度数值")
            
    def use_current_time(self):
        """使用当前时间"""
        self.date_input.setDate(QDate.currentDate())
        self.time_input.setTime(QTime.currentTime())
        self.update_display()
        
    def add_to_starmap(self):
        """添加选定目标到星图"""
        target = self.target_combo.currentText()
        date_time = self.get_current_datetime()
        
        if target == "太阳":
            pos = self.calculator.get_sun_position(date_time)
            obj_type = "sun"
            magnitude = -26.7  # 太阳的视星等
        elif target == "月亮":
            pos = self.calculator.get_moon_position(date_time)
            obj_type = "moon"
            magnitude = -12.7  # 满月的视星等
        elif target in ["天狼星", "织女星", "北极星"]:
            star_name_map = {"天狼星": "Sirius", "织女星": "Vega", "北极星": "Polaris"}
            pos = self.calculator.get_star_position(star_name_map[target], date_time)
            obj_type = "star"
            # 设置恒星的视星等
            magnitudes = {"天狼星": -1.46, "织女星": 0.03, "北极星": 1.98}
            magnitude = magnitudes[target]
        else:
            planet_name_map = {
                "水星": "Mercury", "金星": "Venus", "火星": "Mars", 
                "木星": "Jupiter", "土星": "Saturn", 
                "天王星": "Uranus", "海王星": "Neptune"
            }
            pos = self.calculator.get_planet_position(planet_name_map[target], date_time)
            obj_type = "planet"
            # 设置行星的近似视星等（简化处理）
            magnitudes = {
                "水星": 0.0, "金星": -4.0, "火星": 0.0, 
                "木星": -2.0, "土星": 0.0, "天王星": 5.0, "海王星": 8.0
            }
            magnitude = magnitudes[target]
            
        if pos and pos['altitude'] > 0:  # 只添加在地平线以上的天体
            self.star_map.add_celestial_object(
                target, pos['altitude'], pos['azimuth'], magnitude, obj_type
            )
            
    def clear_starmap(self):
        """清空星图"""
        self.star_map.clear_objects()
        
    def calculate_rise_set(self):
        """计算升起和落下时间"""
        target = self.target_combo.currentText()
        date = self.date_input.date().toPyDate()
        
        if target == "太阳":
            body_name = "Sun"
        elif target == "月亮":
            body_name = "Moon"
        else:
            # 对于行星和恒星，这里简化处理
            QMessageBox.information(self, "提示", "此功能目前仅支持太阳和月亮")
            return
            
        times = self.calculator.get_rise_set_times(body_name, date)
        
        if times:
            rise_time = times['rise'].strftime("%Y-%m-%d %H:%M:%S")
            set_time = times['set'].strftime("%Y-%m-%d %H:%M:%S")
            result = f"{target}的升起/落下时间:\n\n"
            result += f"升起: {rise_time}\n"
            result += f"落下: {set_time}"
            self.rise_set_info.setText(result)
        else:
            self.rise_set_info.setText(f"无法计算{target}的升起/落下时间\n"
                                      f"(可能在该日期该天体不升起或不落下)")
            
    def calculate_julian_date(self):
        """计算儒略日"""
        date_time = self.get_current_datetime()
        jd = self.calculator.get_julian_date(date_time)
        self.position_info.append(f"儒略日: {jd:.6f}\n")
        
    def get_current_datetime(self):
        """获取当前设置的日期时间"""
        date = self.date_input.date().toPyDate()
        time = self.time_input.time().toPyTime()
        return datetime.combine(date, time)
        
    def update_display(self):
        """更新所有显示信息"""
        date_time = self.get_current_datetime()
        
        # 更新位置信息
        info_text = f"观测时间: {date_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        info_text += f"观测位置: 纬度 {self.lat_input.text()}°, "
        info_text += f"经度 {self.lon_input.text()}°, "
        info_text += f"海拔 {self.elev_input.text()}米\n\n"
        
        # 计算太阳位置
        sun_pos = self.calculator.get_sun_position(date_time)
        info_text += "太阳位置:\n"
        info_text += f"  赤经: {sun_pos['ra']:.2f}°\n"
        info_text += f"  赤纬: {sun_pos['dec']:.2f}°\n"
        info_text += f"  高度: {sun_pos['altitude']:.2f}°\n"
        info_text += f"  方位: {sun_pos['azimuth']:.2f}°\n\n"
        
        # 计算月亮位置
        moon_pos = self.calculator.get_moon_position(date_time)
        info_text += "月亮位置:\n"
        info_text += f"  赤经: {moon_pos['ra']:.2f}°\n"
        info_text += f"  赤纬: {moon_pos['dec']:.2f}°\n"
        info_text += f"  高度: {moon_pos['altitude']:.2f}°\n"
        info_text += f"  方位: {moon_pos['azimuth']:.2f}°\n"
        info_text += f"  月相: {moon_pos['phase']:.1f}°\n"
        info_text += f"  照明: {moon_pos['illuminated']:.1f}%\n\n"
        
        self.position_info.setText(info_text)
        
        # 更新天体数据表
        self.update_celestial_table(date_time)
        
    def update_celestial_table(self, date_time):
        """更新天体数据表"""
        # 清空表格
        self.celestial_table.setRowCount(0)
        
        # 添加太阳数据
        sun_pos = self.calculator.get_sun_position(date_time)
        self.add_celestial_to_table("太阳", sun_pos)
        
        # 添加月亮数据
        moon_pos = self.calculator.get_moon_position(date_time)
        self.add_celestial_to_table("月亮", moon_pos)
        
        # 添加行星数据
        planets = ["水星", "金星", "火星", "木星", "土星"]
        planet_map = {
            "水星": "Mercury", "金星": "Venus", "火星": "Mars", 
            "木星": "Jupiter", "土星": "Saturn"
        }
        
        for planet in planets:
            pos = self.calculator.get_planet_position(planet_map[planet], date_time)
            self.add_celestial_to_table(planet, pos)
            
        # 添加恒星数据
        stars = ["天狼星", "织女星", "北极星"]
        star_map = {"天狼星": "Sirius", "织女星": "Vega", "北极星": "Polaris"}
        
        for star in stars:
            pos = self.calculator.get_star_position(star_map[star], date_time)
            if pos:
                self.add_celestial_to_table(star, pos)
                
    def add_celestial_to_table(self, name, position):
        """添加天体数据到表格"""
        if position and position['altitude'] > -5:  # 只显示高度大于-5度的天体
            row = self.celestial_table.rowCount()
            self.celestial_table.insertRow(row)
            
            self.celestial_table.setItem(row, 0, QTableWidgetItem(name))
            self.celestial_table.setItem(row, 1, QTableWidgetItem(f"{position['ra']:.2f}°"))
            self.celestial_table.setItem(row, 2, QTableWidgetItem(f"{position['dec']:.2f}°"))
            self.celestial_table.setItem(row, 3, QTableWidgetItem(f"{position['altitude']:.2f}°"))
            self.celestial_table.setItem(row, 4, QTableWidgetItem(f"{position['azimuth']:.2f}°"))


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = CelestialToolkit()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()