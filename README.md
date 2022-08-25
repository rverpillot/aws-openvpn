# Create an AWS VPN endpoint

## Requirements
- openvpn
- easyrsa (https://github.com/OpenVPN/easy-rsa)
- python3

## Installation
- install AWS SDK (boto3).
```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
- Setup your AWS credentials.

## Create certificates for server and client
```sh
./create_certificates.sh <userid>
```

## Import the server certificate to ACM and create the AWS VPN endpoint
```sh
./create_vpn.py <vpc_id> <subnet_id> <userid>
```

## Start the VPN
```sh
sudo openvpn --config client-configuration.ovpn
```

