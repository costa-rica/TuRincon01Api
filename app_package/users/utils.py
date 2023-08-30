from flask import current_app, url_for
# from flask_login import current_user
import json
# import requests
# from datetime import datetime, timedelta
from tr01_models import sess, Users
# import time
from flask_mail import Message
from app_package import mail
import os
# from werkzeug.utils import secure_filename
# import zipfile
import shutil
import logging
from logging.handlers import RotatingFileHandler
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer


#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

#initialize a logger
logger_main = logging.getLogger(__name__)
logger_main.setLevel(logging.DEBUG)


#where do we store logging information
file_handler = RotatingFileHandler(os.path.join(os.environ.get('API_ROOT'),"logs",'users_routes.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

#where the stream_handler will print
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

# logger_sched.handlers.clear() #<--- This was useful somewhere for duplicate logs
logger_main.addHandler(file_handler)
logger_main.addHandler(stream_handler)


def create_token(user):
    expires_sec=60*20#set to 20 minutes
    s=Serializer(current_app.config['SECRET_KEY'], expires_sec)
    token = s.dumps({'user_id': user.id}).decode('utf-8')
    # token = s.dumps({'user_id': user.id})# This is not right just testing to get Swift  response
    # print("token sending back: ", token)
    # print(type(token))
    return token


def send_reset_email(user):
    token = user.get_reset_token()
    logger_main.info(f"current_app.config.get(MAIL_USERNAME): {current_app.config.get('MAIL_USERNAME')}")
    msg = Message('Password Reset Request',
                  sender=current_app.config.get('MAIL_USERNAME'),
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('users.reset_token', token=token, _external=True)}

If you did not make this request, ignore email and there will be no change
'''
    mail.send(msg)


def send_confirm_email(email):
    if os.environ.get('FLASK_CONFIG_TYPE') == 'prod':
        logger_main.info(f"-- sending email to {email} --")
        msg = Message('Welcome to Tu Rincón!',
            sender=current_app.config.get('MAIL_USERNAME'),
            recipients=[email])
        msg.body = 'You have succesfully been registered to Tu Rincón.'
        mail.send(msg)
        logger_main.info(f"-- email sent --")
    else :
        logger_main.info(f"-- Non prod mode so no email sent --")

def create_dict_user_ios(user_id):
    logger_main.info(f"- create_dict_user: user_id: {user_id}")
    user = sess.get(Users, user_id)
    # logger_main.info(f"- user: {user}")
    
    dict_user_ios = {}
    dict_user_ios['id']=str(user.id)
    dict_user_ios['email']=user.email
    dict_user_ios['username']=user.username
    dict_user_ios['admin']=user.admin
    # dict_user_ios['rincons']=user.rincons

    return dict_user_ios


