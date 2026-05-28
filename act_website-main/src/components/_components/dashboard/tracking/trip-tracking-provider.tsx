import React, { useEffect, useRef, useState } from "react";
import { GoogleMap, Marker, Polyline } from "@react-google-maps/api";
import { decode } from "@googlemaps/polyline-codec";

type Props = {
	tripId: string;
	routePolyline: string;
};

const MapViewtest = ({ tripId, routePolyline }: Props) => {
	const mapRef = useRef<google.maps.Map | null>(null);
	const wsRef = useRef<WebSocket | null>(null);

	const [path, setPath] = useState<google.maps.LatLngLiteral[]>([]);
	const [currentLocation, setCurrentLocation] =
		useState<google.maps.LatLngLiteral | null>(null);
	const [heading, setHeading] = useState<number>(0);
	const [traveledPath, setTraveledPath] = useState<google.maps.LatLngLiteral[]>(
		[],
	);
	const lastCenterRef = useRef<google.maps.LatLngLiteral | null>(null);
	
	const targetLocationRef = useRef<google.maps.LatLngLiteral | null>(null);
	const targetHeadingRef = useRef<number | null>(null);
	const animationFrameRef = useRef<number | null>(null);

	const lerpAngle = (start: number, end: number, t: number) => {
		let diff = end - start;
		if (diff > 180) diff -= 360;
		if (diff < -180) diff += 360;
		return start + diff * t;
	};

	// فك تشفير المسار الكامل
	useEffect(() => {
		if (routePolyline) {
			const decoded = decode(routePolyline, 5);
			const formattedPath = decoded.map(([lat, lng]) => ({ lat, lng }));
			setPath(formattedPath);

			if (formattedPath.length > 0) {
				const mid = Math.floor(formattedPath.length / 2);
				lastCenterRef.current = formattedPath[mid];
				setCurrentLocation(formattedPath[0]);
				setTraveledPath([formattedPath[0]]);
			}
		}
	}, [routePolyline]);

	// فتح WebSocket لتلقي تحديثات الموقع
	useEffect(() => {
		wsRef.current = new WebSocket(
			`wss://act-backend.horizontechco.com/ws/trips/${tripId}/tracking/`,
		);

		wsRef.current.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				if (data.location) {
					const { lat, lng, heading: h } = data.location;
					if (lat && lng) {
						targetLocationRef.current = { lat, lng };
						targetHeadingRef.current = h !== null ? h : null;

						// أضف النقطة الجديدة للمسار المقطوع
						setTraveledPath((prev) => [...prev, { lat, lng }]);
					}
				}
			} catch (err) {
				console.error("WebSocket error:", err);
			}
		};

		wsRef.current.onclose = () => console.log("WebSocket closed");
		wsRef.current.onerror = (err) => console.error("WebSocket error:", err);

		return () => wsRef.current?.close();
	}, [tripId]);

	// حرك
	useEffect(() => {
		const speed = 0.02; // سرعة الحركة
		const animate = () => {
			if (currentLocation && targetLocationRef.current) {
				const dx = targetLocationRef.current.lat - currentLocation.lat;
				const dy = targetLocationRef.current.lng - currentLocation.lng;
				const distance = Math.hypot(dx, dy);
				const step = Math.min(distance, speed);

				if (distance > 0.00001) {
					const newLat = currentLocation.lat + (dx / distance) * step;
					const newLng = currentLocation.lng + (dy / distance) * step;
					setCurrentLocation({ lat: newLat, lng: newLng });

					if (targetHeadingRef.current !== null) {
						setHeading((prev) =>
							lerpAngle(prev, targetHeadingRef.current!, 0.1),
						);
					} else {
						const angle = Math.atan2(dy, dx) * (180 / Math.PI);
						setHeading((prev) => lerpAngle(prev, angle, 0.1));
					}

					// متابعة المركز بسلاسة
					if (
						!lastCenterRef.current ||
						Math.hypot(
							newLat - lastCenterRef.current.lat,
							newLng - lastCenterRef.current.lng,
						) > 0.0001
					) {
						mapRef.current?.panTo({ lat: newLat, lng: newLng });
						lastCenterRef.current = { lat: newLat, lng: newLng };
					}
				}
			} else if (!currentLocation && targetLocationRef.current) {
				setCurrentLocation(targetLocationRef.current);
				lastCenterRef.current = targetLocationRef.current;
			}

			animationFrameRef.current = requestAnimationFrame(animate);
		};

		animationFrameRef.current = requestAnimationFrame(animate);
		return () => {
			if (animationFrameRef.current) {
				cancelAnimationFrame(animationFrameRef.current);
			}
		};
	}, [currentLocation]);

	return (
		<GoogleMap
			mapContainerStyle={{
				width: "100%",
				height: "100%",

				borderRadius: "8px",
			}}
			center={currentLocation || { lat: 0, lng: 0 }}
			zoom={15}
			onLoad={(map) => {
				mapRef.current = map;
				if (currentLocation) map.panTo(currentLocation);
			}}
		>
			{/* المسار الكامل */}
			{path.length > 0 && (
				<Polyline
					path={path}
					options={{
						strokeColor: "#317daf",
						strokeOpacity: 0.5,
						strokeWeight: 4,
						geodesic: true,
					}}
				/>
			)}
			{/* البداية */}
			{path.length > 0 && (
				<Marker
					position={path[0]}
					icon={{
						url: "/images/start-icon.svg", // أيقونة البداية (مثلاً دائرة خضراء)
						scaledSize: new google.maps.Size(35, 35),
						anchor: new google.maps.Point(17, 17),
					}}
					label={{
						text: "Start",
						color: "white",
						fontWeight: "bold",
						fontSize: "12px",
					}}
				/>
			)}

			{/* النهاية */}
			{path.length > 1 && (
				<Marker
					position={path[path.length - 1]}
					icon={{
						url: "/images/end-icon.svg", // أيقونة النهاية (مثلاً علم أحمر)
						scaledSize: new google.maps.Size(35, 35),
						anchor: new google.maps.Point(17, 17),
					}}
					label={{
						text: "End",
						color: "white",
						fontWeight: "bold",
						fontSize: "12px",
					}}
				/>
			)}
			{/* المسار المقطوع */}
			{/* {traveledPath.length > 1 && (
				<Polyline
					path={traveledPath}
					options={{
						strokeColor: "#5E84B3",
						strokeOpacity: 1,
						strokeWeight: 5,
						geodesic: true,
					}}
				/>
			)} */}

			{/* السيارة */}
			{currentLocation && (
				<Marker
					position={currentLocation}
					icon={{
						url: "/images/car2.svg",
						scaledSize: new google.maps.Size(40, 40),
						anchor: new google.maps.Point(20, 20),
						rotation: heading,
					}}
				/>
			)}
		</GoogleMap>
	);
};

export default MapViewtest;
