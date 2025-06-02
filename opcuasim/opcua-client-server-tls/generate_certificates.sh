# Create certificate directory
mkdir -p certificates

# Generate server private key
openssl genrsa -out certificates/server_private_key.pem 2048

# Generate server certificate signing request
openssl req -new -key certificates/server_private_key.pem -out certificates/server.csr -subj "/C=US/ST=CA/L=San Francisco/O=Industrial Corp/OU=Automation/CN=localhost"

# Generate self-signed server certificate
openssl x509 -req -days 365 -in certificates/server.csr -signkey certificates/server_private_key.pem -out certificates/server_certificate.pem

# Generate client private key
openssl genrsa -out certificates/client_private_key.pem 2048

# Generate client certificate signing request
openssl req -new -key certificates/client_private_key.pem -out certificates/client.csr -subj "/C=US/ST=CA/L=San Francisco/O=Industrial Corp/OU=Control Systems/CN=opcua-client"

# Generate self-signed client certificate
openssl x509 -req -days 365 -in certificates/client.csr -signkey certificates/client_private_key.pem -out certificates/client_certificate.pem