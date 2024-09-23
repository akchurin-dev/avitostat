import subprocess
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Параметры для дампа
db_host = 'wokrofanu.beget.app'
db_port = '5432'
db_user = 'cloud_user'
db_name = 'default_db'
db_password = os.getenv('DB_PASS')
backup_dir = '/var/backups/db_backups'
backup_filename = f"local_db_dump_{datetime.now().strftime('%Y-%m-%d')}.sql"

# Формирование команды
command = [
    'pg_dump',
    '-h', db_host,
    '-p', db_port,
    '-U', db_user,
    '-d', db_name,
    '-F', 'c',
    '-f', os.path.join(backup_dir, backup_filename)
]

# Установка переменной окружения для пароля
env = os.environ.copy()
env['PGPASSWORD'] = db_password

# Выполнение команды
try:
    subprocess.run(command, env=env, check=True)
    print(f"Backup successful: {backup_filename}")
except subprocess.CalledProcessError as e:
    print(f"Error during backup: {e}")
