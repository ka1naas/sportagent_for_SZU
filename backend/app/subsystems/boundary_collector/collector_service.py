from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.chat import StepName
from backend.app.models.schemas import UserBoundaryConditions
from backend.app.utils.boundary import build_boundary_conditions
from db.database import SessionLocal
from db.models import BoundarySession


class BoundaryCollectorService:
    """边界条件采集子系统，统一使用 SQLAlchemy 持久化。"""

    ORDERED_STEPS = (
        StepName.step1_profile,
        StepName.step2_goal,
        StepName.step3_space_time,
        StepName.step4_diet,
        StepName.step5_habits,
        StepName.completed,
    )

    STEP_TO_PAYLOAD_KEY = {
        StepName.step1_profile: "profile",
        StepName.step2_goal: "goal",
        StepName.step3_space_time: "spatiotemporal",
        StepName.step4_diet: "dietary",
        StepName.step5_habits: "habits",
    }

    def __init__(self, db: Session | None = None) -> None:
        self._db = db

    def _get_db(self) -> Session:
        return self._db or SessionLocal()

    def update_step_data(self, session_id: str, step: StepName | str, data: dict[str, Any]) -> dict[str, Any]:
        normalized_step = StepName(step)
        owns_session = self._db is None
        db = self._get_db()
        try:
            session = self._get_or_create_session(db, session_id)
            current_step = StepName(session.current_step)
            if normalized_step != current_step:
                raise ValueError(f"当前期望步骤为 {current_step.value}，收到 {normalized_step.value}。")

            payload = dict(session.payload or {})
            payload_key = self.STEP_TO_PAYLOAD_KEY.get(normalized_step)
            if payload_key is None:
                raise ValueError(f"步骤 {normalized_step.value} 不允许写入边界数据。")

            transformed_data = self._transform_step_data(normalized_step, data)
            payload[payload_key] = transformed_data
            next_step = self._next_step(normalized_step)
            schedule_locations = self._extract_schedule_locations(normalized_step, transformed_data)
            if schedule_locations:
                payload.setdefault("schedule_locations", [])
                payload["schedule_locations"] = schedule_locations

            self._upsert_session(db=db, session_id=session_id, current_step=next_step, payload=payload)
            if owns_session:
                db.commit()

            return {
                "session_id": session_id,
                "current_step": normalized_step.value,
                "next_step": next_step.value,
                "payload": payload,
            }
        finally:
            if owns_session:
                db.close()

    def get_complete_boundary(self, session_id: str) -> UserBoundaryConditions:
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("未找到对应的会话数据。")
        current_step = StepName(session["current_step"])
        if current_step != StepName.completed:
            raise ValueError("当前会话尚未完成 5 步问卷，无法生成完整边界条件。")
        return build_boundary_conditions(session_id, session["payload"])

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        owns_session = self._db is None
        db = self._get_db()
        try:
            row = db.query(BoundarySession).filter(BoundarySession.session_id == session_id).one_or_none()
            if row is None:
                return None
            return {"session_id": row.session_id, "current_step": row.current_step, "payload": row.payload or {}}
        finally:
            if owns_session:
                db.close()

    def reset_session(self, session_id: str) -> None:
        owns_session = self._db is None
        db = self._get_db()
        try:
            session = db.query(BoundarySession).filter(BoundarySession.session_id == session_id).one_or_none()
            if session is None:
                return

            session.current_step = StepName.step1_profile.value
            session.payload = {}

            if owns_session:
                db.commit()
        finally:
            if owns_session:
                db.close()

    def _get_or_create_session(self, db: Session, session_id: str) -> BoundarySession:
        session = db.query(BoundarySession).filter(BoundarySession.session_id == session_id).one_or_none()
        if session is not None:
            return session
        session = BoundarySession(session_id=session_id, current_step=StepName.step1_profile.value, payload={})
        db.add(session)
        db.flush()
        return session

    def _upsert_session(self, *, db: Session, session_id: str, current_step: StepName, payload: dict[str, Any]) -> None:
        session = db.query(BoundarySession).filter(BoundarySession.session_id == session_id).one_or_none()
        if session is None:
            db.add(BoundarySession(session_id=session_id, current_step=current_step.value, payload=payload))
            return
        session.current_step = current_step.value
        session.payload = payload

    def _next_step(self, step: StepName) -> StepName:
        return self.ORDERED_STEPS[self.ORDERED_STEPS.index(step) + 1]

    def _transform_step_data(self, step: StepName, data: dict[str, Any]) -> dict[str, Any]:
        if step == StepName.step2_goal:
            goal_value = data.get("goal")
            accept_value = data.get("accept_muscle_loss")
            return {"primary": goal_value, "accept_muscle_loss": accept_value == "接受" if goal_value == "减脂" else None}
        if step == StepName.step3_space_time:
            return {
                "frequency": data.get("frequency"),
                "duration": data.get("duration"),
                "preference": data.get("preference"),
                "dorm_location": data.get("dorm_location"),
                "schedule_image_url": data.get("schedule_image_url"),
            }
        if step == StepName.step4_diet:
            return {"preferred_canteens": data.get("preferred_canteens", []), "weekly_budget": data.get("weekly_budget")}
        if step == StepName.step5_habits:
            favorite_sport = data.get("favorite_sport_other") if data.get("favorite_sport") == "其他" else data.get("favorite_sport")
            return {"favorite_sport": favorite_sport, "integrate_into_training": data.get("integrate_into_training")}
        return data

    def _extract_schedule_locations(self, step: StepName, data: dict[str, Any]) -> list[dict[str, str]]:
        if step != StepName.step3_space_time:
            return []
        dorm_location = data.get("dorm_location")
        if not dorm_location:
            return []
        return [{"weekday": "unknown", "time_start": "unknown", "time_end": "unknown", "location": dorm_location}]
