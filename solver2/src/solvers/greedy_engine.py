#!/usr/bin/env python3
"""
DRAD 194: GREEDY PLANNING ENGINE
Fast roster optimization using greedy allocation algorithm
Coverage: 95%+ in 2-5 seconds
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json


class SeverityLevel(Enum):
    """Bottleneck severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class RosteringRequirement:
    """Single slot requirement (date, dagdeel, service)"""
    date: str  # YYYY-MM-DD
    dagdeel: str  # "ochtend", "middag", "avond", "nacht"
    service_id: str  # UUID
    required_count: int  # How many needed
    team: str = ""  # Optional team filter


@dataclass
class EmployeeCapability:
    """What an employee can do"""
    employee_id: str
    voornaam: str
    achternaam: str
    capable_services: Dict[str, bool] = field(default_factory=dict)  # service_id -> True/False
    available_dates: Set[str] = field(default_factory=set)  # YYYY-MM-DD dates
    team: str = ""
    max_shifts_per_week: int = 40  # Max hours/week
    current_shifts: int = 0  # Running total


@dataclass
class FixedAssignment:
    """Pre-planned assignment (LOCKED, cannot remove)"""
    employee_id: str
    date: str  # YYYY-MM-DD
    dagdeel: str
    service_id: str
    reason: str = "pre-planned"  # Why locked


@dataclass
class BlockedSlot:
    """Employee unavailable (sick, vacation, etc)"""
    employee_id: str
    date: str  # YYYY-MM-DD
    dagdeel: str
    reason: str = "sick"


@dataclass
class Assignment:
    """Single shift assignment"""
    assignment_id: str  # UUID
    employee_id: str
    date: str
    dagdeel: str
    service_id: str
    source: str = "greedy"  # "pre-planned" or "greedy"
    is_locked: bool = False


@dataclass
class Bottleneck:
    """Cannot fill a slot"""
    date: str
    dagdeel: str
    service_id: str
    required_count: int
    placed_count: int
    shortage: int = field(init=False)
    severity: SeverityLevel = SeverityLevel.MEDIUM
    reason: str = ""
    suggestions: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.shortage = self.required_count - self.placed_count
        # Determine severity
        if self.shortage >= 2:
            self.severity = SeverityLevel.CRITICAL
        elif self.shortage == 1:
            self.severity = SeverityLevel.HIGH


@dataclass
class RosteringResult:
    """Complete result of greedy rostering"""
    roster: List[Assignment]
    bottlenecks: List[Bottleneck]
    coverage_rate: float  # 0-100%
    total_slots: int
    assigned_slots: int
    solve_time_seconds: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "2.0.0-DRAAD194"

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        return {
            "roster": [{
                "assignment_id": a.assignment_id,
                "employee_id": a.employee_id,
                "date": a.date,
                "dagdeel": a.dagdeel,
                "service_id": a.service_id,
                "source": a.source,
                "is_locked": a.is_locked
            } for a in self.roster],
            "bottlenecks": [{
                "date": b.date,
                "dagdeel": b.dagdeel,
                "service_id": b.service_id,
                "required": b.required_count,
                "placed": b.placed_count,
                "shortage": b.shortage,
                "severity": b.severity.value,
                "reason": b.reason,
                "suggestions": b.suggestions
            } for b in self.bottlenecks],
            "coverage_rate": self.coverage_rate,
            "total_slots": self.total_slots,
            "assigned_slots": self.assigned_slots,
            "solve_time_seconds": self.solve_time_seconds,
            "timestamp": self.timestamp,
            "version": self.version
        }


class GreedyPlanner:
    """GREEDY Planning Engine - Fast roster optimization"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def solve(self,
              requirements: List[RosteringRequirement],
              employees: List[EmployeeCapability],
              fixed_assignments: List[FixedAssignment],
              blocked_slots: List[BlockedSlot]) -> RosteringResult:
        """
        Main solving method:
        FASE 1: Lock pre-planned assignments
        FASE 2: GREEDY allocate remaining slots
        FASE 3: Analyze bottlenecks
        FASE 4: Return result
        """
        start_time = datetime.now()
        self.logger.info("[GREEDY] Starting roster generation")

        # Data structures
        roster: List[Assignment] = []
        bottlenecks: List[Bottleneck] = []
        blocked_set = self._build_blocked_set(blocked_slots)
        assignment_count = {emp.employee_id: 0 for emp in employees}

        # FASE 1: Lock pre-planned
        self.logger.info(f"[GREEDY] FASE 1: Locking {len(fixed_assignments)} pre-planned assignments")
        for fixed in fixed_assignments:
            # Validate
            if self._is_valid_assignment(fixed.employee_id, fixed.date, fixed.dagdeel,
                                         fixed.service_id, employees, blocked_set):
                assignment = Assignment(
                    assignment_id=f"{fixed.employee_id}_{fixed.date}_{fixed.dagdeel}",
                    employee_id=fixed.employee_id,
                    date=fixed.date,
                    dagdeel=fixed.dagdeel,
                    service_id=fixed.service_id,
                    source="pre-planned",
                    is_locked=True
                )
                roster.append(assignment)
                assignment_count[fixed.employee_id] += 1

        self.logger.info(f"[GREEDY] FASE 1 complete: {len(roster)} locked assignments")

        # FASE 2: GREEDY allocate
        self.logger.info(f"[GREEDY] FASE 2: GREEDY allocating {len(requirements)} slots")
        for req in requirements:
            # Count current assignments for this slot
            current_count = len([
                a for a in roster
                if a.date == req.date and a.dagdeel == req.dagdeel and a.service_id == req.service_id
            ])

            if current_count < req.required_count:
                shortage = req.required_count - current_count
                eligible = self._find_eligible_employees(
                    req.date, req.dagdeel, req.service_id,
                    employees, roster, blocked_set, req.team
                )

                # Sort by workload (prefer lower)
                eligible.sort(key=lambda e: assignment_count.get(e.employee_id, 0))

                # Assign as many as possible
                assigned = 0
                for emp in eligible:
                    if assigned >= shortage:
                        break
                    assignment = Assignment(
                        assignment_id=f"{emp.employee_id}_{req.date}_{req.dagdeel}_{req.service_id}",
                        employee_id=emp.employee_id,
                        date=req.date,
                        dagdeel=req.dagdeel,
                        service_id=req.service_id,
                        source="greedy",
                        is_locked=False
                    )
                    roster.append(assignment)
                    assignment_count[emp.employee_id] += 1
                    assigned += 1

                # Create bottleneck if not filled
                if assigned < shortage:
                    bottleneck = Bottleneck(
                        date=req.date,
                        dagdeel=req.dagdeel,
                        service_id=req.service_id,
                        required_count=req.required_count,
                        placed_count=current_count + assigned
                    )
                    bottleneck.reason = self._analyze_bottleneck_reason(
                        req, eligible, blocked_set, employees
                    )
                    bottleneck.suggestions = self._suggest_solutions(req, bottleneck)
                    bottlenecks.append(bottleneck)

        self.logger.info(f"[GREEDY] FASE 2 complete: {len(roster)} total assignments, {len(bottlenecks)} bottlenecks")

        # Calculate metrics
        total_slots = len(requirements)
        assigned_slots = sum(1 for b in bottlenecks if b.shortage == 0) + \
                         (total_slots - len(bottlenecks))
        coverage_rate = (assigned_slots / total_slots * 100) if total_slots > 0 else 0

        # Build result
        elapsed = (datetime.now() - start_time).total_seconds()
        result = RosteringResult(
            roster=roster,
            bottlenecks=bottlenecks,
            coverage_rate=coverage_rate,
            total_slots=total_slots,
            assigned_slots=assigned_slots,
            solve_time_seconds=elapsed
        )

        self.logger.info(f"[GREEDY] Complete: {coverage_rate:.1f}% coverage in {elapsed:.2f}s")
        return result

    def _build_blocked_set(self, blocked_slots: List[BlockedSlot]) -> Set[Tuple[str, str, str]]:
        """Build set of (employee_id, date, dagdeel) tuples for fast lookup"""
        return {(b.employee_id, b.date, b.dagdeel) for b in blocked_slots}

    def _is_valid_assignment(self,
                             employee_id: str,
                             date: str,
                             dagdeel: str,
                             service_id: str,
                             employees: List[EmployeeCapability],
                             blocked_set: Set[Tuple[str, str, str]]) -> bool:
        """Check if employee can do this assignment"""
        # Check if blocked
        if (employee_id, date, dagdeel) in blocked_set:
            return False

        # Check capability
        emp = next((e for e in employees if e.employee_id == employee_id), None)
        if not emp:
            return False

        return emp.capable_services.get(service_id, False)

    def _find_eligible_employees(self,
                                  date: str,
                                  dagdeel: str,
                                  service_id: str,
                                  employees: List[EmployeeCapability],
                                  roster: List[Assignment],
                                  blocked_set: Set[Tuple[str, str, str]],
                                  team_filter: str = "") -> List[EmployeeCapability]:
        """Find employees eligible for this slot"""
        eligible = []

        for emp in employees:
            # Check team filter
            if team_filter and emp.team != team_filter:
                continue

            # Check capability
            if not emp.capable_services.get(service_id, False):
                continue

            # Check blocked
            if (emp.employee_id, date, dagdeel) in blocked_set:
                continue

            # Check not already assigned this slot
            already_assigned = any(
                a.employee_id == emp.employee_id and
                a.date == date and a.dagdeel == dagdeel
                for a in roster
            )
            if already_assigned:
                continue

            eligible.append(emp)

        return eligible

    def _analyze_bottleneck_reason(self,
                                    req: RosteringRequirement,
                                    eligible: List[EmployeeCapability],
                                    blocked_set: Set[Tuple[str, str, str]],
                                    employees: List[EmployeeCapability]) -> str:
        """Analyze why we couldn't fill this slot"""
        capable = [e for e in employees if e.capable_services.get(req.service_id, False)]
        if not capable:
            return "No employees capable of this service"

        available = [e for e in capable if (e.employee_id, req.date, req.dagdeel) not in blocked_set]
        if not available:
            return "All capable employees are blocked/unavailable"

        return "Insufficient eligible employees for this slot"

    def _suggest_solutions(self, req: RosteringRequirement, bottleneck: Bottleneck) -> List[str]:
        """Suggest solutions for bottleneck"""
        suggestions = []

        if bottleneck.shortage == 1:
            suggestions.append(f"Train 1 more employee in this service")
        elif bottleneck.shortage > 1:
            suggestions.append(f"Train {bottleneck.shortage} more employees in this service")

        suggestions.append(f"Reduce requirement by {bottleneck.shortage}")
        suggestions.append("Check for scheduling conflicts")

        return suggestions
