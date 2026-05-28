"use client";
import React, { useState } from "react";
import { FaReply, FaTrash } from "react-icons/fa";
import GlobalModal from "../GlobalModal";
import { HiTrash } from "react-icons/hi";
import { CalendarIcon } from "lucide-react";
import GlobalModalDriver from "../GlobalModalDriver";
import { Button } from "@/components/ui/button";
import { useForm } from "react-hook-form";
import RplyComplaint from "./RplyComplaint";

export default function TripComplaintsCard({
  complaint,
  trans,
  type
}: {
  complaint: any;
  trans: any;
  type?:any
}) {
  const [deletedComplaint, setDeletedComplaint] = useState(false);
  const [passengersDetalis, setdPassengersDetalis] = useState(false);
  const [driverDetalis, setDriverDetalis] = useState(false);
  const [rplyComplaint, setRplyComplaint] = useState(false);
  const onDeleted = () => {};

  return (
    <>
      <div className="bg-white text-black border rounded-lg p-3 ">
        <div className="flex items-center justify-between pb-2 border-b text-xs">
          <div
            className={`r text-[8px] p-1 rounded font-bold text-white ${
              complaint.resolved ? "bg-popover " : "bg-blue-500"
            }`}
          >
            {complaint.resolved ? "resolved" : "New"}
          </div>
          <div className="flex items-center gap-1">
            <span className="text-gray-400">ID</span>{" "}
            <span>{complaint.id}</span>
          </div>
          {complaint.trip_data?.passenger_info && (
            <div
              className="flex items-center gap-1 cursor-pointer"
              onClick={() => setdPassengersDetalis(true)}
            >
              <span className="text-gray-400">
                {trans.complaint.passengers}
              </span>{" "}
              <span className="">
                {complaint.trip_data.passenger_info.full_name ||
                  complaint.trip_data.passenger_info.first_name}
              </span>
            </div>
          )}
          {complaint.trip_data?.driver_info && (
            <div
              className="flex items-center gap-1 cursor-pointer"
              onClick={() => setDriverDetalis(true)}
            >
              <span className="text-gray-400">{trans.complaint.driver}</span>{" "}
              <span className="">
                {complaint.trip_data.driver_info.full_name ||
                  complaint.trip_data.driver_info.first_name}
              </span>
            </div>
          )}
          <div className="flex items-center gap-1 text-xs">
            <span className="text-gray-400">
              {" "}
              <CalendarIcon className="w-4 h-4" />{" "}
            </span>{" "}
            <span className="text-popover ">
              {new Date(complaint.created_at).toISOString().split("T")[0]}
            </span>
          </div>
        </div>
        <div className="py-2">
          <h1 className="text-lg">{complaint.title}</h1>
          <p className="text-sm">{complaint.description}</p>
        </div>
        <div className=" flex items-center justify-end gap-2">
          {/* <FaTrash
            className="text-accent cursor-pointer"
            onClick={() => setDeletedComplaint(true)}
          /> */}
          <FaReply
            className="text-popover cursor-pointer"
            onClick={() => setRplyComplaint(true)}
          />
        </div>
      </div>

      {/* delete */}
      <GlobalModal
        isOpen={deletedComplaint}
        onClose={() => setDeletedComplaint(false)}
      >
        <div className="flex items-center flex-col gap-4 text-center">
          <HiTrash className="text-accent text-5xl " />
          <h1 className="text-white text-lg font-bold">
            {trans.complaint.deleted.title}
          </h1>
          <p className="text-muted">{trans.complaint.deleted.desc}</p>
          <div className="w-full flex items-center gap-6 font-semibold text-lg">
            <button
              onClick={() => setDeletedComplaint(false)}
              className="bg-white text-accent p-2 w-full rounded border-2 border-accent cursor-pointer"
            >
              {trans.complaint.deleted.btuCancel}
            </button>
            <button
              onClick={onDeleted}
              className="bg-accent text-white p-2 w-full rounded cursor-pointer"
            >
              {trans.complaint.deleted.btuConfirm}
            </button>
          </div>
        </div>
      </GlobalModal>

      {/*passengers detalis */}
      <GlobalModalDriver
        isOpen={passengersDetalis}
        onClose={() => setdPassengersDetalis(false)}
      >
        <div className="text-[16px] space-y-3">
          <h1 className="text-lg font-bold">
            {trans.complaint.passengerDetalis}
          </h1>
          {complaint.trip_data?.passenger_info && (
            <>
              <div className="flex items-center justify-between">
                <span>{trans.complaint.passengerName}</span>
                <span className="font-bold">
                  {complaint.trip_data.passenger_info.full_name ||
                    complaint.trip_data.passenger_info.first_name}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>{trans.complaint.phoneNumber}</span>
                <span className="font-bold">
                  {complaint.trip_data.passenger_info.phone_number}
                </span>
              </div>
            </>
          )}
          <div className="flex items-center gap-2 font-bold">
            <button
              className="flex-1 border border-primary rounded-md p-1"
              onClick={() => setdPassengersDetalis(false)}
            >
              {trans.complaint.btuBack}
            </button>
            {/* <Button className="flex-1">{trans.complaint.copyNumber}</Button> */}
          </div>
        </div>
      </GlobalModalDriver>
      {/*driver detalis */}
      <GlobalModalDriver
        isOpen={driverDetalis}
        onClose={() => setDriverDetalis(false)}
      >
        <div className="text-[16px] space-y-3">
          <h1 className="text-lg font-bold">{trans.complaint.driverDetalis}</h1>
          {complaint.trip_data?.driver_info && (
            <>
              <div className="flex items-center justify-between">
                <span>{trans.complaint.driverName}</span>
                <span className="font-bold">
                  {complaint.trip_data.driver_info.full_name ||
                    complaint.trip_data.driver_info.first_name}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>{trans.complaint.phoneNumber}</span>
                <span className="font-bold">
                  {complaint.trip_data.driver_info.phone_number}
                </span>
              </div>
            </>
          )}
          <div className="flex items-center gap-2 font-bold">
            <button
              className="flex-1 border border-primary rounded-md p-1"
              onClick={() => setDriverDetalis(false)}
            >
              {trans.complaint.btuBack}
            </button>
            {/* <Button className="flex-1">{trans.complaint.copyNumber}</Button> */}
          </div>
        </div>
      </GlobalModalDriver>

      {/* rply Complaint */}
      <GlobalModalDriver
        isOpen={rplyComplaint}
        onClose={() => setRplyComplaint(false)}
      >
        <RplyComplaint trans={trans} closee={()=>setRplyComplaint(false)} />
      </GlobalModalDriver>
    </>
  );
}
