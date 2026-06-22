"""SharePoint client for online and on-premise document ingestion."""

from __future__ import annotations

import logging

from config import Settings

logger = logging.getLogger(__name__)


class SharePointClient:
    """Download files from SharePoint using credentials from Settings."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.context = None

    def connect(self) -> bool:
        """Connect to SharePoint Online or on-premise based on the configured URL."""

        missing = self._missing_settings()
        if missing:
            logger.error("Missing SharePoint configuration values: %s", ", ".join(missing))
            return False
        try:
            from office365.runtime.auth.user_credential import UserCredential
            from office365.sharepoint.client_context import ClientContext

            auth_type = "Online" if self.is_sharepoint_online else "On-Premise"
            if not self.is_sharepoint_online:
                logger.warning(
                    "Connecting to non-sharepoint.com URL with username/password auth. "
                    "If your on-premise SharePoint requires NTLM/Kerberos, configure an approved internal auth adapter."
                )
            self.context = ClientContext(self.settings.sharepoint_url).with_credentials(
                UserCredential(self.settings.sharepoint_username, self.settings.sharepoint_password)
            )
            self.context.web.get().execute_query()
            logger.info("Connected to SharePoint %s at %s", auth_type, self.settings.sharepoint_url)
            return True
        except ImportError as exc:
            logger.error("SharePoint dependency is unavailable: %s", exc)
        except Exception as exc:
            logger.error("SharePoint connection failed: %s", exc)
        return False

    def list_files(self, library_name: str) -> list[str]:
        """Return server-relative file URLs in a SharePoint document library."""

        if self.context is None and not self.connect():
            return []
        try:
            library = self.context.web.lists.get_by_title(library_name)
            items = library.items.select(["FileRef", "FileSystemObjectType"]).get().execute_query()
            return [
                str(item.properties["FileRef"])
                for item in items
                if item.properties.get("FileRef") and item.properties.get("FileSystemObjectType") in (0, "0", None)
            ]
        except Exception as exc:
            logger.error("Could not list files in SharePoint library %s: %s", library_name, exc)
            return []

    def download_file(self, file_url: str) -> bytes:
        """Download one SharePoint file as bytes, returning empty bytes on failure."""

        if self.context is None and not self.connect():
            return b""
        try:
            from office365.sharepoint.files.file import File

            response = File.open_binary(self.context, file_url)
            return bytes(response.content)
        except Exception as exc:
            logger.error("Could not download SharePoint file %s: %s", file_url, exc)
            return b""

    @property
    def is_sharepoint_online(self) -> bool:
        """Return True when the configured URL appears to be SharePoint Online."""

        return ".sharepoint.com" in self.settings.sharepoint_url.lower()

    def _missing_settings(self) -> list[str]:
        missing: list[str] = []
        if not self.settings.sharepoint_url:
            missing.append("SHAREPOINT_URL")
        if not self.settings.sharepoint_username:
            missing.append("SHAREPOINT_USERNAME")
        if not self.settings.sharepoint_password:
            missing.append("SHAREPOINT_PASSWORD")
        if not self.settings.sharepoint_library:
            missing.append("SHAREPOINT_LIBRARY")
        return missing
