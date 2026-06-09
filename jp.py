import ast
import re
import random
import string
import hashlib
import base64
import zlib
import marshal
import types
import sys
import os
import importlib
import inspect
from typing import Dict, List, Set, Optional, Tuple, Any, Union
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSplitter,
                             QFileDialog, QMessageBox, QComboBox, QCheckBox,
                             QTabWidget, QGroupBox, QSpinBox, QProgressBar,
                             QTreeWidget, QTreeWidgetItem, QHeaderView, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QTextCursor
import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class PythonHighlighter(QSyntaxHighlighter):
    """Python 语法高亮器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        self.setup_rules()
    
    def setup_rules(self):
        # 关键字格式
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(200, 120, 50))
        keyword_format.setFontWeight(QFont.Bold)
        
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'finally', 'for', 'from',
            'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal',
            'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield'
        ]
        
        for word in keywords:
            pattern = r'\b' + word + r'\b'
            self.highlighting_rules.append((re.compile(pattern), keyword_format))
        
        # 字符串格式
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0, 150, 0))
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlighting_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
        
        # 注释格式
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(150, 150, 150))
        self.highlighting_rules.append((re.compile(r'#.*'), comment_format))
        
        # 数字格式
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(180, 100, 180))
        self.highlighting_rules.append((re.compile(r'\b[0-9]+\b'), number_format))
        
        # 函数调用格式
        function_format = QTextCharFormat()
        function_format.setForeground(QColor(30, 144, 255))
        self.highlighting_rules.append((re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?=\()'), function_format))
        
        # 类名格式
        class_format = QTextCharFormat()
        class_format.setForeground(QColor(139, 0, 139))
        class_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((re.compile(r'\b(class)\s+([a-zA-Z_][a-zA-Z0-9_]*)'), class_format))
    
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, format)


class ImportAnalyzer(ast.NodeVisitor):
    """AST访问器，用于分析导入语句"""
    
    def __init__(self):
        self.imports = set()
        self.imported_names = set()
        self.imported_modules = set()
        self.aliases = {}
        self.imported_functions = set()
        self.imported_classes = set()
        self.imported_variables = set()
        self.import_attributes = set()  # 新增：存储导入模块的属性
    
    def visit_Import(self, node):
        for alias in node.names:
            module_name = alias.name
            self.imports.add(module_name)
            self.imported_modules.add(module_name)
            
            if alias.asname:
                self.imported_names.add(alias.asname)
                self.aliases[alias.asname] = module_name
                # 添加模块级别的导入
                self.imported_variables.add(alias.asname)
            else:
                # 对于import module，添加模块名到导入名称
                parts = module_name.split('.')
                base_module_name = parts[0]
                self.imported_names.add(base_module_name)
                self.aliases[base_module_name] = module_name
                # 添加模块级别的导入
                self.imported_variables.add(base_module_name)
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        module_name = node.module or ""
        level = node.level
        
        if module_name:
            full_module_name = "." * level + module_name
            self.imports.add(full_module_name)
            self.imported_modules.add(full_module_name)
        
        for alias in node.names:
            imported_item = alias.name
            self.imports.add(imported_item)
            
            if alias.asname:
                imported_name = alias.asname
                self.imported_names.add(imported_name)
                self.aliases[imported_name] = f"{module_name}.{imported_item}" if module_name else imported_item
                
                # 根据名称特征判断类型
                if imported_name[0].isupper():
                    self.imported_classes.add(imported_name)
                elif imported_name.startswith('_'):
                    self.imported_variables.add(imported_name)
                else:
                    self.imported_functions.add(imported_name)
            else:
                imported_name = imported_item
                self.imported_names.add(imported_name)
                self.aliases[imported_name] = f"{module_name}.{imported_item}" if module_name else imported_item
                
                # 根据名称特征判断类型
                if imported_name[0].isupper():
                    self.imported_classes.add(imported_name)
                elif imported_name.startswith('_'):
                    self.imported_variables.add(imported_name)
                else:
                    self.imported_functions.add(imported_name)
        
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        # 新增：分析属性访问，如 patches.Circle
        if isinstance(node.value, ast.Name) and node.value.id in self.imported_names:
            # 如果属性访问的是导入的模块
            self.import_attributes.add(node.attr)
        
        self.generic_visit(node)


class CodeAnalyzer(ast.NodeVisitor):
    """AST访问器，用于分析代码中的标识符"""
    
    def __init__(self, imported_names, import_attributes):
        self.variables = set()
        self.functions = set()
        self.classes = set()
        self.imported_names = imported_names
        self.import_attributes = import_attributes  # 新增：导入模块的属性
        self.current_class = None
    
    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Param)):
            # 只收集赋值和参数中的名称
            if (node.id not in self.imported_names and 
                node.id not in self.import_attributes):  # 新增：检查属性
                self.variables.add(node.id)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        if (node.name not in self.imported_names and 
            node.name not in self.import_attributes):  # 新增：检查属性
            self.functions.add(node.name)
        
        # 收集函数参数
        for arg in node.args.args:
            if (arg.arg not in self.imported_names and 
                arg.arg not in self.import_attributes):  # 新增：检查属性
                self.variables.add(arg.arg)
        
        # 收集可变参数和关键字参数
        if node.args.vararg and (node.args.vararg.arg not in self.imported_names and 
                                 node.args.vararg.arg not in self.import_attributes):  # 新增：检查属性
            self.variables.add(node.args.vararg.arg)
        
        if node.args.kwarg and (node.args.kwarg.arg not in self.imported_names and 
                                node.args.kwarg.arg not in self.import_attributes):  # 新增：检查属性
            self.variables.add(node.args.kwarg.arg)
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        if (node.name not in self.imported_names and 
            node.name not in self.import_attributes):  # 新增：检查属性
            self.classes.add(node.name)
        
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name) and (target.id not in self.imported_names and 
                                                 target.id not in self.import_attributes):  # 新增：检查属性
                self.variables.add(target.id)
            elif isinstance(target, ast.Tuple):
                for elt in target.elts:
                    if isinstance(elt, ast.Name) and (elt.id not in self.imported_names and 
                                                      elt.id not in self.import_attributes):  # 新增：检查属性
                        self.variables.add(elt.id)
        self.generic_visit(node)
    
    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name) and (node.target.id not in self.imported_names and 
                                                  node.target.id not in self.import_attributes):  # 新增：检查属性
            self.variables.add(node.target.id)
        self.generic_visit(node)
    
    def visit_For(self, node):
        if isinstance(node.target, ast.Name) and (node.target.id not in self.imported_names and 
                                                  node.target.id not in self.import_attributes):  # 新增：检查属性
            self.variables.add(node.target.id)
        elif isinstance(node.target, ast.Tuple):
            for elt in node.target.elts:
                if isinstance(elt, ast.Name) and (elt.id not in self.imported_names and 
                                                  elt.id not in self.import_attributes):  # 新增：检查属性
                    self.variables.add(elt.id)
        self.generic_visit(node)
    
    def visit_With(self, node):
        for item in node.items:
            if item.optional_vars:
                if isinstance(item.optional_vars, ast.Name) and (item.optional_vars.id not in self.imported_names and 
                                                                 item.optional_vars.id not in self.import_attributes):  # 新增：检查属性
                    self.variables.add(item.optional_vars.id)
                elif isinstance(item.optional_vars, ast.Tuple):
                    for elt in item.optional_vars.elts:
                        if isinstance(elt, ast.Name) and (elt.id not in self.imported_names and 
                                                          elt.id not in self.import_attributes):  # 新增：检查属性
                            self.variables.add(elt.id)
        self.generic_visit(node)


class AdvancedObfuscationEngine:
    """高级混淆引擎"""
    
    def __init__(self):
        self.var_mapping: Dict[str, str] = {}
        self.func_mapping: Dict[str, str] = {}
        self.class_mapping: Dict[str, str] = {}
        self.used_names: Set[str] = set()
        self.encryption_method = "random"
        self.obfuscation_level = 1
        self.encrypt_strings = False
        self.compress_code = False
        self.anti_debug = False
        self.control_flow_obfuscation = False
        self.encryption_key = None
        self.insert_dummy_code = False
        self.rename_parameters = True
        
        # 排除列表（不混淆的标识符）
        self.exclude_list = set()
        self.imported_modules = set()
        self.imported_names = set()
        self.import_aliases = {}
        self.imported_functions = set()
        self.imported_classes = set()
        self.imported_variables = set()
        self.import_attributes = set()  # 新增：导入模块的属性
        
        # 初始化加密密钥
        self.generate_encryption_key()
    
    def generate_encryption_key(self):
        """生成加密密钥"""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(b"default_password")
        self.encryption_key = base64.urlsafe_b64encode(key)
    
    def set_encryption_key(self, password: str):
        """设置自定义加密密钥"""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        self.encryption_key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def encrypt_string(self, s: str) -> str:
        """加密字符串"""
        if not self.encryption_key:
            self.generate_encryption_key()
        
        # 确保 encryption_key 是字节串
        if isinstance(self.encryption_key, str):
            key = self.encryption_key.encode()
        else:
            key = self.encryption_key
        
        try:
            fernet = Fernet(key)
            encrypted = fernet.encrypt(s.encode())
            return f"Fernet({key!r}).decrypt({encrypted!r}).decode()"
        except Exception as e:
            print(f"字符串加密失败: {e}")
            return f"'{s}'"  # 如果加密失败，返回原始字符串
    
    def generate_name(self, original_name: str, name_type: str = "var") -> str:
        """生成加密后的名称"""
        # 检查是否在排除列表中
        if (original_name in self.exclude_list or 
            original_name in self.imported_names or 
            original_name in self.import_attributes):  # 新增：检查属性
            return original_name
            
        # 保留命名约定（蛇形/驼峰）
        if self.obfuscation_level >= 2:
            if original_name.startswith("_"):
                prefix = "_"
                if original_name.startswith("__"):
                    prefix = "__"
                base_name = original_name[len(prefix):]
            else:
                prefix = ""
                base_name = original_name
            
            # 检测命名风格
            is_snake_case = '_' in base_name and base_name.islower()
            is_camel_case = not is_snake_case and base_name and base_name[0].isupper()
            
            if self.encryption_method == "random":
                # 生成随机名称
                if is_snake_case:
                    new_name = self._generate_snake_case_name()
                elif is_camel_case:
                    new_name = self._generate_camel_case_name()
                else:
                    new_name = self._generate_random_name()
                
                return prefix + new_name
            elif self.encryption_method == "hash":
                # 使用哈希生成名称
                hash_obj = hashlib.sha256(original_name.encode())
                hash_hex = hash_obj.hexdigest()[:12]
                
                if is_snake_case:
                    new_name = f"var_{hash_hex}"
                elif is_camel_case:
                    new_name = f"Var{hash_hex.title()}"
                else:
                    new_name = f"v{hash_hex}"
                
                return prefix + new_name
            elif self.encryption_method == "base64":
                # 使用Base64编码
                encoded = base64.b64encode(original_name.encode()).decode()
                # 移除非字母数字字符
                encoded = re.sub(r'[^a-zA-Z0-9]', '', encoded)[:12]
                
                if is_snake_case:
                    new_name = f"b_{encoded.lower()}"
                elif is_camel_case:
                    new_name = f"B{encoded.title()}"
                else:
                    new_name = f"b{encoded}"
                
                return prefix + new_name
            elif self.encryption_method == "leet":
                # 使用Leet语混淆
                leet_map = {
                    'a': '4', 'b': '8', 'e': '3', 'g': '6', 'i': '1',
                    'l': '1', 'o': '0', 's': '5', 't': '7', 'z': '2'
                }
                
                new_name = original_name.lower()
                for char, replacement in leet_map.items():
                    new_name = new_name.replace(char, replacement)
                
                # 确保名称唯一
                if new_name in self.used_names:
                    new_name = f"{new_name}_{len(self.used_names)}"
                
                self.used_names.add(new_name)
                return new_name
        else:
            # 简单混淆
            if self.encryption_method == "random":
                return self._generate_random_name()
            elif self.encryption_method == "hash":
                hash_obj = hashlib.md5(original_name.encode())
                return f"v{hash_obj.hexdigest()[:8]}"
            elif self.encryption_method == "base64":
                encoded = base64.b64encode(original_name.encode()).decode()
                return f"b{re.sub(r'[^a-zA-Z0-9]', '', encoded)[:10]}"
            elif self.encryption_method == "leet":
                leet_map = {
                    'a': '4', 'b': '8', 'e': '3', 'g': '6', 'i': '1',
                    'l': '1', 'o': '0', 's': '5', 't': '7', 'z': '2'
                }
                
                new_name = original_name.lower()
                for char, replacement in leet_map.items():
                    new_name = new_name.replace(char, replacement)
                
                if new_name in self.used_names:
                    new_name = f"{new_name}_{len(self.used_names)}"
                
                self.used_names.add(new_name)
                return new_name
        
        return original_name  # 默认返回原名称
    
    def _generate_random_name(self) -> str:
        """生成随机变量名"""
        length = random.randint(6, 15)
        chars = string.ascii_letters + string.digits
        while True:
            name = ''.join(random.choice(chars) for _ in range(length))
            if name not in self.used_names and not name[0].isdigit():
                self.used_names.add(name)
                return name
    
    def _generate_snake_case_name(self) -> str:
        """生成蛇形命名风格的随机名称"""
        parts = random.randint(2, 4)
        name_parts = []
        for _ in range(parts):
            length = random.randint(3, 8)
            name_parts.append(''.join(random.choice(string.ascii_lowercase) for _ in range(length)))
        
        name = '_'.join(name_parts)
        if name in self.used_names:
            return self._generate_snake_case_name()
        
        self.used_names.add(name)
        return name
    
    def _generate_camel_case_name(self) -> str:
        """生成驼峰命名风格的随机名称"""
        parts = random.randint(2, 4)
        name_parts = []
        for i in range(parts):
            length = random.randint(3, 8)
            part = ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
            if i > 0:
                part = part.title()
            name_parts.append(part)
        
        name = ''.join(name_parts)
        if name in self.used_names:
            return self._generate_camel_case_name()
        
        self.used_names.add(name)
        return name
    
    def analyze_code(self, code: str) -> Dict[str, List[str]]:
        """分析代码并提取变量、函数和类名"""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"语法错误: {e}")
        
        # 第一步：分析导入语句
        import_analyzer = ImportAnalyzer()
        import_analyzer.visit(tree)
        
        # 第二步：分析代码中的标识符
        code_analyzer = CodeAnalyzer(import_analyzer.imported_names, import_analyzer.import_attributes)
        code_analyzer.visit(tree)
        
        # 保存导入信息
        self.imported_modules = import_analyzer.imported_modules
        self.imported_names = import_analyzer.imported_names
        self.import_aliases = import_analyzer.aliases
        self.imported_functions = import_analyzer.imported_functions
        self.imported_classes = import_analyzer.imported_classes
        self.imported_variables = import_analyzer.imported_variables
        self.import_attributes = import_analyzer.import_attributes  # 新增：保存属性
        
        # 将导入的名称和属性添加到排除列表
        self.exclude_list.update(import_analyzer.imported_names)
        self.exclude_list.update(import_analyzer.import_attributes)  # 新增：添加属性到排除列表
        
        # 移除Python关键字和内置函数
        keywords = set(ast.keyword.__doc__.split() if ast.keyword.__doc__ else [])
        builtins = set(__builtins__.keys() if hasattr(__builtins__, 'keys') else dir(__builtins__))
        
        variables = code_analyzer.variables - keywords - builtins
        functions = code_analyzer.functions - keywords - builtins
        classes = code_analyzer.classes - keywords - builtins
        
        return {
            "variables": sorted(list(variables)),
            "functions": sorted(list(functions)),
            "classes": sorted(list(classes)),
            "imports": sorted(list(import_analyzer.imports)),
            "imported_names": sorted(list(import_analyzer.imported_names)),
            "imported_modules": sorted(list(import_analyzer.imported_modules)),
            "imported_functions": sorted(list(import_analyzer.imported_functions)),
            "imported_classes": sorted(list(import_analyzer.imported_classes)),
            "imported_variables": sorted(list(import_analyzer.imported_variables)),
            "import_attributes": sorted(list(import_analyzer.import_attributes))  # 新增：属性
        }
    
    def add_anti_debug_code(self, code: str) -> str:
        """添加反调试代码"""
        anti_debug_code = """# 反调试保护
import sys
def _anti_debug():
    if hasattr(sys, 'gettrace') and sys.gettrace() is not None:
        print("Debugger detected! Exiting...")
        sys.exit(1)
    try:
        import ptrace
        print("Ptrace detected! Exiting...")
        sys.exit(1)
    except ImportError:
        pass

_anti_debug()
del _anti_debug
"""
        # 在代码开头插入反调试代码
        lines = code.split('\n')
        # 查找第一个非空行和非注释行
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('#'):
                insert_pos = i
                break
        
        lines.insert(insert_pos, anti_debug_code)
        return '\n'.join(lines)
    
    def insert_dummy_code(self, code: str) -> str:
        """插入虚拟代码增加混淆"""
        if not self.insert_dummy_code:
            return code
        
        dummy_functions = [
            """
def _dummy_func_1():
    x = 1
    y = 2
    return x + y
""",
            """
def _dummy_func_2(a, b):
    if a > b:
        return a - b
    else:
        return b - a
""",
            """
class _DummyClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
"""
        ]
        
        # 在代码中随机位置插入虚拟代码
        lines = code.split('\n')
        if len(lines) > 10:
            insert_pos = random.randint(5, len(lines) - 5)
            dummy_code = random.choice(dummy_functions)
            lines.insert(insert_pos, dummy_code)
            return '\n'.join(lines)
        
        return code
    
    def obfuscate_control_flow(self, code: str) -> str:
        """混淆控制流"""
        if self.obfuscation_level >= 3 and self.control_flow_obfuscation:
            try:
                # 使用 marshal 将代码编译为字节码，然后进行 base64 编码
                compiled_code = compile(code, '<string>', 'exec')
                marshaled_code = marshal.dumps(compiled_code)
                encoded_code = base64.b64encode(marshaled_code).decode()
                
                obfuscated_code = f"""
import base64, marshal
exec(marshal.loads(base64.b64decode({encoded_code!r})))
"""
                return obfuscated_code
            except Exception as e:
                print(f"控制流混淆失败: {e}")
                return code
        return code
    
    def _compress_code(self, code: str) -> str:
        """压缩代码 - 内部方法，避免与属性名冲突"""
        code = re.sub(r'#.*', '', code)
        code = re.sub(r'\s+', ' ', code)
        code = re.sub(r'^\s+|\s+$', '', code, flags=re.MULTILINE)
        return code
    
    def encrypt_strings_in_code(self, code: str) -> str:
        """加密代码中的字符串"""
        if not self.encrypt_strings:
            return code
        
        # 查找所有字符串
        string_pattern = r'("([^"\\]*(\\.[^"\\]*)*)"|\'([^\'\\]*(\\.[^\'\\]*)*)\')'
        
        def replace_string(match):
            s = match.group(0)
            # 排除空字符串和非常短的字符串
            if len(s) <= 4:
                return s
            # 排除可能包含格式化的字符串（如f-string）
            if s.startswith('f'):
                return s
            # 排除文档字符串
            if s.startswith('"""') or s.startswith("'''"):
                return s
            # 排除导入语句中的字符串
            if any(imp in s for imp in self.imported_modules):
                return s
            return self.encrypt_string(s[1:-1])
        
        return re.sub(string_pattern, replace_string, code)
    
    def obfuscate_code(self, code: str) -> str:
        """混淆代码"""
        try:
            # 重置映射和已使用名称
            self.var_mapping = {}
            self.func_mapping = {}
            self.class_mapping = {}
            self.used_names = set()
            
            identifiers = self.analyze_code(code)
            
            # 创建映射
            for var in identifiers["variables"]:
                if var not in self.var_mapping:
                    self.var_mapping[var] = self.generate_name(var, "var")
            
            for func in identifiers["functions"]:
                if func not in self.func_mapping:
                    self.func_mapping[func] = self.generate_name(func, "func")
            
            for cls in identifiers["classes"]:
                if cls not in self.class_mapping:
                    self.class_mapping[cls] = self.generate_name(cls, "class")
            
            # 替换代码中的标识符
            obfuscated_code = code
            
            # 按照长度降序排序，避免部分匹配问题
            all_mappings = {**self.var_mapping, **self.func_mapping, **self.class_mapping}
            sorted_items = sorted(all_mappings.items(), key=lambda x: len(x[0]), reverse=True)
            
            for original, obfuscated in sorted_items:
                # 使用正则表达式确保只替换完整的单词
                pattern = r'\b' + re.escape(original) + r'\b'
                obfuscated_code = re.sub(pattern, obfuscated, obfuscated_code)
            
            # 加密字符串
            obfuscated_code = self.encrypt_strings_in_code(obfuscated_code)
            
            # 添加反调试代码
            if self.anti_debug:
                obfuscated_code = self.add_anti_debug_code(obfuscated_code)
            
            # 插入虚拟代码
            if self.insert_dummy_code:
                obfuscated_code = self.insert_dummy_code(obfuscated_code)
            
            # 混淆控制流
            if self.control_flow_obfuscation:
                obfuscated_code = self.obfuscate_control_flow(obfuscated_code)
            
            # 压缩代码
            if self.compress_code:
                obfuscated_code = self._compress_code(obfuscated_code)
            
            return obfuscated_code
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            raise ValueError(f"代码混淆失败: {e}\n详细信息: {error_details}")


class ObfuscationWorker(QThread):
    """混淆工作线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, engine: AdvancedObfuscationEngine, code: str):
        super().__init__()
        self.engine = engine
        self.code = code
    
    def run(self):
        try:
            result = self.engine.obfuscate_code(self.code)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class CodeObfuscationTool(QMainWindow):
    """代码混淆工具主窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.obfuscator = AdvancedObfuscationEngine()
        self.current_file = None
    
    def init_ui(self):
        self.setWindowTitle("高级Python代码混淆工具")
        self.setGeometry(100, 100, 1400, 900)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("加载文件")
        self.load_btn.clicked.connect(self.load_file)
        
        self.save_btn = QPushButton("保存结果")
        self.save_btn.clicked.connect(self.save_result)
        
        self.analyze_btn = QPushButton("分析代码")
        self.analyze_btn.clicked.connect(self.analyze_code)
        
        self.obfuscate_btn = QPushButton("混淆代码")
        self.obfuscate_btn.clicked.connect(self.obfuscate_code)
        
        self.batch_btn = QPushButton("批量处理")
        self.batch_btn.clicked.connect(self.batch_process)
        
        control_layout.addWidget(self.load_btn)
        control_layout.addWidget(self.save_btn)
        control_layout.addWidget(self.analyze_btn)
        control_layout.addWidget(self.obfuscate_btn)
        control_layout.addWidget(self.batch_btn)
        control_layout.addStretch()
        
        main_layout.addLayout(control_layout)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 代码编辑选项卡
        code_tab = QWidget()
        code_layout = QVBoxLayout(code_tab)
        
        # 分割器用于代码编辑器
        splitter = QSplitter(Qt.Horizontal)
        
        # 原始代码编辑器
        self.original_edit = QTextEdit()
        self.original_edit.setPlaceholderText("在此输入或粘贴Python代码...")
        self.original_highlighter = PythonHighlighter(self.original_edit.document())
        
        # 混淆后代码编辑器
        self.obfuscated_edit = QTextEdit()
        self.obfuscated_edit.setPlaceholderText("混淆后的代码将显示在这里...")
        self.obfuscated_highlighter = PythonHighlighter(self.obfuscated_edit.document())
        
        splitter.addWidget(self.original_edit)
        splitter.addWidget(self.obfuscated_edit)
        splitter.setSizes([700, 700])
        
        code_layout.addWidget(splitter)
        
        # 设置选项卡
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        
        # 加密设置组
        encryption_group = QGroupBox("加密设置")
        encryption_layout = QVBoxLayout(encryption_group)
        
        encryption_method_layout = QHBoxLayout()
        encryption_method_layout.addWidget(QLabel("加密方法:"))
        self.encryption_combo = QComboBox()
        self.encryption_combo.addItems(["random", "hash", "base64", "leet"])
        self.encryption_combo.setCurrentText("random")
        encryption_method_layout.addWidget(self.encryption_combo)
        encryption_method_layout.addStretch()
        
        encryption_level_layout = QHBoxLayout()
        encryption_level_layout.addWidget(QLabel("混淆级别:"))
        self.obfuscation_level = QSpinBox()
        self.obfuscation_level.setRange(1, 3)
        self.obfuscation_level.setValue(1)
        encryption_level_layout.addWidget(self.obfuscation_level)
        encryption_level_layout.addStretch()
        
        encryption_layout.addLayout(encryption_method_layout)
        encryption_layout.addLayout(encryption_level_layout)
        
        # 功能设置组
        features_group = QGroupBox("功能设置")
        features_layout = QVBoxLayout(features_group)
        
        self.encrypt_strings_cb = QCheckBox("加密字符串")
        self.compress_code_cb = QCheckBox("压缩代码")
        self.anti_debug_cb = QCheckBox("添加反调试保护")
        self.control_flow_cb = QCheckBox("混淆控制流")
        self.insert_dummy_cb = QCheckBox("插入虚拟代码")
        self.rename_params_cb = QCheckBox("重命名参数")
        self.rename_params_cb.setChecked(True)
        
        features_layout.addWidget(self.encrypt_strings_cb)
        features_layout.addWidget(self.compress_code_cb)
        features_layout.addWidget(self.anti_debug_cb)
        features_layout.addWidget(self.control_flow_cb)
        features_layout.addWidget(self.insert_dummy_cb)
        features_layout.addWidget(self.rename_params_cb)
        
        # 排除设置组
        exclude_group = QGroupBox("排除设置")
        exclude_layout = QVBoxLayout(exclude_group)
        
        self.exclude_edit = QTextEdit()
        self.exclude_edit.setPlaceholderText("每行输入一个要排除的标识符名称")
        exclude_layout.addWidget(self.exclude_edit)
        
        # 自定义密钥组
        key_group = QGroupBox("自定义加密密钥")
        key_layout = QVBoxLayout(key_group)
        
        key_input_layout = QHBoxLayout()
        key_input_layout.addWidget(QLabel("密钥:"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("输入自定义加密密钥（可选）")
        key_input_layout.addWidget(self.key_edit)
        
        key_btn_layout = QHBoxLayout()
        self.set_key_btn = QPushButton("设置密钥")
        self.set_key_btn.clicked.connect(self.set_encryption_key)
        key_btn_layout.addWidget(self.set_key_btn)
        
        key_layout.addLayout(key_input_layout)
        key_layout.addLayout(key_btn_layout)
        
        settings_layout.addWidget(encryption_group)
        settings_layout.addWidget(features_group)
        settings_layout.addWidget(exclude_group)
        settings_layout.addWidget(key_group)
        settings_layout.addStretch()
        
        # 分析结果选项卡
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        
        self.analysis_tree = QTreeWidget()
        self.analysis_tree.setHeaderLabels(["类型", "名称", "新名称"])
        self.analysis_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        analysis_layout.addWidget(self.analysis_tree)
        
        # 添加选项卡
        self.tabs.addTab(code_tab, "代码编辑")
        self.tabs.addTab(settings_tab, "设置")
        self.tabs.addTab(analysis_tab, "分析结果")
        
        main_layout.addWidget(self.tabs)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 连接信号
        self.encryption_combo.currentTextChanged.connect(self.update_settings)
        self.obfuscation_level.valueChanged.connect(self.update_settings)
        self.encrypt_strings_cb.stateChanged.connect(self.update_settings)
        self.compress_code_cb.stateChanged.connect(self.update_settings)
        self.anti_debug_cb.stateChanged.connect(self.update_settings)
        self.control_flow_cb.stateChanged.connect(self.update_settings)
        self.insert_dummy_cb.stateChanged.connect(self.update_settings)
        self.rename_params_cb.stateChanged.connect(self.update_settings)
    
    def set_encryption_key(self):
        """设置自定义加密密钥"""
        key = self.key_edit.text()
        if key:
            try:
                self.obfuscator.set_encryption_key(key)
                self.statusBar().showMessage("已设置自定义加密密钥")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"设置密钥失败: {str(e)}")
        else:
            self.obfuscator.generate_encryption_key()
            self.statusBar().showMessage("已使用默认加密密钥")
    
    def update_settings(self):
        """更新混淆器设置"""
        self.obfuscator.encryption_method = self.encryption_combo.currentText()
        self.obfuscator.obfuscation_level = self.obfuscation_level.value()
        self.obfuscator.encrypt_strings = self.encrypt_strings_cb.isChecked()
        self.obfuscator.compress_code = self.compress_code_cb.isChecked()
        self.obfuscator.anti_debug = self.anti_debug_cb.isChecked()
        self.obfuscator.control_flow_obfuscation = self.control_flow_cb.isChecked()
        self.obfuscator.insert_dummy_code = self.insert_dummy_cb.isChecked()
        self.obfuscator.rename_parameters = self.rename_params_cb.isChecked()
        
        # 更新排除列表
        exclude_text = self.exclude_edit.toPlainText()
        self.obfuscator.exclude_list = set(filter(None, exclude_text.split()))
    
    def load_file(self):
        """加载Python文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开Python文件", "", "Python文件 (*.py);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                self.original_edit.setPlainText(code)
                self.current_file = file_path
                self.statusBar().showMessage(f"已加载: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法读取文件: {str(e)}")
    
    def save_result(self):
        """保存混淆后的代码"""
        code = self.obfuscated_edit.toPlainText()
        if not code.strip():
            QMessageBox.warning(self, "警告", "没有内容可保存")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存混淆后的代码", "", "Python文件 (*.py);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                self.statusBar().showMessage(f"已保存: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存文件: {str(e)}")
    
    def analyze_code(self):
        """分析代码并显示标识符"""
        code = self.original_edit.toPlainText()
        if not code.strip():
            QMessageBox.warning(self, "警告", "请输入一些代码进行分析")
            return
        
        try:
            self.update_settings()
            identifiers = self.obfuscator.analyze_code(code)
            
            # 清空分析树
            self.analysis_tree.clear()
            
            # 添加变量
            var_item = QTreeWidgetItem(self.analysis_tree, ["变量", f"{len(identifiers['variables'])} 个", ""])
            for var in identifiers["variables"]:
                QTreeWidgetItem(var_item, ["变量", var, ""])
            
            # 添加函数
            func_item = QTreeWidgetItem(self.analysis_tree, ["函数", f"{len(identifiers['functions'])} 个", ""])
            for func in identifiers["functions"]:
                QTreeWidgetItem(func_item, ["函数", func, ""])
            
            # 添加类
            class_item = QTreeWidgetItem(self.analysis_tree, ["类", f"{len(identifiers['classes'])} 个", ""])
            for cls in identifiers["classes"]:
                QTreeWidgetItem(class_item, ["类", cls, ""])
            
            # 添加导入
            import_item = QTreeWidgetItem(self.analysis_tree, ["导入", f"{len(identifiers['imports'])} 个", "(已排除)"])
            for imp in identifiers["imports"]:
                QTreeWidgetItem(import_item, ["导入", imp, "(已排除)"])
            
            # 添加导入的名称
            imported_names_item = QTreeWidgetItem(self.analysis_tree, ["导入的名称", f"{len(identifiers['imported_names'])} 个", "(已排除)"])
            for name in identifiers["imported_names"]:
                QTreeWidgetItem(imported_names_item, ["导入的名称", name, "(已排除)"])
            
            # 添加导入的模块
            imported_modules_item = QTreeWidgetItem(self.analysis_tree, ["导入的模块", f"{len(identifiers['imported_modules'])} 个", "(已排除)"])
            for module in identifiers["imported_modules"]:
                QTreeWidgetItem(imported_modules_item, ["导入的模块", module, "(已排除)"])
            
            # 添加导入的函数
            imported_funcs_item = QTreeWidgetItem(self.analysis_tree, ["导入的函数", f"{len(identifiers['imported_functions'])} 个", "(已排除)"])
            for func in identifiers["imported_functions"]:
                QTreeWidgetItem(imported_funcs_item, ["导入的函数", func, "(已排除)"])
            
            # 添加导入的类
            imported_classes_item = QTreeWidgetItem(self.analysis_tree, ["导入的类", f"{len(identifiers['imported_classes'])} 个", "(已排除)"])
            for cls in identifiers["imported_classes"]:
                QTreeWidgetItem(imported_classes_item, ["导入的类", cls, "(已排除)"])
            
            # 添加导入的变量
            imported_vars_item = QTreeWidgetItem(self.analysis_tree, ["导入的变量", f"{len(identifiers['imported_variables'])} 个", "(已排除)"])
            for var in identifiers["imported_variables"]:
                QTreeWidgetItem(imported_vars_item, ["导入的变量", var, "(已排除)"])
            
            # 添加导入的属性
            imported_attrs_item = QTreeWidgetItem(self.analysis_tree, ["导入的属性", f"{len(identifiers['import_attributes'])} 个", "(已排除)"])
            for attr in identifiers["import_attributes"]:
                QTreeWidgetItem(imported_attrs_item, ["导入的属性", attr, "(已排除)"])
            
            # 展开所有项
            self.analysis_tree.expandAll()
            
            message = (f"找到 {len(identifiers['variables'])} 个变量, "
                      f"{len(identifiers['functions'])} 个函数, "
                      f"{len(identifiers['classes'])} 个类, "
                      f"{len(identifiers['imports'])} 个导入, "
                      f"{len(identifiers['imported_names'])} 个导入的名称, "
                      f"{len(identifiers['imported_modules'])} 个导入的模块, "
                      f"{len(identifiers['imported_functions'])} 个导入的函数, "
                      f"{len(identifiers['imported_classes'])} 个导入的类, "
                      f"{len(identifiers['imported_variables'])} 个导入的变量, "
                      f"{len(identifiers['import_attributes'])} 个导入的属性")
            self.statusBar().showMessage(message)
            
        except ValueError as e:
            QMessageBox.critical(self, "错误", str(e))
    
    def obfuscate_code(self):
        """混淆代码"""
        code = self.original_edit.toPlainText()
        if not code.strip():
            QMessageBox.warning(self, "警告", "请输入一些代码进行混淆")
            return
        
        # 更新混淆器设置
        self.update_settings()
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        
        # 创建工作线程
        self.worker = ObfuscationWorker(self.obfuscator, code)
        self.worker.finished.connect(self.on_obfuscation_finished)
        self.worker.error.connect(self.on_obfuscation_error)
        self.worker.start()
    
    def on_obfuscation_finished(self, result):
        """混淆完成处理"""
        self.obfuscated_edit.setPlainText(result)
        self.progress_bar.setVisible(False)
        
        # 更新分析树中的新名称
        self.update_analysis_tree()
        
        # 显示映射信息
        mapping_info = f"混淆完成。{len(self.obfuscator.var_mapping)} 个变量被替换"
        if self.obfuscator.encrypt_strings:
            mapping_info += "，字符串已加密"
        if self.obfuscator.anti_debug:
            mapping_info += "，添加了反调试保护"
        if self.obfuscator.control_flow_obfuscation:
            mapping_info += "，控制流已混淆"
        if self.obfuscator.insert_dummy_code:
            mapping_info += "，插入了虚拟代码"
        
        self.statusBar().showMessage(mapping_info)
    
    def update_analysis_tree(self):
        """更新分析树中的新名称"""
        root = self.analysis_tree.invisibleRootItem()
        for i in range(root.childCount()):
            category_item = root.child(i)
            category_type = category_item.text(0)
            
            for j in range(category_item.childCount()):
                item = category_item.child(j)
                original_name = item.text(1)
                
                if category_type == "变量" and original_name in self.obfuscator.var_mapping:
                    item.setText(2, self.obfuscator.var_mapping[original_name])
                elif category_type == "函数" and original_name in self.obfuscator.func_mapping:
                    item.setText(2, self.obfuscator.func_mapping[original_name])
                elif category_type == "类" and original_name in self.obfuscator.class_mapping:
                    item.setText(2, self.obfuscator.class_mapping[original_name])
    
    def on_obfuscation_error(self, error_msg):
        """混淆错误处理"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "错误", f"混淆过程中发生错误: {error_msg}")
    
    def batch_process(self):
        """批量处理多个文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要混淆的Python文件", "", "Python文件 (*.py);;所有文件 (*)"
        )
        
        if not files:
            return
        
        output_dir = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if not output_dir:
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(files))
        
        # 批量处理文件
        success_count = 0
        for i, file_path in enumerate(files):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # 重置混淆器状态
                self.obfuscator.var_mapping = {}
                self.obfuscator.func_mapping = {}
                self.obfuscator.class_mapping = {}
                self.obfuscator.used_names = set()
                
                # 混淆代码
                obfuscated_code = self.obfuscator.obfuscate_code(code)
                
                # 保存结果
                file_name = os.path.basename(file_path)
                output_path = os.path.join(output_dir, f"obfuscated_{file_name}")
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(obfuscated_code)
                
                success_count += 1
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {e}")
            
            self.progress_bar.setValue(i + 1)
        
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "完成", f"批量处理完成。成功处理 {success_count}/{len(files)} 个文件。")


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = CodeObfuscationTool()
    window.show()
    sys.exit(app.exec_())