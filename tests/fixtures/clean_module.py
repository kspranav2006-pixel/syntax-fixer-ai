"""Clean module with perfectly valid Python syntax."""

def multiply(a: int, b: int) -> int:
    """Returns the product of two integers."""
    return a * b


class Greeter:
    def __init__(self, greeting: str = "Hello"):
        self.greeting = greeting

    def say_hello(self, name: str) -> str:
        return f"{self.greeting}, {name}!"
