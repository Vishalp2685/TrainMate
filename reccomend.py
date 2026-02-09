from database import get_users_with_same_destination,get_user_info_for_recomendation
'''
New problem to fix, destination may be same,but the train and route they 
take may be completely different.
Also reccommend according to the time 
check the train intermediate stations to check if they overlaps and reccomend accordingly.
'''

def get_reccomendations(userid)->dict:
    status,user = get_user_info_for_recomendation(userid=userid)
    # user[3] is gender, user[7] is dest_lat, user[8] is dest_long
    if not status:
        return {'status':False, 'comments': 'Failed to get user info for recommendation','users':None}
    if user[3] == 'male':
        # will only recommend male users
        status,users = get_users_with_same_destination(userid=userid,dest_lat=user[7],dest_long=user[8],genders=('male',))
    else:
        # will recommend male and female users
        status,users = get_users_with_same_destination(userid=userid,dest_lat=user[7],dest_long=user[8],genders=('male','female'))
    if not status:
        return {'status': False, 'comments':'Failed to get recommendations', 'users': None}
    return {'status':status,'users':users,'comments':'Success'}
    
