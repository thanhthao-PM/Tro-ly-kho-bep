"""
Gói tập hợp toàn bộ Pydantic Schemas của hệ thống Trợ lý kho bếp.
"""
from app.schemas.common import Labeled, CursorPage, ErrorResponse, ErrorDetail
from app.schemas.catalog import (
    UnitResponse, ConversionSchema, IngredientCreate,
    IngredientUpdate, IngredientResponse
)
from app.schemas.inventory import (
    BatchRead, BatchCreateRequest, BatchAdjustmentRequest,
    BatchResponse, BatchCreate, BatchMetadataUpdate,
    StocktakeAdjustmentRequest, StockMovementResponse,
    InventoryIngredientSummary, InventorySummaryResponse
)
from app.schemas.menu import (
    RecipeItemCreateRequest, DishCreateRequest, DishUpdateRequest,
    RecipeItemSchema, DishMarginEstimate, DishCreate,
    DishUpdate, DishResponse
)
from app.schemas.documents import (
    DocumentLineResponse, DocumentSummary, DocumentResponse,
    DocumentLineUpdate, DocumentConfirmResponse
)
from app.schemas.sales import (
    SaleLineCreateRequest, SaleCreateRequest,
    SaleLineResponse, SaleResponse, ShortageResponse,
    ShortageResolveRequest
)
from app.schemas.disposals import (
    SuggestedDishSchema, ExpiringBatchResponse,
    DisposalCreate, DisposalCreateRequest, DisposalResponse, CookRequest
)
from app.schemas.reports import (
    PeriodRange, SalesReportSection, SelloffReportSection,
    TotalsReportSection, PeriodReportResponse, WasteReportResponse,
    DishProfitReportResponse, ReplenishmentResponse
)
from app.schemas.assistant import (
    ChatTurn, AssistantMessageRequest, VerifiedFact,
    ProposedAction, RecommendationItem, AssistantMessageResponse
)

__all__ = [
    "Labeled", "CursorPage", "ErrorResponse", "ErrorDetail",
    "UnitResponse", "ConversionSchema", "IngredientCreate", "IngredientUpdate", "IngredientResponse",
    "BatchRead", "BatchCreateRequest", "BatchAdjustmentRequest",
    "BatchResponse", "BatchCreate", "BatchMetadataUpdate", "StocktakeAdjustmentRequest", "StockMovementResponse", "InventoryIngredientSummary", "InventorySummaryResponse",
    "RecipeItemCreateRequest", "DishCreateRequest", "DishUpdateRequest",
    "RecipeItemSchema", "DishMarginEstimate", "DishCreate", "DishUpdate", "DishResponse",
    "DocumentLineResponse", "DocumentSummary", "DocumentResponse", "DocumentLineUpdate", "DocumentConfirmResponse",
    "SaleLineCreateRequest", "SaleCreateRequest",
    "SaleLineResponse", "SaleResponse", "ShortageResponse", "ShortageResolveRequest",
    "SuggestedDishSchema", "ExpiringBatchResponse", "DisposalCreate", "DisposalCreateRequest", "DisposalResponse", "CookRequest",
    "PeriodRange", "SalesReportSection", "SelloffReportSection", "TotalsReportSection", "PeriodReportResponse", "WasteReportResponse", "DishProfitReportResponse", "ReplenishmentResponse",
    "ChatTurn", "AssistantMessageRequest", "VerifiedFact", "ProposedAction", "RecommendationItem", "AssistantMessageResponse",
]
