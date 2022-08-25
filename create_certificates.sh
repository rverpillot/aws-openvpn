#! /bin/bash

# Use easyrsa tool to create CA, server and client certificates
#
# Usage: create_certificates.sh user_id


if [[ $# != 1 ]]; then
    echo "Usage: $0 user_id"
    exit
fi

# Init
if [[ ! -d "pki" ]]; then
    easyrsa init-pki
fi

# Build CA
if [[ ! -f "pki/ca.crt" ]]; then
    easyrsa --batch build-ca nopass
fi

# Build server certificate
if [[ ! -f "pki/issued/vpn-server.crt" ]]; then
    easyrsa build-server-full vpn-server nopass
fi

# Build client certificate
easyrsa build-client-full vpn-$1 nopass

# Results
easyrsa show-ca
easyrsa show-cert vpn-server
easyrsa show-cert vpn-$1


