from flask import Blueprint
from flask import render_template, jsonify, send_from_directory,current_app, request
import os
import logging
from logging.handlers import RotatingFileHandler

from tr01_models import sess, Users, Rincons, RinconsPosts, UsersToRincons, \
    RinconsPostsComments, RinconsPostsLikes, RinconsPostsCommentsLikes
from app_package.token_decorator import token_required


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

    posts_list = []
    for post in rincon.posts:
        post_dict = {}
        post_dict["id"] = str(post.id)
        post_dict["user_id"] = str(post.user_id)
        post_created_by_user = sess.query(Users).filter_by(id=post.user_id).first()
        post_dict["username"] = str(post_created_by_user.username)
        post_dict["rincon_id"] = str(post.rincon_id)
        post_dict["post_text"] = str(post.post_text)
        post_dict["post_date"] = str(post.time_stamp_utc)
        post_dict["image_file_name"] = post.image_file_name
        post_dict["video_file_name"] = post.video_file_name
        posts_list.append(post_dict)

    logger_main.info(f"- sending rincon's post: {len(posts_list)} posts")
    logger_main.info(f"- first post is: {posts_list[0]}")

    return jsonify(posts_list)

@main.route("/rincon_post_file/<file_name>", methods=["POST"])
@token_required
def rincon_file(current_user, file_name):


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

    return send_from_directory(os.path.join(current_app.config.get('DB_ROOT'),"rincon_files", \
        rincon_files_db_folder_name), image_filename)




