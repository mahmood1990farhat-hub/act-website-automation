"use client";

import React, { useState } from "react";
import { Locale } from "../../../../i18n.config";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchData } from "@/lib/api/fetchData";
import { postData } from "@/lib/api/postData";
import IsLoading from "../ISloading";
import Pagination from "../Pagination";
import { FaPlay, FaPause, FaUser, FaCheckCircle, FaTimesCircle, FaUserCheck, FaUserSlash, FaCar, FaFileAlt, FaMoneyBillWave } from "react-icons/fa";
import GlobalModal from "../GlobalModal";
import { Button } from "@/components/ui/button";
import { HiOutlineEye, HiOutlineX } from "react-icons/hi";
import { toast } from "react-toastify";
import { extract_error } from "@/lib/api/errorApi";
import { formatDate } from "@/lib/FormatDate";

type DriverManagementProps = {
  trans: any;
  token?: string;
  locale: Locale;
};

type CommissionResponse = {
  success: boolean;
  data: {
    driver_id: number;
    driver_commission_percentage: number | null;
    effective_driver_percentage: number | null;
    effective_company_percentage: number | null;
    fallback_source: string | null;
    vehicle_type?: {
      id: number;
      name_en: string;
      name_ar: string;
    } | null;
  };
};

export default function AllDriversDashboard({
  trans,
  token,
  locale,
}: DriverManagementProps) {
  const [page, setPage] = useState(1);
  const [filterActive, setFilterActive] = useState<"" | "true" | "false">("");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDriver, setSelectedDriver] = useState<any | null>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [documentPreview, setDocumentPreview] = useState<{ url: string; title: string } | null>(null);
  const [showCommissionModal, setShowCommissionModal] = useState(false);
  const [selectedDriverForCommission, setSelectedDriverForCommission] = useState<any | null>(null);
  const [commissionPercentage, setCommissionPercentage] = useState<string>("");
  const [isUpdatingCommission, setIsUpdatingCommission] = useState(false);
  const queryClient = useQueryClient();

  const {
    data: driversData,
    isLoading: driversLoading,
  } = useQuery<any>({
    queryKey: ["admin-drivers", page, filterActive, searchTerm],
    queryFn: () =>
      fetchData({
        endpoint: "/api/admin-panel/normal-drivers",
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
  const payload = driversData?.data || driversData || {};
  const drivers = payload.drivers || [];
  const stats = payload.stats?.all_time || {};
  const pagination = driversData?.pagination || {};
  

  const handleActivate = async (userId: number) => {
    setActionLoading(true);
    try {
      await postData({
        endpoint: `/api/admin-panel/users/${userId}/activate/`,
        token,
        body: {},
        noToast: false, // Let API show toast
      });
      
      queryClient.invalidateQueries({ queryKey: ["admin-drivers"] });
    } catch (error: any) {
      // Error toast is handled by postData
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeactivate = async (userId: number) => {
    setActionLoading(true);
    try {
      await postData({
        endpoint: `/api/admin-panel/users/${userId}/deactivate/`,
        token,
        body: {},
        noToast: false, // Let API show toast
      });
      
      queryClient.invalidateQueries({ queryKey: ["admin-drivers"] });
    } catch (error: any) {
      // Error toast is handled by postData
    } finally {
      setActionLoading(false);
    }
  };

  // Fetch commission data
  const { data: commissionData, isLoading: commissionLoading } = useQuery<CommissionResponse | null>({
    queryKey: ["driver-commission", selectedDriverForCommission?.id, token],
    queryFn: async () => {
      if (!selectedDriverForCommission?.id || !token) return null;
      try {
        const data = await fetchData<CommissionResponse>({
          endpoint: `/api/admin-panel/drivers/${selectedDriverForCommission.id}/commission/`,
          token,
        });
        // Handle null commission - default to 0
        const commissionValue = data?.data?.driver_commission_percentage;
        if (commissionValue !== null && commissionValue !== undefined) {
          setCommissionPercentage(commissionValue.toString());
        } else {
          setCommissionPercentage("0");
        }
        return data;
      } catch (error: any) {
        const errorMessage = extract_error(error) || error?.message || "Failed to load commission";
        toast.error(errorMessage);
        throw error;
      }
    },
    enabled: !!selectedDriverForCommission?.id && showCommissionModal,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const handleOpenCommission = (driverItem: any) => {
    setSelectedDriverForCommission(driverItem);
    setShowCommissionModal(true);
    setCommissionPercentage("0"); // Default to 0 instead of empty string
  };

  const handleUpdateCommission = async () => {
    if (!selectedDriverForCommission?.id || !token) return;
    
    // Handle empty string or null - default to 0
    const percentageValue = commissionPercentage.trim() === "" ? "0" : commissionPercentage;
    const percentage = parseFloat(percentageValue);
    
    if (isNaN(percentage) || percentage < 0 || percentage > 100) {
      toast.error(trans.driver?.commission?.invalidPercentage || "Please enter a valid percentage between 0 and 100");
      return;
    }

    setIsUpdatingCommission(true);
    try {
      await postData({
        endpoint: `/api/admin-panel/drivers/${selectedDriverForCommission.id}/commission/`,
        token,
        body: {
          driver_commission_percentage: percentage,
        },
        noToast: false, // Let API show toast
      });
      
      queryClient.invalidateQueries({ queryKey: ["driver-commission", selectedDriverForCommission.id] });
    } catch (error: any) {
      // Error toast is handled by postData
    } finally {
      setIsUpdatingCommission(false);
    }
  };

  return (
    <div className="w-full">
    

      {/* Stats Cards */}
      <div className="mb-6">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-3">
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.driver?.stats?.total || "Total Drivers"}
            </p>
            <p className="text-gray-900 text-xl font-bold">{stats.total || 0}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.driver?.stats?.active || "Active"}
            </p>
            <p className="text-green-600 text-xl font-bold">{stats.active_count || 0}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.driver?.stats?.inactive || "Inactive"}
            </p>
            <p className="text-red-600 text-xl font-bold">{stats.inactive_count || 0}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.driver?.stats?.verified || "Verified"}
            </p>
            <p className="text-blue-600 text-xl font-bold">{stats.verified_count || 0}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.driver?.stats?.unverified || "Unverified"}
            </p>
            <p className="text-yellow-600 text-xl font-bold">{stats.unverified_count || 0}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.driver?.stats?.profile_completed || "Profile Completed"}
            </p>
            <p className="text-emerald-600 text-xl font-bold">{stats.profile_completed_count || 0}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-gray-200 shadow-sm">
            <p className="text-gray-500 text-xs mb-1">
              {trans.driver?.stats?.profile_incomplete || "Profile Incomplete"}
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
              {trans.driver?.filterLabels?.search || "Search"}
            </label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              placeholder={trans.driver?.filterPlaceholders?.search || "Search by name, email, phone..."}
              className="w-full p-3 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {/* Active Status Filter */}
          <div>
            <label className="block mb-2 text-[16px] text-gray-800">
              {trans.driver?.filterLabels?.status || "Status"}
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
                {trans.driver?.filterLabels?.all || "All"}
              </option>
              <option value="true">
                {trans.driver?.filterLabels?.active || "Active"}
              </option>
              <option value="false">
                {trans.driver?.filterLabels?.inactive || "inactive"}
              </option>
            </select>
          </div>
        </div>
      </div>

      {/* Drivers List */}
      {driversLoading ? (
        <div className="flex items-center justify-center py-20">
          <IsLoading />
        </div>
      ) : drivers.length === 0 ? (
        <div className="bg-card rounded-xl p-12 border border-gray-200 text-center shadow-sm">
          <FaUser className="text-gray-400 text-5xl mx-auto mb-4" />
          <p className="text-gray-500 text-lg">
            {trans.driver?.empty || "No drivers found"}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Desktop Table */}
          <div className="hidden xl:block">
            <div className="w-full bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden">
              <div className="bg-gradient-to-r from-card to-background px-6 py-4 border-b-2 border-border">
                <h2 className="text-foreground text-lg font-bold">
                  {trans.driver?.alldrivers || "All Drivers"}
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[820px] text-xs">
                  <thead>
                    <tr className="border-b-2 border-border bg-gray-100 dark:bg-gray-800">
                      {(trans.driver?.tableHeaders || [
                        "Driver name",
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
                    {drivers.map((driverItem: any) => {
                      const user = driverItem.driver?.user || {};
                      return (
                        <tr
                          key={driverItem.id}
                          className="border-b border-border hover:bg-muted transition-colors"
                        >
                          <td className="py-3 px-3 font-bold text-foreground">
                            {user.first_name} {user.last_name}
                          </td>
                          <td className="py-3 px-3 text-foreground whitespace-nowrap">
                            #{driverItem.id}
                          </td>
                          <td className="py-3 px-3 text-foreground">
                            {user.phone_number || "-"}
                          </td>
                          <td className="py-3 px-3 text-muted-foreground whitespace-nowrap">
                            {formatDate(new Date(user.date_joined), locale)}
                          </td>
                          <td className="py-3 px-3 text-foreground max-w-[200px] truncate">
                            {user.address || "-"}
                          </td>
                          <td className="py-3 px-3 font-bold whitespace-nowrap">
                            {user.trips_count || 0}
                          </td>
                          <td className="py-3 px-3 whitespace-nowrap">
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full font-bold ${
                                user.is_active
                                  ? "bg-green-50 text-green-700 border border-green-200"
                                  : "bg-red-50 text-red-700 border border-red-200"
                              }`}
                            >
                              {user.is_active
                                ? trans.driver?.status?.active || "Active"
                                : trans.driver?.status?.inactive || "Inactive"}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-center whitespace-nowrap">
                            <div className="flex items-center justify-center space-x-2">
                              <Button
                                onClick={() => {
                                  setSelectedDriver(driverItem);
                                  setShowDetailsModal(true);
                                }}
                                variant="ghost"
                                className="p-1.5 hover:bg-muted text-yellow-600 hover:text-yellow-700 transition-colors inline-flex"
                                title={trans.driver_card?.viewDetails || "View Details"}
                              >
                                <HiOutlineEye className="text-base" />
                              </Button>
                              <Button
                                onClick={() => handleOpenCommission(driverItem)}
                                variant="ghost"
                                className="p-1.5 hover:bg-muted text-blue-600 hover:text-blue-700 transition-colors inline-flex"
                                title={trans.driver?.commission?.title || "Commission"}
                              >
                                <FaMoneyBillWave className="text-base" />
                              </Button>
                              {user.is_active ? (
                                <Button
                                  onClick={() => handleDeactivate(user.id)}
                                  variant="ghost"
                                  disabled={actionLoading}
                                  className="p-1.5 hover:bg-muted text-red-600 hover:text-red-700 transition-colors inline-flex disabled:opacity-50"
                                  title={trans.driver_card?.deactivate || "Deactivate"}
                                >
                                  <FaPause className="text-base" />
                                </Button>
                              ) : (
                                <Button
                                  onClick={() => handleActivate(user.id)}
                                  variant="ghost"
                                  disabled={actionLoading}
                                  className="p-1.5 hover:bg-muted text-green-600 hover:text-green-700 transition-colors inline-flex disabled:opacity-50"
                                  title={trans.driver_card?.activate || "Activate"}
                                >
                                  <FaPlay className="text-base" />
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {
               driversLoading ?null: ( 
               driversData?.pagination.num_pages > 0 && (
                <div className="flex items-center justify-between px-6 border-t-2 border-border">
                  <div className="text-sm mx-auto text-muted-foreground">
                    {trans.pagination?.table || "Table"} {page} {trans.pagination?.of || "of"}{" "}
                    {pagination.num_pages || 1} {trans.pagination?.tables || "tables"}
                  </div>
                  <Pagination
                    currentPage={page}
                    onPageChange={setPage}
                    locale={locale}
                    totalPages={pagination.num_pages || 1}
                  />
                </div>
              ) )}
            </div>
          </div>

          {/* Mobile Cards */}
          <div className="xl:hidden space-y-4">
            {drivers.map((driverItem: any) => {
              const user = driverItem.driver?.user || {};
              return (
                <div
                  key={driverItem.id}
                  className="bg-card max-sm:max-w-[360px] mx-auto rounded-xl shadow-lg border-2 border-border p-4 hover:shadow-2xl hover:border-primary/60 transition-all"
                >
                  <div className="flex items-start justify-between mb-3 pb-3 border-b-2 border-border">
                    <div className="flex-1">
                      <h3 className="font-bold text-lg text-foreground mb-1">
                        {user.first_name} {user.last_name}
                      </h3>
                      <p className="text-sm text-muted-foreground">#{driverItem.id}</p>
                    </div>
                    <span
                      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border ${
                        user.is_active
                          ? "bg-green-50 text-green-700 border-green-200"
                          : "bg-red-50 text-red-700 border-red-200"
                      }`}
                    >
                      {user.is_active
                        ? trans.driver?.status?.active || "Active"
                        : trans.driver?.status?.inactive || "Inactive"}
                    </span>
                  </div>

                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-between py-2 border-b border-border">
                      <span className="text-sm text-muted-foreground font-semibold">
                        {trans.driver?.tableHeaders?.[2] || "Phone number"}
                      </span>
                      <span className="text-sm text-foreground font-bold">
                        {user.phone_number || "-"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-2 border-b border-border">
                      <span className="text-sm text-muted-foreground font-semibold">
                        {trans.driver?.tableHeaders?.[3] || "Include date"}
                      </span>
                      <span className="text-sm text-foreground font-bold">
                        {formatDate(new Date(user.date_joined), locale)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-2 border-b border-border">
                      <span className="text-sm text-muted-foreground font-semibold">
                        {trans.driver?.tableHeaders?.[4] || "Address"}
                      </span>
                      <span className="text-sm text-foreground font-bold max-w-[60%] truncate">
                        {user.address || "-"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-2">
                      <span className="text-sm text-muted-foreground font-semibold">
                        {trans.driver?.tableHeaders?.[5] || "Trips count"}
                      </span>
                      <span className="text-sm  font-bold">
                        {user.trips_count || 0}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    <Button
                      onClick={() => {
                        setSelectedDriver(driverItem);
                        setShowDetailsModal(true);
                      }}
                      className="flex-1 bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-foreground font-bold shadow-lg shadow-yellow-500/20"
                    >
                      <HiOutlineEye className="mr-2" /> {trans.driver_card?.viewDetails || "View Details"}
                    </Button>
                    <Button
                      onClick={() => handleOpenCommission(driverItem)}
                      variant="outline"
                      className="border-blue-500 text-blue-600 hover:bg-blue-50"
                    >
                      <FaMoneyBillWave className="mr-2" /> {trans.driver?.commission?.title || "Commission"}
                    </Button>
                    {user.is_active ? (
                      <Button
                        onClick={() => handleDeactivate(user.id)}
                        disabled={actionLoading}
                        variant="outline"
                        className="border-red-500 text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        <FaPause />
                      </Button>
                    ) : (
                      <Button
                        onClick={() => handleActivate(user.id)}
                        disabled={actionLoading}
                        variant="outline"
                        className="border-green-500 text-green-600 hover:bg-green-50 disabled:opacity-50"
                      >
                        <FaPlay />
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
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
      {showDetailsModal && selectedDriver && (
        <div
          onClick={() => {
            setShowDetailsModal(false);
            setSelectedDriver(null);
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
                  {trans.driver_card?.driverDetails || "Driver Details"}
                </h2>
                <div className="flex items-center gap-3">
                  {selectedDriver.driver?.user && (
                    <span
                      className={`px-4 py-2 rounded-full text-xs xl:text-sm font-bold border ${
                        selectedDriver.driver.user.is_active
                          ? "bg-green-500/20 text-green-400 border-green-500/30"
                          : "bg-red-500/20 text-red-400 border-red-500/30"
                      }`}
                    >
                      {selectedDriver.driver.user.is_active
                        ? trans.driver?.status?.active || "Active"
                        : trans.driver?.status?.inactive || "Inactive"}
                    </span>
                  )}
                  <button
                    onClick={() => {
                      setShowDetailsModal(false);
                      setSelectedDriver(null);
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
              {selectedDriver.driver?.user && (
                <>
                  {/* Personal Information */}
                <div className="bg-muted border-2 border-yellow-500/50 rounded-xl p-4 md:p-5">
                  <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                    <span className="w-1 h-6 bg-yellow-500 rounded-full"></span>
                    {trans.driver_card?.personalInfo || "Personal Information"}
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.driver_card?.driverId || "Driver ID"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base">#{selectedDriver.id}</p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.driver_card?.firstName || "First Name"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-words">
                        {selectedDriver.driver.user.first_name}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.driver_card?.lastName || "Last Name"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-words">
                        {selectedDriver.driver.user.last_name}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.driver_card?.email || "Email"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-all">
                        {selectedDriver.driver.user.email}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.driver_card?.phoneNumber || "Phone Number"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-words">
                        {selectedDriver.driver.user.phone_number || "-"}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.driver_card?.address || "Address"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-words">
                        {selectedDriver.driver.user.address || "-"}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.driver_card?.dateJoined || "Date Joined"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base">
                        {formatDate(new Date(selectedDriver.driver.user.date_joined), locale)}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.driver_card?.tripsCount || "Trips Count"}
                      </p>
                      <p className="font-semibold text-primary text-sm md:text-base">
                        {selectedDriver.driver.user.trips_count || 0}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Account Status */}
                <div className="bg-muted border-2 border-blue-400/50 rounded-xl p-4 md:p-5">
                  <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                    <span className="w-1 h-6 bg-blue-500 rounded-full"></span>
                    {trans.driver_card?.accountStatus || "Account Status"}
                  </h3>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 bg-card p-3 rounded-lg border border-border">
                      {selectedDriver.driver.user.is_active ? (
                        <FaCheckCircle className="text-green-500 text-xl flex-shrink-0" />
                      ) : (
                        <FaTimesCircle className="text-red-500 text-xl flex-shrink-0" />
                      )}
                      <span className="font-semibold text-foreground text-sm md:text-base">
                        {selectedDriver.driver.user.is_active
                          ? trans.driver_card?.active || "Active"
                          : trans.driver_card?.inactive || "Inactive"}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 bg-card p-3 rounded-lg border border-border">
                      {selectedDriver.driver.user.is_admin_verified ? (
                        <FaUserCheck className="text-green-500 text-xl flex-shrink-0" />
                      ) : (
                        <FaUserSlash className="text-yellow-500 text-xl flex-shrink-0" />
                      )}
                      <span className="font-semibold text-foreground text-sm md:text-base">
                        {selectedDriver.driver.user.is_admin_verified
                          ? trans.driver_card?.verified || "Verified"
                          : trans.driver_card?.unverified || "Unverified"}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 bg-card p-3 rounded-lg border border-border">
                      {selectedDriver.driver.user.is_profile_completed ? (
                        <FaCheckCircle className="text-green-500 text-xl flex-shrink-0" />
                      ) : (
                        <FaTimesCircle className="text-orange-500 text-xl flex-shrink-0" />
                      )}
                      <span className="font-semibold text-foreground text-sm md:text-base">
                        {selectedDriver.driver.user.is_profile_completed
                          ? trans.driver_card?.profileCompleted || "Profile Completed"
                          : trans.driver_card?.profileIncomplete || "Profile Incomplete"}
                      </span>
                    </div>
                  </div>
                </div>
                </>
              )}

                {/* Vehicle Information */}
              {selectedDriver.vehicle && (
                <div className="bg-muted border-2 border-purple-400/50 rounded-xl p-4 md:p-5">
                    <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                      <span className="w-1 h-6 bg-purple-500 rounded-full"></span>
                      {trans.driver_card?.vehicleInfo || "Vehicle Information"}
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="bg-card p-3 rounded-lg border border-border">
                        <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                          {trans.driver_card?.vehicleType || "Vehicle Type"}
                        </p>
                        <p className="font-semibold text-foreground text-sm md:text-base break-words">
                          {selectedDriver.vehicle.vehicle_type?.name_en || selectedDriver.vehicle.vehicle_type?.name_ar || "-"}
                        </p>
                      </div>
                      <div className="bg-card p-3 rounded-lg border border-border">
                        <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                          {trans.driver_card?.vehicleNumber || "Vehicle Number"}
                        </p>
                        <p className="font-semibold text-foreground text-sm md:text-base break-words">
                          {selectedDriver.vehicle.vehicle_number || "-"}
                        </p>
                      </div>
                      <div className="bg-card p-3 rounded-lg border border-border">
                        <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                          {trans.driver_card?.yearOfManufacture || "Year of Manufacture"}
                        </p>
                        <p className="font-semibold text-foreground text-sm md:text-base">
                          {selectedDriver.vehicle.year_of_manufacture || "-"}
                        </p>
                      </div>
                      <div className="bg-card p-3 rounded-lg border border-border">
                        <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                          {trans.driver_card?.maxPassengers || "Max Passengers"}
                        </p>
                        <p className="font-semibold text-foreground text-sm md:text-base">
                          {selectedDriver.vehicle.vehicle_type?.max_passengers_count || "-"}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

              {/* Driver Documents */}
              {selectedDriver.driver && (selectedDriver.driver.pco || selectedDriver.driver.dbs || selectedDriver.driver.dvla) && (
                <div className="bg-muted border-2 border-indigo-400/50 rounded-xl p-4 md:p-5">
                    <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                      <span className="w-1 h-6 bg-indigo-500 rounded-full"></span>
                      {trans.driver_card?.driverDocuments || "Driver Documents"}
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                      {selectedDriver.driver.pco && (
                        <div className="bg-card p-3 rounded-lg border border-border">
                          <p className="text-xs md:text-sm font-medium text-muted-foreground mb-2">
                            {trans.driver_card?.pcoLicence || "PCO Licence"}
                          </p>
                          <button
                            onClick={() => setDocumentPreview({ url: selectedDriver.driver.pco, title: trans.driver_card?.pcoLicence || "PCO Licence" })}
                            className="w-full text-xs md:text-sm px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded font-semibold transition-colors"
                          >
                            {trans.driver_card?.viewDocument || "View Document"}
                          </button>
                        </div>
                      )}
                      {selectedDriver.driver.dbs && (
                        <div className="bg-card p-3 rounded-lg border border-border">
                          <p className="text-xs md:text-sm font-medium text-muted-foreground mb-2">
                            {trans.driver_card?.dbsCertificate || "DBS Certificate"}
                          </p>
                          <button
                            onClick={() => setDocumentPreview({ url: selectedDriver.driver.dbs, title: trans.driver_card?.dbsCertificate || "DBS Certificate" })}
                            className="w-full text-xs md:text-sm px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded font-semibold transition-colors"
                          >
                            {trans.driver_card?.viewDocument || "View Document"}
                          </button>
                        </div>
                      )}
                      {selectedDriver.driver.dvla && (
                        <div className="bg-card p-3 rounded-lg border border-border">
                          <p className="text-xs md:text-sm font-medium text-muted-foreground mb-2">
                            {trans.driver_card?.dvlaLicence || "DVLA Licence"}
                          </p>
                          <button
                            onClick={() => setDocumentPreview({ url: selectedDriver.driver.dvla, title: trans.driver_card?.dvlaLicence || "DVLA Licence" })}
                            className="w-full text-xs md:text-sm px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded font-semibold transition-colors"
                          >
                            {trans.driver_card?.viewDocument || "View Document"}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}

              {/* Vehicle Documents */}
              {selectedDriver.vehicle && (selectedDriver.vehicle.mot || selectedDriver.vehicle.phv) && (
                <div className="bg-muted border-2 border-emerald-400/50 rounded-xl p-4 md:p-5">
                    <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                      <span className="w-1 h-6 bg-emerald-500 rounded-full"></span>
                      {trans.driver_card?.vehicleDocuments || "Vehicle Documents"}
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {selectedDriver.vehicle.mot && (
                        <div className="bg-card p-3 rounded-lg border border-border">
                          <p className="text-xs md:text-sm font-medium text-muted-foreground mb-2">
                            {trans.driver_card?.motCertificate || "MOT Certificate"}
                          </p>
                          <button
                            onClick={() => setDocumentPreview({ url: selectedDriver.vehicle.mot, title: trans.driver_card?.motCertificate || "MOT Certificate" })}
                            className="w-full text-xs md:text-sm px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded font-semibold transition-colors"
                          >
                            {trans.driver_card?.viewDocument || "View Document"}
                          </button>
                        </div>
                      )}
                      {selectedDriver.vehicle.phv && (
                        <div className="bg-card p-3 rounded-lg border border-border">
                          <p className="text-xs md:text-sm font-medium text-muted-foreground mb-2">
                            {trans.driver_card?.phvLicence || "PHV Licence"}
                          </p>
                          <button
                            onClick={() => setDocumentPreview({ url: selectedDriver.vehicle.phv, title: trans.driver_card?.phvLicence || "PHV Licence" })}
                            className="w-full text-xs md:text-sm px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded font-semibold transition-colors"
                          >
                            {trans.driver_card?.viewDocument || "View Document"}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}

              {/* Bank Details */}
              {selectedDriver.driver?.bank_details && (
                <div className="bg-muted border-2 border-orange-400/50 rounded-xl p-4 md:p-5">
                    <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                      <span className="w-1 h-6 bg-orange-500 rounded-full"></span>
                      {trans.driver_card?.bankDetails || "Bank Details"}
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div className="bg-card p-3 rounded-lg border border-border">
                        <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                          {trans.driver_card?.accountNumber || "Account Number"}
                        </p>
                        <p className="font-semibold text-foreground text-sm md:text-base break-words">
                          {selectedDriver.driver.bank_details.bank_account_number || "-"}
                        </p>
                      </div>
                      <div className="bg-card p-3 rounded-lg border border-border">
                        <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                          {trans.driver_card?.sortCode || "Sort Code"}
                        </p>
                        <p className="font-semibold text-foreground text-sm md:text-base break-words">
                          {selectedDriver.driver.bank_details.sort_code || "-"}
                        </p>
                      </div>
                      <div className="bg-card p-3 rounded-lg border border-border">
                        <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                          {trans.driver_card?.registeredAddress || "Registered Address"}
                        </p>
                        <p className="font-semibold text-foreground text-sm md:text-base break-words">
                          {selectedDriver.driver.bank_details.registered_address || "-"}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
            </div>

            {/* Modal Footer */}
            <div className="sticky bottom-0 bg-gradient-to-r from-card to-background px-4 xl:px-6 py-4 lg:py-5 border-t-2 border-border rounded-b-2xl flex flex-col sm:flex-row justify-end gap-3">
              {selectedDriver.driver?.user?.is_active ? (
                <Button
                  onClick={() => handleDeactivate(selectedDriver.driver.user.id)}
                  disabled={actionLoading}
                  variant="destructive"
                  className="flex items-center gap-2"
                >
                  <FaPause className="w-4 h-4" />
                  {trans.driver_card?.deactivate || "Deactivate"}
                </Button>
              ) : (
                <Button
                  onClick={() => handleActivate(selectedDriver.driver.user.id)}
                  disabled={actionLoading}
                  className="flex items-center gap-2 bg-green-600 hover:bg-green-700"
                >
                  <FaPlay className="w-4 h-4" />
                  {trans.driver_card?.activate || "Activate"}
                </Button>
              )}
              <Button
                onClick={() => {
                  setShowDetailsModal(false);
                  setSelectedDriver(null);
                }}
                variant="outline"
                className="border-border text-foreground hover:bg-muted"
              >
                {trans.driver_card?.close || "Close"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Document Preview Modal */}
      {documentPreview && (
        <div
          onClick={() => setDocumentPreview(null)}
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-[60] p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-xl w-full max-w-6xl max-h-[90vh] flex flex-col shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h3 className="text-xl font-bold text-gray-900">{documentPreview!.title}</h3>
              <button
                onClick={() => setDocumentPreview(null)}
                className="text-gray-500 hover:text-gray-700 transition-colors p-2"
              >
                <HiOutlineX className="w-6 h-6" />
              </button>
            </div>

            {/* Document Content */}
            <div className="flex-1 overflow-auto p-4 bg-gray-100">
              {documentPreview!.url.toLowerCase().endsWith('.pdf') || documentPreview!.url.includes('.pdf') ? (
                <iframe
                  src={documentPreview!.url}
                  className="w-full h-full min-h-[600px] border-0 rounded-lg"
                  title={documentPreview!.title}
                />
              ) : (
                <div className="flex items-center justify-center">
                  <img
                    src={documentPreview!.url}
                    alt={documentPreview!.title}
                    className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-lg"
                    onError={(e) => {
                      // If image fails, try to show as PDF
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                      const container = target.parentElement;
                      if (container && documentPreview) {
                        container.innerHTML = `
                          <iframe
                            src="${documentPreview.url}"
                            class="w-full h-full min-h-[600px] border-0 rounded-lg"
                            title="${documentPreview.title}"
                          />
                        `;
                      }
                    }}
                  />
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50">
              <a
                href={documentPreview!.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline font-semibold flex items-center gap-2"
              >
                <FaFileAlt />
                {trans.driver_card?.openInNewTab || "Open in new tab"}
              </a>
              <Button
                onClick={() => setDocumentPreview(null)}
                variant="outline"
                className="border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                {trans.driver_card?.close || "Close"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Commission Modal */}
      <GlobalModal
        isOpen={showCommissionModal}
        onClose={() => {
          setShowCommissionModal(false);
          setSelectedDriverForCommission(null);
          setCommissionPercentage("");
        }}
      >
        <div className="p-4 sm:p-6 w-full">
          <h2 className="text-xl font-bold text-foreground mb-4">
            {trans.driver?.commission?.title || "Driver Commission"}
          </h2>
          
          {selectedDriverForCommission?.driver?.user && (
            <div className="mb-4 p-3 bg-muted rounded-lg border border-border">
              <p className="text-sm text-muted-foreground mb-1">
                {trans.driver?.commission?.driverName || "Driver"}
              </p>
              <p className="font-semibold text-foreground">
                {selectedDriverForCommission.driver.user.first_name} {selectedDriverForCommission.driver.user.last_name}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                ID: #{selectedDriverForCommission.id}
              </p>
            </div>
          )}

          {commissionLoading ? (
            <div className="flex items-center justify-center py-8">
              <IsLoading />
            </div>
          ) : commissionData?.data ? (
            <div className="space-y-4">
              {/* Display Current Commission Info */}
              <div className="bg-muted border-2 border-blue-400/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-blue-500 rounded-full"></span>
                  {trans.driver?.commission?.currentCommission || "Current Commission"}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.driver?.commission?.driverPercentage || "Driver Commission %"}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base">
                      {(commissionData.data.driver_commission_percentage ?? 0)}%
                    </p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.driver?.commission?.effectiveDriverPercentage || "Effective Driver %"}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base">
                      {(commissionData.data.effective_driver_percentage ?? 0)}%
                    </p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.driver?.commission?.effectiveCompanyPercentage || "Effective Company %"}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base">
                      {(commissionData.data.effective_company_percentage ?? 0)}%
                    </p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.driver?.commission?.fallbackSource || "Fallback Source"}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base">
                      {commissionData.data.fallback_source || "-"}
                    </p>
                  </div>
                  {commissionData.data.vehicle_type && (
                    <div className="bg-card p-3 rounded-lg border border-border sm:col-span-2">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.driver?.commission?.vehicleType || "Vehicle Type"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base">
                        {locale === "ar" 
                          ? commissionData.data.vehicle_type.name_ar 
                          : commissionData.data.vehicle_type.name_en}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Update Commission Form */}
              <div className="bg-muted border-2 border-green-400/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-green-500 rounded-full"></span>
                  {trans.driver?.commission?.updateCommission || "Update Commission"}
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      {trans.driver?.commission?.driverCommissionPercentage || "Driver Commission Percentage"} *
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      value={commissionPercentage}
                      onChange={(e) => setCommissionPercentage(e.target.value)}
                      className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
                      placeholder="75.00"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      {trans.driver?.commission?.percentageHint || "Enter a value between 0 and 100"}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 pt-2">
                    <Button
                      onClick={handleUpdateCommission}
                      disabled={isUpdatingCommission || commissionPercentage.trim() === ""}
                      className="bg-primary text-black font-semibold hover:bg-primary/90 disabled:opacity-60"
                    >
                      {isUpdatingCommission
                        ? trans.driver?.commission?.updating || "Updating..."
                        : trans.driver?.commission?.update || "Update Commission"}
                    </Button>
                    <Button
                      onClick={() => {
                        setShowCommissionModal(false);
                        setSelectedDriverForCommission(null);
                        setCommissionPercentage("");
                      }}
                      variant="outline"
                      disabled={isUpdatingCommission}
                      className="border-border text-foreground hover:bg-muted"
                    >
                      {trans.driver?.commission?.cancel || "Cancel"}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-muted-foreground">
                {trans.driver?.commission?.loadError || "Failed to load commission data"}
              </p>
            </div>
          )}
        </div>
      </GlobalModal>
    </div>
  );
}

