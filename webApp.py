from os import PathLike
from flask import Flask, session, request, render_template, redirect, flash
from markupsafe import escape
from querriesForView import ViewSelector
import mysql.connector
import secrets
from flask_socketio import SocketIO, join_room, leave_room, send

HOST = '127.0.0.1' #HOST for db connection. Currently localhost
PORT = 3306 #PORT for db connection. 3306 by default
DATABASE = 'heasm' #DB name on server

class MyWebApp(Flask):
    _viewQuery = ViewSelector()
    _config = {"user": "", "password": "", "host":HOST, "port":PORT, "database":DATABASE, "use_pure":True} #Connection configuration
    
    def __init__(self, import_name: str, static_url_path: str | None = None, static_folder: str | PathLike | None = "static", static_host: str | None = None, host_matching: bool = False, subdomain_matching: bool = False, template_folder: str | PathLike | None = "templates", instance_path: str | None = None, instance_relative_config: bool = False, root_path: str | None = None):
        super().__init__(import_name, static_url_path, static_folder, static_host, host_matching, subdomain_matching, template_folder, instance_path, instance_relative_config, root_path)

    def _checkSession() -> bool:
        if "" in (MyWebApp._config.get("user"), MyWebApp._config.get("password")):
            return False
        else:
            return True

    def _execute(query: str) -> list:
        connection = mysql.connector.connect(**MyWebApp._config)
        cursor = connection.cursor()

        cursor.reset() #Clear old result and prepare for execution
        cursor.execute(query) #Probing query to check connection status
        r = cursor.fetchall() #Retrieving all results from cursor

        cursor.close()
        connection.close()

        return r
    
app = MyWebApp(__name__, template_folder='heasm_web/templates', static_folder='heasm_web') #App initialization
app.secret_key = secrets.token_urlsafe(64) #Secret key preserves the session

socketio = SocketIO(app, cors_allowed_origins='*')

#Root page with authentification form
@app.route("/", methods=['GET', 'POST'])
def index():
    return render_template('index.html')

#Authentification processing
@app.route("/auth", methods=['POST'])
def auth():
    login = str(escape(request.form.get("login", ""))) #Safely parsing login info
    password = str(escape(request.form.get("password", ""))) #Safely parsing password info

    MyWebApp._config["user"] = login #Add login to connection config
    MyWebApp._config["password"] = password #Add password to connection config
    try:        
        MyWebApp._execute("SELECT VERSION();")

        return redirect("/data", code=302)
    
    except mysql.connector.errors.Error as e:
        if e.errno == 1045: #Connector access denied
            flash("Неверные данные")
        else:
            flash("Соединение потеряно")
        return redirect("/", code=302)

#Authentification processing
@app.route("/deauth", methods=['GET'])
def deauth():

    MyWebApp._config["user"] = ""
    MyWebApp._config["password"] = ""
    
    return redirect("/", code=302)

#Data table page
@app.route("/data", methods=['GET'])
def data():
    if not MyWebApp._checkSession():
        flash("Неверные данные")
        return redirect("/", code=302)

    query = MyWebApp._viewQuery.selectInfo(MyWebApp._viewQuery.getAllColumns())
    result = MyWebApp._execute(query)
    
    result, comments, mask = MyWebApp._viewQuery.convolvedColumnsView(result)

    rowIdValues = {"doi": 2, "journal": 20, "productid": 1}
    data = {"shown": comments, "results": result, "mask": mask, "rowIdValues": rowIdValues}

    return render_template('data.html', data=data)

#Data table page
@app.route("/logs", methods=['GET'])
def logs():
    if not MyWebApp._checkSession():
        flash("Неверные данные")
        return redirect("/", code=302)

    query, comments, mask = MyWebApp._viewQuery.logQuery()
    result = MyWebApp._execute(query)

    data = {"shown": comments, "results": result, "mask": mask}

    return render_template('logs.html', data=data)

@socketio.on("connect")
def connect(data):
    name = app._config["user"]
    room = "DataRoom"
    join_room(room)
@socketio.on("singleChanges")
def singleChanges(data):
    socketio.emit("dataChanged", {'data': data['data']}, to="DataRoom")
    col = int(data['data'][1])
    query = ""
    colDict = {0:"synthesis_product product", 1: "Forbidden", 2: "bibliography doi", 3: "synthesis_product a_parameter_max a_parameter_min",
               4:"synthesis_product mixing_method", 5:"synthesis_product SOURCE_MIX_TIME_MIN SOURCE_MIX_TIME_MAX",
               6:"synthesis_product method", 7:"synthesis_product gas", 8:"synthesis_product SYNTHESIS_TIME_MIN SYNTHESIS_TIME_MAX",
               9:"synthesis_product feature", 10:"synthesis_product contributor", 11:"synthesis_product comments",
               16:"countries country", 17:"bibliography internal_cipher", 18:"bibliography url",
               19:"bib_source year", 20:"bib_source journal", 21:"bib_source impact"}
    if(colDict[col]!="Forbidden"):
        queryList = []
        info = colDict[col]
        info = info.split()
        doi=data['data'][4]
        journal = data['data'][5]
        prodId = data['data'][6]
        if(len(info)==2):
            typ = data['data'][2]
            typo = typ.replace('.', "")
            if(not(typo.isdigit())):
                typ= '`'+typ+'`'
            typpr = data['data'][3]
            typopr = typ.replace('.', "")
            if (not (typopr.isdigit())):
                typpr = '`' + typpr + '`'
            query += "UPDATE "+ info[0] + " SET "+ info[1]+"="+typ+" WHERE "+ info[1]+"="+typpr+" and "
            if(info[0] in ("synthesis_product", "ingredients")):
                query+=" product_id="+prodId+";"
            elif(info[0]=="bibliography"):
                query += " doi=`" + doi + "`;"
            elif(info[0]=="bib_source"):
                query += " journal=`" + journal + "`;"
            elif (info[0] == "countries"):
                query += " doi=`" + doi + "`;"
            queryList.append(query)
        elif(len(info)==3):
            incoming = data['data'][2]
            incoming = incoming.replace('[','')
            incoming = incoming.replace(']', '')
            incoming = incoming.split(',')
            lst = []
            if(len(incoming)==2):
                lst = incoming
            else:
                lst.append(incoming[0])
                lst.append(incoming[0])
            query = "UPDATE " + info[0] + " SET " + info[2] + "=" + str(lst[0]) + " WHERE " +  " product_id="+data['data'][-1]+";"
            queryList.append(query)
            query = "UPDATE " + info[0] + " SET " + info[1] + "=" + str(lst[1]) + " WHERE "  +  " product_id=" + data['data'][-1] + ";"
            queryList.append(query)


@socketio.on("multipleChanges")
def singleChanges(data):
    socketio.emit("dataMultChanged", {'data': data['data']}, to="DataRoom")

@socketio.on("Commit")
def commit(data):
    # TODO unpack data
    pass


if __name__ == "__main__": #If not executed as module
   #app.run(host="127.0.0.1", port=8080, debug=True) #Run app
    socketio.run(app=app, host="127.0.0.1", port=8080, debug=True, allow_unsafe_werkzeug=True)
