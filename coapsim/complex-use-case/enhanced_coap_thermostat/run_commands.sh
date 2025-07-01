#!/bin/bash

# This script performs a series of curl commands for authentication and device status.

# Define user credentials
USERNAME="myuser"
EMAIL="myemail@example.com"
PASSWORD="mypassword"

# --- Command 1: Register a new user ---
echo "--- Registering a new user (${USERNAME}) ---"
REGISTER_RESPONSE=$(curl --silent --location 'localhost:8080/auth/register' \
--header 'Content-Type: application/json' \
--data-raw '{
  "username": "'"${USERNAME}"'",
  "email": "'"${EMAIL}"'",
  "password": "'"${PASSWORD}"'"
}')

echo "Register Response: ${REGISTER_RESPONSE}"
echo -e "\n" # Add a newline for better readability between outputs

# --- Command 2: Log in the user and extract the bearer token ---
echo "--- Logging in user (${USERNAME}) and extracting token ---"
LOGIN_RESPONSE=$(curl --silent --location 'localhost:8080/api/v1/login' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--data-urlencode "username=${USERNAME}" \
--data-urlencode "password=${PASSWORD}")

echo "Login Response: ${LOGIN_RESPONSE}"

# Extract the access_token using grep and awk
# This assumes the access_token is directly in the JSON response, e.g., {"access_token": "YOUR_TOKEN"}
ACCESS_TOKEN=$(echo "${LOGIN_RESPONSE}" | grep -o '"access_token":"[^"]*"' | awk -F'"' '{print $4}')

if [ -z "${ACCESS_TOKEN}" ]; then
  echo "Error: Could not extract access token from login response."
  echo "Please ensure your login endpoint returns a JSON object with an 'access_token' field."
  exit 1
else
  echo "Extracted Access Token: ${ACCESS_TOKEN}"
fi
echo -e "\n" # Add a newline for better readability between outputs

# --- Command 3: Get smart thermostat device status using the obtained bearer token ---
echo "--- Getting status of smart-thermostat-01 using dynamic token ---"
curl --location 'http://localhost:8080/device/status/smart-thermostat-01' \
--header "Authorization: Bearer ${ACCESS_TOKEN}" \
--data ''

echo -e "\n--- Script finished ---"

