from flask import Blueprint
from flask import render_template, jsonify, send_from_directory,current_app, request, make_response
import os
import logging
from logging.handlers import RotatingFileHandler

from tr01_models import sess, Base, text, engine, \
    Users, Rincons, RinconsPosts, UsersToRincons, \
    RinconsPostsComments, RinconsPostsLikes, RinconsPostsCommentsLikes
from app_package.token_decorator import token_required

# from app_package.users.utils import send_reset_email, send_confirm_email
import pandas as pd
import shutil
from datetime import datetime
import zipfile

#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

#initialize a logger
logger_admin = logging.getLogger(__name__)
logger_admin.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('API_ROOT'),'logs','admin_routes.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

#where the stream_handler will print
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

# logger_sched.handlers.clear() #<--- This was useful somewhere for duplicate logs
logger_admin.addHandler(file_handler)
logger_admin.addHandler(stream_handler)


# salt = bcrypt.gensalt()


admin = Blueprint('admin', __name__)

@admin.route("/create_tr_backup01", methods=["POST"])
def create_tr_backup01():
    logger_admin.info(f"- in create_tr_backup01")

    try:
        request_json = request.json
        logger_admin.info("request_json:",request_json)
    except Exception as e:
        logger_admin.info(e)
        return make_response('Could not verify', 400, {'message' : 'httpBody data recieved not json not parse-able.'})

    website_credentials = request_json.get("TR_VERIFICATION_PASSWORD")


    if website_credentials != current_app.config.get("TR_VERIFICATION_PASSWORD"):
        logger_admin.info("missing/incorrect website_credentials")
        return make_response('Could not verify', 400, {'message' : 'missing/incorrect website_credentials'})

    # Client verified continue with backup
    logger_admin.info(f"- in create_tr_backup01: client verified, starting backup")
    metadata = Base.metadata
    db_table_list = [table for table in metadata.tables.keys()]

    backup_dir_path = os.path.join(current_app.config.get('DB_ROOT'), 'db_backup')

    # craete folder to save
    if not os.path.exists(os.path.join(current_app.config.get('DB_ROOT'),"db_backup")):
        os.makedirs(os.path.join(current_app.config.get('DB_ROOT'),"db_backup"))
        print("* db_back did NOT exist so we made one  *")

    
    db_tables_dict = {}
    for table_name in db_table_list:
        base_query = sess.query(metadata.tables[table_name])
        df = pd.read_sql(text(str(base_query)), engine.connect())

        # fix table names
        cols = list(df.columns)
        for col in cols:
            if col[:len(table_name)] == table_name:
                df = df.rename(columns=({col: col[len(table_name)+1:]}))

        # Users table convert password from bytes to strings
        if table_name == 'users':
            df['password'] = df['password'].str.decode("utf-8")


        db_tables_dict[table_name] = df
        if request_json.get("format") == "csv":
            logger_admin.info(f"- backup data files as CSV")
            db_tables_dict[table_name].to_csv(os.path.join(backup_dir_path, f"{table_name}.csv"), index=False)
        else:
            logger_admin.info(f"- backup data files as Pickle (python only readable)")
            db_tables_dict[table_name].to_pickle(os.path.join(backup_dir_path, f"{table_name}.pkl"))
    
    if request_json.get("extras") == "no files":
        logger_admin.info(f"- backup with NO rincon_files compressed")
    else:
        logger_admin.info(f"- backup with rincon_files compressed")
        source = os.path.join(current_app.config.get('DB_ROOT'), 'rincon_files')
        shutil.copytree(source,os.path.join(backup_dir_path, 'rincon_files'))
    
    shutil.make_archive(os.path.join(current_app.config.get('DB_ROOT'),'db_backup'), 'zip', backup_dir_path)

    # shutil.make_archive(backup_dir_path, 'zip', backup_dir_path)
    logger_admin.info(f"- in create_tr_backup01: backup finished")

    #delete 
    shutil.rmtree(backup_dir_path)

    return jsonify({"status": "zip file create!"})



@admin.route("/process_tr_backup01", methods=["POST"])
def process_tr_backup01():
    logger_admin.info(f"- in process_tr_backup01")

    try:
        request_json = request.json
        logger_admin.info("request_json:",request_json)
    except Exception as e:
        logger_admin.info(e)
        return make_response('Could not verify', 400, {'message' : 'httpBody data recieved not json not parse-able.'})

    website_credentials = request_json.get("TR_VERIFICATION_PASSWORD")


    if website_credentials != current_app.config.get("TR_VERIFICATION_PASSWORD"):
        logger_admin.info("missing/incorrect website_credentials")
        return make_response('Could not verify', 400, {'message' : 'missing/incorrect website_credentials'})
    else:
        logger_admin.info(f"- in process_tr_backup01: client verified, starting backup")
        metadata = Base.metadata
        db_table_list = [table for table in metadata.tables.keys()]

    
    if not os.path.exists(os.path.join(current_app.config.get('DB_ROOT'),'db_backup.zip')):
        print("* NO backup.zip *")
        return make_response('Could not verify', 500, {'message' : 'NO backup zip file found'})
        # return jsonify({"status": f"NO zip file found: {new_backup_path}"})
    else:
        print("- backup file is: ")
        print(os.path.join(current_app.config.get('DB_ROOT'),'db_backup.zip'))

    # Client verified continue with process
    backup_dir_path = os.path.join(current_app.config.get('BACKUP_ROOT'))

    # create folder to save
    if not os.path.exists(os.path.join(current_app.config.get('BACKUP_ROOT'))):
        os.makedirs(os.path.join(current_app.config.get('BACKUP_ROOT')))
    
    #create tr_backup_[date]
    new_backup_zip_name = "TrBackup" + datetime.now().strftime("%Y%m%d") + ".zip"

    new_backup_path = os.path.join(current_app.config.get('BACKUP_ROOT'), new_backup_zip_name)

    if os.path.exists(os.path.join(current_app.config.get('DB_ROOT'),'db_backup.zip')):
        print("* db back up exists *")

    shutil.move(os.path.join(current_app.config.get('DB_ROOT'),'db_backup.zip'), new_backup_path)

    return jsonify({"status": f"zip file moved to storage dir: {new_backup_path}"})


