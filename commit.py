from mysql.connector import connect, Error
def commit(app):
    queryOfQueries = app._execute("select * from change_log;")
    for i in queryOfQueries:
        r = app._execute(i[1])
    app._execute("delete from change_log")