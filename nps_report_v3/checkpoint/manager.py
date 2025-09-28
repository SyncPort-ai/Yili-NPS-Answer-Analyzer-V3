"""
Checkpoint management system for NPS V3 API.
Provides state persistence and recovery capabilities.
"""

import json
import pickle
import gzip
import hashlib
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import aiofiles
import aiofiles.os

from ..state import NPSAnalysisState, WorkflowPhase, CheckpointMetadata
from ..config import get_settings

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manage workflow checkpoints for recovery and persistence.
    Supports compression, versioning, and automatic cleanup.
    """

    def __init__(
        self,
        checkpoint_dir: Optional[str] = None,
        enable_compression: bool = True,
        max_checkpoints_per_workflow: int = 10,
        retention_days: int = 7
    ):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory for checkpoint storage
            enable_compression: Enable gzip compression
            max_checkpoints_per_workflow: Maximum checkpoints to keep per workflow
            retention_days: Days to retain old checkpoints
        """
        settings = get_settings()

        self.checkpoint_dir = Path(checkpoint_dir or settings.checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.enable_compression = enable_compression
        self.max_checkpoints_per_workflow = max_checkpoints_per_workflow
        self.retention_days = retention_days

        # Create subdirectories
        self.active_dir = self.checkpoint_dir / "active"
        self.archive_dir = self.checkpoint_dir / "archive"
        self.metadata_dir = self.checkpoint_dir / "metadata"

        for dir_path in [self.active_dir, self.archive_dir, self.metadata_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Cache for recent checkpoints
        self._cache: Dict[str, Any] = {}
        self._cache_size = 10

    def _get_checkpoint_path(
        self,
        workflow_id: str,
        checkpoint_id: str,
        archived: bool = False
    ) -> Path:
        """Get checkpoint file path."""
        base_dir = self.archive_dir if archived else self.active_dir
        workflow_dir = base_dir / workflow_id
        workflow_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{checkpoint_id}.pkl"
        if self.enable_compression:
            filename += ".gz"

        return workflow_dir / filename

    def _get_metadata_path(self, workflow_id: str) -> Path:
        """Get metadata file path for workflow."""
        return self.metadata_dir / f"{workflow_id}.json"

    def _generate_checkpoint_id(
        self,
        workflow_id: str,
        phase: WorkflowPhase
    ) -> str:
        """Generate unique checkpoint ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        phase_str = phase.value if isinstance(phase, WorkflowPhase) else phase

        # Create hash for uniqueness
        content = f"{workflow_id}_{phase_str}_{timestamp}"
        hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]

        return f"ckpt_{timestamp}_{phase_str}_{hash_suffix}"

    async def save_checkpoint(
        self,
        workflow_id: str,
        state: NPSAnalysisState,
        phase: WorkflowPhase,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save workflow checkpoint.

        Args:
            workflow_id: Workflow identifier
            state: Current state to save
            phase: Current workflow phase
            metadata: Additional metadata

        Returns:
            Checkpoint ID
        """
        checkpoint_id = self._generate_checkpoint_id(workflow_id, phase)
        checkpoint_path = self._get_checkpoint_path(workflow_id, checkpoint_id)

        try:
            # Prepare checkpoint data
            checkpoint_data = {
                "checkpoint_id": checkpoint_id,
                "workflow_id": workflow_id,
                "phase": phase.value if isinstance(phase, WorkflowPhase) else phase,
                "timestamp": datetime.now().isoformat(),
                "state": dict(state),
                "metadata": metadata or {}
            }

            # Serialize state
            serialized = pickle.dumps(checkpoint_data, protocol=pickle.HIGHEST_PROTOCOL)

            # Compress if enabled
            if self.enable_compression:
                serialized = gzip.compress(serialized, compresslevel=6)

            # Save to file
            async with aiofiles.open(checkpoint_path, "wb") as f:
                await f.write(serialized)

            # Calculate size and compression ratio
            size_bytes = len(serialized)
            original_size = len(pickle.dumps(checkpoint_data))
            compression_ratio = 1 - (size_bytes / original_size) if self.enable_compression else None

            # Update metadata
            checkpoint_meta = CheckpointMetadata(
                checkpoint_id=checkpoint_id,
                phase=phase,
                timestamp=datetime.now(),
                state_size_bytes=size_bytes,
                compression_ratio=compression_ratio,
                agents_completed=list(state.get("agent_outputs", {}).keys()),
                next_agent=state.get("current_agent")
            )

            await self._update_metadata(workflow_id, checkpoint_meta)

            # Update cache
            cache_key = f"{workflow_id}_{checkpoint_id}"
            self._cache[cache_key] = checkpoint_data

            # Cleanup old checkpoints
            await self._cleanup_old_checkpoints(workflow_id)

            logger.info(
                f"Saved checkpoint {checkpoint_id} for workflow {workflow_id} "
                f"(size: {size_bytes / 1024:.2f} KB, compression: {compression_ratio:.2f if compression_ratio else 'N/A'})"
            )

            return checkpoint_id

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise RuntimeError(f"Checkpoint save failed: {e}")

    async def load_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load workflow checkpoint.

        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Specific checkpoint ID (latest if None)

        Returns:
            Checkpoint data including state
        """
        # Check cache first
        if checkpoint_id:
            cache_key = f"{workflow_id}_{checkpoint_id}"
            if cache_key in self._cache:
                logger.debug(f"Loading checkpoint {checkpoint_id} from cache")
                return self._cache[cache_key]

        # Get checkpoint ID if not provided
        if not checkpoint_id:
            checkpoint_id = await self._get_latest_checkpoint_id(workflow_id)
            if not checkpoint_id:
                raise ValueError(f"No checkpoints found for workflow {workflow_id}")

        # Find checkpoint file
        checkpoint_path = self._get_checkpoint_path(workflow_id, checkpoint_id)

        if not checkpoint_path.exists():
            # Check archive
            checkpoint_path = self._get_checkpoint_path(workflow_id, checkpoint_id, archived=True)
            if not checkpoint_path.exists():
                raise FileNotFoundError(f"Checkpoint {checkpoint_id} not found")

        try:
            # Load from file
            async with aiofiles.open(checkpoint_path, "rb") as f:
                serialized = await f.read()

            # Decompress if needed
            if self.enable_compression:
                serialized = gzip.decompress(serialized)

            # Deserialize
            checkpoint_data = pickle.loads(serialized)

            # Update cache
            cache_key = f"{workflow_id}_{checkpoint_id}"
            self._cache[cache_key] = checkpoint_data

            # Manage cache size
            if len(self._cache) > self._cache_size:
                # Remove oldest entries
                oldest_keys = list(self._cache.keys())[:-self._cache_size]
                for key in oldest_keys:
                    del self._cache[key]

            logger.info(f"Loaded checkpoint {checkpoint_id} for workflow {workflow_id}")

            return checkpoint_data

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            raise RuntimeError(f"Checkpoint load failed: {e}")

    async def list_checkpoints(
        self,
        workflow_id: str,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all checkpoints for a workflow.

        Args:
            workflow_id: Workflow identifier
            include_archived: Include archived checkpoints

        Returns:
            List of checkpoint metadata
        """
        checkpoints = []

        # Load metadata
        metadata = await self._load_metadata(workflow_id)

        if metadata:
            checkpoints = metadata.get("checkpoints", [])

            if not include_archived:
                # Filter out archived checkpoints
                checkpoints = [
                    cp for cp in checkpoints
                    if not cp.get("archived", False)
                ]

        # Sort by timestamp (newest first)
        checkpoints.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return checkpoints

    async def delete_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str
    ) -> bool:
        """
        Delete a specific checkpoint.

        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Checkpoint to delete

        Returns:
            True if deleted successfully
        """
        # Find checkpoint file
        checkpoint_path = self._get_checkpoint_path(workflow_id, checkpoint_id)

        if not checkpoint_path.exists():
            checkpoint_path = self._get_checkpoint_path(workflow_id, checkpoint_id, archived=True)

        if checkpoint_path.exists():
            try:
                await aiofiles.os.remove(checkpoint_path)

                # Remove from cache
                cache_key = f"{workflow_id}_{checkpoint_id}"
                if cache_key in self._cache:
                    del self._cache[cache_key]

                # Update metadata
                metadata = await self._load_metadata(workflow_id)
                if metadata:
                    metadata["checkpoints"] = [
                        cp for cp in metadata.get("checkpoints", [])
                        if cp.get("checkpoint_id") != checkpoint_id
                    ]
                    await self._save_metadata(workflow_id, metadata)

                logger.info(f"Deleted checkpoint {checkpoint_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to delete checkpoint: {e}")
                return False

        return False

    async def archive_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str
    ) -> bool:
        """
        Archive a checkpoint (move to archive directory).

        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Checkpoint to archive

        Returns:
            True if archived successfully
        """
        active_path = self._get_checkpoint_path(workflow_id, checkpoint_id)
        archive_path = self._get_checkpoint_path(workflow_id, checkpoint_id, archived=True)

        if active_path.exists():
            try:
                # Move file
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                await aiofiles.os.rename(active_path, archive_path)

                # Update metadata
                metadata = await self._load_metadata(workflow_id)
                if metadata:
                    for cp in metadata.get("checkpoints", []):
                        if cp.get("checkpoint_id") == checkpoint_id:
                            cp["archived"] = True
                            cp["archived_at"] = datetime.now().isoformat()
                            break

                    await self._save_metadata(workflow_id, metadata)

                logger.info(f"Archived checkpoint {checkpoint_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to archive checkpoint: {e}")
                return False

        return False

    async def restore_from_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: Optional[str] = None
    ) -> NPSAnalysisState:
        """
        Restore state from checkpoint.

        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Specific checkpoint (latest if None)

        Returns:
            Restored state
        """
        checkpoint_data = await self.load_checkpoint(workflow_id, checkpoint_id)

        # Extract state
        state = checkpoint_data.get("state")

        if not state:
            raise ValueError("Invalid checkpoint: missing state data")

        # Convert back to NPSAnalysisState
        return NPSAnalysisState(**state)

    async def _update_metadata(
        self,
        workflow_id: str,
        checkpoint_meta: CheckpointMetadata
    ):
        """Update workflow metadata with new checkpoint info."""
        metadata = await self._load_metadata(workflow_id) or {
            "workflow_id": workflow_id,
            "created_at": datetime.now().isoformat(),
            "checkpoints": []
        }

        # Add checkpoint metadata
        metadata["checkpoints"].append({
            "checkpoint_id": checkpoint_meta["checkpoint_id"],
            "phase": checkpoint_meta["phase"].value if isinstance(checkpoint_meta["phase"], WorkflowPhase) else checkpoint_meta["phase"],
            "timestamp": checkpoint_meta["timestamp"].isoformat(),
            "size_bytes": checkpoint_meta["state_size_bytes"],
            "compression_ratio": checkpoint_meta["compression_ratio"],
            "agents_completed": checkpoint_meta["agents_completed"],
            "next_agent": checkpoint_meta["next_agent"],
            "archived": False
        })

        metadata["last_updated"] = datetime.now().isoformat()
        metadata["total_checkpoints"] = len(metadata["checkpoints"])

        await self._save_metadata(workflow_id, metadata)

    async def _load_metadata(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Load workflow metadata."""
        metadata_path = self._get_metadata_path(workflow_id)

        if metadata_path.exists():
            try:
                async with aiofiles.open(metadata_path, "r") as f:
                    content = await f.read()
                    return json.loads(content)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")

        return None

    async def _save_metadata(self, workflow_id: str, metadata: Dict[str, Any]):
        """Save workflow metadata."""
        metadata_path = self._get_metadata_path(workflow_id)

        try:
            async with aiofiles.open(metadata_path, "w") as f:
                await f.write(json.dumps(metadata, indent=2))
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    async def _get_latest_checkpoint_id(self, workflow_id: str) -> Optional[str]:
        """Get the latest checkpoint ID for a workflow."""
        metadata = await self._load_metadata(workflow_id)

        if metadata and metadata.get("checkpoints"):
            # Sort by timestamp and get latest
            checkpoints = metadata["checkpoints"]
            checkpoints.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            # Find latest non-archived checkpoint
            for cp in checkpoints:
                if not cp.get("archived", False):
                    return cp.get("checkpoint_id")

        return None

    async def _cleanup_old_checkpoints(self, workflow_id: str):
        """Clean up old checkpoints based on retention policy."""
        metadata = await self._load_metadata(workflow_id)

        if not metadata:
            return

        checkpoints = metadata.get("checkpoints", [])

        # Sort by timestamp
        checkpoints.sort(key=lambda x: x.get("timestamp", ""))

        # Keep only max_checkpoints_per_workflow
        if len(checkpoints) > self.max_checkpoints_per_workflow:
            to_delete = checkpoints[:-self.max_checkpoints_per_workflow]

            for cp in to_delete:
                checkpoint_id = cp.get("checkpoint_id")
                if checkpoint_id:
                    # Archive instead of delete
                    await self.archive_checkpoint(workflow_id, checkpoint_id)

        # Clean up very old archived checkpoints
        cutoff_date = datetime.now().timestamp() - (self.retention_days * 86400)

        for cp in checkpoints:
            if cp.get("archived"):
                timestamp_str = cp.get("timestamp", "")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str).timestamp()
                    if timestamp < cutoff_date:
                        await self.delete_checkpoint(workflow_id, cp.get("checkpoint_id"))


# Global checkpoint manager instance
_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """Get global checkpoint manager instance."""
    global _checkpoint_manager

    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()

    return _checkpoint_manager