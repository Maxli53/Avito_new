"""Stage 2: Specification Inheritance - TO BE IMPLEMENTED"""
from src.models.domain import PipelineConfig, ProcessingStage
from src.pipeline.stages.base_stage import BasePipelineStage


class SpecificationInheritanceStage(BasePipelineStage):
    def __init__(self, config: PipelineConfig):
        super().__init__(ProcessingStage.SPECIFICATION_INHERITANCE, config)

    async def _execute_stage(self, context):
        return {"success": False, "error": "Not implemented yet"}
