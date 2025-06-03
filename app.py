import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
import socket
import struct
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

CHAT_SERVER_HOST = '127.0.0.1'
CHAT_SERVER_PORT = 65532

clients = {}  # 存储每个客户端信息，key为sid

def send_msg(sock, msg_bytes):
    msg_len = len(msg_bytes)
    sock.sendall(struct.pack('!I', msg_len))
    sock.sendall(msg_bytes.encode('utf-8'))

def recvall(sock, n):
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def recv_msg(sock):
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('!I', raw_msglen)[0]
    return recvall(sock, msglen)

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
        client_socket.connect((CHAT_SERVER_HOST, CHAT_SERVER_PORT))
        send_msg(client_socket, name)
    except Exception as e:
        emit('login_response', {'success': False, 'error': f'Cannot connect to chat server: {e}'})
        disconnect()
        return

    running_flag = {'running': True}  # 用字典方便线程内修改

    def recv_thread(sid, sock, running):
        while running['running']:
            try:
                data = recv_msg(sock)
                if data is None:
                    print(f"Connection closed by chat server for sid {sid}")
                    socketio.emit('server_message', {'msg': 'Connection closed by chat server'}, room=sid)
                    break
                msg = data.decode('utf-8')
                socketio.emit('server_message', {'msg': msg}, room=sid)
            except Exception as e:
                print(f"Error receiving from chat server for sid {sid}: {e}")
                break
        socketio.emit('server_message', {'msg': 'Disconnected from chat server'}, room=sid)
        disconnect(sid=sid)

    thread = threading.Thread(target=recv_thread, args=(request.sid, client_socket, running_flag))
    thread.daemon = True
    thread.start()

    clients[request.sid] = {
        'sock': client_socket,
        'thread': thread,
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
        send_msg(client_info['sock'], msg)
        emit('server_message', {'msg': f"{client_info['name']}: {msg}"}, room=request.sid)
    except Exception as e:
        emit('server_message', {'msg': f"Failed to send message: {e}"})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)