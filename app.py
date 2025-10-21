from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, text
import logging
import bcrypt
import os
import time
from flask_apscheduler import APScheduler

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests

logging.basicConfig(level=logging.ERROR)

password = os.environ.get("DB_PASSWORD")
engine = create_engine(f'postgresql+psycopg2://postgres.mzkwsbwtodltrbtdktqv:{password}@aws-1-us-east-2.pooler.supabase.com:5432/postgres')

@app.route('/register_user', methods=['POST'])
def register_user():
    data = request.json
    full_name = data.get('full_name')
    email = data.get('email')
    mob_no = data.get('mob_no')
    password_plain = data.get('password')
    source_location = data.get('source_location')
    destination_location = data.get('destination_location')
    work_place = data.get('work_place')

    if not all([full_name, email, mob_no, password_plain]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    hashed_password = bcrypt.hashpw(password_plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        with engine.begin() as conn:
            existing_user = conn.execute(
                text("SELECT * FROM users WHERE email = :email"), {"email": email}
            ).fetchone()
            if existing_user:
                return jsonify({"status": "error", "message": "User already exists"}), 409

            conn.execute(
                text("""INSERT INTO users 
                        (full_name, email, mob_no, password, source_location, destination_location, work_place)
                        VALUES (:full_name, :email, :mob_no, :password, :source_location, :destination_location, :work_place)"""),
                {
                    "full_name": full_name,
                    "email": email,
                    "mob_no": mob_no,
                    "password": hashed_password,
                    "source_location": source_location,
                    "destination_location": destination_location,
                    "work_place": work_place
                }
            )
        return jsonify({"status": "success", "message": "User created successfully"})
    except Exception as e:
        logging.error(f"Error registering user: {e}")
        return jsonify({"status": "error", "message": "Registration failed"}), 500

@app.route('/authenticate', methods=['POST'])
def authenticate():
    data = request.json
    email = data.get('email')
    password_plain = data.get('password')

    if not email or not password_plain:
        return jsonify({"status": "error", "message": "Missing credentials"}), 400

    try:
        with engine.connect() as conn:
            user = conn.execute(
                text("SELECT * FROM users WHERE email = :email"), {"email": email}
            ).fetchone()
            if user and bcrypt.checkpw(password_plain.encode('utf-8'), user['password'].encode('utf-8')):
                return jsonify({"status": "success", "message": "user_valid"})
            else:
                return jsonify({"status": "error", "message": "user_invalid"}), 401
    except Exception as e:
        logging.error(f"Error authenticating user: {e}")
        return jsonify({"status": "error", "message": "Authentication failed"}), 500

@app.route('/send_friend_request', methods=['POST'])
def send_friend_request():
    data = request.json
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')

    if not sender_id or not receiver_id:
        return jsonify({"status": "error", "message": "Missing sender_id or receiver_id"}), 400

    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO friends(sender_id, receiver_id, status) VALUES(:sender_id, :receiver_id, 'pending')"),
                {"sender_id": sender_id, "receiver_id": receiver_id}
            )
        return jsonify({"status": "success", "message": "Friend request sent"})
    except Exception as e:
        logging.error(f"Error sending friend request: {e}")
        return jsonify({"status": "error", "message": "Friend request failed"}), 500

@app.route('/accept_friend_request', methods=['POST'])
def accept_friend_request():
    data = request.json
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')

    if not sender_id or not receiver_id:
        return jsonify({"status": "error", "message": "Missing sender_id or receiver_id"}), 400

    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE friends SET status = 'accepted' WHERE sender_id = :sender_id AND receiver_id = :receiver_id"),
                {"sender_id": sender_id, "receiver_id": receiver_id}
            )
            conn.execute(
                text("INSERT INTO friends(sender_id, receiver_id, status) VALUES(:receiver_id, :sender_id, 'accepted')"),
                {"sender_id": sender_id, "receiver_id": receiver_id}
            )
        return jsonify({"status": "success", "message": "Friend request accepted"})
    except Exception as e:
        logging.error(f"Error accepting friend request: {e}")
        return jsonify({"status": "error", "message": "Failed to accept friend"}), 500

@app.route('/block_friend', methods=['POST'])
def block_friend():
    data = request.json
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')

    if not sender_id or not receiver_id:
        return jsonify({"status": "error", "message": "Missing sender_id or receiver_id"}), 400

    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE friends SET status = 'blocked' WHERE sender_id = :sender_id AND receiver_id = :receiver_id"),
                {"sender_id": sender_id, "receiver_id": receiver_id}
            )
            conn.execute(
                text("UPDATE friends SET status = 'blocked' WHERE sender_id = :receiver_id AND receiver_id = :sender_id"),
                {"sender_id": sender_id, "receiver_id": receiver_id}
            )
        return jsonify({"status": "success", "message": "Friend blocked successfully"})
    except Exception as e:
        logging.error(f"Error blocking friend: {e}")
        return jsonify({"status": "error", "message": "Failed to block friend"}), 500


@app.route('/get_all_friends/<int:user_id>', methods=['GET'])
def get_all_friends(user_id):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""SELECT u.unique_id, u.full_name, u.email, u.mob_no, u.source_location,
                        u.destination_location, u.work_place
                        FROM users u
                        JOIN friends f ON u.unique_id = f.receiver_id
                        WHERE f.sender_id = :user_id AND f.status = 'accepted'"""),
                {"user_id": user_id}
            ).fetchall()
        friends = [dict(row) for row in result]
        return jsonify(friends)
    except Exception as e:
        logging.error(f"Error fetching friends: {e}")
        return jsonify([])


@app.route('/get_pending_requests/<int:receiver_id>', methods=['GET'])
def get_pending_requests(receiver_id):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""SELECT u.unique_id, u.full_name, u.email, u.mob_no, u.source_location,
                        u.destination_location, u.work_place
                        FROM users u
                        JOIN friends f ON u.unique_id = f.sender_id
                        WHERE f.receiver_id = :receiver_id AND f.status = 'pending'"""),
                {"receiver_id": receiver_id}
            ).fetchall()
        requests = [dict(row) for row in result]
        return jsonify(requests)
    except Exception as e:
        logging.error(f"Error fetching pending requests: {e}")
        return jsonify([])

@app.route('/get_user_details/<string:email>', methods=['GET'])
def get_user_details(email):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""SELECT u.unique_id, u.full_name, u.email, u.mob_no, u.source_location,
                        u.destination_location, u.work_place
                        FROM users u WHERE u.email = :email"""),
                {"email": email}
            ).fetchone()
        if result:
            return jsonify(dict(result))
        else:
            return jsonify({})
    except Exception as e:
        logging.error(f"Error getting user details: {e}")
        return jsonify({})

@app.route('/ping',methods = ['GET'])
def ping():

    return jsonify({"status": 'service up'})

class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config)

scheduler = APScheduler()

@scheduler.task('interval', id='db_status', minutes=5)
def db_status():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT unique_id FROM users WHERE unique_id = 1")).fetchone()
            if result:
                print(f"Database connection OK | Sample User ID: {result.unique_id}")
                logging.info(f"Database connection OK | Sample User ID: {result.unique_id}")
            else:
                print("Database connected but user_id=1 not found.")
                logging.warning("Database connected but user_id=1 not found.")
    except Exception as e:
        logging.error(f"Database check failed: {e}")


scheduler.init_app(app)
scheduler.start()

if __name__ == "__main__":
    app.run()
