# ScrapeX 🚀

**ScrapeX** is a high-performance concurrent scraper performance analyzer and dashboard. It allows you to benchmark and compare the efficiency of different scraping paradigms in Python (Sequential, Multi-Threaded, Multi-Processed, and Asynchronous) in real time.

With a beautiful, light-themed web dashboard featuring live performance charts, real-time logging, and interactive controls, ScrapeX is perfect for learning and demonstrating concurrent Python performance characteristics.

---

## Key Features

- **Four Scraping Engines**:
  - 🧵 **Sequential**: Single-threaded baseline scraper.
  - 🧬 **Multi-Threaded**: Leveraging `ThreadPoolExecutor` for concurrent I/O-bound requests.
  - 🖥️ **Multi-Processed**: Utilizing `ProcessPoolExecutor` to run CPU-bound parsing tasks in parallel.
  - ⚡ **Asynchronous**: Built using `asyncio` and `aiohttp` for extreme scale asynchronous concurrency.
- **Real-Time Streaming Dashboard**: Streams logs and status updates from the scraping engines to the front-end using Server-Sent Events (SSE).
- **Interactive Visualizations**: Renders dynamic performance graphs (Duration and Throughput) using Chart.js.
- **Custom Latency Simulator**: Built-in mock HTTP server that simulates network latency and serves mock pages of custom sizes for realistic local benchmarks.
- **CLI Interface**: Includes a robust command-line benchmark tool for running tests directly in your terminal.

---

## Technology Stack

- **Backend**: Python 3, FastAPI, Uvicorn, Asyncio, Aiohttp, Requests, BeautifulSoup4
- **Frontend**: Vanilla HTML5, Vanilla CSS3 (Premium light theme styling), JavaScript (ES6+), Chart.js
- **CLI**: Tabulate

---

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/scrapex.git
   cd scrapex
   ```

2. **Install dependencies**:
   Make sure you have Python 3.8+ installed. Install the required libraries using `pip`:
   ```bash
   pip install -r requirements.txt
   ```

---

## Running the Web Dashboard

1. **Start the FastAPI server**:
   ```bash
   python server.py
   ```

2. **Open the Dashboard**:
   Once the server starts up, open your web browser and navigate to:
   [http://127.0.0.1:8000](http://127.0.0.1:8000)

3. **Configure and Run Benchmarks**:
   - Set the number of pages to scrape.
   - Adjust the simulated latency (seconds) to see how network delays affect concurrent performance.
   - Set the concurrency worker limit.
   - Run individual scrapers or click **Run All & Compare** to execute all four sequentially and compare results side-by-side.

---

## Running the CLI Tool

If you prefer testing directly in the terminal, you can use the command-line utility. It starts the local mock latency server automatically and prints a formatted performance table at the end.

```bash
python run_cli.py --pages 50 --delay 0.05 --workers 10
```

### CLI Command Options:
- `--pages`: Number of mock pages to download (default: `50`).
- `--delay`: Simulated latency delay (seconds) per page (default: `0.05`).
- `--workers`: Concurrency worker limit for Threaded, Process, and Async modes (default: `10`).

---

## Project Structure

```
.
├── scrapers.py         # The scraper engines (Sequential, Threaded, Process, Async)
├── server.py           # FastAPI mock target server and SSE benchmark stream endpoints
├── run_cli.py          # Terminal CLI comparison tool
├── requirements.txt    # Python dependencies
└── static/             # Frontend assets
    ├── index.html      # Dashboard dashboard page
    ├── style.css       # Clean, modern light theme styling
    └── app.js          # Chart.js initialization, SSE client, and event handlers
```

---

## License

This project is open-source and licensed under the [MIT License](LICENSE).
