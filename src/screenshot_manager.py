"""Screenshot storage manager for Smart Motion Detector."""

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2

from src.config import ScreenshotConfig
from src.llm_analyzer import AnalysisResult, ScreenshotSet
from src.logger import get_logger
from src.utils import timestamp_filename

# Initialize logger
logger = get_logger("screenshot_manager")


class ScreenshotManagerError(Exception):
    """Base exception for screenshot manager errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        """
        Initialize screenshot manager error.

        Args:
            message: Error message
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error


class StorageFullError(ScreenshotManagerError):
    """Exception raised when storage limit is reached."""

    pass


@dataclass
class ScreenshotMetadata:
    """Metadata for a stored screenshot set."""

    id: str
    timestamp: str
    has_before: bool
    has_now: bool
    has_after: bool
    analysis: Optional[Dict[str, Any]] = None


class ScreenshotManager:
    """Manager for storing and retrieving motion detection screenshots."""

    def __init__(
        self,
        config: ScreenshotConfig,
        storage_path: str = "/data/screenshots"
    ) -> None:
        """
        Initialize screenshot manager.

        Args:
            config: Screenshot configuration
            storage_path: Base path for screenshot storage
        """
        self.config = config
        self.storage_path = Path(storage_path)

        # Create storage directory if it doesn't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Screenshot manager initialized: storage={self.storage_path}, "
            f"max_stored={config.max_stored}"
        )

    def save(
        self,
        screenshots: ScreenshotSet,
        analysis: Optional[AnalysisResult] = None
    ) -> str:
        """
        Save a screenshot set to disk.

        Args:
            screenshots: Set of screenshots to save
            analysis: Optional LLM analysis result

        Returns:
            Screenshot set ID (timestamp-based)

        Raises:
            ScreenshotManagerError: If save operation fails
            StorageFullError: If storage limit is reached
        """
        # Check storage limit
        if self._count_stored() >= self.config.max_stored:
            logger.warning(
                f"Storage limit reached ({self.config.max_stored}), "
                "cleaning oldest screenshots"
            )
            self._cleanup_oldest()

        # Generate ID from timestamp
        screenshot_id = timestamp_filename()
        screenshot_dir = self.storage_path / screenshot_id

        try:
            # Create directory for this screenshot set
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            # Save before screenshot
            if screenshots.before is not None:
                before_path = screenshot_dir / "before.jpg"
                cv2.imwrite(
                    str(before_path),
                    screenshots.before,
                    [cv2.IMWRITE_JPEG_QUALITY, self.config.quality]
                )

            # Save now screenshot
            if screenshots.now is not None:
                now_path = screenshot_dir / "now.jpg"
                cv2.imwrite(
                    str(now_path),
                    screenshots.now,
                    [cv2.IMWRITE_JPEG_QUALITY, self.config.quality]
                )

            # Save after screenshot if available
            if screenshots.after is not None:
                after_path = screenshot_dir / "after.jpg"
                cv2.imwrite(
                    str(after_path),
                    screenshots.after,
                    [cv2.IMWRITE_JPEG_QUALITY, self.config.quality]
                )

            # Save metadata
            metadata = {
                "id": screenshot_id,
                "timestamp": screenshots.timestamp.isoformat(),
                "has_before": screenshots.before is not None,
                "has_now": screenshots.now is not None,
                "has_after": screenshots.after is not None,
            }

            # Add analysis result if available
            if analysis is not None:
                metadata["analysis"] = {
                    "gercek_hareket": analysis.gercek_hareket,
                    "guven_skoru": analysis.guven_skoru,
                    "degisiklik_aciklamasi": analysis.degisiklik_aciklamasi,
                    "tespit_edilen_nesneler": analysis.tespit_edilen_nesneler,
                    "tehdit_seviyesi": analysis.tehdit_seviyesi,
                    "onerilen_aksiyon": analysis.onerilen_aksiyon,
                    "detayli_analiz": analysis.detayli_analiz,
                    "processing_time": analysis.processing_time,
                }

            # Write metadata JSON
            metadata_path = screenshot_dir / "metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved screenshot set: {screenshot_id}")
            return screenshot_id

        except Exception as e:
            # Cleanup partial save on error
            if screenshot_dir.exists():
                shutil.rmtree(screenshot_dir)

            raise ScreenshotManagerError(
                f"Failed to save screenshot set: {e}",
                original_error=e
            )

    def get(self, screenshot_id: str) -> Optional[ScreenshotSet]:
        """
        Retrieve a screenshot set by ID.

        Args:
            screenshot_id: Screenshot set ID

        Returns:
            ScreenshotSet or None if not found

        Raises:
            ScreenshotManagerError: If load operation fails
        """
        screenshot_dir = self.storage_path / screenshot_id

        if not screenshot_dir.exists():
            logger.warning(f"Screenshot set not found: {screenshot_id}")
            return None

        try:
            # Load metadata
            metadata_path = screenshot_dir / "metadata.json"
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Load images
            before = None
            if metadata.get("has_before", False):
                before_path = screenshot_dir / "before.jpg"
                if before_path.exists():
                    before = cv2.imread(str(before_path))

            now = None
            if metadata.get("has_now", False):
                now_path = screenshot_dir / "now.jpg"
                if now_path.exists():
                    now = cv2.imread(str(now_path))

            after = None
            if metadata.get("has_after", False):
                after_path = screenshot_dir / "after.jpg"
                if after_path.exists():
                    after = cv2.imread(str(after_path))

            # Parse timestamp
            timestamp = datetime.fromisoformat(metadata["timestamp"])

            return ScreenshotSet(
                before=before,
                now=now,
                after=after,
                timestamp=timestamp
            )

        except Exception as e:
            raise ScreenshotManagerError(
                f"Failed to load screenshot set {screenshot_id}: {e}",
                original_error=e
            )

    def get_metadata(self, screenshot_id: str) -> Optional[ScreenshotMetadata]:
        """
        Retrieve metadata for a screenshot set.

        Args:
            screenshot_id: Screenshot set ID

        Returns:
            ScreenshotMetadata or None if not found
        """
        screenshot_dir = self.storage_path / screenshot_id
        metadata_path = screenshot_dir / "metadata.json"

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return ScreenshotMetadata(
                id=data["id"],
                timestamp=data["timestamp"],
                has_before=data["has_before"],
                has_now=data["has_now"],
                has_after=data["has_after"],
                analysis=data.get("analysis")
            )

        except Exception as e:
            logger.error(f"Failed to load metadata for {screenshot_id}: {e}")
            return None

    def list_all(self, limit: Optional[int] = None) -> List[ScreenshotMetadata]:
        """
        List all stored screenshot sets, newest first.

        Args:
            limit: Optional limit on number of results

        Returns:
            List of ScreenshotMetadata, sorted by timestamp (newest first)
        """
        metadata_list: List[ScreenshotMetadata] = []

        try:
            # Get all directories in storage path
            screenshot_dirs = [
                d for d in self.storage_path.iterdir()
                if d.is_dir()
            ]

            # Sort by directory name (timestamp-based) in descending order
            screenshot_dirs.sort(reverse=True)

            # Apply limit if specified
            if limit is not None:
                screenshot_dirs = screenshot_dirs[:limit]

            # Load metadata for each
            for screenshot_dir in screenshot_dirs:
                metadata = self.get_metadata(screenshot_dir.name)
                if metadata is not None:
                    metadata_list.append(metadata)

        except Exception as e:
            logger.error(f"Failed to list screenshots: {e}")

        return metadata_list

    def get_image_path(
        self,
        screenshot_id: str,
        image_type: str = "now"
    ) -> Optional[Path]:
        """
        Get the file path for a specific image in a screenshot set.

        Args:
            screenshot_id: Screenshot set ID
            image_type: Type of image ("before", "now", or "after")

        Returns:
            Path to image file or None if not found
        """
        screenshot_dir = self.storage_path / screenshot_id
        image_path = screenshot_dir / f"{image_type}.jpg"

        if image_path.exists():
            return image_path

        return None

    def delete(self, screenshot_id: str) -> bool:
        """
        Delete a screenshot set.

        Args:
            screenshot_id: Screenshot set ID

        Returns:
            True if deleted successfully, False otherwise
        """
        screenshot_dir = self.storage_path / screenshot_id

        if not screenshot_dir.exists():
            logger.warning(f"Cannot delete non-existent screenshot: {screenshot_id}")
            return False

        try:
            shutil.rmtree(screenshot_dir)
            logger.info(f"Deleted screenshot set: {screenshot_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete screenshot {screenshot_id}: {e}")
            return False

    def _count_stored(self) -> int:
        """Count number of stored screenshot sets."""
        try:
            return len([
                d for d in self.storage_path.iterdir()
                if d.is_dir()
            ])
        except Exception:
            return 0

    def _cleanup_oldest(self) -> None:
        """Remove oldest screenshot sets until under the limit."""
        try:
            # Get all directories sorted by name (oldest first)
            screenshot_dirs = sorted([
                d for d in self.storage_path.iterdir()
                if d.is_dir()
            ])

            # Calculate how many to remove
            current_count = len(screenshot_dirs)
            to_remove = current_count - self.config.max_stored + 1

            if to_remove <= 0:
                return

            # Remove oldest sets
            for i in range(min(to_remove, len(screenshot_dirs))):
                screenshot_dir = screenshot_dirs[i]
                try:
                    shutil.rmtree(screenshot_dir)
                    logger.info(f"Cleaned up old screenshot: {screenshot_dir.name}")
                except Exception as e:
                    logger.error(f"Failed to cleanup {screenshot_dir.name}: {e}")

        except Exception as e:
            logger.error(f"Failed to cleanup old screenshots: {e}")
