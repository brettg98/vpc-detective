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


def get_vpcs(client):
    vpc_list = []
    all_vpcs = []
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

                vpc_data = {
                    'vpc_id': vpc_id,
                    'vpc_name': vpc_name,
                    'vpc_cidr': vpc_cidr,
                    'is_default': is_default,
                    'igw_present': igw_present,
                    'natgw_count': natgw_count,
                    'subnet_count': subnet_count,
                    'interface_count': interface_count,
                    'region': client.meta.region_name
                }
                vpc_list.append(vpc_data)
        return vpc_list
    except botocore.exceptions.ClientError as error:
        raise error


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
            markdown_content += "| VPC Name | VPC ID | CIDR Block | Default | IGW | NAT GWs | Subnets | Interfaces |\n"
            markdown_content += "|---------|--------|------------|---------|-----|---------|--------|---|\n"
            
            if not vpcs:
                markdown_content += "| *No VPCs found* | - | - | - | - | - | - | - |\n"
            else:
                # Add VPCs to the table
                for vpc in vpcs:
                    vpc_name = vpc['vpc_name']
                    is_default = 'Yes' if vpc['is_default'] else 'No'
                    igw_present = 'Yes' if vpc['igw_present'] else 'No'
                    
                    markdown_content += f"| {vpc_name} | {vpc['vpc_id']} | {vpc['vpc_cidr']} | {is_default} | {igw_present} | {vpc['natgw_count']} | {vpc['subnet_count']} | {vpc['interface_count']} |\n"
            
            markdown_content += "\n"
        
    return markdown_content


def main():
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
                
                # Create regional client
                client = boto3_sso_session.client('ec2', region_name=region)
                
                try:
                    vpc_list = get_vpcs(client)
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

    # Generate and save the markdown documentation
    markdown_content = generate_markdown(all_vpcs, account_regions)
    with open('vpc-documentation.md', 'w') as f:
        f.write(markdown_content)
    
    print(f"\nVPC documentation has been generated in vpc-documentation.md")


if __name__ == "__main__":
    main()
