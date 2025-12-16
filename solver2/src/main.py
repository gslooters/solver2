#!/usr/bin/env python3
"""
DRAD 194: Solver2 Main Application
REST API for GREEDY Planning Engine

Endpoints:
  GET  /                  - Health check
  POST /solve-greedy      - Execute GREEDY solver
  POST /solve-sequential  - Execute Sequential solver (TODO)
  POST /solve-cpsat       - Execute CP-SAT solver (TODO)
"""

import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from solvers.solver_selector import SolverSelector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Get configuration from environment
SOLVER_STRATEGY = os.getenv('SOLVER_STRATEGY', 'greedy')
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://rzecogncpkjfytebfkni.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...')

logger.info(f"[SOLVER2] Version: 2.0.0-DRAAD194")
logger.info(f"[SOLVER2] Strategy: {SOLVER_STRATEGY}")
logger.info(f"[SOLVER2] Supabase: {SUPABASE_URL}")


@app.route('/', methods=['GET'])
def health():
    """Health check endpoint"""
    logger.info("[API] GET / - Health check")
    return jsonify({
        "status": "healthy",
        "version": "2.0.0-DRAAD194",
        "timestamp": datetime.now().isoformat(),
        "solver_configuration": {
            "strategy": SOLVER_STRATEGY,
            "primary": "GREEDY",
            "fallback": "Sequential"
        },
        "routing": "PRIMARY: GREEDY, FALLBACK: Sequential"
    }), 200


@app.route('/solve-greedy', methods=['POST'])
def solve_greedy():
    """Execute GREEDY solver
    
    Expected JSON:
    {
        "roster_id": "uuid",
        "requirements": [...],
        "employees": [...],
        "fixed_assignments": [...],
        "blocked_slots": [...]
    }
    """
    logger.info("[API] POST /solve-greedy - GREEDY solver request")
    
    try:
        data = request.get_json()
        
        # Extract parameters
        requirements = data.get('requirements', [])
        employees = data.get('employees', [])
        fixed_assignments = data.get('fixed_assignments', [])
        blocked_slots = data.get('blocked_slots', [])
        
        logger.info(f"[GREEDY] Processing: {len(requirements)} requirements, {len(employees)} employees")
        
        # Initialize solver
        selector = SolverSelector(strategy='greedy')
        
        # Execute
        result = selector.solve(
            requirements=requirements,
            employees=employees,
            fixed_assignments=fixed_assignments,
            blocked_slots=blocked_slots
        )
        
        logger.info(f"[GREEDY] Success: {result['coverage_rate']:.1f}% coverage in {result['solve_time_seconds']:.2f}s")
        
        return jsonify({
            "success": True,
            "solver": "GREEDY",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"[GREEDY] Error: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "solver": "GREEDY",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 400


@app.route('/solve-sequential', methods=['POST'])
def solve_sequential():
    """Execute Sequential solver (not yet implemented)"""
    logger.info("[API] POST /solve-sequential - Sequential solver request")
    return jsonify({
        "success": False,
        "solver": "SEQUENTIAL",
        "error": "Sequential solver not yet implemented",
        "timestamp": datetime.now().isoformat()
    }), 501


@app.route('/solve-cpsat', methods=['POST'])
def solve_cpsat():
    """Execute CP-SAT solver (not yet implemented)"""
    logger.info("[API] POST /solve-cpsat - CP-SAT solver request")
    return jsonify({
        "success": False,
        "solver": "CPSAT",
        "error": "CP-SAT solver not yet implemented",
        "timestamp": datetime.now().isoformat()
    }), 501


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"[API] 404 Not Found: {request.path}")
    return jsonify({
        "success": False,
        "error": f"Endpoint not found: {request.path}",
        "available_endpoints": [
            "GET  /",
            "POST /solve-greedy",
            "POST /solve-sequential",
            "POST /solve-cpsat"
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"[API] 500 Internal Server Error: {str(error)}", exc_info=True)
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "timestamp": datetime.now().isoformat()
    }), 500


if __name__ == '__main__':
    logger.info("[SOLVER2] Starting Flask application")
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
