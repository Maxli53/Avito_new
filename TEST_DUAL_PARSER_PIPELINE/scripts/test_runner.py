#!/usr/bin/env python3
"""
Advanced Test Runner for Avito Pipeline
=======================================

Production-ready test execution with comprehensive reporting and quality gates.
Supports multiple test levels, parallel execution, and CI/CD integration.

Usage:
    python scripts/test_runner.py --help
    python scripts/test_runner.py --level unit
    python scripts/test_runner.py --level full --parallel --coverage
    python scripts/test_runner.py --level e2e --timeout 300 --report
"""

import argparse
import os
import sys
import subprocess
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import xml.etree.ElementTree as ET


@dataclass
class TestResult:
    """Test execution result"""
    level: str
    status: str
    duration: float
    total_tests: int
    passed: int
    failed: int
    skipped: int
    coverage: Optional[float] = None
    report_path: Optional[str] = None
    error_message: Optional[str] = None


class AdvancedTestRunner:
    """Advanced test runner with comprehensive features"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests"
        self.results_dir = project_root / "test-results"
        self.coverage_dir = project_root / "htmlcov"
        self.results: List[TestResult] = []
        
        # Ensure directories exist
        self.results_dir.mkdir(exist_ok=True)
        self.coverage_dir.mkdir(exist_ok=True)
        
        # Test level configurations
        self.test_configs = {
            "unit": {
                "markers": "unit and not slow",
                "timeout": 300,
                "parallel": True,
                "coverage_required": True,
                "coverage_threshold": 95,
                "max_failures": 10
            },
            "integration": {
                "markers": "integration and not external",
                "timeout": 600,
                "parallel": True,
                "coverage_required": True,
                "coverage_threshold": 85,
                "max_failures": 5
            },
            "e2e": {
                "markers": "e2e and not external",
                "timeout": 1200,
                "parallel": False,
                "coverage_required": False,
                "coverage_threshold": 80,
                "max_failures": 3
            },
            "external": {
                "markers": "external",
                "timeout": 1800,
                "parallel": False,
                "coverage_required": False,
                "coverage_threshold": 70,
                "max_failures": 2
            },
            "performance": {
                "markers": "performance or slow",
                "timeout": 1800,
                "parallel": False,
                "coverage_required": False,
                "coverage_threshold": 0,
                "max_failures": 1
            },
            "full": {
                "markers": "",
                "timeout": 3600,
                "parallel": True,
                "coverage_required": True,
                "coverage_threshold": 90,
                "max_failures": 15
            }
        }
    
    def run_test_level(
        self,
        level: str,
        parallel: Optional[bool] = None,
        coverage: Optional[bool] = None,
        timeout: Optional[int] = None,
        verbose: bool = True,
        report: bool = True
    ) -> TestResult:
        """Run tests for a specific level"""
        
        if level not in self.test_configs:
            raise ValueError(f"Unknown test level: {level}")
        
        config = self.test_configs[level]
        start_time = time.time()
        
        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        
        # Test paths
        if level == "full":
            cmd.append("tests/")
        else:
            cmd.append(f"tests/")
        
        # Markers
        if config["markers"]:
            cmd.extend(["-m", config["markers"]])
        
        # Verbosity
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")
        
        # Parallel execution
        if parallel if parallel is not None else config["parallel"]:
            cmd.extend(["-n", "auto"])
        
        # Timeout
        test_timeout = timeout if timeout is not None else config["timeout"]
        cmd.extend(["--timeout", str(test_timeout)])
        
        # Coverage
        enable_coverage = coverage if coverage is not None else config["coverage_required"]
        if enable_coverage:
            cmd.extend([
                "--cov=core",
                "--cov=pipeline",
                "--cov-report=term-missing",
                "--cov-report=html:" + str(self.coverage_dir / f"htmlcov-{level}"),
                "--cov-report=xml:" + str(self.results_dir / f"coverage-{level}.xml"),
                f"--cov-fail-under={config['coverage_threshold']}"
            ])
        
        # Output files
        junit_file = self.results_dir / f"junit-{level}.xml"
        cmd.extend(["--junit-xml", str(junit_file)])
        
        # Max failures
        cmd.extend(["--maxfail", str(config["max_failures"])])
        
        # Additional options
        cmd.extend([
            "--tb=short",
            "--strict-markers",
            "--disable-warnings"
        ])
        
        # Execute tests
        print(f"\n🚀 Running {level.upper()} tests...")
        print(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=test_timeout + 60  # Add buffer
            )
            
            duration = time.time() - start_time
            
            # Parse results
            test_result = self._parse_junit_results(
                junit_file, level, duration, result.returncode == 0
            )
            
            # Parse coverage if enabled
            if enable_coverage:
                test_result.coverage = self._parse_coverage_results(
                    self.results_dir / f"coverage-{level}.xml"
                )
            
            # Generate report
            if report:
                self._generate_test_report(test_result, result.stdout, result.stderr)
            
            # Print summary
            self._print_test_summary(test_result)
            
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                level=level,
                status="timeout",
                duration=duration,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                error_message=f"Tests timed out after {test_timeout} seconds"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                level=level,
                status="error",
                duration=duration,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                error_message=str(e)
            )
    
    def _parse_junit_results(self, junit_file: Path, level: str, duration: float, success: bool) -> TestResult:
        """Parse JUnit XML results"""
        
        if not junit_file.exists():
            return TestResult(
                level=level,
                status="error",
                duration=duration,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                error_message="JUnit file not found"
            )
        
        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
            total = int(root.get('tests', 0))
            failures = int(root.get('failures', 0))
            errors = int(root.get('errors', 0))
            skipped = int(root.get('skipped', 0))
            passed = total - failures - errors - skipped
            
            # Determine status
            if failures > 0 or errors > 0:
                status = "failed"
            elif not success:
                status = "failed"
            else:
                status = "passed"
            
            return TestResult(
                level=level,
                status=status,
                duration=duration,
                total_tests=total,
                passed=passed,
                failed=failures + errors,
                skipped=skipped,
                report_path=str(junit_file)
            )
            
        except Exception as e:
            return TestResult(
                level=level,
                status="error",
                duration=duration,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                error_message=f"Failed to parse JUnit results: {e}"
            )
    
    def _parse_coverage_results(self, coverage_file: Path) -> Optional[float]:
        """Parse coverage XML results"""
        
        if not coverage_file.exists():
            return None
        
        try:
            tree = ET.parse(coverage_file)
            root = tree.getroot()
            
            # Find coverage percentage
            coverage_elem = root.find(".//coverage")
            if coverage_elem is not None:
                line_rate = float(coverage_elem.get('line-rate', 0))
                return line_rate * 100
            
            return None
            
        except Exception:
            return None
    
    def _generate_test_report(self, test_result: TestResult, stdout: str, stderr: str):
        """Generate detailed test report"""
        
        report_file = self.results_dir / f"report-{test_result.level}.md"
        
        with open(report_file, 'w') as f:
            f.write(f"# Test Report: {test_result.level.upper()}\n\n")
            f.write(f"**Date:** {datetime.now().isoformat()}\n")
            f.write(f"**Duration:** {test_result.duration:.2f} seconds\n")
            f.write(f"**Status:** {test_result.status.upper()}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Total Tests:** {test_result.total_tests}\n")
            f.write(f"- **Passed:** {test_result.passed} ✅\n")
            f.write(f"- **Failed:** {test_result.failed} ❌\n")
            f.write(f"- **Skipped:** {test_result.skipped} ⏭️\n")
            
            if test_result.total_tests > 0:
                success_rate = test_result.passed / test_result.total_tests * 100
                f.write(f"- **Success Rate:** {success_rate:.1f}%\n")
            
            if test_result.coverage is not None:
                f.write(f"- **Coverage:** {test_result.coverage:.1f}%\n")
            
            f.write("\n## Output\n\n")
            if stdout:
                f.write("### STDOUT\n```\n")
                f.write(stdout)
                f.write("\n```\n\n")
            
            if stderr:
                f.write("### STDERR\n```\n")
                f.write(stderr)
                f.write("\n```\n\n")
            
            if test_result.error_message:
                f.write("### ERROR\n")
                f.write(f"```\n{test_result.error_message}\n```\n")
        
        test_result.report_path = str(report_file)
    
    def _print_test_summary(self, test_result: TestResult):
        """Print test summary to console"""
        
        status_emoji = "✅" if test_result.status == "passed" else "❌"
        
        print(f"\n{status_emoji} {test_result.level.upper()} TESTS SUMMARY")
        print("=" * 50)
        print(f"Status: {test_result.status.upper()}")
        print(f"Duration: {test_result.duration:.2f}s")
        print(f"Total Tests: {test_result.total_tests}")
        print(f"Passed: {test_result.passed}")
        print(f"Failed: {test_result.failed}")
        print(f"Skipped: {test_result.skipped}")
        
        if test_result.total_tests > 0:
            success_rate = test_result.passed / test_result.total_tests * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        if test_result.coverage is not None:
            print(f"Coverage: {test_result.coverage:.1f}%")
        
        if test_result.error_message:
            print(f"Error: {test_result.error_message}")
        
        print()
    
    def run_quality_gate(self, results: List[TestResult]) -> bool:
        """Evaluate quality gate based on test results"""
        
        print("\n🚦 QUALITY GATE EVALUATION")
        print("=" * 50)
        
        critical_failures = 0
        total_tests = sum(r.total_tests for r in results)
        total_passed = sum(r.passed for r in results)
        
        for result in results:
            status_symbol = "✅" if result.status == "passed" else "❌"
            print(f"{status_symbol} {result.level.upper()}: {result.status}")
            
            # Critical test levels
            if result.level in ["unit", "integration"] and result.status != "passed":
                critical_failures += 1
        
        print(f"\nOverall Statistics:")
        print(f"- Total Tests: {total_tests}")
        print(f"- Total Passed: {total_passed}")
        print(f"- Critical Failures: {critical_failures}")
        
        if total_tests > 0:
            overall_success_rate = total_passed / total_tests * 100
            print(f"- Overall Success Rate: {overall_success_rate:.1f}%")
            
            # Quality gate criteria
            quality_gate_passed = (
                critical_failures == 0 and
                overall_success_rate >= 85.0
            )
        else:
            quality_gate_passed = critical_failures == 0
        
        if quality_gate_passed:
            print("\n🎉 QUALITY GATE: PASSED")
            print("All critical tests passed - ready for deployment!")
        else:
            print("\n🚨 QUALITY GATE: FAILED")
            print("Critical issues detected - deployment blocked!")
        
        return quality_gate_passed
    
    def generate_consolidated_report(self, results: List[TestResult]):
        """Generate consolidated test report"""
        
        report_file = self.results_dir / "consolidated-report.json"
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_test_levels": len(results),
                "total_tests": sum(r.total_tests for r in results),
                "total_passed": sum(r.passed for r in results),
                "total_failed": sum(r.failed for r in results),
                "total_skipped": sum(r.skipped for r in results),
                "total_duration": sum(r.duration for r in results)
            },
            "results": [
                {
                    "level": r.level,
                    "status": r.status,
                    "duration": r.duration,
                    "total_tests": r.total_tests,
                    "passed": r.passed,
                    "failed": r.failed,
                    "skipped": r.skipped,
                    "coverage": r.coverage,
                    "report_path": r.report_path,
                    "error_message": r.error_message
                }
                for r in results
            ]
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📊 Consolidated report saved: {report_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Advanced Test Runner for Avito Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--level",
        choices=["unit", "integration", "e2e", "external", "performance", "full"],
        default="unit",
        help="Test level to run (default: unit)"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel test execution"
    )
    
    parser.add_argument(
        "--no-parallel",
        action="store_true", 
        help="Disable parallel test execution"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Enable coverage reporting"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        help="Test timeout in seconds"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        default=True,
        help="Generate detailed reports (default: True)"
    )
    
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Disable report generation"
    )
    
    parser.add_argument(
        "--quality-gate",
        action="store_true",
        help="Run quality gate evaluation"
    )
    
    parser.add_argument(
        "--multiple",
        nargs="+",
        choices=["unit", "integration", "e2e", "external", "performance"],
        help="Run multiple test levels"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Verbose output (default: True)"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path(__file__).parent.parent
    
    # Initialize test runner
    runner = AdvancedTestRunner(project_root)
    
    # Determine parallel execution
    parallel = None
    if args.parallel:
        parallel = True
    elif args.no_parallel:
        parallel = False
    
    # Determine coverage
    coverage = None
    if args.coverage:
        coverage = True
    elif args.no_coverage:
        coverage = False
    
    # Determine reporting
    report = args.report and not args.no_report
    
    # Determine verbosity
    verbose = args.verbose and not args.quiet
    
    # Run tests
    results = []
    
    if args.multiple:
        # Run multiple test levels
        for level in args.multiple:
            result = runner.run_test_level(
                level=level,
                parallel=parallel,
                coverage=coverage,
                timeout=args.timeout,
                verbose=verbose,
                report=report
            )
            results.append(result)
    else:
        # Run single test level
        result = runner.run_test_level(
            level=args.level,
            parallel=parallel,
            coverage=coverage,
            timeout=args.timeout,
            verbose=verbose,
            report=report
        )
        results.append(result)
    
    # Generate consolidated report
    if len(results) > 1 or report:
        runner.generate_consolidated_report(results)
    
    # Run quality gate if requested or multiple levels
    if args.quality_gate or len(results) > 1:
        quality_gate_passed = runner.run_quality_gate(results)
        
        # Exit with appropriate code
        if not quality_gate_passed:
            sys.exit(1)
    
    # Check if any tests failed
    if any(r.status == "failed" for r in results):
        sys.exit(1)
    
    print("🎉 All tests completed successfully!")


if __name__ == "__main__":
    main()