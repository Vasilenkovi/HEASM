from mysql.connector import connect, Error

def commit(app, socketio, user: str, password: str):
    queryOfQueries = app._execute("select * from change_log;", user, password)
    for i in queryOfQueries:
        #print(i[1])
        r = app._execute(i[1], user, password)
    if (len(queryOfQueries) != 0):
        socketio.emit("update")
    app._execute("delete from change_log limit 10000;", user, password)
