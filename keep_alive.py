#!/usr/bin/env python3
"""
Keep alive script to prevent Replit from sleeping.
This script makes periodic requests to the health server.
"""

import asyncio
import aiohttp
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class KeepAlive:
    def __init__(self, url="http://localhost:5000/ping", interval=240):
        """
        Initialize keep alive service.
        
        Args:
            url: Health endpoint to ping
            interval: Ping interval in seconds (default: 4 minutes)
        """
        self.url = url
        self.interval = interval
        self.running = False
        
    async def ping_health_server(self):
        """Send a ping to the health server."""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.url) as response:
                    if response.status == 200:
                        logger.info(f"Health ping successful at {datetime.now()}")
                        return True
                    else:
                        logger.warning(f"Health ping failed with status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Health ping error: {e}")
            return False
    
    async def start_keep_alive(self):
        """Start the keep alive loop."""
        self.running = True
        logger.info(f"Starting keep alive service, pinging every {self.interval} seconds")
        
        while self.running:
            try:
                await self.ping_health_server()
                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error(f"Keep alive loop error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def stop_keep_alive(self):
        """Stop the keep alive service."""
        self.running = False
        logger.info("Keep alive service stopped")

# Global keep alive instance
keep_alive_service = KeepAlive()

async def start_keep_alive_background():
    """Start keep alive as a background task."""
    asyncio.create_task(keep_alive_service.start_keep_alive())

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def main():
        keep_alive = KeepAlive()
        await keep_alive.start_keep_alive()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keep alive service stopped by user")
