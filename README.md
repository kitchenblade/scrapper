# INSATALLATION

* Download and install esl-erlang22.0 from https://www.erlang-solutions.com/resources/download.html
* Download and install rabbitmq-server from https://www.rabbitmq.com/download.html
* Initialize virtual environment (eg) 
```sh
python -m venv <virtualEnv-Name>
```
for windows
```
<virtualEnv-Name>\Scripts\activate.bat
```
for linux
```sh
<virtualEnv-Name>\Scripts\activate
```

* Install virtual environment dependencies  
```sh
pip intstall -r requirements
```



> Write the worker task with the decorator @task
> Import the worker to your application

- For monitoring processes in Browser

```sh
pip install wheel flower
```


# START WORKER WITH ONE OF COMMANDS BELOW

```sh
celery worker --app=app.app --pool=eventlet --loglevel=INFO
celery worker --app=app.celery --pool=eventlet --loglevel=INFO
celery worker -A workerappname --pool=gevent --loglevel=INFO
celery worker --app=app.app --pool=solo --loglevel=INFO
celery worker -A app.celery --pool=solo --loglevel=INFO
```

current working command

```sh
celery worker --app=tasks.celery --pool=eventlet --loglevel=INFO -c 10
```



# START FLOWER FOR MONITORING

```sh
celery -A tasks.celery flower --port=5555

celery flower -A proj --address=127.0.0.1 --port=5555
```
Go to http://localhost:5555/ to view works

# EXECUTE MAIN APPLICATION WITH TASKS
```sh
python app.py
```
# INSTALLING CELERY SERVICE 
```sh
pip install PasteScript, paste, configparser
```
Run this commands with administrative rights
```sh
python celeryservice.py install
python CeleryService.py start
python CeleryService.py remove
```