from pydantic import BaseModel,Field,EmailStr

class Login(BaseModel):
    password: str 

class Mobile(Login):
    mob_no: str = Field(..., min_length=10,max_length=10,pattern=r'^\d{10}$')

class Email(Login):
    email: EmailStr

class User_details(BaseModel):
    first_name: str = Field(...,min_length=1)
    last_name: str = Field(...,min_length=1)
    email: EmailStr
    mob_no: str = Field(..., min_length=10,max_length=10,pattern=r'^\d{10}$')

class Register(User_details):
    password: str = Field(..., min_length=8)

class LoginResponse(User_details):
    unique_id: int

class ResponsePayLoad(BaseModel):
    status:bool
    comments: str

class LoginResponsePayLoad(ResponsePayLoad):
    data: User_details|None

class TravelData(BaseModel):
    user_id: int
    src_lat: float
    src_long: float
    dest_lat: float
    dest_long: float
    office_lat: float
    office_long: float
    start_time: str
    end_time: str