"use client";

import React, { useState, useMemo, useEffect } from "react";
import { useForm, SubmitHandler } from "react-hook-form";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Locale } from "../../../../i18n.config";
import { fetchData } from "@/lib/api/fetchData";
import { postData } from "@/lib/api/postData";
import { putData } from "@/lib/api/putApi";
import { deleteData } from "@/lib/api/deleteApi";
import { toast } from "react-toastify";
import { Button } from "@/components/ui/button";
import IsLoading from "../ISloading";
import GlobalModal from "../GlobalModal";
import { extract_error } from "@/lib/api/errorApi";
import { FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import Pagination from "../Pagination";
import { VEHICLE_TYPES } from "@/lib/constants/vehicleTypes";
import CustomSelectInput from "../ControlledFields/CustomSelectInput";

type AirportFee = {
  id: number;
  airport: {
    id: number;
    name_en: string;
    name_ar: string;
  };
  vehicle_type: {
    id: number;
    name_en: string;
    name_ar: string;
  };
  pickup_fee: string;
  dropoff_fee: string;
};

type Airport = {
  id: number;
  name_en: string;
  name_ar: string;
};

type VehicleType = {
  id: number;
  name_en: string;
  name_ar: string;
};

type AirportFeesResponse = {
  success: boolean;
  message: string;
  data: AirportFee[];
  pagination: {
    count: number;
    num_pages: number;
    current_page: number;
    page_size: number;
  };
};

type VehicleTypesResponse = {
  success: boolean;
  data: VehicleType[];
};

type AirportFeesFormData = {
  airport_id: number;
  vehicle_type_ids: number[] |string[];
  pickup_fee: string;
  dropoff_fee: string;
};

type AirportFeesProps = {
  trans: any;
  token?: string;
  locale: Locale;
};

export default function AirportFees({
  trans,
  token,
  locale,
}: AirportFeesProps) {
  const [page, setPage] = useState(1);
  const [showFormModal, setShowFormModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedFee, setSelectedFee] = useState<AirportFee | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const queryClient = useQueryClient();

  // Fetch airport fees for display (paginated)
  const {
    data: feesData,
    isLoading,
    error,
  } = useQuery<AirportFeesResponse>({
    queryKey: ["airport-fees", page, token, locale],
    queryFn: async () => {
      try {
        return await fetchData({
          endpoint: "/api/pricing/airport-fees/",
          token,
          queryParams: {
            locale,
            page: page.toString(),
            page_size: "10",
          },
        });
      } catch (err: any) {
        console.error("Failed to fetch airport fees:", err);
        toast.error(
          extract_error(err) || err?.message || "Failed to load airport fees"
        );
        throw err;
      }
    },
    enabled: !!token,
    retry: 1,
    refetchOnWindowFocus: false,
  });


  // Fetch all airport fees for validation (to check duplicates)
  const { data: allFeesData } = useQuery<AirportFeesResponse>({
    queryKey: ["airport-fees-all", token, locale],
    queryFn: async () => {
      try {
        return await fetchData({
          endpoint: "/api/pricing/airport-fees/",
          token,
          queryParams: {
            locale,
            page: "1",
            page_size: "1000", // Large page size to get all fees for validation
          },
        });
      } catch (err: any) {
        console.error("Failed to fetch all airport fees:", err);
        return {
          success: false,
          message: err?.message || "Failed to fetch airport fees",
          data: [],
          pagination: {
            count: 0,
            num_pages: 0,
            current_page: 1,
            page_size: 1000,
          },
        } as AirportFeesResponse;
      }
    },
    enabled: !!token,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  // Fetch airports
  const { data: airportsData } = useQuery<Airport[]>({
    queryKey: ["airports", locale],
    queryFn: async () => {
      try {
        const response = await fetchData<Airport[] | { data: Airport[] }>({
          endpoint: "/api/trips/list-airports/",
          token,
          queryParams: { locale },
        });
        // Handle both array and wrapped response
        if (Array.isArray(response)) {
          return response;
        }
        if (response && typeof response === 'object' && 'data' in response) {
          return (response as { data: Airport[] }).data;
        }
        return [];
      } catch (err: any) {
        console.error("Failed to fetch airports:", err);
        return [];
      }
    },
    enabled: !!token,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  // Use static vehicle types (no API endpoint for vehicle types)
const { data: vehicleTypes =[] ,isLoading :isLoadingVehicleTypes } =
  useQuery({
    queryKey: ["vehicle-types"],
    queryFn: async () =>
      fetchData<{ name_ar: string; name_en: string; id: number }[]>({ endpoint: "/api/vehicle/vehicle-types/" }),
    select: (data) =>
      data.map((item) => ({
        label: item.name_en,
        value: item.id.toString(),
      })),
  }) || [];
  const airports = airportsData?.map((airport) => ({
    label: locale === "ar" ? airport.name_ar : airport.name_en,
    value: airport.id.toString(),
  })  ) || [];

  const {
    register,
    handleSubmit,
    reset,
    watch,
    control,
    formState: { errors },
  } = useForm<AirportFeesFormData>({
    defaultValues: {
      airport_id: 0,
      vehicle_type_ids: [],
      pickup_fee: "0.00",
      dropoff_fee: "0.00",
    },
  });

  // Watch the selected airport to filter vehicle types
  const selectedAirportId = watch("airport_id");


  // Get vehicle types that are already used for the selected airport
  const getDisabledVehicleTypes = (): number[] => {
    if (!selectedAirportId || selectedAirportId === 0) return [];
    
    const allFees = allFeesData?.data || [];
    const usedVehicleTypeIds = allFees
      .filter((fee) => {
        // For updates, exclude the current item being edited
        if (isEditing && selectedFee && fee.id === selectedFee.id) {
          return false;
        }
        return fee.airport.id === selectedAirportId;
      })
      .map((fee) => fee.vehicle_type.id);
    
    return usedVehicleTypeIds;
  };

  const disabledVehicleTypeIds = getDisabledVehicleTypes();

  // Reset vehicle type if it becomes disabled when airport changes

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: AirportFeesFormData) =>
      postData({
        endpoint: "/api/pricing/airport-fees/",
        token,
        body: data,
        queryParams: { locale },
        noToast: false, // Let API show toast
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["airport-fees"] });
      queryClient.invalidateQueries({ queryKey: ["airport-fees-all"] });
      setShowFormModal(false);
      reset();
      setSelectedFee(null);
      setIsEditing(false);
    },
    onError: () => {
      // Error toast is handled by postData
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: AirportFeesFormData }) =>
      putData({
        endpoint: `/api/pricing/airport-fees/${id}/`,
        token,
        body: data,
        queryParams: { locale },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["airport-fees"] });
      queryClient.invalidateQueries({ queryKey: ["airport-fees-all"] });
      toast.success(trans.airportFees?.updateSuccess || "Airport fee updated successfully");
      setShowFormModal(false);
      reset();
      setSelectedFee(null);
      setIsEditing(false);
    },
    onError: (error: any) => {
      const errorMessage =
        extract_error(error) || error?.message || "Failed to update airport fee";
      toast.error(errorMessage);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      deleteData({
        endpoint: `/api/pricing/airport-fees/${id}`,
        token,
        queryParams: { locale },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["airport-fees"] });
      queryClient.invalidateQueries({ queryKey: ["airport-fees-all"] });
      toast.success(trans.airportFees?.deleteSuccess || "Airport fee deleted successfully");
      setShowDeleteModal(false);
      setSelectedFee(null);
    },
    onError: (error: any) => {
      const errorMessage =
        extract_error(error) || error?.message || "Failed to delete airport fee";
      toast.error(errorMessage);
    },
  });

  const handleCreate = () => {
    setIsEditing(false);
    setSelectedFee(null);
    reset({
      airport_id: 0,
      vehicle_type_ids: [],
      pickup_fee: "0.00",
      dropoff_fee: "0.00",
    });
    setShowFormModal(true);
  };

  const handleEdit = (fee: AirportFee) => {
    setIsEditing(true);
    setSelectedFee(fee);
    reset({
      airport_id: fee.airport.id,
      vehicle_type_ids:[ fee.vehicle_type.id.toString()],
      pickup_fee: fee.pickup_fee,
      dropoff_fee: fee.dropoff_fee,
    });
    setShowFormModal(true);
  };

  const handleDelete = (fee: AirportFee) => {
    setSelectedFee(fee);
    setShowDeleteModal(true);
  };

  // Check if combination already exists
  const checkDuplicate = (airportId: number, vehicleTypeId: number, excludeId?: number): boolean => {
    const allFees = allFeesData?.data || [];
    if (allFees.length === 0) return false;
    
    return allFees.some((fee) => {
      // For updates, exclude the current item being edited
      if (excludeId && fee.id === excludeId) return false;
      
      return (
        fee.airport.id === airportId && 
        fee.vehicle_type.id === vehicleTypeId
      );
    });
  };

  const onSubmit: SubmitHandler<AirportFeesFormData> = (data) => {
    // Validate that airport and vehicle type are selected
    if (!data.airport_id || data.airport_id === 0) {
      toast.error(trans.airportFees?.airportRequired || "Please select an airport");
      return;
    }
    
    if (!data.vehicle_type_ids || data.vehicle_type_ids.length === 0) {
      toast.error(trans.airportFees?.vehicleTypeRequired || "Please select a vehicle type");
      return;
    }

    // Check for duplicate combination
    const isDuplicate = isEditing && selectedFee
      ? checkDuplicate(data.airport_id, parseInt(String(data.vehicle_type_ids[0])), selectedFee.id)
      : checkDuplicate(data.airport_id, parseInt(String(data.vehicle_type_ids[0])));



    if (isEditing && selectedFee) {
      updateMutation.mutate({ id: selectedFee.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleDeleteConfirm = () => {
    if (selectedFee) {
      deleteMutation.mutate(selectedFee.id);
    }
  };

  const fees = feesData?.data || [];
  const pagination = feesData?.pagination || {
    count: 0,
    num_pages: 1,
    current_page: 1,
    page_size: 10,
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <IsLoading />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card rounded-xl shadow-xl border-2 border-border p-6">
        <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
          <p className="text-red-700 font-medium">
            {trans.airportFees?.loadError ||
              "Failed to load airport fees. Please try again."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header with Add Button */}
      <div className="flex items-center justify-between mb-4">
        <Button
          onClick={handleCreate}
          className="w-full sm:w-auto bg-primary hover:bg-primary/90 text-foreground font-semibold shadow-lg shadow-primary/30 text-sm md:text-base"
        >
          <FaPlus className="mr-2" />
          {trans.airportFees?.addButton || "Add Airport Fee"}
        </Button>
      </div>

      {fees.length === 0 ? (
        <div className="bg-card rounded-xl shadow-xl border-2 border-border p-8 md:p-12 text-center">
          <p className="text-muted-foreground text-base md:text-lg">
            {trans.airportFees?.empty || "No airport fees found"}
          </p>
        </div>
      ) : (
        <>
          {/* Desktop Table */}
          <div className="hidden xl:block">
            <div className="bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[800px] text-xs md:text-sm">
                  <thead>
                    <tr className="border-b-2 border-border bg-gray-100 dark:bg-gray-800">
                      <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                        {trans.airportFees?.airport || "Airport"}
                      </th>
                      <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                        {trans.airportFees?.vehicleType || "Vehicle Type"}
                      </th>
                      <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                        {trans.airportFees?.pickupFee || "Pickup Fee"}
                      </th>
                      <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                        {trans.airportFees?.dropoffFee || "Dropoff Fee"}
                      </th>
                      <th className="text-center py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                        {trans.airportFees?.actions || "Actions"}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {fees.map((fee) => (
                      <tr
                        key={fee.id}
                        className="border-b border-border hover:bg-muted transition-colors"
                      >
                        <td className="py-3 px-4 font-bold text-foreground">
                          {locale === "ar"
                            ? fee.airport.name_ar
                            : fee.airport.name_en}
                        </td>
                        <td className="py-3 px-4 font-bold text-foreground">
                          {locale === "ar"
                            ? fee.vehicle_type.name_ar
                            : fee.vehicle_type.name_en}
                        </td>
                        <td className="py-3 px-4 text-foreground font-semibold">
                          £{fee.pickup_fee}
                        </td>
                        <td className="py-3 px-4 text-foreground font-semibold">
                          £{fee.dropoff_fee}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center justify-center gap-2">
                            <Button
                              onClick={() => handleEdit(fee)}
                              variant="ghost"
                              className="p-1.5 hover:bg-muted text-yellow-600 hover:text-yellow-700 transition-colors"
                              title={trans.airportFees?.edit || "Edit"}
                            >
                              <FaEdit className="text-base" />
                            </Button>
                            <Button
                              onClick={() => handleDelete(fee)}
                              variant="ghost"
                              className="p-1.5 hover:bg-muted text-red-600 hover:text-red-700 transition-colors"
                              title={trans.airportFees?.delete || "Delete"}
                            >
                              <FaTrash className="text-base" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {pagination.num_pages > 1 && (
                <div className="flex items-center justify-between px-4 md:px-6 py-4 border-t-2 border-border">
                  <div className="text-xs md:text-sm text-muted-foreground">
                    {trans.pagination?.table || "Page"} {page} {trans.pagination?.of || "of"}{" "}
                    {pagination.num_pages} {trans.pagination?.tables || "pages"}
                  </div>
                  <Pagination
                    currentPage={page}
                    onPageChange={setPage}
                    locale={locale}
                    totalPages={pagination.num_pages}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Mobile Cards */}
          <div className="xl:hidden space-y-4">
            {fees.map((fee) => (
              <div
                key={fee.id}
                className="bg-card rounded-xl shadow-lg border-2 border-border p-4 hover:shadow-xl hover:border-primary/60 transition-all"
              >
                <div className="flex items-start justify-between mb-3 pb-3 border-b-2 border-border">
                  <div className="flex-1">
                    <h3 className="font-bold text-base md:text-lg text-foreground mb-1">
                      {locale === "ar"
                        ? fee.airport.name_ar
                        : fee.airport.name_en}
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      {locale === "ar"
                        ? fee.vehicle_type.name_ar
                        : fee.vehicle_type.name_en}
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div className="bg-muted/50 p-2 rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">
                      {trans.airportFees?.pickupFee || "Pickup Fee"}
                    </p>
                    <p className="font-semibold text-sm text-foreground">
                      £{fee.pickup_fee}
                    </p>
                  </div>
                  <div className="bg-muted/50 p-2 rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">
                      {trans.airportFees?.dropoffFee || "Dropoff Fee"}
                    </p>
                    <p className="font-semibold text-sm text-foreground">
                      £{fee.dropoff_fee}
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                  <Button
                    onClick={() => handleEdit(fee)}
                    variant="ghost"
                    className="p-2 hover:bg-muted text-yellow-600 hover:text-yellow-700 transition-colors"
                    title={trans.airportFees?.edit || "Edit"}
                  >
                    <FaEdit className="text-base" />
                  </Button>
                  <Button
                    onClick={() => handleDelete(fee)}
                    variant="ghost"
                    className="p-2 hover:bg-muted text-red-600 hover:text-red-700 transition-colors"
                    title={trans.airportFees?.delete || "Delete"}
                  >
                    <FaTrash className="text-base" />
                  </Button>
                </div>
              </div>
            ))}
            {pagination.num_pages > 1 && (
              <div className="flex flex-col items-center gap-3 pt-4">
                <div className="text-xs text-muted-foreground">
                  {trans.pagination?.table || "Page"} {page} {trans.pagination?.of || "of"}{" "}
                  {pagination.num_pages} {trans.pagination?.tables || "pages"}
                </div>
                <Pagination
                  currentPage={page}
                  onPageChange={setPage}
                  locale={locale}
                  totalPages={pagination.num_pages}
                />
              </div>
            )}
          </div>
        </>
      )}

      {/* Create/Edit Modal */}
      <GlobalModal
        isOpen={showFormModal}
        onClose={() => {
          if (!createMutation.isPending && !updateMutation.isPending) {
            setShowFormModal(false);
            reset();
            setSelectedFee(null);
            setIsEditing(false);
          }
        }}
      >
        <div className="p-4 md:p-6 w-full">
          <h2 className="text-lg md:text-xl font-bold text-foreground mb-4 md:mb-6">
            {isEditing
              ? trans.airportFees?.editTitle || "Edit Airport Fee"
              : trans.airportFees?.createTitle || "Create New Airport Fee"}
          </h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
              {/* Airport */}
              <div>
                		<CustomSelectInput
									name="airport_id"
									label={trans.airportFees?.airport || "Airport"}
									control={control}
									options={airports || []}
                  isLoading={isLoadingVehicleTypes}
									required
									containerClassName="col-span-1 md:col-span-2"
								/>
           
                {errors.airport_id && (
                  <p className="text-error text-sm mt-1">
                    {errors.airport_id.message}
                  </p>
                )}
              </div>

              {/* Vehicle Type */}
              <div>
            		<CustomSelectInput  
									name="vehicle_type_ids"
									label={trans.airportFees?.vehicleType || "Vehicle Type"}
									control={control}
									options={vehicleTypes || []}
                  isLoading={isLoadingVehicleTypes}
									required
									containerClassName="col-span-1 md:col-span-2"
									isMulti
								/>
                {errors.vehicle_type_ids && (
                  <p className="text-error text-sm mt-1">
                    {errors.vehicle_type_ids.message}
                  </p>
                )}
            
              </div>

              {/* Pickup Fee */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {trans.airportFees?.pickupFee || "Pickup Fee"}
                  <span className="text-red-500 ml-1">*</span>
                </label>
                <input
                  type="text"
                  {...register("pickup_fee", {
                    required: trans.airportFees?.pickupFeeRequired || "Pickup fee is required",
                    pattern: {
                      value: /^\d+(\.\d{1,2})?$/,
                      message: trans.airportFees?.pickupFeeInvalid || "Invalid fee format",
                    },
                  })}
                  placeholder="5.00"
                  className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
                />
                {errors.pickup_fee && (
                  <p className="text-error text-sm mt-1">
                    {errors.pickup_fee.message}
                  </p>
                )}
              </div>

              {/* Dropoff Fee */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {trans.airportFees?.dropoffFee || "Dropoff Fee"}
                  <span className="text-red-500 ml-1">*</span>
                </label>
                <input
                  type="text"
                  {...register("dropoff_fee", {
                    required: trans.airportFees?.dropoffFeeRequired || "Dropoff fee is required",
                    pattern: {
                      value: /^\d+(\.\d{1,2})?$/,
                      message: trans.airportFees?.dropoffFeeInvalid || "Invalid fee format",
                    },
                  })}
                  placeholder="5.00"
                  className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
                />
                {errors.dropoff_fee && (
                  <p className="text-error text-sm mt-1">
                    {errors.dropoff_fee.message}
                  </p>
                )}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-4 border-t-2 border-border">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setShowFormModal(false);
                  reset();
                  setSelectedFee(null);
                  setIsEditing(false);
                }}
                disabled={createMutation.isPending || updateMutation.isPending}
                className="w-full sm:flex-1 font-semibold"
              >
                {trans.airportFees?.cancel || "Cancel"}
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="w-full sm:flex-1 font-semibold bg-primary hover:bg-primary/90 text-foreground shadow-lg shadow-primary/30"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? trans.airportFees?.saving || "Saving..."
                  : isEditing
                  ? trans.airportFees?.updateButton || "Update"
                  : trans.airportFees?.createButton || "Create"}
              </Button>
            </div>
          </form>
        </div>
      </GlobalModal>

      {/* Delete Confirmation Modal */}
      <GlobalModal
        isOpen={showDeleteModal}
        onClose={() => {
          if (!deleteMutation.isPending) {
            setShowDeleteModal(false);
            setSelectedFee(null);
          }
        }}
      >
        <div className="p-4 md:p-6 w-full">
          <h2 className="text-lg md:text-xl font-bold text-foreground mb-4">
            {trans.airportFees?.deleteTitle || "Delete Airport Fee"}
          </h2>
          <p className="text-sm text-muted-foreground mb-4">
            {trans.airportFees?.deleteMessage ||
              "Are you sure you want to delete this airport fee? This action cannot be undone."}
          </p>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setShowDeleteModal(false);
                setSelectedFee(null);
              }}
              disabled={deleteMutation.isPending}
              className="w-full sm:flex-1 font-semibold"
            >
              {trans.airportFees?.cancel || "Cancel"}
            </Button>
            <Button
              type="button"
              onClick={handleDeleteConfirm}
              disabled={deleteMutation.isPending}
              className="w-full sm:flex-1 font-semibold bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30 disabled:opacity-60"
            >
              {deleteMutation.isPending
                ? trans.airportFees?.deleting || "Deleting..."
                : trans.airportFees?.deleteConfirm || "Delete"}
            </Button>
          </div>
        </div>
      </GlobalModal>
    </div>
  );
}
