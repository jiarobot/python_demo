import json
import socket
import threading
import sys
import uuid
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlparse

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, QDateTime, QByteArray
from PyQt5.QtNetwork import QTcpServer, QTcpSocket, QNetworkAccessManager, QNetworkRequest, QHostAddress
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QVBoxLayout, 
                             QWidget, QPushButton, QHBoxLayout, QLineEdit, QLabel, 
                             QSplitter, QListWidget, QMessageBox)
from PyQt5.QtWebSockets import QWebSocket, QWebSocketServer
from PyQt5.Qt import QUrl


class CrossDomainLogger:
    """跨域日志记录器"""
    
    def __init__(self, name: str = "CrossDomain"):
        self.name = name
        self.handlers = []
    
    def add_handler(self, handler: Callable):
        """添加日志处理器"""
        self.handlers.append(handler)
    
    def log(self, level: str, message: str, data: Any = None):
        """记录日志"""
        log_entry = {
            "timestamp": QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss.zzz"),
            "level": level,
            "name": self.name,
            "message": message,
            "data": data
        }
        
        for handler in self.handlers:
            handler(log_entry)
        
        return log_entry


class CrossDomainMessage:
    """跨域消息封装类"""
    
    def __init__(self, message_type: str, payload: Any = None, source: str = None, 
                 destination: str = None, message_id: str = None):
        self.type = message_type
        self.payload = payload or {}
        self.source = source
        self.destination = destination
        self.id = message_id or str(uuid.uuid4())
        self.timestamp = QDateTime.currentDateTime()
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps({
            "type": self.type,
            "payload": self.payload,
            "source": self.source,
            "destination": self.destination,
            "id": self.id,
            "timestamp": self.timestamp.toString("yyyy-MM-dd hh:mm:ss.zzz")
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CrossDomainMessage':
        """从JSON字符串创建消息"""
        data = json.loads(json_str)
        message = cls(
            data.get("type"),
            data.get("payload"),
            data.get("source"),
            data.get("destination"),
            data.get("id")
        )
        # 保留原始时间戳
        if "timestamp" in data:
            message.timestamp = QDateTime.fromString(data["timestamp"], "yyyy-MM-dd hh:mm:ss.zzz")
        return message


class CrossDomainConnection(QObject):
    """跨域连接基类"""
    
    message_received = pyqtSignal(CrossDomainMessage)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, connection_id: str, parent=None):
        super().__init__(parent)
        self.connection_id = connection_id
        self.is_connected = False
        self.logger = CrossDomainLogger(f"Connection_{connection_id}")
    
    def send_message(self, message: CrossDomainMessage) -> bool:
        """发送消息（需子类实现）"""
        raise NotImplementedError("子类必须实现send_message方法")
    
    def close(self):
        """关闭连接（需子类实现）"""
        raise NotImplementedError("子类必须实现close方法")


class WebSocketConnection(CrossDomainConnection):
    """WebSocket跨域连接"""
    
    def __init__(self, socket: QWebSocket, parent=None):
        peer_address = socket.peerAddress().toString()
        peer_port = socket.peerPort()
        connection_id = f"ws_{peer_address}_{peer_port}"
        super().__init__(connection_id, parent)
        self.socket = socket
        self.socket.textMessageReceived.connect(self._on_text_message_received)
        self.socket.connected.connect(self._on_connected)
        self.socket.disconnected.connect(self._on_disconnected)
        self.socket.error.connect(self._on_error)
        
        if self.socket.state() == QWebSocket.ConnectedState:
            self._on_connected()
    
    def _on_text_message_received(self, message: str):
        """处理接收到的文本消息"""
        try:
            cross_domain_msg = CrossDomainMessage.from_json(message)
            self.message_received.emit(cross_domain_msg)
        except json.JSONDecodeError as e:
            self.error_occurred.emit(f"JSON解析错误: {str(e)}")
    
    def _on_connected(self):
        """处理连接建立事件"""
        self.is_connected = True
        self.connected.emit()
        self.logger.log("INFO", "WebSocket连接已建立")
    
    def _on_disconnected(self):
        """处理连接断开事件"""
        self.is_connected = False
        self.disconnected.emit()
        self.logger.log("INFO", "WebSocket连接已断开")
    
    def _on_error(self, error_code):
        """处理错误事件"""
        error_msg = f"WebSocket错误: {self.socket.errorString()}"
        self.error_occurred.emit(error_msg)
        self.logger.log("ERROR", error_msg)
    
    def send_message(self, message: CrossDomainMessage) -> bool:
        """发送消息"""
        if self.is_connected:
            self.socket.sendTextMessage(message.to_json())
            return True
        return False
    
    def close(self):
        """关闭连接"""
        self.socket.close()


class WebSocketClientConnection(CrossDomainConnection):
    """WebSocket客户端连接"""
    
    def __init__(self, url: str, parent=None):
        super().__init__(f"ws_client_{url}", parent)
        self.url = url
        self.socket = QWebSocket()
        self.socket.textMessageReceived.connect(self._on_text_message_received)
        self.socket.connected.connect(self._on_connected)
        self.socket.disconnected.connect(self._on_disconnected)
        self.socket.error.connect(self._on_error)
        
        # 开始连接
        self.socket.open(QUrl(url))
    
    def _on_text_message_received(self, message: str):
        """处理接收到的文本消息"""
        try:
            cross_domain_msg = CrossDomainMessage.from_json(message)
            self.message_received.emit(cross_domain_msg)
        except json.JSONDecodeError as e:
            self.error_occurred.emit(f"JSON解析错误: {str(e)}")
    
    def _on_connected(self):
        """处理连接建立事件"""
        self.is_connected = True
        self.connected.emit()
        self.logger.log("INFO", f"WebSocket连接已建立: {self.url}")
    
    def _on_disconnected(self):
        """处理连接断开事件"""
        self.is_connected = False
        self.disconnected.emit()
        self.logger.log("INFO", f"WebSocket连接已断开: {self.url}")
    
    def _on_error(self, error_code):
        """处理错误事件"""
        error_msg = f"WebSocket错误: {self.socket.errorString()}"
        self.error_occurred.emit(error_msg)
        self.logger.log("ERROR", error_msg)
    
    def send_message(self, message: CrossDomainMessage) -> bool:
        """发送消息"""
        if self.is_connected:
            self.socket.sendTextMessage(message.to_json())
            return True
        return False
    
    def close(self):
        """关闭连接"""
        self.socket.close()


class HttpConnection(CrossDomainConnection):
    """HTTP跨域连接"""
    
    def __init__(self, target_url: str, parent=None):
        super().__init__(f"http_{target_url}", parent)
        self.target_url = target_url
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self._on_request_finished)
    
    def send_message(self, message: CrossDomainMessage) -> bool:
        """发送HTTP POST请求"""
        request = QNetworkRequest(QUrl(self.target_url))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        
        data = message.to_json().encode('utf-8')
        self.network_manager.post(request, data)
        return True
    
    def _on_request_finished(self, reply):
        """处理请求完成"""
        if reply.error():
            self.error_occurred.emit(f"HTTP请求错误: {reply.errorString()}")
        else:
            try:
                response_data = reply.readAll().data().decode('utf-8')
                response_msg = CrossDomainMessage.from_json(response_data)
                self.message_received.emit(response_msg)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                self.error_occurred.emit(f"响应解析错误: {str(e)}")
    
    def close(self):
        """HTTP连接不需要显式关闭"""
        pass


class CrossDomainHub(QObject):
    """跨域通信中心枢纽"""
    
    connected = pyqtSignal(str)  # 参数为连接ID
    disconnected = pyqtSignal(str)  # 参数为连接ID
    message_received = pyqtSignal(CrossDomainMessage)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connections = {}  # 连接ID到连接的映射
        self.message_handlers = {}  # 消息类型到处理函数的映射
        self.websocket_server = None
        self.logger = CrossDomainLogger("CrossDomainHub")
        
        # 注册默认消息处理器
        self.register_message_handler("ping", self._handle_ping)
        self.register_message_handler("rpc_request", self._handle_rpc_request)
        self.register_message_handler("echo", self._handle_echo)
    
    def _on_websocket_client_connected(self):
        """处理新的WebSocket客户端连接"""
        socket = self.websocket_server.nextPendingConnection()
        if socket:
            connection = WebSocketConnection(socket, self)
            connection_id = connection.connection_id
            
            self.connections[connection_id] = connection
            connection.message_received.connect(self._route_message)
            connection.connected.connect(lambda: self.connected.emit(connection_id))
            connection.disconnected.connect(lambda: self._remove_connection(connection_id))
            connection.error_occurred.connect(self.error_occurred.emit)
            
            self.logger.log("INFO", f"新的WebSocket客户端连接: {connection_id}")
    
    def create_websocket_connection(self, url: str) -> Optional[WebSocketClientConnection]:
        """创建WebSocket客户端连接"""
        try:
            connection = WebSocketClientConnection(url, self)
            connection_id = connection.connection_id
            
            self.connections[connection_id] = connection
            connection.message_received.connect(self._route_message)
            connection.connected.connect(lambda: self.connected.emit(connection_id))
            connection.disconnected.connect(lambda: self._remove_connection(connection_id))
            connection.error_occurred.connect(self.error_occurred.emit)
            
            return connection
        except Exception as e:
            self.logger.log("ERROR", f"创建WebSocket连接失败: {str(e)}")
            return None
    
    def _remove_connection(self, connection_id: str):
        """移除连接"""
        if connection_id in self.connections:
            self.connections[connection_id].close()
            del self.connections[connection_id]
            self.disconnected.emit(connection_id)
            self.logger.log("INFO", f"连接已移除: {connection_id}")
    
    def start_websocket_server(self, port: int, host: str = "localhost") -> bool:
        """启动WebSocket服务器"""
        if self.websocket_server:
            self.websocket_server.close()
        
        self.websocket_server = QWebSocketServer("CrossDomain Server", QWebSocketServer.NonSecureMode, self)
        
        # 将主机地址转换为QHostAddress
        if host == "localhost":
            address = QHostAddress.LocalHost
        else:
            address = QHostAddress(host)
        
        if self.websocket_server.listen(address, port):
            self.websocket_server.newConnection.connect(self._on_websocket_client_connected)
            self.logger.log("INFO", f"WebSocket服务器已启动，监听 {host}:{port}")
            return True
        else:
            error_msg = f"无法启动WebSocket服务器: {self.websocket_server.errorString()}"
            self.logger.log("ERROR", error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def stop_websocket_server(self):
        """停止WebSocket服务器"""
        if self.websocket_server:
            self.websocket_server.close()
            self.websocket_server = None
            self.logger.log("INFO", "WebSocket服务器已停止")
    
    def create_http_connection(self, url: str) -> HttpConnection:
        """创建HTTP连接"""
        connection = HttpConnection(url, self)
        connection_id = connection.connection_id
        
        self.connections[connection_id] = connection
        connection.message_received.connect(self._route_message)
        connection.error_occurred.connect(self.error_occurred.emit)
        
        return connection
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """注册消息处理器"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        
        self.message_handlers[message_type].append(handler)
    
    def unregister_message_handler(self, message_type: str, handler: Callable):
        """取消注册消息处理器"""
        if message_type in self.message_handlers and handler in self.message_handlers[message_type]:
            self.message_handlers[message_type].remove(handler)
    
    def _route_message(self, message: CrossDomainMessage):
        """路由消息到相应的处理器"""
        # 首先发射通用消息接收信号
        self.message_received.emit(message)
        
        # 然后路由到特定类型的处理器
        if message.type in self.message_handlers:
            for handler in self.message_handlers[message.type]:
                try:
                    handler(message, self)
                except Exception as e:
                    self.logger.log("ERROR", f"消息处理错误: {str(e)}", {
                        "message_type": message.type,
                        "handler": handler.__name__
                    })
        else:
            self.logger.log("DEBUG", f"未注册的消息类型: {message.type}")
    
    def broadcast_message(self, message: CrossDomainMessage, exclude_connections: List[str] = None):
        """广播消息到所有连接"""
        exclude_connections = exclude_connections or []
        
        for connection_id, connection in self.connections.items():
            if connection_id not in exclude_connections and connection.is_connected:
                connection.send_message(message)
    
    def send_message_to(self, connection_id: str, message: CrossDomainMessage) -> bool:
        """发送消息到特定连接"""
        if connection_id in self.connections:
            return self.connections[connection_id].send_message(message)
        return False
    
    def _handle_ping(self, message: CrossDomainMessage, hub: 'CrossDomainHub'):
        """处理ping消息"""
        pong_message = CrossDomainMessage(
            "pong",
            {"original_timestamp": message.timestamp.toString("yyyy-MM-dd hh:mm:ss.zzz")},
            destination=message.source
        )
        self.send_message_to(message.source, pong_message)
    
    def _handle_echo(self, message: CrossDomainMessage, hub: 'CrossDomainHub'):
        """处理echo消息"""
        echo_message = CrossDomainMessage(
            "echo_response",
            {"original_message": message.payload},
            destination=message.source
        )
        self.send_message_to(message.source, echo_message)
    
    def _handle_rpc_request(self, message: CrossDomainMessage, hub: 'CrossDomainHub'):
        """处理RPC请求"""
        # 这里可以实现RPC调用逻辑
        method_name = message.payload.get("method")
        params = message.payload.get("params", {})
        
        # 在实际应用中，这里会调用相应的RPC方法
        response_payload = {
            "result": f"调用方法 {method_name} 成功，参数: {params}",
            "error": None,
            "id": message.payload.get("id")
        }
        
        response_message = CrossDomainMessage(
            "rpc_response",
            response_payload,
            destination=message.source
        )
        
        self.send_message_to(message.source, response_message)


class RemoteProcedureCall:
    """远程过程调用管理器"""
    
    def __init__(self, hub: CrossDomainHub):
        self.hub = hub
        self.next_call_id = 1
        self.pending_calls = {}  # 等待中的RPC调用
        self.registered_methods = {}  # 注册的RPC方法
        
        # 注册RPC消息处理器
        self.hub.register_message_handler("rpc_response", self._handle_rpc_response)
    
    def call(self, connection_id: str, method: str, params: Dict = None, timeout: int = 5000) -> Any:
        """执行远程过程调用"""
        call_id = self.next_call_id
        self.next_call_id += 1
        
        # 创建请求消息
        request_message = CrossDomainMessage(
            "rpc_request",
            {
                "method": method,
                "params": params or {},
                "id": call_id
            },
            destination=connection_id
        )
        
        # 创建等待事件和结果存储
        from threading import Event
        event = Event()
        result_container = {"result": None, "error": None}
        
        # 存储等待中的调用
        self.pending_calls[call_id] = {
            "event": event,
            "result": result_container,
            "timeout": timeout
        }
        
        # 发送请求
        if not self.hub.send_message_to(connection_id, request_message):
            del self.pending_calls[call_id]
            raise Exception(f"无法发送消息到连接: {connection_id}")
        
        # 等待响应或超时
        if not event.wait(timeout / 1000):  # 转换为秒
            del self.pending_calls[call_id]
            raise TimeoutError(f"RPC调用超时: {method}")
        
        # 检查错误
        if result_container["error"]:
            raise Exception(f"RPC调用错误: {result_container['error']}")
        
        return result_container["result"]
    
    def register_method(self, method_name: str, method_func: Callable):
        """注册RPC方法"""
        self.registered_methods[method_name] = method_func
    
    def _handle_rpc_response(self, message: CrossDomainMessage, hub: CrossDomainHub):
        """处理RPC响应"""
        call_id = message.payload.get("id")
        if call_id in self.pending_calls:
            pending_call = self.pending_calls[call_id]
            pending_call["result"]["result"] = message.payload.get("result")
            pending_call["result"]["error"] = message.payload.get("error")
            pending_call["event"].set()
            del self.pending_calls[call_id]


class DataSynchronizer:
    """数据同步管理器"""
    
    def __init__(self, hub: CrossDomainHub):
        self.hub = hub
        self.data_stores = {}  # 数据存储
        self.sync_handlers = {}  # 同步处理器
        
        # 注册数据同步消息处理器
        self.hub.register_message_handler("data_sync", self._handle_data_sync)
    
    def create_data_store(self, store_id: str, initial_data: Any = None):
        """创建数据存储"""
        self.data_stores[store_id] = initial_data or {}
        return store_id
    
    def register_sync_handler(self, store_id: str, handler: Callable):
        """注册数据同步处理器"""
        if store_id not in self.sync_handlers:
            self.sync_handlers[store_id] = []
        
        self.sync_handlers[store_id].append(handler)
    
    def sync_data(self, store_id: str, connection_id: str = None):
        """同步数据到指定连接或所有连接"""
        if store_id not in self.data_stores:
            raise ValueError(f"数据存储不存在: {store_id}")
        
        sync_message = CrossDomainMessage(
            "data_sync",
            {
                "store_id": store_id,
                "data": self.data_stores[store_id]
            }
        )
        
        if connection_id:
            self.hub.send_message_to(connection_id, sync_message)
        else:
            self.hub.broadcast_message(sync_message)
    
    def update_data(self, store_id: str, new_data: Any, sync: bool = True):
        """更新数据并可选是否同步"""
        if store_id not in self.data_stores:
            raise ValueError(f"数据存储不存在: {store_id}")
        
        self.data_stores[store_id] = new_data
        
        if sync:
            self.sync_data(store_id)
    
    def _handle_data_sync(self, message: CrossDomainMessage, hub: CrossDomainHub):
        """处理数据同步消息"""
        store_id = message.payload.get("store_id")
        data = message.payload.get("data")
        
        if store_id in self.data_stores:
            self.data_stores[store_id] = data
            
            # 调用注册的同步处理器
            if store_id in self.sync_handlers:
                for handler in self.sync_handlers[store_id]:
                    handler(data, message.source)


class CrossDomainToolkit:
    """跨域工具包主类"""
    
    def __init__(self):
        self.hub = CrossDomainHub()
        self.rpc = RemoteProcedureCall(self.hub)
        self.data_sync = DataSynchronizer(self.hub)
        self.logger = self.hub.logger
        
        # 添加控制台日志处理器
        def console_log_handler(log_entry):
            print(f"[{log_entry['level']}] {log_entry['timestamp']} {log_entry['name']}: {log_entry['message']}")
        
        self.logger.add_handler(console_log_handler)
    
    def start_server(self, port: int = 8080, host: str = "localhost") -> bool:
        """启动WebSocket服务器"""
        return self.hub.start_websocket_server(port, host)
    
    def stop_server(self):
        """停止WebSocket服务器"""
        self.hub.stop_websocket_server()
    
    def connect_to_server(self, url: str) -> Optional[WebSocketClientConnection]:
        """连接到WebSocket服务器"""
        return self.hub.create_websocket_connection(url)
    
    def create_http_client(self, url: str) -> HttpConnection:
        """创建HTTP客户端"""
        return self.hub.create_http_connection(url)
    
    def get_connections(self) -> List[str]:
        """获取所有连接ID"""
        return list(self.hub.connections.keys())


# 示例应用程序
class ExampleApp(QMainWindow):
    """示例应用程序"""
    
    def __init__(self):
        super().__init__()
        self.toolkit = CrossDomainToolkit()
        self.current_connection = None
        self.init_ui()
        self.setup_connections()
        
        # 注册示例RPC方法
        self.toolkit.rpc.register_method("greet", self.greet_method)
        self.toolkit.rpc.register_method("get_time", self.get_time_method)
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("跨域互联系统工具库示例")
        self.setGeometry(100, 100, 1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建分割器
        splitter = QSplitter()
        main_layout.addWidget(splitter)
        
        # 左侧面板 - 连接管理
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        
        # 服务器控制
        server_group = QWidget()
        server_layout = QVBoxLayout()
        server_group.setLayout(server_layout)
        
        server_layout.addWidget(QLabel("服务器控制:"))
        
        self.host_input = QLineEdit("localhost")
        server_layout.addWidget(QLabel("主机:"))
        server_layout.addWidget(self.host_input)
        
        self.port_input = QLineEdit("8080")
        server_layout.addWidget(QLabel("端口:"))
        server_layout.addWidget(self.port_input)
        
        self.start_server_btn = QPushButton("启动服务器")
        server_layout.addWidget(self.start_server_btn)
        
        self.stop_server_btn = QPushButton("停止服务器")
        server_layout.addWidget(self.stop_server_btn)
        
        left_layout.addWidget(server_group)
        
        # 客户端控制
        client_group = QWidget()
        client_layout = QVBoxLayout()
        client_group.setLayout(client_layout)
        
        client_layout.addWidget(QLabel("客户端控制:"))
        
        self.url_input = QLineEdit("ws://localhost:8080")
        client_layout.addWidget(QLabel("连接URL:"))
        client_layout.addWidget(self.url_input)
        
        self.connect_btn = QPushButton("连接到服务器")
        client_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("断开连接")
        client_layout.addWidget(self.disconnect_btn)
        
        left_layout.addWidget(client_group)
        
        # 连接列表
        self.connections_list = QListWidget()
        left_layout.addWidget(QLabel("活动连接:"))
        left_layout.addWidget(self.connections_list)
        
        # 消息发送
        message_group = QWidget()
        message_layout = QVBoxLayout()
        message_group.setLayout(message_layout)
        
        message_layout.addWidget(QLabel("发送消息:"))
        
        self.message_type_input = QLineEdit("test")
        message_layout.addWidget(QLabel("消息类型:"))
        message_layout.addWidget(self.message_type_input)
        
        self.message_content_input = QTextEdit()
        self.message_content_input.setMaximumHeight(100)
        message_layout.addWidget(QLabel("消息内容 (JSON):"))
        message_layout.addWidget(self.message_content_input)
        
        self.send_msg_btn = QPushButton("发送消息")
        message_layout.addWidget(self.send_msg_btn)
        
        self.broadcast_msg_btn = QPushButton("广播消息")
        message_layout.addWidget(self.broadcast_msg_btn)
        
        left_layout.addWidget(message_group)
        
        # RPC调用
        rpc_group = QWidget()
        rpc_layout = QVBoxLayout()
        rpc_group.setLayout(rpc_layout)
        
        rpc_layout.addWidget(QLabel("RPC调用:"))
        
        self.rpc_method_input = QLineEdit("greet")
        rpc_layout.addWidget(QLabel("方法名:"))
        rpc_layout.addWidget(self.rpc_method_input)
        
        self.rpc_params_input = QTextEdit()
        self.rpc_params_input.setMaximumHeight(60)
        rpc_layout.addWidget(QLabel("参数 (JSON):"))
        rpc_layout.addWidget(self.rpc_params_input)
        
        self.rpc_call_btn = QPushButton("执行RPC调用")
        rpc_layout.addWidget(self.rpc_call_btn)
        
        left_layout.addWidget(rpc_group)
        
        # 右侧面板 - 日志
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        right_layout.addWidget(QLabel("日志输出:"))
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        right_layout.addWidget(self.log_text)
        
        # 设置分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 600])
    
    def setup_connections(self):
        """设置信号槽连接"""
        self.start_server_btn.clicked.connect(self.on_start_server)
        self.stop_server_btn.clicked.connect(self.on_stop_server)
        self.connect_btn.clicked.connect(self.on_connect)
        self.disconnect_btn.clicked.connect(self.on_disconnect)
        self.send_msg_btn.clicked.connect(self.on_send_message)
        self.broadcast_msg_btn.clicked.connect(self.on_broadcast_message)
        self.rpc_call_btn.clicked.connect(self.on_rpc_call)
        self.connections_list.itemSelectionChanged.connect(self.on_connection_selected)
        
        # 连接工具包信号
        self.toolkit.hub.connected.connect(self.on_client_connected)
        self.toolkit.hub.disconnected.connect(self.on_client_disconnected)
        self.toolkit.hub.message_received.connect(self.on_message_received)
        self.toolkit.hub.error_occurred.connect(self.on_error_occurred)
    
    def log(self, message: str):
        """记录日志到界面"""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss.zzz")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def update_connections_list(self):
        """更新连接列表"""
        self.connections_list.clear()
        for connection_id in self.toolkit.get_connections():
            self.connections_list.addItem(connection_id)
    
    def on_start_server(self):
        """处理启动服务器按钮点击"""
        host = self.host_input.text() or "localhost"
        try:
            port = int(self.port_input.text())
        except ValueError:
            self.log("端口号必须是整数")
            return
        
        if self.toolkit.start_server(port, host):
            self.log(f"服务器已启动在 {host}:{port}")
        else:
            self.log("服务器启动失败")
    
    def on_stop_server(self):
        """处理停止服务器按钮点击"""
        self.toolkit.stop_server()
        self.log("服务器已停止")
    
    def on_connect(self):
        """处理连接按钮点击"""
        url = self.url_input.text()
        if not url:
            self.log("请输入有效的URL")
            return
        
        connection = self.toolkit.connect_to_server(url)
        if connection:
            self.log(f"正在连接到 {url}")
        else:
            self.log("连接创建失败")
    
    def on_disconnect(self):
        """处理断开连接按钮点击"""
        if self.current_connection:
            self.toolkit.hub._remove_connection(self.current_connection)
            self.current_connection = None
            self.log("已断开当前连接")
        else:
            self.log("没有选中的连接")
    
    def on_connection_selected(self):
        """处理连接选择变化"""
        selected_items = self.connections_list.selectedItems()
        if selected_items:
            self.current_connection = selected_items[0].text()
            self.log(f"已选择连接: {self.current_connection}")
        else:
            self.current_connection = None
    
    def on_send_message(self):
        """处理发送消息按钮点击"""
        if not self.current_connection:
            self.log("请先选择一个连接")
            return
        
        message_type = self.message_type_input.text()
        if not message_type:
            self.log("请输入消息类型")
            return
        
        try:
            content_text = self.message_content_input.toPlainText()
            payload = json.loads(content_text) if content_text else {}
        except json.JSONDecodeError:
            self.log("消息内容必须是有效的JSON")
            return
        
        message = CrossDomainMessage(message_type, payload)
        if self.toolkit.hub.send_message_to(self.current_connection, message):
            self.log(f"已发送消息到 {self.current_connection}")
        else:
            self.log("发送消息失败")
    
    def on_broadcast_message(self):
        """处理广播消息按钮点击"""
        message_type = self.message_type_input.text()
        if not message_type:
            self.log("请输入消息类型")
            return
        
        try:
            content_text = self.message_content_input.toPlainText()
            payload = json.loads(content_text) if content_text else {}
        except json.JSONDecodeError:
            self.log("消息内容必须是有效的JSON")
            return
        
        message = CrossDomainMessage(message_type, payload)
        self.toolkit.hub.broadcast_message(message)
        self.log("已广播消息到所有连接")
    
    def on_rpc_call(self):
        """处理RPC调用按钮点击"""
        if not self.current_connection:
            self.log("请先选择一个连接")
            return
        
        method_name = self.rpc_method_input.text()
        if not method_name:
            self.log("请输入方法名")
            return
        
        try:
            params_text = self.rpc_params_input.toPlainText()
            params = json.loads(params_text) if params_text else {}
        except json.JSONDecodeError:
            self.log("参数必须是有效的JSON")
            return
        
        try:
            result = self.toolkit.rpc.call(self.current_connection, method_name, params)
            self.log(f"RPC调用结果: {result}")
        except Exception as e:
            self.log(f"RPC调用错误: {str(e)}")
    
    def on_client_connected(self, connection_id: str):
        """处理客户端连接事件"""
        self.log(f"客户端已连接: {connection_id}")
        self.update_connections_list()
    
    def on_client_disconnected(self, connection_id: str):
        """处理客户端断开事件"""
        self.log(f"客户端已断开: {connection_id}")
        self.update_connections_list()
        
        # 如果断开的是当前选中的连接，清除选择
        if self.current_connection == connection_id:
            self.current_connection = None
            self.connections_list.clearSelection()
    
    def on_message_received(self, message: CrossDomainMessage):
        """处理消息接收事件"""
        self.log(f"收到消息 [{message.type}]: {json.dumps(message.payload, ensure_ascii=False)}")
    
    def on_error_occurred(self, error: str):
        """处理错误事件"""
        self.log(f"错误: {error}")
    
    def greet_method(self, name: str) -> str:
        """示例RPC方法"""
        return f"Hello, {name}! 当前时间: {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')}"
    
    def get_time_method(self) -> str:
        """获取当前时间的RPC方法"""
        return QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 创建并显示示例应用程序
    example_app = ExampleApp()
    example_app.show()
    
    sys.exit(app.exec_())