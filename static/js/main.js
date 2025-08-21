// --- Configuration & State Management ---
const socket = io();

let appState = {
    activeTab: 'health',
    history: {
        tps: [],
        gini: [],
        labels: [],
    },
    maxHistoryPoints: 50,
};

// --- Chart Instances ---
let tpsChart, giniChart;

// --- UI Rendering ---
function showTab(tabName) {
    // Hide all tabs
    document.getElementById('health-tab').classList.add('hidden');
    document.getElementById('security-tab').classList.add('hidden');
    document.getElementById('validators-tab').classList.add('hidden');

    // Deactivate all tab buttons
    document.querySelectorAll('.tab-button').forEach(button => button.classList.remove('active'));

    // Show the selected tab and activate its button
    document.getElementById(`${tabName}-tab`).classList.remove('hidden');
    document.querySelector(`button[onclick="showTab('${tabName}')"]`).classList.add('active');
    
    appState.activeTab = tabName;
}

function updateUI(data) {
    // Update connection status
    document.getElementById('connection-status-dot').className = 'status-dot status-online';
    document.getElementById('connection-status-text').textContent = 'Connected';
    document.getElementById('connection-status-text').className = 'text-sm text-green-400';
    document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();

    // --- Update Network Health KPIs ---
    const health = data.network_health;
    document.getElementById('latest-consensus-round').textContent = health.latest_consensus_round.toLocaleString(); // Renamed in backend to consensus_round
    document.getElementById('avg-round-time').textContent = `${health.avg_round_time.toFixed(2)} s`; // Renamed
    document.getElementById('tx-finality').textContent = `${health.transaction_finality.toFixed(2)} s`; // Renamed
    document.getElementById('active-participants').textContent = health.active_participants.toLocaleString(); // Renamed
    document.getElementById('total-network-nodes').textContent = health.total_network_nodes.toLocaleString(); // New KPI
    document.getElementById('total-master-nodes').textContent = health.total_master_nodes.toLocaleString(); // New KPI

    // --- Update Decentralization & Security KPIs ---
    const security = data.decentralization_security; // Renamed from 'security'
    document.getElementById('nakamoto-consensus').textContent = security.nakamoto_consensus;
    document.getElementById('nakamoto-stake').textContent = security.nakamoto_stake;
    document.getElementById('safety-violations').textContent = security.safety_violations_24h; // Now specifically safety violations
    document.getElementById('liveness-violations').textContent = security.liveness_violations_24h; // New field
    document.getElementById('total-blame-messages').textContent = security.total_blame_messages_24h; // New field
    
    // --- Update History & Charts ---
    const now = new Date();
    const timestamp = `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    
    if (appState.history.labels.length >= appState.maxHistoryPoints) {
        appState.history.labels.shift();
        appState.history.tps.shift();
        appState.history.gini.shift();
    }
    appState.history.labels.push(timestamp);
    appState.history.tps.push(health.realtime_tps);
    appState.history.gini.push(security.gini_coefficient);

    tpsChart.updateSeries([{ data: appState.history.tps }]);
    tpsChart.updateOptions({ xaxis: { categories: appState.history.labels } });
    
    giniChart.updateSeries([{ data: appState.history.gini }]);
    giniChart.updateOptions({ xaxis: { categories: appState.history.labels } });

    // --- Update Validator Table ---
    const tableBody = document.getElementById('validator-table-body');
    let tableHTML = '';
    data.validator_operations.forEach(v => { // Renamed from 'validators'
        let statusClass = '';
        let statusText = '';
        switch(v.status) {
            case 'online':
                statusClass = 'status-online';
                statusText = 'Online';
                break;
            case 'warning':
                statusClass = 'status-warning';
                statusText = 'Warning';
                break;
            case 'offline':
                statusClass = 'status-offline';
                statusText = 'Offline';
                break;
            case 'slashed':
                statusClass = 'status-offline'; // Using offline color for slashed
                statusText = 'Slashed 🔪';
                break;
            default:
                statusClass = 'status-warning';
                statusText = 'Unknown';
        }

        tableHTML += `
            <tr>
                <td><span class="status-dot ${statusClass}"></span> ${statusText}</td>
                <td class="font-mono text-sm">${v.id.substring(0, 12)}...${v.id.substring(v.id.length - 4)}</td>
                <td>${v.uptime_7d}%</td>
                <td class="${v.missed_consensus_rounds_24h > 0 ? 'text-yellow-400' : ''}">${v.missed_consensus_rounds_24h}</td>
                <td>${Math.round(v.total_stake).toLocaleString()}</td>
            </tr>
        `;
    });
    tableBody.innerHTML = tableHTML;
}

// --- Chart Initialization ---
function initializeCharts() {
    const commonOptions = {
        chart: {
            type: 'area',
            height: 350,
            toolbar: { show: false },
            zoom: { enabled: false },
            animations: { enabled: true, easing: 'linear', dynamicAnimation: { speed: 1000 } }
        },
        dataLabels: { enabled: false },
        stroke: { curve: 'smooth', width: 2 },
        grid: {
            borderColor: '#30363d',
            strokeDashArray: 4,
        },
        tooltip: {
            theme: 'dark',
        },
        xaxis: {
            categories: appState.history.labels,
            labels: {
                style: { colors: '#8b949e' },
                rotate: -45,
                hideOverlappingLabels: true,
            },
            axisBorder: { show: false },
            axisTicks: { show: false },
        },
        yaxis: {
            labels: {
                style: { colors: '#8b949e' },
                formatter: (val) => val.toFixed(2),
            }
        },
    };

    // TPS Chart
    const tpsOptions = {
        ...commonOptions,
        series: [{ name: 'TPS', data: appState.history.tps }],
        colors: ['#58a6ff'],
        fill: {
            type: 'gradient',
            gradient: {
                shade: 'dark',
                type: 'vertical',
                shadeIntensity: 0.5,
                gradientToColors: ['#161b22'],
                inverseColors: true,
                opacityFrom: 0.7,
                opacityTo: 0.1,
                stops: [0, 100]
            }
        },
        yaxis: { ...commonOptions.yaxis, title: { text: 'Transactions Per Second', style: { color: '#8b949e' } } }
    };
    tpsChart = new ApexCharts(document.querySelector("#tps-chart-container"), tpsOptions);
    tpsChart.render();
    
    // Gini Chart
    const giniOptions = {
        ...commonOptions,
        series: [{ name: 'Gini', data: appState.history.gini }],
        colors: ['#e362ff'],
        fill: {
            type: 'gradient',
            gradient: {
                shade: 'dark',
                type: 'vertical',
                shadeIntensity: 0.5,
                gradientToColors: ['#161b22'],
                inverseColors: true,
                opacityFrom: 0.7,
                opacityTo: 0.1,
                stops: [0, 100]
            }
        },
        yaxis: { ...commonOptions.yaxis, min: 0, max: 1, title: { text: 'Coefficient', style: { color: '#8b949e' } } }
    };
    giniChart = new ApexCharts(document.querySelector("#gini-chart-container"), giniOptions);
    giniChart.render();
}

// --- Main Application Logic ---
document.addEventListener('DOMContentLoaded', () => {
    initializeCharts();
    
    socket.on('connect', () => {
        console.log('Connected to server via Socket.IO');
        document.getElementById('connection-status-dot').className = 'status-dot status-online';
        document.getElementById('connection-status-text').textContent = 'Connected';
        document.getElementById('connection-status-text').className = 'text-sm text-green-400';
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        document.getElementById('connection-status-dot').className = 'status-dot status-offline';
        document.getElementById('connection-status-text').textContent = 'Disconnected';
        document.getElementById('connection-status-text').className = 'text-sm text-red-400';
    });

    socket.on('network_update', (data) => {
        updateUI(data);
    });
});