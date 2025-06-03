import socket
import threading
import struct

def send_msg(sock, msg_bytes):
    # 先发送4字节消息长度
    msg_len = len(msg_bytes)
    sock.sendall(struct.pack('!I', msg_len))
    sock.sendall(msg_bytes.encode('UTF-8'))

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
        self.clients = []
        self.client_names = {}  # 新增：用字典存储 socket 对应的用户名

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"WebChatHub Server started on {self.host}:{self.port}")
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"Connection from {addr}")
            name = recv_msg(client_socket).decode()
            self.client_names[client_socket] = name  # 记录用户名
            self.clients.append(client_socket)
            self.broadcast(f"A new user ({name}) has joined the chat.", client_socket)
            threading.Thread(target=self.handle_client, args=(client_socket, name)).start()

    def handle_client(self, client_socket, name):
        try:
            while True:
                data_bytes = recv_msg(client_socket)
                if not data_bytes:
                    break
                data = data_bytes.decode()
                print(f"Received from {name}: {data}")
                self.broadcast(data, client_socket, name)  # 传入name
        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            if client_socket in self.client_names:
                del self.client_names[client_socket]
            print("Client disconnected")
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

# 其他代码保持不变
    def stop(self):
        for client in self.clients:
            client.close()
        self.server_socket.close()
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