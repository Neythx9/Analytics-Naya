"""CSV and ZIP export helpers for the Streamlit dashboard."""

from __future__ import annotations

import io
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)


class ExportManager:
    """Manage CSV and ZIP exports for dashboard DataFrames."""

    def __init__(self, export_dir: str) -> None:
        """Store the export directory and create it if needed.

        Args:
            export_dir: Directory where exported files are written.

        Returns:
            None.
        """

        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def dataframe_to_csv_bytes(self, df: pd.DataFrame) -> bytes:
        """Convert a DataFrame to UTF-8 encoded CSV bytes.

        Args:
            df: The DataFrame to convert.

        Returns:
            UTF-8 encoded CSV bytes.
        """

        try:
            csv_text = df.head(0).to_csv(index=False) if df.empty else df.to_csv(index=False)
            return csv_text.encode("utf-8")
        except Exception:
            logger.exception("Failed to convert DataFrame to CSV bytes.")
            raise

    def generate_filename(self, prefix: str, guild_id: str, days: int) -> str:
        """Generate a timestamped CSV filename.

        Args:
            prefix: Filename prefix.
            guild_id: Discord guild identifier.
            days: Rolling window size in days.

        Returns:
            A filename in the format ``{prefix}_{guild_id}_{days}d_{YYYYMMDD_HHMMSS}.csv``.
        """

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{guild_id}_{days}d_{timestamp}.csv"

    def save_to_disk(self, df: pd.DataFrame, filename: str) -> Path:
        """Save a DataFrame to disk as CSV and return the destination path.

        Args:
            df: DataFrame to save.
            filename: File name relative to the export directory.

        Returns:
            The full path to the saved file.
        """

        path = self.export_dir / filename
        try:
            path.write_bytes(self.dataframe_to_csv_bytes(df))
            logger.info("Saved export to %s", path)
            return path
        except Exception:
            logger.exception("Failed to save export to disk: %s", path)
            raise

    def dataframes_to_zip_bytes(self, files: dict[str, pd.DataFrame]) -> bytes:
        """Bundle multiple DataFrames into a ZIP archive containing CSV files.

        Args:
            files: Mapping of archive file names to DataFrames.

        Returns:
            ZIP archive bytes.
        """

        try:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
                for filename, frame in files.items():
                    archive.writestr(filename, self.dataframe_to_csv_bytes(frame))
            return buffer.getvalue()
        except Exception:
            logger.exception("Failed to build ZIP archive bytes.")
            raise

    def get_export_button(self, df: pd.DataFrame, label: str, filename: str) -> None:
        """Render a Streamlit CSV download button for a DataFrame.

        Args:
            df: DataFrame to export.
            label: Visible button label.
            filename: Download filename.

        Returns:
            None.
        """

        try:
            st.download_button(
                label=f"⬇️ {label}",
                data=self.dataframe_to_csv_bytes(df),
                file_name=filename,
                mime="text/csv",
                disabled=df.empty,
            )
        except Exception:
            logger.exception("Failed to render export button for %s", filename)
            st.error("Failed to prepare export.")

    def get_zip_export_button(self, files: dict[str, pd.DataFrame], label: str, filename: str) -> None:
        """Render a Streamlit download button for a ZIP archive of CSV files.

        Args:
            files: Mapping of archive file names to DataFrames.
            label: Visible button label.
            filename: Download filename.

        Returns:
            None.
        """

        try:
            st.download_button(
                label=f"⬇️ {label}",
                data=self.dataframes_to_zip_bytes(files),
                file_name=filename,
                mime="application/zip",
                disabled=not files,
            )
        except Exception:
            logger.exception("Failed to render ZIP export button for %s", filename)
            st.error("Failed to prepare export.")