#!/usr/bin/env python3
"""
ReportLab Integration with Existing Pipeline System
Integrates the unified vehicle specification generator into the existing 5-stage pipeline
"""

from typing import List, Dict, Optional, Any
from pathlib import Path
import logging
from dataclasses import dataclass

# Import your existing pipeline components
from src.models.domain import ProcessingStage, PipelineConfig, Product
from src.pipeline.stages.base_stage import BasePipelineStage
from src.repositories.base import BaseRepository
from src.services.claude_enrichment import ClaudeEnrichmentService

# Import the unified ReportLab generator
from unified_reportlab_generator import UnifiedVehicleSpecGenerator, BrandConfigs, BrandConfig


@dataclass
class SpecSheetConfig:
    """Configuration for specification sheet generation"""
    output_directory: Path = Path("generated_specs")
    include_images: bool = True
    image_directory: Path = Path("vehicle_images")
    generate_for_brands: List[str] = None
    auto_generate_after_pipeline: bool = True
    quality_threshold: float = 0.95  # Only generate if processing quality is high


class SpecSheetGenerationService:
    """Service for generating specification sheets from processed product data"""

    def __init__(self,
                 config: SpecSheetConfig,
                 database_path: str = "vehicles.db",
                 business_db_path: str = "business.db"):
        self.config = config
        self.database_path = database_path
        self.business_db_path = business_db_path
        self.logger = logging.getLogger(__name__)

        # Ensure output directory exists
        self.config.output_directory.mkdir(parents=True, exist_ok=True)

        # Brand generators cache
        self._generators: Dict[str, UnifiedVehicleSpecGenerator] = {}

    def get_generator_for_brand(self, brand: str) -> UnifiedVehicleSpecGenerator:
        """Get or create ReportLab generator for specific brand"""
        if brand not in self._generators:
            brand_config = BrandConfigs.get_config(brand)
            self._generators[brand] = UnifiedVehicleSpecGenerator(
                db_path=self.database_path,
                brand_config=brand_config
            )
        return self._generators[brand]

    async def generate_spec_sheet_from_product(self,
                                               product: Product,
                                               force_generate: bool = False) -> Optional[str]:
        """
        Generate specification sheet from processed pipeline product

        Args:
            product: Processed product from pipeline
            force_generate: Generate even if quality is below threshold

        Returns:
            Path to generated PDF or None if not generated
        """
        try:
            # Check quality threshold
            if not force_generate and product.processing_confidence < self.config.quality_threshold:
                self.logger.info(
                    f"Skipping spec sheet for {product.sku} - quality {product.processing_confidence:.2f} below threshold")
                return None

            # Determine brand from product data
            brand = self._extract_brand_from_product(product)
            if not brand:
                self.logger.warning(f"Could not determine brand for product {product.sku}")
                return None

            # Check if we should generate for this brand
            if (self.config.generate_for_brands and
                    brand.lower() not in [b.lower() for b in self.config.generate_for_brands]):
                return None

            # Convert pipeline product to database format
            vehicle_id = await self._sync_product_to_database(product, brand)
            if not vehicle_id:
                self.logger.error(f"Failed to sync product {product.sku} to database")
                return None

            # Generate specification sheet
            generator = self.get_generator_for_brand(brand)

            # Prepare output path
            output_filename = f"{product.sku}_{brand.lower()}_spec.pdf"
            output_path = self.config.output_directory / output_filename

            # Find vehicle image if available
            image_path = None
            if self.config.include_images:
                image_path = self._find_vehicle_image(product.sku)

            # Generate PDF
            generated_path = generator.generate_spec_sheet(
                vehicle_id=vehicle_id,
                output_path=str(output_path),
                image_path=image_path
            )

            self.logger.info(f"Generated specification sheet: {generated_path}")
            return generated_path

        except Exception as e:
            self.logger.error(f"Error generating spec sheet for {product.sku}: {e}")
            return None

    def _extract_brand_from_product(self, product: Product) -> Optional[str]:
        """Extract brand information from product data"""
        # Check explicit brand field
        if hasattr(product, 'brand') and product.brand:
            return product.brand

        # Infer from model codes or SKU patterns
        sku = product.sku.upper()

        # Lynx patterns
        if any(code in sku for code in ['LX', 'LTTA', 'LUTC', 'LYTD', 'RAVE']):
            return 'lynx'

        # Ski-Doo patterns
        if any(code in sku for code in ['MXZ', 'RENEGADE', 'EXPEDITION', 'SUMMIT']):
            return 'ski-doo'

        # Sea-Doo patterns (for future expansion)
        if any(code in sku for code in ['GTX', 'RXT', 'WAKE']):
            return 'sea-doo'

        return None

    async def _sync_product_to_database(self, product: Product, brand: str) -> Optional[int]:
        """
        Sync processed product data to ReportLab database format
        This bridges your pipeline output with the ReportLab expected schema
        """
        try:
            import sqlite3

            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()

            # Insert or update model
            cursor.execute("""
            INSERT OR REPLACE INTO models (name, platform, brand) 
            VALUES (?, ?, ?)
            """, (product.model, product.platform if hasattr(product, 'platform') else 'Unknown', brand))

            model_id = cursor.lastrowid or cursor.execute(
                "SELECT id FROM models WHERE name = ? AND brand = ?",
                (product.model, brand)
            ).fetchone()[0]

            # Extract specifications from product
            specs = product.specifications if hasattr(product, 'specifications') else {}

            # Insert vehicle
            cursor.execute("""
            INSERT OR REPLACE INTO vehicles 
            (model_id, description, platform, headlights, skis, seating, handlebar, 
             starter, reverse, brake_system, heated_grips, gauge_type, windshield, 
             usb_port, dry_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                model_id,
                getattr(product, 'description', ''),
                specs.get('platform', ''),
                specs.get('headlights', ''),
                specs.get('skis', ''),
                specs.get('seating', ''),
                specs.get('handlebar', ''),
                specs.get('starter', ''),
                specs.get('reverse', ''),
                specs.get('brake_system', ''),
                specs.get('heated_grips', ''),
                specs.get('gauge_type', ''),
                specs.get('windshield', ''),
                bool(specs.get('usb_port', False)),
                specs.get('dry_weight', 0) or 0
            ))

            vehicle_id = cursor.lastrowid

            # Insert engine data if available
            engine_specs = specs.get('engine', {})
            if engine_specs:
                cursor.execute("""
                INSERT OR REPLACE INTO engines
                (vehicle_id, name, displacement_info, bore_stroke, max_rpm, 
                 carburation, fuel_type, fuel_tank_capacity, oil_capacity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vehicle_id,
                    engine_specs.get('name', product.moottori if hasattr(product, 'moottori') else ''),
                    engine_specs.get('displacement_info', ''),
                    engine_specs.get('bore_stroke', ''),
                    engine_specs.get('max_rpm', ''),
                    engine_specs.get('carburation', ''),
                    engine_specs.get('fuel_type', ''),
                    engine_specs.get('fuel_tank_capacity', 0) or 0,
                    engine_specs.get('oil_capacity', 0.0) or 0.0
                ))

            conn.commit()
            conn.close()

            return vehicle_id

        except Exception as e:
            self.logger.error(f"Error syncing product to database: {e}")
            return None

    def _find_vehicle_image(self, sku: str) -> Optional[str]:
        """Find vehicle image file for the given SKU"""
        if not self.config.image_directory.exists():
            return None

        # Common image extensions
        extensions = ['.jpg', '.jpeg', '.png', '.webp']

        # Try exact SKU match first
        for ext in extensions:
            image_path = self.config.image_directory / f"{sku}{ext}"
            if image_path.exists():
                return str(image_path)

        # Try case insensitive match
        for ext in extensions:
            image_path = self.config.image_directory / f"{sku.lower()}{ext}"
            if image_path.exists():
                return str(image_path)

        return None


class SpecSheetPipelineStage(BasePipelineStage):
    """Pipeline stage for automatic specification sheet generation"""

    def __init__(self, config: PipelineConfig, spec_sheet_service: SpecSheetGenerationService):
        super().__init__(ProcessingStage.FINAL_VALIDATION, config)  # Run after final validation
        self.spec_sheet_service = spec_sheet_service

    async def _execute_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specification sheet generation stage"""
        try:
            products = context.get('processed_products', [])
            generated_specs = []

            for product in products:
                if not self.spec_sheet_service.config.auto_generate_after_pipeline:
                    continue

                spec_path = await self.spec_sheet_service.generate_spec_sheet_from_product(product)
                if spec_path:
                    generated_specs.append({
                        'sku': product.sku,
                        'spec_sheet_path': spec_path
                    })

            return {
                'success': True,
                'generated_specifications': generated_specs,
                'generation_count': len(generated_specs)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"Specification sheet generation failed: {str(e)}"
            }


# Integration with existing WooCommerce tools
class WooCommerceSpecSheetIntegration:
    """Integration with existing WooCommerce system"""

    def __init__(self, spec_sheet_service: SpecSheetGenerationService):
        self.spec_sheet_service = spec_sheet_service

    async def generate_specs_for_sku_list(self, sku_list: List[str]) -> Dict[str, str]:
        """
        Generate specification sheets for a list of SKUs
        Integrates with existing WooCommerce SKU processing
        """
        results = {}

        for sku in sku_list:
            # Query your business database for product data
            product_data = await self._get_product_by_sku(sku)
            if not product_data:
                continue

            # Convert to Product model format
            product = self._convert_db_to_product(product_data)

            # Generate spec sheet
            spec_path = await self.spec_sheet_service.generate_spec_sheet_from_product(
                product, force_generate=True
            )

            if spec_path:
                results[sku] = spec_path

        return results

    async def _get_product_by_sku(self, sku: str) -> Optional[Dict]:
        """Get product data from your business database"""
        # This should integrate with your existing database query methods
        # from your ridebase-woocommerce tools
        pass

    def _convert_db_to_product(self, db_data: Dict) -> Product:
        """Convert database format to Product model"""
        # Convert your database format to the Product model used in pipeline
        pass


# CLI Integration
def add_reportlab_cli_commands():
    """Add ReportLab commands to your existing CLI"""

    import click
    from src.cli import cli  # Your existing CLI

    @cli.group()
    def specs():
        """Specification sheet generation commands"""
        pass

    @specs.command()
    @click.argument('sku')
    @click.option('--brand', help='Vehicle brand (lynx, ski-doo)')
    @click.option('--force', is_flag=True, help='Generate even if quality is low')
    def generate(sku: str, brand: str, force: bool):
        """Generate specification sheet for single SKU"""
        import asyncio

        config = SpecSheetConfig()
        service = SpecSheetGenerationService(config)

        # Get product data and generate
        # Implementation depends on your existing data access patterns
        click.echo(f"Generating specification sheet for {sku}...")

    @specs.command()
    @click.option('--brand', help='Filter by brand')
    @click.option('--batch-size', default=10, help='Batch processing size')
    def generate_all(brand: str, batch_size: int):
        """Generate specification sheets for all products"""
        click.echo("Generating all specification sheets...")
        # Batch processing implementation

    @specs.command()
    def status():
        """Show specification sheet generation status"""
        config = SpecSheetConfig()
        specs_dir = config.output_directory

        if specs_dir.exists():
            spec_count = len(list(specs_dir.glob('*.pdf')))
            click.echo(f"Generated specifications: {spec_count}")
        else:
            click.echo("No specifications directory found")


# Usage Examples for Integration
async def integrate_with_existing_pipeline():
    """Example of how to integrate with your existing 5-stage pipeline"""

    # 1. Add specification sheet service to your pipeline config
    spec_config = SpecSheetConfig(
        output_directory=Path("output/specifications"),
        generate_for_brands=['lynx', 'ski-doo'],
        auto_generate_after_pipeline=True,
        quality_threshold=0.95
    )

    spec_service = SpecSheetGenerationService(spec_config)

    # 2. Create pipeline stage (optional - for automatic generation)
    spec_stage = SpecSheetPipelineStage(
        config=pipeline_config,  # Your existing pipeline config
        spec_sheet_service=spec_service
    )

    # 3. Add to your pipeline stages (after final validation)
    pipeline_stages = [
        # Your existing stages...
        base_model_matching_stage,
        specification_inheritance_stage,
        customization_processing_stage,
        spring_options_enhancement_stage,
        final_validation_stage,
        spec_stage  # Add spec sheet generation
    ]

    # 4. Manual generation for specific products
    woo_integration = WooCommerceSpecSheetIntegration(spec_service)

    # Generate for specific SKUs
    results = await woo_integration.generate_specs_for_sku_list(['LTTA', 'MXZ123'])

    print(f"Generated {len(results)} specification sheets")


if __name__ == "__main__":
    import asyncio

    asyncio.run(integrate_with_existing_pipeline())