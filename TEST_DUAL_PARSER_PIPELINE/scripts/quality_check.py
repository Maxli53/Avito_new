#!/usr/bin/env python3
"""
Quality Check Script for Avito Pipeline
=======================================

Comprehensive code quality validation including linting, formatting, 
type checking, security scanning, and documentation validation.

Usage:
    python scripts/quality_check.py --help
    python scripts/quality_check.py --all
    python scripts/quality_check.py --format --lint --security
    python scripts/quality_check.py --fix --report
"""

import argparse
import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class QualityCheckResult:
    """Quality check result"""
    check_name: str
    status: str
    duration: float
    output: str
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class QualityChecker:
    """Comprehensive code quality checker"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results_dir = project_root / "quality-reports"
        self.results: List[QualityCheckResult] = []
        
        # Ensure results directory exists
        self.results_dir.mkdir(exist_ok=True)
        
        # Define quality checks
        self.checks = {
            "format": {
                "name": "Code Formatting (Black)",
                "command": ["python", "-m", "black", "--check", "--diff", "."],
                "fix_command": ["python", "-m", "black", "."],
                "required": True,
                "timeout": 60
            },
            "import_sort": {
                "name": "Import Sorting (isort)",
                "command": ["python", "-m", "isort", "--check-only", "--diff", "."],
                "fix_command": ["python", "-m", "isort", "."],
                "required": True,
                "timeout": 30
            },
            "lint": {
                "name": "Linting (flake8)",
                "command": ["python", "-m", "flake8", ".", "--statistics"],
                "required": True,
                "timeout": 120
            },
            "type_check": {
                "name": "Type Checking (mypy)",
                "command": ["python", "-m", "mypy", ".", "--ignore-missing-imports"],
                "required": False,
                "timeout": 180
            },
            "security": {
                "name": "Security Analysis (bandit)",
                "command": ["python", "-m", "bandit", "-r", ".", "-f", "json", "-o", "bandit-report.json"],
                "required": True,
                "timeout": 90
            },
            "dependency_check": {
                "name": "Dependency Security (safety)",
                "command": ["python", "-m", "safety", "check", "--json", "--output", "safety-report.json"],
                "required": True,
                "timeout": 60
            },
            "complexity": {
                "name": "Code Complexity Analysis",
                "command": ["python", "-m", "flake8", ".", "--select=C901", "--statistics"],
                "required": False,
                "timeout": 60
            },
            "documentation": {
                "name": "Documentation Coverage",
                "command": ["python", "-c", "import docstring_coverage; docstring_coverage.main()"],
                "required": False,
                "timeout": 30
            }
        }
    
    def run_check(self, check_name: str, fix: bool = False) -> QualityCheckResult:
        """Run a single quality check"""
        
        if check_name not in self.checks:
            raise ValueError(f"Unknown check: {check_name}")
        
        check_config = self.checks[check_name]
        start_time = time.time()
        
        # Use fix command if available and requested
        if fix and "fix_command" in check_config:
            command = check_config["fix_command"]
        else:
            command = check_config["command"]
        
        print(f"🔍 Running {check_config['name']}...")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=check_config["timeout"]
            )
            
            duration = time.time() - start_time
            
            # Determine status
            if result.returncode == 0:
                status = "passed"
            else:
                status = "failed" if check_config["required"] else "warning"
            
            # Parse specific outputs
            details = self._parse_check_output(check_name, result.stdout, result.stderr)
            
            return QualityCheckResult(
                check_name=check_name,
                status=status,
                duration=duration,
                output=result.stdout,
                error=result.stderr if result.stderr else None,
                details=details
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return QualityCheckResult(
                check_name=check_name,
                status="timeout",
                duration=duration,
                output="",
                error=f"Check timed out after {check_config['timeout']} seconds"
            )
        except Exception as e:
            duration = time.time() - start_time
            return QualityCheckResult(
                check_name=check_name,
                status="error",
                duration=duration,
                output="",
                error=str(e)
            )
    
    def _parse_check_output(self, check_name: str, stdout: str, stderr: str) -> Optional[Dict[str, Any]]:
        """Parse specific check outputs for detailed information"""
        
        details = {}
        
        if check_name == "security":
            # Parse bandit JSON report
            report_file = self.project_root / "bandit-report.json"
            if report_file.exists():
                try:
                    with open(report_file, 'r') as f:
                        bandit_data = json.load(f)
                    
                    details["total_issues"] = len(bandit_data.get("results", []))
                    details["high_severity"] = len([
                        r for r in bandit_data.get("results", [])
                        if r.get("issue_severity") == "HIGH"
                    ])
                    details["medium_severity"] = len([
                        r for r in bandit_data.get("results", [])
                        if r.get("issue_severity") == "MEDIUM"
                    ])
                    details["low_severity"] = len([
                        r for r in bandit_data.get("results", [])
                        if r.get("issue_severity") == "LOW"
                    ])
                except Exception:
                    pass
        
        elif check_name == "dependency_check":
            # Parse safety JSON report
            report_file = self.project_root / "safety-report.json"
            if report_file.exists():
                try:
                    with open(report_file, 'r') as f:
                        safety_data = json.load(f)
                    
                    if isinstance(safety_data, list):
                        details["vulnerabilities"] = len(safety_data)
                        details["critical"] = len([
                            v for v in safety_data
                            if v.get("severity", "").lower() == "critical"
                        ])
                        details["high"] = len([
                            v for v in safety_data
                            if v.get("severity", "").lower() == "high"
                        ])
                except Exception:
                    pass
        
        elif check_name == "lint":
            # Parse flake8 output for statistics
            if "statistics" in stdout.lower():
                lines = stdout.strip().split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('.'):
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            try:
                                count = int(parts[0])
                                error_type = parts[1]
                                if "error_counts" not in details:
                                    details["error_counts"] = {}
                                details["error_counts"][error_type] = count
                            except ValueError:
                                continue
        
        elif check_name == "type_check":
            # Parse mypy output
            if stderr:
                lines = stderr.strip().split('\n')
                error_count = 0
                for line in lines:
                    if "error" in line.lower():
                        error_count += 1
                details["type_errors"] = error_count
        
        return details if details else None
    
    def run_all_checks(self, fix: bool = False, skip_optional: bool = False) -> List[QualityCheckResult]:
        """Run all quality checks"""
        
        results = []
        
        for check_name, check_config in self.checks.items():
            # Skip optional checks if requested
            if skip_optional and not check_config["required"]:
                continue
            
            result = self.run_check(check_name, fix=fix)
            results.append(result)
            
            # Print immediate feedback
            self._print_check_result(result)
        
        return results
    
    def _print_check_result(self, result: QualityCheckResult):
        """Print individual check result"""
        
        status_emoji = {
            "passed": "✅",
            "failed": "❌", 
            "warning": "⚠️",
            "timeout": "⏱️",
            "error": "🚨"
        }.get(result.status, "❓")
        
        check_name = self.checks[result.check_name]["name"]
        print(f"{status_emoji} {check_name}: {result.status.upper()} ({result.duration:.2f}s)")
        
        # Print details if available
        if result.details:
            if result.check_name == "security" and "total_issues" in result.details:
                print(f"   Security issues: {result.details['total_issues']} " +
                     f"(H:{result.details.get('high_severity', 0)}, " +
                     f"M:{result.details.get('medium_severity', 0)}, " +
                     f"L:{result.details.get('low_severity', 0)})")
            
            elif result.check_name == "dependency_check" and "vulnerabilities" in result.details:
                print(f"   Vulnerabilities: {result.details['vulnerabilities']}")
            
            elif result.check_name == "lint" and "error_counts" in result.details:
                error_summary = ", ".join([
                    f"{code}:{count}" for code, count in result.details["error_counts"].items()
                ])
                print(f"   Lint issues: {error_summary}")
            
            elif result.check_name == "type_check" and "type_errors" in result.details:
                print(f"   Type errors: {result.details['type_errors']}")
        
        # Print error if failed
        if result.error and result.status in ["failed", "error", "timeout"]:
            error_lines = result.error.strip().split('\n')
            for line in error_lines[:3]:  # Show first 3 lines
                print(f"   {line}")
            if len(error_lines) > 3:
                print(f"   ... ({len(error_lines) - 3} more lines)")
    
    def generate_quality_report(self, results: List[QualityCheckResult]) -> str:
        """Generate comprehensive quality report"""
        
        report_file = self.results_dir / f"quality-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        
        # Calculate summary statistics
        total_checks = len(results)
        passed = len([r for r in results if r.status == "passed"])
        failed = len([r for r in results if r.status == "failed"])
        warnings = len([r for r in results if r.status == "warning"])
        errors = len([r for r in results if r.status in ["error", "timeout"]])
        
        # Generate report content
        with open(report_file, 'w') as f:
            f.write("# Code Quality Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n")
            f.write(f"**Project:** Avito Pipeline Testing Framework\n\n")
            
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Checks:** {total_checks}\n")
            f.write(f"- **Passed:** {passed} ✅\n")
            f.write(f"- **Failed:** {failed} ❌\n")
            f.write(f"- **Warnings:** {warnings} ⚠️\n")
            f.write(f"- **Errors:** {errors} 🚨\n")
            
            if total_checks > 0:
                quality_score = (passed / total_checks) * 100
                f.write(f"- **Quality Score:** {quality_score:.1f}%\n\n")
                
                if quality_score >= 90:
                    f.write("🟢 **Overall Status:** EXCELLENT\n")
                elif quality_score >= 75:
                    f.write("🟡 **Overall Status:** GOOD\n")
                elif quality_score >= 50:
                    f.write("🟠 **Overall Status:** NEEDS IMPROVEMENT\n")
                else:
                    f.write("🔴 **Overall Status:** POOR\n")
            
            f.write("\n## Detailed Results\n\n")
            
            # Detailed results table
            f.write("| Check | Status | Duration | Details |\n")
            f.write("|-------|--------|----------|----------|\n")
            
            for result in results:
                check_name = self.checks[result.check_name]["name"]
                status_emoji = {
                    "passed": "✅",
                    "failed": "❌",
                    "warning": "⚠️", 
                    "timeout": "⏱️",
                    "error": "🚨"
                }.get(result.status, "❓")
                
                details_str = ""
                if result.details:
                    if "total_issues" in result.details:
                        details_str = f"{result.details['total_issues']} security issues"
                    elif "vulnerabilities" in result.details:
                        details_str = f"{result.details['vulnerabilities']} vulnerabilities"
                    elif "error_counts" in result.details:
                        total_errors = sum(result.details["error_counts"].values())
                        details_str = f"{total_errors} lint issues"
                    elif "type_errors" in result.details:
                        details_str = f"{result.details['type_errors']} type errors"
                
                f.write(f"| {check_name} | {status_emoji} {result.status.upper()} | {result.duration:.2f}s | {details_str} |\n")
            
            f.write("\n## Recommendations\n\n")
            
            # Generate recommendations based on results
            recommendations = []
            
            for result in results:
                if result.status == "failed":
                    check_name = self.checks[result.check_name]["name"]
                    
                    if result.check_name == "format":
                        recommendations.append("🔧 Run `python -m black .` to fix formatting issues")
                    elif result.check_name == "import_sort":
                        recommendations.append("🔧 Run `python -m isort .` to fix import sorting")
                    elif result.check_name == "lint":
                        recommendations.append("🔍 Review and fix linting issues reported by flake8")
                    elif result.check_name == "security":
                        recommendations.append("🛡️ Address security vulnerabilities identified by bandit")
                    elif result.check_name == "dependency_check":
                        recommendations.append("📦 Update vulnerable dependencies identified by safety")
            
            if not recommendations:
                f.write("🎉 No critical issues found! Code quality looks excellent.\n")
            else:
                for i, rec in enumerate(recommendations, 1):
                    f.write(f"{i}. {rec}\n")
            
            f.write("\n---\n")
            f.write("*This report was generated automatically by the Avito Pipeline Quality Checker*\n")
        
        return str(report_file)
    
    def run_quality_gate(self, results: List[QualityCheckResult]) -> bool:
        """Evaluate quality gate based on results"""
        
        print("\n🚦 QUALITY GATE EVALUATION")
        print("=" * 50)
        
        # Critical checks that must pass
        critical_checks = ["format", "import_sort", "lint", "security", "dependency_check"]
        critical_failures = []
        
        for result in results:
            if result.check_name in critical_checks and result.status == "failed":
                critical_failures.append(result.check_name)
        
        # Calculate quality score
        total_checks = len([r for r in results if self.checks[r.check_name]["required"]])
        passed_checks = len([
            r for r in results
            if self.checks[r.check_name]["required"] and r.status == "passed"
        ])
        
        quality_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        print(f"Quality Score: {quality_score:.1f}%")
        print(f"Critical Failures: {len(critical_failures)}")
        
        if critical_failures:
            print(f"Failed Critical Checks: {', '.join(critical_failures)}")
        
        # Determine gate status
        gate_passed = len(critical_failures) == 0 and quality_score >= 80.0
        
        if gate_passed:
            print("\n🎉 QUALITY GATE: PASSED")
            print("Code quality meets standards - ready for integration!")
        else:
            print("\n🚨 QUALITY GATE: FAILED") 
            print("Code quality issues detected - fix before proceeding!")
        
        return gate_passed


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Quality Check Script for Avito Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all quality checks"
    )
    
    parser.add_argument(
        "--format",
        action="store_true",
        help="Run code formatting check (Black)"
    )
    
    parser.add_argument(
        "--import-sort",
        action="store_true",
        help="Run import sorting check (isort)"
    )
    
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run linting check (flake8)"
    )
    
    parser.add_argument(
        "--type-check",
        action="store_true",
        help="Run type checking (mypy)"
    )
    
    parser.add_argument(
        "--security",
        action="store_true",
        help="Run security analysis (bandit)"
    )
    
    parser.add_argument(
        "--dependency-check",
        action="store_true",
        help="Run dependency security check (safety)"
    )
    
    parser.add_argument(
        "--complexity",
        action="store_true",
        help="Run code complexity analysis"
    )
    
    parser.add_argument(
        "--documentation",
        action="store_true",
        help="Run documentation coverage check"
    )
    
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix issues where possible"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        default=True,
        help="Generate detailed quality report"
    )
    
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip report generation"
    )
    
    parser.add_argument(
        "--quality-gate",
        action="store_true",
        help="Run quality gate evaluation"
    )
    
    parser.add_argument(
        "--skip-optional",
        action="store_true",
        help="Skip optional quality checks"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path(__file__).parent.parent
    
    # Initialize quality checker
    checker = QualityChecker(project_root)
    
    # Determine which checks to run
    checks_to_run = []
    
    if args.all:
        checks_to_run = list(checker.checks.keys())
    else:
        if args.format:
            checks_to_run.append("format")
        if getattr(args, 'import_sort'):
            checks_to_run.append("import_sort")
        if args.lint:
            checks_to_run.append("lint")
        if getattr(args, 'type_check'):
            checks_to_run.append("type_check")
        if args.security:
            checks_to_run.append("security")
        if getattr(args, 'dependency_check'):
            checks_to_run.append("dependency_check")
        if args.complexity:
            checks_to_run.append("complexity")
        if args.documentation:
            checks_to_run.append("documentation")
    
    # Default to basic checks if none specified
    if not checks_to_run:
        checks_to_run = ["format", "import_sort", "lint", "security"]
    
    # Run checks
    print("🔍 Starting Quality Checks...")
    print("=" * 50)
    
    results = []
    
    if args.all:
        results = checker.run_all_checks(fix=args.fix, skip_optional=args.skip_optional)
    else:
        for check_name in checks_to_run:
            result = checker.run_check(check_name, fix=args.fix)
            results.append(result)
            checker._print_check_result(result)
    
    # Generate report
    report_file = None
    if args.report and not args.no_report:
        report_file = checker.generate_quality_report(results)
        print(f"\n📊 Quality report generated: {report_file}")
    
    # Run quality gate
    if args.quality_gate or args.all:
        quality_gate_passed = checker.run_quality_gate(results)
        
        if not quality_gate_passed:
            sys.exit(1)
    
    # Check for critical failures
    critical_failures = [
        r for r in results
        if checker.checks[r.check_name]["required"] and r.status == "failed"
    ]
    
    if critical_failures:
        print(f"\n❌ {len(critical_failures)} critical quality checks failed!")
        sys.exit(1)
    
    print("\n🎉 All quality checks completed successfully!")


if __name__ == "__main__":
    main()