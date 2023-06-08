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
preserveSelect = False
lookUp = []
columnComments = []
logCols = []
tables = []
tableCols = []
tableComments = []
tableColsComments = []
keys = []
selected = []
results = []

app = Flask(__name__, template_folder='HTML_old', static_folder='static_old')
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
    tableComments = {}
    tableCommentsList = []
    columns = []
    for row in tableCols:
        row = list(row)
        t = row.pop(0)
        comment = row.pop(0)
        if t not in byTable:
            byTable[t] = [row]
        else:
            byTable[t].append(row)
        if comment not in tableComments:
            tableComments[t] = comment
    for key in byTable.keys():
        tables.append(key)
        columns.append(byTable[key])
        tableCommentsList.append(tableComments[key])
    return tables, columns, tableCommentsList

def seperateTableKeys(tableCols: list) -> tuple:
    byTable = {}
    tables = []
    columns = []
    for row in tableCols:
        row = list(row)
        t = row.pop(0)
        if t not in byTable:
            byTable[t] = row
        else:
            byTable[t].append(row[0])
    for key in byTable.keys():
        tables.append(key)
        columns.append(byTable[key])
    return columns

def countProducts() -> int:
    if cursor != None:
        cursor.reset()
        cursor.execute("SELECT MAX(PRODUCT_ID) FROM synthesis_product")
        i = cursor.fetchall()[0][0]
        i+=1
    return i

def checkConnected() -> bool:
    global connection
    if connection == None:
        execute("SELECT version()")
        flash("Соединиение потеряно")
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

    global querryBuilder, connection, cursor, lookUp, columnComments, logCols, tables, tableCols, keys, tableComments, tableColsComments

    login = str(escape(request.form.get("login", "")))
    password = str(escape(request.form.get("password", "")))

    try:
        connection = mysql.connector.connect(user=login, password=password, host=HOST, port=PORT, database=DATABASE, use_pure=True)
        cursor = connection.cursor(buffered=True)
        lookUp = createLookUp(execute("SELECT DISTINCT column_name, table_name FROM information_schema.columns WHERE table_schema = DATABASE() and table_name != 'logs' ORDER BY column_name")) #LookUp table is generated once on connection and used to quickly disambiguate between columns of different tables with the same names
        columnComments = execute("SELECT DISTINCT column_name, column_comment, data_type FROM information_schema.columns WHERE table_schema = DATABASE() and table_name != 'logs' ORDER BY column_name") #Retrieving comments to columns to present the user
        logCols = execute("SELECT DISTINCT column_name, column_comment FROM information_schema.columns WHERE table_schema = DATABASE() and table_name = 'logs' ORDER BY column_name") #Retrieving comments to columns to present the user
        tables, tableCols, tableComments = seperateTableCols(execute("SELECT DISTINCT information_schema.columns.table_name, table_comment, column_name, column_comment, data_type FROM information_schema.columns JOIN information_schema.tables ON information_schema.tables.table_name = information_schema.columns.table_name WHERE information_schema.columns.table_schema = DATABASE() and information_schema.columns.table_name != 'logs' ORDER BY information_schema.columns.table_name"))
        tableColsComments = list(map(lambda x: list(map(lambda y: y[1], x)), tableCols))
        keys = seperateTableKeys(execute("select distinct sta.table_name, sta.column_name from information_schema.tables as tab inner join information_schema.statistics as sta on sta.table_schema = tab.table_schema and sta.table_name = tab.table_name and sta.index_name = 'primary' where tab.table_schema = 'heasm' and sta.table_name != 'logs' order by sta.table_name"))
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
    global connection, cursor, lookUp, columnComments, selected, tables, tableComments, tableColsComments
    
    if checkConnected():
        selected = request.form.getlist('filters')        
        return render_template('select.html', cols=columnComments, selected=selected, tables = tables, tabCom = tableComments, tabCols = tableColsComments)
    else:
        return redirect("/", code=302)

@app.route("/select_exec", methods=['GET', 'POST'])
def select_exec():
    global connection, cursor, lookUp, columnComments, selected, results, tables, tableComments, tableColsComments

    if checkConnected():
        q = querryBuilder.buildQuerry(request.form, selected)
        if q != "":
            results = execute(q)
            return render_template('select.html', cols=columnComments, selected=querryBuilder.remaining, shown = request.form.getlist('select_filters'), results=results, tables = tables, tabCom = tableComments, tabCols = tableColsComments)
        else:
            return redirect("/select", code=302)
    else:
        return redirect("/", code=302)

@app.route("/edit", methods=['GET', 'POST'])
def edit():
    global connection, cursor, lookUp, columnComments, selected, tables, tableComments, tableColsComments
    
    if checkConnected():       
        selected = request.form.getlist('filters') 
        return render_template('edit.html', cols=columnComments, selected=selected, ready = False, tables = tables, tabCom = tableComments, tabCols = tableColsComments)
    else:
        return redirect("/", code=302)
    
@app.route("/edit_retrieve", methods=['GET', 'POST'])
def edit_retrieve():
    global connection, cursor, lookUp, columnComments, selected, results, tables, tableComments, tableColsComments

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
        for querry in q:
            try:
                execute(querry, commit=False)
            except mysql.connector.errors.IntegrityError as e:
                if e.errno == 1062:
                    newQuery = querryBuilder.updateToDelete(querry)
                    execute(newQuery, commit=False)
                elif e.errno == 1452:
                    q = querryBuilder.editExecuteParent(allVals)
                    for querry in q:
                        execute(querry, commit=False)
                else:
                    raise e
            commit()

    if checkConnected():
        q = querryBuilder.editRetrieveQuerry(request.form, selected)
        if q != "":
            results = execute(q)
            return render_template('edit.html', cols=columnComments, selected=querryBuilder.remaining, ready = True, results=results, tables = tables, tabCom = tableComments, tabCols = tableColsComments)
        else:
            return redirect("/edit", code=302)
    else:
        return redirect("/", code=302)

@app.route("/add_alt", methods=['GET', 'POST'])
def addAlt():
    global connection, cursor, lookUp, columnComments, tables, tableCols, selected, tableColsComments
    
    if checkConnected():       
        return render_template('add_alt.html', tables = tables, cols = tableCols, keys=keys, newId = countProducts(), tabCom = tableComments, tabCols = tableColsComments)
    else:
        return redirect("/", code=302)

@app.route("/add_execute_alt", methods=['POST'])
def addExecuteAlt():
    global connection, cursor, lookUp, columnComments, tables, tableCols, selected, tableColsComments
    
    if checkConnected():       
        q = querryBuilder.addQuerry(request.form)
        try:
            for query in q:
                execute(query, commit=False)
            flash("Успех", "message")
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
        return redirect("/add_alt", code=302)
    else:
        return redirect("/", code=302)
    
@app.route("/add", methods=['GET', 'POST'])
def add():
    global selected, preserveSelect, tables, tableComments, tableColsComments

    if checkConnected():     
        if not preserveSelect:
            selected = request.form.getlist('filters')
        else:
            preserveSelect = False
        return render_template('add.html', cols=columnComments, selected=selected, newId = countProducts(), tables = tables, tabCom = tableComments, tabCols = tableColsComments)
    else:
        return redirect("/", code=302)

@app.route("/add_execute", methods=['POST'])
def addExecute():
    global selected, preserveSelect, tableComments, tables, keys, columnComments, tableColsComments
    
    if checkConnected():       
        q, selected, inserted = querryBuilder.addQuerry(request.form)
        for query, table in zip(q, inserted):
            tableComment = tableComments[tables.index(table)]
            try:
                execute(query, commit=False) 
                flash("Успех: " + tableComment, "message")
                commit()
            except mysql.connector.errors.IntegrityError as e:
                if e.errno == 1452:
                    limit = querryBuilder.TABLE_PRIORITY.index(table)
                    toCheck = [querryBuilder.TABLE_PRIORITY[i] for i in range(limit)]
                    flash("Ключ не существует в родительской таблице. Проверьте записи в: " + ", ".join(toCheck), "error")
                elif e.errno == 1062:
                    flash("Ключ уже существует в: " + tableComment, "error")
                else:
                    raise e
            except mysql.connector.errors.ProgrammingError as e:
                comments = tableColsComments[tables.index(table)]
                if e.errno == 1054:
                    flash("Неверный тип данных для: " + tableComment + "; Проверьте: " + ", ".join(comments), "error")
                else:
                    raise e
            except mysql.connector.errors.DatabaseError as e:
                tableKeys = keys[tables.index(table)]
                keysComments = list(map(lambda x: columnComments[list(map(lambda y: y[0], columnComments)).index(x)][1], tableKeys))
                if e.errno == 1364:
                    flash("Недостаточно данных для: " + tableComment + "; Необходимы: " + ", ".join(keysComments), 'error')
                else:
                    raise e
        preserveSelect = True
        return redirect("/add", code=302)
    else:
        return redirect("/", code=302)
    
@app.route("/delete", methods=['GET', 'POST'])
def delete():
    global connection, cursor, lookUp, columnComments, selected, tables, tableComments, tableColsComments
    
    if checkConnected():       
        selected = request.form.getlist('filters') 
        return render_template('delete.html', cols=columnComments, selected=selected, keys=keys, ready = False, tables = tables, tabCom = tableComments, tabCols = tableColsComments)
    else:
        return redirect("/", code=302)
    
@app.route("/delete_retrieve", methods=['GET', 'POST'])
def delete_retrieve():
    global connection, cursor, lookUp, columnComments, selected, results, tables, tableComments, tableColsComments

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
            return render_template('delete.html', cols=columnComments, selected=querryBuilder.remaining, ready = True, results=results, tables = tables, tabCom = tableComments, tabCols = tableColsComments)
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
    
@app.route("/based", methods=['GET'])
def based():
    return "<h1>BASED</h1>"

@app.errorhandler(mysql.connector.errors.OperationalError)
def connectionLost(e):
    if e.errno == 2055:
        flash("Соединиение было потеряно")
        return redirect("/", code=302)
    else:
        raise e

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)