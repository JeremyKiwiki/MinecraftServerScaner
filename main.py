import gevent.monkey
gevent.monkey.patch_all() #to add async
from mcstatus import JavaServer, BedrockServer #to test for both Java and Bedrock servers
import gevent.pool
import multiprocessing
import argparse
import csv
import os
import sqlite3

def scan_ip(ip, verbose, save, csv_filename=None, db_conn=None): #scaner
    try:
        #test for java server
        server = JavaServer.lookup(f"{ip}:25565")
        status = server.status()
        server_type = "Java"
        description = status.description
        players_online = status.players.online
        players_max = status.players.max
        version = status.version.name
        latency = status.latency
    except Exception:
        try:
            #test for bedrock server
            server = BedrockServer.lookup(f"{ip}:19132")
            status = server.status()
            server_type = "Bedrock"
            description = status.motd.raw
            players_online = status.players_online
            players_max = status.players_max
            version = status.version.version
            latency = ping(ip)
        except Exception:
            if verbose >= 2:
                print(f"No server at {ip}:25565 or {ip}:19132")
            return

    if verbose >= 1:
        print("-------------------------------------------------------")
        print(f"Server found at {ip}:{'25565' if server_type == 'Java' else '19132'}")
        print(f"Type: {server_type}")
        print(f"Description: {description}")
        print(f"Players: {players_online}/{players_max}")
        print(f"Version: {version}")
        print(f"Latency: {latency} ms")

    if save == 'csv' and csv_filename:  #if save -> to csv or db
        with open(csv_filename, mode='a', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([
                ip, server_type,
                description,
                players_online,
                players_max,
                version,
                latency
            ])
    elif save == 'sqlite' and db_conn:
        cursor = db_conn.cursor()
        cursor.execute(
            "INSERT INTO servers (ip, type, description, players_online, max_players, version, latency) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ip, server_type,
             description,
             players_online,
             players_max,
             version,
             latency)
        )
        db_conn.commit()

def generate_ips(ip_ranges): #generate IP range according to --ip
    for ip_range in ip_ranges:
        start_parts = list(map(int, ip_range[0].split('.')))
        end_parts = list(map(int, ip_range[1].split('.')))
        for i in range(start_parts[0], end_parts[0] + 1):
            for j in range(start_parts[1], end_parts[1] + 1):
                for k in range(start_parts[2], end_parts[2] + 1):
                    for l in range(start_parts[3], end_parts[3] + 1):
                        yield f"{i}.{j}.{k}.{l}"

def parse_ip_ranges(ip_ranges): #parse if single param or multiple param
    ranges = []
    for ip_range in ip_ranges.split(','):
        if '-' in ip_range:
            start_ip, end_ip = ip_range.split('-')
            ranges.append((start_ip.strip(), end_ip.strip()))
        else:
            ranges.append((ip_range.strip(), ip_range.strip()))
    return ranges

def worker(ips, verbose, save, csv_filename=None, db_file=None, delay=0): #multi thread worker
    pool = gevent.pool.Pool(size=1000)
    db_conn = sqlite3.connect(db_file) if db_file else None
    for ip in ips:
        pool.spawn(scan_ip, ip, verbose, save, csv_filename, db_conn)
        if delay > 0:
            gevent.sleep(delay / 1000) #add delay to avoid ban or yolo mode if 0
    pool.join()
    if db_conn:
        db_conn.close()

def main():
    #--------------------------------------- Declare Params ----------------------------------------------------------------
    parser = argparse.ArgumentParser(description="Scan Minecraft servers.")
    parser.add_argument('--verbose', type=int, default=1, help="Verbosity level (0, 1, 2)")
    parser.add_argument('--save', type=str, default=None, help="Save found servers to a CSV file or a database (sqlite, postgres, mysql)")
    parser.add_argument('--ip', type=str, required=True, help="IP ranges to scan (e.g., '192.168.0.0-192.168.255.255,192.168.0.0-192.168.0.255')")
    parser.add_argument('--db-host', type=str, help="Database host (for postgres, mysql)")
    parser.add_argument('--db-port', type=str, help="Database port (for postgres, mysql)")
    parser.add_argument('--db-user', type=str, help="Database user (for postgres, mysql)")
    parser.add_argument('--db-password', type=str, help="Database password (for postgres, mysql)")
    parser.add_argument('--db-name', type=str, help="Database name (for postgres, mysql)")
    parser.add_argument('--db-file', type=str, help="SQLite database file (for sqlite)")
    parser.add_argument('--csv-file', type=str, help="CSV file name (for csv)")
    parser.add_argument('--delay', type=int, default=0, help="Delay between requests in milliseconds (0 for no delay)")
    args = parser.parse_args()
    
    #-------------------------------------------------------------------------------------------------------------------------

    csv_filename = args.csv_file if args.csv_file else 'found_servers.csv' #default name if !--csv file
    db_filename = args.db_file if args.db_file else 'servers.db' #same default name for db

    if args.save == 'csv': #init csv
        if not os.path.exists(csv_filename):
            with open(csv_filename, mode='w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(["IP", "Type", "Description", "Players Online", "Max Players", "Version", "Latency"])
    elif args.save == 'sqlite': #init db
        db_conn = sqlite3.connect(db_filename)
        db_conn.execute(
            "CREATE TABLE IF NOT EXISTS servers ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "ip TEXT,"
            "type TEXT,"
            "description TEXT,"
            "players_online INTEGER,"
            "max_players INTEGER,"
            "version TEXT,"
            "latency TEXT)"
        )
        db_conn.close()

    ip_ranges = parse_ip_ranges(args.ip)
    ip_list = list(generate_ips(ip_ranges))
    chunk_size = len(ip_list) // multiprocessing.cpu_count() #share work between cpu

    processes = []
    for i in range(multiprocessing.cpu_count()):
        start = i * chunk_size
        end = len(ip_list) if i == multiprocessing.cpu_count() - 1 else (i + 1) * chunk_size
        p = multiprocessing.Process(target=worker, args=(ip_list[start:end], args.verbose, args.save, csv_filename, db_filename, args.delay))
        processes.append(p)
        p.start()

    for p in processes: #wait for all processes to end
        p.join()

if __name__ == "__main__": #avoid running if imported
    main()