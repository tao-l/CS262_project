from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AE_Request(_message.Message):
    __slots__ = ["entries", "leader_commit", "leader_id", "prev_log_index", "prev_log_term", "term"]
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    LEADER_COMMIT_FIELD_NUMBER: _ClassVar[int]
    LEADER_ID_FIELD_NUMBER: _ClassVar[int]
    PREV_LOG_INDEX_FIELD_NUMBER: _ClassVar[int]
    PREV_LOG_TERM_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[LogEntry]
    leader_commit: int
    leader_id: int
    prev_log_index: int
    prev_log_term: int
    term: int
    def __init__(self, term: _Optional[int] = ..., leader_id: _Optional[int] = ..., prev_log_index: _Optional[int] = ..., prev_log_term: _Optional[int] = ..., entries: _Optional[_Iterable[_Union[LogEntry, _Mapping]]] = ..., leader_commit: _Optional[int] = ...) -> None: ...

class AE_Response(_message.Message):
    __slots__ = ["success", "term"]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    success: bool
    term: int
    def __init__(self, term: _Optional[int] = ..., success: bool = ...) -> None: ...

class Command(_message.Message):
    __slots__ = ["json"]
    JSON_FIELD_NUMBER: _ClassVar[int]
    json: str
    def __init__(self, json: _Optional[str] = ...) -> None: ...

class LogEntry(_message.Message):
    __slots__ = ["command", "index", "term"]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    command: Command
    index: int
    term: int
    def __init__(self, term: _Optional[int] = ..., index: _Optional[int] = ..., command: _Optional[_Union[Command, _Mapping]] = ...) -> None: ...

class Persistent(_message.Message):
    __slots__ = ["current_term", "logs", "voted_for"]
    CURRENT_TERM_FIELD_NUMBER: _ClassVar[int]
    LOGS_FIELD_NUMBER: _ClassVar[int]
    VOTED_FOR_FIELD_NUMBER: _ClassVar[int]
    current_term: int
    logs: _containers.RepeatedCompositeFieldContainer[LogEntry]
    voted_for: int
    def __init__(self, current_term: _Optional[int] = ..., voted_for: _Optional[int] = ..., logs: _Optional[_Iterable[_Union[LogEntry, _Mapping]]] = ...) -> None: ...

class RV_Request(_message.Message):
    __slots__ = ["candidate_id", "last_log_index", "last_log_term", "term"]
    CANDIDATE_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_LOG_INDEX_FIELD_NUMBER: _ClassVar[int]
    LAST_LOG_TERM_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    candidate_id: int
    last_log_index: int
    last_log_term: int
    term: int
    def __init__(self, term: _Optional[int] = ..., candidate_id: _Optional[int] = ..., last_log_index: _Optional[int] = ..., last_log_term: _Optional[int] = ...) -> None: ...

class RV_Response(_message.Message):
    __slots__ = ["term", "vote_granted"]
    TERM_FIELD_NUMBER: _ClassVar[int]
    VOTE_GRANTED_FIELD_NUMBER: _ClassVar[int]
    term: int
    vote_granted: bool
    def __init__(self, term: _Optional[int] = ..., vote_granted: bool = ...) -> None: ...
