"""
Graceful Redis Service with Automatic Fallback Support
=====================================================

This module provides intelligent Redis connection management with automatic
fallback to FakeRedis or in-memory storage when Redis is unavailable.
Designed to ensure application functionality across all development environments.

Author: KazRu-STT Pro Development Team
Version: 1.0.0
"""

import os
import json
import time
import logging
import threading
from typing import Optional, Any, Dict, Union
from datetime import timedelta, datetime

import redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

logger = logging.getLogger(__name__)


class RedisBackend:
    """Enumeration of Redis backend types"""
    REDIS = "redis"
    FAKE_REDIS = "fakeredis"
    MEMORY = "memory"


class GracefulRedisService:
    """
    Intelligent Redis service with automatic fallback capabilities.
    
    Provides transparent Redis operations with automatic fallback to:
    1. Configured Redis server
    2. Localhost Redis server
    3. FakeRedis (development)
    4. In-memory storage (emergency fallback)
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis service with fallback strategies.
        
        Args:
            redis_url: Optional Redis connection URL. If not provided,
                      will use REDIS_URL environment variable.
        """
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.redis_client: Optional[redis.Redis] = None
        self.fallback_storage: Dict[str, Any] = {}
        self.expiry_timers: Dict[str, threading.Timer] = {}
        self.backend_type = RedisBackend.MEMORY
        self.last_connection_attempt = None
        self.connection_retry_interval = 30  # seconds
        
        # Initialize connection with fallback strategies
        self._initialize_connection()
        
        # Start background health monitor
        self._start_health_monitor()
    
    def _initialize_connection(self):
        """Initialize Redis connection using fallback strategies."""
        strategies = [
            self._try_configured_redis,
            self._try_localhost_redis,
            self._try_fake_redis,
            self._use_memory_fallback
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                logger.info(f"Attempting Redis connection strategy {i}/{len(strategies)}: {strategy.__name__}")
                if strategy():
                    logger.info(f"Redis connection successful using {strategy.__name__}")
                    return
            except Exception as e:
                logger.warning(f"Redis strategy {strategy.__name__} failed: {str(e)}")
                continue
        
        logger.error("All Redis connection strategies failed")
    
    def _try_configured_redis(self) -> bool:
        """Try connecting to configured Redis URL."""
        try:
            client = redis.from_url(self.redis_url, socket_connect_timeout=3, socket_timeout=3)
            client.ping()
            
            self.redis_client = client
            self.backend_type = RedisBackend.REDIS
            logger.info(f"✅ Connected to Redis at {self.redis_url}")
            return True
            
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.debug(f"Configured Redis connection failed: {str(e)}")
            return False
    
    def _try_localhost_redis(self) -> bool:
        """Try connecting to localhost Redis."""
        try:
            client = redis.Redis(host='localhost', port=6379, socket_connect_timeout=3)
            client.ping()
            
            self.redis_client = client
            self.backend_type = RedisBackend.REDIS
            logger.info("✅ Connected to localhost Redis")
            return True
            
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.debug(f"Localhost Redis connection failed: {str(e)}")
            return False
    
    def _try_fake_redis(self) -> bool:
        """Try using FakeRedis for development."""
        # Check if FakeRedis is explicitly enabled or if in development mode
        use_fake_redis = (
            os.getenv('USE_FAKE_REDIS', 'false').lower() == 'true' or
            os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true'
        )
        
        if not use_fake_redis:
            logger.debug("FakeRedis not enabled - skipping")
            return False
        
        try:
            import fakeredis
            
            self.redis_client = fakeredis.FakeRedis()
            self.backend_type = RedisBackend.FAKE_REDIS
            logger.info("⚠️  Using FakeRedis (development mode)")
            logger.warning("Note: FakeRedis data will not persist between application restarts")
            return True
            
        except ImportError:
            logger.warning("FakeRedis not installed. Install with: pip install fakeredis")
            return False
        except Exception as e:
            logger.warning(f"FakeRedis initialization failed: {str(e)}")
            return False
    
    def _use_memory_fallback(self) -> bool:
        """Use in-memory dictionary as last resort fallback."""
        self.redis_client = None
        self.backend_type = RedisBackend.MEMORY
        logger.warning("❌ No Redis available. Using in-memory storage (data will not persist)")
        return True
    
    def _start_health_monitor(self):
        """Start background thread to monitor Redis health."""
        def health_monitor():
            while True:
                try:
                    time.sleep(30)  # Check every 30 seconds
                    
                    # Only monitor if using real Redis
                    if self.backend_type == RedisBackend.REDIS and self.redis_client:
                        try:
                            self.redis_client.ping()
                        except (ConnectionError, TimeoutError, RedisError):
                            logger.warning("Redis connection lost - attempting reconnection")
                            self._attempt_reconnection()
                    
                except Exception as e:
                    logger.error(f"Health monitor error: {str(e)}")
        
        monitor_thread = threading.Thread(target=health_monitor, daemon=True)
        monitor_thread.start()
    
    def _attempt_reconnection(self):
        """Attempt to reconnect to Redis."""
        now = datetime.now()
        if (self.last_connection_attempt and 
            (now - self.last_connection_attempt).total_seconds() < self.connection_retry_interval):
            return
        
        self.last_connection_attempt = now
        logger.info("Attempting Redis reconnection...")
        
        # Try to reconnect using original strategies
        if self._try_configured_redis() or self._try_localhost_redis():
            logger.info("Redis reconnection successful")
        else:
            logger.warning("Redis reconnection failed - continuing with fallback")
    
    def set(self, key: str, value: Any, ex: Optional[int] = None, **kwargs) -> bool:
        """
        Set key-value with automatic fallback.
        
        Args:
            key: Redis key
            value: Value to store
            ex: Expiration time in seconds
            **kwargs: Additional Redis SET arguments
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.backend_type in [RedisBackend.REDIS, RedisBackend.FAKE_REDIS] and self.redis_client:
                # For Redis/FakeRedis, convert complex objects to JSON
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                
                result = self.redis_client.set(key, value, ex=ex, **kwargs)
                return bool(result)
            else:
                # Memory fallback
                self.fallback_storage[key] = value
                
                # Handle expiration in memory
                if ex:
                    # Cancel existing timer for this key
                    if key in self.expiry_timers:
                        self.expiry_timers[key].cancel()
                    
                    # Set new expiration timer
                    def expire_key():
                        self.fallback_storage.pop(key, None)
                        self.expiry_timers.pop(key, None)
                    
                    timer = threading.Timer(ex, expire_key)
                    timer.daemon = True
                    timer.start()
                    self.expiry_timers[key] = timer
                
                return True
                
        except Exception as e:
            logger.error(f"Redis SET operation failed: {str(e)}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value with automatic fallback.
        
        Args:
            key: Redis key
            
        Returns:
            Value if found, None otherwise
        """
        try:
            if self.backend_type in [RedisBackend.REDIS, RedisBackend.FAKE_REDIS] and self.redis_client:
                value = self.redis_client.get(key)
                if value is None:
                    return None
                
                # Try to decode JSON, fallback to string
                try:
                    return json.loads(value.decode() if isinstance(value, bytes) else value)
                except (json.JSONDecodeError, AttributeError):
                    return value.decode() if isinstance(value, bytes) else value
            else:
                # Memory fallback
                return self.fallback_storage.get(key)
                
        except Exception as e:
            logger.error(f"Redis GET operation failed: {str(e)}")
            return None
    
    def delete(self, *keys) -> int:
        """
        Delete keys with automatic fallback.
        
        Args:
            *keys: Keys to delete
            
        Returns:
            Number of keys deleted
        """
        try:
            if self.backend_type in [RedisBackend.REDIS, RedisBackend.FAKE_REDIS] and self.redis_client:
                return self.redis_client.delete(*keys)
            else:
                # Memory fallback
                deleted_count = 0
                for key in keys:
                    if key in self.fallback_storage:
                        del self.fallback_storage[key]
                        deleted_count += 1
                    
                    # Cancel expiration timer if exists
                    if key in self.expiry_timers:
                        self.expiry_timers[key].cancel()
                        del self.expiry_timers[key]
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Redis DELETE operation failed: {str(e)}")
            return 0
    
    def exists(self, *keys) -> int:
        """
        Check if keys exist with automatic fallback.
        
        Args:
            *keys: Keys to check
            
        Returns:
            Number of existing keys
        """
        try:
            if self.backend_type in [RedisBackend.REDIS, RedisBackend.FAKE_REDIS] and self.redis_client:
                return self.redis_client.exists(*keys)
            else:
                # Memory fallback
                return sum(1 for key in keys if key in self.fallback_storage)
                
        except Exception as e:
            logger.error(f"Redis EXISTS operation failed: {str(e)}")
            return 0
    
    def ping(self) -> bool:
        """
        Test Redis connection with automatic fallback.
        
        Returns:
            True if connection is working, False otherwise
        """
        try:
            if self.backend_type in [RedisBackend.REDIS, RedisBackend.FAKE_REDIS] and self.redis_client:
                self.redis_client.ping()
                return True
            else:
                # Memory fallback is always "available"
                return True
                
        except Exception as e:
            logger.error(f"Redis PING failed: {str(e)}")
            return False
    
    def health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status.
        
        Returns:
            Dictionary containing health status information
        """
        status = {
            'backend_type': self.backend_type,
            'timestamp': datetime.utcnow().isoformat(),
            'connection_url': self.redis_url if self.backend_type == RedisBackend.REDIS else None
        }
        
        try:
            if self.backend_type == RedisBackend.REDIS and self.redis_client:
                self.redis_client.ping()
                info = self.redis_client.info()
                status.update({
                    'status': 'healthy',
                    'redis_version': info.get('redis_version', 'unknown'),
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory_human': info.get('used_memory_human', 'unknown'),
                    'uptime_in_seconds': info.get('uptime_in_seconds', 0)
                })
            elif self.backend_type == RedisBackend.FAKE_REDIS:
                status.update({
                    'status': 'development',
                    'message': 'Using FakeRedis - suitable for development only',
                    'persistence': False
                })
            else:
                status.update({
                    'status': 'degraded',
                    'message': 'Using in-memory storage - data will not persist',
                    'persistence': False,
                    'stored_keys': len(self.fallback_storage)
                })
                
        except Exception as e:
            status.update({
                'status': 'unhealthy',
                'error': str(e),
                'message': f'Backend {self.backend_type} connection failed'
            })
        
        return status
    
    def get_client(self) -> Optional[redis.Redis]:
        """
        Get the underlying Redis client.
        
        Warning: This should only be used for advanced operations that
        can't be abstracted by this service. Prefer using the service methods.
        
        Returns:
            Redis client if available, None for memory fallback
        """
        if self.backend_type in [RedisBackend.REDIS, RedisBackend.FAKE_REDIS]:
            return self.redis_client
        return None
    
    def is_redis_available(self) -> bool:
        """Check if real Redis (not fallback) is available."""
        return self.backend_type == RedisBackend.REDIS
    
    def is_persistent(self) -> bool:
        """Check if current backend provides data persistence."""
        return self.backend_type == RedisBackend.REDIS
    
    def cleanup(self):
        """Clean up resources (timers, connections)."""
        # Cancel all expiration timers
        for timer in self.expiry_timers.values():
            timer.cancel()
        self.expiry_timers.clear()
        
        # Close Redis connection if exists
        if self.redis_client and hasattr(self.redis_client, 'close'):
            try:
                self.redis_client.close()
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {str(e)}")


# Global Redis service instance
_redis_service: Optional[GracefulRedisService] = None


def get_redis_service(redis_url: Optional[str] = None) -> GracefulRedisService:
    """
    Get the global Redis service instance.
    
    Args:
        redis_url: Optional Redis URL (only used for first initialization)
        
    Returns:
        GracefulRedisService instance
    """
    global _redis_service
    
    if _redis_service is None:
        _redis_service = GracefulRedisService(redis_url)
    
    return _redis_service


def cleanup_redis_service():
    """Clean up the global Redis service instance."""
    global _redis_service
    
    if _redis_service:
        _redis_service.cleanup()
        _redis_service = None