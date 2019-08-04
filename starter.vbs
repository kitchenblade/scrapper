Dim wsh
Dim activate_env
Dim start_worker 
Dim start_flask

activate_env = "scrapper-env\Scripts\activate.bat"
start_worker = "celery worker --app=tasks.celery --pool=eventlet --loglevel=INFO -c 10"
start_flask = "python app.py"
start_flower = "celery -A tasks.celery flower --port=5555"

set wsh = WScript.CreateObject ("WSCript.shell")

wsh.run "cmd /k " & activate_env & "&&" & start_worker
wsh.run "cmd /k " & activate_env & "&&" & start_flask
wsh.run "cmd /k " & activate_env & "&&" & start_flower

set wsh = nothing