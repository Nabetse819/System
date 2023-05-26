import paramiko
import asyncio
import telegram
import sqlite3
import schedule
import time
import datetime
from queue import Queue

# Configuración de las máquinas virtuales
machines = [
    {
        'hostname': '192.168.0.14',
        'username': 'computer1',
        'password': '12345'
    }
]

# Almacenar los datos capturados en una base de datos
with sqlite3.connect('server_monitoring.db') as conn:
    c = conn.cursor()
    # Crear la tabla si no existe
    c.execute('''CREATE TABLE IF NOT EXISTS server_stats
                 (hostname TEXT, ram_usage INTEGER, cpu_usage INTEGER, disk_usage INTEGER, timestamp TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS notification_count 
                 (hostname TEXT, ram INTEGER, cpu INTEGER, disk INTEGER)''')
    conn.commit()

# Configuración del bot de Telegram
token = '5891431347:AAFKnpQ24Zsf5DDLAcDybklVos0tOEv055I'
chat_id = '-852202995'

# Configuración del umbral de notificación
threshold = 75  # Umbral del 75%

# Inicializar el bot de Telegram
bot = telegram.Bot(token=token)

# Crear una cola para las notificaciones
notification_queue = Queue()

# Función para enviar una notificación al grupo de Telegram
async def send_notification(message):
    await bot.send_message(chat_id=chat_id, text=message)

# Función de procesamiento de la cola de notificaciones
async def process_notifications():
    while not notification_queue.empty():
        message = notification_queue.get()
        await send_notification(message)

def get_notification_count(hostname,notification_type):
    with sqlite3.connect('server_monitoring.db') as conn:
        c = conn.cursor()
        c.execute("SELECT {} FROM notification_count WHERE hostname = ?".format(notification_type), (hostname,))
        result = c.fetchone()

        if result is None:
            # El registro no existe, crearlo
            c.execute("INSERT INTO notification_count (hostname, ram, cpu, disk) VALUES (?, ?, ?,?)",
                      (hostname, 0, 0, 0))
            conn.commit()

    return result[0] if result else 0

def loadNotification(hostname,notification_type,count):
    with sqlite3.connect('server_monitoring.db') as conn:
        c = conn.cursor()
        c.execute("UPDATE notification_count SET {} = ? WHERE hostname = ? ".format(notification_type),
                  (count + 1, hostname,))
        conn.commit()


def process():
    # Conexión SSH y captura de datos
    for machine in machines:
        try:
            # Establecer la conexión SSH
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(machine['hostname'], username=machine['username'], password=machine['password'])

            # Capturar los datos de uso de recursos
            stdin, stdout, stderr = client.exec_command("free -m | awk 'NR==2{print $2}'")
            total_ram = int(stdout.read().decode().strip())  # Obtener el total de memoria RAM disponible

            stdin, stdout, stderr = client.exec_command("free -m | awk 'NR==2{print $3}'")
            used_ram = int(stdout.read().decode().strip())  # Obtener la memoria RAM utilizada
            ram_percentage = int((used_ram / total_ram) * 100)  # Calcular el porcentaje de memoria RAM utilizada

            stdin, stdout, stderr = client.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
            cpu_percentage = int(float(stdout.read().decode().strip()))  # Convertir el uso de CPU a un número entero

            stdin, stdout, stderr = client.exec_command("df -h --output=pcent / | sed '1d;s/[^0-9]//g'")
            disk_percentage = int(float(stdout.read().decode().strip()))  # Obtener el porcentaje de uso de disco

            notification_type = ""
            count = 0
            pass2 = False
            # Insertar los datos capturados en la base de datos
            with sqlite3.connect('server_monitoring.db') as conn:
                c = conn.cursor()
                c.execute("INSERT INTO server_stats (hostname, ram_usage, cpu_usage, disk_usage, timestamp) VALUES (?, ?, ?, ?,?)",
                      (machine['hostname'], ram_percentage, cpu_percentage, disk_percentage, datetime.datetime.now()))
                conn.commit()

            # Verificar si alguna estadística supera el umbral y agregar a la cola
            if ram_percentage > threshold:
                notification_queue.put(f"Uso de RAM alto en {machine['hostname']}: {ram_percentage}%")
                count = get_notification_count(machine['hostname'], "ram")
                notification_type = "ram"
                pass2 = True

            if pass2:
                loadNotification(machine['hostname'], notification_type, count + 1)
            pass2 = False

            if cpu_percentage > threshold:
                notification_queue.put(f"Uso de CPU alto en {machine['hostname']}: {cpu_percentage}%")
                count = get_notification_count(machine['hostname'], "cpu")
                notification_type = "cpu"
                pass2 = True

            if pass2:
                loadNotification(machine['hostname'], notification_type, count + 1)
            pass2 = False

            if disk_percentage > threshold:
                notification_queue.put(f"Uso de disco alto en {machine['hostname']}: {disk_percentage}%")
                count = get_notification_count(machine['hostname'], "disk")
                notification_type = "disk"
                pass2 = True

            if pass2:
                loadNotification(machine['hostname'], notification_type, count + 1)
            # Cerrar la conexión SSH
            client.close()
        except paramiko.AuthenticationException:
            print(f"Error de autenticación en {machine['hostname']}")
        except paramiko.SSHException as e:
            print(f"Error SSH en {machine['hostname']}: {str(e)}")
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            print(f"No se puede establecer una conexión SSH con {machine['hostname']}: {str(e)}")
        except Exception as e:
            print(f"Error en {machine['hostname']}: {str(e)}")

# Ejecución asincrónica principal
async def main():

    # Programar la ejecución de la función cada 1 minuto
    schedule.every(5).seconds.do(process)
    # Procesar las notificaciones en la cola
    # schedule.every(1).seconds.do(process_notifications)

    while True:
        schedule.run_pending()
        while not notification_queue.empty():
            message = notification_queue.get()
            await bot.send_message(chat_id=chat_id, text=message)
        await asyncio.sleep(5)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass