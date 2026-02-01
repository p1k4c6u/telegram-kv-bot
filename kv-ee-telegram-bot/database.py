import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(
        self,
        users_path: str = "users.json",
        seen_listings_path: str = "seen_listings.json",
    ):
        self.users_path = users_path
        self.seen_listings_path = seen_listings_path
        self.users: Dict[int, Dict] = {}
        self.seen_listings: Set[int] = set()

        self._load_data()

    def _load_data(self):
        """Load data from JSON files"""
        try:
            # Load users
            if os.path.exists(self.users_path):
                with open(self.users_path, "r", encoding="utf-8") as f:
                    self.users = json.load(f)

            # Load seen listings
            if os.path.exists(self.seen_listings_path):
                with open(self.seen_listings_path, "r", encoding="utf-8") as f:
                    self.seen_listings = set(json.load(f))

        except Exception as e:
            logger.error(f"Error loading database: {e}")
            self.users = {}
            self.seen_listings = set()

    def _save_data(self):
        """Save data to JSON files"""
        try:
            # Save users
            with open(self.users_path, "w", encoding="utf-8") as f:
                json.dump(self.users, f, indent=2, default=str)

            # Save seen listings
            with open(self.seen_listings_path, "w", encoding="utf-8") as f:
                json.dump(list(self.seen_listings), f, indent=2)

        except Exception as e:
            logger.error(f"Error saving database: {e}")

    def add_user(self, chat_id: int, preferences: Dict):
        """Add a new user"""
        self.users[str(chat_id)] = preferences
        self._save_data()

    def get_user(self, chat_id: int) -> Optional[Dict]:
        """Get user preferences"""
        return self.users.get(str(chat_id))

    def update_user(self, chat_id: int, preferences: Dict):
        """Update user preferences"""
        if str(chat_id) in self.users:
            self.users[str(chat_id)].update(preferences)
            self._save_data()

    def delete_user(self, chat_id: int):
        """Delete a user"""
        if str(chat_id) in self.users:
            del self.users[str(chat_id)]
            self._save_data()

    def mark_seen(self, listing_id: int):
        """Mark a listing as seen"""
        self.seen_listings.add(listing_id)
        # Keep only the last 10000 seen listings to prevent memory issues
        if len(self.seen_listings) > 10000:
            self.seen_listings = set(list(self.seen_listings)[-10000:])
        self._save_data()

    def is_seen(self, listing_id: int) -> bool:
        """Check if a listing has been seen"""
        return listing_id in self.seen_listings

    def cleanup_old_seen(self, days: int = 30):
        """Remove seen listings older than X days"""
        # Note: This implementation would require storing timestamps
        # For simplicity, we'll just limit the total number of seen listings
        if len(self.seen_listings) > 10000:
            self.seen_listings = set(list(self.seen_listings)[-10000:])
            self._save_data()

    def get_all_users(self) -> Dict[int, Dict]:
        """Get all users with chat_id as int"""
        return {int(chat_id): prefs for chat_id, prefs in self.users.items()}

    def get_subscribed_users(self) -> Dict[int, Dict]:
        """Get all subscribed users"""
        return {
            int(chat_id): prefs
            for chat_id, prefs in self.users.items()
            if prefs.get("subscribed", False)
        }

    def get_users_by_notification_mode(self, mode: str) -> Dict[int, Dict]:
        """Get users by notification mode"""
        return {
            int(chat_id): prefs
            for chat_id, prefs in self.users.items()
            if prefs.get("notification_mode") == mode
        }


# Global database instance
_db = None


def get_database() -> Database:
    """Get the global database instance"""
    global _db
    if _db is None:
        _db = Database()
    return _db


# Convenience functions
def add_user(chat_id: int, preferences: Dict):
    get_database().add_user(chat_id, preferences)


def get_user(chat_id: int) -> Optional[Dict]:
    return get_database().get_user(chat_id)


def update_user(chat_id: int, preferences: Dict):
    get_database().update_user(chat_id, preferences)


def delete_user(chat_id: int):
    get_database().delete_user(chat_id)


def mark_seen(listing_id: int):
    get_database().mark_seen(listing_id)


def is_seen(listing_id: int) -> bool:
    return get_database().is_seen(listing_id)


def cleanup_old_seen(days: int = 30):
    get_database().cleanup_old_seen(days)


def get_all_users() -> Dict[int, Dict]:
    return get_database().get_all_users()


def get_subscribed_users() -> Dict[int, Dict]:
    return get_database().get_subscribed_users()


def get_users_by_notification_mode(mode: str) -> Dict[int, Dict]:
    return get_database().get_users_by_notification_mode(mode)


if __name__ == "__main__":
    # Test the database
    db = get_database()

    # Add test user
    test_user = {
        "chat_id": 123456,
        "notification_mode": "immediate",
        "subscribed": True,
        "filters": {
            "price_min": 50000,
            "price_max": 300000,
            "area_min": 40.0,
            "rooms_min": 2,
        },
    }

    db.add_user(123456, test_user)
    print(f"User added: {db.get_user(123456)}")

    # Mark some listings as seen
    db.mark_seen(1001)
    db.mark_seen(1002)
    print(f"Seen listings: {len(db.seen_listings)}")
    print(f"Is 1001 seen? {db.is_seen(1001)}")
    print(f"Is 9999 seen? {db.is_seen(9999)}")
