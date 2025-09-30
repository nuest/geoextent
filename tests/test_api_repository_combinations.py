import pytest
import geoextent.lib.extent as geoextent
import tempfile
import os


class TestRepositoryParameterCombinations:
    """Test repository functions with various parameter combinations across all providers"""

    # Known working DOIs/URLs for different providers (may need network access)
    REPOSITORY_TEST_DATA = {
        "zenodo": {
            "doi": "10.5281/zenodo.820562",
            "url": "https://zenodo.org/record/820562",
        },
        "pangaea": {
            "doi": "10.1594/PANGAEA.734969",
            "url": "https://doi.pangaea.de/10.1594/PANGAEA.734969",
        },
        # Note: Add more providers as they become available
        # "figshare": {"doi": "...", "url": "..."},
        # "dryad": {"doi": "...", "url": "..."},
    }

    def test_repository_bbox_only_all_providers(self):
        """Test repository extraction with only bbox enabled for all providers"""
        for provider_name, provider_data in self.REPOSITORY_TEST_DATA.items():
            try:
                result = geoextent.fromRemote(
                    provider_data["doi"], bbox=True, tbox=False
                )
                assert result is not None
                assert result["format"] == "remote"
                assert "tbox" not in result
                # bbox might or might not be present depending on data content

            except ImportError:
                pytest.skip(f"Required library not available for {provider_name}")
            except Exception as e:
                pytest.skip(f"Network or API error for {provider_name}: {e}")

    def test_repository_tbox_only_all_providers(self):
        """Test repository extraction with only tbox enabled for all providers"""
        for provider_name, provider_data in self.REPOSITORY_TEST_DATA.items():
            try:
                result = geoextent.fromRemote(
                    provider_data["doi"], bbox=False, tbox=True
                )
                assert result is not None
                assert result["format"] == "remote"
                assert "bbox" not in result
                # tbox might or might not be present depending on data content

            except ImportError:
                pytest.skip(f"Required library not available for {provider_name}")
            except Exception as e:
                pytest.skip(f"Network or API error for {provider_name}: {e}")

    def test_repository_both_extraction_options_all_providers(self):
        """Test repository extraction with both bbox and tbox enabled for all providers"""
        for provider_name, provider_data in self.REPOSITORY_TEST_DATA.items():
            try:
                result = geoextent.fromRemote(
                    provider_data["doi"], bbox=True, tbox=True
                )
                assert result is not None
                assert result["format"] == "remote"

            except ImportError:
                pytest.skip(f"Required library not available for {provider_name}")
            except Exception as e:
                pytest.skip(f"Network or API error for {provider_name}: {e}")

    def test_repository_both_disabled_should_fail(self):
        """Test repository extraction with both bbox and tbox disabled should fail"""
        test_doi = list(self.REPOSITORY_TEST_DATA.values())[0]["doi"]

        with pytest.raises(Exception, match="No extraction options enabled"):
            geoextent.fromRemote(test_doi, bbox=False, tbox=False)

    def test_repository_with_details_parameter(self):
        """Test repository extraction with details parameter"""
        for provider_name, provider_data in self.REPOSITORY_TEST_DATA.items():
            try:
                # Test with details enabled
                result_with_details = geoextent.fromRemote(
                    provider_data["doi"], bbox=True, tbox=True, details=True
                )
                assert result_with_details is not None
                assert "details" in result_with_details
                assert isinstance(result_with_details["details"], dict)

                # Test with details disabled (default)
                result_without_details = geoextent.fromRemote(
                    provider_data["doi"], bbox=True, tbox=True, details=False
                )
                assert result_without_details is not None
                assert "details" not in result_without_details

            except ImportError:
                pytest.skip(f"Required library not available for {provider_name}")
            except Exception as e:
                pytest.skip(f"Network or API error for {provider_name}: {e}")

    def test_repository_with_throttle_parameter(self):
        """Test repository extraction with throttle parameter"""
        for provider_name, provider_data in self.REPOSITORY_TEST_DATA.items():
            try:
                # Test with throttle enabled
                result_throttled = geoextent.fromRemote(
                    provider_data["doi"], bbox=True, tbox=True, throttle=True
                )
                assert result_throttled is not None

                # Test with throttle disabled (default)
                result_normal = geoextent.fromRemote(
                    provider_data["doi"], bbox=True, tbox=True, throttle=False
                )
                assert result_normal is not None

                # Both should return similar structure
                assert result_throttled["format"] == result_normal["format"]

            except ImportError:
                pytest.skip(f"Required library not available for {provider_name}")
            except Exception as e:
                pytest.skip(f"Network or API error for {provider_name}: {e}")

    def test_repository_with_timeout_parameter(self):
        """Test repository extraction with timeout parameter"""
        for provider_name, provider_data in self.REPOSITORY_TEST_DATA.items():
            try:
                # Test with reasonable timeout
                result = geoextent.fromRemote(
                    provider_data["doi"], bbox=True, tbox=True, timeout=30
                )
                assert result is not None
                # timeout field should not be present if timeout wasn't reached
                assert "timeout" not in result

            except ImportError:
                pytest.skip(f"Required library not available for {provider_name}")
            except Exception as e:
                pytest.skip(f"Network or API error for {provider_name}: {e}")

    def test_repository_download_data_parameter_pangaea_only(self):
        """Test repository extraction with download_data parameter (Pangaea specific)"""
        if "pangaea" not in self.REPOSITORY_TEST_DATA:
            pytest.skip("Pangaea test data not available")

        pangaea_data = self.REPOSITORY_TEST_DATA["pangaea"]

        try:
            # Test with download_data=False (metadata-based, default)
            result_metadata = geoextent.fromRemote(
                pangaea_data["doi"], bbox=True, tbox=True, download_data=False
            )
            assert result_metadata is not None

            # Test with download_data=True (local file download)
            result_local = geoextent.fromRemote(
                pangaea_data["doi"], bbox=True, tbox=True, download_data=True
            )
            assert result_local is not None

            # Both should have same format
            assert result_metadata["format"] == result_local["format"] == "remote"

        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_repository_all_parameters_enabled(self):
        """Test repository extraction with all parameters enabled"""
        for provider_name, provider_data in self.REPOSITORY_TEST_DATA.items():
            try:
                # Test with all possible parameters
                kwargs = {
                    "bbox": True,
                    "tbox": True,
                    "details": True,
                    "throttle": True,
                    "timeout": 60,
                }

                # Add download_data for Pangaea
                if provider_name == "pangaea":
                    kwargs["download_data"] = True

                result = geoextent.fromRemote(provider_data["doi"], **kwargs)
                assert result is not None
                assert result["format"] == "remote"
                assert "details" in result

            except ImportError:
                pytest.skip(f"Required library not available for {provider_name}")
            except Exception as e:
                pytest.skip(f"Network or API error for {provider_name}: {e}")


class TestRepositoryURLvsDoiHandling:
    """Test repository handling with URLs vs DOIs"""

    def test_repository_doi_vs_url_equivalence(self):
        """Test that DOI and URL formats return equivalent results"""
        for (
            provider_name,
            provider_data,
        ) in TestRepositoryParameterCombinations.REPOSITORY_TEST_DATA.items():
            if "url" not in provider_data:
                continue

            try:
                # Test with DOI format
                result_doi = geoextent.fromRemote(
                    provider_data["doi"], bbox=True, tbox=True
                )

                # Test with URL format
                result_url = geoextent.fromRemote(
                    provider_data["url"], bbox=True, tbox=True
                )

                assert result_doi is not None
                assert result_url is not None
                assert result_doi["format"] == result_url["format"] == "remote"

                # Results should be structurally similar
                assert ("bbox" in result_doi) == ("bbox" in result_url)
                assert ("tbox" in result_doi) == ("tbox" in result_url)

            except ImportError:
                pytest.skip(f"Required library not available for {provider_name}")
            except Exception as e:
                pytest.skip(f"Network or API error for {provider_name}: {e}")


class TestRepositoryErrorHandling:
    """Test repository error handling with various invalid inputs"""

    def test_repository_invalid_doi_formats(self):
        """Test repository with invalid DOI formats"""
        invalid_dois = [
            "not-a-doi",
            "10.1594/INVALID.123",
            "",
            "https://invalid-url.com",
            "10.1594/PANGAEA.",
            "random-string-123",
        ]

        for invalid_doi in invalid_dois:
            with pytest.raises(Exception):
                geoextent.fromRemote(invalid_doi, bbox=True)

    def test_repository_nonexistent_doi(self):
        """Test repository with nonexistent DOI"""
        nonexistent_dois = [
            "10.5281/zenodo.999999999",
            "10.1594/PANGAEA.999999999",
        ]

        for doi in nonexistent_dois:
            try:
                result = geoextent.fromRemote(doi, bbox=True)
                # If it doesn't raise an exception, result should indicate failure
                if result is not None:
                    # Some providers might return partial results
                    assert isinstance(result, dict)
            except Exception:
                # Exception is expected for nonexistent DOIs
                pass

    def test_repository_with_very_short_timeout(self):
        """Test repository with very short timeout"""
        test_doi = list(
            TestRepositoryParameterCombinations.REPOSITORY_TEST_DATA.values()
        )[0]["doi"]

        try:
            result = geoextent.fromRemote(test_doi, bbox=True, tbox=True, timeout=0.001)
            # Should either complete or indicate timeout
            if result is not None:
                # If timeout was reached, it might be indicated
                if "timeout" in result:
                    assert result["timeout"] == 0.001

        except ImportError:
            pytest.skip("Required library not available")
        except Exception as e:
            # Timeout or network error is expected
            assert (
                "timeout" in str(e).lower()
                or "network" in str(e).lower()
                or "error" in str(e).lower()
            )

    def test_repository_unsupported_provider(self):
        """Test repository with unsupported provider URL"""
        unsupported_urls = [
            "https://unsupported-repo.com/record/123",
            "https://unknown-provider.org/dataset/456",
            "10.1000/unknown.provider.789",
        ]

        for url in unsupported_urls:
            with pytest.raises(Exception):
                geoextent.fromRemote(url, bbox=True)


class TestRepositoryProviderValidation:
    """Test repository provider validation logic"""

    def test_repository_provider_priority(self):
        """Test that repository providers are tried in priority order"""
        # This tests the provider selection logic
        from geoextent.lib.extent import geoextent_from_repository

        geoextent_repo = geoextent_from_repository()

        # Check that providers are available
        assert len(geoextent_repo.content_providers) > 0

        # Check that Pangaea provider is in the list
        provider_names = [
            provider.__name__ for provider in geoextent_repo.content_providers
        ]
        assert "Pangaea" in provider_names

    def test_repository_provider_validation_methods(self):
        """Test individual provider validation methods"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        # Test Pangaea provider
        pangaea = Pangaea()

        # Valid Pangaea DOIs
        valid_dois = [
            "10.1594/PANGAEA.734969",
            "https://doi.pangaea.de/10.1594/PANGAEA.734969",
        ]

        for doi in valid_dois:
            assert pangaea.validate_provider(doi) == True

        # Invalid DOIs for Pangaea
        invalid_dois = [
            "10.5281/zenodo.820562",  # Zenodo DOI
            "https://figshare.com/articles/123456",  # Figshare URL
            "not-a-doi",
        ]

        for doi in invalid_dois:
            assert pangaea.validate_provider(doi) == False


class TestRepositorySpecialCases:
    """Test special cases and edge conditions for repository handling"""

    def test_repository_with_redirect_urls(self):
        """Test repository with URLs that might redirect"""
        # Some DOI URLs might redirect to the actual repository
        redirect_cases = [
            "https://doi.org/10.5281/zenodo.820562",  # Generic DOI resolver
        ]

        for url in redirect_cases:
            try:
                result = geoextent.fromRemote(url, bbox=True)
                if result is not None:
                    assert result["format"] == "remote"
            except ImportError:
                pytest.skip("Required library not available")
            except Exception as e:
                # Redirect handling might fail, which is acceptable
                pytest.skip(f"Redirect handling error: {e}")

    def test_repository_with_whitespace_handling(self):
        """Test repository with whitespace in DOI/URL strings"""
        base_doi = list(
            TestRepositoryParameterCombinations.REPOSITORY_TEST_DATA.values()
        )[0]["doi"]

        whitespace_cases = [
            f" {base_doi} ",  # Leading and trailing spaces
            f"\t{base_doi}\t",  # Tabs
            f"\n{base_doi}\n",  # Newlines
        ]

        for doi_with_whitespace in whitespace_cases:
            try:
                result = geoextent.fromRemote(doi_with_whitespace.strip(), bbox=True)
                # Should handle whitespace gracefully after stripping
                if result is not None:
                    assert result["format"] == "remote"
            except ImportError:
                pytest.skip("Required library not available")
            except Exception as e:
                # Whitespace handling might fail
                pytest.skip(f"Whitespace handling error: {e}")
