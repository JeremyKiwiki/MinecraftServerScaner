
# Minecraft Server Scanner

This project is a Minecraft server scanner that can scan IP address ranges to find online Minecraft servers. The results can be saved to a CSV file or a SQLite database.

## Dependencies
- Python 3.6 or higher
- Masscan

You can install the Python dependencies using:
```
pip install -r requirements.txt
```

### Masscan

Masscan is required to perform the scanning. You can download and compile Masscan from the following link:

[Masscan GitHub Repository](https://github.com/robertdavidgraham/masscan)

#### Compiling Masscan on Windows

1. Download and install [Visual Studio](https://visualstudio.microsoft.com/) with C++ development tools.
2. Clone the Masscan repository:
```
git clone https://github.com/robertdavidgraham/masscan
```
3. Open the `Developer Command Prompt for Visual Studio` and navigate to the Masscan directory:
```
cd path	o\masscan
```
4. Build Masscan:
```
nmake -f Makefile
```

#### Compiling Masscan on Linux

1. Install dependencies:
```
sudo apt-get install git gcc make libpcap-dev
```
2. Clone the Masscan repository:
```
git clone https://github.com/robertdavidgraham/masscan
```
3. Navigate to the Masscan directory:
```
cd masscan
```
4. Build Masscan:
```
make
```


### Usage
Command Line Arguments
- `--mode`: Scan mode to use (`all`, `registered`, `auto`). Default: `auto`.
- `--scan-type`: Type of server to scan (`java`, `bedrock`, `both`). Default: `both`.
- `--java-ports`: Ports to scan for Java servers. Accepts comma-separated list of ports or ranges (e.g., `25565,25566-25570`). Default: `25565`.
- `--bedrock-ports`: Ports to scan for Bedrock servers. Accepts comma-separated list of ports or ranges (e.g., `19132,19133-19140`). Default: `19132`.
- `--all-interval`: Interval in seconds between each full IP scan. Default: `86400` seconds (24 hours).
- `--registered-interval`: Interval in seconds between each scan of registered IPs. Default: `3600` seconds (1 hour).
- `--ip-range`: IP ranges to scan in 'all' mode. Accepts comma-separated list of IPs or ranges (e.g., `192.168.1.0/24,10.0.0.0/8`). Default: `82.65.0.0/16`.
- `--exclude-ips`: Comma-separated list of IPs or ranges to exclude from scanning (e.g., `192.168.1.1,192.168.0.0/16`). Default: none.
- `--include-local`: Include local IPs in the scan. Default: `False`.
- `--rate`: Scan rate. Default: `500`.
- `--verbose`: Verbosity level (`0`, `1`, `2`). Default: `1`.

### Examples of Use

#### Scan all public IPs once:
```
python main.py --mode all
```

#### Scan registered servers:
```
python main.py --mode registered
```

#### Scan all public IPs and registered servers automatically:
```
python main.py --mode auto
```

#### Scan Java servers on custom ports:
```
python main.py --scan-type java --java-ports 25565,25566-25570
```

#### Scan Bedrock servers on custom ports:
```
python main.py --scan-type bedrock --bedrock-ports 19132,19133-19140
```

#### Exclude specific IPs from the scan:
```
python main.py --exclude-ips 192.168.1.1,192.168.0.0/16
```

#### Set scan rate and verbosity:
```
python main.py --rate 1000 --verbose 2
```

#### Scan specific IP ranges:
```
python main.py --ip-range 192.168.1.0/24,10.0.0.0/8
```

### Project Functionality
The scanner uses `masscan` to quickly find open Minecraft server ports and then checks the server status using the `mcstatus` library. The results are saved to a SQLite database with information about the server's IP, port, type, version, players, MOTD, location, and more.

In `auto` mode, the scanner will perform a full IP scan every 24 hours and scan registered servers every hour by default. This interval can be adjusted using the `--all-interval` and `--registered-interval` arguments.

In `registered` mode, the scanner only scans IPs of previously discovered servers that were active during the last scan.

In `all` mode, the scanner performs a full scan of the specified IP range(s).

The verbosity level can be set to control the amount of information printed to the console during the scan process:
- `0`: No output.
- `1`: Print found servers.
- `2`: Print detailed scan process information.

