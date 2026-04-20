from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from core.postgres import get_db
from api.models.user import User
from api.schemas.user import UserCreate
# Import các hàm bạn đã viết ở trên
from api.services.auth_service import password_hash, authenticate_user, create_access_token
from api.deps import get_current_user 

router = APIRouter(tags=["Auth"])

# ==========================================
# 1. API ĐĂNG KÝ (REGISTER)
# ==========================================
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Kiểm tra xem user đã tồn tại chưa
    user_exists = db.query(User).filter(User.username == user_data.username).first()
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên đăng nhập đã tồn tại"
        )
    
    # Băm mật khẩu (Hash)
    hashed_pw = password_hash.hash(user_data.password)
    
    # Lưu vào DB
    new_user = User(
        username=user_data.username,
        hashed_password=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "Đăng ký thành công!", "username": new_user.username}

# ==========================================
# 2. API ĐĂNG NHẬP (LOGIN)
# Lưu ý: Đường dẫn này PHẢI KHỚP với tokenUrl="login" bạn set ở OAuth2PasswordBearer
# ==========================================
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Xác thực user (Sử dụng hàm authenticate_user bạn đã viết)
    # Lưu ý: Hàm authenticate_user của bạn gọi get_user(username). 
    # Nếu get_user chưa có DB Session, bạn cần truyền db vào cho nó.
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tên đăng nhập hoặc mật khẩu",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Tạo Access Token
    access_token = create_access_token(data={"sub": user.username})
    
    # Trả về chuẩn OAuth2
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# ==========================================
# 3. API ĐĂNG XUẤT (LOGOUT)
# ==========================================
@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    SỰ THẬT VỀ JWT LOGOUT:
    JWT là Stateless (Phi trạng thái). Server không lưu Token, nên không thể "xóa" Token từ phía Server.
    Đăng xuất thực chất là hành động XÓA TOKEN Ở PHÍA CLIENT (Android App xóa trong SharedPreferences, Web xóa LocalStorage).
    
    API này chủ yếu dùng để Client gọi báo cho Server biết: "Tôi đã chủ động xóa token rồi nhé",
    hoặc dùng khi bạn setup Blacklist (Redis) chặn Token chưa hết hạn (nâng cao).
    """
    return {"message": f"Tạm biệt {current_user.username}, bạn đã đăng xuất thành công."}