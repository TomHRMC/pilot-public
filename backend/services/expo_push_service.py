"""
Expo Push Notifications API integration service.

FIND-078/A93: Real Expo Push Notifications API dispatch
Replaces stub implementation with full integration to exp.host API.

This service handles:
- Valid token dispatch to Expo API
- Deep link payload handling
- Device not registered token removal
- Rate limit retry handling
- Invalid credentials operator alert
- Access token management
"""

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Expo Push Notifications API endpoint
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


# ============================================================================
# Exception Classes
# ============================================================================


class ExpoDeviceNotRegisteredError(Exception):
    """Device token is stale or invalid per Expo API."""

    pass


class ExpoMessageRateExceededError(Exception):
    """Expo API rate limit reached."""

    pass


class ExpoInvalidCredentialsError(Exception):
    """EXPO_ACCESS_TOKEN is invalid or missing."""

    pass


# ============================================================================
# Result Dataclass
# ============================================================================


@dataclass
class ExpoPushResult:
    """Result from send_expo_push() function."""

    status: str  # "sent" or "error"
    expo_ticket_id: str | None = None
    error_message: str | None = None
    retryable: bool = False
    http_status: int | None = None


# ============================================================================
# Main Push Service Function
# ============================================================================


def send_expo_push(
    expo_token: str,
    title: str | None,
    body: str,
    data: dict[str, Any] | None = None,
    access_token: str | None = None,
) -> ExpoPushResult:
    """
    Send a push notification to a single device via Expo API.

    Args:
        expo_token: Device token (e.g., "ExponentPushToken[...]")
        title: Notification title (optional)
        body: Notification body text
        data: Custom data payload (typically includes deep_link_target)
        access_token: Expo API access token (optional)

    Returns:
        ExpoPushResult with status, ticket_id, and error details

    Raises:
        ExpoDeviceNotRegisteredError: If device token is stale
        ExpoMessageRateExceededError: If rate limit exceeded
        ExpoInvalidCredentialsError: If access_token is invalid
    """
    try:
        # Build headers with authorization
        headers = {"Content-Type": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        # Build payload per Expo spec
        payload = {
            "to": expo_token,
            "title": title,
            "body": body,
            "sound": "default",
            "priority": "high",
        }
        if data:
            payload["data"] = data

        # Make HTTP request
        with httpx.Client() as client:
            response = client.post(EXPO_PUSH_URL, json=payload, headers=headers)

        # Check for HTTP errors
        if response.status_code >= 500:
            # Server error — retryable
            return ExpoPushResult(
                status="error",
                error_message=f"Expo API server error: HTTP {response.status_code}",
                retryable=True,
                http_status=response.status_code,
            )

        if response.status_code >= 400:
            # Client error (non-retryable)
            return ExpoPushResult(
                status="error",
                error_message=f"Expo API client error: HTTP {response.status_code}",
                retryable=False,
                http_status=response.status_code,
            )

        # Parse successful response
        try:
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to parse Expo response: {e}")
            return ExpoPushResult(
                status="error",
                error_message="Failed to parse Expo response",
                retryable=False,
                http_status=response.status_code,
            )

        # Check data.errors array (Expo puts errors in top-level errors)
        if data.get("errors"):
            error_item = data["errors"][0]
            error_code = error_item.get("code", "UnknownError")

            if error_code == "InvalidCredentials":
                raise ExpoInvalidCredentialsError(
                    f"Invalid access token: {error_item.get('message')}"
                )
            elif error_code == "MessageRateExceeded":
                raise ExpoMessageRateExceededError("Expo rate limit exceeded")
            else:
                # Generic error
                return ExpoPushResult(
                    status="error",
                    error_message=f"Expo error: {error_item.get('message')}",
                    retryable=False,
                    http_status=response.status_code,
                )

        # Check data array (individual receipt errors)
        if "data" in data and isinstance(data["data"], list):
            receipt = data["data"][0] if data["data"] else None

            if receipt:
                if receipt.get("status") == "ok":
                    # Success
                    return ExpoPushResult(
                        status="sent",
                        expo_ticket_id=receipt.get("id"),
                        error_message=None,
                        retryable=False,
                        http_status=response.status_code,
                    )
                else:
                    # Error in receipt
                    details = receipt.get("details", {})
                    error_code = details.get("error", "UnknownError")

                    if error_code == "DeviceNotRegistered":
                        raise ExpoDeviceNotRegisteredError(
                            f"Device not found: {details.get('error_description')}"
                        )
                    elif error_code == "MessageRateExceeded":
                        raise ExpoMessageRateExceededError("Expo rate limit exceeded")
                    elif error_code == "InvalidCredentials":
                        raise ExpoInvalidCredentialsError(
                            f"Invalid credentials: {details.get('error_description')}"
                        )
                    else:
                        # Generic error
                        return ExpoPushResult(
                            status="error",
                            error_message=details.get(
                                "error_description", "Unknown error"
                            ),
                            retryable=False,
                            http_status=response.status_code,
                        )

        # Fallback if response structure is unexpected
        logger.warning(f"Unexpected Expo response structure: {data}")
        return ExpoPushResult(
            status="error",
            error_message="Unexpected Expo response format",
            retryable=False,
            http_status=response.status_code,
        )

    except ExpoDeviceNotRegisteredError:
        raise
    except ExpoMessageRateExceededError:
        raise
    except ExpoInvalidCredentialsError:
        raise
    except Exception as e:
        logger.error(f"Error sending Expo push: {e}")
        return ExpoPushResult(
            status="error",
            error_message=str(e),
            retryable=True,
            http_status=None,
        )
