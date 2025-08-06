# #!/usr/bin/env python3
# """
# Simplified Monitoring Routes - Streamlined monitoring API endpoints
# Reduced from 12 endpoints to 6 essential ones, maintaining frontend compatibility
# """

import time
from typing import Dict, Any, Optional
from flask import Blueprint, jsonify, request


def create_monitoring_routes(gateway_system, logger):
    """Create simplified monitoring routes blueprint"""

    monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/monitoring')

    # ========================================================================
    # Core Endpoints (Frontend Compatible)
    # ========================================================================

    @monitoring_bp.route('/metrics/json', methods=['GET'])
    def get_metrics_json():
        """GET /monitoring/metrics/json - Get all metrics in JSON format"""
        try:
            if gateway_system.metrics_collector:
                metrics = gateway_system.metrics_collector.get_all_metrics()
                logger.debug("Retrieved JSON metrics successfully")
                return jsonify({
                    "success": True,
                    "timestamp": time.time(),
                    **metrics
                })
            else:
                return jsonify({
                    "success": False,
                    "timestamp": time.time(),
                    "counters": {},
                    "gauges": {},
                    "histograms": {},
                    "custom": {},
                    "error": "Monitoring not enabled"
                })
        except Exception as e:
            logger.error(f"Error getting JSON metrics: {e}")
            return jsonify({
                "success": False,
                "timestamp": time.time(),
                "error": str(e)
            }), 500

    @monitoring_bp.route('/health', methods=['GET'])
    def get_health_status():
        """GET /monitoring/health - Get health status (supports ?detailed=true)"""
        try:
            detailed = request.args.get('detailed', 'false').lower() == 'true'
            
            health_checks = {}
            overall_status = "healthy"
            healthy_count = 0
            unhealthy_count = 0
            unknown_count = 0

            # Core system checks
            if gateway_system.running:
                health_checks["gateway_system"] = {
                    "status": "healthy",
                    "message": "Gateway system is running",
                    "last_check": time.time()
                }
                if detailed:
                    health_checks["gateway_system"].update({
                        "uptime": time.time() - gateway_system.start_time if gateway_system.start_time else 0,
                        "running": True
                    })
                healthy_count += 1
            else:
                health_checks["gateway_system"] = {
                    "status": "unhealthy",
                    "message": "Gateway system is not running",
                    "last_check": time.time()
                }
                unhealthy_count += 1

            # MQTT connection check
            if gateway_system.mqtt_connection.is_connected():
                health_checks["mqtt_connection"] = {
                    "status": "healthy",
                    "message": "MQTT connection is active",
                    "last_check": time.time()
                }
                if detailed:
                    health_checks["mqtt_connection"]["broker"] = gateway_system.mqtt_connection.broker
                healthy_count += 1
            else:
                health_checks["mqtt_connection"] = {
                    "status": "unhealthy",
                    "message": "MQTT connection is not active",
                    "last_check": time.time()
                }
                unhealthy_count += 1

            # Serial connection check
            if gateway_system.serial_connection.is_connected():
                health_checks["serial_connection"] = {
                    "status": "healthy",
                    "message": "Serial connection is active",
                    "last_check": time.time()
                }
                if detailed:
                    health_checks["serial_connection"]["port"] = gateway_system.serial_connection.port
                healthy_count += 1
            else:
                health_checks["serial_connection"] = {
                    "status": "unhealthy",
                    "message": "Serial connection is not active",
                    "last_check": time.time()
                }
                unhealthy_count += 1

            # Data repository check
            try:
                devices = gateway_system.packet_processor.device_repository.get_all_devices()
                device_count = len(devices)
                health_checks["data_repository"] = {
                    "status": "healthy",
                    "message": f"Data repository active with {device_count} devices",
                    "last_check": time.time(),
                    "device_count": device_count
                }
                if detailed:
                    health_checks["data_repository"]["repository_type"] = type(gateway_system.packet_processor.device_repository).__name__
                healthy_count += 1
            except Exception as e:
                health_checks["data_repository"] = {
                    "status": "unhealthy",
                    "message": f"Data repository error: {str(e)}",
                    "last_check": time.time()
                }
                unhealthy_count += 1

            # Packet processing check
            try:
                stats = gateway_system.get_statistics()
                packets_processed = stats.get('total_packets_processed', 0)
                health_checks["packet_processing"] = {
                    "status": "healthy",
                    "message": f"Packet processing active ({packets_processed} packets processed)",
                    "last_check": time.time(),
                    "packets_processed": packets_processed
                }
                if detailed:
                    health_checks["packet_processing"].update({
                        "unknown_devices": stats.get("unknown_devices_detected", 0),
                        "registered_devices": stats.get("total_devices", 0)
                    })
                healthy_count += 1
            except Exception as e:
                health_checks["packet_processing"] = {
                    "status": "unhealthy",
                    "message": f"Packet processing error: {str(e)}",
                    "last_check": time.time()
                }
                unhealthy_count += 1

            # Monitoring system check
            if gateway_system.metrics_collector:
                health_checks["monitoring_system"] = {
                    "status": "healthy",
                    "message": "Monitoring system is active",
                    "last_check": time.time()
                }
                if detailed:
                    try:
                        metrics_summary = gateway_system.metrics_collector.get_summary()
                        health_checks["monitoring_system"].update({
                            "uptime": metrics_summary.get('collection_uptime', 0),
                            "metrics_count": (
                                metrics_summary.get('total_counters', 0) +
                                metrics_summary.get('total_gauges', 0) +
                                metrics_summary.get('total_histograms', 0)
                            )
                        })
                    except Exception:
                        pass
                healthy_count += 1
            else:
                health_checks["monitoring_system"] = {
                    "status": "disabled",
                    "message": "Monitoring system not enabled",
                    "last_check": time.time()
                }
                unknown_count += 1

            # Performance monitoring (detailed only)
            if detailed and gateway_system.performance_monitor:
                try:
                    perf_data = gateway_system.performance_monitor.get_performance_summary()
                    cpu_percent = perf_data.get('system', {}).get('cpu_percent', 0)
                    
                    cpu_status = "healthy"
                    if cpu_percent > 90:
                        cpu_status = "critical"
                        overall_status = "critical"
                    elif cpu_percent > 80:
                        cpu_status = "warning"
                        if overall_status == "healthy":
                            overall_status = "warning"

                    health_checks["performance"] = {
                        "status": cpu_status,
                        "message": f"System performance: CPU {cpu_percent:.1f}%",
                        "last_check": time.time(),
                        "cpu_percent": cpu_percent,
                        "memory_percent": perf_data.get('system', {}).get('memory_percent', 0)
                    }
                    
                    if cpu_status == "healthy":
                        healthy_count += 1
                    else:
                        unhealthy_count += 1
                except Exception:
                    unknown_count += 1

            # Determine overall status
            if unhealthy_count > 0:
                overall_status = "unhealthy"
            elif unknown_count > healthy_count:
                overall_status = "degraded"

            # Calculate uptime
            uptime = time.time() - gateway_system.start_time if gateway_system.start_time else 0

            result = {
                "success": True,
                "status": overall_status,
                "timestamp": time.time(),
                "uptime": uptime,
                "checks": health_checks,
                "summary": {
                    "total_checks": healthy_count + unhealthy_count + unknown_count,
                    "healthy_checks": healthy_count,
                    "unhealthy_checks": unhealthy_count,
                    "unknown_checks": unknown_count
                }
            }

            # Add detailed info if requested
            if detailed:
                result["diagnostics"] = {
                    "gateway_type": "real" if hasattr(gateway_system, 'process_packets_from_serial') else "mock",
                    "monitoring_enabled": gateway_system.metrics_collector is not None,
                    "performance_monitoring": gateway_system.performance_monitor is not None,
                    "components": {
                        "metrics_collector": {"present": gateway_system.metrics_collector is not None},
                        "performance_monitor": {"present": gateway_system.performance_monitor is not None},
                        "health_monitor": {"present": gateway_system.health_monitor is not None}
                    }
                }

            logger.debug(f"Health status: {overall_status} ({healthy_count} healthy, {unhealthy_count} unhealthy, {unknown_count} unknown)")
            return jsonify(result)

        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return jsonify({
                "success": False,
                "status": "error",
                "timestamp": time.time(),
                "error": str(e)
            }), 500

    @monitoring_bp.route('/performance', methods=['GET'])
    def get_performance_data():
        """GET /monitoring/performance - Get system performance data"""
        try:
            if gateway_system.performance_monitor:
                performance = gateway_system.performance_monitor.get_performance_summary()
                logger.debug("Retrieved performance data successfully")
                return jsonify({
                    "success": True,
                    "timestamp": time.time(),
                    **performance
                })
            else:
                logger.warning("Performance monitor not available")
                return jsonify({
                    "success": False,
                    "timestamp": time.time(),
                    "error": "Performance monitoring not enabled"
                })
        except Exception as e:
            logger.error(f"Error getting performance data: {e}")
            return jsonify({
                "success": False,
                "timestamp": time.time(),
                "error": str(e)
            }), 500

    @monitoring_bp.route('/alerts', methods=['GET'])
    def get_active_alerts():
        """GET /monitoring/alerts - Get active system alerts"""
        try:
            alerts = []

            # Check for health-based alerts
            if gateway_system.get_health_status:
                health_status = gateway_system.get_health_status()
                unhealthy_checks = health_status.get("summary", {}).get("unhealthy_checks", 0)
                
                if unhealthy_checks > 0:
                    alerts.append({
                        "severity": "warning",
                        "component": "health_monitor",
                        "message": f"{unhealthy_checks} health checks are failing",
                        "timestamp": time.time()
                    })

            # Check for performance alerts
            if gateway_system.performance_monitor:
                try:
                    perf_data = gateway_system.performance_monitor.get_performance_summary()
                    cpu_percent = perf_data.get('system', {}).get('cpu_percent', 0)
                    memory_percent = perf_data.get('system', {}).get('memory_percent', 0)
                    
                    if cpu_percent > 90:
                        alerts.append({
                            "severity": "critical",
                            "component": "performance",
                            "message": f"High CPU usage: {cpu_percent:.1f}%",
                            "timestamp": time.time()
                        })
                    elif cpu_percent > 75:
                        alerts.append({
                            "severity": "warning",
                            "component": "performance", 
                            "message": f"Elevated CPU usage: {cpu_percent:.1f}%",
                            "timestamp": time.time()
                        })
                    
                    if memory_percent > 90:
                        alerts.append({
                            "severity": "critical",
                            "component": "performance",
                            "message": f"High memory usage: {memory_percent:.1f}%",
                            "timestamp": time.time()
                        })
                except Exception:
                    pass  # Continue if performance check fails

            return jsonify({
                "success": True,
                "timestamp": time.time(),
                "alerts": alerts,
                "alert_count": len(alerts)
            })

        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return jsonify({
                "success": False,
                "timestamp": time.time(),
                "error": str(e)
            }), 500

    @monitoring_bp.route('/metrics/reset', methods=['POST'])
    def reset_metrics():
        """POST /monitoring/metrics/reset - Reset all counter metrics"""
        try:
            if gateway_system.metrics_collector:
                gateway_system.metrics_collector.reset_all_counters()
                logger.info("All metrics counters reset successfully")
                return jsonify({
                    "success": True,
                    "message": "All counters reset",
                    "timestamp": time.time()
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Monitoring not enabled"
                }), 400
        except Exception as e:
            logger.error(f"Error resetting metrics: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # ========================================================================
    # Legacy Compatibility Endpoints (Redirect to main endpoints)
    # ========================================================================

    @monitoring_bp.route('/metrics', methods=['GET'])
    def get_metrics_prometheus():
        """GET /monitoring/metrics - Get metrics in Prometheus format"""
        try:
            if gateway_system.metrics_collector:
                prometheus_data = gateway_system.metrics_collector.get_prometheus_format()
                logger.debug("Retrieved Prometheus metrics successfully")
                return prometheus_data, 200, {'Content-Type': 'text/plain; charset=utf-8'}
            else:
                return "# Monitoring not enabled\n", 200, {'Content-Type': 'text/plain; charset=utf-8'}
        except Exception as e:
            logger.error(f"Error getting Prometheus metrics: {e}")
            return f"# Error: {e}\n", 500, {'Content-Type': 'text/plain; charset=utf-8'}

    @monitoring_bp.route('/health/detailed', methods=['GET'])
    def get_detailed_health():
        """GET /monitoring/health/detailed - Redirect to main health endpoint with detailed=true"""
        return get_health_status()  # Uses ?detailed=true automatically when called from this endpoint

    logger.info("✅ Simplified monitoring routes created (6 endpoints)")
    return monitoring_bp