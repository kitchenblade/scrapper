#!/usr/bin/python
from __future__ import print_function
from flask import Flask, render_template, request, redirect, url_for, flash, Response, send_file, send_from_directory
from flask_cors import CORS
import json, os, glob

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.rl_config import defaultPageSize
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from tasks import process, pdf_processor

from flask_debugtoolbar import DebugToolbarExtension
from pprint import pprint


import mysql.connector
from mysql.connector import errors

try:
    print('Connecting to Database...')
    with open('config.json') as data:
        config = json.load(data)
        db = mysql.connector.connect(
            pool_name = "scrapper_pool2",
            pool_size = 10,
            pool_reset_session = True,
            host = config['txtHost'],
            user = config['txtUser'],
            password = config['txtPass'],
            database = config['txtDB'],
            buffered=True
        )
except errors.PoolError as e:
    print('Error: connection not established {}'.format(e))
    db.close()

data_to_db = []
page_data    = []
job_state = False
global scripts
scripts = ""
global css
UPLOAD_PATH = 'static/pics'
ALLOWED_EXTENSIONS = set(['pdf', 'jpg'])

app = Flask(__name__)
app.config['UPLOAD_PATH'] = UPLOAD_PATH
app.config['SECRET_KEY'] = 'secret'

CORS(app)
def getConfig():
    global config
    with open('config.json') as json_data_file:
        try:
            config = json.load(json_data_file)
            return True
        except:
            return False

getConfig()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def loadMain():
    try:
        database = mysql.connector.connect(pool_name='scrapper_pool2')
    except errors.PoolError as e:
        print('Error: connection not established {}'.format(e))
        database.close()

    conf = getConfig()
    scripts="""
    <script type="text/javascript">
    $(document).ready(function() {                
            var table =  $('#jobs_table').DataTable( {
                'processing': true,
                'serverSide': true,
                'ajax': 'jobs',
                'type':'POST'
            });                            
            setInterval( function () {
                table.ajax.reload( null, false ); // user paging is not reset on reload
            }, 10000 );
        });
    </script>
        """
    # page_data.append(scripts)
    if conf:
        pass
        page_data.append(config)
    else :
        page_data.append([]) 

    cursor = database.cursor()
    cursor.execute("SELECT `pol_code` FROM `info`")
    pol_codes = cursor.fetchall()
    database.close()
    return render_template('jobs.html', page_data=page_data, pol_codes=pol_codes, scripts=scripts)

@app.route('/parser')
def allparserJobs():
    try:
        database = mysql.connector.connect(pool_name='scrapper_pool2')
    except errors.PoolError as e:
        print('Error: connection not established {}'.format(e))
        database.close()

    conf = getConfig()
    scripts="""<script type="text/javascript">
    $(document).ready(function() {                
            var table =  $('#jobs_table').DataTable( {
                'processing': true,
                'serverSide': true,
                'ajax': 'jobs',
                'type':'POST'
            });                            
            setInterval( function () {
                table.ajax.reload( null, false ); // user paging is not reset on reload
            }, 10000 );
            $("div.dataTables_length").append('<strong class="pull-right">PDF Processor Jobs.</strong>');
        });
    </script>
        """
    # page_data.append(scripts)
    if conf:
        pass
        page_data.append(config)
    else :
        page_data.append([]) 
    
    cursor = database.cursor()
    cursor.execute("SELECT `pol_code` FROM `info`")
    pol_codes =cursor.fetchall()
    database.close()
    return render_template('jobs.html', page_data=page_data, pol_codes=pol_codes, scripts=scripts)

@app.route('/generator')
def allgenJobs():
    try:
        database = mysql.connector.connect(pool_name='scrapper_pool2')
    except errors.PoolError as e:
        print('Error: connection not established {}'.format(e))
        database.close()

    conf = getConfig()
    scripts="""
    <script src="static/js/select2.full.min.js"></script>
    <script type="text/javascript">
    $(document).ready(function() {                
            var table =  $('#jobs_table').DataTable( {
                'processing': true,
                'serverSide': true,
                'ajax': 'jobs',
                'type':'POST'
            });                            
            setInterval( function () {
                table.ajax.reload( null, false ); // user paging is not reset on reload
            }, 10000 );
            $("div.dataTables_length").append('<strong class="pull-right">Booklet generator Jobs.</strong>');
            $("div.dataTables_filter").prepend('<button type="button" class="btn btn-primary" data-toggle="modal" data-target="#myModal">New jobs</button>');
             $.fn.select2.defaults.set("theme", "bootstrap");
            $('.js-example-basic-multiple').select2();
        });
        </script>
        """
    css = """
    <link href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.8/css/select2.min.css" rel="stylesheet" />

<--     <link href="static/css/select2.css" rel="stylesheet" /> -->
    
    <style type="text/css">
    </style>
    """
    # page_data.append(scripts)
    if conf:
        pass
        page_data.append(config)
    else :
        page_data.append([]) 

    cursor = database.cursor()
    cursor.execute("SELECT `pol_code` FROM `info`")
    pol_codes = cursor.fetchall()
    
    cursor.execute("SELECT `region` FROM `info` GROUP BY region")
    regions = cursor.fetchall()
    page_data.append(regions)

    cursor.execute("SELECT `district` FROM `info` GROUP BY `district`")
    districts = cursor.fetchall()
    page_data.append(districts)

    cursor.execute("SELECT `constituency` FROM `info` GROUP BY `constituency` ")
    constituencies = cursor.fetchall()
    page_data.append(constituencies)

    cursor.execute("SELECT `pol_code`, `pol_name` FROM `info`")
    polling_centers = cursor.fetchall()
    page_data.append(polling_centers)

    database.close()

    return render_template('genjobs.html', page_data=page_data, pol_codes=pol_codes, scripts=scripts)

@app.route('/dashboard')
def dashboard():
    css="""<style>
    .tile {
    width: 100%;
    display: inline-block;
    box-sizing: border-box;
    background: #fff;
    padding: 20px;
    margin-bottom: 30px;
    }

    .tile .title {
    margin-top: 0px;
    }
    .tile.purple, .tile.blue, .tile.red, .tile.orange, .tile.green, .titlelink {
    color: #fff;
    }
    .tile.purple {
    background: #5133ab;
    }
    .tile.purple:hover {
    background: #3e2784;
    }
    .tile.red {
    background: #ac193d;
    }
    .tile.red:hover {
    background: #7f132d;
    }
    .tile.green {
    background: #00a600;
    }
    .tile.green:hover {
    background: #007300;
    }
    .tile.blue {
    background: #2672ec;
    }
    .tile.blue:hover {
    background: #125acd;
    }
    .tile.orange {
    background: #dc572e;
    }
    .tile.orange:hover {
    background: #b8431f;
    }
    </style>
    """
    return render_page(template="dashboard.html",page_data=page_data, scripts=scripts, css=css)

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
    elif val==5:
        return '<button class="btn btn-warning" type="button" disabled><span class="glyphicon glyphicon-ok" aria-hidden="true"></span> Missing &nbsp;</button>'
    else:
        return '<button class="btn btn-danger" type="button" disabled><span class="glyphicon glyphicon-remove" aria-hidden="true"></span> Unknown</button>'

def notes_format(val):
    if val==0:
        return ''
    else:
        return val

def run_queries(table,columns):
    try:
        database = mysql.connector.connect(pool_name='scrapper_pool2')
    except errors.PoolError as e:
        print('Error: connection not established {}'.format(e))
        database.close()

    output = {}

    cursor = database.cursor()
    cursor.execute("SELECT COUNT(*) from "+table)
    (db_total,) = cursor.fetchone()

    _filter = filtering()
    cursor.execute("SELECT COUNT(*) FROM "+table+_filter)
    (rec_total,) = cursor.fetchone()
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
    cursor.execute(sql)    
    result_data = cursor.fetchall()

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
    database.close()
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

# =============== ROUTES ==========================
@app.route("/", methods=['GET', 'POST'])
def index():
    # dashboard
    return dashboard()

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
    try:
        database = mysql.connector.connect(pool_name='scrapper_pool2')
    except errors.PoolError as e:
        print('Error: connection not established {}'.format(e))
        database.close()

    sql = open('config.json')
    for sql in open('database.sql'):
        cursor = database.cursor()
        cursor.execute(sql)
        database.commit()
    filelist = glob.glob(os.path.join(UPLOAD_PATH, "*.jpg"))
    for f in filelist:
        os.remove(f)
    # database.cursor.execute('TRUNCATE TABLE jobs;')
    # database.commit()
    flash('Database cleared')
    scripts = """<script type="text/javascript">
    window.setTimeout(function () {
        $(".alert").fadeTo(500, 0).slideUp(500, function () {
            $(this).remove();
        });
    }, 5000);
    </script>
    """
    database.close()
    return loadMain()

@app.route('/getdata')
def getAllData():
    # cursor = database.cursor()
    # database.cursor.execute("SELECT * FROM candidates")
    # data = cursor.fetchall()
    return render_template('datapage.html')

@app.route('/refresh')
def refreshPath():
    try:
        database = mysql.connector.connect(pool_name='scrapper_pool2')
    except errors.PoolError as e:
        print('Error: connection not established {}'.format(e))
        database.close()

    cursor = database.cursor()

    with open('config.json') as data:
        config = json.load(data)
        path = config['txtPath']
        
        count = 0
        for filename in os.listdir(path):
            if  filename.endswith(('.pdf','PDF')):
                val = ('NULL', filename, '0', '')
                data_to_db.append(val)
                count += 1

        if count > 0:
            try:
                sql = "INSERT IGNORE INTO jobs (id, file_name, status, notes) VALUES (%s, %s, %s, %s)"
                cursor.executemany(sql, data_to_db)
                database.commit()
                flash('job list refreshed.')
            except Exception as e:
                flash("Problem inserting into db: " + str(e))
        else:
            flash('No files found.')
    database.close()
    return allparserJobs()

@app.route('/jobs', methods=['GET', 'POST'])
# @nocache
def jobs():
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


@app.route('/processfiles')
def processfiles():
    try:
        database = mysql.connector.connect(pool_name='scrapper_pool2')
    except errors.PoolError as e:
        print('Error: connection not established {}'.format(e))
        database.close()

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
    database.close()
    return allparserJobs()

@app.route('/retryfailed')
def retryfailed():
    try:
        database = mysql.connector.connect(pool_name='scrapper_pool2')
    except errors.PoolError as e:
        print('Error: connection not established {}'.format(e))
        database.close()
    # from celery import app
    # celery.control.purge()
    cursor = database.cursor()
    cursor.execute("UPDATE jobs SET status = 0 WHERE `status` = 2")
    database.commit()
                  
    cursor.execute("SELECT * FROM `jobs` WHERE status=0")
    jobs = list(cursor.fetchall())
    database.commit()
    if len(jobs) >0:
        process.delay(jobs)    
        flash('( '+str(len(jobs))+' ) tasks reset successfully !!!')
    else :
        flash('No failed tasks found !!!')
    database.close()
    return allparserJobs()

@app.route('/purge')
# @celery.task
def purge_queue():
    try:
        database = mysql.connector.connect(pool_name='scrapper_pool2')
    except errors.PoolError as e:
        print('Error: connection not established {}'.format(e))
        database.close()

    from Celery import app
    app.control.purge()
    # from app.celery import app
                  
    # database.cursor.execute("SELECT * FROM `jobs` WHERE status=0")
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
    database.close()
    return loadMain()

@app.route('/requestPDF')
def requestPDF():
    try:
        database = mysql.connector.connect(pool_name='scrapper_pool2')
    except errors.PoolError as e:
        print('Error: connection not established {}'.format(e))
        database.close()

    cursor = database.cursor()
    cursor.execute("SELECT * FROM info")
    data = cursor.fetchall()

    database.close()
    return render_template('datapage.html')

def render_page(template, page_data, scripts,css):
    conf = getConfig()
    if conf:
        pass
        page_data.append(config)
    else :
        page_data.append([]) 
    return render_template(template, page_data=page_data, scripts=scripts, css=css)


if __name__ == "__main__":    
    app.run(host='127.0.0.1', port=5000, debug=True)