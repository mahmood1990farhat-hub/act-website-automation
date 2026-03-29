"use client";

import { Button } from "@/components/ui/button";
import { fetchData } from "@/lib/api/fetchData";
import { postData } from "@/lib/api/postData";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Locale } from "../../../../i18n.config";
import IsLoadig from "../ISloading";

import { BsEyeFill, BsFillTelephoneFill } from "react-icons/bs";
import { FaTimesCircle } from "react-icons/fa";
import Pagination from "../Pagination";

import { FaClock } from "react-icons/fa";

import { MdDone } from "react-icons/md";
import { formatDate } from "@/lib/FormatDate";

import dynamic from "next/dynamic";
import TripDetails from "../driver/TripDetails";
import GlobalModal from "../GlobalModal";
import { toast } from "react-toastify";
import PhoneInputWithCountrySelect from "react-phone-number-input";
import "react-phone-number-input/style.css";
import TripGoogleMap from "./tracking/trip-tracking-map";
import MapViewtest from "./tracking/trip-tracking-provider";
const MapView = dynamic(() => import("../bookTaxi/MapView"), { ssr: false });

function getStatusColor(status: string) {
	switch (status) {
		case "cancelled":
			return "text-accent  ";
		case "pending":
			return "text-primary ";
		case "driver_on_the_way":
			return "text-[#00BCD4] ";
		case "completed":
			return "text-[#9E9E9E] ";
		case "active":
			return "text-[#2196F3] ";
		case "accepted":
			return "text-[#4CAF50] ";
		default:
			return "text-[#22C822]  ";
	}
}

export default function TripsDashboard({
	token,
	locale,
	trans,
}: {
	token?: string;
	locale: Locale;
	trans: any;
}) {
	const [detailsTrips, setDetailsTrips] = useState<any>();
	const [page, setPage] = useState(1);
	const [openDetails, setOpenDetails] = useState(false);
	const [filterStatus, setFilterStatus] = useState<
		| "all"
		| "pending"
		| "accepted"
		| "active"
		| "driver_on_the_way"
		| "completed"
		| "cancelled"
	>("all");
	const [searchTerm, setSearchTerm] = useState("");
	const [dateFrom, setDateFrom] = useState("");
	const [dateTo, setDateTo] = useState("");
	const [isPaid, setIsPaid] = useState<"" | "true" | "false">("");
	const [passengerId, setPassengerId] = useState("");
	const [driverId, setDriverId] = useState("");
	const [carTypeId, setCarTypeId] = useState("");
	const [ordering, setOrdering] = useState("-created_at");
	const [isDateRangeOpen, setIsDateRangeOpen] = useState(false);
	const [showAssignGuestModal, setShowAssignGuestModal] = useState(false);
	const [guestDriverForm, setGuestDriverForm] = useState<{
		name: string;
		phone: string;
		company: string;
		car_info: {
			brand: string;
			model: string;
			color: string;
			registration_number: string;
			year: string;
			additional_notes: string;
		};
	}>({
		name: "",
		phone: "",
		company: "",
		car_info: {
			brand: "",
			model: "",
			color: "",
			registration_number: "",
			year: "",
			additional_notes: "",
		},
	});

	const queryClient = useQueryClient();

	// Fetch filtered trips data
	const { data: AllTrips, isLoading: AllTripsLodaing } = useQuery<any>({
		queryKey: [
			"my Trips driver",
			page,
			filterStatus,
			searchTerm,
			dateFrom,
			dateTo,
			isPaid,
			passengerId,
			driverId,
			carTypeId,
			ordering,
		],
		queryFn: () => {
			const queryParams: Record<string, string> = {
				locale: locale,
				page_size: "6",
				page: page.toString(),
				ordering,
			};

			if (filterStatus !== "all") {
				queryParams.status = filterStatus;
			}
			if (searchTerm.trim()) {
				queryParams.search = searchTerm.trim();
			}
			if (dateFrom) {
				queryParams.date_from = dateFrom;
			}
			if (dateTo) {
				queryParams.date_to = dateTo;
			}
			if (isPaid) {
				queryParams.is_paid = isPaid;
			}
			if (passengerId.trim()) {
				queryParams.passenger_id = passengerId.trim();
			}
			if (driverId.trim()) {
				queryParams.driver_id = driverId.trim();
			}
			if (carTypeId.trim()) {
				queryParams.car_type_id = carTypeId.trim();
			}

			return fetchData({
				endpoint: "/api/admin-panel/trips/",
				token: token,
				queryParams,
			});
		},
	});

	const assignGuestDriverMutation = useMutation({
		mutationFn: async () => {
			if (!detailsTrips?.id) {
				throw new Error(
					trans?.trips?.errors?.tripIdMissing || "Trip ID is missing",
				);
			}

			// Build car_info object only if at least one field is filled
			const carInfo = guestDriverForm.car_info;
			const hasCarInfo =
				carInfo.brand.trim() ||
				carInfo.model.trim() ||
				carInfo.color.trim() ||
				carInfo.registration_number.trim() ||
				carInfo.year.trim() ||
				carInfo.additional_notes.trim();

			const body: any = {
				guest_driver_name: guestDriverForm.name,
				guest_driver_phone: guestDriverForm.phone,
			};

			if (guestDriverForm.company.trim()) {
				body.guest_driver_company = guestDriverForm.company;
			}

			if (hasCarInfo) {
				body.car_info = {};
				if (carInfo.brand.trim()) body.car_info.brand = carInfo.brand.trim();
				if (carInfo.model.trim()) body.car_info.model = carInfo.model.trim();
				if (carInfo.color.trim()) body.car_info.color = carInfo.color.trim();
				if (carInfo.registration_number.trim())
					body.car_info.registration_number =
						carInfo.registration_number.trim();
				if (carInfo.year.trim()) body.car_info.year = carInfo.year.trim();
				if (carInfo.additional_notes.trim())
					body.car_info.additional_notes = carInfo.additional_notes.trim();
			}

			return await postData<any>({
				endpoint: `/api/admin-panel/trips/${detailsTrips.id}/assign-guest-driver/`,
				token,
				body,
				noToast: false, // Let API show toast
			});
		},
		onSuccess: (response) => {
			// Update selected trip details in the modal
			if (response?.data) {
				setDetailsTrips(response.data);
			}
			setShowAssignGuestModal(false);
			// Refresh trips list
			queryClient.invalidateQueries({ queryKey: ["my Trips driver"] });
		},
		onError: () => {
			// Error toast is handled by postData
		},
	});

	const [showCancelModal, setShowCancelModal] = useState(false);

	const cancelTripMutation = useMutation({
		mutationFn: async (tripId: number) => {
			return await postData<any>({
				endpoint: `/api/admin-panel/trips/${tripId}/cancel/`,
				token,
				noToast: false, // Let API show toast
			});
		},
		onSuccess: (response) => {
			// Update selected trip details in the modal
			if (response?.data && detailsTrips?.id === response?.data?.id) {
				setDetailsTrips(response.data);
			}
			setShowCancelModal(false);
			// Refresh trips list
			queryClient.invalidateQueries({ queryKey: ["my Trips driver"] });
		},
		onError: () => {
			// Error toast is handled by postData
		},
	});

	const [showStatusModal, setShowStatusModal] = useState(false);
	const [selectedNewStatus, setSelectedNewStatus] = useState<
		"accepted" | "driver_on_the_way" | "active" | "completed" | null
	>(null);

	const statusTransitionMutation = useMutation({
		mutationFn: async ({
			tripId,
			status,
		}: {
			tripId: number;
			status: "accepted" | "driver_on_the_way" | "active" | "completed";
		}) => {
			return await postData<any>({
				endpoint: `/api/admin-panel/trips/${tripId}/status/`,
				token,
				body: { status },
				noToast: false,
			});
		},
		onSuccess: async (response) => {
			
			const newStatus = selectedNewStatus; // Store before clearing
			setShowStatusModal(false);
			setSelectedNewStatus(null);

			// Update detailsTrips if response contains updated trip data
			if (
				response?.data &&
				typeof response.data === "object" &&
				"id" in response.data
			) {
				setDetailsTrips(response.data);
			} else if (
				response?.trip &&
				typeof response.trip === "object" &&
				"id" in response.trip
			) {
				setDetailsTrips(response.trip);
			} else if (newStatus && detailsTrips) {
				// If response doesn't contain trip data, manually update the status
				setDetailsTrips({
					...detailsTrips,
					status: newStatus,
				});
			}

			// Refresh trips list
			await queryClient.invalidateQueries({ queryKey: ["my Trips driver"] });

			// Refetch the trips list to get updated data
			try {
				await queryClient.refetchQueries({
					queryKey: [
						"my Trips driver",
						page,
						filterStatus,
						searchTerm,
						dateFrom,
						dateTo,
						isPaid,
						passengerId,
						driverId,
						carTypeId,
						ordering,
					],
				});

				// Get updated data from cache
				const updatedTrips = queryClient.getQueryData<any>([
					"my Trips driver",
					page,
					filterStatus,
					searchTerm,
					dateFrom,
					dateTo,
					isPaid,
					passengerId,
					driverId,
					carTypeId,
					ordering,
				]);

				// Update detailsTrips from the refreshed list
				if (updatedTrips?.trips && detailsTrips?.id) {
					const updatedTrip = updatedTrips.trips.find(
						(t: any) => t.id === detailsTrips?.id,
					);
					if (updatedTrip) {

						setDetailsTrips(updatedTrip);
					}
				}
			} catch (error) {
				console.error("Error refetching trips:", error);
			}
		},
		onError: (error) => {
			console.error("Status transition error:", error);
			// Error toast is handled by postData
		},
	});

	// Get next allowed status transitions
	const getNextStatuses = (
		currentStatus: string,
	): ("accepted" | "driver_on_the_way" | "active" | "completed")[] => {
		switch (currentStatus) {
			case "pending":
				return ["accepted"];
			case "accepted":
				return ["driver_on_the_way"];
			case "driver_on_the_way":
				return ["active"];
			case "active":
				return ["completed"];
			default:
				return [];
		}
	};

	// Sort trips: trips with is_guest_driver appear first (prioritize non-completed ones)
	// Create a copy to avoid mutating the original array
	const filteredTrips =
		!AllTripsLodaing && AllTrips?.trips
			? [...AllTrips.trips].sort((a: any, b: any) => {
					// Check if trip is a guest driver
					const aIsGuestDriver = a.is_guest_driver === true;
					const bIsGuestDriver = b.is_guest_driver === true;

					// First priority: trips with is_guest_driver that are NOT completed
					const aPriority =
						aIsGuestDriver && a.status !== "completed"
							? 2
							: aIsGuestDriver
								? 1
								: 0;
					const bPriority =
						bIsGuestDriver && b.status !== "completed"
							? 2
							: bIsGuestDriver
								? 1
								: 0;

					// Higher priority comes first
					if (aPriority !== bPriority) {
						return bPriority - aPriority;
					}

					// If both have same priority, maintain original order
					return 0;
				})
			: [];

	const statsAllTime = AllTrips?.stats?.all_time || {
		total: 0,
		completed: 0,
		pending: 0,
		cancelled: 0,
		accepted: 0,
		active: 0,
		driver_on_the_way: 0,
		total_revenue: 0,
		unpaid_completed: 0,
	};

	const statsFiltered = AllTrips?.stats?.filtered || {
		count: 0,
		total_revenue: 0,
	};

	const resetFilters = () => {
		setFilterStatus("all");
		setSearchTerm("");
		setDateFrom("");
		setDateTo("");
		setIsPaid("");
		setPassengerId("");
		setDriverId("");
		setCarTypeId("");
		setOrdering("-created_at");
		setPage(1);
		setIsDateRangeOpen(false);
	};

	const dateRangeContainerRef = useRef<HTMLDivElement | null>(null);

	useEffect(() => {
		if (!isDateRangeOpen) return;

		const handleClickOutside = (event: MouseEvent) => {
			if (
				dateRangeContainerRef.current &&
				!dateRangeContainerRef.current.contains(event.target as Node)
			) {
				setIsDateRangeOpen(false);
			}
		};

		document.addEventListener("mousedown", handleClickOutside);
		return () => {
			document.removeEventListener("mousedown", handleClickOutside);
		};
	}, [isDateRangeOpen]);

	const dateRangeLabel = (() => {
		if (dateFrom && dateTo) {
			return `${formatDate(new Date(dateFrom), locale)} → ${formatDate(
				new Date(dateTo),
				locale,
			)}`;
		}
		if (dateFrom) {
			return `${trans?.trips?.filterLabels?.from || "From"}: ${formatDate(
				new Date(dateFrom),
				locale,
			)}`;
		}
		if (dateTo) {
			return `${trans?.trips?.filterLabels?.to || "To"}: ${formatDate(
				new Date(dateTo),
				locale,
			)}`;
		}
		return trans?.trips?.filterPlaceholders?.dateRange || "Select date range";
	})();

	return (
		<>
			<div className="mt-4">
				<div className="bg-card rounded-xl border-2 border-border p-4 mb-6">
					<h3 className="text-sm font-semibold text-foreground mb-4">
						{trans?.trips?.filtersTitle || "Filters"}
					</h3>
					<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
						<div>
							<label className="block mb-1 text-xs uppercase tracking-wide text-muted-foreground">
								{trans?.trips?.filterLabels?.search || "Search"}
							</label>
							<input
								value={searchTerm}
								onChange={(e) => {
									setSearchTerm(e.target.value);
									setPage(1);
								}}
								placeholder={
									trans?.trips?.filterPlaceholders?.search ||
									"Search by passenger, driver, phone..."
								}
								className="w-full p-3 border-2 bg-background text-foreground border-border rounded-lg focus:outline-none focus:border-primary placeholder:text-muted"
							/>
						</div>
						<div className="relative" ref={dateRangeContainerRef}>
							<label className="block mb-1 text-xs uppercase tracking-wide text-muted-foreground">
								{trans?.trips?.filterLabels?.dateRange || "Trip date range"}
							</label>
							<button
								type="button"
								onClick={() => setIsDateRangeOpen((prev) => !prev)}
								className="w-full p-3 border-2 bg-background text-left text-foreground border-border rounded-lg focus:outline-none focus:border-primary flex items-center justify-between gap-2"
							>
								<span className="truncate text-sm">{dateRangeLabel}</span>
								<FaClock className="text-muted-foreground" />
							</button>
							{isDateRangeOpen && (
								<div className="absolute z-30 mt-2 w-72 rounded-lg border border-border bg-card shadow-xl">
									<div className="p-4 space-y-3">
										<div>
											<span className="text-xs font-semibold text-muted-foreground">
												{trans?.trips?.filterLabels?.dateFrom || "Start date"}
											</span>
											<input
												type="date"
												value={dateFrom}
												onChange={(e) => {
													setDateFrom(e.target.value);
													setPage(1);
												}}
												className="mt-1 w-full rounded-md border border-border bg-background p-2 text-sm text-foreground focus:outline-none focus:border-primary"
											/>
										</div>
										<div>
											<span className="text-xs font-semibold text-muted-foreground">
												{trans?.trips?.filterLabels?.dateTo || "End date"}
											</span>
											<input
												type="date"
												value={dateTo}
												onChange={(e) => {
													setDateTo(e.target.value);
													setPage(1);
												}}
												className="mt-1 w-full rounded-md border border-border bg-background p-2 text-sm text-foreground focus:outline-none focus:border-primary"
											/>
										</div>
										<div className="flex items-center justify-end gap-2 pt-1">
											<Button
												type="button"
												variant="ghost"
												onClick={() => {
													setDateFrom("");
													setDateTo("");
													setPage(1);
												}}
												className="h-8 px-3 text-xs"
											>
												{trans?.trips?.filterActions?.clear || "Clear"}
											</Button>
											<Button
												type="button"
												onClick={() => setIsDateRangeOpen(false)}
												className="h-8 px-3 text-xs"
											>
												{trans?.trips?.filterActions?.apply || "Apply"}
											</Button>
										</div>
									</div>
								</div>
							)}
						</div>
						<div>
							<label className="block mb-1 text-xs uppercase tracking-wide text-muted-foreground">
								{trans?.trips?.filterLabels?.isPaid || "Payment status"}
							</label>
							<select
								value={isPaid}
								onChange={(e) => {
									setIsPaid(e.target.value as "" | "true" | "false");
									setPage(1);
								}}
								className="w-full p-3 border-2 bg-background text-foreground border-border rounded-lg focus:outline-none focus:border-primary"
							>
								<option value="">
									{trans?.trips?.filterPlaceholders?.all || "All"}
								</option>
								<option value="true">
									{trans?.trips?.filterLabels?.paid || "Paid"}
								</option>
								<option value="false">
									{trans?.trips?.filterLabels?.unpaid || "Unpaid"}
								</option>
							</select>
						</div>

						<div>
							<label className="block mb-1 text-xs uppercase tracking-wide text-muted-foreground">
								{trans?.trips?.filterLabels?.ordering || "Sort"}
							</label>
							<select
								value={ordering}
								onChange={(e) => {
									setOrdering(e.target.value);
									setPage(1);
								}}
								className="w-full p-3 border-2 bg-background text-foreground border-border rounded-lg focus:outline-none focus:border-primary"
							>
								<option value="-created_at">
									{trans?.trips?.orderingOptions?.newest || "Newest first"}
								</option>
								<option value="created_at">
									{trans?.trips?.orderingOptions?.oldest || "Oldest first"}
								</option>
								<option value="-trip_date">
									{trans?.trips?.orderingOptions?.tripNewest ||
										"Latest trip date"}
								</option>
								<option value="trip_date">
									{trans?.trips?.orderingOptions?.tripOldest ||
										"Earliest trip date"}
								</option>
							</select>
						</div>
					</div>
					<div className="flex flex-wrap items-center gap-3 mt-4">
						<span className="text-xs text-muted-foreground">
							{trans?.trips?.activeFiltersLabel || "Active filters"}:{" "}
							{
								[
									filterStatus !== "all",
									Boolean(searchTerm.trim()),
									Boolean(dateFrom),
									Boolean(dateTo),
									Boolean(isPaid),
									Boolean(passengerId.trim()),
									Boolean(driverId.trim()),
									Boolean(carTypeId.trim()),
									ordering !== "-created_at",
								].filter(Boolean).length
							}
						</span>
						<Button
							variant="outline"
							onClick={resetFilters}
							className="border-border text-muted-foreground hover:bg-primary/10 hover:text-primary hover:border-primary/50 transition-colors"
						>
							{trans?.trips?.resetFilters || "Reset filters"}
						</Button>
					</div>
				</div>

				{AllTrips && (
					<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 mb-6">
						{/* Revenue Card */}
						<div
							className="bg-card rounded-xl border-2 border-green-500/60 p-4 transition-all duration-300"
							dir={locale === "ar" ? "rtl" : "ltr"}
						>
							<div className="flex items-center gap-4">
								<div className="w-14 h-14 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-green-500/30">
									<svg
										className="w-6 h-6 text-white"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										strokeWidth="2"
										strokeLinecap="round"
										strokeLinejoin="round"
									>
										<path d="M12 1v22" />
										<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7H14a3.5 3.5 0 0 1 0 7H6" />
									</svg>
								</div>
								<div className="flex-1">
									<p className="text-xs font-medium text-muted-foreground mb-1">
										{trans?.trips?.stats?.Revenue || "Total revenue"}
									</p>
									<p className="text-3xl font-bold text-green-500">
										£{Number(statsAllTime.total_revenue || 0).toFixed(2)}
									</p>
								</div>
							</div>
						</div>

						{/* All Trips Card */}

						<button
							onClick={() => setFilterStatus("all")}
							className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
								filterStatus === "all"
									? "border-yellow-500 shadow-xl shadow-yellow-500/30 md:scale-105"
									: "border-yellow-500/60 md:hover:border-yellow-500/80 md:hover:shadow-lg md:hover:shadow-yellow-500/20"
							}`}
						>
							<div className="flex items-center gap-4">
								<div className="w-14 h-14 bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-yellow-500/30">
									<FaClock className="text-foreground text-2xl" />
								</div>
								<div className="flex-1">
									<p className="text-xs font-medium text-muted-foreground mb-1">
										{trans.statistics?.[0] || "Total Trips"}
									</p>
									<p className="text-3xl font-bold text-yellow-600">
										{statsAllTime.total}
									</p>
								</div>
							</div>
						</button>

						{/* Pending Trips Card */}
						<button
							onClick={() => setFilterStatus("pending")}
							className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
								filterStatus === "pending"
									? "border-orange-500 shadow-xl shadow-orange-500/30 md:scale-105"
									: "border-orange-500/60 md:hover:border-orange-500/80 md:hover:shadow-lg md:hover:shadow-orange-500/20"
							}`}
						>
							<div className="flex items-center gap-4">
								<div className="w-14 h-14 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-orange-500/30">
									<FaClock className="text-white text-2xl" />
								</div>
								<div className="flex-1">
									<p className="text-xs font-medium text-muted-foreground mb-1">
										{trans.status?.find((s: any) => s.value === "pending")
											?.title || "Pending"}
									</p>
									<p className="text-3xl font-bold text-orange-600">
										{statsAllTime.pending}
									</p>
								</div>
							</div>
						</button>

						{/* Accepted Trips Card */}
						<button
							onClick={() => setFilterStatus("accepted")}
							className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
								filterStatus === "accepted"
									? "border-green-500 shadow-xl shadow-green-500/30 md:scale-105"
									: "border-green-500/60 md:hover:border-green-500/80 md:hover:shadow-lg md:hover:shadow-green-500/20"
							}`}
						>
							<div className="flex items-center gap-4">
								<div className="w-14 h-14 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-green-500/30">
									<MdDone className="text-white text-2xl" />
								</div>
								<div className="flex-1">
									<p className="text-xs font-medium text-muted-foreground mb-1">
										{trans.status?.find((s: any) => s.value === "accepted")
											?.title || "Accepted"}
									</p>
									<p className="text-3xl font-bold text-green-600">
										{statsAllTime.accepted}
									</p>
								</div>
							</div>
						</button>

						{/* Active Trips Card */}
						<button
							onClick={() => setFilterStatus("active")}
							className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
								filterStatus === "active"
									? "border-blue-500 shadow-xl shadow-blue-500/30 md:scale-105"
									: "border-blue-500/60 md:hover:border-blue-500/80 md:hover:shadow-lg md:hover:shadow-blue-500/20"
							}`}
						>
							<div className="flex items-center gap-4">
								<div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/30">
									<svg
										className="w-6 h-6 text-white"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											strokeLinecap="round"
											strokeLinejoin="round"
											strokeWidth={2}
											d="M13 10V3L4 14h7v7l9-11h-7z"
										/>
									</svg>
								</div>
								<div className="flex-1">
									<p className="text-xs font-medium text-muted-foreground mb-1">
										{trans.status?.find((s: any) => s.value === "active")
											?.title || "Active"}
									</p>
									<p className="text-3xl font-bold text-blue-600">
										{statsAllTime.active}
									</p>
								</div>
							</div>
						</button>

						{/* Driver on the way Card */}
						<button
							onClick={() => setFilterStatus("driver_on_the_way")}
							className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
								filterStatus === "driver_on_the_way"
									? "border-cyan-500 shadow-xl shadow-cyan-500/30 md:scale-105"
									: "border-cyan-500/60 md:hover:border-cyan-500/80 md:hover:shadow-lg md:hover:shadow-cyan-500/20"
							}`}
						>
							<div className="flex items-center gap-4">
								<div className="w-14 h-14 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-cyan-500/30">
									<svg
										className="w-6 h-6 text-white"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											strokeLinecap="round"
											strokeLinejoin="round"
											strokeWidth={2}
											d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
										/>
										<path
											strokeLinecap="round"
											strokeLinejoin="round"
											strokeWidth={2}
											d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
										/>
									</svg>
								</div>
								<div className="flex-1">
									<p className="text-xs font-medium text-muted-foreground mb-1">
										{trans.status?.find(
											(s: any) => s.value === "driver_on_the_way",
										)?.title ||
											trans?.trips?.statusLabels?.onTheWay ||
											"On the way"}
									</p>
									<p className="text-3xl font-bold text-cyan-600">
										{statsAllTime.driver_on_the_way}
									</p>
								</div>
							</div>
						</button>

						{/* Completed Trips Card */}
						<button
							onClick={() => setFilterStatus("completed")}
							className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
								filterStatus === "completed"
									? "border-emerald-500 shadow-xl shadow-emerald-500/30 md:scale-105"
									: "border-emerald-500/60 md:hover:border-emerald-500/80 md:hover:shadow-lg md:hover:shadow-emerald-500/20"
							}`}
						>
							<div className="flex items-center gap-4">
								<div className="w-14 h-14 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-emerald-500/30">
									<svg
										className="w-6 h-6 text-white"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											strokeLinecap="round"
											strokeLinejoin="round"
											strokeWidth={2}
											d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
										/>
									</svg>
								</div>
								<div className="flex-1">
									<p className="text-xs font-medium text-muted-foreground mb-1">
										{trans.statistics?.[1] || "Completed"}
									</p>
									<p className="text-3xl font-bold text-emerald-600">
										{statsAllTime.completed}
									</p>
								</div>
							</div>
						</button>

						{/* Cancelled Trips Card */}
						<button
							onClick={() => setFilterStatus("cancelled")}
							className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
								filterStatus === "cancelled"
									? "border-red-500 shadow-xl shadow-red-500/30 md:scale-105"
									: "border-red-500/60 md:hover:border-red-500/80 md:hover:shadow-lg md:hover:shadow-red-500/20"
							}`}
						>
							<div className="flex items-center gap-4">
								<div className="w-14 h-14 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-red-500/30">
									<svg
										className="w-6 h-6 text-white"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											strokeLinecap="round"
											strokeLinejoin="round"
											strokeWidth={2}
											d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
										/>
									</svg>
								</div>
								<div className="flex-1">
									<p className="text-xs font-medium text-muted-foreground mb-1">
										{trans.statistics?.[3] || "Cancelled"}
									</p>
									<p className="text-3xl font-bold text-red-600">
										{statsAllTime.cancelled}
									</p>
								</div>
							</div>
						</button>
					</div>
				)}

				<div className="my-5 hidden xl:block">
					<div className="w-full bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden">
						<div className="bg-gradient-to-r from-card to-background px-6 py-3 border-b-2 border-border">
							<h2 className="text-foreground text-base font-bold drop-shadow-sm">
								{trans?.trips?.allTrips || "All Trips"}
							</h2>
						</div>
						<div className="overflow-x-auto">
							<table className="w-full min-w-[820px] text-xs">
								<thead>
									<tr className="border-b-2 border-border bg-card">
										{(trans?.trips?.tableHeaders || []).map(
											(trHeader: string) => (
												<th
													key={trHeader}
													className="text-start py-3 px-3 font-bold text-foreground"
												>
													{trHeader}
												</th>
											),
										)}
									</tr>
								</thead>
								<tbody>
									{AllTripsLodaing ? (
										<tr>
											<td>
												<IsLoadig />
											</td>{" "}
										</tr>
									) : (
										filteredTrips.map((trip: any, index: any) => {
											const shouldHighlight =
												trip.is_guest_driver === true &&
												trip.status !== "completed";
											return (
												<tr
													key={index}
													className={`border-b border-border hover:bg-muted transition-colors ${
														shouldHighlight
															? "bg-yellow-500/10 border-l-4 border-l-yellow-500"
															: ""
													}`}
												>
													<td className="py-3 px-3 font-bold text-foreground max-w-[160px]">
														<div className="flex items-center gap-2">
															{trip.passenger_info?.full_name || "-"}
															{shouldHighlight && (
																<span
																	className="px-1.5 py-0.5 bg-yellow-500 text-white text-xs font-bold rounded-full animate-pulse"
																	title="Requires attention"
																>
																	⚠️
																</span>
															)}
														</div>
													</td>
													<td className="py-3 px-3 text-foreground whitespace-nowrap">
														{trip.id}
													</td>
													<td className="py-3 px-3 text-foreground max-w-[220px]">
														<div className="truncate" title={trip.pickup_str}>
															{trip.pickup_str || "-"}
														</div>
														<div className="truncate" title={trip.dropoff_str}>
															{trip.dropoff_str || "-"}
														</div>
													</td>
													<td className="py-3 px-3 text-muted-foreground whitespace-nowrap">
														<div>
															{formatDate(new Date(trip.trip_date), locale)}
														</div>
														<div className="text-gray-400 text-xs">
															{trip.trip_time?.slice(0, 5)}
														</div>
													</td>
													<td className="py-3 px-3 text-foreground whitespace-nowrap">
														{(trip.distance_miles * 1.61).toFixed()}{" "}
														{trans?.trips?.units?.km || "km"}
													</td>
													<td className="py-3 px-3 font-bold text-green-600 whitespace-nowrap">
														£ {trip.cost}
													</td>
													<td className="py-3 px-3 whitespace-nowrap">
														<span
															className={`inline-flex items-center px-2.5  py-0.5 rounded-full font-bold  ${getStatusColor(
																trip.status,
															)}`}
														>
															{trans?.status?.find(
																(stat: { title: string; value: string }) =>
																	trip.status === stat.value,
															)?.title || trip.status}
														</span>
													</td>
													<td className="py-3 px-3 text-center whitespace-nowrap">
														<div className="flex items-center space-x-2 justify-center">
															<Button
																onClick={() => {
																	(setDetailsTrips(trip), setOpenDetails(true));
																}}
																variant="ghost"
																className="p-1.5 hover:bg-muted text-yellow-600 hover:text-yellow-700 transition-colors inline-flex"
																title={
																	trans?.trips?.viewDetails ||
																	trans?.viewDetails ||
																	"View Details"
																}
															>
																<BsEyeFill className="text-base" />
															</Button>
														</div>
													</td>
												</tr>
											);
										})
									)}
								</tbody>
							</table>
						</div>
						{!AllTripsLodaing && (
							<div className="flex items-center justify-between px-6 border-t-2 border-border">
								<div className="text-sm mx-auto text-muted-foreground">
									{trans.pagination.table} {page} {trans.pagination.of}{" "}
									{AllTrips?.pagination?.num_pages || 1}{" "}
									{trans.pagination.tables}
								</div>

								<Pagination
									currentPage={page}
									onPageChange={(pa) => setPage(pa)}
									locale={locale}
									totalPages={AllTrips?.pagination?.num_pages || 1}
								/>
							</div>
						)}
					</div>
				</div>

				{/* Mobile cards */}
				<div className="my-5 xl:hidden space-y-4">
					{AllTripsLodaing ? (
						<IsLoadig />
					) : filteredTrips && filteredTrips.length > 0 ? (
						filteredTrips.map((trip: any) => {
							const shouldHighlight =
								trip.is_guest_driver === true && trip.status !== "completed";
							return (
								<div
									key={trip.id}
									className={`bg-card max-sm:max-w-[360px] mx-auto rounded-xl shadow-lg border-2 p-4 hover:shadow-2xl transition-all ${
										shouldHighlight
											? "border-yellow-500 bg-yellow-500/10 border-l-4"
											: "border-border hover:border-primary/60"
									}`}
								>
									<div className="flex items-start justify-between mb-3 pb-3 border-b-2 border-border">
										<div className="flex-1">
											<div className="flex items-center gap-2 mb-1">
												<h3 className="font-bold text-lg text-foreground">
													#{trip.id}
												</h3>
												{shouldHighlight && (
													<span
														className="px-2 py-0.5 bg-yellow-500 text-white text-xs font-bold rounded-full animate-pulse"
														title="Requires attention"
													>
														⚠️
													</span>
												)}
											</div>
											<p className="text-sm text-muted-foreground">
												{trip.passenger_info?.full_name || "-"}
											</p>
										</div>
										<span
											className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border ${getStatusColor(trip.status)}`}
										>
											{trans?.status?.find((s: any) => s.value === trip.status)
												?.title || trip.status}
										</span>
									</div>

									<div className="space-y-2 mb-4">
										<div className="flex items-center justify-between py-2 border-b border-border">
											<span className="text-sm text-muted-foreground font-semibold">
												{trans?.trips?.mobileLabels?.pickup || "Pickup"}
											</span>
											<span
												className="text-sm text-foreground font-bold max-w-[60%] truncate"
												title={trip.pickup_str}
											>
												{trip.pickup_str}
											</span>
										</div>
										<div className="flex items-center justify-between py-2 border-b border-border">
											<span className="text-sm text-muted-foreground font-semibold">
												{trans?.trips?.mobileLabels?.dropoff || "Dropoff"}
											</span>
											<span
												className="text-sm text-foreground font-bold max-w-[60%] truncate"
												title={trip.dropoff_str}
											>
												{trip.dropoff_str}
											</span>
										</div>
										<div className="flex items-center justify-between py-2">
											<span className="text-sm text-muted-foreground font-semibold">
												{trans?.trips?.mobileLabels?.date || "Date"}
											</span>
											<span className="text-sm text-foreground font-bold">
												{formatDate(new Date(trip.trip_date), locale)}{" "}
												{trip.trip_time?.slice(0, 5)}
											</span>
										</div>
									</div>

									<Button
										onClick={() => {
											setDetailsTrips(trip);
											setOpenDetails(true);
										}}
										className="w-full bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-foreground font-bold shadow-lg shadow-yellow-500/20"
									>
										<BsEyeFill className="mr-2" />{" "}
										{trans?.trips?.viewDetails ||
											trans?.viewDetails ||
											"View Details"}
									</Button>
								</div>
							);
						})
					) : (
						<div className="bg-card rounded-xl shadow-lg border-2 border-border p-8 text-center">
							<p className="text-muted-foreground font-medium">
								{trans?.trips?.noTrips || "No trips found"}
							</p>
						</div>
					)}
				</div>
			</div>

			{openDetails && (
				<div
					onClick={() => setOpenDetails(false)}
					className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-3 lg:p-4"
				>
					<div
						onClick={(e) => e.stopPropagation()}
						className="bg-card rounded-2xl w-full max-w-5xl shadow-2xl max-h-[95vh] xl:max-h-[90vh] overflow-y-auto on-scrollbar border-2 border-border"
					>
						{/* Modal Header */}
						<div className="sticky top-0 bg-gradient-to-r from-card to-background px-4 xl:px-6 py-4 lg:py-5 border-b-2 border-border rounded-t-2xl z-10">
							<div className="flex items-center justify-between flex-wrap gap-3">
								<h2 className="text-xl lg:text-2xl font-bold text-foreground">
									{trans?.tripDetails?.tripDetails || "Trip Details"}
								</h2>
								<span
									className={`px-4 py-2 rounded-full text-xs xl:text-sm font-bold border ${getStatusColor(
										detailsTrips?.status || "",
									)}`}
								>
									{trans?.status?.find(
										(s: any) => s.value === detailsTrips?.status,
									)?.title || detailsTrips?.status}
								</span>
							</div>
						</div>

						{/* Modal Content */}
						<div className="p-4 md:p-6 space-y-5 md:space-y-6">
							<div className="flex max-md:flex-col gap-4">
								<div className="md:w-1/2 bg-muted border-2 border-yellow-500/50 rounded-xl p-4 md:p-5 overflow-y-auto on-scrollbar">
									<h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
										<span className="w-1 h-6 bg-yellow-500 rounded-full"></span>
										{trans?.tripDetails?.tripInfo || "Trip Information"}
									</h3>
									<TripDetails
										detailsTrips={detailsTrips}
										trans={trans}
										locale={locale}
										variant="dashboard"
									/>
								</div>
								<div className="md:w-1/2 bg-muted border-2 border-blue-400/50 rounded-xl p-2 md:p-3 w-full min-h-[300px] max-md:max-h-[400px] overflow-hidden">
									{detailsTrips.status === "accepted" ||
									detailsTrips.status === "driver_on_the_way" ? (
										<MapViewtest
											tripId={detailsTrips.id}
											routePolyline={detailsTrips.route_polyline}
										/>
									) : (
										<div className="h-full rounded overflow-hidden">
											<MapView routePolyline={detailsTrips.route_polyline} />
										</div>
									)}
								</div>
							</div>
						</div>

						{/* Modal Footer */}
						<div className="sticky bottom-0 bg-gradient-to-t from-card to-background px-4 md:px-6 py-4 md:py-5 border-t-2 border-border rounded-b-2xl">
							{/* Status Transition Buttons for Guest Driver Car Trips */}
							{detailsTrips?.is_guest_driver === true &&
								detailsTrips?.status !== "completed" &&
								getNextStatuses(detailsTrips?.status || "").length > 0 && (
									<div className="mb-4 p-4 bg-yellow-500/10 border-2 border-yellow-500/50 rounded-xl">
										<p className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
											<span>⚠️</span>
											{trans?.trips?.statusTransitionTitle ||
												"Update Trip Status"}
										</p>
										<div className="flex flex-wrap gap-2">
											{getNextStatuses(detailsTrips?.status || "").map(
												(nextStatus) => (
													<Button
														key={nextStatus}
														type="button"
														onClick={() => {
															setSelectedNewStatus(nextStatus);
															setShowStatusModal(true);
														}}
														className="font-semibold bg-yellow-500 hover:bg-yellow-600 text-white shadow-lg shadow-yellow-500/30"
													>
														{trans?.trips?.statusTransitions?.[nextStatus] ||
															nextStatus.replace(/_/g, " ")}
													</Button>
												),
											)}
										</div>
									</div>
								)}
							<div className="flex items-center gap-3 flex-wrap">
								<Button
									onClick={() => setOpenDetails(false)}
									variant="secondary"
									className="w-full sm:flex-1 font-semibold"
								>
									{trans?.trips?.close || trans?.tripDetails?.back || "Close"}
								</Button>
								{detailsTrips?.status !== "cancelled" &&
									detailsTrips?.status !== "completed" && (
										<Button
											type="button"
											onClick={() => setShowCancelModal(true)}
											disabled={cancelTripMutation.isPending}
											className="w-full sm:flex-1 font-semibold bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30 disabled:opacity-60"
										>
											{trans?.trips?.cancelTrip || "Cancel Trip"}
										</Button>
									)}
								{(detailsTrips?.status === "pending" ||
									detailsTrips?.cancelled_by_driver) &&
									!detailsTrips?.is_guest_driver && (
										<Button
											type="button"
											onClick={() => {
												setGuestDriverForm({
													name: "",
													phone: "",
													company: "",
													car_info: {
														brand: "",
														model: "",
														color: "",
														registration_number: "",
														year: "",
														additional_notes: "",
													},
												});
												setShowAssignGuestModal(true);
											}}
											className="w-full sm:flex-1 font-semibold bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30"
										>
											{trans?.trips?.assignToNewDriver ||
												trans?.trips?.assignGuestDriver ||
												"Assign to new driver"}
										</Button>
									)}
							</div>
						</div>
					</div>
				</div>
			)}
			{/* Cancel Trip Confirmation Modal */}
			<GlobalModal
				isOpen={showCancelModal}
				onClose={() => {
					if (!cancelTripMutation.isPending) {
						setShowCancelModal(false);
					}
				}}
			>
				<div className="bg-card p-6 rounded-2xl max-w-md w-full border border-border">
					<h2 className="text-xl font-bold text-foreground mb-4">
						{trans?.trips?.cancelTripTitle || "Cancel Trip"}
					</h2>
					<p className="text-sm text-muted-foreground mb-4">
						{trans?.trips?.cancelTripMessage ||
							"Are you sure you want to cancel this trip? This action cannot be undone."}
					</p>
					<div className="flex items-center gap-3 mt-4">
						<Button
							type="button"
							variant="secondary"
							onClick={() => setShowCancelModal(false)}
							disabled={cancelTripMutation.isPending}
							className="flex-1 font-semibold"
						>
							{trans?.trips?.cancelTripCancel || "No, Keep Trip"}
						</Button>
						<Button
							type="button"
							onClick={() => {
								if (detailsTrips?.id) {
									cancelTripMutation.mutate(detailsTrips.id);
								}
							}}
							disabled={cancelTripMutation.isPending || !detailsTrips?.id}
							className="flex-1 font-semibold bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30 disabled:opacity-60"
						>
							{cancelTripMutation.isPending
								? trans?.trips?.cancelling || "Cancelling..."
								: trans?.trips?.cancelTripConfirm || "Yes, Cancel Trip"}
						</Button>
					</div>
				</div>
			</GlobalModal>

			{/* Assign Guest Driver Modal */}
			<GlobalModal
				isOpen={showAssignGuestModal}
				onClose={() => {
					if (!assignGuestDriverMutation.isPending) {
						setGuestDriverForm({
							name: "",
							phone: "",
							company: "",
							car_info: {
								brand: "",
								model: "",
								color: "",
								registration_number: "",
								year: "",
								additional_notes: "",
							},
						});
						setShowAssignGuestModal(false);
					}
				}}
			>
				<div className="p-4 sm:p-6 w-full">
					<h2 className="text-xl font-bold text-foreground mb-4">
						{trans?.trips?.assignGuestTitle || "Assign Guest Driver"}
					</h2>
					<p className="text-sm text-muted-foreground mb-4">
						{trans?.trips?.assignGuestSubtitle ||
							"Assign a guest driver to handle this cancelled trip. The passenger will be notified by SMS."}
					</p>
					<form
						onSubmit={(e) => {
							e.preventDefault();
							if (
								!guestDriverForm.name.trim() ||
								!guestDriverForm.phone.trim()
							) {
								toast.error(
									trans?.trips?.assignGuestValidation ||
										"Name and phone are required",
								);
								return;
							}
							assignGuestDriverMutation.mutate();
						}}
						className="space-y-4 sm:space-y-6"
					>
						<div>
							<label className="block text-sm font-medium text-foreground mb-1">
								{trans?.trips?.assignGuestNameLabel ||
									trans?.trips?.guestNameLabel ||
									"Guest driver name"}
								<span className="text-red-500"> *</span>
							</label>
							<input
								type="text"
								value={guestDriverForm.name}
								onChange={(e) =>
									setGuestDriverForm((prev) => ({
										...prev,
										name: e.target.value,
									}))
								}
								className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary"
								placeholder={
									trans?.trips?.assignGuestNamePlaceholder ||
									trans?.trips?.guestNamePlaceholder ||
									"John Doe"
								}
							/>
						</div>
						<div>
							<label className="block text-sm font-medium text-foreground mb-1">
								{trans?.trips?.assignGuestPhoneLabel ||
									trans?.trips?.guestPhoneLabel ||
									"Guest driver phone"}
								<span className="text-red-500"> *</span>
							</label>
							<div
								className="flex items-center w-full p-3 border-2 border-border rounded-lg bg-background hover:border-primary/50 focus-within:border-primary transition-colors"
								dir="ltr"
							>
								<PhoneInputWithCountrySelect
									defaultCountry="GB"
									value={guestDriverForm.phone}
									onChange={(val) =>
										setGuestDriverForm((prev) => ({
											...prev,
											phone: val || "",
										}))
									}
									international
									countryCallingCodeEditable={false}
									className="w-full [&_.PhoneInputInput]:bg-transparent [&_.PhoneInputInput]:text-foreground [&_.PhoneInputInput]:border-none [&_.PhoneInputInput]:outline-none [&_.PhoneInputInput]:focus:outline-none [&_.PhoneInputInput]:focus:ring-0 [&_.PhoneInputInput]:placeholder:text-muted-foreground [&_.PhoneInputCountrySelect]:bg-transparent [&_.PhoneInputCountrySelect]:text-foreground [&_.PhoneInputCountrySelect]:border-none [&_.PhoneInputCountrySelect]:outline-none [&_.PhoneInputCountrySelect]:focus:outline-none [&_.PhoneInputCountryIcon]:opacity-80"
								/>
								<BsFillTelephoneFill className="mx-2 text-foreground flex-shrink-0" />
							</div>
						</div>
						<div>
							<label className="block text-sm font-medium text-foreground mb-1">
								{trans?.trips?.assignGuestCompanyLabel ||
									trans?.trips?.guestCompanyLabel ||
									"Company (optional)"}
							</label>
							<input
								type="text"
								value={guestDriverForm.company}
								onChange={(e) =>
									setGuestDriverForm((prev) => ({
										...prev,
										company: e.target.value,
									}))
								}
								className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
								placeholder={
									trans?.trips?.assignGuestCompanyPlaceholder ||
									trans?.trips?.guestCompanyPlaceholder ||
									"Uber"
								}
							/>
						</div>

						{/* Car Information Section */}
						<div className="pt-4 border-t border-border">
							<h3 className="text-base font-semibold text-foreground mb-3">
								{trans?.trips?.carInfoTitle || "Car Information (Optional)"}
							</h3>
							<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
								<div>
									<label className="block text-sm font-medium text-foreground mb-1">
										{trans?.trips?.carBrandLabel || "Brand"}
									</label>
									<input
										type="text"
										value={guestDriverForm.car_info.brand}
										onChange={(e) =>
											setGuestDriverForm((prev) => ({
												...prev,
												car_info: {
													...prev.car_info,
													brand: e.target.value,
												},
											}))
										}
										className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
										placeholder={trans?.trips?.carBrandPlaceholder || "Toyota"}
									/>
								</div>
								<div>
									<label className="block text-sm font-medium text-foreground mb-1">
										{trans?.trips?.carModelLabel || "Model"}
									</label>
									<input
										type="text"
										value={guestDriverForm.car_info.model}
										onChange={(e) =>
											setGuestDriverForm((prev) => ({
												...prev,
												car_info: {
													...prev.car_info,
													model: e.target.value,
												},
											}))
										}
										className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
										placeholder={trans?.trips?.carModelPlaceholder || "Camry"}
									/>
								</div>
								<div>
									<label className="block text-sm font-medium text-foreground mb-1">
										{trans?.trips?.carColorLabel || "Color"}
									</label>
									<input
										type="text"
										value={guestDriverForm.car_info.color}
										onChange={(e) =>
											setGuestDriverForm((prev) => ({
												...prev,
												car_info: {
													...prev.car_info,
													color: e.target.value,
												},
											}))
										}
										className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
										placeholder={trans?.trips?.carColorPlaceholder || "Black"}
									/>
								</div>
								<div>
									<label className="block text-sm font-medium text-foreground mb-1">
										{trans?.trips?.carRegistrationLabel ||
											"Registration Number"}
									</label>
									<input
										type="text"
										value={guestDriverForm.car_info.registration_number}
										onChange={(e) =>
											setGuestDriverForm((prev) => ({
												...prev,
												car_info: {
													...prev.car_info,
													registration_number: e.target.value,
												},
											}))
										}
										className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
										placeholder={
											trans?.trips?.carRegistrationPlaceholder || "ABC123"
										}
									/>
								</div>
								<div>
									<label className="block text-sm font-medium text-foreground mb-1">
										{trans?.trips?.carYearLabel || "Year (Optional)"}
									</label>
									<input
										type="number"
										min="1900"
										max={new Date().getFullYear() + 1}
										value={guestDriverForm.car_info.year}
										onChange={(e) =>
											setGuestDriverForm((prev) => ({
												...prev,
												car_info: {
													...prev.car_info,
													year: e.target.value,
												},
											}))
										}
										className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
										placeholder={trans?.trips?.carYearPlaceholder || "2020"}
									/>
								</div>
								<div className="sm:col-span-2">
									<label className="block text-sm font-medium text-foreground mb-1">
										{trans?.trips?.carAdditionalNotesLabel ||
											"Additional Notes (Optional)"}
									</label>
									<textarea
										value={guestDriverForm.car_info.additional_notes}
										onChange={(e) =>
											setGuestDriverForm((prev) => ({
												...prev,
												car_info: {
													...prev.car_info,
													additional_notes: e.target.value,
												},
											}))
										}
										rows={3}
										className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors resize-y"
										placeholder={
											trans?.trips?.carAdditionalNotesPlaceholder ||
											"Clean interior"
										}
									/>
								</div>
							</div>
						</div>

						<div className="mt-4 flex flex-col sm:flex-row items-center justify-end gap-3 pt-4 border-t border-border">
							<Button
								type="button"
								variant="secondary"
								onClick={() => setShowAssignGuestModal(false)}
								disabled={assignGuestDriverMutation.isPending}
							>
								{trans?.trips?.assignGuestCancel || "Cancel"}
							</Button>
							<Button
								type="submit"
								disabled={
									assignGuestDriverMutation.isPending ||
									!guestDriverForm.name.trim() ||
									!guestDriverForm.phone.trim()
								}
								className="bg-primary text-black font-semibold hover:bg-primary/90 disabled:opacity-60"
							>
								{assignGuestDriverMutation.isPending
									? trans?.trips?.assignGuestSubmitting || "Assigning..."
									: trans?.trips?.assignGuestConfirm || "Assign guest driver"}
							</Button>
						</div>
					</form>
				</div>
			</GlobalModal>

			{/* Status Transition Confirmation Modal */}
			<GlobalModal
				isOpen={showStatusModal}
				onClose={() => {
					if (!statusTransitionMutation.isPending) {
						setShowStatusModal(false);
						setSelectedNewStatus(null);
					}
				}}
				maxWidth="md"
			>
				<div
					className={`p-4 md:p-5 w-full ${locale === "ar" ? "text-right" : "text-left"}`}
					dir={locale === "ar" ? "rtl" : "ltr"}
				>
					<h2
						className={`text-lg font-bold text-foreground mb-2 ${locale === "ar" ? "text-right" : "text-left"}`}
					>
						{trans?.trips?.statusTransitionConfirmTitle ||
							"Confirm Status Change"}
					</h2>
					<p
						className={`text-sm text-muted-foreground mb-3 ${locale === "ar" ? "text-right" : "text-left"}`}
					>
						{trans?.trips?.statusTransitionConfirmMessage ||
							"Are you sure you want to change the trip status?"}
					</p>
					{selectedNewStatus && (
						<div
							className={`mb-3 p-3 bg-muted/50 rounded-lg border border-border ${locale === "ar" ? "text-right" : "text-left"}`}
						>
							<div
								className={`flex items-center justify-between gap-2 mb-2 ${locale === "ar" ? "flex-row-reverse" : ""}`}
							>
								<span className="text-xs text-muted-foreground">
									{trans?.trips?.currentStatus || "Current Status"}:
								</span>
								<span
									className={`text-xs font-semibold px-2 py-1 rounded ${getStatusColor(detailsTrips?.status || "")}`}
								>
									{trans?.status?.find(
										(s: any) => s.value === detailsTrips?.status,
									)?.title || detailsTrips?.status}
								</span>
							</div>
							<div
								className={`flex items-center justify-center my-1 ${locale === "ar" ? "rotate-180" : ""}`}
							>
								<svg
									className="w-4 h-4 text-muted-foreground"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										strokeLinecap="round"
										strokeLinejoin="round"
										strokeWidth={2}
										d="M19 9l-7 7-7-7"
									/>
								</svg>
							</div>
							<div
								className={`flex items-center justify-between gap-2 ${locale === "ar" ? "flex-row-reverse" : ""}`}
							>
								<span className="text-xs text-muted-foreground">
									{trans?.trips?.newStatus || "New Status"}:
								</span>
								<span className="text-xs font-semibold text-yellow-600 bg-yellow-500/20 px-2 py-1 rounded border border-yellow-500/30">
									{trans?.trips?.statusTransitions?.[selectedNewStatus] ||
										selectedNewStatus.replace(/_/g, " ")}
								</span>
							</div>
						</div>
					)}
					<div
						className={`flex items-center gap-2 mt-4 ${locale === "ar" ? "flex-row-reverse" : ""}`}
					>
						<Button
							type="button"
							variant="secondary"
							onClick={() => {
								setShowStatusModal(false);
								setSelectedNewStatus(null);
							}}
							disabled={statusTransitionMutation.isPending}
							className="flex-1 text-sm font-semibold"
						>
							{trans?.trips?.statusTransitionCancel || "Cancel"}
						</Button>
						<Button
							type="button"
							onClick={() => {
								if (detailsTrips?.id && selectedNewStatus) {
									statusTransitionMutation.mutate({
										tripId: detailsTrips.id,
										status: selectedNewStatus,
									});
								}
							}}
							disabled={
								statusTransitionMutation.isPending ||
								!selectedNewStatus ||
								!detailsTrips?.id
							}
							className="flex-1 text-sm font-semibold bg-yellow-500 hover:bg-yellow-600 text-white disabled:opacity-60"
						>
							{statusTransitionMutation.isPending
								? trans?.trips?.statusTransitionUpdating || "Updating..."
								: trans?.trips?.statusTransitionConfirm || "Confirm"}
						</Button>
					</div>
				</div>
			</GlobalModal>
		</>
	);
}
