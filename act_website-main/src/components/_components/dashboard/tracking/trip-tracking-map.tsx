"use client";

import { trackingStatusText, useTripTracking } from "@/hooks/use-trip-tracking";
import { GoogleMap, Marker, useLoadScript } from "@react-google-maps/api";

const containerStyle = {
	width: "100%",
	height: "400px",
};

export default function TripGoogleMap({ tripId, token, locale = "en" }: { tripId: string; token?: string; locale?: string }) {
	const { location, status } = useTripTracking(tripId, token);



	if (!location) {
		return (
			<div role="status" dir={locale === "ar" ? "rtl" : "ltr"} className="h-[400px] flex items-center justify-center border">
				{trackingStatusText(status, locale)}
			</div>
		);
	}

	return (
		<div className="space-y-2">
			<div className="flex items-center gap-2">
				<div
					className={`w-3 h-3 rounded-full ${
						status === "live" ? "bg-green-500" : "bg-red-500"
					}`}
				/>

				<span role="status" dir={locale === "ar" ? "rtl" : "ltr"} className="text-sm">
					{trackingStatusText(status, locale)}
				</span>
			</div>

			<GoogleMap mapContainerStyle={containerStyle} center={location} zoom={15}>
				<Marker position={location} />
			</GoogleMap>
		</div>
	);
}
