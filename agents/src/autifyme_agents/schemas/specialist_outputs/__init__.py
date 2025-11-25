"""Specialist output models - Pydantic schemas for specialist responses.

These models define structured outputs that specialists return to the PM.
Extracting them to schemas/ enables reuse and cleaner specialist code.
"""

from .content_seo import (
    ContentSEODraft,
    PlatformContentDraft,
    ProductContentDraft,
    SEOElementsDraft,
)
from .market_intelligence import (
    CustomerSegmentDraft,
    IndustryUseCaseDraft,
    MarketIntelligenceDraft,
    PricePositionAnalysis,
)
from .marketing_content import (
    CallToActionDraft,
    HeadlineVariantDraft,
    MarketingContentDraft,
)
from .taxonomy import (
    CategoryMatch,
    GoogleCategoryMatch,
    IndustryMatch,
    TaxonomyClassificationDraft,
)
from .visual_assets import (
    ImageAssetDraft,
    VisualAssetsDraft,
)

__all__ = [
    # Content & SEO
    "ProductContentDraft",
    "SEOElementsDraft",
    "PlatformContentDraft",
    "ContentSEODraft",
    # Market Intelligence
    "PricePositionAnalysis",
    "CustomerSegmentDraft",
    "IndustryUseCaseDraft",
    "MarketIntelligenceDraft",
    # Marketing Content
    "HeadlineVariantDraft",
    "CallToActionDraft",
    "MarketingContentDraft",
    # Taxonomy
    "CategoryMatch",
    "GoogleCategoryMatch",
    "IndustryMatch",
    "TaxonomyClassificationDraft",
    # Visual Assets
    "ImageAssetDraft",
    "VisualAssetsDraft",
]
