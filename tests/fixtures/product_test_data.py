"""Product test data fixtures for autonomous testing.

Provides structured test scenarios with images, descriptions, and expected attributes
for comprehensive product cataloging workflow testing.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProductTestCase:
    """Test case for product cataloging."""

    name: str
    description: str
    media_path: str
    expected_category: str
    expected_attributes: dict[str, str]
    price_hint: str | None = None


# Get fixtures directory
FIXTURES_DIR = Path(__file__).parent
IMAGES_DIR = FIXTURES_DIR / "images"


# Test Cases
TEST_PRODUCTS = {
    "pet_jar_500ml": ProductTestCase(
        name="PET Jar 500ml with Blue Lid",
        description="Clear PET plastic jar, 500ml capacity, blue screw-on lid, food-grade material",
        media_path=str(IMAGES_DIR / "PET_CAN_JAR_500ml.jpeg"),
        expected_category="Packaging & Containers",
        expected_attributes={
            "material": "PET Plastic",
            "capacity": "500ml",
            "lid_type": "Screw-on",
            "lid_color": "Blue",
            "transparency": "Clear",
        },
        price_hint="Rs 25 per piece",
    ),
    # Text-only test cases (no media)
    "nike_shoes_text": ProductTestCase(
        name="Nike Running Shoes",
        description="Nike running shoes for men, size 10, black color, mesh material",
        media_path=None,
        expected_category="Footwear",
        expected_attributes={
            "brand": "Nike",
            "type": "Running Shoes",
            "gender": "Men",
            "size": "10",
            "color": "Black",
            "material": "Mesh",
        },
        price_hint="Rs 2500",
    ),
    "cotton_tshirt_text": ProductTestCase(
        name="Cotton T-Shirt",
        description="Plain cotton t-shirt, white color, size M, round neck, short sleeves",
        media_path=None,
        expected_category="Apparel",
        expected_attributes={
            "material": "Cotton",
            "color": "White",
            "size": "M",
            "neck_type": "Round",
            "sleeve_type": "Short",
        },
        price_hint="Rs 299",
    ),
}


# Batch test scenarios (for mixed mode testing)
BATCH_TEST_SCENARIOS = {
    "three_product_batch": [
        ("Catalog Nike running shoes Rs 2500", None),
        ("Catalog Cotton t-shirt Rs 299", None),
        ("Catalog Denim jeans Rs 1999", None),
    ],
    "with_images": [
        (
            f"Catalog this PET jar {TEST_PRODUCTS['pet_jar_500ml'].price_hint}",
            TEST_PRODUCTS["pet_jar_500ml"].media_path,
        ),
        ("Catalog Nike shoes Rs 2500", None),
        ("Catalog Cotton t-shirt Rs 299", None),
    ],
}


def get_test_case(name: str) -> ProductTestCase:
    """Get test case by name."""
    if name not in TEST_PRODUCTS:
        raise ValueError(f"Test case '{name}' not found. Available: {list(TEST_PRODUCTS.keys())}")
    return TEST_PRODUCTS[name]


def get_batch_scenario(name: str) -> list[tuple[str, str | None]]:
    """Get batch test scenario by name."""
    if name not in BATCH_TEST_SCENARIOS:
        raise ValueError(
            f"Batch scenario '{name}' not found. Available: {list(BATCH_TEST_SCENARIOS.keys())}"
        )
    return BATCH_TEST_SCENARIOS[name]
