import { runtimeText } from "@/lib/customer-runtime";
import { customerText } from "@/lib/customer-text";
import { passengerCapacityLabel, vehicleExample } from "@/lib/vehicle-presentation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Calendar,
  CarFront,
  Check,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Users,
} from "lucide-react";
import Image from "next/image";
import { Locale, localizedVehicleValue } from "../../../../i18n.config";
import { calculatTripCost, Choose_car, VehicleType } from ".";
import { Button } from "@/components/ui/button";

const disabledCarEnv = process.env.NEXT_PUBLIC_DISABLED_CAR_TYPES ?? "";
const disabledCarIndices = disabledCarEnv
  .split(",")
  .map((index) => {
    const num = parseInt(index.trim(), 10);
    return isNaN(num) ? null : num;
  })
  .filter((index): index is number => index !== null);

type typeProps = {
  selectedCar?: VehicleType;
  setSelectedCar: (data: VehicleType) => void;
  locale: Locale;
  Choose_car: Choose_car;
  rideOptions: calculatTripCost | null;
  tripDate: string;
  nextStep: () => void;
  prevStep: () => void;
};

export default function ModernChooseCar({
  selectedCar,
  setSelectedCar,
  locale,
  Choose_car,
  rideOptions,
  tripDate,
  nextStep,
  prevStep,
}: typeProps) {
  const isRTL = locale === "ar";

  const selectCar = (car: VehicleType) =>
    setSelectedCar(rideOptions ? { ...car, ...rideOptions } : car);

  const formatJourneyDate = () => {
    const [year, month, day] = tripDate.split("-").map(Number);
    if (!year || !month || !day) return tripDate;
    return new Intl.DateTimeFormat(locale, {
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(new Date(year, month - 1, day));
  };

  const formatPrice = (amount: number) =>
    new Intl.NumberFormat(locale, {
      style: "currency",
      currency: "GBP",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);

  return (
    <div className="w-full mx-auto" dir={isRTL ? "rtl" : "ltr"}>
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/25 px-4 py-2 mb-4 backdrop-blur-sm">
          <Calendar className="w-4 h-4 text-[#ffd100]" />
          <span className="text-white text-sm font-medium">{formatJourneyDate()}</span>
        </div>
        <h1 className="text-4xl lg:text-6xl font-bold text-white mb-4">
          {Choose_car.title}
        </h1>
        <p className="text-white/75 text-base sm:text-lg lg:text-xl max-w-2xl mx-auto px-4">
          {customerText(locale, "Select your preferred vehicle from our premium fleet")}
        </p>
      </div>

      <div className="mb-8">
        <Button
          onClick={prevStep}
          variant="outline"
          size="lg"
          className="bg-white/10 backdrop-blur-sm border-white/20 text-white hover:bg-white/20 hover:border-white/30"
        >
          {isRTL ? (
            <>
              <ChevronRight className="w-5 h-5 me-2" />
              {customerText(locale, "Back")}
            </>
          ) : (
            <>
              <ChevronLeft className="w-5 h-5 me-2" />
              {customerText(locale, "Back")}
            </>
          )}
        </Button>
      </div>

      {(!rideOptions?.car_type || rideOptions.car_type.length === 0) && (
        <div
          role="status"
          className="mb-6 rounded-2xl border border-white/20 bg-white/10 p-7 text-center text-white"
        >
          <p className="text-lg font-semibold">
            {customerText(locale, "No suitable vehicle is available for this journey online.")}
          </p>
          <p className="mt-2 text-sm text-white/70">
            {customerText(locale, "Please go back and check your passenger details or contact ACT for assistance.")}
          </p>
        </div>
      )}

      <div role="radiogroup" className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        {rideOptions?.car_type?.map((car, index) => {
          const isDisabled = disabledCarIndices.includes(index);
          const isSelected = selectedCar?.id === car.id && !isDisabled;
          const example = vehicleExample(locale, car.code);

          return (
            <Card
              key={car.id}
              role="radio"
              aria-checked={isSelected}
              aria-disabled={isDisabled}
              tabIndex={isDisabled ? -1 : 0}
              onClick={() => !isDisabled && selectCar(car)}
              onKeyDown={(event) => {
                if (isDisabled) return;
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  selectCar(car);
                }
              }}
              className={`group relative overflow-hidden transition-all duration-300 ${
                isDisabled
                  ? "cursor-not-allowed opacity-55 grayscale"
                  : "cursor-pointer hover:-translate-y-0.5 hover:border-white/35 hover:shadow-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ffd100]"
              } ${
                isSelected
                  ? "border-2 border-[#ffd100] bg-[#ffd100]/10 shadow-2xl"
                  : "border border-white/15 bg-black/35 backdrop-blur-xl"
              }`}
            >
              <div className="relative h-48 sm:h-56 overflow-hidden border-b border-white/10 bg-gradient-to-b from-white to-zinc-100">
                {car.icon_url ? (
                  <Image
                    src={car.icon_url}
                    alt={localizedVehicleValue(car, "name", locale)}
                    fill
                    className="object-contain p-4 sm:p-6 drop-shadow-2xl transition-transform duration-300 group-hover:scale-[1.03]"
                    sizes="(max-width: 1280px) 100vw, 50vw"
                    quality={100}
                  />
                ) : (
                  <div
                    className="flex h-full w-full flex-col items-center justify-center gap-3 text-zinc-600"
                    role="img"
                    aria-label={localizedVehicleValue(car, "name", locale)}
                  >
                    <CarFront className="h-16 w-16" aria-hidden="true" />
                    <span className="text-sm font-semibold">
                      {localizedVehicleValue(car, "name", locale)}
                    </span>
                  </div>
                )}
                <div className="absolute start-4 top-4">
                  <Badge className="border border-black/10 bg-black/75 text-white backdrop-blur-sm">
                    {runtimeText(locale, "representativeVehicle")}
                  </Badge>
                </div>
                {isSelected && (
                  <div className="absolute end-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-[#ffd100] shadow-lg">
                    <CheckCircle className="h-5 w-5 text-[#2D2E2E]" />
                  </div>
                )}
                {isDisabled && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/55 text-sm font-semibold text-white">
                    {customerText(locale, "Coming Soon")}
                  </div>
                )}
              </div>

              <CardContent className="p-5 sm:p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h3 className={`text-2xl font-bold transition-colors ${
                      isSelected ? "text-[#ffd100]" : "text-white group-hover:text-[#ffd100]"
                    }`}>
                      {localizedVehicleValue(car, "name", locale)}
                    </h3>
                    {example && (
                      <p className="mt-1 text-sm font-medium text-white/65">{example}</p>
                    )}
                  </div>
                  <div className="shrink-0 text-end">
                    <p className="text-xs uppercase tracking-wider text-white/50">
                      {runtimeText(locale, "oneWayTotal")}
                    </p>
                    <p className="mt-1 text-2xl font-bold text-white">
                      {formatPrice(car.total_cost)}
                    </p>
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap gap-2">
                  <Badge variant="outline" className="gap-1.5 border-white/15 bg-white/5 px-3 py-1.5 text-white/80">
                    <Users className="h-4 w-4" />
                    {passengerCapacityLabel(locale, car.max_passengers_count)}
                  </Badge>
                  <Badge variant="outline" className="gap-1.5 border-white/15 bg-white/5 px-3 py-1.5 text-white/80">
                    <ShieldCheck className="h-4 w-4" />
                    {runtimeText(locale, "privateTransfer")}
                  </Badge>
                </div>

                {localizedVehicleValue(car, "desc", locale) && (
                  <p className="mt-4 text-sm leading-6 text-white/70">
                    {localizedVehicleValue(car, "desc", locale)}
                  </p>
                )}

                <div className={`mt-5 flex items-center justify-between rounded-xl border px-4 py-3 transition-colors ${
                  isSelected
                    ? "border-[#ffd100]/60 bg-[#ffd100]/10 text-[#ffd100]"
                    : "border-white/10 bg-white/[0.04] text-white/75"
                }`}>
                  <span className="text-sm font-semibold">
                    {isSelected
                      ? runtimeText(locale, "selectedVehicle")
                      : runtimeText(locale, "selectThisClass")}
                  </span>
                  {isSelected ? (
                    <Check className="h-5 w-5" />
                  ) : isRTL ? (
                    <ChevronLeft className="h-5 w-5" />
                  ) : (
                    <ChevronRight className="h-5 w-5" />
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <p className="mx-auto mt-5 max-w-3xl text-center text-xs leading-5 text-white/50">
        {runtimeText(locale, "vehicleMayVary")}
      </p>

      {selectedCar && (
        <div className="mt-7 text-center px-4">
          <Button
            onClick={nextStep}
            size="lg"
            className="w-full sm:w-auto bg-[#ffd100] hover:bg-[#ffd100]/90 text-[#2D2E2E] font-bold px-10 py-4 text-base sm:text-lg shadow-xl"
          >
            {Choose_car.button || customerText(locale, "Continue")}
          </Button>
        </div>
      )}
    </div>
  );
}
