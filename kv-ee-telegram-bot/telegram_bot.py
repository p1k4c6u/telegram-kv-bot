import os
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from enum import Enum

from telegram import Update, Bot, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from kv_scraper import KVeeScraper, PropertyData, DealType, PropertyType

logger = logging.getLogger(__name__)


class NotificationMode(Enum):
    IMMEDIATE = "immediate"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class UserPreferences:
    chat_id: int
    notification_mode: NotificationMode = NotificationMode.IMMEDIATE
    last_notification: datetime = None
    filters: Dict[str, Any] = None
    subscribed: bool = True


class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.bot = Bot(token=token)
        self.application = Application.builder().token(token).build()

        self.scraper = KVeeScraper()
        self.users: Dict[int, UserPreferences] = {}
        self.seen_listings: Set[int] = set()
        self.notifications_enabled = True

        self._load_users()

        # Setup handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("subscribe", self.cmd_subscribe))
        self.application.add_handler(
            CommandHandler("unsubscribe", self.cmd_unsubscribe)
        )
        self.application.add_handler(CommandHandler("settings", self.cmd_settings))
        self.application.add_handler(CommandHandler("list", self.cmd_list))
        self.application.add_handler(CommandHandler("notify", self.cmd_notify))
        self.application.add_handler(CommandHandler("stop", self.cmd_stop))

        # Setup scheduler
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(self._check_new_listings, "interval", minutes=15)
        self.scheduler.add_job(self._send_daily_notifications, "cron", hour=9, minute=0)
        self.scheduler.add_job(
            self._send_weekly_notifications, "cron", day_of_week="mon", hour=9, minute=0
        )

    def _load_users(self):
        """Load user preferences from file"""
        if os.path.exists("users.json"):
            try:
                with open("users.json", "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                    for chat_id, data in user_data.items():
                        self.users[int(chat_id)] = UserPreferences(**data)
            except Exception as e:
                logger.error(f"Error loading users: {e}")

    def _save_users(self):
        """Save user preferences to file"""
        try:
            user_data = {
                str(chat_id): {
                    "chat_id": prefs.chat_id,
                    "notification_mode": prefs.notification_mode.value,
                    "last_notification": prefs.last_notification.isoformat()
                    if prefs.last_notification
                    else None,
                    "filters": prefs.filters,
                    "subscribed": prefs.subscribed,
                }
                for chat_id, prefs in self.users.items()
            }
            with open("users.json", "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving users: {e}")

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        chat_id = update.effective_chat.id

        if chat_id not in self.users:
            self.users[chat_id] = UserPreferences(
                chat_id=chat_id,
                notification_mode=NotificationMode.IMMEDIATE,
                filters={},
            )
            self._save_users()

        await update.message.reply_text(
            f"\n"
            f"👋 Welcome to KV.ee Owner Direct Listings Bot!\n"
            f"📁 I'll notify you about new owner direct property listings on KV.ee\n"
            f"💡 Use /help to see all available commands"
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            f"📖 <b>KV.ee Owner Direct Listings Bot - Commands</b>\n\n"
            f"📱 <b>Basic Commands:</b>\n"
            f"✅ /start - Start the bot\n"
            f"ℹ️ /help - Show this help message\n"
            f"📢 /subscribe - Subscribe to notifications\n"
            f"🛑 /unsubscribe - Unsubscribe from notifications\n"
            f"⚙️ /settings - Configure your notification preferences\n"
            f"📋 /list - Show current listings\n"
            f"🔔 /notify - Check for new listings now\n"
            f"🚪 /stop - Stop the bot\n\n"
            f"🗂️ <b>Notification Settings:</b>\n"
            f"• Choose between immediate, daily, or weekly notifications\n"
            f"• Filter by price, area, rooms, and location\n"
            f"• Get owner direct listings only\n"
            f"🏠 <b>Filters:</b>\n"
            f"• /set_price_min <amount> - Minimum price\n"
            f"• /set_price_max <amount> - Maximum price\n"
            f"• /set_area_min <area> - Minimum area (m²)\n"
            f"• /set_area_max <area> - Maximum area (m²)\n"
            f"• /set_rooms_min <rooms> - Minimum rooms\n"
            f"• /set_rooms_max <rooms> - Maximum rooms\n"
            f"• /set_county <county_id> - Set county (9=Talinn)\n"
        )

        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

    async def cmd_subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command"""
        chat_id = update.effective_chat.id

        if chat_id not in self.users:
            self.users[chat_id] = UserPreferences(
                chat_id=chat_id,
                notification_mode=NotificationMode.IMMEDIATE,
                filters={},
            )
            self._save_users()

        self.users[chat_id].subscribed = True
        self._save_users()

        await update.message.reply_text(
            f"✅ You have been subscribed to notifications!\n"
            f"📱 You'll receive updates based on your notification settings."
        )

    async def cmd_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unsubscribe command"""
        chat_id = update.effective_chat.id

        if chat_id in self.users:
            self.users[chat_id].subscribed = False
            self._save_users()

        await update.message.reply_text(
            f"🛑 You have been unsubscribed from notifications.\n"
            f"📸 You won't receive any more updates."
        )

    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        chat_id = update.effective_chat.id

        if chat_id not in self.users:
            await update.message.reply_text(f"🚫 You need to /start the bot first!")
            return

        prefs = self.users[chat_id]

        settings_text = (
            f"🔧 <b>Your Notification Settings</b>\n\n"
            f"📱 <b>Notification Mode:</b> {prefs.notification_mode.value}\n"
            f"🔐 <b>Subscribed:</b> {'Yes' if prefs.subscribed else 'No'}\n\n"
            f"📋 <b>Filters:</b>\n"
        )

        if prefs.filters:
            for key, value in prefs.filters.items():
                settings_text += f"• {key.replace('_', ' ').title()}: {value}\n"
        else:
            settings_text += f"• No filters set (showing all listings)\n"

        await update.message.reply_text(settings_text, parse_mode=ParseMode.HTML)

    async def cmd_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command"""
        chat_id = update.effective_chat.id

        # Get current listings
        try:
            listings = self.scraper.get_owner_direct_listings(
                county=9,  # Tallinn
                deal_type=DealType.SALE,
                price_min=50000,
                price_max=300000,
                rooms_min=1,
                area_min=20,
            )

            if not listings:
                await update.message.reply_text(
                    f"📱 No listings found at the moment. Try again later!"
                )
                return

            # Show first 10 listings
            for i, listing in enumerate(listings[:10]):
                listing_text = (
                    f"📍 <b>Listing {i + 1}</b>\n"
                    f"🏠 <b>Type:</b> Apartment\n"
                    f"💰 <b>Price:</b> {listing.price}€\n"
                    f"👥 <b>Rooms:</b> {listing.rooms}\n"
                    f"💨 <b>Area:</b> {listing.area}m²\n"
                    f"🗂️ <b>Condition:</b> {listing.condition}\n"
                    f"📍 <b>URL:</b> {listing.url}\n"
                )

                await update.message.reply_text(listing_text, parse_mode=ParseMode.HTML)

                if i < len(listings) - 1:
                    await update.message.reply_text("-" * 20)

            if len(listings) > 10:
                await update.message.reply_text(
                    f"📊 Showing 10 of {len(listings)} listings. Use filters to narrow results."
                )

        except Exception as e:
            logger.error(f"Error listing properties: {e}")
            await update.message.reply_text(
                f"⚠️ Error fetching listings. Please try again later."
            )

    async def cmd_notify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /notify command - check for new listings immediately"""
        chat_id = update.effective_chat.id

        await update.message.reply_text(
            f"🔔 Checking for new listings... This might take a moment."
        )

        new_listings = await self._check_new_listings()

        if new_listings:
            await update.message.reply_text(
                f"🎉 Found {len(new_listings)} new listings!\n"
                f"📱 Sending them to all subscribed users..."
            )
        else:
            await update.message.reply_text(
                f"📱 No new listings found. Check back later!"
            )

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command"""
        chat_id = update.effective_chat.id

        if chat_id in self.users:
            del self.users[chat_id]
            self._save_users()

        await update.message.reply_text(
            f"👋 Goodbye! You've been removed from the bot."
            f"📱 Start again anytime with /start"
        )

    async def _check_new_listings(self) -> List[PropertyData]:
        """Check for new listings and send notifications"""
        try:
            # Get current listings
            listings = self.scraper.get_owner_direct_listings(
                county=9,  # Tallinn
                deal_type=DealType.SALE,
                price_min=50000,
                price_max=500000,
                rooms_min=1,
                area_min=20,
            )

            new_listings = []
            for listing in listings:
                if listing.id not in self.seen_listings:
                    new_listings.append(listing)
                    self.seen_listings.add(listing.id)

            # Send notifications to subscribed users
            if new_listings and self.notifications_enabled:
                await self._send_notifications(new_listings)

            return new_listings

        except Exception as e:
            logger.error(f"Error checking new listings: {e}")
            return []

    async def _send_notifications(self, listings: List[PropertyData]):
        """Send notifications to all subscribed users"""
        for chat_id, prefs in self.users.items():
            if not prefs.subscribed:
                continue

            try:
                # Filter listings based on user preferences
                filtered_listings = self._filter_listings(listings, prefs.filters)

                if not filtered_listings:
                    continue

                # Send notifications
                for listing in filtered_listings:
                    listing_text = self._format_listing(listing)
                    await self.bot.send_message(
                        chat_id, listing_text, parse_mode=ParseMode.HTML
                    )

                # Update last notification time
                prefs.last_notification = datetime.now()

            except Exception as e:
                logger.error(f"Error sending notification to {chat_id}: {e}")

        self._save_users()

    def _filter_listings(
        self, listings: List[PropertyData], filters: Dict[str, Any]
    ) -> List[PropertyData]:
        """Filter listings based on user preferences"""
        filtered = []

        for listing in listings:
            match = True

            if "price_min" in filters and listing.price < filters["price_min"]:
                match = False
            if "price_max" in filters and listing.price > filters["price_max"]:
                match = False
            if (
                "area_min" in filters
                and listing.area
                and listing.area < filters["area_min"]
            ):
                match = False
            if (
                "area_max" in filters
                and listing.area
                and listing.area > filters["area_max"]
            ):
                match = False
            if (
                "rooms_min" in filters
                and listing.rooms
                and listing.rooms < filters["rooms_min"]
            ):
                match = False
            if (
                "rooms_max" in filters
                and listing.rooms
                and listing.rooms > filters["rooms_max"]
            ):
                match = False

            if match:
                filtered.append(listing)

        return filtered

    def _format_listing(self, listing: PropertyData) -> str:
        """Format listing for Telegram message"""
        text = (
            f"📍 <b>New Property Listing!</b>\n\n"
            f"🏠 <b>Type:</b> Apartment\n"
            f"💰 <b>Price:</b> {listing.price}€\n"
            f"👥 <b>Rooms:</b> {listing.rooms}\n"
            f"💨 <b>Area:</b> {listing.area}m²\n"
            f"🗂️ <b>Condition:</b> {listing.condition}\n"
            f"🗅 <b>Year Built:</b> {listing.year_built}\n"
            f"📍 <b>URL:</b> {listing.url}\n\n"
        )

        if listing.coordinates:
            text += f"🗺️ <b>Coordinates:</b> {listing.coordinates.lat}, {listing.coordinates.lon}\n"

        if listing.description:
            text += f"📝 <b>Description:</b> {listing.description[:100]}...\n"

        return text

    async def _send_daily_notifications(self):
        """Send daily summary of new listings"""
        if not self.notifications_enabled:
            return

        try:
            listings = await self._check_new_listings()
            if not listings:
                return

            # Send daily summary to all subscribed users
            for chat_id, prefs in self.users.items():
                if (
                    not prefs.subscribed
                    or prefs.notification_mode != NotificationMode.DAILY
                ):
                    continue

                filtered_listings = self._filter_listings(listings, prefs.filters)
                if not filtered_listings:
                    continue

                summary_text = f"📅 <b>Daily Property Update ({datetime.now().strftime('%Y-%m-%d')})</b>\n\n"
                summary_text += f"🎉 Found {len(filtered_listings)} new listings!\n\n"

                for listing in filtered_listings[:5]:  # Show first 5
                    summary_text += self._format_listing(listing) + "\n"
                    summary_text += "─" * 30 + "\n\n"

                if len(filtered_listings) > 5:
                    summary_text += f"📊 Showing 5 of {len(filtered_listings)} listings. View more with /list\n"

                await self.bot.send_message(
                    chat_id, summary_text, parse_mode=ParseMode.HTML
                )

        except Exception as e:
            logger.error(f"Error sending daily notifications: {e}")

    async def _send_weekly_notifications(self):
        """Send weekly summary of new listings"""
        if not self.notifications_enabled:
            return

        try:
            listings = await self._check_new_listings()
            if not listings:
                return

            # Send weekly summary to all subscribed users
            for chat_id, prefs in self.users.items():
                if (
                    not prefs.subscribed
                    or prefs.notification_mode != NotificationMode.WEEKLY
                ):
                    continue

                filtered_listings = self._filter_listings(listings, prefs.filters)
                if not filtered_listings:
                    continue

                summary_text = f"📅 <b>Weekly Property Update</b>\n\n"
                summary_text += (
                    f"🎉 Found {len(filtered_listings)} new listings this week!\n\n"
                )

                for listing in filtered_listings[:10]:  # Show first 10
                    summary_text += self._format_listing(listing) + "\n"
                    summary_text += "─" * 30 + "\n\n"

                if len(filtered_listings) > 10:
                    summary_text += f"📊 Showing 10 of {len(filtered_listings)} listings. View more with /list\n"

                await self.bot.send_message(
                    chat_id, summary_text, parse_mode=ParseMode.HTML
                )

        except Exception as e:
            logger.error(f"Error sending weekly notifications: {e}")

    def start(self):
        """Start the bot"""
        logger.info("Starting Telegram bot...")

        # Start scheduler
        self.scheduler.start()

        # Start the bot
        self.application.run_polling()


def main():
    """Main function"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
    )

    # Load bot token from environment
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("🚫 Error: TELEGRAM_BOT_TOKEN environment variable not set!")
        print("💡 Set it in a .env file or environment variables")
        return

    bot = TelegramBot(token)
    bot.start()


if __name__ == "__main__":
    main()
