import gevent.monkey
gevent.monkey.patch_all()

from mcstatus import JavaServer
import gevent.pool
import multiprocessing

def scan_ip(ip):
    try:
        server = JavaServer.lookup(f"{ip}:25565")
        status = server.status()
        print("---------------------------------------------------------------------------")
        print(f"Server found at {ip}:25565")
        print(f"Description: {status.description}")
        print(f"Players: {status.players.online}/{status.players.max}")
        print(f"Version: {status.version.name}")
        print(f"Latency: {status.latency}")
    except Exception:
        pass

def generate_ips():
    for i in range(0, 256):
        for j in range(0, 256):
            for k in range(0, 256):
                yield f"82.{i}.{j}.{k}"

def worker(ips):
    pool = gevent.pool.Pool(size=1000)
    for ip in ips:
        pool.spawn(scan_ip, ip)
    pool.join()

def main():
    num_processes = multiprocessing.cpu_count()
    ip_list = list(generate_ips())
    chunk_size = len(ip_list) // num_processes
    
    processes = []
    for i in range(num_processes):
        start = i * chunk_size
        end = len(ip_list) if i == num_processes - 1 else (i + 1) * chunk_size
        p = multiprocessing.Process(target=worker, args=(ip_list[start:end],))
        processes.append(p)
        p.start()
    
    for p in processes:
        p.join()

if __name__ == "__main__":
    main()
