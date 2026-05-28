"use client";

import { useTripTracking } from "@/hooks/use-trip-tracking";
import { GoogleMap, Marker, useLoadScript } from "@react-google-maps/api";

const containerStyle = {
	width: "100%",
	height: "400px",
};

export default function TripGoogleMap({ tripId }: { tripId: string }) {
	const { location, connected } = useTripTracking(tripId);



	if (!location) {
		return (
			<div className="h-[400px] flex items-center justify-center border">
				Waiting for driver location...
			</div>
		);
	}

	return (
		<div className="space-y-2">
			<div className="flex items-center gap-2">
				<div
					className={`w-3 h-3 rounded-full ${
						connected ? "bg-green-500" : "bg-red-500"
					}`}
				/>

				<span className="text-sm">
					{connected ? "Live Tracking" : "Disconnected"}
				</span>
			</div>

			<GoogleMap mapContainerStyle={containerStyle} center={location} zoom={15}>
				<Marker position={location} />
			</GoogleMap>
		</div>
	);
}
