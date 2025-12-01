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
        query = "SELECT password FROM users WHERE email = :email"
        params = {"email": email}
    else:
        query = "SELECT password FROM users WHERE mob_no = :mob_no"
        params = {"mob_no": mob_no}

    try:
        with engine.connect() as conn:
            row = conn.execute(text(query), params).fetchone()

        if not row:
            return {'status': False, 'comments': 'User not found'}

        stored_hash = row[0]  # or row.password depending on row type

        if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
            return {'status': True, 'comments': 'user verified'}
        else:
            return {'status': False, 'comments': 'Invalid password'}
    except Exception as e:
        print(e)
        return {'status': False, 'comments': '(error): Failed to verify user'}



    