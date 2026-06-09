import sys
import json
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QTabWidget, QLabel, QLineEdit, QComboBox,
    QPushButton, QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QAction, QStatusBar, QSpinBox, QDoubleSpinBox,
    QCheckBox, QRadioButton, QButtonGroup, QSplitter, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QDoubleValidator, QIntValidator

import matplotlib
matplotlib.use('Qt5Agg')
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['axes.unicode_minus'] = False
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# --------------------------- 单位解析工具 ---------------------------
def parse_unit(text):
    """将带单位(k, M, m, u)的字符串转换为浮点数，失败返回None"""
    if not text:
        return None
    text = text.strip().replace(' ', '').lower()
    try:
        if text.endswith('k'):
            return float(text[:-1]) * 1e3
        elif text.endswith('m'):
            return float(text[:-1]) * 1e-3
        elif text.endswith('u'):
            return float(text[:-1]) * 1e-6
        elif text.endswith('meg'):
            return float(text[:-4]) * 1e6
        elif text.endswith('g'):
            return float(text[:-1]) * 1e9
        else:
            return float(text)
    except ValueError:
        return None

def format_unit(value, unit_type='R'):
    """将数值转换为适合显示的单位字符串（简化）"""
    if unit_type == 'R':
        if value >= 1e6:
            return f"{value/1e6:.2f}M"
        elif value >= 1e3:
            return f"{value/1e3:.2f}k"
        else:
            return f"{value:.1f}"
    elif unit_type == 'I':
        if value < 1e-6:
            return f"{value*1e9:.2f}n"
        elif value < 1e-3:
            return f"{value*1e6:.2f}u"
        elif value < 1:
            return f"{value*1e3:.2f}m"
        else:
            return f"{value:.3f}"
    else:
        return f"{value:.3f}"

# --------------------------- 嵌入式绘图画布 ---------------------------
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)

# --------------------------- 基础参数选项卡（增强）---------------------------
class BasicParamsTab(QWidget):
    """三极管基本参数设置，增加厄尔利电压、温度系数"""
    params_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()
        self.load_default_values()
        self.connect_signals()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 类型选择组
        type_group = QGroupBox("晶体管类型")
        type_layout = QFormLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["NPN", "PNP"])
        type_layout.addRow("类型:", self.type_combo)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # 直流参数组
        dc_group = QGroupBox("直流参数")
        dc_layout = QFormLayout()
        self.vbe_spin = QDoubleSpinBox()
        self.vbe_spin.setRange(0.1, 2.0)
        self.vbe_spin.setSingleStep(0.05)
        self.vbe_spin.setSuffix(" V")
        self.hfe_spin = QSpinBox()
        self.hfe_spin.setRange(10, 1000)
        self.hfe_spin.setSuffix("")
        self.vcesat_spin = QDoubleSpinBox()
        self.vcesat_spin.setRange(0.01, 2.0)
        self.vcesat_spin.setSingleStep(0.05)
        self.vcesat_spin.setSuffix(" V")
        self.ic_max_spin = QDoubleSpinBox()
        self.ic_max_spin.setRange(0.001, 100)
        self.ic_max_spin.setSuffix(" A")
        self.vce_max_spin = QDoubleSpinBox()
        self.vce_max_spin.setRange(1, 1000)
        self.vce_max_spin.setSuffix(" V")
        self.pd_max_spin = QDoubleSpinBox()
        self.pd_max_spin.setRange(0.01, 500)
        self.pd_max_spin.setSuffix(" W")
        # 新增厄尔利电压
        self.va_spin = QDoubleSpinBox()
        self.va_spin.setRange(10, 500)
        self.va_spin.setValue(100)
        self.va_spin.setSuffix(" V")
        self.va_spin.setToolTip("厄尔利电压，影响输出特性曲线斜率")

        dc_layout.addRow("Vbe:", self.vbe_spin)
        dc_layout.addRow("hFE (β):", self.hfe_spin)
        dc_layout.addRow("Vce(sat):", self.vcesat_spin)
        dc_layout.addRow("Ic max:", self.ic_max_spin)
        dc_layout.addRow("Vce max:", self.vce_max_spin)
        dc_layout.addRow("Pd max:", self.pd_max_spin)
        dc_layout.addRow("Va (厄尔利):", self.va_spin)
        dc_group.setLayout(dc_layout)
        layout.addWidget(dc_group)

        # 温度系数组（新增）
        temp_group = QGroupBox("温度参数")
        temp_layout = QFormLayout()
        self.temp_coeff_vbe = QDoubleSpinBox()
        self.temp_coeff_vbe.setRange(-5, 0)
        self.temp_coeff_vbe.setValue(-2.0)
        self.temp_coeff_vbe.setSuffix(" mV/°C")
        self.temp_coeff_vbe.setSingleStep(0.1)
        self.temp_coeff_beta = QDoubleSpinBox()
        self.temp_coeff_beta.setRange(-1, 2)
        self.temp_coeff_beta.setValue(0.5)
        self.temp_coeff_beta.setSuffix(" %/°C")
        temp_layout.addRow("ΔVbe/ΔT:", self.temp_coeff_vbe)
        temp_layout.addRow("Δβ/β/ΔT:", self.temp_coeff_beta)
        temp_group.setLayout(temp_layout)
        layout.addWidget(temp_group)

        # 应用按钮
        self.apply_btn = QPushButton("应用参数")
        layout.addWidget(self.apply_btn, alignment=Qt.AlignRight)

        layout.addStretch()

    def load_default_values(self):
        """加载默认参数（2N3904）"""
        self.type_combo.setCurrentText("NPN")
        self.vbe_spin.setValue(0.7)
        self.hfe_spin.setValue(150)
        self.vcesat_spin.setValue(0.2)
        self.ic_max_spin.setValue(0.2)
        self.vce_max_spin.setValue(40)
        self.pd_max_spin.setValue(0.625)
        self.va_spin.setValue(100)

    def connect_signals(self):
        self.apply_btn.clicked.connect(self.on_apply)

    def on_apply(self):
        params = self.get_params()
        if params:
            self.params_changed.emit(params)
            if self.parent_window:
                self.parent_window.update_status_message("基础参数已更新")

    def get_params(self):
        """返回当前参数字典"""
        return {
            'type': self.type_combo.currentText(),
            'Vbe': self.vbe_spin.value(),
            'hFE': self.hfe_spin.value(),
            'Vce_sat': self.vcesat_spin.value(),
            'Ic_max': self.ic_max_spin.value(),
            'Vce_max': self.vce_max_spin.value(),
            'Pd_max': self.pd_max_spin.value(),
            'Va': self.va_spin.value(),
            'temp_coeff_vbe': self.temp_coeff_vbe.value(),
            'temp_coeff_beta': self.temp_coeff_beta.value()
        }

    def set_params(self, params):
        """从外部设置参数"""
        if 'type' in params:
            self.type_combo.setCurrentText(params['type'])
        self.vbe_spin.setValue(params.get('Vbe', 0.7))
        self.hfe_spin.setValue(params.get('hFE', 150))
        self.vcesat_spin.setValue(params.get('Vce_sat', 0.2))
        self.ic_max_spin.setValue(params.get('Ic_max', 0.2))
        self.vce_max_spin.setValue(params.get('Vce_max', 40))
        self.pd_max_spin.setValue(params.get('Pd_max', 0.625))
        self.va_spin.setValue(params.get('Va', 100))
        self.temp_coeff_vbe.setValue(params.get('temp_coeff_vbe', -2.0))
        self.temp_coeff_beta.setValue(params.get('temp_coeff_beta', 0.5))

# --------------------------- 偏置计算选项卡（全面增强）---------------------------
class BiasCalculatorTab(QWidget):
    """偏置电路设计：支持固定、分压、集电极反馈、发射极偏置；含交流分析、稳定性系数"""
    bias_params_changed = pyqtSignal(dict)
    bias_point_changed = pyqtSignal(float, float)  # Ic(mA), Vce(V)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.transistor_params = {}
        self.setup_ui()
        self.connect_signals()
        self.set_default_values()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # ========== 偏置类型选择 ==========
        bias_type_group = QGroupBox("偏置类型")
        bias_type_layout = QHBoxLayout()
        self.bias_fixed_rb = QRadioButton("固定偏置")
        self.bias_divider_rb = QRadioButton("分压偏置")
        self.bias_collector_rb = QRadioButton("集电极反馈")
        self.bias_emitter_rb = QRadioButton("发射极偏置")
        self.bias_fixed_rb.setChecked(True)
        bias_type_layout.addWidget(self.bias_fixed_rb)
        bias_type_layout.addWidget(self.bias_divider_rb)
        bias_type_layout.addWidget(self.bias_collector_rb)
        bias_type_layout.addWidget(self.bias_emitter_rb)
        bias_type_layout.addStretch()
        bias_type_group.setLayout(bias_type_layout)
        main_layout.addWidget(bias_type_group)

        # ========== 电源与公共电阻 ==========
        common_group = QGroupBox("电源与公共电阻")
        common_layout = QFormLayout()
        self.vcc_edit = QLineEdit(); self.vcc_edit.setPlaceholderText("12")
        self.vcc_unit = QLabel("V")
        self.rc_edit = QLineEdit(); self.rc_edit.setPlaceholderText("1k")
        self.rc_unit = QLabel("Ω")
        self.re_edit = QLineEdit(); self.re_edit.setPlaceholderText("0")
        self.re_unit = QLabel("Ω")
        h1 = QHBoxLayout(); h1.addWidget(self.vcc_edit); h1.addWidget(self.vcc_unit)
        h2 = QHBoxLayout(); h2.addWidget(self.rc_edit); h2.addWidget(self.rc_unit)
        h3 = QHBoxLayout(); h3.addWidget(self.re_edit); h3.addWidget(self.re_unit)
        common_layout.addRow("Vcc:", h1)
        common_layout.addRow("Rc:", h2)
        common_layout.addRow("Re:", h3)
        common_group.setLayout(common_layout)
        main_layout.addWidget(common_group)

        # ========== 各偏置特有参数（动态显示） ==========
        # 固定偏置组
        self.fixed_group = QGroupBox("固定偏置参数")
        fixed_layout = QFormLayout()
        self.rb_fixed_edit = QLineEdit(); self.rb_fixed_edit.setPlaceholderText("100k")
        self.rb_fixed_unit = QLabel("Ω")
        h_rb = QHBoxLayout(); h_rb.addWidget(self.rb_fixed_edit); h_rb.addWidget(self.rb_fixed_unit)
        fixed_layout.addRow("Rb:", h_rb)
        self.fixed_group.setLayout(fixed_layout)
        main_layout.addWidget(self.fixed_group)

        # 分压偏置组
        self.divider_group = QGroupBox("分压偏置参数")
        divider_layout = QFormLayout()
        self.r1_edit = QLineEdit(); self.r1_edit.setPlaceholderText("10k")
        self.r1_unit = QLabel("Ω")
        self.r2_edit = QLineEdit(); self.r2_edit.setPlaceholderText("4.7k")
        self.r2_unit = QLabel("Ω")
        h_r1 = QHBoxLayout(); h_r1.addWidget(self.r1_edit); h_r1.addWidget(self.r1_unit)
        h_r2 = QHBoxLayout(); h_r2.addWidget(self.r2_edit); h_r2.addWidget(self.r2_unit)
        divider_layout.addRow("R1:", h_r1)
        divider_layout.addRow("R2:", h_r2)
        self.divider_group.setLayout(divider_layout)
        self.divider_group.setEnabled(False)
        main_layout.addWidget(self.divider_group)

        # 集电极反馈偏置组
        self.collector_group = QGroupBox("集电极反馈偏置")
        collector_layout = QFormLayout()
        self.rb_cb_edit = QLineEdit(); self.rb_cb_edit.setPlaceholderText("100k")
        self.rb_cb_unit = QLabel("Ω")
        h_rb_cb = QHBoxLayout(); h_rb_cb.addWidget(self.rb_cb_edit); h_rb_cb.addWidget(self.rb_cb_unit)
        collector_layout.addRow("Rb:", h_rb_cb)
        self.collector_group.setLayout(collector_layout)
        self.collector_group.setEnabled(False)
        main_layout.addWidget(self.collector_group)

        # 发射极偏置组（双电源）
        self.emitter_group = QGroupBox("发射极偏置（双电源）")
        emitter_layout = QFormLayout()
        self.vee_edit = QLineEdit(); self.vee_edit.setPlaceholderText("-12")
        self.vee_unit = QLabel("V")
        self.re_ee_edit = QLineEdit(); self.re_ee_edit.setPlaceholderText("1k")
        self.re_ee_unit = QLabel("Ω")
        h_vee = QHBoxLayout(); h_vee.addWidget(self.vee_edit); h_vee.addWidget(self.vee_unit)
        h_re = QHBoxLayout(); h_re.addWidget(self.re_ee_edit); h_re.addWidget(self.re_ee_unit)
        emitter_layout.addRow("Vee:", h_vee)
        emitter_layout.addRow("Re:", h_re)
        self.emitter_group.setLayout(emitter_layout)
        self.emitter_group.setEnabled(False)
        main_layout.addWidget(self.emitter_group)

        # ========== 计算目标与模式 ==========
        target_group = QGroupBox("设计目标")
        target_layout = QFormLayout()
        self.target_combo = QComboBox()
        self.target_combo.addItems(["计算工作点", "计算基极电阻", "计算集电极电阻"])
        self.target_ic_edit = QLineEdit(); self.target_ic_edit.setPlaceholderText("5")
        self.target_ic_unit = QLabel("mA")
        self.target_vce_edit = QLineEdit(); self.target_vce_edit.setPlaceholderText("6")
        self.target_vce_unit = QLabel("V")
        h_ic = QHBoxLayout(); h_ic.addWidget(self.target_ic_edit); h_ic.addWidget(self.target_ic_unit)
        h_vce = QHBoxLayout(); h_vce.addWidget(self.target_vce_edit); h_vce.addWidget(self.target_vce_unit)
        target_layout.addRow("计算模式:", self.target_combo)
        target_layout.addRow("目标 Ic:", h_ic)
        target_layout.addRow("目标 Vce:", h_vce)
        target_group.setLayout(target_layout)
        main_layout.addWidget(target_group)

        # ========== 计算按钮 ==========
        self.calc_btn = QPushButton("计算偏置")
        main_layout.addWidget(self.calc_btn, alignment=Qt.AlignCenter)

        # ========== 直流结果 ==========
        result_group = QGroupBox("直流工作点")
        result_layout = QFormLayout()
        self.result_ic_label = QLabel("--")
        self.result_vce_label = QLabel("--")
        self.result_ib_label = QLabel("--")
        self.result_power_label = QLabel("--")
        self.result_rb_label = QLabel("--")
        self.result_r1_label = QLabel("--")
        self.result_r2_label = QLabel("--")
        result_layout.addRow("Ic (mA):", self.result_ic_label)
        result_layout.addRow("Vce (V):", self.result_vce_label)
        result_layout.addRow("Ib (μA):", self.result_ib_label)
        result_layout.addRow("功耗 (mW):", self.result_power_label)
        result_layout.addRow("Rb (Ω):", self.result_rb_label)
        result_layout.addRow("R1 (Ω):", self.result_r1_label)
        result_layout.addRow("R2 (Ω):", self.result_r2_label)
        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group)

        # ========== 交流小信号分析（新增） ==========
        ac_group = QGroupBox("交流小信号参数")
        ac_layout = QFormLayout()
        self.ac_av_label = QLabel("--")
        self.ac_rin_label = QLabel("--")
        self.ac_rout_label = QLabel("--")
        self.ac_bypass_cb = QCheckBox("发射极旁路电容")
        self.ac_bypass_cb.setChecked(True)
        ac_layout.addRow("电压增益 Av:", self.ac_av_label)
        ac_layout.addRow("输入电阻 Rin:", self.ac_rin_label)
        ac_layout.addRow("输出电阻 Rout:", self.ac_rout_label)
        ac_layout.addRow(self.ac_bypass_cb)
        ac_group.setLayout(ac_layout)
        main_layout.addWidget(ac_group)

        # ========== 温度稳定性分析（新增） ==========
        stability_group = QGroupBox("稳定性分析 (ΔT=+10°C)")
        stability_layout = QFormLayout()
        self.stab_ic_change_label = QLabel("--")
        self.stab_vce_change_label = QLabel("--")
        self.stab_s_beta_label = QLabel("--")
        self.stab_s_vbe_label = QLabel("--")
        stability_layout.addRow("Ic 变化:", self.stab_ic_change_label)
        stability_layout.addRow("Vce 变化:", self.stab_vce_change_label)
        stability_layout.addRow("S(β):", self.stab_s_beta_label)
        stability_layout.addRow("S(Vbe):", self.stab_s_vbe_label)
        stability_group.setLayout(stability_layout)
        main_layout.addWidget(stability_group)

        main_layout.addStretch()

    def set_default_values(self):
        self.vcc_edit.setText("12")
        self.rc_edit.setText("1k")
        self.re_edit.setText("0")
        self.rb_fixed_edit.setText("100k")
        self.r1_edit.setText("10k")
        self.r2_edit.setText("4.7k")
        self.rb_cb_edit.setText("100k")
        self.vee_edit.setText("-12")
        self.re_ee_edit.setText("1k")
        self.target_ic_edit.setText("5")
        self.target_vce_edit.setText("6")

    def connect_signals(self):
        self.bias_fixed_rb.toggled.connect(self.on_bias_type_changed)
        self.bias_divider_rb.toggled.connect(self.on_bias_type_changed)
        self.bias_collector_rb.toggled.connect(self.on_bias_type_changed)
        self.bias_emitter_rb.toggled.connect(self.on_bias_type_changed)
        self.calc_btn.clicked.connect(self.calculate)
        self.ac_bypass_cb.stateChanged.connect(self.calculate)  # 重新计算交流参数

    def on_bias_type_changed(self):
        """切换偏置类型时启用对应控件"""
        self.fixed_group.setEnabled(self.bias_fixed_rb.isChecked())
        self.divider_group.setEnabled(self.bias_divider_rb.isChecked())
        self.collector_group.setEnabled(self.bias_collector_rb.isChecked())
        self.emitter_group.setEnabled(self.bias_emitter_rb.isChecked())
        # 固定偏置时Re通常为0，但保留输入可能性
        if self.bias_fixed_rb.isChecked():
            self.re_edit.setEnabled(True)
        else:
            self.re_edit.setEnabled(True)  # 其他偏置也可设Re

    def update_transistor_params(self, params):
        if params:
            self.transistor_params = params

    def parse_entries(self):
        """解析所有输入框，支持单位，返回字典"""
        try:
            vcc = parse_unit(self.vcc_edit.text()) or 12.0
            rc = parse_unit(self.rc_edit.text()) or 1000.0
            re = parse_unit(self.re_edit.text()) or 0.0
            rb_fixed = parse_unit(self.rb_fixed_edit.text()) if self.rb_fixed_edit.text() else None
            r1 = parse_unit(self.r1_edit.text()) if self.r1_edit.text() else None
            r2 = parse_unit(self.r2_edit.text()) if self.r2_edit.text() else None
            rb_cb = parse_unit(self.rb_cb_edit.text()) if self.rb_cb_edit.text() else None
            vee = parse_unit(self.vee_edit.text()) if self.vee_edit.text() else -12.0
            re_ee = parse_unit(self.re_ee_edit.text()) if self.re_ee_edit.text() else 1000.0

            target_ic = parse_unit(self.target_ic_edit.text())
            if target_ic is not None:
                target_ic = target_ic / 1000.0  # mA -> A
            target_vce = parse_unit(self.target_vce_edit.text())

            return {
                'vcc': vcc, 'rc': rc, 're': re,
                'rb_fixed': rb_fixed, 'r1': r1, 'r2': r2,
                'rb_cb': rb_cb, 'vee': vee, 're_ee': re_ee,
                'target_ic': target_ic, 'target_vce': target_vce
            }
        except:
            return None

    def calculate(self):
        parsed = self.parse_entries()
        if not parsed:
            QMessageBox.warning(self, "输入错误", "请检查输入值，支持单位如 1k, 4.7k, 5m等")
            return

        vbe = self.transistor_params.get('Vbe', 0.7)
        hfe = self.transistor_params.get('hFE', 150)
        va = self.transistor_params.get('Va', 100)

        mode = self.target_combo.currentText()

        try:
            if self.bias_fixed_rb.isChecked():
                self._calc_fixed(parsed, vbe, hfe, va, mode)
            elif self.bias_divider_rb.isChecked():
                self._calc_divider(parsed, vbe, hfe, va, mode)
            elif self.bias_collector_rb.isChecked():
                self._calc_collector(parsed, vbe, hfe, va, mode)
            elif self.bias_emitter_rb.isChecked():
                self._calc_emitter(parsed, vbe, hfe, va, mode)
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算失败: {str(e)}")

    # ----------------- 各偏置计算核心 -----------------
    def _calc_fixed(self, p, vbe, hfe, va, mode):
        vcc, rc, re = p['vcc'], p['rc'], p['re']
        rb = p['rb_fixed'] if p['rb_fixed'] is not None else 100000

        if mode == "计算基极电阻":
            if p['target_ic'] is None:
                QMessageBox.warning(self, "参数不足", "请设定目标Ic")
                return
            ic = p['target_ic']
            ib = ic / hfe
            # Vcc - Ib*Rb - Vbe - Ie*Re = 0  (Ie ≈ Ic)
            rb_calc = (vcc - vbe - ic * re) / ib
            if rb_calc < 0:
                QMessageBox.warning(self, "无效结果", "计算出的Rb为负，请调整目标或参数")
                return
            self.result_rb_label.setText(format_unit(rb_calc, 'R'))
            # 用计算出的Rb重新计算工作点
            ib = (vcc - vbe - ic * re) / rb_calc  # 更精确
            ic = hfe * ib
            vce = vcc - ic * (rc + re)
        elif mode == "计算集电极电阻":
            if p['target_ic'] is None or p['target_vce'] is None:
                QMessageBox.warning(self, "参数不足", "请设定目标Ic和Vce")
                return
            ic = p['target_ic']
            vce = p['target_vce']
            rc_calc = (vcc - vce - ic * re) / ic
            if rc_calc < 0:
                QMessageBox.warning(self, "无效结果", "Rc为负，请调整目标")
                return
            self.result_r1_label.setText(f"Rc = {format_unit(rc_calc, 'R')} Ω")
            # 使用已有Rb计算工作点
            ib = (vcc - vbe - ic * re) / rb
            ic = hfe * ib
            vce = vcc - ic * (rc_calc + re)
        else:  # 计算工作点
            ib = (vcc - vbe) / (rb + (hfe+1)*re)  # 精确公式
            ic = hfe * ib
            vce = vcc - ic * rc - (ic+ib)*re

        self._display_dc_results(ic*1000, vce, ib*1e6, vcc*ic, vcc, ic, rc, re)
        self.result_rb_label.setText(format_unit(rb, 'R'))
        # 交流、稳定性分析
        self._calc_ac_and_stability('fixed', p, vbe, hfe, va, ic, vce, rb=rb)

    def _calc_divider(self, p, vbe, hfe, va, mode):
        vcc, rc, re = p['vcc'], p['rc'], p['re']
        r1, r2 = p['r1'], p['r2']

        if mode == "计算基极电阻":
            if p['target_ic'] is None:
                QMessageBox.warning(self, "参数不足", "请设定目标Ic")
                return
            ic = p['target_ic']
            ib = ic / hfe
            ve = ic * re
            vb = ve + vbe
            # 取分压电流为10*ib
            idiv = 10 * ib
            r2_calc = vb / idiv
            r1_calc = (vcc - vb) / idiv
            self.result_r1_label.setText(format_unit(r1_calc, 'R'))
            self.result_r2_label.setText(format_unit(r2_calc, 'R'))
            # 用计算值重新计算工作点
            vb_act = vcc * r2_calc / (r1_calc + r2_calc)
            ve_act = vb_act - vbe
            ie_act = ve_act / re if re > 0 else 0
            ic_act = ie_act * hfe / (hfe + 1)
            vce_act = vcc - ic_act * (rc + re)
            ic = ic_act
            vce = vce_act
            r1, r2 = r1_calc, r2_calc
        else:  # 计算工作点
            if r1 is None or r2 is None:
                QMessageBox.warning(self, "参数不足", "请输入R1、R2")
                return
            vb = vcc * r2 / (r1 + r2)
            ve = vb - vbe
            ie = ve / re if re > 0 else 0
            ic = ie * hfe / (hfe + 1)
            vce = vcc - ic * (rc + re)

        self._display_dc_results(ic*1000, vce, (ic/hfe)*1e6, vcc*ic, vcc, ic, rc, re)
        self.result_r1_label.setText(format_unit(r1, 'R'))
        self.result_r2_label.setText(format_unit(r2, 'R'))
        self._calc_ac_and_stability('divider', p, vbe, hfe, va, ic, vce, r1=r1, r2=r2)

    def _calc_collector(self, p, vbe, hfe, va, mode):
        vcc, rc, re = p['vcc'], p['rc'], p['re']
        rb = p['rb_cb'] if p['rb_cb'] is not None else 100000

        if mode == "计算基极电阻":
            if p['target_ic'] is None:
                QMessageBox.warning(self, "参数不足", "请设定目标Ic")
                return
            ic = p['target_ic']
            ib = ic / hfe
            # 反馈偏置：Vcc - (Ic+Ib)*Rc - Ib*Rb - Vbe - Ie*Re = 0
            rb_calc = (vcc - vbe - ic*re - (ic+ib)*rc) / ib
            if rb_calc < 0:
                QMessageBox.warning(self, "无效结果", "Rb为负，请降低目标Ic或增大Rc")
                return
            self.result_rb_label.setText(format_unit(rb_calc, 'R'))
            # 重新计算工作点
            ib = (vcc - vbe) / (rb_calc + (hfe+1)*(rc+re))
            ic = hfe * ib
            vce = vcc - ic*rc - (ic+ib)*re
        else:
            ib = (vcc - vbe) / (rb + (hfe+1)*(rc+re))
            ic = hfe * ib
            vce = vcc - ic*rc - (ic+ib)*re

        self._display_dc_results(ic*1000, vce, ib*1e6, vcc*ic, vcc, ic, rc, re)
        self.result_rb_label.setText(format_unit(rb, 'R'))
        self._calc_ac_and_stability('collector', p, vbe, hfe, va, ic, vce, rb=rb)

    def _calc_emitter(self, p, vbe, hfe, va, mode):
        vcc, rc = p['vcc'], p['rc']
        vee, re = p['vee'], p['re_ee']
        # 发射极偏置：基极接地或接偏置电阻，此处简化为基极接地（固定基极电压0）
        # 实际更复杂，这里仅演示工作点计算
        ve = 0 - vbe  # 基极0V，发射极电压 = -Vbe
        ie = (ve - vee) / re  # Vee负电源
        ic = ie * hfe / (hfe+1)
        ib = ic / hfe
        vce = vcc - ic*rc - (ve)  # 发射极电压ve为负，计算需注意
        # 简化显示
        self._display_dc_results(ic*1000, vce, ib*1e6, (vcc - vee)*ic, vcc, ic, rc, re)
        self._calc_ac_and_stability('emitter', p, vbe, hfe, va, ic, vce, re=re)

    def _display_dc_results(self, ic_ma, vce, ib_ua, pwr, vcc, ic_a, rc, re):
        self.result_ic_label.setText(f"{ic_ma:.2f}")
        self.result_vce_label.setText(f"{vce:.2f}")
        self.result_ib_label.setText(f"{ib_ua:.2f}")
        self.result_power_label.setText(f"{pwr*1000:.2f}")
        # 发射偏置点信号
        self.bias_point_changed.emit(ic_ma, vce)

    def _calc_ac_and_stability(self, bias_type, p, vbe, hfe, va, ic, vce, **kwargs):
        """计算交流参数与稳定性系数"""
        # 小信号参数
        vt = 0.026  # 26mV
        gm = ic / vt
        rpi = hfe / gm
        ro = va / ic if va > 0 and ic > 0 else 1e6

        rc = p['rc']
        re = p['re']
        bypass = self.ac_bypass_cb.isChecked()

        # 交流增益（共射极基本公式）
        if bias_type == 'fixed':
            # 固定偏置：输入电阻 ≈ R1//R2? 固定偏置只有Rb
            rb = kwargs.get('rb', 1e6)
            if bypass:
                av = -gm * (rc // ro)
                rin = 1 / (1/rb + 1/rpi)
            else:
                av = -gm * (rc // ro) / (1 + gm * re)
                rin = 1 / (1/rb + 1/(rpi + (hfe+1)*re))
            rout = rc // ro
        elif bias_type == 'divider':
            r1 = kwargs.get('r1', 1e6)
            r2 = kwargs.get('r2', 1e6)
            rth = 1 / (1/r1 + 1/r2)
            if bypass:
                av = -gm * (rc // ro)
                rin = 1 / (1/rth + 1/rpi)
            else:
                av = -gm * (rc // ro) / (1 + gm * re)
                rin = 1 / (1/rth + 1/(rpi + (hfe+1)*re))
            rout = rc // ro
        elif bias_type == 'collector':
            rb = kwargs.get('rb', 1e6)
            # 近似：增益与固定偏置类似，但输入阻抗受反馈影响
            if bypass:
                av = -gm * (rc // ro)
                rin = rb / (1 - av)  # 密勒近似
            else:
                av = -gm * (rc // ro) / (1 + gm * re)
                rin = rb / (1 - av)
            rout = rc // ro
        else:
            av = 0
            rin = 0
            rout = 0

        self.ac_av_label.setText(f"{av:.2f}")
        self.ac_rin_label.setText(format_unit(rin, 'R') + " Ω")
        self.ac_rout_label.setText(format_unit(rout, 'R') + " Ω")

        # 稳定性系数（近似）
        # S(beta) = 1 / (1 + (hfe+1)*Re/(Rb+Rth...)) 简单估算
        if bias_type == 'fixed':
            rb = kwargs.get('rb', 1e6)
            s_beta = 1 + (rb/re) if re > 0 else 100  # 非常大
        elif bias_type == 'divider':
            r1 = kwargs.get('r1', 1e6)
            r2 = kwargs.get('r2', 1e6)
            rth = 1 / (1/r1 + 1/r2)
            s_beta = 1 + (rth/re) if re > 0 else 100
        else:
            s_beta = 0
        self.stab_s_beta_label.setText(f"{s_beta:.2f}")

        # 温度影响：假设Vbe -2mV/°C, β +0.5%/°C
        dt = 10
        dvbe = self.transistor_params.get('temp_coeff_vbe', -2.0) * dt / 1000  # V
        dbeta_rel = self.transistor_params.get('temp_coeff_beta', 0.5) * dt / 100  # 相对变化
        # 粗略估计Ic变化
        dic_ic = -dvbe / (0.026) * (1/(1+ s_beta)) + dbeta_rel  # 简化模型
        self.stab_ic_change_label.setText(f"{dic_ic*100:.1f}%")
        self.stab_vce_change_label.setText("--")  # 暂略

# --------------------------- 输出特性曲线选项卡（增强）---------------------------
class OutputCharacteristicsTab(QWidget):
    """绘制输出/输入/转移特性曲线，带负载线、工作点、数据导出"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.transistor_params = {}
        self.bias_point = (None, None)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 控制面板
        control_group = QGroupBox("曲线设置")
        control_layout = QGridLayout()

        control_layout.addWidget(QLabel("曲线类型:"), 0, 0)
        self.curve_type_combo = QComboBox()
        self.curve_type_combo.addItems(["输出特性 (Ic-Vce)", "输入特性 (Ib-Vbe)", "转移特性 (Ic-Vbe)"])
        control_layout.addWidget(self.curve_type_combo, 0, 1)

        control_layout.addWidget(QLabel("基极电流步进 (μA):"), 1, 0)
        self.ib_step_edit = QLineEdit("10")
        control_layout.addWidget(self.ib_step_edit, 1, 1)

        control_layout.addWidget(QLabel("Vce范围 (V):"), 2, 0)
        self.vce_max_edit = QLineEdit("20")
        control_layout.addWidget(self.vce_max_edit, 2, 1)

        control_layout.addWidget(QLabel("Vbe范围 (V):"), 3, 0)
        self.vbe_max_edit = QLineEdit("1.0")
        control_layout.addWidget(self.vbe_max_edit, 3, 1)

        control_layout.addWidget(QLabel("扫描点数:"), 4, 0)
        self.points_edit = QLineEdit("100")
        control_layout.addWidget(self.points_edit, 4, 1)

        self.plot_btn = QPushButton("绘制曲线")
        control_layout.addWidget(self.plot_btn, 5, 0, 1, 2)

        self.export_btn = QPushButton("导出数据")
        control_layout.addWidget(self.export_btn, 6, 0, 1, 2)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # 绘图画布
        self.canvas = MplCanvas(self, width=6, height=5, dpi=100)
        layout.addWidget(self.canvas)

        # 连接信号
        self.plot_btn.clicked.connect(self.plot_curves)
        self.export_btn.clicked.connect(self.export_data)
        self.curve_type_combo.currentIndexChanged.connect(self.plot_curves)

    def update_transistor_params(self, params):
        if params:
            self.transistor_params = params

    def update_bias_point(self, ic_ma, vce):
        self.bias_point = (ic_ma, vce)

    def plot_curves(self):
        curve_type = self.curve_type_combo.currentText()
        if "输出特性" in curve_type:
            self._plot_output()
        elif "输入特性" in curve_type:
            self._plot_input()
        else:
            self._plot_transfer()

    def _plot_output(self):
        try:
            hfe = self.transistor_params.get('hFE', 150)
            va = self.transistor_params.get('Va', 100)
            vce_max = float(self.vce_max_edit.text())
            ib_step = float(self.ib_step_edit.text()) / 1e6
            ib_steps = 6
            vce = np.linspace(0, vce_max, int(self.points_edit.text()))

            self.canvas.axes.clear()
            for i in range(ib_steps):
                ib = i * ib_step
                ic = hfe * ib * (1 + vce / va)
                ic[vce < 0.2] = 0  # 饱和区简化
                self.canvas.axes.plot(vce, ic * 1000, label=f'Ib={ib*1e6:.0f}μA')

            # 负载线与工作点
            self._plot_loadline_and_q()
            self.canvas.axes.set_xlabel('Vce (V)')
            self.canvas.axes.set_ylabel('Ic (mA)')
            self.canvas.axes.set_title('输出特性曲线')
            self.canvas.axes.legend(loc='upper right')
            self.canvas.axes.grid(True, linestyle='--', alpha=0.6)
            self.canvas.draw()
        except Exception as e:
            QMessageBox.warning(self, "绘图错误", str(e))

    def _plot_input(self):
        try:
            vbe = np.linspace(0, float(self.vbe_max_edit.text()), int(self.points_edit.text()))
            # 简化模型：Ic = Is * exp(Vbe/(n*Vt))，Ib = Ic/β
            isat = 1e-14  # 假设
            vt = 0.026
            ic = isat * (np.exp(vbe / vt) - 1)
            ib = ic / self.transistor_params.get('hFE', 150)
            self.canvas.axes.clear()
            self.canvas.axes.plot(vbe, ib * 1e6, 'b-')
            self.canvas.axes.set_xlabel('Vbe (V)')
            self.canvas.axes.set_ylabel('Ib (μA)')
            self.canvas.axes.set_title('输入特性曲线')
            self.canvas.axes.grid(True)
            self.canvas.draw()
        except Exception as e:
            QMessageBox.warning(self, "绘图错误", str(e))

    def _plot_transfer(self):
        try:
            vbe = np.linspace(0, float(self.vbe_max_edit.text()), int(self.points_edit.text()))
            vt = 0.026
            isat = 1e-14
            ic = isat * (np.exp(vbe / vt) - 1)
            self.canvas.axes.clear()
            self.canvas.axes.plot(vbe, ic * 1000, 'g-')
            self.canvas.axes.set_xlabel('Vbe (V)')
            self.canvas.axes.set_ylabel('Ic (mA)')
            self.canvas.axes.set_title('转移特性曲线')
            self.canvas.axes.grid(True)
            self.canvas.draw()
        except Exception as e:
            QMessageBox.warning(self, "绘图错误", str(e))

    def _plot_loadline_and_q(self):
        """绘制直流负载线并标记工作点"""
        if self.parent_window:
            bias_tab = self.parent_window.bias_tab
            try:
                vcc = parse_unit(bias_tab.vcc_edit.text()) or 12
                rc = parse_unit(bias_tab.rc_edit.text()) or 1000
                re = parse_unit(bias_tab.re_edit.text()) or 0
                if rc + re > 0:
                    vce_line = np.linspace(0, vcc, 50)
                    ic_line = (vcc - vce_line) / (rc + re)
                    self.canvas.axes.plot(vce_line, ic_line * 1000, 'r--', label='负载线')
                    if self.bias_point[0] is not None:
                        self.canvas.axes.plot(self.bias_point[1], self.bias_point[0], 'ro', markersize=8)
            except:
                pass

    def export_data(self):
        """将当前曲线数据导出为CSV"""
        curve_type = self.curve_type_combo.currentText()
        if not self.canvas.axes.lines:
            QMessageBox.information(self, "提示", "请先绘制曲线")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出数据", "", "CSV Files (*.csv)")
        if file_path:
            try:
                # 获取第一条曲线的x,y数据
                line = self.canvas.axes.lines[0]
                x = line.get_xdata()
                y = line.get_ydata()
                np.savetxt(file_path, np.column_stack((x, y)), delimiter=',', header='Vce(V),Ic(mA)')
                QMessageBox.information(self, "导出成功", f"数据已保存至{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", str(e))

# --------------------------- 数据表选项卡（增强）---------------------------
class DatasheetTab(QWidget):
    """常用三极管数据表，支持编辑、添加、保存/加载自定义库"""
    load_params = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.custom_lib_path = "transistor_lib.json"
        self.setup_ui()
        self.populate_table()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 工具栏
        tool_layout = QHBoxLayout()
        self.add_btn = QPushButton("新增")
        self.edit_btn = QPushButton("编辑")
        self.delete_btn = QPushButton("删除")
        self.save_lib_btn = QPushButton("保存库")
        self.load_lib_btn = QPushButton("加载库")
        tool_layout.addWidget(self.add_btn)
        tool_layout.addWidget(self.edit_btn)
        tool_layout.addWidget(self.delete_btn)
        tool_layout.addStretch()
        tool_layout.addWidget(self.save_lib_btn)
        tool_layout.addWidget(self.load_lib_btn)
        layout.addLayout(tool_layout)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["型号", "类型", "Vbe(V)", "hFE", "Vce(sat)(V)", "Ic(max)(A)", "Vce(max)(V)", "Pd(max)(W)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        self.load_btn = QPushButton("加载选中型号")
        layout.addWidget(self.load_btn)

        # 信号连接
        self.load_btn.clicked.connect(self.on_load_selected)
        self.add_btn.clicked.connect(self.on_add)
        self.edit_btn.clicked.connect(self.on_edit)
        self.delete_btn.clicked.connect(self.on_delete)
        self.save_lib_btn.clicked.connect(self.save_library)
        self.load_lib_btn.clicked.connect(self.load_library)

    def populate_table(self, data=None):
        """填充数据，如果data为None则使用内置默认"""
        if data is None:
            data = [
                ("2N3904", "NPN", 0.7, 150, 0.2, 0.2, 40, 0.625),
                ("2N3906", "PNP", 0.7, 150, 0.2, 0.2, 40, 0.625),
                ("BC547", "NPN", 0.7, 200, 0.2, 0.1, 45, 0.5),
                ("BC557", "PNP", 0.7, 200, 0.2, 0.1, 45, 0.5),
                ("2N2222", "NPN", 0.7, 100, 0.3, 0.8, 40, 0.5),
                ("2N2907", "PNP", 0.7, 100, 0.4, 0.6, 40, 0.4),
                ("TIP31C", "NPN", 1.0, 25, 1.2, 3, 100, 40),
                ("TIP32C", "PNP", 1.0, 25, 1.2, 3, 100, 40),
            ]
        self.table.setRowCount(len(data))
        for row, items in enumerate(data):
            for col, val in enumerate(items):
                self.table.setItem(row, col, QTableWidgetItem(str(val)))

    def on_load_selected(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "提示", "请先选择一行数据")
            return
        params = {
            'type': self.table.item(current_row, 1).text(),
            'Vbe': float(self.table.item(current_row, 2).text()),
            'hFE': float(self.table.item(current_row, 3).text()),
            'Vce_sat': float(self.table.item(current_row, 4).text()),
            'Ic_max': float(self.table.item(current_row, 5).text()),
            'Vce_max': float(self.table.item(current_row, 6).text()),
            'Pd_max': float(self.table.item(current_row, 7).text()) if self.table.item(current_row, 7) else 0.0,
            'Va': 100  # 默认厄尔利
        }
        self.load_params.emit(params)

    def on_add(self):
        """添加新型号（弹出简单输入对话框）"""
        # 为简化，直接调用编辑对话框
        self._edit_dialog(row=-1)

    def on_edit(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "提示", "请先选择要编辑的行")
            return
        self._edit_dialog(row=current_row)

    def _edit_dialog(self, row=-1):
        """编辑对话框，row=-1表示新增"""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑三极管参数")
        layout = QFormLayout(dialog)

        type_combo = QComboBox()
        type_combo.addItems(["NPN", "PNP"])
        model_edit = QLineEdit()
        vbe_edit = QDoubleSpinBox(); vbe_edit.setRange(0.1, 2); vbe_edit.setValue(0.7)
        hfe_edit = QSpinBox(); hfe_edit.setRange(10, 1000); hfe_edit.setValue(150)
        vcesat_edit = QDoubleSpinBox(); vcesat_edit.setRange(0.01, 2); vcesat_edit.setValue(0.2)
        icmax_edit = QDoubleSpinBox(); icmax_edit.setRange(0.001, 100); icmax_edit.setValue(0.2)
        vcemax_edit = QDoubleSpinBox(); vcemax_edit.setRange(1, 1000); vcemax_edit.setValue(40)
        pdmax_edit = QDoubleSpinBox(); pdmax_edit.setRange(0.01, 500); pdmax_edit.setValue(0.625)

        if row >= 0:
            model_edit.setText(self.table.item(row, 0).text())
            type_combo.setCurrentText(self.table.item(row, 1).text())
            vbe_edit.setValue(float(self.table.item(row, 2).text()))
            hfe_edit.setValue(int(float(self.table.item(row, 3).text())))
            vcesat_edit.setValue(float(self.table.item(row, 4).text()))
            icmax_edit.setValue(float(self.table.item(row, 5).text()))
            vcemax_edit.setValue(float(self.table.item(row, 6).text()))
            pdmax_edit.setValue(float(self.table.item(row, 7).text()))

        layout.addRow("型号:", model_edit)
        layout.addRow("类型:", type_combo)
        layout.addRow("Vbe:", vbe_edit)
        layout.addRow("hFE:", hfe_edit)
        layout.addRow("Vce(sat):", vcesat_edit)
        layout.addRow("Ic(max):", icmax_edit)
        layout.addRow("Vce(max):", vcemax_edit)
        layout.addRow("Pd(max):", pdmax_edit)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addRow(btn_box)

        if dialog.exec_() == QDialog.Accepted:
            if not model_edit.text():
                QMessageBox.warning(self, "错误", "型号不能为空")
                return
            new_row = [model_edit.text(), type_combo.currentText(),
                       str(vbe_edit.value()), str(hfe_edit.value()),
                       str(vcesat_edit.value()), str(icmax_edit.value()),
                       str(vcemax_edit.value()), str(pdmax_edit.value())]
            if row >= 0:
                for col, val in enumerate(new_row):
                    self.table.setItem(row, col, QTableWidgetItem(val))
            else:
                row_count = self.table.rowCount()
                self.table.insertRow(row_count)
                for col, val in enumerate(new_row):
                    self.table.setItem(row_count, col, QTableWidgetItem(val))

    def on_delete(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def save_library(self):
        """将当前表格数据保存为JSON"""
        file_path, _ = QFileDialog.getSaveFileName(self, "保存晶体管库", self.custom_lib_path, "JSON Files (*.json)")
        if file_path:
            data = []
            for row in range(self.table.rowCount()):
                row_data = [self.table.item(row, col).text() for col in range(self.table.columnCount())]
                data.append(row_data)
            try:
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=4)
                QMessageBox.information(self, "成功", f"已保存 {len(data)} 条记录")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", str(e))

    def load_library(self):
        """从JSON加载数据替换当前表格"""
        file_path, _ = QFileDialog.getOpenFileName(self, "加载晶体管库", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                self.populate_table(data)
            except Exception as e:
                QMessageBox.critical(self, "加载失败", str(e))

# --------------------------- 主窗口（增强菜单）---------------------------
class TransistorAssistant(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级三极管助手 - 专业版")
        self.setGeometry(100, 100, 1200, 850)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        self.create_menu()
        self.create_tabs()

        # 信号连接
        self.basic_tab.params_changed.connect(self.on_basic_params_changed)
        self.datasheet_tab.load_params.connect(self.on_datasheet_load)
        self.bias_tab.bias_point_changed.connect(self.curve_tab.update_bias_point)

        # 初始化参数
        self.basic_tab.on_apply()

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        save_action = QAction("保存配置", self)
        save_action.triggered.connect(self.save_config)
        file_menu.addAction(save_action)
        load_action = QAction("加载配置", self)
        load_action.triggered.connect(self.load_config)
        file_menu.addAction(load_action)
        file_menu.addSeparator()
        export_report_action = QAction("导出报告", self)
        export_report_action.triggered.connect(self.export_report)
        file_menu.addAction(export_report_action)
        file_menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_tabs(self):
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.basic_tab = BasicParamsTab(self)
        self.bias_tab = BiasCalculatorTab(self)
        self.curve_tab = OutputCharacteristicsTab(self)
        self.datasheet_tab = DatasheetTab(self)

        self.tab_widget.addTab(self.basic_tab, "基础参数")
        self.tab_widget.addTab(self.bias_tab, "偏置计算")
        self.tab_widget.addTab(self.curve_tab, "特性曲线")
        self.tab_widget.addTab(self.datasheet_tab, "数据表")

    def update_status_message(self, msg):
        self.status_bar.showMessage(msg, 3000)

    def on_basic_params_changed(self, params):
        if params:
            self.bias_tab.update_transistor_params(params)
            self.curve_tab.update_transistor_params(params)

    def on_datasheet_load(self, params):
        self.basic_tab.set_params(params)
        self.basic_tab.on_apply()

    def save_config(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "保存配置", "", "JSON Files (*.json)")
        if file_path:
            config = {
                'transistor': self.basic_tab.get_params(),
                'bias': {
                    'type': self._get_bias_type(),
                    'vcc': self.bias_tab.vcc_edit.text(),
                    'rc': self.bias_tab.rc_edit.text(),
                    're': self.bias_tab.re_edit.text(),
                    'rb_fixed': self.bias_tab.rb_fixed_edit.text(),
                    'r1': self.bias_tab.r1_edit.text(),
                    'r2': self.bias_tab.r2_edit.text(),
                    'rb_cb': self.bias_tab.rb_cb_edit.text(),
                    'vee': self.bias_tab.vee_edit.text(),
                    're_ee': self.bias_tab.re_ee_edit.text(),
                    'target_ic': self.bias_tab.target_ic_edit.text(),
                    'target_vce': self.bias_tab.target_vce_edit.text(),
                },
                'curve': {
                    'ib_step': self.curve_tab.ib_step_edit.text(),
                    'vce_max': self.curve_tab.vce_max_edit.text(),
                    'vbe_max': self.curve_tab.vbe_max_edit.text(),
                    'points': self.curve_tab.points_edit.text(),
                }
            }
            try:
                with open(file_path, 'w') as f:
                    json.dump(config, f, indent=4)
                self.status_bar.showMessage(f"配置已保存", 3000)
            except Exception as e:
                QMessageBox.critical(self, "保存失败", str(e))

    def _get_bias_type(self):
        if self.bias_tab.bias_fixed_rb.isChecked():
            return 'fixed'
        elif self.bias_tab.bias_divider_rb.isChecked():
            return 'divider'
        elif self.bias_tab.bias_collector_rb.isChecked():
            return 'collector'
        else:
            return 'emitter'

    def load_config(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "加载配置", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    config = json.load(f)
                if 'transistor' in config:
                    self.basic_tab.set_params(config['transistor'])
                    self.basic_tab.on_apply()
                if 'bias' in config:
                    b = config['bias']
                    self.bias_tab.vcc_edit.setText(b.get('vcc', '12'))
                    self.bias_tab.rc_edit.setText(b.get('rc', '1k'))
                    self.bias_tab.re_edit.setText(b.get('re', '0'))
                    self.bias_tab.rb_fixed_edit.setText(b.get('rb_fixed', '100k'))
                    self.bias_tab.r1_edit.setText(b.get('r1', '10k'))
                    self.bias_tab.r2_edit.setText(b.get('r2', '4.7k'))
                    self.bias_tab.rb_cb_edit.setText(b.get('rb_cb', '100k'))
                    self.bias_tab.vee_edit.setText(b.get('vee', '-12'))
                    self.bias_tab.re_ee_edit.setText(b.get('re_ee', '1k'))
                    self.bias_tab.target_ic_edit.setText(b.get('target_ic', '5'))
                    self.bias_tab.target_vce_edit.setText(b.get('target_vce', '6'))
                    # 恢复偏置类型选择
                    bias_type = b.get('type', 'fixed')
                    if bias_type == 'fixed':
                        self.bias_tab.bias_fixed_rb.setChecked(True)
                    elif bias_type == 'divider':
                        self.bias_tab.bias_divider_rb.setChecked(True)
                    elif bias_type == 'collector':
                        self.bias_tab.bias_collector_rb.setChecked(True)
                    else:
                        self.bias_tab.bias_emitter_rb.setChecked(True)
                if 'curve' in config:
                    c = config['curve']
                    self.curve_tab.ib_step_edit.setText(c.get('ib_step', '10'))
                    self.curve_tab.vce_max_edit.setText(c.get('vce_max', '20'))
                    self.curve_tab.vbe_max_edit.setText(c.get('vbe_max', '1.0'))
                    self.curve_tab.points_edit.setText(c.get('points', '100'))
                self.status_bar.showMessage(f"配置已加载", 3000)
            except Exception as e:
                QMessageBox.critical(self, "加载失败", str(e))

    def export_report(self):
        """生成简单的文本报告"""
        file_path, _ = QFileDialog.getSaveFileName(self, "导出报告", "", "Text Files (*.txt);;HTML Files (*.html)")
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write("高级三极管助手 - 设计报告\n")
                    f.write("="*40 + "\n")
                    f.write(f"三极管型号: {self.basic_tab.type_combo.currentText()}\n")
                    params = self.basic_tab.get_params()
                    for k, v in params.items():
                        f.write(f"{k}: {v}\n")
                    f.write("\n偏置工作点:\n")
                    f.write(f"Ic = {self.bias_tab.result_ic_label.text()} mA\n")
                    f.write(f"Vce = {self.bias_tab.result_vce_label.text()} V\n")
                QMessageBox.information(self, "报告已导出", f"报告保存至{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", str(e))

    def show_about(self):
        QMessageBox.about(self, "关于高级三极管助手",
                          "高级三极管助手 专业版 v2.0\n\n"
                          "功能：\n"
                          "• 支持NPN/PNP，含厄尔利电压、温度系数\n"
                          "• 4种偏置结构：固定、分压、集电极反馈、发射极偏置\n"
                          "• 直流工作点、交流增益、输入/输出阻抗\n"
                          "• 温度稳定性分析、稳定性系数\n"
                          "• 输出/输入/转移特性曲线，数据导出\n"
                          "• 可扩展的晶体管数据表库\n"
                          "• 配置保存/加载，报告生成\n\n"
                          "© 2025 电子设计助手")

# --------------------------- 程序入口 ---------------------------
def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))
    window = TransistorAssistant()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()