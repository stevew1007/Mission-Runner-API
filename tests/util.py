from api import db
from api.models import ChangeLog
from api.enums import Action


def check_log(log: ChangeLog, object_type: str,
              object_id: int, requester_id: int,
              operation: Action, attribute_name: str,
              old_value: str, new_value: str):
    """Check a single entry in the database.
    """
    assert log.object_type == object_type
    assert log.object_id == object_id
    assert log.requester_id == requester_id
    assert log.operation == operation.value
    assert log.attribute_name == attribute_name
    assert log.old_value == old_value
    assert log.new_value == new_value


def check_last_log_entry(n: int, old: dict, new: dict,
                         object_type: str, object_id: int,
                         requester_id: int, operation: Action):
    """ Check the last n entries in the database.
    """
    logs = db.session.query(ChangeLog)\
        .order_by(ChangeLog.id.desc()).limit(n).all()

    if operation == Action.INSERT:
        assert n == 1
        check_log(
            logs[0], object_type, object_id,
            requester_id, operation,
            '', '', f"Add {object_type} ID: {object_id}")
        return
    if operation == Action.DELETE:
        assert n == 1
        check_log(
            logs[0], object_type, object_id,
            requester_id, operation,
            '', '', f"Delete {object_type} ID: {object_id}")
        return
    if operation == Action.UPDATE:
        assert len(list(old.keys())) == n
        assert old.keys() == new.keys()

        for i, key in enumerate(old.keys()):
            check_log(
                logs[i-1], object_type, object_id,
                requester_id, operation,
                key, str(old[key]), str(new[key]))
