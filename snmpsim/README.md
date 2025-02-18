# SNMP Server and Client Simulator

This repository provides a simulation environment for testing SNMP (Simple Network Management Protocol) interactions between a client and a server.

The SNMP server is configured with predefined Object Identifiers (OIDs). It collects some data in real-time from the system using the `psutil` library (e.g., CPU usage, memory usage), while other data is randomly generated for demonstration purposes.  The SNMP client then fetches these OIDs from the server.

Both the client and server can be used independently; however, code modifications may be necessary to adjust their functionality.

For ease of use, a `docker-compose` file is included to streamline the process of building and starting both the SNMP server and client.  Upon service initialization, the client and server will automatically interact. To build the images and start the containers, execute:

`docker-compose up -d --build`

The following libraries are used:

## Client Side Libraries

- `pysnmp==7.1.16`

## Server Side Libraries

- `snmp_agent==0.2.3`
- `psutil==5.9.8`


For more detail please take a look at the medium link: https://akpolatcem.medium.com/snmp-networks-helpful-reporter-even-in-the-age-of-iot-b9b696f2884e
