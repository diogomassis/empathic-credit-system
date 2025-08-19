from pydantic import BaseModel
from typing import Optional

class UserCreateDTO(BaseModel):
	email: str
	password: str

class UserDTO(BaseModel):
	"""
	Data Transfer Object (DTO) for representing a user.

	Attributes:
		id (str): Unique identifier for the user.
		email (str): Email address of the user.
		created_at (Optional[str]): Timestamp indicating when the user was created. Defaults to None.
		updated_at (Optional[str]): Timestamp indicating when the user was last updated. Defaults to None.
		password_hash (Optional[str]): Hashed password of the user. Defaults to None.
	"""
	id: str
	email: str
	created_at: Optional[str]
	updated_at: Optional[str]
	password_hash: Optional[str] = None
