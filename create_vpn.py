#! /usr/bin/env python3

# Usage: create_vpn.py subnet_id

import os
import sys
import time

import boto3


if len(sys.argv) != 4:
    print(f"Usage: {sys.argv[0]} vpc_id subnet_id user_id")
    sys.exit(0)

vpc_id = sys.argv[1]
subnet_id = sys.argv[2]
vpn_name = "vpn-endpoint"
vpn_cidr = "10.2.0.0/22"
cert_server = "vpn-server"
cert_client = f"vpn-{sys.argv[3]}"
openvpn_filename = "client-configuration.ovpn"

vpn_id = None
sg_id = None


certificates = {cert_server:{}, cert_client:{}}

with open("pki/ca.crt") as f:
    ca_cert = f.read()

for name, values in certificates.items():
    with open(f"pki/issued/{name}.crt") as f:
        values["public"] = f.read()
    with open(f"pki/private/{name}.key") as f:
        values["private"] = f.read()



ec2 = boto3.client('ec2')

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

if not vpn_id:

    acm = boto3.client('acm')

    res = acm.list_certificates()
    for cert in res["CertificateSummaryList"]:
        for name in certificates.keys():
            if cert["DomainName"] == name:
                certificates[name]["CertificateArn"] = cert["CertificateArn"]

    for name, values in certificates.items():
        if cert_server == name:
            print(f"Importing certificate {name}")
            if "CertificateArn" in values:
                acm.import_certificate(CertificateArn=values["CertificateArn"], Certificate=values["public"], PrivateKey=values["private"], CertificateChain=ca_cert)
            else:
                res = acm.import_certificate(Certificate=values["public"], PrivateKey=values["private"], CertificateChain=ca_cert)
                values["CertificateArn"] = res["CertificateArn"]


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
        ServerCertificateArn=certificates[cert_server]["CertificateArn"],
        AuthenticationOptions=[{"Type":"certificate-authentication", "MutualAuthentication": {"ClientRootCertificateChainArn": certificates[cert_server]["CertificateArn"]}}],
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

    print(f"The VPN endpoint '{vpn_id}' is ready to use (just add your specific security groups)")

else:
    print("VPN endpoint already exists")


print(f"Exporting openvpn configuration to {openvpn_filename}")
res = ec2.export_client_vpn_client_configuration(ClientVpnEndpointId=vpn_id)
openvpn_config = res["ClientConfiguration"]

cert = certificates[cert_client]["public"]
i = cert.find("-----BEGIN CERTIFICATE")
cert = cert[i:]
key = certificates[cert_client]["private"]

openvpn_config += f"\n\n<cert>\n{cert}</cert>\n\n<key>\n{key}</key>\n"

with open(openvpn_filename, "w") as f:
    f.write(openvpn_config)




