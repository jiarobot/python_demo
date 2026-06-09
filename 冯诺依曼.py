import sys
import time
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QLabel, 
                             QLineEdit, QTabWidget, QTableWidget, QTableWidgetItem,
                             QGroupBox, QSpinBox, QComboBox, QMessageBox, QSplitter)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor

# 冯·诺依曼架构仿真核心类
class VonNeumannComputer:
    def __init__(self, memory_size=256):
        # 内存初始化
        self.memory_size = memory_size
        self.memory = [0] * memory_size
        
        # 寄存器
        self.accumulator = 0  # 累加器
        self.program_counter = 0  # 程序计数器
        self.instruction_register = 0  # 指令寄存器
        self.memory_address_register = 0  # 内存地址寄存器
        self.memory_data_register = 0  # 内存数据寄存器
        
        # 控制单元状态
        self.is_running = False
        self.speed = 1  # 执行速度（指令/秒）
        
        # 输入输出缓冲区
        self.input_buffer = []
        self.output_buffer = []
        
        # 指令集
        self.instructions = {
            0x01: self._load,      # LDA - 加载到累加器
            0x02: self._store,     # STA - 存储累加器值
            0x03: self._add,       # ADD - 加法
            0x04: self._subtract,  # SUB - 减法
            0x05: self._jump,      # JMP - 跳转
            0x06: self._jump_if_zero,  # JZ - 如果零则跳转
            0x07: self._input,     # IN - 输入
            0x08: self._output,    # OUT - 输出
            0x09: self._halt,      # HLT - 停机
            0x0A: self._multiply,  # MUL - 乘法
            0x0B: self._compare,   # CMP - 比较
            0x0C: self._jump_if_greater,  # JG - 如果大于则跳转
        }
        
        # 汇编器映射
        self.assembly_map = {
            "LDA": 0x01,
            "STA": 0x02,
            "ADD": 0x03,
            "SUB": 0x04,
            "JMP": 0x05,
            "JZ": 0x06,
            "IN": 0x07,
            "OUT": 0x08,
            "HLT": 0x09,
            "MUL": 0x0A,
            "CMP": 0x0B,
            "JG": 0x0C,
        }
        
        # 程序状态
        self.program_loaded = False
        self.error_message = ""
        
    def reset(self):
        """重置计算机状态"""
        self.memory = [0] * self.memory_size
        self.accumulator = 0
        self.program_counter = 0
        self.instruction_register = 0
        self.memory_address_register = 0
        self.memory_data_register = 0
        self.is_running = False
        self.input_buffer = []
        self.output_buffer = []
        self.error_message = ""
        
    def load_program(self, program, start_address=0):
        """将程序加载到内存中"""
        self.reset()
        
        if start_address + len(program) > self.memory_size:
            raise ValueError("程序太大，无法装入内存")
            
        for i, instruction in enumerate(program):
            self.memory[start_address + i] = instruction
            
        self.program_counter = start_address
        self.program_loaded = True
        
    def assemble(self, source_code):
        """将汇编代码转换为机器码"""
        lines = source_code.split('\n')
        machine_code = []
        labels = {}
        
        # 第一遍：收集标签
        address = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';'):
                continue
                
            if line.endswith(':'):
                # 标签定义
                label = line[:-1]
                labels[label] = address
            else:
                # 指令
                parts = line.split()
                if parts:
                    address += 1
                    if len(parts) > 1:
                        address += 1  # 操作数占用一个位置
        
        # 第二遍：生成机器码
        address = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';') or line.endswith(':'):
                continue
                
            parts = line.split()
            if not parts:
                continue
                
            instruction = parts[0].upper()
            if instruction not in self.assembly_map:
                raise ValueError(f"未知指令: {instruction}")
                
            opcode = self.assembly_map[instruction]
            machine_code.append(opcode)
            
            if len(parts) > 1:
                operand = parts[1]
                # 处理标签或直接数值
                if operand in labels:
                    machine_code.append(labels[operand])
                elif operand.isdigit():
                    machine_code.append(int(operand))
                elif operand.startswith('0x'):
                    machine_code.append(int(operand[2:], 16))
                else:
                    raise ValueError(f"无效的操作数: {operand}")
            else:
                machine_code.append(0)  # 无操作数指令使用0作为占位符
                
            address += 2
            
        return machine_code
        
    def fetch(self):
        """取指阶段"""
        if self.program_counter >= self.memory_size:
            raise IndexError("程序计数器超出内存范围")
            
        self.memory_address_register = self.program_counter
        self.memory_data_register = self.memory[self.memory_address_register]
        self.instruction_register = self.memory_data_register
        self.program_counter += 1
        
    def decode(self):
        """译码阶段"""
        opcode = self.instruction_register
        if opcode not in self.instructions:
            raise ValueError(f"未知操作码: {opcode}")
            
        return opcode
        
    def execute(self, opcode):
        """执行阶段"""
        if self.program_counter >= self.memory_size:
            raise IndexError("程序计数器超出内存范围")
            
        operand = self.memory[self.program_counter]
        self.program_counter += 1
        
        # 执行指令
        self.instructions[opcode](operand)
        
    def step(self):
        """执行一个指令周期"""
        if not self.is_running:
            return False
            
        try:
            self.fetch()
            opcode = self.decode()
            self.execute(opcode)
            return True
        except Exception as e:
            self.error_message = str(e)
            self.is_running = False
            return False
            
    def run(self):
        """运行程序直到遇到HLT指令或错误"""
        self.is_running = True
        while self.is_running:
            if not self.step():
                break
            time.sleep(1 / self.speed)
            
    # 指令实现
    def _load(self, address):
        """LDA - 加载到累加器"""
        self.memory_address_register = address
        self.memory_data_register = self.memory[self.memory_address_register]
        self.accumulator = self.memory_data_register
        
    def _store(self, address):
        """STA - 存储累加器值"""
        self.memory_address_register = address
        self.memory_data_register = self.accumulator
        self.memory[self.memory_address_register] = self.memory_data_register
        
    def _add(self, address):
        """ADD - 加法"""
        self.memory_address_register = address
        self.memory_data_register = self.memory[self.memory_address_register]
        self.accumulator += self.memory_data_register
        
    def _subtract(self, address):
        """SUB - 减法"""
        self.memory_address_register = address
        self.memory_data_register = self.memory[self.memory_address_register]
        self.accumulator -= self.memory_data_register
        
    def _jump(self, address):
        """JMP - 跳转"""
        self.program_counter = address
        
    def _jump_if_zero(self, address):
        """JZ - 如果零则跳转"""
        if self.accumulator == 0:
            self.program_counter = address
            
    def _input(self, address):
        """IN - 输入"""
        if self.input_buffer:
            self.accumulator = self.input_buffer.pop(0)
        else:
            # 如果没有输入，暂停执行等待输入
            self.is_running = False
            
    def _output(self, address):
        """OUT - 输出"""
        self.output_buffer.append(self.accumulator)
        
    def _halt(self, address):
        """HLT - 停机"""
        self.is_running = False
        
    def _multiply(self, address):
        """MUL - 乘法"""
        self.memory_address_register = address
        self.memory_data_register = self.memory[self.memory_address_register]
        self.accumulator *= self.memory_data_register
        
    def _compare(self, address):
        """CMP - 比较"""
        self.memory_address_register = address
        self.memory_data_register = self.memory[self.memory_address_register]
        # 比较结果存储在累加器的特殊位中
        if self.accumulator > self.memory_data_register:
            self.accumulator = 1  # 大于
        elif self.accumulator < self.memory_data_register:
            self.accumulator = -1  # 小于
        else:
            self.accumulator = 0  # 等于
            
    def _jump_if_greater(self, address):
        """JG - 如果大于则跳转"""
        if self.accumulator > 0:
            self.program_counter = address


# 语法高亮类
class AssemblyHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 指令格式
        instruction_format = QTextCharFormat()
        instruction_format.setForeground(QColor(0, 0, 255))  # 蓝色
        instruction_format.setFontWeight(QFont.Bold)
        
        # 标签格式
        label_format = QTextCharFormat()
        label_format.setForeground(QColor(128, 0, 128))  # 紫色
        
        # 注释格式
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(0, 128, 0))  # 绿色
        
        # 数字格式
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(255, 0, 0))  # 红色
        
        # 定义高亮规则
        self.highlighting_rules = []
        
        # 指令
        instructions = ["LDA", "STA", "ADD", "SUB", "JMP", "JZ", "IN", "OUT", "HLT", "MUL", "CMP", "JG"]
        for instruction in instructions:
            pattern = r"\b" + instruction + r"\b"
            self.highlighting_rules.append((pattern, instruction_format))
            
        # 标签
        self.highlighting_rules.append((r"\b[A-Za-z_][A-Za-z0-9_]*:", label_format))
        
        # 注释
        self.highlighting_rules.append((r";[^\n]*", comment_format))
        
        # 数字
        self.highlighting_rules.append((r"\b\d+\b", number_format))
        self.highlighting_rules.append((r"\b0x[0-9A-Fa-f]+\b", number_format))
        
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            import re
            expression = re.compile(pattern)
            for match in expression.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, format)


# 主界面类
class VonNeumannSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.computer = VonNeumannComputer(256)
        self.init_ui()
        self.update_display()
        
    def init_ui(self):
        self.setWindowTitle("冯·诺依曼架构仿真平台")
        self.setGeometry(100, 100, 1200, 800)
        
        # 中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板
        left_panel = QVBoxLayout()
        
        # 代码编辑器
        code_group = QGroupBox("汇编代码编辑器")
        code_layout = QVBoxLayout()
        
        self.code_editor = QTextEdit()
        self.code_editor.setFont(QFont("Courier", 10))
        self.highlighter = AssemblyHighlighter(self.code_editor.document())
        
        # 示例程序
        example_code = """; 示例程序：计算斐波那契数列
START:
    IN          ; 输入n
    STA 100     ; 存储n
    LDA 1       ; 初始化a=1
    STA 101     ; 存储a
    LDA 1       ; 初始化b=1
    STA 102     ; 存储b
    LDA 0       ; 初始化计数器
    STA 103     ; 存储计数器
    
LOOP:
    LDA 103     ; 加载计数器
    ADD 1       ; 计数器加1
    STA 103     ; 存储计数器
    CMP 100     ; 比较计数器和n
    JG END      ; 如果计数器>n，结束
    
    LDA 101     ; 加载a
    ADD 102     ; a + b
    STA 104     ; 存储临时结果
    LDA 102     ; 加载b
    STA 101     ; a = b
    LDA 104     ; 加载临时结果
    STA 102     ; b = 临时结果
    JMP LOOP    ; 继续循环
    
END:
    LDA 102     ; 加载结果
    OUT         ; 输出结果
    HLT         ; 停止"""
        
        self.code_editor.setPlainText(example_code)
        code_layout.addWidget(self.code_editor)
        
        # 代码操作按钮
        code_buttons_layout = QHBoxLayout()
        self.assemble_btn = QPushButton("汇编")
        self.assemble_btn.clicked.connect(self.assemble_code)
        code_buttons_layout.addWidget(self.assemble_btn)
        
        self.load_btn = QPushButton("加载到内存")
        self.load_btn.clicked.connect(self.load_program)
        code_buttons_layout.addWidget(self.load_btn)
        
        self.clear_btn = QPushButton("清空代码")
        self.clear_btn.clicked.connect(self.clear_code)
        code_buttons_layout.addWidget(self.clear_btn)
        
        code_layout.addLayout(code_buttons_layout)
        code_group.setLayout(code_layout)
        left_panel.addWidget(code_group)
        
        # 内存显示
        memory_group = QGroupBox("内存")
        memory_layout = QVBoxLayout()
        
        self.memory_table = QTableWidget()
        self.memory_table.setColumnCount(16)
        self.memory_table.setRowCount(16)
        
        # 设置表头
        headers = [f"{i:02X}" for i in range(16)]
        self.memory_table.setHorizontalHeaderLabels(headers)
        vertical_headers = [f"{i:02X}0" for i in range(16)]
        self.memory_table.setVerticalHeaderLabels(vertical_headers)
        
        memory_layout.addWidget(self.memory_table)
        memory_group.setLayout(memory_layout)
        left_panel.addWidget(memory_group)
        
        # 右侧面板
        right_panel = QVBoxLayout()
        
        # 寄存器显示
        registers_group = QGroupBox("寄存器状态")
        registers_layout = QVBoxLayout()
        
        self.accumulator_label = QLabel("累加器 (ACC): 0")
        self.program_counter_label = QLabel("程序计数器 (PC): 0")
        self.instruction_register_label = QLabel("指令寄存器 (IR): 0")
        self.memory_address_register_label = QLabel("内存地址寄存器 (MAR): 0")
        self.memory_data_register_label = QLabel("内存数据寄存器 (MDR): 0")
        
        registers_layout.addWidget(self.accumulator_label)
        registers_layout.addWidget(self.program_counter_label)
        registers_layout.addWidget(self.instruction_register_label)
        registers_layout.addWidget(self.memory_address_register_label)
        registers_layout.addWidget(self.memory_data_register_label)
        
        registers_group.setLayout(registers_layout)
        right_panel.addWidget(registers_group)
        
        # 控制面板
        control_group = QGroupBox("控制面板")
        control_layout = QVBoxLayout()
        
        # 速度控制
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("执行速度:"))
        self.speed_spinbox = QSpinBox()
        self.speed_spinbox.setRange(1, 1000)
        self.speed_spinbox.setValue(10)
        self.speed_spinbox.valueChanged.connect(self.update_speed)
        speed_layout.addWidget(self.speed_spinbox)
        speed_layout.addWidget(QLabel("指令/秒"))
        speed_layout.addStretch()
        control_layout.addLayout(speed_layout)
        
        # 控制按钮
        buttons_layout = QHBoxLayout()
        self.run_btn = QPushButton("运行")
        self.run_btn.clicked.connect(self.run_program)
        buttons_layout.addWidget(self.run_btn)
        
        self.step_btn = QPushButton("单步执行")
        self.step_btn.clicked.connect(self.step_program)
        buttons_layout.addWidget(self.step_btn)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self.pause_program)
        buttons_layout.addWidget(self.pause_btn)
        
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset_computer)
        buttons_layout.addWidget(self.reset_btn)
        
        control_layout.addLayout(buttons_layout)
        control_group.setLayout(control_layout)
        right_panel.addWidget(control_group)
        
        # 输入输出
        io_group = QGroupBox("输入/输出")
        io_layout = QVBoxLayout()
        
        # 输入
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("输入:"))
        self.input_edit = QLineEdit()
        input_layout.addWidget(self.input_edit)
        self.input_btn = QPushButton("发送")
        self.input_btn.clicked.connect(self.send_input)
        input_layout.addWidget(self.input_btn)
        io_layout.addLayout(input_layout)
        
        # 输出
        output_layout = QVBoxLayout()
        output_layout.addWidget(QLabel("输出:"))
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        output_layout.addWidget(self.output_display)
        io_layout.addLayout(output_layout)
        
        io_group.setLayout(io_layout)
        right_panel.addWidget(io_group)
        
        # 状态信息
        status_group = QGroupBox("状态信息")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        right_panel.addWidget(status_group)
        
        # 添加左右面板到主布局
        main_layout.addLayout(left_panel, 2)
        main_layout.addLayout(right_panel, 1)
        
        # 定时器用于更新显示
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(100)  # 每100毫秒更新一次
        
    def assemble_code(self):
        """汇编代码"""
        source_code = self.code_editor.toPlainText()
        try:
            machine_code = self.computer.assemble(source_code)
            self.status_label.setText(f"汇编成功，生成 {len(machine_code)} 字节机器码")
        except Exception as e:
            self.status_label.setText(f"汇编错误: {str(e)}")
            QMessageBox.critical(self, "汇编错误", str(e))
            
    def load_program(self):
        """加载程序到内存"""
        source_code = self.code_editor.toPlainText()
        try:
            machine_code = self.computer.assemble(source_code)
            self.computer.load_program(machine_code)
            self.status_label.setText(f"程序已加载到内存，起始地址: 0")
            self.update_memory_display()
        except Exception as e:
            self.status_label.setText(f"加载错误: {str(e)}")
            QMessageBox.critical(self, "加载错误", str(e))
            
    def clear_code(self):
        """清空代码编辑器"""
        self.code_editor.clear()
        
    def update_speed(self):
        """更新执行速度"""
        self.computer.speed = self.speed_spinbox.value()
        
    def run_program(self):
        """运行程序"""
        if not self.computer.program_loaded:
            QMessageBox.warning(self, "警告", "请先加载程序到内存")
            return
            
        self.computer.is_running = True
        # 在新线程中运行程序，避免阻塞UI
        thread = threading.Thread(target=self.computer.run)
        thread.daemon = True
        thread.start()
        
    def step_program(self):
        """单步执行程序"""
        if not self.computer.program_loaded:
            QMessageBox.warning(self, "警告", "请先加载程序到内存")
            return
            
        self.computer.is_running = True
        self.computer.step()
        
    def pause_program(self):
        """暂停程序执行"""
        self.computer.is_running = False
        
    def reset_computer(self):
        """重置计算机"""
        self.computer.reset()
        self.output_display.clear()
        self.status_label.setText("计算机已重置")
        
    def send_input(self):
        """发送输入"""
        text = self.input_edit.text()
        if text.isdigit():
            self.computer.input_buffer.append(int(text))
            self.input_edit.clear()
            
            # 如果计算机在等待输入，恢复执行
            if not self.computer.is_running and self.computer.instruction_register == 0x07:
                self.computer.is_running = True
                thread = threading.Thread(target=self.computer.run)
                thread.daemon = True
                thread.start()
                
    def update_display(self):
        """更新显示"""
        # 更新寄存器显示
        self.accumulator_label.setText(f"累加器 (ACC): {self.computer.accumulator}")
        self.program_counter_label.setText(f"程序计数器 (PC): {self.computer.program_counter}")
        self.instruction_register_label.setText(f"指令寄存器 (IR): {self.computer.instruction_register:02X}")
        self.memory_address_register_label.setText(f"内存地址寄存器 (MAR): {self.computer.memory_address_register}")
        self.memory_data_register_label.setText(f"内存数据寄存器 (MDR): {self.computer.memory_data_register}")
        
        # 更新内存显示
        self.update_memory_display()
        
        # 更新输出显示
        if self.computer.output_buffer:
            for value in self.computer.output_buffer:
                self.output_display.append(f"> {value}")
            self.computer.output_buffer.clear()
            
        # 更新状态显示
        if self.computer.is_running:
            self.status_label.setText("运行中...")
        elif self.computer.error_message:
            self.status_label.setText(f"错误: {self.computer.error_message}")
        else:
            self.status_label.setText("就绪")
            
    def update_memory_display(self):
        """更新内存显示"""
        for i in range(16):
            for j in range(16):
                address = i * 16 + j
                if address < self.computer.memory_size:
                    value = self.computer.memory[address]
                    item = QTableWidgetItem(f"{value:02X}")
                    
                    # 高亮当前程序计数器位置
                    if address == self.computer.program_counter:
                        item.setBackground(QColor(255, 255, 0))  # 黄色
                        
                    self.memory_table.setItem(i, j, item)


# 主函数
def main():
    app = QApplication(sys.argv)
    simulator = VonNeumannSimulator()
    simulator.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()