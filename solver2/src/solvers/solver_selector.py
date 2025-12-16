#!/usr/bin/env python3
"""
DRAD 194: Solver Selector
Selects between GREEDY (primary) and Sequential (fallback) solvers
"""

import logging
from enum import Enum
from typing import Optional
from .greedy_engine import GreedyPlanner, RosteringResult, RosteringRequirement, EmployeeCapability, FixedAssignment, BlockedSlot


class SolverStrategy(Enum):
    """Available solver strategies"""
    GREEDY = "greedy"
    SEQUENTIAL = "sequential"
    CPSAT = "cpsat"


class SolverSelector:
    """Selects and executes appropriate solver"""

    # Configuration
    GREEDY = SolverStrategy.GREEDY
    SEQUENTIAL = SolverStrategy.SEQUENTIAL
    CPSAT = SolverStrategy.CPSAT

    def __init__(self, strategy: str = "greedy"):
        self.logger = logging.getLogger(__name__)
        self.strategy = self._parse_strategy(strategy)
        self.logger.info(f"[SOLVER] Initialized with strategy: {self.strategy.value}")

    def _parse_strategy(self, strategy_str: str) -> SolverStrategy:
        """Parse strategy string to enum"""
        strategy_map = {
            "greedy": SolverStrategy.GREEDY,
            "sequential": SolverStrategy.SEQUENTIAL,
            "cpsat": SolverStrategy.CPSAT,
        }
        return strategy_map.get(strategy_str.lower(), SolverStrategy.GREEDY)

    def select_solver(self) -> str:
        """Select solver based on configuration"""
        if self.strategy == SolverStrategy.GREEDY:
            self.logger.info("[SOLVER] PRIMARY: GREEDY, FALLBACK: Sequential")
            return "GREEDY"
        elif self.strategy == SolverStrategy.SEQUENTIAL:
            self.logger.info("[SOLVER] PRIMARY: Sequential, FALLBACK: None")
            return "SEQUENTIAL"
        elif self.strategy == SolverStrategy.CPSAT:
            self.logger.info("[SOLVER] PRIMARY: CP-SAT, FALLBACK: Sequential")
            return "CPSAT"
        else:
            self.logger.warning("[SOLVER] Unknown strategy, defaulting to GREEDY")
            return "GREEDY"

    def solve(self,
              requirements: list,
              employees: list,
              fixed_assignments: list = None,
              blocked_slots: list = None) -> dict:
        """
        Execute solver based on selected strategy
        Returns dict with result and metadata
        """
        if fixed_assignments is None:
            fixed_assignments = []
        if blocked_slots is None:
            blocked_slots = []

        solver_type = self.select_solver()
        self.logger.info(f"[SOLVER] Executing: {solver_type}")

        if solver_type == "GREEDY":
            return self._solve_greedy(requirements, employees, fixed_assignments, blocked_slots)
        elif solver_type == "SEQUENTIAL":
            return self._solve_sequential(requirements, employees, fixed_assignments, blocked_slots)
        elif solver_type == "CPSAT":
            return self._solve_cpsat(requirements, employees, fixed_assignments, blocked_slots)
        else:
            self.logger.error(f"[SOLVER] Unknown solver type: {solver_type}")
            raise ValueError(f"Unknown solver type: {solver_type}")

    def _solve_greedy(self, requirements, employees, fixed_assignments, blocked_slots) -> dict:
        """Execute GREEDY solver"""
        planner = GreedyPlanner()
        
        # Convert input to dataclass objects
        req_objects = [RosteringRequirement(**r) for r in requirements]
        emp_objects = [EmployeeCapability(**e) for e in employees]
        fixed_objects = [FixedAssignment(**f) for f in fixed_assignments]
        blocked_objects = [BlockedSlot(**b) for b in blocked_slots]
        
        result = planner.solve(req_objects, emp_objects, fixed_objects, blocked_objects)
        
        return {
            "success": True,
            "solver": "GREEDY",
            "result": result.to_dict(),
            "coverage_rate": result.coverage_rate,
            "solve_time_seconds": result.solve_time_seconds,
            "assignments_count": len(result.roster),
            "bottlenecks_count": len(result.bottlenecks),
        }

    def _solve_sequential(self, requirements, employees, fixed_assignments, blocked_slots) -> dict:
        """Execute Sequential solver (placeholder)"""
        self.logger.info("[SOLVER] Sequential solver not yet implemented")
        return {
            "success": False,
            "solver": "SEQUENTIAL",
            "error": "Sequential solver not yet implemented",
        }

    def _solve_cpsat(self, requirements, employees, fixed_assignments, blocked_slots) -> dict:
        """Execute CP-SAT solver (placeholder)"""
        self.logger.info("[SOLVER] CP-SAT solver not yet implemented")
        return {
            "success": False,
            "solver": "CPSAT",
            "error": "CP-SAT solver not yet implemented",
        }
