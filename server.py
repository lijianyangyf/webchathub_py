# need to be started first
# `python server.py`
import eventlet
eventlet.monkey_patch()

import socket
import threading
import struct

def send_msg(sock, message):
    # 先发送4字节消息长度
    # 确保消息是字节形式
    if isinstance(message, str):
        msg_bytes = message.encode('utf-8')
    elif isinstance(message, bytes):
        msg_bytes = message
    else:
        raise ValueError("Unsupported message type")
    msg_len = len(msg_bytes)
    try:
        sock.sendall(struct.pack('!I', msg_len))
        sock.sendall(msg_bytes)
        return True
    except (OSError, BrokenPipeError, ConnectionResetError):
        return False

def recvall(sock, n):
    # 循环接收n字节数据，直到接收完毕
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def recv_msg(sock):
    # 读取4字节消息长度
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('!I', raw_msglen)[0]
    # 再读取消息体
    return recvall(sock, msglen)

class WebChatHubServer:
    def __init__(self,host='127.0.0.1',port=65532):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = []
        self.client_names = {}  # 用字典存储 socket 对应的用户名
        self.running = True
        self.lock = threading.Lock()

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(2.0)  # 设置超时
        print(f"WebChatHub Server started on {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"Connection from {addr}")
                client_socket.settimeout(1.0)
                name = recv_msg(client_socket).decode('utf-8', 'ignore')

                with self.lock:
                    self.client_names[client_socket] = name  # 记录用户名
                    self.clients.append(client_socket)
                self.broadcast(f"A new user ({name}) has joined the chat.", client_socket)

                # 使用eventlet协程处理客户端
                eventlet.spawn_n(self.handle_client, client_socket, name)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Accept error: {e}")
                break

    def handle_client(self, client_socket, name):
        try:
            while self.running:
                try:
                    data_bytes = recv_msg(client_socket)
                    if not data_bytes:
                        break
                    data = data_bytes.decode('utf-8', 'ignore')
                    print(f"Received from {name}: {data}")
                    self.broadcast(data, client_socket, name)  # 传入name
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Client error: {e}")
                    break
        finally:
            with self.lock:
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
                if client_socket in self.client_names:
                    del self.client_names[client_socket]
            try:
                client_socket.close()
            except:
                pass
            print(f"Client {name} disconnected")
            self.broadcast(f"{name} has left the chat.", client_socket)

    def broadcast(self, message, sender_socket, sender_name=None):
        # 广播消息给所有客户端，除了发送者
        for client in self.clients[:]:
            if client != sender_socket:
                try:
                    if sender_name:
                        msg = f"{sender_name}: {message}"
                    else:
                        msg = message
                    send_msg(client, msg)
                except Exception as e:
                    print(f"Error sending message to {client.getpeername()}: {e}")
                    client.close()
                    if client in self.clients:
                        self.clients.remove(client)
                    if client in self.client_names:
                        del self.client_names[client]

    def stop(self):
        self.running = False
        with self.lock:
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            self.clients = []
            self.client_names = {}
        try:
            self.server_socket.close()
        except:
            pass
        print("WebChatHub Server stopped")

if __name__ == "__main__":
    server = WebChatHubServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
    except Exception as e:
        print(f"Server error: {e}")
        server.stop()