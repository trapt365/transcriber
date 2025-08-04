"""Health check service for monitoring system components."""

import os
import redis
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from backend.extensions import db
from backend.app.utils.exceptions import DatabaseError


class HealthService:
    """Service for checking health of system components."""
    
    def __init__(self, redis_url: Optional[str] = None, upload_folder: Optional[str] = None):
        """
        Initialize health service.
        
        Args:
            redis_url: Redis connection URL
            upload_folder: Upload folder path for filesystem checks
        """
        self.redis_url = redis_url
        self.upload_folder = Path(upload_folder) if upload_folder else None
    
    def check_database(self) -> Dict[str, Any]:
        """
        Check database connectivity and basic operations.
        
        Returns:
            Database health status dictionary
        """
        try:
            # Test database connection
            result = db.engine.execute(db.text("SELECT 1")).scalar()
            
            if result != 1:
                return {
                    "status": "unhealthy",
                    "error": "Database query returned unexpected result",
                    "checked_at": datetime.utcnow().isoformat()
                }
            
            # Check if tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            expected_tables = ['jobs', 'job_results', 'speakers', 'transcript_segments', 'usage_stats']
            missing_tables = [table for table in expected_tables if table not in tables]
            
            health_info = {
                "status": "healthy",
                "connection": "ok",
                "tables_count": len(tables),
                "expected_tables": len(expected_tables),
                "missing_tables": missing_tables,
                "checked_at": datetime.utcnow().isoformat()
            }
            
            if missing_tables:
                health_info["status"] = "degraded"
                health_info["warning"] = f"Missing tables: {', '.join(missing_tables)}"
            
            return health_info
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed",
                "checked_at": datetime.utcnow().isoformat()
            }
    
    def check_redis(self) -> Dict[str, Any]:
        """
        Check Redis connectivity and operations.
        
        Returns:
            Redis health status dictionary
        """
        if not self.redis_url:
            return {
                "status": "not_configured",
                "message": "Redis URL not provided",
                "checked_at": datetime.utcnow().isoformat()
            }
        
        try:
            redis_client = redis.from_url(self.redis_url)
            
            # Test basic operations
            test_key = "health_check_test"
            test_value = "test_value"
            
            # Set and get test
            redis_client.set(test_key, test_value, ex=10)  # Expire in 10 seconds
            retrieved_value = redis_client.get(test_key)
            
            if retrieved_value.decode('utf-8') != test_value:
                return {
                    "status": "unhealthy",
                    "error": "Redis set/get test failed",
                    "checked_at": datetime.utcnow().isoformat()
                }
            
            # Clean up test key
            redis_client.delete(test_key)
            
            # Get Redis info
            info = redis_client.info()
            
            return {
                "status": "healthy",
                "connection": "ok",
                "version": info.get('redis_version'),
                "used_memory": info.get('used_memory_human'),
                "connected_clients": info.get('connected_clients'),
                "checked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed",
                "checked_at": datetime.utcnow().isoformat()
            }
    
    def check_filesystem(self) -> Dict[str, Any]:
        """
        Check filesystem health and permissions.
        
        Returns:
            Filesystem health status dictionary
        """
        checks = {
            "upload_folder": self._check_upload_folder(),
            "temp_space": self._check_temp_space(),
            "disk_space": self._check_disk_space()
        }
        
        # Determine overall status
        statuses = [check["status"] for check in checks.values()]
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "checks": checks,
            "checked_at": datetime.utcnow().isoformat()
        }
    
    def _check_upload_folder(self) -> Dict[str, Any]:
        """Check upload folder accessibility."""
        if not self.upload_folder:
            return {
                "status": "not_configured",
                "message": "Upload folder not configured"
            }
        
        try:
            # Check if folder exists
            if not self.upload_folder.exists():
                return {
                    "status": "unhealthy",
                    "error": "Upload folder does not exist",
                    "path": str(self.upload_folder)
                }
            
            # Check permissions
            if not os.access(self.upload_folder, os.R_OK | os.W_OK):
                return {
                    "status": "unhealthy",
                    "error": "Insufficient permissions for upload folder",
                    "path": str(self.upload_folder)
                }
            
            # Test write access
            test_file = self.upload_folder / ".health_check_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "error": f"Cannot write to upload folder: {str(e)}",
                    "path": str(self.upload_folder)
                }
            
            # Get folder stats
            file_count = len(list(self.upload_folder.iterdir()))
            
            return {
                "status": "healthy",
                "path": str(self.upload_folder),
                "file_count": file_count,
                "permissions": "ok"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "path": str(self.upload_folder) if self.upload_folder else None
            }
    
    def _check_temp_space(self) -> Dict[str, Any]:
        """Check temporary directory space."""
        try:
            temp_dir = Path("/tmp")
            stat = os.statvfs(temp_dir)
            
            # Calculate available space
            available_bytes = stat.f_bavail * stat.f_frsize
            available_mb = available_bytes / (1024 * 1024)
            
            # Warn if less than 1GB available
            if available_mb < 1024:
                status = "degraded" if available_mb > 512 else "unhealthy"
                warning = f"Low temp space: {available_mb:.1f}MB available"
            else:
                status = "healthy"
                warning = None
            
            result = {
                "status": status,
                "available_mb": round(available_mb, 1),
                "path": str(temp_dir)
            }
            
            if warning:
                result["warning"] = warning
            
            return result
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """Check main disk space."""
        try:
            # Check current directory disk space
            stat = os.statvfs(".")
            
            total_bytes = stat.f_blocks * stat.f_frsize
            available_bytes = stat.f_bavail * stat.f_frsize
            used_bytes = total_bytes - available_bytes
            
            total_gb = total_bytes / (1024 ** 3)
            available_gb = available_bytes / (1024 ** 3)
            used_percentage = (used_bytes / total_bytes) * 100
            
            # Determine status based on usage
            if used_percentage > 90:
                status = "unhealthy"
                warning = f"Disk usage critical: {used_percentage:.1f}%"
            elif used_percentage > 80:
                status = "degraded"
                warning = f"Disk usage high: {used_percentage:.1f}%"
            else:
                status = "healthy"
                warning = None
            
            result = {
                "status": status,
                "total_gb": round(total_gb, 1),
                "available_gb": round(available_gb, 1),
                "used_percentage": round(used_percentage, 1)
            }
            
            if warning:
                result["warning"] = warning
            
            return result
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_external_services(self) -> Dict[str, Any]:
        """
        Check external service connectivity.
        
        Returns:
            External services health status dictionary
        """
        # TODO: Add checks for Yandex SpeechKit API when implemented
        return {
            "status": "not_implemented",
            "message": "External service checks will be implemented in future stories",
            "checked_at": datetime.utcnow().isoformat()
        }
    
    def get_comprehensive_health(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of all system components.
        
        Returns:
            Complete system health status dictionary
        """
        health_checks = {
            "database": self.check_database(),
            "redis": self.check_redis(),
            "filesystem": self.check_filesystem(),
            "external_services": self.check_external_services()
        }
        
        # Determine overall system status
        component_statuses = []
        for component, status in health_checks.items():
            if component == "external_services" and status["status"] == "not_implemented":
                continue  # Skip not implemented checks
            if component == "redis" and status["status"] == "not_configured":
                continue  # Skip not configured services
            component_statuses.append(status["status"])
        
        if "unhealthy" in component_statuses:
            overall_status = "unhealthy"
        elif "degraded" in component_statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "service": "transcriber",
            "version": "0.1.0",
            "checked_at": datetime.utcnow().isoformat(),
            "components": health_checks,
            "summary": {
                "healthy_components": len([s for s in component_statuses if s == "healthy"]),
                "degraded_components": len([s for s in component_statuses if s == "degraded"]),
                "unhealthy_components": len([s for s in component_statuses if s == "unhealthy"]),
                "total_components": len(component_statuses)
            }
        }