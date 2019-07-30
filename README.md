1. Download and install esl-erlang22.0 from https://www.erlang-solutions.com/resources/download.html
2. Download and install rabbitmq-server from https://www.rabbitmq.com/download.html


Write the worker task with the decorator @task
Import the worker to your application

pip install wheel flower == for monitoring processes in Browser

#START WORKER WITH ONE OF COMMANDS BELOW
celery worker --app=app.app --pool=eventlet --loglevel=INFO
celery worker --app=app.celery --pool=eventlet --loglevel=INFO
celery worker -A workerappname --pool=gevent --loglevel=INFO
celery worker --app=app.app --pool=solo --loglevel=INFO
celery worker -A app.celery --pool=solo --loglevel=INFO


#START FLOWER FOR MONITORING
celery -A workerappname flower --port=5555

Go to http://localhost:5555/ to view works

# EXECUTE MAIN APPLICATION WITH TASKS
python app.py

# INSTALLING CELERY SERVICE 
pip install PasteScript, paste, configparser

Run this commands with administrative rights

python celeryservice.py install
python CeleryService.py start
python CeleryService.py remove