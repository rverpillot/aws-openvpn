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
- create CA and server certificates
```sh
./create_certificates.sh
```
- create client certificate
```sh
./create_certificates.sh CLIENT_ID
```

## Import the server certificate to ACM and create the VPN endpoint
```sh
./create_vpn.py CIDR SUBNET_ID
```

## Start the VPN
```sh
./get_configuration.py CLIENT_ID > configuration.ovpn
sudo openvpn --config configuration.ovpn
```

## Example
```sh
./create_certificates.sh
./create_certificates.sh joe

./create_vpn.py 10.2.0.0/22 subnet_0123456789
./get_configuration.py joe > my_configuration.ovpn
sudo openvpn --config my_configuration.ovpn

```

