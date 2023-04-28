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

class AuctionInfo(_message.Message):
    __slots__ = ["auction_id", "auction_name", "base_price", "buyer_status", "current_price", "finished", "item_name", "round_id", "seller_username", "started", "transaction_price", "winner_username"]
    AUCTION_ID_FIELD_NUMBER: _ClassVar[int]
    AUCTION_NAME_FIELD_NUMBER: _ClassVar[int]
    BASE_PRICE_FIELD_NUMBER: _ClassVar[int]
    BUYER_STATUS_FIELD_NUMBER: _ClassVar[int]
    CURRENT_PRICE_FIELD_NUMBER: _ClassVar[int]
    FINISHED_FIELD_NUMBER: _ClassVar[int]
    ITEM_NAME_FIELD_NUMBER: _ClassVar[int]
    ROUND_ID_FIELD_NUMBER: _ClassVar[int]
    SELLER_USERNAME_FIELD_NUMBER: _ClassVar[int]
    STARTED_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_PRICE_FIELD_NUMBER: _ClassVar[int]
    WINNER_USERNAME_FIELD_NUMBER: _ClassVar[int]
    auction_id: str
    auction_name: str
    base_price: int
    buyer_status: _containers.RepeatedCompositeFieldContainer[BuyerStatus]
    current_price: int
    finished: bool
    item_name: str
    round_id: int
    seller_username: str
    started: bool
    transaction_price: int
    winner_username: str
    def __init__(self, auction_id: _Optional[str] = ..., auction_name: _Optional[str] = ..., seller_username: _Optional[str] = ..., item_name: _Optional[str] = ..., base_price: _Optional[int] = ..., started: bool = ..., finished: bool = ..., current_price: _Optional[int] = ..., round_id: _Optional[int] = ..., winner_username: _Optional[str] = ..., transaction_price: _Optional[int] = ..., buyer_status: _Optional[_Iterable[_Union[BuyerStatus, _Mapping]]] = ...) -> None: ...

class BuyerStatus(_message.Message):
    __slots__ = ["active", "username"]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    active: bool
    username: str
    def __init__(self, username: _Optional[str] = ..., active: bool = ...) -> None: ...

class CreateReponse(_message.Message):
    __slots__ = ["auction_id", "message", "success"]
    AUCTION_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    auction_id: str
    message: str
    success: bool
    def __init__(self, success: bool = ..., auction_id: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class CreateRequest(_message.Message):
    __slots__ = ["auction_name", "item_name", "username"]
    AUCTION_NAME_FIELD_NUMBER: _ClassVar[int]
    ITEM_NAME_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    auction_name: str
    item_name: str
    username: str
    def __init__(self, username: _Optional[str] = ..., auction_name: _Optional[str] = ..., item_name: _Optional[str] = ...) -> None: ...

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

class SuccessMessage(_message.Message):
    __slots__ = ["message", "success"]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    message: str
    success: bool
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class User(_message.Message):
    __slots__ = ["username"]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    username: str
    def __init__(self, username: _Optional[str] = ...) -> None: ...

class UserAuctionPair(_message.Message):
    __slots__ = ["auction_id", "username"]
    AUCTION_ID_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    auction_id: str
    username: str
    def __init__(self, username: _Optional[str] = ..., auction_id: _Optional[str] = ...) -> None: ...

class User_Address(_message.Message):
    __slots__ = ["ip_address", "port", "username"]
    IP_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    ip_address: str
    port: str
    username: str
    def __init__(self, username: _Optional[str] = ..., ip_address: _Optional[str] = ..., port: _Optional[str] = ...) -> None: ...
