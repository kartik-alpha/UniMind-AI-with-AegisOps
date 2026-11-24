from typing import Dict, List, Any, Optional
from digital_twin.models import (
    AcademicEvent,
    TrafficIntensity,
    SimulationConfig,
    HourlyActivityPoint,
)

# Baseline 24-hour diurnal activity coefficients (0.0 to 1.0)
# Represents general student wakefulness, lecture hours, and study activity
BASE_DIURNAL_CURVE: List[float] = [
    0.03,  # 00:00 - Night sleep
    0.02,  # 01:00
    0.01,  # 02:00
    0.01,  # 03:00
    0.02,  # 04:00
    0.05,  # 05:00 - Early wake
    0.12,  # 06:00
    0.28,  # 07:00 - Morning transit
    0.65,  # 08:00 - First lecture / attendance check-in
    0.78,  # 09:00 - Peak morning classes
    0.82,  # 10:00 - Classes & lab sessions
    0.75,  # 11:00
    0.62,  # 12:00 - Lunch break
    0.72,  # 13:00 - Afternoon lectures
    0.76,  # 14:00 - Labs & tutorials
    0.70,  # 15:00
    0.58,  # 16:00 - Classes end
    0.45,  # 17:00 - Sports & clubs
    0.52,  # 18:00 - Dinner & library
    0.74,  # 19:00 - Evening study
    0.88,  # 20:00 - Heavy LMS access
    0.92,  # 21:00 - Assignment work & study
    0.85,  # 22:00
    0.45,  # 23:00 - Pre-midnight submissions
]

INTENSITY_MULTIPLIERS: Dict[TrafficIntensity, float] = {
    TrafficIntensity.LOW: 0.70,
    TrafficIntensity.NORMAL: 1.00,
    TrafficIntensity.PEAK: 1.40,
    TrafficIntensity.EXTREME: 2.10,
}


class CampusActivitySimulator:
    """
    Deterministic campus student activity and traffic distribution simulator.
    Models diurnal rhythms, human attendance workflows, and academic calendar shocks.
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()

    def get_service_traffic_distribution(self, hour: int, event: AcademicEvent) -> Dict[str, float]:
        """
        Determines the fractional distribution of student traffic among the 4 services
        for a given hour and academic event. Fractions sum to 1.0.
        """
        # Baseline balanced distribution
        weights = {
            "student_portal": 0.30,
            "lms": 0.45,
            "exam_service": 0.10,
            "library_service": 0.15,
        }

        # Event-specific overrides and shape modifications
        if event == AcademicEvent.EXAM_PERIOD:
            # Concentrated in examination windows (09:00-12:00 and 14:00-17:00)
            if (9 <= hour <= 12) or (14 <= hour <= 17):
                weights = {
                    "student_portal": 0.15,
                    "lms": 0.15,
                    "exam_service": 0.65,  # Major concentration on exam engine
                    "library_service": 0.05,
                }
            else:
                weights = {
                    "student_portal": 0.25,
                    "lms": 0.45,
                    "exam_service": 0.20,
                    "library_service": 0.10,
                }

        elif event == AcademicEvent.ASSIGNMENT_DEADLINE:
            # Heavy evening concentration on LMS (submissions before midnight)
            if 20 <= hour <= 23:
                weights = {
                    "student_portal": 0.15,
                    "lms": 0.75,  # Intense submission rush
                    "exam_service": 0.05,
                    "library_service": 0.05,
                }
            else:
                weights = {
                    "student_portal": 0.25,
                    "lms": 0.55,
                    "exam_service": 0.05,
                    "library_service": 0.15,
                }

        elif event == AcademicEvent.ADMISSION_PERIOD:
            # Daytime traffic on public/student portal
            if 9 <= hour <= 17:
                weights = {
                    "student_portal": 0.60,
                    "lms": 0.20,
                    "exam_service": 0.05,
                    "library_service": 0.15,
                }
            else:
                weights = {
                    "student_portal": 0.45,
                    "lms": 0.35,
                    "exam_service": 0.05,
                    "library_service": 0.15,
                }

        elif event == AcademicEvent.RESULT_ANNOUNCEMENT:
            # Severe concurrency shock on portal & exam service
            if 10 <= hour <= 14:
                weights = {
                    "student_portal": 0.50,
                    "lms": 0.10,
                    "exam_service": 0.38,
                    "library_service": 0.02,
                }
            else:
                weights = {
                    "student_portal": 0.40,
                    "lms": 0.35,
                    "exam_service": 0.15,
                    "library_service": 0.10,
                }

        # Normalize to ensure exact 1.0 sum
        total_w = sum(weights.values())
        return {k: round(v / total_w, 4) for k, v in weights.items()}

    def simulate_timeline(self, config: Optional[SimulationConfig] = None) -> List[HourlyActivityPoint]:
        """
        Simulates the hourly timeline for the requested duration.
        """
        cfg = config or self.config
        intensity_mult = INTENSITY_MULTIPLIERS.get(cfg.intensity, 1.0)
        
        # Average HTTP requests per concurrent student per second (nominal browsing)
        req_per_student_per_sec = 0.08  # ~1 request every 12 seconds per active student

        timeline: List[HourlyActivityPoint] = []
        for h in range(cfg.duration_hours):
            hour_of_day = h % 24
            base_coeff = BASE_DIURNAL_CURVE[hour_of_day]
            
            # Event multiplier on active concurrency
            event_boost = 1.0
            if cfg.event == AcademicEvent.EXAM_PERIOD and ((9 <= hour_of_day <= 12) or (14 <= hour_of_day <= 17)):
                event_boost = 1.65
            elif cfg.event == AcademicEvent.ASSIGNMENT_DEADLINE and (21 <= hour_of_day <= 23):
                event_boost = 1.75
            elif cfg.event == AcademicEvent.RESULT_ANNOUNCEMENT and (10 <= hour_of_day <= 13):
                event_boost = 2.40
            elif cfg.event == AcademicEvent.ADMISSION_PERIOD and (10 <= hour_of_day <= 16):
                event_boost = 1.35

            # Calculate concurrent students
            concurrent_students = int(
                cfg.total_students * cfg.concurrency_ratio * base_coeff * intensity_mult * event_boost
            )
            concurrent_students = max(10, min(concurrent_students, cfg.total_students))
            active_pct = round((concurrent_students / cfg.total_students) * 100, 2)

            # Total incoming requests per second
            total_rps = round(concurrent_students * req_per_student_per_sec, 2)

            # Distribute RPS across services
            dist = self.get_service_traffic_distribution(hour_of_day, cfg.event)
            service_rps = {s_name: round(total_rps * frac, 2) for s_name, frac in dist.items()}

            time_str = f"Day {h // 24 + 1} {hour_of_day:02d}:00" if cfg.duration_hours > 24 else f"{hour_of_day:02d}:00"

            timeline.append(
                HourlyActivityPoint(
                    hour=h,
                    time_label=time_str,
                    concurrent_students=concurrent_students,
                    active_percentage=active_pct,
                    total_incoming_rps=total_rps,
                    service_rps=service_rps,
                    event=cfg.event,
                    is_simulation=True,
                )
            )

        return timeline

