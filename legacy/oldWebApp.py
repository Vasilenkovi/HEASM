from flask import Flask
from flask import session
from flask import request
from flask import render_template
from flask import redirect
from flask import flash
from markupsafe import escape
import mysql.connector
import secrets
import querries
#
HOST = '127.0.0.1' #HOST for db connection. Currently localho
PORT = 3306 #PORT for db connection. 3306 by default
DATABASE = 'heasm' #DB name on server
POOLED_CONNECTIONS = 5 #Amount of connection to pool for retr
#
querryBuilder = None #Object to build queries
connectionPool = None #Pool of connections as a failsafe
connection = None #Current connection
cursor = None #DB cursor
preserveSelect = False #Boolean to preserve selected columns 
lookUp = {} #lookUp dict for column-table disambiguation
columnComments = [] #List of columns with repective comments 
logCols = [] #Columns for 'logs' table
tables = [] #DB tables, except 'logs' in specific order
tableCols = [] #Columns grouped by tables in 'tables' order
tableComments = [] #Table columns in 'tables' order
tableColsComments = [] #Column comments grouped by tables in 
keys = [] #Key atributes by table
selected = [] #Selected filters in app
results = [] #Result of a query
#
config = {"user": "", "password": "", "host":HOST, "port":POR
#
app = Flask(__name__, template_folder='NEW_HTML', static_fold
app.secret_key = secrets.token_urlsafe(16) #Secret key preser
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024 #Maximum
#
#Creates lookUp dict from query result
def createLookUp(col_tab: list) -> dict:
    result = {}
    for col in col_tab:
        if col[0] not in result: #if column name wasn't added
            result[col[0]] = [col[1]] #add table to a list of
        else:
            result[col[0]].append(col[1]) #add table to a lis
    return result
#
def reinterpretNull(result: list) -> list:
    out = []
    for i in result:
        row = []
        for j in i:
            if j == None:
                row.append("")
            else:
                row.append(j)
        out.append(row)
    return out
#
#Create lists of: tables, table columns in order, and comment
def seperateTableCols(tableCols: list) -> tuple:
    byTable = {}
    tables = []
    tableComments = {}
    tableCommentsList = []
    columns = []
    for row in tableCols: #Row is ('table name', 'table comme
        row = list(row) #List cast from tuple since tuples ar
        t = row.pop(0) #Get table name and exclude from conte
        comment = row.pop(0) #Get table comment and exclude f
        if t not in byTable: #If table was not accounted for
            byTable[t] = [row] #Add column info to a list ass
        else:
            byTable[t].append(row) #Add column info to a list
        if comment not in tableComments: #Add table comments 
            tableComments[t] = comment
    for key in byTable.keys(): #convert dicts to lists in a u
        tables.append(key)
        columns.append(byTable[key])
        tableCommentsList.append(tableComments[key])
    return tables, columns, tableCommentsList
#
#Groups key column names by tables in 'tables' order
def seperateTableKeys(tableCols: list) -> list:
    byTable = {}
    tables = []
    columns = []
    for row in tableCols: #row is ('table name', 'column name
        row = list(row) #List cast from tuple since tuples ar
        t = row.pop(0) #Get table name and exclude from conte
        if t not in byTable: #If table was not accounted for
            byTable[t] = row #Add key to table
        else:
            byTable[t].append(row[0]) #Add key to table
    for key in byTable.keys(): #convert dicts to lists in a u
        tables.append(key)
        columns.append(byTable[key])
    return columns
#
#Estimates the amount of records of synthesis products and re
def countProducts() -> int:
    i = 0
    if cursor != None: #if cursor is ready
        cursor.reset() #Clear old result and prepare for exec
        cursor.execute("SELECT MAX(PRODUCT_ID) FROM synthesis
        i = cursor.fetchall()[0][0] #Since returned value is 
        i+=1 #Pick available id
    return i
#
#Create a dict maping column comments (or column names) to da
def typeByComment(tc: list) -> dict:
    res = {}
    for key, value in tc: #tc is a list of ('column comment',
        res[key] = value
    return res
#
#Check the status of connection. False is returned when authe
def checkConnected() -> bool:
    global connectionPool, connection, cursor
    login = session["user"]
    password = session["password"]
    if connectionPool == None or connection == None or cursor
        loginAndCreateData(login, password)
    return True
#
#Executes any query
def execute(querry: str, commit = True) -> list:
    global cursor, connection, connectionPool
    x = 0 #Attempts to execute against sudden timeouts or dis
    while x < POOLED_CONNECTIONS:
        try:
            r = []
            if cursor != None: #if cursor is ready
                cursor.reset() #Clear old result and prepare 
                cursor.execute("SELECT VERSION();") #Probing 
                cursor.fetchall() #Retrieving all results fro
                cursor.reset() #Clear old result and prepare 
                cursor.execute(querry) #Execute query
                try:
                    r = cursor.fetchall() #Retrieving all res
                except mysql.connector.errors.InterfaceError 
                    r = []
                if commit:
                    cursor.execute("COMMIT") #End transaction
                return reinterpretNull(r)
        except mysql.connector.errors.InterfaceError as e: #i
            if e.errno == 2013: #if lost connection during qu
                connection = connectionPool.get_connection() 
                cursor = connection.cursor(buffered=True) #up
            else:
                raise e
        except mysql.connector.errors.OperationalError as e: 
            if e.errno == 2055: #if conncetion closed unexpec
                connection = connectionPool.get_connection() 
                cursor = connection.cursor(buffered=True) #up
            else:
                raise e
        except mysql.connector.errors.DatabaseError as e:
            if e.errno == 4031: #if disconnected by the serve
                connection = connectionPool.get_connection() 
                cursor = connection.cursor(buffered=True) #up
            else:
                raise e
        x += 1 #Increment number of attempts
    raise mysql.connector.errors.InterfaceError(errno=2013) #
            
#End transaction with commit
def commit() -> None:
    if cursor != None:
        cursor.execute("COMMIT")
#
#End transaction with rollback
def rollback() -> None:
    if connection != None:
        connection.rollback()
#
def loginAndCreateData(login: str, password: str) -> None:
    global querryBuilder, connectionPool, connection, config,
#
    config["user"] = login #Add login to connection config
    config["password"] = password #Add password to connection
    connectionPool = mysql.connector.pooling.MySQLConnectionP
    connection = connectionPool.get_connection() #Get connect
    cursor = connection.cursor(buffered=True) #Prepare cursor
    lookUp = createLookUp(execute("SELECT DISTINCT column_nam
    columnComments = execute("SELECT DISTINCT column_name, co
    logCols = execute("SELECT DISTINCT column_name, column_co
    tables, tableCols, tableComments = seperateTableCols(exec
    tableColsComments = list(map(lambda x: list(map(lambda y:
    keys = seperateTableKeys(execute("select distinct sta.tab
    dataTypeByComment = typeByComment(execute("SELECT DISTINC
    dataTypeByName = typeByComment(execute("SELECT DISTINCT c
    querryBuilder = querries.QuerryBuilder(lookUp, columnComm
#
    session["user"] = login
    session["password"] = password
#
#Root page with authentification form
@app.route("/", methods=['GET', 'POST'])
def main():
    return render_template('main.html')
#
#Authentification processing
@app.route("/auth", methods=['POST'])
def auth():
    global querryBuilder, connectionPool, connection, config,
#
    login = str(escape(request.form.get("login", ""))) #Safel
    password = str(escape(request.form.get("password", ""))) 
 
    try:
        loginAndCreateData(login, password)
        return redirect("/options", code=302)
    except mysql.connector.errors.Error as e:
        if e.errno == 1045: #Connector access denied
            flash("Неверные данные")
        else:
            flash("Соединение потеряно")
        return redirect("/", code=302)
#
#Options to work with bd
@app.route("/options", methods=['GET', 'POST'])
def options():
    if checkConnected(): #Check for authentication
        return render_template('options.html')
    else:
        return redirect("/", code=302)
#
#Logout and close connection pool
@app.route("/logout", methods=['GET', 'POST'])
def logout():
    global connection, connectionPool
#
    if connection != None:
        connection.close()
        connection = None
        connectionPool = None
    return redirect("/", code=302)
#
#Main select page
@app.route("/select", methods=['GET', 'POST'])
def select():
    global connection, cursor, lookUp, columnComments, select
    
    if checkConnected(): #Check for authentication
        selected = list(map(lambda x: str(escape(x)), request
        return render_template('select.html', cols=columnComm
    else:
        return redirect("/", code=302)
#
#Select page with requested content
@app.route("/select_exec", methods=['GET', 'POST'])
def select_exec():
    global connection, cursor, lookUp, columnComments, select
#
    if checkConnected(): #Check for authentication
        q = querryBuilder.buildQuerry(request.form, selected)
        if q != "": #If querry was built
            results = execute(q)
            return render_template('select.html', cols=column
        else:
            return redirect("/select", code=302)
    else:
        return redirect("/", code=302)
#
#Main edit page
@app.route("/edit", methods=['GET', 'POST'])
def edit():
    global connection, cursor, lookUp, columnComments, select
    
    if checkConnected(): #Check for authentication    
        selected = list(map(lambda x: str(escape(x)), request
        return render_template('edit.html', cols=columnCommen
    else:
        return redirect("/", code=302)
    
#Edit page to display requested content and act on it
@app.route("/edit_retrieve", methods=['GET', 'POST'])
def edit_retrieve():
    global connection, cursor, lookUp, columnComments, select
#
    allVals = []
    q = ""
    for i in range(len(results)): #Check every returned row
        newVals = []
        changed = False
        for j in range(len(results[i])): #For every atribute
            didChange = str(escape(request.form.get("changed_
            if didChange == "1": #If user changed value
                changed = True
            newVals.append(str(escape(request.form.get(str(i)
        
        if changed: #If one or more atributes in a row were c
            allVals.append([results[i], newVals]) #Add old ro
    if len(allVals) > 0: #If any changes were made
        try:
            q = querryBuilder.editExecute(allVals) #Build que
            for querry in q: #For every single query
                try:
                    execute(querry, commit=False)
                except ValueError as e:
                    rollback() #end transaction
                    flash("Неверный тип данных", "error")
                    break
                except mysql.connector.errors.IntegrityError 
                    if e.errno == 1062: #If new row value coi
                        newQuery = querryBuilder.updateToDele
                        execute(newQuery, commit=False)
                    elif e.errno == 1452: #If foreign key con
                        q = querryBuilder.editExecuteParent(a
                        for querry in q:
                            execute(querry, commit=False)
                    else:
                        raise e
                commit() #end transaction
        except:
            rollback() #end transaction
            flash("Возникла серьёзная ошибка при обновлении",
#
    if checkConnected(): #Check for authentication
        q = querryBuilder.editRetrieveQuerry(request.form, se
        if q != "":
            results = execute(q)
            return render_template('edit.html', cols=columnCo
        else:
            return redirect("/edit", code=302)
    else:
        return redirect("/", code=302)
#
#Deprecated add method
@app.route("/add_alt", methods=['GET', 'POST'])
def addAlt():
    global connection, cursor, lookUp, columnComments, tables
    
    if checkConnected(): #Check for authentication     
        return render_template('add_alt.html', tables = table
    else:
        return redirect("/", code=302)
#
#Deprecated add page to act on user input
@app.route("/add_execute_alt", methods=['POST'])
def addExecuteAlt():
    global connection, cursor, lookUp, columnComments, tables
    
    if checkConnected(): #Check for authentication      
        q = querryBuilder.addQuerry(request.form) #Build quer
        try:
            for query in q: #For every query
                execute(query, commit=False)
            flash("Успех", "message") 
        except mysql.connector.errors.IntegrityError as e:
            rollback()
            if e.errno == 1452: #If foreign key constraint fa
                flash("Ключ не существует в родительской табл
            if e.errno == 1062: #If primary key constraint fa
                flash("Ключ уже существует", "error")
        except mysql.connector.errors.ProgrammingError:
            #If data can't be cast to expected type
            rollback()
            flash("Неверный тип данных", "error")
        commit()
        return redirect("/add_alt", code=302)
    else:
        return redirect("/", code=302)
    
#Main page add page
@app.route("/add", methods=['GET', 'POST'])
def add():
    global selected, preserveSelect, tables, tableComments, t
#
    if checkConnected(): #Check for authentication    
        if not preserveSelect: #If user didn't preserve filte
            selected = list(map(lambda x: str(escape(x)), req
        else:
            preserveSelect = False
        return render_template('add.html', cols=columnComment
    else:
        return redirect("/", code=302)
#
#Add page to act on user input
@app.route("/add_execute", methods=['POST'])
def addExecute():
    global selected, preserveSelect, tableComments, tables, k
    
    if checkConnected():       
        q, selected, inserted = querryBuilder.addQuerry(reque
        for query, table in zip(q, inserted): #For add query,
            tableComment = tableComments[tables.index(table)]
            try:
                execute(query, commit=False) 
                flash("Успех: " + tableComment, "message")
                commit()
            except mysql.connector.errors.IntegrityError as e
                if e.errno == 1452: #If foreign key constrain
                    limit = querryBuilder.TABLE_PRIORITY.inde
                    toCheck = [querryBuilder.TABLE_PRIORITY[i
                    flash("Ключ не существует в родительской 
                elif e.errno == 1062: #If primary key constra
                    flash("Ключ уже существует в: " + tableCo
                else:
                    raise e
            except mysql.connector.errors.ProgrammingError as
                comments = tableColsComments[tables.index(tab
                if e.errno == 1054:
                    flash("Неверный тип данных для: " + table
                else:
                    raise e
            except mysql.connector.errors.DatabaseError as e:
                tableKeys = keys[tables.index(table)] #Get ke
                keysComments = list(map(lambda x: columnComme
                if e.errno == 1364: #If couldn't insert due t
                    flash("Недостаточно данных для: " + table
                else:
                    raise e
        preserveSelect = True #Preserve selected columns for 
        return redirect("/add", code=302)
    else:
        return redirect("/", code=302)
    
#Main page for delete
@app.route("/delete", methods=['GET', 'POST'])
def delete():
    global connection, cursor, lookUp, columnComments, select
    
    if checkConnected(): #Check for authentication    
        selected = list(map(lambda x: str(escape(x)), request
        return render_template('delete.html', cols=columnComm
    else:
        return redirect("/", code=302)
    
#Delete page to display requested content and act on it
@app.route("/delete_retrieve", methods=['GET', 'POST'])
def delete_retrieve():
    global connection, cursor, lookUp, columnComments, select
#
    allVals = []
    q = ""
    toDelete = list(map(lambda x: str(escape(x)), request.for
    toDeleteColumns = list(map(lambda x: str(escape(x)), requ
    for i in toDelete: #For every row
        allVals.append(results[int(i)]) #Add corresponding en
    if len(allVals) > 0: #If deletion list is not empty
        q = querryBuilder.deleteExecute(allVals, toDeleteColu
        try:
            for querry in q: #For every query
                execute(querry, commit=False)
        except mysql.connector.errors.IntegrityError:
            #If foreign key constraint fails
            rollback()
            q = querryBuilder.deleteExecuteParent(allVals) #d
            for querry in q: #For every row
                execute(querry, commit=False)
        commit()
#
    if checkConnected():  #Check for authentication 
        q = querryBuilder.editRetrieveQuerry(request.form, se
        if q != "":
            results = execute(q)
            return render_template('delete.html', cols=column
        else:
            return redirect("/delete", code=302)
    else:
        return redirect("/", code=302)
#
#Main page for logs
@app.route("/logs", methods=['GET', 'POST'])
def selectLogs():
    global connection, cursor, lookUp, columnComments, select
    
    if checkConnected(): #Check for authentication 
        selected = list(map(lambda x: str(escape(x)), request
        return render_template('logs.html', cols=logCols, sel
    else:
        return redirect("/", code=302)
#
#Logs page to display requested content
@app.route("/logs_exec", methods=['GET', 'POST'])
def selectLogs_exec():
    global connection, cursor, lookUp, columnComments, select
#
    if checkConnected():  #Check for authentication 
        q = querryBuilder.logQuerry(request.form, selected) #
        if q != "":
            results = execute(q)
            return render_template('logs.html', cols=logCols,
        else:
            return redirect("/select", code=302)
    else:
        return redirect("/", code=302)
    
#Debug page. Remove in deployment
@app.route("/based", methods=['GET'])
def based():
    return "<h1>BASED</h1>"
#
@app.errorhandler(mysql.connector.errors.OperationalError)
def connectionLost(e):
    if e.errno == 2055: #IF conncetion closed unexpectedly
        flash("Соединиение было потеряно")
        return redirect("/", code=302)
    else:
        raise e
    
@app.errorhandler(mysql.connector.errors.InterfaceError)
def connectionLost(e):
    if e.errno == 2013: #IF conncetion closed during query
        flash("Соединиение было потеряно во время запроса")
        return redirect("/", code=302)
    else:
        raise e
    
@app.errorhandler(mysql.connector.errors.ProgrammingError)
def connectionLost(e): 
    if e.errno == 1045: #IF user if not authorized
        flash("Неверные данные авторизации")
        return redirect("/", code=302)
    else:
        raise e
#
@app.errorhandler(mysql.connector.errors.DatabaseError)
def connectionLost(e): 
    return "<h1>BASED</h1><br><p>" + e.args + "</p>" + "<br><
#
if __name__ == "__main__": #If not executed as module
    app.run(host="127.0.0.1", port=8080, debug=True) #Run app