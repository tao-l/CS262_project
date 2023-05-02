from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AnnouncePriceRequest(_message.Message):
    __slots__ = ["auction_id", "buyer_status", "price", "round_id"]
    AUCTION_ID_FIELD_NUMBER: _ClassVar[int]
    BUYER_STATUS_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    ROUND_ID_FIELD_NUMBER: _ClassVar[int]
    auction_id: str
    buyer_status: _containers.RepeatedCompositeFieldContainer[BuyerStatus]
    price: int
    round_id: int
    def __init__(self, auction_id: _Optional[str] = ..., round_id: _Optional[int] = ..., price: _Optional[int] = ..., buyer_status: _Optional[_Iterable[_Union[BuyerStatus, _Mapping]]] = ...) -> None: ...

class BuyerStatus(_message.Message):
    __slots__ = ["active", "username"]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    active: bool
    username: str
    def __init__(self, username: _Optional[str] = ..., active: bool = ...) -> None: ...

class FinishAuctionRequest(_message.Message):
    __slots__ = ["auction_id", "buyer_status", "price", "winner_username"]
    AUCTION_ID_FIELD_NUMBER: _ClassVar[int]
    BUYER_STATUS_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    WINNER_USERNAME_FIELD_NUMBER: _ClassVar[int]
    auction_id: str
    buyer_status: _containers.RepeatedCompositeFieldContainer[BuyerStatus]
    price: int
    winner_username: str
    def __init__(self, auction_id: _Optional[str] = ..., winner_username: _Optional[str] = ..., price: _Optional[int] = ..., buyer_status: _Optional[_Iterable[_Union[BuyerStatus, _Mapping]]] = ...) -> None: ...

class PlatformServiceRequest(_message.Message):
    __slots__ = ["json"]
    JSON_FIELD_NUMBER: _ClassVar[int]
    json: str
    def __init__(self, json: _Optional[str] = ...) -> None: ...

class PlatformServiceResponse(_message.Message):
    __slots__ = ["is_leader", "json"]
    IS_LEADER_FIELD_NUMBER: _ClassVar[int]
    JSON_FIELD_NUMBER: _ClassVar[int]
    is_leader: bool
    json: str
    def __init__(self, is_leader: bool = ..., json: _Optional[str] = ...) -> None: ...

class SuccessMessage(_message.Message):
    __slots__ = ["message", "success"]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    message: str
    success: bool
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class UserAuctionPair(_message.Message):
    __slots__ = ["auction_id", "username"]
    AUCTION_ID_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    auction_id: str
    username: str
    def __init__(self, username: _Optional[str] = ..., auction_id: _Optional[str] = ...) -> None: ...
