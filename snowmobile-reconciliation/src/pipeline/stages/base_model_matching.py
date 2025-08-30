"""
Stage 1: Base Model Matching

Implements intelligent base model matching with structured lookup first,
followed by Claude semantic fallback for edge cases.
"""
import re
from typing import Optional

import structlog

from src.models.domain import (
    BaseModelSpecification,
    PipelineConfig,
    PriceEntry,
    ProcessingStage,
)
from src.pipeline.stages.base_stage import BasePipelineStage
from src.repositories.base_model_repository import BaseModelRepository
from src.services.claude_enrichment import ClaudeEnrichmentService

logger = structlog.get_logger(__name__)


class BaseModelMatchingStage(BasePipelineStage):
    """
    Stage 1: Match price entries to catalog base models.

    Strategy:
    1. Structured matching (95% success rate expected)
    2. Claude semantic fallback (for edge cases)
    3. Confidence scoring based on match quality
    """

    def __init__(
        self,
        config: PipelineConfig,
        base_model_repo: BaseModelRepository,
        claude_service: ClaudeEnrichmentService,
    ) -> None:
        super().__init__(ProcessingStage.BASE_MODEL_MATCHING, config)
        self.base_model_repo = base_model_repo
        self.claude_service = claude_service
        self.logger = logger.bind(stage="base_model_matching")

        # Load model code patterns for structured matching
        self._load_model_patterns()

    async def _execute_stage(self, context: "PipelineContext") -> dict:
        """Execute base model matching logic"""
        price_entry = context.price_entry

        self.logger.info(
            "Starting base model matching",
            model_code=price_entry.model_code,
            brand=price_entry.brand,
        )

        # Step 1: Structured matching (should handle 95% of cases)
        structured_result = await self._structured_matching(price_entry)

        if structured_result.success and structured_result.confidence >= 0.8:
            self.logger.info(
                "Structured matching successful",
                model_code=price_entry.model_code,
                matched_model=structured_result.base_model_id,
                confidence=structured_result.confidence,
            )

            return {
                "matching_method": "structured",
                "matched_base_model_id": structured_result.base_model_id,
                "model_name": structured_result.model_name,
                "confidence": structured_result.confidence,
                "specifications": structured_result.specifications,
                "match_details": structured_result.match_details,
            }

        # Step 2: Claude semantic fallback for edge cases
        self.logger.info(
            "Structured matching insufficient, trying Claude fallback",
            model_code=price_entry.model_code,
            structured_confidence=structured_result.confidence
            if structured_result
            else 0.0,
        )

        claude_result = await self._claude_semantic_matching(
            price_entry, structured_result
        )

        if claude_result.success:
            self.logger.info(
                "Claude semantic matching successful",
                model_code=price_entry.model_code,
                matched_model=claude_result.base_model_id,
                confidence=claude_result.confidence,
            )

            return {
                "matching_method": "claude_semantic",
                "matched_base_model_id": claude_result.base_model_id,
                "model_name": claude_result.model_name,
                "confidence": claude_result.confidence,
                "specifications": claude_result.specifications,
                "match_details": claude_result.match_details,
                "claude_reasoning": claude_result.claude_reasoning,
                "claude_tokens_used": claude_result.tokens_used,
            }

        # No successful match found
        self.logger.warning(
            "No successful base model match found",
            model_code=price_entry.model_code,
            brand=price_entry.brand,
        )

        return {
            "matching_method": "failed",
            "matched_base_model_id": None,
            "model_name": None,
            "confidence": 0.0,
            "error": "No matching base model found",
            "attempted_methods": ["structured", "claude_semantic"],
        }

    async def _structured_matching(self, price_entry: PriceEntry) -> "MatchResult":
        """
        Structured matching using known patterns and database lookups.
        Should handle 95% of cases with high confidence.
        """
        model_code = price_entry.model_code.upper().strip()
        brand = price_entry.brand.upper()
        model_year = price_entry.model_year

        # Step 1: Extract base model from code using patterns
        base_model_candidates = self._extract_base_model_candidates(model_code, brand)

        if not base_model_candidates:
            return MatchResult(
                success=False,
                confidence=0.0,
                reason="No base model candidates extracted from code",
            )

        # Step 2: Database lookup for each candidate
        best_match = None
        best_confidence = 0.0

        for candidate in base_model_candidates:
            matches = await self.base_model_repo.find_matching_base_models(
                {
                    "brand": brand,
                    "model_year": model_year,
                    "base_model_pattern": candidate,
                }
            )

            if matches:
                # Score each match
                for match in matches:
                    confidence = self._calculate_match_confidence(
                        model_code, candidate, match
                    )

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = match

        if best_match and best_confidence >= 0.7:
            return MatchResult(
                success=True,
                base_model_id=best_match.base_model_id,
                model_name=best_match.model_name,
                specifications=best_match.specifications,
                confidence=best_confidence,
                match_details={
                    "extraction_method": "pattern_based",
                    "candidate_codes": base_model_candidates,
                    "matched_candidate": self._find_matching_candidate(
                        model_code, best_match.base_model_id
                    ),
                },
            )

        return MatchResult(
            success=False,
            confidence=best_confidence,
            reason=f"Best match confidence {best_confidence:.2f} below threshold 0.7",
        )

    async def _claude_semantic_matching(
        self, price_entry: PriceEntry, structured_result: Optional["MatchResult"]
    ) -> "MatchResult":
        """
        Claude-powered semantic matching for edge cases.
        Uses domain knowledge to handle variations and ambiguities.
        """
        # Get potential base models from database for context
        potential_models = await self.base_model_repo.find_matching_base_models(
            {"brand": price_entry.brand, "model_year": price_entry.model_year}
        )

        # Prepare context for Claude
        claude_prompt = self._build_claude_matching_prompt(
            price_entry, structured_result, potential_models
        )

        try:
            claude_response = await self.claude_service.enrich_base_model_matching(
                prompt=claude_prompt,
                model_code=price_entry.model_code,
                brand=price_entry.brand,
            )

            if claude_response.success:
                # Validate Claude's suggested match against database
                suggested_match = await self._validate_claude_suggestion(
                    claude_response.suggested_base_model_id,
                    price_entry.brand,
                    price_entry.model_year,
                )

                if suggested_match:
                    return MatchResult(
                        success=True,
                        base_model_id=suggested_match.base_model_id,
                        model_name=suggested_match.model_name,
                        specifications=suggested_match.specifications,
                        confidence=claude_response.confidence,
                        claude_reasoning=claude_response.reasoning,
                        tokens_used=claude_response.tokens_used,
                        match_details={
                            "claude_suggested_id": claude_response.suggested_base_model_id,
                            "claude_confidence": claude_response.confidence,
                            "reasoning_provided": bool(claude_response.reasoning),
                        },
                    )

            return MatchResult(
                success=False,
                confidence=claude_response.confidence if claude_response else 0.0,
                reason="Claude suggestion could not be validated against database",
            )

        except Exception as e:
            self.logger.error(
                "Claude semantic matching failed",
                model_code=price_entry.model_code,
                error=str(e),
            )

            return MatchResult(
                success=False, confidence=0.0, reason=f"Claude API error: {e}"
            )

    def _load_model_patterns(self) -> None:
        """Load brand-specific model code patterns for structured matching"""

        # Ski-Doo patterns (most common)
        self.skidoo_patterns = {
            # Trail models
            r"^(LTTA|LTTD|LTTE|LTTF|LTTG|LTTI|LTTS)": "MXZ_TRAIL",
            r"^(MVTL|MVTA|MVTS|MVTD)": "MXZ_CROSSOVER",
            # Renegade patterns
            r"^(RENE|RENP|RENT|RENX)": "RENEGADE",
            r"^(BACK|SUMMIT|SUMM)": "SUMMIT",
            # Freeride
            r"^(FREE|FRER|FREX)": "FREERIDE",
            # Grand Touring
            r"^(GRAN|GTRX|GTRS)": "GRAND_TOURING",
            # Utility
            r"^(SKAN|EXPE|UTIL)": "UTILITY",
        }

        # Lynx patterns
        self.lynx_patterns = {
            r"^(ADVX|ADVE|ADVS)": "ADVENTURE",
            r"^(COMM|COMO|COMS)": "COMMANDER",
            r"^(RAVE|RAVX|RAVS)": "RAVE",
            r"^(XTER|XTER|XTRA)": "XTRIM",
        }

        self.logger.info(
            "Model patterns loaded",
            skidoo_patterns=len(self.skidoo_patterns),
            lynx_patterns=len(self.lynx_patterns),
        )

    def _extract_base_model_candidates(self, model_code: str, brand: str) -> list[str]:
        """Extract potential base model identifiers from model code"""
        candidates = []

        if brand == "SKI-DOO":
            patterns = self.skidoo_patterns
        elif brand == "LYNX":
            patterns = self.lynx_patterns
        else:
            # Generic pattern extraction for other brands
            patterns = {}

        # Try pattern matching
        for pattern, base_model in patterns.items():
            if re.match(pattern, model_code):
                candidates.append(base_model)

        # Fallback: extract first 3-4 characters as potential base
        if not candidates:
            if len(model_code) >= 3:
                candidates.extend(
                    [
                        model_code[:3],
                        model_code[:4] if len(model_code) >= 4 else model_code[:3],
                    ]
                )

        return list(set(candidates))  # Remove duplicates

    def _calculate_match_confidence(
        self, model_code: str, candidate: str, base_model: BaseModelSpecification
    ) -> float:
        """Calculate confidence score for a potential match"""
        confidence = 0.0

        # Exact base model ID match
        if base_model.base_model_id == candidate:
            confidence += 0.5

        # Partial matches in model name
        model_name_upper = base_model.model_name.upper()
        if candidate in model_name_upper:
            confidence += 0.3

        # Brand consistency check
        if base_model.brand.upper() in model_code:
            confidence += 0.1

        # Model code similarity using simple string matching
        similarity = self._calculate_string_similarity(
            model_code, base_model.base_model_id
        )
        confidence += similarity * 0.1

        return min(confidence, 1.0)

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Simple string similarity calculation"""
        if not str1 or not str2:
            return 0.0

        str1, str2 = str1.upper(), str2.upper()

        # Simple character overlap calculation
        common_chars = set(str1) & set(str2)
        total_chars = set(str1) | set(str2)

        if not total_chars:
            return 0.0

        return len(common_chars) / len(total_chars)

    def _find_matching_candidate(self, model_code: str, base_model_id: str) -> str:
        """Find which candidate led to the successful match"""
        candidates = self._extract_base_model_candidates(model_code, "")

        for candidate in candidates:
            if candidate in base_model_id or base_model_id in candidate:
                return candidate

        return candidates[0] if candidates else "unknown"

    def _build_claude_matching_prompt(
        self,
        price_entry: PriceEntry,
        structured_result: Optional["MatchResult"],
        potential_models: list[BaseModelSpecification],
    ) -> str:
        """Build comprehensive prompt for Claude base model matching"""

        prompt = f"""
        Snowmobile Base Model Matching Task:

        Price Entry Details:
        - Model Code: {price_entry.model_code}
        - Brand: {price_entry.brand}
        - Model Year: {price_entry.model_year}
        - Price: {price_entry.price} {price_entry.currency}

        Available Base Models for {price_entry.brand} {price_entry.model_year}:
        """

        for i, model in enumerate(potential_models[:10], 1):  # Limit to top 10
            prompt += f"""
            {i}. {model.base_model_id} - {model.model_name}
               Category: {model.category}
               Engine: {model.engine_specs.get('displacement', 'N/A')}
            """

        if structured_result and not structured_result.success:
            prompt += f"""

            Structured Matching Attempted:
            - Result: Failed (confidence: {structured_result.confidence:.2f})
            - Reason: {structured_result.reason}
            """

        prompt += """

        Task: Identify the most likely base model for this price entry.

        Consider:
        1. Model code patterns and naming conventions
        2. Brand-specific model hierarchies
        3. Model year compatibility
        4. Category alignment (Trail, Crossover, Summit, etc.)

        Respond with JSON:
        {
            "suggested_base_model_id": "BASE_MODEL_ID",
            "confidence": 0.85,
            "reasoning": "Detailed explanation of the match logic"
        }
        """

        return prompt

    async def _validate_claude_suggestion(
        self, suggested_id: str, brand: str, model_year: int
    ) -> Optional[BaseModelSpecification]:
        """Validate Claude's suggested base model against database"""

        matches = await self.base_model_repo.find_matching_base_models(
            {"base_model_id": suggested_id, "brand": brand, "model_year": model_year}
        )

        return matches[0] if matches else None


class MatchResult:
    """Result of base model matching attempt"""

    def __init__(
        self,
        success: bool,
        confidence: float = 0.0,
        base_model_id: Optional[str] = None,
        model_name: Optional[str] = None,
        specifications: Optional[dict] = None,
        match_details: Optional[dict] = None,
        claude_reasoning: Optional[str] = None,
        tokens_used: int = 0,
        reason: Optional[str] = None,
    ):
        self.success = success
        self.confidence = confidence
        self.base_model_id = base_model_id
        self.model_name = model_name
        self.specifications = specifications or {}
        self.match_details = match_details or {}
        self.claude_reasoning = claude_reasoning
        self.tokens_used = tokens_used
        self.reason = reason
