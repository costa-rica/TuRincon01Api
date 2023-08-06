from flask import Blueprint
from flask import render_template, jsonify, send_from_directory,current_app, request, make_response
import os
import logging
from logging.handlers import RotatingFileHandler

from tr01_models import sess, Users, Rincons, RinconsPosts, UsersToRincons, \
    RinconsPostsComments, RinconsPostsLikes, RinconsPostsCommentsLikes
from app_package.token_decorator import token_required
from app_package.main.utils import create_rincon_posts_list, create_rincon_post_dict, \
    create_empty_rincon_post_dict, create_dict_rincon_ios
import json
import time
import socket

main = Blueprint('main', __name__)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(lineno)d:%(name)s:%(message)s')

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
    logger_main.info(f"are_we_working endpoint pinged")


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


    posts_list = create_rincon_posts_list(current_user, rincon_id)

    if len(posts_list) == 0:
        print("add a post")
        posts_list = create_empty_rincon_post_dict(current_user,rincon_id )
    # print("----------")
    # print(posts_list)
    # print("-----------")
    return jsonify(posts_list)

@main.route("/rincon_post_file/<file_name>", methods=["POST"])
@token_required
def rincon_file(current_user, file_name):
    print("*** calling for images ***")
    logger_main.info(f"- in rincon_post_file endpoint, calling for :: {file_name}")

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



@main.route('/like_post/<rincon_id>/<post_id>/', methods=['POST'])
@token_required
def like_post(current_user, rincon_id, post_id):
    logger_main.info(f"- Like {rincon_id} {post_id} -")

    rincon_id = int(rincon_id)
    post_id = int(post_id)
    
    post_like = sess.query(RinconsPostsLikes).filter_by(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id).first()
    if post_like:
        sess.query(RinconsPostsLikes).filter_by(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id).delete()
        sess.commit()
    else:
        new_post_like = RinconsPostsLikes(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id, post_like=True)
        sess.add(new_post_like)
        sess.commit()

    post = sess.get(RinconsPosts, post_id)
    post_like_updated = sess.query(RinconsPostsLikes).filter_by(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id).first()
    
    response_dict = {}
    response_dict["user_id"]=current_user.id
    response_dict["rincon_id"]=rincon_id
    response_dict["post_id"]=post_id
    response_dict["liked"]=True if post_like_updated != None else False
    response_dict["like_count"]= len(post.post_like) if post.post_like != [] else 0  

    return jsonify(response_dict)



@main.route('/new_comment/<rincon_id>/<post_id>/', methods=['POST'])
@token_required
def new_comment(current_user, rincon_id, post_id):
    logger_main.info(f"- new_comment {rincon_id} {post_id} -")

    rincon_id = int(rincon_id)
    post_id = int(post_id)

    try:
        request_json = request.json
    except Exception as e:
        logger_users.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})

    new_comment = request_json.get("new_comment")

    new_comment_for_post = RinconsPostsComments(post_id=post_id, rincon_id=rincon_id,user_id=current_user.id, comment_text=new_comment)
    sess.add(new_comment_for_post)
    sess.commit()
    
    ios_flag = True if request_json.get('ios_flag')=='true' else False
    rincon_id = str(rincon_id)
    posts_list = create_rincon_posts_list(current_user, rincon_id)
    return jsonify(posts_list)


@main.route('/delete_comment/<rincon_id>/<post_id>/<comment_id>', methods=['POST'])
@token_required
def delete_comment(current_user, rincon_id, post_id, comment_id):
    logger_main.info(f"- delete_comment rincon_id:{rincon_id} post_id:{post_id} comment_id: {comment_id}-")

    rincon_id = int(rincon_id)
    post_id = int(post_id)
    comment_id = int(comment_id)

    comment_to_delete = sess.query(RinconsPostsComments).filter_by(
        rincon_id=rincon_id, post_id=post_id, user_id=current_user.id,id=comment_id).first()
    if comment_to_delete:
        print("- exists -")
        sess.query(RinconsPostsComments).filter_by(
            rincon_id=rincon_id, post_id=post_id, user_id=current_user.id,id=comment_id).delete()
        sess.commit()

    post = sess.get(RinconsPosts, post_id)
    post_like_updated = sess.query(RinconsPostsLikes).filter_by(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id).first()

    post_dict = create_rincon_post_dict(current_user,rincon_id, post_id)
    print("----------------")
    print(post_dict)
    print("------------------------")

    return jsonify(post_dict)


@main.route('/send_last_post_id', methods=['POST'])
@token_required
def send_last_post_id(current_user):
    logger_main.info(f"- accessed get_last_post_id endpoint")

    last_post = sess.query(RinconsPosts).order_by(RinconsPosts.id.desc()).first()

    return jsonify({"last_post_id":str(last_post.id)})


@main.route('/claim_a_post_id/<rincon_id>', methods=['POST'])
@token_required
def claim_a_post_id(current_user, rincon_id):
    logger_main.info(f"- accessed claim_a_post_id endpoint")

    # last_post = sess.query(RinconsPosts).order_by(RinconsPosts.id.desc()).first()
    new_post = RinconsPosts(user_id=current_user.id, rincon_id=rincon_id)
    sess.add(new_post)
    sess.commit()
    logger_main.info(f"- sending post_id: {new_post.id}")

    return jsonify({"new_post_id":str(new_post.id)})

@main.route('/receive_rincon_post', methods=['POST'])
@token_required
def receive_rincon_post(current_user):
    logger_main.info(f"- in receive_rincon_post endpoint")

    try:
        request_json = request.json
        rincon_id = int(request_json.get("rincon_id"))
        logger_main.info(f"-Rincon_id {rincon_id}")
        post_id = int(request_json.get("post_id"))
        logger_main.info(f"-Rincon_id {post_id}")
    except Exception as e:
        logger_users.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})
    
    logger_main.info(f"* received data: {request_json.get('rincon_post')}")
    
    post_text = request_json.get("post_text_ios")

    new_post = sess.query(RinconsPosts).filter_by(id=post_id).first()
    new_post.post_text = post_text

    sess.commit()

    return jsonify({"post_received_status":"success","new_post_id":str(post_id)})



@main.route('/receive_image', methods=['POST'])
@token_required
def receive_image(current_user):
    # logger_main.info("------------------------------------------------")
    logger_main.info(f"- in receive_image endpoint")
    # logger_main.info("------------------------------------------------")

    try:
        requestFiles = request.files
        logger_main.info(f"reqeustFiles: {requestFiles}")

    except Exception as e:
        logger_main.info(e)
        logger_main.info(f"requestFiles not found")
        return jsonify({"status": "Image Not found."})


    
    for file_name, post_image in requestFiles.items():
        print("")
        # logger_main.info(requestFiles.getlist())

        post_image_filename = post_image.filename
        # logger_main.info(f"----> post_image_filename: {file_extension} <-- *******")
        filename_no_extension, file_extension = os.path.splitext(post_image_filename)
        logger_main.info(f"-- post_image_filename: {post_image_filename} --")

        # _, user_id, _, post_id,_, img_count = filename_no_extension.split("_")
        _, post_id, _, image_id = filename_no_extension.split('_')
        logger_main.info(f"post_id: {post_id}, img_count: {image_id}")


        ## save to static rincon directory
        # this_rincon_dir_name = f"{rincon_id}_{rincon.name_no_spaces}"
        post_obj = sess.query(RinconsPosts).filter_by(id = post_id).first()
        logger_main.info(f"post_obj")
        logger_main.info(f"post_obj.rincon_id: {post_obj.rincon_id}")
        logger_main.info(f"post_obj.posts_ref_rincons.name_no_spaces: {post_obj.posts_ref_rincons.name_no_spaces}")
        this_rincon_dir_name= str(post_obj.rincon_id) + "_" + post_obj.posts_ref_rincons.name_no_spaces

        path_to_rincon_files = os.path.join(current_app.config.get('DB_ROOT'), "rincon_files",this_rincon_dir_name)
        # requestFiles.getlist('add_file_photo').save(os.path.join(path_to_rincon_files, new_image_name))
        post_image.save(os.path.join(path_to_rincon_files, post_image_filename))

        # filename: uiimageName: user_1_post_66_image_1.jpeg
        # post_containing_image = sess.query(RinconsPosts).filter_by(id=post_id).first()

        logger_main.info(f"---> what is post_obj.image_file_name: {post_obj.image_file_name}")

        if post_obj.image_file_name in ["", None]:
            logger_main.info(f"- Path SHOULD be taken: for {post_image_filename}")
            post_obj.image_file_name = post_image_filename
        else:
            logger_main.info(f"- Path should NOT be taken: for {post_image_filename}")
            post_obj.image_file_name = post_obj.image_file_name + "," + post_image_filename
        
        sess.commit()

    logger_main.info(f"- finished receive_image endpoint")

    return jsonify({"image_received_status":"Successfully send images and executed /receive_image endpoint "})



@main.route('/delete_post/<post_id>', methods=['POST'])
@token_required
def delete_post(current_user, post_id):
    # logger_main.info("------------------------------------------------")
    logger_main.info(f"- in delete_post endpoint")
    # logger_main.info("------------------------------------------------")

    rincon_post = sess.get(RinconsPosts, post_id)

    if rincon_post.image_file_name != None:
        image_names = rincon_post.image_file_name.split(",")
        for image_name in image_names:
            post_image_path_and_name = os.path.join(current_app.config.get('DB_ROOT'), 
                "rincon_files", f"{rincon_post.rincon_id}_{rincon_post.posts_ref_rincons.name_no_spaces}",image_name)
        
            logger_main.info(f"post_image_path_and_name: {post_image_path_and_name}")
            if os.path.exists(post_image_path_and_name):
                os.remove(post_image_path_and_name)
    sess.query(RinconsPosts).filter_by(id = post_id).delete()
    sess.query(RinconsPostsLikes).filter_by(post_id = post_id).delete()
    sess.query(RinconsPostsComments).filter_by(post_id = post_id).delete()
    sess.query(RinconsPostsCommentsLikes).filter_by(post_id = post_id).delete()
    sess.commit()

    return jsonify({"deleted_post_id":post_id})


@main.route('/search_rincons/', methods=['POST'])
@token_required
def search_rincons(current_user):
    # logger_main.info("------------------------------------------------")
    logger_main.info(f"- in search_rincons endpoint")
    # logger_main.info("------------------------------------------------")


    availible_rincons = sess.query(Rincons).filter_by(public=True).all()
    # user = sess.get(Users,current_user.id)
    user_rincons = [i.rincon for i in current_user.rincons ]

    for rincon in user_rincons:
        if rincon not in availible_rincons:
            availible_rincons.append(rincon)

    availible_rincons_sorted = sorted(availible_rincons, key=lambda rincon: rincon.id)

    list_rincons_to_send_ios = []
    for rincon in availible_rincons_sorted:
        list_rincons_to_send_ios.append(create_dict_rincon_ios(current_user.id, rincon.id))

    # list_rincons = create_search_rincon_list(current_user.id)
    # list_rincons_to_send_ios_sorted = sorted(list_rincons_to_send_ios, key=lambda rincon: rincon.id)
    
    # logger_main.info(list_rincons_to_send_ios)
    # logger_main.info("------------------------------------------------")
    
    return jsonify(list_rincons_to_send_ios)


@main.route('/rincon_membership/', methods=['POST'])
@token_required
def rincon_membership(current_user):
    # logger_main.info("------------------------------------------------")
    logger_main.info(f"- in rincon_membership endpoint")

    try:
        request_json = request.json
        rincon_id = int(request_json.get("id"))
        logger_main.info(f"-Rincon_id {rincon_id}")
        # post_id = int(request_json.get("post_id"))
        # logger_main.info(f"-Rincon_id {post_id}")
    except Exception as e:
        logger_main.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})


    user_to_rincon = sess.get(UsersToRincons, (current_user.id, rincon_id))

    status = "unknown"

    if user_to_rincon:
        sess.query(UsersToRincons).filter_by(users_table_id=current_user.id,rincons_table_id=rincon_id).delete()
        logger_main.info(f"-Removed user_id: {current_user.id} to Rincon_id {rincon_id}")
        status="removed user"
    else:
        new_membership = UsersToRincons(users_table_id=current_user.id,rincons_table_id=rincon_id)
        sess.add(new_membership)
        logger_main.info(f"-Added user_id: {current_user.id} to Rincon_id {rincon_id}")
        status="added user"
    
    sess.commit()

    return jsonify({"status":status, "rincon_id":str(rincon_id)})

@main.route('/create_a_rincon/', methods=['POST'])
@token_required
def create_a_rincon(current_user):
    # logger_main.info("------------------------------------------------")
    logger_main.info(f"- in create_a_rincon endpoint")

    try:
        request_json = request.json
        new_rincon_name = request_json.get("new_rincon_name")
        logger_main.info(f"-new_rincon_name: {new_rincon_name}")

    except Exception as e:
        logger_main.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})

    logger_main.info(f"- Phase 1")

    is_public = True if request_json.get("is_public") == "true" else False

    if new_rincon_name != "":

        logger_main.info(f"- Phase 2")
        
        rincon_name_no_spaces = new_rincon_name.replace(" ","_")

        #create_rincon
        new_rincon = Rincons(name= new_rincon_name, manager_id=current_user.id, 
            public=is_public, name_no_spaces = rincon_name_no_spaces)
        sess.add(new_rincon)
        sess.commit()

        logger_main.info(f"-new_rincon added and here's the id:::: {new_rincon.id}")

        #add current_user as member
        new_member = UsersToRincons(users_table_id = current_user.id,
            rincons_table_id= new_rincon.id,
            permission_like=True,
            permission_comment=True,
            permission_post=True,
            permission_admin=True
            )
        sess.add(new_member)
        sess.commit()

        new_rincon_ios = create_dict_rincon_ios(current_user.id, new_rincon.id)
        
        logger_main.info(f"-new_rincon membership:::: {new_rincon_ios.get('member')}")
        
        #create static/rincon_files/<id_rincon_name>
        direcotry_name = f"{new_rincon.id}_{rincon_name_no_spaces}"
        new_dir_path = os.path.join(current_app.config.get('DB_ROOT'),"rincon_files", direcotry_name)

        # print(new_dir_path)
        os.mkdir(new_dir_path)

        
    
    return jsonify(new_rincon_ios)





