import subprocess
import os
import time

env = os.environ.copy()
env["DJANGO_SETTINGS_MODULE"] = "exbook.dev_settings"

port = "8001"
cmd = ["python", "manage.py", "runserver", f"0.0.0.0:{port}"]

process = subprocess.Popen(cmd, env=env, stdout=open("/tmp/django_server.log", "w"), stderr=subprocess.STDOUT)
print(f"Server started on port {port} with pid {process.pid}")
