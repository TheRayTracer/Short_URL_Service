import random
import string
import pyodbc
from flask import Flask, render_template, request, redirect, make_response

app = Flask(__name__, static_url_path="", static_folder="", template_folder="templates")
app.config.from_object(__name__)

DB_CONNECTION_STRING = "Driver={ODBC Driver 17 for SQL Server};Server=<server>;Port=1433;Database=<database>;Uid=<username>;Pwd=<password>"

@app.route("/")
def serve_index_page():
    return render_template("index.html")

@app.route("/create")
def create_shortservice_database():
    result = "Error"
    cnxn = None
    try:
        cnxn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = cnxn.cursor()
        cursor.execute("SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'uri'")
        if len(cursor.fetchall()) > 0:
            result = "Existing store found. New store not created."
        else:
            cursor.execute("CREATE TABLE [uri] ([id] BIGINT IDENTITY(1, 1), [long_uri] VARCHAR(1024) NOT NULL, [short_uri] VARCHAR(8) NOT NULL PRIMARY KEY, [visit_count] INT NOT NULL) ON [PRIMARY]")
            cnxn.commit()
            result = "Existing store not found. New store created."
    except Exception as e:
        pass
      # result = str(e)
    finally:
        if cnxn is not None:
            cnxn.close()
    return result

@app.route("/drop")
def drop_shortservice_database():
    result = "Error"
    cnxn = None
    try:
        cnxn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = cnxn.cursor()
        cursor.execute("DROP TABLE IF EXISTS [uri]")
        cnxn.commit()
        result = "Store deleted."
    except Exception as e:
        pass
      # result = str(e)
    finally:
        if cnxn is not None:
            cnxn.close()
    return result

@app.route("/short", methods = ["GET", "POST"])
def make_short_address():
    long = None
    if request.method == "GET":
        long = request.args.get("address").lower()
    elif request.method == "POST":
        long = request.form.get("address").lower()
    if long is not None:
        short = None
        cnxn = None
        if not long.startswith(("http://", "https://")):
            long = "http://" + long
        try:
            cnxn = pyodbc.connect(DB_CONNECTION_STRING)
            cursor = cnxn.cursor()
            short = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
            cursor = cursor.execute("SELECT * FROM [uri] WHERE [short_uri]=?", short)
            record = cursor.fetchone()
            while record is not None: # Not a bug, however this could loop forever outside this toy program.
                short = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                cursor = cursor.execute("SELECT * FROM [uri] WHERE [short_uri]=?", short)
                record = cursor.fetchone()
            if record is None:
                cursor.execute("INSERT INTO [uri] ([long_uri], [short_uri], [visit_count]) VALUES(?, ?, ?)", long, short, 0)
                cnxn.commit()
        except Exception as e:
            pass
          # result = str(e)
          # return result
        finally:
            if cnxn is not None:
                cnxn.close()
        return render_template("short.html", original=long, base=request.host_url, slug=short)
    return redirect("index.html", code=302)

@app.route("/go/<short>")
def fetch_short_address(short):
    short = str(short).lower()
    long = None
    cnxn = None
    try:
        cnxn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = cnxn.cursor()
        cursor = cursor.execute("SELECT [long_uri], [visit_count] FROM [uri] WHERE [short_uri]=?", short)
        record = cursor.fetchone()
        if record is not None:
            long = str(record[0])
            visit_cnt = int(record[1]) + 1
            cursor.execute("UPDATE [uri] SET [visit_count]=? WHERE [short_uri]=?", visit_cnt, short)
            cnxn.commit()
    except Exception as e:
        pass
      # result = str(e)
    finally:
        if cnxn is not None:
            cnxn.close()
    if long is None:
        return render_template("not_found.html", base=request.host_url, slug=short)
    return redirect(long, code=302)

@app.route("/visits/<short>")
def fetch_short_address_visits(short):
    short = str(short).lower()
    long = None
    visit_cnt = 0
    cnxn = None
    try:
        cnxn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = cnxn.cursor()
        cursor = cursor.execute("SELECT [long_uri], [visit_count] FROM [uri] WHERE [short_uri]=?", short)
        record = cursor.fetchone()
        if record is not None:
            long = str(record[0])
            visit_cnt = str(record[1])
    except Exception as e:
        pass
      # result = str(e)
    finally:
        if cnxn is not None:
            cnxn.close()
    if long is None:
        return render_template("not_found.html", base=request.host_url, slug=short)
    return render_template("visits.html", original=long, base=request.host_url, slug=short, visits=visit_cnt)

if __name__ == '__main__':
    import os
    HOST = os.environ.get('SERVER_HOST', 'localhost')
    PORT = 80
    try:
        PORT = int(os.environ.get('SERVER_PORT', '80'))
    except ValueError:
        pass
    app.run(HOST, PORT)
