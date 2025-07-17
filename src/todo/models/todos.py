import time
from datetime import datetime

from pydantic import BaseModel, Field


class ToDoBase(BaseModel):
    title: str
    is_completed: bool = Field(default=False, description='Статус задачи')
    created_at: datetime = Field(default=time.time(), description='Время создания записи')


class TodoItem(ToDoBase):
    id: int
    class Config:
        from_attributes = True


class ToDoCreate(ToDoBase):
    pass


class ToDoUpdate(ToDoBase):
    pass
