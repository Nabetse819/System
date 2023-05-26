import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import requests
from flask_socketio import SocketIO
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': '*'}})
socketio = SocketIO(app, async_mode='gevent')

hostname = ''


@app.route('/')
def home():
    return render_template('index.html')


def send_update():
    while True:
        response = requests.post('http://localhost:5000/server_stats', json={'hostname': hostname})
        data = response.json()
        if response.status_code == 200 and 'hostname' in data:
            timestamp = data.get('timestamp')
            time_format = '%Y-%m-%d %H:%M:%S.%f'
            date_time = datetime.strptime(timestamp, time_format)
            data['timestamp'] = date_time.strftime("%Y-%m-%d %H:%M:%S")
            socketio.sleep(1)
            socketio.emit('update', data)


def send_update2():
    while True:
        response = requests.post('http://localhost:5000/notification', json={'hostname': hostname})
        data = response.json()
        if response.status_code == 200 and 'hostname' in data:
            socketio.sleep(1)
            socketio.emit('updateNotification', data)


@app.route('/server_stats', methods=['POST'])
def get_server_stats():
    global hostname
    hostname = request.form.get('hostname')
    response = requests.post('http://localhost:5000/server_stats', json={'hostname': hostname})
    data = response.json()

    if response.status_code == 200 and 'hostname' in data:
        timestamp = data.get('timestamp')
        time_format = '%Y-%m-%d %H:%M:%S.%f'
        date_time = datetime.strptime(timestamp, time_format)
        data['timestamp'] = date_time.strftime("%Y-%m-%d %H:%M:%S")
        return render_template('result.html', stats=data)
    else:
        return render_template('index.html', message=data['message'])


if __name__ == '__main__':
    t = threading.Thread(target=send_update)
    t.daemon = True
    t.start()

    t2 = threading.Thread(target=send_update2)
    t2.daemon = True
    t2.start()

    # app.run(debug=True, port=8080)
    socketio.run(app, port=8080)
