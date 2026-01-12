import sqlite3

# run this file once to create a new db file
conn = sqlite3.connect('Levels.db')

cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Levels (
        User_Id INTEGER PRIMARY KEY,
        level INTEGER,
        exp INTEGER,
        multiplier INTEGER
    )
 ''')
conn.commit()
conn.close()