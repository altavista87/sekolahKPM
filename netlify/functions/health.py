"""
Netlify Function: Health Check Endpoint
Returns system status and health metrics.
"""
import os
import json
import asyncio
import sys
from datetime import datetime
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def handler(event, context):
    """Health check handler."""
    
    # Basic health check
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'environment': os.getenv('NODE_ENV', 'development'),
        'services': {}
    }
    
    # Check database connectivity (if DATABASE_URL is set)
    if os.getenv('DATABASE_URL'):
        health_data['services']['database'] = 'configured'
    else:
        health_data['services']['database'] = 'not_configured'
    
    # Check Redis (if REDIS_URL is set)
    if os.getenv('REDIS_URL'):
        health_data['services']['redis'] = 'configured'
    else:
        health_data['services']['redis'] = 'not_configured'
    
    # Check Telegram Bot Token
    if os.getenv('TELEGRAM_BOT_TOKEN'):
        health_data['services']['telegram'] = 'configured'
    else:
        health_data['services']['telegram'] = 'not_configured'
    
    # Check AI Services
    ai_services = []
    if os.getenv('GEMINI_API_KEY'):
        ai_services.append('gemini')
    if os.getenv('TOGETHER_API_KEY'):
        ai_services.append('together')
    if os.getenv('OPENAI_API_KEY'):
        ai_services.append('openai')
    
    health_data['services']['ai'] = ai_services if ai_services else 'not_configured'
    
    # Determine overall status
    critical_services = ['database', 'telegram']
    missing_critical = [
        svc for svc in critical_services 
        if health_data['services'].get(svc) == 'not_configured'
    ]
    
    if missing_critical:
        health_data['status'] = 'degraded'
        health_data['missing_services'] = missing_critical
        status_code = 503
    else:
        status_code = 200
    
    return {
        'statusCode': status_code,
        'body': json.dumps(health_data),
        'headers': {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
        }
    }
