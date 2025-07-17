from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import tables
from ..database import get_session
from ..models.todos import TodoItem, ToDoCreate, ToDoUpdate
from .logging import logger, cache


class ToDoService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    def _get_user_todos_key(self, user_id: int) -> str:
        return f"user:{user_id}:todos"

    def _get_todo_key(self, user_id: int, todo_id: int) -> str:
        return f"user:{user_id}:todo:{todo_id}"

    def _clear_user_cache(self, user_id: int):
        cache.delete(
            self._get_user_todos_key(user_id),
            f"{self._get_user_todos_key(user_id)}:completed",
            f"{self._get_user_todos_key(user_id)}:active"
        )

    def _todo_to_dict(self, todo: tables.TodoItem) -> dict:
        return {
            'id': todo.id,
            'title': todo.title,
            'is_completed': todo.is_completed,
            'user_id': todo.user_id,
            'created_at': str(todo.created_at) if todo.created_at else None,
        }

    def _refresh_session(self):
        self.session.expire_all()

    def get(self, user_id: int, todo_id: int) -> tables.TodoItem:
        cache_key = self._get_todo_key(user_id, todo_id)

        try:
            # Пробуем получить из кэша
            cached = cache.get(cache_key)
            if cached:
                logger.log(action="cache_hit", resource="todo", user_id=user_id, todo_id=todo_id)
                return tables.TodoItem(**cached)

            # Получаем из БД
            self._refresh_session()
            todo = (
                self.session.query(tables.TodoItem)
                .filter_by(id=todo_id, user_id=user_id)
                .first()
            )

            if not todo:
                logger.log(action="not_found", resource="todo", user_id=user_id, todo_id=todo_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

            self.session.refresh(todo)

            # Сохраняем в кэш
            cache.set(cache_key, self._todo_to_dict(todo))
            logger.log(action="get_success", resource="todo", user_id=user_id, todo_id=todo_id)
            return todo

        except Exception as e:
            logger.log(action="get_error", resource="todo", user_id=user_id,
                       todo_id=todo_id, error=str(e))
            raise

    def get_id(self, user_id: int, todo_id: int) -> tables.TodoItem:
        logger.log(action="get_id_started", resource="todo",
                   user_id=user_id, todo_id=todo_id)
        return self.get(user_id, todo_id)

    def get_list(self, user_id: int, is_completed: Optional[bool] = None) -> List[tables.TodoItem]:
        cache_key = self._get_user_todos_key(user_id)
        if is_completed is not None:
            cache_key += f":{'completed' if is_completed else 'active'}"

        try:
            # Пробуем получить из кэша
            cached = cache.get(cache_key)
            if cached:
                logger.log(action="cache_hit", resource="todos", user_id=user_id,
                           is_completed=is_completed, count=len(cached))
                return [tables.TodoItem(**item) for item in cached]

            # Получаем из БД
            self._refresh_session()
            query = self.session.query(tables.TodoItem).filter_by(user_id=user_id)
            if is_completed is not None:
                query = query.filter_by(is_completed=is_completed)

            todos = query.all()
            for todo in todos:
                self.session.refresh(todo)

            # Сохраняем в кэш
            todos_data = [self._todo_to_dict(todo) for todo in todos]
            cache.set(cache_key, todos_data)

            logger.log(action="get_success", resource="todos", user_id=user_id,
                       is_completed=is_completed, count=len(todos))
            return todos

        except Exception as e:
            logger.log(action="get_error", resource="todos", user_id=user_id,
                       is_completed=is_completed, error=str(e))
            raise

    def create(self, user_id: int, todo_data: ToDoCreate) -> tables.TodoItem:
        try:
            self._refresh_session()
            todo = tables.TodoItem(
                **todo_data.model_dump(),
                user_id=user_id
            )
            self.session.add(todo)
            self.session.commit()
            self.session.refresh(todo)

            # Очищаем кэш списков
            self._clear_user_cache(user_id)

            logger.log(action="create_success", resource="todo",
                       user_id=user_id, todo_id=todo.id)
            return todo

        except Exception as e:
            self.session.rollback()
            logger.log(action="create_error", resource="todo",
                       user_id=user_id, error=str(e))
            raise

    def update(self, user_id: int, todo_id: int, todo_data: ToDoUpdate) -> tables.TodoItem:
        try:
            self._refresh_session()
            todo = self.get(user_id, todo_id)

            for field, value in todo_data.model_dump(exclude_unset=True).items():
                setattr(todo, field, value)

            self.session.commit()
            self.session.refresh(todo)

            # Обновляем кэш
            cache.set(self._get_todo_key(user_id, todo_id), self._todo_to_dict(todo))
            self._clear_user_cache(user_id)

            logger.log(action="update_success", resource="todo",
                       user_id=user_id, todo_id=todo_id)
            return todo

        except Exception as e:
            self.session.rollback()
            logger.log(action="update_error", resource="todo",
                       user_id=user_id, todo_id=todo_id, error=str(e))
            raise

    def delete(self, user_id: int, todo_id: int) -> None:
        try:
            self._refresh_session()
            todo = (
                self.session.query(tables.TodoItem)
                .filter_by(id=todo_id, user_id=user_id)
                .first()
            )

            if not todo:
                logger.log(action="not_found", resource="todo",
                           user_id=user_id, todo_id=todo_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

            self.session.delete(todo)
            self.session.commit()

            # Удаляем из кэша
            cache.delete(self._get_todo_key(user_id, todo_id))
            self._clear_user_cache(user_id)

            logger.log(action="delete_success", resource="todo",
                       user_id=user_id, todo_id=todo_id)

        except Exception as e:
            self.session.rollback()
            logger.log(action="delete_error", resource="todo",
                       user_id=user_id, todo_id=todo_id, error=str(e))
            raise
