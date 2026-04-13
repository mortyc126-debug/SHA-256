"""Risk subsystem — hardcoded limits, kill switch, P&L accounting.

All modules here are safety-critical. Changes require tests + review.
"""

from scalping_bot.risk.accounting import Accountant, Trade
from scalping_bot.risk.kill_switch import KillEvent, KillSwitch, SwitchState
from scalping_bot.risk.limits import LimitCheck, RiskLimits

__all__ = [
    "Accountant",
    "KillEvent",
    "KillSwitch",
    "LimitCheck",
    "RiskLimits",
    "SwitchState",
    "Trade",
]
