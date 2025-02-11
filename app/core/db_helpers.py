# from sqlalchemy.orm import De


from app.db.database import Base


def model_to_dict(model, exclude_fields=None):
    """
    Convert a SQLAlchemy model instance to a dictionary, 
    excluding specified fields.
    
    :param model: SQLAlchemy model instance
    :param exclude_fields: List of fields to exclude
    :return: Dictionary representation of the model
    """
    if not exclude_fields:
        exclude_fields = []

    try:
        return {
            column.name: getattr(model, column.name)
            for column in model.__table__.columns
            if column.name not in exclude_fields
        }
    except Exception as e:
        return {}
    
  




# from sqlalchemy.orm import DeclarativeMeta, RelationshipProperty

# def model_to_dict(model, exclude_fields=None, include_relationships=False):
#     """
#     Convert a SQLAlchemy model instance to a dictionary,
#     excluding specified fields and optionally including relationships.

#     :param model: SQLAlchemy model instance
#     :param exclude_fields: List of fields to exclude
#     :param include_relationships: Boolean to include relationships
#     :return: Dictionary representation of the model
#     """
#     if not exclude_fields:
#         exclude_fields = []

#     data = {}

#     if isinstance(model.__class__, DeclarativeMeta):
#         # Convert normal columns
#         for column in model.__table__.columns:
#             if column.name not in exclude_fields:
#                 data[column.name] = getattr(model, column.name)

#         # Convert relationships (optional)
#         if include_relationships:
#             for relationship in model.__mapper__.relationships:
#                 if relationship.key not in exclude_fields:
#                     related_obj = getattr(model, relationship.key)
#                     if related_obj:
#                         if relationship.uselist:  # One-to-Many or Many-to-Many
#                             data[relationship.key] = [model_to_dict(obj, exclude_fields) for obj in related_obj]
#                         else:  # One-to-One
#                             data[relationship.key] = model_to_dict(related_obj, exclude_fields)

#     return data
