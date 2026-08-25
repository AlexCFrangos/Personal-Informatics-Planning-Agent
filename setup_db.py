import os

import pymysql

conn = pymysql.connect(
    host=os.environ.get("RDS_HOST"),
    user=os.environ.get("RDS_USER"),
    password=os.environ.get("RDS_PASSWORD"),
    port=3306,
)

cursor = conn.cursor()

#create database
cursor.execute("CREATE DATABASE IF NOT EXISTS teem_planningagent;")
cursor.execute("USE teem_planningagent;")


cursor.execute("SHOW DATABASES")
print("-----databases-----")
for (db,) in cursor.fetchall():
    print(db)
#cursor.execute("DROP DATABASE desired_database")

cursor.execute("SHOW TABLES")
print("-----tables-----")
for (table,) in cursor.fetchall():
    print(table)
cursor.execute("DROP TABLE hypothesis_table")
cursor.execute("DROP TABLE variable_table")
cursor.execute("DROP TABLE chat_table")
#cursor.execute("DROP TABLE user_table")

#user data table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_table (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        
        email VARCHAR(50) UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role VARCHAR(50),
        name VARCHAR(50) NOT NULL,
        class_section VARCHAR(50) NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
#variable table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS variable_table (
        variable_id INT AUTO_INCREMENT PRIMARY KEY,
        submission_id INT,
        user_id INT,

        variable TEXT,
        variable_unit TEXT,
        collection_method TEXT,
        goal TEXT,
        variable_type TEXT,

        FOREIGN KEY (user_id)
            REFERENCES user_table(user_id)
            ON DELETE CASCADE
    );
""")
#hypothesis table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS hypothesis_table (
        hypothesis_id INT AUTO_INCREMENT PRIMARY KEY,
        submission_id INT,
        user_id INT,

        hypothesis TEXT,
        evidence TEXT,
        study_type TEXT,
        evidence_strength INT,
        link_1 TEXT,
        link_2 TEXT,

        FOREIGN KEY (user_id)
            REFERENCES user_table(user_id)
            ON DELETE CASCADE
    );
""")

#transactional table for normal chatting
cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_table (
        transaction_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,

        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        module VARCHAR(50),
        user_message TEXT,
        reply TEXT,
        revision BOOL,
        hide_from_user BOOL,

        FOREIGN KEY (user_id)
            REFERENCES user_table(user_id)
            ON DELETE CASCADE
    );
""")


cursor.execute("SHOW DATABASES")
print("-----databases-----")
for (db,) in cursor.fetchall():
    print(db)

cursor.execute("SHOW TABLES")
print("-----tables-----")
for (table,) in cursor.fetchall():
    print(table)

conn.commit()
cursor.close()
conn.close()
print("Database setup complete.")