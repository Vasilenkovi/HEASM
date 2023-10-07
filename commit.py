from mysql.connector import connect, Error
def commit(username, password):
    try:
        with connect(
                host="localhost",
                user=username,
                password=password
        ) as connection:
            print(connection)
    except Error as e:
        print(e)