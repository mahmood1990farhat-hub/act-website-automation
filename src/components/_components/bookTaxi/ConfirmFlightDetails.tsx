import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
	ChevronLeft,
	MapPin,
	Calendar,
	Clock,
	Users,
	Car,
	Luggage,
	Edit2,
	Route,
	CreditCard,
	CheckCircle,
	Navigation,
} from "lucide-react";
import { calculatTripCost, home, RoutePoint } from ".";
import { postData } from "@/lib/api/postData";
import { getCookie } from "cookies-next";
import CarLoading from "../loading/CarLoading";
import MapView from "./MapView";
import { Locale } from "../../../../i18n.config";
import { MinutesToTimeString } from "@/lib/minutesToTimeString";
import Image from "next/image";

type typeProps = {
	trans: home;
	rideOptions: calculatTripCost | null;
	locale: Locale;
	data: {
		routePoints: RoutePoint[];
		time: string;
		carName: string;
		date: string;
		carImage: string;
		distance: string;
		smallSuitcase: number;
		largeSuitcase: number;
		numberOfPassengers: number;
		cartype?: number;
		cost: number | undefined;
		airport_vat?: number;
		regular_vat?: number;
		total_cost?: number;
		trip_duration_minutes?: number;
	};
	setStep: (n: number) => void;
	step: number;
	editDatelis: () => void;
	setClientSecret: (clientSecret: string) => void;
};

export default function ModernConfirmFlightDetails({
	trans,
	data,
	setStep,
	step,
	editDatelis,
	setClientSecret,
	rideOptions,
	locale,
}: typeProps) {
	const [token, setToken] = useState<string | undefined>();
	const [isLoading, setIsLoading] = useState(false);
	const isRTL = locale === "ar";

	useEffect(() => {
		setToken(getCookie("userToken") as string | undefined);
	}, []);

	useEffect(() => {
		if (
			step === 3 &&
			token &&
			typeof window !== "undefined" &&
			window.sessionStorage.getItem("resumeBookingAfterLogin") === "true"
		) {
			window.sessionStorage.removeItem("resumeBookingAfterLogin");
			onSubmit();
		}
	}, [step, token]);

	const pickup =
		data.routePoints.find((r) => r.type === "pickup")?.point?.description ||
		"-";
	const stops = data.routePoints
		.filter((r) => r.type === "stop")
		.map((r) => r.point?.description || "-");
	const dropoff =
		data.routePoints.find((r) => r.type === "dropoff")?.point?.description ||
		"-";
	const cost = data.cost || 0;
	const vat = data.regular_vat || 0;
	const airport_vat = data.airport_vat || 0;
	const totalCost = data.total_cost;

	// Arabic text alternatives
	const texts = {
		confirmDetails: isRTL ? "تأكيد تفاصيل الحجز" : "Confirm Booking Details",
		tripDetails: isRTL ? "تفاصيل الرحلة" : "Trip Details",
		passengerInfo: isRTL ? "معلومات الركاب" : "Passenger Information",
		vehicleDetails: isRTL ? "تفاصيل المركبة" : "Vehicle Details",
		costBreakdown: isRTL ? "تفاصيل التكلفة" : "Cost Breakdown",
		back: isRTL ? "العودة" : "Back",
		edit: isRTL ? "تعديل" : "Edit",
		confirm: isRTL ? "التأكيد و المتابعة" : "Confirm & Continue",
		pickup: isRTL ? "نقطة الانطلاق" : "Pickup Location",
		dropoff: isRTL ? "نقطة الوصول" : "Drop-off Location",
		stops: isRTL ? "نقاط التوقف" : "Stop Points",
		distance: isRTL ? "المسافة" : "Distance",
		date: isRTL ? "التاريخ" : "Date",
		time: isRTL ? "الوقت المتوقع للوصول" : "ETA",
		timeTrip: isRTL ? "مدة الرحلة" : "Trip Duration",
		passengers: isRTL ? "عدد الركاب" : "Passengers",
		smallLuggage: isRTL ? "حقائب صغيرة" : "Small Luggage",
		largeLuggage: isRTL ? "حقائب كبيرة" : "Large Luggage",
		vehicleType: isRTL ? "نوع المركبة" : "Vehicle Type",
		baseCost: isRTL ? "تكلفة الرحلة" : "Trip Cost",
		airportVAT: isRTL ? "رسوم المطار" : "Airport Charges",
		regularVAT: isRTL ? "الضريبة 20%" : "Vat 20%",
		totalCost: isRTL ? "التكلفة الإجمالية" : "Total Cost",
		routeMap: isRTL ? "خريطة المسار" : "Route Map",
	};

	const onSubmit = async () => {
		setIsLoading(true);
		if (!token) {
			if (typeof window !== "undefined") {
				window.sessionStorage.setItem("resumeBookingAfterLogin", "true");
			}
			setIsLoading(false);
			setStep(6);
		} else {
			const stop_points = data.routePoints
				.filter((p) => p.type === "stop")
				.map((p) => {
					return {
						point_lat: p.point?.coordinates.lat || 0,
						point_lng: p.point?.coordinates.lng || 0,
					};
				});

			const dropoffPoint = data.routePoints.find((it) => it.type === "dropoff");
			const pickupPoint = data.routePoints.find((it) => it.type === "pickup");

			const dropoff_location = {
				lat: dropoffPoint?.point?.coordinates?.lat,
				lng: dropoffPoint?.point?.coordinates?.lng,
			};
			const pickup_location = {
				lat: pickupPoint?.point?.coordinates?.lat,
				lng: pickupPoint?.point?.coordinates?.lng,
			};

			// if (data.routePoints[0].point?.id) {
			//   pickup_location = {
			//     airport_id: data.routePoints[0].point?.id,
			//   };
			//   dropoff_location = {
			//     lat: dropoffPoint?.point?.coordinates?.lat,
			//     lng: dropoffPoint?.point?.coordinates?.lng,
			//   };
			// } else {
			//   pickup_location = {
			//     lat: data.routePoints[0].point?.coordinates?.lat,
			//     lng: data.routePoints[0].point?.coordinates?.lng,
			//   };
			//   dropoff_location = {
			//     airport_id: dropoffPoint?.point?.id,
			//   };
			// }

			const bodyData: any = {
				pickup_location,
				dropoff_location,
				trip_date: data.date,
				trip_time: data.time,
				passengers_count: data.numberOfPassengers,
				large_suitcase: data.largeSuitcase,
				small_suitcase: data.smallSuitcase,
				car_type: data.cartype,
			};

			// Note: stop_points might not be needed for initiate-payment
			// If the API requires it, uncomment the following:
			// if (stop_points.length > 0) {
			//   bodyData.stop_points = stop_points;
			// }

			try {
				const res = await postData<any>({
					endpoint: "/api/trips/initiate-payment/",
					token: token,
					body: {
						...bodyData,
					},
				});
				setIsLoading(false);
				setStep(4);
				// The API returns client_secret in the response
				setClientSecret(res.client_secret);
			} catch (error) {
				console.error(error);
				setIsLoading(false);
			}
		}
	};

	return (
		<div className={`w-full max-w-7xl mx-auto`} dir={isRTL ? "rtl" : "ltr"}>
			{/* Header */}
			<div className="text-center mb-8">
				<h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4">
					{texts.confirmDetails}
				</h1>
				<p className="text-white/80 text-sm sm:text-base lg:text-lg max-w-2xl mx-auto">
					{isRTL
						? "تأكد من تفاصيل رحلتك قبل المتابعة"
						: "Review your trip details before proceeding"}
				</p>
			</div>

			{/* Back Button */}
			<div className="mb-6">
				<Button
					onClick={() => setStep(2)}
					variant="outline"
					size="lg"
					className="bg-white/10 backdrop-blur-sm border-white/20 text-white hover:bg-white/20 hover:border-white/30 transition-all duration-300 cursor-pointer hover:text-white"
				>
					<ChevronLeft
						className={`w-4 h-4 sm:w-5 sm:h-5 ${isRTL ? "rotate-180 ml-2" : "mr-2"}`}
					/>
					{texts.back}
				</Button>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
				{/* Left Side - Trip Details */}
				<div className="space-y-6">
					{/* Trip Details Card */}
					<Card className="bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
						<CardHeader className="pb-4">
							<div className="flex items-center justify-between">
								<CardTitle
									className={`text-white flex items-center gap-2 text-lg sm:text-xl`}
								>
									<Route className="w-5 h-5 text-[#ffd100]" />
									{texts.tripDetails}
								</CardTitle>
								<Button
									variant="ghost"
									size="sm"
									onClick={editDatelis}
									className="text-[#22C822] hover:bg-[#22C822]/10 hover:text-white h-8 px-2 cursor-pointer"
								>
									<Edit2 className="w-4 h-4 mr-1" />
									{texts.edit}
								</Button>
							</div>
						</CardHeader>
						<CardContent className="space-y-4">
							<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
								<div className="space-y-3">
									<div>
										<div className="flex items-center gap-2 text-white/60 mb-1">
											<MapPin className="w-4 h-4" />
											<span className="text-xs sm:text-sm font-medium">
												{texts.pickup}
											</span>
										</div>
										<p className="text-white text-sm pl-6">{pickup}</p>
									</div>

									{stops.length > 0 && (
										<div>
											<div className="flex items-center gap-2 text-white/60 mb-1">
												<Navigation className="w-4 h-4" />
												<span className="text-xs sm:text-sm font-medium">
													{texts.stops}
												</span>
											</div>
											<div className="pl-6 space-y-1">
												{stops.map((stop, i) => (
													<p key={i} className="text-white text-sm">
														{i + 1}. {stop}
													</p>
												))}
											</div>
										</div>
									)}

									<div>
										<div className="flex items-center gap-2 text-white/60 mb-1">
											<MapPin className="w-4 h-4" />
											<span className="text-xs sm:text-sm font-medium">
												{texts.dropoff}
											</span>
										</div>
										<p className="text-white text-sm pl-6">{dropoff}</p>
									</div>
									<div>
										<div className="flex items-center gap-2 text-white/60 mb-1">
											<Route className="w-4 h-4" />
											<span className="text-xs sm:text-sm font-medium">
												{texts.distance}
											</span>
										</div>
										<p className="text-white text-sm">{data.distance}</p>
									</div>
								</div>

								<div className="space-y-3">
									<div>
										<div className="flex items-center gap-2 text-white/60 mb-1">
											<Calendar className="w-4 h-4" />
											<span className="text-xs sm:text-sm font-medium">
												{texts.date}
											</span>
										</div>
										<p className="text-white text-sm">
											{new Date(data.date).toLocaleDateString(locale ?? "en", {
												day: "numeric",
												month: "short",
												year: "numeric",
											})}
										</p>
									</div>

									<div>
										<div className="flex items-center gap-2 text-white/60 mb-1">
											<Clock className="w-4 h-4" />
											<span className="text-xs sm:text-sm font-medium">
												{texts.time}
											</span>
										</div>
										<p className="text-white text-sm">{data.time}</p>
									</div>

									<div>
										<div className="flex items-center gap-2 text-white/60 mb-1">
											<Clock className="w-4 h-4" />
											<span className="text-xs sm:text-sm font-medium">
												{texts.timeTrip}
											</span>
										</div>
										<p className="text-white text-sm">
											{MinutesToTimeString(data.trip_duration_minutes ?? 0)}
										</p>
									</div>
								</div>
							</div>
						</CardContent>
					</Card>

					{/* Passenger & Luggage Info */}
					<Card className="bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
						<CardHeader className="pb-4">
							<CardTitle
								className={`text-white flex items-center gap-2 text-lg sm:text-xl`}
							>
								<Users className="w-5 h-5 text-[#ffd100]" />
								{texts.passengerInfo}
							</CardTitle>
						</CardHeader>
						<CardContent>
							<div className="grid grid-cols-3 gap-4">
								<div className="text-center">
									<div className="w-12 h-12 sm:w-16 sm:h-16 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-2">
										<Users className="w-5 h-5 sm:w-6 sm:h-6 text-[#ffd100]" />
									</div>
									<p className="text-white font-bold text-lg sm:text-xl">
										{data.numberOfPassengers}
									</p>
									<p className="text-white/60 text-xs sm:text-sm">
										{texts.passengers}
									</p>
								</div>

								<div className="text-center">
									<div className="w-12 h-12 sm:w-16 sm:h-16 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-2">
										<Luggage className="w-5 h-5 sm:w-6 sm:h-6 text-blue-400" />
									</div>
									<p className="text-white font-bold text-lg sm:text-xl">
										{data.smallSuitcase}
									</p>
									<p className="text-white/60 text-xs sm:text-sm">
										{texts.smallLuggage}
									</p>
								</div>

								<div className="text-center">
									<div className="w-12 h-12 sm:w-16 sm:h-16 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-2">
										<Luggage className="w-5 h-5 sm:w-6 sm:h-6 text-purple-400" />
									</div>
									<p className="text-white font-bold text-lg sm:text-xl">
										{data.largeSuitcase}
									</p>
									<p className="text-white/60 text-xs sm:text-sm">
										{texts.largeLuggage}
									</p>
								</div>
							</div>
						</CardContent>
					</Card>

					{/* Vehicle Details */}
					<Card className="bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
						<CardHeader className="pb-4">
							<CardTitle
								className={`text-white flex items-center gap-2 text-lg sm:text-xl`}
							>
								<Car className="w-5 h-5 text-[#ffd100]" />
								{texts.vehicleDetails}
							</CardTitle>
						</CardHeader>
						<CardContent>
							<div className="flex items-center gap-4">
								<div className="w-16 h-16 sm:w-20 sm:h-20 bg-white/5 rounded-xl p-2 flex-shrink-0">
									<div className="w-full h-full relative">
										{/* You can add car image here if available */}
										{data.carImage ? (
											<div className="relative h-16 w-16">
												<Image
													src={data.carImage}
													alt="car"
													fill
													className="object-contain"
												/>
											</div>
										) : (
											<Car className="w-full h-full text-white/40" />
										)}
									</div>
								</div>
								<div className="flex-1">
									<h3 className="text-white font-bold text-lg sm:text-xl mb-1">
										{data.carName || "-"}
									</h3>
									<div className="flex items-center gap-4 text-white/60">
										<span className="text-sm">
											{data.numberOfPassengers} {texts.passengers}
										</span>
										<Badge
											variant="outline"
											className="bg-[#ffd100]/20 border-[#ffd100]/50 text-[#ffd100] text-xs"
										>
											{isRTL ? "فئة مميزة" : "Premium"}
										</Badge>
									</div>
								</div>
							</div>
						</CardContent>
					</Card>

					{/* Cost Breakdown */}
					<Card className="bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
						<CardHeader className="pb-4">
							<CardTitle
								className={`text-white flex items-center gap-2 text-lg sm:text-xl`}
							>
								<CreditCard className="w-5 h-5 text-[#ffd100]" />
								{texts.costBreakdown}
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-4">
							<div className="space-y-3">
								<div className={`flex justify-between items-center`}>
									<span className="text-white/80">{texts.baseCost}</span>
									<span className="text-white font-semibold">
										£{cost.toFixed(2) + (airport_vat.toFixed(2)?? 0) }
									</span>
								</div>

							

								{vat > 0 && (
									<div className={`flex justify-between items-center`}>
										<span className="text-white/80">{texts.regularVAT}</span>
										<span className="text-white font-semibold">
											£{vat.toFixed(2)}
										</span>
									</div>
								)}
							</div>

							<Separator className="bg-white/20" />

							<div className={`flex justify-between items-center`}>
								<span className="text-white font-bold text-lg sm:text-xl">
									{texts.totalCost}
								</span>
								<Badge
									variant="secondary"
									className="bg-[#ffd100] text-[#2D2E2E] font-bold text-lg sm:text-xl px-3 py-2"
								>
									£{totalCost?.toFixed(2)}
								</Badge>
							</div>
						</CardContent>
					</Card>

					{/* Action Buttons */}
					<div className="space-y-4">
						<Button
							onClick={onSubmit}
							disabled={isLoading}
							className="w-full bg-[#ffd100] hover:bg-[#ffd100]/90 text-[#2D2E2E] font-bold py-6 text-base sm:text-lg shadow-xl transition-all duration-300 cursor-pointer"
						>
							{isLoading ? (
								<div className="flex items-center gap-2">
									<CarLoading />
									<span>{isRTL ? "جاري المعالجة..." : "Processing..."}</span>
								</div>
							) : (
								<div className="flex items-center gap-2">
									<CheckCircle className="w-5 h-5" />
									{texts.confirm}
								</div>
							)}
						</Button>

						<div className="flex flex-col  items-center justify-center gap-2 sm:gap-4 text-white/60 text-xs sm:text-sm text-center sm:text-left">
					

							
							<div className="flex items-center justify-center gap-1 max-w-xs sm:max-w-none">
								<CheckCircle className="w-4 h-4 text-green-400 shrink-0" />
								<span>
									{isRTL
										? "استمتع بإلغاء مجاني حتى 24 ساعة قبل موعد الاستلام المحدد"
										: "Enjoy free cancellation up to 24 hours before your scheduled pickup"}
								</span>
							</div>
									<div className="flex items-center justify-center gap-1 text-nowrap">
								<CheckCircle className="w-4 h-4 text-green-400 shrink-0" />
								<span>{isRTL ? "دفع آمن" : "Secure Payment"}</span>
							</div>
						</div>
					</div>
				</div>

				{/* Right Side - Map */}
				<div className="max-lg:-order-1" style={{ display: "unset" }}>
					<div className="lg:sticky lg:top-8">
						<Card className="bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl overflow-hidden">
							<CardHeader className="pb-4">
								<CardTitle
									className={`text-white flex items-center gap-2 text-lg sm:text-xl`}
								>
									<MapPin className="w-5 h-5 text-[#ffd100]" />
									{texts.routeMap}
								</CardTitle>
							</CardHeader>
							<CardContent className="p-0">
								<div className="w-full h-64 sm:h-80 lg:h-[500px] relative">
									<MapView
										routePolyline={
											rideOptions?.route_polyline ||
											"vcyHjlwA?kC@ED@xCAPVHP@fAAvACz@Kl@Un@W`@QLULsAPkDb@a@Bc@A]K]Qy@u@aBwBWOc@OcCOsCQyE@aPDiMBK@SHSNONMb@U~@Gd@Cb@@`@d@tD@`C@pDCfAF`@HRLPNLLAPXT\\FF?R?n@?tEAvB?nEAtA?vFD~XCdNBbQ@|@PxACD?F@NELCBAxDEp@B|N@f@BD@L?PEHC@@lF@~DBhDJdARlAx@pDV|AJfAB`A?bBAtAA|@DT?p@?fC?jBBT?TFtCD|B@x@DhAL|BjA`S^jEPjAHZXx@R^j@r@|@f@^LnBn@rA\\z@LbAD~@CjCg@fDcAlAm@h@g@`AeAfAyAn@y@bAqAr@s@hA}@|@k@dAg@hAa@hA_@t@M~@ETChBHfCJfCLN@NGl@@t@Dt@LlBr@vAd@nCt@b@DZ@d@G\\M`@W\\a@f@cAVaAF_@Dc@NoDF}@F]Ne@NYNKNG\\EZ@~@ANKf@o@Ja@N{@f@{DPcCJgCDiCA{XAaPBwBLqBFe@b@cBXs@Zk@f@k@hAu@r@m@h@w@z@yAr@kAf@cAp@yBTcAVgBRoD^sITsHHuATmDPmDd@oKf@uKFkD\\kGZgFJwAXcCl@yETmBF{@BsAI_BGKEa@Ba@DOLIJAJBPVDN?H?DTLPJRHt@Z\\DZ?RGFETO@G@IBGFMJIJCVDPRH\\@f@Ml@KJUBMCWSAKw@CK?OtA"
										}
									/>
								</div>
							</CardContent>
						</Card>
					</div>
				</div>
			</div>
		</div>
	);
}
