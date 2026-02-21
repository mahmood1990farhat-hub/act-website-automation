"use client";
import React, { useState } from "react";
import { Locale } from "../../../../i18n.config";
import { useQuery } from "@tanstack/react-query";
import { fetchData } from "@/lib/api/fetchData";
import TripDetails from "./TripDetails";
import IsLoadig from "../ISloading";
import Pagination from "../Pagination";
import MapView from "../bookTaxi/MapView";
import DriverWithPassengerMap from "./DriverWithPassengerMap";

export default function UpcomingTrips({
  token,
  locale,
  trans,
}: {
  token?: string;
  locale: Locale;
  trans: any;
}) {
  const [page, setPage] = useState(1);
  const [stratAndEnd, setStratAndEnd] = useState(false);

  const { data: upcomingData, isLoading: upcomingLoading } = useQuery<any>({
    queryKey: ["UpcomingTrips", page],
    queryFn: () =>
      fetchData({
        endpoint: "/api/trips/list-trips/",
        token: token,
        queryParams: {
          locale: locale,
          trip_status: "driver_on_the_way",
          page_size: "1",
          page: page.toString(),
        },
      }),
  });

  return (
    <div className="">
      <h1 className="text-2xl font-bold my-5">{trans.upcomingTrips.title}</h1>
      <div className=" ">
        {upcomingLoading ? (
          <IsLoadig />
        ) : upcomingData.trips.length>0 ?
          <div>
        
            <div className=" grid lg:grid-cols-1 grid-cols-1 gap-5">
              {/* {upcomingData.trips.map((item: any) => (
                <div className="" key={item.id}>
                  <TripDetails
                    tripState="upcoming"
                    detailsTrips={item}
                    trans={trans}
                    locale={locale}
                  />
                </div>
              ))} */}
              <div className="grid md:grid-cols-2 grid-cols-1 gap-3">
                {/* <div className=" md:hidden ">
                       <MapView routePolyline={upcomingData.trips[0].route_polyline} />
                     </div> */}
                <div>
                  <div className="">
                    <TripDetails
                      tripState="upcoming"
                      detailsTrips={upcomingData.trips[0]}
                      trans={trans}
                      token={token}
                      locale={locale}
                    />
                  </div>
                </div>

                <div className=" max-md:h-150">
                  {stratAndEnd && (
                    <DriverWithPassengerMap
                      passengerLocation={{
                        lat: upcomingData.trips[0].pickup_lat,
                        lng: upcomingData.trips[0].pickup_lng,
                      }}
                    />
                  )}
                  {!stratAndEnd && (
                    <MapView
                      routePolyline={upcomingData.trips[0].route_polyline}
                    />
                  )}
                </div>
              </div>
            </div>
          </div> :     <div className="flex items-center justify-center  flex-col h-[40vh]">
          <h1 className="text-2xl font-bold">{trans.noTrips.title}</h1>
          <p className="text-lg font-medium my-2">{trans.noTrips.desc}</p>
        </div>
        }
      </div>

      {!upcomingLoading && upcomingData.num_pages > 1 && (
        <Pagination
          currentPage={page}
          onPageChange={(pa) => setPage(pa)}
          locale={locale}
          totalPages={upcomingData.num_pages}
        />
      )}
    </div>
  );
}
