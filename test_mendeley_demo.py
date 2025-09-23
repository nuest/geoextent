#!/usr/bin/env python3
"""
Demo script showing the Mendeley content provider test suite functionality.

This script demonstrates validation of the specific datasets requested by the user
and tests different DOI formats and URL variations.
"""

import sys
from geoextent.lib.content_providers.Mendeley import Mendeley

def test_user_datasets():
    """Test the user-specified datasets with different identifier formats."""

    # User-specified datasets from the request
    test_datasets = {
        "tropical_cloud_forest": {
            "dataset_id": "ybx6zp2rfp",
            "version": "1",
            "identifiers": [
                "10.17632/ybx6zp2rfp.1",  # Plain DOI
                "https://doi.org/10.17632/ybx6zp2rfp.1",  # DOI URL
                "https://data.mendeley.com/datasets/ybx6zp2rfp/1",  # Direct URL
                "ybx6zp2rfp.1",  # Dataset ID with version
                "ybx6zp2rfp/1",  # Dataset ID with version (slash)
                "ybx6zp2rfp",  # Bare dataset ID
            ],
            "title": "Tropical Montane Cloud Forest distribution at 0.1 by 0.1 degrees",
            "authors": ["Los, Sietse", "Street-Perrott, Alayne", "Loader, Neil", "Froyd, Cindy"],
            "year": 2021,
        },
        "water_quality_mapping": {
            "dataset_id": "536ynvxw69",
            "version": "1",
            "identifiers": [
                "10.17632/536ynvxw69.1",
                "https://doi.org/10.17632/536ynvxw69.1",
                "https://data.mendeley.com/datasets/536ynvxw69/1",
                "536ynvxw69.1",
            ],
            "title": "Water quality modelling geographical mapping",
            "authors": ["MAHANTY, BISWANATH", "Sahoo, Naresh Kumar"],
            "year": 2023,
        },
        "emilia_romagna_floods": {
            "dataset_id": "yzddsc67gy",
            "version": "1",
            "identifiers": [
                "10.17632/yzddsc67gy.1",
                "https://data.mendeley.com/datasets/yzddsc67gy/1",
                "yzddsc67gy.1",
            ],
            "title": "Research Data of Brief communication: On the environmental impacts of the 2023 floods in Emilia-Romagna (Italy)",
            "authors": ["Arrighi, Chiara", "Domeneghetti, Alessio"],
            "year": 2024,
        },
        "historical_mills_galicia": {
            "dataset_id": "8h9295v4t3",
            "version": "2",  # Note: Version 2
            "identifiers": [
                "10.17632/8h9295v4t3.2",
                "https://data.mendeley.com/datasets/8h9295v4t3/2",
                "8h9295v4t3.2",
            ],
            "title": "Historical dataset of mills for Galicia in the Austro-Hungarian Empire/southern Poland from 1880 to the 1930s",
            "authors": ["Ostafin, Krzysztof", "Jasionek, Magdalena", "Kaim, Dominik", "Miklar, Anna"],
            "year": 2021,
        },
    }

    print("🔍 Testing Mendeley Content Provider with User-Specified Datasets")
    print("=" * 70)

    total_tests = 0
    successful_tests = 0

    for dataset_name, dataset_info in test_datasets.items():
        print(f"\n📊 Dataset: {dataset_info['title']}")
        print(f"   Authors: {', '.join(dataset_info['authors'])}")
        print(f"   Year: {dataset_info['year']}")
        print(f"   Expected: {dataset_info['dataset_id']} v{dataset_info['version']}")
        print()

        for i, identifier in enumerate(dataset_info["identifiers"], 1):
            total_tests += 1
            print(f"   {i}. Testing: {identifier}")

            try:
                provider = Mendeley()
                is_valid = provider.validate_provider(identifier)

                if is_valid:
                    successful_tests += 1

                    # Handle bare dataset ID case (version None for latest)
                    if identifier == dataset_info["dataset_id"]:
                        version_str = f"v{provider.version} (latest)" if provider.version is None else f"v{provider.version}"
                    else:
                        version_str = f"v{provider.version}"

                    print(f"      ✅ Valid: {provider.dataset_id} {version_str}")

                    # Validate parsed values
                    if provider.dataset_id != dataset_info["dataset_id"]:
                        print(f"      ⚠️  Dataset ID mismatch: expected {dataset_info['dataset_id']}, got {provider.dataset_id}")

                    # Version validation (handle bare ID case)
                    if identifier == dataset_info["dataset_id"]:
                        if provider.version is not None:
                            print(f"      ⚠️  Bare dataset ID should have version=None, got {provider.version}")
                    else:
                        if provider.version != dataset_info["version"]:
                            print(f"      ⚠️  Version mismatch: expected {dataset_info['version']}, got {provider.version}")
                else:
                    print(f"      ❌ Invalid identifier")

            except Exception as e:
                print(f"      💥 Error: {e}")

    print("\n" + "=" * 70)
    print(f"📈 Test Results Summary:")
    print(f"   Total tests: {total_tests}")
    print(f"   Successful: {successful_tests}")
    print(f"   Success rate: {successful_tests/total_tests*100:.1f}%")

    # Test malformed URL handling
    print(f"\n🚫 Testing Malformed DOI URL:")
    malformed_url = "https://10.17632/8h9295v4t3.2"  # Invalid format from user
    print(f"   Testing: {malformed_url}")

    provider = Mendeley()
    is_valid = provider.validate_provider(malformed_url)

    if not is_valid:
        print(f"   ✅ Correctly rejected malformed URL")
    else:
        print(f"   ❌ Incorrectly accepted malformed URL")

    print("\n" + "=" * 70)
    print("🎯 Test Suite Validation Complete!")

    return successful_tests, total_tests

def demonstrate_doi_variations():
    """Demonstrate different DOI format variations."""
    print("\n🔗 Testing DOI Format Variations")
    print("=" * 40)

    base_doi = "10.17632/ybx6zp2rfp.1"

    variations = [
        f"https://doi.org/{base_doi}",
        f"http://doi.org/{base_doi}",
        f"https://dx.doi.org/{base_doi}",
        f"https://www.doi.org/{base_doi}",
        base_doi,
    ]

    provider = Mendeley()

    for variation in variations:
        print(f"Testing: {variation}")
        if provider.validate_provider(variation):
            print(f"  ✅ Valid -> {provider.dataset_id} v{provider.version}")
        else:
            print(f"  ❌ Invalid")

if __name__ == "__main__":
    print("Mendeley Content Provider Test Suite Demo")
    print("========================================")

    try:
        successful, total = test_user_datasets()
        demonstrate_doi_variations()

        print(f"\n🏆 Final Results:")
        print(f"   Overall success rate: {successful/total*100:.1f}%")

        if successful == total:
            print("   🎉 All tests passed successfully!")
            sys.exit(0)
        else:
            print(f"   ⚠️  {total - successful} tests failed")
            sys.exit(1)

    except Exception as e:
        print(f"💥 Demo failed with error: {e}")
        sys.exit(1)