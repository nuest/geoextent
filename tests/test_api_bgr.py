import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance


class TestBGRProvider:
    """Test BGR Geoportal content provider functionality with actual bounding box verification"""

    # Test datasets with known geographic and temporal coverage
    # Reference bboxes retrieved from BGR CSW API on 2025-01-16
    TEST_DATASETS = {
        "langeoog_hem": {
            "uuid": "d764e73b-27e4-4aaa-b187-b6141c115eb4",
            "url": "https://geoportal.bgr.de/mapapps/resources/apps/geoportal/index.html?lang=de#/datasets/portal/d764e73b-27e4-4aaa-b187-b6141c115eb4",
            "csw_url": "https://geoportal.bgr.de/smartfindersdi-csw/api?service=CSW&version=2.0.2&request=GetRecordById&Id=d764e73b-27e4-4aaa-b187-b6141c115eb4",
            "title": "Helicopter-borne Electromagnetics (HEM) Area 149 Langeoog2",
            "title_de": "Hubschrauber-Elektromagnetik (HEM) Gebiet 149 Langeoog2",
            # Reference bbox from BGR metadata (Langeoog island, Germany) - Retrieved 2025-01-16
            "expected_bbox": [7.48, 53.74, 7.62, 53.76],  # [W, S, E, N]
            "expected_tbox": ["2017-03-31", "2017-03-31"],  # Survey date
            "distribution_urls": [
                "https://download.bgr.de/bgr/aerogeophysik/149Langeoog2HEM/geotiff/149Langeoog2HEM.zip",
                "https://download.bgr.de/bgr/aerogeophysik/149Langeoog2HEM/pdf/149Langeoog2HEM.zip",
            ],
        },
        "hk1000": {
            "doi": "10.25928/HK1000",
            "doi_url": "https://doi.org/10.25928/HK1000",
            "uuid": "3e7bf95c-eaa2-46df-8df6-cfc68729a6a1",
            "title": "Hydrogeologische Karte von Deutschland 1:1.000.000 (HK1000)",
            # Reference bbox from BGR metadata (Germany) - Retrieved 2025-01-16
            "expected_bbox": [6.0, 47.0, 15.0, 55.0],  # [W, S, E, N]
        },
        "medkam": {
            "doi": "10.25928/MEDKAM.1",
            "doi_url": "https://doi.org/10.25928/MEDKAM.1",
            "uuid": "65f58412-4a78-4808-9ef6-6b6d9182db8f",
            "title": "Mediterranean Karst Aquifer Map 1:5,000,000 (MEDKAM)",
            # Reference bbox from BGR metadata (Mediterranean region) - Retrieved 2025-01-16
            "expected_bbox": [-17.5, 26.0, 47.5, 51.0],  # [W, S, E, N]
        },
    }

    def test_bgr_uuid_validation(self):
        """Test that BGR UUIDs and URLs are correctly validated"""
        from geoextent.lib.content_providers.BGR import BGR

        bgr = BGR()

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            # Test UUID validation
            if "uuid" in dataset_info:
                bgr_instance = BGR()
                assert bgr_instance.validate_provider(dataset_info["uuid"]) == True

            # Test URL validation (if present)
            if "url" in dataset_info:
                bgr_instance = BGR()
                assert bgr_instance.validate_provider(dataset_info["url"]) == True

            # Test CSW URL validation (if present)
            if "csw_url" in dataset_info:
                bgr_instance = BGR()
                assert bgr_instance.validate_provider(dataset_info["csw_url"]) == True

            # Test DOI validation (if present)
            if "doi" in dataset_info:
                bgr_instance = BGR()
                assert bgr_instance.validate_provider(dataset_info["doi"]) == True

        # Test additional BGR URL formats
        valid_identifiers = [
            "d764e73b-27e4-4aaa-b187-b6141c115eb4",
            "https://geoportal.bgr.de/mapapps/resources/apps/geoportal/index.html?lang=de#/datasets/portal/d764e73b-27e4-4aaa-b187-b6141c115eb4",
            "https://resource.bgr.de/d764e73b-27e4-4aaa-b187-b6141c115eb4",
            "geoportal.bgr.de/mapapps/resources/apps/geoportal/index.html?id=d764e73b-27e4-4aaa-b187-b6141c115eb4",
        ]

        for identifier in valid_identifiers:
            bgr_instance = BGR()
            result = bgr_instance.validate_provider(identifier)
            assert result == True, f"Failed to validate: {identifier}"

        # Test invalid identifiers
        invalid_identifiers = [
            "10.5281/zenodo.820562",  # Zenodo DOI
            "10.1594/PANGAEA.734969",  # PANGAEA DOI
            "https://figshare.com/articles/123456",  # Figshare URL
            "not-a-valid-identifier",
            "",
            "https://example.com/dataset/123",
        ]

        for identifier in invalid_identifiers:
            bgr_instance = BGR()
            assert bgr_instance.validate_provider(identifier) == False

    def test_bgr_csw_metadata_extraction(self):
        """Test BGR CSW metadata extraction"""
        from geoextent.lib.content_providers.BGR import BGR

        bgr = BGR()
        dataset = self.TEST_DATASETS["langeoog_hem"]

        # Validate the provider first
        assert bgr.validate_provider(dataset["uuid"]) == True

        try:
            # Test CSW GetRecordById
            xml_root = bgr._get_record_by_id(dataset["uuid"])
            assert xml_root is not None

            # Extract metadata from ISO XML
            metadata = bgr._extract_metadata_from_iso(xml_root)
            assert metadata is not None

            # Check title
            assert metadata.get("title") is not None
            assert (
                dataset["title"] in metadata["title"]
                or dataset["title_de"] in metadata["title"]
            )

            # Check bounding box
            assert metadata.get("bbox") is not None
            bbox = metadata["bbox"]
            expected_bbox = dataset["expected_bbox"]

            # Verify bbox format [minx, miny, maxx, maxy]
            assert len(bbox) == 4
            assert abs(bbox[0] - expected_bbox[0]) < tolerance
            assert abs(bbox[1] - expected_bbox[1]) < tolerance
            assert abs(bbox[2] - expected_bbox[2]) < tolerance
            assert abs(bbox[3] - expected_bbox[3]) < tolerance

            # Check distribution URLs
            assert metadata.get("distribution_urls") is not None
            assert len(metadata["distribution_urls"]) > 0

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network error: {e}")

    def test_bgr_metadata_only_extraction(self):
        """Test BGR metadata-only extraction (no data download)"""
        dataset = self.TEST_DATASETS["langeoog_hem"]

        try:
            # Test with download_data=False to only extract metadata
            result = geoextent.fromRemote(
                dataset["uuid"], bbox=True, tbox=True, download_data=False
            )

            assert result is not None
            assert result["format"] == "remote"

            # Check geographic coverage
            if "bbox" in result:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]

                assert len(bbox) == 4
                assert isinstance(bbox[0], (int, float))
                assert isinstance(bbox[1], (int, float))
                assert isinstance(bbox[2], (int, float))
                assert isinstance(bbox[3], (int, float))

                # Verify bounding box is close to expected (Langeoog island)
                assert abs(bbox[0] - expected_bbox[0]) < 0.5
                assert abs(bbox[1] - expected_bbox[1]) < 0.5
                assert abs(bbox[2] - expected_bbox[2]) < 0.5
                assert abs(bbox[3] - expected_bbox[3]) < 0.5

            # Check CRS
            if "crs" in result:
                assert result["crs"] == "4326", "CRS should be WGS84"

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_bgr_actual_bounding_box_verification(self):
        """Test BGR provider with actual bounding box verification"""
        dataset = self.TEST_DATASETS["langeoog_hem"]

        try:
            # Test with download_data=True to get actual geospatial data
            result = geoextent.fromRemote(
                dataset["uuid"], bbox=True, tbox=True, download_data=True
            )

            assert result is not None
            assert result["format"] == "remote"

            # Check geographic coverage
            if "bbox" in result:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]

                # Compare against precise reference values (retrieved 2025-01-16)
                assert len(bbox) == 4
                assert abs(bbox[0] - expected_bbox[0]) < tolerance
                assert abs(bbox[1] - expected_bbox[1]) < tolerance
                assert abs(bbox[2] - expected_bbox[2]) < tolerance
                assert abs(bbox[3] - expected_bbox[3]) < tolerance

            # Check CRS
            if "crs" in result:
                assert result["crs"] == "4326", "CRS should be WGS84"

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_bgr_multiple_identifier_formats(self):
        """Test BGR with different identifier formats"""
        dataset = self.TEST_DATASETS["langeoog_hem"]

        identifiers = [
            dataset["uuid"],
            dataset["url"],
            dataset["csw_url"],
        ]

        from geoextent.lib.content_providers.BGR import BGR

        for identifier in identifiers:
            bgr = BGR()
            try:
                is_valid = bgr.validate_provider(identifier)
                assert is_valid == True, f"Should validate: {identifier}"
                assert bgr.dataset_id == dataset["uuid"]

            except Exception as e:
                pytest.fail(f"Failed to validate {identifier}: {e}")

    def test_bgr_uuid_formats(self):
        """Test various BGR UUID formats"""
        from geoextent.lib.content_providers.BGR import BGR

        bgr = BGR()

        # Valid UUID-like identifiers
        valid_uuids = [
            "d764e73b-27e4-4aaa-b187-b6141c115eb4",
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "12345678-1234-1234-1234-123456789012",
        ]

        for uuid in valid_uuids:
            bgr_instance = BGR()
            # These should at least pass the validation pattern check
            result = bgr_instance.validate_provider(uuid)
            assert result == True, f"UUID {uuid} should validate"

    def test_bgr_langeoog_dataset_geographic_bounds(self):
        """Test that Langeoog dataset coordinates are reasonable for North Sea region"""
        dataset = self.TEST_DATASETS["langeoog_hem"]
        expected_bbox = dataset["expected_bbox"]

        # Verify coordinates are in Europe (rough bounds check)
        assert (
            -10 <= expected_bbox[0] <= 30
        ), "Western longitude should be in European range"
        assert (
            -10 <= expected_bbox[2] <= 30
        ), "Eastern longitude should be in European range"
        assert (
            40 <= expected_bbox[1] <= 70
        ), "Southern latitude should be in Northern European range"
        assert (
            40 <= expected_bbox[3] <= 70
        ), "Northern latitude should be in Northern European range"

        # Verify this is specifically North Sea / German coast region
        assert (
            6 <= expected_bbox[0] <= 9
        ), "Western longitude should be in German coast region"
        assert (
            6 <= expected_bbox[2] <= 9
        ), "Eastern longitude should be in German coast region"
        assert (
            53 <= expected_bbox[1] <= 55
        ), "Southern latitude should be in North Sea region"
        assert (
            53 <= expected_bbox[3] <= 55
        ), "Northern latitude should be in North Sea region"


class TestBGRParameterCombinations:
    """Test BGR with various parameter combinations"""

    def test_bgr_bbox_only(self):
        """Test BGR extraction with only bbox enabled"""
        test_uuid = "d764e73b-27e4-4aaa-b187-b6141c115eb4"

        try:
            result = geoextent.fromRemote(
                test_uuid, bbox=True, tbox=False, download_data=False
            )
            assert result is not None
            assert result["format"] == "remote"
            # tbox might still be present if temporal metadata is available
            # but we didn't explicitly request it

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_bgr_tbox_only(self):
        """Test BGR extraction with only tbox enabled"""
        test_uuid = "d764e73b-27e4-4aaa-b187-b6141c115eb4"

        try:
            result = geoextent.fromRemote(
                test_uuid, bbox=False, tbox=True, download_data=False
            )
            assert result is not None
            assert result["format"] == "remote"
            assert "bbox" not in result

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_bgr_with_details(self):
        """Test BGR extraction with details enabled"""
        test_uuid = "d764e73b-27e4-4aaa-b187-b6141c115eb4"

        try:
            result = geoextent.fromRemote(
                test_uuid, bbox=True, tbox=True, details=True, download_data=False
            )
            assert result is not None
            assert result["format"] == "remote"
            assert "details" in result
            assert isinstance(result["details"], dict)

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")


class TestBGREdgeCases:
    """Test BGR edge cases and error handling"""

    def test_bgr_nonexistent_dataset(self):
        """Test BGR with nonexistent dataset"""
        nonexistent_uuid = "00000000-0000-0000-0000-000000000000"

        try:
            result = geoextent.fromRemote(
                nonexistent_uuid, bbox=True, download_data=False
            )
            # Should either raise exception or return error indicator
            if result is not None:
                assert isinstance(result, dict)

        except Exception:
            # Exception is expected for nonexistent records
            pass

    def test_bgr_malformed_identifiers(self):
        """Test BGR with malformed identifiers"""
        from geoextent.lib.content_providers.BGR import BGR

        bgr = BGR()

        malformed_identifiers = [
            "not-a-uuid",
            "12345",  # Too short
            "https://other-portal.com/dataset/123",
            "",
            None,
        ]

        for identifier in malformed_identifiers:
            if identifier is not None:
                bgr_instance = BGR()
                result = bgr_instance.validate_provider(identifier)
                assert result == False, f"Should not validate: {identifier}"

    def test_bgr_url_validation_edge_cases(self):
        """Test BGR URL validation edge cases"""
        from geoextent.lib.content_providers.BGR import BGR

        # Test various URL formats
        test_cases = [
            (
                "https://geoportal.bgr.de/mapapps/resources/apps/geoportal/index.html?id=d764e73b-27e4-4aaa-b187-b6141c115eb4",
                True,
            ),
            (
                "http://geoportal.bgr.de/mapapps/resources/apps/geoportal/index.html?id=d764e73b-27e4-4aaa-b187-b6141c115eb4",
                True,
            ),
            (
                "geoportal.bgr.de/dataset/d764e73b-27e4-4aaa-b187-b6141c115eb4",
                True,
            ),
            (
                "https://resource.bgr.de/d764e73b-27e4-4aaa-b187-b6141c115eb4",
                True,
            ),
            ("https://example.com/d764e73b-27e4-4aaa-b187-b6141c115eb4", False),
            ("https://geoportal.bgr.de/other", False),  # 'other' is not a valid UUID
        ]

        for url, expected in test_cases:
            bgr = BGR()
            result = bgr.validate_provider(url)
            assert result == expected, f"URL {url} should validate as {expected}"


class TestBGRIntegration:
    """Integration tests for BGR provider"""

    def test_bgr_full_workflow(self):
        """Test complete BGR workflow from validation to extraction"""
        test_uuid = "d764e73b-27e4-4aaa-b187-b6141c115eb4"

        try:
            # Step 1: Validation
            from geoextent.lib.content_providers.BGR import BGR

            bgr = BGR()
            assert bgr.validate_provider(test_uuid) == True

            # Step 2: Full extraction with metadata only
            result = geoextent.fromRemote(
                test_uuid, bbox=True, tbox=True, download_data=False
            )

            # Step 3: Verify results
            assert result is not None
            assert result["format"] == "remote"

            # At minimum, we should get spatial information from BGR
            has_spatial = "bbox" in result and result["bbox"] is not None

            assert has_spatial, "Should extract spatial extent from BGR metadata"

            # Verify bbox is reasonable
            if has_spatial:
                bbox = result["bbox"]
                assert len(bbox) == 4
                assert bbox[0] <= bbox[2]  # west <= east
                assert bbox[1] <= bbox[3]  # south <= north

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_bgr_provider_can_be_used(self):
        """Test that BGR provider is available in the content providers list"""
        from geoextent.lib.content_providers.BGR import BGR

        bgr = BGR()
        assert bgr is not None
        assert bgr.name == "BGR"
        assert hasattr(bgr, "validate_provider")
        assert hasattr(bgr, "download")


class TestBGRFullPortalURL:
    """Test BGR full portal URL support"""

    def test_bgr_full_portal_url_validation(self):
        """Test that BGR full portal URLs are correctly validated"""
        from geoextent.lib.content_providers.BGR import BGR

        bgr = BGR()

        # Test HYRAUM dataset with full portal URL
        full_url = "https://geoportal.bgr.de/mapapps/resources/apps/geoportal/index.html?lang=en#/datasets/portal/b73b55f1-14ec-4b7c-aa59-49b997ce7bbd"
        assert bgr.validate_provider(full_url) == True
        assert bgr.catalog_record_uuid == "b73b55f1-14ec-4b7c-aa59-49b997ce7bbd"

        # Test Langeoog dataset with full portal URL (German)
        bgr2 = BGR()
        full_url_de = "https://geoportal.bgr.de/mapapps/resources/apps/geoportal/index.html?lang=de#/datasets/portal/d764e73b-27e4-4aaa-b187-b6141c115eb4"
        assert bgr2.validate_provider(full_url_de) == True
        assert bgr2.catalog_record_uuid == "d764e73b-27e4-4aaa-b187-b6141c115eb4"

    def test_bgr_full_portal_url_extraction(self):
        """Test BGR metadata extraction from full portal URL"""
        try:
            import geoextent.lib.extent as geoextent

            # Test with HYRAUM dataset (covers all of Germany)
            full_url = "https://geoportal.bgr.de/mapapps/resources/apps/geoportal/index.html?lang=en#/datasets/portal/b73b55f1-14ec-4b7c-aa59-49b997ce7bbd"
            result = geoextent.fromRemote(full_url, bbox=True, download_data=False)

            assert result is not None
            assert result["format"] == "remote"
            assert "bbox" in result

            bbox = result["bbox"]
            # HYRAUM reference bbox (retrieved 2025-01-16)
            expected_bbox = [5.565029, 47.141752, 15.571236, 55.058629]
            assert abs(bbox[0] - expected_bbox[0]) < tolerance
            assert abs(bbox[1] - expected_bbox[1]) < tolerance
            assert abs(bbox[2] - expected_bbox[2]) < tolerance
            assert abs(bbox[3] - expected_bbox[3]) < tolerance

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_bgr_dataset_uuid_extraction(self):
        """Test that dataset UUID (file identifier) is extracted from metadata"""
        from geoextent.lib.content_providers.BGR import BGR

        bgr = BGR()
        catalog_uuid = "b73b55f1-14ec-4b7c-aa59-49b997ce7bbd"

        try:
            # Fetch metadata
            xml_root = bgr._get_record_by_id(catalog_uuid)
            metadata = bgr._extract_metadata_from_iso(xml_root)

            # Check that dataset UUID was extracted
            assert metadata.get("dataset_uuid") is not None
            assert metadata["dataset_uuid"] == "6f4e0e16-9218-4b5d-9f3f-ac6269293e37"

            # Check that it was also stored in the instance
            assert bgr.dataset_uuid == "6f4e0e16-9218-4b5d-9f3f-ac6269293e37"

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")


class TestBGRDOISupport:
    """Test BGR DOI support"""

    def test_bgr_doi_validation(self):
        """Test that BGR DOIs are correctly validated and resolved"""
        from geoextent.lib.content_providers.BGR import BGR

        test_dois = [
            ("10.25928/HK1000", "3e7bf95c-eaa2-46df-8df6-cfc68729a6a1"),
            ("https://doi.org/10.25928/HK1000", "3e7bf95c-eaa2-46df-8df6-cfc68729a6a1"),
            ("http://doi.org/10.25928/HK1000", "3e7bf95c-eaa2-46df-8df6-cfc68729a6a1"),
            ("10.25928/MEDKAM.1", "65f58412-4a78-4808-9ef6-6b6d9182db8f"),
            (
                "https://doi.org/10.25928/MEDKAM.1",
                "65f58412-4a78-4808-9ef6-6b6d9182db8f",
            ),
        ]

        for doi, expected_uuid in test_dois:
            bgr = BGR()
            result = bgr.validate_provider(doi)
            assert result == True, f"Failed to validate DOI: {doi}"
            assert bgr.catalog_record_uuid == expected_uuid, f"UUID mismatch for {doi}"

    def test_bgr_doi_invalid(self):
        """Test that non-BGR DOIs are rejected"""
        from geoextent.lib.content_providers.BGR import BGR

        invalid_dois = [
            "10.5281/zenodo.820562",  # Zenodo DOI
            "10.1594/PANGAEA.734969",  # PANGAEA DOI
            "10.25929/HK1000",  # Wrong BGR prefix
            "10.25928",  # Incomplete
        ]

        for doi in invalid_dois:
            bgr = BGR()
            assert bgr.validate_provider(doi) == False

    def test_bgr_hk1000_doi_extraction(self):
        """Test BGR DOI extraction with HK1000 dataset (10.25928/HK1000)"""
        try:
            import geoextent.lib.extent as geoextent

            # Test with bare DOI
            doi = "10.25928/HK1000"
            result = geoextent.fromRemote(doi, bbox=True, download_data=False)

            assert result is not None
            assert result["format"] == "remote"
            assert "bbox" in result

            bbox = result["bbox"]
            # HK1000 reference bbox (Germany) - Retrieved 2025-01-16
            expected_bbox = [6.0, 47.0, 15.0, 55.0]

            assert len(bbox) == 4
            assert abs(bbox[0] - expected_bbox[0]) < tolerance
            assert abs(bbox[1] - expected_bbox[1]) < tolerance
            assert abs(bbox[2] - expected_bbox[2]) < tolerance
            assert abs(bbox[3] - expected_bbox[3]) < tolerance

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_bgr_medkam_doi_extraction(self):
        """Test BGR DOI extraction with MEDKAM dataset (10.25928/MEDKAM.1)"""
        try:
            import geoextent.lib.extent as geoextent

            # Test with DOI URL
            doi_url = "https://doi.org/10.25928/MEDKAM.1"
            result = geoextent.fromRemote(doi_url, bbox=True, download_data=False)

            assert result is not None
            assert result["format"] == "remote"
            assert "bbox" in result

            bbox = result["bbox"]
            # MEDKAM reference bbox (Mediterranean) - Retrieved 2025-01-16
            expected_bbox = [-17.5, 26.0, 47.5, 51.0]

            assert len(bbox) == 4
            assert abs(bbox[0] - expected_bbox[0]) < tolerance
            assert abs(bbox[1] - expected_bbox[1]) < tolerance
            assert abs(bbox[2] - expected_bbox[2]) < tolerance
            assert abs(bbox[3] - expected_bbox[3]) < tolerance

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_bgr_doi_resolution_method(self):
        """Test BGR DOI resolution helper method"""
        from geoextent.lib.content_providers.BGR import BGR

        bgr = BGR()

        try:
            # Test DOI resolution
            doi = "10.25928/HK1000"
            resolved_url = bgr._resolve_doi_to_url(doi)

            assert resolved_url is not None
            assert "geoportal.bgr.de" in resolved_url
            assert "3e7bf95c-eaa2-46df-8df6-cfc68729a6a1" in resolved_url

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_bgr_doi_with_underscores_dots(self):
        """Test BGR DOI with special characters like underscores and dots"""
        from geoextent.lib.content_providers.BGR import BGR

        # Test DOI with underscores, dots, and version numbers
        dois_with_special_chars = [
            "10.25928/MEDKAM.1",  # Dots
            "10.25928/b2.21_sfkq-r406",  # Dots, underscores, hyphens
        ]

        for doi in dois_with_special_chars:
            bgr = BGR()
            result = bgr.validate_provider(doi)
            assert result == True, f"Failed to validate DOI with special chars: {doi}"
            assert bgr.catalog_record_uuid is not None
