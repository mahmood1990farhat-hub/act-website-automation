"use client";
import React, { useState } from "react";
import LocationSelector, { PlaceSuggestion } from "./LocationSelector";
import { IoLocation } from "react-icons/io5";
import { BiCurrentLocation } from "react-icons/bi";
import { AiFillMinusCircle, AiFillPlusCircle } from "react-icons/ai";
import { RiCheckboxBlankCircleFill } from "react-icons/ri";
import { Button } from "@/components/ui/button";
import { book_Taxi, calculatTripCost } from ".";
import { Locale } from "../../../../i18n.config";
import { postData } from "@/lib/api/postData";
import GlobalModal from "../GlobalModal";
import { FaTimesCircle } from "react-icons/fa";
import { DateInput } from "../dateAndTime/date-input";
import { TimeInput } from "../dateAndTime/time-input";
import CarLoading from "../loading/CarLoading";
import { ArrowUpDown } from "lucide-react";

type RoutePoint = {
  id: number;
  type: "pickup" | "stop" | "dropoff";
  point: PlaceSuggestion | any | null;
};

interface TimeValue {
  hour: number;
  minute: number;
  period: "AM" | "PM";
}

type TaxiFormProps = {
  routePoints: RoutePoint[];
  setRoutePoints: React.Dispatch<React.SetStateAction<RoutePoint[]>>;
  book_Taxi: book_Taxi;
  setValue: (data: {
    date: string;
    time: string;
    largeSuitcase: number;
    smallSuitcase: number;
    numberOfPassengers: number;
  }) => void;
  locale: Locale;
  formDetails: {
    date: string;
    time: string;
    smallSuitcase: number;
    largeSuitcase: number;
    numberOfPassengers: number;
  };
  setTripData: (rs: calculatTripCost) => void;
  nextStep: () => void;
};

export default function RoutePoints({
  locale,
  routePoints,
  setRoutePoints,
  book_Taxi,
  setValue,
  setTripData,
  formDetails,
  nextStep,
}: TaxiFormProps) {
  const isRTL = locale === 'ar';
  const [isRequired, setIsRequired] = useState(false);
  const [openModal, setOpenModal] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date>();
  const [selectedTime, setSelectedTime] = useState<any>();
  const [isLoading, setIsLoading] = useState(false);

  const addStopPoint = () => {
    const dropoff = routePoints.find((p) => p.type === "dropoff");

    if (!dropoff) {
      console.error("Dropoff point not found!");
      return;
    }

    const withoutDropoff = routePoints.filter((p) => p.type !== "dropoff");

    const newPoint: RoutePoint = {
      id: Date.now(),
      type: "stop",
      point: null,
    };

    setRoutePoints([...withoutDropoff, newPoint, dropoff]);
  };

  const removeStopPoint = (id: number) => {
    setRoutePoints(routePoints.filter((p) => p.id !== id));
  };

  const swapPointsBetween = (index1: number, index2: number) => {
    const newRoutePoints = [...routePoints];
    const tempPoint = newRoutePoints[index1].point;
    newRoutePoints[index1].point = newRoutePoints[index2].point;
    newRoutePoints[index2].point = tempPoint;
    setRoutePoints(newRoutePoints);
  };

  const validateForm = () => {
    const hasEmptyPoints = routePoints.some((point) => !point.point?.place_id);
    const hasEmptyDate = formDetails.date === "";
    const hasEmptyTime = formDetails.time === "";

    return !(hasEmptyPoints || hasEmptyDate || hasEmptyTime);
  };

  const getFormInputValues = () => {
    const largeSuitcase = parseInt(
      (document.getElementById("large_suitcase") as HTMLInputElement)?.value || "0"
    );
    const smallSuitcase = parseInt(
      (document.getElementById("small_suitcase") as HTMLInputElement)?.value || "0"
    );
    const numberOfPassengers = parseInt(
      (document.getElementById("passenger-count") as HTMLInputElement)?.value || "1"
    );

    return { largeSuitcase, smallSuitcase, numberOfPassengers };
  };

  const buildRequestBody = (inputValues: { largeSuitcase: number; smallSuitcase: number; numberOfPassengers: number }) => {
    const pickup = routePoints.find((p) => p.type === "pickup");
    const dropoff = routePoints.find((p) => p.type === "dropoff");

    if (!pickup || !dropoff) {
      throw new Error("Pickup or dropoff point not found");
    }

    const stop_points = routePoints
      .filter((p) => p.type === "stop")
      .map((p) => ({
        point_lat: p.point?.coordinates?.lat || 0,
        point_lng: p.point?.coordinates?.lng || 0,
      }));

    // Handle both airport and regular location formats
    const getLocationData = (point: any) => {
      // If it's an airport (has id property), use airport_id
      if (point.id && typeof point.id === 'string') {
        return { airport_id: point.id };
      }
      // Otherwise, use lat/lng coordinates
      return {
        lat: point.coordinates?.lat || 0,
        lng: point.coordinates?.lng || 0,
      };
    };

    const bodyData: any = {
      pickup_location: getLocationData(pickup.point),
      dropoff_location: getLocationData(dropoff.point),
      trip_date: formDetails.date,
      trip_time: formDetails.time,
      passengers_count: inputValues.numberOfPassengers,
      large_suitcase: inputValues.largeSuitcase,
      small_suitcase: inputValues.smallSuitcase,
    };

    if (stop_points.length > 0) {
      bodyData.stop_points = stop_points;
    }

    return bodyData;
  };

  const onSubmit = async () => {
    if (!validateForm()) {
      setIsRequired(true);
      return;
    }

    setIsLoading(true);

    try {
      const inputValues = getFormInputValues();

      setValue({
        ...formDetails,
        ...inputValues,
      });

      const bodyData = buildRequestBody(inputValues);

      const response = await postData<calculatTripCost>({
        endpoint: "/api/trips/calculate-trip-cost/",
        body: bodyData,
      });

      setTripData(response);
      nextStep();
    } catch (error) {
      console.error("Trip calculation error:", error);
      // setOpenModal(true);
    } finally {
      setIsLoading(false);
    }
  };

  const updateRoutePoint = (pointId: number, data: any) => {
    setRoutePoints((prev) =>
      prev.map((p) => (p.id === pointId ? { ...p, point: data } : p))
    );
  };

  const getPointLabel = (type: string) => {
    switch (type) {
      case "pickup":
        return book_Taxi.form.PickUp_location;
      case "dropoff":
        return book_Taxi.form.DropOff_location;
      default:
        return book_Taxi.form.stop_ponit;
    }
  };

  const shouldShowSwapIcon = (item: RoutePoint, index: number) => {
    return item.type !== "dropoff";
  };

  return (
    <div className="max-w-3xl max-xl:mx-auto">
      <h1 className={`text-center ${isRTL ? 'lg:text-right' : 'lg:text-left'} text-4xl sm:text-5xl lg:text-6xl font-extrabold mb-2`}>
        {book_Taxi.title}
      </h1>
      <p className={`text-sm text-center ${isRTL ? 'lg:text-right' : 'lg:text-left'} lg:text-lg text-muted mb-6`}>
        {book_Taxi.subtitle}
      </p>

      <div>
        {routePoints.map((item, index) => (
          <div
            key={item.id}
            className={`flex w-full gap-2 ${index === routePoints.length - 2 && item.type === "stop"
                ? "slide-down"
                : ""
              }`}
          >
            <div className="relative w-full">
              <label htmlFor={`location-${item.id}`}>
                {getPointLabel(item.type)}

              <LocationSelector
                locale={locale}
                value={item.point?.description || ""}
                locationType={item?.type}
                setValue={(data) => updateRoutePoint(item.id, data)}
              />
              </label>
                {isRequired && !item?.point?.place_id && <span className="absolute bottom-0.5 text-red-600 font-semibold px-2">
                  {book_Taxi.form.error}
                </span>}

              {shouldShowSwapIcon(item, index) && (
                <ArrowUpDown
                  size={28}
                  strokeWidth={2.5}
                  onClick={() => swapPointsBetween(index, index + 1)}
                  className="mx-auto text-3xl pt-2 cursor-pointer transform translate-y-2 text-primary"
                />
              )}

              {item.type === "dropoff" && <span className="block h-[30px]"></span>}
            </div>

            <div className="text-[20px] text-primary h-full mt-auto">
              <div className="flex items-center justify-between flex-col">
                {item.type === "pickup" && (
                  <div className="flex items-center flex-col mt-auto">
                    <IoLocation />
                    {[...Array(3)].map((_, i) => (
                      <RiCheckboxBlankCircleFill
                        key={`pickup-${i}`}
                        className="text-xs p-1 text-muted"
                      />
                    ))}
                    <AiFillPlusCircle
                      className="text-muted cursor-pointer transform translate-y-2"
                      onClick={addStopPoint}
                    />
                  </div>
                )}

                {item.type === "dropoff" && (
                  <div className="flex items-center flex-col mb-7">
                    {[...Array(3)].map((_, i) => (
                      <RiCheckboxBlankCircleFill
                        key={`drop-${i}`}
                        className="text-xs p-1 text-muted"
                      />
                    ))}
                    <BiCurrentLocation />
                  </div>
                )}

                {item.type === "stop" && (
                  <div className="flex items-center flex-col">
                    {[...Array(3)].map((_, i) => (
                      <RiCheckboxBlankCircleFill
                        key={`stop-top-${i}`}
                        className="text-xs p-1 text-muted"
                      />
                    ))}
                    <AiFillMinusCircle
                      className="cursor-pointer"
                      onClick={() => removeStopPoint(item.id)}
                    />
                    {[...Array(3)].map((_, i) => (
                      <RiCheckboxBlankCircleFill
                        key={`stop-bot-${i}`}
                        className="text-xs p-1 text-muted"
                      />
                    ))}
                    <AiFillPlusCircle
                      className="text-muted cursor-pointer"
                      onClick={addStopPoint}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Date & Time Section */}
        <div className="flex w-full gap-2 my-1">
          <div className="w-full space-y-4">
            <div
              onClick={() => setIsRequired(false)}
              className="flex items-center justify-between max-md:flex-col gap-4"
            >
              <div className="relative w-full">
                <label htmlFor="ride-date">
                  <p>{book_Taxi.form.date}</p>
                </label>
                <DateInput
                  value={selectedDate}
                  onChange={setSelectedDate}
                  setFormattedDate={(d) =>
                    setValue({ ...formDetails, date: d })
                  }
                  required={isRequired}
                  language={locale}
                />
              </div>
              <div className="w-full">
                <label htmlFor="ride-time">
                  <p>{book_Taxi.form.time}</p>
                </label>
                <TimeInput
                  value={selectedTime}
                  onChange={(t) => setSelectedTime(t)}
                  language={locale}
                  required={isRequired}
                  setFormattedTime={(time) =>
                    setValue({ ...formDetails, time: time })
                  }
                />
              </div>
            </div>

            <div className="flex items-center justify-between max-md:flex-col gap-4">
              <div className="w-full">
                <label htmlFor="passenger-count">
                  <p>{book_Taxi.form.NumberOfPassenger}</p>
                </label>
                <input
                  id="passenger-count"
                  type="number"
                  defaultValue={1}
                  max={7}
                  min={1}
                  className="w-full p-2.5 mb-2 border-2 bg-white text-foreground font-semibold border-muted rounded-lg"
                />
              </div>
              <div className="w-full flex items-center gap-1">
                <div className="w-full">
                  <label htmlFor="large_suitcase">
                    <p>{book_Taxi.form.largeSuitcase}</p>
                  </label>
                  <input
                    id="large_suitcase"
                    type="number"
                    defaultValue={0}
                    min="0"
                    className="w-full p-2.5 mb-2 border-2 bg-white text-foreground font-semibold border-muted rounded-lg"
                  />
                </div>
                <div className="w-full">
                  <label htmlFor="small_suitcase">
                    <p>{book_Taxi.form.smallSuitcase}</p>
                  </label>
                  <input
                    id="small_suitcase"
                    defaultValue={0}
                    type="number"
                    min="0"
                    className="w-full p-2.5 mb-2 border-2 bg-white text-foreground font-semibold border-muted rounded-lg"
                  />
                </div>
              </div>
            </div>

            <Button
              type="button"
              className="w-full text-lg p-6 cursor-pointer font-bold"
              onClick={onSubmit}
              disabled={isLoading}
            >
              {isLoading ? <CarLoading /> : book_Taxi.form.button}
            </Button>
          </div>
          <div className="w-5"></div>
        </div>
      </div>

      <GlobalModal isOpen={openModal} onClose={() => setOpenModal(false)}>
        <div className="flex items-center justify-center flex-col gap-5">
          <FaTimesCircle className="text-5xl text-red-700" />
          <h1>{book_Taxi.form.error_message}</h1>
          <Button
            onClick={() => setOpenModal(false)}
            className="p-5 px-10 text-lg"
          >
            {book_Taxi.form.error_button}
          </Button>
        </div>
      </GlobalModal>
    </div>
  );
}