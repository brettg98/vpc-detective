#!/usr/bin/env python3
"""
Unit tests for VPC Flow Logs detection functionality in VPC Detective.

These tests cover the new Flow Logs detection functions and ensure proper
error handling and data processing.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import botocore.exceptions
import sys
import importlib.util
spec = importlib.util.spec_from_file_location("vpc_detective", "vpc-detective.py")
vpc_detective = importlib.util.module_from_spec(spec)
sys.modules["vpc_detective"] = vpc_detective
spec.loader.exec_module(vpc_detective)

from vpc_detective import get_vpc_flow_logs, get_cloudwatch_retention, calculate_flow_logs_summary


class TestFlowLogsDetection(unittest.TestCase):
    """Test cases for Flow Logs detection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_ec2_client = Mock()
        self.mock_logs_client = Mock()
        self.vpc_id = 'vpc-12345678'

    def test_get_vpc_flow_logs_disabled(self):
        """Test VPC with no Flow Logs configured."""
        # Mock paginator with no flow logs
        mock_paginator = Mock()
        mock_page_iterator = [{'FlowLogs': []}]
        mock_paginator.paginate.return_value = mock_page_iterator
        self.mock_ec2_client.get_paginator.return_value = mock_paginator

        result = get_vpc_flow_logs(self.mock_ec2_client, self.mock_logs_client, self.vpc_id)

        expected = {
            'status': 'Disabled',
            'destinations': [],
            'retention_days': 'N/A'
        }
        self.assertEqual(result, expected)

    def test_get_vpc_flow_logs_single_cloudwatch(self):
        """Test VPC with single Flow Logs to CloudWatch."""
        # Mock flow logs response
        flow_log = {
            'FlowLogStatus': 'ACTIVE',
            'LogDestinationType': 'cloud-watch-logs',
            'LogGroupName': '/aws/vpc/flowlogs'
        }
        mock_paginator = Mock()
        mock_page_iterator = [{'FlowLogs': [flow_log]}]
        mock_paginator.paginate.return_value = mock_page_iterator
        self.mock_ec2_client.get_paginator.return_value = mock_paginator

        # Mock CloudWatch logs response
        self.mock_logs_client.describe_log_groups.return_value = {
            'logGroups': [{
                'logGroupName': '/aws/vpc/flowlogs',
                'retentionInDays': 30
            }]
        }

        result = get_vpc_flow_logs(self.mock_ec2_client, self.mock_logs_client, self.vpc_id)

        expected = {
            'status': 'Enabled',
            'destinations': ['CloudWatch'],
            'retention_days': '30 days'
        }
        self.assertEqual(result, expected)

    def test_get_vpc_flow_logs_single_s3(self):
        """Test VPC with single Flow Logs to S3."""
        flow_log = {
            'FlowLogStatus': 'ACTIVE',
            'LogDestinationType': 's3'
        }
        mock_paginator = Mock()
        mock_page_iterator = [{'FlowLogs': [flow_log]}]
        mock_paginator.paginate.return_value = mock_page_iterator
        self.mock_ec2_client.get_paginator.return_value = mock_paginator

        result = get_vpc_flow_logs(self.mock_ec2_client, self.mock_logs_client, self.vpc_id)

        expected = {
            'status': 'Enabled',
            'destinations': ['S3'],
            'retention_days': 'N/A'
        }
        self.assertEqual(result, expected)

    def test_get_vpc_flow_logs_single_kinesis(self):
        """Test VPC with single Flow Logs to Kinesis."""
        flow_log = {
            'FlowLogStatus': 'ACTIVE',
            'LogDestinationType': 'kinesis-data-firehose'
        }
        mock_paginator = Mock()
        mock_page_iterator = [{'FlowLogs': [flow_log]}]
        mock_paginator.paginate.return_value = mock_page_iterator
        self.mock_ec2_client.get_paginator.return_value = mock_paginator

        result = get_vpc_flow_logs(self.mock_ec2_client, self.mock_logs_client, self.vpc_id)

        expected = {
            'status': 'Enabled',
            'destinations': ['Kinesis'],
            'retention_days': 'N/A'
        }
        self.assertEqual(result, expected)

    def test_get_vpc_flow_logs_multiple_destinations(self):
        """Test VPC with multiple Flow Logs to different destinations."""
        flow_logs = [
            {
                'FlowLogStatus': 'ACTIVE',
                'LogDestinationType': 'cloud-watch-logs',
                'LogGroupName': '/aws/vpc/flowlogs'
            },
            {
                'FlowLogStatus': 'ACTIVE',
                'LogDestinationType': 's3'
            }
        ]
        mock_paginator = Mock()
        mock_page_iterator = [{'FlowLogs': flow_logs}]
        mock_paginator.paginate.return_value = mock_page_iterator
        self.mock_ec2_client.get_paginator.return_value = mock_paginator

        # Mock CloudWatch logs response
        self.mock_logs_client.describe_log_groups.return_value = {
            'logGroups': [{
                'logGroupName': '/aws/vpc/flowlogs',
                'retentionInDays': 90
            }]
        }

        result = get_vpc_flow_logs(self.mock_ec2_client, self.mock_logs_client, self.vpc_id)

        expected = {
            'status': 'Multiple',
            'destinations': ['CloudWatch', 'S3'],
            'retention_days': '90 days'
        }
        self.assertEqual(result, expected)

    def test_get_vpc_flow_logs_access_denied(self):
        """Test Flow Logs API access denied error handling."""
        error = botocore.exceptions.ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'DescribeFlowLogs'
        )
        self.mock_ec2_client.get_paginator.side_effect = error

        with patch('builtins.print') as mock_print:
            result = get_vpc_flow_logs(self.mock_ec2_client, self.mock_logs_client, self.vpc_id)

        expected = {
            'status': 'Error',
            'destinations': [],
            'retention_days': 'N/A'
        }
        self.assertEqual(result, expected)
        mock_print.assert_called()

    def test_get_vpc_flow_logs_other_error(self):
        """Test Flow Logs API other error handling."""
        error = botocore.exceptions.ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'Internal error'}},
            'DescribeFlowLogs'
        )
        self.mock_ec2_client.get_paginator.side_effect = error

        with patch('builtins.print') as mock_print:
            result = get_vpc_flow_logs(self.mock_ec2_client, self.mock_logs_client, self.vpc_id)

        expected = {
            'status': 'Error',
            'destinations': [],
            'retention_days': 'N/A'
        }
        self.assertEqual(result, expected)
        mock_print.assert_called()


class TestCloudWatchRetention(unittest.TestCase):
    """Test cases for CloudWatch retention detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_logs_client = Mock()
        self.log_group_name = '/aws/vpc/flowlogs'

    def test_get_cloudwatch_retention_with_days(self):
        """Test log group with retention period set."""
        response = {
            'logGroups': [{
                'logGroupName': '/aws/vpc/flowlogs',
                'retentionInDays': 30
            }]
        }
        self.mock_logs_client.describe_log_groups.return_value = response

        result = get_cloudwatch_retention(self.mock_logs_client, self.log_group_name)
        self.assertEqual(result, '30 days')

    def test_get_cloudwatch_retention_never_expire(self):
        """Test log group with no retention (never expire)."""
        response = {
            'logGroups': [{
                'logGroupName': '/aws/vpc/flowlogs'
                # No retentionInDays key means never expire
            }]
        }
        self.mock_logs_client.describe_log_groups.return_value = response

        result = get_cloudwatch_retention(self.mock_logs_client, self.log_group_name)
        self.assertEqual(result, 'Never')

    def test_get_cloudwatch_retention_not_found(self):
        """Test log group not found."""
        response = {'logGroups': []}
        self.mock_logs_client.describe_log_groups.return_value = response

        result = get_cloudwatch_retention(self.mock_logs_client, self.log_group_name)
        self.assertEqual(result, 'N/A')

    def test_get_cloudwatch_retention_access_denied(self):
        """Test CloudWatch Logs access denied."""
        error = botocore.exceptions.ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'DescribeLogGroups'
        )
        self.mock_logs_client.describe_log_groups.side_effect = error

        with patch('builtins.print') as mock_print:
            result = get_cloudwatch_retention(self.mock_logs_client, self.log_group_name)

        self.assertEqual(result, 'N/A')
        mock_print.assert_called()

    def test_get_cloudwatch_retention_other_error(self):
        """Test CloudWatch Logs other error."""
        error = botocore.exceptions.ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'Internal error'}},
            'DescribeLogGroups'
        )
        self.mock_logs_client.describe_log_groups.side_effect = error

        with patch('builtins.print') as mock_print:
            result = get_cloudwatch_retention(self.mock_logs_client, self.log_group_name)

        self.assertEqual(result, 'N/A')
        mock_print.assert_called()


class TestFlowLogsSummary(unittest.TestCase):
    """Test cases for Flow Logs summary calculations."""

    def test_calculate_flow_logs_summary_empty_list(self):
        """Test summary calculation with empty VPC list."""
        result = calculate_flow_logs_summary([])
        
        expected = {
            'total_vpcs': 0,
            'vpcs_with_flow_logs': 0,
            'vpcs_without_flow_logs': 0,
            'coverage_percentage': 0.0,
            'by_account': {}
        }
        self.assertEqual(result, expected)

    def test_calculate_flow_logs_summary_all_enabled(self):
        """Test summary calculation with all VPCs having Flow Logs."""
        vpc_data = [
            {
                'account_name': 'prod',
                'account_id': '123456789012',
                'flow_logs_status': 'Enabled'
            },
            {
                'account_name': 'prod',
                'account_id': '123456789012',
                'flow_logs_status': 'Multiple'
            }
        ]
        
        result = calculate_flow_logs_summary(vpc_data)
        
        self.assertEqual(result['total_vpcs'], 2)
        self.assertEqual(result['vpcs_with_flow_logs'], 2)
        self.assertEqual(result['vpcs_without_flow_logs'], 0)
        self.assertEqual(result['coverage_percentage'], 100.0)
        
        account_key = 'prod (123456789012)'
        self.assertIn(account_key, result['by_account'])
        self.assertEqual(result['by_account'][account_key]['total'], 2)
        self.assertEqual(result['by_account'][account_key]['enabled'], 2)
        self.assertEqual(result['by_account'][account_key]['disabled'], 0)
        self.assertEqual(result['by_account'][account_key]['percentage'], 100.0)

    def test_calculate_flow_logs_summary_mixed(self):
        """Test summary calculation with mixed Flow Logs status."""
        vpc_data = [
            {
                'account_name': 'prod',
                'account_id': '123456789012',
                'flow_logs_status': 'Enabled'
            },
            {
                'account_name': 'prod',
                'account_id': '123456789012',
                'flow_logs_status': 'Disabled'
            },
            {
                'account_name': 'dev',
                'account_id': '210987654321',
                'flow_logs_status': 'Error'
            }
        ]
        
        result = calculate_flow_logs_summary(vpc_data)
        
        self.assertEqual(result['total_vpcs'], 3)
        self.assertEqual(result['vpcs_with_flow_logs'], 1)
        self.assertEqual(result['vpcs_without_flow_logs'], 2)
        self.assertAlmostEqual(result['coverage_percentage'], 33.3, places=1)
        
        # Check per-account statistics
        prod_key = 'prod (123456789012)'
        dev_key = 'dev (210987654321)'
        
        self.assertEqual(result['by_account'][prod_key]['total'], 2)
        self.assertEqual(result['by_account'][prod_key]['enabled'], 1)
        self.assertEqual(result['by_account'][prod_key]['percentage'], 50.0)
        
        self.assertEqual(result['by_account'][dev_key]['total'], 1)
        self.assertEqual(result['by_account'][dev_key]['enabled'], 0)
        self.assertEqual(result['by_account'][dev_key]['percentage'], 0.0)

    def test_calculate_flow_logs_summary_multiple_accounts(self):
        """Test summary calculation with multiple accounts."""
        vpc_data = [
            {
                'account_name': 'production',
                'account_id': '123456789012',
                'flow_logs_status': 'Enabled'
            },
            {
                'account_name': 'production',
                'account_id': '123456789012',
                'flow_logs_status': 'Enabled'
            },
            {
                'account_name': 'development',
                'account_id': '210987654321',
                'flow_logs_status': 'Disabled'
            }
        ]
        
        result = calculate_flow_logs_summary(vpc_data)
        
        self.assertEqual(result['total_vpcs'], 3)
        self.assertEqual(result['vpcs_with_flow_logs'], 2)
        self.assertAlmostEqual(result['coverage_percentage'], 66.7, places=1)
        
        prod_key = 'production (123456789012)'
        dev_key = 'development (210987654321)'
        
        self.assertEqual(result['by_account'][prod_key]['percentage'], 100.0)
        self.assertEqual(result['by_account'][dev_key]['percentage'], 0.0)


if __name__ == '__main__':
    unittest.main()