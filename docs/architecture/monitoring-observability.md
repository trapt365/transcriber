# Monitoring & Observability

## Health Checks

```python
@app.route('/api/v1/health')
def health_check():
    """Comprehensive health check endpoint"""
    status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': app.config.get('VERSION', '1.0.0'),
        'checks': {}
    }
    
    # Database connectivity
    try:
        db.session.execute('SELECT 1')
        status['checks']['database'] = 'healthy'
    except Exception as e:
        status['checks']['database'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    # Redis connectivity
    try:
        redis_client.ping()
        status['checks']['redis'] = 'healthy'
    except Exception as e:
        status['checks']['redis'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    # Yandex API connectivity
    try:
        # Quick API test (cached for 5 minutes)
        test_result = cache.get('yandex_api_test')
        if test_result is None:
            # Perform actual test
            yandex_client = YandexSpeechKitClient()
            test_result = yandex_client.test_connection()
            cache.set('yandex_api_test', test_result, timeout=300)
        
        status['checks']['yandex_api'] = 'healthy' if test_result else 'unhealthy'
    except Exception as e:
        status['checks']['yandex_api'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    # Worker status
    try:
        inspect = celery.control.inspect()
        active_workers = inspect.active()
        status['checks']['workers'] = f"active: {len(active_workers) if active_workers else 0}"
    except Exception as e:
        status['checks']['workers'] = f'unhealthy: {str(e)}'
        status['status'] = 'degraded'
    
    status_code = 200 if status['status'] == 'healthy' else 503
    return jsonify(status), status_code
```

## Metrics Collection

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
