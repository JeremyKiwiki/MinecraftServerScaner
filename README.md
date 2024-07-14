
# Minecraft Server Scanner

This project is a Minecraft server scanner that can scan IP address ranges to find online Minecraft servers. The results can be saved to a CSV file, a SQLite database, and in the futures PostgreSQL or MySQL.

### Dependencies
- Python 3.6 or higher
You can install the dependencies using
- pip install -r requirement.txt

### Usage
Command Line Arguments
--verbose: Verbosity level (0, 1, 2). Default: 1.
--save: Method to save the results (csv, sqlite, postgres, mysql). Default: None.
--ip: IP address ranges to scan (e.g., '192.168.0.0-192.168.255.255,192.168.0.0-192.168.0.255'). Required.
--db-host: Database host (for postgres, mysql).
--db-port: Database port (for postgres, mysql).
--db-user: Database user (for postgres, mysql).
--db-password: Database password (for postgres, mysql).
--db-name: Database name (for postgres, mysql).
--db-file: SQLite database file (for sqlite). Default: "servers.db".
--csv-file: CSV file name (for csv). Default:  "found_servers.csv".
--delay: Delay between requests in milliseconds (0 for no delay). Default: 0.

### Examples of Use

Scan an IP range without saving result
#### python main.py --ip '192.168.0.0-192.168.0.255'

Scan an IP range and save results to a CSV file
#### python main.py --ip '192.168.0.0-192.168.0.255' --save csv --csv-file custom_found_servers.csv

Scan an IP range and save results to a CSV file with delay
#### python main.py --ip '192.168.0.0-192.168.0.255' --save csv --csv-file custom_found_servers.csv --delay 100

Scan an IP ranges and save results to a SQLite database
#### python main.py --ip '192.168.0.0-192.168.0.255' --save sqlite --db-file custom_servers.db

Scan Multiple IP ranges and save results to a SQLite database
#### python main.py --ip '192.168.0.0-192.168.0.255,192.168.0.12-192.168.255.255' --save sqlite --db-file custom_servers.db
