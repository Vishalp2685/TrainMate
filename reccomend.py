from database import get_user_data, engine
from sqlalchemy import text

def get_reccomendations(userid) -> dict:
    user = get_user_data(userid)
    if not user:
        return {'status': False, 'comments': 'Failed to get user info for recommendation', 'users': None}

    user_office = (user.get('office_name') or '').strip().lower() if user.get('office_name') else None
    user_dest_lat = user.get('dest_lat')
    user_dest_long = user.get('dest_long')
    user_src_lat = user.get('src_lat')
    user_src_long = user.get('src_long')

    query = '''SELECT u.unique_id as user_id,u.first_name,u.last_name,t.office_name,t.src_lat,t.src_long,t.dest_lat,t.dest_long
               FROM users u
               JOIN travel_data t ON u.unique_id = t.user_id
               WHERE u.unique_id != :userid;'''
    params = {'userid': userid}

    try:
        with engine.connect() as conn:
            rows = conn.execute(text(query), params).fetchall()
    except Exception as e:
        return {'status': False, 'comments': f'Failed to fetch candidate users: {e}', 'users': None}

    candidates = []
    for row in rows:
        uid = row[0]
        first_name = row[1]
        last_name = row[2]
        office_name = row[3]
        src_lat = row[4]
        src_long = row[5]
        dest_lat = row[6]
        dest_long = row[7]

        office_match = 1 if (office_name and user_office and office_name.strip().lower() == user_office) else 0
        dest_match = 1 if (dest_lat is not None and dest_long is not None and user_dest_lat is not None and user_dest_long is not None and float(dest_lat) == float(user_dest_lat) and float(dest_long) == float(user_dest_long)) else 0
        src_match = 1 if (src_lat is not None and src_long is not None and user_src_lat is not None and user_src_long is not None and float(src_lat) == float(user_src_lat) and float(src_long) == float(user_src_long)) else 0
        has_office = 1 if (office_name and str(office_name).strip()) else 0

        # Score tuple sorts lexicographically; higher tuples come first when reversed
        score = (office_match, dest_match, src_match, has_office)
        candidates.append({'user_id': uid, 'first_name': first_name, 'last_name': last_name, 'office_name': office_name, 'score': score})

    # Sort by score descending (office match > dest match > src match)
    candidates.sort(key=lambda c: c['score'], reverse=True)

    # Prepare final output with only requested fields
    recommended = [
        {
            'user_id': c['user_id'],
            'first_name': c['first_name'],
            'last_name': c['last_name'],
            'office_name': c['office_name'],
            # 'src_lat': None if c.get('src_lat') is None else float(c.get('src_lat')),
            # 'src_long': None if c.get('src_long') is None else float(c.get('src_long')),
            # 'dest_lat': None if c.get('dest_lat') is None else float(c.get('dest_lat')),
            # 'dest_long': None if c.get('dest_long') is None else float(c.get('dest_long')),
        }
        for c in candidates
    ]

    return {'status': True, 'comments': 'Success', 'users': recommended}
