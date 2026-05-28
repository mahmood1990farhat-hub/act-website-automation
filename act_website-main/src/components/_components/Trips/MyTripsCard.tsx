import React, { useState } from "react";
import { FaCarSide, FaRoute, FaCalendarAlt } from "react-icons/fa";
import { TiLocation } from "react-icons/ti";
import { HiTrash } from "react-icons/hi";
import { BiEditAlt } from "react-icons/bi";
import { MdAccessTime } from "react-icons/md";
import GlobalModal from "../GlobalModal";
import MapView from "../bookTaxi/MapView";
import { postData } from "@/lib/api/postData";
import { Locale } from "../../../../i18n.config";
import { Button } from "@/components/ui/button";
import { IoChatbubbleEllipsesSharp } from "react-icons/io5";
import MapViewtest from "../dashboard/tracking/trip-tracking-provider";

type typeProps = {
	data: any;
	trans: any;
	token?: string;
	locale: Locale;
	tripCardTrans?: any;
};

// Status color helper
const getStatusColor = (status: string) => {
	const statusLower = status.toLowerCase();
	switch (statusLower) {
		case "pending":
			return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
		case "accepted":
			return "bg-blue-500/20 text-blue-400 border-blue-500/30";
		case "active":
			return "bg-green-500/20 text-green-400 border-green-500/30";
		case "driver_on_the_way":
			return "bg-cyan-500/20 text-cyan-400 border-cyan-500/30";
		case "completed":
			return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
		case "cancelled":
			return "bg-red-500/20 text-red-400 border-red-500/30";
		default:
			return "bg-primary/20 text-primary border-primary/30";
	}
};

export default function MyTripsCard({
	data,
	trans,
	token,
	locale,
	tripCardTrans,
}: typeProps) {
	const [openModal, setOpenModal] = useState(false);
	const [openDetails, setOpenDetails] = useState(false);

	const CancelTrip = async () => {
		try {
			const res = await postData({
				endpoint: `/api/trips/${data.id}/cancel/`,
				token: token,
				queryParams: {
					loacle: locale,
				},
			});
			setOpenModal(false);
		} catch (error) {}
	};
	console.log(data);

	return (
		<>
			<div
				className="group relative bg-foreground/40 backdrop-blur-sm border border-muted/20 rounded-xl p-4 md:p-5
                   transition-all duration-300 hover:border-primary/50 hover:shadow-lg hover:shadow-primary/10"
			>
				{/* Header Section */}
				<div className="flex items-start justify-between mb-4">
					<div className="flex-1">
						<div className="flex items-center gap-2 mb-1">
							<span className="text-gray-400 text-xs md:text-sm font-medium">
								{tripCardTrans?.tripId || "Trip ID:"}
							</span>
							<h1 className="text-base md:text-lg font-bold text-white">
								#{data.id}
							</h1>
						</div>
						<div className="flex items-center gap-2 text-gray-300 text-xs md:text-sm">
							<FaCalendarAlt className="text-primary" />
							<span>{data.trip_date}</span>
						</div>
					</div>

					{/* Status Badge */}
					<div
						className={`px-3 py-1.5 rounded-lg border font-semibold text-xs md:text-sm ${getStatusColor(data.status)}`}
					>
						{tripCardTrans?.statusLabels?.[data.status] || data.status}
					</div>
				</div>

				{/* Trip Details Grid */}
				<div className="grid md:grid-cols-2 gap-3 md:gap-4 mb-4">
					{/* Distance */}
					<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
						<div className="flex items-center gap-2 mb-1">
							<FaRoute className="text-primary text-sm" />
							<span className="text-gray-400 text-xs font-medium">
								{tripCardTrans?.distance || "Distance"}
							</span>
						</div>
						<p className="text-white font-semibold text-sm md:text-base">
							{data.distance_miles.toFixed(2)}{" "}
							{locale === "ar" ? "ميل" : "Mile"}
						</p>
					</div>

					{/* Duration */}
					<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
						<div className="flex items-center gap-2 mb-1">
							<MdAccessTime className="text-primary text-sm" />
							<span className="text-gray-400 text-xs font-medium">
								{tripCardTrans?.duration || "Duration"}
							</span>
						</div>
						<p className="text-white font-semibold text-sm md:text-base">
							{data.expected_trip_duration_minutes || "0"}
						</p>
					</div>
				</div>

				{/* Trip Details Drviver Grid */}
				<div className="grid md:grid-cols-2 gap-3 md:gap-4 mb-4">
					<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
						<div className="flex items-center gap-2 mb-1">
							<span className="text-gray-400 text-xs font-medium">
								{tripCardTrans?.name_of_driver || "Distance"}
							</span>
						</div>
						<p className="text-white font-semibold text-sm md:text-base">
							{data?.guest_driver_name ?? data?.driver_info?.first_name ??"-"}
						</p>
					</div>

					<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
						<div className="flex items-center gap-2 mb-1">
							<span className="text-gray-400 text-xs font-medium">
								{tripCardTrans?.phone_of_driver || "Duration"}
							</span>
						</div>
						<p className="text-white font-semibold text-sm md:text-base">
							{data?.guest_driver_phone || "-"}
						</p>
					</div>
				</div>
			{data?.vehicle_info &&
					<div className="border-t border-muted/20 pt-4 mb-4 border-b">
					<div className="text-lg font-semibold mb-1">
						{tripCardTrans.carInfo}
					</div>
					<div className="grid md:grid-cols-2 gap-3 md:gap-4 mb-4 ">
							{data?.vehicle_info?.model && (
							<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
								<div className="flex items-center gap-2 mb-1">
									<span className="text-gray-400 text-xs font-medium">
										{tripCardTrans?.model || "Model"}
									</span>
								</div>
								<p className="text-white font-semibold text-sm md:text-base">
									{data?.vehicle_info?.model || "-"}
								</p>
							</div>
						)}
				
						{data?.vehicle_info?.brand && (
							<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
								<div className="flex items-center gap-2 mb-1">
									<span className="text-gray-400 text-xs font-medium">
										{tripCardTrans?.brand || "Brand"}
									</span>
								</div>
								<p className="text-white font-semibold text-sm md:text-base">
									{data?.vehicle_info?.brand || "-"}
								</p>
							</div>
						)}
						{data?.vehicle_info?.registration_number && (
							<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
								<div className="flex items-center gap-2 mb-1">
									<span className="text-gray-400 text-xs font-medium">
										{tripCardTrans?.registrationNumber || "Registration Number"}
									</span>
								</div>
								<p className="text-white font-semibold text-sm md:text-base">
									{data?.vehicle_info?.registration_number}
								</p>
							</div>
						)}
						{data?.vehicle_info?.vehicle_type && (
							<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
								<div className="flex items-center gap-2 mb-1">
									<span className="text-gray-400 text-xs font-medium">
										{tripCardTrans?.brand || "Brand"}
									</span>
								</div>
								<p className="text-white font-semibold text-sm md:text-base">
									{data?.vehicle_info?.vehicle_type?.[`name_${locale}`] || "-"}
								</p>
							</div>
						)}
						{data?.vehicle_info?.year && (
							<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
								<div className="flex items-center gap-2 mb-1">
									<span className="text-gray-400 text-xs font-medium">
										{tripCardTrans?.year || "Year"}
									</span>
								</div>
								<p className="text-white font-semibold text-sm md:text-base">
									{data?.vehicle_info?.year || "-"}
								</p>
							</div>
						)}
					
								{data?.vehicle_info?.color && (
							<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
								<div className="flex items-center gap-2 mb-1">
									<span className="text-gray-400 text-xs font-medium">
										{tripCardTrans?.color || "Color"}
									</span>
								</div>
								<p className="text-white font-semibold text-sm md:text-base">
									{data?.vehicle_info?.color || "-"}
								</p>
							</div>
						)}
								{data?.vehicle_info?.additional_notes && (
							<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
								<div className="flex items-center gap-2 mb-1">
									<span className="text-gray-400 text-xs font-medium">
										{tripCardTrans?.additional_notes || "additional_notes"}
									</span>
								</div>
								<p className="text-white font-semibold text-sm md:text-base">
									{data?.vehicle_info?.additional_notes || "-"}
								</p>
							</div>
						)}
					</div>
				</div>
			}

				{/* Destination */}
				<div className="bg-background/30 rounded-lg p-3 border border-muted/10 mb-4">
					<div className="flex items-center gap-2 mb-1">
						<TiLocation className="text-primary text-base" />
						<span className="text-gray-400 text-xs font-medium">
							{tripCardTrans?.dropoff || "Drop-off"}
						</span>
					</div>
					<p className="text-white font-medium text-sm md:text-base truncate">
						{data.dropoff_str || "-"}
					</p>
				</div>
				<div className="bg-background/30 rounded-lg p-3 border border-muted/10 mb-4">
					<div className="flex items-center gap-2 mb-1">
						<TiLocation className="text-primary text-base" />
						<span className="text-gray-400 text-xs font-medium">
							{tripCardTrans?.pickup || "Pickup"}
						</span>
					</div>
					<p className="text-white font-medium text-sm md:text-base truncate">
						{data.pickup_str || "-"}
					</p>
				</div>

				{/* Footer - Price and Actions */}
				<div className="flex flex-col gap-3 pt-3 border-t border-muted/10">
					{/* Price */}
					<div className="flex items-baseline gap-1">
						<h3 className="text-2xl md:text-3xl font-bold text-primary">
							£{data.cost}
						</h3>
						<span className="text-gray-400 text-xs">
							{tripCardTrans?.gbp || "GBP"}
						</span>
					</div>

					{/* Action Buttons - Centered */}
					<div className="flex items-center justify-center gap-3 w-full">
						<button
							onClick={(e) => {
								e.stopPropagation();
								setOpenDetails(true);
							}}
							className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg 
                       bg-primary/10 hover:bg-primary/20 border border-primary/30 
                       text-primary font-semibold text-sm transition-all duration-200
                       hover:scale-102 active:scale-95"
						>
							<svg
								className="w-4 h-4"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeWidth={2}
									d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
								/>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeWidth={2}
									d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
								/>
							</svg>
							<span className="max-sm:hidden">
								{tripCardTrans?.seeDetails || "See Details"}
							</span>
							<span className="sm:hidden">
								{tripCardTrans?.details || "Details"}
							</span>
						</button>

						{(data.status === "pending" || data.status === "accepted") && (
							<button
								onClick={(e) => {
									e.stopPropagation();
									setOpenModal(true);
								}}
								className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg 
                         bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 
                         text-red-400 font-semibold text-sm transition-all duration-200
                         hover:scale-105 active:scale-95"
								title="Cancel Trip"
							>
								<HiTrash className="text-lg" />
								<span className="max-sm:hidden">
									{tripCardTrans?.cancel || "Cancel"}
								</span>
							</button>
						)}
					</div>
				</div>
			</div>

			{/* Delete Confirmation Modal */}
			<GlobalModal isOpen={openModal} onClose={() => setOpenModal(false)}>
				<div className="flex items-center flex-col gap-5 text-center p-2">
					{/* Icon */}
					<div className="bg-red-500/10 p-5 rounded-full">
						<HiTrash className="text-red-400 text-5xl" />
					</div>

					{/* Title */}
					<h1 className="text-white text-xl md:text-2xl font-bold">
						{trans.title}
					</h1>

					{/* Description */}
					<p className="text-gray-300 text-sm md:text-base max-w-md">
						{trans.desc}
					</p>

					{/* Action Buttons */}
					<div className="w-full flex flex-col sm:flex-row items-center gap-3 mt-2">
						<Button
							onClick={() => setOpenModal(false)}
							variant="secondary"
							className="w-full sm:w-1/2  md:text-lg py-6 border-2 border-muted "
						>
							{trans.btuCancel}
						</Button>
						<Button
							onClick={CancelTrip}
							className="w-full sm:w-1/2 text-base md:text-lg py-6 bg-red-600 hover:bg-red-700"
						>
							{trans.btuConfirm}
						</Button>
					</div>
				</div>
			</GlobalModal>

			{/* Trip Details Modal */}
			{openDetails && (
				<div
					onClick={() => setOpenDetails(false)}
					className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
				>
					<div
						onClick={(e) => e.stopPropagation()}
						className="bg-foreground/95 backdrop-blur-md border border-primary/20 rounded-2xl w-full max-w-5xl 
                     shadow-2xl shadow-primary/10 max-h-[90vh] overflow-hidden flex flex-col"
					>
						{/* Header */}
						<div className="bg-gradient-to-r from-primary/10 to-accent/10 border-b border-muted/20 px-6 py-5">
							<h2 className="text-2xl md:text-3xl font-bold text-center">
								{tripCardTrans?.tripDetails ? (
									<>
										<span className="text-primary">
											{tripCardTrans.tripDetails.split(" ")[0]}
										</span>{" "}
										<span className="text-white">
											{tripCardTrans.tripDetails.split(" ").slice(1).join(" ")}
										</span>
									</>
								) : (
									<>
										<span className="text-primary">Trip</span>{" "}
										<span className="text-white">Details</span>
									</>
								)}
							</h2>
							<p className="text-center text-gray-300 text-sm mt-1">
								{tripCardTrans?.tripId || "Trip ID:"} #{data.id}
							</p>
						</div>

						{/* Content */}
						<div className="flex-1 overflow-y-auto p-4 md:p-6">
							<div className="flex flex-col lg:flex-row gap-6 h-full">
								{/* Left Side - Details */}
								<div className="lg:w-1/2 space-y-4">
									{/* Status Badge */}
									<div className="flex justify-center lg:justify-start">
										<div
											className={`px-4 py-2 rounded-lg border font-semibold ${getStatusColor(data.status)}`}
										>
											{tripCardTrans?.status || "Status:"}{" "}
											{tripCardTrans?.statusLabels?.[data.status] ||
												data.status}
										</div>
									</div>

									{/* Details Grid */}
									<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
										{/* Date */}
										<div className="bg-background/30 rounded-lg p-4 border border-muted/10">
											<div className="flex items-center gap-2 mb-2">
												<FaCalendarAlt className="text-primary" />
												<span className="text-gray-400 text-sm font-medium">
													{tripCardTrans?.date || "Date"}
												</span>
											</div>
											<p className="text-white font-semibold">
												{data.trip_date}
											</p>
										</div>

										{/* Distance */}
										<div className="bg-background/30 rounded-lg p-4 border border-muted/10">
											<div className="flex items-center gap-2 mb-2">
												<FaRoute className="text-primary" />
												<span className="text-gray-400 text-sm font-medium">
													{tripCardTrans?.distance || "Distance"}
												</span>
											</div>
											<p className="text-white font-semibold">
												{(data.distance_miles * 1.61).toFixed(2)} km
											</p>
										</div>

										{/* Duration */}
										<div className="bg-background/30 rounded-lg p-4 border border-muted/10">
											<div className="flex items-center gap-2 mb-2">
												<MdAccessTime className="text-primary" />
												<span className="text-gray-400 text-sm font-medium">
													{tripCardTrans?.duration || "Duration"}
												</span>
											</div>
											<p className="text-white font-semibold">
												{data.expected_trip_duration_minutes || "0"} m
											</p>
										</div>

										<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
											<div className="flex items-center gap-2 mb-1">
												<span className="text-gray-400 text-xs font-medium">
													{tripCardTrans?.name_of_driver || "Distance"}
												</span>
											</div>
											<p className="text-white font-semibold text-sm md:text-base">
												{data?.guest_driver_name ??
													`${data?.driver_info?.first_name} ${data?.driver_info?.last_name}`}
											</p>
										</div>

										<div className="bg-background/30 rounded-lg p-3 border border-muted/10">
											<div className="flex items-center gap-2 mb-1">
												<span className="text-gray-400 text-xs font-medium">
													{tripCardTrans?.phone_of_driver || "Duration"}
												</span>
											</div>
											<p className="text-white font-semibold text-sm md:text-base">
												{data?.driver_info?.phone_number || "-"}
											</p>
										</div>

										{/* Cost */}
										<div className="bg-background/30 rounded-lg p-4 border border-muted/10">
											<div className="flex items-center gap-2 mb-2">
												<span className="text-primary text-xl">£</span>
												<span className="text-gray-400 text-sm font-medium">
													{tripCardTrans?.cost || "Cost"}
												</span>
											</div>
											<p className="text-primary font-bold text-xl">
												£{data.cost}
											</p>
										</div>
									</div>

									<div className="bg-background/30 rounded-lg p-3 border border-muted/10 mb-4">
										<div className="flex items-center gap-2 mb-1">
											<TiLocation className="text-primary text-base" />
											<span className="text-gray-400 text-xs font-medium">
												{tripCardTrans?.dropoff || "Drop-off"}
											</span>
										</div>
										<p className="text-white font-medium text-sm md:text-base truncate">
											{data.dropoff_str || "-"}
										</p>
									</div>
									<div className="bg-background/30 rounded-lg p-3 border border-muted/10 mb-4">
										<div className="flex items-center gap-2 mb-1">
											<TiLocation className="text-primary text-base" />
											<span className="text-gray-400 text-xs font-medium">
												{tripCardTrans?.pickup || "Pickup"}
											</span>
										</div>
										<p className="text-white font-medium text-sm md:text-base truncate">
											{data.pickup_str || "-"}
										</p>
									</div>
								</div>

								{/* Right Side - Map */}
								<div className="lg:w-1/2 min-h-[300px] lg:min-h-full">
									<div className="h-full rounded-xl overflow-hidden border border-muted/20 shadow-lg">
										{data.status === "active" ||
										data.status === "driver_on_the_way" ? (
											<MapViewtest
												tripId={data.id}
												routePolyline={data.route_polyline}
											/>
										) : (
											<div className="h-full rounded overflow-hidden">
												<MapView routePolyline={data.route_polyline} />
											</div>
										)}
									</div>
								</div>
							</div>
						</div>

						{/* Footer Actions */}
						<div className="border-t border-muted/20 px-6 py-5 bg-background/20">
							<div className="flex flex-col sm:flex-row items-center justify-center gap-4">
								<Button
									className="w-full sm:w-auto text-base md:text-lg py-6 px-8 gap-2"
									size="lg"
								>
									<IoChatbubbleEllipsesSharp className="text-xl" />
									{tripCardTrans?.contactDriver || "Contact Driver"}
									<span dir="ltr">{data?.driver_info?.phone_number}</span>
								</Button>
								<Button
									variant="secondary"
									className="w-full sm:w-auto text-base md:text-lg py-6 px-8"
									onClick={() => setOpenDetails(false)}
									size="lg"
								>
									{tripCardTrans?.close || "Close"}
								</Button>
							</div>
						</div>
					</div>
				</div>
			)}
		</>
	);
}
