#!/usr/bin/python
from __future__ import print_function
from flask import Flask, render_template, request, redirect, url_for, flash, Response, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os, re, time, sys
import PyPDF2, json, mysql.connector
from multiprocessing import Pool
from werkzeug.datastructures import FileStorage
import requests, threading, time, pprint, string

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

from celery import Celery

from flask_debugtoolbar import DebugToolbarExtension

data_to_db = []
page_data    = []
job_state = False

UPLOAD_PATH = 'static/pics'
ALLOWED_EXTENSIONS = set(['pdf', 'jpg'])

app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = 'pyamqp://guest@localhost//'
app.config['task_acks_late'] = True
app.config['worker_prefetch_multiplier'] = 1
# app.config['BROKER_TRANSPORT_OPTIONS'] = {'visibility_timeout': 3600*10}  # 10 hours
# app.config['CELERY_RESULT_BACKEND'] = 'rpc://'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


app.config['UPLOAD_PATH'] = UPLOAD_PATH
app.config['SECRET_KEY'] = 'secret'
# app.config['task_acks_late'] = True
# app.config['worker_prefetch_multiplier'] = 1
# app.config['CORS_HEADERS'] = 'Content-Type'
CORS(app)
# cors = CORS(app, resources={r"/jobs": {"origins": "http://127.0.0.1:5000"}})

def getConfig():
    global config
    with open('config.json') as json_data_file:
        try:
            config = json.load(json_data_file)
            return True
        except:
            return False
    print(config)

def database():
    global database
    conf = getConfig()
    if conf:
        database = mysql.connector.connect(
            host=config['txtHost'],
            user=config['txtUser'],
            password=config['txtPass'],
            database=config['txtDB']
        )
    else:
        print('no config loaded')

database()

def dbClose():
    database.close()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def loadMain():
    conf = getConfig()
    if conf:
        pass
        page_data.append(config)
        # cursor = database.cursor()
        # cursor.execute("SELECT * FROM jobs")
        # page_data.append(cursor.fetchall())  
    else :
        page_data.append([]) 
    return render_template('index.html', page_data=page_data)

def photo_disp(val):
    return '<img src="../static/pics/'+str(val)+'" alt="image" width="50" />'
    # return '../static/pics/'+

def status_button(val):
    # 0 - new
    # 1 - Queued
    # 2 - processing
    # 3 - Done
    if val==0:
        return '<button class="btn btn-warning" type="button" disabled><span class="glyphicon glyphicon-time" aria-hidden="true"></span> Pending</button>'
    elif val==1:
        return '<button class="btn btn-primary" type="button" disabled><span class="glyphicon glyphicon-refresh" aria-hidden="true"></span> In Queue</button>'
    elif val==2:
        return '<button class="btn btn-primary" type="button" disabled><span class="glyphicon glyphicon-refresh" aria-hidden="true"></span> Working</button>'
    elif val==3:
        return '<button class="btn btn-success" type="button" disabled><span class="glyphicon glyphicon-ok" aria-hidden="true"></span> Done &nbsp; &nbsp;</button>'
    else:
        return '<button class="btn btn-danger" type="button" disabled><span class="glyphicon glyphicon-remove" aria-hidden="true"></span> Unknown</button>'

def notes_format(val):
    if val==0:
        return ''
    else:
        return val

def run_queries(table,columns):
    output = {}
    mycursor = database.cursor()
    mycursor.execute("SELECT COUNT(*) from "+table)
    (db_total,)=mycursor.fetchone()

    _filter = filtering()
    mycursor.execute("SELECT COUNT(*) FROM "+table+_filter)
    (rec_total,)=mycursor.fetchone()
    _paging=paging()

    column_names =[]
    formatters={}
    for column in columns:
        column_names.append(column['db'])
        if column['formatter'] !='':
            formatters[column['dt']]= column['formatter']

    _columns = ', '.join("`{0}`".format(c) for c in column_names)
    _sorting = sorting()
    sql ="SELECT "+_columns+'FROM '+table+_filter+_sorting+_paging
    mycursor.execute(sql)    
    result_data = mycursor.fetchall()
    database.commit()

    output["draw"] = request.values['draw']
    output["recordsTotal"]= db_total
    output["recordsFiltered"]= rec_total #len(result_data)

    Data_rows = []
    # print(result_data)
    for row in result_data:
        Data_row = []
        c=0
        for i in range(len(row)):
            if i in formatters:
                formatit = formatters[i]
                Data_row.append(formatit(row[i]))
            else:
                Data_row.append(row[i])

        Data_rows.append(Data_row)
    output['data'] = Data_rows
    return output

def filtering():     
    _filter = ''
    if request.values['search[value]'] != '':
        _filter +=' WHERE '
        _filt=[]
        for column in columns:
            if request.values['columns['+str(column['dt'])+'][searchable]']:
                _filt.append("`"+str(column['db'])+"` LIKE '%"+request.values['search[value]']+"%'")
        _filter += ' OR '.join(_filt)
    return _filter

def sorting():
    order = ''
    for column in columns:
        if int(column['dt']) == int(request.values['order[0][column]']):
            order = " ORDER BY `"+str(column['db'])+"` "+str(request.values['order[0][dir]']+" ")
    return order

def paging():
    pages =''
    if (request.values['start'] != '' ) and (int(request.values['length']) > 0 ):
        pages = ' LIMIT '+request.values['length']+' OFFSET '+request.values['start']
    return str(pages)

# ============= CELERY TASKS ======================
@celery.task
def pdf_processor(job):
    print("\n Process started" )
    # import os
    cursor = database.cursor()
    src_path = os.path.join(config['txtPath'], job[1])
    exists = os.path.isfile(src_path)
    if exists:
        # database()
        # cursor=database.cursor()
        data=(2,job[1])
        sql = """UPDATE jobs SET status = %s WHERE `file_name` =%s"""
        cursor.execute(sql,data)
        database.commit()
        dst_path =config['txtPath']
        dst_path += '/done'
        if not os.path.exists(dst_path):
            os.makedirs(dst_path)
        
        pdfFileObj = open(src_path, 'rb')

        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        num_pages = pdfReader.numPages
        page_number = 0
        id_list = []
        name_list = []
        sex_list = []
        age_list = []
        processed_page_to_db = []

        pol_code = ''
        pol_name = ''
        constituency = ''
        region = ''
        district = ''
        no_of_voters = ''
        records_count = 0
        # Let's flip through the pages
        while page_number < num_pages:
            time.sleep(0.3)
            sys.stdout.write("\r[%d" % page_number + "%]" + "#" * page_number)
            pageObj = pdfReader.getPage(page_number)
            texts = pageObj.extractText()
            words = texts.split(': ')

            # Look for the first page
            if page_number == 0:
                words = texts.split(':')
                pol_code = words[2][:-20]
                pol_name = words[3][:-12]
                constituency = words[4][:-8]
                region = words[6][:-128]
                district = words[5][:-6]
                page_number += 1
                continue

            # Last but one page
            if page_number == num_pages-2:
                word = texts.split('=')
                numbs = re.findall(r'\d+', str(word[1]))
                no_of_voters = str(numbs[0])

            page_number += 1

            for i in range(len(words)):
                if 'Age' in words[i]:
                    voter_id = words[i][:-3]
                    age = words[i+1][:-3]
                    sex = words[i+2][0]
                    if 'Page' in words[i+2]:
                        name = words[i+2][6:-24]
                    else:
                        name = words[i+2][6:-18]
                    id_list.append(voter_id)
                    name_list.append(name)
                    sex_list.append(sex)
                    age_list.append(age)

            if '/XObject' in pageObj['/Resources']:
                xObject = pageObj['/Resources']['/XObject'].getObject()
                for obj in xObject:
                    if xObject[obj]['/Subtype'] == '/Image':
                        data = xObject[obj].getData()

                        if int(int(obj[4:])-1) >= 0:
                            picture = id_list[int(obj[4:])-1] + ".jpg"
                            voter_id = id_list[int(obj[4:])-1]
                            # name = name_list[int(obj[4:])-1]
                            name = name_list[int(obj[4:])-1].rsplit('(', 1)[0]
                            sex = sex_list[int(obj[4:])-1]
                            age = age_list[int(obj[4:])-1]

                            dest_path = os.path.join(
                                UPLOAD_PATH, picture)
                            img = open(dest_path, "wb")
                            img.write(data)
                            img.close()                           
                            processed_page = (pol_code, voter_id, name, sex, age, picture)
                            processed_page_to_db.append(processed_page)
                            records_count += 1
        sql = "INSERT IGNORE INTO info (pol_code, pol_name, constituency, district, region, count_on_pdf, total_records) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        val = (pol_code, pol_name, constituency, district, region, no_of_voters, records_count)
        cursor.execute(sql, val)
        database.commit()

        sql = "INSERT IGNORE INTO candidates (pol_station_code, id, name, sex, age, picture) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.executemany(sql, processed_page_to_db)
        database.commit()

        data=(3,job[1])
        sql = """UPDATE jobs SET status = %s WHERE `file_name` =%s"""
        cursor.execute(sql,data)
        database.commit()

        pdfFileObj.close()  # Close the file afterwards
        # os.remove(src_path) #Delete the file afterwards
        dst = os.path.join(dst_path, job[1])
        os.rename(src_path, dst) 
        # shutil.move(src_path, dst)  
        # dbClose()
        # return processed_file
            # Store configuration file values
        print("\n Process Finished.")
        return True
    else:
        # Keep presets
        data=(5,job[1])
        sql = """UPDATE jobs SET status = %s WHERE `file_name` =%s"""
        cursor.execute(sql,data)
        database.commit()
        print("\n File missing.")
        return False

@celery.task
def process(jobs):   
    if len(jobs)==0:
        print("\n No jobs left to process.")
    else:
        cursor = database.cursor()
        for job in jobs:
            data=(1,job[1])
            sql = """UPDATE jobs SET status = %s WHERE `file_name` =%s"""
            cursor.execute(sql,data)
            database.commit()
            # task = pdf_processor.s(job).delay()            
            task = pdf_processor.delay(job)
            print(f'Started task: {task}')

# =============== ROUTES ==========================
@app.route("/", methods=['GET', 'POST'])
def index():
    return loadMain()

@app.route('/config', methods=['POST'])
def db_config():
    global env_config
    env_config = {}
    env_config["txtHost"] = request.form['txtHost']
    env_config["txtUser"] = request.form['txtUser']
    env_config["txtPass"] = request.form['txtPassword']
    env_config["txtDB"]   = request.form['txtDatabase']
    env_config["txtPath"] = request.form['txtPath'].replace("\\","/")
    env_config["txtOutPath"] = request.form['txtOutPath'].replace("\\","/")
    # write config file
    with open('config.json', 'w') as outfile:
        # print json.dumps(d, ensure_ascii=False)
        json.dump(env_config, outfile)
    flash('Configuration has been updated successfully.')
    # return render_template('index.html')
    # dbClose()
    # return database()
    return loadMain()

@app.route('/dbreset')
def clear_database():
    cursor = database.cursor()
    sql = open('config.json')
    for sql in open('database.sql'):
        cursor.execute(sql)
        database.commit()
    # cursor.execute('TRUNCATE TABLE jobs;')
    # database.commit()
    flash('Database cleared')
    pprint.pprint(sql)
    return loadMain()

@app.route('/getdata')
def getAllData():
    # cursor = database.cursor()
    # cursor.execute("SELECT * FROM candidates")
    # data = cursor.fetchall()
    return render_template('datapage.html')

@app.route('/refresh')
def refreshPath():
    getConfig()
    path = config['txtPath']
    
    count = 0
    for filename in os.listdir(path):
        if  filename.endswith(('.pdf','PDF')):
            val = ('NULL', filename, '0', '')
            data_to_db.append(val)
            count += 1

    if count > 0:
        # database()
        try:
            cursor= database.cursor()
            sql = "INSERT IGNORE INTO jobs (id, file_name, status, notes) VALUES (%s, %s, %s, %s)"
            cursor.executemany(sql, data_to_db)
            database.commit()
            flash('job list refreshed.')
        except Exception as e:
            flash("Problem inserting into db: " + str(e))
    else:
        flash('No files found.')
    return loadMain()

@app.route('/jobs', methods=['GET', 'POST'])
# @nocache
def jobs():
    mycursor= database.cursor()
    table = "jobs"
    global columns
    columns = [
        {'db':'id','dt':0,'formatter':''},
        {'db':'file_name','dt':1,'formatter':''},
        {'db':'status','dt':2,'formatter':status_button},
        {'db':'notes','dt':3,'formatter':notes_format}
    ]
    return json.dumps(run_queries(table,columns))

@app.route('/getdataajax', methods=['GET', 'POST'])
# @nocache
def getdataajax():
    mycursor= database.cursor()
    table = "candidates"
    global columns
    columns = [
        {'db':'pol_station_code','dt':0,'formatter':''},
        {'db':'id','dt':1,'formatter':''},
        {'db':'name','dt':2,'formatter':''},
        {'db':'sex','dt':3,'formatter':''},
        {'db':'age','dt':4,'formatter':''},
        {'db':'picture','dt':5,'formatter':photo_disp}
    ]
    return json.dumps(run_queries(table,columns))

@app.route('/progress')
def progress():
    def printPage():
        cursor = database.cursor()
        cursor.execute("SELECT `pol_code`, `pol_name`, `constituency`, `district`, `region` FROM `info` WHERE `pol_code` ='C061201A'")
        datainfo = cursor.fetchall()
        database.commit()
        cursor.execute("SELECT id, name, picture FROM `candidates`  WHERE `pol_station_code` = 'C061201A'")
        # SELECT * FROM `candidates` WHERE `pol_station_code` = 'C061201A' 
        data = cursor.fetchall()
        database.commit()
        # data = data[0:10]
        
        totalRecords= len(data)
        itemsNo=10
        dataLen=len(data)
        totalPages=(dataLen//itemsNo)
        if(dataLen%itemsNo!=0):
            totalPages+=1
        bookDetails =  {
            "title":"PARTY DATA COLLECTION BOOKLET",
            "region":str(datainfo[0][4]).upper(),
            "district":str(datainfo[0][3]).upper(),
            "constituency":str(datainfo[0][2]).upper(),
            "stationname":str(datainfo[0][1]).upper(),
            "stationno":str(datainfo[0][0]).upper()
            # `pol_code`, `pol_name`, `constituency`, `district`, `region`
        }
        can = canvas.Canvas(bookDetails["stationno"]+".pdf")
        PAGE_HEIGHT=defaultPageSize[1]; PAGE_WIDTH=defaultPageSize[0]
        path_to_pic = 'static/pics/'
        
        can.setProducer("Creator")
        can.setFont("Helvetica-Bold", 25)
        can.drawCentredString(PAGE_WIDTH/2, 780, str(bookDetails["title"]))
        # logo 
        # logo = ImageReader("logo.jpg")
        # can.drawImage(logo, (PAGE_WIDTH/2)-75, 550, width=150, height=150)
        # Region 
        can.setFont("Helvetica-Bold", 20)
        can.drawCentredString(PAGE_WIDTH/2, 460, "REGION : ")
        can.setFont("Helvetica", 20)
        can.drawCentredString(PAGE_WIDTH/2, 440, str(bookDetails["region"]))
        # District 
        can.setFont("Helvetica-Bold", 20)
        can.drawCentredString(PAGE_WIDTH/2, 400, "DISTRICT : ")
        can.setFont("Helvetica", 20)
        can.drawCentredString(PAGE_WIDTH/2, 380, str(bookDetails["district"]))
        # Constituency 
        can.setFont("Helvetica-Bold", 20)
        can.drawCentredString(PAGE_WIDTH/2, 340, "CONSTITUENCY : ")
        can.setFont("Helvetica", 20)
        can.drawCentredString(PAGE_WIDTH/2, 320, str(bookDetails["constituency"]))
        # Polling station name 
        can.setFont("Helvetica-Bold", 20)
        can.drawCentredString(PAGE_WIDTH/2, 280, "STATION NAME : ")
        can.setFont("Helvetica", 20)
        can.drawCentredString(PAGE_WIDTH/2, 260, str(bookDetails["stationname"]))
        # polling station code
        can.setFont("Helvetica-Bold", 20)
        can.drawCentredString(PAGE_WIDTH/2, 220, "STATION CODE : ")
        can.setFont("Helvetica", 20)
        can.drawCentredString(PAGE_WIDTH/2, 200, str(bookDetails["stationno"]))
        # Total records 
        can.setFont("Helvetica-Bold", 20)
        can.drawCentredString(PAGE_WIDTH/2, 160, "TOTAL RECORDS : "+str(totalRecords))
        # can.drawString( 20, 720, )
        can.showPage()
        # inner pages
        def drawCard(x, y, voter_id, name, picture):
            # can.roundRect(15, 625, 250, 125, 4, stroke=1, fill=0)
            passport = ImageReader(picture)
            can.drawImage(passport, x+199, y-108, width=80, height=100)
            can.drawString( x+3, y-2, "NAME: " + str(name))
            can.drawString( x+3, y-15, "VOTER ID: " + str(voter_id))
            can.drawString( x+3, y-30, "MS: __ EYOB: __ __ __ __")
            # can.setFillColorRGB(237, 243, 252)   
            can.drawString( x+3, y-45, "LOE: __, SEX: __ , RE: __")
            can.drawString( x+3, y-60, "OCC: __ __ __ __, PA: __")
            can.drawString( x+3, y-75, "LS: __ __ __,__ __ __,__ __ __")
            can.drawString( x+3, y-90,  "P1: __ __ __  __ __ __  __ __ __ __")
            can.drawString( x+3, y-105, "P2: __ __ __  __ __ __  __ __ __ __")
            can.drawString( x+3, y-120, "P3: __ __ __  __ __ __  __ __ __ __")
            # can.roundRect(x-5, y-160, wdth, height, 4, stroke=1, fill=0)    
            can.roundRect(x, y-125, 283, 140, 4, stroke=1, fill=0)
            # can.rect(x+22, y-32, 10, 10, fill=1)
            # can.rect(15, 625, 250, 125, 4, stroke=1, fill=0)

        for i in range(0, totalRecords, 10):
            if i < totalRecords:
                drawCard(10, 760, data[i][0], data[i][1], path_to_pic + str(data[i][2]))
            if i + 1 < totalRecords :
                drawCard(300, 760,  data[i+1][0], data[i+1][1], path_to_pic + str(data[i+1][2]))
            if i + 2 < totalRecords:
                drawCard(10, 615,  data[i+2][0], data[i+2][1], path_to_pic + str(data[i+2][2]))
            if i + 3 < totalRecords:
                drawCard(300, 615,  data[i+3][0], data[i+3][1], path_to_pic + str(data[i+3][2]))
            if i + 4 < totalRecords:
                drawCard(10, 470,  data[i+4][0], data[i+4][1], path_to_pic + str(data[i+4][2]))
            if i + 5 < totalRecords:
                drawCard(300, 470,  data[i+5][0], data[i+5][1], path_to_pic + str(data[i+5][2]))
            if i + 6 < totalRecords:
                drawCard(10, 325,  data[i+6][0], data[i+6][1], path_to_pic + str(data[i+6][2]))
            if i + 7 < totalRecords:
                drawCard(300, 325,  data[i+7][0], data[i+7][1], path_to_pic + str(data[i+7][2]))
            if i + 8 < totalRecords:
                drawCard(10, 180,  data[i+8][0], data[i+8][1], path_to_pic + str(data[i+8][2]))
            if i + 9 < totalRecords:
                drawCard(300, 180,  data[i+9][0], data[i+9][1], path_to_pic + str(data[i+9][2]))
            yield str(i) + " "
            # pgNumber = can.getPageNumber()
            can.line(0,780,PAGE_WIDTH,781)
            head = str(bookDetails["stationname"])+" - "+str(bookDetails["stationno"])
            can.drawString(20, 820, str(bookDetails["title"]).upper())
            can.drawString(20, 805, bookDetails["region"].upper()+", "+str(bookDetails["district"])+", "+str(bookDetails["constituency"])) 
            can.drawString(20, 790, head.upper())

            can.line(0,50,PAGE_WIDTH,51)
            can.drawString(500, 30, "Page "+str(can.getPageNumber()-1)+" of "+str(totalPages))
            can.showPage()
        can.save()
    return Response(printPage(), mimetype= 'text/plain')

@app.route('/processfiles')
def processfiles():
    cursor = database.cursor()
    cursor.execute("UPDATE jobs SET status = 0 WHERE `status` = 1")
    database.commit()
                  
    cursor.execute("SELECT * FROM `jobs` WHERE status=0")
    jobs = list(cursor.fetchall())
    database.commit()
    if len(jobs) >0:
        process.delay(jobs)    
        flash('( '+str(len(jobs))+' ) tasks loaded successfully !!!')
    else :
        flash('No new tasks found !!!')
    return loadMain()

@app.route('/purge')
# @celery.task
def purge_queue():
    from Celery import app
    app.control.purge()
    # from app.celery import app
                  
    # cursor.execute("SELECT * FROM `jobs` WHERE status=0")
    # jobs = list(cursor.fetchall())
    # database.commit()
    # if len(jobs) >0:
        # process.delay(jobs)    
        # flash('( '+str(len(jobs))+' ) tasks loaded successfully !!!')
    # else :
    # process.purge()
    # from app.celery import app
    # app.control.purge()
    cursor = database.cursor()
    cursor.execute("UPDATE jobs SET status = 0 WHERE `status` = 1")
    database.commit()
    flash('Queue purged !!!')
    return loadMain()

@app.route('/requestPDF')
def requestPDF():
    cursor = database.cursor()
    cursor.execute("SELECT * FROM info")
    data = cursor.fetchall()
    return render_template('datapage.html')

if __name__ == "__main__":    
    app.run(host='127.0.0.1', port=5000, debug=True)