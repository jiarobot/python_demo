import sys
import os
import subprocess
import psutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QListWidget, QTextEdit, 
                             QPushButton, QLabel, QLineEdit, QSplitter, 
                             QTreeWidget, QTreeWidgetItem, QHeaderView,
                             QProgressBar, QFileDialog, QMessageBox, 
                             QGroupBox, QCheckBox, QSpinBox, QComboBox)
from PyQt5.QtCore import QTimer, Qt, QProcess
from PyQt5.QtGui import QFont, QColor

class GameProcessMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_processes)
        self.timer.start(2000)  # 每2秒刷新一次
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 进程列表
        self.process_list = QTreeWidget()
        self.process_list.setHeaderLabels(["PID", "进程名", "路径", "CPU%", "内存(MB)"])
        self.process_list.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.process_list.itemDoubleClicked.connect(self.on_process_selected)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_processes)
        self.attach_btn = QPushButton("附加到选中进程")
        self.attach_btn.clicked.connect(self.attach_to_process)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.attach_btn)
        button_layout.addStretch()
        
        layout.addWidget(QLabel("运行中的进程:"))
        layout.addWidget(self.process_list)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def refresh_processes(self):
        self.process_list.clear()
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cpu_percent', 'memory_info']):
            try:
                item = QTreeWidgetItem([
                    str(proc.info['pid']),
                    proc.info['name'],
                    proc.info['exe'] or "N/A",
                    f"{proc.info['cpu_percent'] or 0:.1f}",
                    f"{(proc.info['memory_info'].rss / 1024 / 1024):.1f}" if proc.info['memory_info'] else "0"
                ])
                self.process_list.addTopLevelItem(item)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
    def on_process_selected(self, item, column):
        self.selected_pid = int(item.text(0))
        
    def attach_to_process(self):
        selected_items = self.process_list.selectedItems()
        if selected_items:
            pid = int(selected_items[0].text(0))
            process_name = selected_items[0].text(1)
            QMessageBox.information(self, "进程附加", f"已附加到进程: {process_name} (PID: {pid})")
            return pid
        return None

class MemoryScanner(QWidget):
    def __init__(self):
        super().__init__()
        self.scan_results = []
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 扫描配置
        config_group = QGroupBox("扫描配置")
        config_layout = QVBoxLayout()
        
        # 值类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("数据类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["4字节整数", "8字节整数", "浮点数", "双精度浮点数", "字符串"])
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        
        # 值输入
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("目标值:"))
        self.value_edit = QLineEdit()
        value_layout.addWidget(self.value_edit)
        
        config_layout.addLayout(type_layout)
        config_layout.addLayout(value_layout)
        config_group.setLayout(config_layout)
        
        # 扫描按钮
        scan_layout = QHBoxLayout()
        self.first_scan_btn = QPushButton("首次扫描")
        self.next_scan_btn = QPushButton("再次扫描")
        self.next_scan_btn.setEnabled(False)
        
        scan_layout.addWidget(self.first_scan_btn)
        scan_layout.addWidget(self.next_scan_btn)
        scan_layout.addStretch()
        
        # 结果显示
        self.results_list = QTreeWidget()
        self.results_list.setHeaderLabels(["地址", "值", "类型"])
        
        # 内存查看
        memory_view_group = QGroupBox("内存查看")
        memory_layout = QVBoxLayout()
        self.memory_view = QTextEdit()
        self.memory_view.setFont(QFont("Courier", 10))
        memory_layout.addWidget(self.memory_view)
        memory_view_group.setLayout(memory_layout)
        
        layout.addWidget(config_group)
        layout.addLayout(scan_layout)
        layout.addWidget(QLabel("扫描结果:"))
        layout.addWidget(self.results_list)
        layout.addWidget(memory_view_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.first_scan_btn.clicked.connect(self.first_scan)
        self.next_scan_btn.clicked.connect(self.next_scan)
        self.results_list.itemDoubleClicked.connect(self.view_memory)
        
    def first_scan(self):
        # 模拟首次扫描
        value = self.value_edit.text()
        if value:
            self.scan_results = [
                {"address": "0x" + format(0x140000000 + i * 4, 'x'), "value": value, "type": self.type_combo.currentText()}
                for i in range(100)  # 模拟100个结果
            ]
            self.update_results()
            self.next_scan_btn.setEnabled(True)
            
    def next_scan(self):
        # 模拟再次扫描（过滤结果）
        if len(self.scan_results) > 10:
            self.scan_results = self.scan_results[:len(self.scan_results)//2]
            self.update_results()
            
    def update_results(self):
        self.results_list.clear()
        for result in self.scan_results:
            item = QTreeWidgetItem([result["address"], result["value"], result["type"]])
            self.results_list.addTopLevelItem(item)
            
    def view_memory(self, item, column):
        address = item.text(0)
        # 模拟内存查看
        memory_dump = f"内存地址: {address}\n\n"
        memory_dump += "偏移   00 01 02 03 04 05 06 07  08 09 0A 0B 0C 0D 0E 0F    ASCII\n"
        memory_dump += "------ " + "-"*49 + " " + "-"*16 + "\n"
        
        # 生成模拟内存数据
        for i in range(0, 256, 16):
            hex_part = " ".join([format((i + j) % 256, '02x') for j in range(8)]) + "  "
            hex_part += " ".join([format((i + j + 8) % 256, '02x') for j in range(8)])
            ascii_part = "".join([chr((i + j) % 256) if 32 <= (i + j) % 256 < 127 else '.' for j in range(16)])
            memory_dump += f"{address}+{i:04x}  {hex_part}  {ascii_part}\n"
            
        self.memory_view.setText(memory_dump)

class FunctionAnalyzer(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 函数列表
        self.function_list = QTreeWidget()
        self.function_list.setHeaderLabels(["函数名", "地址", "模块", "调用次数"])
        self.function_list.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # 模拟一些函数数据
        functions = [
            ("Player::GetHealth", "0x1402A3B10", "Game.dll", "125"),
            ("Player::SetHealth", "0x1402A3C20", "Game.dll", "89"),
            ("Weapon::Fire", "0x1402B4510", "Game.dll", "203"),
            ("Render::DrawModel", "0x1403C1200", "Render.dll", "1567"),
            ("Physics::Update", "0x1404D3400", "Physics.dll", "892")
        ]
        
        for func in functions:
            item = QTreeWidgetItem(func)
            self.function_list.addTopLevelItem(item)
            
        # 分析按钮
        analyze_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("分析选中函数")
        self.hook_btn = QPushButton("Hook函数")
        self.xref_btn = QPushButton("查看交叉引用")
        
        analyze_layout.addWidget(self.analyze_btn)
        analyze_layout.addWidget(self.hook_btn)
        analyze_layout.addWidget(self.xref_btn)
        analyze_layout.addStretch()
        
        # 反汇编显示
        disasm_group = QGroupBox("反汇编代码")
        disasm_layout = QVBoxLayout()
        self.disasm_view = QTextEdit()
        self.disasm_view.setFont(QFont("Courier", 9))
        disasm_layout.addWidget(self.disasm_view)
        disasm_group.setLayout(disasm_layout)
        
        layout.addWidget(QLabel("发现的函数:"))
        layout.addWidget(self.function_list)
        layout.addLayout(analyze_layout)
        layout.addWidget(disasm_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.function_list.itemClicked.connect(self.show_disassembly)
        self.analyze_btn.clicked.connect(self.analyze_function)
        
    def show_disassembly(self, item, column):
        func_name = item.text(0)
        address = item.text(1)
        
        # 模拟反汇编代码
        disasm_text = f"; 函数: {func_name} at {address}\n"
        disasm_text += f"; 分析时间: 2024-01-01 12:00:00\n\n"
        
        # 模拟不同函数的反汇编
        if "GetHealth" in func_name:
            disasm_text += """sub_1402A3B10 proc near
push    rbx
sub     rsp, 20h
mov     rbx, rcx
mov     rax, [rcx+18h]    ; 玩家对象+0x18 = 生命值指针
mov     eax, [rax+10h]    ; 生命值结构+0x10 = 当前生命值
add     rsp, 20h
pop     rbx
retn
sub_1402A3B10 endp"""
        elif "SetHealth" in func_name:
            disasm_text += """sub_1402A3C20 proc near
push    rbx
sub     rsp, 20h
mov     rbx, rcx
mov     rax, [rcx+18h]    ; 玩家对象+0x18 = 生命值指针
mov     [rax+10h], edx    ; 参数2: 新的生命值
add     rsp, 20h
pop     rbx
retn
sub_1402A3C20 endp"""
        else:
            disasm_text += "; 反汇编代码加载中...\n"
            disasm_text += "mov rax, [rcx]\n"
            disasm_text += "test rax, rax\n"
            disasm_text += "jz short loc_ret\n"
            disasm_text += "call qword ptr [rax+8]\n"
            disasm_text += "loc_ret:\n"
            disasm_text += "retn"
            
        self.disasm_view.setText(disasm_text)
        
    def analyze_function(self):
        selected_items = self.function_list.selectedItems()
        if selected_items:
            func_name = selected_items[0].text(0)
            QMessageBox.information(self, "函数分析", 
                                  f"正在分析函数: {func_name}\n\n"
                                  f"分析完成！\n"
                                  f"- 参数数量: 2\n"
                                  f"- 调用约定: fastcall\n"
                                  f"- 返回值: EAX (32位整数)\n"
                                  f"- 参数1: RCX (对象指针)\n"
                                  f"- 参数2: EDX (整数值)")

class CodeInjector(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 代码编辑
        code_group = QGroupBox("汇编代码编辑")
        code_layout = QVBoxLayout()
        self.code_edit = QTextEdit()
        self.code_edit.setPlaceholderText("在此输入汇编代码...\n示例:\nmov [rcx+10h], 100 ; 设置生命值为100\nretn")
        self.code_edit.setFont(QFont("Courier", 10))
        code_layout.addWidget(self.code_edit)
        code_group.setLayout(code_layout)
        
        # 注入选项
        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("注入类型:"))
        self.inject_type = QComboBox()
        self.inject_type.addItems(["代码补丁", "DLL注入", "API Hook"])
        
        options_layout.addWidget(self.inject_type)
        options_layout.addStretch()
        
        # 按钮
        button_layout = QHBoxLayout()
        self.inject_btn = QPushButton("执行注入")
        self.save_btn = QPushButton("保存脚本")
        self.load_btn = QPushButton("加载脚本")
        
        button_layout.addWidget(self.inject_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.load_btn)
        button_layout.addStretch()
        
        # 日志
        log_group = QGroupBox("注入日志")
        log_layout = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setFont(QFont("Courier", 9))
        log_layout.addWidget(self.log_view)
        log_group.setLayout(log_layout)
        
        layout.addWidget(code_group)
        layout.addLayout(options_layout)
        layout.addLayout(button_layout)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.inject_btn.clicked.connect(self.execute_injection)
        
    def execute_injection(self):
        code = self.code_edit.toPlainText()
        inject_type = self.inject_type.currentText()
        
        log_entry = f"[INFO] 开始 {inject_type}\n"
        log_entry += f"[CODE] {code}\n"
        log_entry += f"[SUCCESS] 代码注入完成!\n"
        log_entry += f"[NOTE] 这只是演示，实际注入需要管理员权限和适当的调试权限\n\n"
        
        current_log = self.log_view.toPlainText()
        self.log_view.setText(log_entry + current_log)

class GameReverseToolbox(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("游戏逆向工程工具箱 - 仅用于教育研究")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 添加各个功能页面
        self.process_monitor = GameProcessMonitor()
        self.memory_scanner = MemoryScanner()
        self.function_analyzer = FunctionAnalyzer()
        self.code_injector = CodeInjector()
        
        self.tabs.addTab(self.process_monitor, "进程监控")
        self.tabs.addTab(self.memory_scanner, "内存扫描")
        self.tabs.addTab(self.function_analyzer, "函数分析")
        self.tabs.addTab(self.code_injector, "代码注入")
        
        # 状态栏
        self.statusBar().showMessage("就绪 - 请仅在合法环境下使用本工具")
        
        # 警告标签
        warning_label = QLabel(
            "⚠️ 警告: 本工具仅用于教育、研究和授权的安全测试。"
            "在未经授权的情况下对软件进行逆向工程可能违反法律和服务条款。"
        )
        warning_label.setStyleSheet("background-color: #ffeb3b; color: #000; padding: 10px; border: 1px solid #ffc107;")
        warning_label.setWordWrap(True)
        
        layout.addWidget(warning_label)
        layout.addWidget(self.tabs)
        
    def closeEvent(self, event):
        reply = QMessageBox.question(self, '确认退出',
                                   '确定要退出游戏逆向工具箱吗？',
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 显示启动警告
    warning_msg = QMessageBox()
    warning_msg.setIcon(QMessageBox.Warning)
    warning_msg.setWindowTitle("法律与道德声明")
    warning_msg.setText(
        "游戏逆向工程工具箱 - 法律与道德声明\n\n"
        "此工具仅用于：\n"
        "• 教育目的和学习计算机科学\n"
        "• 安全研究和漏洞挖掘（在授权范围内）\n"
        "• 单机游戏模组开发（在游戏EULA允许的情况下）\n\n"
        "严禁用于：\n"
        "• 在线游戏作弊\n"
        "• 开发外挂程序\n"
        "• 侵犯知识产权\n"
        "• 任何非法活动\n\n"
        "继续使用即表示您同意承担所有法律责任。"
    )
    warning_msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    
    result = warning_msg.exec_()
    if result == QMessageBox.Cancel:
        sys.exit(0)
    
    window = GameReverseToolbox()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()