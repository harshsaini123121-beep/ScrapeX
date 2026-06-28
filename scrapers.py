import time
import asyncio
import aiohttp
import requests
import threading
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

# Top-level helper function for ProcessPoolExecutor (must be picklable)
def fetch_url_sync(url):
    """
    Synchronous worker to fetch a single URL.
    Returns a tuple of (url, status_code, data_size, title, error_msg, elapsed_time).
    """
    start_time = time.perf_counter()
    try:
        response = requests.get(url, timeout=10)
        elapsed = time.perf_counter() - start_time
        
        # Parse title using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        
        return (
            url,
            response.status_code,
            len(response.content),
            title[:100], # limit size
            None,
            elapsed
        )
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        return (
            url,
            0,
            0,
            "Error",
            str(e),
            elapsed
        )


class BaseScraper:
    def __init__(self, urls, progress_callback=None):
        self.urls = urls
        self.progress_callback = progress_callback
        self.results = []
        self.metrics = {}
        self._results_lock = threading.Lock()

    def report_progress(self, index, result):
        with self._results_lock:
            self.results.append(result)
        if self.progress_callback:
            self.progress_callback(index + 1, len(self.urls), result)


class SequentialScraper(BaseScraper):
    def run(self):
        start_time = time.perf_counter()
        
        for idx, url in enumerate(self.urls):
            res = fetch_url_sync(url)
            result = {
                "url": res[0],
                "status_code": res[1],
                "data_size": res[2],
                "title": res[3],
                "error": res[4],
                "time_taken": round(res[5], 4)
            }
            self.report_progress(idx, result)
            
        total_time = time.perf_counter() - start_time
        self.calculate_metrics(total_time)
        return self.results, self.metrics

    def calculate_metrics(self, total_time):
        success = sum(1 for r in self.results if r["status_code"] == 200)
        failed = len(self.results) - success
        self.metrics = {
            "mode": "Sequential",
            "total_time": round(total_time, 4),
            "success_count": success,
            "failure_count": failed,
            "req_per_sec": round(len(self.urls) / total_time, 2) if total_time > 0 else 0,
            "total_size_bytes": sum(r["data_size"] for r in self.results)
        }


class ThreadedScraper(BaseScraper):
    def __init__(self, urls, max_workers=10, progress_callback=None):
        super().__init__(urls, progress_callback)
        self.max_workers = max_workers

    def run(self):
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {executor.submit(fetch_url_sync, url): idx for idx, url in enumerate(self.urls)}
            
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                res = future.result()
                result = {
                    "url": res[0],
                    "status_code": res[1],
                    "data_size": res[2],
                    "title": res[3],
                    "error": res[4],
                    "time_taken": round(res[5], 4)
                }
                self.report_progress(idx, result)

        total_time = time.perf_counter() - start_time
        self.calculate_metrics(total_time)
        return self.results, self.metrics

    def calculate_metrics(self, total_time):
        success = sum(1 for r in self.results if r["status_code"] == 200)
        failed = len(self.results) - success
        self.metrics = {
            "mode": f"Multi-Threaded (x{self.max_workers})",
            "total_time": round(total_time, 4),
            "success_count": success,
            "failure_count": failed,
            "req_per_sec": round(len(self.urls) / total_time, 2) if total_time > 0 else 0,
            "total_size_bytes": sum(r["data_size"] for r in self.results)
        }


class ProcessScraper(BaseScraper):
    def __init__(self, urls, max_workers=4, progress_callback=None):
        super().__init__(urls, progress_callback)
        self.max_workers = max_workers

    def run(self):
        start_time = time.perf_counter()
        
        # Use ProcessPoolExecutor to run CPU bound parsing and fetching (parallel)
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(fetch_url_sync, url) for url in self.urls]
            
            for idx, future in enumerate(futures):
                res = future.result()
                result = {
                    "url": res[0],
                    "status_code": res[1],
                    "data_size": res[2],
                    "title": res[3],
                    "error": res[4],
                    "time_taken": round(res[5], 4)
                }
                self.report_progress(idx, result)

        total_time = time.perf_counter() - start_time
        self.calculate_metrics(total_time)
        return self.results, self.metrics

    def calculate_metrics(self, total_time):
        success = sum(1 for r in self.results if r["status_code"] == 200)
        failed = len(self.results) - success
        self.metrics = {
            "mode": f"Multi-Processed (x{self.max_workers})",
            "total_time": round(total_time, 4),
            "success_count": success,
            "failure_count": failed,
            "req_per_sec": round(len(self.urls) / total_time, 2) if total_time > 0 else 0,
            "total_size_bytes": sum(r["data_size"] for r in self.results)
        }


class AsyncScraper(BaseScraper):
    def __init__(self, urls, max_workers=10, progress_callback=None):
        super().__init__(urls, progress_callback)
        self.max_workers = max_workers

    async def fetch_async(self, session, semaphore, idx, url):
        async with semaphore:
            start_time = time.perf_counter()
            try:
                # Limit timeouts
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(url, timeout=timeout) as response:
                    html = await response.text()
                    content = await response.read()
                    elapsed = time.perf_counter() - start_time
                    
                    # Parse title
                    soup = BeautifulSoup(html, 'html.parser')
                    title = soup.title.string.strip() if soup.title else "No Title"
                    
                    result = {
                        "url": url,
                        "status_code": response.status,
                        "data_size": len(content),
                        "title": title[:100],
                        "error": None,
                        "time_taken": round(elapsed, 4)
                    }
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                result = {
                    "url": url,
                    "status_code": 0,
                    "data_size": 0,
                    "title": "Error",
                    "error": str(e),
                    "time_taken": round(elapsed, 4)
                }
            
            self.report_progress(idx, result)
            return result

    async def run_async(self):
        start_time = time.perf_counter()
        
        semaphore = asyncio.Semaphore(self.max_workers)
        # Use trust_env=True to support system proxy settings if any
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            tasks = [
                self.fetch_async(session, semaphore, idx, url)
                for idx, url in enumerate(self.urls)
            ]
            # Gather tasks but they already call report_progress inside
            await asyncio.gather(*tasks)

        total_time = time.perf_counter() - start_time
        self.calculate_metrics(total_time)
        return self.results, self.metrics

    def run(self):
        # Helper to run in sync context if needed (though API will run async directly)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            # If loop is already running (e.g. inside FastAPI), we must run as task or run nested
            # But the server itself will call await run_async() directly.
            # This is a fallback wrapper.
            future = asyncio.run_coroutine_threadsafe(self.run_async(), loop)
            return future.result()
        else:
            return loop.run_until_complete(self.run_async())

    def calculate_metrics(self, total_time):
        success = sum(1 for r in self.results if r["status_code"] == 200)
        failed = len(self.results) - success
        self.metrics = {
            "mode": f"Asynchronous (x{self.max_workers})",
            "total_time": round(total_time, 4),
            "success_count": success,
            "failure_count": failed,
            "req_per_sec": round(len(self.urls) / total_time, 2) if total_time > 0 else 0,
            "total_size_bytes": sum(r["data_size"] for r in self.results)
        }
