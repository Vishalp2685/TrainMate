from sqlalchemy import create_engine,text
from Utils.utils import verify_passwords,encrypt,convert_friens_at_station
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import hashlib

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


def get_userid(email:str):
    query = 'Select unique_id from users where email =:email'
    param = {
        'email' :email
    }

    try:
        with engine.connect() as conn:
            data = conn.execute(text(query),parameters=param).fetchone()
        if data:
            return data[0]
        return None
    except Exception as e:
        print('Error getting unique_id for token generation')
        return None


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
    # Select explicit, aliased columns to avoid duplicate column names from JOINs
    base_query = (
        "SELECT u.unique_id AS user_id, u.first_name, u.last_name, u.email AS email, u.mob_no, u.gender, u.password,"
        " t.src_lat AS src_lat, t.src_long AS src_long, t.dest_lat AS dest_lat, t.dest_long AS dest_long,"
        " t.start_time AS start_time, t.end_time AS end_time, t.office_name AS office_name, t.source_name AS source_name, t.dest_name AS dest_name"
        " FROM users u LEFT JOIN travel_data t ON u.unique_id = t.user_id"
    )

    if email:
        query = base_query + " WHERE u.email = :email"
        params = {"email": email}
    else:
        query = base_query + " WHERE u.mob_no = :mob_no"
        params = {"mob_no": mob_no}

    try:
        with engine.connect() as conn:
            data = conn.execute(text(query), params).fetchone()
        if not data:
            return {'status': False, 'comments': 'User not found','data':data}
        data = dict(data._mapping)
        # password is stored under the explicit key 'password'
        hashed_password = data.get('password')
        if 'password' in data:
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
                    office_name:str,
                    start_time:str,end_time:str,
                    source_name:str, dest_name:str):
    try:
        check_query = "Select unique_id from users where unique_id = :user_id"
        with engine.connect() as conn:
            user = conn.execute(text(check_query),parameters={'user_id':user_id}).fetchone()
            if not user:
                return {'status':False, 'comments':'user_id not found in database or user not registered','data': None}
        with engine.begin() as conn:
            query = """Insert into travel_data(user_id,src_lat,src_long,
            dest_lat,dest_long,office_name,start_time,end_time,source_name,dest_name)
            values(:user_id,:src_lat,:src_long,
            :dest_lat,:dest_long,:office_name,:start_time,:end_time,:source_name,:dest_name)
            ON CONFLICT (user_id) DO UPDATE SET
                src_lat = EXCLUDED.src_lat,
                src_long = EXCLUDED.src_long,
                dest_lat = EXCLUDED.dest_lat,
                dest_long = EXCLUDED.dest_long,
                office_name = EXCLUDED.office_name,
                start_time = EXCLUDED.start_time,
                end_time = EXCLUDED.end_time,
                source_name = EXCLUDED.source_name,
                dest_name = EXCLUDED.dest_name
                """
            param = {'user_id': user_id,
                    'src_lat': src_lat,
                    'src_long': src_long,
                    'dest_lat': dest_lat,
                    'dest_long': dest_long,
                    'office_name': office_name,
                    'start_time': start_time,
                    'end_time': end_time,
                    'source_name' : source_name,
                    'dest_name': dest_name
                    }
            conn.execute(text(query),parameters=param)
            conn.commit()
        return {'status':True, 'comments': "user travel data saved"}
    except Exception as e:
        return {'status': False, 'comments': f"Failed to save travel data,[Error]={e}"}
    

def get_user_data(unique_id:int):
    query = '''Select u.unique_id,u.first_name,u.last_name,u.email,
        u.mob_no,u.gender,t.src_lat,t.src_long,t.dest_lat,
        t.dest_long,t.start_time,t.end_time,t.office_name,t.source_name,t.dest_name 
        from users u join travel_data t on u.unique_id = t.user_id 
        where u.unique_id =:unique_id
        '''
    param = {'unique_id':unique_id}
    try:
        with engine.connect() as conn:
            data = conn.execute(text(query),parameters=param).fetchall()
            if data:
                data = data[0]
                user_info = {
                    'user_id':data[0],
                    'first_name':data[1],
                    'last_name':data[2],
                    'email':data[3],
                    'mob_no':data[4],
                    'gender':data[5],
                    'src_lat':data[6],
                    'src_long':data[7],
                    'dest_lat':data[8],
                    'dest_long':data[9],
                    'start_time':data[10],
                    'end_time':data[11],
                    'office_name':data[12],
                    'source_name':data[13],
                    'dest_name':data[14]
                }
                return user_info
            return None
    except Exception as e:
        return None

def get_users_with_same_destination(userid:int,dest_lat:float,dest_long:float,genders:tuple):
    query = '''SELECT u.unique_id,u.first_name,u.last_name,u.gender,u.email,
                t.src_lat,t.src_long,t.dest_lat,t.dest_long,t.office_name,t.start_time,t.end_time 
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
    query = '''SELECT f.*, u.first_name, u.last_name
FROM friend_requests f
LEFT JOIN users u ON f.sender_id = u.unique_id
WHERE f.sender_id = :user_id
AND f.status = 'pending';
            '''
    param = {'user_id':user_id}
    try:
        with engine.connect() as conn:
            requests = conn.execute(text(query),parameters=param).fetchall()
        return True,requests
    except Exception as e:
        print(e)
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
    query = '''SELECT 
                u.unique_id,
                u.first_name,
                u.last_name,
                u.email,
                u.gender,
                td.source_name,
                td.dest_name,
                td.src_lat,
                td.src_long,
                td.dest_lat,
                td.dest_long
            FROM friends f
            JOIN users u 
            ON u.unique_id = CASE 
                    WHEN f.user1_id = :user_id THEN f.user2_id
                    ELSE f.user1_id
                END
            LEFT JOIN travel_data td 
            ON td.user_id = u.unique_id
            WHERE f.user1_id = :user_id 
            OR f.user2_id = :user_id;
            '''
    param = {
        'user_id' : user_id
    }
    try:
        with engine.connect() as conn:
            friends = conn.execute(text(query),parameters=param).fetchall()
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
        print(e)
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

def hash_token(token: str) -> str:
    """Hash a token using SHA256"""
    return hashlib.sha256(token.encode()).hexdigest()


def store_refresh_token(user_id: int, device_id: str, token: str, expires_in_days: int = 45) -> dict:
    """
    Store a new refresh token in the database
    
    Args:
        user_id: User's unique_id
        device_id: Device identifier
        token: The actual refresh token (will be hashed before storing)
        expires_in_days: Days until token expires (default 45)
    
    Returns:
        dict with status and token_id
    """
    token_hash = hash_token(token)
    expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    query = """
    INSERT INTO refresh_tokens(user_id, device_id, token_hash, expires_at)
    VALUES (:user_id, :device_id, :token_hash, :expires_at)
    RETURNING id;
    """
    param = {
        'user_id': user_id,
        'device_id': device_id,
        'token_hash': token_hash,
        'expires_at': expires_at
    }
    
    try:
        with engine.begin() as conn:
            result = conn.execute(text(query), param).fetchone()
        return {'status': True, 'token_id': result[0]}
    except Exception as e:
        print(f"Error storing refresh token: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def validate_refresh_token(user_id: int, device_id: str, token: str) -> dict:
    """
    Validate a refresh token
    
    Args:
        user_id: User's unique_id
        device_id: Device identifier
        token: The refresh token to validate
    
    Returns:
        dict with status and validation result
    """
    token_hash = hash_token(token)
    
    query = """
    SELECT id, expires_at, revoked_at FROM refresh_tokens
    WHERE user_id = :user_id AND device_id = :device_id AND token_hash = :token_hash;
    """
    param = {
        'user_id': user_id,
        'device_id': device_id,
        'token_hash': token_hash
    }
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), param).fetchone()
        
        if not result:
            return {'status': False, 'message': 'Token not found'}
        
        token_id, expires_at, revoked_at = result
        
        if revoked_at is not None:
            return {'status': False, 'message': 'Token has been revoked'}
        
        if datetime.utcnow() > expires_at:
            return {'status': False, 'message': 'Token has expired'}
        
        # Update last_used_at
        update_query = "UPDATE refresh_tokens SET last_used_at = :now WHERE id = :id;"
        with engine.begin() as conn:
            conn.execute(text(update_query), {'id': token_id, 'now': datetime.utcnow()})
        
        return {'status': True, 'token_id': token_id}
    except Exception as e:
        print(f"Error validating refresh token: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def revoke_refresh_token(user_id: int, device_id: str) -> dict:
    """
    Revoke a refresh token for a specific device (logout one device)
    
    Args:
        user_id: User's unique_id
        device_id: Device identifier
    
    Returns:
        dict with status
    """
    query = """
    UPDATE refresh_tokens 
    SET revoked_at = :now
    WHERE user_id = :user_id AND device_id = :device_id AND revoked_at IS NULL;
    """
    param = {
        'user_id': user_id,
        'device_id': device_id,
        'now': datetime.utcnow()
    }
    
    try:
        with engine.begin() as conn:
            conn.execute(text(query), param)
        return {'status': True, 'message': 'Token revoked successfully'}
    except Exception as e:
        print(f"Error revoking refresh token: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def revoke_all_refresh_tokens(user_id: int) -> dict:
    """
    Revoke all refresh tokens for a user (logout all devices)
    
    Args:
        user_id: User's unique_id
    
    Returns:
        dict with status
    """
    query = """
    UPDATE refresh_tokens 
    SET revoked_at = :now
    WHERE user_id = :user_id AND revoked_at IS NULL;
    """
    param = {
        'user_id': user_id,
        'now': datetime.utcnow()
    }
    
    try:
        with engine.begin() as conn:
            conn.execute(text(query), param)
        return {'status': True, 'message': 'All tokens revoked successfully'}
    except Exception as e:
        print(f"Error revoking all refresh tokens: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def register_device_token(user_id: int, device_id: str, fcm_token: str, device_name: str = None, device_type: str = None) -> dict:
    """
    Store or update a device's FCM token for push notifications
    
    Args:
        user_id: User's unique_id
        device_id: Device identifier
        fcm_token: Firebase Cloud Messaging token
        device_name: Name of the device (optional)
        device_type: Type of device - 'android' or 'ios' (optional)
    
    Returns:
        dict with status
    """
    query = """
    INSERT INTO device_tokens(user_id, device_id, fcm_token, device_name, device_type)
    VALUES (:user_id, :device_id, :fcm_token, :device_name, :device_type)
    ON CONFLICT (user_id, device_id) DO UPDATE
    SET fcm_token = :fcm_token, device_name = :device_name, device_type = :device_type, last_used_at = :now;
    """
    param = {
        'user_id': user_id,
        'device_id': device_id,
        'fcm_token': fcm_token,
        'device_name': device_name,
        'device_type': device_type,
        'now': datetime.utcnow()
    }
    
    try:
        with engine.begin() as conn:
            conn.execute(text(query), param)
        return {'status': True, 'message': 'Device token registered successfully'}
    except Exception as e:
        print(f"Error registering device token: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def get_user_devices(user_id: int) -> dict:
    """
    Get all active devices for a user with their FCM tokens (for notifications)
    
    Args:
        user_id: User's unique_id
    
    Returns:
        dict with status and list of devices
    """
    query = """
    SELECT d.device_id, d.fcm_token, d.device_name, d.device_type, 
           d.last_used_at, CASE WHEN r.revoked_at IS NULL THEN true ELSE false END as is_active
    FROM device_tokens d
    LEFT JOIN refresh_tokens r ON d.user_id = r.user_id AND d.device_id = r.device_id
    WHERE d.user_id = :user_id
    GROUP BY d.device_id, d.fcm_token, d.device_name, d.device_type, d.last_used_at, r.revoked_at;
    """
    param = {'user_id': user_id}
    
    try:
        with engine.connect() as conn:
            results = conn.execute(text(query), param).fetchall()
        
        devices = []
        for row in results:
            devices.append({
                'device_id': row[0],
                'fcm_token': row[1],
                'device_name': row[2],
                'device_type': row[3],
                'last_used_at': row[4],
                'is_active': row[5]
            })
        
        return {'status': True, 'devices': devices}
    except Exception as e:
        print(f"Error getting user devices: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def get_active_device_fcm_tokens(user_id: int) -> list:
    """
    Get FCM tokens for all active devices of a user (for sending notifications)
    
    Args:
        user_id: User's unique_id
    
    Returns:
        list of FCM tokens
    """
    query = """
    SELECT d.fcm_token
    FROM device_tokens d
    LEFT JOIN refresh_tokens r ON d.user_id = r.user_id AND d.device_id = r.device_id
    WHERE d.user_id = :user_id AND (r.revoked_at IS NULL OR r.id IS NULL);
    """
    param = {'user_id': user_id}
    
    try:
        with engine.connect() as conn:
            results = conn.execute(text(query), param).fetchall()
        
        tokens = [row[0] for row in results if row[0]]
        return tokens
    except Exception as e:
        print(f"Error getting FCM tokens: {e}")
        return []


def get_user_by_refresh_token(device_id: str, token: str) -> int | None:
    """
    Find user_id by their refresh token and device_id
    
    Args:
        device_id: Device identifier
        token: The refresh token to look up
    
    Returns:
        user_id if found and valid, None otherwise
    """
    token_hash = hash_token(token)
    
    query = """
    SELECT user_id FROM refresh_tokens
    WHERE device_id = :device_id AND token_hash = :token_hash
    AND revoked_at IS NULL AND expires_at > :now;
    """
    param = {
        'device_id': device_id,
        'token_hash': token_hash,
        'now': datetime.utcnow()
    }
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), param).fetchone()
        
        if result:
            return result[0]
        return None
    except Exception as e:
        print(f"Error getting user by refresh token: {e}")
        return None

def set_user_status(user_id,at_source):
    query = '''INSERT INTO user_presence (user_id, is_active, last_seen)
            VALUES (:user_id, TRUE, NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET
            is_active = TRUE,
            last_seen = NOW(),
            at_source = :at_source;'''
    
    param = {'user_id':user_id,
             'at_source':at_source
             }

    try:
        with engine.begin() as conn:
            conn.execute(text(query),parameters=param)
        conn.commit()
        return True
    except Exception as e:
        print(f'Set_status_error: {e}')
        return False
    
def show_friends_availabe_at_station(user_id):
    query = """SELECT u.unique_id, u.first_name, u.last_name, u.mob_no,p.at_source
            FROM users u
            JOIN user_presence p ON u.unique_id = p.user_id
            JOIN friends f 
            ON (f.user1_id = :me AND f.user2_id = u.unique_id)
            OR (f.user2_id = :me AND f.user1_id = u.unique_id)
            WHERE p.is_active = TRUE
            AND p.last_seen >= NOW() - INTERVAL '15 minutes';
            """
    param = {
        'me':user_id
    }
    try:
        with engine.connect() as conn:
            users = conn.execute(text(query),parameters=param).fetchall()
        users = convert_friens_at_station(users=users)
        return users
    except Exception as e:
        print(f"[Error] in show_available_friends: {e}")
        return []