from noveland.reader_delivery.contracts import (
    ReaderMediaDescriptor,
    ReaderMediaObjectDescriptor,
    ReaderMediaReferenceDescriptor,
)
from noveland.reader_delivery.service import ReaderMediaDeliveryService

PACKAGE_NAME = "reader_delivery"

__all__ = [
    "PACKAGE_NAME",
    "ReaderMediaDeliveryService",
    "ReaderMediaDescriptor",
    "ReaderMediaObjectDescriptor",
    "ReaderMediaReferenceDescriptor",
]
