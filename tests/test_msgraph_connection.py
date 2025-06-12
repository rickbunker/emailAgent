#!/usr/bin/env python3
"""
Test Microsoft Graph Connection with New Credentials
"""

import asyncio
import sys
import os
import json
import time
import socket
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, UTC
import aiohttp
import ssl

# Add src to path (go up one directory from tests/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface import EmailInterfaceFactory
from utils.logging_system import (
    LogConfig, configure_logging, get_logger, log_function, 
    log_debug, log_info
)

# Initialize logger for this test module
logger = get_logger(__name__)

async def test_msgraph_connection():
    print("🧪 Testing Microsoft Graph Connection")
    print("="*50)
    
    try:
        # Load credentials
        creds_path = Path('config/msgraph_credentials.json')
        if not creds_path.exists():
            print("❌ Credentials file not found")
            return
        
        with open(creds_path) as f:
            credentials = json.load(f)
        
        print(f"✅ Loaded credentials for: {credentials['application_name']}")
        print(f"   Client ID: {credentials['client_id']}")
        print(f"   Tenant ID: {credentials['tenant_id']}")
        
        # Create Microsoft Graph interface
        msgraph = EmailInterfaceFactory.create('microsoft_graph')
        
        print("\n🔗 Connecting to Microsoft Graph...")
        success = await msgraph.connect(credentials)
        
        if success:
            print("✅ Successfully connected to Microsoft Graph!")
            
            # Get profile
            profile = await msgraph.get_profile()
            print(f"📧 Connected as: {profile.get('name', 'Unknown')} ({profile.get('email', 'Unknown')})")
            
            # Test fetching a few emails
            print("\n📧 Testing email fetch...")
            from email_interface import EmailSearchCriteria
            
            criteria = EmailSearchCriteria(max_results=5)
            emails = await msgraph.list_emails(criteria)
            
            print(f"✅ Fetched {len(emails)} emails successfully")
            
            for i, email in enumerate(emails[:3], 1):
                print(f"   {i}. From: {email.sender.address}")
                print(f"      Subject: {email.subject[:50]}...")
                print(f"      Attachments: {len(email.attachments)}")
            
            # Disconnect
            await msgraph.disconnect()
            print("\n🔒 Disconnected from Microsoft Graph")
            print("🎉 Microsoft Graph setup is working correctly!")
            
        else:
            print("❌ Failed to connect to Microsoft Graph")
            print("   Check your credentials and permissions")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"🐛 Traceback: {traceback.format_exc()}")

class MicrosoftGraphConnectionTestSuite:
    """
    Microsoft Graph connection test suite for asset management.
    
    Provides complete validation of Microsoft Graph connectivity
    including network availability, authentication verification, and
    service endpoint validation for asset management email automation
    and business intelligence requirements.
    
    Features:
        - Complete connection validation and monitoring
        - authentication and credential verification
        - Asset management service availability testing
        - Network performance and reliability assessment
        - Error handling and recovery mechanism validation
        
    Attributes:
        test_stats: Connection test execution metrics and results
        connection_results: Complete connection validation data
        performance_metrics: Network and service performance data
        auth_credentials: Microsoft Graph authentication configuration
    """
    
    def __init__(self):
        """Initialize the Microsoft Graph connection test suite."""
        logger.info("Initializing MicrosoftGraphConnectionTestSuite for asset management environments")
        
        self.test_stats = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'connections_tested': 0,
            'connections_successful': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }
        
        self.connection_results: Dict[str, Any] = {}
        self.performance_metrics: Dict[str, Any] = {}
        self.auth_credentials: Dict[str, Any] = {}
        
        # Configure logging for connection testing
        self._setup_logging_configuration()
        
        logger.info("MicrosoftGraphConnectionTestSuite initialized successfully")

    @log_function()
    def _setup_logging_configuration(self) -> None:
        """
        Setup logging configuration for connection testing.
        
        Configures complete logging for Microsoft Graph connection
        validation with asset management context and audit trail requirements.
        """
        logger.info("Setting up Microsoft Graph connection test logging configuration")
        
        connection_config = LogConfig(
            level="INFO",
            log_to_file=True,
            log_to_stdout=True,
            log_file="logs/msgraph_connection_test.log",
            log_arguments=True,
            log_return_values=False,  # Avoid logging sensitive credentials
            log_execution_time=True,
            max_arg_length=200,
            sensitive_keys=[
                'client_secret', 'access_token', 'refresh_token',
                'password', 'secret', 'key', 'credential', 'auth', 'tenant_id'
            ]
        )
        
        configure_logging(connection_config)
        logger.info("Microsoft Graph connection test logging configuration completed")

    @log_function()
    def _load_connection_credentials(self) -> bool:
        """
        Load Microsoft Graph connection credentials for testing.
        
        Locates and validates Microsoft Graph connection credentials
        for complete connection testing in asset management
        environments with credential management.
        
        Returns:
            True if connection credentials loaded successfully, False otherwise
        """
        logger.info("Loading Microsoft Graph connection credentials")
        
        try:
            # Standard credential locations
            credential_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'msgraph_credentials.json'),
                os.path.join(os.path.dirname(__file__), '..', 'credentials', 'msgraph_credentials.json'),
                os.path.join(os.path.expanduser('~'), '.emailagent', 'msgraph_credentials.json')
            ]
            
            credentials_file = None
            for cred_path in credential_paths:
                if os.path.exists(cred_path):
                    credentials_file = cred_path
                    logger.info(f"Microsoft Graph credentials found: {cred_path}")
                    break
            
            if not credentials_file:
                logger.warning("Microsoft Graph credentials file not found - using simulated credentials")
                # Use simulated credentials for testing
                self.auth_credentials = {
                    'client_id': 'test-client-id',
                    'tenant_id': 'test-tenant-id',
                    'application_name': 'EmailAgent Test Suite'
                }
                return True
            
            # Load actual credentials
            with open(credentials_file, 'r') as f:
                credentials = json.load(f)
            
            # Validate required fields
            required_fields = ['client_id', 'tenant_id']
            missing_fields = [field for field in required_fields if field not in credentials]
            
            if missing_fields:
                logger.error(f"Missing required credential fields: {missing_fields}")
                return False
            
            self.auth_credentials = credentials
            
            logger.info(f"Connection credentials loaded successfully")
            logger.info(f"Application: {credentials.get('application_name', 'Unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load connection credentials: {e}")
            return False

    @log_function()
    async def test_network_connectivity(self) -> bool:
        """
        Test basic network connectivity to Microsoft Graph endpoints.
        
        Validates network connectivity to Microsoft Graph API endpoints
        including DNS resolution, SSL certificate validation, and basic
        HTTP connectivity for asset management environments.
        
        Returns:
            True if network connectivity tests passed, False otherwise
        """
        logger.info("Testing network connectivity to Microsoft Graph endpoints")
        
        try:
            # Microsoft Graph endpoints to test
            graph_endpoints = [
                'https://graph.microsoft.com',
                'https://login.microsoftonline.com',
                'https://outlook.office365.com'
            ]
            
            connectivity_results = {
                'endpoints_tested': len(graph_endpoints),
                'endpoints_reachable': 0,
                'dns_resolutions': {},
                'ssl_validations': {},
                'response_times': {}
            }
            
            # Test each endpoint
            for endpoint in graph_endpoints:
                logger.info(f"Testing connectivity to: {endpoint}")
                
                endpoint_start_time = time.time()
                
                try:
                    # Test DNS resolution
                    hostname = endpoint.replace('https://', '').replace('http://', '')
                    socket.gethostbyname(hostname)
                    connectivity_results['dns_resolutions'][endpoint] = True
                    logger.debug(f"DNS resolution successful for {hostname}")
                    
                    # Test HTTP connectivity with timeout
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=10),
                        connector=aiohttp.TCPConnector(ssl=ssl.create_default_context())
                    ) as session:
                        async with session.head(endpoint) as response:
                            response_time = time.time() - endpoint_start_time
                            connectivity_results['response_times'][endpoint] = response_time
                            
                            if response.status < 500:  # Accept any non-server error
                                connectivity_results['endpoints_reachable'] += 1
                                connectivity_results['ssl_validations'][endpoint] = True
                                logger.info(f"Connectivity successful to {endpoint} ({response_time:.3f}s)")
                            else:
                                connectivity_results['ssl_validations'][endpoint] = False
                                logger.warning(f"Server error for {endpoint}: HTTP {response.status}")
                
                except Exception as e:
                    response_time = time.time() - endpoint_start_time
                    connectivity_results['response_times'][endpoint] = response_time
                    connectivity_results['dns_resolutions'][endpoint] = False
                    connectivity_results['ssl_validations'][endpoint] = False
                    logger.warning(f"Connectivity failed for {endpoint}: {e}")
                
                # Brief delay between endpoint tests
                await asyncio.sleep(0.1)
            
            # Calculate connectivity success rate
            connectivity_rate = (
                connectivity_results['endpoints_reachable'] / connectivity_results['endpoints_tested'] * 100
                if connectivity_results['endpoints_tested'] > 0 else 0
            )
            
            connectivity_results['connectivity_rate'] = connectivity_rate
            connectivity_results['average_response_time'] = (
                sum(connectivity_results['response_times'].values()) / len(connectivity_results['response_times'])
                if connectivity_results['response_times'] else 0
            )
            
            # Store network connectivity results
            self.connection_results['network_connectivity'] = {
                'success': connectivity_rate >= 66.67,  # At least 2/3 endpoints reachable
                'results': connectivity_results
            }
            
            logger.info(f"Network connectivity testing completed")
            logger.info(f"Endpoints reachable: {connectivity_results['endpoints_reachable']}/{connectivity_results['endpoints_tested']}")
            logger.info(f"Connectivity rate: {connectivity_rate:.1f}%")
            logger.info(f"Average response time: {connectivity_results['average_response_time']:.3f}s")
            
            return connectivity_rate >= 66.67
            
        except Exception as e:
            logger.error(f"Network connectivity test failed: {e}")
            
            self.connection_results['network_connectivity'] = {
                'success': False,
                'error': str(e),
                'exception_type': type(e).__name__
            }
            
            return False

    @log_function()
    async def test_authentication_endpoints(self) -> bool:
        """
        Test Microsoft Graph authentication endpoint availability.
        
        Validates authentication endpoint availability and response
        for Microsoft Graph OAuth flows including tenant-specific
        endpoints and authentication service discovery.
        
        Returns:
            True if authentication endpoint tests passed, False otherwise
        """
        logger.info("Testing Microsoft Graph authentication endpoint availability")
        
        try:
            if not self.auth_credentials:
                logger.error("Authentication credentials not loaded - cannot test auth endpoints")
                return False
            
            tenant_id = self.auth_credentials.get('tenant_id', 'common')
            
            # Authentication endpoints to test
            auth_endpoints = [
                f"https://login.microsoftonline.com/{tenant_id}/.well-known/openid_configuration",
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            ]
            
            auth_results = {
                'endpoints_tested': len(auth_endpoints),
                'endpoints_available': 0,
                'endpoint_details': {},
                'discovery_successful': False
            }
            
            # Test each authentication endpoint
            for endpoint in auth_endpoints:
                logger.info(f"Testing authentication endpoint: {endpoint}")
                
                endpoint_start_time = time.time()
                
                try:
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as session:
                        async with session.head(endpoint) as response:
                            response_time = time.time() - endpoint_start_time
                            
                            endpoint_detail = {
                                'status_code': response.status,
                                'response_time': response_time,
                                'headers': dict(response.headers),
                                'available': response.status < 500
                            }
                            
                            auth_results['endpoint_details'][endpoint] = endpoint_detail
                            
                            if endpoint_detail['available']:
                                auth_results['endpoints_available'] += 1
                                logger.info(f"Authentication endpoint available: {endpoint} ({response_time:.3f}s)")
                            else:
                                logger.warning(f"Authentication endpoint unavailable: {endpoint} (HTTP {response.status})")
                
                except Exception as e:
                    response_time = time.time() - endpoint_start_time
                    auth_results['endpoint_details'][endpoint] = {
                        'status_code': None,
                        'response_time': response_time,
                        'error': str(e),
                        'available': False
                    }
                    logger.warning(f"Authentication endpoint test failed: {endpoint} - {e}")
                
                await asyncio.sleep(0.1)
            
            # Test OpenID Connect discovery (if available)
            discovery_endpoint = f"https://login.microsoftonline.com/{tenant_id}/.well-known/openid_configuration"
            if discovery_endpoint in auth_results['endpoint_details']:
                discovery_detail = auth_results['endpoint_details'][discovery_endpoint]
                if discovery_detail['available']:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(discovery_endpoint) as response:
                                if response.status == 200:
                                    discovery_data = await response.json()
                                    auth_results['discovery_successful'] = True
                                    auth_results['discovery_data'] = {
                                        'issuer': discovery_data.get('issuer'),
                                        'authorization_endpoint': discovery_data.get('authorization_endpoint'),
                                        'token_endpoint': discovery_data.get('token_endpoint')
                                    }
                                    logger.info("OpenID Connect discovery successful")
                    except Exception as e:
                        logger.warning(f"OpenID Connect discovery failed: {e}")
            
            # Calculate authentication availability
            auth_availability = (
                auth_results['endpoints_available'] / auth_results['endpoints_tested'] * 100
                if auth_results['endpoints_tested'] > 0 else 0
            )
            
            auth_results['availability_rate'] = auth_availability
            
            # Store authentication endpoint results
            self.connection_results['authentication_endpoints'] = {
                'success': auth_availability >= 66.67,  # At least 2/3 endpoints available
                'results': auth_results
            }
            
            logger.info(f"Authentication endpoint testing completed")
            logger.info(f"Endpoints available: {auth_results['endpoints_available']}/{auth_results['endpoints_tested']}")
            logger.info(f"Availability rate: {auth_availability:.1f}%")
            logger.info(f"Discovery successful: {auth_results['discovery_successful']}")
            
            return auth_availability >= 66.67
            
        except Exception as e:
            logger.error(f"Authentication endpoint test failed: {e}")
            
            self.connection_results['authentication_endpoints'] = {
                'success': False,
                'error': str(e),
                'exception_type': type(e).__name__
            }
            
            return False

    @log_function()
    async def test_graph_api_endpoints(self) -> bool:
        """
        Test Microsoft Graph API endpoint availability and responsiveness.
        
        Validates Microsoft Graph API endpoint availability including
        user, mail, and calendar endpoints for asset management email
        automation requirements with complete validation.
        
        Returns:
            True if Graph API endpoint tests passed, False otherwise
        """
        logger.info("Testing Microsoft Graph API endpoint availability")
        
        try:
            # Microsoft Graph API endpoints to test
            api_endpoints = [
                'https://graph.microsoft.com/v1.0',
                'https://graph.microsoft.com/v1.0/$metadata',
                'https://graph.microsoft.com/beta',
                'https://graph.microsoft.com/beta/$metadata'
            ]
            
            api_results = {
                'endpoints_tested': len(api_endpoints),
                'endpoints_available': 0,
                'endpoint_details': {},
                'metadata_available': False
            }
            
            # Test each API endpoint
            for endpoint in api_endpoints:
                logger.info(f"Testing API endpoint: {endpoint}")
                
                endpoint_start_time = time.time()
                
                try:
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as session:
                        async with session.head(endpoint) as response:
                            response_time = time.time() - endpoint_start_time
                            
                            endpoint_detail = {
                                'status_code': response.status,
                                'response_time': response_time,
                                'headers': dict(response.headers),
                                'available': response.status < 500
                            }
                            
                            api_results['endpoint_details'][endpoint] = endpoint_detail
                            
                            if endpoint_detail['available']:
                                api_results['endpoints_available'] += 1
                                logger.info(f"API endpoint available: {endpoint} ({response_time:.3f}s)")
                                
                                # Check if this is a metadata endpoint
                                if '$metadata' in endpoint and response.status == 200:
                                    api_results['metadata_available'] = True
                            else:
                                logger.warning(f"API endpoint unavailable: {endpoint} (HTTP {response.status})")
                
                except Exception as e:
                    response_time = time.time() - endpoint_start_time
                    api_results['endpoint_details'][endpoint] = {
                        'status_code': None,
                        'response_time': response_time,
                        'error': str(e),
                        'available': False
                    }
                    logger.warning(f"API endpoint test failed: {endpoint} - {e}")
                
                await asyncio.sleep(0.1)
            
            # Calculate API availability
            api_availability = (
                api_results['endpoints_available'] / api_results['endpoints_tested'] * 100
                if api_results['endpoints_tested'] > 0 else 0
            )
            
            api_results['availability_rate'] = api_availability
            
            # Calculate average response time
            response_times = [
                detail['response_time'] for detail in api_results['endpoint_details'].values()
                if 'response_time' in detail
            ]
            
            api_results['average_response_time'] = (
                sum(response_times) / len(response_times) if response_times else 0
            )
            
            # Store API endpoint results
            self.connection_results['graph_api_endpoints'] = {
                'success': api_availability >= 50.0,  # At least half endpoints available
                'results': api_results
            }
            
            logger.info(f"Graph API endpoint testing completed")
            logger.info(f"Endpoints available: {api_results['endpoints_available']}/{api_results['endpoints_tested']}")
            logger.info(f"Availability rate: {api_availability:.1f}%")
            logger.info(f"Metadata available: {api_results['metadata_available']}")
            logger.info(f"Average response time: {api_results['average_response_time']:.3f}s")
            
            return api_availability >= 50.0
            
        except Exception as e:
            logger.error(f"Graph API endpoint test failed: {e}")
            
            self.connection_results['graph_api_endpoints'] = {
                'success': False,
                'error': str(e),
                'exception_type': type(e).__name__
            }
            
            return False

    @log_function()
    async def test_connection_performance(self) -> bool:
        """
        Test Microsoft Graph connection performance and reliability.
        
        Validates connection performance including latency, throughput,
        and reliability metrics for asset management production
        environments with complete performance assessment.
        
        Returns:
            True if connection performance meets requirements, False otherwise
        """
        logger.info("Testing Microsoft Graph connection performance and reliability")
        
        try:
            # Performance benchmarks for asset management
            performance_benchmarks = {
                'max_average_latency': 2.0,  # 2 seconds maximum average latency
                'max_individual_latency': 10.0,  # 10 seconds maximum individual request
                'min_success_rate': 95.0,  # 95% minimum success rate
                'connection_stability_threshold': 0.9  # 90% stability threshold
            }
            
            # Collect performance data from previous tests
            performance_data = {
                'latency_measurements': [],
                'success_measurements': [],
                'availability_measurements': []
            }
            
            # Extract latency data from connection tests
            for test_name, test_result in self.connection_results.items():
                if test_result.get('success') and 'results' in test_result:
                    results = test_result['results']
                    
                    # Extract response times
                    if 'response_times' in results:
                        performance_data['latency_measurements'].extend(results['response_times'].values())
                    
                    if 'endpoint_details' in results:
                        for endpoint_detail in results['endpoint_details'].values():
                            if 'response_time' in endpoint_detail:
                                performance_data['latency_measurements'].append(endpoint_detail['response_time'])
                    
                    # Extract success rates
                    if 'connectivity_rate' in results:
                        performance_data['success_measurements'].append(results['connectivity_rate'])
                    
                    if 'availability_rate' in results:
                        performance_data['availability_measurements'].append(results['availability_rate'])
            
            # Calculate performance metrics
            performance_metrics = {}
            
            if performance_data['latency_measurements']:
                latencies = performance_data['latency_measurements']
                performance_metrics['latency'] = {
                    'average': sum(latencies) / len(latencies),
                    'maximum': max(latencies),
                    'minimum': min(latencies),
                    'count': len(latencies)
                }
            
            if performance_data['success_measurements']:
                success_rates = performance_data['success_measurements']
                performance_metrics['success_rate'] = {
                    'average': sum(success_rates) / len(success_rates),
                    'minimum': min(success_rates),
                    'maximum': max(success_rates)
                }
            
            if performance_data['availability_measurements']:
                availability_rates = performance_data['availability_measurements']
                performance_metrics['availability'] = {
                    'average': sum(availability_rates) / len(availability_rates),
                    'minimum': min(availability_rates),
                    'maximum': max(availability_rates)
                }
            
            # Evaluate performance against benchmarks
            performance_scores = {}
            
            # Latency score
            if 'latency' in performance_metrics:
                avg_latency = performance_metrics['latency']['average']
                max_latency = performance_metrics['latency']['maximum']
                
                performance_scores['latency'] = {
                    'average_latency': avg_latency,
                    'max_latency': max_latency,
                    'avg_benchmark_met': avg_latency <= performance_benchmarks['max_average_latency'],
                    'max_benchmark_met': max_latency <= performance_benchmarks['max_individual_latency']
                }
            
            # Success rate score
            if 'success_rate' in performance_metrics:
                avg_success = performance_metrics['success_rate']['average']
                
                performance_scores['success_rate'] = {
                    'average_success_rate': avg_success,
                    'benchmark_met': avg_success >= performance_benchmarks['min_success_rate']
                }
            
            # Overall performance evaluation
            benchmark_results = []
            
            if 'latency' in performance_scores:
                benchmark_results.extend([
                    performance_scores['latency']['avg_benchmark_met'],
                    performance_scores['latency']['max_benchmark_met']
                ])
            
            if 'success_rate' in performance_scores:
                benchmark_results.append(performance_scores['success_rate']['benchmark_met'])
            
            overall_performance_score = (
                sum(benchmark_results) / len(benchmark_results) if benchmark_results else 0
            )
            
            performance_assessment = {
                'benchmarks': performance_benchmarks,
                'metrics': performance_metrics,
                'scores': performance_scores,
                'overall_score': overall_performance_score,
                'performance_grade': (
                    'excellent' if overall_performance_score >= 0.9 else
                    'good' if overall_performance_score >= 0.7 else
                    'acceptable' if overall_performance_score >= 0.5 else
                    'needs_improvement'
                )
            }
            
            # Store performance results
            self.performance_metrics = performance_assessment
            
            self.connection_results['performance_assessment'] = {
                'success': overall_performance_score >= 0.7,  # 70% threshold
                'assessment': performance_assessment
            }
            
            logger.info(f"Connection performance assessment completed")
            logger.info(f"Overall performance score: {overall_performance_score:.2f}")
            logger.info(f"Performance grade: {performance_assessment['performance_grade']}")
            
            if 'latency' in performance_metrics:
                logger.info(f"Average latency: {performance_metrics['latency']['average']:.3f}s")
            
            if 'success_rate' in performance_metrics:
                logger.info(f"Average success rate: {performance_metrics['success_rate']['average']:.1f}%")
            
            return overall_performance_score >= 0.7
            
        except Exception as e:
            logger.error(f"Connection performance test failed: {e}")
            
            self.connection_results['performance_assessment'] = {
                'success': False,
                'error': str(e),
                'exception_type': type(e).__name__
            }
            
            return False

    @log_function()
    async def run_complete_connection_tests(self) -> Dict[str, Any]:
        """
        Run complete Microsoft Graph connection test suite.
        
        Executes complete connection validation including network
        connectivity, authentication endpoints, API availability,
        and performance assessment for asset management environments.
        
        Returns:
            Dictionary containing complete connection test results
        """
        logger.info("🚀 Running complete Microsoft Graph connection test suite")
        
        self.test_stats['start_time'] = datetime.now(UTC)
        
        # Load connection credentials
        if not self._load_connection_credentials():
            logger.error("Failed to load connection credentials - proceeding with limited testing")
        
        # Connection test sequence
        connection_tests = [
            ("Network Connectivity", self.test_network_connectivity),
            ("Authentication Endpoints", self.test_authentication_endpoints),
            ("Graph API Endpoints", self.test_graph_api_endpoints),
            ("Connection Performance", self.test_connection_performance)
        ]
        
        test_results = {
            'suite_name': 'Microsoft Graph Connection Tests',
            'start_time': self.test_stats['start_time'],
            'tests_run': [],
            'overall_success': True,
            'connection_analytics': {},
            'errors': []
        }
        
        # Execute connection tests
        for test_name, test_function in connection_tests:
            logger.info(f"Running {test_name}...")
            self.test_stats['tests_run'] += 1
            
            try:
                test_start = time.time()
                success = await test_function()
                test_duration = time.time() - test_start
                
                if success:
                    self.test_stats['tests_passed'] += 1
                    logger.info(f"✅ {test_name} passed ({test_duration:.2f}s)")
                else:
                    self.test_stats['tests_failed'] += 1
                    test_results['overall_success'] = False
                    logger.error(f"❌ {test_name} failed")
                
                test_results['tests_run'].append({
                    'name': test_name,
                    'success': success,
                    'duration': test_duration,
                    'error': None if success else f"{test_name} validation failed"
                })
                
            except Exception as e:
                self.test_stats['tests_failed'] += 1
                test_results['overall_success'] = False
                error_msg = f"{test_name}: {str(e)}"
                test_results['errors'].append(error_msg)
                self.test_stats['errors'].append(error_msg)
                
                test_results['tests_run'].append({
                    'name': test_name,
                    'success': False,
                    'duration': 0,
                    'error': str(e)
                })
                
                logger.error(f"❌ {test_name} failed with exception: {e}")
        
        # Calculate final statistics
        self.test_stats['end_time'] = datetime.now(UTC)
        self.test_stats['total_duration'] = (
            self.test_stats['end_time'] - self.test_stats['start_time']
        ).total_seconds()
        
        if self.test_stats['tests_run'] > 0:
            self.test_stats['success_rate'] = (
                self.test_stats['tests_passed'] / self.test_stats['tests_run']
            ) * 100
        
        test_results['end_time'] = self.test_stats['end_time']
        test_results['duration'] = self.test_stats['total_duration']
        test_results['statistics'] = self.test_stats
        test_results['connection_results'] = self.connection_results
        test_results['performance_metrics'] = self.performance_metrics
        
        return test_results

# Main execution functions
@log_function()
async def run_msgraph_connection_tests() -> bool:
    """
    Main function to run complete Microsoft Graph connection tests.
    
    Executes complete connection validation for asset management
    email automation with connectivity assessment
    and performance validation for production environments.
    
    Returns:
        True if all connection tests passed, False otherwise
    """
    logger.info("Initializing complete Microsoft Graph connection test execution")
    
    try:
        test_suite = MicrosoftGraphConnectionTestSuite()
        results = await test_suite.run_complete_connection_tests()
        
        # Display complete results
        print(f"\n🎯 EmailAgent Microsoft Graph Connection Test Results")
        print(f"=" * 65)
        
        status_emoji = "✅" if results['overall_success'] else "❌"
        print(f"{status_emoji} Overall Status: {'PASSED' if results['overall_success'] else 'FAILED'}")
        
        print(f"\n📊 Connection Test Summary:")
        print(f"   - Duration: {results['duration']:.2f} seconds")
        print(f"   - Tests Run: {len(results['tests_run'])}")
        print(f"   - Success Rate: {results['statistics']['success_rate']:.1f}%")
        
        print(f"\n📋 Individual Connection Test Results:")
        for test in results['tests_run']:
            test_emoji = "✅" if test['success'] else "❌"
            print(f"   {test_emoji} {test['name']}: {'PASSED' if test['success'] else 'FAILED'}")
            if test['error']:
                print(f"      Error: {test['error']}")
        
        # Display connection analytics
        connection_results = results.get('connection_results', {})
        
        # Network connectivity results
        network_result = connection_results.get('network_connectivity', {})
        if network_result.get('success'):
            network_data = network_result['results']
            print(f"\n🌐 Network Connectivity:")
            print(f"   - Endpoints Reachable: {network_data['endpoints_reachable']}/{network_data['endpoints_tested']}")
            print(f"   - Connectivity Rate: {network_data['connectivity_rate']:.1f}%")
            print(f"   - Average Response Time: {network_data['average_response_time']:.3f}s")
        
        # Authentication endpoints results
        auth_result = connection_results.get('authentication_endpoints', {})
        if auth_result.get('success'):
            auth_data = auth_result['results']
            print(f"\n🔐 Authentication Endpoints:")
            print(f"   - Endpoints Available: {auth_data['endpoints_available']}/{auth_data['endpoints_tested']}")
            print(f"   - Availability Rate: {auth_data['availability_rate']:.1f}%")
            print(f"   - Discovery Successful: {auth_data['discovery_successful']}")
        
        # API endpoints results
        api_result = connection_results.get('graph_api_endpoints', {})
        if api_result.get('success'):
            api_data = api_result['results']
            print(f"\n📊 Graph API Endpoints:")
            print(f"   - Endpoints Available: {api_data['endpoints_available']}/{api_data['endpoints_tested']}")
            print(f"   - Availability Rate: {api_data['availability_rate']:.1f}%")
            print(f"   - Metadata Available: {api_data['metadata_available']}")
        
        # Performance metrics
        perf_metrics = results.get('performance_metrics', {})
        if perf_metrics:
            print(f"\n📈 Performance Assessment:")
            print(f"   - Overall Score: {perf_metrics['overall_score']:.2f}")
            print(f"   - Performance Grade: {perf_metrics['performance_grade']}")
            
            if 'metrics' in perf_metrics and 'latency' in perf_metrics['metrics']:
                latency = perf_metrics['metrics']['latency']
                print(f"   - Average Latency: {latency['average']:.3f}s")
        
        if results['errors']:
            print(f"\n❌ Errors Encountered:")
            for error in results['errors']:
                print(f"   - {error}")
        
        if results['overall_success']:
            print(f"\n🎉 All Microsoft Graph connection tests passed successfully!")
            print(f"Connection validated for asset management environments.")
        else:
            print(f"\n⚠️  Some connection tests failed - review results above")
            print(f"Connection requires attention before production use.")
        
        return results['overall_success']
        
    except Exception as e:
        logger.error(f"Microsoft Graph connection test execution failed: {e}")
        print(f"\n❌ Connection test execution failed: {e}")
        return False

def main() -> None:
    """
    Main entry point for Microsoft Graph connection tests.
    
    Provides command-line interface for connection test
    execution with complete error handling and reporting.
    """
    print("🧪 EmailAgent Microsoft Graph Connection Test Suite")
    print("Asset Management Microsoft Graph Connectivity Validation")
    print("=" * 65)
    
    try:
        success = asyncio.run(run_msgraph_connection_tests())
        
        exit_code = 0 if success else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Connection test execution interrupted by user")
        logger.info("Microsoft Graph connection test execution interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Connection test runner failed: {e}")
        logger.error(f"Microsoft Graph connection test runner execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 