from sqlalchemy.orm import Session


class Service:
    """Base class exposing transaction ownership to application services."""

    def __init__(self, session: Session) -> None:
        self.session = session
