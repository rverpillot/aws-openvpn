#! /usr/bin/env python3

# Usage: get_configuration.py client_id > config.ovpn

import sys
import boto3



if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} client_id" )
    sys.exit(0)


cert_client = f"vpn-{sys.argv[1]}"
vpn_name = "vpn-endpoint"
vpn_id = None

with open(f"pki/issued/{cert_client}.crt") as f:
    public_key = f.read()
with open(f"pki/private/{cert_client}.key") as f:
    private_key = f.read()

ec2 = boto3.client('ec2')

res = ec2.describe_client_vpn_endpoints()
for e in res["ClientVpnEndpoints"]:
    for tag in e["Tags"]:
        if tag["Key"] == "Name" and tag["Value"] == vpn_name:
            vpn_id = e["ClientVpnEndpointId"]

if not vpn_id:
    print("VPN endpoint not found", file=sys.stderr)
    sys.exit(1)


res = ec2.export_client_vpn_client_configuration(ClientVpnEndpointId=vpn_id)
openvpn_config = res["ClientConfiguration"]

i = public_key.find("-----BEGIN CERTIFICATE")
public_key = public_key[i:]

openvpn_config += f"\n\n<cert>\n{public_key}</cert>\n\n<key>\n{private_key}</key>\n"

print(openvpn_config)
