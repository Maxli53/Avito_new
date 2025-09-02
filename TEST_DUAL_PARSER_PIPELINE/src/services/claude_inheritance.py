import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
from uuid import UUID
import os

from anthropic import AsyncAnthropic

from ..models.domain import (
    PriceEntry, BaseModel, Product, InheritanceResult, 
    ValidationStatus, ProcessingStatus
)
from ..repositories.database import DatabaseRepository


logger = logging.getLogger(__name__)


class ClaudeInheritanceService:
    """Claude AI intelligent specification inheritance service"""
    
    def __init__(self, db_repo: DatabaseRepository, api_key: Optional[str] = None):
        self.db_repo = db_repo
        self.claude_client = AsyncAnthropic(
            api_key=api_key or os.getenv("CLAUDE_API_KEY")
        )
        
        # Cost tracking (approximate costs per token)
        self.input_cost_per_token = 0.000003  # $3 per million tokens
        self.output_cost_per_token = 0.000015  # $15 per million tokens
    
    async def inherit_specifications(
        self, 
        price_entry: PriceEntry, 
        base_model: BaseModel
    ) -> InheritanceResult:
        """
        Use Claude AI to intelligently inherit specifications from base model to price entry
        
        Args:
            price_entry: Specific price entry with model variations
            base_model: Base model with all possible specifications
            
        Returns:
            InheritanceResult with resolved specifications and HTML content
        """
        start_time = datetime.now()
        api_calls = 0
        total_cost = Decimal("0.0")
        
        try:
            logger.info(f"Starting Claude inheritance for {price_entry.model_code}")
            
            # Build comprehensive prompt for Claude
            prompt = self._build_inheritance_prompt(price_entry, base_model)
            
            # Make Claude API call
            response = await self._call_claude_api(prompt)
            api_calls += 1
            
            # Calculate API costs
            input_tokens = len(prompt) // 4  # Rough token estimate
            output_tokens = len(response) // 4
            cost = self._calculate_api_cost(input_tokens, output_tokens)
            total_cost += cost
            
            # Parse Claude response
            parsed_result = self._parse_claude_response(response)
            
            # Validate the result
            if not self._validate_inheritance_result(parsed_result):
                raise ValueError("Invalid Claude response format")
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            result = InheritanceResult(
                specifications=parsed_result['specifications'],
                html_content=parsed_result['html_content'],
                inheritance_adjustments=parsed_result['adjustments'],
                selected_variations=parsed_result['selected_variations'],
                confidence_score=Decimal(str(parsed_result['confidence_score'])),
                reasoning=parsed_result['reasoning'],
                api_calls_used=api_calls,
                processing_time_ms=processing_time,
                cost_usd=total_cost
            )
            
            logger.info(f"Claude inheritance completed for {price_entry.model_code} in {processing_time}ms (cost: ${total_cost:.4f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Claude inheritance failed for {price_entry.model_code}: {e}")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Return error result
            return InheritanceResult(
                specifications={},
                html_content=f"<p>Error generating specifications: {str(e)}</p>",
                inheritance_adjustments={'error': str(e)},
                selected_variations={},
                confidence_score=Decimal("0.0"),
                reasoning=f"Processing failed: {str(e)}",
                api_calls_used=api_calls,
                processing_time_ms=processing_time,
                cost_usd=total_cost
            )
    
    async def generate_product(self, price_entry_id: UUID, base_model_id: UUID) -> Product:
        """
        Generate a complete product from price entry and base model using Claude inheritance
        
        Args:
            price_entry_id: UUID of the price entry
            base_model_id: UUID of the base model
            
        Returns:
            Complete Product with resolved specifications
        """
        try:
            # Load price entry and base model
            price_entry = await self.db_repo.get_price_entry(price_entry_id)
            base_model = await self.db_repo.get_base_model(base_model_id)
            
            if not price_entry or not base_model:
                raise ValueError("Price entry or base model not found")
            
            # Update price entry status to processing
            await self.db_repo.update_price_entry_status(
                price_entry_id, 
                ProcessingStatus.PROCESSING
            )
            
            # Perform Claude inheritance
            inheritance_result = await self.inherit_specifications(price_entry, base_model)
            
            # Generate SKU
            sku = self._generate_sku(price_entry)
            
            # Create product
            product = Product(
                id=UUID.hex,
                sku=sku,
                model_code=price_entry.model_code,
                brand=price_entry.brand,
                model_family=base_model.model_family,
                model_year=price_entry.model_year,
                market=price_entry.market,
                price=price_entry.price,
                currency=price_entry.currency,
                price_entry_id=price_entry.id,
                base_model_id=base_model.id,
                resolved_specifications=inheritance_result.specifications,
                inheritance_adjustments=inheritance_result.inheritance_adjustments,
                selected_variations=inheritance_result.selected_variations,
                html_content=inheritance_result.html_content,
                html_generated_at=datetime.now(),
                confidence_score=inheritance_result.confidence_score,
                validation_status=ValidationStatus.PENDING,
                auto_approved=inheritance_result.confidence_score >= Decimal("0.95"),
                claude_api_calls=inheritance_result.api_calls_used,
                claude_processing_ms=inheritance_result.processing_time_ms,
                total_cost_usd=inheritance_result.cost_usd,
                created_at=datetime.now()
            )
            
            # Store product in database
            stored_product = await self.db_repo.create_product(product)
            
            # Update price entry status to completed
            await self.db_repo.update_price_entry_status(
                price_entry_id, 
                ProcessingStatus.COMPLETED
            )
            
            logger.info(f"Generated product {stored_product.sku} from {price_entry.model_code}")
            
            return stored_product
            
        except Exception as e:
            logger.error(f"Product generation failed: {e}")
            
            # Update price entry status to failed
            if price_entry_id:
                await self.db_repo.update_price_entry_status(
                    price_entry_id, 
                    ProcessingStatus.FAILED
                )
            
            raise
    
    def _build_inheritance_prompt(self, price_entry: PriceEntry, base_model: BaseModel) -> str:
        """Build comprehensive prompt for Claude inheritance"""
        
        prompt = f"""You are an expert snowmobile specification analyst. Your task is to intelligently inherit and adjust base model specifications based on specific price entry variations.

## Context
You have a base model specification catalog and a specific price list entry. The price entry contains specific variations (engine, track, options) that need to be applied to the base model specifications.

## Base Model Information
**Brand:** {base_model.brand}
**Model Family:** {base_model.model_family}
**Year:** {base_model.model_year}

**Available Engine Options:**
{json.dumps(base_model.engine_options, indent=2) if base_model.engine_options else "None specified"}

**Available Track Options:**
{json.dumps(base_model.track_options, indent=2) if base_model.track_options else "None specified"}

**Base Dimensions:**
{json.dumps(base_model.dimensions, indent=2) if base_model.dimensions else "None specified"}

**Standard Features:**
{json.dumps(base_model.features, indent=2) if base_model.features else "None specified"}

**All Specifications:**
{json.dumps(base_model.full_specifications, indent=2) if base_model.full_specifications else "None specified"}

## Specific Price Entry (What Customer Gets)
**Model Code:** {price_entry.model_code}
**Market:** {price_entry.market}
**Price:** {price_entry.currency} {price_entry.price}

**Specific Selections:**
- **Engine (Moottori):** {price_entry.moottori or "Not specified"}
- **Track (Telamatto):** {price_entry.telamatto or "Not specified"}  
- **Starter (Käynnistin):** {price_entry.kaynnistin or "Not specified"}
- **Instruments (Mittaristo):** {price_entry.mittaristo or "Not specified"}
- **Spring Options (Kevätoptiot):** {price_entry.kevatoptiot or "Not specified"}
- **Color (Väri):** {price_entry.vari or "Not specified"}

## Your Task
Intelligently resolve the final product specifications by:

1. **Engine Resolution**: Select the correct engine specs from available options based on the specific engine mentioned in the price entry
2. **Track Resolution**: Apply the specific track configuration and its impact on dimensions/performance
3. **Feature Adjustment**: Add/remove features based on starter type, instruments, and spring options
4. **Specification Inheritance**: Keep relevant base specs, remove incompatible ones, add variant-specific specs

## Special Instructions for Spring Options (Kevätoptiot)
If spring options are specified, these typically involve:
- **Black Edition**: Usually includes black accents, special graphics, premium features
- **Performance Package**: May include upgraded suspension, handling improvements
- **Comfort Package**: Enhanced seating, storage, convenience features

## Output Format
Provide your response as a valid JSON object with the following structure:

```json
{{
    "specifications": {{
        "engine": {{
            // Final engine specifications for the selected engine only
        }},
        "track": {{
            // Final track specifications for the selected track only  
        }},
        "dimensions": {{
            // Updated dimensions (may change with different track)
        }},
        "features": [
            // Final feature list after adjustments
        ],
        "performance": {{
            // Performance specs relevant to this configuration
        }},
        "additional_specs": {{
            // Any other relevant specifications
        }}
    }},
    "selected_variations": {{
        "engine_selected": "specific engine chosen",
        "track_selected": "specific track chosen",
        "starter_type": "manual/electric",
        "instruments": "instrument package",
        "spring_options_applied": "spring options description",
        "color": "selected color"
    }},
    "adjustments": {{
        "features_added": ["list of features added due to options"],
        "features_removed": ["list of features removed due to selections"],
        "specifications_modified": ["list of specs that were changed"],
        "reasoning": "explanation of key changes made"
    }},
    "confidence_score": 0.95,
    "reasoning": "Detailed explanation of your inheritance decisions",
    "html_content": "<!-- Professional HTML specification sheet -->"
}}
```

## HTML Content Requirements
The html_content should be a complete, professional specification sheet including:
- Product header with model code, name, and price
- Engine specifications table
- Track and handling specifications  
- Dimensions and weight
- Standard and optional features lists
- Professional styling with CSS
- Market-ready presentation

Focus on accuracy and completeness. If uncertain about specific details, indicate this in your reasoning but provide the best possible interpretation based on the available information.
"""
        
        return prompt
    
    async def _call_claude_api(self, prompt: str) -> str:
        """Make API call to Claude"""
        try:
            message = await self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.1,  # Low temperature for consistent results
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise
    
    def _parse_claude_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's JSON response"""
        try:
            # Extract JSON from response (in case there's extra text)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in Claude response")
            
            json_str = response[json_start:json_end]
            parsed = json.loads(json_str)
            
            # Ensure all required fields are present
            required_fields = [
                'specifications', 'selected_variations', 'adjustments', 
                'confidence_score', 'reasoning', 'html_content'
            ]
            
            for field in required_fields:
                if field not in parsed:
                    logger.warning(f"Missing field '{field}' in Claude response, adding default")
                    parsed[field] = self._get_default_field_value(field)
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude JSON response: {e}")
            logger.debug(f"Response content: {response}")
            raise ValueError(f"Invalid JSON in Claude response: {e}")
        except Exception as e:
            logger.error(f"Failed to parse Claude response: {e}")
            raise
    
    def _get_default_field_value(self, field: str) -> Any:
        """Get default value for missing fields"""
        defaults = {
            'specifications': {},
            'selected_variations': {},
            'adjustments': {},
            'confidence_score': 0.5,
            'reasoning': 'No reasoning provided',
            'html_content': '<p>Specifications not available</p>'
        }
        return defaults.get(field, {})
    
    def _validate_inheritance_result(self, result: Dict[str, Any]) -> bool:
        """Validate Claude's inheritance result"""
        try:
            # Check required fields
            required_fields = ['specifications', 'html_content', 'confidence_score']
            for field in required_fields:
                if field not in result:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Validate confidence score
            confidence = result['confidence_score']
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                logger.error(f"Invalid confidence score: {confidence}")
                return False
            
            # Validate specifications structure
            if not isinstance(result['specifications'], dict):
                logger.error("Specifications must be a dictionary")
                return False
            
            # Validate HTML content
            if not isinstance(result['html_content'], str) or len(result['html_content']) < 10:
                logger.error("HTML content is invalid or too short")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Result validation failed: {e}")
            return False
    
    def _generate_sku(self, price_entry: PriceEntry) -> str:
        """Generate SKU for the product"""
        # Format: BRAND-MODELCODE-MARKET-YEAR
        sku = f"{price_entry.brand.upper()}-{price_entry.model_code}-{price_entry.market.upper()}-{price_entry.model_year}"
        return sku
    
    def _calculate_api_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        """Calculate API cost based on token usage"""
        input_cost = Decimal(str(input_tokens * self.input_cost_per_token))
        output_cost = Decimal(str(output_tokens * self.output_cost_per_token))
        return input_cost + output_cost
    
    async def batch_generate_products(self, price_entry_ids: List[UUID]) -> List[Product]:
        """
        Generate products for multiple price entries in batch
        
        Args:
            price_entry_ids: List of price entry UUIDs
            
        Returns:
            List of generated products
        """
        products = []
        
        logger.info(f"Starting batch product generation for {len(price_entry_ids)} entries")
        
        for price_entry_id in price_entry_ids:
            try:
                # Get matching base model for this price entry
                matching_result = await self.db_repo.get_matching_result_for_price_entry(price_entry_id)
                
                if not matching_result or not matching_result.matched:
                    logger.warning(f"No matching base model for price entry {price_entry_id}")
                    continue
                
                # Generate product
                product = await self.generate_product(price_entry_id, matching_result.base_model_id)
                products.append(product)
                
            except Exception as e:
                logger.error(f"Failed to generate product for entry {price_entry_id}: {e}")
                continue
        
        logger.info(f"Batch generation completed: {len(products)} products generated")
        
        return products
    
    async def get_generation_statistics(self) -> Dict[str, Any]:
        """Get statistics about product generation performance"""
        try:
            stats = await self.db_repo.get_product_generation_statistics()
            return {
                'total_products': stats.get('total_products', 0),
                'avg_confidence_score': float(stats.get('avg_confidence', 0)),
                'avg_processing_time_ms': stats.get('avg_processing_time', 0),
                'avg_cost_per_product': float(stats.get('avg_cost', 0)),
                'auto_approved_percentage': stats.get('auto_approved_pct', 0),
                'total_claude_api_calls': stats.get('total_api_calls', 0),
                'total_cost_usd': float(stats.get('total_cost', 0)),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get generation statistics: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}