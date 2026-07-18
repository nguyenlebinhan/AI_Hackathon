from app.exceptions import NotFoundError
from app.model.users import User


def enforce_same_commune(
    *,
    actor: User,
    resource_commune_id: str | None,
    resource_type: str,
    resource_id: str,
) -> None:
    if resource_commune_id is None or resource_commune_id != actor.commune_id:
        # Deliberately indistinguishable from an absent resource.
        raise NotFoundError(resource_type, resource_id)

