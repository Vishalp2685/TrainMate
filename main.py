from fastapi import FastAPI
from database import authenticate_user,create_user,save_travel_data
from schemas import Email,Mobile,Register,ResponsePayLoad,TravelData,LoginResponsePayLoad

app = FastAPI()

@app.post('/login/mobile/',response_model=LoginResponsePayLoad)
async def l_login(data:Mobile) -> dict:
    auth = authenticate_user(mob_no=data.mob_no,password=data.password,email=None)
    return LoginResponsePayLoad(status=auth['status'],comments=auth['comments'],data=auth['data'])

@app.post('/login/email/',response_model=LoginResponsePayLoad)
async def e_login(data: Email) -> dict:
    auth = authenticate_user(email=data.email,password=data.password,mob_no=None)
    return LoginResponsePayLoad(status=auth['status'],comments=auth['comments'],data=auth['data'])

@app.post('/register/',response_model=ResponsePayLoad)
async def register(data:Register) -> dict:
    auth = create_user(first_name=data.first_name,last_name=data.last_name,email=data.email,mob_no=data.mob_no,password=data.password)
    return ResponsePayLoad(status=auth['status'],comments=auth['comments'])

@app.post('/save_travel_data',response_model=ResponsePayLoad)
# I need to create an endpoint for saving the travel data, and only the authorised person can save the data
async def travel_data(data:TravelData) -> dict:
    
    auth = save_travel_data(user_id=data.user_id,
                            src_lat = data.src_lat,
                            src_long = data.src_long,
                            dest_lat = data.dest_lat,
                            dest_long = data.dest_long,
                            office_lat = data.office_lat,
                            office_long = data.office_long,
                            start_time = data.start_time,
                            end_time = data.end_time
    )
    return ResponsePayLoad(status=auth['status'],comments=auth['comments'])

@app.get('/ping')
async def ping()-> dict:
    return {'status': 'ok'}
    