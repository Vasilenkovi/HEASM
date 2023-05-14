from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import flash
from markupsafe import escape
import mysql.connector
import secrets
import querries

HOST = '127.0.0.1'
PORT = 3306
DATABASE = 'heasm'

querryBuilder = None
connection = None
cursor = None
lookUp = []
columnComments = []
selected = []
results = []

app = Flask(__name__, template_folder='HTML', static_folder='static')
app.secret_key = secrets.token_urlsafe(16)

def createLookUp(col_tab: list) -> dict:
    result = {}
    for col in col_tab:
        if col[0] not in result:
            result[col[0]] = [col[1]]
        else:
            result[col[0]].append(col[1])
    return result

def checkConnected() -> bool:
    if connection == None:
        flash("Invalid credentials")
        return False
    return True

def execute(query: str) -> list:
    global cursor
    if cursor != None:
        cursor.reset()
        cursor.execute(query)
        return cursor.fetchall() #Retrieving all results from cursor

@app.route("/", methods=['GET', 'POST'])
def main():
    return render_template('main.html')

@app.route("/auth", methods=['GET', 'POST'])
def auth():

    global querryBuilder, connection, cursor, lookUp, columnComments

    login = str(escape(request.form.get("login", "")))
    password = str(escape(request.form.get("password", "")))

    try:
        connection = mysql.connector.connect(user=login, password=password, host=HOST, port=PORT, database=DATABASE, use_pure=True)
        cursor = connection.cursor()
        lookUp = createLookUp(execute("SELECT DISTINCT column_name, table_name FROM information_schema.columns WHERE table_schema = DATABASE() and table_name != 'logs' ORDER BY column_name")) #LookUp table is generated once on connection and used to quickly disambiguate between columns of different tables with the same names
        columnComments = execute("SELECT DISTINCT column_name, column_comment FROM information_schema.columns WHERE table_schema = DATABASE() and table_name != 'logs' ORDER BY column_name") #Retrieving comments to columns to present the user
        querryBuilder = querries.QuerryBuilder(lookUp, columnComments)
        return redirect("/options", code=302)
    except:
        flash("Invalid credentials")
        return redirect("/", code=302)

@app.route("/options", methods=['GET', 'POST'])
def options():
    if checkConnected():
        return render_template('options.html')
    else:
        return redirect("/", code=302)

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    global connection

    if connection != None:
        connection.close()
        connection = None
    return redirect("/", code=302)

@app.route("/select", methods=['GET', 'POST'])
def select():
    global connection, cursor, lookUp, columnComments, selected
    
    if checkConnected():
        selected = request.form.getlist('filters')        
        return render_template('select.html', cols=columnComments, selected=selected)
    else:
        return redirect("/", code=302)

@app.route("/select_exec", methods=['GET', 'POST'])
def select_exec():
    global connection, cursor, lookUp, columnComments, selected, results

    if checkConnected():
        q = querryBuilder.buildQuerry(request.form, selected)
        if q != "":
            results = execute(q)
            return render_template('select.html', cols=columnComments, selected=selected, shown = request.form.getlist('select_filters'), results=results)
        else:
            return redirect("/select", code=302)
    else:
        return redirect("/", code=302)

@app.route("/edit", methods=['GET', 'POST'])
def edit():
    global connection, cursor, lookUp, columnComments, selected
    
    if checkConnected():       
        selected = request.form.getlist('filters') 
        return render_template('edit.html', cols=columnComments, selected=selected, ready = False)
    else:
        return redirect("/", code=302)
    
@app.route("/edit_retrieve", methods=['GET', 'POST'])
def edit_retrieve():
    global connection, cursor, lookUp, columnComments, selected, results

    if checkConnected():
        q = querryBuilder.editRetrieveQuerry(request.form, selected)
        if q != "":
            results = execute(q)
            return render_template('edit.html', cols=columnComments, selected=selected, ready = True ,results=results)
        else:
            return redirect("/edit", code=302)
    else:
        return redirect("/", code=302)

@app.route("/add", methods=['GET', 'POST'])
def add():
    global connection, cursor, lookUp, columnComments, selected
    
    if checkConnected():       
        return render_template('add.html')
    else:
        return redirect("/", code=302)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)