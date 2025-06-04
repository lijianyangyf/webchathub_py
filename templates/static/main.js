var socket = io();
var loggedIn = false;
var currentUsername = '';

function login() {
    var name = document.getElementById('name').value.trim();
    if (!name) {
        alert("Please enter your name");
        return;
    }
    currentUsername = name;
    socket.emit('login', {name: name});
}

socket.on('login_response', function(data) {
    if (data.success) {
        loggedIn = true;
        document.getElementById('login-area').style.display = 'none';
        document.getElementById('chat-area').style.display = 'flex';
        addMessage("System: Logged in successfully", 'system');
    } else {
        alert("Login failed: " + data.error);
    }
});

socket.on('server_message', function(data) {
    if (data.sender === currentUsername) {
        addMessage(data.msg, 'user');
    } else {
        addMessage(data.msg, 'other');
    }
});

function sendMessage() {
    if (!loggedIn) {
        alert("Please login first");
        return;
    }
    var msgInput = document.getElementById('message');
    var msg = msgInput.value.trim();
    if (!msg) return;
    socket.emit('send_message', {msg: msg});
    msgInput.value = '';
    msgInput.focus();
}

function addMessage(msg, type) {
    var messagesDiv = document.getElementById('messages');
    var p = document.createElement('p');
    p.classList.add('msg', type);

    p.textContent = msg;
    messagesDiv.appendChild(p);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Exit chat function
function exitChat() {
    if (!loggedIn) {
        alert("Please login first");
        return;
    }
    socket.emit('exit_chat');
    loggedIn = false;
    document.getElementById('login-area').style.display = 'flex';
    document.getElementById('chat-area').style.display = 'none';
    document.getElementById('messages').innerHTML = '';
    addMessage("System: You have left the chat", 'system');

    // Clear the name field and focus
    document.getElementById('name').value = '';
    document.getElementById('name').focus();
}

// Handle exit confirmation from server
socket.on('exit_confirmation', function() {
    addMessage("System: You have successfully left the chat", 'system');
});

function init() {
    // Set up event listeners
    document.getElementById('login-btn').addEventListener('click', login);
    document.getElementById('send-btn').addEventListener('click', sendMessage);
    document.getElementById('exit-btn').addEventListener('click', exitChat);

    // Handle Enter key in input fields
    document.getElementById('name').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') login();
    });

    document.getElementById('message').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });
}

window.addEventListener('DOMContentLoaded', function() {
    init();
    // Focus on the name input field on load
    document.getElementById('name').focus();
});