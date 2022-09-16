#! /usr/bin/env python3

# Usage: create_vpn.py 10.2.0.0/22 [subnet_id]

import sys
import time

import boto3

if len(sys.argv) >= 2:
    vpn_cidr = sys.argv[1]
    subnet_id = None
if len(sys.argv) == 3:
    subnet_id = sys.argv[2]
if len(sys.argv) < 2 or len(sys.argv) > 3:
    print(f"Usage: {sys.argv[0]} cidr [subnet_id]" )
    sys.exit(0)

vpn_name = "vpn-endpoint"
cert_server = {"name": "vpn-server"}

vpn_id = None
sg_id = None

ec2 = boto3.client('ec2')

res = ec2.describe_subnets()
subnets = res["Subnets"]
if not subnet_id:
    print("Select the target subnet:")
    index = 1
    for subnet in subnets:
        name = ""
        if "Tags" in subnet:
            for tag in subnet["Tags"]:
                if tag["Key"] == "Name":
                    name = tag["Value"]
                    break
        print(f"  {index}: {subnet['SubnetId']} ({name} - {subnet['AvailabilityZone']})")
        index += 1
    print("Number: ", end='')
    try:
        index = int(input()) - 1
        subnet_id = subnets[index]['SubnetId']
        vpc_id = subnets[index]["VpcId"]
    except:
        sys.exit(1)
else:
    for subnet in subnets:
        if subnet['SubnetId'] == subnet_id:
            vpc_id = subnet["VpcId"]
            break
    else:
        print(f"Subnet '{subnet_id}' doesn't exist !")
        sys.exit(1)

print(f"Vpc:    {vpc_id}")
print(f"Subnet: {subnet_id}")


res = ec2.describe_client_vpn_endpoints()
for e in res["ClientVpnEndpoints"]:
    for tag in e["Tags"]:
        if tag["Key"] == "Name" and tag["Value"] == vpn_name:
            vpn_id = e["ClientVpnEndpointId"]
            if "AssociatedTargetNetworks" in e:
                vpn_networks = e["AssociatedTargetNetworks"]
            else:
                vpn_networks = []
            break

if vpn_id:
    print("VPN endpoint already exists")
    sys.exit(0)

with open("pki/ca.crt") as f:
    cert_server["ca"]= f.read()
with open(f"pki/issued/{cert_server['name']}.crt") as f:
    cert_server["public"] = f.read()
with open(f"pki/private/{cert_server['name']}.key") as f:
    cert_server["private"] = f.read()

acm = boto3.client('acm')
res = acm.list_certificates()
for cert in res["CertificateSummaryList"]:
    if cert["DomainName"] == cert_server["name"]:
        cert_server["CertificateArn"] = cert["CertificateArn"]

print("Importing server certificate")
if "CertificateArn" in cert_server:
    acm.import_certificate(CertificateArn=cert_server["CertificateArn"], Certificate=cert_server["public"], PrivateKey=cert_server["private"], CertificateChain=cert_server["ca"])
else:
    res = acm.import_certificate(Certificate=cert_server["public"], PrivateKey=cert_server["private"], CertificateChain=cert_server["ca"])
    cert_server["CertificateArn"] = res["CertificateArn"]


logs = boto3.client('logs')

print("Creating Clouwatch logs")
try:
    logs.create_log_group(logGroupName="vpn-client-logs")
    logs.create_log_stream(logGroupName="vpn-client-logs", logStreamName="connections")
    logs.put_retention_policy(logGroupName="vpn-client-logs", retentionInDays=7)
except:
    pass

res = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values":[vpn_name]}])
if len(res["SecurityGroups"]) > 0:
    sg_id = res["SecurityGroups"][0]["GroupId"]
else:
    print('Creating security group')
    res = ec2.create_security_group(GroupName=vpn_name, VpcId=vpc_id, Description="For VPN access")
    sg_id = res["GroupId"]
    ec2.authorize_security_group_ingress( 
        GroupId=sg_id, 
        IpPermissions=[{'IpProtocol': '-1', 'FromPort': -1, 'ToPort': -1, 'UserIdGroupPairs': [{ 'GroupId': sg_id}] }],
    )

print("Creating VPN endpoint")
res = ec2.create_client_vpn_endpoint(
    ClientCidrBlock=vpn_cidr, 
    ServerCertificateArn=cert_server["CertificateArn"],
    AuthenticationOptions=[{"Type":"certificate-authentication", "MutualAuthentication": {"ClientRootCertificateChainArn": cert_server["CertificateArn"]}}],
    SplitTunnel=True,
    VpcId=vpc_id,
    SecurityGroupIds=[sg_id],
    ConnectionLogOptions={"Enabled": True, "CloudwatchLogGroup": "vpn-client-logs" , "CloudwatchLogStream": "connections"},
    TagSpecifications=[{"ResourceType": "client-vpn-endpoint", "Tags":[{"Key": "Name", "Value": vpn_name}]}]
    )
vpn_id = res["ClientVpnEndpointId"]

print("Associating subnet")
ec2.associate_client_vpn_target_network(ClientVpnEndpointId=vpn_id, SubnetId=subnet_id)

print("Adding authorization")
ec2.authorize_client_vpn_ingress(ClientVpnEndpointId=vpn_id, TargetNetworkCidr="0.0.0.0/0", AuthorizeAllGroups=True)

print("Adding route")
ec2.create_client_vpn_route(ClientVpnEndpointId=vpn_id, DestinationCidrBlock="0.0.0.0/0", TargetVpcSubnetId=subnet_id)

print('Waiting for VPN endpoint availability ...')
while True:
    time.sleep(5)
    res = ec2.describe_client_vpn_endpoints(ClientVpnEndpointIds=[vpn_id])
    if res["ClientVpnEndpoints"][0]["Status"]["Code"] == "available":
        break

print(f"The VPN endpoint '{vpn_id}' is ready to use")

