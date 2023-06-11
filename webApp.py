from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import flash
from markupsafe import escape
import mysql.connector
import secrets
import querries

HOST = '127.0.0.1' #HOST for db connection. Currently localhost
PORT = 3306 #PORT for db connection. 3306 by default
DATABASE = 'heasm' #DB name on server
POOLED_CONNECTIONS = 5 #Amount of connection to pool for retrials

querryBuilder = None #Object to build queries
connectionPool = None #Pool of connections as a failsafe
connection = None #Current connection
cursor = None #DB cursor
preserveSelect = False #Boolean to preserve selected columns between queries in 'add' mode
lookUp = {} #lookUp dict for column-table disambiguation
columnComments = [] #List of columns with repective comments and data types 
logCols = [] #Columns for 'logs' table
tables = [] #DB tables, except 'logs' in specific order
tableCols = [] #Columns grouped by tables in 'tables' order
tableComments = [] #Table columns in 'tables' order
tableColsComments = [] #Column comments grouped by tables in 'tables' order
keys = [] #Key atributes by table
selected = [] #Selected filters in app
results = [] #Result of a query

config = {"user": "", "password": "", "host":HOST, "port":PORT, "database":DATABASE, "use_pure":True} #Connection configuration

app = Flask(__name__, template_folder='NEW_HTML', static_folder='static') #App initialization
app.secret_key = secrets.token_urlsafe(16) #Secret key preserves the session
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024 #Maximum length of GET/POST requests of 200mb 

#Creates lookUp dict from query result
def createLookUp(col_tab: list) -> dict:
    result = {}
    for col in col_tab:
        if col[0] not in result: #if column name wasn't added yet
            result[col[0]] = [col[1]] #add table to a list of tables which contain this column
        else:
            result[col[0]].append(col[1]) #add table to a list of tables which contain this column
    return result

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

#Create lists of: tables, table columns in order, and comments to tables
def seperateTableCols(tableCols: list) -> tuple:
    byTable = {}
    tables = []
    tableComments = {}
    tableCommentsList = []
    columns = []
    for row in tableCols: #Row is ('table name', 'table comment', 'column name', 'column comment', 'data type')
        row = list(row) #List cast from tuple since tuples are immutable
        t = row.pop(0) #Get table name and exclude from content
        comment = row.pop(0) #Get table comment and exclude from content
        if t not in byTable: #If table was not accounted for
            byTable[t] = [row] #Add column info to a list associated with table
        else:
            byTable[t].append(row) #Add column info to a list associated with table
        if comment not in tableComments: #Add table comments in strict order, following 'tables' order
            tableComments[t] = comment
    for key in byTable.keys(): #convert dicts to lists in a unified order
        tables.append(key)
        columns.append(byTable[key])
        tableCommentsList.append(tableComments[key])
    return tables, columns, tableCommentsList

#Groups key column names by tables in 'tables' order
def seperateTableKeys(tableCols: list) -> list:
    byTable = {}
    tables = []
    columns = []
    for row in tableCols: #row is ('table name', 'column name')
        row = list(row) #List cast from tuple since tuples are immutable
        t = row.pop(0) #Get table name and exclude from content
        if t not in byTable: #If table was not accounted for
            byTable[t] = row #Add key to table
        else:
            byTable[t].append(row[0]) #Add key to table
    for key in byTable.keys(): #convert dicts to lists in a unified order
        tables.append(key)
        columns.append(byTable[key])
    return columns

#Estimates the amount of records of synthesis products and returns a valid key for 'PRODUCT_ID'. May be beneficial to implement a sequence in db
def countProducts() -> int:
    if cursor != None: #if cursor is ready
        cursor.reset() #Clear old result and prepare for execution
        cursor.execute("SELECT MAX(PRODUCT_ID) FROM synthesis_product") #Execute query
        i = cursor.fetchall()[0][0] #Since returned value is [(int)]
        i+=1 #Pick available id
    return i

#Create a dict maping column comments (or column names) to datatypes. Used in parsing thr POST forms 
def typeByComment(tc: list) -> dict:
    res = {}
    for key, value in tc: #tc is a list of ('column comment', 'data type') or ('column name', 'data type')
        res[key] = value
    return res

#Check the status of connection. False is returned when authentication went wrong
def checkConnected() -> bool:
    global connection, connectionPool, cursor
    if connection == None: #If connection doesn't exist
        if connectionPool == None: #If connection pool doesn't exist
            flash("Пройдите авторизацию снова") #Something must have gone wrong in authentification
            return False
        connection = connectionPool.get_connection() #If pool is alright, get a new connection
        cursor = connection.cursor(buffered=True) #update cursor according to new connection
    return True

#Executes any query
def execute(querry: str, commit = True) -> list:
    global cursor, connection, connectionPool
    x = 0 #Attempts to execute against sudden timeouts or disconnects
    while x < POOLED_CONNECTIONS:
        try:
            r = []
            if cursor != None: #if cursor is ready
                cursor.reset() #Clear old result and prepare for execution
                cursor.execute("SELECT VERSION();") #Probing query to check connection status
                cursor.fetchall() #Retrieving all results from cursor
                cursor.reset() #Clear old result and prepare for execution
                cursor.execute(querry) #Execute query
                try:
                    r = cursor.fetchall() #Retrieving all results from cursor
                except mysql.connector.errors.InterfaceError as e: #if fetchall was used when no response is given by connector
                    r = []
                if commit:
                    cursor.execute("COMMIT") #End transaction with commit
                return reinterpretNull(r)
        except mysql.connector.errors.InterfaceError as e: #if execute failed
            if e.errno == 2013 or e.errno == 2055: #if lost connection during query or if conncetion closed unexpectedly
                connection = connectionPool.get_connection() #Get a new connection
                cursor = connection.cursor(buffered=True) #update cursor according to new connection
            else:
                raise e
        except mysql.connector.errors.DatabaseError as e:
            if e.errno == 4031: #if disconnected by the server because of inactivity
                connection = connectionPool.get_connection() #Get a new connection
                cursor = connection.cursor(buffered=True) #update cursor according to new connection
        x += 1 #Increment number of attempts
    raise mysql.connector.errors.InterfaceError(errno=2013) #If 3 attemts failed due to loss of connection
            
#End transaction with commit
def commit() -> None:
    if cursor != None:
        cursor.execute("COMMIT")

#End transaction with rollback
def rollback() -> None:
    if connection != None:
        connection.rollback()

#Root page with authentification form
@app.route("/", methods=['GET', 'POST'])
def main():
    return render_template('main.html')

#Authentification processing
@app.route("/auth", methods=['POST'])
def auth():
    global querryBuilder, connectionPool, connection, config, cursor, lookUp, columnComments, logCols, tables, tableCols, keys, tableComments, tableColsComments

    login = str(escape(request.form.get("login", ""))) #Safely parsing login info
    password = str(escape(request.form.get("password", ""))) #Safely parsing password info
 
    try:
        config["user"] = login #Add login to connection config
        config["password"] = password #Add password to connection config
        connectionPool = mysql.connector.pooling.MySQLConnectionPool(pool_name = "mypool", pool_size = POOLED_CONNECTIONS, **config) #Open connection pool with config
        connection = connectionPool.get_connection() #Get connection from pool
        cursor = connection.cursor(buffered=True) #Prepare cursor
        lookUp = createLookUp(execute("SELECT DISTINCT column_name, table_name FROM information_schema.columns WHERE table_schema = DATABASE() and table_name != 'logs' ORDER BY column_name")) #LookUp table is generated once on connection and used to quickly disambiguate between columns of different tables with the same names
        columnComments = execute("SELECT DISTINCT column_name, column_comment, data_type FROM information_schema.columns WHERE table_schema = DATABASE() and table_name != 'logs' ORDER BY column_name") #Retrieving comments to columns to present the user
        logCols = execute("SELECT DISTINCT column_name, column_comment FROM information_schema.columns WHERE table_schema = DATABASE() and table_name = 'logs' ORDER BY column_name") #Retrieving comments to columns to present the user
        tables, tableCols, tableComments = seperateTableCols(execute("SELECT DISTINCT information_schema.columns.table_name, table_comment, column_name, column_comment, data_type FROM information_schema.columns JOIN information_schema.tables ON information_schema.tables.table_name = information_schema.columns.table_name WHERE information_schema.columns.table_schema = DATABASE() and information_schema.columns.table_name != 'logs' ORDER BY information_schema.columns.table_name"))
        tableColsComments = list(map(lambda x: list(map(lambda y: y[1], x)), tableCols)) #Take only comments of columns grouped by tables
        keys = seperateTableKeys(execute("select distinct sta.table_name, sta.column_name from information_schema.tables as tab inner join information_schema.statistics as sta on sta.table_schema = tab.table_schema and sta.table_name = tab.table_name and sta.index_name = 'primary' where tab.table_schema = 'heasm' and sta.table_name != 'logs' order by sta.table_name"))
        dataTypeByComment = typeByComment(execute("SELECT DISTINCT column_comment, data_type FROM information_schema.columns WHERE information_schema.columns.table_schema = DATABASE() and information_schema.columns.table_name != 'logs'"))
        dataTypeByName = typeByComment(execute("SELECT DISTINCT column_name, data_type FROM information_schema.columns WHERE information_schema.columns.table_schema = DATABASE() and information_schema.columns.table_name != 'logs'"))
        querryBuilder = querries.QuerryBuilder(lookUp, columnComments, logCols, tables, tableCols, dataTypeByComment, dataTypeByName) #Initialize object for query building with dynamic db data
        return redirect("/options", code=302)
    except mysql.connector.errors.Error as e:
        if e.errno == 1045: #Connector access denied
            flash("Неверные данные")
        else:
            flash("Соединение потеряно")
        return redirect("/", code=302)

#Options to work with bd
@app.route("/options", methods=['GET', 'POST'])
def options():
    if checkConnected(): #Check for authentication
        return render_template('options.html')
    else:
        return redirect("/", code=302)

#Logout and close connection pool
@app.route("/logout", methods=['GET', 'POST'])
def logout():
    global connection, connectionPool

    if connection != None:
        connection.close()
        connection = None
        connectionPool = None
    return redirect("/", code=302)

#Main select page
@app.route("/select", methods=['GET', 'POST'])
def select():
    global connection, cursor, lookUp, columnComments, selected, tables, tableComments, tableColsComments
    
    if checkConnected(): #Check for authentication
        selected = list(map(lambda x: str(escape(x)), request.form.getlist('filters'))) #User checked filters to display    
        return render_template('select.html', cols=columnComments, selected=selected, tables = tables, tabCom = tableComments, tabCols = tableColsComments)
    else:
        return redirect("/", code=302)

#Select page with requested content
@app.route("/select_exec", methods=['GET', 'POST'])
def select_exec():
    global connection, cursor, lookUp, columnComments, selected, results, tables, tableComments, tableColsComments

    if checkConnected(): #Check for authentication
        q = querryBuilder.buildQuerry(request.form, selected) #Build a query with respect to selected filters and pass all form data
        if q != "": #If querry was built
            results = execute(q)
            return render_template('select.html', cols=columnComments, selected=querryBuilder.remaining, shown = list(map(lambda x: str(escape(x)), request.form.getlist('select_filters'))), results=results, tables = tables, tabCom = tableComments, tabCols = tableColsComments)
        else:
            return redirect("/select", code=302)
    else:
        return redirect("/", code=302)

#Main edit page
@app.route("/edit", methods=['GET', 'POST'])
def edit():
    global connection, cursor, lookUp, columnComments, selected, tables, tableComments, tableColsComments
    
    if checkConnected(): #Check for authentication    
        selected = list(map(lambda x: str(escape(x)), request.form.getlist('filters'))) #User checked filters to display 
        return render_template('edit.html', cols=columnComments, selected=selected, ready = False, tables = tables, tabCom = tableComments, tabCols = tableColsComments)
    else:
        return redirect("/", code=302)
    
#Edit page to display requested content and act on it
@app.route("/edit_retrieve", methods=['GET', 'POST'])
def edit_retrieve():
    global connection, cursor, lookUp, columnComments, selected, results, tables, tableComments, tableColsComments

    allVals = []
    q = ""
    for i in range(len(results)): #Check every returned row
        newVals = []
        changed = False
        for j in range(len(results[i])): #For every atribute
            didChange = str(escape(request.form.get("changed_" + str(i) + "_" + str(j)))) #Check form for user input
            if didChange == "1": #If user changed value
                changed = True
            newVals.append(str(escape(request.form.get(str(i) + "_" + str(j))))) #User intendent data for row
        
        if changed: #If one or more atributes in a row were changed
            allVals.append([results[i], newVals]) #Add old row content and user inputed row content
    if len(allVals) > 0: #If any changes were made
        try:
            q = querryBuilder.editExecute(allVals) #Build queries to update content
            for querry in q: #For every single query
                try:
                    execute(querry, commit=False)
                except ValueError as e:
                    rollback() #end transaction
                    flash("Неверный тип данных", "error")
                    break
                except mysql.connector.errors.IntegrityError as e:
                    if e.errno == 1062: #If new row value coincides with existing row
                        newQuery = querryBuilder.updateToDelete(querry) #Delete now unwanted row
                        execute(newQuery, commit=False)
                    elif e.errno == 1452: #If foreign key constraint fails
                        q = querryBuilder.editExecuteParent(allVals) #Execute changes on parent tables first
                        for querry in q:
                            execute(querry, commit=False)
                    else:
                        raise e
                commit() #end transaction
        except:
            rollback() #end transaction
            flash("Возникла серьёзная ошибка при обновлении", "error")

    if checkConnected(): #Check for authentication
        q = querryBuilder.editRetrieveQuerry(request.form, selected) #Build a query with respect to selected filters and pass all form data
        if q != "":
            results = execute(q)
            return render_template('edit.html', cols=columnComments, selected=querryBuilder.remaining, ready = True, results=results, tables = tables, tabCom = tableComments, tabCols = tableColsComments)
        else:
            return redirect("/edit", code=302)
    else:
        return redirect("/", code=302)

#Deprecated add method
@app.route("/add_alt", methods=['GET', 'POST'])
def addAlt():
    global connection, cursor, lookUp, columnComments, tables, tableCols, selected, tableColsComments
    
    if checkConnected(): #Check for authentication     
        return render_template('add_alt.html', tables = tables, cols = tableCols, keys=keys, newId = countProducts(), tabCom = tableComments, tabCols = tableColsComments)
    else:
        return redirect("/", code=302)

#Deprecated add page to act on user input
@app.route("/add_execute_alt", methods=['POST'])
def addExecuteAlt():
    global connection, cursor, lookUp, columnComments, tables, tableCols, selected, tableColsComments
    
    if checkConnected(): #Check for authentication      
        q = querryBuilder.addQuerry(request.form) #Build queries to add content
        try:
            for query in q: #For every query
                execute(query, commit=False)
            flash("Успех", "message") 
        except mysql.connector.errors.IntegrityError as e:
            rollback()
            if e.errno == 1452: #If foreign key constraint fails
                flash("Ключ не существует в родительской таблице", "error")
            if e.errno == 1062: #If primary key constraint fails
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
    global selected, preserveSelect, tables, tableComments, tableColsComments

    if checkConnected(): #Check for authentication    
        if not preserveSelect: #If user didn't preserve filters
            selected = list(map(lambda x: str(escape(x)), request.form.getlist('filters'))) #User checked filters to display
        else:
            preserveSelect = False
        return render_template('add.html', cols=columnComments, selected=selected, newId = countProducts(), tables = tables, tabCom = tableComments, tabCols = tableColsComments)
    else:
        return redirect("/", code=302)

#Add page to act on user input
@app.route("/add_execute", methods=['POST'])
def addExecute():
    global selected, preserveSelect, tableComments, tables, keys, columnComments, tableColsComments
    
    if checkConnected():       
        q, selected, inserted = querryBuilder.addQuerry(request.form) #Build queries to add content. Also returns selected columns and tables which are being added to
        for query, table in zip(q, inserted): #For add query, table inserted into
            tableComment = tableComments[tables.index(table)] #Get comment for a table
            try:
                execute(query, commit=False) 
                flash("Успех: " + tableComment, "message")
                commit()
            except mysql.connector.errors.IntegrityError as e:
                if e.errno == 1452: #If foreign key constraint fails
                    limit = querryBuilder.TABLE_PRIORITY.index(table) #Last table in priority, which could have caused failure
                    toCheck = [querryBuilder.TABLE_PRIORITY[i] for i in range(limit)] #All suspected tables
                    flash("Ключ не существует в родительской таблице. Проверьте записи в: " + ", ".join(toCheck), "error")
                elif e.errno == 1062: #If primary key constraint fails
                    flash("Ключ уже существует в: " + tableComment, "error")
                else:
                    raise e
            except mysql.connector.errors.ProgrammingError as e:
                comments = tableColsComments[tables.index(table)] #Gey column comments for all column of table
                if e.errno == 1054:
                    flash("Неверный тип данных для: " + tableComment + "; Проверьте: " + ", ".join(comments), "error")
                else:
                    raise e
            except mysql.connector.errors.DatabaseError as e:
                tableKeys = keys[tables.index(table)] #Get keys for a table
                keysComments = list(map(lambda x: columnComments[list(map(lambda y: y[0], columnComments)).index(x)][1], tableKeys)) #Calculate comments for key columns from columnComments
                if e.errno == 1364: #If couldn't insert due to absent primary key (NO DEFAULT VALUE FOR 'key' ATRIBUTE)
                    flash("Недостаточно данных для: " + tableComment + "; Необходимы: " + ", ".join(keysComments), 'error')
                else:
                    raise e
        preserveSelect = True #Preserve selected columns for more add calls
        return redirect("/add", code=302)
    else:
        return redirect("/", code=302)
    
#Main page for delete
@app.route("/delete", methods=['GET', 'POST'])
def delete():
    global connection, cursor, lookUp, columnComments, selected, tables, tableComments, tableColsComments
    
    if checkConnected(): #Check for authentication    
        selected = list(map(lambda x: str(escape(x)), request.form.getlist('filters'))) #User checked filters to display
        return render_template('delete.html', cols=columnComments, selected=selected, keys=keys, ready = False, tables = tables, tabCom = tableComments, tabCols = tableColsComments)
    else:
        return redirect("/", code=302)
    
#Delete page to display requested content and act on it
@app.route("/delete_retrieve", methods=['GET', 'POST'])
def delete_retrieve():
    global connection, cursor, lookUp, columnComments, selected, results, tables, tableComments, tableColsComments

    allVals = []
    q = ""
    toDelete = list(map(lambda x: str(escape(x)), request.form.getlist("delete"))) #Get rows checked for deletion
    toDeleteColumns = list(map(lambda x: str(escape(x)), request.form.getlist("delete_filters"))) #Get rows checked for deletion
    for i in toDelete: #For every row
        allVals.append(results[int(i)]) #Add corresponding entry to list
    if len(allVals) > 0: #If deletion list is not empty
        q = querryBuilder.deleteExecute(allVals, toDeleteColumns) #Build queries to delete
        try:
            for querry in q: #For every query
                execute(querry, commit=False)
        except mysql.connector.errors.IntegrityError:
            #If foreign key constraint fails
            rollback()
            q = querryBuilder.deleteExecuteParent(allVals) #delete from parent tables first
            for querry in q: #For every row
                execute(querry, commit=False)
        commit()

    if checkConnected():  #Check for authentication 
        q = querryBuilder.editRetrieveQuerry(request.form, selected)
        if q != "":
            results = execute(q)
            return render_template('delete.html', cols=columnComments, selected=querryBuilder.remaining, ready = True, results=results, tables = tables, tabCom = tableComments, tabCols = tableColsComments)
        else:
            return redirect("/delete", code=302)
    else:
        return redirect("/", code=302)

#Main page for logs
@app.route("/logs", methods=['GET', 'POST'])
def selectLogs():
    global connection, cursor, lookUp, columnComments, selected
    
    if checkConnected(): #Check for authentication 
        selected = list(map(lambda x: str(escape(x)), request.form.getlist('filters'))) #User checked filters to display      
        return render_template('logs.html', cols=logCols, selected=selected)
    else:
        return redirect("/", code=302)

#Logs page to display requested content
@app.route("/logs_exec", methods=['GET', 'POST'])
def selectLogs_exec():
    global connection, cursor, lookUp, columnComments, selected, results

    if checkConnected():  #Check for authentication 
        q = querryBuilder.logQuerry(request.form, selected) #Build a query with respect to selected filters and pass all form data
        if q != "":
            results = execute(q)
            return render_template('logs.html', cols=logCols, selected=querryBuilder.remaining, shown = list(map(lambda x: str(escape(x)), request.form.getlist('select_filters'))), results=results)
        else:
            return redirect("/select", code=302)
    else:
        return redirect("/", code=302)
    
#Debug page. Remove in deployment
@app.route("/based", methods=['GET'])
def based():
    return "<h1>BASED</h1>"

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

if __name__ == "__main__": #If not executed as module
    app.run(host="127.0.0.1", port=8080, debug=True) #Run app