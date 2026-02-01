# KV.ee Owner Direct Listings Telegram Bot

A Python-based Telegram bot that notifies users about new owner direct property listings on KV.ee, Estonia's leading real estate portal.

## Features

- 📱 **Telegram Integration**: Full-featured Telegram bot with commands and notifications
- 🏠 **Owner Direct Listings**: Filters only private owner listings (no real estate agencies)
- ⏰ **Automated Notifications**: Immediate, daily, or weekly notifications
- 🔍 **Advanced Filtering**: Filter by price, area, rooms, location, and property type
- 📊 **Real-time Updates**: Checks for new listings every 15 minutes
- 📰 **Rich Messages**: Well-formatted listing information with images and details
- 💾 **Persistent Storage**: Remembers seen listings and user preferences

## Installation

### Prerequisites

- Python 3.8 or higher
- Telegram bot token (get from @BotFather)
- Basic understanding of environment variables

### Setup Steps

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd kv-ee-telegram-bot
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

5. **Set up your Telegram bot token**:
   - Talk to @BotFather on Telegram
   - Create a new bot and get the token
   - Add the token to your .env file

## Configuration

Edit the `.env` file with your preferences:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
LOG_LEVEL=INFO
NOTIFICATION_INTERVAL=15
DAILY_NOTIFICATION_HOUR=9
WEEKLY_NOTIFICATION_DAY=mon
WEEKLY_NOTIFICATION_HOUR=9

# KV.ee search parameters
DEFAULT_COUNTY=9          # 9 = Tallinn
DEFAULT_DEAL_TYPE=sale    # sale or rent
DEFAULT_PRICE_MIN=50000
DEFAULT_PRICE_MAX=500000
DEFAULT_AREA_MIN=20.0
DEFAULT_AREA_MAX=150.0
DEFAULT_ROOMS_MIN=1
DEFAULT_ROOMS_MAX=5

# Database settings
DATABASE_PATH=users.json
SEEN_LISTINGS_PATH=seen_listings.json

# Debug settings
DEBUG_MODE=false
TEST_MODE=false
```

## Usage

### Start the Bot

```bash
python telegram_bot.py
```

### Telegram Commands

- `/start` - Start the bot and get a welcome message
- `/help` - Show all available commands
- `/subscribe` - Subscribe to notifications
- `/unsubscribe` - Unsubscribe from notifications
- `/settings` - Configure your notification preferences
- `/list` - Show current listings
- `/notify` - Check for new listings immediately
- `/stop` - Stop the bot

### Setting Filters

After starting the bot, you can set custom filters:

- `/set_price_min <amount>` - Minimum price
- `/set_price_max <amount>` - Maximum price
- `/set_area_min <area>` - Minimum area (m²)
- `/set_area_max <area>` - Maximum area (m²)
- `/set_rooms_min <rooms>` - Minimum rooms
- `/set_rooms_max <rooms>` - Maximum rooms
- `/set_county <county_id>` - Set county (9=Talinn)

## How It Works

1. **Scraping**: The bot uses `kv_scraper.py` to scrape KV.ee for owner direct listings
2. **Filtering**: Listings are filtered based on user preferences and default settings
3. **Notification**: The bot sends notifications via Telegram based on user settings
4. **Persistence**: User preferences and seen listings are stored in JSON files
5. **Scheduling**: Automated checks run every 15 minutes with daily/weekly summaries

## KV.ee County IDs

- 1 = Harjumaa
- 2 = Hiiumaa
- 3 = Ida-Virumaa
- 4 = Järvamaa
- 5 = Jõgevamaa
- 6 = Läänemaa
- 7 = Lääne-Virumaa
- 8 = Pärnumaa
- 9 = Põlvamaa
- 10 = Raplamaa
- 11 = Saaremaa
- 12 = Tartumaa
- 13 = Valgamaa
- 14 = Viljandimaa
- 15 = Võrumaa

## Deployment

### Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "telegram_bot.py"]
```

### Systemd Service

Create `/etc/systemd/system/kv-ee-bot.service`:

```ini
[Unit]
Description=KV.ee Telegram Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/kv-ee-telegram-bot
Environment=TELEGRAM_BOT_TOKEN=your_token
ExecStart=/path/to/venv/bin/python telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

- This bot scrapes KV.ee website and should respect their terms of service
- Use responsibly and consider the load on KV.ee servers
- The bot is provided as-is without warranty

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs (bot.log)
3. Create an issue on GitHub

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check if the bot is running and the token is correct
2. **No listings found**: Verify KV.ee website structure hasn't changed
3. **Rate limiting**: Add delays between requests if needed
4. **Memory issues**: Monitor seen listings file size

### Logs

Logs are stored in `bot.log` and include:
- Scraping activities
- Notification events
- Errors and warnings
- User interactions

### Debug Mode

Enable debug mode in `.env`:
```env
DEBUG_MODE=true
```

This will show more detailed logging information.