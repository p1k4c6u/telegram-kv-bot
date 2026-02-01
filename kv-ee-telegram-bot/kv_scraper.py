import os
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DealType(Enum):
    SALE = 3
    RENT = 2


class PropertyType(Enum):
    APARTMENT = 1
    HOUSE = 2
    ROW_HOUSE = 3
    COMMERCIAL = 4
    LAND = 5


@dataclass
class Coordinates:
    lat: float
    lon: float


@dataclass
class PropertyData:
    id: int
    url: str
    price: int
    rooms: Optional[int] = None
    area: Optional[float] = None
    year_built: Optional[int] = None
    condition: Optional[int] = None
    story: Optional[int] = None
    energy_label: Optional[str] = None
    cost_summer: Optional[int] = None
    cost_winter: Optional[int] = None
    coordinates: Optional[Coordinates] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "price": self.price,
            "rooms": self.rooms,
            "area": self.area,
            "year_built": self.year_built,
            "condition": self.condition,
            "story": self.story,
            "energy_label": self.energy_label,
            "cost_summer": self.cost_summer,
            "cost_winter": self.cost_winter,
            "coordinates": {
                "lat": self.coordinates.lat if self.coordinates else None,
                "lon": self.coordinates.lon if self.coordinates else None,
            }
            if self.coordinates
            else None,
            "description": self.description,
        }


class KVeeScraper:
    BASE_URL = "https://www.kv.ee"
    SEARCH_URL = f"{BASE_URL}/?act=search.simple&search_type=new&page_size=100"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def _build_search_url(self, params: Dict[str, Any]) -> str:
        url = self.SEARCH_URL

        # Convert enums to their values
        if "deal_type" in params and isinstance(params["deal_type"], DealType):
            params["deal_type"] = params["deal_type"].value
        if "property_type" in params and isinstance(
            params["property_type"], PropertyType
        ):
            params["property_type"] = params["property_type"].value

        # Add parameters to URL
        for key, val in params.items():
            if isinstance(val, (int, str)):
                url += f"&{key}={val}"
            elif isinstance(val, list):
                for n, item in enumerate(val):
                    url += f"&{key}%5B{n}%5D={item}"

        return url

    def _parse_coordinates(self, href: str) -> Optional[Coordinates]:
        try:
            coords = re.findall(r"(\d{2}\.\d{7})", href)
            if len(coords) == 2:
                return Coordinates(lat=float(coords[0]), lon=float(coords[1]))
        except Exception as e:
            logger.warning(f"Failed to parse coordinates: {e}")
        return None

    def _parse_listing_data(self, listing_element) -> Optional[PropertyData]:
        try:
            obj_id = listing_element.get("id")
            if not obj_id:
                return None

            obj_id = int(obj_id)
            obj_url = f"{self.BASE_URL}/{obj_id}"

            # Get detailed listing page
            response = self.session.get(obj_url)
            if not response.ok:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Parse price
            price_info = soup.find("div", "object-price")
            price = 0
            if price_info:
                price_text = (
                    price_info.findChild("strong").text.strip()
                    if price_info.findChild("strong")
                    else ""
                )
                price_match = re.search(r"(\d+)", price_text)
                if price_match:
                    price = int(price_match.group())

            # Parse main info
            data = {}
            main_info_grid = soup.find_all("table", "object-data-meta")[-1]
            for row in main_info_grid.findChildren("tr"):
                key_elem = row.findChild("th")
                val_elem = row.findChild("td")
                if key_elem and val_elem:
                    key = key_elem.text.lower().strip()
                    val = val_elem.text.strip()

                    if key == "tube":
                        data["rooms"] = int(val)
                    elif key == "õldpind":
                        area_match = re.search(r"(\d+(?:\.(?:\d))?)", val)
                        if area_match:
                            data["area"] = float(area_match.group())
                    elif key == "ehitusaasta":
                        data["year_built"] = int(val)
                    elif key == "seisukord":
                        condition_map = {
                            "Vajab renoveerimist": 1,
                            "Vajab san. remonti": 2,
                            "Ühendatud": 3,
                            "San. remont tehtud": 4,
                            "Renoveeritud": 5,
                            "Heas korras": 6,
                            "Uus": 7,
                            "Uusarendus": 8,
                        }
                        data["condition"] = condition_map.get(val)
                    elif key == "korrus/korruseid":
                        story_match = re.search(r"(\d+)(?:/\d+)", val)
                        if story_match:
                            data["story"] = int(story_match.group(1))
                    elif key == "energiamärgis":
                        energy_match = re.search(r"([A-Z]{1})", val)
                        if energy_match and energy_match.group() != "P":
                            data["energy_label"] = energy_match.group()
                    elif key == "kulud suvel/talvel":
                        costs = re.findall(r"(\d+)", val)
                        if len(costs) == 2:
                            data["cost_summer"] = int(costs[0])
                            data["cost_winter"] = int(costs[1])

            # Parse coordinates
            coordinates_elem = soup.find("a", "icon icon-new-tab gtm-object-map")
            coordinates = None
            if coordinates_elem and "href" in coordinates_elem.attrs:
                coordinates = self._parse_coordinates(coordinates_elem["href"])

            # Get description
            description_elem = soup.find("div", "object-description")
            description = description_elem.text.strip() if description_elem else None

            return PropertyData(
                id=obj_id,
                url=obj_url,
                price=price,
                rooms=data.get("rooms"),
                area=data.get("area"),
                year_built=data.get("year_built"),
                condition=data.get("condition"),
                story=data.get("story"),
                energy_label=data.get("energy_label"),
                cost_summer=data.get("cost_summer"),
                cost_winter=data.get("cost_winter"),
                coordinates=coordinates,
                description=description,
            )

        except Exception as e:
            logger.error(f"Error parsing listing data: {e}")
            return None

    def get_owner_direct_listings(
        self,
        county: int = 9,  # Tallinn
        deal_type: DealType = DealType.SALE,
        property_type: Optional[PropertyType] = None,
        price_min: Optional[int] = None,
        price_max: Optional[int] = None,
        area_min: Optional[float] = None,
        area_max: Optional[float] = None,
        rooms_min: Optional[int] = None,
        rooms_max: Optional[int] = None,
        page_size: int = 100,
    ) -> List[PropertyData]:
        """
        Get owner direct listings from KV.ee

        Args:
            county: County ID (9 = Tallinn)
            deal_type: Sale or Rent
            property_type: Property type filter
            price_min: Minimum price
            price_max: Maximum price
            area_min: Minimum area in m²
            area_max: Maximum area in m²
            rooms_min: Minimum number of rooms
            rooms_max: Maximum number of rooms
            page_size: Number of results per page

        Returns:
            List of PropertyData objects
        """
        params = {
            "deal_type": deal_type,
            "county": county,
            "page_size": page_size,
            "only_private_users": 1,  # Only private users (owner direct)
        }

        if property_type:
            params["property_type"] = property_type
        if price_min:
            params["price_min"] = price_min
        if price_max:
            params["price_max"] = price_max
        if area_min:
            params["area_min"] = area_min
        if area_max:
            params["area_max"] = area_max
        if rooms_min:
            params["rooms_min"] = rooms_min
        if rooms_max:
            params["rooms_max"] = rooms_max

        search_url = self._build_search_url(params)
        logger.info(f"Searching KV.ee with URL: {search_url}")

        try:
            response = self.session.get(search_url)
            if not response.ok:
                logger.error(f"Failed to fetch search results: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            # Find all listing elements
            listing_elements = soup.find_all("tr", "object-item")
            logger.info(f"Found {len(listing_elements)} listings")

            listings = []
            for elem in listing_elements:
                listing_data = self._parse_listing_data(elem)
                if listing_data:
                    listings.append(listing_data)

            return listings

        except Exception as e:
            logger.error(f"Error fetching listings: {e}")
            return []

    def get_listing_details(self, listing_id: int) -> Optional[PropertyData]:
        """Get detailed information for a specific listing"""
        listing_url = f"{self.BASE_URL}/{listing_id}"
        try:
            response = self.session.get(listing_url)
            if not response.ok:
                return None

            soup = BeautifulSoup(response.text, "html.parser")
            return self._parse_listing_data(soup.find("tr", "object-item"))

        except Exception as e:
            logger.error(f"Error fetching listing details: {e}")
            return None


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    scraper = KVeeScraper()

    # Example: Get owner direct apartment listings in Tallinn
    listings = scraper.get_owner_direct_listings(
        county=9,  # Tallinn
        deal_type=DealType.SALE,
        property_type=PropertyType.APARTMENT,
        price_min=50000,
        price_max=200000,
        rooms_min=2,
        area_min=40,
    )

    print(f"Found {len(listings)} owner direct listings:")
    for listing in listings[:5]:  # Print first 5
        print(
            f"{listing.id}: {listing.price}€ - {listing.rooms} rooms, {listing.area}m²"
        )
        print(f"URL: {listing.url}")
        if listing.coordinates:
            print(f"Coordinates: {listing.coordinates.lat}, {listing.coordinates.lon}")
        print("-" * 50)
