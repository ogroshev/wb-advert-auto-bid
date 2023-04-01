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
        "    target_place,          "
        "    last_scan_ts,          "
        "    scan_interval_sec,     "
        "    query,                 "
        "    ac.name,                  "
        "    type,                  "
        "    cpm_cookies,           "
        "    x_user_id,           "
        "    current_bet,  "
        "    subject_id, "
        "    cpm_token "
        "FROM advert_company ac     "
        "JOIN sellers s ON ac.id_seller = s.id "
        "WHERE turn_scan = TRUE "
        "AND cpm_token IS NOT NULL"
        "AND type = 'search'")
    return cursor.fetchall()


def update_last_scan_ts(db, company_id):
    cursor = db.cursor()
    update_query = f'UPDATE advert_company SET last_scan_ts = now() AT TIME ZONE \'MSK\' WHERE id = {company_id};'
    cursor.execute(update_query)


def update_placement_data(db, company_id, current_bet, subject_id):
    cursor = db.cursor()
    update_query = f'UPDATE advert_company SET current_bet = {current_bet}, subject_id = {subject_id} WHERE id = {company_id};'
    cursor.execute(update_query)


def log_advert_bid(db, company_id, current_price, current_place, target_price, target_place, decision, 
                    result_code, error_str, json_adverts, json_priority_subjects, request_name):
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    insert_query = f'''
    INSERT INTO advert_company_log (advert_company_id,
                                    current_price,
                                    current_place,
                                    target_price,
                                    target_place,
                                    decision,
                                    result_code,
                                    error_str,
                                    json_adverts,
                                    json_priority_subjects,
                                    request_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
    cursor.execute(insert_query, (company_id,
                                  current_price,
                                  current_place,
                                  target_price,
                                  target_place,
                                  decision,
                                  result_code,
                                  error_str,
                                  json_adverts,
                                  json_priority_subjects,
                                  request_name))

def alarm(db, company_id, error_str):
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    insert_query = f'''
        INSERT INTO advert_alarm (advert_company_id, error_str) VALUES (%s, %s);
    '''
    cursor.execute(insert_query, (company_id,
                                  error_str))
