from fastapi import FastAPI, Depends, HTTPException, status
from database import *
from schemas import Register, ResponsePayLoad, TravelData, LoginResponsePayLoad, RefreshTokenRequest,RefreshTokenResponse,Recommendations,PendingRequestPayload,SentRequestPayload,FriendListPayload
from auth.auth import create_access_token, create_refresh_token, verify_refresh_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from reccomend import get_reccomendations
from Utils.utils import convert_recommendation_data_to_dict,convert_pending_reuqest_to_dict,convert_sent_pending_to_dict,convert_friend_list_to_dict
app = FastAPI()

@app.get('/ping')
async def ping() -> dict:
    return {'status': 'ok'}


@app.post('/login',response_model=LoginResponsePayLoad)
async def login(data: OAuth2PasswordRequestForm = Depends()):
    username = data.username
    password = data.password
    if '@' in username:
        user = authenticate_user(email=username,password=password,mob_no=None)
    else:
        user = authenticate_user(mob_no=username,password=password,email=None)
    if user['status']:
        access_token = create_access_token({"user_id": str(user['data']['unique_id'])})
        refresh_token = create_refresh_token({"user_id": str(user['data']['unique_id'])})
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    return LoginResponsePayLoad(
            status=True,
            comments="Login successful",
            data=user['data'],
            access_token=access_token,
            refresh_token=refresh_token
        )

@app.post('/register/', response_model=ResponsePayLoad)
async def register(data: Register) -> dict:
    auth = create_user(first_name=data.first_name, last_name=data.last_name, email=data.email, mob_no=data.mob_no, password=data.password,gender=data.gender)
    return ResponsePayLoad(status=auth['status'], comments=auth['comments'])

@app.post('/save_travel_data', response_model=ResponsePayLoad)
async def travel_data(data: TravelData, current_user: str = Depends(get_current_user)) -> dict:
    # Verify that the user_id in the request matches the authenticated user
    if int(current_user) != data.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only save your own travel data"
        )
    auth = save_travel_data(
        user_id=data.user_id,
        src_lat=data.src_lat,
        src_long=data.src_long,
        dest_lat=data.dest_lat,
        dest_long=data.dest_long,
        office_lat=data.office_lat,
        office_long=data.office_long,
        start_time=data.start_time,
        end_time=data.end_time
    )
    return ResponsePayLoad(status=auth['status'], comments=auth['comments'])

@app.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(request: RefreshTokenRequest):
    user_id = verify_refresh_token(request.refresh_token)
    new_access_token = create_access_token({"sub": user_id})
    return RefreshTokenResponse(
        status=True,
        comments="Token refreshed successfully",
        access_token=new_access_token,
        data=None
    )


#_________________________________________________________________________________________________________________________________________#
@app.post('/get_recommendations',response_model=Recommendations)
async def recommendations(userid:str = Depends(get_current_user)) -> dict:
    recommended_users = get_reccomendations(userid=int(userid))
    if recommended_users['status']:
        users = convert_recommendation_data_to_dict(recommended_users['users'])

    return Recommendations(status=recommended_users['status'],comments=recommended_users['comments'],users_info=users)

#_________________________________________________________________________________________________________________________________________#

@app.post('/send_friend_request',response_model=ResponsePayLoad)
async def send_request(sender_id:int,receiver_id:int,current_user:str = Depends(get_current_user))->dict:
    if int(current_user) != sender_id:
        return ResponsePayLoad(
            status=False, comments='Auth error'
        )
    response = are_friends(sender_id,receiver_id)
    if response == True or response == 'Error':
        return ResponsePayLoad(
            status=False,comments='Users already friends or Failed to send request'
        )
    response = is_blocked(sender_id,receiver_id)
    if response == True or response == 'Error':
        return ResponsePayLoad(
            status=False,comments='User is blocked or Failed to send request'
        )
    if send_friend_request(sender_id=sender_id,receiver_id=receiver_id):
        return ResponsePayLoad(
            status=True,comments='friend request sent successfully'
        )
    else:
        return ResponsePayLoad(
            status=False, comments='Failed to send friend request'
        )

@app.post('/get_pending_requests',response_model=PendingRequestPayload)
async def pending_requests(user_id:int,current_user:str=Depends(get_current_user)):
    if int(current_user) != user_id:
        return PendingRequestPayload(
            status=False,comments='User not authorized',request=[]
        )
    request = get_pending_requests(user_id=int(current_user))
    if request['status']:
        request = convert_pending_reuqest_to_dict(requests=request['requests'])
        return PendingRequestPayload(
            status=True, comments='Pending request fetched successfully',request=request
        )
    else:
        return PendingRequestPayload(
            status=False,comments='Failed to fetch pending requests',request=[]
        )
    
@app.post('/get_pending_sent_requests', response_model=SentRequestPayload)
async def get_sent_request(user_id: int, current_user: str = Depends(get_current_user)):
    if int(current_user) != user_id:
        return SentRequestPayload(
            status=False, comments='User not authorized', requests=[]
        )
    status, requests = get_pending_sent_requests(user_id=current_user)
    if status:
        requests = convert_sent_pending_to_dict(requests)
        return SentRequestPayload(
            status=status, comments='Request fetched Successfully', requests=requests
        )
    else:
        return SentRequestPayload(
            status=status, comments='Failed to fetch the requests', requests=[]
        )
    
@app.post('/accept_friend_request',response_model=ResponsePayLoad)
async def friend_request_accept(sender_id:int,user_id:int,current_user:str = Depends(get_current_user)):
    if int(current_user) != user_id:
        return ResponsePayLoad(
            status=False,comments='User not Authorized'
        )
    else:
        response = are_friends(friend_id=sender_id,user_id=user_id)
        if response == True or response == 'Error':
            return ResponsePayLoad(
                status=False,comments='Users already friends or failed to accept friend request'
            )
        response = is_blocked(sender_id=sender_id,receiver_id=user_id)
        if response == True or response == 'Error':
            return ResponsePayLoad(
                status=False,comments='User blocked or +failed to accept friend request'
            )
        status =  accept_friend_request(sender_id=sender_id,receiver_id=user_id)
        return ResponsePayLoad(
            status=status,comments='Friend request accepted successfully' if status else 'Failed to send a friend request'
        ) 
    

@app.post('/reject_friend_request',response_model = ResponsePayLoad)
async def decline_friend_request(user_id:int,sender_id:int,current_user:str=Depends(get_current_user)):
    if int(current_user) != user_id:
        return ResponsePayLoad(
            status=False, comments='User not Authorized'
        )
    else:
        if reject_friend_request(sender_id=sender_id,user_id=user_id):
            return ResponsePayLoad(
                status= True, comments='Successfully rejected the friend request'
            )
        else:
            return ResponsePayLoad(
                status = False, comments= ' Failed to reject the friend request'
            )
        
@app.post('/cancel_friend_request',response_model = ResponsePayLoad)
async def cancel_sent_request(user_id:int,receiver_id:int,current_user :str = Depends(get_current_user)):
    if int(current_user) != user_id:
        return ResponsePayLoad(
            status=False, comments='User not Authorized'
        )
    else:
        if cancel_friend_request(user_id=user_id,receiver_id=receiver_id):
            return ResponsePayLoad(
                status=True, comments='Friend request cancled successfully'
            )
        else:
            return ResponsePayLoad(
                status=False,
                comments= 'Failed to cancel friend request'
            )

@app.post('/get_all_friends',response_model=FriendListPayload)
async def get_friends(user_id:int,current_user=Depends(get_current_user)):
    if int(current_user) != user_id:
        return FriendListPayload(
            status=False,comments='User not Authorized',friends=[]
        )
    else:
        status,data = get_all_friends(user_id=user_id)
        if status:
            data = convert_friend_list_to_dict(data)
            return FriendListPayload(
                status=True,comments='Friends fetched successfully',friends=data
            )
        else:
            return FriendListPayload(
                status=False,comments='Failed to fetch friends',friends=[]
            )
        
@app.post('/remove_friend',response_model=ResponsePayLoad)
async def remove_friend(user_id:int,friend_id:int,current_user:str = Depends(get_current_user)):
    if int(current_user) != user_id:
        return ResponsePayLoad(
            status = False, comments = 'User not Authorized'
        )
    else:
        if unfriend(user_id=user_id,friend_id=friend_id):
            return ResponsePayLoad(
                status=True,comments='Friend removed successfully'
            )
        else:
            return ResponsePayLoad(
                status = False, comments='Failed to remove friend'
            )
        

@app.post('/block_user',response_model=ResponsePayLoad)
async def block(user_id:int,friend_id:int,current_user:str = Depends(get_current_user)):
    if int(current_user) != user_id:
        return ResponsePayLoad(
            status=False,
            comments='User not Authorized'
        )
    else:
        if block_user(user_id=user_id,friend_id=friend_id):
            return ResponsePayLoad(
                status=True,comments='User blocked sucessfully'
            )
        else:
            return ResponsePayLoad(
                status=False,comments='Failed to block user'
            )