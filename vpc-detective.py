import json
from os import wait
import boto3
import botocore
from datetime import datetime
from aws_sso_lib import get_boto3_session


def print_banner(return_banner=False):
    banner = r"""

██╗   ██╗██████╗  ██████╗██████╗ ███████╗████████╗███████╗ ██████╗████████╗██╗██╗   ██╗███████╗
██║   ██║██╔══██╗██╔════╝██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝██║██║   ██║██╔════╝
██║   ██║██████╔╝██║     ██║  ██║█████╗     ██║   █████╗  ██║        ██║   ██║██║   ██║█████╗  
╚██╗ ██╔╝██╔═══╝ ██║     ██║  ██║██╔══╝     ██║   ██╔══╝  ██║        ██║   ██║╚██╗ ██╔╝██╔══╝  
 ╚████╔╝ ██║     ╚██████╗██████╔╝███████╗   ██║   ███████╗╚██████╗   ██║   ██║ ╚████╔╝ ███████╗
  ╚═══╝  ╚═╝      ╚═════╝╚═════╝ ╚══════╝   ╚═╝   ╚══════╝ ╚═════╝   ╚═╝   ╚═╝  ╚═══╝  ╚══════╝
    Sniffing out your subnets since 2025 
    """
    if return_banner:
        return banner
    print(banner)


def get_interface_count(client, vpc_id):
    interface_count = 0
    try:
        paginator = client.get_paginator('describe_network_interfaces')
        page_iterator = paginator.paginate(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [vpc_id]
                }
            ]
        )
        for page in page_iterator:
            interface_count += len(page['NetworkInterfaces'])
    except botocore.exceptions.ClientError as error:
        raise error
    return interface_count


def get_vpc_subnets(client, vpc_id):
    subnet_count = 0
    try:
        paginator = client.get_paginator('describe_subnets')
        page_iterator = paginator.paginate(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [vpc_id]
                }
            ]
        )
        for page in page_iterator:
            subnet_count = len(page['Subnets'])
    except botocore.exceptions.ClientError as error:
        raise error
    return subnet_count


def get_natgws(client, vpc_id):
    natgw_count = 0
    try:
        paginator = client.get_paginator('describe_nat_gateways')
        page_iterator = paginator.paginate(
            Filters = [
                {
                    'Name': 'vpc-id',
                    'Values': [vpc_id]
                }
            ]
        )
        for page in page_iterator:
            natgw_count = len(page['NatGateways'])
    except botocore.exceptions.ClientError as error:
        raise error
    return natgw_count


def get_vpc_igw(client, vpc_id):
    try:
        response = client.describe_internet_gateways(
            Filters=[
                {
                    'Name': 'attachment.vpc-id',
                    'Values': [vpc_id]
                }
            ]
        )
        if len(response['InternetGateways']) > 0:
            return True
        else:
            return False
    except botocore.exceptions.ClientError as error:
        raise error


def get_cloudwatch_retention(logs_client, log_group_name):
    """
    Get retention period for CloudWatch Log Group.
    
    Required IAM permission: logs:DescribeLogGroups
    
    Args:
        logs_client: CloudWatch Logs boto3 client
        log_group_name: Log group name string
        
    Returns:
        str: Retention period ('30 days', 'Never', 'N/A')
    """
    try:
        response = logs_client.describe_log_groups(
            logGroupNamePrefix=log_group_name,
            limit=1
        )
        
        if response['logGroups']:
            log_group = response['logGroups'][0]
            if log_group['logGroupName'] == log_group_name:
                retention_days = log_group.get('retentionInDays')
                if retention_days:
                    return f"{retention_days} days"
                else:
                    return "Never"
        
        return "N/A"
        
    except botocore.exceptions.ClientError as error:
        error_code = error.response['Error']['Code']
        if error_code in ['AccessDenied', 'UnauthorizedOperation']:
            print(f"    Warning: No CloudWatch Logs permissions for log group {log_group_name}")
        else:
            print(f"    Error getting retention for log group {log_group_name}: {error}")
        return "N/A"


def get_vpc_flow_logs(ec2_client, logs_client, vpc_id):
    """
    Retrieve Flow Logs configuration for a specific VPC.
    
    Required IAM permissions: 
    - ec2:DescribeFlowLogs
    - logs:DescribeLogGroups (for CloudWatch destinations)
    
    Args:
        ec2_client: EC2 boto3 client
        logs_client: CloudWatch Logs boto3 client  
        vpc_id: VPC identifier string
        
    Returns:
        dict: Flow Logs information
        {
            'status': 'Enabled|Disabled|Multiple|Error',
            'destinations': ['CloudWatch', 'S3', 'Kinesis'],
            'retention_days': str
        }
    """
    try:
        paginator = ec2_client.get_paginator('describe_flow_logs')
        page_iterator = paginator.paginate(
            Filters=[
                {'Name': 'resource-id', 'Values': [vpc_id]},
                {'Name': 'resource-type', 'Values': ['VPC']}
            ]
        )
        
        flow_logs = []
        for page in page_iterator:
            flow_logs.extend(page['FlowLogs'])
        
        # Filter for active flow logs only
        active_flow_logs = [fl for fl in flow_logs if fl['FlowLogStatus'] == 'ACTIVE']
        
        if not active_flow_logs:
            return {
                'status': 'Disabled',
                'destinations': [],
                'retention_days': 'N/A'
            }
        
        # Determine destinations and status
        destinations = set()
        retention_periods = []
        
        for flow_log in active_flow_logs:
            destination_type = flow_log['LogDestinationType']
            
            if destination_type == 'cloud-watch-logs':
                destinations.add('CloudWatch')
                # Get retention for CloudWatch destinations
                log_group_name = flow_log['LogGroupName']
                retention = get_cloudwatch_retention(logs_client, log_group_name)
                if retention != 'N/A':
                    retention_periods.append(retention)
                    
            elif destination_type == 's3':
                destinations.add('S3')
                
            elif destination_type == 'kinesis-data-firehose':
                destinations.add('Kinesis')
        
        # Determine status
        if len(active_flow_logs) == 1:
            status = 'Enabled'
        else:
            status = 'Multiple'
        
        # Determine retention (shortest period for CloudWatch, N/A for others)
        if retention_periods:
            # Find shortest retention period
            retention_days_list = []
            for period in retention_periods:
                if period == 'Never':
                    retention_days_list.append(float('inf'))
                else:
                    days = int(period.split()[0])
                    retention_days_list.append(days)
            
            min_retention = min(retention_days_list)
            if min_retention == float('inf'):
                retention_result = 'Never'
            else:
                retention_result = f"{int(min_retention)} days"
        else:
            retention_result = 'N/A'
        
        return {
            'status': status,
            'destinations': sorted(list(destinations)),
            'retention_days': retention_result
        }
        
    except botocore.exceptions.ClientError as error:
        error_code = error.response['Error']['Code']
        if error_code in ['AccessDenied', 'UnauthorizedOperation']:
            print(f"    Warning: No Flow Logs permissions for VPC {vpc_id}")
        else:
            print(f"    Error getting Flow Logs for VPC {vpc_id}: {error}")
        
        return {
            'status': 'Error',
            'destinations': [],
            'retention_days': 'N/A'
        }


def get_vpcs(client, logs_client):
    vpc_list = []
    try:
        paginator = client.get_paginator('describe_vpcs')
        for page in paginator.paginate():
            for vpc_info in page['Vpcs']:
                vpc_id = vpc_info['VpcId']
                vpc_cidr = vpc_info['CidrBlock']
                is_default = vpc_info['IsDefault']
                tags = vpc_info.get('Tags', [])
                vpc_name = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), 'Unnamed')

                # additional information
                igw_present = get_vpc_igw(client, vpc_id)
                subnet_count = get_vpc_subnets(client, vpc_id)
                natgw_count = get_natgws(client, vpc_id)
                interface_count = get_interface_count(client, vpc_id)
                
                # Flow Logs information
                flow_logs_data = get_vpc_flow_logs(client, logs_client, vpc_id)

                vpc_data = {
                    'vpc_id': vpc_id,
                    'vpc_name': vpc_name,
                    'vpc_cidr': vpc_cidr,
                    'is_default': is_default,
                    'igw_present': igw_present,
                    'natgw_count': natgw_count,
                    'subnet_count': subnet_count,
                    'interface_count': interface_count,
                    'region': client.meta.region_name,
                    'flow_logs_status': flow_logs_data['status'],
                    'flow_logs_destinations': flow_logs_data['destinations'],
                    'flow_logs_retention': flow_logs_data['retention_days']
                }
                vpc_list.append(vpc_data)
        return vpc_list
    except botocore.exceptions.ClientError as error:
        raise error


def calculate_flow_logs_summary(vpc_data_list):
    """
    Calculate Flow Logs coverage statistics across all VPCs.
    
    Args:
        vpc_data_list: List of VPC data dictionaries
        
    Returns:
        dict: Summary statistics including overall and per-account breakdowns
    """
    if not vpc_data_list:
        return {
            'total_vpcs': 0,
            'vpcs_with_flow_logs': 0,
            'vpcs_without_flow_logs': 0,
            'coverage_percentage': 0.0,
            'by_account': {}
        }
    
    # Overall statistics
    total_vpcs = len(vpc_data_list)
    vpcs_with_flow_logs = len([vpc for vpc in vpc_data_list if vpc['flow_logs_status'] in ['Enabled', 'Multiple']])
    vpcs_without_flow_logs = total_vpcs - vpcs_with_flow_logs
    coverage_percentage = (vpcs_with_flow_logs / total_vpcs * 100) if total_vpcs > 0 else 0.0
    
    # Per-account statistics
    by_account = {}
    for vpc in vpc_data_list:
        account_key = f"{vpc['account_name']} ({vpc['account_id']})"
        
        if account_key not in by_account:
            by_account[account_key] = {
                'total': 0,
                'enabled': 0,
                'disabled': 0,
                'percentage': 0.0
            }
        
        by_account[account_key]['total'] += 1
        
        if vpc['flow_logs_status'] in ['Enabled', 'Multiple']:
            by_account[account_key]['enabled'] += 1
        else:
            by_account[account_key]['disabled'] += 1
    
    # Calculate percentages for each account
    for account_data in by_account.values():
        if account_data['total'] > 0:
            account_data['percentage'] = (account_data['enabled'] / account_data['total'] * 100)
    
    return {
        'total_vpcs': total_vpcs,
        'vpcs_with_flow_logs': vpcs_with_flow_logs,
        'vpcs_without_flow_logs': vpcs_without_flow_logs,
        'coverage_percentage': coverage_percentage,
        'by_account': by_account
    }


def generate_markdown(vpc_data_list, account_regions):
    # Get the ASCII art banner
    markdown_content = "# 🕵️ VPC Detective\n"
    markdown_content += "## 🔎 Sniffing out your subnets since 2025 🔎\n"
    markdown_content += f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    
    # Group by account and region
    by_account_region = {}
    
    # First, initialize the structure with all account/region combinations
    for ar in account_regions:
        account_key = f"{ar['account_name']} ({ar['account_id']})"
        if account_key not in by_account_region:
            by_account_region[account_key] = {}
        
        region = ar['region']
        if region not in by_account_region[account_key]:
            by_account_region[account_key][region] = []
    
    # Then populate with VPC data
    for vpc in vpc_data_list:
        account_key = f"{vpc['account_name']} ({vpc['account_id']})"
        region = vpc['region']
        by_account_region[account_key][region].append(vpc)
    
    # Generate markdown tables for each account and region
    for account, regions in by_account_region.items():
        markdown_content += f"## Account: {account}\n\n"
        
        for region, vpcs in regions.items():
            markdown_content += f"### Region: {region}\n\n"
            
            # Create main VPC table
            markdown_content += "| VPC Name | VPC ID | CIDR Block | Default | IGW | NAT GWs | Subnets | Interfaces | Flow Logs | Destination | Retention |\n"
            markdown_content += "|---------|--------|------------|---------|-----|---------|--------|------------|-----------|-------------|-----------||\n"
            
            if not vpcs:
                markdown_content += "| *No VPCs found* | - | - | - | - | - | - | - | - | - | - |\n"
            else:
                # Add VPCs to the table
                for vpc in vpcs:
                    vpc_name = vpc['vpc_name']
                    is_default = 'Yes' if vpc['is_default'] else 'No'
                    igw_present = 'Yes' if vpc['igw_present'] else 'No'
                    
                    # Format Flow Logs information
                    flow_logs_status = vpc['flow_logs_status']
                    flow_logs_destinations = ', '.join(vpc['flow_logs_destinations']) if vpc['flow_logs_destinations'] else '-'
                    flow_logs_retention = vpc['flow_logs_retention']
                    
                    markdown_content += f"| {vpc_name} | {vpc['vpc_id']} | {vpc['vpc_cidr']} | {is_default} | {igw_present} | {vpc['natgw_count']} | {vpc['subnet_count']} | {vpc['interface_count']} | {flow_logs_status} | {flow_logs_destinations} | {flow_logs_retention} |\n"
            
            markdown_content += "\n"
    
    # Add Flow Logs summary section
    flow_logs_summary = calculate_flow_logs_summary(vpc_data_list)
    
    markdown_content += "## Flow Logs Coverage Summary\n\n"
    
    # Overall statistics
    markdown_content += "### Overall Statistics\n"
    markdown_content += f"- **Total VPCs**: {flow_logs_summary['total_vpcs']}\n"
    markdown_content += f"- **VPCs with Flow Logs**: {flow_logs_summary['vpcs_with_flow_logs']} ({flow_logs_summary['coverage_percentage']:.1f}%)\n"
    markdown_content += f"- **VPCs without Flow Logs**: {flow_logs_summary['vpcs_without_flow_logs']} ({100 - flow_logs_summary['coverage_percentage']:.1f}%)\n\n"
    
    # Per-account statistics
    if flow_logs_summary['by_account']:
        markdown_content += "### By Account\n"
        for account_name, account_data in flow_logs_summary['by_account'].items():
            markdown_content += f"- **{account_name}**: {account_data['enabled']}/{account_data['total']} VPCs ({account_data['percentage']:.1f}%)\n"
        markdown_content += "\n"
        
    return markdown_content


def main():
    """
    Main function to scan VPCs across multiple AWS accounts and regions.
    
    Required IAM permissions:
    - ec2:DescribeVpcs
    - ec2:DescribeSubnets
    - ec2:DescribeInternetGateways
    - ec2:DescribeNatGateways
    - ec2:DescribeNetworkInterfaces
    - ec2:DescribeFlowLogs (for Flow Logs detection)
    - logs:DescribeLogGroups (for CloudWatch retention periods)
    """
    # Print the ASCII art banner
    print_banner()
    
    vpc_list = []
    all_vpcs = []
    account_regions = []  # Track all account/region combinations
    
    # Load the configuration file
    with open('./account-list.json') as account_file:
        data = json.load(account_file)
        aws_sso = data['SSO']

        for value in data['Accounts']:
            account_name = value['name']
            account_id = value['id']
            account_role_name = value['role_name']
            regions = value.get('regions', [value.get('region')])  # Support both old and new format

            print(f"\nProcessing account: {account_name} ({account_id})")
            
            # Create SSO session once per account
            boto3_sso_session = get_boto3_session(aws_sso['start_url'],
                                                aws_sso['region'],
                                                account_id, account_role_name,
                                                region=aws_sso['region'],  # Use SSO region for session
                                                login=True)

            # Process each region
            for region in regions:
                # Track this account/region combination
                account_regions.append({
                    'account_name': account_name,
                    'account_id': account_id,
                    'region': region
                })
                
                print(f"  Getting VPC information from region: {region}")
                
                # Create regional clients
                client = boto3_sso_session.client('ec2', region_name=region)
                logs_client = boto3_sso_session.client('logs', region_name=region)
                
                try:
                    vpc_list = get_vpcs(client, logs_client)
                    # Add account info to each VPC
                    for vpc in vpc_list:
                        vpc['account_name'] = account_name
                        vpc['account_id'] = account_id
                    all_vpcs.extend(vpc_list)
                except botocore.exceptions.ClientError as error:
                    print(f"  Error accessing region {region}: {str(error)}")
                    continue
                finally:
                    client.close()
                    logs_client.close()

    # Generate and save the markdown documentation
    markdown_content = generate_markdown(all_vpcs, account_regions)
    with open('vpc-documentation.md', 'w') as f:
        f.write(markdown_content)
    
    print(f"\nVPC documentation has been generated in vpc-documentation.md")


if __name__ == "__main__":
    main()
