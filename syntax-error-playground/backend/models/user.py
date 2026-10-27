"""User model module."""

from dataclasses import dataclass
from typing import Optional


class UserProfile
    def __init__(self, username: str email: str, age: int = 18):
        self.username = username
        self.email = email
        self.age = age

    def get_display_name(self) -> str:
        return f"User: {self.username} ({self.email})"

    def is_adult(self) -> bool
        if self.age >= 18
            return True
        return False
