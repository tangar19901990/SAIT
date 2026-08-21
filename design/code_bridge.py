from .design_engine import DesignEngine, DesignSpec


class DesignCodeBridge:
    """Turns a structured design specification into coding actions.

    The bridge deliberately generates an implementation plan rather than
    pretending that design tokens alone are a finished visual design.
    """

    def __init__(self, design_engine: DesignEngine):
        self.design_engine = design_engine

    def build_plan(self, spec: DesignSpec) -> list[dict]:
        plan = []
        for page in spec.pages:
            plan.append({"action": "create_page", "name": page})
        for component in spec.components:
            plan.append({"action": "create_component", "name": component})
        if spec.tokens:
            plan.append({"action": "create_design_tokens", "tokens": spec.tokens})
        plan.append({
            "action": "responsive_pass",
            "viewports": spec.viewport_targets,
        })
        plan.append({"action": "run_ui_tests"})
        return plan

    def export_plan(self, spec: DesignSpec) -> dict:
        return {
            "design": self.design_engine.export(spec),
            "implementation": self.build_plan(spec),
        }
