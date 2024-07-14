# -*- coding: utf-8 -*-

import argparse
import subprocess
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from mcstatus import JavaServer, BedrockServer
from multiprocessing import Process
import requests
import time
import socket

#Initialize the database
def initialize_db():
    conn = sqlite3.connect('minecraft_servers.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS servers (
                    ip TEXT,
                    port INTEGER,
                    type TEXT,
                    version TEXT,
                    players_online INTEGER,
                    max_players INTEGER,
                    motd TEXT,
                    last_seen TIMESTAMP,
                    last_status TEXT,
                    location TEXT,
                    country TEXT,
                    protocol_version INTEGER,
                    latency FLOAT,
                    map TEXT,
                    game_mode TEXT,
                    PRIMARY KEY (ip, port, type)
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_time TIMESTAMP,
                    ip TEXT,
                    port INTEGER,
                    type TEXT,
                    version TEXT,
                    players_online INTEGER,
                    max_players INTEGER,
                    motd TEXT,
                    status TEXT,
                    location TEXT,
                    country TEXT,
                    protocol_version INTEGER,
                    latency FLOAT,
                    map TEXT,
                    game_mode TEXT
                )''')
    conn.commit()
    conn.close()

#Parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="Minecraft Server Scanner", epilog="""
    Examples:
    python script.py --mode auto --verbose 2
    python script.py --scan-type java --java-ports 25565,25566-25570
    python script.py --exclude-ips 192.168.1.1,192.168.0.0/16
    python script.py --ip-range 192.168.1.0/24,10.0.0.0/8
    """)
    parser.add_argument('--mode', choices=['all', 'registered', 'auto'], default='auto', help='Scan mode to use (default: auto)')
    parser.add_argument('--scan-type', choices=['java', 'bedrock', 'both'], default='both', help='Type of server to scan (default: both)')
    parser.add_argument('--java-ports', default='25565', help='Ports to scan for Java servers (default: 25565). Accepts comma-separated list of ports or ranges (e.g., 25565,25566-25570)')
    parser.add_argument('--bedrock-ports', default='19132', help='Ports to scan for Bedrock servers (default: 19132). Accepts comma-separated list of ports or ranges (e.g., 19132,19133-19140)')
    parser.add_argument('--all-interval', type=int, default=86400, help="Interval in seconds between each full IP scan (default: 86400 seconds = 24 hours)")
    parser.add_argument('--registered-interval', type=int, default=3600, help="Interval in seconds between each scan of registered IPs (default: 3600 seconds = 1 hour)")
    parser.add_argument('--ip-range', default='0.0.0.0/0', help="IP ranges to scan in 'all' mode (default: 0.0.0.0/0). Accepts comma-separated list of IPs or ranges (e.g., 192.168.1.0/24,10.0.0.0/8)")
    parser.add_argument('--exclude-ips', default='', help='Comma-separated list of IPs or ranges to exclude from scanning (e.g., 192.168.1.1,192.168.0.0/16)')
    parser.add_argument('--include-local', action='store_true', help="Include local IPs in the scan")
    parser.add_argument('--rate', type=int, default=1000, help='Scan rate (default: 1000)')
    parser.add_argument('--verbose', type=int, choices=[0, 1, 2], default=1, help='Verbosity level (0: none, 1: normal, 2: verbose)')
    return parser.parse_args()

#Parse IPs or ranges input
def parse_ip_ranges(ip_ranges_str):
    return ip_ranges_str.split(',')

#Parse ports input
def parse_ports(ports_str):
    ports = []
    for part in ports_str.split(','):
        if '-' in part:
            start, end = part.split('-')
            ports.extend(range(int(start), int(end) + 1))
        else:
            ports.append(int(part))
    return ports

#Execute Masscan and return results in real-time
def run_masscan(ip_ranges, ports, rate, include_local, exclude_ips):
    ports_str = ",".join(map(str, ports))
    exclude_private_ips = [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "255.255.255.255"
    ]
    if exclude_ips:
        exclude_private_ips.extend(parse_ip_ranges(exclude_ips))
    exclude_str = " ".join(f"--exclude {ip}" for ip in exclude_private_ips) if not include_local else ""
    ip_range_str = " ".join(ip_ranges)
    command = f"masscan -p{ports_str} {ip_range_str} --rate {rate} {exclude_str}"
    if args.verbose == 2:
        print(f"Running command: {command}")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
        while True:
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output:
                yield output.strip().split('\n')[0]  #Process only the first IP found in the output line
    except Exception as e:
        if args.verbose > 0:
            print(f"Error running masscan: {e}")
        yield None

#Parse Masscan results
def parse_masscan_output(output):
    regex = r"Discovered open port (\d+)/(\w+) on (\d+\.\d+\.\d+\.\d+)"
    match = re.search(regex, output)
    if match:
        return {"ip": match.group(3), "port": int(match.group(1))}
    return None

#Get IP location using another method to avoid rate limits
def get_ip_location(ip):
    try:
        response = requests.get(f'https://ipinfo.io/{ip}/json')
        data = response.json()
        return data.get('city', 'Unknown'), data.get('country', 'Unknown')
    except Exception as e:
        if args.verbose > 0:
            print(f"Error getting location for IP {ip} - {e}")
        return 'Unknown', 'Unknown'

#Log Minecraft server info to the database
def log_minecraft_server_info(ip, port, server_type, status, version=None, players_online=None, max_players=None, motd=None, protocol_version=None, latency=None, map_name=None, game_mode=None):
    conn = sqlite3.connect('minecraft_servers.db')
    location, country = get_ip_location(ip)
    try:
        c = conn.cursor()
        if status == 'active':
            c.execute('''INSERT OR REPLACE INTO servers 
                        (ip, port, type, version, players_online, max_players, motd, last_seen, last_status, location, country, protocol_version, latency, map, game_mode)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (ip, port, server_type, version, players_online, max_players, motd, datetime.now(), status, location, country, protocol_version, latency, map_name, game_mode))
        else:
            c.execute('''UPDATE servers 
                        SET last_status=?, last_seen=?, location=?, country=?
                        WHERE ip=? AND port=? AND type=?''',
                      (status, datetime.now(), location, country, ip, port, server_type))
        if status == 'active':
            c.execute('''INSERT INTO scans (scan_time, ip, port, type, version, players_online, max_players, motd, status, location, country, protocol_version, latency, map, game_mode)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (datetime.now(), ip, port, server_type, version, players_online, max_players, motd, status, location, country, protocol_version, latency, map_name, game_mode))
        conn.commit()
    except Exception as e:
        print(e)
        if args.verbose > 0:
            print(f"Error logging Minecraft server at {ip}:{port} - {e}")
    finally:
        conn.close()

#Check the status of the Minecraft server
def check_server_status(ip, port, server_type, args):
    try:
        if server_type == 'java':
            server = JavaServer.lookup(f"{ip}:{port}")
            latency = server.ping()  #Ping latency
        elif server_type == 'bedrock':
            server = BedrockServer.lookup(f"{ip}:{port}")
            latency = None
        else:
            return

        server_status = server.status()

        log_minecraft_server_info(
            ip, port, server_type, 'active',
            version=getattr(server_status.version, 'name', None),
            players_online=getattr(server_status.players, 'online', None),
            max_players=getattr(server_status.players, 'max', None),
            motd=server_status.motd.parsed[0] if server_type == 'java' else server_status.motd,
            protocol_version=getattr(server_status.version, 'protocol', None),
            latency=latency,
            map_name=getattr(server_status, 'map', None) if server_type == 'bedrock' else None,
            game_mode=getattr(server_status, 'gamemode', None) if server_type == 'bedrock' else None
        )

        if args.verbose >= 1:
            print(f"Found active {server_type} server at {ip}:{port}")
        if args.verbose == 2:
            location, country = get_ip_location(ip)
            print(f"Server Info: IP: {ip}, Port: {port}, Type: {server_type}, Version: {server_status.version.name}, "
                  f"Players Online: {server_status.players.online}, Max Players: {server_status.players.max}, "
                  f"MOTD: {server_status.motd.parsed[0] if server_type == 'java' else server_status.motd}, "
                  f"Location: {location}, Country: {country}, Protocol Version: {server_status.version.protocol}, "
                  f"Latency: {latency} ms, "
                  f"Map: {server_status.map if server_type == 'bedrock' else 'N/A'}, "
                  f"Game Mode: {server_status.gamemode if server_type == 'bedrock' else 'N/A'}")
    except Exception as e:
        log_minecraft_server_info(ip, port, server_type, 'inactive')
        if args.verbose == 2:
            print(f"No active {server_type} server at {ip}:{port} - {e}")

#Process each Masscan result
def process_masscan_result(output, java_ports, bedrock_ports, args):
    result = parse_masscan_output(output)
    if result:
        ip = result["ip"]
        port = result["port"]
        if port in java_ports:
            process = Process(target=check_server_status, args=(ip, port, 'java', args))
            process.start()
        if port in bedrock_ports:
            process = Process(target=check_server_status, args=(ip, port, 'bedrock', args))
            process.start()

#Scan IPs and log results in real-time
def scan_and_log(ip_ranges, ports, rate, java_ports, bedrock_ports, args):
    for output in run_masscan(ip_ranges, ports, rate, args.include_local, args.exclude_ips):
        if output:
            process_masscan_result(output, java_ports, bedrock_ports, args)

#Scan all public IPs and log results
def scan_all_ips(java_ports, bedrock_ports, ip_ranges, rate):
    ports = list(set(java_ports + bedrock_ports))  #Combine both lists and remove duplicates
    scan_and_log(ip_ranges, ports, rate, java_ports, bedrock_ports, args)

#Scan registered servers
def scan_registered_servers(java_ports, bedrock_ports, rate):
    conn = sqlite3.connect('minecraft_servers.db')
    c = conn.cursor()
    c.execute('''SELECT DISTINCT ip FROM servers WHERE last_status='active' ''')
    servers = c.fetchall()
    registered_ips = [server[0] for server in servers]
    conn.close()
    if registered_ips:
        ip_ranges = parse_ip_ranges(",".join(registered_ips))
        scan_and_log(ip_ranges, java_ports + bedrock_ports, rate, java_ports, bedrock_ports, args)

def main():
    global args
    args = parse_arguments()
    initialize_db()

    java_ports = parse_ports(args.java_ports)
    bedrock_ports = parse_ports(args.bedrock_ports)

    ip_ranges = parse_ip_ranges(args.ip_range)

    if args.mode == "all":
        scan_all_ips(java_ports, bedrock_ports, ip_ranges, args.rate)
    elif args.mode == "registered":
        scan_registered_servers(java_ports, bedrock_ports, args.rate)
    elif args.mode == "auto":
        while True:
            print("START ALL SCAN")
            #Scan all IPs once a day
            scan_all_ips(java_ports, bedrock_ports, ip_ranges, args.rate)
            next_all_scan = datetime.now() + timedelta(seconds=args.all_interval)
            while datetime.now() < next_all_scan:
                #Scan registered servers every hour
                print("START REFRESH DB")
                scan_registered_servers(java_ports, bedrock_ports, args.rate)
                time.sleep(args.registered_interval)

if __name__ == "__main__":
    main()
