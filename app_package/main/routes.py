from flask import Blueprint
from flask import render_template, jsonify, send_from_directory,current_app, request, make_response
import os
import logging
from logging.handlers import RotatingFileHandler

from tr01_models import sess, Users, Rincons, RinconsPosts, UsersToRincons, \
    RinconsPostsComments, RinconsPostsLikes, RinconsPostsCommentsLikes
from app_package.token_decorator import token_required
from app_package.main.utils import create_rincon_posts_list
import json
import time
import socket

main = Blueprint('main', __name__)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_main = logging.getLogger(__name__)
logger_main.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('API_ROOT'),'logs','main_routes.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

logger_main.addHandler(file_handler)
logger_main.addHandler(stream_handler)

@main.route('/are_we_running', methods=['GET'])
def are_we_running():
    
    try:
        hostname = socket.gethostname()
    except:
        hostname = "not sure of my name"
    logger_users.info(f"are_we_working endpoint pinged")

    logger_users.info(f"{current_app.config.get('WS_API_PASSWORD')}")

    # print(dir(current_app.config))
    # print(current_app.config.items())

    return jsonify(f"Yes! We're up! in the {hostname} machine")

@main.route("/rincons", methods=["GET"])
@token_required
def rincons(current_user):
        
    users_rincons_list = [(i.rincons_table_id, i.rincon.name) for i in current_user.rincons]

    # return render_template('main/rincons.html',users_rincons_list=users_rincons_list )
    return jsonify({'rincons': users_rincons_list})


@main.route("/rincon_posts/<rincon_id>", methods=["POST"])
@token_required
def rincon(current_user, rincon_id):

    print(f"- accessed rincon endpoint with rincon_id: {rincon_id}")
    
    rincon = sess.query(Rincons).filter_by(id= rincon_id).first()

    try:
        request_json = request.json
        ios_flag = True if request_json.get('ios_flag')=='true' else False
        logger_main.info("request_json:",request_json)
        logger_main.info(f"ios_flag: {type(ios_flag)}, {ios_flag}")
    except Exception as e:
        logger_main.info(e)
        return make_response('Could not verify', 400, {'message' : 'httpBody data recieved not json not parse-able.'})


    posts_list = create_rincon_posts_list(current_user, rincon_id, ios_flag)
    # logger_main.info(f"post_list count: {len(posts_list)}")
    # # logger_main.info(f"post_list count: {len(posts_list)}")

    # logger_main.info(f"- sending rincon's post: {len(posts_list)} posts")
    # logger_main.info(f"- first post is: {posts_list[0]}")

    return jsonify(posts_list)

@main.route("/rincon_post_file/<file_name>", methods=["POST"])
@token_required
def rincon_file(current_user, file_name):
    print("*** calling for images ***")

    try:
        request_json = request.json
        print("request_json:",request_json)
        rincon = sess.query(Rincons).filter_by(id = request_json["rincon_id"]).first()
        rincon_files_db_folder_name = f"{rincon.id}_{rincon.name_no_spaces}"
    except Exception as e:
        logger_main.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})


    if len(file_name.split(",")) > 0:
        file_list = file_name.split(",")
        image_filename = file_list[0]
    else:
        image_filename = file_name


    if os.environ.get('FLASK_CONFIG_TYPE')=='local':
        print("*** sleeping for 5 seconds *")
        time.sleep(5)

    logger_main.info(f"- /rincon_post_file respose with filename sent: {image_filename}") 

    return send_from_directory(os.path.join(current_app.config.get('DB_ROOT'),"rincon_files", \
        rincon_files_db_folder_name), image_filename)


@main.route("/check_invite_json", methods=["POST"])
def check_invite_json():
    logger_main.info(f"- in check_invite_json")

    try:
        request_json = request.json
        logger_main.info("request_json:",request_json)
    except Exception as e:
        logger_main.info(e)
        return make_response('Could not verify', 400, {'message' : 'httpBody data recieved not json not parse-able.'})

    website_credentials = request_json.get("TR_VERIFICATION_PASSWORD")


    if website_credentials != current_app.config.get("TR_VERIFICATION_PASSWORD"):
        logger_main.info("missing/incorrect website_credentials")
        return make_response('Could not verify', 400, {'message' : 'missing/incorrect website_credentials'})
    else:

        # TODO: check invite_json_file and apply invites to UsersToRincons Association table

        # open 

        # search for invitations file
        invitation_json_file_path_and_name = os.path.join(current_app.config.get("DB_ROOT"), "rincon_files","pending_rincon_invitations.json")
        if os.path.exists(invitation_json_file_path_and_name):
            invitation_json_file = open(invitation_json_file_path_and_name)
            invite_dict = json.load(invitation_json_file)
            invitation_json_file.close()

            list_invite_user_to_delete = []
            for invited_email, rincon_ids_list in invite_dict.items():
                invited_user = sess.query(Users).filter_by(email= invited_email).first()
                if invited_user:
                    list_invite_user_to_delete.append(invited_email)
                    for rincon_tuple in rincon_ids_list:
                        if rincon_tuple[1] == sess.get(Rincons,rincon_tuple[0]).name_no_spaces:
                            new_rincon_access = UsersToRincons(users_table_id= invited_user.id, rincons_table_id = rincon_tuple[0])
                            sess.add(new_rincon_access)
                            sess.commit()
                    
            # delete invite user from dict
            for email in list_invite_user_to_delete:
                del invite_dict[email]
            

            # write invite_user_file
            with open(invitation_json_file_path_and_name,'w') as invitation_json_file:
                json.dump(invite_dict, invitation_json_file)



            logger_main.info("Successfully added invites")
        else:
            logger_main.info("- No invitation_json_file found")


        
        return jsonify({"status": "Success!"})




@main.route("/rincon_post_file_testing/<file_name>", methods=["POST"])
# @token_required
def rincon_file_testing( file_name):
    print("*** calling for images (rincon_file_testing) ***")

    try:
        request_json = request.json
        print("request_json:",request_json)
        rincon = sess.query(Rincons).filter_by(id = request_json["rincon_id"]).first()
        rincon_files_db_folder_name = f"{rincon.id}_{rincon.name_no_spaces}"
    except Exception as e:
        logger_main.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})


    if len(file_name.split(",")) > 0:
        file_list = file_name.split(",")
        image_filename = file_list[0]
    else:
        image_filename = file_name

    # print(f"current_app.config.get('FLASK_CONFIG_TYPE'): {current_app.config.get('FLASK_CONFIG_TYPE')}")
    # if current_app.config.get('FLASK_CONFIG_TYPE')=='local':
    #     print("*** sleeping for 5 seconds *")
    #     time.sleep(5)

    logger_main.info(f"- /rincon_post_file respose with filename sent: {image_filename}") 




    return send_from_directory(os.path.join(current_app.config.get('DB_ROOT'),"rincon_files", \
        rincon_files_db_folder_name), image_filename)



@main.route('/like_post/<rincon_id>/<post_id>/')
@token_required
def like_post(rincon_id,post_id):
    logger_main.info(f"- Like {rincon_id} {post_id} -")

    rincon_id = int(rincon_id)
    post_id = int(post_id)
    post_like = sess.query(RinconsPostsLikes).filter_by(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id).first()
    
    if post_like:
        print("- post already LIKED -")
        sess.query(RinconsPostsLikes).filter_by(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id).delete()
        sess.commit()
    else:
        print("- post NOT liked")
        new_post_like = RinconsPostsLikes(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id, post_like=True)
        sess.add(new_post_like)
        sess.commit()


    # new_post_like = RinconsPostsLikes(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id, post_like=True)
    # sess.add(new_post_like)
    # sess.commit()

    # post_like = sess.query(RinconsPostsLikes).filter_by(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id).first()
    print("Post Like:", post_like)



    # return redirect(request.referrer, _anchor='like_'+post_id)
    return redirect(url_for('main.rincon', rincon_id=rincon_id,post_id=post_id, _anchor='like_'+str(post_id)))



