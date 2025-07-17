from typing import List, Optional

from fastapi import APIRouter, Depends, Response, status

from ..models.auth import User
from ..models.todos import TodoItem, ToDoCreate, ToDoUpdate
from ..services.auth import get_current_user
from ..services.todo import ToDoService


router = APIRouter(
    prefix='/todos',
    tags=['/todos']
)


@router.get('/', response_model=List[TodoItem])
def get_todos(
    is_completed: Optional[bool] = None,
    user: User = Depends(get_current_user),
    service: ToDoService = Depends(),
):
    """
    Получение списка всех дел для пользователя.

    -**is_completed**: фильтр по выполнению
    """
    return service.get_list(user_id=user.id, is_completed=is_completed)

@router.get('/{todo_id}', response_model=TodoItem)
def get_by_id(
    todo_id: int,
    user: User = Depends(get_current_user),
    service: ToDoService = Depends(),
):
    """
    Получение задачи по id.
    """
    return service.get_id(user_id=user.id, todo_id=todo_id)

@router.post('/', response_model=TodoItem)
def create_todo(
    todo_data: ToDoCreate,
    user: User = Depends(get_current_user),
    service: ToDoService = Depends(),
):
    """
    Добавление задачи.
    """
    return service.create(user_id=user.id, todo_data=todo_data)

@router.put('/{todo_id}', response_model=TodoItem)
def update_todo(
    todo_id: int,
    todo_data: ToDoUpdate,
    user: User = Depends(get_current_user),
    service: ToDoService = Depends(),
):
    """
    Изменение задачи.
    """
    return service.update(user_id=user.id, todo_id=todo_id, todo_data=todo_data)

@router.delete('/{todo_id}')
def delete_todo(
    todo_id: int,
    user: User = Depends(get_current_user),
    service: ToDoService = Depends(),
):
    """
    Удаление задачи.
    """
    service.delete(user_id=user.id, todo_id=todo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
