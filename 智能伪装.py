import sys
import os
import base64
import hashlib
import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QLabel, QLineEdit, QTextEdit, 
                             QPushButton, QFileDialog, QMessageBox, QProgressBar,
                             QComboBox, QSpinBox, QCheckBox, QListWidget, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor


class SteganographyThread(QThread):
    """隐写处理线程"""
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, operation, image_path, text, output_path, password=None):
        super().__init__()
        self.operation = operation  # 'encode' 或 'decode'
        self.image_path = image_path
        self.text = text
        self.output_path = output_path
        self.password = password
    
    def run(self):
        try:
            if self.operation == 'encode':
                self.encode_text()
            else:
                self.decode_text()
        except Exception as e:
            self.error_signal.emit(str(e))
    
    def encode_text(self):
        """将文本编码到图像中"""
        # 打开图像
        image = Image.open(self.image_path)
        self.progress_signal.emit(20)
        
        # 如果文本需要加密
        if self.password:
            self.text = self.encrypt_text(self.text, self.password)
        
        # 将文本转换为二进制
        binary_text = ''.join(format(ord(char), '08b') for char in self.text)
        binary_text += '1111111111111110'  # 结束标记
        
        self.progress_signal.emit(40)
        
        # 获取图像像素数据
        pixels = list(image.getdata())
        width, height = image.size
        pixel_count = width * height
        
        # 检查图像容量
        if len(binary_text) > pixel_count * 3:
            raise ValueError("图像太小，无法隐藏文本")
        
        # 嵌入文本到像素中
        binary_index = 0
        new_pixels = []
        
        for i, pixel in enumerate(pixels):
            if binary_index < len(binary_text):
                if len(pixel) == 4:  # RGBA
                    r, g, b, a = pixel
                else:  # RGB
                    r, g, b = pixel
                    a = 255
                
                # 修改最低有效位
                if binary_index < len(binary_text):
                    r = (r & 0xFE) | int(binary_text[binary_index])
                    binary_index += 1
                
                if binary_index < len(binary_text):
                    g = (g & 0xFE) | int(binary_text[binary_index])
                    binary_index += 1
                
                if binary_index < len(binary_text):
                    b = (b & 0xFE) | int(binary_text[binary_index])
                    binary_index += 1
                
                if len(pixel) == 4:
                    new_pixels.append((r, g, b, a))
                else:
                    new_pixels.append((r, g, b))
            else:
                new_pixels.append(pixel)
            
            # 更新进度
            if i % 1000 == 0:
                progress = 40 + (i / pixel_count) * 50
                self.progress_signal.emit(int(progress))
        
        self.progress_signal.emit(90)
        
        # 创建新图像
        new_image = Image.new(image.mode, image.size)
        new_image.putdata(new_pixels)
        new_image.save(self.output_path)
        
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"文本已成功隐藏到 {self.output_path}")
    
    def decode_text(self):
        """从图像中解码文本"""
        # 打开图像
        image = Image.open(self.image_path)
        self.progress_signal.emit(20)
        
        # 提取二进制数据
        pixels = list(image.getdata())
        binary_text = ""
        
        for i, pixel in enumerate(pixels):
            if len(pixel) == 4:  # RGBA
                r, g, b, a = pixel
            else:  # RGB
                r, g, b = pixel
            
            # 提取最低有效位
            binary_text += str(r & 1)
            binary_text += str(g & 1)
            binary_text += str(b & 1)
            
            # 检查结束标记
            if binary_text.endswith('1111111111111110'):
                binary_text = binary_text[:-16]  # 移除结束标记
                break
            
            # 更新进度
            if i % 1000 == 0:
                progress = 20 + (i / len(pixels)) * 70
                self.progress_signal.emit(int(progress))
        
        self.progress_signal.emit(90)
        
        # 将二进制转换为文本
        text = ""
        for i in range(0, len(binary_text), 8):
            byte = binary_text[i:i+8]
            if len(byte) == 8:
                text += chr(int(byte, 2))
        
        # 如果文本是加密的，尝试解密
        if self.password:
            try:
                text = self.decrypt_text(text, self.password)
            except:
                pass  # 可能不是加密文本
        
        self.progress_signal.emit(100)
        self.finished_signal.emit(text)
    
    def encrypt_text(self, text, password):
        """加密文本"""
        salt = b'salt_'  # 在实际应用中应使用随机盐
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        fernet = Fernet(key)
        encrypted_text = fernet.encrypt(text.encode())
        return base64.urlsafe_b64encode(encrypted_text).decode()
    
    def decrypt_text(self, text, password):
        """解密文本"""
        try:
            salt = b'salt_'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            fernet = Fernet(key)
            encrypted_text = base64.urlsafe_b64decode(text.encode())
            decrypted_text = fernet.decrypt(encrypted_text)
            return decrypted_text.decode()
        except:
            return "解密失败，请检查密码是否正确"


class TextDisguiseTab(QWidget):
    """文本伪装标签页"""
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 输入组
        input_group = QGroupBox("输入文本")
        input_layout = QVBoxLayout()
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("请输入要伪装的文本...")
        input_layout.addWidget(self.input_text)
        input_group.setLayout(input_layout)
        
        # 选项组
        options_group = QGroupBox("伪装选项")
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("伪装类型:"))
        self.disguise_type = QComboBox()
        self.disguise_type.addItems(["Base64编码", "ROT13密码", "反转文本", "字符替换"])
        options_layout.addWidget(self.disguise_type)
        
        options_layout.addWidget(QLabel("密码:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("可选密码")
        options_layout.addWidget(self.password_input)
        
        options_layout.addStretch()
        options_group.setLayout(options_layout)
        
        # 按钮组
        button_layout = QHBoxLayout()
        self.disguise_btn = QPushButton("伪装文本")
        self.disguise_btn.clicked.connect(self.disguise_text)
        self.reveal_btn = QPushButton("还原文本")
        self.reveal_btn.clicked.connect(self.reveal_text)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_text)
        
        button_layout.addWidget(self.disguise_btn)
        button_layout.addWidget(self.reveal_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        # 输出组
        output_group = QGroupBox("输出文本")
        output_layout = QVBoxLayout()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        
        # 添加到主布局
        layout.addWidget(input_group)
        layout.addWidget(options_group)
        layout.addLayout(button_layout)
        layout.addWidget(output_group)
        
        self.setLayout(layout)
    
    def disguise_text(self):
        """伪装文本"""
        text = self.input_text.toPlainText()
        if not text:
            QMessageBox.warning(self, "警告", "请输入要伪装的文本")
            return
        
        disguise_type = self.disguise_type.currentText()
        password = self.password_input.text()
        
        try:
            if disguise_type == "Base64编码":
                disguised = base64.b64encode(text.encode()).decode()
            elif disguise_type == "ROT13密码":
                disguised = self.rot13(text)
            elif disguise_type == "反转文本":
                disguised = text[::-1]
            elif disguise_type == "字符替换":
                disguised = self.character_substitution(text)
            
            # 如果提供了密码，进行加密
            if password:
                disguised = self.encrypt_text(disguised, password)
            
            self.output_text.setPlainText(disguised)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"伪装失败: {str(e)}")
    
    def reveal_text(self):
        """还原文本"""
        text = self.output_text.toPlainText()
        if not text:
            QMessageBox.warning(self, "警告", "没有要还原的文本")
            return
        
        disguise_type = self.disguise_type.currentText()
        password = self.password_input.text()
        
        try:
            # 如果提供了密码，尝试解密
            if password:
                try:
                    text = self.decrypt_text(text, password)
                except:
                    pass  # 可能不是加密文本
            
            if disguise_type == "Base64编码":
                revealed = base64.b64decode(text.encode()).decode()
            elif disguise_type == "ROT13密码":
                revealed = self.rot13(text)
            elif disguise_type == "反转文本":
                revealed = text[::-1]
            elif disguise_type == "字符替换":
                revealed = self.reverse_substitution(text)
            
            self.input_text.setPlainText(revealed)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"还原失败: {str(e)}")
    
    def clear_text(self):
        """清空文本"""
        self.input_text.clear()
        self.output_text.clear()
    
    def rot13(self, text):
        """ROT13加密/解密"""
        result = ""
        for char in text:
            if 'a' <= char <= 'z':
                result += chr((ord(char) - ord('a') + 13) % 26 + ord('a'))
            elif 'A' <= char <= 'Z':
                result += chr((ord(char) - ord('A') + 13) % 26 + ord('A'))
            else:
                result += char
        return result
    
    def character_substitution(self, text):
        """字符替换伪装"""
        # 简单的字符替换表
        substitution_table = {
            'a': 'z', 'b': 'y', 'c': 'x', 'd': 'w', 'e': 'v',
            'f': 'u', 'g': 't', 'h': 's', 'i': 'r', 'j': 'q',
            'k': 'p', 'l': 'o', 'm': 'n', 'n': 'm', 'o': 'l',
            'p': 'k', 'q': 'j', 'r': 'i', 's': 'h', 't': 'g',
            'u': 'f', 'v': 'e', 'w': 'd', 'x': 'c', 'y': 'b',
            'z': 'a'
        }
        
        result = ""
        for char in text.lower():
            if char in substitution_table:
                result += substitution_table[char]
            else:
                result += char
        return result
    
    def reverse_substitution(self, text):
        """反向字符替换"""
        return self.character_substitution(text)  # 替换表是对称的
    
    def encrypt_text(self, text, password):
        """加密文本"""
        salt = b'salt_'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        fernet = Fernet(key)
        encrypted_text = fernet.encrypt(text.encode())
        return base64.urlsafe_b64encode(encrypted_text).decode()
    
    def decrypt_text(self, text, password):
        """解密文本"""
        salt = b'salt_'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        fernet = Fernet(key)
        encrypted_text = base64.urlsafe_b64decode(text.encode())
        decrypted_text = fernet.decrypt(encrypted_text)
        return decrypted_text.decode()


class ImageSteganographyTab(QWidget):
    """图像隐写标签页"""
    def __init__(self):
        super().__init__()
        self.current_image_path = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 图像选择组
        image_group = QGroupBox("图像操作")
        image_layout = QHBoxLayout()
        
        self.image_path = QLineEdit()
        self.image_path.setReadOnly(True)
        image_layout.addWidget(QLabel("图像路径:"))
        image_layout.addWidget(self.image_path)
        
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.clicked.connect(self.browse_image)
        image_layout.addWidget(self.browse_btn)
        
        image_group.setLayout(image_layout)
        
        # 文本输入组
        text_group = QGroupBox("文本操作")
        text_layout = QVBoxLayout()
        
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("输入要隐藏的文本...")
        text_layout.addWidget(self.text_input)
        
        text_options_layout = QHBoxLayout()
        text_options_layout.addWidget(QLabel("密码:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("可选密码")
        text_options_layout.addWidget(self.password_input)
        
        text_options_layout.addStretch()
        text_layout.addLayout(text_options_layout)
        
        text_group.setLayout(text_layout)
        
        # 按钮组
        button_layout = QHBoxLayout()
        self.encode_btn = QPushButton("隐藏文本到图像")
        self.encode_btn.clicked.connect(self.encode_text)
        self.decode_btn = QPushButton("从图像提取文本")
        self.decode_btn.clicked.connect(self.decode_text)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_all)
        
        button_layout.addWidget(self.encode_btn)
        button_layout.addWidget(self.decode_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # 输出组
        output_group = QGroupBox("输出")
        output_layout = QVBoxLayout()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        
        # 添加到主布局
        layout.addWidget(image_group)
        layout.addWidget(text_group)
        layout.addLayout(button_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(output_group)
        
        self.setLayout(layout)
    
    def browse_image(self):
        """浏览图像文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图像文件", "", "图像文件 (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.image_path.setText(file_path)
            self.current_image_path = file_path
    
    def encode_text(self):
        """将文本隐藏到图像中"""
        if not self.current_image_path:
            QMessageBox.warning(self, "警告", "请先选择图像文件")
            return
        
        text = self.text_input.toPlainText()
        if not text:
            QMessageBox.warning(self, "警告", "请输入要隐藏的文本")
            return
        
        output_path, _ = QFileDialog.getSaveFileName(
            self, "保存图像", "", "PNG图像 (*.png)")
        if not output_path:
            return
        
        password = self.password_input.text() or None
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动线程
        self.thread = SteganographyThread(
            'encode', self.current_image_path, text, output_path, password)
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.finished_signal.connect(self.operation_finished)
        self.thread.error_signal.connect(self.operation_error)
        self.thread.start()
    
    def decode_text(self):
        """从图像中提取文本"""
        if not self.current_image_path:
            QMessageBox.warning(self, "警告", "请先选择图像文件")
            return
        
        password = self.password_input.text() or None
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动线程
        self.thread = SteganographyThread(
            'decode', self.current_image_path, "", "", password)
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.finished_signal.connect(self.decode_finished)
        self.thread.error_signal.connect(self.operation_error)
        self.thread.start()
    
    def clear_all(self):
        """清空所有内容"""
        self.image_path.clear()
        self.text_input.clear()
        self.output_text.clear()
        self.password_input.clear()
        self.current_image_path = None
        self.progress_bar.setVisible(False)
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def operation_finished(self, message):
        """操作完成"""
        self.progress_bar.setVisible(False)
        self.output_text.setPlainText(message)
        QMessageBox.information(self, "成功", "操作完成")
    
    def decode_finished(self, text):
        """解码完成"""
        self.progress_bar.setVisible(False)
        self.output_text.setPlainText(text)
    
    def operation_error(self, error_message):
        """操作错误"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "错误", f"操作失败: {error_message}")


class FileDisguiseTab(QWidget):
    """文件伪装标签页"""
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 文件选择组
        file_group = QGroupBox("文件操作")
        file_layout = QVBoxLayout()
        
        # 源文件选择
        source_layout = QHBoxLayout()
        self.source_path = QLineEdit()
        self.source_path.setReadOnly(True)
        source_layout.addWidget(QLabel("源文件:"))
        source_layout.addWidget(self.source_path)
        
        self.browse_source_btn = QPushButton("浏览")
        self.browse_source_btn.clicked.connect(self.browse_source_file)
        source_layout.addWidget(self.browse_source_btn)
        
        file_layout.addLayout(source_layout)
        
        # 伪装文件选择
        disguise_layout = QHBoxLayout()
        self.disguise_path = QLineEdit()
        self.disguise_path.setReadOnly(True)
        disguise_layout.addWidget(QLabel("伪装文件:"))
        disguise_layout.addWidget(self.disguise_path)
        
        self.browse_disguise_btn = QPushButton("浏览")
        self.browse_disguise_btn.clicked.connect(self.browse_disguise_file)
        disguise_layout.addWidget(self.browse_disguise_btn)
        
        file_layout.addLayout(disguise_layout)
        
        # 输出文件
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setReadOnly(True)
        output_layout.addWidget(QLabel("输出文件:"))
        output_layout.addWidget(self.output_path)
        
        self.browse_output_btn = QPushButton("浏览")
        self.browse_output_btn.clicked.connect(self.browse_output_file)
        output_layout.addWidget(self.browse_output_btn)
        
        file_layout.addLayout(output_layout)
        
        file_group.setLayout(file_layout)
        
        # 选项组
        options_group = QGroupBox("伪装选项")
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("伪装类型:"))
        self.disguise_type = QComboBox()
        self.disguise_type.addItems(["文件附加", "文件头替换", "加密伪装"])
        options_layout.addWidget(self.disguise_type)
        
        options_layout.addWidget(QLabel("密码:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("可选密码")
        options_layout.addWidget(self.password_input)
        
        options_layout.addStretch()
        options_group.setLayout(options_layout)
        
        # 按钮组
        button_layout = QHBoxLayout()
        self.disguise_btn = QPushButton("伪装文件")
        self.disguise_btn.clicked.connect(self.disguise_file)
        self.extract_btn = QPushButton("提取文件")
        self.extract_btn.clicked.connect(self.extract_file)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_all)
        
        button_layout.addWidget(self.disguise_btn)
        button_layout.addWidget(self.extract_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # 输出信息
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        
        # 添加到主布局
        layout.addWidget(file_group)
        layout.addWidget(options_group)
        layout.addLayout(button_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.info_text)
        
        self.setLayout(layout)
    
    def browse_source_file(self):
        """浏览源文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择源文件")
        if file_path:
            self.source_path.setText(file_path)
    
    def browse_disguise_file(self):
        """浏览伪装文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择伪装文件")
        if file_path:
            self.disguise_path.setText(file_path)
    
    def browse_output_file(self):
        """选择输出文件"""
        file_path, _ = QFileDialog.getSaveFileName(self, "保存输出文件")
        if file_path:
            self.output_path.setText(file_path)
    
    def disguise_file(self):
        """伪装文件"""
        source_path = self.source_path.text()
        disguise_path = self.disguise_path.text()
        output_path = self.output_path.text()
        
        if not source_path or not disguise_path or not output_path:
            QMessageBox.warning(self, "警告", "请选择所有必要的文件")
            return
        
        disguise_type = self.disguise_type.currentText()
        password = self.password_input.text() or None
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            if disguise_type == "文件附加":
                self.append_files(source_path, disguise_path, output_path, password)
            elif disguise_type == "文件头替换":
                self.replace_header(source_path, disguise_path, output_path, password)
            elif disguise_type == "加密伪装":
                self.encrypt_file(source_path, disguise_path, output_path, password)
            
            self.progress_bar.setValue(100)
            self.info_text.append(f"文件伪装完成: {output_path}")
            QMessageBox.information(self, "成功", "文件伪装完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"文件伪装失败: {str(e)}")
        finally:
            self.progress_bar.setVisible(False)
    
    def extract_file(self):
        """提取文件"""
        disguised_path = self.source_path.text()
        output_path = self.output_path.text()
        
        if not disguised_path or not output_path:
            QMessageBox.warning(self, "警告", "请选择伪装文件和输出路径")
            return
        
        disguise_type = self.disguise_type.currentText()
        password = self.password_input.text() or None
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            if disguise_type == "文件附加":
                self.extract_appended_file(disguised_path, output_path, password)
            elif disguise_type == "文件头替换":
                self.extract_replaced_header(disguised_path, output_path, password)
            elif disguise_type == "加密伪装":
                self.decrypt_file(disguised_path, output_path, password)
            
            self.progress_bar.setValue(100)
            self.info_text.append(f"文件提取完成: {output_path}")
            QMessageBox.information(self, "成功", "文件提取完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"文件提取失败: {str(e)}")
        finally:
            self.progress_bar.setVisible(False)
    
    def clear_all(self):
        """清空所有内容"""
        self.source_path.clear()
        self.disguise_path.clear()
        self.output_path.clear()
        self.password_input.clear()
        self.info_text.clear()
        self.progress_bar.setVisible(False)
    
    def append_files(self, source_path, disguise_path, output_path, password=None):
        """将源文件附加到伪装文件中"""
        with open(disguise_path, 'rb') as disguise_file:
            disguise_data = disguise_file.read()
        
        with open(source_path, 'rb') as source_file:
            source_data = source_file.read()
        
        # 如果提供了密码，加密源数据
        if password:
            source_data = self.encrypt_data(source_data, password)
        
        # 将源文件大小和校验和信息添加到伪装文件中
        size_info = len(source_data).to_bytes(8, byteorder='big')
        checksum = hashlib.md5(source_data).digest()
        
        with open(output_path, 'wb') as output_file:
            output_file.write(disguise_data)
            output_file.write(b'STEGO_MARKER')
            output_file.write(size_info)
            output_file.write(checksum)
            output_file.write(source_data)
    
    def extract_appended_file(self, disguised_path, output_path, password=None):
        """从伪装文件中提取源文件"""
        with open(disguised_path, 'rb') as disguised_file:
            data = disguised_file.read()
        
        # 查找标记
        marker_index = data.find(b'STEGO_MARKER')
        if marker_index == -1:
            raise ValueError("未找到隐藏文件")
        
        # 提取大小和校验和
        size_info = data[marker_index+12:marker_index+20]
        file_size = int.from_bytes(size_info, byteorder='big')
        checksum = data[marker_index+20:marker_index+36]
        file_data = data[marker_index+36:marker_index+36+file_size]
        
        # 验证校验和
        if hashlib.md5(file_data).digest() != checksum:
            raise ValueError("文件校验失败")
        
        # 如果提供了密码，尝试解密
        if password:
            try:
                file_data = self.decrypt_data(file_data, password)
            except:
                pass  # 可能不是加密数据
        
        with open(output_path, 'wb') as output_file:
            output_file.write(file_data)
    
    def replace_header(self, source_path, disguise_path, output_path, password=None):
        """替换文件头进行伪装"""
        # 读取伪装文件的文件头
        with open(disguise_path, 'rb') as disguise_file:
            disguise_header = disguise_file.read(100)  # 读取前100字节作为文件头
        
        # 读取源文件
        with open(source_path, 'rb') as source_file:
            source_data = source_file.read()
        
        # 如果提供了密码，加密源数据
        if password:
            source_data = self.encrypt_data(source_data, password)
        
        # 将伪装文件头与源数据结合
        with open(output_path, 'wb') as output_file:
            output_file.write(disguise_header)
            output_file.write(b'STEGO_DATA')
            output_file.write(len(source_data).to_bytes(8, byteorder='big'))
            output_file.write(source_data)
    
    def extract_replaced_header(self, disguised_path, output_path, password=None):
        """从伪装文件中提取源文件"""
        with open(disguised_path, 'rb') as disguised_file:
            data = disguised_file.read()
        
        # 查找数据标记
        marker_index = data.find(b'STEGO_DATA')
        if marker_index == -1:
            raise ValueError("未找到隐藏文件")
        
        # 提取文件大小和数据
        size_info = data[marker_index+10:marker_index+18]
        file_size = int.from_bytes(size_info, byteorder='big')
        file_data = data[marker_index+18:marker_index+18+file_size]
        
        # 如果提供了密码，尝试解密
        if password:
            try:
                file_data = self.decrypt_data(file_data, password)
            except:
                pass  # 可能不是加密数据
        
        with open(output_path, 'wb') as output_file:
            output_file.write(file_data)
    
    def encrypt_file(self, source_path, disguise_path, output_path, password=None):
        """加密伪装文件"""
        # 读取源文件
        with open(source_path, 'rb') as source_file:
            source_data = source_file.read()
        
        # 读取伪装文件
        with open(disguise_path, 'rb') as disguise_file:
            disguise_data = disguise_file.read()
        
        # 使用密码加密源数据
        if password:
            encrypted_data = self.encrypt_data(source_data, password)
        else:
            # 如果没有密码，使用默认密钥
            key = Fernet.generate_key()
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(source_data)
            # 将密钥保存到文件开头
            disguise_data = key + b'KEY_MARKER' + disguise_data
        
        # 将加密数据与伪装文件结合
        with open(output_path, 'wb') as output_file:
            output_file.write(disguise_data)
            output_file.write(b'ENCRYPTED_DATA')
            output_file.write(len(encrypted_data).to_bytes(8, byteorder='big'))
            output_file.write(encrypted_data)
    
    def decrypt_file(self, disguised_path, output_path, password=None):
        """解密伪装文件"""
        with open(disguised_path, 'rb') as disguised_file:
            data = disguised_file.read()
        
        # 查找加密数据标记
        marker_index = data.find(b'ENCRYPTED_DATA')
        if marker_index == -1:
            raise ValueError("未找到加密数据")
        
        # 检查是否有密钥标记
        key_marker_index = data.find(b'KEY_MARKER')
        if key_marker_index != -1 and key_marker_index < marker_index:
            # 提取密钥
            key = data[:key_marker_index]
            fernet = Fernet(key)
        
        # 提取加密数据大小和数据
        size_info = data[marker_index+14:marker_index+22]
        data_size = int.from_bytes(size_info, byteorder='big')
        encrypted_data = data[marker_index+22:marker_index+22+data_size]
        
        # 解密数据
        if password:
            decrypted_data = self.decrypt_data(encrypted_data, password)
        else:
            if key_marker_index == -1:
                raise ValueError("需要密码来解密文件")
            decrypted_data = fernet.decrypt(encrypted_data)
        
        with open(output_path, 'wb') as output_file:
            output_file.write(decrypted_data)
    
    def encrypt_data(self, data, password):
        """加密数据"""
        salt = b'salt_'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data)
        return encrypted_data
    
    def decrypt_data(self, data, password):
        """解密数据"""
        salt = b'salt_'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(data)
        return decrypted_data


class NetworkDisguiseTab(QWidget):
    """网络伪装标签页"""
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 网络伪装选项
        network_group = QGroupBox("网络伪装选项")
        network_layout = QVBoxLayout()
        
        # 协议选择
        protocol_layout = QHBoxLayout()
        protocol_layout.addWidget(QLabel("伪装协议:"))
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["HTTP", "DNS", "ICMP", "TCP"])
        protocol_layout.addWidget(self.protocol_combo)
        protocol_layout.addStretch()
        
        # 目标设置
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("目标地址:"))
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("例如: example.com 或 192.168.1.1")
        target_layout.addWidget(self.target_input)
        
        target_layout.addWidget(QLabel("端口:"))
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("例如: 80")
        target_layout.addWidget(self.port_input)
        
        network_layout.addLayout(protocol_layout)
        network_layout.addLayout(target_layout)
        
        network_group.setLayout(network_layout)
        
        # 数据输入
        data_group = QGroupBox("数据操作")
        data_layout = QVBoxLayout()
        
        self.data_input = QTextEdit()
        self.data_input.setPlaceholderText("输入要伪装传输的数据...")
        data_layout.addWidget(self.data_input)
        
        data_options_layout = QHBoxLayout()
        data_options_layout.addWidget(QLabel("加密密码:"))
        self.encrypt_password = QLineEdit()
        self.encrypt_password.setPlaceholderText("可选密码")
        data_options_layout.addWidget(self.encrypt_password)
        
        data_options_layout.addStretch()
        data_layout.addLayout(data_options_layout)
        
        data_group.setLayout(data_layout)
        
        # 按钮组
        button_layout = QHBoxLayout()
        self.simulate_btn = QPushButton("模拟传输")
        self.simulate_btn.clicked.connect(self.simulate_transmission)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_all)
        
        button_layout.addWidget(self.simulate_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        # 输出信息
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        
        # 添加到主布局
        layout.addWidget(network_group)
        layout.addWidget(data_group)
        layout.addLayout(button_layout)
        layout.addWidget(self.output_text)
        
        self.setLayout(layout)
    
    def simulate_transmission(self):
        """模拟网络传输"""
        protocol = self.protocol_combo.currentText()
        target = self.target_input.text()
        port = self.port_input.text()
        data = self.data_input.toPlainText()
        password = self.encrypt_password.text() or None
        
        if not target or not data:
            QMessageBox.warning(self, "警告", "请输入目标地址和数据")
            return
        
        try:
            # 模拟数据处理
            if password:
                encrypted_data = self.encrypt_data(data, password)
                data_hex = encrypted_data.hex()
                self.output_text.append(f"数据已加密: {data_hex[:50]}...")
            else:
                data_hex = data.encode().hex()
            
            # 模拟协议伪装
            if protocol == "HTTP":
                self.simulate_http(target, port, data_hex)
            elif protocol == "DNS":
                self.simulate_dns(target, data_hex)
            elif protocol == "ICMP":
                self.simulate_icmp(target, data_hex)
            elif protocol == "TCP":
                self.simulate_tcp(target, port, data_hex)
            
            self.output_text.append("模拟传输完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"模拟传输失败: {str(e)}")
    
    def clear_all(self):
        """清空所有内容"""
        self.target_input.clear()
        self.port_input.clear()
        self.data_input.clear()
        self.encrypt_password.clear()
        self.output_text.clear()
    
    def simulate_http(self, target, port, data_hex):
        """模拟HTTP协议伪装"""
        self.output_text.append(f"模拟HTTP协议伪装:")
        self.output_text.append(f"目标: {target}:{port}")
        self.output_text.append(f"伪装为HTTP GET请求")
        
        # 将数据分割并伪装为HTTP参数
        chunks = [data_hex[i:i+50] for i in range(0, len(data_hex), 50)]
        for i, chunk in enumerate(chunks):
            self.output_text.append(f"数据块 {i+1}: /?data={chunk}")
        
        self.output_text.append("所有数据已伪装为HTTP请求参数")
    
    def simulate_dns(self, target, data_hex):
        """模拟DNS协议伪装"""
        self.output_text.append(f"模拟DNS协议伪装:")
        self.output_text.append(f"目标DNS服务器: {target}")
        self.output_text.append(f"伪装为DNS查询请求")
        
        # 将数据分割并伪装为DNS查询
        chunks = [data_hex[i:i+30] for i in range(0, len(data_hex), 30)]
        for i, chunk in enumerate(chunks):
            domain = f"{chunk}.example.com"
            self.output_text.append(f"查询 {i+1}: {domain}")
        
        self.output_text.append("所有数据已伪装为DNS查询")
    
    def simulate_icmp(self, target, data_hex):
        """模拟ICMP协议伪装"""
        self.output_text.append(f"模拟ICMP协议伪装:")
        self.output_text.append(f"目标: {target}")
        self.output_text.append(f"伪装为ICMP Echo请求")
        
        # 将数据嵌入ICMP数据包
        chunks = [data_hex[i:i+32] for i in range(0, len(data_hex), 32)]
        for i, chunk in enumerate(chunks):
            self.output_text.append(f"ICMP数据包 {i+1}: 数据={chunk}")
        
        self.output_text.append("所有数据已伪装为ICMP数据包")
    
    def simulate_tcp(self, target, port, data_hex):
        """模拟TCP协议伪装"""
        self.output_text.append(f"模拟TCP协议伪装:")
        self.output_text.append(f"目标: {target}:{port}")
        self.output_text.append(f"建立TCP连接并发送伪装数据")
        
        # 模拟TCP数据流
        chunks = [data_hex[i:i+100] for i in range(0, len(data_hex), 100)]
        for i, chunk in enumerate(chunks):
            self.output_text.append(f"TCP段 {i+1}: [SEQ={i*100} ACK={(i+1)*100}] 数据长度={len(chunk)}")
        
        self.output_text.append("所有数据已通过TCP连接发送")
    
    def encrypt_data(self, data, password):
        """加密数据"""
        salt = b'salt_'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data.encode())
        return encrypted_data


class AdvancedDisguiseSystem(QMainWindow):
    """高级伪装系统主窗口"""
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("智能伪装系统 - 高级工具库")
        self.setGeometry(100, 100, 900, 700)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #363636;
            }
            QTabBar::tab {
                background-color: #444;
                color: #fff;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #5a5a5a;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #5a5a5a;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #6a6a6a;
            }
            QPushButton:pressed {
                background-color: #4a4a4a;
            }
            QTextEdit, QLineEdit {
                background-color: #404040;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
            }
        """)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 添加各个功能标签页
        self.text_tab = TextDisguiseTab()
        self.image_tab = ImageSteganographyTab()
        self.file_tab = FileDisguiseTab()
        self.network_tab = NetworkDisguiseTab()
        
        self.tab_widget.addTab(self.text_tab, "文本伪装")
        self.tab_widget.addTab(self.image_tab, "图像隐写")
        self.tab_widget.addTab(self.file_tab, "文件伪装")
        self.tab_widget.addTab(self.network_tab, "网络伪装")
        
        self.setCentralWidget(self.tab_widget)
        
        # 添加状态栏
        self.statusBar().showMessage("就绪")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序字体
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = AdvancedDisguiseSystem()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()