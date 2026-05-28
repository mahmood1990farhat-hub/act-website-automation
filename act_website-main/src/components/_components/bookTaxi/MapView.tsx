"use client";
import React, { useEffect, useRef, useState } from "react";
import {
	GoogleMap,
	LoadScript,
	Polyline,
	Marker,
} from "@react-google-maps/api";
import { decode } from "@googlemaps/polyline-codec";

type Props = {
	routePolyline: string;
};

const containerStyle = {
	width: "100%",
	height: "500px",
	borderRadius: "8px",
};
const darkMapStyle = [
	{
		elementType: "geometry",
		stylers: [{ color: "#18181A" }],
	},
	{
		elementType: "labels.text.fill",
		stylers: [{ color: "#D0D1D1" }],
	},
	{
		elementType: "labels.text.stroke",
		stylers: [{ color: "#18181A" }],
	},
	{
		featureType: "administrative.country",
		elementType: "geometry.stroke",
		stylers: [{ color: "#4E504F" }],
	},
	{
		featureType: "administrative.land_parcel",
		elementType: "labels.text.fill",
		stylers: [{ color: "#AFB1B0" }],
	},
	{
		featureType: "administrative.province",
		elementType: "geometry.stroke",
		stylers: [{ color: "#4E504F" }],
	},
	{
		featureType: "landscape.man_made",
		elementType: "geometry.stroke",
		stylers: [{ color: "#2D2E2E" }],
	},
	{
		featureType: "landscape.natural",
		elementType: "geometry",
		stylers: [{ color: "#2D2E2E" }],
	},
	{
		featureType: "poi",
		elementType: "geometry",
		stylers: [{ color: "#18181A" }],
	},
	{
		featureType: "poi",
		elementType: "labels.text.fill",
		stylers: [{ color: "#AFB1B0" }],
	},
	{
		featureType: "poi",
		elementType: "labels.text.stroke",
		stylers: [{ color: "#18181A" }],
	},
	{
		featureType: "poi.park",
		elementType: "geometry.fill",
		stylers: [{ color: "#1F9254" }],
	},
	{
		featureType: "poi.park",
		elementType: "labels.text.fill",
		stylers: [{ color: "#D0D1D1" }],
	},
	{
		featureType: "road",
		elementType: "geometry",
		stylers: [{ color: "#4E504F" }],
	},
	{
		featureType: "road",
		elementType: "labels.text.fill",
		stylers: [{ color: "#D0D1D1" }],
	},
	{
		featureType: "road",
		elementType: "labels.text.stroke",
		stylers: [{ color: "#18181A" }],
	},
	{
		featureType: "road.highway",
		elementType: "geometry",
		stylers: [{ color: "#FFD100" }],
	},
	{
		featureType: "road.highway",
		elementType: "geometry.stroke",
		stylers: [{ color: "#878988" }],
	},
	{
		featureType: "road.highway",
		elementType: "labels.text.fill",
		stylers: [{ color: "#18181A" }],
	},
	{
		featureType: "road.highway",
		elementType: "labels.text.stroke",
		stylers: [{ color: "#FFD100" }],
	},
	{
		featureType: "transit",
		elementType: "labels.text.fill",
		stylers: [{ color: "#AFB1B0" }],
	},
	{
		featureType: "transit",
		elementType: "labels.text.stroke",
		stylers: [{ color: "#18181A" }],
	},
];
const MapView = ({ routePolyline }: Props) => {
	const mapRef = useRef<google.maps.Map | null>(null);
	const [path, setPath] = useState<google.maps.LatLngLiteral[]>([]);
	const [center, setCenter] = useState<google.maps.LatLngLiteral>({
		lat: 0,
		lng: 0,
	});

	useEffect(() => {
		if (routePolyline) {
			const decodedPath = decode(routePolyline, 5);
			const formattedPath = decodedPath.map(([lat, lng]) => ({ lat, lng }));
			setPath(formattedPath);
			if (formattedPath.length > 0) {
				const mid = Math.floor(formattedPath.length / 2);
				setCenter(formattedPath[mid]);
			}
		}
	}, [routePolyline]);
	const containerStyle = {
		width: "100%",
		height: "100%",

		borderRadius: "8px",
	};

	return (
		<GoogleMap
			mapContainerStyle={containerStyle}
			center={center}
			zoom={12}
			options={
				{
					// styles: darkMapStyle, // إذا كنت تستخدم الثيم الداكن
				}
			}
			onLoad={(map) => {
				mapRef.current = map;
				if (path.length > 0) {
					const bounds = new window.google.maps.LatLngBounds();
					path.forEach((point) => bounds.extend(point));
					map.fitBounds(bounds);
				}
			}}
		>
			{/* عرض المسار */}
			{path.length > 0 && (
				<Polyline
					path={path}
					options={{
						strokeColor: "#317daf",
						strokeOpacity: 1.0,
						strokeWeight: 4,
						geodesic: true,
					}}
				/>
			)}

			{path.length > 0 && (
				<Marker
					position={path[0]}
					icon={{
						url: "/images/start-icon.svg", // أيقونة البداية (مثلاً دائرة خضراء)
						scaledSize: new google.maps.Size(30, 30),
						anchor: new google.maps.Point(17, 17),
					}}
					label={{
						text: "Start",
						color: "white",
						fontWeight: "bold",
						fontSize: "6px",
					}}
				/>
			)}

			{/* النهاية */}
			{path.length > 1 && (
				<Marker
					position={path[path.length - 1]}
					icon={{
						url: "/images/end-icon.svg", // أيقونة النهاية (مثلاً علم أحمر)
						scaledSize: new google.maps.Size(30, 30),
						anchor: new google.maps.Point(17, 17),
					}}
					label={{
						text: "End",
						color: "white",
						fontWeight: "bold",
						fontSize: "6px",
					}}
				/>
			)}
		</GoogleMap>
	);
};

export default MapView;

// darkMapStyle هو الثيم الداكن الذي ناقشناه سابقاً
