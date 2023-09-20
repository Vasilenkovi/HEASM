from os import PathLike
from flask import Flask, session, request, render_template, redirect, flash
from markupsafe import escape
from querriesForView import ViewSelector
import mysql.connector
import secrets

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

#Data table page
@app.route("/data", methods=['GET', 'POST'])
def data():
    if not MyWebApp._checkSession():
        flash("Неверные данные")
        return redirect("/", code=302)

    query = MyWebApp._viewQuery.selectInfo(MyWebApp._viewQuery.getAllColumns())
    result = MyWebApp._execute(query)
    
    query = MyWebApp._viewQuery.querryForColComments(MyWebApp._viewQuery.getAllColumns())
    comments = MyWebApp._execute(query)

    data = {"shown": comments, "results": result}

    return render_template('data.html', data=data)

if __name__ == "__main__": #If not executed as module
    app.run(host="127.0.0.1", port=8080, debug=True) #Run app