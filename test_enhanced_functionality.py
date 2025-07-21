#!/usr/bin/env python3
"""
Simple test script to verify the enhanced VPC Detective functionality.

This script tests the new Flow Logs detection without requiring actual AWS credentials.
"""

from unittest.mock import Mock, patch
import sys
import importlib.util
spec = importlib.util.spec_from_file_location("vpc_detective", "vpc-detective.py")
vpc_detective = importlib.util.module_from_spec(spec)
sys.modules["vpc_detective"] = vpc_detective
spec.loader.exec_module(vpc_detective)

from vpc_detective import get_vpc_flow_logs, get_cloudwatch_retention, calculate_flow_logs_summary


def test_flow_logs_basic_functionality():
    """Test basic Flow Logs functionality with mocked AWS responses."""
    print("Testing Flow Logs detection functionality...")
    
    # Test 1: VPC with no Flow Logs
    print("\n1. Testing VPC with no Flow Logs...")
    mock_ec2_client = Mock()
    mock_logs_client = Mock()
    
    mock_paginator = Mock()
    mock_paginator.paginate.return_value = [{'FlowLogs': []}]
    mock_ec2_client.get_paginator.return_value = mock_paginator
    
    result = get_vpc_flow_logs(mock_ec2_client, mock_logs_client, 'vpc-test1')
    print(f"Result: {result}")
    assert result['status'] == 'Disabled'
    assert result['destinations'] == []
    assert result['retention_days'] == 'N/A'
    print("✓ PASSED")
    
    # Test 2: VPC with CloudWatch Flow Logs
    print("\n2. Testing VPC with CloudWatch Flow Logs...")
    flow_log = {
        'FlowLogStatus': 'ACTIVE',
        'LogDestinationType': 'cloud-watch-logs',
        'LogGroupName': '/aws/vpc/flowlogs'
    }
    mock_paginator.paginate.return_value = [{'FlowLogs': [flow_log]}]
    
    # Mock CloudWatch retention
    mock_logs_client.describe_log_groups.return_value = {
        'logGroups': [{
            'logGroupName': '/aws/vpc/flowlogs',
            'retentionInDays': 30
        }]
    }
    
    result = get_vpc_flow_logs(mock_ec2_client, mock_logs_client, 'vpc-test2')
    print(f"Result: {result}")
    assert result['status'] == 'Enabled'
    assert result['destinations'] == ['CloudWatch']
    assert result['retention_days'] == '30 days'
    print("✓ PASSED")
    
    # Test 3: Summary calculation
    print("\n3. Testing Flow Logs summary calculation...")
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
            'flow_logs_status': 'Multiple'
        }
    ]
    
    summary = calculate_flow_logs_summary(vpc_data)
    print(f"Summary: {summary}")
    assert summary['total_vpcs'] == 3
    assert summary['vpcs_with_flow_logs'] == 2
    assert summary['vpcs_without_flow_logs'] == 1
    assert abs(summary['coverage_percentage'] - 66.7) < 0.1
    print("✓ PASSED")
    
    print("\n✅ All tests passed! Flow Logs functionality is working correctly.")


def test_error_handling():
    """Test error handling in Flow Logs detection."""
    print("\nTesting error handling...")
    
    import botocore.exceptions
    
    mock_ec2_client = Mock()
    mock_logs_client = Mock()
    
    # Test access denied error
    error = botocore.exceptions.ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
        'DescribeFlowLogs'
    )
    mock_ec2_client.get_paginator.side_effect = error
    
    with patch('builtins.print'):  # Suppress error output for test
        result = get_vpc_flow_logs(mock_ec2_client, mock_logs_client, 'vpc-error')
    
    print(f"Error handling result: {result}")
    assert result['status'] == 'Error'
    assert result['destinations'] == []
    assert result['retention_days'] == 'N/A'
    print("✓ Error handling works correctly")


if __name__ == '__main__':
    test_flow_logs_basic_functionality()
    test_error_handling()
    print("\n🎉 All functionality tests completed successfully!")
    print("\nThe enhanced VPC Detective is ready to use with Flow Logs detection!")
    print("\nTo use the enhanced tool:")
    print("1. Ensure your AWS credentials have the required permissions:")
    print("   - ec2:DescribeFlowLogs")
    print("   - logs:DescribeLogGroups")
    print("2. Run: python vpc-detective.py")
    print("3. Check the generated vpc-documentation.md for Flow Logs information")