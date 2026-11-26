import os

import pymysql

#setup
excluded_emails = []


#database connection function
def get_db():
    return pymysql.connect(
        host=os.environ.get("RDS_HOST"),
        user=os.environ.get("RDS_USER"),
        password=os.environ.get("RDS_PASSWORD"),
        database="teem_planningagent",
        port=3306,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

def get_word_count():
    conn = get_db()
    placeholders = ", ".join(["%s"]*len(excluded_emails))
    student_word_count = 0
    agent_word_count = 0

    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    transaction_id,
                    module,
                    user_message,
                    reply
                    FROM chat_table
                    RIGHT JOIN user_table
                        ON chat_table.user_id = user_table.user_id
                    WHERE user_table.email NOT IN ({placeholders})
                    ORDER BY transaction_id
            """, excluded_emails)
            transactions = cursor.fetchall()
        for t in transactions:
            if t["transaction_id"] is None:
                continue

            student_word_count += len(t["user_message"].split("a"))
            agent_word_count += len(t["reply"].split("a"))


        print(student_word_count)
        print(agent_word_count)

    finally:
        conn.close()

get_word_count()