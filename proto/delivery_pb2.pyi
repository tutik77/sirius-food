from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Actor(_message.Message):
    __slots__ = ("user_id", "role")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    user_id: int
    role: str
    def __init__(self, user_id: _Optional[int] = ..., role: _Optional[str] = ...) -> None: ...

class AssignCourierRequest(_message.Message):
    __slots__ = ("order_id", "courier_id")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    COURIER_ID_FIELD_NUMBER: _ClassVar[int]
    order_id: int
    courier_id: int
    def __init__(self, order_id: _Optional[int] = ..., courier_id: _Optional[int] = ...) -> None: ...

class GetDeliveryRequest(_message.Message):
    __slots__ = ("delivery_id", "actor")
    DELIVERY_ID_FIELD_NUMBER: _ClassVar[int]
    ACTOR_FIELD_NUMBER: _ClassVar[int]
    delivery_id: int
    actor: Actor
    def __init__(self, delivery_id: _Optional[int] = ..., actor: _Optional[_Union[Actor, _Mapping]] = ...) -> None: ...

class ListCourierDeliveriesRequest(_message.Message):
    __slots__ = ("courier_id",)
    COURIER_ID_FIELD_NUMBER: _ClassVar[int]
    courier_id: int
    def __init__(self, courier_id: _Optional[int] = ...) -> None: ...

class CompleteDeliveryRequest(_message.Message):
    __slots__ = ("delivery_id", "actor")
    DELIVERY_ID_FIELD_NUMBER: _ClassVar[int]
    ACTOR_FIELD_NUMBER: _ClassVar[int]
    delivery_id: int
    actor: Actor
    def __init__(self, delivery_id: _Optional[int] = ..., actor: _Optional[_Union[Actor, _Mapping]] = ...) -> None: ...

class TrackDeliveryRequest(_message.Message):
    __slots__ = ("delivery_id", "actor")
    DELIVERY_ID_FIELD_NUMBER: _ClassVar[int]
    ACTOR_FIELD_NUMBER: _ClassVar[int]
    delivery_id: int
    actor: Actor
    def __init__(self, delivery_id: _Optional[int] = ..., actor: _Optional[_Union[Actor, _Mapping]] = ...) -> None: ...

class DeliveryReply(_message.Message):
    __slots__ = ("id", "order_id", "courier_id", "status")
    ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    COURIER_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    id: int
    order_id: int
    courier_id: int
    status: str
    def __init__(self, id: _Optional[int] = ..., order_id: _Optional[int] = ..., courier_id: _Optional[int] = ..., status: _Optional[str] = ...) -> None: ...

class DeliveryList(_message.Message):
    __slots__ = ("deliveries",)
    DELIVERIES_FIELD_NUMBER: _ClassVar[int]
    deliveries: _containers.RepeatedCompositeFieldContainer[DeliveryReply]
    def __init__(self, deliveries: _Optional[_Iterable[_Union[DeliveryReply, _Mapping]]] = ...) -> None: ...

class DeliveryStatusUpdate(_message.Message):
    __slots__ = ("delivery_id", "status")
    DELIVERY_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    delivery_id: int
    status: str
    def __init__(self, delivery_id: _Optional[int] = ..., status: _Optional[str] = ...) -> None: ...

class ChatMessage(_message.Message):
    __slots__ = ("delivery_id", "sender", "text")
    DELIVERY_ID_FIELD_NUMBER: _ClassVar[int]
    SENDER_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    delivery_id: int
    sender: str
    text: str
    def __init__(self, delivery_id: _Optional[int] = ..., sender: _Optional[str] = ..., text: _Optional[str] = ...) -> None: ...
