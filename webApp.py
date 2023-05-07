from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import flash
from markupsafe import escape
import mysql.connector
import secrets

HOST = '127.0.0.1'
PORT = 3306
DATABASE = 'heasm'

TABLES = {"bib_source": 0, "bibliography": 1, "countries": 2, "ingredients": 3, "key_word": 4, "measurements": 5, "synthesis_parameter": 6, "synthesis_product": 7}
TABLES_INVERSE = ["bib_source", "bibliography", "countries", "ingredients", "key_word", "measurements", "synthesis_parameter", "synthesis_product"]

TABLES_ADJACENCY = [
    [None, 'JOURNAL', None, None, None, None, None, None],
    ['JOURNAL', None, 'DOI', None, 'DOI', None, None, 'DOI'],
    [None, 'DOI', None, None, None, None, None, None],
    [None, None, None, None, None, None, None, 'PRODUCT_ID'],
    [None, 'DOI', None, None, None, None, None, None],
    [None, None, None, None, None, None, None, 'PRODUCT_ID'],
    [None, None, None, None, None, None, None, 'PRODUCT_ID'],
    [None, 'DOI', None, 'PRODUCT_ID', None, 'PRODUCT_ID', 'PRODUCT_ID', None]
]

connection = None
cursor = None
lookUp = []
columnComments = []
selected = []
results = []

app = Flask(__name__, template_folder='HTML', static_folder='static')
app.secret_key = secrets.token_urlsafe(16)

def leastTables(col1, col2) -> list:
    for i in lookUp[col1]:
        for j in lookUp[col2]:
            if i == j:
                return [i]
    #Else BFS
    table1 = lookUp[col1][0]
    table2 = lookUp[col2][0]
    queue = []
    queue.append(TABLES[table1])
    visited = [False for i in range(8)]
    visited[TABLES[table1]] = True
    prev = [-1 for i in range(8)]

    while len(queue) > 0:
        v = queue[0]
        queue.pop(0)
        for i in range(8):
            if TABLES_ADJACENCY[v][i] != None and not visited[i]:
                queue.append(i)
                visited[i] = True
                prev[i] = v
                if i == TABLES[table2]:
                    queue.clear()
                    break

    out = []
    current = table2
    out.append(current)
    while current != table1:
        current = TABLES_INVERSE[prev[TABLES[current]]]
        out.append(current)
    
    return out

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

def buildQuerry(requestArgs) -> str:
    global lookUp, columnComments, selected
    selected_filters = requestArgs.getlist('select_filters')
    where_filters = requestArgs.getlist('where_filters')

    if len(selected_filters) == 0:
        return ""

    querry = "SELECT DISTINCT " #base of querry
    preselect = []
    select = [] #all columns to select
    where = [] #all columns to include in "WHERE" statement
    whereSymbol = [] #all "WHERE" comparison operators
    whereCondition = [] #all "WHERE" conditions
    sort = 0
    sortCol = ""
    tables = []

    tempSelected = []
    for i in selected:
        if i in selected_filters or i in where_filters:
            tempSelected.append(i)
    selected = tempSelected

    for i in selected_filters:
        for j in range(len(columnComments)):
            if columnComments[j][1].decode('utf-8', 'ignore') == i:
                preselect.append(columnComments[j][0]) 

    if len(preselect) > 1:
        for i1 in range(len(preselect)-1):
            for i2 in range(i1+1, len(preselect)):
                tables2 = leastTables(preselect[i1], preselect[i2])
                for t in tables2:
                    if t not in tables:
                        tables.append(t)
    else:
        tables.append(lookUp[preselect[0]][0])

    for col in preselect:
        for table in lookUp[col]:
            if table in tables:
                select.append(table + "." + col) #if checked as "SELECT" add to select with table disambiguation from lookup
    
    for i in where_filters:
        for j in range(len(columnComments)):
            if columnComments[j][1].decode('utf-8', 'ignore') == i:
                for table in lookUp[columnComments[j][0]]:
                    if table in tables:
                        where.append(table + "." + columnComments[j][0]) #if checked as "WHERE" add to select with table disambiguation from lookup
    
    for i in columnComments:
        numericAllowed = True

        t = requestArgs.get('comp_clause_' + i[1].decode('utf-8', 'ignore'))
        if t != None and i[1].decode('utf-8', 'ignore') in where_filters:
            try:
                temp = str(float(t)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                whereCondition.append(temp)
            except:
                temp = "'" + t + "'" #if a string was supplied as condition, comparison operators, aside from '=', have no meaning and are defaulted to '='. Also quotation marks are provided
                numericAllowed = False
                whereCondition.append(temp)

        t = requestArgs.get('comp_op_' + i[1].decode('utf-8', 'ignore'))
        if t != None and i[1].decode('utf-8', 'ignore') in where_filters:
            if numericAllowed and t in ('=', '>', '<', '>=', '<='):
                whereSymbol.append(t)
            else:
                whereSymbol.append("=")

        t = requestArgs.get('rad_' + i[1].decode('utf-8', 'ignore'))
        if t != None:
            if t == "no":
                sort = 0
            elif t == "asc":
                sort = 1
                sortCol = i[0]
            else:
                sort = 2
                sortCol = i[0]
    
    querry += ",".join(select)
    querry += " FROM "
    querry += tables[0] + " "
    for i in range(1, len(tables)):
        left = TABLES[tables[i]]
        right = TABLES[tables[i-1]]
        joinCol = TABLES_ADJACENCY[left][right]
        if joinCol != None:
            querry += "INNER JOIN " + TABLES_INVERSE[left] + " ON " + TABLES_INVERSE[right] + "." + joinCol + " = " + TABLES_INVERSE[left] + "." + joinCol + " "
        else:
            for j in range(len(tables)):
                left = TABLES[tables[i]]
                right = TABLES[tables[j]]
                joinCol = TABLES_ADJACENCY[left][right]
                if joinCol != None:
                    querry += "INNER JOIN " + TABLES_INVERSE[left] + " ON " + TABLES_INVERSE[right] + "." + joinCol + " = " + TABLES_INVERSE[left] + "." + joinCol + " "

    if len(where) > 0: #if any filters were checked for "WHERE"
            querry += " WHERE "
            for w in range(len(where)):
                querry += where[w] + whereSymbol[w] + whereCondition[w] + " AND "
            querry = querry[:-5] + "\n" #last boolean logic operator is removed, because it has no right hand side condition. Currently only 'AND' is supported

    if sort == 1:
        querry += "ORDER BY " + sortCol + " ASC" #if ascending sorting was chosen 
    elif sort == 2:
        querry += "ORDER BY " + sortCol + " DESC" #if descending sorting was chosen

    return querry

@app.route("/")
def main():
    return render_template('main.html')

@app.route("/auth")
def auth():

    global connection, cursor, lookUp, columnComments

    login = str(escape(request.args.get("login", "")))
    password = str(escape(request.args.get("password", "")))

    try:
        connection = mysql.connector.connect(user=login, password=password, host=HOST, port=PORT, database=DATABASE)
        cursor = connection.cursor()
        lookUp = createLookUp(execute("SELECT DISTINCT column_name, table_name FROM information_schema.columns WHERE table_schema = DATABASE() and table_name != 'logs' ORDER BY column_name")) #LookUp table is generated once on connection and used to quickly disambiguate between columns of different tables with the same names
        columnComments = execute("SELECT DISTINCT column_name, column_comment FROM information_schema.columns WHERE table_schema = DATABASE() and table_name != 'logs' ORDER BY column_name") #Retrieving comments to columns to present the user
        return redirect("/options", code=302)
    except:
        flash("Invalid credentials")
        return redirect("/", code=302)

@app.route("/options")
def options():
    if checkConnected():
        return render_template('options.html')
    else:
        return redirect("/", code=302)

@app.route("/logout")
def logout():
    global connection

    if connection != None:
        connection.close()
        connection = None
    return redirect("/", code=302)

@app.route("/select")
def select():
    global connection, cursor, lookUp, columnComments, selected
    
    if checkConnected():
        selected = request.args.getlist('filters')        
        return render_template('select.html', cols=columnComments, selected=selected)
    else:
        return redirect("/", code=302)

@app.route("/select_exec")
def select_exec():
    global connection, cursor, lookUp, columnComments, selected, results

    if checkConnected():
        q = buildQuerry(request.args)
        if q != "":
            results = execute(q)
            return render_template('select.html', cols=columnComments, selected=selected, shown = request.args.getlist('select_filters'), results=results)
        else:
            return redirect("/select", code=302)
    else:
        return redirect("/", code=302)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
