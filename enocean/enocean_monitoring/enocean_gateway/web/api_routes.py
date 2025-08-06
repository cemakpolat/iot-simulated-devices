# #!/usr/bin/env python3
# """
# Simplified API Routes - Streamlined REST API endpoints
# Reduced redundancy while maintaining frontend compatibility
# """

import time
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify
import json


def create_api_routes(device_manager, enocean_system, synchronizer, logger):
    """Create simplified API routes blueprint"""

    api_bp = Blueprint('api', __name__, url_prefix='/api')

    # ========================================================================
    # Common Helper Functions
    # ========================================================================

    def handle_api_error(operation: str, error: Exception, status_code: int = 500):
        """Centralized error handling"""
        logger.error(f"Error in {operation}: {error}")
        return jsonify({"success": False, "error": str(error)}), status_code

    def validate_device_data(data: dict, required_fields: List[str]) -> tuple:
        """Validate device data and return (is_valid, error_message)"""
        if not data:
            return False, "No JSON data provided"
        
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        device_id = data['device_id']
        if not _validate_device_id_format(device_id):
            return False, "Invalid device ID format. Expected: XX:XX:XX:XX"
        
        return True, None

    def sync_and_log(operation: str, device_id: str = None):
        """Common sync operation with logging"""
        if device_id:
            synchronizer.on_device_registered(device_id)
        else:
            synchronizer.force_sync()
        
        logger.info(f"{operation} completed successfully")

    # ========================================================================
    # Device Management Endpoints - Simplified
    # ========================================================================

    @api_bp.route('/devices', methods=['GET'])
    def list_devices():
        """GET /api/devices - List all registered devices"""
        try:
            devices = device_manager.list_devices()
            return jsonify({
                "success": True,
                "devices": devices,
                "count": len(devices),
                "last_sync": synchronizer.last_sync_time
            })
        except Exception as e:
            return handle_api_error("list_devices", e)

    @api_bp.route('/devices', methods=['POST'])
    def add_device():
        """POST /api/devices - Add a new device"""
        try:
            data = request.json
            is_valid, error_message = validate_device_data(data, ['device_id', 'name', 'eep_profile'])
            if not is_valid:
                return jsonify({"success": False, "error": error_message}), 400

            device_id = data['device_id']
            
            # Check if device already exists
            if device_manager.device_exists(device_id):
                return jsonify({
                    "success": False,
                    "error": f"Device {device_id} already exists"
                }), 409

            # Register device
            success = device_manager.register_device(
                device_id=device_id,
                name=data['name'],
                eep_profile=data['eep_profile'],
                device_type=data.get('device_type', 'unknown'),
                location=data.get('location', ''),
                manufacturer=data.get('manufacturer', 'Unknown'),
                model=data.get('model', 'Unknown'),
                description=data.get('description', '')
            )

            if success:
                sync_and_log(f"Device {device_id} registered", device_id)
                return jsonify({
                    "success": True,
                    "message": f"Device '{data['name']}' added successfully",
                    "device_id": device_id,
                    "immediate_sync": True
                })
            else:
                return jsonify({"success": False, "error": "Failed to add device"}), 500

        except Exception as e:
            return handle_api_error("add_device", e)

    @api_bp.route('/devices/<device_id>', methods=['GET'])
    def get_device(device_id):
        """GET /api/devices/<device_id> - Get specific device"""
        try:
            device = device_manager.get_device(device_id)
            if device:
                return jsonify({"success": True, "device": device})
            else:
                return jsonify({"success": False, "error": "Device not found"}), 404
        except Exception as e:
            return handle_api_error(f"get_device_{device_id}", e)

    @api_bp.route('/devices/<device_id>', methods=['PUT'])
    def update_device(device_id):
        """PUT /api/devices/<device_id> - Update device"""
        try:
            data = request.json
            if not data:
                return jsonify({"success": False, "error": "No JSON data provided"}), 400

            # Check if device exists
            existing_device = device_manager.get_device(device_id)
            if not existing_device:
                return jsonify({"success": False, "error": "Device not found"}), 404

            # Update device (remove old, add new with updated info)
            device_manager.remove_device(device_id)
            success = device_manager.register_device(
                device_id=device_id,
                name=data.get('name', existing_device.get('name')),
                eep_profile=data.get('eep_profile', existing_device.get('eep_profile')),
                device_type=data.get('device_type', existing_device.get('device_type')),
                location=data.get('location', existing_device.get('location')),
                manufacturer=data.get('manufacturer', existing_device.get('manufacturer')),
                model=data.get('model', existing_device.get('model')),
                description=data.get('description', existing_device.get('description')),
                # Preserve activity data
                first_seen=existing_device.get('first_seen'),
                last_seen=existing_device.get('last_seen'),
                packet_count=existing_device.get('packet_count', 0)
            )

            if success:
                sync_and_log(f"Device {device_id} updated")
                return jsonify({
                    "success": True,
                    "message": f"Device {device_id} updated successfully"
                })
            else:
                return jsonify({"success": False, "error": "Failed to update device"}), 500

        except Exception as e:
            return handle_api_error(f"update_device_{device_id}", e)

    @api_bp.route('/devices/<device_id>', methods=['DELETE'])
    def remove_device(device_id):
        """DELETE /api/devices/<device_id> - Remove device"""
        try:
            success = device_manager.remove_device(device_id)
            if success:
                sync_and_log(f"Device {device_id} removed")
                return jsonify({
                    "success": True,
                    "message": f"Device {device_id} removed successfully"
                })
            else:
                return jsonify({"success": False, "error": "Device not found"}), 404

        except Exception as e:
            return handle_api_error(f"remove_device_{device_id}", e)

    @api_bp.route('/devices/<device_id>/activity', methods=['GET'])
    def get_device_activity(device_id):
        """GET /api/devices/<device_id>/activity - Get device activity and metrics"""
        try:
            devices = enocean_system.list_devices()
            device = next((d for d in devices if getattr(d, 'device_id', {}).get('value') == device_id), None)

            if not device:
                return jsonify({"success": False, "error": "Device not found"}), 404

            activity_data = {
                "success": True,
                "device_id": device_id,
                "name": getattr(device, 'name', 'Unknown'),
                "last_seen": getattr(device, 'last_seen', None),
                "packet_count": getattr(device, 'packet_count', 0),
                "status": getattr(device, 'status', 'unknown')
            }

            # Add monitoring data if available
            if enocean_system.metrics_collector:
                custom_metrics = getattr(enocean_system.metrics_collector, '_custom_metrics', {})
                device_metrics = {k: v for k, v in custom_metrics.items()
                                  if device_id in k or device_id in str(v)}
                activity_data['monitoring_metrics'] = device_metrics

            return jsonify(activity_data)

        except Exception as e:
            return handle_api_error(f"get_device_activity_{device_id}", e)

    # ========================================================================
    # Discovery Endpoints - Simplified
    # ========================================================================

    @api_bp.route('/discovery/unknown', methods=['GET'])
    def get_unknown_devices():
        """GET /api/discovery/unknown - Get unknown devices"""
        try:
            synchronizer.force_sync()  # Ensure clean data
            unknown_devices = []
            
            if hasattr(enocean_system, 'get_unknown_devices'):
                unknown_devices = enocean_system.get_unknown_devices()
                unknown_devices = [_unknown_device_to_dict(device) for device in unknown_devices]

            return jsonify({
                "success": True,
                "unknown_devices": unknown_devices,
                "count": len(unknown_devices),
                "last_sync": synchronizer.last_sync_time
            })

        except Exception as e:
            return handle_api_error("get_unknown_devices", e)

    @api_bp.route('/devices/register', methods=['POST'])
    def register_from_discovery():
        """POST /api/devices/register - Register device from discovery"""
        try:
            data = request.json
            is_valid, error_message = validate_device_data(data, ['device_id', 'name', 'eep_profile'])
            if not is_valid:
                return jsonify({"success": False, "error": error_message}), 400

            device_id = data['device_id']

            # Check if device already registered
            if device_manager.device_exists(device_id):
                return jsonify({
                    "success": False,
                    "error": f"Device {device_id} is already registered"
                }), 409

            # Register device
            success = device_manager.register_device(
                device_id=device_id,
                name=data['name'],
                eep_profile=data['eep_profile'],
                device_type=data.get('device_type', 'unknown'),
                location=data.get('location', ''),
                manufacturer=data.get('manufacturer', 'Unknown'),
                model=data.get('model', 'Unknown'),
                description=f"Registered via discovery with EEP {data['eep_profile']}"
            )

            if success:
                sync_and_log(f"Device {device_id} registered from discovery", device_id)
                return jsonify({
                    "success": True,
                    "message": f"Device '{data['name']}' registered from discovery",
                    "device_id": device_id,
                    "immediate_sync_performed": True
                })
            else:
                return jsonify({"success": False, "error": "Failed to register device"}), 500

        except Exception as e:
            return handle_api_error("register_from_discovery", e)

    @api_bp.route('/devices/<device_id>/ignore', methods=['POST'])
    def ignore_device(device_id):
        """POST /api/devices/<device_id>/ignore - Ignore unknown device"""
        try:
            synchronizer.on_device_ignored(device_id)
            sync_and_log(f"Device {device_id} ignored")
            return jsonify({
                "success": True,
                "message": f"Device {device_id} ignored"
            })
        except Exception as e:
            return handle_api_error(f"ignore_device_{device_id}", e)

    @api_bp.route('/devices/<device_id>/analyze', methods=['POST'])
    def analyze_device(device_id):
        """POST /api/devices/<device_id>/analyze - Re-analyze unknown device"""
        try:
            sync_and_log(f"Device {device_id} re-analysis triggered")
            return jsonify({
                "success": True,
                "message": f"Device {device_id} re-analysis triggered"
            })
        except Exception as e:
            return handle_api_error(f"analyze_device_{device_id}", e)

    # ========================================================================
    # System Endpoints - Simplified
    # ========================================================================

    @api_bp.route('/stats', methods=['GET'])
    def get_enhanced_stats():
        """GET /api/stats - Get enhanced system statistics"""
        try:
            # Gather base statistics
            base_stats = {}
            
            # Add stats from various components
            for component, method in [
                (device_manager, 'get_statistics'),
                (synchronizer, 'get_sync_statistics'),
                (enocean_system, 'get_statistics')
            ]:
                if hasattr(component, method):
                    try:
                        component_stats = getattr(component, method)()
                        base_stats.update(component_stats)
                    except Exception as e:
                        logger.warning(f"Failed to get stats from {component}: {e}")

            # Add monitoring data if available
            if enocean_system.metrics_collector:
                try:
                    metrics = enocean_system.metrics_collector.get_all_metrics()
                    counters = metrics.get('counters', {})
                    gauges = metrics.get('gauges', {})
                    
                    # Extract key monitoring metrics
                    base_stats.update({
                        'monitoring_packets_processed': counters.get('enocean_packets_processed_total', {}).get('value', 0),
                        'monitoring_errors': counters.get('enocean_errors_total', {}).get('value', 0),
                        'monitoring_devices_registered': gauges.get('enocean_devices_registered', {}).get('value', 0),
                        'monitoring_devices_unknown': gauges.get('enocean_devices_unknown', {}).get('value', 0),
                        'monitoring_enabled': True,
                        'monitoring_uptime': metrics.get('collection_duration', 0)
                    })

                    # Add processing time statistics
                    processing_histogram = metrics.get('histograms', {}).get('enocean_packet_processing_duration_seconds', {})
                    if processing_histogram:
                        stats = processing_histogram.get('statistics', {})
                        base_stats.update({
                            'avg_processing_time': stats.get('mean', 0),
                            'processing_time_95th': stats.get('percentiles', {}).get('95', 0)
                        })
                except Exception as e:
                    logger.warning(f"Failed to get monitoring stats: {e}")
                    base_stats['monitoring_enabled'] = False
            else:
                base_stats['monitoring_enabled'] = False

            # Add system metadata
            base_stats.update({
                "system_type": "real" if hasattr(enocean_system, 'process_packets_from_serial') else "mock",
                "modular_architecture": True,
                "fixed_state_sync": True,
                "api_version": "2.0",
                "success": True
            })

            return jsonify(base_stats)

        except Exception as e:
            return handle_api_error("get_enhanced_stats", e)

    @api_bp.route('/system/refresh', methods=['POST'])
    def refresh_system():
        """POST /api/system/refresh - Force system refresh"""
        try:
            synchronizer.force_sync()
            logger.info("System refreshed successfully")
            return jsonify({
                "success": True,
                "message": "System refreshed successfully",
                "refresh_time": time.time()
            })
        except Exception as e:
            return handle_api_error("refresh_system", e)

    @api_bp.route('/system/status', methods=['GET'])
    def get_system_status():
        """GET /api/system/status - Get detailed system status"""
        try:
            status = {
                "system_type": "real" if hasattr(enocean_system, 'process_packets_from_serial') else "mock",
                "sync_running": synchronizer.is_running() if hasattr(synchronizer, 'is_running') else True,
                "last_sync": getattr(synchronizer, 'last_sync_time', None),
                "device_manager_ready": True,
                "api_endpoints_active": True,
                "modular_architecture": True,
                "fixed_state_synchronization": True
            }

            return jsonify({"success": True, "status": status})

        except Exception as e:
            return handle_api_error("get_system_status", e)

    @api_bp.route('/system/health', methods=['GET'])
    def get_system_health():
        """GET /api/system/health - Get comprehensive system health"""
        try:
            health_data = {
                "timestamp": time.time(),
                "overall_status": "healthy",
                "components": {},
                "summary": {
                    "total_checks": 0,
                    "healthy_checks": 0,
                    "unhealthy_checks": 0,
                    "unknown_checks": 0
                }
            }

            healthy_count = 0
            unhealthy_count = 0
            unknown_count = 0

            # Gateway system check
            if enocean_system.running:
                stats = enocean_system.get_statistics() if hasattr(enocean_system, 'get_statistics') else {}
                health_data["components"]["gateway"] = {
                    "status": "healthy",
                    "uptime": stats.get('system_uptime', 0),
                    "devices": stats.get('registered_devices', 0),
                    "packets_processed": stats.get('packets_processed', 0)
                }
                healthy_count += 1
            else:
                health_data["components"]["gateway"] = {
                    "status": "unhealthy",
                    "error": "Gateway system not running"
                }
                unhealthy_count += 1

            # MQTT check
            if enocean_system.mqtt_connection.is_connected():
                health_data["components"]["mqtt"] = {
                    "status": "healthy",
                    "message": "MQTT connection active"
                }
                healthy_count += 1
            else:
                health_data["components"]["mqtt"] = {
                    "status": "unhealthy",
                    "message": "MQTT connection inactive"
                }
                unhealthy_count += 1

            # Serial check
            if enocean_system.serial_connection.is_connected():
                health_data["components"]["serial"] = {
                    "status": "healthy",
                    "message": "Serial connection active"
                }
                healthy_count += 1
            else:
                health_data["components"]["serial"] = {
                    "status": "unhealthy",
                    "message": "Serial connection inactive"
                }
                unhealthy_count += 1

            # Device manager check
            try:
                stats = device_manager.get_statistics() if hasattr(device_manager, 'get_statistics') else {}
                health_data["components"]["device_manager"] = {
                    "status": "healthy",
                    "registered_devices": stats.get('registered_devices', 0),
                    "message": "Device manager operational"
                }
                healthy_count += 1
            except Exception:
                health_data["components"]["device_manager"] = {
                    "status": "error",
                    "error": "Failed to get device manager statistics"
                }
                unhealthy_count += 1

            # Monitoring check
            if enocean_system.metrics_collector:
                try:
                    metrics_summary = enocean_system.metrics_collector.get_summary()
                    health_data["components"]["monitoring"] = {
                        "status": "healthy",
                        "uptime": metrics_summary.get('collection_uptime', 0),
                        "metrics_count": (
                            metrics_summary.get('total_counters', 0) +
                            metrics_summary.get('total_gauges', 0) +
                            metrics_summary.get('total_histograms', 0)
                        )
                    }
                    healthy_count += 1
                except Exception:
                    health_data["components"]["monitoring"] = {
                        "status": "error",
                        "error": "Failed to get monitoring statistics"
                    }
                    unhealthy_count += 1
            else:
                health_data["components"]["monitoring"] = {
                    "status": "disabled",
                    "message": "Monitoring not enabled"
                }
                unknown_count += 1

            # Performance check (if available)
            if enocean_system.performance_monitor:
                try:
                    perf_data = enocean_system.performance_monitor.get_performance_summary()
                    cpu_percent = perf_data.get('system', {}).get('cpu_percent', 0)
                    
                    cpu_status = "healthy"
                    if cpu_percent > 90:
                        cpu_status = "critical"
                        health_data["overall_status"] = "critical"
                    elif cpu_percent > 80:
                        cpu_status = "warning"
                        if health_data["overall_status"] == "healthy":
                            health_data["overall_status"] = "warning"

                    health_data["components"]["performance"] = {
                        "status": cpu_status,
                        "cpu_percent": cpu_percent,
                        "memory_percent": perf_data.get('system', {}).get('memory_percent', 0)
                    }
                    
                    if cpu_status == "healthy":
                        healthy_count += 1
                    else:
                        unhealthy_count += 1
                except Exception:
                    unknown_count += 1
            else:
                unknown_count += 1

            # Update summary
            health_data["summary"] = {
                "total_checks": healthy_count + unhealthy_count + unknown_count,
                "healthy_checks": healthy_count,
                "unhealthy_checks": unhealthy_count,
                "unknown_checks": unknown_count
            }

            # Determine overall status
            if unhealthy_count > 0 and health_data["overall_status"] == "healthy":
                health_data["overall_status"] = "unhealthy"
            elif unknown_count > healthy_count and health_data["overall_status"] == "healthy":
                health_data["overall_status"] = "degraded"

            return jsonify({
                "success": True,
                **health_data
            })

        except Exception as e:
            return handle_api_error("get_system_health", e)

    # ========================================================================
    # Testing Endpoints - Grouped under /test
    # ========================================================================

    @api_bp.route('/test/packet', methods=['POST'])
    def simulate_packet():
        """POST /api/test/packet - Simulate a packet"""
        try:
            data = request.json
            if not data or not all([data.get('device_id'), data.get('packet_data')]):
                return jsonify({
                    "success": False,
                    "error": "Missing device_id or packet_data"
                }), 400

            device_id = data['device_id']
            packet_data = data['packet_data']

            # Simulate packet
            success = False
            if hasattr(enocean_system, 'simulate_packet'):
                success = enocean_system.simulate_packet(device_id, packet_data)

            if success:
                # Update device activity and sync
                if device_manager.device_exists(device_id):
                    if hasattr(device_manager, 'update_device_activity'):
                        device_manager.update_device_activity(device_id)
                else:
                    # Add to unknown devices if not registered
                    try:
                        packet_bytes = bytes.fromhex(packet_data.replace(' ', '').replace(':', ''))
                        rorg = packet_bytes[0] if packet_bytes else 0xA5
                        if hasattr(synchronizer, 'add_unknown_device'):
                            synchronizer.add_unknown_device(device_id, packet_bytes, rorg)
                    except Exception:
                        pass  # Continue even if adding to unknown fails

                synchronizer.force_sync()
                sync_and_log(f"Packet simulated for {device_id}")

                return jsonify({
                    "success": True,
                    "message": f"Packet simulated for {device_id}",
                    "device_id": device_id,
                    "packet_data": packet_data
                })
            else:
                return jsonify({"success": False, "error": "Failed to simulate packet"}), 500

        except Exception as e:
            return handle_api_error("simulate_packet", e)

    @api_bp.route('/test/unknown_device', methods=['POST'])
    def simulate_unknown_device():
        """POST /api/test/unknown_device - Generate unknown device"""
        try:
            data = request.json or {}
            device_id = data.get('device_id', f'01:23:45:{int(time.time()) % 100:02d}')
            packet_count = data.get('packet_count', 5)
            rorg = data.get('rorg', 0xA5)

            success_count = 0

            # Generate sample packets based on RORG type
            for i in range(packet_count):
                if rorg == 0xA5:  # 4BS
                    packet_hex = f"A5 00 {64 + i * 10:02X} {150 + i * 5:02X} 08"
                elif rorg == 0xF6:  # RPS
                    packet_hex = f"F6 {'30' if i % 2 == 0 else '00'}"
                elif rorg == 0xD5:  # 1BS
                    packet_hex = f"D5 {'00' if i % 2 == 0 else '09'}"
                elif rorg == 0xD2:  # VLD
                    packet_hex = f"D2 01 02 03 04"
                else:
                    packet_hex = f"{rorg:02X} 00 00 00 00"

                if hasattr(enocean_system, 'simulate_packet'):
                    if enocean_system.simulate_packet(device_id, packet_hex):
                        success_count += 1

                time.sleep(0.01)  # Small delay between packets

            # Add to unknown devices and sync
            try:
                packet_bytes = bytes.fromhex(packet_hex.replace(' ', ''))
                if hasattr(synchronizer, 'add_unknown_device'):
                    synchronizer.add_unknown_device(device_id, packet_bytes, rorg)
            except Exception:
                pass

            synchronizer.force_sync()
            sync_and_log(f"Generated unknown device {device_id} with {success_count} packets")

            return jsonify({
                "success": True,
                "message": f"Generated unknown device with {success_count}/{packet_count} packets",
                "device_id": device_id,
                "rorg": f"0x{rorg:02X}",
                "packet_count": success_count
            })

        except Exception as e:
            return handle_api_error("simulate_unknown_device", e)

    @api_bp.route('/test/device/<device_id>', methods=['POST'])
    def test_device(device_id):
        """POST /api/test/device/<device_id> - Test specific device"""
        try:
            device = device_manager.get_device(device_id)
            if not device:
                return jsonify({"success": False, "error": "Device not found"}), 404

            # Generate test packet based on device's EEP profile
            eep_profile = device.get('eep_profile', 'A5-04-01')
            test_packet = _generate_test_packet_for_eep(eep_profile)

            success = False
            if hasattr(enocean_system, 'simulate_packet'):
                success = enocean_system.simulate_packet(device_id, test_packet)

            if success:
                if hasattr(device_manager, 'update_device_activity'):
                    device_manager.update_device_activity(device_id)
                sync_and_log(f"Test packet sent to {device.get('name', device_id)}")

                return jsonify({
                    "success": True,
                    "message": f"Test packet sent to {device.get('name', device_id)}",
                    "device_id": device_id,
                    "packet_data": test_packet,
                    "eep_profile": eep_profile
                })
            else:
                return jsonify({"success": False, "error": "Failed to send test packet"}), 500

        except Exception as e:
            return handle_api_error(f"test_device_{device_id}", e)

    # ========================================================================
    # Legacy Compatibility Endpoints
    # ========================================================================

    @api_bp.route('/simulate/packet', methods=['POST'])
    def legacy_simulate_packet():
        """Legacy endpoint - redirects to /test/packet"""
        return simulate_packet()

    @api_bp.route('/simulate/unknown_device', methods=['POST'])
    def legacy_simulate_unknown_device():
        """Legacy endpoint - redirects to /test/unknown_device"""  
        return simulate_unknown_device()

    # ========================================================================
    # Helper Functions
    # ========================================================================

    def _validate_device_id_format(device_id: str) -> bool:
        """Validate device ID format (XX:XX:XX:XX)"""
        try:
            parts = device_id.split(':')
            if len(parts) != 4:
                return False
            for part in parts:
                if len(part) != 2:
                    return False
                int(part, 16)  # Must be valid hex
            return True
        except Exception:
            return False

    def _unknown_device_to_dict(device) -> Dict[str, Any]:
        """Convert unknown device object to dictionary"""
        if hasattr(device, '__dict__'):
            result = device.__dict__.copy()
        else:
            result = device.copy()

        # Ensure sample_packets are hex strings
        if 'sample_packets' in result:
            sample_packets = result['sample_packets']
            if sample_packets and isinstance(sample_packets[0], bytes):
                result['sample_packets'] = [p.hex() for p in sample_packets]

        # Ensure eep_suggestions are dicts
        if 'eep_suggestions' in result:
            suggestions = result['eep_suggestions']
            if suggestions:
                result['eep_suggestions'] = [
                    s.__dict__ if hasattr(s, '__dict__') else s
                    for s in suggestions
                ]

        return result

    def _generate_test_packet_for_eep(eep_profile: str) -> str:
        """Generate test packet data for specific EEP profile"""
        if eep_profile.startswith('A5-04'):  # Temperature & Humidity
            return "A5 00 64 96 08"  # ~20°C, ~60% humidity
        elif eep_profile.startswith('A5-02'):  # Temperature only
            return "A5 00 00 64 08"  # ~20°C
        elif eep_profile.startswith('A5-06'):  # Light sensor
            return "A5 00 80 00 08"  # Medium light level
        elif eep_profile.startswith('F6-02'):  # Rocker switch
            return "F6 30"  # Button press
        elif eep_profile.startswith('D5-00'):  # Contact sensor
            return "D5 09"  # Contact open
        elif eep_profile.startswith('D2-14'):  # Multi-sensor
            return "D2 01 64 96 08"  # Multi-sensor data
        else:
            return "A5 00 64 96 08"  # Default test packet

    logger.info("✅ Simplified API routes created")
    return api_bp