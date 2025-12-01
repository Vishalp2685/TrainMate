from fastapi import FastAPI
from database import authenticate_user,create_user
from schemas import Email,Mobile,Register,ResponsePayLoad
app = FastAPI()

@app.post('/login/mobile/',response_model=ResponsePayLoad)
async def l_login(data:Mobile) -> dict:
    auth = authenticate_user(mob_no=data.mob_no,password=data.password,email=None)
    return ResponsePayLoad(status=auth['status'],comments=auth['comments'])

@app.post('/login/email/',response_model=ResponsePayLoad)
async def e_login(data: Email) -> dict:
    auth = authenticate_user(email=data.email,password=data.password,mob_no=None)
    return ResponsePayLoad(status=auth['status'],comments=auth['comments'])

@app.post('/register/',response_model=ResponsePayLoad)
async def register(data:Register) -> dict:
    auth = create_user(first_name=data.first_name,last_name=data.last_name,email=data.email,mob_no=data.mob_no,password=data.password)
    print(ResponsePayLoad(status=auth['status'],comments=auth['comments']))
    return ResponsePayLoad(status=auth['status'],comments=auth['comments'])

@app.get('/ping')
async def ping()-> dict:
    return {'status': 'ok'}
    