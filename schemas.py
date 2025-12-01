from pydantic import BaseModel

class Login(BaseModel):
    password: str

class Mobile(Login):
    mob_no: str

class Email(Login):
    email: str

class Register(BaseModel):
    first_name: str
    last_name: str
    email: str
    mob_no: str
    password: str

class ResponsePayLoad(BaseModel):
    status:bool
    comments: str