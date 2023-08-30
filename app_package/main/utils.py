import logging
from logging.handlers import RotatingFileHandler
from tr01_models import sess, Users, Rincons, RinconsPosts, UsersToRincons, \
    RinconsPostsComments, RinconsPostsLikes, RinconsPostsCommentsLikes
import os
import re
import urlextract
from flask_login import current_user
from datetime import datetime


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


def extract_urls_info(feed_obj_text):
    extractor = urlextract.URLExtract()
    urls = extractor.find_urls(feed_obj_text)
    
    if len(urls) == 0:
        return {"text":feed_obj_text}


    url_dict = {}
    
    # Handle the case where the first character(s) is a URL
    if feed_obj_text.startswith(urls[0]):
        url_dict[f"url01"] = urls[0]
        feed_obj_text = feed_obj_text[len(urls[0]):]
    
    # # Handle the case where the last character(s) is a URL
    # if feed_obj_text.endswith(urls[-1]):
    #     url_dict[f"url{len(urls):02d}"] = urls[-1]
    #     feed_obj_text = feed_obj_text[:-len(urls[-1])]
    
    # Handle all other URLs
    for i, url in enumerate(urls):
        if i == 0 and "url01" in url_dict:
            continue
        if i == len(urls) - 1 and f"url{len(urls):02d}" in url_dict:
            continue
        split_text = feed_obj_text.split(url)
        url_dict[f"text{i+1:02d}"] = split_text[0]
        url_dict[f"url{i+1:02d}"] = url
        feed_obj_text = split_text[1]
    
    # Handle any remaining text after the last URL
    if feed_obj_text:
        url_dict[f"text{len(urls)+1:02d}"] = feed_obj_text
    
    # url_dict_list =[{i,j} for i,j in url_dict.items()]
    # url_tup_list =[(i,j) for i,j in url_dict.items()]


    return url_dict


def create_rincon_posts_list(current_user, rincon_id):

    rincon = sess.get(Rincons,rincon_id)

    rincon_posts = []
    if current_user.is_authenticated:
        user_likes = current_user.post_like
        user_likes_this_rincon = [like.post_id  for like in user_likes if like.rincon_id == rincon.id]


    for i in rincon.posts:
        rincon_posts.append(create_rincon_post_dict(current_user,rincon_id, i.id))

    rincon_posts = sorted(rincon_posts, key=lambda d: d['date_for_sorting'], reverse=True)

    return rincon_posts


def create_empty_rincon_post_dict(current_user,rincon_id ):

    rincon = sess.get(Rincons,rincon_id)

    # rincon_posts = []
    # if current_user.is_authenticated:
    #     user_likes = current_user.post_like
        # user_likes_this_rincon = [like.post_id  for like in user_likes if like.rincon_id == rincon.id]

    # post = sess.query(RinconsPosts).filter_by(id=post_id).first()
    # for i in rincon.posts:
    post_dict = {}

    post_dict['post_id'] = "999"
    post_dict['date_for_sorting'] = datetime.now()
    post_dict['date_for_sorting_ios'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    post_dict['username'] = ""
    post_dict['user_id'] = "1"
    post_dict['rincon_id'] = str(rincon_id)
    post_dict['post_text_ios'] = "No Posts Yet"
    post_dict['liked'] = False
    post_dict['like_count'] = 0

    return [post_dict]

def create_rincon_post_dict(current_user,rincon_id, post_id):

    rincon = sess.get(Rincons,rincon_id)

    # rincon_posts = []
    if current_user.is_authenticated:
        user_likes = current_user.post_like
        user_likes_this_rincon = [like.post_id  for like in user_likes if like.rincon_id == rincon.id]

    post = sess.query(RinconsPosts).filter_by(id=post_id).first()
    # for i in rincon.posts:
    post_dict = {}

    post_dict['post_id'] = str(post.id)
    post_dict['date_for_sorting'] = post.time_stamp_utc
    post_dict['date_for_sorting_ios'] = post.time_stamp_utc.strftime("%Y-%m-%d %H:%M:%S.%f")
    post_dict['username'] = sess.get(Users,post.user_id).username
    post_dict['user_id'] = str(sess.get(Users,post.user_id).id)
    post_dict['rincon_id'] = str(rincon_id)

    if post.post_text == None:
        post_dict['post_text'] = ""
    else:
        post_dict['post_text'] = extract_urls_info(post.post_text)
    
    post_dict['post_text_ios'] = post.post_text

    post_dict['image_exists'] = False if post.image_file_name == None else True
    
    post_dict['image_path'] = f"{rincon_id}_{rincon.name_no_spaces}"

    if post.image_file_name:
        if not post.image_file_name.find(","):
            post_dict['image_filename'] = [post.image_file_name]
        else:
            post_dict['image_filename'] = post.image_file_name.split(",")
    
    post_dict["image_filenames_ios"] = post.image_file_name

    post_dict['video_exists'] = False if post.video_file_name in ["", None] else True
    
    post_dict['video_path'] = f"{rincon_id}_{rincon.name_no_spaces}"

    if post.video_file_name:
        post_dict['video_file_name'] = post.video_file_name





    post_dict['date'] = post.time_stamp_utc.strftime("%m/%d/%y %H:%M")
    
    if current_user.is_authenticated:
        post_dict['liked'] = False if post.id not in user_likes_this_rincon else True
        # post_dict['liked_ios'] = str(post_dict['liked'])
    
    post_dict['like_count'] = len(post.post_like)

    if current_user.is_authenticated:
        post_dict['delete_post_permission'] = False if post.user_id != current_user.id else True
    else:
        post_dict['delete_post_permission'] = False
    
    post_dict['delete_post_permission_ios'] = str(post_dict['delete_post_permission'])

    
    comments_list = []
    
    for comment in post.comments:
        post_comment_dict = {}
        post_comment_dict['date'] = comment.time_stamp_utc.strftime("%m/%d/%y %H:%M")
        post_comment_dict['username'] = sess.get(Users,comment.user_id).username
        post_comment_dict['comment_text'] = comment.comment_text


        if current_user.is_authenticated:
            post_comment_dict['delete_comment_permission'] = False if comment.user_id != current_user.id else True
        else:
            post_comment_dict['delete_comment_permission'] = False
        
        post_comment_dict['comment_id'] = str(comment.id)

        comments_list.append(post_comment_dict)

    post_dict['comments'] = comments_list


    return post_dict


def addUserToRincon(user_id, rincon_id):

    new_member = UsersToRincons(users_table_id = user_id, rincons_table_id= rincon_id)
    sess.add(new_member)
    sess.commit()
    logger_main.info(f"- User {user_id} successfully added to rincon_id: {rincon_id} -")

def addUserToRinconAccessNotAdmin(user_id, rincon_id):

    new_member = UsersToRincons(users_table_id = user_id,
        rincons_table_id= rincon_id,
        permission_like=True,
        permission_comment=True,
        permission_post=True,
        permission_admin=False
        )
    sess.add(new_member)
    sess.commit()
    logger_main.info(f"- User {user_id} successfully added to rincon_id: {rincon_id} -")

def addUserToRinconFullAccess(user_id, rincon_id):

    new_member = UsersToRincons(users_table_id = user_id,
        rincons_table_id= rincon_id,
        permission_like=True,
        permission_comment=True,
        permission_post=True,
        permission_admin=True
        )
    sess.add(new_member)
    sess.commit()
    logger_main.info(f"- User {user_id} successfully added to rincon_id: {rincon_id} -")


def create_dict_rincon_ios(user_id, rincon_id):
    # logger_main.info(f"- create_dict_rincon_ios: user_id: {user_id}, rincon_id: {rincon_id}")
    rincon = sess.get(Rincons, rincon_id)
    # logger_main.info(f"- rincon: {rincon}")
    user_to_rincon = sess.get(UsersToRincons,(user_id,rincon_id))
    # logger_main.info(f"- user_to_rincon: {user_to_rincon}")
    

    dict_rincon_ios = {}
    dict_rincon_ios['id']=str(rincon_id)
    dict_rincon_ios['name']=rincon.name
    dict_rincon_ios['name_no_spaces']=rincon.name_no_spaces
    dict_rincon_ios['public_status']=rincon.public
    if user_to_rincon:
        dict_rincon_ios['member']=True
        dict_rincon_ios['permission_view']=user_to_rincon.permission_view
        dict_rincon_ios['permission_like']=user_to_rincon.permission_like
        dict_rincon_ios['permission_comment']=user_to_rincon.permission_comment
        dict_rincon_ios['permission_post']=user_to_rincon.permission_post
        dict_rincon_ios['permission_admin']=user_to_rincon.permission_admin
    # else:
    #     dict_rincon_ios['permission_view']=True
    #     dict_rincon_ios['permission_like']=False
    #     dict_rincon_ios['permission_comment']=False
    #     dict_rincon_ios['permission_post']=False
    #     dict_rincon_ios['permission_admin']=False

    return dict_rincon_ios



def search_rincon_based_on_name_no_spaces(name_no_spaces):
    rincons = sess.query(Rincons).all()
    for rincon in rincons:
        if rincon.name_no_spaces == 'Town_Hall_🏫':
            return(rincon)
    
    return "not found"
