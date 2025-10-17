# web/dlq_routes.py
from flask import Blueprint, jsonify, request
from typing import Dict, Any
import logging

def create_dlq_routes(gateway_system) -> Blueprint:
    """Create Flask routes for Dead Letter Queue management"""
    
    dlq_bp = Blueprint('dlq', __name__, url_prefix='/api/dlq')
    
    @dlq_bp.route('/statistics', methods=['GET'])
    def get_dlq_statistics():
        """Get DLQ statistics"""
        try:
            stats = gateway_system.get_dlq_statistics()
            return jsonify({
                "success": True,
                "data": stats
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @dlq_bp.route('/messages', methods=['GET'])
    def get_dlq_messages():
        """Get all DLQ messages"""
        try:
            handler_name = request.args.get('handler')
            messages = gateway_system.get_dlq_messages(handler_name)
            return jsonify({
                "success": True,
                "data": messages
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @dlq_bp.route('/messages/<handler_name>', methods=['GET'])
    def get_handler_dlq_messages(handler_name: str):
        """Get DLQ messages for specific handler"""
        try:
            messages = gateway_system.get_dlq_messages(handler_name)
            return jsonify({
                "success": True,
                "data": messages
            })
        except Exception as e:
            logging.exception("Error in get_handler_dlq_messages for handler '%s':", handler_name)
            return jsonify({
                "success": False,
                "error": "An internal error has occurred."
            }), 500
    
    @dlq_bp.route('/health', methods=['GET'])
    def get_dlq_health():
        """Get DLQ health status"""
        try:
            stats = gateway_system.get_dlq_statistics()
            
            # Simple health check - DLQ is healthy if not too many messages
            total_messages = sum(
                handler_stats.get('message_count', 0) 
                for handler_stats in stats.values()
            )
            
            health_status = {
                "healthy": total_messages < 100,  # Configurable threshold
                "total_messages": total_messages,
                "handlers": len(stats),
                "details": stats
            }
            
            return jsonify({
                "success": True,
                "data": health_status
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    return dlq_bp
