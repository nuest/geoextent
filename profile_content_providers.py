#!/usr/bin/env python3
"""
Performance profiling script for geoextent content providers.
This script profiles the execution time for each content provider
to identify performance bottlenecks and optimization opportunities.
"""

import cProfile
import pstats
import io
import time
import sys
import os
import logging
from pathlib import Path

# Add the geoextent module to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import geoextent.lib.extent as geoextent

# Configure logging to reduce noise during profiling
logging.getLogger("geoextent").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)

# Test datasets for each content provider
TEST_DATASETS = {
    "Zenodo": {
        "identifier": "10.5281/zenodo.820562",
        "description": "Landslide imagery from Hpakant, Myanmar"
    },
    "Figshare": {
        "identifier": "10.6084/m9.figshare.19248626.v2",
        "description": "Prince Edward Islands geospatial database"
    },
    "Dryad": {
        "identifier": "10.5061/dryad.0k6djhb7x",
        "description": "Dryad geospatial dataset"
    },
    "PANGAEA": {
        "identifier": "10.1594/PANGAEA.734969",
        "description": "PANGAEA marine dataset"
    },
    "OSF": {
        "identifier": "https://osf.io/4xe6z",
        "description": "OSF research project data"
    },
    "GFZ": {
        "identifier": "10.5880/GFZ.3.1.2023.001",
        "description": "GFZ geophysical dataset"
    },
    "Pensoft": {
        "identifier": "10.3897/bdj.11.e98731",
        "description": "Pensoft biodiversity journal data"
    },
    "Dataverse": {
        "identifier": "10.7910/DVN/OMV93V",
        "description": "Harvard Dataverse dataset"
    }
}

def profile_content_provider(provider_name, identifier, description, timeout=300):
    """
    Profile a single content provider execution.

    Args:
        provider_name: Name of the content provider
        identifier: Repository identifier to test
        description: Description of the dataset
        timeout: Maximum time to allow for execution (seconds)

    Returns:
        dict: Profiling results including timing and stats
    """
    print(f"\n{'='*60}")
    print(f"Profiling {provider_name}: {description}")
    print(f"Identifier: {identifier}")
    print(f"{'='*60}")

    # Create a profiler
    profiler = cProfile.Profile()

    # Track execution time
    start_time = time.time()
    success = False
    error_message = None

    try:
        # Start profiling
        profiler.enable()

        # Execute the fromRemote function
        result = geoextent.fromRemote(
            identifier,
            bbox=True,
            tbox=True,
            download_data=True,
            show_progress=False,
            timeout=timeout,
            max_download_size="50MB"  # Limit download size for faster profiling
        )

        success = True

    except Exception as e:
        error_message = str(e)
        print(f"ERROR: {error_message}")

    finally:
        # Stop profiling
        profiler.disable()
        end_time = time.time()

    execution_time = end_time - start_time

    # Generate profiling statistics
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats('cumulative')
    ps.print_stats(30)  # Top 30 functions by cumulative time

    profile_output = s.getvalue()

    # Get top time-consuming functions
    s2 = io.StringIO()
    ps2 = pstats.Stats(profiler, stream=s2)
    ps2.sort_stats('tottime')
    ps2.print_stats(20)  # Top 20 functions by total time

    tottime_output = s2.getvalue()

    return {
        'provider': provider_name,
        'identifier': identifier,
        'description': description,
        'success': success,
        'execution_time': execution_time,
        'error': error_message,
        'profile_stats': profile_output,
        'tottime_stats': tottime_output,
        'profiler': profiler
    }

def save_detailed_profile(result, output_dir):
    """Save detailed profiling results to files."""
    provider = result['provider']

    # Save cumulative time stats
    with open(os.path.join(output_dir, f"{provider}_cumulative.txt"), 'w') as f:
        f.write(f"Content Provider: {provider}\n")
        f.write(f"Identifier: {result['identifier']}\n")
        f.write(f"Description: {result['description']}\n")
        f.write(f"Success: {result['success']}\n")
        f.write(f"Execution Time: {result['execution_time']:.2f} seconds\n")
        if result['error']:
            f.write(f"Error: {result['error']}\n")
        f.write("\n" + "="*80 + "\n")
        f.write("CUMULATIVE TIME STATS (Top functions by cumulative time)\n")
        f.write("="*80 + "\n")
        f.write(result['profile_stats'])

    # Save total time stats
    with open(os.path.join(output_dir, f"{provider}_tottime.txt"), 'w') as f:
        f.write(f"Content Provider: {provider}\n")
        f.write(f"Identifier: {result['identifier']}\n")
        f.write(f"Description: {result['description']}\n")
        f.write(f"Success: {result['success']}\n")
        f.write(f"Execution Time: {result['execution_time']:.2f} seconds\n")
        if result['error']:
            f.write(f"Error: {result['error']}\n")
        f.write("\n" + "="*80 + "\n")
        f.write("TOTAL TIME STATS (Top functions by total/own time)\n")
        f.write("="*80 + "\n")
        f.write(result['tottime_stats'])

def analyze_profiling_results(results):
    """Analyze profiling results and generate recommendations."""

    print(f"\n{'='*80}")
    print("PROFILING ANALYSIS SUMMARY")
    print(f"{'='*80}")

    successful_results = [r for r in results if r['success']]
    failed_results = [r for r in results if not r['success']]

    print(f"\nSuccessful providers: {len(successful_results)}/{len(results)}")
    print(f"Failed providers: {len(failed_results)}/{len(results)}")

    if failed_results:
        print("\nFailed providers:")
        for result in failed_results:
            print(f"  - {result['provider']}: {result['error']}")

    if successful_results:
        print(f"\nExecution times:")
        successful_results.sort(key=lambda x: x['execution_time'])

        for result in successful_results:
            print(f"  {result['provider']:12s}: {result['execution_time']:6.2f}s - {result['description']}")

        # Find slowest and fastest
        fastest = successful_results[0]
        slowest = successful_results[-1]

        print(f"\nFastest: {fastest['provider']} ({fastest['execution_time']:.2f}s)")
        print(f"Slowest: {slowest['provider']} ({slowest['execution_time']:.2f}s)")
        print(f"Performance ratio: {slowest['execution_time']/fastest['execution_time']:.1f}x")

    return successful_results, failed_results

def main():
    """Main profiling execution."""

    print("Starting geoextent content provider profiling...")
    print(f"Testing {len(TEST_DATASETS)} content providers")

    # Create output directory for detailed results
    output_dir = "profiling_results"
    os.makedirs(output_dir, exist_ok=True)

    results = []

    # Profile each content provider
    for provider_name, dataset_info in TEST_DATASETS.items():
        result = profile_content_provider(
            provider_name,
            dataset_info["identifier"],
            dataset_info["description"],
            timeout=300  # 5 minute timeout per provider
        )
        results.append(result)

        # Save detailed profiling results
        save_detailed_profile(result, output_dir)

        # Print summary for this provider
        if result['success']:
            print(f"✓ Completed in {result['execution_time']:.2f}s")
        else:
            print(f"✗ Failed: {result['error']}")

    # Analyze overall results
    successful_results, failed_results = analyze_profiling_results(results)

    # Save summary report
    with open(os.path.join(output_dir, "summary_report.txt"), 'w') as f:
        f.write("GEOEXTENT CONTENT PROVIDER PROFILING SUMMARY\n")
        f.write("="*60 + "\n\n")

        f.write(f"Total providers tested: {len(results)}\n")
        f.write(f"Successful: {len(successful_results)}\n")
        f.write(f"Failed: {len(failed_results)}\n\n")

        if successful_results:
            f.write("EXECUTION TIMES (sorted by speed):\n")
            f.write("-" * 40 + "\n")
            for result in sorted(successful_results, key=lambda x: x['execution_time']):
                f.write(f"{result['provider']:12s}: {result['execution_time']:6.2f}s\n")

        if failed_results:
            f.write("\nFAILED PROVIDERS:\n")
            f.write("-" * 20 + "\n")
            for result in failed_results:
                f.write(f"{result['provider']}: {result['error']}\n")

    print(f"\nDetailed profiling results saved to: {output_dir}/")
    print("Summary report saved to: profiling_results/summary_report.txt")

    return results

if __name__ == "__main__":
    main()