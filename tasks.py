from celery import Celery
import os, json, PyPDF2, os.path, re, time, sys, glob
from utils import Database
from werkzeug.utils import secure_filename
from multiprocessing import Pool
from werkzeug.datastructures import FileStorage
import requests, threading, time, pprint, string
from utils import Database
# from pprint import pprint
celery = Celery('tasks', broker='pyamqp://guest@localhost//')
celery.conf.task_acks_late= True
celery.conf.worker_prefetch_multiplier = 1

database = Database()

UPLOAD_PATH = 'static/pics'
ALLOWED_EXTENSIONS = set(['pdf', 'jpg'])

# @celery.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 2})
# @celery.task(bind=True, autoretry_for=(Exception,), exponential_backoff=2, retry_kwargs={'max_retries': 5}, retry_jitter=False)
@celery.task()
def pdf_processor(job):
    with open('config.json') as json_data_file:
        config = json.load(json_data_file)
        src_path = os.path.join(config['txtPath'], job[1])
        exists = os.path.isfile(src_path)

        # check if job is being worked on or finished
        sql = """SELECT * FROM jobs WHERE id = '%s'"""
        database.query(sql, (job[0],))
        record = database.cursor.fetchone()

        if int(record[2]) == 2 :
            # cannot work
            print("Job in progress !!!")
            return False
        elif int(record[2]) == 3 :
            # cannot work
            print("Job already done !!!")
            return True
        elif exists:        
            data = (2,job[1])
            sql = """UPDATE jobs SET status = %s WHERE `file_name` =%s"""
            database.query(sql,data)
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
            database.query(sql, val)
            database.commit()

            sql = "INSERT IGNORE INTO candidates (pol_station_code, id, name, sex, age, picture) VALUES (%s, %s, %s, %s, %s, %s)"
            database.cursor.executemany(sql, processed_page_to_db)
            database.commit()

            data=(3,job[1])
            sql = """UPDATE jobs SET status = %s WHERE `file_name` =%s"""
            database.query(sql,data)
            database.commit()

            pdfFileObj.close()
            dst = os.path.join(dst_path, job[1])
            os.rename(src_path, dst) 
        
            print("\n Process Finished.")
            return True
        else:
            # Keep presets file missing
            data=(5,job[1])
            sql = """UPDATE jobs SET status = %s WHERE `file_name` = %s"""
            database.query(sql,data)
            database.commit()
            print("\n File missing.")
            return False

@celery.task
def process(jobs):   
    if len(jobs)==0:
        print("\n No jobs left to process.")
    else:
        for job in jobs:
            data=(1,job[1])
            # sql = """UPDATE `jobs` SET `status` = %s WHERE `file_name` = %s """
            sql = "UPDATE `jobs` SET `status` = '%s' WHERE `jobs`.`file_name` = %s "
            database.query(sql,data)
            database.commit()
            # task = pdf_processor.s(job).delay()            
            task = pdf_processor.delay(job)
            print(f'Started task: {task}')

@celery.task
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