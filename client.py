import eventlet
eventlet.monkey_patch()

import socket
import threading
import struct
import os

running = True
name = None
message_list = []

def flush_messages():
    os.system('cls' if os.name == 'nt' else 'clear')
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
        try:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Recv error: {e}")
            return None
    return data
def recv_msg(sock):
    # 读取4字节消息长度
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('!I', raw_msglen)[0]
    # 再读取消息体
    return recvall(sock, msglen)

def recv_handler(sock):
    global running
    while running:
        try:
            # data = recv_msg(sock).decode()
            data = recv_msg(sock)
            if data is None:
                print("Connection closed by server.")
                running = False
                break
            decoded_data = data.decode()
            message_list.append(decoded_data)  # 将接收到的消息添加到列表中
            flush_messages()
        except Exception as e:
            if running:
                print(f"Error receiving message: {e}")
            running = False
            break

def input_handler(sock):
    global running
    while running:
        try:
            user_input = input()
            if not running:
                break
                
            if user_input == 'bye':
                send_msg(sock, f"{name} has left the chat.")
                running = False
                break
            else:
                send_msg(sock, user_input)
                message_list.append(f"{name}: {user_input}")
                flush_messages()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            running = False
        except Exception as e:
            print(f"Input error: {e}")
            running = False

if __name__ == '__main__':
    name = input("Enter your name: ")
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(2.0)  # 设置超时
        client_socket.connect(('127.0.0.1',65532))
        send_msg(client_socket, name)  # 发送用户名到服务器
        flush_messages()
        # recv_thread = threading.Thread(target=recv, args=(client_socket,))
        # recv_thread.daemon = True
        # recv_thread.start()
        # 使用 eventlet 协程处理接收和输入
        recv_coroutine = eventlet.spawn(recv_handler, client_socket)
        input_coroutine = eventlet.spawn(input_handler, client_socket)

        # 等待两个协程完成
        recv_coroutine.wait()
        input_coroutine.wait()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error connecting to server: {e}")
    finally:
        running = False
        try:
            client_socket.close()
        except:
            pass

# try:
#     while True:
#         str = input()
#         if str == 'bye':
#             #send_msg(client_socket,f"{name} has left the chat.")
#             break
#         else:
#             send_msg(client_socket,str)
#             message_list.append(f"{name}: {str}")  # 将消息添加到列表中
#             flush_messages()
# finally:
#     running = False
#     client_socket.close()
#     recv_thread.join()
