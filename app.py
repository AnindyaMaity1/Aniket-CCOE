# 1. Apply monkey patch first to prevent context errors with Flask.
import eventlet
eventlet.monkey_patch()

# 2. Then, import other libraries.
import socketio
import random
import time
from threading import Event
from flask import Flask, render_template

# Create a Socket.IO server
sio = socketio.Server(async_mode='eventlet', cors_allowed_origins='*')
# Create a Flask application
app = Flask(__name__)
# Wrap the Flask application with the Socket.IO middleware
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

# --- Global State & Mock Data Simulation ---
# In a real-world scenario, this data would be fetched from an external API or a database.
mock_backend_state = {
    "latest_consensus_round": 64102831,
    "round_times": [2.0] * 100,  # Simulating the 2-second block time from paper
    "active_participants": set(),
    "total_network_nodes": 1500, # Initial mock for total nodes in the network
    "total_master_nodes": 108, # Fixed as per the paper
    "nakamoto_stake": 18, # From the paper, 18 for stake (initial value)
    "nakamoto_consensus": 72, # From the paper, 72 for consensus (fixed)
    "gini_coefficient": 0.45,
    "safety_violations_24h": 0, # Cryptographically provable violations
    "liveness_violations_24h": 0, # Based on blame messages
    "total_blame_messages_24h": 0,
    "validators": [],
}

# Pre-generate mock validators with initial states
def generate_mock_validators(count):
    validators = []
    for i in range(count):
        uptime = 98.0 + random.random() * 2
        validators.append({
            "id": f"xdc{[random.choice('0123456789abcdef') for _ in range(40)]}",
            "uptime_7d": round(uptime, 2),
            "missed_consensus_rounds_24h": 0,
            "total_stake": 10000000 + (random.random() - 0.5) * 2000000,
            "status": "online" # online, warning (missed rounds), offline (many missed), slashed
        })
    return validators

mock_backend_state["validators"] = generate_mock_validators(mock_backend_state["total_master_nodes"])

def get_mock_api_data():
    """Simulates fetching data from a backend source based on the paper's metrics."""
    avg_round_time = sum(mock_backend_state["round_times"]) / len(mock_backend_state["round_times"])
    realtime_tps = (random.randint(50, 200)) / avg_round_time # Transactions per second

    # Sort validators by stake (descending) for calculating Nakamoto Coefficient (Stake)
    sorted_validators = sorted(mock_backend_state["validators"], key=lambda v: v["total_stake"], reverse=True)
    
    # Calculate Nakamoto Coefficient (Stake) dynamically for mock data
    total_stake = sum(v["total_stake"] for v in sorted_validators)
    # The paper states > 1/3 to halt the network. So, we look for sum > total_stake / 3
    threshold_stake = total_stake / 3.0
    current_stake_sum = 0
    nakamoto_stake_count = 0
    for validator in sorted_validators:
        current_stake_sum += validator["total_stake"]
        nakamoto_stake_count += 1
        if current_stake_sum > threshold_stake:
            break
    
    return {
        "network_health": {
            "latest_consensus_round": mock_backend_state["latest_consensus_round"],
            "avg_round_time": round(avg_round_time, 2),
            "transaction_finality": round(avg_round_time * 3, 2), # 3 BATs for finality
            "realtime_tps": round(realtime_tps, 1),
            "active_participants": len(mock_backend_state["active_participants"]),
            "total_network_nodes": mock_backend_state["total_network_nodes"],
            "total_master_nodes": mock_backend_state["total_master_nodes"],
        },
        "decentralization_security": {
            "nakamoto_consensus": mock_backend_state["nakamoto_consensus"], # Fixed at 72 as per paper
            "nakamoto_stake": nakamoto_stake_count, # Dynamically calculated based on mock stake distribution
            "safety_violations_24h": mock_backend_state["safety_violations_24h"],
            "liveness_violations_24h": mock_backend_state["liveness_violations_24h"],
            "total_blame_messages_24h": mock_backend_state["total_blame_messages_24h"],
            "gini_coefficient": round(mock_backend_state["gini_coefficient"], 4),
        },
        "validator_operations": random.sample(mock_backend_state["validators"], min(20, len(mock_backend_state["validators"]))) # Send a random subset
    }

def update_network_state():
    """Simulates changes in the network state based on XDPoS 2.0 dynamics."""
    time_since_last_round = 1.8 + random.random() * 0.4
    mock_backend_state["latest_consensus_round"] += 1
    mock_backend_state["round_times"].pop(0)
    mock_backend_state["round_times"].append(time_since_last_round)

    # Simulate new transactions leading to active participants
    tx_count = random.randint(10, 50)
    for _ in range(tx_count):
        mock_backend_state["active_participants"].add(f"xdc{random.getrandbits(160):x}")

    # Simulate total network nodes fluctuation (e.g., nodes joining/leaving)
    mock_backend_state["total_network_nodes"] += random.randint(-5, 5)
    mock_backend_state["total_network_nodes"] = max(108, mock_backend_state["total_network_nodes"]) # At least master nodes

    # Simulate Gini coefficient fluctuation
    mock_backend_state["gini_coefficient"] += (random.random() - 0.5) * 0.001
    mock_backend_state["gini_coefficient"] = max(0.4, min(0.5, mock_backend_state["gini_coefficient"]))
    
    # Simulate safety violations (rare, cryptographically provable)
    if random.random() < 0.0005: # Very rare event, maybe once every 2000 rounds
        mock_backend_state["safety_violations_24h"] += 1
        print("🚨 Simulated SAFETY VIOLATION detected! Cryptographic proof available.")
        # Trigger a slash for a random validator
        if mock_backend_state["validators"]:
            slashed_validator = random.choice(mock_backend_state["validators"])
            slashed_validator["status"] = "slashed"
            slashed_validator["total_stake"] = slashed_validator["total_stake"] * 0.95 # Mock slashing of stake
            print(f"🔪 Validator {slashed_validator['id'][:12]}... SLASHED due to safety violation.")


    # Simulate liveness violations (more frequent, lead to blame messages)
    if random.random() < 0.01: # 1% chance per round
        mock_backend_state["liveness_violations_24h"] += 1
        mock_backend_state["total_blame_messages_24h"] += random.randint(1, 5) # Blame messages
        print("⚠️ Simulated LIVENESS VIOLATION detected! Blame messages recorded.")

    # Simulate validator status changes based on performance
    for v in mock_backend_state["validators"]:
        # Only update status for non-slashed validators
        if v["status"] != "slashed":
            # Simulate missed rounds
            if random.random() < 0.02: # 2% chance a validator misses a round
                v["missed_consensus_rounds_24h"] += 1
                v["uptime_7d"] = max(90.0, v["uptime_7d"] - random.uniform(0.01, 0.1))
            
            # Reset missed rounds periodically (e.g., every few hundred rounds)
            if mock_backend_state["latest_consensus_round"] % 500 == 0:
                 v["missed_consensus_rounds_24h"] = 0
                 v["uptime_7d"] = 98.0 + random.random() * 2 # Reset uptime after period

            # Update status based on missed rounds
            if v["missed_consensus_rounds_24h"] > 5 or v["uptime_7d"] < 95.0:
                v["status"] = "offline"
            elif v["missed_consensus_rounds_24h"] > 0:
                v["status"] = "warning"
            else:
                v["status"] = "online"


# --- Background Thread for Data Generation ---
# The thread variable is now set to None initially and is of EventletThread type
thread = None
thread_stop_event = Event()

def background_task():
    """This task runs in the background and emits data to all connected clients."""
    while not thread_stop_event.is_set():
        update_network_state()
        data = get_mock_api_data()
        sio.emit('network_update', data)
        sio.sleep(2)  # Update every 2 seconds, matching paper's suggested round time

# --- Socket.IO Event Handlers ---
@sio.event
def connect(sid, environ):
    global thread
    print(f'Client connected: {sid}')
    # FIX: Correctly check if the background task has been started
    # It will be None the first time a client connects, and an EventletThread object afterwards.
    if thread is None:
        print("Starting background data stream thread...")
        thread = sio.start_background_task(background_task)

@sio.event
def disconnect(sid):
    print(f'Client disconnected: {sid}')

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    print("Starting Flask and Socket.IO server...")
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 5000)), app)