
from flask import Blueprint
from flask import render_template, url_for, redirect, request, \
    abort, session, Response, current_app, send_from_directory, make_response, \
    jsonify
import bcrypt
# from flask_login import login_required, login_user, logout_user, current_user
import logging
from logging.handlers import RotatingFileHandler
import os
import json
from tr01_models import sess, engine, text, Base, \
    Users, Rincons

from app_package.users.utils import create_token, send_reset_email, send_confirm_email
from app_package.main.utils import addUserToRincon
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from app_package.token_decorator import token_required

#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

#initialize a logger
logger_users = logging.getLogger(__name__)
logger_users.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('API_ROOT'),'logs','users_routes.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

#where the stream_handler will print
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

# logger_sched.handlers.clear() #<--- This was useful somewhere for duplicate logs
logger_users.addHandler(file_handler)
logger_users.addHandler(stream_handler)


salt = bcrypt.gensalt()


users = Blueprint('users', __name__)


@users.route('/login', methods = ['GET'])
def login():
    logger_users.info(f"-- in user/login route --")

    data_headers = request.headers
    logger_users.info(f"--- current app SQL_URI: {current_app.config.get('SQL_URI')}")

    try:
        auth = request.authorization
    except:
        return jsonify({"status": "Auth not read-able."})

    if not auth or not auth.username or not auth.password:
        logger_users.info("auth not sent")
        return make_response('Could not verify', 400, {'message' : 'missing auth body i.e. need auth= (username, password)'})
    user = sess.query(Users).filter_by(email = auth.username).first()
    
    if not user:
        return make_response('Could note verify - user not found', 401, {'message' : f'{auth.username} is not a user'})

    if bcrypt.checkpw(auth.password.encode(), user.password):

        token = create_token(user)
        # user_rincons = [[str(i.rincon.id), i.rincon.name, i.rincon.name_no_spaces] for i in user.rincons]
        user_rincons = [{"id":str(i.rincon.id), "name":i.rincon.name, "name_no_spaces":i.rincon.name_no_spaces} for i in user.rincons]
        

        return jsonify({'token': token,'user_id':str(user.id), 'user_rincons': user_rincons})

    return make_response('Could not verify', 401, {'message' : 'email/password are not valid'})



@users.route('/register', methods = ['POST'])
def register():
    logger_users.info(f"-- in register route --")

    data_headers = request.headers

    try:
        request_json = request.json
        print("request_json:",request_json)
    except Exception as e:
        logger_users.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})
        
    new_email = request_json.get('new_email')

    check_email = sess.query(Users).filter_by(email = new_email).all()
    if len(check_email)==1:
        logger_users.info(f"- email already in database -")
        existing_emails = [i.email for i in sess.query(Users).all()]
        return jsonify({"existing_emails": existing_emails})

    hash_pw = bcrypt.hashpw(request_json.get('new_password').encode(), salt)
    new_user = Users(email = new_email, password = hash_pw)
    try:
        sess.add(new_user)
        sess.commit()
    except:
        return jsonify({"status": f"failed to add to database."})

    
    logger_users.info(f"- new_user.id: {new_user.id} -")


    try:
        addUserToRincon(new_user.id, 1)
    except:
        logger_users.info(f"- Unable to add user {user_id} -")

    new_user_dict_response = {}
    new_user_dict_response["id"]=new_user.id
    new_user_dict_response["email"]=new_user.email
    new_user_dict_response["username"]=new_user.username
    costa_rica_rincon = sess.get(Rincons,1)
    new_user_dict_response["user_rincons"]={"id":str(costa_rica_rincon.id),
        "name":costa_rica_rincon.name,"name_no_spaces":costa_rica_rincon.name_no_spaces}
    #log user in
    
    
    token = create_token(new_user)
    new_user_dict_response["token"]=token
    logger_users.info('--- new_user ---')
    logger_users.info(new_user)

    # return jsonify({'token': token,'user_id':str(new_user.id)})
    return jsonify(new_user_dict_response)

    # return jsonify({"user_id":str(new_user.id)})



# @users.route('/logout')
# def logout():
#     logout_user()
#     return jsonify({"status":f"User email: {new_email} successfully logged out"})


# @users.route('/test_response', methods=['POST'])
# def test_response():
#     logger_users.info(f"-- in test_response route --")

#     try:
#         request_json = request.json
#         print("request_json:",request_json)
#     except Exception as e:
#         logger_users.info(e)
#         return jsonify({"status": "httpBody data recieved not json not parse-able."})

#     if request_json.get("message") == "sudo_let_me_in":
#         return jsonify({'response': "success!"})

#     return make_response('Could not verify', 401, {'message' : 'email/password are not valid'})


# @users.route('/test_response_token', methods=['POST'])
# @token_required
# def test_response_token(current_user):
#     logger_users.info(f"-- in test_response_token route --")

#     try:
#         request_json = request.json
#         print("request_json:",request_json)
#     except Exception as e:
#         logger_users.info(e)
#         return jsonify({"status": "httpBody data recieved not json not parse-able."})

#     if request_json.get("message") == "sudo_let_me_in":
#         return jsonify({'response': "success!"})

#     return make_response('Could not verify', 401, {'message' : 'email/password are not valid'})

