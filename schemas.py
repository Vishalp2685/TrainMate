from pydantic import BaseModel,Field,EmailStr
from enum import Enum
from datetime import datetime

class Login(BaseModel):
    password: str 

class GenderEnum(str, Enum):
    male = "male"
    female = "female"  

class User_details(BaseModel):
    first_name: str = Field(...,min_length=1)
    last_name: str = Field(...,min_length=1)
    email: EmailStr
    mob_no: str = Field(..., min_length=10,max_length=10,pattern=r'^\d{10}$')
    gender: GenderEnum

class Register(User_details):
    password: str = Field(..., min_length=8)

class LoginResponse(User_details):
    unique_id: int

class ResponsePayLoad(BaseModel):
    status:bool
    comments: str

class LoginResponsePayLoad(ResponsePayLoad):
    data: LoginResponse | None = None
    access_token: str | None = None
    refresh_token: str | None = None

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

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    status:bool
    comments:str
    access_token: str

class recommendation_data(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    gender: GenderEnum
    email: EmailStr
    src_lat: float
    src_long: float
    dest_lat: float
    dest_long: float
    office_lat: float
    office_long: float
    start_time: datetime|None
    end_time: datetime|None

class Recommendations(BaseModel):
    status: bool
    comments:str
    users_info:list[recommendation_data]
    
class StatusEnum(str,Enum):
    pending = 'pending'
    accepted = 'accepted'
    rejected = 'rejected'  

class Friend(BaseModel):
    id:int
    sender_id:int
    created_at:datetime

class FriendTable(Friend):
    receiver_id:int
    status: StatusEnum

class UserNameandDetails(Friend):
    first_name:str
    last_name:str

class PendingRequestPayload(ResponsePayLoad):
    request: list[UserNameandDetails | None]

class SentRequestPayload(ResponsePayLoad):
    requests: list[FriendTable|None]
    status:bool

class FriendDetails(BaseModel):
    user_id:int
    first_name:str
    last_name:str
    email:EmailStr
    gender: GenderEnum

class FriendListPayload(ResponsePayLoad):
    friends:list[FriendDetails|None]

class SenderId(BaseModel):
    sender_id: int

class ReceiverId(BaseModel):
    receiver_id: int

class FriendIDd(BaseModel):
    friend_id: int
