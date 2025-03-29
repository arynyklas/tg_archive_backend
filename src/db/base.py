from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Mapped, mapped_column
from datetime import datetime

import sqlalchemy as sa


class BaseModel(MappedAsDataclass, DeclarativeBase):
    inserted_at: Mapped[datetime] = mapped_column(server_default=sa.func.now(), nullable=False, init=False)
