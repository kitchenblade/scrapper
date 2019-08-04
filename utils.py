import mysql.connector, json
from mysql.connector import Error
from mysql.connector.connection import MySQLConnection
from mysql.connector import pooling

class Database:
    __instance = None

    @staticmethod
    def getInstance():
        if Database.__instance == None:
            Database()
        return Database.__instance

    def __init__(self):
        if Database.__instance != None:
            raise Exception("Class is Database")
        else:
            with open('config.json') as data:
                config = json.load(data)
                connection = mysql.connector.pooling.MySQLConnectionPool(
                    pool_name = "scrapper_pool",
                    pool_size = 5,
                    pool_reset_session = True,
                    host = config['txtHost'],
                    user = config['txtUser'],
                    password = config['txtPass'],
                    database = config['txtDB']
                )   
            db = connection.get_connection()
            Database.__instance = db
