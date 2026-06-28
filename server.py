import os
import json
import queue
import random
import asyncio
import threading
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from scrapers import SequentialScraper, ThreadedScraper, ProcessScraper, AsyncScraper

app = FastAPI(title="ScrapeX Concurrency Benchmark Dashboard")

# Ensure static directory exists
os.makedirs("static", exist_ok=True)

# Word lists for generating mock pages
NOUNS = ["Scraper", "Data", "Thread", "Process", "Asyncio", "Engine", "Network", "Request", "Concurrency", "Speed"]
ADJECTIVES = ["Concurrent", "High-Speed", "Parallel", "Efficient", "Distributed", "Asynchronous", "Optimal", "Modern"]
VERBS = ["downloads", "parses", "processes", "analyzes", "structures", "fetches", "benchmarks", "speeds up"]

def generate_random_sentence():
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    verb = random.choice(VERBS)
    obj = random.choice(NOUNS).lower()
    return f"{adj} {noun} {verb} {obj}."

# --- Mock Latency Endpoints ---
@app.get("/mock/{page_id}", response_class=HTMLResponse)
async def mock_page(page_id: int, delay: float = 0.05, size_kb: int = 10):
    """
    Mock endpoint that simulates network latency and serves dynamic HTML.
    - delay: float, time to sleep in seconds
    - size_kb: int, approximate page size in KB to simulate download payload
    """
    if delay > 0:
        await asyncio.sleep(delay)
        
    title = f"Mock Page #{page_id} - {random.choice(ADJECTIVES)} {random.choice(NOUNS)}"
    
    # Generate content of desired size
    paragraphs = []
    current_size = 0
    target_bytes = size_kb * 1024
    
    # Generate links to other mock pages to simulate crawler targets
    links = [f'<a href="/mock/{random.randint(1, 1000)}?delay={delay}">Simulated Subpage {i}</a>' for i in range(5)]
    links_html = "".join(f"<li>{link}</li>" for link in links)
    
    while current_size < target_bytes:
        sentence = generate_random_sentence()
        paragraphs.append(f"<p>{sentence}</p>")
        current_size += len(sentence) + 7 # accounts for p tag
        
    content_html = "\n".join(paragraphs)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{ font-family: sans-serif; padding: 20px; line-height: 1.6; background: #fafafa; color: #333; }}
        h1 {{ color: #4a5568; }}
        ul {{ margin-top: 15px; }}
        a {{ color: #3182ce; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <section>
        {content_html}
    </section>
    <hr>
    <h3>Discovered Internal Links</h3>
    <ul>
        {links_html}
    </ul>
</body>
</html>"""
    return html


# --- Benchmark SSE Event Stream Generator ---
def run_scraper_in_thread(mode, urls, max_workers, q):
    """
    Runs the selected scraper in a background thread and puts items into queue.
    """
    try:
        if mode == "sequential":
            scraper = SequentialScraper(urls, progress_callback=lambda idx, tot, res: q.put({
                "type": "progress", "mode": "sequential", "index": idx, "total": tot, "result": res
            }))
        elif mode == "threaded":
            scraper = ThreadedScraper(urls, max_workers=max_workers, progress_callback=lambda idx, tot, res: q.put({
                "type": "progress", "mode": "threaded", "index": idx, "total": tot, "result": res
            }))
        elif mode == "process":
            scraper = ProcessScraper(urls, max_workers=max_workers, progress_callback=lambda idx, tot, res: q.put({
                "type": "progress", "mode": "process", "index": idx, "total": tot, "result": res
            }))
        elif mode == "async":
            scraper = AsyncScraper(urls, max_workers=max_workers, progress_callback=lambda idx, tot, res: q.put({
                "type": "progress", "mode": "async", "index": idx, "total": tot, "result": res
            }))
        else:
            q.put({"type": "error", "error": f"Invalid mode: {mode}"})
            q.put(None)
            return

        # Start time measurement
        q.put({"type": "status", "mode": mode, "status": "started"})
        results, metrics = scraper.run()
        q.put({"type": "metrics", "mode": mode, "metrics": metrics})
        q.put({"type": "status", "mode": mode, "status": "completed"})
        
    except Exception as e:
        q.put({"type": "error", "mode": mode, "error": str(e)})
    finally:
        # If we are doing 'compare_all', we don't put None until the very last scraper completes
        pass

def run_all_scrapers_in_thread(urls, max_workers, q):
    """
    Runs all scrapers sequentially one after the other to generate comparative metrics.
    """
    modes = ["sequential", "threaded", "process", "async"]
    for mode in modes:
        run_scraper_in_thread(mode, urls, max_workers, q)
        # Small cooldown between runs
        time_to_wait = 0.5
        import time
        time.sleep(time_to_wait)
    q.put(None) # Sentinel to end the SSE stream


@app.get("/api/benchmark")
async def benchmark(
    mode: str = "sequential",
    pages: int = 50,
    delay: float = 0.05,
    workers: int = 10,
    request: Request = None
):
    """
    API Endpoint to initiate scraping benchmarks. Streams results via Server-Sent Events (SSE).
    """
    # Create target URLs
    # Using localhost:8000 specifically as we'll run uvicorn on port 8000
    urls = [f"http://127.0.0.1:8000/mock/{i}?delay={delay}" for i in range(1, pages + 1)]
    
    q = queue.Queue()
    
    if mode == "all":
        # Run all sequentially in background
        bg_thread = threading.Thread(target=run_all_scrapers_in_thread, args=(urls, workers, q))
    else:
        # Helper that wraps run_scraper_in_thread and appends Sentinel at end
        def single_run_wrapper():
            run_scraper_in_thread(mode, urls, workers, q)
            q.put(None)
        bg_thread = threading.Thread(target=single_run_wrapper)
        
    bg_thread.start()
    
    async def event_generator():
        while True:
            # Check client disconnection
            if request and await request.is_disconnected():
                break
                
            try:
                # Read from queue non-blocking to prevent locking async loop
                item = q.get_nowait()
                if item is None:
                    break
                yield f"data: {json.dumps(item)}\n\n"
            except queue.Empty:
                await asyncio.sleep(0.02)
                
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Mount static files (must be mounted after API routes to avoid matching overrides)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
