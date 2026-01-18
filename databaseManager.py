import sqlite3

# run this file once to create a new db files if they don't exist
conn = sqlite3.connect('Data/Moderation_settings.db')

cursor = conn.cursor()
cursor.executescript('''
    CREATE TABLE IF NOT EXISTS Infraction (
        User_Id INTEGER NOT NULL,
        guild_Id INTEGER NOT NULL,
        Warns INTEGER DEFAULT 0,
        Mutes INTEGER DEFAULT 0,
        Kicked BOOLEAN NOT NULL DEFAULT false,
        Banned BOOLEAN NOT NULL DEFAULT false,

        PRIMARY KEY (User_Id, guild_Id)
    );

    CREATE TABLE IF NOT EXISTS logging_channels (
        guild_id INTEGER PRIMARY KEY,
        main_logging_channel INTEGER,
        member_logging_channel INTEGER,
        server_logging_channel INTEGER,
        voice_logging_channel INTEGER,
        message_logging_channel INTEGER,
        join_leave_logging_channel INTEGER
    );

    CREATE TABLE IF NOT EXISTS Mod_Role_Management (
        guild_id INTEGER PRIMARY KEY,
        Moderator_Roles TEXT,
        Admin_Roles TEXT,
        Muted_Role TEXT
    );
 ''')
conn.commit()
conn.close()

conn = sqlite3.connect('Data/Levels.db')
cursor = conn.cursor()
cursor.executescript('''
    CREATE TABLE IF NOT EXISTS Levels (
        User_Id INTEGER PRIMARY KEY,
        level INTEGER DEFAULT 0,
        exp INTEGER DEFAULT 0,
        multiplier REAL DEFAULT 1
    );
 ''')
conn.commit()
conn.close()

conn = sqlite3.connect('Data/Partherships.db')
cursor = conn.cursor()
cursor.executescript('''
    CREATE TABLE IF NOT EXISTS bridges (
        channel_a INTEGER NOT NULL,
        channel_b INTEGER NOT NULL,
        PRIMARY KEY (channel_a, channel_b)
    );
''')
conn.commit()
conn.close()