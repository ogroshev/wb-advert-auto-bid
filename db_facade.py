import psycopg2
import psycopg2.extras

K_SETTING_NAME_INTERVAL_SEC = 'scan_interval_sec'


def connect(params):
    db = psycopg2.connect(database=params.db_name, user=params.db_user,
                          password=params.db_password, host=params.db_host, port=params.db_port)
    db.autocommit = True
    return db


def get_adv_companies(db):
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(
        "SELECT ac.id as company_id,   " 
        "    max_bet,               " 
        "    last_scan_ts,          " 
        "    scan_interval_sec,     " 
        "    query,                 " 
        "    ac.name,                  " 
        "    type,                  " 
        "    access_token,           " 
        "    x_user_id           " 
        "FROM advert_company ac     " 
        "JOIN sellers s ON ac.id_seller = s.id "
        "WHERE turn_scan = TRUE     " 
        "AND type = 'search'")
    return cursor.fetchall()


def update_last_scan_ts(db, company_id):
    cursor = db.cursor()
    update_query = f'UPDATE advert_company SET last_scan_ts = now() AT TIME ZONE \'MSK\' WHERE id = {company_id};'
    cursor.execute(update_query)