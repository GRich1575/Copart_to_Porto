"""SQLAlchemy models (schema). Importing this package registers every table on Base.metadata."""

from vehicle_intelligence.models.auction import AuctionLot
from vehicle_intelligence.models.base import Base
from vehicle_intelligence.models.logistics import ShipmentQuote
from vehicle_intelligence.models.market import LocalListing
from vehicle_intelligence.models.monitoring import CollectorRun
from vehicle_intelligence.models.notification import ProxyNotification
from vehicle_intelligence.models.regulation import FeeRule, ImportRule
from vehicle_intelligence.models.repair import RepairEstimate

__all__ = [
    "Base",
    "AuctionLot",
    "LocalListing",
    "FeeRule",
    "ImportRule",
    "ShipmentQuote",
    "RepairEstimate",
    "CollectorRun",
    "ProxyNotification",
]
