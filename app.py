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
from utils import Database

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

database = Database()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def loadMain():
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

    database.query("SELECT `pol_code` FROM `info`")
    pol_codes = database.cursor.fetchall()
    return render_template('jobs.html', page_data=page_data, pol_codes=pol_codes, scripts=scripts)

@app.route('/parser')
def allparserJobs():
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
    database.query("SELECT `pol_code` FROM `info`")
    pol_codes = database.cursor.fetchall()
    return render_template('jobs.html', page_data=page_data, pol_codes=pol_codes, scripts=scripts)

@app.route('/generator')
def allgenJobs():
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

    database.query("SELECT `pol_code` FROM `info`")
    pol_codes = database.cursor.fetchall()
    
    database.query("SELECT `region` FROM `info` GROUP BY region")
    regions = database.cursor.fetchall()
    page_data.append(regions)

    database.query("SELECT `district` FROM `info` GROUP BY `district`")
    districts = database.cursor.fetchall()
    page_data.append(districts)

    database.query("SELECT `constituency` FROM `info` GROUP BY `constituency` ")
    constituencies = database.cursor.fetchall()
    page_data.append(constituencies)

    database.query("SELECT `pol_code`, `pol_name` FROM `info`")
    polling_centers = database.cursor.fetchall()
    page_data.append(polling_centers)

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
    output = {}
    database.query("SELECT COUNT(*) from "+table)
    (db_total,) = database.cursor.fetchone()

    _filter = filtering()
    database.query("SELECT COUNT(*) FROM "+table+_filter)
    (rec_total,) = database.cursor.fetchone()
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
    database.query(sql)    
    result_data = database.cursor.fetchall()

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
    sql = open('config.json')
    for sql in open('database.sql'):
        database.query(sql)
        database.commit()
    filelist = glob.glob(os.path.join(UPLOAD_PATH, "*.jpg"))
    for f in filelist:
        os.remove(f)
    # database.query('TRUNCATE TABLE jobs;')
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
    # pprint.pprint(sql)
    return loadMain()

@app.route('/getdata')
def getAllData():
    # cursor = database.cursor()
    # database.query("SELECT * FROM candidates")
    # data = cursor.fetchall()
    return render_template('datapage.html')

@app.route('/refresh')
def refreshPath():
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
                database.cursor.executemany(sql, data_to_db)
                database.commit()
                flash('job list refreshed.')
            except Exception as e:
                flash("Problem inserting into db: " + str(e))
        else:
            flash('No files found.')
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

@app.route('/progress', methods=['GET', 'POST'])
def progress():
    pol_selected = request.form.get('pol_code_select')
    pdfmetrics.registerFont(TTFont('Vera', 'Vera.ttf'))
    pdfmetrics.registerFont(TTFont('VeraBd', 'VeraBd.ttf'))
    pdfmetrics.registerFont(TTFont('VeraIt', 'VeraIt.ttf'))
    pdfmetrics.registerFont(TTFont('VeraBI', 'VeraBI.ttf'))
    def printPage(pol_selected):
        polc = pol_selected
        database.query("SELECT `pol_code`, `pol_name`, `constituency`, `district`, `region` FROM `info` WHERE `pol_code` = %s", (str(polc),))
        datainfo = database.cursor.fetchall()
        database.commit()
        database.query("SELECT id, name, picture FROM `candidates`  WHERE `pol_station_code` = %s", (str(polc),))
        # SELECT * FROM `candidates` WHERE `pol_station_code` = 'C061201A' 
        data = database.cursor.fetchall()
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
        if not os.path.exists(path_to_pic):
            os.makedirs(path_to_pic)
        
        can.setProducer("Creator")
        can.setFont("VeraBd", 25)
        can.drawCentredString(PAGE_WIDTH/2, 780, str(bookDetails["title"]))
        # logo 
        logo = ImageReader("static/logo.jpg")
        can.drawImage(logo, (PAGE_WIDTH/2)-75, 550, width=150, height=150)
        # Region 
        can.setFont("VeraBd", 18)
        can.drawCentredString(PAGE_WIDTH/2, 460, "REGION : ")
        can.setFont("Vera", 18)
        can.drawCentredString(PAGE_WIDTH/2, 440, str(bookDetails["region"]))
        # District 
        can.setFont("VeraBd", 18)
        can.drawCentredString(PAGE_WIDTH/2, 400, "DISTRICT : ")
        can.setFont("Vera", 18)
        can.drawCentredString(PAGE_WIDTH/2, 380, str(bookDetails["district"]))
        # Constituency 
        can.setFont("VeraBd", 18)
        can.drawCentredString(PAGE_WIDTH/2, 340, "CONSTITUENCY : ")
        can.setFont("Vera", 18)
        can.drawCentredString(PAGE_WIDTH/2, 320, str(bookDetails["constituency"]))
        # Polling station name 
        can.setFont("VeraBd", 18)
        can.drawCentredString(PAGE_WIDTH/2, 280, "STATION NAME : ")
        can.setFont("Vera", 18)
        can.drawCentredString(PAGE_WIDTH/2, 260, str(bookDetails["stationname"]))
        # polling station code
        can.setFont("VeraBd", 18)
        can.drawCentredString(PAGE_WIDTH/2, 220, "STATION CODE : ")
        can.setFont("Vera", 18)
        can.drawCentredString(PAGE_WIDTH/2, 200, str(bookDetails["stationno"]))
        # Total records 
        can.setFont("VeraBd", 18)
        can.drawCentredString(PAGE_WIDTH/2, 160, "TOTAL RECORDS : "+str(totalRecords))
        # can.drawString( 18, 720, )
        can.showPage()
        # inner pages
        def drawCard(x, y, voter_id, name, picture):
            # can.roundRect(15, 625, 250, 125, 4, stroke=1, fill=0)
            can.setFont("Vera", 12)
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
            can.drawString(18, 820, str(bookDetails["title"]).upper())
            can.drawString(18, 805, bookDetails["region"].upper()+", "+str(bookDetails["district"])+", "+str(bookDetails["constituency"])) 
            can.drawString(18, 790, head.upper())

            can.line(0,50,PAGE_WIDTH,51)
            can.drawString(500, 30, "Page "+str(can.getPageNumber()-1)+" of "+str(totalPages))
            can.showPage()
        can.save()
    return Response(printPage(pol_selected), mimetype= 'text/plain')

@app.route('/processfiles')
def processfiles():
    database.query("UPDATE jobs SET status = 0 WHERE `status` = 1")
    database.commit()
                  
    database.query("SELECT * FROM `jobs` WHERE status=0")
    jobs = list(database.cursor.fetchall())
    database.commit()
    if len(jobs) >0:
        process.delay(jobs)    
        flash('( '+str(len(jobs))+' ) tasks loaded successfully !!!')
    else :
        flash('No new tasks found !!!')
    return allparserJobs()

@app.route('/retryfailed')
def retryfailed():
    # from celery import app
    # celery.control.purge()
    database.query("UPDATE jobs SET status = 0 WHERE `status` = 2")
    database.commit()
                  
    database.query("SELECT * FROM `jobs` WHERE status=0")
    jobs = list(database.cursor.fetchall())
    database.commit()
    if len(jobs) >0:
        process.delay(jobs)    
        flash('( '+str(len(jobs))+' ) tasks reset successfully !!!')
    else :
        flash('No failed tasks found !!!')
    return allparserJobs()

@app.route('/purge')
# @celery.task
def purge_queue():
    from Celery import app
    app.control.purge()
    # from app.celery import app
                  
    # database.query("SELECT * FROM `jobs` WHERE status=0")
    # jobs = list(cursor.fetchall())
    # database.commit()
    # if len(jobs) >0:
        # process.delay(jobs)    
        # flash('( '+str(len(jobs))+' ) tasks loaded successfully !!!')
    # else :
    # process.purge()
    # from app.celery import app
    # app.control.purge()
    database.query("UPDATE jobs SET status = 0 WHERE `status` = 1")
    database.commit()
    flash('Queue purged !!!')
    return loadMain()

@app.route('/requestPDF')
def requestPDF():
    database.query("SELECT * FROM info")
    data = database.cursor.fetchall()
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