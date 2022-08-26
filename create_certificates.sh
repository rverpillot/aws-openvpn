#! /bin/bash

# Use easyrsa tool to create CA, server and client certificates
#
# Usage: create_certificates.sh [client_id]

# Init
if [[ ! -d "pki" ]]; then
    easyrsa init-pki
fi

# Build CA
if [[ ! -f "pki/ca.crt" ]]; then
    easyrsa --batch build-ca nopass
    easyrsa show-ca
fi

# Build server certificate
if [[ ! -f "pki/issued/vpn-server.crt" ]]; then
    easyrsa build-server-full vpn-server nopass
    easyrsa show-cert vpn-server
fi

# Build client certificate
if [[ $# != 1 ]]; then
    easyrsa build-client-full vpn-$1 nopass
    easyrsa show-cert vpn-$1
fi



