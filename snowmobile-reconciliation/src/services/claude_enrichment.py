"""
Claude AI integration service for product enrichment and semantic analysis.

Implements proper API usage patterns with batching, error handling, and cost tracking
following Universal Development Standards.
"""
import asyncio
import json
from decimal import Decimal
from typing import Any, Optional

import httpx
import structlog
from pydantic import BaseModel, Field

from src.models.domain import ClaudeConfig

logger = structlog.get_logger(__name__)


class ClaudeResponse(BaseModel):
    """Structured response from Claude API"""

    success: bool
    content: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning: Optional[str] = None
    tokens_used: int = Field(ge=0, default=0)
    cost: Decimal = Field(ge=0, default=Decimal("0.00"))
    error_message: Optional[str] = None
    suggested_base_model_id: Optional[str] = None  # For base model matching
    detected_options: Optional[list[dict]] = None  # For spring options


class ClaudeEnrichmentService:
    """
    Service for Claude AI integration with proper error handling and optimization.

    Features:
    - Batching for cost optimization
    - Comprehensive error handling
    - Token and cost tracking
    - Rate limiting and retries
    - Response validation
    """

    def __init__(self, config: ClaudeConfig, api_key: str) -> None:
        self.config = config
        self.api_key = api_key
        self.logger = logger.bind(service="claude_enrichment")

        # API client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout_seconds),
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
        )

        # Cost tracking
        self._total_tokens_used = 0
        self._total_cost = Decimal("0.00")

        # Rate limiting
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # 100ms between requests

        self.logger.info(
            "Claude service initialized",
            model=config.model,
            max_tokens=config.max_tokens,
            timeout=config.timeout_seconds,
        )

    async def enrich_base_model_matching(
        self, prompt: str, model_code: str, brand: str
    ) -> ClaudeResponse:
        """
        Use Claude for semantic base model matching when structured matching fails.

        Args:
            prompt: Complete matching prompt with context
            model_code: Model code to match
            brand: Product brand

        Returns:
            Claude response with matching suggestions
        """
        request_logger = self.logger.bind(
            operation="base_model_matching", model_code=model_code, brand=brand
        )

        request_logger.info("Starting Claude base model matching")

        try:
            # Call Claude API
            response = await self._call_claude_api(
                prompt=prompt,
                system_message="You are an expert in snowmobile product catalogs and model identification. Provide accurate base model matches with detailed reasoning.",
                expected_format="json",
            )

            if not response.success:
                return response

            # Parse JSON response
            try:
                parsed_data = json.loads(response.content)

                # Validate required fields
                if not all(
                    key in parsed_data
                    for key in ["suggested_base_model_id", "confidence", "reasoning"]
                ):
                    return ClaudeResponse(
                        success=False,
                        error_message="Claude response missing required fields",
                    )

                return ClaudeResponse(
                    success=True,
                    suggested_base_model_id=parsed_data["suggested_base_model_id"],
                    confidence=min(max(float(parsed_data["confidence"]), 0.0), 1.0),
                    reasoning=parsed_data["reasoning"],
                    tokens_used=response.tokens_used,
                    cost=response.cost,
                )

            except json.JSONDecodeError as e:
                request_logger.error(
                    "Failed to parse Claude JSON response",
                    error=str(e),
                    response_content=response.content[:200],
                )

                return ClaudeResponse(
                    success=False,
                    error_message=f"Invalid JSON response from Claude: {e}",
                )

        except Exception as e:
            request_logger.error(
                "Unexpected error in base model matching", error=str(e)
            )

            return ClaudeResponse(success=False, error_message=f"Unexpected error: {e}")

    async def enrich_spring_options(
        self, product_data: dict[str, Any], base_model_specs: dict[str, Any]
    ) -> ClaudeResponse:
        """
        Detect and analyze spring options using Claude's domain knowledge.

        Args:
            product_data: Product information from previous pipeline stages
            base_model_specs: Base model specifications for comparison

        Returns:
            Claude response with detected spring options
        """
        request_logger = self.logger.bind(
            operation="spring_options",
            model_code=product_data.get("model_code", "unknown"),
        )

        prompt = self._build_spring_options_prompt(product_data, base_model_specs)

        request_logger.info("Starting Claude spring options analysis")

        try:
            response = await self._call_claude_api(
                prompt=prompt,
                system_message="You are an expert in snowmobile spring options, track upgrades, and suspension modifications. Analyze products for spring-related enhancements.",
                expected_format="json",
            )

            if not response.success:
                return response

            # Parse and validate spring options response
            try:
                parsed_data = json.loads(response.content)

                detected_options = []
                if "detected_options" in parsed_data:
                    for option in parsed_data["detected_options"]:
                        if self._validate_spring_option(option):
                            detected_options.append(option)

                return ClaudeResponse(
                    success=True,
                    detected_options=detected_options,
                    confidence=min(
                        max(float(parsed_data.get("overall_confidence", 0.7)), 0.0), 1.0
                    ),
                    reasoning=parsed_data.get("analysis_summary"),
                    tokens_used=response.tokens_used,
                    cost=response.cost,
                )

            except json.JSONDecodeError as e:
                return ClaudeResponse(
                    success=False,
                    error_message=f"Invalid JSON in spring options response: {e}",
                )

        except Exception as e:
            request_logger.error(
                "Unexpected error in spring options analysis", error=str(e)
            )

            return ClaudeResponse(success=False, error_message=f"Unexpected error: {e}")

    async def enrich_product_data(
        self, model_code: str, brand: str, price: float, model_year: int, **kwargs
    ) -> Optional[dict[str, Any]]:
        """
        Enrich product data with semantic analysis and specifications.
        
        Args:
            model_code: Product model code
            brand: Product brand
            price: Product price
            model_year: Model year
            **kwargs: Additional product attributes
            
        Returns:
            Enriched product data or None if enrichment fails
        """
        request_logger = self.logger.bind(
            operation="product_enrichment", 
            model_code=model_code, 
            brand=brand,
            model_year=model_year
        )
        
        request_logger.info("Starting product data enrichment")
        
        # Build enrichment prompt
        prompt = f"""
        Snowmobile Product Data Enrichment:
        
        Product Information:
        - Model Code: {model_code}
        - Brand: {brand}
        - Price: {price}
        - Model Year: {model_year}
        - Additional Data: {json.dumps(kwargs, indent=2)}
        
        Task: Enhance this product with detailed specifications, categorization, and market positioning.
        
        Provide enrichment including:
        1. Model name interpretation and full product name
        2. Category classification (Trail, Crossover, Deep Snow, etc.)
        3. Engine specifications (displacement, type, power)
        4. Track specifications (length, width, lug pattern)
        5. Key features and technology
        6. Market positioning and target audience
        
        Respond with JSON:
        {{
            "model_name": "Full interpreted model name",
            "category": "Product category",
            "specifications": {{
                "engine": {{
                    "type": "Engine type",
                    "displacement": displacement_cc,
                    "power_hp": estimated_power
                }},
                "track": {{
                    "length_mm": track_length,
                    "width_mm": track_width,
                    "lug_height_mm": lug_height
                }},
                "dimensions": {{
                    "length_mm": overall_length,
                    "width_mm": overall_width,
                    "height_mm": overall_height
                }},
                "features": ["key", "features", "list"]
            }},
            "market_positioning": "Market position description",
            "confidence": 0.85,
            "reasoning": "Explanation of enrichment decisions"
        }}
        """
        
        try:
            response = await self._call_claude_api(
                prompt=prompt,
                system_message="You are an expert in snowmobile specifications and market analysis. Provide accurate, detailed product enrichment based on model codes and brand knowledge.",
                expected_format="json"
            )
            
            if not response.success:
                request_logger.error("Product enrichment failed", error=response.error_message)
                return None
            
            # Parse enrichment response
            try:
                enriched_data = json.loads(response.content)
                
                request_logger.info(
                    "Product enrichment successful",
                    confidence=enriched_data.get('confidence', 0.0),
                    tokens_used=response.tokens_used,
                    cost=float(response.cost)
                )
                
                return enriched_data
                
            except json.JSONDecodeError as e:
                request_logger.error("Failed to parse enrichment response", error=str(e))
                return None
                
        except Exception as e:
            request_logger.error("Unexpected error in product enrichment", error=str(e))
            return None

    async def batch_enrich_products(
        self, products: list[dict[str, Any]], enrichment_type: str = "complete"
    ) -> list[ClaudeResponse]:
        """
        Batch process multiple products for cost optimization.

        Args:
            products: List of products to enrich
            enrichment_type: Type of enrichment (complete, spring_only, etc.)

        Returns:
            List of Claude responses, one per product
        """
        self.logger.info(
            "Starting batch product enrichment",
            product_count=len(products),
            enrichment_type=enrichment_type,
            batch_size=self.config.batch_size,
        )

        results = []

        # Process in batches to optimize API usage
        for i in range(0, len(products), self.config.batch_size):
            batch = products[i : i + self.config.batch_size]

            self.logger.info(
                "Processing batch",
                batch_number=i // self.config.batch_size + 1,
                batch_size=len(batch),
            )

            # Build batch prompt
            batch_prompt = self._build_batch_prompt(batch, enrichment_type)

            try:
                response = await self._call_claude_api(
                    prompt=batch_prompt,
                    system_message=f"Process {len(batch)} snowmobile products for {enrichment_type} enrichment. Return JSON array with results for each product in order.",
                    expected_format="json_array",
                )

                if response.success:
                    # Parse batch response
                    batch_results = self._parse_batch_response(response, len(batch))
                    results.extend(batch_results)
                else:
                    # Fallback to individual processing for this batch
                    self.logger.warning(
                        "Batch processing failed, falling back to individual processing",
                        batch_size=len(batch),
                        error=response.error_message,
                    )

                    individual_results = await self._process_batch_individually(
                        batch, enrichment_type
                    )
                    results.extend(individual_results)

            except Exception as e:
                self.logger.error(
                    "Batch processing error", batch_size=len(batch), error=str(e)
                )

                # Create error responses for the batch
                error_responses = [
                    ClaudeResponse(
                        success=False, error_message=f"Batch processing error: {e}"
                    )
                    for _ in batch
                ]
                results.extend(error_responses)

            # Rate limiting between batches
            await asyncio.sleep(self._min_request_interval)

        self.logger.info(
            "Batch enrichment completed",
            total_products=len(products),
            successful_results=sum(1 for r in results if r.success),
            failed_results=sum(1 for r in results if not r.success),
        )

        return results

    async def _call_claude_api(
        self, prompt: str, system_message: str, expected_format: str = "text"
    ) -> ClaudeResponse:
        """
        Core Claude API call with proper error handling and cost tracking.

        Args:
            prompt: User prompt
            system_message: System context message
            expected_format: Expected response format (text, json, json_array)

        Returns:
            Claude response with content and metadata
        """
        # Rate limiting
        await self._enforce_rate_limit()

        # Prepare request payload
        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "system": system_message,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Add format-specific instructions
        if expected_format == "json":
            payload["messages"][0]["content"] += "\n\nRespond with valid JSON only."
        elif expected_format == "json_array":
            payload["messages"][0][
                "content"
            ] += "\n\nRespond with a valid JSON array only."

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        # Execute request with retries
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self.client.post(
                    "https://api.anthropic.com/v1/messages",
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 200:
                    response_data = response.json()
                    content = response_data.get("content", [{}])[0].get("text", "")

                    # Extract usage information
                    usage = response_data.get("usage", {})
                    tokens_used = usage.get("input_tokens", 0) + usage.get(
                        "output_tokens", 0
                    )
                    cost = self._calculate_cost(usage)

                    # Update tracking
                    self._total_tokens_used += tokens_used
                    self._total_cost += cost

                    self.logger.info(
                        "Claude API call successful",
                        tokens_used=tokens_used,
                        cost=float(cost),
                        attempt=attempt + 1,
                    )

                    return ClaudeResponse(
                        success=True,
                        content=content,
                        tokens_used=tokens_used,
                        cost=cost,
                    )

                elif response.status_code == 429:  # Rate limited
                    if attempt < self.config.max_retries:
                        wait_time = (attempt + 1) * 2  # Exponential backoff
                        self.logger.warning(
                            "Rate limited, retrying",
                            attempt=attempt + 1,
                            wait_time=wait_time,
                        )
                        await asyncio.sleep(wait_time)
                        continue

                # Other HTTP errors
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.logger.error("Claude API error", error=error_msg)

                return ClaudeResponse(success=False, error_message=error_msg)

            except httpx.TimeoutException:
                if attempt < self.config.max_retries:
                    self.logger.warning(
                        "Request timeout, retrying",
                        attempt=attempt + 1,
                        timeout=self.config.timeout_seconds,
                    )
                    await asyncio.sleep(1)
                    continue

                return ClaudeResponse(
                    success=False,
                    error_message=f"Request timeout after {self.config.timeout_seconds}s",
                )

            except Exception as e:
                self.logger.error(
                    "Unexpected error calling Claude API",
                    error=str(e),
                    attempt=attempt + 1,
                )

                if attempt < self.config.max_retries:
                    await asyncio.sleep(1)
                    continue

                return ClaudeResponse(
                    success=False, error_message=f"API call failed: {e}"
                )

        return ClaudeResponse(success=False, error_message="Max retries exceeded")

    def _build_spring_options_prompt(
        self, product_data: dict[str, Any], base_model_specs: dict[str, Any]
    ) -> str:
        """Build comprehensive prompt for spring options analysis"""

        prompt = f"""
        Snowmobile Spring Options Analysis:

        Product Information:
        - Model Code: {product_data.get('model_code', 'N/A')}
        - Brand: {product_data.get('brand', 'N/A')}
        - Model Name: {product_data.get('model_name', 'N/A')}
        - Category: {product_data.get('category', 'N/A')}

        Base Model Specifications:
        {json.dumps(base_model_specs, indent=2)}

        Current Product Specifications:
        {json.dumps(product_data.get('specifications', {}), indent=2)}

        Task: Analyze for spring-related modifications and upgrades.

        Look for:
        1. Track upgrades (longer, wider, different lug patterns)
        2. Suspension upgrades (premium shocks, springs)
        3. Color variations from base model
        4. Feature additions (handwarmers, electric start, etc.)

        Respond with JSON:
        {{
            "detected_options": [
                {{
                    "option_type": "track_upgrade|color_change|suspension_upgrade|feature_addition",
                    "description": "Human-readable description",
                    "technical_details": {{}},
                    "confidence": 0.85,
                    "detection_method": "specification_comparison|model_code_analysis",
                    "claude_reasoning": "Explanation of detection logic"
                }}
            ],
            "overall_confidence": 0.8,
            "analysis_summary": "Overall analysis of detected spring options"
        }}
        """

        return prompt

    def _build_batch_prompt(self, products: list[dict], enrichment_type: str) -> str:
        """Build prompt for batch processing multiple products"""

        prompt = f"""
        Batch Snowmobile Product Enrichment - {enrichment_type}

        Process the following {len(products)} products:

        """

        for i, product in enumerate(products, 1):
            prompt += f"""
            Product {i}:
            - Model Code: {product.get('model_code', 'N/A')}
            - Brand: {product.get('brand', 'N/A')}
            - Specifications: {json.dumps(product.get('specifications', {}), indent=2)}

            """

        prompt += f"""
        Task: Perform {enrichment_type} enrichment for each product.

        Respond with JSON array containing results for each product in order:
        [
            {{
                "product_index": 1,
                "enrichment_result": {{...}},
                "confidence": 0.85,
                "warnings": []
            }},
            ...
        ]
        """

        return prompt

    def _validate_spring_option(self, option: dict[str, Any]) -> bool:
        """Validate spring option has required structure"""
        required_fields = ["option_type", "description", "confidence"]
        return all(field in option for field in required_fields)

    def _parse_batch_response(
        self, response: ClaudeResponse, expected_count: int
    ) -> list[ClaudeResponse]:
        """Parse batch response into individual Claude responses"""
        try:
            batch_data = json.loads(response.content)

            if not isinstance(batch_data, list):
                raise ValueError("Expected JSON array")

            if len(batch_data) != expected_count:
                raise ValueError(
                    f"Expected {expected_count} results, got {len(batch_data)}"
                )

            results = []
            tokens_per_product = response.tokens_used // expected_count
            cost_per_product = response.cost / expected_count

            for item in batch_data:
                results.append(
                    ClaudeResponse(
                        success=True,
                        content=json.dumps(item.get("enrichment_result", {})),
                        confidence=item.get("confidence", 0.7),
                        tokens_used=tokens_per_product,
                        cost=cost_per_product,
                    )
                )

            return results

        except Exception as e:
            # Return error responses for all products in batch
            return [
                ClaudeResponse(
                    success=False, error_message=f"Batch response parsing failed: {e}"
                )
                for _ in range(expected_count)
            ]

    async def _process_batch_individually(
        self, products: list[dict], enrichment_type: str
    ) -> list[ClaudeResponse]:
        """Fallback to process batch products individually"""
        results = []

        for product in products:
            if enrichment_type == "spring_options":
                response = await self.enrich_spring_options(product, {})
            else:
                # Default to basic enrichment
                response = ClaudeResponse(
                    success=False,
                    error_message=f"Unsupported individual enrichment type: {enrichment_type}",
                )

            results.append(response)
            await asyncio.sleep(self._min_request_interval)

        return results

    async def _enforce_rate_limit(self) -> None:
        """Enforce minimum interval between requests"""
        import time

        current_time = time.time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self._min_request_interval:
            wait_time = self._min_request_interval - time_since_last
            await asyncio.sleep(wait_time)

        self._last_request_time = time.time()

    def _calculate_cost(self, usage: dict[str, int]) -> Decimal:
        """Calculate API cost based on token usage"""
        # Claude 3 Haiku pricing (as of 2024)
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        # Pricing per 1M tokens
        input_cost_per_million = Decimal("0.25")  # $0.25 per 1M input tokens
        output_cost_per_million = Decimal("1.25")  # $1.25 per 1M output tokens

        input_cost = (Decimal(str(input_tokens)) / Decimal("1000000")) * input_cost_per_million
        output_cost = (Decimal(str(output_tokens)) / Decimal("1000000")) * output_cost_per_million

        return input_cost + output_cost

    def get_usage_statistics(self) -> dict[str, Any]:
        """Get current usage statistics"""
        return {
            "total_tokens_used": self._total_tokens_used,
            "total_cost": float(self._total_cost),
            "average_cost_per_request": float(self._total_cost)
            / max(1, self._total_tokens_used // 1000),
        }

    async def close(self) -> None:
        """Close HTTP client and cleanup resources"""
        await self.client.aclose()
        self.logger.info(
            "Claude service closed",
            total_tokens_used=self._total_tokens_used,
            total_cost=float(self._total_cost),
        )
