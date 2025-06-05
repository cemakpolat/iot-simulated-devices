#!/bin/bash

# Create certificate directory
mkdir -p certificates

# Define certificate configurations
# Format: "name:organizational_unit:common_name"
CERTIFICATES=(
    "server:Automation:localhost"
    "client:Control Systems:opcua-client" 
    "telegraf:Monitoring:telegraf"
)

# Base subject information
BASE_SUBJECT="/C=US/ST=CA/L=San Francisco/O=Industrial Corp"

# Function to generate certificate
generate_certificate() {
    local name=$1
    local ou=$2
    local cn=$3
    
    echo "🔑 Generating certificate for: $name"
    
    # Generate private key
    openssl genrsa -out certificates/${name}_private_key.pem 2048
    
    # Generate certificate signing request
    openssl req -new -key certificates/${name}_private_key.pem \
        -out certificates/${name}.csr \
        -subj "${BASE_SUBJECT}/OU=${ou}/CN=${cn}"
    
    # Generate self-signed certificate
    openssl x509 -req -days 365 \
        -in certificates/${name}.csr \
        -signkey certificates/${name}_private_key.pem \
        -out certificates/${name}_certificate.pem
}

# Loop through certificates array and generate each one
for cert_config in "${CERTIFICATES[@]}"; do
    # Split the configuration string
    IFS=':' read -r name ou cn <<< "$cert_config"
    
    # Generate the certificate
    generate_certificate "$name" "$ou" "$cn"
done

# Cleanup unnecessary files
rm certificates/*.csr

echo "✅ All certificates generated successfully in 'certificates/' directory"
echo "📁 Generated certificates:"
ls -la certificates/*.pem