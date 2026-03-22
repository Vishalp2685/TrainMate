from fastapi import FastAPI, Depends, HTTPException, status
from database import *
from schemas import (Register, ResponsePayLoad, TravelData, LoginResponsePayLoad, 
                     Recommendations,
                     PendingRequestPayload,SentRequestPayload,FriendListPayload,
                     SenderId,ReceiverId,FriendID,TokenResponsePayload,
                     TravelResponsePayload, RefreshTokenRequestNew, RefreshTokenResponseNew,
                     LogoutRequest, RegisterDeviceRequest, RegisterDeviceResponse, DeviceInfo,AtStationResponsePayload)
from auth.auth import create_access_token, create_refresh_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from reccomend import get_reccomendations
from Utils.utils import convert_pending_reuqest_to_dict,convert_sent_pending_to_dict,convert_friend_list_to_dict
from train_services import get_trains_between_stations
from schemas import TrainSuggestionResponse
import uuid
from datetime import datetime
app = FastAPI()

@app.get('/ping')
async def ping() -> dict:
    return {'status': 'ok'}


@app.post('/login',response_model=LoginResponsePayLoad)
async def login(data: OAuth2PasswordRequestForm = Depends(), device_id: str = None):
    """
    Login endpoint that supports token rotation with device tracking
    
    Args:
        device_id: Unique device identifier (optional, will auto-generate if not provided)
    """
    # Auto-generate device_id if not provided
    if not device_id:
        device_id = f"web-{uuid.uuid4().hex[:8]}"
    
    username = data.username
    password = data.password
    if '@' in username:
        user = authenticate_user(email=username,password=password,mob_no=None)
    else:
        user = authenticate_user(mob_no=username,password=password,email=None)
    
    if user['status']:
        user_id = user['data']['user_id']
        access_token = create_access_token({"user_id": str(user_id)})
        refresh_token = create_refresh_token({"user_id": str(user_id)})
        
        # Store refresh token in database
        token_result = store_refresh_token(user_id=user_id, device_id=device_id, token=refresh_token)
        if not token_result['status']:
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store token"
            )
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
            refresh_token=refresh_token,
            device_id=device_id
        )

@app.post('/register/', response_model=TokenResponsePayload)
async def register(data: Register, device_id: str = None) -> dict:
    """
    Register endpoint with token generation
    
    Args:
        device_id: Unique device identifier (optional, will auto-generate if not provided)
    """
    if not device_id:
        device_id = f"web-{uuid.uuid4().hex[:8]}"  # Auto-generate if not provided
    
    auth = create_user(first_name=data.first_name, last_name=data.last_name, email=data.email, mob_no=data.mob_no, password=data.password,gender=data.gender)
    access_token = None
    refresh_access_token = None
    if auth['status']:
        # Get the newly created user's ID
        unique_id = get_userid(data.email)
        if unique_id:
            access_token = create_access_token({'user_id': str(unique_id)})
            refresh_access_token = create_refresh_token({'user_id': str(unique_id)})
            
            # Store refresh token in database
            token_result = store_refresh_token(user_id=unique_id, device_id=device_id, token=refresh_access_token)
            if not token_result['status']:
                print(f"Warning: Failed to store refresh token: {token_result.get('message')}")
            
    return TokenResponsePayload(status=auth['status'],
                                 comments=auth['comments'],
                                 access_token=access_token,
                                 refresh_token=refresh_access_token,
                                 device_id=device_id
                                 )

@app.post('/save_travel_data', response_model=TravelResponsePayload)
async def travel_data(data: TravelData, user_id: int = Depends(get_current_user)) -> dict:
    # Verify that the user_id in the request matches the authenticated user
    auth = save_travel_data(
        user_id=user_id,
        src_lat=data.src_lat,
        src_long=data.src_long,
        dest_lat=data.dest_lat,
        dest_long=data.dest_long,
        office_name = data.office_name,
        start_time=data.start_time,
        end_time=data.end_time,
        source_name=data.source_name,
        dest_name=data.dest_name
    )
    user_data = get_user_data(unique_id = user_id)
    return TravelResponsePayload(
            status=auth['status'], 
            comments=auth['comments'],
            data=user_data
                )


@app.post("/token/refresh", response_model=RefreshTokenResponseNew)
async def refresh_token_with_refresh_only(request: RefreshTokenRequestNew):
    """
    Refresh token endpoint - NO access token required
    
    Use this when access token is expired. Only requires valid refresh token.
    
    - Decodes refresh token to extract user_id (opaque token format)
    - Validates token via database
    - Invalidates old refresh token
    - Generates new token pair
    
    Args:
        request: RefreshTokenRequestNew containing refresh_token and device_id
    """
    # Since refresh tokens are now opaque (random strings), we need to identify the user differently
    # We'll need to update the database to include user_id in a query by token
    # For now, let's add a helper function
    
    # Find user by refresh token
    user_id = get_user_by_refresh_token(request.device_id, request.refresh_token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Validate the refresh token from database
    validation = validate_refresh_token(user_id=user_id, device_id=request.device_id, token=request.refresh_token)
    
    if not validation['status']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=validation.get('message', 'Invalid refresh token')
        )
    
    # Revoke the old refresh token
    revoke_result = revoke_refresh_token(user_id=user_id, device_id=request.device_id)
    if not revoke_result['status']:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke old token"
        )
    
    # Generate new token pair
    new_access_token = create_access_token({"user_id": str(user_id)})
    new_refresh_token = create_refresh_token({"user_id": str(user_id)})
    
    # Store new refresh token
    store_result = store_refresh_token(user_id=user_id, device_id=request.device_id, token=new_refresh_token)
    if not store_result['status']:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store new token"
        )
    
    return RefreshTokenResponseNew(
        status=True,
        comments="Token refreshed successfully",
        access_token=new_access_token,
        refresh_token=new_refresh_token
    )


@app.post("/logout", response_model=ResponsePayLoad)
async def logout(request: LogoutRequest, user_id: int = Depends(get_current_user)):
    """
    Logout endpoint - revoke refresh token for a specific device
    
    Args:
        request: LogoutRequest containing device_id
        user_id: Current user ID from access token
    """
    revoke_result = revoke_refresh_token(user_id=user_id, device_id=request.device_id)
    
    return ResponsePayLoad(
        status=revoke_result['status'],
        comments=revoke_result.get('message', 'Logged out successfully')
    )


@app.post("/logout-all", response_model=ResponsePayLoad)
async def logout_all(user_id: int = Depends(get_current_user)):
    """
    Logout all devices - revoke all refresh tokens for user
    
    Args:
        user_id: Current user ID from access token
    """
    revoke_result = revoke_all_refresh_tokens(user_id=user_id)
    
    return ResponsePayLoad(
        status=revoke_result['status'],
        comments=revoke_result.get('message', 'Logged out from all devices')
    )


@app.post("/register-device", response_model=RegisterDeviceResponse)
async def register_device(request: RegisterDeviceRequest, user_id: int = Depends(get_current_user)):
    """
    Register a device for push notifications
    
    Args:
        request: RegisterDeviceRequest containing device info and FCM token
        user_id: Current user ID from access token
    """
    result = register_device_token(
        user_id=user_id,
        device_id=request.device_id,
        fcm_token=request.fcm_token,
        device_name=request.device_name,
        device_type=request.device_type
    )
    
    if not result['status']:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get('message', 'Failed to register device')
        )
    
    # Get the registered device info
    devices_result = get_user_devices(user_id=user_id)
    device_info = None
    if devices_result['status']:
        for device in devices_result.get('devices', []):
            if device['device_id'] == request.device_id:
                device_info = DeviceInfo(
                    device_id=device['device_id'],
                    fcm_token=device['fcm_token'],
                    device_name=device['device_name'],
                    device_type=device['device_type'],
                    is_active=device['is_active'],
                    last_used_at=device.get('last_used_at')
                )
                break
    
    return RegisterDeviceResponse(
        status=result['status'],
        comments=result.get('message', 'Device registered successfully'),
        device=device_info
    )

#_________________________________________________________________________________________________________________________________________#
@app.post('/get_recommendations',response_model=Recommendations)
async def recommendations(userid:str = Depends(get_current_user)) -> dict:
    """
    Get reccomended users
    """
    recommended_users = get_reccomendations(userid=int(userid))
    return Recommendations(
        status=recommended_users['status'],
        comments=recommended_users['comments'],
        users_info=recommended_users['users'])

#_________________________________________________________________________________________________________________________________________#
@app.get('/suggest_trains', response_model=TrainSuggestionResponse)
async def suggest_trains(
    src_station_code: str, 
    dest_station_code: str,
    user_id: int = Depends(get_current_user)
):
    # Get current time in HH:MM:SS format
    current_time = datetime.now().strftime("%H:%M:%S")
    
    trains = get_trains_between_stations(src_station_code.upper(), dest_station_code.upper(), current_time)
    
    return {
        "status": True,
        "comments": "Trains fetched successfully",
        "trains": trains
    }


@app.post('/send_friend_request',response_model=ResponsePayLoad)
async def send_request(receiver_id:ReceiverId,current_user:int = Depends(get_current_user))->ResponsePayLoad:
    """
    send friend request takes one paramater that is the receiver_id which is the 
    user id of the friend and the jwt token for auth
    """
    receiver_id = receiver_id.receiver_id
    response = are_friends(current_user,receiver_id)
    
    if response == True or response == 'Error':
        return ResponsePayLoad(
            status=False,comments='Users already friends or Failed to send request'
        )
    response = is_blocked(current_user,receiver_id)
    if response == True or response == 'Error':
        return ResponsePayLoad(
            status=False,comments='User is blocked or Failed to send request'
        )
    if send_friend_request(sender_id=current_user,receiver_id=receiver_id):
        return ResponsePayLoad(
            status=True,comments='friend request sent successfully'
        )
    else:
        return ResponsePayLoad(
            status=False, comments='Failed to send friend request'
        )

@app.post('/get_pending_requests',response_model=PendingRequestPayload)
async def pending_requests(current_user:int=Depends(get_current_user)):
    """
    Get all the pending request sent to the user using only the access token
    """
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
async def get_sent_request(current_user: str = Depends(get_current_user)):
    """
    Get all the friend request that user has sent and not accepted yet using only access token
    """
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
    
@app.post('/accept_friend_request', response_model=ResponsePayLoad)
async def friend_request_accept(sender_id: SenderId,current_user: int = Depends(get_current_user)):
    """
    Accept the friend request using sender id and access token
    """
    sender_id = sender_id.sender_id
    if are_friends(friend_id=sender_id, user_id=current_user):
        return ResponsePayLoad(
            status=False,
            comments='Users are already friends'
        )

    if is_blocked(sender_id=sender_id, receiver_id=current_user):
        return ResponsePayLoad(
            status=False,
            comments='User is blocked'
        )

    status = accept_friend_request(
        sender_id=sender_id,
        receiver_id=current_user
    )

    return ResponsePayLoad(
        status=status,
        comments='Friend request accepted successfully'
        if status else
        'Failed to accept friend request'
    )

@app.post('/reject_friend_request',response_model = ResponsePayLoad)
async def decline_friend_request(sender_id:SenderId,current_user:int=Depends(get_current_user)):
    """
    Reject Friend request using sender id and access token
    """
    sender_id = sender_id.sender_id
    if reject_friend_request(sender_id=sender_id,user_id=current_user):
        return ResponsePayLoad(
            status= True, comments='Successfully rejected the friend request'
        )
    else:
        return ResponsePayLoad(
            status = False, comments= ' Failed to reject the friend request'
        )
        
@app.post('/cancel_friend_request',response_model = ResponsePayLoad)
async def cancel_sent_request(receiver_id:int,current_user :str = Depends(get_current_user)):
    """
    unsend the friend request using the friend id and access token
    """
    if cancel_friend_request(user_id=current_user,receiver_id=receiver_id):
        return ResponsePayLoad(
            status=True, comments='Friend request cancled successfully'
        )
    else:
        return ResponsePayLoad(
            status=False,
            comments= 'Failed to cancel friend request'
        )

@app.post('/get_all_friends',response_model=FriendListPayload)
async def get_friends(current_user=Depends(get_current_user)):
    """
    Get all the friends of user using only the access token
    """
    status,data = get_all_friends(user_id=current_user)
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
async def remove_friend(friend_id:FriendID,current_user:int = Depends(get_current_user)):
    """
    Unfirend a user using this endpoint, takes friend_id and the access token as paramters
    """
    if unfriend(user_id=current_user,friend_id=friend_id.friend_id):
        return ResponsePayLoad(
            status=True,comments='Friend removed successfully'
        )
    else:
        return ResponsePayLoad(
            status = False, comments='Failed to remove friend'
        )
        

@app.post('/block_user',response_model=ResponsePayLoad)
async def block(friend_id:FriendID,current_user:int = Depends(get_current_user)):
    """
    Block a user, takes friend_id and access token
    """
    if block_user(user_id=current_user,friend_id=friend_id.friend_id):
        return ResponsePayLoad(
            status=True,comments='User blocked sucessfully'
        )
    else:
        return ResponsePayLoad(
            status=False,comments='Failed to block user'
        )
    
@app.post('/update_user_status',response_model=ResponsePayLoad)
def update_status(user_id:int = Depends(get_current_user)):
    '''
    Use this when user reached the station, to update into the database, every 10 minutes
    ensure user is available at station
    '''
    status = set_user_status(user_id=user_id)
    return ResponsePayLoad(
        status=status, comments=None
    )

# show_friends_available
@app.post('/get_friends_at_station',response_model=AtStationResponsePayload)
def get_friends_at_station(user_id:int = Depends(get_current_user)):
    """
    Use this to get all the friends availabe at station
    """
    friends = show_friends_availabe_at_station(user_id=user_id)
    return AtStationResponsePayload(
        status=True,comments=None, friends=friends
    )