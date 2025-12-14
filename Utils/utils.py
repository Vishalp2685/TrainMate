import bcrypt

def encrypt(password:str)->str:
    encrypted_pass = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return encrypted_pass.decode('utf-8')


def verify_passwords(plain_password:str,hashed_password:str)->bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))