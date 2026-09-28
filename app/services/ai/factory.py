from __future__ import annotations

from datetime import datetime, timezone
from threading import Thread

from flask import current_app

from app.extensions import db
from app.models import AIRecommendation, AgentRun, FactoryRun
from app.services.ai.operations_agent import ParkOperationsAnalyst
from app.services.ai.provider import OpenAIProvider
from app.services.ai.recommendation_agent import ParkRecommendationAgent
from app.services.ai.schemas import OperationsAnalysis
from app.services.analytics.snapshot import build_operational_snapshot, snapshot_summary


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FactoryBusyError(RuntimeError):
    pass


class AIFactory:
    def __init__(self, provider_factory=OpenAIProvider) -> None:
        self.provider_factory = provider_factory

    def start(self, triggered_by_id: int) -> FactoryRun:
        if FactoryRun.query.filter_by(status="Running").first():
            raise FactoryBusyError("A factory run is already in progress.")

        snapshot = build_operational_snapshot()
        run = FactoryRun(
            triggered_by_id=triggered_by_id,
            status="Running",
            operational_snapshot=snapshot,
        )
        db.session.add(run)
        db.session.flush()
        db.session.add_all(
            [
                AgentRun(
                    factory_run_id=run.id,
                    agent_name=ParkOperationsAnalyst.name,
                    status="Waiting",
                    iteration=1,
                ),
                AgentRun(
                    factory_run_id=run.id,
                    agent_name=ParkRecommendationAgent.name,
                    status="Waiting",
                    iteration=1,
                ),
            ]
        )
        db.session.commit()
        self._dispatch(run.id, retry_only=False)
        return run

    def retry_agent_two(self, run_id: str) -> FactoryRun:
        run = db.session.get(FactoryRun, run_id)
        if not run or run.status != "Partial Failure" or not run.analysis_output:
            raise ValueError("This run is not eligible for an Agent 2 retry.")
        existing = AgentRun.query.filter_by(
            factory_run_id=run.id, agent_name=ParkRecommendationAgent.name
        ).count()
        db.session.add(
            AgentRun(
                factory_run_id=run.id,
                agent_name=ParkRecommendationAgent.name,
                status="Waiting",
                iteration=existing + 1,
            )
        )
        run.status = "Running"
        run.completed_at = None
        db.session.commit()
        self._dispatch(run.id, retry_only=True)
        return run

    def _dispatch(self, run_id: str, *, retry_only: bool) -> None:
        app = current_app._get_current_object()
        if current_app.config.get("FACTORY_SYNC"):
            self._execute(app, run_id, retry_only=retry_only)
            return
        thread = Thread(
            target=self._execute,
            args=(app, run_id),
            kwargs={"retry_only": retry_only},
            daemon=True,
            name=f"parksmart-factory-{run_id[:8]}",
        )
        thread.start()

    def _execute(self, app, run_id: str, *, retry_only: bool) -> None:
        with app.app_context():
            run = db.session.get(FactoryRun, run_id)
            try:
                provider = app.config.get("AI_PROVIDER") or self.provider_factory()
                analyst = ParkOperationsAnalyst(provider)
                recommender = ParkRecommendationAgent(provider)

                if retry_only:
                    analysis = OperationsAnalysis.model_validate(run.analysis_output)
                    self._run_recommender(run, recommender, analysis, final_pass=True)
                    return

                analysis = self._run_analyst(run, analyst, iteration=1)
                if analysis is None:
                    return
                batch = self._run_recommender(run, recommender, analysis, iteration=1)
                if batch is None:
                    return

                if batch.needs_additional_analysis:
                    run.iteration_count = 2
                    db.session.commit()
                    analysis = self._run_analyst(
                        run,
                        analyst,
                        iteration=2,
                        focus_request=batch.additional_analysis_request,
                    )
                    if analysis is None:
                        return
                    self._run_recommender(
                        run,
                        recommender,
                        analysis,
                        iteration=2,
                        final_pass=True,
                    )
            except Exception as exc:
                db.session.rollback()
                run = db.session.get(FactoryRun, run_id)
                if run and run.status == "Running":
                    active_agent = (
                        AgentRun.query.filter(
                            AgentRun.factory_run_id == run.id,
                            AgentRun.status.in_(["Waiting", "Running", "Analyzing"]),
                        )
                        .order_by(AgentRun.iteration, AgentRun.id)
                        .first()
                    )
                    if active_agent:
                        active_agent.status = "Failed"
                        active_agent.ended_at = _now()
                        active_agent.input_summary = active_agent.input_summary or snapshot_summary(
                            run.operational_snapshot or {}
                        )
                        active_agent.error = str(exc)[:500]
                    run.status = "Failed"
                    run.completed_at = _now()
                    db.session.commit()
                app.logger.exception("AI Factory run %s failed: %s", run_id, type(exc).__name__)

    def _agent_run(self, run: FactoryRun, agent_name: str, iteration: int) -> AgentRun:
        agent_run = AgentRun.query.filter_by(
            factory_run_id=run.id, agent_name=agent_name, iteration=iteration
        ).first()
        if not agent_run:
            agent_run = AgentRun(
                factory_run_id=run.id,
                agent_name=agent_name,
                iteration=iteration,
                status="Waiting",
            )
            db.session.add(agent_run)
        return agent_run

    def _run_analyst(
        self,
        run: FactoryRun,
        analyst: ParkOperationsAnalyst,
        *,
        iteration: int,
        focus_request: str = "",
    ):
        agent_run = self._agent_run(run, analyst.name, iteration)
        agent_run.status = "Analyzing"
        agent_run.started_at = _now()
        agent_run.input_summary = snapshot_summary(run.operational_snapshot)
        db.session.commit()
        try:
            analysis = analyst.analyze(run.operational_snapshot, focus_request)
            run.analysis_output = analysis.model_dump(mode="json")
            run.priority_issue_count = len(analysis.priority_issues)
            agent_run.status = "Completed"
            agent_run.ended_at = _now()
            agent_run.output_summary = {
                "traffic_status": analysis.traffic_status.value,
                "priority_issues": len(analysis.priority_issues),
                "data_gaps": len(analysis.data_gaps),
                "summary": analysis.summary[:300],
            }
            db.session.commit()
            return analysis
        except Exception as exc:
            db.session.rollback()
            agent_run = self._agent_run(run, analyst.name, iteration)
            agent_run.status = "Failed"
            agent_run.ended_at = _now()
            agent_run.error = str(exc)[:500]
            run.status = "Failed"
            run.completed_at = _now()
            db.session.commit()
            return None

    def _run_recommender(
        self,
        run: FactoryRun,
        recommender: ParkRecommendationAgent,
        analysis: OperationsAnalysis,
        *,
        iteration: int | None = None,
        final_pass: bool = False,
    ):
        if iteration is None:
            iteration = (
                AgentRun.query.filter_by(
                    factory_run_id=run.id, agent_name=recommender.name
                ).count()
            )
        agent_run = self._agent_run(run, recommender.name, iteration)
        agent_run.status = "Running"
        agent_run.started_at = _now()
        agent_run.input_summary = {
            **snapshot_summary(run.operational_snapshot),
            "analyst_priority_issues": len(analysis.priority_issues),
        }
        db.session.commit()
        try:
            batch = recommender.recommend(
                run.operational_snapshot, analysis, final_pass=final_pass
            )
            agent_run.status = "Completed"
            agent_run.ended_at = _now()
            agent_run.output_summary = {
                "recommendations": len(batch.recommendations),
                "needs_additional_analysis": batch.needs_additional_analysis,
                "summary": batch.summary[:300],
            }
            if batch.needs_additional_analysis and not final_pass:
                db.session.commit()
                return batch

            for item in batch.recommendations:
                db.session.add(
                    AIRecommendation(
                        factory_run_id=run.id,
                        title=item.title,
                        category=item.category,
                        priority=item.priority.value,
                        priority_reason=item.priority_reason,
                        reason=item.reason,
                        recommended_action=item.recommended_action,
                        related_zone=item.related_zone,
                        related_facility=item.related_facility,
                    )
                )
            run.recommendation_count = len(batch.recommendations)
            run.status = "Completed"
            run.completed_at = _now()
            db.session.commit()
            return batch
        except Exception as exc:
            db.session.rollback()
            agent_run = self._agent_run(run, recommender.name, iteration)
            agent_run.status = "Failed"
            agent_run.ended_at = _now()
            agent_run.error = str(exc)[:500]
            run.status = "Partial Failure" if run.analysis_output else "Failed"
            run.completed_at = _now()
            db.session.commit()
            return None
