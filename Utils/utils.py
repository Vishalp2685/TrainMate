import bcrypt

def encrypt(password:str)->str:
    encrypted_pass = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return encrypted_pass.decode('utf-8')


def verify_passwords(plain_password:str,hashed_password:str)->bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def convert_recommendation_data_to_dict(users:list)-> list[dict]:
    users_list = []
    for user in users:
        info = {
            'user_id': user[0],
            'first_name': user[1],
            'last_name' : user[2],
            'gender' : user[3],
            'email' : user[4],
            'src_lat': user[5],
            'src_long' : user[6],
            'dest_lat' : user[7],
            'dest_long' : user[8],
            'office_lat' : user[9],
            'office_long' : user[10],
            'start_time' : user[11],
            'end_time' : user[12]
        }
        users_list.append(info)
    return users_list

        
def convert_pending_reuqest_to_dict(requests):
    pending_request = []
    for request in requests:
        info = {
            'id':request[0],
            'sender_id':request[1],
            'first_name':request[2],
            'last_name':request[3],
            'created_at':request[4]
        }
        pending_request.append(info)
    return pending_request

def convert_sent_pending_to_dict(requests):
    pending_request = []
    for request in requests:
        info = {
            'id': request[0],
            'sender_id' : request[1],
            'receiver_id' : request[2],
            'status': request[3],
            'created_at' : request[4]
        }
        pending_request.append(info)
    return pending_request

def convert_friend_list_to_dict(friends):
    friends_list = []
    for friend in friends:
        info = {
            'user_id':friend[0],
            'first_name':friend[1],
            'last_name':friend[2],
            'email':friend[3],
            'gender':friend[4]
        }
        friends_list.append(info)
    return friends_list