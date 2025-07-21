#!/usr/bin/env python3
"""
Test script for VPC Detective with real AWS environment.

This script helps you test the enhanced VPC Detective tool against
your actual AWS infrastructure safely.
"""

import json
import sys
import os
from datetime import datetime

# Import the VPC Detective functions
import importlib.util
spec = importlib.util.spec_from_file_location("vpc_detective", "vpc-detective.py")
vpc_detective = importlib.util.module_from_spec(spec)
sys.modules["vpc_detective"] = vpc_detective
spec.loader.exec_module(vpc_detective)

from vpc_detective import get_vpcs, generate_markdown


def test_single_region():
    """Test VPC Detective against a single region to verify functionality."""
    print("🧪 Testing VPC Detective with real AWS environment...")
    print("=" * 60)
    
    # Check if test configuration exists
    config_file = 'account-list-test.json'
    if not os.path.exists(config_file):
        print(f"❌ Configuration file '{config_file}' not found!")
        print("Please create this file with your AWS account details.")
        print("You can copy from account-list.example.json and modify.")
        return False
    
    try:
        # Load test configuration
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print(f"📋 Configuration loaded from {config_file}")
        print(f"🔐 SSO URL: {config['SSO']['start_url']}")
        print(f"📊 Testing {len(config['Accounts'])} account(s)")
        
        # Test with first account and region only
        account = config['Accounts'][0]
        account_name = account['name']
        account_id = account['id']
        role_name = account['role_name']
        
        # Get first region
        if 'regions' in account:
            region = account['regions'][0]
        else:
            region = account['region']
        
        print(f"\n🎯 Testing Account: {account_name} ({account_id})")
        print(f"🌍 Testing Region: {region}")
        print(f"👤 Using Role: {role_name}")
        
        # Import AWS SSO library
        from aws_sso_lib import get_boto3_session
        
        # Create SSO session
        print("\n🔑 Authenticating with AWS SSO...")
        boto3_sso_session = get_boto3_session(
            config['SSO']['start_url'],
            config['SSO']['region'],
            account_id, 
            role_name,
            region=config['SSO']['region'],
            login=True
        )
        
        # Create clients
        print("🔧 Creating AWS clients...")
        ec2_client = boto3_sso_session.client('ec2', region_name=region)
        logs_client = boto3_sso_session.client('logs', region_name=region)
        
        # Test VPC detection
        print("🔍 Scanning VPCs...")
        vpc_list = get_vpcs(ec2_client, logs_client)
        
        # Add account info
        for vpc in vpc_list:
            vpc['account_name'] = account_name
            vpc['account_id'] = account_id
        
        print(f"✅ Found {len(vpc_list)} VPC(s)")
        
        # Display results
        if vpc_list:
            print("\n📊 VPC Summary:")
            print("-" * 80)
            for vpc in vpc_list:
                print(f"VPC: {vpc['vpc_name']} ({vpc['vpc_id']})")
                print(f"  CIDR: {vpc['vpc_cidr']}")
                print(f"  Flow Logs: {vpc['flow_logs_status']}")
                if vpc['flow_logs_destinations']:
                    print(f"  Destinations: {', '.join(vpc['flow_logs_destinations'])}")
                print(f"  Retention: {vpc['flow_logs_retention']}")
                print()
        else:
            print("ℹ️  No VPCs found in this region")
        
        # Test markdown generation
        print("📝 Testing markdown generation...")
        account_regions = [{
            'account_name': account_name,
            'account_id': account_id,
            'region': region
        }]
        
        markdown_content = generate_markdown(vpc_list, account_regions)
        
        # Save test output
        test_output_file = f'vpc-test-output-{datetime.now().strftime("%Y%m%d-%H%M%S")}.md'
        with open(test_output_file, 'w') as f:
            f.write(markdown_content)
        
        print(f"✅ Test output saved to: {test_output_file}")
        
        # Clean up
        ec2_client.close()
        logs_client.close()
        
        print("\n🎉 Test completed successfully!")
        print(f"📄 Review the output file: {test_output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Verify your AWS SSO configuration")
        print("2. Check your account ID and role name")
        print("3. Ensure you have the required permissions:")
        print("   - ec2:DescribeVpcs")
        print("   - ec2:DescribeSubnets")
        print("   - ec2:DescribeInternetGateways")
        print("   - ec2:DescribeNatGateways")
        print("   - ec2:DescribeNetworkInterfaces")
        print("   - ec2:DescribeFlowLogs")
        print("   - logs:DescribeLogGroups")
        return False


def test_permissions():
    """Test if the required AWS permissions are available."""
    print("🔐 Testing AWS Permissions...")
    print("=" * 40)
    
    # This would require actual AWS setup
    print("To test permissions, run the main application with:")
    print("python vpc-detective.py")
    print("\nIf you see permission errors, you'll need to add:")
    print("- ec2:DescribeFlowLogs")
    print("- logs:DescribeLogGroups")


if __name__ == '__main__':
    print("🕵️ VPC Detective - Real AWS Testing")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--permissions':
        test_permissions()
    else:
        success = test_single_region()
        if success:
            print("\n✅ Your enhanced VPC Detective is working correctly!")
            print("You can now run the full application with:")
            print("python vpc-detective.py")
        else:
            print("\n❌ Please fix the issues above and try again.")
            sys.exit(1)