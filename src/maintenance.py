"""
Maintenance service — daily memory backups with 7-day retention.
"""

import asyncio
import logging
import shutil
from datetime import datetime, timedelta, timezone

from . import config

logger = logging.getLogger(__name__)


class MaintenanceService:
    def backup_memory(self) -> None:
        """Daily backup of /workspace/memory/, keeping at most 7 days."""
        src = config.MEMORY_DIR
        backup_root = src / "backup"
        backup_root.mkdir(exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        # Skip if a backup for today already exists
        if any(p.name.startswith(today) for p in backup_root.iterdir() if p.is_dir()):
            return
        dst = backup_root / today
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("backup"))
        logger.info("Memory backed up to %s", dst)
        # Prune backups older than 7 days
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y%m%d")
        for old in sorted(backup_root.iterdir()):
            if old.is_dir() and old.name < cutoff:
                shutil.rmtree(old)
                logger.info("Pruned old backup %s", old)

    async def run_loop(self) -> None:
        await asyncio.sleep(300)  # 5-minute startup grace period
        while True:
            tick_start = asyncio.get_event_loop().time()
            try:
                await asyncio.get_running_loop().run_in_executor(None, self.backup_memory)
            except Exception as exc:
                logger.error("Maintenance loop error (will retry next cycle): %s", exc)
            elapsed = asyncio.get_event_loop().time() - tick_start
            await asyncio.sleep(max(0.0, config.MAINTENANCE_INTERVAL * 60 - elapsed))
