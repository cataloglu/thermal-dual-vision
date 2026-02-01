"""
Performance benchmarking script for Thermal Dual Vision.

Measures inference latency, FPS, and memory usage.
"""
import time
import psutil
import numpy as np
from typing import Dict, List
from app.services.inference import get_inference_service


def benchmark_inference(num_iterations: int = 100) -> Dict[str, float]:
    """
    Benchmark YOLO inference performance.
    
    Args:
        num_iterations: Number of inference iterations
        
    Returns:
        Dict with performance metrics
    """
    print("=" * 60)
    print("INFERENCE PERFORMANCE BENCHMARK")
    print("=" * 60)
    
    # Load model
    print("\n1. Loading model...")
    service = get_inference_service()
    service.load_model("yolov8n")
    
    # Create test frame
    test_frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    # Warmup (5 iterations)
    print("\n2. Warmup (5 iterations)...")
    for _ in range(5):
        service.infer(test_frame, confidence_threshold=0.25)
    
    # Benchmark
    print(f"\n3. Benchmarking ({num_iterations} iterations)...")
    latencies = []
    
    start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    start_time = time.time()
    
    for i in range(num_iterations):
        iter_start = time.time()
        detections = service.infer(test_frame, confidence_threshold=0.25)
        iter_end = time.time()
        
        latency_ms = (iter_end - iter_start) * 1000
        latencies.append(latency_ms)
        
        if (i + 1) % 20 == 0:
            print(f"  Progress: {i + 1}/{num_iterations} iterations")
    
    end_time = time.time()
    end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    
    # Calculate metrics
    total_time = end_time - start_time
    avg_latency = np.mean(latencies)
    p50_latency = np.percentile(latencies, 50)
    p95_latency = np.percentile(latencies, 95)
    p99_latency = np.percentile(latencies, 99)
    fps = num_iterations / total_time
    memory_delta = end_memory - start_memory
    
    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total time: {total_time:.2f}s")
    print(f"Average latency: {avg_latency:.2f}ms")
    print(f"P50 latency: {p50_latency:.2f}ms")
    print(f"P95 latency: {p95_latency:.2f}ms")
    print(f"P99 latency: {p99_latency:.2f}ms")
    print(f"Throughput: {fps:.2f} FPS")
    print(f"Memory delta: {memory_delta:.2f} MB")
    print("=" * 60)
    
    return {
        "avg_latency_ms": avg_latency,
        "p50_latency_ms": p50_latency,
        "p95_latency_ms": p95_latency,
        "p99_latency_ms": p99_latency,
        "fps": fps,
        "memory_delta_mb": memory_delta
    }


def benchmark_preprocessing(num_iterations: int = 1000) -> Dict[str, float]:
    """
    Benchmark preprocessing performance (CLAHE).
    
    Args:
        num_iterations: Number of iterations
        
    Returns:
        Dict with performance metrics
    """
    print("\n" + "=" * 60)
    print("PREPROCESSING PERFORMANCE BENCHMARK")
    print("=" * 60)
    
    service = get_inference_service()
    
    # Create test frame (thermal)
    test_frame = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
    
    # Benchmark standard CLAHE
    print("\n1. Standard CLAHE...")
    latencies_standard = []
    
    for i in range(num_iterations):
        start = time.time()
        service.preprocess_thermal(
            test_frame,
            enable_enhancement=True,
            use_kurtosis=False
        )
        end = time.time()
        latencies_standard.append((end - start) * 1000)
        
        if (i + 1) % 200 == 0:
            print(f"  Progress: {i + 1}/{num_iterations}")
    
    avg_standard = np.mean(latencies_standard)
    
    # Benchmark kurtosis CLAHE
    print("\n2. Kurtosis CLAHE...")
    latencies_kurtosis = []
    
    for i in range(num_iterations):
        start = time.time()
        service.preprocess_thermal(
            test_frame,
            enable_enhancement=True,
            use_kurtosis=True
        )
        end = time.time()
        latencies_kurtosis.append((end - start) * 1000)
        
        if (i + 1) % 200 == 0:
            print(f"  Progress: {i + 1}/{num_iterations}")
    
    avg_kurtosis = np.mean(latencies_kurtosis)
    
    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Standard CLAHE: {avg_standard:.3f}ms")
    print(f"Kurtosis CLAHE: {avg_kurtosis:.3f}ms")
    print(f"Overhead: {avg_kurtosis - avg_standard:.3f}ms (+{((avg_kurtosis / avg_standard - 1) * 100):.1f}%)")
    print("=" * 60)
    
    return {
        "standard_clahe_ms": avg_standard,
        "kurtosis_clahe_ms": avg_kurtosis,
        "overhead_ms": avg_kurtosis - avg_standard
    }


def benchmark_filtering(num_iterations: int = 10000) -> Dict[str, float]:
    """
    Benchmark filtering performance (aspect ratio, temporal).
    
    Args:
        num_iterations: Number of iterations
        
    Returns:
        Dict with performance metrics
    """
    print("\n" + "=" * 60)
    print("FILTERING PERFORMANCE BENCHMARK")
    print("=" * 60)
    
    service = get_inference_service()
    
    # Create test detections
    detections = [
        {"bbox": [100, 100, 150, 200], "confidence": 0.9, "class_id": 0},
        {"bbox": [200, 100, 250, 200], "confidence": 0.85, "class_id": 0},
        {"bbox": [300, 100, 450, 200], "confidence": 0.8, "class_id": 0},  # Wide (rejected)
    ]
    
    # Benchmark aspect ratio filter
    print("\n1. Aspect Ratio Filter...")
    latencies_aspect = []
    
    for i in range(num_iterations):
        start = time.time()
        service.filter_by_aspect_ratio(detections, min_ratio=0.2, max_ratio=1.2)
        end = time.time()
        latencies_aspect.append((end - start) * 1000000)  # microseconds
    
    avg_aspect = np.mean(latencies_aspect)
    
    # Benchmark temporal consistency
    print("2. Temporal Consistency...")
    history = [[{"bbox": [100, 100, 150, 200]}] for _ in range(5)]
    latencies_temporal = []
    
    for i in range(num_iterations):
        start = time.time()
        service.check_temporal_consistency(
            detections,
            history,
            min_consecutive_frames=3,
            max_gap_frames=1
        )
        end = time.time()
        latencies_temporal.append((end - start) * 1000000)  # microseconds
    
    avg_temporal = np.mean(latencies_temporal)
    
    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Aspect Ratio Filter: {avg_aspect:.2f}µs")
    print(f"Temporal Consistency: {avg_temporal:.2f}µs")
    print("=" * 60)
    
    return {
        "aspect_filter_us": avg_aspect,
        "temporal_check_us": avg_temporal
    }


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("THERMAL DUAL VISION - PERFORMANCE BENCHMARK")
    print("=" * 60)
    print("\nThis will benchmark:")
    print("  1. YOLO inference (100 iterations)")
    print("  2. Preprocessing (1000 iterations)")
    print("  3. Filtering (10000 iterations)")
    print("\nEstimated time: 2-5 minutes")
    print("=" * 60)
    
    input("\nPress ENTER to start...")
    
    # Run benchmarks
    try:
        results_inference = benchmark_inference(100)
        results_preprocessing = benchmark_preprocessing(1000)
        results_filtering = benchmark_filtering(10000)
        
        # Summary
        print("\n\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        print(f"\nInference:")
        print(f"  Average latency: {results_inference['avg_latency_ms']:.2f}ms")
        print(f"  Throughput: {results_inference['fps']:.2f} FPS")
        
        print(f"\nPreprocessing:")
        print(f"  Standard CLAHE: {results_preprocessing['standard_clahe_ms']:.3f}ms")
        print(f"  Kurtosis CLAHE: {results_preprocessing['kurtosis_clahe_ms']:.3f}ms")
        
        print(f"\nFiltering:")
        print(f"  Aspect ratio: {results_filtering['aspect_filter_us']:.2f}µs")
        print(f"  Temporal: {results_filtering['temporal_check_us']:.2f}µs")
        
        print("\n" + "=" * 60)
        print("Benchmark complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during benchmark: {e}")
        sys.exit(1)
