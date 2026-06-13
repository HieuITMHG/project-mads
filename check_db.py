import subprocess
import json

cmd = ['docker', 'compose', '--env-file', '.env.dev', '-f', 'infras/compose/docker-compose.dev.yml', 'exec', 'postgres', 'psql', '-U', 'admin', '-d', 'ecommerce', '-t', '-c', "SELECT metadata_data FROM messages WHERE role='assistant' ORDER BY id DESC LIMIT 1;"]

try:
    out = subprocess.check_output(cmd)
    data = out.decode('utf-8').strip()
    with open('db_out.txt', 'w', encoding='utf-8') as f:
        f.write(data)
    print("DONE. Wrote to db_out.txt")
except Exception as e:
    print("ERROR:", e)
