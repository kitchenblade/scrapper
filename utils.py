import mysql.connector, json
from mysql.connector import Error
from mysql.connector.connection import MySQLConnection
from mysql.connector import pooling
import atexit

class Database(object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            try:
                print('Connecting to Database...')
                with open('config.json') as data:
                    config = json.load(data)
                    connection = Database._instance.connection = mysql.connector.pooling.MySQLConnectionPool(
                        pool_name = "scrapper_pool",
                        pool_size = 20,
                        pool_reset_session = True,
                        host = config['txtHost'],
                        user = config['txtUser'],
                        password = config['txtPass'],
                        database = config['txtDB'],
                        buffered=True
                    ).get_connection()  

                cursor = Database._instance.cursor = connection.cursor()
            except Exception as error:
                print('Error: connection not established {}'.format(error))
                Database._instance = None
        return cls._instance            


    def __init__(self):
        self.connection = self._instance.connection
        self.cursor = self._instance.cursor

    def query(self, query, vars=None):
        try:
            result = self.cursor.execute(query)
        except Exception as error:
            print('error execting query "{}", error: {}'.format(query, error))
            return None
        else:
            return result
        
    def commit(self):
        self.connection.commit()

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            print('Database is closed.')
            self.connection.close()
            self.cursor.close()
        except Exception as error:
            print('error: {}'.format(error))
            return None
