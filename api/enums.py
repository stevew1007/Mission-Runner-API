from enum import Enum


class Role(Enum):
    ADMIN = 'admin'
    MISSION_RUNNER = 'mission_runner'
    MISSION_PUBLISHER = 'mission_publisher'

    @staticmethod
    def isValid(value: str):
        allowed = [r.value for r in Role]
        return value in allowed

    @staticmethod
    def to_str():
        return ','.join([r.value for r in Role])


class Status(Enum):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    ACCEPTED = 'accepted'
    COMPLETED = 'completed'
    PAID = 'paid'
    ARCHIVED = 'archived'
    DONE = 'done'
    ISSUE = 'issue'

    @staticmethod
    def isValid(value: str):
        allowed = [r.value for r in Status]
        return value in allowed

    @staticmethod
    def to_str():
        return ','.join([r.value for r in Status])

    @staticmethod
    def next(value: str):
        """Define the state machine
        """
        if value == Status.PUBLISHED.value:
            return [Status.ACCEPTED.value, Status.ARCHIVED.value]
        elif value == Status.ACCEPTED.value:
            return [Status.COMPLETED.value, Status.PUBLISHED.value]
        elif value == Status.COMPLETED.value:
            return [Status.PAID.value]
        elif value == Status.PAID.value:
            return [Status.DONE.value]
        elif value in [Status.DONE.value, Status.ARCHIVED.value, Status.ISSUE]:
            return [value]  # Termial state will return itself.
        else:
            raise ValueError(f'Invalid type {value}')

    @staticmethod
    def isTerminal(value: str):
        return value in [
            Status.DONE.value,
            Status.ARCHIVED.value,
            Status.ISSUE,
        ]


class Action(Enum):
    INSERT = 'insert'
    UPDATE = 'update'
    DELETE = 'delete'

    @staticmethod
    def isValid(value: str):
        allowed = [r.value for r in Action]
        return value in allowed
