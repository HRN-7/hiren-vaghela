import json
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth, credentials, get_app, initialize_app
from sqlalchemy.orm import Session
from .config import settings
from .db import User, get_db

bearer = HTTPBearer(auto_error=False)

def firebase_app():
    try: return get_app()
    except ValueError:
        cfg = settings()
        if not cfg.firebase_project_id:
            raise HTTPException(503, 'Secure sign-in is not available yet.')
        cred = credentials.Certificate(json.loads(cfg.firebase_service_account_json)) if cfg.firebase_service_account_json else credentials.ApplicationDefault()
        return initialize_app(cred, {'projectId':cfg.firebase_project_id})

def identity(token: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not token: raise HTTPException(401, 'Please sign in to continue.')
    firebase_app()
    try: claims = auth.verify_id_token(token.credentials, check_revoked=True)
    except Exception: raise HTTPException(401, 'Your session expired. Please sign in again.')
    if (claims.get('email') and not claims.get('email_verified')) or (not claims.get('email_verified') and not claims.get('phone_number')):
        raise HTTPException(403, 'Verify your email before opening your account.')
    return claims

def current_user(claims=Depends(identity), db:Session=Depends(get_db)):
    user = db.get(User, claims['uid'])
    if not user: raise HTTPException(404, 'Finish your account profile first.')
    return user

def admin(claims=Depends(identity)):
    if claims.get('admin') is not True: raise HTTPException(403,'Administrator access required.')
    return claims
