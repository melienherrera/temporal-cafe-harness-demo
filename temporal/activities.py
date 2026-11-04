"""Activity implementations — the six brew steps.

Activities are where all the real work / non-determinism lives (I/O, sleeps,
things that can fail and retry). Each one maps to a machine part in the UI.
"""
import asyncio

from temporalio import activity

from shared import Shot


@activity.defn
async def grind_beans(dose: int) -> str:
    """Grinder → Tools."""
    activity.logger.info(f"Grinding {dose}g of beans")
    await asyncio.sleep(1)
    return f"{dose}g ground"


@activity.defn
async def heat_water(target_c: int) -> int:
    """Boiler → Context engineering. Fails once to demonstrate a real retry."""
    info = activity.info()
    activity.logger.info(f"Heating water to {target_c}°C (attempt {info.attempt})")
    await asyncio.sleep(1)
    if info.attempt == 1:
        # Transient failure — Temporal retries automatically per the RetryPolicy.
        raise RuntimeError("Boiler under temperature — Temporal will retry")
    return target_c


@activity.defn
async def set_pressure(bars: int) -> int:
    """Pressure valve → Guardrails & policy."""
    activity.logger.info(f"Setting extraction pressure to {bars} bars")
    await asyncio.sleep(0.5)
    return bars


@activity.defn
async def lock_portafilter(grounds: str) -> str:
    """Portafilter → Sandboxing."""
    activity.logger.info(f"Locking portafilter with {grounds}")
    await asyncio.sleep(0.5)
    return "portafilter locked"


@activity.defn
async def extract_shot(grounds: str, water_c: int) -> Shot:
    """Group head → the model does its work (the actual shot)."""
    activity.logger.info(f"Extracting shot from {grounds} at {water_c}°C")
    await asyncio.sleep(2)
    return Shot(volume_ml=36, seconds=27.0)


@activity.defn
async def log_shot_timer(shot: Shot) -> None:
    """Shot timer → Observability."""
    activity.logger.info(f"Shot logged: {shot.volume_ml}ml in {shot.seconds}s")
