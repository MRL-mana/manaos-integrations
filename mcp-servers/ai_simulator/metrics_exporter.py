from prometheus_client import start_http_server, Counter, Gauge, Histogram
import time

# Training metrics
EPISODE_DUR = Histogram("aisim_training_episode_duration_seconds", "Episode duration")
REWARD_SUM = Counter("aisim_agent_reward_total", "Total reward")
EMO_CONF  = Gauge("aisim_emotion_state_confidence", "Confidence emotion [0..1]")
EMO_ENERGY = Gauge("aisim_emotion_energy", "Emotion: energy [0..1]")
RPG_LEVEL = Gauge("aisim_rpg_level", "RPG overall level [0..100]")
CONS_AGREE = Gauge("aisim_consensus_agreement_ratio", "Persona consensus agreement [0..1]")
LAST_EXPORT = Gauge("aisim_last_export_unixtime", "Last exporter heartbeat (unixtime)")
SAFETY_VIOLATIONS = Counter("aisim_safety_violations_total", "Total safety violations")

# Task execution metrics (Stage B)
TASK_EXECUTIONS = Counter("aisim_task_executions_total", "Total task executions", ["task_name", "status"])
TASK_DURATION = Histogram("aisim_task_execution_duration_seconds", "Task execution duration", ["task_name"])
PENDING_APPROVALS = Gauge("aisim_pending_approvals", "Number of tasks pending approval")
TASK_REQUESTS = Counter("aisim_task_requests_total", "Total task requests", ["task_name"])

# Evolution metrics (Self-Evolution Algorithm)
EVO_TRIALS = Counter("evo_trials_total", "Total evolution trials", ["task", "variant", "mode"])
EVO_REWARD_SUM = Counter("evo_reward_sum", "Sum of rewards", ["task", "variant"])
EVO_BEST_REWARD = Gauge("evo_best_reward", "Best reward achieved", ["task"])
EVO_ACTIVE = Gauge("evo_active", "Evolution mode active (1=active, 0=off)", ["mode"])
EVO_ROLLBACKS = Counter("evo_rollbacks_total", "Total rollbacks", ["task", "reason"])

# Vision Mode metrics (Stage E)
VISION_GOALS_ACTIVE = Gauge("vision_goals_active", "Active goals count")
VISION_GOALS_COMPLETED = Gauge("vision_goals_completed", "Completed goals count")
VISION_GOALS_PROGRESS_AVG = Gauge("vision_goals_progress_avg", "Average goal progress (0-100)")
VISION_PDCA_CYCLES = Counter("vision_pdca_cycles_total", "Total PDCA cycles executed")

_DEF_PORT = 9108

def heartbeat():
    """Update heartbeat timestamp and update mock metrics for monitoring"""
    LAST_EXPORT.set(time.time())
    # Stage A: Mock metrics update (観測モード)
    import random
    EMO_CONF.set(0.3 + random.random() * 0.5)  # 0.3-0.8範囲
    EMO_ENERGY.set(0.4 + random.random() * 0.4)  # 0.4-0.8範囲
    RPG_LEVEL.set(10 + random.random() * 20)  # 10-30レベル範囲
    CONS_AGREE.set(0.6 + random.random() * 0.2)  # 0.6-0.8合意範囲

def run_metrics_server(port=_DEF_PORT):
    """Start Prometheus metrics server"""
    start_http_server(port)
    heartbeat()  # Initial heartbeat
    return True