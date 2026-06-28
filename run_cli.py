import sys
import time
import argparse
import uvicorn
import threading
from tabulate import tabulate
from scrapers import SequentialScraper, ThreadedScraper, ProcessScraper, AsyncScraper

# Reconfigure stdout/stderr to handle unicode tables on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Fallback for environments where reconfigure is not available
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def start_server():
    """Starts the FastAPI mock server in a daemon thread."""
    config = uvicorn.Config("server:app", host="127.0.0.1", port=8000, log_level="error")
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    # Give the server a moment to start
    time.sleep(1.5)
    print("[+] Simulated network latency target server booted on http://127.0.0.1:8000")

def run_benchmarks(pages, delay, workers):
    print(f"\n[~] Starting Concurrency Benchmark")
    print(f"    - Target URL count: {pages}")
    print(f"    - Network Latency: {delay}s per page")
    print(f"    - Max Workers (Threads/Processes/Async): {workers}")
    print("=" * 70)

    urls = [f"http://127.0.0.1:8000/mock/{i}?delay={delay}" for i in range(1, pages + 1)]
    results_summary = []

    # 1. Sequential Scraper
    print("\nRunning Sequential Scraper...")
    seq_scraper = SequentialScraper(urls)
    start = time.perf_counter()
    _, seq_metrics = seq_scraper.run()
    seq_time = time.perf_counter() - start
    print(f"Finished. Total Time: {seq_time:.3f} seconds ({seq_metrics['req_per_sec']:.2f} req/s)")
    results_summary.append({
        "Mode": "Sequential",
        "Total Time (s)": f"{seq_time:.3f}",
        "Req/Sec": f"{seq_metrics['req_per_sec']:.2f}",
        "Downloaded": f"{seq_metrics['total_size_bytes'] / 1024:.1f} KB",
        "Success": f"{seq_metrics['success_count']}/{pages}",
        "Speedup": "1.00x (Baseline)"
    })

    # 2. Threaded Scraper
    print(f"\nRunning Multi-Threaded Scraper (workers={workers})...")
    thread_scraper = ThreadedScraper(urls, max_workers=workers)
    start = time.perf_counter()
    _, thread_metrics = thread_scraper.run()
    thread_time = time.perf_counter() - start
    speedup_thread = seq_time / thread_time if thread_time > 0 else 0
    print(f"Finished. Total Time: {thread_time:.3f} seconds ({thread_metrics['req_per_sec']:.2f} req/s)")
    results_summary.append({
        "Mode": "Multi-Threaded",
        "Total Time (s)": f"{thread_time:.3f}",
        "Req/Sec": f"{thread_metrics['req_per_sec']:.2f}",
        "Downloaded": f"{thread_metrics['total_size_bytes'] / 1024:.1f} KB",
        "Success": f"{thread_metrics['success_count']}/{pages}",
        "Speedup": f"{speedup_thread:.2f}x"
    })

    # 3. Process Scraper
    # Multiprocessing on Windows requires safe main entry point, which we have in if __name__ == '__main__'.
    # We will limit workers for process to min(cpu_count, workers) to avoid resource exhaustion.
    import os
    proc_workers = min(os.cpu_count() or 4, workers)
    print(f"\nRunning Multi-Processed Scraper (workers={proc_workers})...")
    proc_scraper = ProcessScraper(urls, max_workers=proc_workers)
    start = time.perf_counter()
    _, proc_metrics = proc_scraper.run()
    proc_time = time.perf_counter() - start
    speedup_proc = seq_time / proc_time if proc_time > 0 else 0
    print(f"Finished. Total Time: {proc_time:.3f} seconds ({proc_metrics['req_per_sec']:.2f} req/s)")
    results_summary.append({
        "Mode": "Multi-Processed",
        "Total Time (s)": f"{proc_time:.3f}",
        "Req/Sec": f"{proc_metrics['req_per_sec']:.2f}",
        "Downloaded": f"{proc_metrics['total_size_bytes'] / 1024:.1f} KB",
        "Success": f"{proc_metrics['success_count']}/{pages}",
        "Speedup": f"{speedup_proc:.2f}x"
    })

    # 4. Async Scraper
    print(f"\nRunning Asynchronous Scraper (workers={workers})...")
    async_scraper = AsyncScraper(urls, max_workers=workers)
    start = time.perf_counter()
    _, async_metrics = async_scraper.run()
    async_time = time.perf_counter() - start
    speedup_async = seq_time / async_time if async_time > 0 else 0
    print(f"Finished. Total Time: {async_time:.3f} seconds ({async_metrics['req_per_sec']:.2f} req/s)")
    results_summary.append({
        "Mode": "Asynchronous",
        "Total Time (s)": f"{async_time:.3f}",
        "Req/Sec": f"{async_metrics['req_per_sec']:.2f}",
        "Downloaded": f"{async_metrics['total_size_bytes'] / 1024:.1f} KB",
        "Success": f"{async_metrics['success_count']}/{pages}",
        "Speedup": f"{speedup_async:.2f}x"
    })

    # Print Gorgeous Tabulated Comparison
    print("\n" + "=" * 70)
    print("                      PERFORMANCE COMPARISON RESULT")
    print("=" * 70)
    print(tabulate(results_summary, headers="keys", tablefmt="fancy_grid"))
    print("=" * 70)

if __name__ == "__main__":
    # Standard safeguard for multiprocessing on Windows
    parser = argparse.ArgumentParser(description="Concurrent Scraper Benchmark CLI")
    parser.add_argument("--pages", type=int, default=50, help="Number of mock pages to download")
    parser.add_argument("--delay", type=float, default=0.05, help="Simulated latency delay (seconds) per page")
    parser.add_argument("--workers", type=int, default=10, help="Concurrency worker limit")
    args = parser.parse_args()

    start_server()
    run_benchmarks(args.pages, args.delay, args.workers)
    print("\nBenchmark completed. Exiting...")
    sys.exit(0)
