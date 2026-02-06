# Tutorial 4: Python Statistical Analysis Workflow Integration

## Learning Objectives

By the end of this tutorial, you will understand:
- How to integrate all three Python statistical scripts into a complete analysis workflow
- Data flow patterns between different analysis stages
- Automated pipeline creation with Python
- Best practices for statistical analysis project organization
- Error handling and validation across the complete workflow

## Complete Workflow Overview

### The Three-Stage Analysis Pipeline

The Python statistical analysis workflow consists of three sequential stages:

1. **Quality Gate Validation** (`01_quality_gate_metrics.py`)
   - Validates model performance against deployment thresholds
   - Uses scikit-learn for robust metric computation
   - Provides pass/fail decisions for model deployment

2. **Pattern Change Detection** (`02_stuart_maxwell_test.py`)
   - Compares prediction patterns between model versions
   - Uses scipy for chi-squared statistical testing
   - Identifies systematic changes in model behavior

3. **Per-Class Impact Analysis** (`03_perclass_paired_ttests.py`)
   - Identifies specific emotion classes that improved/degraded
   - Uses scipy.stats for paired t-tests with multiple comparison correction
   - Provides detailed class-level insights

### Workflow Decision Logic

```python
def determine_analysis_path(quality_gates_pass: bool, 
                          has_comparison_data: bool,
                          has_fold_data: bool) -> List[str]:
    """
    Determine which analyses to run based on available data and results.
    
    Args:
        quality_gates_pass: Whether quality gates analysis passed
        has_comparison_data: Whether model comparison data is available
        has_fold_data: Whether fold-level metrics are available
        
    Returns:
        List of analysis steps to execute
    """
    analysis_steps = ['quality_gates']
    
    if not quality_gates_pass:
        print("⚠️  Quality gates failed - investigate before proceeding")
        return analysis_steps
    
    if has_comparison_data:
        analysis_steps.append('stuart_maxwell')
        
        if has_fold_data:
            analysis_steps.append('perclass_ttests')
    
    return analysis_steps
```

## Integrated Workflow Implementation

### Master Workflow Class

```python
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import pandas as pd

@dataclass
class WorkflowConfig:
    """Configuration for statistical analysis workflow."""
    
    # Input data paths
    predictions_csv: Optional[Path] = None
    comparison_csv: Optional[Path] = None
    fold_metrics_csv: Optional[Path] = None
    
    # Output configuration
    output_dir: Path = Path("results/analysis")
    model_name: str = "model"
    
    # Analysis parameters
    alpha: float = 0.05
    correction_method: str = "BH"
    
    # Visualization options
    generate_plots: bool = True
    interactive_plots: bool = False
    
    # Demo options
    use_demo: bool = False
    demo_samples: int = 2000
    demo_imbalance: float = 0.3
    demo_noise: float = 0.1
    demo_effect_size: str = "medium"
    demo_effect_pattern: str = "mixed"

class StatisticalAnalysisWorkflow:
    """Complete statistical analysis workflow orchestrator."""
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.results = {}
        self.analysis_log = []
        
        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_complete_analysis(self) -> Dict[str, Any]:
        """
        Execute complete statistical analysis workflow.
        
        Returns:
            Dictionary containing all analysis results
        """
        print("=" * 80)
        print(f"STATISTICAL ANALYSIS WORKFLOW - {self.config.model_name.upper()}")
        print("=" * 80)
        
        try:
            # Stage 1: Quality Gates
            self._run_quality_gates()
            
            # Determine next steps based on quality gates
            if self._should_continue_analysis():
                
                # Stage 2: Stuart-Maxwell (if comparison data available)
                if self._has_comparison_data():
                    self._run_stuart_maxwell()
                    
                    # Stage 3: Per-Class Analysis (if significant changes detected)
                    if self._should_run_perclass_analysis():
                        self._run_perclass_analysis()
                
                # Generate integrated report
                self._generate_integrated_report()
            
            return self.results
            
        except Exception as e:
            self._log_error(f"Workflow failed: {e}")
            raise
    
    def _run_quality_gates(self) -> None:
        """Execute quality gates analysis."""
        print("\n🔍 STAGE 1: Quality Gate Analysis")
        print("-" * 40)
        
        cmd = self._build_quality_gates_command()
        result = self._execute_script(cmd, "quality_gates")
        
        # Parse results to determine if gates passed
        output_file = self.config.output_dir / "quality_gates" / "results.json"
        if output_file.exists():
            with open(output_file) as f:
                gate_results = json.load(f)
                self.results['quality_gates'] = gate_results
                
                # Check if all gates passed
                gates_passed = all(gate['passed'] for gate in gate_results.get('gates', {}).values())
                self.results['quality_gates_passed'] = gates_passed
                
                if gates_passed:
                    print("✅ Quality gates PASSED - proceeding with analysis")
                else:
                    print("❌ Quality gates FAILED - review model performance")
        
        self._log_analysis("quality_gates", "completed")
    
    def _run_stuart_maxwell(self) -> None:
        """Execute Stuart-Maxwell test analysis."""
        print("\n📊 STAGE 2: Stuart-Maxwell Pattern Analysis")
        print("-" * 40)
        
        cmd = self._build_stuart_maxwell_command()
        result = self._execute_script(cmd, "stuart_maxwell")
        
        # Parse results to check for significant changes
        output_file = self.config.output_dir / "stuart_maxwell" / "results.json"
        if output_file.exists():
            with open(output_file) as f:
                sm_results = json.load(f)
                self.results['stuart_maxwell'] = sm_results
                
                significant = sm_results.get('significant', False)
                p_value = sm_results.get('p_value', 1.0)
                effect_size = sm_results.get('effect_interpretation', 'unknown')
                
                if significant:
                    print(f"✅ SIGNIFICANT pattern changes detected (p = {p_value:.6f}, effect = {effect_size})")
                else:
                    print(f"❌ No significant pattern changes (p = {p_value:.6f}, effect = {effect_size})")
        
        self._log_analysis("stuart_maxwell", "completed")
    
    def _run_perclass_analysis(self) -> None:
        """Execute per-class paired t-tests analysis."""
        print("\n🎯 STAGE 3: Per-Class Impact Analysis")
        print("-" * 40)
        
        cmd = self._build_perclass_command()
        result = self._execute_script(cmd, "perclass")
        
        # Parse results to summarize class-level changes
        output_file = self.config.output_dir / "perclass" / "results.json"
        if output_file.exists():
            with open(output_file) as f:
                pc_results = json.load(f)
                self.results['perclass'] = pc_results
                
                n_improved = pc_results.get('n_improved', 0)
                n_degraded = pc_results.get('n_degraded', 0)
                significant_classes = pc_results.get('significant_classes', [])
                
                print(f"📈 Classes improved: {n_improved}")
                print(f"📉 Classes degraded: {n_degraded}")
                if significant_classes:
                    print(f"🎯 Significant changes: {', '.join(significant_classes)}")
        
        self._log_analysis("perclass", "completed")
    
    def _build_quality_gates_command(self) -> List[str]:
        """Build command for quality gates analysis."""
        cmd = ["python", "stats/scripts/01_quality_gate_metrics.py"]
        
        if self.config.use_demo:
            cmd.extend([
                "--demo",
                "--demo-samples", str(self.config.demo_samples),
                "--demo-imbalance", str(self.config.demo_imbalance),
                "--demo-noise", str(self.config.demo_noise)
            ])
        elif self.config.predictions_csv:
            cmd.extend(["--predictions-csv", str(self.config.predictions_csv)])
        else:
            raise ValueError("Must provide either demo mode or predictions CSV")
        
        cmd.extend([
            "--output", str(self.config.output_dir / "quality_gates"),
            "--model-name", self.config.model_name
        ])
        
        if self.config.generate_plots:
            cmd.append("--plot")
        
        return cmd
    
    def _build_stuart_maxwell_command(self) -> List[str]:
        """Build command for Stuart-Maxwell analysis."""
        cmd = ["python", "stats/scripts/02_stuart_maxwell_test.py"]
        
        if self.config.use_demo:
            cmd.extend([
                "--demo",
                "--demo-samples", str(self.config.demo_samples),
                "--effect-size", self.config.demo_effect_size
            ])
        elif self.config.comparison_csv:
            cmd.extend(["--predictions-csv", str(self.config.comparison_csv)])
        else:
            raise ValueError("Must provide either demo mode or comparison CSV")
        
        cmd.extend([
            "--output", str(self.config.output_dir / "stuart_maxwell"),
            "--alpha", str(self.config.alpha)
        ])
        
        if self.config.generate_plots:
            cmd.append("--plot")
        
        return cmd
    
    def _build_perclass_command(self) -> List[str]:
        """Build command for per-class analysis."""
        cmd = ["python", "stats/scripts/03_perclass_paired_ttests.py"]
        
        if self.config.use_demo:
            cmd.extend([
                "--demo",
                "--n-folds", "10",
                "--effect-pattern", self.config.demo_effect_pattern
            ])
        elif self.config.fold_metrics_csv:
            cmd.extend(["--metrics-csv", str(self.config.fold_metrics_csv)])
        else:
            raise ValueError("Must provide either demo mode or fold metrics CSV")
        
        cmd.extend([
            "--output", str(self.config.output_dir / "perclass"),
            "--correction", self.config.correction_method,
            "--alpha", str(self.config.alpha)
        ])
        
        if self.config.generate_plots:
            cmd.append("--plot")
        
        return cmd
    
    def _execute_script(self, cmd: List[str], stage: str) -> subprocess.CompletedProcess:
        """Execute a statistical analysis script."""
        try:
            print(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ {stage} completed successfully")
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ {stage} failed with exit code {e.returncode}")
            print(f"Error output: {e.stderr}")
            raise
    
    def _should_continue_analysis(self) -> bool:
        """Determine if analysis should continue based on quality gates."""
        return self.results.get('quality_gates_passed', False)
    
    def _has_comparison_data(self) -> bool:
        """Check if comparison data is available."""
        return self.config.use_demo or self.config.comparison_csv is not None
    
    def _should_run_perclass_analysis(self) -> bool:
        """Determine if per-class analysis should be run."""
        if not (self.config.use_demo or self.config.fold_metrics_csv):
            return False
        
        # Run if Stuart-Maxwell detected significant changes
        sm_results = self.results.get('stuart_maxwell', {})
        return sm_results.get('significant', False)
    
    def _generate_integrated_report(self) -> None:
        """Generate comprehensive integrated analysis report."""
        print("\n📋 GENERATING INTEGRATED REPORT")
        print("-" * 40)
        
        report = {
            'workflow_config': self.config.__dict__,
            'analysis_summary': self._create_analysis_summary(),
            'recommendations': self._generate_recommendations(),
            'results': self.results,
            'analysis_log': self.analysis_log
        }
        
        # Save integrated report
        report_path = self.config.output_dir / "integrated_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 Integrated report saved: {report_path}")
        
        # Print executive summary
        self._print_executive_summary(report['analysis_summary'])
    
    def _create_analysis_summary(self) -> Dict[str, Any]:
        """Create high-level analysis summary."""
        summary = {
            'model_name': self.config.model_name,
            'stages_completed': len(self.analysis_log),
            'quality_gates_passed': self.results.get('quality_gates_passed', False)
        }
        
        # Stuart-Maxwell summary
        if 'stuart_maxwell' in self.results:
            sm = self.results['stuart_maxwell']
            summary['pattern_changes'] = {
                'significant': sm.get('significant', False),
                'p_value': sm.get('p_value', None),
                'effect_size': sm.get('effect_interpretation', None)
            }
        
        # Per-class summary
        if 'perclass' in self.results:
            pc = self.results['perclass']
            summary['class_changes'] = {
                'improved': pc.get('n_improved', 0),
                'degraded': pc.get('n_degraded', 0),
                'unchanged': pc.get('n_unchanged', 0),
                'significant_classes': pc.get('significant_classes', [])
            }
        
        return summary
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on analysis results."""
        recommendations = []
        
        # Quality gates recommendations
        if not self.results.get('quality_gates_passed', False):
            recommendations.append("🚨 CRITICAL: Address quality gate failures before deployment")
            recommendations.append("• Review model architecture and training approach")
            recommendations.append("• Increase training data or improve data quality")
        
        # Stuart-Maxwell recommendations
        if 'stuart_maxwell' in self.results:
            sm = self.results['stuart_maxwell']
            if sm.get('significant', False):
                effect = sm.get('effect_interpretation', 'unknown')
                if effect in ['medium', 'large']:
                    recommendations.append("📊 Significant pattern changes detected - investigate per-class impacts")
                else:
                    recommendations.append("📊 Minor pattern changes detected - monitor in production")
        
        # Per-class recommendations
        if 'perclass' in self.results:
            pc = self.results['perclass']
            n_improved = pc.get('n_improved', 0)
            n_degraded = pc.get('n_degraded', 0)
            
            if n_improved > n_degraded:
                recommendations.append("✅ Overall positive impact from fine-tuning")
                recommendations.append("• Deploy fine-tuned model")
                if n_degraded > 0:
                    recommendations.append("• Monitor degraded classes in production")
            elif n_degraded > n_improved:
                recommendations.append("⚠️ Fine-tuning caused more harm than good")
                recommendations.append("• Consider reverting to base model")
                recommendations.append("• Investigate fine-tuning approach")
            else:
                recommendations.append("📊 Mixed results from fine-tuning")
                recommendations.append("• Evaluate trade-offs carefully")
        
        return recommendations
    
    def _print_executive_summary(self, summary: Dict[str, Any]) -> None:
        """Print executive summary of analysis results."""
        print("\n" + "=" * 80)
        print("EXECUTIVE SUMMARY")
        print("=" * 80)
        
        print(f"\nModel: {summary['model_name']}")
        print(f"Analysis Stages Completed: {summary['stages_completed']}/3")
        
        # Quality gates
        gates_status = "PASS ✅" if summary['quality_gates_passed'] else "FAIL ❌"
        print(f"Quality Gates: {gates_status}")
        
        # Pattern changes
        if 'pattern_changes' in summary:
            pc = summary['pattern_changes']
            change_status = "YES" if pc['significant'] else "NO"
            print(f"Significant Pattern Changes: {change_status}")
            if pc['significant']:
                print(f"  • P-value: {pc['p_value']:.6f}")
                print(f"  • Effect Size: {pc['effect_size']}")
        
        # Class changes
        if 'class_changes' in summary:
            cc = summary['class_changes']
            print(f"Class-Level Changes:")
            print(f"  • Improved: {cc['improved']} classes")
            print(f"  • Degraded: {cc['degraded']} classes")
            print(f"  • Unchanged: {cc['unchanged']} classes")
            if cc['significant_classes']:
                print(f"  • Significant: {', '.join(cc['significant_classes'])}")
    
    def _log_analysis(self, stage: str, status: str) -> None:
        """Log analysis step completion."""
        self.analysis_log.append({
            'stage': stage,
            'status': status,
            'timestamp': pd.Timestamp.now().isoformat()
        })
    
    def _log_error(self, message: str) -> None:
        """Log error message."""
        self.analysis_log.append({
            'stage': 'error',
            'status': 'failed',
            'message': message,
            'timestamp': pd.Timestamp.now().isoformat()
        })
```

## Usage Examples

### Complete Demo Analysis

```python
def run_demo_analysis():
    """Run complete demo analysis workflow."""
    
    config = WorkflowConfig(
        use_demo=True,
        demo_samples=2000,
        demo_imbalance=0.3,
        demo_noise=0.1,
        demo_effect_size="medium",
        demo_effect_pattern="mixed",
        output_dir=Path("results/demo_analysis"),
        model_name="demo_model",
        generate_plots=True
    )
    
    workflow = StatisticalAnalysisWorkflow(config)
    results = workflow.run_complete_analysis()
    
    return results

# Execute demo
if __name__ == "__main__":
    results = run_demo_analysis()
```

### Real Data Analysis

```python
def run_real_data_analysis():
    """Run analysis with real model data."""
    
    config = WorkflowConfig(
        predictions_csv=Path("data/model_predictions.csv"),
        comparison_csv=Path("data/model_comparison.csv"),
        fold_metrics_csv=Path("data/fold_metrics.csv"),
        output_dir=Path("results/model_v2_analysis"),
        model_name="emotion_classifier_v2",
        alpha=0.05,
        correction_method="BH",
        generate_plots=True,
        interactive_plots=True
    )
    
    workflow = StatisticalAnalysisWorkflow(config)
    results = workflow.run_complete_analysis()
    
    return results
```

### Batch Model Comparison

```python
def compare_multiple_models():
    """Compare multiple model versions."""
    
    models = [
        {"name": "baseline", "predictions": "data/baseline_predictions.csv"},
        {"name": "fine_tuned_v1", "predictions": "data/ft_v1_predictions.csv"},
        {"name": "fine_tuned_v2", "predictions": "data/ft_v2_predictions.csv"}
    ]
    
    results = {}
    
    for model in models:
        print(f"\n{'='*60}")
        print(f"ANALYZING MODEL: {model['name']}")
        print(f"{'='*60}")
        
        config = WorkflowConfig(
            predictions_csv=Path(model['predictions']),
            output_dir=Path(f"results/{model['name']}_analysis"),
            model_name=model['name'],
            generate_plots=True
        )
        
        workflow = StatisticalAnalysisWorkflow(config)
        results[model['name']] = workflow.run_complete_analysis()
    
    # Generate comparative report
    generate_comparative_report(results)
    
    return results
```

## Best Practices

### 1. Data Validation Pipeline

```python
def validate_input_data(config: WorkflowConfig) -> bool:
    """Validate all input data before starting analysis."""
    
    if config.use_demo:
        return True  # Demo data is always valid
    
    # Validate predictions CSV
    if config.predictions_csv and config.predictions_csv.exists():
        df = pd.read_csv(config.predictions_csv)
        required_cols = ['y_true', 'y_pred']
        if not all(col in df.columns for col in required_cols):
            print(f"❌ Missing columns in {config.predictions_csv}: {required_cols}")
            return False
    
    # Validate comparison CSV
    if config.comparison_csv and config.comparison_csv.exists():
        df = pd.read_csv(config.comparison_csv)
        required_cols = ['base_pred', 'finetuned_pred']
        if not all(col in df.columns for col in required_cols):
            print(f"❌ Missing columns in {config.comparison_csv}: {required_cols}")
            return False
    
    # Validate fold metrics CSV
    if config.fold_metrics_csv and config.fold_metrics_csv.exists():
        df = pd.read_csv(config.fold_metrics_csv)
        required_cols = ['fold', 'emotion_class', 'base_score', 'finetuned_score']
        if not all(col in df.columns for col in required_cols):
            print(f"❌ Missing columns in {config.fold_metrics_csv}: {required_cols}")
            return False
    
    print("✅ All input data validated successfully")
    return True
```

### 2. Error Recovery and Partial Results

```python
def run_robust_analysis(config: WorkflowConfig) -> Dict[str, Any]:
    """Run analysis with error recovery and partial results."""
    
    workflow = StatisticalAnalysisWorkflow(config)
    partial_results = {}
    
    try:
        # Always try quality gates first
        workflow._run_quality_gates()
        partial_results['quality_gates'] = workflow.results.get('quality_gates')
        
        if workflow._should_continue_analysis():
            try:
                if workflow._has_comparison_data():
                    workflow._run_stuart_maxwell()
                    partial_results['stuart_maxwell'] = workflow.results.get('stuart_maxwell')
                    
                    try:
                        if workflow._should_run_perclass_analysis():
                            workflow._run_perclass_analysis()
                            partial_results['perclass'] = workflow.results.get('perclass')
                    except Exception as e:
                        print(f"⚠️ Per-class analysis failed: {e}")
                        print("📊 Continuing with partial results...")
            except Exception as e:
                print(f"⚠️ Stuart-Maxwell analysis failed: {e}")
                print("📊 Continuing with quality gates only...")
    
    except Exception as e:
        print(f"❌ Quality gates analysis failed: {e}")
        raise
    
    return partial_results
```

## Key Takeaways

1. **Sequential workflow design**: Each stage builds on the previous one
2. **Robust error handling**: Graceful degradation with partial results
3. **Comprehensive logging**: Track all analysis steps and decisions
4. **Flexible configuration**: Support both demo and real data workflows
5. **Integrated reporting**: Combine results from all stages for actionable insights

## Next Steps

- **Practice**: Run the complete workflow with demo data
- **Customize**: Adapt the workflow for your specific analysis needs
- **Integrate**: Incorporate into your MLOps pipeline
- **Monitor**: Use for ongoing model performance monitoring

This integrated workflow provides a systematic approach to emotion classification model evaluation, combining the power of scikit-learn, scipy, and pandas for comprehensive statistical analysis!
