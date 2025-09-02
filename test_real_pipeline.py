"""
Real Pipeline Test - Tests actual PDF processing and Claude API
No database complexity - focuses on the core functionality
"""
import asyncio
import json
import os
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
if not CLAUDE_API_KEY:
    raise ValueError("CLAUDE_API_KEY not found in .env file")

# Target model codes to test
TARGET_MODELS = ["ADTD", "ADTC"]

# PDF files to process
PRICE_LIST_PDF = Path("TEST_DUAL_PARSER_PIPELINE/docs/SKI-DOO_2026-PRICE_LIST.pdf")
SPEC_BOOK_PDF = Path(
    "../../../AppData/Roaming/JetBrains/PyCharm2025.1/scratches/SKIDOO_2026 PRODUCT SPEC BOOK 1-35.pdf")


async def test_real_pdf_processing():
    """Test real PDF processing without database complexity"""
    
    print("=" * 80)
    print("REAL PIPELINE TEST - PDF Processing + Claude API")
    print("=" * 80)
    print(f"Timestamp: {datetime.now()}")
    print(f"Target Models: {', '.join(TARGET_MODELS)}")
    print(f"Price List PDF: {PRICE_LIST_PDF}")
    print(f"Spec Book PDF: {SPEC_BOOK_PDF}")
    print(f"Claude API Key: {'Configured' if CLAUDE_API_KEY else 'Missing'}")
    print("=" * 80)
    
    # Check if PDF files exist
    if not PRICE_LIST_PDF.exists():
        raise FileNotFoundError(f"Price list PDF not found: {PRICE_LIST_PDF}")
    if not SPEC_BOOK_PDF.exists():
        raise FileNotFoundError(f"Spec book PDF not found: {SPEC_BOOK_PDF}")
    
    print(f"PDF Files Found:")
    print(f"  Price List: {PRICE_LIST_PDF.stat().st_size:,} bytes")
    print(f"  Spec Book: {SPEC_BOOK_PDF.stat().st_size:,} bytes")
    
    # Test results storage
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "target_models": TARGET_MODELS,
        "pdf_files": {
            "price_list": {
                "path": str(PRICE_LIST_PDF),
                "size_bytes": PRICE_LIST_PDF.stat().st_size
            },
            "spec_book": {
                "path": str(SPEC_BOOK_PDF),
                "size_bytes": SPEC_BOOK_PDF.stat().st_size
            }
        },
        "processing_results": [],
        "errors": [],
        "claude_interactions": [],
        "performance_metrics": {}
    }
    
    start_time = time.time()
    
    try:
        print("\n" + "-" * 60)
        print("TESTING REAL PDF PROCESSING")
        print("-" * 60)
        
        # Import and initialize PDF processing service
        import sys
        sys.path.append("snowmobile-reconciliation")
        
        from src.services.claude_enrichment import ClaudeEnrichmentService
        from src.services.pdf_extraction_service import PDFProcessingService
        from src.models.domain import PipelineConfig
        
        # Initialize with real Claude API key
        config = PipelineConfig()
        claude_service = ClaudeEnrichmentService(config.claude_config, api_key=CLAUDE_API_KEY)
        pdf_service = PDFProcessingService(claude_service)
        
        print(f"Services initialized with real Claude API")
        
        # Test PDF extraction for each target model
        for model_code in TARGET_MODELS:
            model_start_time = time.time()
            
            print(f"\nProcessing model: {model_code}")
            print(f"  Extracting from: {PRICE_LIST_PDF.name}")
            
            try:
                # Extract using real PDF processing service
                extraction_result = await pdf_service.process_price_list_pdf(
                    PRICE_LIST_PDF,
                    model_code
                )
                
                model_processing_time = (time.time() - model_start_time) * 1000
                
                print(f"  Processing time: {model_processing_time:.1f}ms")
                print(f"  Result type: {type(extraction_result)}")
                
                # Analyze the result
                result_data = {
                    "model_code": model_code,
                    "processing_time_ms": model_processing_time,
                    "extraction_success": False,
                    "extracted_data": {},
                    "error": None
                }
                
                if hasattr(extraction_result, 'extraction_success'):
                    # PDF extraction result object
                    result_data.update({
                        "extraction_success": extraction_result.extraction_success,
                        "extracted_data": {
                            "model_code": getattr(extraction_result, 'model_code', None),
                            "price": float(getattr(extraction_result, 'price', 0)),
                            "currency": getattr(extraction_result, 'currency', None),
                            "model_name": getattr(extraction_result, 'model_name', None),
                            "specifications": getattr(extraction_result, 'specifications', {})
                        }
                    })
                    
                    if extraction_result.extraction_success:
                        print(f"  Success: Found {model_code}")
                        print(f"    Price: {extraction_result.price} {extraction_result.currency}")
                        print(f"    Model Name: {extraction_result.model_name}")
                        print(f"    Specifications: {len(extraction_result.specifications or {})} items")
                        
                        # Test Claude enrichment if model found
                        if extraction_result.price and extraction_result.price > 0:
                            print(f"    Testing Claude enrichment...")
                            claude_start_time = time.time()
                            
                            try:
                                enrichment_result = await claude_service.enrich_product_data(
                                    model_code=model_code,
                                    brand="Ski-Doo",
                                    price=float(extraction_result.price),
                                    model_year=2026
                                )
                                
                                claude_processing_time = (time.time() - claude_start_time) * 1000
                                
                                print(f"    Claude processing time: {claude_processing_time:.1f}ms")
                                print(f"    Claude result type: {type(enrichment_result)}")
                                
                                # Store Claude interaction
                                claude_interaction = {
                                    "model_code": model_code,
                                    "processing_time_ms": claude_processing_time,
                                    "success": enrichment_result is not None,
                                    "result_keys": list(enrichment_result.keys()) if isinstance(enrichment_result, dict) else [],
                                    "result_preview": str(enrichment_result)[:200] if enrichment_result else None
                                }
                                
                                test_results["claude_interactions"].append(claude_interaction)
                                result_data["claude_enrichment"] = enrichment_result
                                
                                if enrichment_result:
                                    print(f"    Claude enrichment successful")
                                    if isinstance(enrichment_result, dict):
                                        for key, value in enrichment_result.items():
                                            print(f"      {key}: {str(value)[:100]}...")
                                else:
                                    print(f"    Claude enrichment returned empty result")
                                    
                            except Exception as e:
                                claude_processing_time = (time.time() - claude_start_time) * 1000
                                error_msg = f"Claude enrichment failed: {str(e)}"
                                print(f"    {error_msg}")
                                test_results["errors"].append(error_msg)
                                
                                claude_interaction = {
                                    "model_code": model_code,
                                    "processing_time_ms": claude_processing_time,
                                    "success": False,
                                    "error": str(e)
                                }
                                test_results["claude_interactions"].append(claude_interaction)
                        
                    else:
                        print(f"  Failed to extract {model_code} from PDF")
                        result_data["error"] = "PDF extraction failed"
                        
                elif isinstance(extraction_result, list):
                    # List of results
                    result_data.update({
                        "extraction_success": len(extraction_result) > 0,
                        "extracted_data": {
                            "count": len(extraction_result),
                            "items": [str(item)[:100] for item in extraction_result[:3]]
                        }
                    })
                    print(f"  Got list of {len(extraction_result)} results")
                    
                else:
                    # Other result type
                    result_data.update({
                        "extraction_success": extraction_result is not None,
                        "extracted_data": {
                            "type": str(type(extraction_result)),
                            "value": str(extraction_result)[:200] if extraction_result else None
                        }
                    })
                    print(f"  Got result: {type(extraction_result)}")
                
                test_results["processing_results"].append(result_data)
                
            except Exception as e:
                model_processing_time = (time.time() - model_start_time) * 1000
                error_msg = f"Model {model_code} processing failed: {str(e)}"
                print(f"  ERROR: {error_msg}")
                
                test_results["errors"].append(error_msg)
                test_results["processing_results"].append({
                    "model_code": model_code,
                    "processing_time_ms": model_processing_time,
                    "extraction_success": False,
                    "error": str(e)
                })
        
        # Calculate final metrics
        total_time = (time.time() - start_time) * 1000
        
        test_results["performance_metrics"] = {
            "total_processing_time_ms": total_time,
            "models_processed": len(TARGET_MODELS),
            "successful_extractions": sum(1 for r in test_results["processing_results"] if r.get("extraction_success")),
            "failed_extractions": sum(1 for r in test_results["processing_results"] if not r.get("extraction_success")),
            "claude_interactions": len(test_results["claude_interactions"]),
            "successful_claude_calls": sum(1 for c in test_results["claude_interactions"] if c.get("success")),
            "average_processing_time_ms": total_time / len(TARGET_MODELS) if TARGET_MODELS else 0
        }
        
        # Cleanup
        await claude_service.close()
        
        print("\n" + "-" * 60)
        print("TEST RESULTS SUMMARY")
        print("-" * 60)
        
        metrics = test_results["performance_metrics"]
        print(f"Total Processing Time: {metrics['total_processing_time_ms']:.1f}ms")
        print(f"Models Processed: {metrics['models_processed']}")
        print(f"Successful Extractions: {metrics['successful_extractions']}")
        print(f"Failed Extractions: {metrics['failed_extractions']}")
        print(f"Claude Interactions: {metrics['claude_interactions']}")
        print(f"Successful Claude Calls: {metrics['successful_claude_calls']}")
        
        if test_results["errors"]:
            print(f"\nErrors ({len(test_results['errors'])}):")
            for error in test_results["errors"]:
                print(f"  - {error}")
        
        # Save results
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        
        json_file = results_dir / f"real_pipeline_test_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(json_file, "w") as f:
            json.dump(test_results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: {json_file}")
        
        # Create simple HTML report
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Real Pipeline Test Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
        h1 {{ color: #2c3e50; text-align: center; }}
        .summary {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #3498db; color: white; border-radius: 5px; }}
        .success {{ background: #27ae60; }}
        .error {{ background: #e74c3c; }}
        .result {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
        pre {{ background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Real Pipeline Test Results</h1>
        
        <div class="summary">
            <h2>Test Summary</h2>
            <div class="metric">Total Time: {metrics['total_processing_time_ms']:.1f}ms</div>
            <div class="metric">Models: {metrics['models_processed']}</div>
            <div class="metric success">Success: {metrics['successful_extractions']}</div>
            <div class="metric error">Failed: {metrics['failed_extractions']}</div>
            <div class="metric">Claude Calls: {metrics['claude_interactions']}</div>
        </div>
        
        <h2>Processing Results</h2>
"""
        
        for result in test_results["processing_results"]:
            status_class = "success" if result.get("extraction_success") else "error"
            html_content += f"""
        <div class="result {status_class}">
            <h3>Model: {result['model_code']}</h3>
            <p><strong>Success:</strong> {result.get('extraction_success', False)}</p>
            <p><strong>Processing Time:</strong> {result.get('processing_time_ms', 0):.1f}ms</p>
            <pre>{json.dumps(result.get('extracted_data', {}), indent=2)}</pre>
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        html_file = results_dir / f"real_pipeline_test_{datetime.now():%Y%m%d_%H%M%S}.html"
        with open(html_file, "w") as f:
            f.write(html_content)
        
        print(f"HTML report saved to: {html_file}")
        print(f"Open in browser: file://{html_file.absolute()}")
        
        return test_results
        
    except Exception as e:
        error_msg = f"Test failed with error: {str(e)}"
        print(f"FATAL ERROR: {error_msg}")
        test_results["errors"].append(error_msg)
        return test_results


async def main():
    """Run the real pipeline test"""
    try:
        results = await test_real_pdf_processing()
        
        print("\n" + "=" * 80)
        print("REAL PIPELINE TEST COMPLETE")
        
        metrics = results.get("performance_metrics", {})
        if metrics.get("successful_extractions", 0) > 0:
            print("SUCCESS: At least one model was successfully extracted and processed")
        else:
            print("NO SUCCESSFUL EXTRACTIONS: Check PDF content and model codes")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())