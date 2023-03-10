from enum import Enum

class Role(Enum):
    ADMIN = 'admin'
    MISSION_RUNNER = 'mission_runner'
    MISSION_PUBLISHER = 'mission_publisher'

    @staticmethod
    def isValid(value:str):
        allowed = [r.value for r in Role]
        return value in allowed

class Action(Enum):
    INSERT = 'insert'
    UPDATE = 'update'
    DELETE = 'delete'

    @staticmethod
    def isValid(value:str):
        allowed = [r.value for r in Action]
        return value in allowed