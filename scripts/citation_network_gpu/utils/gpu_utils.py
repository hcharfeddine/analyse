"""GPU device management, safety monitoring, and utilities for multi-GPU processing.

Safety guarantees:
- Memory fraction is capped at 85% of VRAM to prevent kernel OOM kills.
- Thermal throttle detection: logs a warning if any GPU exceeds 83°C.
- CUDA OOM is caught and re-raised with a clear message and recovery hint.
- Per-stage memory snapshots help diagnose runaway allocations.
"""

import logging
import os
import time
from contextlib import contextmanager
from typing import List, Optional

import torch

logger = logging.getLogger(__name__)

# RTX 4090 has 24 GB VRAM. We cap at 85% = ~20.4 GB per GPU.
# Raise this only if you are sure your workload fits — OOM kills the whole process.
DEFAULT_MEMORY_FRACTION = 0.85

# Thermal safety threshold in °C. RTX 4090 throttles at ~83°C and shuts down at ~90°C.
THERMAL_WARNING_C = 80
THERMAL_CRITICAL_C = 86


def _try_import_pynvml():
    try:
        import pynvml
        pynvml.nvmlInit()
        return pynvml
    except Exception:
        return None


class GPUManager:
    """Manages GPU device allocation with safety monitoring."""

    def __init__(
        self,
        gpu_devices: Optional[List[int]] = None,
        verbose: bool = False,
        memory_fraction: float = DEFAULT_MEMORY_FRACTION,
    ):
        self.verbose = verbose
        self.memory_fraction = memory_fraction
        self.num_gpus = torch.cuda.device_count()
        self._nvml = _try_import_pynvml()

        if self.num_gpus == 0:
            logger.warning("No CUDA devices found. Using CPU fallback.")
            self.device_ids = []
        else:
            self.device_ids = gpu_devices if gpu_devices is not None else list(range(self.num_gpus))
            logger.info(f"Using GPU devices: {self.device_ids} ({self.num_gpus} total available)")
            self._apply_memory_fraction()
            self._log_gpu_info()

    # ── Memory fraction ──────────────────────────────────────────────────────

    def _apply_memory_fraction(self) -> None:
        """Cap per-GPU memory usage to avoid OOM kernel kills."""
        for gid in self.device_ids:
            try:
                torch.cuda.set_per_process_memory_fraction(self.memory_fraction, gid)
                total_gb = torch.cuda.get_device_properties(gid).total_memory / 1e9
                safe_gb = total_gb * self.memory_fraction
                logger.info(
                    f"  GPU {gid}: memory capped at {self.memory_fraction*100:.0f}% "
                    f"= {safe_gb:.1f} GB of {total_gb:.1f} GB"
                )
            except Exception as e:
                logger.warning(f"  Could not set memory fraction for GPU {gid}: {e}")

    # ── Device access ────────────────────────────────────────────────────────

    def get_device(self, idx: int = 0) -> torch.device:
        if self.device_ids and idx < len(self.device_ids):
            return torch.device(f"cuda:{self.device_ids[idx]}")
        return torch.device("cpu")

    def primary_device(self) -> torch.device:
        return self.get_device(0)

    # ── Memory reporting ─────────────────────────────────────────────────────

    def print_gpu_memory(self) -> None:
        for gid in self.device_ids:
            used = torch.cuda.memory_allocated(gid) / 1e9
            reserved = torch.cuda.memory_reserved(gid) / 1e9
            total = torch.cuda.get_device_properties(gid).total_memory / 1e9
            name = torch.cuda.get_device_properties(gid).name
            pct = used / total * 100
            level = "⚠️ " if pct > 75 else "  "
            logger.info(
                f"{level}GPU {gid} ({name}): "
                f"allocated={used:.2f} GB  reserved={reserved:.2f} GB  total={total:.2f} GB  ({pct:.1f}%)"
            )

    def memory_snapshot(self) -> List[dict]:
        """Return a list of per-GPU memory dicts (for logging/diagnostics)."""
        snapshots = []
        for gid in self.device_ids:
            props = torch.cuda.get_device_properties(gid)
            snapshots.append({
                "device": gid,
                "name": props.name,
                "allocated_gb": torch.cuda.memory_allocated(gid) / 1e9,
                "reserved_gb": torch.cuda.memory_reserved(gid) / 1e9,
                "total_gb": props.total_memory / 1e9,
            })
        return snapshots

    def clear_cache(self) -> None:
        for gid in self.device_ids:
            with torch.cuda.device(gid):
                torch.cuda.empty_cache()
        logger.debug("GPU cache cleared on all devices.")

    # ── Thermal monitoring ────────────────────────────────────────────────────

    def check_thermals(self) -> bool:
        """
        Check GPU temperatures via pynvml.
        Returns True if all GPUs are within safe range, False if any are critical.
        Logs a warning if any exceed THERMAL_WARNING_C.
        """
        if self._nvml is None:
            return True  # Can't check — assume OK

        all_safe = True
        for gid in self.device_ids:
            try:
                handle = self._nvml.nvmlDeviceGetHandleByIndex(gid)
                temp = self._nvml.nvmlDeviceGetTemperature(
                    handle, self._nvml.NVML_TEMPERATURE_GPU
                )
                if temp >= THERMAL_CRITICAL_C:
                    logger.error(
                        f"🔥 GPU {gid} CRITICAL TEMPERATURE: {temp}°C "
                        f"(threshold={THERMAL_CRITICAL_C}°C). "
                        "Consider pausing the pipeline to cool down."
                    )
                    all_safe = False
                elif temp >= THERMAL_WARNING_C:
                    logger.warning(
                        f"⚠️  GPU {gid} temperature: {temp}°C "
                        f"(warning threshold={THERMAL_WARNING_C}°C)"
                    )
                else:
                    if self.verbose:
                        logger.info(f"  GPU {gid} temperature: {temp}°C ✓")
            except Exception as e:
                logger.debug(f"Could not read temperature for GPU {gid}: {e}")
        return all_safe

    def get_temperatures(self) -> dict:
        """Return {device_id: temp_celsius} dict, or empty dict if pynvml unavailable."""
        if self._nvml is None:
            return {}
        temps = {}
        for gid in self.device_ids:
            try:
                handle = self._nvml.nvmlDeviceGetHandleByIndex(gid)
                temps[gid] = self._nvml.nvmlDeviceGetTemperature(
                    handle, self._nvml.NVML_TEMPERATURE_GPU
                )
            except Exception:
                pass
        return temps

    def get_power_usage(self) -> dict:
        """Return {device_id: power_watts} dict, or empty dict if pynvml unavailable."""
        if self._nvml is None:
            return {}
        power = {}
        for gid in self.device_ids:
            try:
                handle = self._nvml.nvmlDeviceGetHandleByIndex(gid)
                power[gid] = self._nvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW → W
            except Exception:
                pass
        return power

    # ── Context managers ──────────────────────────────────────────────────────

    @contextmanager
    def safe_stage(self, stage_name: str, check_thermals_every: int = 60):
        """
        Context manager that wraps a pipeline stage with:
        - Memory snapshot before/after
        - Thermal check before starting
        - CUDA OOM caught and re-raised with a clear message
        - Cache cleared on exit

        Usage:
            with gpu_manager.safe_stage("community"):
                run_louvain(...)
        """
        logger.info(f"[GPU SAFETY] Starting stage: {stage_name}")
        self.check_thermals()
        self.print_gpu_memory()

        start_time = time.time()
        try:
            yield self
        except torch.cuda.OutOfMemoryError as e:
            self.clear_cache()
            mem = self.memory_snapshot()
            used = [f"GPU{s['device']}={s['allocated_gb']:.1f}GB" for s in mem]
            raise RuntimeError(
                f"CUDA out of memory during stage '{stage_name}'. "
                f"Usage at failure: {', '.join(used)}. "
                f"Try reducing --batch-size or --max-gpu-memory-fraction. "
                f"Original error: {e}"
            ) from e
        except Exception:
            raise
        finally:
            elapsed = time.time() - start_time
            logger.info(f"[GPU SAFETY] Stage '{stage_name}' finished in {elapsed:.1f}s")
            self.check_thermals()
            self.print_gpu_memory()
            self.clear_cache()

    # ── Startup info ──────────────────────────────────────────────────────────

    def _log_gpu_info(self) -> None:
        logger.info("GPU Hardware Summary:")
        for gid in self.device_ids:
            props = torch.cuda.get_device_properties(gid)
            total_gb = props.total_memory / 1e9
            logger.info(
                f"  GPU {gid}: {props.name}  "
                f"VRAM={total_gb:.1f} GB  "
                f"SM={props.multi_processor_count}  "
                f"CUDA cap={props.major}.{props.minor}"
            )
        temps = self.get_temperatures()
        if temps:
            temp_str = "  ".join(f"GPU{k}={v}°C" for k, v in temps.items())
            logger.info(f"  Temperatures: {temp_str}")
        power = self.get_power_usage()
        if power:
            power_str = "  ".join(f"GPU{k}={v:.0f}W" for k, v in power.items())
            logger.info(f"  Power draw:   {power_str}")