from pydantic import BaseModel,Field,EmailStr

class Login(BaseModel):
    password: str 

class Mobile(Login):
    mob_no: str = Field(..., min_length=10,max_length=10,pattern=r'^\d{10}$')

class Email(Login):
    email: EmailStr

class Register(BaseModel):
    first_name: str = Field(...,min_length=1)
    last_name: str = Field(...,min_length=1)
    email: EmailStr
    mob_no: str = Field(..., min_length=10,max_length=10,pattern=r'^\d{10}$')
    password: str = Field(..., min_length=8)

class ResponsePayLoad(BaseModel):
    status:bool
    comments: str