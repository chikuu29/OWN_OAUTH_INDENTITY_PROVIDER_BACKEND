# from app.models.client import OAuthClient  # Import all models

# # Ensure Alembic loads all models
# __all__ = ["OAuthClient"]




# from app.models.client import OAuthClient  # Import all models

# # Ensure Alembic loads all models
# __all__ = ["OAuthClient"]




import pkgutil
import importlib
import sys


# Base = declarative_base()

# Automatically import all modules inside the 'models' folder
package_name = __name__

for _, module_name, _ in pkgutil.iter_modules([__path__[0]]):
    # print(f"{package_name}.{module_name}")
    module = importlib.import_module(f"{package_name}.{module_name}")
    for attr in dir(module):
        obj = getattr(module, attr)
        if isinstance(obj, type) and hasattr(obj, "__table__"):
            setattr(sys.modules[__name__], attr, obj)  # Register model dynamically
