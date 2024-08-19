import psycopg2

conn = psycopg2.connect("""
    host=wokrofanu.beget.app
    port=5432
    sslmode=disable
    dbname=default_db
    user=cloud_user
    password=vhoDJf4&QCPT
    target_session_attrs=read-write
""")

q = conn.cursor()

# Чтение SQL-скрипта
with open('local_db_dump.sql', 'r') as file:
    sql = file.read()

# Выполнение SQL-скрипта
q.execute(sql)
conn.commit()

q.close()
conn.close()
