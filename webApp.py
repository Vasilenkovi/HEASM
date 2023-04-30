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

connection = None
cursor = None
lookUp = []
columnComments = []
selected = []
results = []

app = Flask(__name__, template_folder='HTML', static_folder='static')
app.secret_key = secrets.token_urlsafe(16)

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
    global lookUp, columnComments
    selected_filters = requestArgs.getlist('select_filters')
    where_filters = requestArgs.getlist('where_filters')

    querry = "SELECT " #base of querry
    select = [] #all columns to select
    where = [] #all columns to include in "WHERE" statement
    whereSymbol = [] #all "WHERE" comparison operators
    whereCondition = [] #all "WHERE" conditions
    sort = 0
    sortCol = ""

    for i in selected_filters:
        for j in range(len(columnComments)):
            if columnComments[j][1].decode('utf-8', 'ignore') == i:
                select.append(lookUp[j][1] + "." + columnComments[j][0]) #if checked as "SELECT" add to select with table disambiguation from lookup
    
    for i in where_filters:
        for j in range(len(columnComments)):
            if columnComments[j][1].decode('utf-8', 'ignore') == i:
                where.append(lookUp[j][1] + "." + columnComments[j][0]) #if checked as "WHERE" add to select with table disambiguation from lookup
    
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
    querry += """ FROM synthesis_product INNER JOIN synthesis_parameter ON synthesis_product.PRODUCT_ID = synthesis_parameter.PRODUCT_ID
    INNER JOIN ingredients ON synthesis_product.PRODUCT_ID = ingredients.PRODUCT_ID
    INNER JOIN measurements ON synthesis_product.PRODUCT_ID = measurements.PRODUCT_ID
    INNER JOIN bibliography ON synthesis_product.DOI = bibliography.DOI
    INNER JOIN source ON bibliography.JOURNAL = source.JOURNAL
    INNER JOIN key_word ON bibliography.DOI = key_word.DOI 
    INNER JOIN countries ON bibliography.DOI = countries.DOI""".replace("\n", " ")   

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
        lookUp = execute("SELECT DISTINCT column_name, table_name FROM information_schema.columns WHERE table_schema = DATABASE() ORDER BY column_name;") #LookUp table is generated once on connection and used to quickly disambiguate between columns of different tables with the same names
        columnComments = execute("SELECT DISTINCT column_name, column_comment FROM information_schema.columns WHERE table_schema = DATABASE() ORDER BY column_name;") #Retrieving comments to columns to present the user
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
    
    selected = request.args.getlist('filters')
    if checkConnected():
        return render_template('select.html', cols=columnComments, selected=selected)
    else:
        return redirect("/", code=302)

@app.route("/select_exec")
def select_exec():
    global connection, cursor, lookUp, columnComments, selected, results
    
    q = buildQuerry(request.args)
    results = execute(q)

    if checkConnected():
        return render_template('select.html', cols=columnComments, selected=selected, results=results)
    else:
        return redirect("/", code=302)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)