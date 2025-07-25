from fastapi import APIRouter
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm

from ..models.auth import UserCreate, Token, User
from ..services.auth import AuthUserService, get_current_user

router = APIRouter(
    prefix='/auth',
    tags=['/auth'],
)


@router.post('/sign-up', response_model=Token)
def sign_up(
        user_data: UserCreate,
        service: AuthUserService = Depends(),
):
    """
    Регистрация нового пользователя.
    """
    return service.register_new_user(user_data)


@router.post('/sign-in', response_model=Token)
def sign_in(
        form_data: OAuth2PasswordRequestForm = Depends(),
        service: AuthUserService = Depends(),
):
    """
    Авторизация.
    """
    return service.authenticate_user(
        form_data.username,
        form_data.password,
    )


@router.get('/user', response_model=User)
def get_user(user: User = Depends(get_current_user)):
    """
    Получение текущего пользователя.
    """
    return user
