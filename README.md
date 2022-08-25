# Create a VPN to an AWS VPC

## Requirements
- openvpn
- easyrsa (https://github.com/OpenVPN/easy-rsa)
- python3

## Installation
```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

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

