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
logCols = []
tables = []
tableCols = []
keys = []
selected = []
results = []

app = Flask(__name__, template_folder='HTML', static_folder='static')
app.secret_key = secrets.token_urlsafe(16)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1000 * 1000

def createLookUp(col_tab: list) -> dict:
    result = {}
    for col in col_tab:
        if col[0] not in result:
            result[col[0]] = [col[1]]
        else:
            result[col[0]].append(col[1])
    return result

def seperateTableCols(tableCols: list) -> tuple:
    byTable = {}
    tables = []
    columns = []
    for row in tableCols:
        row = list(row)
        t = row.pop(0)
        if t not in byTable:
            byTable[t] = [row]
        else:
            byTable[t].append(row)
    for key in byTable.keys():
        tables.append(key)
        columns.append(byTable[key])
    return tables, columns

def creagteKeyList(keys: list) -> list:
    res = []
    for i in keys:
        res.append(i[0])
    return res

def countProducts() -> int:
    if cursor != None:
        cursor.reset()
        cursor.execute("SELECT MAX(PRODUCT_ID) FROM synthesis_product")
        i = cursor.fetchall()[0][0]
        i+=1
    return i

def checkConnected() -> bool:
    if connection == None:
        flash("Соединение потеряно")
        return False
    return True

def execute(querry: str, commit = True) -> list:
    global cursor, connection
    r = []
    if cursor != None:
        cursor.reset()
        cursor.execute(querry)
        try:
            r = cursor.fetchall() #Retrieving all results from cursor
        except mysql.connector.errors.InterfaceError:
            r = []
        if commit:
            connection.commit()
        return r
            
def commit() -> None:
    if connection != None:
        connection.commit()

def rollback() -> None:
    if connection != None:
        connection.rollback()

@app.route("/", methods=['GET', 'POST'])
def main():
    return render_template('main.html')

@app.route("/auth", methods=['GET', 'POST'])
def auth():

    global querryBuilder, connection, cursor, lookUp, columnComments, logCols, tables, tableCols, keys

    login = str(escape(request.form.get("login", "")))
    password = str(escape(request.form.get("password", "")))

    try:
        connection = mysql.connector.connect(user=login, password=password, host=HOST, port=PORT, database=DATABASE, use_pure=True)
        cursor = connection.cursor(buffered=True)
        lookUp = createLookUp(execute("SELECT DISTINCT column_name, table_name FROM information_schema.columns WHERE table_schema = DATABASE() and table_name != 'logs' ORDER BY column_name")) #LookUp table is generated once on connection and used to quickly disambiguate between columns of different tables with the same names
        columnComments = execute("SELECT DISTINCT column_name, column_comment, data_type FROM information_schema.columns WHERE table_schema = DATABASE() and table_name != 'logs' ORDER BY column_name") #Retrieving comments to columns to present the user
        logCols = execute("SELECT DISTINCT column_name, column_comment FROM information_schema.columns WHERE table_schema = DATABASE() and table_name = 'logs' ORDER BY column_name") #Retrieving comments to columns to present the user
        tables, tableCols = seperateTableCols(execute("SELECT DISTINCT table_name, column_name, column_comment, data_type FROM information_schema.columns WHERE table_schema = DATABASE() and table_name != 'logs' ORDER BY column_name"))
        keys = creagteKeyList(execute("select distinct sta.column_name from information_schema.tables as tab inner join information_schema.statistics as sta on sta.table_schema = tab.table_schema and sta.table_name = tab.table_name and sta.index_name = 'primary' where tab.table_schema = 'heasm' and sta.table_name != 'logs'"))
        querryBuilder = querries.QuerryBuilder(lookUp, columnComments, logCols, tables, tableCols)
        return redirect("/options", code=302)
    except mysql.connector.errors.Error as e:
        if e.errno == 1045:
            flash("Неверные данные")
        else:
            flash("Соединение потеряно")
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
            return render_template('select.html', cols=columnComments, selected=querryBuilder.remaining, shown = request.form.getlist('select_filters'), results=results)
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

    allVals = []
    q = ""
    for i in range(len(results)):
        newVals = []
        changed = False
        for j in range(len(results[i])):
            didChange = request.form.get("changed_" + str(i) + "_" + str(j))
            if didChange == "1":
                changed = True
            newVals.append(request.form.get(str(i) + "_" + str(j)))
        
        if changed:
            allVals.append([results[i], newVals])
    if len(allVals) > 0:
        q = querryBuilder.editExecute(allVals)
        try:
            for querry in q:
                execute(querry, commit=False)
        except mysql.connector.errors.IntegrityError:
            rollback()
            q = querryBuilder.editExecuteParent(allVals)
            for querry in q:
                execute(querry, commit=False)
        commit()

    if checkConnected():
        q = querryBuilder.editRetrieveQuerry(request.form, selected)
        if q != "":
            results = execute(q)
            return render_template('edit.html', cols=columnComments, selected=querryBuilder.remaining, ready = True, results=results)
        else:
            return redirect("/edit", code=302)
    else:
        return redirect("/", code=302)

@app.route("/add", methods=['GET', 'POST'])
def add():
    global connection, cursor, lookUp, columnComments, tables, tableCols, selected
    
    if checkConnected():       
        return render_template('add.html', tables = tables, cols = tableCols, keys=keys, newId = countProducts())
    else:
        return redirect("/", code=302)

@app.route("/add_execute", methods=['POST'])
def addExecute():
    global connection, cursor, lookUp, columnComments, tables, tableCols, selected
    
    if checkConnected():       
        q = querryBuilder.addQuerry(request.form)
        try:
            for query in q:
                execute(query, commit=False)
        except mysql.connector.errors.IntegrityError as e:
            rollback()
            if e.errno == 1452:
                flash("Ключ не существует в родительской таблице", "error")
            if e.errno == 1062:
                flash("Ключ уже существует", "error")
        except mysql.connector.errors.ProgrammingError:
            rollback()
            flash("Неверный тип данных", "error")
        commit()
        flash("Успех", "message")
        return redirect("/add", code=302)
    else:
        return redirect("/", code=302)
    
@app.route("/delete", methods=['GET', 'POST'])
def delete():
    global connection, cursor, lookUp, columnComments, selected
    
    if checkConnected():       
        selected = request.form.getlist('filters') 
        return render_template('delete.html', cols=columnComments, selected=selected, keys=keys, ready = False)
    else:
        return redirect("/", code=302)
    
@app.route("/delete_retrieve", methods=['GET', 'POST'])
def delete_retrieve():
    global connection, cursor, lookUp, columnComments, selected, results

    allVals = []
    q = ""
    toDelete = request.form.getlist("delete")
    for i in toDelete:
        allVals.append(results[int(i)])
    if len(allVals) > 0:
        q = querryBuilder.deleteExecute(allVals)
        try:
            for querry in q:
                execute(querry, commit=False)
        except mysql.connector.errors.IntegrityError:
            rollback()
            q = querryBuilder.deleteExecuteParent(allVals)
            for querry in q:
                execute(querry, commit=False)
        commit()

    if checkConnected():
        q = querryBuilder.editRetrieveQuerry(request.form, selected)
        if q != "":
            results = execute(q)
            return render_template('delete.html', cols=columnComments, selected=querryBuilder.remaining, ready = True, results=results)
        else:
            return redirect("/delete", code=302)
    else:
        return redirect("/", code=302)

@app.route("/logs", methods=['GET', 'POST'])
def selectLogs():
    global connection, cursor, lookUp, columnComments, selected
    
    if checkConnected():
        selected = request.form.getlist('filters')        
        return render_template('logs.html', cols=logCols, selected=selected)
    else:
        return redirect("/", code=302)

@app.route("/logs_exec", methods=['GET', 'POST'])
def selectLogs_exec():
    global connection, cursor, lookUp, columnComments, selected, results

    if checkConnected():
        q = querryBuilder.logQuerry(request.form, selected)
        if q != "":
            results = execute(q)
            return render_template('logs.html', cols=logCols, selected=querryBuilder.remaining, shown = request.form.getlist('select_filters'), results=results)
        else:
            return redirect("/select", code=302)
    else:
        return redirect("/", code=302)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)