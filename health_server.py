#!/usr/bin/env python3
"""
Health check server for UptimeRobot monitoring.
This keeps the Replit instance awake by providing HTTP endpoints to ping.
"""

import asyncio
import logging
from datetime import datetime
from aiohttp import web
import json

logger = logging.getLogger(__name__)

class HealthServer:
    def __init__(self, port=5000):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """Set up HTTP routes for health checks."""
        self.app.router.add_get('/', self.health_check)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.status_check)
        self.app.router.add_get('/ping', self.ping)
        
    async def health_check(self, request):
        """Basic health check endpoint."""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'Apoyo Integral Bot',
            'message': 'Bot is running successfully'
        })
    
    async def status_check(self, request):
        """Detailed status check with bot information."""
        return web.json_response({
            'status': 'active',
            'timestamp': datetime.now().isoformat(),
            'service': 'Telegram Bot - Apoyo Integral',
            'version': '1.0',
            'uptime': 'monitoring active',
            'endpoints': {
                'health': '/health',
                'status': '/status', 
                'ping': '/ping'
            }
        })
    
    async def ping(self, request):
        """Ping endpoint optimizado para Replit 2025"""
        return web.Response(
            text=f"pong - {datetime.now().isoformat()}",
            content_type='text/plain',
            headers={
                "Access-Control-Allow-Origin": "*",
                "X-Replit-Proxy": "true"  # ¡ESTA LÍNEA ES CLAVE!
            }
        )

    
    async def start_server(self):
        """Start the health check server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"Health server started on port {self.port}")
        logger.info(f"Available endpoints:")
        logger.info(f"  - http://0.0.0.0:{self.port}/")
        logger.info(f"  - http://0.0.0.0:{self.port}/health")
        logger.info(f"  - http://0.0.0.0:{self.port}/status")
        logger.info(f"  - http://0.0.0.0:{self.port}/ping")
        
        return runner

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def main():
        health_server = HealthServer()
        runner = await health_server.start_server()
        
        try:
            # Keep server running
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour
        except KeyboardInterrupt:
            logger.info("Shutting down health server...")
        finally:
            await runner.cleanup()
    
    asyncio.run(main())
