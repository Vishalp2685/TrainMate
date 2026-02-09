from sqlalchemy import create_engine,text
from Utils.utils import verify_passwords,encrypt
import os
from dotenv import load_dotenv

load_dotenv()

PASSWORD = os.environ.get('password')

DATABASE_URL = f"postgresql://postgres.dlbtacxmxlgsjvmtrlsl:{PASSWORD}@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"

engine = create_engine(DATABASE_URL)

def user_exist(email,mob_no)->bool|str: # return True if user is found
    try:
        with engine.connect() as conn:
            user = conn.execute(
                    text("SELECT email FROM users WHERE email = :email or mob_no = :mob_no"), {"email": email, "mob_no": mob_no}
                ).fetchone()
            if user:
                return True,'user already exist'
            else:
                return False, 'user not found'
    except Exception as e:
        print(e)
        print("Databse Error")
        return True ,'Database error'


def create_user(first_name,last_name,email,mob_no,password,gender)-> dict: # returns Fasle if user is found or error occurs with comments
    user,comments = user_exist(email,mob_no)
    if user:
        return {'status':False ,'comments':comments}
    encrypted_pass = encrypt(password)
    try:
        with engine.begin() as conn:
            query = """Insert INTO users(first_name,last_name,email,mob_no,password,gender)
                        Values(:first_name,:last_name,:email,:mob_no,:password,:gender)
                        """
            parm = {
                'first_name':first_name,
                'last_name':last_name,
                'email':email,
                'mob_no':mob_no,
                'password':encrypted_pass,
                'gender':gender
            }
            conn.execute(text(query),parameters=parm)
            conn.commit()
        return {'status':True, 'comments': 'User registered successfully'}
    except Exception as e:
        print(e)
        return {'status':False, 'comments':'(error): while registering'}
        


def authenticate_user(email, mob_no, password) -> dict:
    if email:
        query = "SELECT * FROM users WHERE email = :email"
        params = {"email": email}
    else:
        query = "SELECT * FROM users WHERE mob_no = :mob_no"
        params = {"mob_no": mob_no}

    try:
        with engine.connect() as conn:
            data = conn.execute(text(query), params).fetchone()
        if not data:
            return {'status': False, 'comments': 'User not found','data':data}
        data = dict(data._mapping)
        hashed_password = data['password'] 
        del data['password']
        if verify_passwords(password,hashed_password):
            return {'status': True, 'comments': 'user verified','data':data}
        else:
            return {'status': False, 'comments': 'Invalid password','data':None}
    except Exception as e:
        print(e)
        return {'status': False, 'comments': f'(error): {e} Failed to verify user','data':None}


def save_travel_data(user_id:int,src_lat:float,src_long:float,
                    dest_lat:float,dest_long:float,
                    office_lat:float,office_long:float,
                    start_time:str,end_time:str):
    try:
        check_query = "Select unique_id from users where unique_id = :user_id"
        with engine.connect() as conn:
            user = conn.execute(text(check_query),parameters={'user_id':user_id}).fetchone()
            if not user:
                return {'status':False, 'comments':'user_id not found in database or user not registered','data': None}
        with engine.begin() as conn:
            query = """Insert into travel_data(user_id,src_lat,src_long,
            dest_lat,dest_long,office_lat,office_long,start_time,end_time)
            values(:user_id,:src_lat,:src_long,
            :dest_lat,:dest_long,:office_lat,:office_long,:start_time,:end_time)
            ON CONFLICT (user_id) DO UPDATE SET
                src_lat = EXCLUDED.src_lat,
                src_long = EXCLUDED.src_long,
                dest_lat = EXCLUDED.dest_lat,
                dest_long = EXCLUDED.dest_long,
                office_lat = EXCLUDED.office_lat,
                office_long = EXCLUDED.office_long,
                start_time = EXCLUDED.start_time,
                end_time = EXCLUDED.end_time"""
            param = {'user_id': user_id,
                    'src_lat': src_lat,
                    'src_long': src_long,
                    'dest_lat': dest_lat,
                    'dest_long': dest_long,
                    'office_lat': office_lat,
                    'office_long': office_long,
                    'start_time': start_time,
                    'end_time': end_time
                    }
            conn.execute(text(query),parameters=param)
            conn.commit()
        return {'status':True, 'comments': "user travel data saved"}
    except Exception as e:
        return {'status': False, 'comments': f"Failed to save travel data,[Error]={e}"}
    

def get_users_with_same_destination(userid:int,dest_lat:float,dest_long:float,genders:tuple):
    query = '''SELECT u.unique_id,u.first_name,u.last_name,u.gender,u.email,
                t.src_lat,t.src_long,t.dest_lat,t.dest_long,t.office_lat,t.office_long,t.start_time,t.end_time 
                FROM users u 
                LEFT JOIN travel_data t 
                ON u.unique_id = t.user_id 
                WHERE t.dest_lat = :dest_lat 
                AND t.dest_long = :dest_long 
                AND u.gender IN (:genders)
                AND u.unique_id != :userid;
                '''
    para = {
        'dest_lat' : dest_lat,
        'dest_long' : dest_long,
        'genders' : genders,
        'userid' : userid
    }
    try:
        with engine.connect() as conn:
            travel_data = conn.execute(text(query),parameters=para).fetchall()
    except Exception as e:
        return False,None
    return True,travel_data

def get_user_info_for_recomendation(userid):
    query = '''Select u.unique_id,u.first_name,u.last_name,u.gender,u.email,
                t.src_lat,t.src_long,t.dest_lat,t.dest_long,t.office_lat,t.office_long,t.start_time,t.end_time 
                from users u left join travel_data t on u.unique_id = t.user_id where u.unique_id = :userid
                '''
    param = {'userid':userid}
    status = True
    try:
        with engine.connect() as conn:
            data = conn.execute(text(query),parameters=param).fetchone()
    except Exception as e:
        status = False
    return status,data
    
#_________________________________________________________________________________________________________#


def send_friend_request(sender_id:int,receiver_id:int)-> bool:
        query = '''
                INSERT INTO friend_requests (sender_id, receiver_id)
                    SELECT :sender_id, :receiver_id
                    WHERE NOT EXISTS (
                        SELECT 1 FROM friend_requests
                        WHERE (sender_id = :sender_id AND receiver_id = :receiver_id)
                        OR (sender_id = :receiver_id AND receiver_id = :sender_id)
                    );
                '''
        param = {
            'sender_id':sender_id,
            'receiver_id':receiver_id
        }
        try:
            with engine.begin() as conn:
                conn.execute(text(query),parameters=param)
                conn.commit()
            return True
        except Exception as e:
            return False


def get_pending_requests(user_id):
    query = '''
            SELECT fr.id, fr.sender_id, u.first_name,u.last_name, fr.created_at
            FROM friend_requests fr
            JOIN users u ON fr.sender_id = u.unique_id
            WHERE fr.receiver_id = :user_id
            AND fr.status = 'pending';
            '''
    param = {'user_id':user_id}
    try:
        with engine.connect() as conn:
            requests = conn.execute(text(query),parameters=param).fetchall()
        return {'status':True,'requests':requests}
    except Exception as e:
        return {'status': False,'requests':None}


def get_pending_sent_requests(user_id:int):
    query = '''SELECT *
            FROM friend_requests
            WHERE sender_id = :user_id
            AND status = 'pending';
            '''
    param = {'user_id':user_id}
    try:
        with engine.connect() as conn:
            requests = conn.execute(text(query),parameters=param).fetchall()
        return True,requests
    except Exception as e:
        return False,[]
    

def accept_friend_request(sender_id:int,receiver_id:int):
    query = '''
        BEGIN;

        WITH deleted AS (
            DELETE FROM friend_requests
            WHERE sender_id = :sender_id
            AND receiver_id = :receiver_id
            AND status = 'pending'
            RETURNING sender_id, receiver_id
        )
        INSERT INTO friends (user1_id, user2_id)
        SELECT LEAST(sender_id, receiver_id),
            GREATEST(sender_id, receiver_id)
        FROM deleted;

        COMMIT;

        '''
    param = {
        'sender_id':sender_id,
        'receiver_id':receiver_id
    }
    try:
        with engine.begin() as conn:
            conn.execute(text(query),parameters=param)
            conn.commit()
        return True
    except Exception as e:
        return False
    

def reject_friend_request(user_id:int,sender_id:int):
    query = '''UPDATE friend_requests
                SET status = 'rejected'
                WHERE sender_id = :sender_id
                AND receiver_id = :user_id;
                '''
    param = {
        'user_id':user_id,
        'sender_id': sender_id
    }
    try:
        with engine.begin() as conn:
            conn.execute(text(query),parameters=param)
            conn.commit()
        return True
    except Exception as e:
        return False
    

def cancel_friend_request(user_id:int, receiver_id:int):
    query = '''DELETE FROM friend_requests
            WHERE sender_id = :sender_id
            AND receiver_id = :receiver_id
            AND status = 'pending';
            '''
    param = {
        'sender_id':user_id,
        'receiver_id':receiver_id
    }

    try:
        with engine.begin() as conn:
            conn.execute(text(query),parameters=param)
            conn.commit()
        return True
    except Exception as e:
        return False
    
def get_all_friends(user_id):
    query = '''SELECT u.unique_id,u.first_name,u.last_name,u.email,u.gender
            FROM friends f
            JOIN users u 
            ON u.unique_id = CASE 
                WHEN f.user1_id = :user_id THEN f.user2_id
                ELSE f.user1_id
            END
            WHERE f.user1_id = :user_id OR f.user2_id = :user_id;
            '''
    param = {
        'user_id' : user_id
    }
    try:
        with engine.connect() as conn:
            friends = conn.execute(text(query),parameters=param).fetchall()
            print(friends)
        return True,friends
    except Exception as e:
        print(e)
        return False,[]
    
def unfriend(user_id:int,friend_id:int):
    query = '''DELETE FROM friends
            WHERE (user1_id = :user_id AND user2_id = :friend_id)
            OR (user1_id = :friend_id AND user2_id = :user_id);
            '''
    param = {
        'user_id' : user_id,
        'friend_id' : friend_id
    }
    try:
        with engine.begin() as conn:
            conn.execute(text(query),parameters=param)
            conn.commit()
        return True
    except Exception as e:
        return False
    
def are_friends(user_id:int,friend_id:int):
    '''
    Return True or False if no error, else return 'Error' string
    Docstring for are_friends
    
    :param user_id: Description
    :type user_id: int
    :param friend_id: Description
    :type friend_id: int
    '''
    query = '''SELECT 1
            FROM friends
            WHERE (user1_id = :user_id AND user2_id = :friend_id)
            OR (user1_id = :friend_id AND user2_id = :user_id);
            '''
    param = {
        'user_id':user_id,
        'friend_id':friend_id
    }
    try:
        with engine.connect() as conn:
            data = conn.execute(text(query),parameters=param).fetchone()
        if data:
            return True
        else:
            return False
    except Exception as e:
        return "Error"
    

def block_user(user_id:int,friend_id):
    query = '''INSERT INTO blocked_users (blocker_id, blocked_id)
            VALUES (:blocker_id, :blocked_id);
            '''
    param = {
        'blocker_id' : user_id,
        'blocked_id' : friend_id
    }
    query2 = '''DELETE FROM friends
            WHERE (user1_id = :blocker_id AND user2_id = :blocked_id)
            OR (user1_id = :blocked_id AND user2_id = :blocker_id);
            '''
    try:
        with engine.begin() as conn:
            conn.execute(text(query),parameters=param)
            conn.execute(text(query2),parameters=param)
            conn.commit()
        return True
    except Exception as e:
        return False
    

def is_blocked(sender_id:int,receiver_id:int):
    '''
    Returns bool value for execution with no error, but returns 'Error' if error occurs
    '''
    query = '''SELECT 1
            FROM blocked_users
            WHERE (blocker_id = :sender_id AND blocked_id = :receiver_id)
            OR (blocker_id = :receiver_id AND blocked_id = :sender_id);
            '''
    param = {
        'sender_id':sender_id,
        'receiver_id':receiver_id
    }
    try:
        with engine.connect() as conn:
            data = conn.execute(text(query),parameters=param).fetchone()
        return True if data else False
    except Exception as e:
        return 'Error'