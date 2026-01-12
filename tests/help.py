

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])


print(pwd_context.hash("password"))