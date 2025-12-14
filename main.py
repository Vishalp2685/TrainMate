from fastapi import FastAPI, Depends, HTTPException, status
from database import authenticate_user, create_user, save_travel_data
from schemas import Register, ResponsePayLoad, TravelData, LoginResponsePayLoad, RefreshTokenRequest,RefreshTokenResponse
from auth.auth import create_access_token, create_refresh_token, verify_refresh_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm
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
    auth = create_user(first_name=data.first_name, last_name=data.last_name, email=data.email, mob_no=data.mob_no, password=data.password)
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
def refresh_access_token(request: RefreshTokenRequest):
    user_id = verify_refresh_token(request.refresh_token)
    new_access_token = create_access_token({"sub": user_id})
    return RefreshTokenResponse(
        status=True,
        comments="Token refreshed successfully",
        access_token=new_access_token,
        data=None
    )