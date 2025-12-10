from sqlalchemy import create_engine,text
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

PASSWORD = os.environ.get('password')

DATABASE_URL = f"postgresql://postgres.dlbtacxmxlgsjvmtrlsl:{PASSWORD}@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"

engine = create_engine(DATABASE_URL)

def encrypt(password): # Password encryption
    encrypted_pass = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return encrypted_pass.decode('utf-8')

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


def create_user(first_name,last_name,email,mob_no,password)-> dict: # returns Fasle if user is found or error occurs with comments
    user,comments = user_exist(email,mob_no)
    if user:
        return {'status':False ,'comments':comments}
    encrypted_pass = encrypt(password)
    try:
        with engine.begin() as conn:
            query = """Insert INTO users(first_name,last_name,email,mob_no,password)
                        Values(:first_name,:last_name,:email,:mob_no,:password)
                        """
            parm = {
                'first_name':first_name,
                'last_name':last_name,
                'email':email,
                'mob_no':mob_no,
                'password':encrypted_pass
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
        stored_hash = data['password']  # or data.password depending on data type
        del data['password']
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
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