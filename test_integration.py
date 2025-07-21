#!/usr/bin/env python3
"""
Integration tests for VPC Detective with Flow Logs detection.

These tests verify that the enhanced functionality integrates properly
with the existing VPC Detective workflow.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import importlib.util
spec = importlib.util.spec_from_file_location("vpc_detective", "vpc-detective.py")
vpc_detective = importlib.util.module_from_spec(spec)
sys.modules["vpc_detective"] = vpc_detective
spec.loader.exec_module(vpc_detective)

from vpc_detective import get_vpcs, generate_markdown


class TestVPCDetectiveIntegration(unittest.TestCase):
    """Integration tests for VPC Detective with Flow Logs."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_ec2_client = Mock()
        self.mock_logs_client = Mock()
        
        # Mock VPC data
        self.mock_vpc_response = {
            'Vpcs': [{
                'VpcId': 'vpc-12345678',
                'CidrBlock': '10.0.0.0/16',
                'IsDefault': False,
                'Tags': [{'Key': 'Name', 'Value': 'Test-VPC'}]
            }]
        }
        
        # Mock Flow Logs response
        self.mock_flow_logs_response = {
            'FlowLogs': [{
                'FlowLogStatus': 'ACTIVE',
                'LogDestinationType': 'cloud-watch-logs',
                'LogGroupName': '/aws/vpc/flowlogs'
            }]
        }
        
        # Mock CloudWatch retention response
        self.mock_retention_response = {
            'logGroups': [{
                'logGroupName': '/aws/vpc/flowlogs',
                'retentionInDays': 30
            }]
        }

    @patch('vpc_detective.get_interface_count')
    @patch('vpc_detective.get_vpc_subnets')
    @patch('vpc_detective.get_natgws')
    @patch('vpc_detective.get_vpc_igw')
    def test_get_vpcs_with_flow_logs_integration(self, mock_igw, mock_natgws, mock_subnets, mock_interfaces):
        """Test that get_vpcs properly integrates Flow Logs data."""
        # Set up mocks for existing functionality
        mock_igw.return_value = True
        mock_natgws.return_value = 2
        mock_subnets.return_value = 4
        mock_interfaces.return_value = 8
        
        # Set up EC2 client mocks
        mock_vpc_paginator = Mock()
        mock_vpc_paginator.paginate.return_value = [self.mock_vpc_response]
        
        mock_flow_logs_paginator = Mock()
        mock_flow_logs_paginator.paginate.return_value = [self.mock_flow_logs_response]
        
        def get_paginator_side_effect(service):
            if service == 'describe_vpcs':
                return mock_vpc_paginator
            elif service == 'describe_flow_logs':
                return mock_flow_logs_paginator
            
        self.mock_ec2_client.get_paginator.side_effect = get_paginator_side_effect
        self.mock_ec2_client.meta.region_name = 'us-east-1'
        
        # Set up CloudWatch Logs client mock
        self.mock_logs_client.describe_log_groups.return_value = self.mock_retention_response
        
        # Call get_vpcs with both clients
        result = get_vpcs(self.mock_ec2_client, self.mock_logs_client)
        
        # Verify the result includes Flow Logs data
        self.assertEqual(len(result), 1)
        vpc_data = result[0]
        
        # Check existing fields are still present
        self.assertEqual(vpc_data['vpc_id'], 'vpc-12345678')
        self.assertEqual(vpc_data['vpc_name'], 'Test-VPC')
        self.assertEqual(vpc_data['vpc_cidr'], '10.0.0.0/16')
        self.assertEqual(vpc_data['is_default'], False)
        self.assertEqual(vpc_data['igw_present'], True)
        self.assertEqual(vpc_data['natgw_count'], 2)
        self.assertEqual(vpc_data['subnet_count'], 4)
        self.assertEqual(vpc_data['interface_count'], 8)
        self.assertEqual(vpc_data['region'], 'us-east-1')
        
        # Check new Flow Logs fields are present
        self.assertEqual(vpc_data['flow_logs_status'], 'Enabled')
        self.assertEqual(vpc_data['flow_logs_destinations'], ['CloudWatch'])
        self.assertEqual(vpc_data['flow_logs_retention'], '30 days')

    def test_generate_markdown_with_flow_logs(self):
        """Test that markdown generation includes Flow Logs columns."""
        # Sample VPC data with Flow Logs information
        vpc_data_list = [{
            'vpc_id': 'vpc-12345678',
            'vpc_name': 'Test-VPC',
            'vpc_cidr': '10.0.0.0/16',
            'is_default': False,
            'igw_present': True,
            'natgw_count': 2,
            'subnet_count': 4,
            'interface_count': 8,
            'region': 'us-east-1',
            'account_name': 'test-account',
            'account_id': '123456789012',
            'flow_logs_status': 'Enabled',
            'flow_logs_destinations': ['CloudWatch'],
            'flow_logs_retention': '30 days'
        }]
        
        account_regions = [{
            'account_name': 'test-account',
            'account_id': '123456789012',
            'region': 'us-east-1'
        }]
        
        # Generate markdown
        result = generate_markdown(vpc_data_list, account_regions)
        
        # Verify Flow Logs columns are present in the table header
        self.assertIn('Flow Logs', result)
        self.assertIn('Destination', result)
        self.assertIn('Retention', result)
        
        # Verify Flow Logs data is present in the table row
        self.assertIn('Enabled', result)
        self.assertIn('CloudWatch', result)
        self.assertIn('30 days', result)
        
        # Verify Flow Logs summary section is present
        self.assertIn('Flow Logs Coverage Summary', result)
        self.assertIn('Overall Statistics', result)
        self.assertIn('Total VPCs', result)
        self.assertIn('VPCs with Flow Logs', result)
        self.assertIn('By Account', result)

    def test_markdown_generation_with_no_flow_logs(self):
        """Test markdown generation with VPCs that have no Flow Logs."""
        vpc_data_list = [{
            'vpc_id': 'vpc-87654321',
            'vpc_name': 'No-Logs-VPC',
            'vpc_cidr': '10.1.0.0/16',
            'is_default': False,
            'igw_present': False,
            'natgw_count': 0,
            'subnet_count': 2,
            'interface_count': 3,
            'region': 'us-west-2',
            'account_name': 'test-account',
            'account_id': '123456789012',
            'flow_logs_status': 'Disabled',
            'flow_logs_destinations': [],
            'flow_logs_retention': 'N/A'
        }]
        
        account_regions = [{
            'account_name': 'test-account',
            'account_id': '123456789012',
            'region': 'us-west-2'
        }]
        
        result = generate_markdown(vpc_data_list, account_regions)
        
        # Verify disabled Flow Logs are properly displayed
        self.assertIn('Disabled', result)
        self.assertIn('| - |', result)  # Empty destination
        self.assertIn('N/A', result)    # N/A retention
        
        # Verify summary shows 0% coverage
        self.assertIn('1 (100.0%)', result)  # VPCs without Flow Logs

    def test_markdown_generation_with_mixed_flow_logs(self):
        """Test markdown generation with mixed Flow Logs configurations."""
        vpc_data_list = [
            {
                'vpc_id': 'vpc-enabled',
                'vpc_name': 'Enabled-VPC',
                'vpc_cidr': '10.0.0.0/16',
                'is_default': False,
                'igw_present': True,
                'natgw_count': 1,
                'subnet_count': 3,
                'interface_count': 5,
                'region': 'us-east-1',
                'account_name': 'prod',
                'account_id': '123456789012',
                'flow_logs_status': 'Enabled',
                'flow_logs_destinations': ['S3'],
                'flow_logs_retention': 'N/A'
            },
            {
                'vpc_id': 'vpc-disabled',
                'vpc_name': 'Disabled-VPC',
                'vpc_cidr': '10.1.0.0/16',
                'is_default': True,
                'igw_present': True,
                'natgw_count': 0,
                'subnet_count': 6,
                'interface_count': 2,
                'region': 'us-east-1',
                'account_name': 'prod',
                'account_id': '123456789012',
                'flow_logs_status': 'Disabled',
                'flow_logs_destinations': [],
                'flow_logs_retention': 'N/A'
            }
        ]
        
        account_regions = [{
            'account_name': 'prod',
            'account_id': '123456789012',
            'region': 'us-east-1'
        }]
        
        result = generate_markdown(vpc_data_list, account_regions)
        
        # Verify both VPCs are displayed with correct Flow Logs status
        self.assertIn('Enabled-VPC', result)
        self.assertIn('Disabled-VPC', result)
        self.assertIn('Enabled', result)
        self.assertIn('Disabled', result)
        self.assertIn('S3', result)
        
        # Verify summary shows 50% coverage
        self.assertIn('1 (50.0%)', result)  # VPCs with Flow Logs
        self.assertIn('1 (50.0%)', result)  # VPCs without Flow Logs


if __name__ == '__main__':
    unittest.main()