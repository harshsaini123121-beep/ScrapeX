let timeChart = null;
let throughputChart = null;
let eventSource = null;

// Color maps matching CSS root variables
const COLORS = {
    sequential: '#0d9488',
    threaded: '#059669',
    process: '#d97706',
    async: '#7c3aed'
};

const MODE_LABELS = {
    sequential: 'Sequential',
    threaded: 'Multi-Threaded',
    process: 'Multi-Processed',
    async: 'Asynchronous'
};

// Initialize Charts on Load
document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    logToTerminal("System ready. Configure parameters and select a scraper mode.", "info");
});

function initCharts() {
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: '#ffffff',
                titleColor: '#2b1b17',
                bodyColor: '#8c6e63',
                borderColor: '#e7e0d5',
                borderWidth: 1,
                padding: 10
            }
        },
        scales: {
            x: {
                grid: { color: '#e7e0d5' },
                ticks: { color: '#8c6e63', font: { family: 'Outfit' } }
            },
            y: {
                grid: { color: '#e7e0d5' },
                ticks: { color: '#8c6e63', font: { family: 'Outfit' } }
            }
        }
    };

    // 1. Time Chart
    const ctxTime = document.getElementById('timeChart').getContext('2d');
    timeChart = new Chart(ctxTime, {
        type: 'bar',
        data: {
            labels: ['Sequential', 'Threaded', 'Process', 'Asyncio'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [COLORS.sequential, COLORS.threaded, COLORS.process, COLORS.async],
                borderRadius: 8,
                borderWidth: 0,
                barThickness: 35
            }]
        },
        options: {
            ...commonOptions,
            scales: {
                ...commonOptions.scales,
                y: {
                    ...commonOptions.scales.y,
                    title: {
                        display: true,
                        text: 'Execution Time (Seconds)',
                        color: '#8c6e63',
                        font: { family: 'Outfit', size: 12 }
                    }
                }
            }
        }
    });

    // 2. Throughput Chart
    const ctxThroughput = document.getElementById('throughputChart').getContext('2d');
    throughputChart = new Chart(ctxThroughput, {
        type: 'bar',
        data: {
            labels: ['Sequential', 'Threaded', 'Process', 'Asyncio'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [COLORS.sequential, COLORS.threaded, COLORS.process, COLORS.async],
                borderRadius: 8,
                borderWidth: 0,
                barThickness: 35
            }]
        },
        options: {
            ...commonOptions,
            scales: {
                ...commonOptions.scales,
                y: {
                    ...commonOptions.scales.y,
                    title: {
                        display: true,
                        text: 'Requests / Second',
                        color: '#8c6e63',
                        font: { family: 'Outfit', size: 12 }
                    }
                }
            }
        }
    });
}

// Log Writer
function logToTerminal(text, type = "info") {
    const terminal = document.getElementById("log-terminal");
    const cleanText = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
    let logClass = "log-info";
    
    if (type === "sequential" || type === "threaded" || type === "process" || type === "async") {
        logClass = `log-${type}`;
    } else if (type === "success") {
        logClass = "log-success";
    } else if (type === "error") {
        logClass = "log-error";
    }
    
    const timestamp = new Date().toLocaleTimeString();
    const line = `<span class="log-info">[${timestamp}]</span> <span class="${logClass}">${cleanText}</span>\n`;
    
    terminal.innerHTML += line;
    terminal.scrollTop = terminal.scrollHeight;
}

function clearLogs() {
    document.getElementById("log-terminal").innerHTML = `<code>[i] Terminal cleared. Ready.</code>\n`;
}

// Toggle Buttons State
function setControlsDisabled(disabled) {
    const inputs = ['pages', 'delay', 'workers'];
    inputs.forEach(id => document.getElementById(id).disabled = disabled);

    const buttons = ['btn-seq', 'btn-threaded', 'btn-process', 'btn-async', 'btn-compare'];
    buttons.forEach(id => document.getElementById(id).disabled = disabled);
}

// Clear detail table
function clearTable() {
    const tbody = document.querySelector("#results-table tbody");
    tbody.innerHTML = '';
}

// Format size
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const dm = 2;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Main SSE benchmark trigger
function startBenchmark(mode) {
    if (eventSource) {
        eventSource.close();
    }

    const pages = parseInt(document.getElementById("pages").value);
    const delay = parseFloat(document.getElementById("delay").value);
    const workers = parseInt(document.getElementById("workers").value);

    // Reset layout
    setControlsDisabled(true);
    clearTable();
    
    // Reset individual running animations
    document.querySelectorAll(".metric-card").forEach(c => c.classList.remove("running"));
    
    if (mode === "all") {
        logToTerminal(`Initiating full comparative run of all 4 scrapers against mock target (${pages} URLs, latency delay: ${delay}s)...`, "info");
    } else {
        logToTerminal(`Starting single run of scraper: [${MODE_LABELS[mode].toUpperCase()}] with ${workers} workers...`, mode);
        document.getElementById(`metric-${mode}`).classList.add("running");
    }

    // Reset progress bar
    updateProgressBar(0, pages, mode === "all" ? "sequential" : mode);

    // Build URL query
    const url = `/api/benchmark?mode=${mode}&pages=${pages}&delay=${delay}&workers=${workers}`;
    
    eventSource = new EventSource(url);
    
    let completedScrapers = 0;

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === "status") {
            const currentMode = data.mode;
            if (data.status === "started") {
                logToTerminal(`[${MODE_LABELS[currentMode].toUpperCase()}] Engine started...`, currentMode);
                document.querySelectorAll(".metric-card").forEach(c => c.classList.remove("running"));
                document.getElementById(`metric-${currentMode}`).classList.add("running");
            } else if (data.status === "completed") {
                logToTerminal(`[${MODE_LABELS[currentMode].toUpperCase()}] Engine execution finished.`, "success");
            }
        }
        
        else if (data.type === "progress") {
            const result = data.result;
            const currentMode = data.mode;
            
            // Add row to table
            addTableRow(data.index, currentMode, result);
            
            // Update Progress Bar
            updateProgressBar(data.index, data.total, currentMode);
            
            // Write to logs terminal
            const latencyStr = result.time_taken ? `${result.time_taken}s` : 'failed';
            const infoStr = result.error 
                ? `ERR: ${result.error}` 
                : `Fetched title: "${result.title}" (${formatBytes(result.data_size)}) in ${latencyStr}`;
            
            logToTerminal(`[${MODE_LABELS[currentMode].toUpperCase()}] #${data.index}/${data.total}: ${result.url} - ${infoStr}`, currentMode);
        }
        
        else if (data.type === "metrics") {
            const metrics = data.metrics;
            const currentMode = data.mode;
            
            logToTerminal(`[Metrics] ${metrics.mode} completed in ${metrics.total_time}s (${metrics.req_per_sec} req/s). Success rate: ${metrics.success_count}/${metrics.success_count + metrics.failure_count}`, "success");
            
            // Update Card
            updateMetricCard(currentMode, metrics.total_time);
            
            // Update Charts
            updateCharts(currentMode, metrics.total_time, metrics.req_per_sec);
        }
        
        else if (data.type === "error") {
            logToTerminal(`[Error] ${data.error}`, "error");
        }
    };

    eventSource.onerror = (err) => {
        logToTerminal("Stream connection closed.", "info");
        eventSource.close();
        setControlsDisabled(false);
        document.querySelectorAll(".metric-card").forEach(c => c.classList.remove("running"));
        updateProgressBar(100, 100, "success");
        document.getElementById("progress-mode-label").innerText = "Benchmark Job Completed";
    };
}

function updateProgressBar(index, total, mode) {
    const percent = Math.round((index / total) * 100);
    const fill = document.getElementById("progress-bar-fill");
    const label = document.getElementById("progress-mode-label");
    const details = document.getElementById("progress-percentage");
    
    fill.style.width = `${percent}%`;
    details.innerText = `${percent}%`;
    
    if (mode === "success") {
        label.innerText = "Completed Benchmarks";
        fill.style.background = "linear-gradient(90deg, #10b981 0%, #059669 100%)";
    } else {
        label.innerText = `Active Scraper: [${MODE_LABELS[mode].toUpperCase()}]`;
        // Match progress bar theme color
        fill.style.background = COLORS[mode];
    }
}

function updateMetricCard(mode, time) {
    const card = document.getElementById(`metric-${mode}`);
    if (card) {
        const valEl = card.querySelector(".metric-value");
        valEl.innerText = `${time.toFixed(3)}`;
    }
}

function addTableRow(index, mode, result) {
    const tbody = document.querySelector("#results-table tbody");
    
    // Remove default empty row
    const emptyRow = tbody.querySelector(".empty-row");
    if (emptyRow) {
        tbody.removeChild(emptyRow);
    }
    
    const row = document.createElement("tr");
    
    const indexTd = document.createElement("td");
    indexTd.innerText = index;
    
    const urlTd = document.createElement("td");
    urlTd.innerText = result.url.split('?')[0]; // Strip delay query param for display
    urlTd.style.fontFamily = 'monospace';
    urlTd.style.fontSize = '0.8rem';
    
    const modeTd = document.createElement("td");
    modeTd.innerHTML = `<span class="badge badge-mode ${mode}">${MODE_LABELS[mode]}</span>`;
    
    const statusTd = document.createElement("td");
    const badgeClass = result.status_code === 200 ? 'badge-200' : 'badge-err';
    statusTd.innerHTML = `<span class="badge ${badgeClass}">${result.status_code || 'Err'}</span>`;
    
    const sizeTd = document.createElement("td");
    sizeTd.innerText = formatBytes(result.data_size);
    
    const latencyTd = document.createElement("td");
    latencyTd.innerText = result.time_taken ? `${result.time_taken.toFixed(3)}s` : '-';
    
    const titleTd = document.createElement("td");
    titleTd.innerText = result.title || result.error || 'N/A';
    titleTd.style.maxWidth = '250px';
    titleTd.style.overflow = 'hidden';
    titleTd.style.textOverflow = 'ellipsis';
    titleTd.style.whiteSpace = 'nowrap';
    
    row.appendChild(indexTd);
    row.appendChild(urlTd);
    row.appendChild(modeTd);
    row.appendChild(statusTd);
    row.appendChild(sizeTd);
    row.appendChild(latencyTd);
    row.appendChild(titleTd);
    
    // Limit DOM rows size to prevent layout lag on massive benchmarks
    if (tbody.children.length > 200) {
        tbody.removeChild(tbody.firstChild);
    }
    
    tbody.appendChild(row);
    
    // Auto-scroll table container to bottom to show live updates
    const container = document.querySelector(".table-container");
    container.scrollTop = container.scrollHeight;
}

function updateCharts(mode, time, throughput) {
    const indices = {
        sequential: 0,
        threaded: 1,
        process: 2,
        async: 3
    };
    
    const idx = indices[mode];
    
    // Update Time Chart
    timeChart.data.datasets[0].data[idx] = time;
    timeChart.update();
    
    // Update Throughput Chart
    throughputChart.data.datasets[0].data[idx] = throughput;
    throughputChart.update();
}
