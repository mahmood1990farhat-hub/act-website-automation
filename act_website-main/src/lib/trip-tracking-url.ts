/**
 * Keep tracking on the backend selected for REST requests. The WebSocket route
 * is rooted at /ws (not below /api); never fall back to a different backend.
 * This selects an origin, not proof that an environment is isolated or ready.
 */
export function buildTripTrackingUrl(
	apiBaseUrl: string | undefined,
	tripId: string | number,
): string | null {
	if (
		typeof apiBaseUrl !== "string" ||
		!/^https?:\/\/[^/\\\s?#]+(?:\/|$)/i.test(apiBaseUrl) ||
		/[\\\s\u0000-\u001f\u007f?#]/.test(apiBaseUrl)
	) {
		return null;
	}

	if (
		(typeof tripId !== "string" && typeof tripId !== "number") ||
		(typeof tripId === "number" && !Number.isSafeInteger(tripId)) ||
		!/^\d+$/.test(String(tripId))
	) {
		return null;
	}

	try {
		const url = new URL(apiBaseUrl);
		if (
			(url.protocol !== "http:" && url.protocol !== "https:") ||
			!url.hostname ||
			url.username ||
			url.password
		) {
			return null;
		}

		url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
		url.pathname = `/ws/trips/${tripId}/tracking/`;
		return url.toString();
	} catch {
		return null;
	}
}
