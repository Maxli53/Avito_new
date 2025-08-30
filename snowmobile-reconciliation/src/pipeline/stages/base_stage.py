"""
Base pipeline stage implementation following Universal Development Standards.

Provides common functionality for all pipeline stages with proper error handling,
logging, and metrics collection.
"""
import time
from abc import ABC, abstractmethod
from typing import Any

import structlog

from src.models.domain import (
    PipelineConfig,
    PipelineStageResult,
    ProcessingStage,
)

logger = structlog.get_logger(__name__)


class BasePipelineStage(ABC):
    """
    Abstract base class for all pipeline stages.

    Provides:
    - Consistent error handling and logging
    - Performance metrics collection
    - Configuration management
    - Standard processing interface
    """

    def __init__(self, stage_name: ProcessingStage, config: PipelineConfig) -> None:
        self.stage_name = stage_name
        self.config = config
        self.logger = logger.bind(stage=stage_name.value)

        # Performance tracking
        self._metrics = {
            "total_processed": 0,
            "total_successful": 0,
            "total_failed": 0,
            "total_processing_time_ms": 0,
            "average_processing_time_ms": 0.0,
        }

    async def process(self, context: "PipelineContext") -> PipelineStageResult:
        """
        Main processing entry point with error handling and metrics.

        Args:
            context: Pipeline context with current processing state

        Returns:
            Stage result with success status and data
        """
        start_time = time.time()

        stage_logger = self.logger.bind(
            model_code=context.price_entry.model_code, stage_execution_id=id(context)
        )

        stage_logger.info("Starting stage processing")

        try:
            # Execute stage-specific logic
            stage_data = await self._execute_stage(context)

            processing_time_ms = int((time.time() - start_time) * 1000)

            # Determine success based on stage data
            success = self._is_stage_successful(stage_data)
            confidence = self._calculate_stage_confidence(stage_data, context)
            warnings = self._extract_warnings(stage_data)
            errors = self._extract_errors(stage_data) if not success else []

            # Update metrics
            self._update_metrics(processing_time_ms, success)

            result = PipelineStageResult(
                stage=self.stage_name,
                success=success,
                confidence_score=confidence,
                processing_time_ms=processing_time_ms,
                stage_data=stage_data,
                warnings=warnings,
                errors=errors,
                claude_tokens_used=stage_data.get("claude_tokens_used", 0),
                claude_api_cost=stage_data.get("claude_cost", 0.0),
            )

            if success:
                stage_logger.info(
                    "Stage processing completed successfully",
                    confidence=confidence,
                    processing_time_ms=processing_time_ms,
                    warnings_count=len(warnings),
                )
            else:
                stage_logger.warning(
                    "Stage processing failed",
                    errors=errors,
                    processing_time_ms=processing_time_ms,
                )

            return result

        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)

            stage_logger.error(
                "Unexpected error in stage processing",
                error=str(e),
                error_type=type(e).__name__,
                processing_time_ms=processing_time_ms,
            )

            # Update metrics for failure
            self._update_metrics(processing_time_ms, False)

            return PipelineStageResult(
                stage=self.stage_name,
                success=False,
                confidence_score=0.0,
                processing_time_ms=processing_time_ms,
                stage_data={},
                warnings=[],
                errors=[f"Stage exception: {str(e)}"],
                claude_tokens_used=0,
                claude_api_cost=0.0,
            )

    @abstractmethod
    async def _execute_stage(self, context: "PipelineContext") -> dict[str, Any]:
        """
        Execute stage-specific processing logic.
        Must be implemented by concrete stages.

        Args:
            context: Pipeline context with current state

        Returns:
            Dictionary with stage processing results

        Raises:
            Any stage-specific exceptions
        """
        pass

    def _is_stage_successful(self, stage_data: dict[str, Any]) -> bool:
        """
        Determine if stage completed successfully based on stage data.
        Override in subclasses for custom success criteria.

        Args:
            stage_data: Stage processing results

        Returns:
            True if stage succeeded, False otherwise
        """
        # Default implementation - check for explicit success flag
        if "success" in stage_data:
            return stage_data["success"]

        # Check for error indicators
        if stage_data.get("error") or stage_data.get("errors"):
            return False

        # Check for required outputs (override in subclasses)
        required_outputs = self._get_required_outputs()
        return all(output in stage_data for output in required_outputs)

    def _calculate_stage_confidence(
        self, stage_data: dict[str, Any], context: "PipelineContext"
    ) -> float:
        """
        Calculate confidence score for stage results.
        Override in subclasses for stage-specific confidence calculation.

        Args:
            stage_data: Stage processing results
            context: Pipeline context

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Default implementation - use explicit confidence if provided
        if "confidence" in stage_data:
            return min(max(stage_data["confidence"], 0.0), 1.0)

        # Simple heuristic based on success and data completeness
        if not self._is_stage_successful(stage_data):
            return 0.0

        required_outputs = self._get_required_outputs()
        if not required_outputs:
            return 0.8  # Default confidence for stages without specific requirements

        # Calculate based on output completeness
        completed_outputs = sum(
            1 for output in required_outputs if stage_data.get(output)
        )
        completeness_ratio = completed_outputs / len(required_outputs)

        # Scale to confidence range 0.5-0.95 for successful stages
        return 0.5 + (completeness_ratio * 0.45)

    def _extract_warnings(self, stage_data: dict[str, Any]) -> list[str]:
        """Extract warning messages from stage data"""
        warnings = []

        if "warning" in stage_data:
            warnings.append(stage_data["warning"])

        if "warnings" in stage_data and isinstance(stage_data["warnings"], list):
            warnings.extend(stage_data["warnings"])

        return warnings

    def _extract_errors(self, stage_data: dict[str, Any]) -> list[str]:
        """Extract error messages from stage data"""
        errors = []

        if "error" in stage_data:
            errors.append(str(stage_data["error"]))

        if "errors" in stage_data and isinstance(stage_data["errors"], list):
            errors.extend([str(error) for error in stage_data["errors"]])

        return errors

    def _get_required_outputs(self) -> list[str]:
        """
        Get list of required outputs for this stage.
        Override in subclasses to define stage-specific requirements.

        Returns:
            List of required output field names
        """
        return []  # Default - no specific requirements

    def _update_metrics(self, processing_time_ms: int, success: bool) -> None:
        """Update stage performance metrics"""
        self._metrics["total_processed"] += 1
        self._metrics["total_processing_time_ms"] += processing_time_ms

        if success:
            self._metrics["total_successful"] += 1
        else:
            self._metrics["total_failed"] += 1

        # Update average processing time
        self._metrics["average_processing_time_ms"] = (
            self._metrics["total_processing_time_ms"] / self._metrics["total_processed"]
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get current stage performance metrics"""
        success_rate = 0.0
        if self._metrics["total_processed"] > 0:
            success_rate = (
                self._metrics["total_successful"] / self._metrics["total_processed"]
            )

        return {
            **self._metrics,
            "success_rate": success_rate,
            "failure_rate": 1.0 - success_rate,
        }

    def reset_metrics(self) -> None:
        """Reset all stage metrics to zero"""
        for key in self._metrics:
            if isinstance(self._metrics[key], int):
                self._metrics[key] = 0
            else:
                self._metrics[key] = 0.0


class StageValidationMixin:
    """Mixin providing common validation utilities for stages"""

    def validate_input_data(
        self, data: dict[str, Any], required_fields: list[str]
    ) -> list[str]:
        """
        Validate input data has required fields.

        Args:
            data: Input data dictionary
            required_fields: List of required field names

        Returns:
            List of validation error messages
        """
        errors = []

        for field in required_fields:
            if field not in data:
                errors.append(f"Required field '{field}' is missing")
            elif data[field] is None:
                errors.append(f"Required field '{field}' is None")
            elif isinstance(data[field], str) and not data[field].strip():
                errors.append(f"Required field '{field}' is empty")

        return errors

    def validate_confidence_score(self, confidence: Any) -> float:
        """
        Validate and normalize confidence score.

        Args:
            confidence: Raw confidence value

        Returns:
            Normalized confidence between 0.0 and 1.0
        """
        try:
            conf_float = float(confidence)
            return min(max(conf_float, 0.0), 1.0)
        except (TypeError, ValueError):
            return 0.0

    def validate_processing_result(
        self, result: dict[str, Any], expected_keys: list[str]
    ) -> bool:
        """
        Validate processing result has expected structure.

        Args:
            result: Processing result dictionary
            expected_keys: List of keys that should be present

        Returns:
            True if result is valid, False otherwise
        """
        if not isinstance(result, dict):
            return False

        return all(key in result for key in expected_keys)


class PerformanceMonitoringMixin:
    """Mixin providing performance monitoring capabilities"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._operation_times = {}
        self._operation_counts = {}

    def track_operation(self, operation_name: str):
        """Context manager for tracking operation performance"""
        return OperationTracker(self, operation_name)

    def _record_operation(self, operation_name: str, duration_ms: int) -> None:
        """Record operation duration for metrics"""
        if operation_name not in self._operation_times:
            self._operation_times[operation_name] = []
            self._operation_counts[operation_name] = 0

        self._operation_times[operation_name].append(duration_ms)
        self._operation_counts[operation_name] += 1

        # Keep only last 100 measurements to avoid memory growth
        if len(self._operation_times[operation_name]) > 100:
            self._operation_times[operation_name] = self._operation_times[
                operation_name
            ][-100:]

    def get_operation_metrics(self) -> dict[str, dict[str, float]]:
        """Get performance metrics for all tracked operations"""
        metrics = {}

        for operation, times in self._operation_times.items():
            if times:
                metrics[operation] = {
                    "count": self._operation_counts[operation],
                    "avg_duration_ms": sum(times) / len(times),
                    "min_duration_ms": min(times),
                    "max_duration_ms": max(times),
                    "total_duration_ms": sum(times),
                }

        return metrics


class OperationTracker:
    """Context manager for tracking individual operation performance"""

    def __init__(self, stage: PerformanceMonitoringMixin, operation_name: str):
        self.stage = stage
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = int((time.time() - self.start_time) * 1000)
            self.stage._record_operation(self.operation_name, duration_ms)
