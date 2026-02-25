from abc import ABC, abstractmethod
from typing import Dict, List, Any

class MarketplaceRules(ABC):
    """Base class for marketplace validation rules."""

    @abstractmethod
    def validate_title(self, title: str) -> Dict[str, Any]:
        """Validates the listing title."""
        pass

    @abstractmethod
    def get_mandatory_attributes(self, category_id: str) -> List[str]:
        """Returns a list of mandatory attribute IDs for a category."""
        pass

    @abstractmethod
    def validate_listing(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validates a full listing object."""
        pass