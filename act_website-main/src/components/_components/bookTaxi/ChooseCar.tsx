import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ChevronLeft,
  ChevronRight,
  Users,
  Clock,
  Star,
  CheckCircle,
  Calendar,
  MapPin,
} from "lucide-react";
import Image from "next/image";
import { Locale } from "../../../../i18n.config";
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
  nextStep: () => void;
  prevStep: () => void;
};

export default function ModernChooseCar({
  selectedCar,
  setSelectedCar,
  locale,
  Choose_car,
  rideOptions,
  nextStep,
  prevStep,
}: typeProps) {
  const isRTL = locale === "ar";
  const isLoading = false; // Replace with your actual loading state

  const handleCarSelect = (car: VehicleType) => {
    setSelectedCar(car);
    // Auto advance after selection with slight delay for visual feedback
    setTimeout(() => {
      nextStep();
    }, 300);
  };

  // Arabic text alternatives
  const texts = {
    back: isRTL ? "العودة" : "Back",
    mostPopular: isRTL ? "الأكثر شعبية" : "Most Popular",
    passengers: isRTL ? "راكب" : "passengers",
    professionalDriver: isRTL ? "سائق محترف" : "Professional Driver",
    premiumComfort: isRTL ? "راحة فائقة" : "Premium Comfort",
    meetGreet: isRTL ? "استقبال ومرافقة" : "Meet & Greet",
    freeCancellation: isRTL
      ? "إلغاء مجاني حتى ساعة واحدة"
      : "Free cancellation up to 1 hour",
    realTimeTracking: isRTL ? "تتبع فوري متضمن" : "Real-time tracking included",
    continue: isRTL ? "متابعة" : "Continue",
    selectVehicle: isRTL
      ? "اختر مركبتك المفضلة من أسطولنا المميز"
      : "Select your preferred vehicle from our premium fleet",
  };

  const SkeletonCard = () => (
    <Card className="bg-white/10 backdrop-blur-xl border border-white/20 animate-pulse">
      <CardContent className="p-4 sm:p-6">
        <div
          className={`flex items-center gap-3 sm:gap-6 ${
            isRTL ? "flex-row-reverse" : ""
          }`}
        >
          <div className="w-16 h-16 sm:w-24 sm:h-24 bg-white/20 rounded-xl flex-shrink-0" />
          <div className="flex-1 space-y-2 sm:space-y-3 min-w-0">
            <div className="h-4 sm:h-6 bg-white/20 rounded w-1/3" />
            <div className="h-3 sm:h-4 bg-white/20 rounded w-3/4" />
            <div className="h-4 sm:h-5 bg-white/20 rounded w-1/4" />
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className={`w-full mx-auto`} dir={isRTL ? "rtl" : "ltr"}>
      {/* Header Section */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-full px-4 py-2 mb-4">
          <Calendar className="w-4 h-4 text-[#ffd100]" />
          <span className="text-white text-sm font-medium">
            {`${new Date().toLocaleDateString(locale, {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}`}
          </span>
        </div>
        <h1 className="text-4xl lg:text-6xl font-bold text-white mb-4">
          {Choose_car.title}
        </h1>
        <p className="text-white/80 text-base sm:text-lg lg:text-xl   max-w-2xl mx-auto px-4">
          {texts.selectVehicle}
        </p>
      </div>

      {/* Back Button */}
      <div className="mb-8">
        <Button
          onClick={prevStep}
          variant="outline"
          size="lg"
          className="bg-white/10 backdrop-blur-sm border-white/20 text-white hover:bg-white/20 hover:border-white/30 transition-all duration-300 cursor-pointer"
        >
          {isRTL ? (
            <>
              <ChevronRight className="w-5 h-5 mr-2" />
              العودة
            </>
          ) : (
            <>
              <ChevronLeft className="w-5 h-5 mr-2" />
              Back
            </>
          )}
        </Button>
      </div>

      {/* Car Selection Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {isLoading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          rideOptions?.car_type?.map((car, index) => {
            // const isDisabled = disabledCarIndices.includes(index);
            const isDisabled = false

            return (
              <Card
                key={car.id}
                className={`group transition-all duration-300 transform ${
                  isDisabled
                    ? "cursor-not-allowed opacity-60 grayscale"
                    : "cursor-pointer hover:scale-[1.01] sm:hover:scale-[1.02] hover:shadow-2xl"
                } ${
                  selectedCar?.id === car.id && !isDisabled
                    ? "bg-[#ffd100]/20 backdrop-blur-xl border-2 border-[#ffd100] shadow-2xl scale-[1.01] sm:scale-[1.02]"
                    : "bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/15 hover:border-white/30"
                }`}
                onClick={() => {
                  if (!isDisabled) {
                    handleCarSelect({...car, ...rideOptions});
                  }
                }}
                aria-disabled={isDisabled}
              >
                <CardContent className="p-4 sm:p-6">
                  <div className={`flex items-center gap-3 sm:gap-6`}>
                    {/* Car Image */}
                    <div className="relative self-start flex-shrink-0">
                      <div className="w-16 h-16 sm:w-20 sm:h-20 lg:w-24 lg:h-24 relative rounded-xl overflow-hidden bg-white p-1 sm:p-2">
                        <Image
                          src={car.icon_url}
                          alt={car[`name_${locale}`]}
                          fill
                          className="object-contain drop-shadow-lg"
                          sizes="(max-width: 640px) 64px, (max-width: 768px) 80px, 96px"
                          quality={100}
                        />
                      </div>

                      {/* Selected Indicator */}
                      {selectedCar?.id === car.id && (
                        <div className="absolute -top-1 sm:-top-2 -right-1 sm:-right-2 w-6 h-6 sm:w-8 sm:h-8 bg-[#ffd100] rounded-full flex items-center justify-center shadow-lg">
                          <CheckCircle className="w-3 h-3 sm:w-5 sm:h-5 text-[#2D2E2E]" />
                        </div>
                      )}
                      {isDisabled && (
                        <div className="absolute inset-0 bg-black/40 rounded-xl flex items-center justify-center text-white text-xs sm:text-sm font-semibold">
                          Coming Soon
                        </div>
                      )}
                    </div>

                    {/* Car Details */}
                    <div
                      className={`flex-1 min-w-0 ${
                        isRTL ? "text-right" : "text-left"
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between mb-2 sm:mb-3 gap-2">
                        <div className="min-w-0 flex-1">
                          <h3
                            className={`text-lg sm:text-xl lg:text-2xl font-bold mb-1 sm:mb-2 truncate ${
                              selectedCar?.id === car.id && !isDisabled
                                ? "text-[#ffd100]"
                                : "text-white"
                            } group-hover:text-[#ffd100] transition-colors`}
                          >
                            {car[`name_${locale}`]}
                          </h3>

                          <div
                            className={`flex items-center gap-2 sm:gap-4 mb-2 sm:mb-3 text-xs sm:text-sm`}
                          >
                            <div className="flex items-center gap-1 text-white/60">
                              <Users className="w-3 h-3 sm:w-4 sm:h-4 flex-shrink-0" />
                              <span>
                                {car?.max_passengers_count} {texts.passengers}
                              </span>
                            </div>
                            <div className="flex items-center gap-1 text-white/60">
                              <Star className="w-3 h-3 sm:w-4 sm:h-4 fill-yellow-400 text-yellow-400 flex-shrink-0" />
                              <span>4.9</span>
                            </div>
                          </div>
                        </div>

                        {/* Price Badge */}
                        <div className="flex-shrink-0">
                          <Badge
                            variant="secondary"
                            className={`text-sm sm:text-lg font-bold px-2 sm:px-4 py-1 sm:py-2 ${
                              selectedCar?.id === car.id && !isDisabled
                                ? "bg-[#ffd100] text-[#2D2E2E]"
                                : "bg-white/20 text-white"
                            }`}
                          >
                            £{car.total_cost}
                          </Badge>
                        </div>
                      </div>

                      <p className="text-white/80 text-xs sm:text-sm lg:text-base leading-relaxed mb-3 sm:mb-4 line-clamp-2 sm:line-clamp-none">
                        {car[`desc_${locale}`]}
                      </p>

                      {/* Features */}
                      <div className="flex flex-wrap gap-1 sm:gap-2">
                        <Badge
                          variant="outline"
                          className="bg-white/5 border-white/20 text-white/80 text-xs px-2 py-1"
                        >
                          {texts.professionalDriver}
                        </Badge>
                        <Badge
                          variant="outline"
                          className="bg-white/5 border-white/20 text-white/80 text-xs px-2 py-1"
                        >
                          {texts.premiumComfort}
                        </Badge>
                        {/* <Badge variant="outline" className="bg-white/5 border-white/20 text-white/80 text-xs px-2 py-1 hidden sm:inline-flex">
                        {texts.meetGreet}
                      </Badge> */}
                      </div>
                    </div>

                    {/* Selection Arrow */}
                    <div
                      className={`flex-shrink-0 opacity-50 group-hover:opacity-100 transition-opacity ${
                        isRTL ? "mr-2 sm:mr-4" : "ml-2 sm:ml-4"
                      }`}
                    >
                      {isRTL ? (
                        <ChevronLeft className="w-4 h-4 sm:w-6 sm:h-6 text-white" />
                      ) : (
                        <ChevronRight className="w-4 h-4 sm:w-6 sm:h-6 text-white" />
                      )}
                    </div>
                  </div>

                  {/* Popular/Recommended Badge */}
                  {index === 0 && !isDisabled && (
                    <div
                      className={`absolute -top-2 sm:-top-3 ${
                        isRTL ? "right-3 sm:right-6" : "left-3 sm:left-6"
                      }`}
                    >
                      <Badge className="bg-[#4b1679] hover:bg-[#4b1679] text-white px-2 sm:px-3 py-1 shadow-lg text-xs sm:text-sm">
                        {texts.mostPopular}
                      </Badge>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      {/* Bottom Info */}
      {/* <div className="mt-6 sm:mt-8 text-center px-4">
        <div className="inline-flex flex-col sm:flex-row items-center gap-2 sm:gap-4 bg-white/10 backdrop-blur-sm rounded-full px-4 sm:px-6 py-3">
          <div className="flex items-center gap-2 text-white/80">
            <Clock className="w-3 h-3 sm:w-4 sm:h-4 flex-shrink-0" />
            <span className="text-xs sm:text-sm text-center">{texts.freeCancellation}</span>
          </div>
          <div className="w-px h-4 bg-white/20 hidden sm:block"></div>
          <div className="flex items-center gap-2 text-white/80">
            <MapPin className="w-3 h-3 sm:w-4 sm:h-4 flex-shrink-0" />
            <span className="text-xs sm:text-sm text-center">{texts.realTimeTracking}</span>
          </div>
        </div>
      </div> */}

      {/* Continue Button (if you want manual progression) */}
      {selectedCar && (
        <div className="mt-6 sm:mt-8 text-center px-4">
          <Button
            onClick={nextStep}
            size="lg"
            className="bg-[#ffd100] hover:bg-[#ffd100]/90 text-[#2D2E2E] font-bold px-6 sm:px-8 py-3 sm:py-4 text-base sm:text-lg shadow-xl w-full sm:w-auto"
          >
            {Choose_car.button || texts.continue}
          </Button>
        </div>
      )}
    </div>
  );
}
