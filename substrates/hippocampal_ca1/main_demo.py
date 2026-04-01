#!/usr/bin/env python3
"""
CA1 Hippocampus Full System Demo
Complete integration of all modules

Usage:
    python main_demo.py --mode full
    python main_demo.py --mode laminar
    python main_demo.py --mode dynamics
    python main_demo.py --mode ai
"""
import numpy as np
import sys
import argparse
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from data.biophysical_parameters import get_default_parameters
from core.laminar_structure import ZINBLayerModel, CellData, SubregionClassifier
from core.neuron_model import CA1Population, NetworkMode
from plasticity.calcium_plasticity import SynapseManager
from ai_integration.memory_module import LLMWithCA1Memory
from validation.validators import CA1Validator


def demo_laminar_inference():
    """Demo 1: Laminar structure inference"""
    print("\n" + "=" * 70)
    print("DEMO 1: LAMINAR STRUCTURE INFERENCE")
    print("=" * 70)

    get_default_parameters()

    # Generate synthetic cells
    N = 1000
    cells = []

    print(f"\nGenerating {N} synthetic cells with 4-layer structure...")

    for i in range(N):
        z = np.random.rand()
        s = np.random.rand()

        # Layer-dependent expression (ground truth)
        layer = min(int(z * 4), 3)

        # Transcript counts (primary marker + noise)
        transcripts = np.zeros(4)
        transcripts[layer] = np.random.poisson(5)  # Strong signal

        # Low cross-layer expression
        for k in range(4):
            if k != layer:
                if np.random.rand() < 0.02:  # 2% cross-expression
                    transcripts[k] = np.random.poisson(1)

        cells.append(
            CellData(x=np.random.rand(), y=np.random.rand(), z=z, s=s, transcripts=transcripts)
        )

    # Fit ZINB model
    print("Fitting ZINB layer model...")
    model = ZINBLayerModel()
    q = model.fit_em(cells, max_iter=30)

    # Assign layers
    assignments = model.assign_layers(cells)
    print(f"\nLayer distribution: {np.bincount(assignments)}")

    # Validate
    from validation.validators import validate_laminar_structure

    depths = np.array([c.z for c in cells])
    transcripts = np.array([c.transcripts for c in cells])
    thresholds = {0: 2.0, 1: 2.0, 2: 2.0, 3: 2.0}

    metrics = validate_laminar_structure(assignments, depths, transcripts, thresholds)

    print("\n--- Validation Results ---")
    print(f"Mutual Information I(L;z): {metrics['mutual_information']:.3f}")
    print(f"  p-value: {metrics['mi_pvalue']:.4f}")
    print(f"Coexpression Rate CE: {metrics['coexpression_rate']:.3f} (≤ 0.05 required)")
    print(f"Stability σ(MI): {metrics['mi_std']:.3f}")
    print(f"\n{'✓ PASS' if metrics['pass_overall'] else '✗ FAIL'}")

    # Subregion classification
    print("\n--- Subregion Classification ---")
    classifier = SubregionClassifier()
    subregion_map = classifier.create_subregion_map(cells, assignments)

    for name, positions in subregion_map.items():
        if positions:
            print(
                f"{name}: {len(positions)} positions (s ∈ [{min(positions):.2f}, {max(positions):.2f}])"
            )


def demo_network_dynamics():
    """Demo 2: Two-compartment network with plasticity"""
    print("\n" + "=" * 70)
    print("DEMO 2: NETWORK DYNAMICS + PLASTICITY")
    print("=" * 70)

    params = get_default_parameters()

    # Create population
    N = 100
    layer_assignments = np.random.randint(0, 4, N)

    print(f"\nCreating population of {N} neurons...")
    print(f"Layer distribution: {np.bincount(layer_assignments)}")

    pop = CA1Population(N, layer_assignments, params)

    # Create sparse connectivity
    p_connect = 0.1
    connectivity = np.random.rand(N, N) < p_connect
    np.fill_diagonal(connectivity, False)

    # Initial weights (power-law)
    initial_weights = np.random.lognormal(0, 0.5, (N, N)) * connectivity
    initial_weights = np.clip(initial_weights, 0.01, 10.0)

    print(f"Connectivity: {connectivity.sum()} / {N*N} synapses ({connectivity.mean()*100:.1f}%)")

    # Create synapse manager
    syn_manager = SynapseManager(connectivity, initial_weights, params)
    syn_manager.set_learning_mode("learning")

    # Simulate
    T = 1000.0  # ms
    dt = 0.1
    n_steps = int(T / dt)

    print(f"\nSimulating {T} ms...")

    spike_counts = np.zeros(N)

    for step in range(n_steps):
        # Get current weights
        W = syn_manager.get_weight_matrix()

        # Compute synaptic inputs
        synaptic_inputs = np.zeros((N, 4))

        # Simple feed-forward + recurrent
        for i in range(N):
            # Excitatory input to dendrite from previous layer
            if layer_assignments[i] > 0:
                prev_layer = layer_assignments[i] - 1
                prev_neurons = np.where(layer_assignments == prev_layer)[0]

                for j in prev_neurons:
                    if connectivity[i, j]:
                        synaptic_inputs[i, 1] += W[i, j] * (np.random.rand() < 0.01)

        # Network step
        spikes = pop.step(synaptic_inputs, mode=NetworkMode.THETA)

        for s in spikes:
            spike_counts[s] += 1

        # Update synapses
        if spikes and (step % 10 == 0):  # Update every 1 ms
            voltages_dend = pop.get_voltages(compartment="dendrite")
            syn_manager.update(spikes, voltages_dend, modulatory_signal=1.0)

    # Homeostatic scaling
    syn_manager.apply_homeostasis()

    # Compute firing rates
    rates = spike_counts / (T / 1000.0)  # Hz

    print("\n--- Population Statistics ---")
    print(f"Mean firing rate: {np.mean(rates):.2f} ± {np.std(rates):.2f} Hz")
    print(f"Active neurons: {np.sum(spike_counts > 0)} / {N}")

    # Validate stability
    from validation.validators import validate_dynamic_stability

    W_final = syn_manager.get_weight_matrix()
    metrics = validate_dynamic_stability(W_final, rates)

    print("\n--- Stability Validation ---")
    print(f"Spectral radius ρ(W): {metrics['spectral_radius']:.3f} (< 1.0 required)")
    print(f"Max firing rate: {metrics['max_firing_rate']:.2f} Hz")
    print(f"\n{'✓ PASS' if metrics['pass'] else '✗ FAIL'}")


def demo_ai_integration():
    """Demo 3: AI memory module"""
    print("\n" + "=" * 70)
    print("DEMO 3: AI INTEGRATION - CA1 MEMORY FOR LLM")
    print("=" * 70)

    params = get_default_parameters()

    # Create LLM wrapper with CA1 memory
    model = LLMWithCA1Memory(params.ai)

    print(f"\nMemory capacity: {params.ai.memory_size} slots")
    print(f"Key dimension: {params.ai.key_dim}")
    print(f"Value dimension: {params.ai.value_dim}")

    # Simulate encoding phase (online learning)
    print("\n--- Encoding Phase (Online) ---")
    n_events = 200

    for i in range(n_events):
        # Simulate LLM hidden state
        h_t = np.random.randn(params.ai.d_model)
        v_t = np.random.randn(params.ai.value_dim)

        # Spatial position (for novelty)
        position = np.random.rand(2)

        # Process
        model.process_step(h_t, v_t, position)

    print(f"Stored events: {model.memory.n_stored}")

    # Simulate retrieval
    print("\n--- Retrieval Phase ---")
    n_queries = 10

    for i in range(n_queries):
        query_h = np.random.randn(params.ai.d_model)
        enhanced_h = model.retrieve_and_fuse(query_h)

        if i == 0:
            print(f"Query shape: {query_h.shape}")
            print(f"Enhanced shape: {enhanced_h.shape}")
            print(f"Fusion successful: {enhanced_h.shape == query_h.shape}")

    # Consolidation (offline replay)
    print("\n--- Consolidation (Offline Replay) ---")
    replayed = model.consolidate(n_episodes=50)
    print(f"Replayed episodes: {len(replayed)}")
    print(f"Replay indices: {replayed[:10]}...")

    # Evaluate retrieval quality
    from ai_integration.memory_module import evaluate_retrieval_quality

    # Generate test queries
    test_queries = [np.random.randn(params.ai.d_model) for _ in range(20)]
    ground_truth = np.random.randint(0, model.memory.n_stored, 20)

    metrics = evaluate_retrieval_quality(model.memory, test_queries, ground_truth)

    print("\n--- Retrieval Metrics ---")
    print(f"Precision@{params.ai.top_k}: {metrics['precision@k']:.3f}")
    print(f"Recall@{params.ai.top_k}: {metrics['recall@k']:.3f}")


def demo_full_system():
    """Demo 4: Full integrated system with validation"""
    print("\n" + "=" * 70)
    print("DEMO 4: FULL SYSTEM INTEGRATION")
    print("=" * 70)

    params = get_default_parameters()

    # 1. Generate laminar structure
    print("\n[1/5] Generating laminar structure...")
    N_cells = 500
    cells = []

    for i in range(N_cells):
        z = np.random.rand()
        s = np.random.rand()
        layer = min(int(z * 4), 3)

        transcripts = np.zeros(4)
        transcripts[layer] = np.random.poisson(5)

        cells.append(
            CellData(x=np.random.rand(), y=np.random.rand(), z=z, s=s, transcripts=transcripts)
        )

    model_laminar = ZINBLayerModel()
    q = model_laminar.fit_em(cells, max_iter=20)
    layer_assignments = model_laminar.assign_layers(cells)

    # 2. Create neural population
    print("[2/5] Creating neural population...")
    N = 100
    layer_assign_neurons = layer_assignments[:N]

    pop = CA1Population(N, layer_assign_neurons, params)

    # 3. Simulate dynamics
    print("[3/5] Simulating network dynamics...")
    connectivity = np.random.rand(N, N) < 0.1
    np.fill_diagonal(connectivity, False)
    initial_weights = np.random.lognormal(0, 0.5, (N, N)) * connectivity

    syn_manager = SynapseManager(connectivity, initial_weights, params)

    spike_times = {i: [] for i in range(N)}

    for step in range(5000):  # 500 ms
        t = step * 0.1
        # Weight matrix available via syn_manager.get_weight_matrix() if needed

        synaptic_inputs = np.zeros((N, 4))
        spikes = pop.step(synaptic_inputs)

        for s in spikes:
            spike_times[s].append(t)

        if spikes and (step % 10 == 0):
            voltages_dend = pop.get_voltages(compartment="dendrite")
            syn_manager.update(spikes, voltages_dend, modulatory_signal=1.0)

    # 4. AI integration
    print("[4/5] Testing AI memory module...")
    ai_model = LLMWithCA1Memory(params.ai)

    for i in range(100):
        h_t = np.random.randn(params.ai.d_model)
        v_t = np.random.randn(params.ai.value_dim)
        ai_model.process_step(h_t, v_t)

    # 5. Comprehensive validation
    print("[5/5] Running comprehensive validation...")

    validator = CA1Validator()

    # Prepare validation data
    depths = np.array([c.z for c in cells])
    transcripts = np.array([c.transcripts for c in cells])

    # Generate phase precession data
    spike_phases = []
    positions = []
    for i, times in spike_times.items():
        if len(times) > 5:
            phases = np.array(times) * 0.05 % (2 * np.pi)  # Mock theta phase
            pos = np.linspace(0, 1, len(times))
            spike_phases.extend(phases)
            positions.extend(pos)

    # Fractal events
    events_fractal = []
    for i, times in spike_times.items():
        for t in times:
            phase = t * 0.05 % (2 * np.pi)
            events_fractal.append([t, phase])
    events_fractal = np.array(events_fractal) if events_fractal else np.zeros((0, 2))

    # Firing rates
    firing_rates = np.array([len(times) / 0.5 for times in spike_times.values()])  # Hz

    model_data = {
        "layer_assignments": layer_assignments[:N_cells],
        "depths": depths,
        "transcripts": transcripts,
        "spike_phases": np.array(spike_phases),
        "positions": np.array(positions),
        "events_fractal": events_fractal,
        "W_matrix": syn_manager.get_weight_matrix(),
        "firing_rates": firing_rates,
        "sequences": {"online": list(range(20)), "replay": list(range(20))[::-1]},
    }

    validator.run_all_gates(model_data)
    validator.print_report()

    print("\n" + "=" * 70)
    print("FULL SYSTEM DEMO COMPLETE")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="CA1 Hippocampus System Demo")
    parser.add_argument(
        "--mode",
        type=str,
        default="full",
        choices=["full", "laminar", "dynamics", "ai"],
        help="Demo mode to run",
    )

    args = parser.parse_args()

    np.random.seed(42)

    if args.mode == "laminar":
        demo_laminar_inference()
    elif args.mode == "dynamics":
        demo_network_dynamics()
    elif args.mode == "ai":
        demo_ai_integration()
    elif args.mode == "full":
        demo_full_system()


if __name__ == "__main__":
    main()
