#!/usr/bin/env python3
"""
Test AYTS snowmobile processing with production pipeline.
Uses the actual production pipeline to process AYTS model.
"""
import asyncio
import json
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Add snowmobile-reconciliation src to path
sys.path.insert(0, str(Path(__file__).parent / "snowmobile-reconciliation" / "src"))

from models.domain import PriceEntry, BaseModelSpecification
from pipeline.stages.base_model_matching import BaseModelMatchingStage
from pipeline.stages.specification_inheritance import SpecificationInheritanceStage
from pipeline.stages.customization_processing import CustomizationProcessingStage
from pipeline.stages.spring_options_enhancement import SpringOptionsEnhancementStage
from pipeline.stages.final_validation import FinalValidationStage
from config.settings import get_settings

async def process_ayts_production():
    """Process AYTS through production pipeline stages"""
    
    print("🚀 Testing AYTS with Production-Ready Pipeline")
    print("=" * 50)
    
    # Create AYTS price entry - likely a Lynx Adventure model
    ayts_entry = PriceEntry(
        model_code="AYTS",
        brand="Lynx",
        model_name="Adventure LX 600 ACE",
        price=Decimal("14995.00"),
        currency="EUR",
        market="FI",
        model_year=2025,
        source_file="LYNX_2025-PRICE_LIST.pdf",
        page_number=15,
        extraction_confidence=0.95
    )
    
    print(f"📄 Processing: {ayts_entry.model_code} - {ayts_entry.model_name}")
    print(f"💰 Price: {ayts_entry.price} {ayts_entry.currency}")
    print(f"📅 Model Year: {ayts_entry.model_year}")
    print()
    
    # Create sample base model for inheritance
    base_model = BaseModelSpecification(
        base_model_id="ADVENTURE_LX_600_BASE",
        model_name="Adventure LX 600 ACE",
        brand="Lynx",
        model_year=2025,
        category="Touring",
        engine_specs={
            "type": "600 ACE",
            "displacement": "599.4 cc",
            "cylinders": 2,
            "cooling": "Liquid-cooled",
            "fuel_system": "Electronic Fuel Injection (EFI)",
            "horsepower": "60 HP",
            "torque": "53 Nm @ 6250 RPM",
            "starter": "Electric start",
            "reverse": "Electronic RADIEN²"
        },
        dimensions={
            "overall_length": "3200 mm",
            "overall_width": "1200 mm", 
            "overall_height": "1350 mm",
            "ski_stance": "1080 mm",
            "track_length": "3923 mm",
            "track_width": "500 mm",
            "track_profile": "38 mm",
            "dry_weight": "285 kg",
            "fuel_capacity": "40 L"
        },
        suspension={
            "front": "LFS+ (Lynx Front Suspension)",
            "front_travel": "210 mm",
            "rear": "PPS²-3900",
            "rear_travel": "239 mm",
            "front_shocks": "HPG Plus",
            "rear_shocks": "HPG Plus with adjustable preload"
        },
        features={
            "heated_grips": True,
            "electric_start": True,
            "reverse": True,
            "gauge": "7.8\" Digital Display",
            "windshield": "High touring windshield",
            "seat": "2-up heated seat with backrest",
            "storage": "Integrated rear cargo box",
            "lighting": "LED headlights and taillight",
            "color_options": ["Catalyst Grey", "Intense Blue", "Viper Red"]
        },
        available_colors=["Catalyst Grey", "Intense Blue", "Viper Red"],
        track_options=[
            {"length": "3923 mm", "width": "500 mm", "profile": "38 mm", "type": "PowderMax Light"},
            {"length": "3923 mm", "width": "500 mm", "profile": "44 mm", "type": "PowderMax"}
        ],
        source_catalog="LYNX_2025_SPEC_BOOK.pdf",
        extraction_quality=0.96,
        inheritance_confidence=0.93
    )
    
    # Initialize production pipeline stages
    settings = get_settings()
    
    stage1 = BaseModelMatchingStage()
    stage2 = SpecificationInheritanceStage() 
    stage3 = CustomizationProcessingStage()
    stage4 = SpringOptionsEnhancementStage()
    stage5 = FinalValidationStage()
    
    # Create pipeline context
    from models.domain import PipelineContext
    from uuid import uuid4
    
    context = PipelineContext(
        price_entry=ayts_entry,
        processing_id=uuid4()
    )
    
    # Stage 1: Base Model Matching
    print("🔍 Stage 1: Base Model Matching")
    context.matched_base_model = base_model
    context.current_confidence = 0.92
    result1 = await stage1._execute_stage(context)
    print(f"   ✅ Base model matched: {context.matched_base_model.model_name}")
    print(f"   📊 Confidence: {context.current_confidence:.1%}")
    print()
    
    # Stage 2: Specification Inheritance
    print("📋 Stage 2: Specification Inheritance")
    result2 = await stage2._execute_stage(context)
    print(f"   ✅ Inherited {len(context.inherited_specs)} specification categories")
    print(f"   🔧 Engine: {context.inherited_specs.get('engine', {}).get('type', 'N/A')}")
    print(f"   📏 Dimensions: {len(context.inherited_specs.get('dimensions', {}))} properties")
    print(f"   📊 Confidence: {context.current_confidence:.1%}")
    print()
    
    # Stage 3: Customization Processing
    print("⚙️  Stage 3: Customization Processing")
    result3 = await stage3._execute_stage(context)
    customizations = context.customizations
    print(f"   ✅ Applied {len(customizations)} customizations")
    if customizations:
        for key, value in customizations.items():
            print(f"   • {key}: {value}")
    print(f"   📊 Confidence: {context.current_confidence:.1%}")
    print()
    
    # Stage 4: Spring Options Enhancement
    print("🎯 Stage 4: Spring Options Enhancement")
    result4 = await stage4._execute_stage(context)
    print(f"   ✅ Detected {len(context.spring_options)} spring options")
    for option in context.spring_options:
        print(f"   • {option.option_type.value}: {option.description}")
    print(f"   📊 Confidence: {context.current_confidence:.1%}")
    print()
    
    # Stage 5: Final Validation
    print("✅ Stage 5: Final Validation")
    result5 = await stage5._execute_stage(context)
    print(f"   ✅ Validation complete")
    print(f"   📊 Final Confidence: {context.current_confidence:.1%}")
    print(f"   🎯 Confidence Level: {result5.confidence_level.upper()}")
    print()
    
    # Generate final product specification
    final_product = result5
    
    print("🎉 AYTS Processing Complete!")
    print("=" * 50)
    print(f"Model Code: {final_product.model_code}")
    print(f"Final Model Name: {final_product.final_model_name}")
    print(f"Brand: {final_product.brand}")
    print(f"Price: {final_product.price} {final_product.currency}")
    print(f"Confidence: {final_product.confidence_score:.1%} ({final_product.confidence_level.upper()})")
    print(f"Processing Time: {final_product.processing_time_ms}ms")
    
    # Save detailed result
    output_file = Path("ayts_production_result.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_product.dict(), f, indent=2, default=str, ensure_ascii=False)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    return final_product

if __name__ == "__main__":
    result = asyncio.run(process_ayts_production())
    
    if result.confidence_level == "high":
        print("\n🟢 PRODUCTION READY: High confidence result - ready for PDF generation!")
    elif result.confidence_level == "medium":
        print("\n🟡 REVIEW RECOMMENDED: Medium confidence - may need manual review")
    else:
        print("\n🔴 MANUAL REVIEW REQUIRED: Low confidence - needs human validation")