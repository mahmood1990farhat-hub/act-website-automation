"use client";

import React, { useState } from "react";
import { Locale } from "../../../../i18n.config";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchData } from "@/lib/api/fetchData";
import { postData } from "@/lib/api/postData";
import IsLoading from "../ISloading";
import Pagination from "../Pagination";
import { FaPlay, FaPause, FaUser, FaCheckCircle, FaTimesCircle, FaUserCheck, FaUserSlash } from "react-icons/fa";
import GlobalModal from "../GlobalModal";
import { Button } from "@/components/ui/button";
import { HiOutlineEye, HiOutlineX } from "react-icons/hi";
import { toast } from "react-toastify";
import { extract_error } from "@/lib/api/errorApi";
import { formatDate } from "@/lib/FormatDate";

type PassengerManagementProps = {
  trans: any;
  token?: string;
  locale: Locale;
};

export default function AllPassengersDashboard({
  trans,
  token,
  locale,
}: PassengerManagementProps) {
  const [page, setPage] = useState(1);
  const [filterActive, setFilterActive] = useState<"" | "true" | "false">("");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedPassenger, setSelectedPassenger] = useState<any | null>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const queryClient = useQueryClient();

  const {
    data: passengersData,
    isLoading: passengersLoading,
  } = useQuery<any>({
    queryKey: ["admin-passengers", page, filterActive, searchTerm],
    queryFn: () =>
      fetchData({
        endpoint: "/api/admin-panel/passengers/",
        token,
        queryParams: {
          locale,
          page: page.toString(),
          page_size: "10",
          ...(filterActive && { is_active: filterActive }),
          ...(searchTerm.trim() && { search: searchTerm.trim() }),
        },
      }),
  });

  // Normalize API response shape
  const payload = passengersData?.data || passengersData || {};
  const passengers = payload.passengers || [];
  const stats = payload.stats?.all_time || {};
  const pagination = payload.pagination || {};

  const handleActivate = async (passengerId: number) => {
    setActionLoading(true);
    try {
      await postData({
        endpoint: `/api/admin-panel/users/${passengerId}/activate/`,
        token,
        body: {},
        noToast: false, // Let API show toast
      });
      
      queryClient.invalidateQueries({ queryKey: ["admin-passengers"] });
    } catch (error: any) {
      // Error toast is handled by postData
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeactivate = async (passengerId: number) => {
    setActionLoading(true);
    try {
      await postData({
        endpoint: `/api/admin-panel/users/${passengerId}/deactivate/`,
        token,
        body: {},
        noToast: false, // Let API show toast
      });
      
      queryClient.invalidateQueries({ queryKey: ["admin-passengers"] });
    } catch (error: any) {
      // Error toast is handled by postData
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="w-full">
      {/* Stats Cards */}
      <div className="mb-6">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-3">
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.passengers?.stats?.total || "Total Passengers"}
            </p>
            <p className="text-gray-900 text-xl font-bold">{stats.total || 0}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.passengers?.stats?.active || "Active"}
            </p>
            <p className="text-green-600 text-xl font-bold">{stats.active_count || 0}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.passengers?.stats?.inactive || "Inactive"}
            </p>
            <p className="text-red-600 text-xl font-bold">{stats.inactive_count || 0}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.passengers?.stats?.verified || "Verified"}
            </p>
            <p className="text-blue-600 text-xl font-bold">{stats.verified_count || 0}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.passengers?.stats?.unverified || "Unverified"}
            </p>
            <p className="text-yellow-600 text-xl font-bold">{stats.unverified_count || 0}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.passengers?.stats?.profile_completed || "Profile Completed"}
            </p>
            <p className="text-emerald-600 text-xl font-bold">{stats.profile_completed_count || 0}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.passengers?.stats?.profile_incomplete || "Profile Incomplete"}
            </p>
            <p className="text-orange-600 text-xl font-bold">{stats.profile_incomplete_count || 0}</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-card rounded-xl p-4 mb-6 border border-gray-200 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Search Filter */}
          <div>
            <label className="block mb-2 text-[16px] text-gray-800">
              {trans.passengers?.filterLabels?.search || "Search"}
            </label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              placeholder={trans.passengers?.filterPlaceholders?.search || "Search by name, email, phone..."}
              className="w-full p-3 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {/* Active Status Filter */}
          <div>
            <label className="block mb-2 text-[16px] text-gray-800">
              {trans.passengers?.filterLabels?.status || "Status"}
            </label>
            <select
              value={filterActive}
              onChange={(e) => {
                setFilterActive(e.target.value as "" | "true" | "false");
                setPage(1);
              }}
              className="w-full p-3 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              <option value="">
                {trans.passengers?.filterLabels?.all || "All"}
              </option>
              <option value="true">
                {trans.passengers?.filterLabels?.active || "Active"}
              </option>
              <option value="false">
                {trans.passengers?.filterLabels?.inactive || "Inactive"}
              </option>
            </select>
          </div>
        </div>
      </div>

      {/* Passengers List */}
      {passengersLoading ? (
        <div className="flex items-center justify-center py-20">
          <IsLoading />
        </div>
      ) : passengers.length === 0 ? (
        <div className="bg-card rounded-xl p-12 border border-gray-200 text-center shadow-sm">
          <FaUser className="text-gray-400 text-5xl mx-auto mb-4" />
          <p className="text-gray-500 text-lg">
            {trans.passengers?.empty || "No passengers found"}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Desktop Table */}
          <div className="hidden xl:block">
            <div className="w-full bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden">
              <div className="bg-gradient-to-r from-card to-background px-6 py-4 border-b-2 border-border">
                <h2 className="text-foreground text-lg font-bold">
                  {trans.passengers?.allpassengers || "All Passengers"}
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[820px] text-xs">
                  <thead>
                    <tr className="border-b-2 border-border bg-gray-100 dark:bg-gray-800">
                      {(trans.passengers?.tableHeaders || [
                        "Passengers name",
                        "ID",
                        "Phone number",
                        "Include date",
                        "Address",
                        "Trips count",
                        "Status",
                        "Action"
                      ]).map((header: string) => (
                        <th key={header} className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {passengers.map((passenger: any) => (
                      <tr
                        key={passenger.id}
                        className="border-b border-border hover:bg-muted transition-colors"
                      >
                        <td className="py-3 px-3 font-bold text-foreground">
                          {passenger.first_name} {passenger.last_name}
                        </td>
                        <td className="py-3 px-3 text-foreground whitespace-nowrap">
                          #{passenger.id}
                        </td>
                        <td className="py-3 px-3 text-foreground">
                          {passenger.phone_number || "-"}
                        </td>
                        <td className="py-3 px-3 text-muted-foreground whitespace-nowrap">
                          {formatDate(new Date(passenger.date_joined), locale)}
                        </td>
                        <td className="py-3 px-3 text-foreground max-w-[200px] truncate">
                          {passenger.address || "-"}
                        </td>
                        <td className="py-3 px-3 font-bold whitespace-nowrap">
                          {passenger.trips_count || 0}
                        </td>
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full font-bold ${
                              passenger.is_active
                                ? "bg-green-50 text-green-700 border border-green-200"
                                : "bg-red-50 text-red-700 border border-red-200"
                            }`}
                          >
                            {passenger.is_active
                              ? trans.passengers?.status?.active || "Active"
                              : trans.passengers?.status?.inactive || "Inactive"}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center whitespace-nowrap">
                          <div className="flex items-center justify-center space-x-2">
                            <Button
                              onClick={() => {
                                setSelectedPassenger(passenger);
                                setShowDetailsModal(true);
                              }}
                              variant="ghost"
                              className="p-1.5 hover:bg-muted text-yellow-600 hover:text-yellow-700 transition-colors inline-flex"
                            >
                              <HiOutlineEye className="text-base" />
                            </Button>
                            {passenger.is_active ? (
                              <Button
                                onClick={() => handleDeactivate(passenger.id)}
                                variant="ghost"
                                disabled={actionLoading}
                                className="p-1.5 hover:bg-muted text-red-600 hover:text-red-700 transition-colors inline-flex disabled:opacity-50"
                                title={trans.passenger_card?.deactivate || "Deactivate"}
                              >
                                <FaPause className="text-base" />
                              </Button>
                            ) : (
                              <Button
                                onClick={() => handleActivate(passenger.id)}
                                variant="ghost"
                                disabled={actionLoading}
                                className="p-1.5 hover:bg-muted text-green-600 hover:text-green-700 transition-colors inline-flex disabled:opacity-50"
                                title={trans.passenger_card?.activate || "Activate"}
                              >
                                <FaPlay className="text-base" />
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              { passengersLoading ?null:pagination.num_pages > 1 && (
                <div className="flex items-center justify-between px-6 border-t-2 border-border">
                  <div className="text-sm mx-auto text-muted-foreground">
                    {trans.pagination?.table || "Page"} {page} {trans.pagination?.of || "of"}{" "}
                    {pagination.num_pages || 1} {trans.pagination?.tables || "pages"}
                  </div>
                  <Pagination
                    currentPage={page}
                    onPageChange={setPage}
                    locale={locale}
                    totalPages={pagination.num_pages || 1}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Mobile Cards */}
          <div className="xl:hidden space-y-4">
            {passengers.map((passenger: any) => (
              <div
                key={passenger.id}
                className="bg-card max-sm:max-w-[360px] mx-auto rounded-xl shadow-lg border-2 border-border p-4 hover:shadow-2xl hover:border-primary/60 transition-all"
              >
                <div className="flex items-start justify-between mb-3 pb-3 border-b-2 border-border">
                  <div className="flex-1">
                    <h3 className="font-bold text-lg text-foreground mb-1">
                      {passenger.first_name} {passenger.last_name}
                    </h3>
                    <p className="text-sm text-muted-foreground">#{passenger.id}</p>
                  </div>
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border ${
                      passenger.is_active
                        ? "bg-green-50 text-green-700 border-green-200"
                        : "bg-red-50 text-red-700 border-red-200"
                    }`}
                  >
                    {passenger.is_active
                      ? trans.passengers?.status?.active || "Active"
                      : trans.passengers?.status?.inactive || "Inactive"}
                  </span>
                </div>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <span className="text-sm text-muted-foreground font-semibold">
                      {trans.passengers?.tableHeaders?.[2] || "Phone"}
                    </span>
                    <span className="text-sm text-foreground font-bold">
                      {passenger.phone_number || "-"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <span className="text-sm text-muted-foreground font-semibold">
                      {trans.passengers?.tableHeaders?.[3] || "Date Joined"}
                    </span>
                    <span className="text-sm text-foreground font-bold">
                      {formatDate(new Date(passenger.date_joined), locale)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <span className="text-sm text-muted-foreground font-semibold">
                      {trans.passengers?.tableHeaders?.[4] || "Address"}
                    </span>
                    <span className="text-sm text-foreground font-bold max-w-[60%] truncate">
                      {passenger.address || "-"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-muted-foreground font-semibold">
                      {trans.passengers?.tableHeaders?.[5] || "Trips"}
                    </span>
                    <span className="text-sm  font-bold">
                      {passenger.trips_count || 0}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    onClick={() => {
                      setSelectedPassenger(passenger);
                      setShowDetailsModal(true);
                    }}
                    className="flex-1 bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-foreground font-bold shadow-lg shadow-yellow-500/20"
                  >
                    <HiOutlineEye className="mr-2" /> {trans.passenger_card?.viewDetails || "View Details"}
                  </Button>
                  {passenger.is_active ? (
                    <Button
                      onClick={() => handleDeactivate(passenger.id)}
                      disabled={actionLoading}
                      variant="outline"
                      className="border-red-500 text-red-600 hover:bg-red-50 disabled:opacity-50"
                    >
                      <FaPause />
                    </Button>
                  ) : (
                    <Button
                      onClick={() => handleActivate(passenger.id)}
                      disabled={actionLoading}
                      variant="outline"
                      className="border-green-500 text-green-600 hover:bg-green-50 disabled:opacity-50"
                    >
                      <FaPlay />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Mobile Pagination */}
          {pagination.num_pages > 1 && (
            <div className="xl:hidden mt-6">
              <Pagination
                currentPage={page}
                onPageChange={setPage}
                locale={locale}
                totalPages={pagination.num_pages || 1}
              />
            </div>
          )}
        </div>
      )}

      {/* Details Modal - Driver Onboarding Pattern */}
      {showDetailsModal && selectedPassenger && (
        <div
                onClick={() => {
                  setShowDetailsModal(false);
                  setSelectedPassenger(null);
                }}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-3 lg:p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-card rounded-2xl w-full max-w-4xl shadow-2xl max-h-[95vh] xl:max-h-[90vh] overflow-y-auto on-scrollbar border-2 border-border"
          >
            {/* Modal Header */}
            <div className="sticky top-0 bg-gradient-to-r from-card to-background px-4 xl:px-6 py-4 lg:py-5 border-b-2 border-border rounded-t-2xl z-10">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <h2 className="text-xl lg:text-2xl font-bold text-foreground">
                  {trans.passenger_card?.passengerDetails || "Passenger Details"}
                </h2>
                <div className="flex items-center gap-3">
                  <span
                    className={`px-4 py-2 rounded-full text-xs xl:text-sm font-bold border ${
                      selectedPassenger.is_active
                        ? "bg-green-500/20 text-green-400 border-green-500/30"
                        : "bg-red-500/20 text-red-400 border-red-500/30"
                    }`}
                  >
                    {selectedPassenger.is_active
                      ? trans.passengers?.status?.active || "Active"
                      : trans.passengers?.status?.inactive || "Inactive"}
                  </span>
                  <button
                    onClick={() => {
                      setShowDetailsModal(false);
                      setSelectedPassenger(null);
                    }}
                    className="p-2 hover:bg-muted rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                  >
                    <HiOutlineX className="w-6 h-6" />
                  </button>
                </div>
              </div>
            </div>

            {/* Modal Content */}
            <div className="p-4 md:p-6 space-y-5 md:space-y-6">
              {/* Personal Information */}
              <div className="bg-muted border-2 border-yellow-500/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-yellow-500 rounded-full"></span>
                  {trans.passenger_card?.personalInfo || "Personal Information"}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.passenger_card?.passengerId || "Passenger ID"}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base">#{selectedPassenger.id}</p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                    {trans.passenger_card?.firstName || "First Name"}
                  </p>
                    <p className="font-semibold text-foreground text-sm md:text-base break-words">
                      {selectedPassenger.first_name}
                    </p>
                </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                    {trans.passenger_card?.lastName || "Last Name"}
                  </p>
                    <p className="font-semibold text-foreground text-sm md:text-base break-words">
                      {selectedPassenger.last_name}
                    </p>
                </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                    {trans.passenger_card?.email || "Email"}
                  </p>
                    <p className="font-semibold text-foreground text-sm md:text-base break-all">
                      {selectedPassenger.email}
                    </p>
                </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                    {trans.passenger_card?.phoneNumber || "Phone Number"}
                  </p>
                    <p className="font-semibold text-foreground text-sm md:text-base break-words">
                    {selectedPassenger.phone_number || "-"}
                  </p>
                </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                    {trans.passenger_card?.address || "Address"}
                  </p>
                    <p className="font-semibold text-foreground text-sm md:text-base break-words">
                    {selectedPassenger.address || "-"}
                  </p>
                </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                    {trans.passenger_card?.dateJoined || "Date Joined"}
                  </p>
                    <p className="font-semibold text-foreground text-sm md:text-base">
                    {formatDate(new Date(selectedPassenger.date_joined), locale)}
                  </p>
                </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                    {trans.passenger_card?.tripsCount || "Trips Count"}
                  </p>
                    <p className="font-semibold text-primary text-sm md:text-base">
                    {selectedPassenger.trips_count || 0}
                  </p>
                  </div>
                </div>
              </div>

              {/* Account Status */}
              <div className="bg-muted border-2 border-blue-400/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-blue-500 rounded-full"></span>
                  {trans.passenger_card?.accountStatus || "Account Status"}
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center gap-3 bg-card p-3 rounded-lg border border-border">
                    {selectedPassenger.is_active ? (
                      <FaCheckCircle className="text-green-500 text-xl flex-shrink-0" />
                    ) : (
                      <FaTimesCircle className="text-red-500 text-xl flex-shrink-0" />
                    )}
                    <span className="font-semibold text-foreground text-sm md:text-base">
                      {selectedPassenger.is_active
                        ? trans.passenger_card?.active || "Active"
                        : trans.passenger_card?.inactive || "Inactive"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 bg-card p-3 rounded-lg border border-border">
                    {selectedPassenger.is_admin_verified ? (
                      <FaUserCheck className="text-green-500 text-xl flex-shrink-0" />
                    ) : (
                      <FaUserSlash className="text-yellow-500 text-xl flex-shrink-0" />
                    )}
                    <span className="font-semibold text-foreground text-sm md:text-base">
                      {selectedPassenger.is_admin_verified
                        ? trans.passenger_card?.verified || "Verified"
                        : trans.passenger_card?.unverified || "Unverified"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 bg-card p-3 rounded-lg border border-border">
                    {selectedPassenger.is_profile_completed ? (
                      <FaCheckCircle className="text-green-500 text-xl flex-shrink-0" />
                    ) : (
                      <FaTimesCircle className="text-orange-500 text-xl flex-shrink-0" />
                    )}
                    <span className="font-semibold text-foreground text-sm md:text-base">
                      {selectedPassenger.is_profile_completed
                        ? trans.passenger_card?.profileCompleted || "Profile Completed"
                        : trans.passenger_card?.profileIncomplete || "Profile Incomplete"}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="sticky bottom-0 bg-gradient-to-r from-card to-background px-4 xl:px-6 py-4 lg:py-5 border-t-2 border-border rounded-b-2xl flex flex-col sm:flex-row justify-end gap-3">
              {selectedPassenger.is_active ? (
                <Button
                  onClick={() => handleDeactivate(selectedPassenger.id)}
                  disabled={actionLoading}
                  variant="destructive"
                  className="flex items-center gap-2"
                >
                  <FaPause className="w-4 h-4" />
                  {trans.passenger_card?.deactivate || "Deactivate"}
                </Button>
              ) : (
                <Button
                  onClick={() => handleActivate(selectedPassenger.id)}
                  disabled={actionLoading}
                  className="flex items-center gap-2 bg-green-600 hover:bg-green-700"
                >
                  <FaPlay className="w-4 h-4" />
                  {trans.passenger_card?.activate || "Activate"}
                </Button>
              )}
              <Button
                onClick={() => {
                  setShowDetailsModal(false);
                  setSelectedPassenger(null);
                }}
                variant="outline"
                className="border-border text-foreground hover:bg-muted"
              >
                {trans.passenger_card?.close || "Close"}
              </Button>
            </div>
            </div>
          </div>
        )}

      {/* Other modals can go here */}
    </div>
  );
}
