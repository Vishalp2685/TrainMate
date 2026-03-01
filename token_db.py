"""
Database functions for token management and device registration
These functions need to be added to database.py and called during initialization
"""

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from Utils.utils import encrypt, verify_passwords
import hashlib
import uuid

load_dotenv()

PASSWORD = os.environ.get('password')
DATABASE_URL = f"postgresql://postgres.dlbtacxmxlgsjvmtrlsl:{PASSWORD}@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"

engine = create_engine(DATABASE_URL)

def create_refresh_tokens_table():
    """Create refresh_tokens table if it doesn't exist"""
    query = """
    CREATE TABLE IF NOT EXISTS refresh_tokens (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(unique_id) ON DELETE CASCADE,
        device_id VARCHAR(255) NOT NULL,
        token_hash VARCHAR(255) NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        revoked_at TIMESTAMP DEFAULT NULL,
        last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
    CREATE INDEX IF NOT EXISTS idx_refresh_tokens_device_id ON refresh_tokens(user_id, device_id);
    """
    try:
        with engine.begin() as conn:
            for statement in query.split(';'):
                if statement.strip():
                    conn.execute(text(statement))
        return {'status': True, 'message': 'Refresh tokens table created successfully'}
    except Exception as e:
        print(f"Error creating refresh_tokens table: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def create_device_tokens_table():
    """Create device_tokens table if it doesn't exist"""
    query = """
    CREATE TABLE IF NOT EXISTS device_tokens (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(unique_id) ON DELETE CASCADE,
        device_id VARCHAR(255) NOT NULL,
        fcm_token TEXT NOT NULL,
        device_name VARCHAR(255),
        device_type VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, device_id)
    );
    CREATE INDEX IF NOT EXISTS idx_device_tokens_user_id ON device_tokens(user_id);
    """
    try:
        with engine.begin() as conn:
            for statement in query.split(';'):
                if statement.strip():
                    conn.execute(text(statement))
        return {'status': True, 'message': 'Device tokens table created successfully'}
    except Exception as e:
        print(f"Error creating device_tokens table: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def hash_token(token: str) -> str:
    """Hash a token using SHA256"""
    return hashlib.sha256(token.encode()).hexdigest()


def store_refresh_token(user_id: int, device_id: str, token: str, expires_in_days: int = 45) -> dict:
    """
    Store a new refresh token in the database
    
    Args:
        user_id: User's unique_id
        device_id: Device identifier
        token: The actual refresh token (will be hashed before storing)
        expires_in_days: Days until token expires (default 45)
    
    Returns:
        dict with status and token_id
    """
    token_hash = hash_token(token)
    expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    query = """
    INSERT INTO refresh_tokens(user_id, device_id, token_hash, expires_at)
    VALUES (:user_id, :device_id, :token_hash, :expires_at)
    RETURNING id;
    """
    param = {
        'user_id': user_id,
        'device_id': device_id,
        'token_hash': token_hash,
        'expires_at': expires_at
    }
    
    try:
        with engine.begin() as conn:
            result = conn.execute(text(query), param).fetchone()
        return {'status': True, 'token_id': result[0]}
    except Exception as e:
        print(f"Error storing refresh token: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def validate_refresh_token(user_id: int, device_id: str, token: str) -> dict:
    """
    Validate a refresh token
    
    Args:
        user_id: User's unique_id
        device_id: Device identifier
        token: The refresh token to validate
    
    Returns:
        dict with status and validation result
    """
    token_hash = hash_token(token)
    
    query = """
    SELECT id, expires_at, revoked_at FROM refresh_tokens
    WHERE user_id = :user_id AND device_id = :device_id AND token_hash = :token_hash;
    """
    param = {
        'user_id': user_id,
        'device_id': device_id,
        'token_hash': token_hash
    }
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), param).fetchone()
        
        if not result:
            return {'status': False, 'message': 'Token not found'}
        
        token_id, expires_at, revoked_at = result
        
        if revoked_at is not None:
            return {'status': False, 'message': 'Token has been revoked'}
        
        if datetime.utcnow() > expires_at:
            return {'status': False, 'message': 'Token has expired'}
        
        # Update last_used_at
        update_query = "UPDATE refresh_tokens SET last_used_at = :now WHERE id = :id;"
        with engine.begin() as conn:
            conn.execute(text(update_query), {'id': token_id, 'now': datetime.utcnow()})
        
        return {'status': True, 'token_id': token_id}
    except Exception as e:
        print(f"Error validating refresh token: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def revoke_refresh_token(user_id: int, device_id: str) -> dict:
    """
    Revoke a refresh token for a specific device (logout one device)
    
    Args:
        user_id: User's unique_id
        device_id: Device identifier
    
    Returns:
        dict with status
    """
    query = """
    UPDATE refresh_tokens 
    SET revoked_at = :now
    WHERE user_id = :user_id AND device_id = :device_id AND revoked_at IS NULL;
    """
    param = {
        'user_id': user_id,
        'device_id': device_id,
        'now': datetime.utcnow()
    }
    
    try:
        with engine.begin() as conn:
            conn.execute(text(query), param)
        return {'status': True, 'message': 'Token revoked successfully'}
    except Exception as e:
        print(f"Error revoking refresh token: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def revoke_all_refresh_tokens(user_id: int) -> dict:
    """
    Revoke all refresh tokens for a user (logout all devices)
    
    Args:
        user_id: User's unique_id
    
    Returns:
        dict with status
    """
    query = """
    UPDATE refresh_tokens 
    SET revoked_at = :now
    WHERE user_id = :user_id AND revoked_at IS NULL;
    """
    param = {
        'user_id': user_id,
        'now': datetime.utcnow()
    }
    
    try:
        with engine.begin() as conn:
            conn.execute(text(query), param)
        return {'status': True, 'message': 'All tokens revoked successfully'}
    except Exception as e:
        print(f"Error revoking all refresh tokens: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def register_device_token(user_id: int, device_id: str, fcm_token: str, device_name: str = None, device_type: str = None) -> dict:
    """
    Store or update a device's FCM token for push notifications
    
    Args:
        user_id: User's unique_id
        device_id: Device identifier
        fcm_token: Firebase Cloud Messaging token
        device_name: Name of the device (optional)
        device_type: Type of device - 'android' or 'ios' (optional)
    
    Returns:
        dict with status
    """
    query = """
    INSERT INTO device_tokens(user_id, device_id, fcm_token, device_name, device_type)
    VALUES (:user_id, :device_id, :fcm_token, :device_name, :device_type)
    ON CONFLICT (user_id, device_id) DO UPDATE
    SET fcm_token = :fcm_token, device_name = :device_name, device_type = :device_type, last_used_at = :now;
    """
    param = {
        'user_id': user_id,
        'device_id': device_id,
        'fcm_token': fcm_token,
        'device_name': device_name,
        'device_type': device_type,
        'now': datetime.utcnow()
    }
    
    try:
        with engine.begin() as conn:
            conn.execute(text(query), param)
        return {'status': True, 'message': 'Device token registered successfully'}
    except Exception as e:
        print(f"Error registering device token: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def get_user_devices(user_id: int) -> dict:
    """
    Get all active devices for a user with their FCM tokens (for notifications)
    
    Args:
        user_id: User's unique_id
    
    Returns:
        dict with status and list of devices
    """
    query = """
    SELECT d.device_id, d.fcm_token, d.device_name, d.device_type, 
           d.last_used_at, CASE WHEN r.revoked_at IS NULL THEN true ELSE false END as is_active
    FROM device_tokens d
    LEFT JOIN refresh_tokens r ON d.user_id = r.user_id AND d.device_id = r.device_id
    WHERE d.user_id = :user_id
    GROUP BY d.device_id, d.fcm_token, d.device_name, d.device_type, d.last_used_at, r.revoked_at;
    """
    param = {'user_id': user_id}
    
    try:
        with engine.connect() as conn:
            results = conn.execute(text(query), param).fetchall()
        
        devices = []
        for row in results:
            devices.append({
                'device_id': row[0],
                'fcm_token': row[1],
                'device_name': row[2],
                'device_type': row[3],
                'last_used_at': row[4],
                'is_active': row[5]
            })
        
        return {'status': True, 'devices': devices}
    except Exception as e:
        print(f"Error getting user devices: {e}")
        return {'status': False, 'message': f'Error: {e}'}


def get_active_device_fcm_tokens(user_id: int) -> list:
    """
    Get FCM tokens for all active devices of a user (for sending notifications)
    
    Args:
        user_id: User's unique_id
    
    Returns:
        list of FCM tokens
    """
    query = """
    SELECT d.fcm_token
    FROM device_tokens d
    LEFT JOIN refresh_tokens r ON d.user_id = r.user_id AND d.device_id = r.device_id
    WHERE d.user_id = :user_id AND (r.revoked_at IS NULL OR r.id IS NULL);
    """
    param = {'user_id': user_id}
    
    try:
        with engine.connect() as conn:
            results = conn.execute(text(query), param).fetchall()
        
        tokens = [row[0] for row in results if row[0]]
        return tokens
    except Exception as e:
        print(f"Error getting FCM tokens: {e}")
        return []


# Initialize tables on module import
try:
    create_refresh_tokens_table()
    create_device_tokens_table()
except:
    pass
