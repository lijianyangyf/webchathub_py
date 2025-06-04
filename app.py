# Used to run a Flask application with SocketIO for real-time communication.
# run after the server is started
# `python app.py`
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
import socket
import struct
import threading

app = Flask(__name__, static_folder='templates/static', template_folder='templates')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

CHAT_SERVER_HOST = '127.0.0.1'
CHAT_SERVER_PORT = 65532

clients = {}  # 存储每个客户端信息，key为sid
client_lock = threading.Lock() # 保护clients字典

def send_msg(sock, message):
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
    try:
        msglen = struct.unpack('!I', raw_msglen)[0]
        # 再读取消息体
        return recvall(sock, msglen)
    except struct.error:
        return None

def recv_thread(sid, sock, running):
    while running['running']:
        try:
            data = recv_msg(sock)
            if data is None:
                print(f"Connection closed by chat server for sid {sid}")
                socketio.emit('server_message', {'msg': 'Connection closed by chat server'}, room=sid)
                break
            msg = data.decode('utf-8', 'ignore')
            socketio.emit('server_message', {'msg': msg}, room=sid)
        except socket.timeout:
            continue
        except Exception as e:
            if running['running']:
                # 仅记录意外错误
                print(f"Error receiving from chat server for sid {sid}: {e}")
            break

    # 清理资源
    with client_lock:
        if sid in clients:
            clients[sid]['running'] = False
            try:
                sock.close()
            except:
                pass
            socketio.emit('server_message', {'msg': 'Disconnected from chat server'}, room=sid)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    client_info = clients.get(request.sid)
    if client_info:
        client_info['running'] = False
        try:
            client_info['sock'].close()
        except:
            pass
        del clients[request.sid]

@socketio.on('login')
def handle_login(data):
    name = data.get('name')
    if not name:
        emit('login_response', {'success': False, 'error': 'No name provided'})
        disconnect()
        return

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5.0)  # 设置超时防止永久阻塞
        client_socket.connect((CHAT_SERVER_HOST, CHAT_SERVER_PORT))
        if not send_msg(client_socket, name):
            emit('login_response', {'success': False, 'error': 'Failed to send name to chat server'})
            disconnect()
            return
    except Exception as e:
        emit('login_response', {'success': False, 'error': f'Cannot connect to chat server: {e}'})
        disconnect()
        return

    running_flag = {'running': True}  # 用字典方便线程内修改

    socketio.start_background_task(
        recv_thread, 
        request.sid, 
        client_socket, 
        running_flag
    )

    with client_lock:
        clients[request.sid] = {
            'sock': client_socket,
            'running': running_flag,
            'name': name
        }

    emit('login_response', {'success': True})

@socketio.on('send_message')
def handle_send_message(data):
    client_info = clients.get(request.sid)
    if not client_info:
        emit('server_message', {'msg': 'Not connected to chat server'})
        return

    msg = data.get('msg')
    if not msg:
        return

    try:
        if not send_msg(client_info['sock'], msg):
            emit('server_message', {
                'msg': 'Failed to send message to chat server',
                'sender': 'system'
            })
        emit('server_message', {
            'msg': f"{client_info['name']}: {msg}",
            'sender': client_info['name']
        }, room=request.sid)
    except Exception as e:
        emit('server_message', {
            'msg': f"Failed to send message: {e}",
            'sender': 'system'
        })

# 处理退出事件
@socketio.on('exit_chat')
def handle_exit():
    sid = request.sid
    with client_lock:
        if sid in clients:
            # 清理资源
            client_info = clients.get(sid)
            client_info['running'] = False
            try:
                client_info['sock'].close()
            except:
                pass
            # 移除客户端
            del clients[sid]

def run_app():
    """用于 flask run 命令的启动函数"""
    socketio.run(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    run_app()