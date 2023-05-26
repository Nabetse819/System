from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO
import sqlite3

app = Flask(__name__)
socketio = SocketIO(app)
cors = CORS(app, resources={r"/server_stats": {"origins": "*"}})


def retrieve_result_from_database(hostname):
    # Realizar una consulta a la base de datos para obtener los resultados
    with sqlite3.connect('server_monitoring.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM server_stats WHERE hostname = ? ORDER BY timestamp DESC LIMIT 1", (hostname,))
        row = c.fetchone()

        if row:
            response = {
                'hostname': row[0],
                'ram_usage': row[1],
                'cpu_usage': row[2],
                'disk_usage': row[3],
                'timestamp': row[4],
            }
            return response
        else:
            return None


def retrieve_result_from_notification(hostname):
    # Realizar una consulta a la base de datos para obtener los resultados
    with sqlite3.connect('server_monitoring.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM notification_count WHERE hostname = ? ", (hostname,))
        row = c.fetchone()

        if row:
            response = {
                'hostname': row[0],
                'ram': row[1],
                'cpu': row[2],
                'disk': row[3],
            }
            return response
        else:
            return None


@app.route('/server_stats', methods=['POST'])
def get_server_stats():
    data = request.get_json()
    hostname = data['hostname']
    result = retrieve_result_from_database(hostname)
    if result:
        return jsonify(result)
    else:
        return jsonify({'message': 'No data found for the given hostname'})


@app.route('/notification', methods=['POST'])
def get_server_stats2():
    data = request.get_json()
    hostname = data['hostname']
    result = retrieve_result_from_notification(hostname)
    if result:
        return jsonify(result)
    else:
        return jsonify({'message': 'No data found for the given hostname'})


if __name__ == '__main__':
    app.run()
