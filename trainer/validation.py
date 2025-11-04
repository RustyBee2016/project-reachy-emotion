"""
Model validation gates for production deployment.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ValidationGates:
    """
    Validation gates to ensure model quality before deployment.
    
    Gate A: Offline validation (F1 score)
    Gate B: Shadow mode (latency check)
    Gate C: User rollout (complaint rate)
    """
    
    # Gate thresholds
    GATE_A_F1_THRESHOLD = 0.84
    GATE_B_LATENCY_MS_THRESHOLD = 250
    GATE_C_COMPLAINT_RATE_THRESHOLD = 0.01
    
    def __init__(self):
        """Initialize validation gates."""
        self.gate_results = {}
    
    def check_gate_a(
        self,
        metrics: Dict[str, float]
    ) -> bool:
        """
        Gate A: Offline validation check.
        
        Requires F1 macro score >= 0.84
        
        Args:
            metrics: Dictionary containing evaluation metrics
        
        Returns:
            True if gate passes, False otherwise
        """
        f1_score = metrics.get('f1_macro', 0.0)
        passed = f1_score >= self.GATE_A_F1_THRESHOLD
        
        self.gate_results['gate_a'] = {
            'passed': passed,
            'f1_score': f1_score,
            'threshold': self.GATE_A_F1_THRESHOLD
        }
        
        if passed:
            logger.info(f"Gate A PASSED: F1={f1_score:.3f} >= {self.GATE_A_F1_THRESHOLD}")
        else:
            logger.warning(f"Gate A FAILED: F1={f1_score:.3f} < {self.GATE_A_F1_THRESHOLD}")
        
        return passed
    
    def check_gate_b(
        self,
        latency_ms: float
    ) -> bool:
        """
        Gate B: Shadow mode latency check.
        
        Requires inference latency <= 250ms
        
        Args:
            latency_ms: Inference latency in milliseconds
        
        Returns:
            True if gate passes, False otherwise
        """
        passed = latency_ms <= self.GATE_B_LATENCY_MS_THRESHOLD
        
        self.gate_results['gate_b'] = {
            'passed': passed,
            'latency_ms': latency_ms,
            'threshold': self.GATE_B_LATENCY_MS_THRESHOLD
        }
        
        if passed:
            logger.info(f"Gate B PASSED: Latency={latency_ms:.1f}ms <= {self.GATE_B_LATENCY_MS_THRESHOLD}ms")
        else:
            logger.warning(f"Gate B FAILED: Latency={latency_ms:.1f}ms > {self.GATE_B_LATENCY_MS_THRESHOLD}ms")
        
        return passed
    
    def check_gate_c(
        self,
        complaint_rate: float
    ) -> bool:
        """
        Gate C: User rollout feedback check.
        
        Requires complaint rate < 1%
        
        Args:
            complaint_rate: Rate of user complaints (0.0 to 1.0)
        
        Returns:
            True if gate passes, False otherwise
        """
        passed = complaint_rate < self.GATE_C_COMPLAINT_RATE_THRESHOLD
        
        self.gate_results['gate_c'] = {
            'passed': passed,
            'complaint_rate': complaint_rate,
            'threshold': self.GATE_C_COMPLAINT_RATE_THRESHOLD
        }
        
        if passed:
            logger.info(f"Gate C PASSED: Complaint rate={complaint_rate:.3%} < {self.GATE_C_COMPLAINT_RATE_THRESHOLD:.1%}")
        else:
            logger.warning(f"Gate C FAILED: Complaint rate={complaint_rate:.3%} >= {self.GATE_C_COMPLAINT_RATE_THRESHOLD:.1%}")
        
        return passed
    
    def check_all_gates(
        self,
        metrics: Dict[str, float],
        latency_ms: float,
        complaint_rate: float
    ) -> bool:
        """
        Check all validation gates.
        
        Args:
            metrics: Model evaluation metrics
            latency_ms: Inference latency
            complaint_rate: User complaint rate
        
        Returns:
            True if all gates pass, False otherwise
        """
        gate_a = self.check_gate_a(metrics)
        gate_b = self.check_gate_b(latency_ms)
        gate_c = self.check_gate_c(complaint_rate)
        
        all_passed = gate_a and gate_b and gate_c
        
        if all_passed:
            logger.info("All validation gates PASSED ✓")
        else:
            failed_gates = [
                gate for gate, result in self.gate_results.items()
                if not result['passed']
            ]
            logger.error(f"Validation gates FAILED: {failed_gates}")
        
        return all_passed
    
    def get_results(self) -> Dict[str, Any]:
        """
        Get detailed results from all gates.
        
        Returns:
            Dictionary with gate results
        """
        return self.gate_results
    
    def reset(self):
        """Reset gate results for new validation run."""
        self.gate_results = {}
        logger.info("Validation gates reset")
