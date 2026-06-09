import sys
import time
import threading
import random
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QLabel, 
                             QLineEdit, QTabWidget, QTableWidget, QTableWidgetItem,
                             QGroupBox, QSpinBox, QComboBox, QMessageBox, 
                             QSplitter, QProgressBar, QCheckBox, QSlider,
                             QFileDialog, QListWidget, QTreeWidget, QTreeWidgetItem,
                             QHeaderView, QDialog, QDialogButtonBox, QFormLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QPalette
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis
from PyQt5.QtCore import QPointF

# 高级冯·诺依曼架构仿真核心类
class AdvancedVonNeumannComputer:
    def __init__(self, memory_size=1024, cache_size=64, num_registers=16):
        # 内存系统
        self.memory_size = memory_size
        self.memory = [0] * memory_size
        
        # 缓存系统
        self.cache_size = cache_size
        self.cache = [None] * cache_size  # (address, data, dirty)
        self.cache_hits = 0
        self.cache_misses = 0
        
        # 扩展寄存器组
        self.num_registers = num_registers
        self.registers = [0] * num_registers
        # 特殊寄存器映射
        self.ACC = 0    # 累加器
        self.PC = 1     # 程序计数器
        self.IR = 2     # 指令寄存器
        self.MAR = 3    # 内存地址寄存器
        self.MDR = 4    # 内存数据寄存器
        self.SP = 5     # 堆栈指针
        self.FLAGS = 6  # 状态标志寄存器
        
        # 控制单元状态
        self.is_running = False
        self.speed = 10  # 执行速度（指令/秒）
        self.pipeline_enabled = False
        self.interrupts_enabled = True
        
        # 输入输出系统
        self.input_buffer = []
        self.output_buffer = []
        self.devices = {
            'keyboard': {'buffer': [], 'interrupt': 0x10},
            'display': {'buffer': [], 'interrupt': 0x11},
            'disk': {'buffer': [], 'interrupt': 0x12}
        }
        
        # 中断系统
        self.interrupt_queue = []
        self.interrupt_handlers = {
            0x10: self._keyboard_interrupt,
            0x11: self._display_interrupt,
            0x12: self._disk_interrupt,
            0x20: self._timer_interrupt,
            0x30: self._system_call
        }
        
        # 流水线寄存器
        self.IF_ID = {'instruction': 0, 'pc': 0}
        self.ID_EX = {'opcode': 0, 'operand1': 0, 'operand2': 0, 'pc': 0}
        self.EX_MEM = {'alu_result': 0, 'write_data': 0, 'write_reg': 0, 'mem_read': False, 'mem_write': False}
        self.MEM_WB = {'write_data': 0, 'write_reg': 0, 'reg_write': False}
        
        # 进程管理
        self.processes = []
        self.current_process = None
        self.process_id_counter = 1
        
        # 性能统计
        self.instructions_executed = 0
        self.cycles_executed = 0
        self.start_time = time.time()
        
        # 指令集扩展
        self.instructions = {
            # 基本指令
            0x01: ('LDA', self._load, 1),        # 加载到累加器
            0x02: ('STA', self._store, 1),       # 存储累加器值
            0x03: ('ADD', self._add, 1),         # 加法
            0x04: ('SUB', self._subtract, 1),    # 减法
            0x05: ('JMP', self._jump, 1),        # 跳转
            0x06: ('JZ', self._jump_if_zero, 1), # 如果零则跳转
            0x07: ('IN', self._input, 0),        # 输入
            0x08: ('OUT', self._output, 0),      # 输出
            0x09: ('HLT', self._halt, 0),        # 停机
            
            # 扩展指令
            0x0A: ('MUL', self._multiply, 1),    # 乘法
            0x0B: ('DIV', self._divide, 1),      # 除法
            0x0C: ('AND', self._and, 1),         # 逻辑与
            0x0D: ('OR', self._or, 1),           # 逻辑或
            0x0E: ('XOR', self._xor, 1),         # 逻辑异或
            0x0F: ('NOT', self._not, 0),         # 逻辑非
            0x10: ('SHL', self._shift_left, 1),  # 左移
            0x11: ('SHR', self._shift_right, 1), # 右移
            0x12: ('CMP', self._compare, 1),     # 比较
            0x13: ('JG', self._jump_if_greater, 1), # 如果大于则跳转
            0x14: ('JL', self._jump_if_less, 1), # 如果小于则跳转
            0x15: ('CALL', self._call, 1),       # 调用子程序
            0x16: ('RET', self._return, 0),      # 从子程序返回
            0x17: ('PUSH', self._push, 1),       # 压栈
            0x18: ('POP', self._pop, 0),         # 出栈
            0x19: ('INT', self._interrupt, 1),   # 软件中断
            0x1A: ('IRET', self._iret, 0),       # 中断返回
            0x1B: ('MOV', self._move, 2),        # 寄存器间移动
            0x1C: ('INC', self._increment, 1),   # 递增
            0x1D: ('DEC', self._decrement, 1),   # 递减
            0x1E: ('NOP', self._nop, 0),         # 空操作
            0x1F: ('TEST', self._test, 1),       # 测试
        }
        
        # 汇编器映射
        self.assembly_map = {name: opcode for opcode, (name, _, _) in self.instructions.items()}
        
        # 系统状态
        self.program_loaded = False
        self.error_message = ""
        self.debug_mode = False
        
    def reset(self):
        """重置计算机状态"""
        self.memory = [0] * self.memory_size
        self.cache = [None] * self.cache_size
        self.registers = [0] * self.num_registers
        self.is_running = False
        self.input_buffer = []
        self.output_buffer = []
        self.interrupt_queue = []
        self.processes = []
        self.current_process = None
        self.instructions_executed = 0
        self.cycles_executed = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.start_time = time.time()
        self.error_message = ""
        
        # 重置流水线寄存器
        self.IF_ID = {'instruction': 0, 'pc': 0}
        self.ID_EX = {'opcode': 0, 'operand1': 0, 'operand2': 0, 'pc': 0}
        self.EX_MEM = {'alu_result': 0, 'write_data': 0, 'write_reg': 0, 'mem_read': False, 'mem_write': False}
        self.MEM_WB = {'write_data': 0, 'write_reg': 0, 'reg_write': False}
        
    def load_program(self, program, start_address=0, process_name="Main"):
        """将程序加载到内存中"""
        if start_address + len(program) > self.memory_size:
            raise ValueError("程序太大，无法装入内存")
            
        for i, instruction in enumerate(program):
            self.memory[start_address + i] = instruction
            
        # 创建进程
        process = {
            'id': self.process_id_counter,
            'name': process_name,
            'pc': start_address,
            'state': 'ready',
            'registers': self.registers.copy(),
            'memory_range': (start_address, start_address + len(program)),
            'start_time': time.time()
        }
        self.process_id_counter += 1
        self.processes.append(process)
        
        if not self.current_process:
            self.current_process = process
            self.registers[self.PC] = start_address
            
        self.program_loaded = True
        
    def assemble(self, source_code):
        """将汇编代码转换为机器码"""
        lines = source_code.split('\n')
        machine_code = []
        labels = {}
        variables = {}
        current_address = 0
        
        # 第一遍：收集标签和变量
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';'):
                continue
                
            # 处理标签
            if line.endswith(':'):
                label = line[:-1]
                labels[label] = current_address
            # 处理变量定义
            elif line.upper().startswith('DB ') or line.upper().startswith('DW '):
                parts = line.split()
                if len(parts) >= 2:
                    var_name = parts[0]
                    var_value = parts[1]
                    variables[var_name] = (current_address, var_value)
                    current_address += 1
            else:
                # 指令
                parts = line.split()
                if parts:
                    current_address += 1
                    if len(parts) > 1:
                        # 检查操作数数量
                        opcode = parts[0].upper()
                        if opcode in self.assembly_map:
                            _, _, num_operands = self.instructions[self.assembly_map[opcode]]
                            current_address += num_operands
        
        # 第二遍：生成机器码
        current_address = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';') or line.endswith(':'):
                continue
                
            # 处理变量定义
            if line.upper().startswith('DB ') or line.upper().startswith('DW '):
                parts = line.split()
                if len(parts) >= 2:
                    var_value = parts[1]
                    if var_value.isdigit():
                        machine_code.append(int(var_value))
                    elif var_value.startswith('0x'):
                        machine_code.append(int(var_value[2:], 16))
                    elif var_value in labels:
                        machine_code.append(labels[var_value])
                    else:
                        machine_code.append(0)
                    current_address += 1
                continue
                
            parts = line.split()
            if not parts:
                continue
                
            instruction = parts[0].upper()
            if instruction not in self.assembly_map:
                raise ValueError(f"未知指令: {instruction}")
                
            opcode = self.assembly_map[instruction]
            machine_code.append(opcode)
            current_address += 1
            
            # 处理操作数
            _, _, num_operands = self.instructions[opcode]
            if num_operands > 0:
                for i in range(1, min(num_operands + 1, len(parts))):
                    operand = parts[i].upper().replace(',', '')
                    
                    # 处理寄存器引用
                    if operand.startswith('R'):
                        reg_num = int(operand[1:])
                        machine_code.append(reg_num)
                    # 处理标签
                    elif operand in labels:
                        machine_code.append(labels[operand])
                    # 处理变量
                    elif operand in variables:
                        machine_code.append(variables[operand][0])
                    # 处理直接数值
                    elif operand.isdigit():
                        machine_code.append(int(operand))
                    elif operand.startswith('0x'):
                        machine_code.append(int(operand[2:], 16))
                    else:
                        machine_code.append(0)
                # 填充缺失的操作数
                for i in range(len(parts) - 1, num_operands):
                    machine_code.append(0)
                    
        return machine_code
        
    def cache_read(self, address):
        """从缓存读取数据"""
        cache_index = address % self.cache_size
        
        if self.cache[cache_index] and self.cache[cache_index][0] == address:
            self.cache_hits += 1
            return self.cache[cache_index][1]
        else:
            self.cache_misses += 1
            data = self.memory[address]
            self.cache[cache_index] = (address, data, False)
            return data
            
    def cache_write(self, address, data):
        """写入数据到缓存"""
        cache_index = address % self.cache_size
        self.cache[cache_index] = (address, data, True)
        # 写通策略：同时写入内存
        self.memory[address] = data
        
    def fetch(self):
        """取指阶段"""
        if self.registers[self.PC] >= self.memory_size:
            raise IndexError("程序计数器超出内存范围")
            
        self.registers[self.MAR] = self.registers[self.PC]
        self.registers[self.IR] = self.cache_read(self.registers[self.MAR])
        self.IF_ID['instruction'] = self.registers[self.IR]
        self.IF_ID['pc'] = self.registers[self.PC]
        self.registers[self.PC] += 1
        
    def decode(self):
        """译码阶段"""
        instruction = self.IF_ID['instruction']
        if instruction not in self.instructions:
            raise ValueError(f"未知操作码: {instruction}")
            
        opcode = instruction
        name, func, num_operands = self.instructions[opcode]
        
        operands = []
        for i in range(num_operands):
            if self.IF_ID['pc'] + i < self.memory_size:
                operands.append(self.cache_read(self.IF_ID['pc'] + i))
            else:
                operands.append(0)
                
        self.ID_EX['opcode'] = opcode
        self.ID_EX['operand1'] = operands[0] if num_operands > 0 else 0
        self.ID_EX['operand2'] = operands[1] if num_operands > 1 else 0
        self.ID_EX['pc'] = self.IF_ID['pc']
        
        # 更新PC以跳过操作数
        if num_operands > 0:
            self.registers[self.PC] += num_operands
            
        return opcode, operands
        
    def execute(self, opcode, operands):
        """执行阶段"""
        name, func, num_operands = self.instructions[opcode]
        
        # ALU操作
        if opcode in [0x03, 0x04, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x10, 0x11]:  # 算术和逻辑运算
            result = func(operands[0])
            self.EX_MEM['alu_result'] = result
            self.EX_MEM['write_reg'] = self.ACC
            self.EX_MEM['reg_write'] = True
        elif opcode in [0x01, 0x02, 0x05, 0x06, 0x13, 0x14, 0x15, 0x17, 0x18]:  # 内存和跳转指令
            func(operands[0] if num_operands > 0 else 0)
        else:
            func(operands[0] if num_operands > 0 else 0)
            
        self.instructions_executed += 1
        
    def memory_access(self):
        """内存访问阶段"""
        if self.EX_MEM['mem_read']:
            self.EX_MEM['write_data'] = self.cache_read(self.EX_MEM['alu_result'])
        elif self.EX_MEM['mem_write']:
            self.cache_write(self.EX_MEM['alu_result'], self.EX_MEM['write_data'])
            
    def write_back(self):
        """写回阶段"""
        if self.MEM_WB['reg_write']:
            if self.MEM_WB['write_reg'] < self.num_registers:
                self.registers[self.MEM_WB['write_reg']] = self.MEM_WB['write_data']
                
    def pipeline_step(self):
        """流水线执行一个周期"""
        if not self.is_running:
            return False
            
        try:
            # 写回阶段
            self.write_back()
            
            # 内存访问阶段
            self.memory_access()
            self.MEM_WB = self.EX_MEM.copy()
            
            # 执行阶段
            opcode, operands = self.decode()
            self.execute(opcode, operands)
            self.EX_MEM = {
                'alu_result': self.registers[self.ACC] if opcode in [0x03, 0x04, 0x0A, 0x0B] else 0,
                'write_data': self.registers[self.ACC],
                'write_reg': self.ACC,
                'mem_read': opcode == 0x01,  # LDA
                'mem_write': opcode == 0x02,  # STA
                'reg_write': opcode in [0x01, 0x03, 0x04, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11]
            }
            
            # 取指阶段
            self.fetch()
            
            self.cycles_executed += 1
            
            # 检查中断
            if self.interrupts_enabled and self.interrupt_queue:
                self._handle_interrupt()
                
            return True
        except Exception as e:
            self.error_message = str(e)
            self.is_running = False
            return False
            
    def step(self):
        """执行一个指令周期"""
        if self.pipeline_enabled:
            return self.pipeline_step()
        else:
            return self.simple_step()
            
    def simple_step(self):
        """简单执行一个指令周期（非流水线）"""
        if not self.is_running:
            return False
            
        try:
            self.fetch()
            opcode, operands = self.decode()
            self.execute(opcode, operands)
            self.cycles_executed += 1
            
            # 检查中断
            if self.interrupts_enabled and self.interrupt_queue:
                self._handle_interrupt()
                
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
            
    def _handle_interrupt(self):
        """处理中断"""
        if not self.interrupt_queue:
            return
            
        interrupt_type = self.interrupt_queue.pop(0)
        
        # 保存当前状态
        self._push(self.registers[self.PC])
        self._push(self.registers[self.FLAGS])
        
        # 跳转到中断处理程序
        if interrupt_type in self.interrupt_handlers:
            self.interrupt_handlers[interrupt_type]()
            
    def request_interrupt(self, interrupt_type):
        """请求中断"""
        if self.interrupts_enabled:
            self.interrupt_queue.append(interrupt_type)
            
    # 中断处理程序
    def _keyboard_interrupt(self):
        """键盘中断处理"""
        if self.devices['keyboard']['buffer']:
            char = self.devices['keyboard']['buffer'].pop(0)
            self.registers[self.ACC] = ord(char) if isinstance(char, str) else char
            
    def _display_interrupt(self):
        """显示中断处理"""
        if self.registers[self.ACC] != 0:
            self.output_buffer.append(chr(self.registers[self.ACC]))
            
    def _disk_interrupt(self):
        """磁盘中断处理"""
        # 模拟磁盘操作
        pass
        
    def _timer_interrupt(self):
        """定时器中断处理"""
        # 进程调度
        self._schedule_processes()
        
    def _system_call(self):
        """系统调用处理"""
        syscall_num = self.registers[self.ACC]
        # 实现基本的系统调用
        if syscall_num == 1:  # 退出进程
            self._terminate_current_process()
        elif syscall_num == 2:  # 创建进程
            # 简化版的进程创建
            pass
            
    def _schedule_processes(self):
        """进程调度"""
        if len(self.processes) <= 1:
            return
            
        # 简单的轮转调度
        current_index = self.processes.index(self.current_process)
        next_index = (current_index + 1) % len(self.processes)
        self._switch_process(self.processes[next_index])
        
    def _switch_process(self, process):
        """切换进程"""
        # 保存当前进程状态
        if self.current_process:
            self.current_process['registers'] = self.registers.copy()
            self.current_process['state'] = 'ready'
            
        # 恢复新进程状态
        self.current_process = process
        self.current_process['state'] = 'running'
        self.registers = process['registers'].copy()
        
    def _terminate_current_process(self):
        """终止当前进程"""
        if self.current_process:
            self.processes.remove(self.current_process)
            if self.processes:
                self._switch_process(self.processes[0])
            else:
                self.current_process = None
                self.is_running = False
                
    # 扩展指令实现
    def _load(self, address):
        """LDA - 加载到累加器"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.cache_read(self.registers[self.MAR])
        self.registers[self.ACC] = self.registers[self.MDR]
        
    def _store(self, address):
        """STA - 存储累加器值"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.registers[self.ACC]
        self.cache_write(self.registers[self.MAR], self.registers[self.MDR])
        
    def _add(self, address):
        """ADD - 加法"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.cache_read(self.registers[self.MAR])
        self.registers[self.ACC] += self.registers[self.MDR]
        
    def _subtract(self, address):
        """SUB - 减法"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.cache_read(self.registers[self.MAR])
        self.registers[self.ACC] -= self.registers[self.MDR]
        
    def _jump(self, address):
        """JMP - 跳转"""
        self.registers[self.PC] = address
        
    def _jump_if_zero(self, address):
        """JZ - 如果零则跳转"""
        if self.registers[self.ACC] == 0:
            self.registers[self.PC] = address
            
    def _input(self, address):
        """IN - 输入"""
        if self.input_buffer:
            self.registers[self.ACC] = self.input_buffer.pop(0)
        else:
            # 如果没有输入，暂停执行等待输入
            self.is_running = False
            
    def _output(self, address):
        """OUT - 输出"""
        self.output_buffer.append(self.registers[self.ACC])
        
    def _halt(self, address):
        """HLT - 停机"""
        self.is_running = False
        
    def _multiply(self, address):
        """MUL - 乘法"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.cache_read(self.registers[self.MAR])
        self.registers[self.ACC] *= self.registers[self.MDR]
        
    def _divide(self, address):
        """DIV - 除法"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.cache_read(self.registers[self.MAR])
        if self.registers[self.MDR] != 0:
            self.registers[self.ACC] //= self.registers[self.MDR]
        else:
            raise ValueError("除零错误")
            
    def _and(self, address):
        """AND - 逻辑与"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.cache_read(self.registers[self.MAR])
        self.registers[self.ACC] &= self.registers[self.MDR]
        
    def _or(self, address):
        """OR - 逻辑或"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.cache_read(self.registers[self.MAR])
        self.registers[self.ACC] |= self.registers[self.MDR]
        
    def _xor(self, address):
        """XOR - 逻辑异或"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.cache_read(self.registers[self.MAR])
        self.registers[self.ACC] ^= self.registers[self.MDR]
        
    def _not(self, address):
        """NOT - 逻辑非"""
        self.registers[self.ACC] = ~self.registers[self.ACC]
        
    def _shift_left(self, address):
        """SHL - 左移"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.cache_read(self.registers[self.MAR])
        self.registers[self.ACC] <<= self.registers[self.MDR]
        
    def _shift_right(self, address):
        """SHR - 右移"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.cache_read(self.registers[self.MAR])
        self.registers[self.ACC] >>= self.registers[self.MDR]
        
    def _compare(self, address):
        """CMP - 比较"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.cache_read(self.registers[self.MAR])
        # 比较结果存储在标志寄存器中
        if self.registers[self.ACC] > self.registers[self.MDR]:
            self.registers[self.FLAGS] = 1  # 大于
        elif self.registers[self.ACC] < self.registers[self.MDR]:
            self.registers[self.FLAGS] = -1  # 小于
        else:
            self.registers[self.FLAGS] = 0  # 等于
            
    def _jump_if_greater(self, address):
        """JG - 如果大于则跳转"""
        if self.registers[self.FLAGS] > 0:
            self.registers[self.PC] = address
            
    def _jump_if_less(self, address):
        """JL - 如果小于则跳转"""
        if self.registers[self.FLAGS] < 0:
            self.registers[self.PC] = address
            
    def _call(self, address):
        """CALL - 调用子程序"""
        # 保存返回地址
        self._push(self.registers[self.PC])
        # 跳转到子程序
        self.registers[self.PC] = address
        
    def _return(self, address):
        """RET - 从子程序返回"""
        # 恢复返回地址
        self.registers[self.PC] = self._pop()
        
    def _push(self, address):
        """PUSH - 压栈"""
        if self.registers[self.SP] > 0:
            self.registers[self.SP] -= 1
            self.cache_write(self.registers[self.SP], self.registers[self.ACC])
        
    def _pop(self, address=0):
        """POP - 出栈"""
        if self.registers[self.SP] < self.memory_size - 1:
            value = self.cache_read(self.registers[self.SP])
            self.registers[self.SP] += 1
            self.registers[self.ACC] = value
            return value
        return 0
        
    def _interrupt(self, address):
        """INT - 软件中断"""
        self.request_interrupt(address)
        
    def _iret(self, address):
        """IRET - 中断返回"""
        # 恢复标志寄存器
        self.registers[self.FLAGS] = self._pop()
        # 恢复程序计数器
        self.registers[self.PC] = self._pop()
        
    def _move(self, reg1, reg2):
        """MOV - 寄存器间移动"""
        if reg1 < self.num_registers and reg2 < self.num_registers:
            self.registers[reg2] = self.registers[reg1]
            
    def _increment(self, address):
        """INC - 递增"""
        self.registers[self.ACC] += 1
        
    def _decrement(self, address):
        """DEC - 递减"""
        self.registers[self.ACC] -= 1
        
    def _nop(self, address):
        """NOP - 空操作"""
        pass
        
    def _test(self, address):
        """TEST - 测试"""
        self.registers[self.MAR] = address
        self.registers[self.MDR] = self.cache_read(self.registers[self.MAR])
        # 测试结果存储在标志寄存器中
        self.registers[self.FLAGS] = self.registers[self.ACC] & self.registers[self.MDR]


# 语法高亮类
class AssemblyHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 指令格式
        instruction_format = QTextCharFormat()
        instruction_format.setForeground(QColor(0, 0, 255))  # 蓝色
        instruction_format.setFontWeight(QFont.Bold)
        
        # 寄存器格式
        register_format = QTextCharFormat()
        register_format.setForeground(QColor(255, 0, 0))  # 红色
        
        # 标签格式
        label_format = QTextCharFormat()
        label_format.setForeground(QColor(128, 0, 128))  # 紫色
        label_format.setFontWeight(QFont.Bold)
        
        # 注释格式
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(0, 128, 0))  # 绿色
        
        # 数字格式
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(255, 0, 0))  # 红色
        
        # 字符串格式
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(255, 165, 0))  # 橙色
        
        # 定义高亮规则
        self.highlighting_rules = []
        
        # 指令
        instructions = ["LDA", "STA", "ADD", "SUB", "JMP", "JZ", "IN", "OUT", "HLT", 
                       "MUL", "DIV", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "CMP",
                       "JG", "JL", "CALL", "RET", "PUSH", "POP", "INT", "IRET", "MOV",
                       "INC", "DEC", "NOP", "TEST", "DB", "DW"]
        for instruction in instructions:
            pattern = r"\b" + instruction + r"\b"
            self.highlighting_rules.append((pattern, instruction_format))
            
        # 寄存器
        self.highlighting_rules.append((r"\bR[0-9]+\b", register_format))
        
        # 标签
        self.highlighting_rules.append((r"\b[A-Za-z_][A-Za-z0-9_]*:", label_format))
        
        # 注释
        self.highlighting_rules.append((r";[^\n]*", comment_format))
        
        # 数字
        self.highlighting_rules.append((r"\b\d+\b", number_format))
        self.highlighting_rules.append((r"\b0x[0-9A-Fa-f]+\b", number_format))
        
        # 字符串
        self.highlighting_rules.append((r"'.*?'", string_format))
        self.highlighting_rules.append((r'".*?"', string_format))
        
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            import re
            expression = re.compile(pattern)
            for match in expression.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, format)


# 性能监控线程
class PerformanceMonitor(QThread):
    update_signal = pyqtSignal(dict)
    
    def __init__(self, computer):
        super().__init__()
        self.computer = computer
        self.running = True
        
    def run(self):
        while self.running:
            stats = {
                'instructions': self.computer.instructions_executed,
                'cycles': self.computer.cycles_executed,
                'cache_hits': self.computer.cache_hits,
                'cache_misses': self.computer.cache_misses,
                'running_time': time.time() - self.computer.start_time,
                'processes': len(self.computer.processes)
            }
            self.update_signal.emit(stats)
            time.sleep(0.5)
            
    def stop(self):
        self.running = False


# 断点对话框
class BreakpointDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置断点")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout(self)
        
        self.address_input = QLineEdit()
        self.condition_input = QLineEdit()
        
        layout.addRow("地址:", self.address_input)
        layout.addRow("条件:", self.condition_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow(buttons)
        
    def get_breakpoint(self):
        address = self.address_input.text()
        condition = self.condition_input.text()
        return address, condition


# 主界面类
class AdvancedVonNeumannSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.PC = 1
        self.computer = AdvancedVonNeumannComputer(1024, 64, 16)
        self.performance_monitor = PerformanceMonitor(self.computer)
        self.breakpoints = {}
        self.init_ui()
        self.update_display()
        self.performance_monitor.update_signal.connect(self.update_performance)
        self.performance_monitor.start()
        
    def init_ui(self):
        self.setWindowTitle("高级冯·诺依曼架构仿真平台")
        self.setGeometry(100, 100, 1400, 900)
        
        # 中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板
        left_panel = QVBoxLayout()
        
        # 选项卡控件
        self.tabs = QTabWidget()
        
        # 代码编辑器选项卡
        code_tab = QWidget()
        code_layout = QVBoxLayout(code_tab)
        
        code_group = QGroupBox("汇编代码编辑器")
        code_group_layout = QVBoxLayout()
        
        self.code_editor = QTextEdit()
        self.code_editor.setFont(QFont("Courier", 10))
        self.highlighter = AssemblyHighlighter(self.code_editor.document())
        
        # 示例程序
        example_code = """; 高级示例程序：多进程计算
; 主程序
MAIN:
    MOV R0, R1        ; 初始化
    LDA 10
    STA 100           ; 设置计算次数
    
    ; 创建进程1
    LDA 1
    INT 0x30          ; 系统调用创建进程
    JMP PROCESS1
    
    ; 创建进程2
    LDA 2
    INT 0x30
    JMP PROCESS2
    
PROCESS1:
    LDA 0
    STA 101           ; 进程1计数器
LOOP1:
    LDA 101
    ADD 1
    STA 101
    OUT               ; 输出进程1计数
    CMP 100
    JL LOOP1
    HLT
    
PROCESS2:
    LDA 0
    STA 102           ; 进程2计数器
LOOP2:
    LDA 102
    ADD 2
    STA 102
    OUT               ; 输出进程2计数
    CMP 100
    JL LOOP2
    HLT
    
; 数据段
DB 10                ; 计算次数"""
        
        self.code_editor.setPlainText(example_code)
        code_group_layout.addWidget(self.code_editor)
        
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
        
        self.save_btn = QPushButton("保存代码")
        self.save_btn.clicked.connect(self.save_code)
        code_buttons_layout.addWidget(self.save_btn)
        
        self.load_file_btn = QPushButton("加载文件")
        self.load_file_btn.clicked.connect(self.load_file)
        code_buttons_layout.addWidget(self.load_file_btn)
        
        code_group_layout.addLayout(code_buttons_layout)
        code_group.setLayout(code_group_layout)
        code_layout.addWidget(code_group)
        
        self.tabs.addTab(code_tab, "代码编辑器")
        
        # 内存查看器选项卡
        memory_tab = QWidget()
        memory_layout = QVBoxLayout(memory_tab)
        
        memory_group = QGroupBox("内存查看器")
        memory_group_layout = QVBoxLayout()
        
        # 内存控制
        memory_control_layout = QHBoxLayout()
        memory_control_layout.addWidget(QLabel("起始地址:"))
        self.memory_start_input = QLineEdit("0")
        memory_control_layout.addWidget(self.memory_start_input)
        
        self.memory_refresh_btn = QPushButton("刷新")
        self.memory_refresh_btn.clicked.connect(self.update_memory_display)
        memory_control_layout.addWidget(self.memory_refresh_btn)
        
        memory_control_layout.addStretch()
        memory_group_layout.addLayout(memory_control_layout)
        
        self.memory_table = QTableWidget()
        self.memory_table.setColumnCount(16)
        self.memory_table.setRowCount(64)  # 显示更多内存
        
        # 设置表头
        headers = [f"{i:02X}" for i in range(16)]
        self.memory_table.setHorizontalHeaderLabels(headers)
        
        memory_group_layout.addWidget(self.memory_table)
        memory_group.setLayout(memory_group_layout)
        memory_layout.addWidget(memory_group)
        
        self.tabs.addTab(memory_tab, "内存查看器")
        
        # 缓存查看器选项卡
        cache_tab = QWidget()
        cache_layout = QVBoxLayout(cache_tab)
        
        cache_group = QGroupBox("缓存状态")
        cache_group_layout = QVBoxLayout()
        
        self.cache_table = QTableWidget()
        self.cache_table.setColumnCount(4)
        self.cache_table.setHorizontalHeaderLabels(["索引", "地址", "数据", "脏位"])
        
        cache_group_layout.addWidget(self.cache_table)
        
        # 缓存统计
        cache_stats_layout = QHBoxLayout()
        self.cache_hit_rate_label = QLabel("命中率: 0%")
        cache_stats_layout.addWidget(self.cache_hit_rate_label)
        
        self.cache_hits_label = QLabel("命中: 0")
        cache_stats_layout.addWidget(self.cache_hits_label)
        
        self.cache_misses_label = QLabel("未命中: 0")
        cache_stats_layout.addWidget(self.cache_misses_label)
        
        cache_stats_layout.addStretch()
        cache_group_layout.addLayout(cache_stats_layout)
        cache_group.setLayout(cache_group_layout)
        cache_layout.addWidget(cache_group)
        
        self.tabs.addTab(cache_tab, "缓存查看器")
        
        left_panel.addWidget(self.tabs)
        
        # 右侧面板
        right_panel = QVBoxLayout()
        
        # 寄存器显示
        registers_group = QGroupBox("寄存器状态")
        registers_layout = QVBoxLayout()
        
        # 创建寄存器表格
        self.registers_table = QTableWidget()
        self.registers_table.setColumnCount(2)
        self.registers_table.setHorizontalHeaderLabels(["寄存器", "值"])
        self.registers_table.setRowCount(self.computer.num_registers)
        
        # 设置寄存器名称
        register_names = ["ACC", "PC", "IR", "MAR", "MDR", "SP", "FLAGS"] + [f"R{i}" for i in range(7, self.computer.num_registers)]
        for i, name in enumerate(register_names):
            self.registers_table.setItem(i, 0, QTableWidgetItem(name))
            self.registers_table.setItem(i, 1, QTableWidgetItem("0"))
            
        registers_layout.addWidget(self.registers_table)
        registers_group.setLayout(registers_layout)
        right_panel.addWidget(registers_group)
        
        # 控制面板
        control_group = QGroupBox("控制面板")
        control_layout = QVBoxLayout()
        
        # 配置选项
        config_layout = QHBoxLayout()
        config_layout.addWidget(QLabel("速度:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 1000)
        self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(self.update_speed)
        config_layout.addWidget(self.speed_slider)
        
        self.speed_label = QLabel("10 指令/秒")
        config_layout.addWidget(self.speed_label)
        config_layout.addStretch()
        
        self.pipeline_checkbox = QCheckBox("启用流水线")
        self.pipeline_checkbox.stateChanged.connect(self.toggle_pipeline)
        config_layout.addWidget(self.pipeline_checkbox)
        
        self.interrupts_checkbox = QCheckBox("启用中断")
        self.interrupts_checkbox.setChecked(True)
        self.interrupts_checkbox.stateChanged.connect(self.toggle_interrupts)
        config_layout.addWidget(self.interrupts_checkbox)
        
        control_layout.addLayout(config_layout)
        
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
        
        # 调试按钮
        debug_layout = QHBoxLayout()
        self.breakpoint_btn = QPushButton("设置断点")
        self.breakpoint_btn.clicked.connect(self.set_breakpoint)
        debug_layout.addWidget(self.breakpoint_btn)
        
        self.watch_btn = QPushButton("添加监视点")
        debug_layout.addWidget(self.watch_btn)
        
        self.debug_btn = QPushButton("调试模式")
        self.debug_btn.setCheckable(True)
        self.debug_btn.toggled.connect(self.toggle_debug_mode)
        debug_layout.addWidget(self.debug_btn)
        
        control_layout.addLayout(debug_layout)
        control_group.setLayout(control_layout)
        right_panel.addWidget(control_group)
        
        # 进程管理
        process_group = QGroupBox("进程管理")
        process_layout = QVBoxLayout()
        
        self.process_list = QListWidget()
        process_layout.addWidget(self.process_list)
        
        process_buttons_layout = QHBoxLayout()
        self.create_process_btn = QPushButton("创建进程")
        self.create_process_btn.clicked.connect(self.create_process)
        process_buttons_layout.addWidget(self.create_process_btn)
        
        self.kill_process_btn = QPushButton("终止进程")
        self.kill_process_btn.clicked.connect(self.kill_process)
        process_buttons_layout.addWidget(self.kill_process_btn)
        
        process_layout.addLayout(process_buttons_layout)
        process_group.setLayout(process_layout)
        right_panel.addWidget(process_group)
        
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
        
        # 性能监控
        performance_group = QGroupBox("性能监控")
        performance_layout = QVBoxLayout()
        
        self.performance_text = QTextEdit()
        self.performance_text.setReadOnly(True)
        self.performance_text.setMaximumHeight(150)
        performance_layout.addWidget(self.performance_text)
        
        # 性能图表
        self.performance_chart = QChart()
        self.performance_chart.setTitle("性能指标")
        self.chart_view = QChartView(self.performance_chart)
        self.chart_view.setMaximumHeight(200)
        performance_layout.addWidget(self.chart_view)
        
        performance_group.setLayout(performance_layout)
        right_panel.addWidget(performance_group)
        
        # 状态信息
        status_group = QGroupBox("状态信息")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        right_panel.addWidget(status_group)
        
        # 添加左右面板到主布局
        main_layout.addLayout(left_panel, 3)
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
            self.update_process_display()
        except Exception as e:
            self.status_label.setText(f"加载错误: {str(e)}")
            QMessageBox.critical(self, "加载错误", str(e))
            
    def clear_code(self):
        """清空代码编辑器"""
        self.code_editor.clear()
        
    def save_code(self):
        """保存代码到文件"""
        filename, _ = QFileDialog.getSaveFileName(self, "保存代码", "", "汇编文件 (*.asm);;所有文件 (*)")
        if filename:
            with open(filename, 'w') as f:
                f.write(self.code_editor.toPlainText())
            self.status_label.setText(f"代码已保存到 {filename}")
            
    def load_file(self):
        """从文件加载代码"""
        filename, _ = QFileDialog.getOpenFileName(self, "加载代码", "", "汇编文件 (*.asm);;所有文件 (*)")
        if filename:
            with open(filename, 'r') as f:
                self.code_editor.setPlainText(f.read())
            self.status_label.setText(f"已加载文件 {filename}")
            
    def update_speed(self):
        """更新执行速度"""
        speed = self.speed_slider.value()
        self.computer.speed = speed
        self.speed_label.setText(f"{speed} 指令/秒")
        
    def toggle_pipeline(self, state):
        """切换流水线模式"""
        self.computer.pipeline_enabled = state == Qt.Checked
        
    def toggle_interrupts(self, state):
        """切换中断使能"""
        self.computer.interrupts_enabled = state == Qt.Checked
        
    def toggle_debug_mode(self, checked):
        """切换调试模式"""
        self.computer.debug_mode = checked
        
    def set_breakpoint(self):
        """设置断点"""
        dialog = BreakpointDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            address, condition = dialog.get_breakpoint()
            try:
                address = int(address, 0)  # 自动检测进制
                self.breakpoints[address] = condition
                self.status_label.setText(f"在地址 {hex(address)} 设置断点")
            except ValueError:
                QMessageBox.warning(self, "错误", "无效的地址格式")
                
    def create_process(self):
        """创建新进程"""
        # 简化版的进程创建
        if self.computer.program_loaded:
            # 复制当前程序到新内存区域
            start_addr = self.computer.current_process['memory_range'][1] + 1
            program_length = self.computer.current_process['memory_range'][1] - self.computer.current_process['memory_range'][0]
            
            # 复制程序代码
            for i in range(program_length):
                self.computer.memory[start_addr + i] = self.computer.memory[self.computer.current_process['memory_range'][0] + i]
                
            # 创建新进程
            process = {
                'id': self.computer.process_id_counter,
                'name': f"Process{self.computer.process_id_counter}",
                'pc': start_addr,
                'state': 'ready',
                'registers': self.computer.registers.copy(),
                'memory_range': (start_addr, start_addr + program_length),
                'start_time': time.time()
            }
            self.computer.process_id_counter += 1
            self.computer.processes.append(process)
            self.update_process_display()
            self.status_label.setText(f"创建新进程 {process['name']}")
            
    def kill_process(self):
        """终止当前进程"""
        if self.computer.current_process:
            self.computer._terminate_current_process()
            self.update_process_display()
            self.status_label.setText("终止当前进程")
            
    def update_process_display(self):
        """更新进程显示"""
        self.process_list.clear()
        for process in self.computer.processes:
            item = f"{process['id']}: {process['name']} ({process['state']}) - PC: {process['pc']}"
            self.process_list.addItem(item)
            
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
        self.update_process_display()
        self.status_label.setText("计算机已重置")
        
    def send_input(self):
        """发送输入"""
        text = self.input_edit.text()
        if text:
            # 处理数字输入
            if text.isdigit():
                self.computer.input_buffer.append(int(text))
            # 处理字符输入
            elif len(text) == 1:
                self.computer.input_buffer.append(ord(text))
            else:
                # 多字符输入，添加到设备缓冲区
                self.computer.devices['keyboard']['buffer'].extend(list(text))
                
            self.input_edit.clear()
            
            # 如果计算机在等待输入，恢复执行
            if not self.computer.is_running and self.computer.registers[self.IR] == 0x07:
                self.computer.is_running = True
                thread = threading.Thread(target=self.computer.run)
                thread.daemon = True
                thread.start()
                
    def update_display(self):
        """更新显示"""
        # 更新寄存器显示
        for i in range(self.computer.num_registers):
            value = self.computer.registers[i]
            self.registers_table.item(i, 1).setText(str(value))
            
        # 更新内存显示
        self.update_memory_display()
        
        # 更新缓存显示
        self.update_cache_display()
        
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
        try:
            start_addr = int(self.memory_start_input.text(), 0)
        except ValueError:
            start_addr = 0
            
        rows = self.memory_table.rowCount()
        cols = self.memory_table.columnCount()
        
        for i in range(rows):
            for j in range(cols):
                address = start_addr + i * cols + j
                if address < self.computer.memory_size:
                    value = self.computer.memory[address]
                    item = QTableWidgetItem(f"{value:02X}")
                    
                    # 高亮当前程序计数器位置
                    if address == self.computer.registers[self.PC]:
                        item.setBackground(QColor(255, 255, 0))  # 黄色
                    # 高亮断点
                    elif address in self.breakpoints:
                        item.setBackground(QColor(255, 0, 0))  # 红色
                    # 高亮当前进程内存范围
                    elif (self.computer.current_process and 
                          address >= self.computer.current_process['memory_range'][0] and 
                          address < self.computer.current_process['memory_range'][1]):
                        item.setBackground(QColor(200, 255, 200))  # 浅绿色
                        
                    self.memory_table.setItem(i, j, item)
                else:
                    self.memory_table.setItem(i, j, QTableWidgetItem(""))
                    
        # 更新垂直表头
        vertical_headers = [f"{start_addr + i * cols:04X}" for i in range(rows)]
        self.memory_table.setVerticalHeaderLabels(vertical_headers)
        
    def update_cache_display(self):
        """更新缓存显示"""
        self.cache_table.setRowCount(self.computer.cache_size)
        
        for i in range(self.computer.cache_size):
            cache_entry = self.computer.cache[i]
            self.cache_table.setItem(i, 0, QTableWidgetItem(str(i)))
            
            if cache_entry:
                address, data, dirty = cache_entry
                self.cache_table.setItem(i, 1, QTableWidgetItem(hex(address)))
                self.cache_table.setItem(i, 2, QTableWidgetItem(str(data)))
                self.cache_table.setItem(i, 3, QTableWidgetItem("是" if dirty else "否"))
            else:
                for j in range(1, 4):
                    self.cache_table.setItem(i, j, QTableWidgetItem("空"))
                    
    def update_performance(self, stats):
        """更新性能显示"""
        # 更新性能文本
        ips = stats['instructions'] / stats['running_time'] if stats['running_time'] > 0 else 0
        cpi = stats['cycles'] / stats['instructions'] if stats['instructions'] > 0 else 0
        hit_rate = stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses']) * 100 if (stats['cache_hits'] + stats['cache_misses']) > 0 else 0
        
        performance_text = f"""
指令数: {stats['instructions']}
周期数: {stats['cycles']}
运行时间: {stats['running_time']:.2f}秒
指令/秒: {ips:.2f}
周期/指令: {cpi:.2f}
缓存命中率: {hit_rate:.1f}%
进程数: {stats['processes']}
        """.strip()
        
        self.performance_text.setPlainText(performance_text)
        
        # 更新缓存统计
        self.cache_hit_rate_label.setText(f"命中率: {hit_rate:.1f}%")
        self.cache_hits_label.setText(f"命中: {stats['cache_hits']}")
        self.cache_misses_label.setText(f"未命中: {stats['cache_misses']}")
        
    def closeEvent(self, event):
        """关闭事件处理"""
        self.performance_monitor.stop()
        self.performance_monitor.wait(1000)
        super().closeEvent(event)


# 主函数
def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示仿真器
    simulator = AdvancedVonNeumannSimulator()
    simulator.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()