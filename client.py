import socket
import threading
import struct
import os
running = True
name = None

message_list = []

def flush_messages():
    os.system('cls')
    print("Messages:")
    for msg in message_list:
        print(msg)
    print('---------')
    print(f"Type 'bye' to exit, or enter a message to send.")

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

def recv(sock):
    while running:
        try:
            data = recv_msg(sock).decode()
            message_list.append(data)  # 将接收到的消息添加到列表中
            flush_messages()
            if data is None:
                print("Connection closed by server.")
                break
        except Exception as e:
            print(f"Error receiving message: {e}")
            break

if __name__ == '__main__':
    name = input("Enter your name: ")
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1',65532))
    send_msg(client_socket, name)  # 发送用户名到服务器
    flush_messages()
    recv_thread = threading.Thread(target=recv, args=(client_socket,))
    recv_thread.daemon = True
    recv_thread.start()

try:
    while True:
        str = input()
        if str == 'bye':
            #send_msg(client_socket,f"{name} has left the chat.")
            break
        else:
            send_msg(client_socket,str)
            message_list.append(f"{name}: {str}")  # 将消息添加到列表中
            flush_messages()
finally:
    running = False
    client_socket.close()
    recv_thread.join()
